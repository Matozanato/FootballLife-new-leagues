"""python appcap.py [cap]  -> sider/experimental/fl26appcap.lua: a bigger PlayerAppearance table

The appearance object is [[exe+0x3705e10] + 0x60]: one heap allocation of 0x260554 bytes,

    +0x000000   2500 records of 0x84         (a table of its own; count at +0x260550)
    +0x050910   30024 records of 0x48        the appearance table (id, 56 appearance bytes)
    +0x260550   u16 count of the first table
    +0x260552   u16 count of the appearance table

and nothing after it. The table is the last array, so it grows in place: the two counts move
up to sit after the bigger table, the allocation grows by the same amount, and every cap
moves with it. The table itself does not move (+0x50910 stays), so no table access changes.

Every site the object has, found by the scans below and nowhere else in the exe:

  * the allocation size 0x260554 (2 x new, 3 x sized delete, 1 x memset in the backup);
  * the backup copy [owner+0x88] <-> [owner+0x60]: two unrolled copies of 0x4c0a chunks of
    0x80 plus a fixed 0x54-byte tail -- so the new size must keep (size - 0x54) % 0x80 == 0,
    which with the counts right after the table means cap = 8 (mod 16);
  * the constructor's memset of the table, 0x20fc40 = 30024 * 0x48;
  * the two counts, +0x260550 (11 sites, one of them a dword write that clears both) and
    +0x260552 (10 sites);
  * the cap 0x7548 (5 sites) and cap - 1 = 0x7547 (2 sites: insert refuses at it, the
    remove's compaction clamps to it).

The cap is a u16 count everywhere (movzx / 16-bit compares, all unsigned), so it must stay
under 65536. 65000 is the largest round number with cap % 16 == 8, and leaves room under
the u16 for anything that counts one past it.

Completeness is checked, not assumed: the generator refuses to write the module if
  - any instruction in .trace has one of the old values as an operand (non-rip) and is not
    a patch site, or
  - any raw occurrence of the old displacements / sizes (0x260550, 0x260552, 0x260554,
    0x20fc40) in ANY section of the exe (.impdata included) lies outside a patched
    instruction.
"""
import json, os, re, struct, sys
from capstone import *
import flpaths

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
IMG = 0x140000000

TAB, STRIDE, CAP_OLD = 0x50910, 0x48, 30024
CNT1_OLD, CNT2_OLD = TAB + CAP_OLD * STRIDE, TAB + CAP_OLD * STRIDE + 2
SIZE_OLD = CNT1_OLD + 4
CHUNK, TAIL = 0x80, 0x54
assert (CNT1_OLD, SIZE_OLD) == (0x260550, 0x260554)
assert (SIZE_OLD - TAIL) % CHUNK == 0 and (SIZE_OLD - TAIL) // CHUNK == 0x4c0a

# (va, role); the kind is what the old value means there
SITES = {
    "size": [(0x1414b5b31, "sized delete of [owner+0x88] (backup)"),
             (0x1414b5bea, "sized delete of [owner+0x60]"),
             (0x1414b6ee9, "sized delete of [owner+0x88] after the restore"),
             (0x1414b6fde, "new of [owner+0x60] in the owner's constructor"),
             (0x1414b7197, "new of [owner+0x88] before the backup copy"),
             (0x1414b7264, "memset of the backup when the source is missing")],
    "chunks": [(0x1414b6e29, "restore copy [owner+0x88] -> [owner+0x60]"),
               (0x1414b71dd, "backup copy [owner+0x60] -> [owner+0x88]")],
    "bytes": [(0x1414bce2f, "constructor: memset of the appearance table")],
    "cnt1": [(0x1414bcff8, "remove (first table): loop bound"),
             (0x1414bd047, "remove (first table): loop bound"),
             (0x1414bd050, "remove (first table): count"),
             (0x1414bd070, "remove (first table): compaction bound"),
             (0x1414bd12b, "remove (first table): compaction loop"),
             (0x1414bd138, "remove (first table): count"),
             (0x1414bd147, "remove (first table): count - 1"),
             (0x1414bd3b9, "first table lookup: count"),
             (0x1414bd5aa, "constructor: both counts = 0 (dword)"),
             (0x1414bd9f9, "first table recount"),
             (0x141ef7ff9, "first table walk (outside the object's own functions)")],
    "cnt2": [(0x1414bce5d, "remove by id: count"),
             (0x1414bceea, "remove by id: loop bound"),
             (0x1414bcf20, "remove by id: compaction bound"),
             (0x1414bcfc1, "remove by id: count"),
             (0x1414bcfd0, "remove by id: count - 1"),
             (0x1414bd16f, "lookup by id, copy out: count"),
             (0x1414bd22a, "lookup by id, pointer: count"),
             (0x1414bd5d0, "insert/update by id: count"),
             (0x1414bd781, "insert: count + 1"),
             (0x1414bd949, "recount after the PlayerAppearance.bin load")],
    "cap": [(0x1414bcf31, "remove by id: compaction clamp"),
            (0x1414bd17f, "lookup by id, copy out: count < cap"),
            (0x1414bd237, "lookup by id, pointer: count < cap"),
            (0x1414bd52c, "constructor: records to reset"),
            (0x1414bd895, "recount: records to look at")],
    "cap1": [(0x1414bcf27, "remove by id: compaction clamp value"),
             (0x1414bd6ae, "insert: refuses at cap - 1")],
}


def sections(d):
    pe = struct.unpack_from("<I", d, 0x3c)[0]
    nsec = struct.unpack_from("<H", d, pe + 6)[0]
    opt = struct.unpack_from("<H", d, pe + 20)[0]
    out = []
    for i in range(nsec):
        p = pe + 24 + opt + i * 40
        nm = d[p:p + 8].rstrip(b"\0").decode("latin1")
        vsz, va, rsz, ro = struct.unpack_from("<IIII", d, p + 8)
        out.append((nm, IMG + va, vsz, ro, rsz))
    return out


def main():
    cap = int(sys.argv[1]) if len(sys.argv) > 1 else 65000
    if not (CAP_OLD < cap < 65536 and cap % 16 == 8):
        raise SystemExit("cap must be > %d, < 65536 and = 8 (mod 16) so the backup copy's "
                         "0x54-byte tail still fits; %d is not" % (CAP_OLD, cap))
    cnt1 = TAB + cap * STRIDE
    size = cnt1 + 4
    assert (size - TAIL) % CHUNK == 0
    new_of = {"size": (SIZE_OLD, size),
              "chunks": ((SIZE_OLD - TAIL) // CHUNK, (size - TAIL) // CHUNK),
              "bytes": (CAP_OLD * STRIDE, cap * STRIDE),
              "cnt1": (CNT1_OLD, cnt1), "cnt2": (CNT2_OLD, cnt1 + 2),
              "cap": (CAP_OLD, cap), "cap1": (CAP_OLD - 1, cap - 1)}

    d = open(flpaths.need_exe(), "rb").read()
    secs = sections(d)
    tr = [s for s in secs if s[0] == ".trace"][0]
    off = lambda va: tr[3] + (va - tr[1])
    md = Cs(CS_ARCH_X86, CS_MODE_64)

    patches = []
    for kind, sites in SITES.items():
        old_v, new_v = new_of[kind]
        for va, role in sites:
            ins = next(md.disasm(d[off(va):off(va) + 16], va))
            b = bytes(ins.bytes)
            want = struct.pack("<I", old_v)
            k = [i for i in range(len(b) - 3) if b[i:i + 4] == want]
            if len(k) != 1:
                raise SystemExit("%x: expected one %08x in %s (%s %s)" % (va, old_v, b.hex(), ins.mnemonic, ins.op_str))
            nb = b[:k[0]] + struct.pack("<I", new_v) + b[k[0] + 4:]
            patches.append({"va": va, "old": b.hex(), "new": nb.hex(), "kind": kind,
                            "asm": "%s %s" % (ins.mnemonic, ins.op_str),
                            "why": "appearance %s 0x%x -> 0x%x: %s" % (kind, old_v, new_v, role)})
    patches.sort(key=lambda p: p["va"])
    spans = [(p["va"], p["va"] + len(p["old"]) // 2) for p in patches]
    inside = lambda a, n=4: any(lo <= a and a + n <= hi for lo, hi in spans)

    # completeness 1: every non-rip operand in .trace carrying an old value
    olds = {v[0] for v in new_of.values()}
    hx = re.compile(r"0x([0-9a-f]+)")
    md.skipdata = True
    stray = []
    for i in md.disasm(d[tr[3]:tr[3] + tr[4]], tr[1]):
        s = i.op_str
        if "0x" not in s or "rip" in s or i.mnemonic == "call" or i.mnemonic.startswith("j"):
            continue
        if any(int(m.group(1), 16) in olds for m in hx.finditer(s)) and not inside(i.address, 1):
            stray.append("%x %s %s" % (i.address, i.mnemonic, s))
    # completeness 2: the displacements and sizes as raw dwords, every section
    for nm, va, vsz, ro, rsz in secs:
        for v in (CNT1_OLD, CNT2_OLD, SIZE_OLD, CAP_OLD * STRIDE):
            b = struct.pack("<I", v)
            k = d.find(b, ro, ro + rsz)
            while k >= 0:
                a = va + (k - ro)
                if not inside(a):
                    stray.append("raw %08x at %x (%s)" % (v, a, nm))
                k = d.find(b, k + 1, ro + rsz)
    if stray:
        print("REFUSING: %d references to the appearance object are not patch sites:" % len(stray))
        for s in stray[:40]:
            print("   " + s)
        return 1

    # no other fl26 module may write these bytes
    clash = []
    for dirp in (os.path.join(ROOT, "sider"), os.path.join(ROOT, "sider", "experimental")):
        for f in os.listdir(dirp):
            if (not f.endswith(".lua") or f.startswith("fl26appcap")
                    or (f.startswith("fl26caps.") and f != "fl26caps.lua")):
                continue
            txt = open(os.path.join(dirp, f), encoding="utf-8", errors="replace").read()
            for v, o in re.findall(r'va=0x([0-9a-f]+), old="([0-9a-f]*)"', txt):
                lo, hi = int(v, 16), int(v, 16) + len(o) // 2
                for a, b in spans:
                    if lo < b and a < hi:
                        clash.append("%s 0x%x" % (f, lo))
    if clash:
        print("REFUSING: other modules patch the same bytes: " + ", ".join(clash))
        return 1

    by = {}
    for p in patches:
        by[p["kind"]] = by.get(p["kind"], 0) + 1
    print("appearance cap %d -> %d: %d patches (%s); object 0x%x -> 0x%x, counts at +0x%x/+0x%x"
          % (CAP_OLD, cap, len(patches), ", ".join("%s %d" % kv for kv in by.items()),
             SIZE_OLD, size, cnt1, cnt1 + 2))
    print("completeness: no other operand in .trace and no other raw dword in any section")

    rows = "\n".join('  {va=0x%x, old="%s", new="%s", why=%s},'
                     % (p["va"], p["old"], p["new"], json.dumps(p["why"])) for p in patches)
    tpl = open(os.path.join(HERE, "appcap.template.lua"), encoding="utf-8").read()
    lua = (tpl.replace("--[[PATCHES]]", rows)
              .replace("--[[CAP]]", str(cap))
              .replace("--[[N]]", str(len(patches)))
              .replace("--[[SIZE]]", "0x%x" % size)
              .replace("--[[CNT2]]", "0x%x" % (cnt1 + 2))
              .replace("--[[CAPM1]]", str(cap - 1))
              .replace("--[[CNT]]", "0x%x" % cnt1))
    out = os.path.join(ROOT, "sider", "experimental", "fl26appcap.lua")
    open(out, "w", newline="\n", encoding="utf-8").write(lua)
    print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
