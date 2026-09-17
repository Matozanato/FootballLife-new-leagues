r"""python hdr127.py [N] [--out sider/fl26hdr127.lua]  -> a module that widens the season header

The standings object begins with a header of exactly 100 entries of 0xb4, one per
competition instance, followed by 600 phase tables of 0x187c.  A season with more than 100
competitions silently loses the surplus: the leagues that miss out never get a row for the
new season and keep writing into the previous one, which is why a table can show 76 matches
played -- two seasons of 38 -- and about 130 points.

0x39a8f0 is not the object's allocation; it is an offset *into* it, and another member sits
at +0x39a9f0.  So the header cannot simply be pushed outwards -- the boundary has to stay
where it is, and the extra header entries are paid for out of phase tables:

    entries   header bytes   tables that still fit
       100        0x4650              600
       127        0x594c              599

That is the whole trade at 127: twenty-seven more competitions for one phase table.  127 is
the ceiling of the cheap version, because every bound is `cmp r32, 0x64` with an 8-bit
immediate and 0x7f is the largest value that still fits in a signed byte.  Above 127 each
of the thirteen bounds has to grow to `81 /7 id`, which is longer than the instruction it
replaces and therefore needs a trampoline per site.

This generator disassembles every site hdrscan.py found, locates the immediate inside each
instruction, and writes a nullguard-style applier with exact old/new bytes.  It writes only
the lua file; nothing touches the game.

    python hdr127.py                  the 127-entry module
    python hdr127.py 120              a smaller step, if 127 turns out to cost too much
"""
import os
import struct
import sys

try:
    import capstone
except ImportError:
    raise SystemExit("hdr127 needs capstone: python -m pip install capstone")

EXE = os.path.join(os.environ.get("FL26_DIR", r"E:\instalacija"), "FL_2026.exe")
IMAGE_BASE = 0x140000000

HDR_STRIDE = 0xb4
BOUND_OLD = 0x64                 # 100 header entries
OBJ_BASE_OLD = 0x4650            # = 100 * 0xb4
OBJ_STRIDE = 0x187c
OBJ_COUNT_OLD = 0x258            # 600 phase tables
TOTAL = 0x39a8f0                 # the member boundary that must not move

# every site hdrscan.py reported, by kind
BOUNDS = [0x14158f71c, 0x14158f73c, 0x14158f760, 0x14158f78c, 0x14158f7ac,
          0x14159048e, 0x1415904be, 0x14159ec1d, 0x14159ec4d, 0x14159ecfd,
          0x14159ed3d, 0x14159ee70, 0x14159ee91]
OBJ_BASE = [0x1414fd472, 0x14158df94, 0x14158f39d, 0x14158f8e3, 0x14158fe4f, 0x14159026e,
            0x14e9b7d86, 0x14ea4168b, 0x15ac4cb48]
OBJ_COUNT = [0x1413fb202, 0x1414fd477, 0x14158df84, 0x14158f383, 0x14158f3b2,
             0x14158f8d3, 0x14158fe3b, 0x141590256, 0x14159edb5]

# The one that matters most, and the one hdrscan could not see.  0x1414fd4e0 is the header
# initialiser: it writes the free-entry sentinel from 0x14351ae28 into every entry and both
# of its 0x58 sub-records, `add r8, 0xb4` between them, counting down `r9`.  The count is a
# MOV immediate, not a CMP, so a scan that pairs a 0xb4 stride with `cmp ?, 0x64` in the
# same function misses it entirely.
#
# Leaving it out is why the first version of this patch applied cleanly and changed nothing.
# Entries 100-126 were never stamped, so they held zero rather than the sentinel, and the
# allocator -- which looks for the first entry whose key IS the sentinel -- never considered
# one of them.  Verified afterwards by reading the live header: real keys at 0-99, zero at
# 100-126, in both a fresh season and the one after it.
MOV_BOUNDS = [0x1414fd4e3]      # mov r9d, 0x64 -- the immediate is at +2


def sections(d):
    pe = struct.unpack_from("<I", d, 0x3c)[0]
    n = struct.unpack_from("<H", d, pe + 6)[0]
    opt = struct.unpack_from("<H", d, pe + 20)[0]
    o = pe + 24 + opt
    out = []
    for i in range(n):
        h = d[o + i * 40:o + (i + 1) * 40]
        vs, va, rs, raw = struct.unpack_from("<IIII", h, 8)
        out.append((IMAGE_BASE + va, vs, raw, rs, h[:8].rstrip(b"\0").decode("latin1")))
    return out


def offset_of(secs, va):
    """File offset for a VA, or None when the address is in a page tail with no bytes."""
    for base, vs, raw, rs, _ in secs:
        if base <= va < base + vs:
            off = va - base
            return raw + off if off < rs else None
    return None


def section_of(secs, va):
    for base, vs, raw, rs, name in secs:
        if base <= va < base + vs:
            return name
    return None


def bound_site(d, secs, va, want):
    """Locate the 8-bit immediate `want` inside the instruction that starts at `va`.

    hdrscan reports the bounds as instruction addresses, so these are decoded and the
    immediate is located by structure rather than by searching for a byte that might just
    as well be part of a displacement.  Returns (offset of the immediate within the
    instruction, the disassembled instruction).
    """
    off = offset_of(secs, va)
    if off is None:
        raise SystemExit("0x%x has no bytes in the file" % va)
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    ins = next(md.disasm(d[off:off + 16], va))
    at = ins.bytes.rfind(bytes([want & 0xff]))
    if at < 0 or at + 1 != ins.size:
        raise SystemExit("0x%x: %s %s -- immediate %#x is not at the tail of %s"
                         % (va, ins.mnemonic, ins.op_str, want, ins.bytes.hex()))
    return at, ins


def movbound_site(d, secs, va, want):
    """Locate the 32-bit immediate of a `mov r32, want` that starts at `va`."""
    off = offset_of(secs, va)
    if off is None:
        raise SystemExit("0x%x has no bytes in the file" % va)
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    ins = next(md.disasm(d[off:off + 16], va))
    raw = struct.pack("<I", want)
    at = ins.bytes.rfind(raw)
    if not ins.mnemonic.startswith("mov") or at < 0 or at + 4 != ins.size:
        raise SystemExit("0x%x: %s %s -- not a mov with %#x as its tail immediate (%s)"
                         % (va, ins.mnemonic, ins.op_str, want, ins.bytes.hex()))
    return at, ins


def word_site(d, secs, va, want):
    """Confirm the u32 `want` sits at `va` itself.

    The table-base and table-count sites are reported as the address of the number, not of
    the instruction that carries it, because some are immediates and some are displacements
    inside an lea.  Both are the same fact -- where the phase tables begin, and how many
    there are -- so the check here is that the four bytes really are the old value, and the
    applier verifies them again against the running process before it writes.
    """
    off = offset_of(secs, va)
    if off is None:
        raise SystemExit("0x%x has no bytes in the file" % va)
    got = struct.unpack_from("<I", d, off)[0]
    if got != want:
        raise SystemExit("0x%x holds %#x, expected %#x" % (va, got, want))
    if section_of(secs, va) != ".trace":
        # .impdata is ordinary code -- impscan.py exists because attribution does not see
        # it -- but the three 0x4650 hits in it are not.  Each sits in a run of u32s beside
        # 0xffffffff sentinels, and the only way to decode one as an instruction is to
        # start mid-number.  They are a table of quantities that happens to contain 0x4650.
        return None
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    for back in range(1, 16):
        try:
            ins = next(md.disasm(d[off - back:off - back + 16], va - back))
        except StopIteration:
            continue
        # The number has to be the tail of the instruction, otherwise the back-step landed
        # mid-instruction and decoded something that only looks like code.
        if ins.address == va - back and ins.address + ins.size == va + 4:
            return "%s %s" % (ins.mnemonic, ins.op_str)
    return None


DOC = """--[[
fl26caps -- runtime patch applier (hdr%(n)d set).

Capacity patch.  It does NOT move the standings object or change its size: 0x39a8f0 is an
offset into the object, with another member at +0x39a9f0, so the boundary is held fixed and
the extra header entries are paid for out of phase tables.

Set:     hdr%(n)d
Summary: season header 100 -> %(n)d competitions, phase tables 600 -> %(count_new)d, %(sites)d patches

A season holds exactly 100 competition instances.  Past that the surplus is dropped without
a word: the leagues that miss out never get a row for the new season and keep accumulating
into the previous one, which is how a league table comes to show 76 matches played -- two
seasons of 38 -- and about 130 points.

    entries   header bytes   phase tables that still fit
       100        0x4650              600
       %(n)3d        0x%(base_new)x              %(count_new)d

%(lost)d phase table is the entire price.  127 is the ceiling of this cheap version: every
bound is `cmp r32, 0x64` with an 8-bit immediate, and 0x7f is the largest value that still
fits in a signed byte.  Above that each of the thirteen bounds needs `81 /7 id`, which is
longer than the instruction it replaces and so needs a trampoline per site.

Generated by tools/hdr127.py, which disassembles every site and locates each immediate by
structure rather than by searching for bytes that might belong to a displacement.

Install:
  1. copy this file to <game>\\SiderAddons\\modules\\fl26hdr%(n)d.lua
  2. add to sider.ini, in the lua.module list:   lua.module = "fl26hdr%(n)d.lua"
  3. start the game and read sider.log

Start a NEW Master League season after installing.  A season already on disk was built
against the 100-entry layout.

The exe has no ASLR (DllCharacteristics 0x8120), so the addresses are absolute and stable.
The applier checks that anyway by verifying the bytes.
--]]
"""


def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    n = int(a[0]) if a else 127
    out = (sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv
           else os.path.join("sider", "fl26hdr%d.lua" % n))
    if not 100 < n <= 127:
        raise SystemExit("N must be between 101 and 127; above 127 the bounds no longer "
                         "fit in a signed byte and each of the 13 sites needs a trampoline")

    base_new = n * HDR_STRIDE
    count_new = (TOTAL - base_new) // OBJ_STRIDE
    if count_new < 1:
        raise SystemExit("no phase tables would be left")

    d = open(EXE, "rb").read()
    secs = sections(d)
    patches = []

    for va in BOUNDS:
        at, ins = bound_site(d, secs, va, BOUND_OLD)
        patches.append((va + at, "%02x" % BOUND_OLD, "%02x" % n,
                        "header bound: %s %s -> %d entries" % (ins.mnemonic, ins.op_str, n)))
    skipped = []
    for va in MOV_BOUNDS:
        at, ins = movbound_site(d, secs, va, BOUND_OLD)
        patches.append((va + at,
                        struct.pack("<I", BOUND_OLD).hex(),
                        struct.pack("<I", n).hex(),
                        "header initialiser count: %s %s -> %d entries stamped with the "
                        "free sentinel" % (ins.mnemonic, ins.op_str, n)))
    for va in OBJ_BASE:
        ctx = word_site(d, secs, va, OBJ_BASE_OLD)
        if ctx is None:
            skipped.append((va, OBJ_BASE_OLD))
            continue
        patches.append((va,
                        struct.pack("<I", OBJ_BASE_OLD).hex(),
                        struct.pack("<I", base_new).hex(),
                        "phase tables start 0x%x -> 0x%x  (%s)"
                        % (OBJ_BASE_OLD, base_new, ctx)))
    for va in OBJ_COUNT:
        ctx = word_site(d, secs, va, OBJ_COUNT_OLD)
        if ctx is None:
            skipped.append((va, OBJ_COUNT_OLD))
            continue
        patches.append((va,
                        struct.pack("<I", OBJ_COUNT_OLD).hex(),
                        struct.pack("<I", count_new).hex(),
                        "phase table count %d -> %d  (%s)"
                        % (OBJ_COUNT_OLD, count_new, ctx)))

    body = "\n".join('  {va=0x%x, old="%s", new="%s",\n   why="%s"},' % p for p in patches)
    tmpl = open(os.path.join("sider", "fl26nullguard8.lua"), encoding="utf-8").read()
    tail = tmpl[tmpl.index("local function unhex"):]
    tail = tail.replace("nullguard8", "hdr%d" % n)
    tail = tail.replace("negative standings position guarded at 0x1413236e1",
                        "season header widened to %d competitions, %d phase tables"
                        % (n, count_new))
    doc = DOC % dict(n=n, base_new=base_new, count_new=count_new,
                     lost=600 - count_new, sites=len(patches))
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(doc + "\nlocal m = {}\n\nlocal patches = {\n" + body + "\n}\n\n" + tail)
    print("wrote %s: %d patches, %d entries, %d phase tables (%d given up)"
          % (out, len(patches), n, count_new, 600 - count_new))
    for va, want in skipped:
        # No instruction ends on the number, so it is data rather than an operand.  Left
        # out on purpose: writing over a constant whose use has not been read would be a
        # guess, and the whole point of the generator is that nothing here is guessed.
        print("  NOT patched, 0x%x (%s) holds %#x but no instruction ends on it -- "
              "data, not an operand" % (va, section_of(secs, va), want))
    return 0


if __name__ == "__main__":
    sys.exit(main())
