r"""python mkregs.py [N] [--stub] [--recount-only] [--out fl26regsN.lua]
     -> a Sider module that finishes the regulation-record raise fl26caps started

fl26caps (patch family "regs", layout.json arrays.regulations, cap_new 600) relocates the
regulation array (stride 0x314) out of the edit block's middle and raises its cap from 300
to 600: constructor, destructor, unwind funclet, 108 bounds, the mode copy A (mlcopy).  Four
places that still say 300 were never collected, because none of them is a `cmp r, 300`
next to an array access:

  0x1414bc1c3  lea r9d, [rbp+0x32]        THE ONE THAT BITES.  0x1414bc0a0 recounts the four
               counters after every mode-copy write-back, at mode-data creation and in the
               load-idle thread.  Its regulation part is unrolled six records per pass,
               r9d = 0x32 passes (rbp is 0 there), so it counts the valid records among the
               first 6 x 50 = 300 and stores that as the live regulation count
               (block + 0xd0bcf4, relocated by fl26caps).  The array is sorted by its u16 key
               at load (0x1414ef960), so every record past sorted index 300 -- the highest
               keys, i.e. the late ties (key >> 10 = 6..8) of the European, Libertadores, AFC
               and World Cup rounds -- drops out of every count-bounded search, and the ML
               save (block -> copy A, 0x141401d39, bounded by the count) leaves it out.
               fl26regfast measured "300 distinct of 300" on the 334-row Modpack world.
  0x1414bba63  mov esi, 300   initialiser 0x1414bb970: re-constructs 300 records in place
  0x1414bbeec  mov esi, 300   reset 0x1414bbe60 (before every mode copy writes the block
               back): only rows 0..299 are cleared, so with a raised recount the stale rows
               300..N-1 of a previous session would be counted in League mode (copy B
               writes back 180 rows).  These two must move WITH the recount.
  0x140fbdfbf  cmp eax, 300   back edge of the walk in 0x140fbdc70 (the competitions a
               player's clubs are in); its dummy-select at 0x140fbdd40 is already 600, the
               back edge was missed because the loop exits with `jae` forward + `jmp` home,
               a shape patchset.check_cap_completeness does not look for.

N must equal fl26caps' regulation cap: the module refuses to write unless the block
constructor (0x1414b87dd) and destructor (0x1414ba5e8) already carry N -- raising these sites
over a 300-record array would clear and count past its end.  So load it AFTER fl26caps.lua.

The recount is written in place when N is a multiple of 6 and N/6 fits the disp8 (N <= 762):
one byte.  Otherwise (or with --stub) the unrolled loop is replaced by a plain loop of N on
our page 0x163800000.  --recount-only leaves the three dword sites out, for a fl26caps that
was regenerated with them in layout.json (arrays.regulations.extra_cap_sites).

Read-only on the exe; writes only the .lua.
"""
import glob
import os
import struct
import sys

import capstone

IMAGE_BASE = 0x140000000
EXE = os.path.join(os.environ.get("FL26_DIR", r"E:\instalacija"), "FL_2026.exe")
SIDER_DIRS = [r"D:\dev\fl26\wt\limits\sider", r"D:\dev\fl26\wt\limits\sider\experimental",
              r"E:\instalacija\SiderAddons\modules"]            # read only: overlap checks
HERE = os.path.dirname(os.path.abspath(__file__))

PAGE = 0x163800000            # our page; fl26caps 0x163000000, fl26slots 0x163400000
OLD = 300
STRIDE = 0x314

# --- the sites, with the bytes the shipped exe has there --------------------------------
RECOUNT = 0x1414bc1c3
RECOUNT_OLD = "448d4d32" "41baffff0000" "0f1f00"     # lea r9d,[rbp+0x32]; mov r10d,0xffff; nop3
RECOUNT_EXIT = 0x1414bc235                           # mov rbx,[rsp+0x70] -- after the loop
CONTEXT = [  # (va, hex) file bytes that pin the recount's assumptions
    (0x1414bc1ab, "4881c758020000" "4883ed01" "75d8"),   # coach loop: rbp counts down to 0
    (0x1414bc1b8, "8b4c2460"),                            # ecx = 0 (regulation count so far)
    (0x1414bc1bc, "4d8d85"),                              # lea r8,[r13+REG+0x314] (disp: fl26caps)
    (0x1414bc1d0, "66453990ecfcffff"),                    # loop: cmp word [r8-0x314], r10w
    (0x1414bc22f, "4983e901" "759b"),                     # sub r9,1 ; jne loop
    (RECOUNT_EXIT, "488b5c2470"),
    (0x1414bc24f, "41898d"),                              # mov [r13+COUNT], ecx
    (0x1414bba5c, "488dbb"), (0x1414bba68, "488bcfe880de0000" "4881c714030000"),
    (0x1414bbee5, "488dbb"), (0x1414bbef1, "488bcfe8f7d90000" "4881c714030000"),
    (0x140fbdd40, "3d2c010000"),                          # its dummy-select (fl26caps raises it)
    (0x140fbdd50, "4869c814030000"),
]
DWORD_SITES = [
    (0x1414bba63, "be", "initialiser 0x1414bb970: regulation records re-constructed in place "
                        "(mov esi; 0x1414c98f0 per record)"),
    (0x1414bbeec, "be", "reset 0x1414bbe60, run before a mode copy writes the block back: "
                        "regulation records cleared in place"),
    (0x140fbdfbf, "3d", "back edge of the regulation walk in 0x140fbdc70 (competitions a "
                        "player's clubs are in; cmp eax / jae out / jmp home)"),
]
# fl26caps must already have grown the array to N: verified, never written
REQUIRES = [
    (0x1414b87dd, "41be", "block constructor: __ehvec_ctor(regulations, 0x314, N) (fl26caps)"),
    (0x1414ba5e8, "41b8", "block destructor: __ehvec_dtor(regulations, 0x314, N) (fl26caps)"),
]


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
    for base, vs, raw, rs, _ in secs:
        if base <= va < base + vs:
            off = va - base
            return raw + off if off < rs else None
    return None


def rel32(src_next, dst):
    x = dst - src_next
    if not -0x80000000 <= x < 0x80000000:
        raise SystemExit("rel32 out of range: 0x%x -> 0x%x" % (src_next, dst))
    return struct.pack("<i", x)


def branches_into(d, secs, va, total):
    """direct branches whose target falls strictly inside (va, va+total), +-0x4000 around"""
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    md.skipdata = True
    hits = set()
    lo, hi = va - 0x4000, va + 0x4000
    for start in range(lo, lo + 16):
        o = offset_of(secs, start)
        for ins in md.disasm(d[o:o + (hi - start)], start):
            if ins.mnemonic.startswith("j") or ins.mnemonic == "call":
                try:
                    t = int(ins.op_str, 16)
                except ValueError:
                    continue
                if va < t < va + total:
                    hits.add((ins.address, ins.mnemonic, t))
    return sorted(hits)


def lua_ranges():
    """[(file, va, len)] of every {va=..., old=...} patch in the modules we can see"""
    import re
    pat = re.compile(r'va\s*=\s*0x([0-9a-fA-F]+)\s*,\s*old\s*=\s*"([0-9a-fA-F]*)"')
    out = []
    for dd in SIDER_DIRS:
        for f in glob.glob(os.path.join(dd, "*.lua")):
            if os.path.basename(f).startswith("fl26regs"):
                continue
            txt = open(f, encoding="utf-8", errors="replace").read()
            out += [(f, int(v, 16), len(o) // 2) for v, o in pat.findall(txt)]
    return out


def stub(n, at):
    """count the valid records among the first n; entry: r8 = rec0 + 0x314, ecx = 0"""
    b = bytearray()
    b += bytes.fromhex("4981e8") + struct.pack("<I", STRIDE)       # sub r8, 0x314
    b += bytes.fromhex("41b9") + struct.pack("<I", n)              # mov r9d, n
    top = len(b)
    b += bytes.fromhex("664181" "38" "ffff")                       # cmp word [r8], 0xffff
    b += bytes.fromhex("7402")                                     # je +2
    b += bytes.fromhex("ffc1")                                     # inc ecx
    b += bytes.fromhex("4981c0") + struct.pack("<I", STRIDE)       # add r8, 0x314
    b += bytes.fromhex("41ffc9")                                   # dec r9d
    b += bytes([0x75, (top - (len(b) + 2)) & 0xff])                # jnz top
    b += b"\xe9" + rel32(at + len(b) + 5, RECOUNT_EXIT)            # jmp back after the loop
    return bytes(b)


DOC = """--[[
fl26regs -- regulation records: the live count follows fl26caps' cap (300 -> %(n)d).

GENERATED FILE by mkregs.py.  Every 'old' below was read from the exe at that address.

Set:     regs%(n)d
Summary: %(summary)s

fl26caps grows the regulation array to %(n)d records, but the game recounts its records
after every mode-copy write-back, at mode-data creation and on load (0x1414bc0a0), and that
recount is unrolled six records a pass over 50 passes: it never looks past record 300.  The
array is sorted by key, so with more than 300 regulations the highest keys (late cup and
European ties) stop being found and are left out of the Master League save.  This module
makes the recount cover all %(n)d, and moves the three other bounds still at 300 (the two
in-place re-initialisers and one walk's back edge).

Needs fl26caps.lua with a regulation cap of exactly %(n)d, loaded BEFORE this module: it
checks the block constructor and destructor and writes nothing if they do not say %(n)d.
Touches no byte fl26caps, fl26slots, fl26hdr* or fl26regfast touch.  %(page_note)s
A career saved with this module carries more than 300 regulations; load it with it.

Install:
  1. copy this file to <game>\\SiderAddons\\modules\\fl26regs%(n)d.lua
  2. sider.ini, after lua.module = "fl26caps.lua":   lua.module = "fl26regs%(n)d.lua"
  3. start the game; sider.log says "fl26regs: applied all ..."
--]]
"""

TAIL = r'''
local PAGES = { %(pages)s }

local function unhex(s)
  local out = {}
  for i = 1, #s, 2 do
    out[#out + 1] = string.char(tonumber(string.sub(s, i, i + 1), 16))
  end
  return table.concat(out)
end

local function tohex(s)
  if s == nil then return "nil" end
  local out = {}
  for i = 1, #s do
    out[#out + 1] = string.format("%%02x", string.byte(s, i))
  end
  return table.concat(out)
end

local function reserve(page)
  if ffi == nil then
    log("fl26regs: global ffi is nil -- set luajit.ext.enabled = 1 in sider.ini")
    return false
  end
  if not m.cdef then
    -- a name of our own: another module may already have declared VirtualAlloc
    ffi.cdef([[ void* fl26regs_VirtualAlloc(void*, size_t, uint32_t, uint32_t) asm("VirtualAlloc"); ]])
    m.cdef = true
  end
  local function try(kind)
    local p = ffi.C.fl26regs_VirtualAlloc(ffi.cast("void*", page), 0x1000, kind, 0x40)
    return p ~= nil and tonumber(ffi.cast("uint64_t", p)) or 0
  end
  -- MEM_COMMIT|MEM_RESERVE, PAGE_EXECUTE_READWRITE; MEM_COMMIT alone if already reserved
  local got = try(0x3000)
  if got ~= page then got = try(0x1000) end
  if got ~= page then
    log(string.format("fl26regs: could not get the page at 0x%%x (got 0x%%x)", page, got))
    return false
  end
  log(string.format("fl26regs: page 0x%%x..0x%%x ready", page, page + 0x1000))
  return true
end

function m.init(ctx)
  local n = #patches

  -- pass 0: fl26caps must already have grown the array to the same cap. Read only.
  for _, r in ipairs(requires) do
    local want = unhex(r.want)
    local cur = memory.read(r.va, #want)
    if cur ~= want then
      log(string.format("fl26regs: ABORTED, 0x%%x is %%s, expected %%s [%%s]. Is fl26caps.lua "
                        .. "loaded before this module, with a regulation cap of %(n)d? "
                        .. "Nothing was written; the game is unmodified.",
                        r.va, tohex(cur), r.want, r.why))
      return
    end
  end

  for _, page in ipairs(PAGES) do
    if not reserve(page) then
      log("fl26regs: ABORTED before verifying. Nothing was written; the game is unmodified.")
      return
    end
  end
  log(string.format("fl26regs: set '%%s', %%d patches, verifying", "%(set)s", n))

  -- pass 1: read only. Nothing is written until every single site has been confirmed.
  local bad = 0
  for i = 1, n do
    local p = patches[i]
    local want = unhex(p.old)
    local cur = memory.read(p.va, #want)
    if cur ~= want then
      log(string.format("fl26regs: MISMATCH at 0x%%x: found %%s, expected %%s  [%%s]",
                        p.va, tohex(cur), p.old, p.why))
      bad = bad + 1
    end
  end
  if bad > 0 then
    log(string.format("fl26regs: ABORTED, %%d of %%d sites did not match. "
                      .. "Nothing was written; the game is unmodified. "
                      .. "A different exe build, or a fl26caps that already carries these "
                      .. "sites (then use the --recount-only build).", bad, n))
    return
  end

  -- pass 2: write, then read back. Page contents first, the jump into them last.
  local written, failed = 0, 0
  for i = 1, n do
    local p = patches[i]
    local new = unhex(p.new)
    memory.write(p.va, new)
    local back = memory.read(p.va, #new)
    if back == new then
      written = written + 1
      log(string.format("fl26regs: [%%d/%%d] 0x%%x %%s -> %%s  %%s",
                        i, n, p.va, p.old, p.new, p.why))
    else
      failed = failed + 1
      log(string.format("fl26regs: WRITE FAILED at 0x%%x (%%s) -- read back %%s",
                        p.va, p.why, tohex(back)))
    end
  end

  if failed == 0 then
    log(string.format("fl26regs: applied all %%d patches -- %%s", written, "%(summary)s"))
  else
    log(string.format("fl26regs: PARTIAL: %%d written, %%d failed. The game is now in an "
                      .. "inconsistent state -- quit and report the addresses above.",
                      written, failed))
  end
end

return m
'''


def main():
    args = [x for x in sys.argv[1:] if not x.startswith("--") and not x.endswith(".lua")]
    n = int(args[0]) if args else 600
    use_stub = "--stub" in sys.argv or n % 6 or n // 6 > 0x7f
    recount_only = "--recount-only" in sys.argv
    out = (sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv
           else os.path.join(HERE, "..", "sider", "experimental", "fl26regs%d%s.lua" % (n, "s" if "--stub" in sys.argv else "")))
    if not OLD < n <= 0xffff:
        raise SystemExit("N must be above 300")
    d = open(EXE, "rb").read()
    secs = sections(d)

    def file_hex(va, k):
        return d[offset_of(secs, va):offset_of(secs, va) + k].hex()

    # 1. every byte the patches and their assumptions rest on
    if file_hex(RECOUNT, len(RECOUNT_OLD) // 2) != RECOUNT_OLD:
        raise SystemExit("recount at 0x%x moved" % RECOUNT)
    for va, h in CONTEXT:
        if file_hex(va, len(h) // 2) != h:
            raise SystemExit("context 0x%x is %s, expected %s" % (va, file_hex(va, len(h) // 2), h))
    for va, op, _ in DWORD_SITES:
        if file_hex(va, 5) != op + struct.pack("<I", OLD).hex():
            raise SystemExit("0x%x is not %s 300" % (va, op))
    for va, op, _ in REQUIRES:
        if file_hex(va, len(op) // 2 + 4) != op + struct.pack("<I", OLD).hex():
            raise SystemExit("0x%x is not the shipped 300" % va)

    patches, ranges, page_used = [], [], 0
    if use_stub:
        s = stub(n, PAGE)
        patches.append((PAGE, "00" * len(s), s.hex(),
                        "recount stub: valid regulation records among the first %d "
                        "(r8 = record 0 + 0x314 from the game's own relocated lea), then back "
                        "to 0x%x" % (n, RECOUNT_EXIT)))
        site = b"\xe9" + rel32(RECOUNT + 5, PAGE) + b"\x90" * (len(RECOUNT_OLD) // 2 - 5)
        patches.append((RECOUNT, RECOUNT_OLD, site.hex(),
                        "recount 0x1414bc0a0: unrolled 50 x 6 = 300 regulation records -> "
                        "jmp to the stub at 0x%x" % PAGE))
        ranges.append((RECOUNT, len(RECOUNT_OLD) // 2))
        page_used = len(s)
    else:
        patches.append((RECOUNT, "448d4d32", "448d4d%02x" % (n // 6),
                        "recount 0x1414bc0a0: lea r9d,[rbp+passes] -- %d passes x 6 records "
                        "= %d (was 50 x 6 = 300)" % (n // 6, n)))
        ranges.append((RECOUNT, 4))
    if not recount_only:
        for va, op, why in DWORD_SITES:
            patches.append((va, op + struct.pack("<I", OLD).hex(), op + struct.pack("<I", n).hex(),
                            "%s: 300 -> %d" % (why, n)))
            ranges.append((va, 5))

    # 2. checks: rel32 reach, no branch lands inside a range we rewrite, no other module
    #    writes any byte we write
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    problems = []
    for va, total in ranges:
        if total > 5:
            for a, mn, t in branches_into(d, secs, va, total):
                problems.append("branch into 0x%x+%d from 0x%x (%s 0x%x)" % (va, total, a, mn, t))
    for f, pva, plen in lua_ranges():
        for va, total in ranges:
            if pva < va + total and va < pva + max(plen, 1):
                problems.append("%s: 0x%x+%d overlaps ours 0x%x+%d"
                                % (f, pva, plen, va, total))
    if problems:
        print("\n".join(problems))
        raise SystemExit("refusing to write: see above")

    for va, old, new, why in patches:
        print("0x%x  %s -> %s" % (va, old[:26], new[:26]))
        for ins in md.disasm(bytes.fromhex(new), va):
            print("      %x  %-22s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))

    summary = ("regulation records %d: live recount %s, re-initialisers and the 0x140fbdc70 "
               "walk raised, %d patches" % (n, "stub" if use_stub else "in place", len(patches)))
    if recount_only:
        summary = ("regulation records %d: live recount %s (the other bounds come from "
                   "fl26caps), %d patches" % (n, "stub" if use_stub else "in place", len(patches)))
    setname = "regs%d" % n
    page_note = ("Its page is 0x%x (%d bytes of code), not fl26caps' or fl26slots'. Needs "
                 "luajit.ext.enabled = 1." % (PAGE, page_used)) if use_stub else \
                "Allocates no page."
    body = "\n".join('  {va=0x%x, old="%s", new="%s",\n   why="%s"},' % p for p in patches)
    req = "\n".join('  {va=0x%x, want="%s", why="%s"},' % (va, op + struct.pack("<I", n).hex(), w)
                    for va, op, w in REQUIRES)
    txt = (DOC % dict(n=n, summary=summary, page_note=page_note)
           + "\nlocal m = {}\n\nlocal requires = {\n" + req + "\n}\n\nlocal patches = {\n"
           + body + "\n}\n"
           + TAIL % dict(pages=("0x%x" % PAGE) if use_stub else "", n=n, set=setname,
                         summary=summary))
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(txt)
    print("wrote %s: %d patches (%s)" % (out, len(patches), summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
