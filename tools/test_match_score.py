"""The score of a result row (21.11.2026, Master League, Ligue 1 of a big world): the matchday-results page
listed the round's other fixtures with no result, only the user's had one, and the table counted them all.
0x141515300 (a row's score) takes the match id in ecx; its seven callers hand it the record's id as
`movzx ecx, word [rec]`, so with twins live (first 65536, mask 0xffffffff, ids handed out below 65536) it
looked up the low twin, another competition's match not played. fl26match.dll rewrites the seven reads as
dword reads (SCORE_WIDE in tools/native/fl26match.c).

Against FL_2027.exe (FL27_DIR, read only):
  - the call sites of 0x141515300 are exactly SCORE_WIDE's seven, one site per call;
  - every site holds the shipped `movzx ecx, word [reg]`, its new bytes decode as `mov ecx, dword [reg]`
    of the same register, and the call follows within two instructions with ecx untouched;
  - the register is the record a lookup (0x1414bb280) handed back in rax just before;
  - inside 0x141515300 caps widens the cut (0x14151530f) and no fl26caps FL27 patch touches a site.

    python tools/test_match_score.py

Needs capstone and FL27_DIR (default E:/FL/FL27/game); without them it is reported as SKIPPED.
"""
import os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = open(os.path.join(HERE, "native", "fl26match.c"), encoding="utf-8").read()
SCORE = 0x141515300
LOOKUP = 0x1414bb280


def wide_table(name):
    body = SRC[SRC.index("static const wide_t %s[]" % name):]
    body = body[:body.index("};")]
    out = []
    for va, n, old, new in re.findall(r"\{(0x[0-9a-f]+)ull,\s*(\d+),\s*\{([^}]*)\},\s*\{([^}]*)\}\}", body):
        b = lambda s: bytes(int(x, 16) for x in s.split(","))
        out.append((int(va, 16), int(n), b(old), b(new)))
    return out


SITES = wide_table("SCORE_WIDE")
assert len(SITES) == 7, SITES
for va, n, old, new in SITES:
    assert len(old) == n and len(new) == n, hex(va)
assert "score_widen();" in SRC and "result row score reads" in SRC
others = {va for t in ("PAGE_WIDE", "TWIN_WIDE") for va, _, _, _ in wide_table(t)}
assert not others & {va for va, _, _, _ in SITES}

exe = os.path.join(os.environ.get("FL27_DIR", "E:/FL/FL27/game"), "FL_2027.exe")
try:
    from capstone import Cs, CS_ARCH_X86, CS_MODE_64
except ImportError:
    Cs = None
if not os.path.exists(exe) or Cs is None:
    print("SKIPPED: %s" % ("no capstone" if Cs is None else "no " + exe))
    sys.exit(0)

data = open(exe, "rb").read()
pe = struct.unpack_from("<I", data, 0x3c)[0]
nsec = struct.unpack_from("<H", data, pe + 6)[0]
opt = struct.unpack_from("<H", data, pe + 20)[0]
base = struct.unpack_from("<Q", data, pe + 24 + 24)[0]
secs = []
for i in range(nsec):
    o = pe + 24 + opt + 40 * i
    name = data[o:o + 8].rstrip(b"\0")
    vsz, vaddr, rsz, raw = struct.unpack_from("<IIII", data, o + 8)
    secs.append((name, vaddr, max(vsz, rsz), raw, rsz))


def read(va, n):
    rva = va - base
    for _, vaddr, sz, raw, _ in secs:
        if vaddr <= rva < vaddr + sz:
            return data[raw + rva - vaddr: raw + rva - vaddr + n]
    raise KeyError(hex(va))


md = Cs(CS_ARCH_X86, CS_MODE_64)

# every call of 0x141515300 in the code section
name, vaddr, _, raw, rsz = secs[0]
code = data[raw:raw + rsz]
calls = []
for m in re.finditer(b"\xe8", code):
    i = m.start()
    if i + 5 <= len(code):
        va = base + vaddr + i
        if va + 5 + struct.unpack_from("<i", code, i + 1)[0] == SCORE:
            calls.append(va)
# a stray e8 byte inside another instruction can point there too: keep the ones that decode as the call
calls = [c for c in calls if next(md.disasm(read(c, 5), c)).op_str == hex(SCORE)]

seen = set()
for va, n, old, new in SITES:
    assert read(va, n) == old, "%x: not the shipped bytes (%s)" % (va, read(va, n).hex())
    a = next(md.disasm(old, va)); b = next(md.disasm(new, va))
    m = re.fullmatch(r"ecx, word ptr \[(\w+)\]", a.op_str)
    assert a.mnemonic == "movzx" and m, "%x: %s %s" % (va, a.mnemonic, a.op_str)
    reg = m.group(1)
    assert b.mnemonic == "mov" and b.op_str == "ecx, dword ptr [%s]" % reg and b.size + 1 >= n, "%x: %s %s" % (va, b.mnemonic, b.op_str)
    # forward: the call within two instructions, ecx/rcx not written in between
    ins = list(md.disasm(read(va + n, 16), va + n))[:2]
    hit = None
    for x in ins:
        if x.mnemonic == "call" and x.op_str == hex(SCORE):
            hit = x.address; break
        assert not re.match(r"(e|r)?cx\b|cl\b", x.op_str.split(",")[0].strip()), "%x: ecx written at %x" % (va, x.address)
    assert hit in calls, "%x: no call of 0x141515300 after it" % va
    seen.add(hit)
    # backward: the register is the record a lookup just returned (call 0x1414bb280; [mov reg, rax])
    found = False
    for back in range(5, 40):
        seq = list(md.disasm(read(va - back, back), va - back))
        if not seq or sum(x.size for x in seq) != back:
            continue
        if reg == "rax":     # straight after the lookup, rax not written since
            lk = [k for k, x in enumerate(seq) if x.mnemonic == "call" and x.op_str == hex(LOOKUP)]
            ok = bool(lk) and not any(x.op_str.startswith(("rax", "eax", "ax")) or x.mnemonic == "call"
                                      for x in seq[lk[-1] + 1:])
        else:                # `mov reg, rax` right after a lookup, reg not written since
            mv = [k for k, x in enumerate(seq) if x.mnemonic == "mov" and x.op_str == "%s, rax" % reg]
            lk = [k for k in range(max(0, mv[-1] - 3), mv[-1]) if seq[k].mnemonic == "call" and seq[k].op_str == hex(LOOKUP)] if mv else []
            ok = bool(lk) and not any(x.op_str.startswith(("rax", "eax", "ax")) or x.mnemonic == "call"
                                      for x in seq[lk[-1] + 1:mv[-1]]) \
                and not any(x.op_str.split(",")[0].strip() in (reg, "e" + reg[1:]) for x in seq[mv[-1] + 1:])
        if ok:
            found = True; break
    assert found, "%x: [%s] is not the record of a lookup just before" % (va, reg)
assert seen == set(calls), "calls of 0x141515300 not covered: %s" % sorted(hex(c) for c in set(calls) - seen)

# the rows' round test (LIST_WIDE): 0x140ca22a0 gets the id whole in ecx from the remove_if over the day's
# dword list, cuts it for the lookup only, and compares with the current match (ctx+0x35960)
LIST = wide_table("LIST_WIDE")
assert [va for va, _, _, _ in LIST] == [0x140ca22bf], LIST
va, n, old, new = LIST[0]
assert read(va, n) == old and next(md.disasm(new, va)).op_str == "edx, edi"
fn = list(md.disasm(read(0x140ca22a0, 0x40), 0x140ca22a0))
assert [x.op_str for x in fn[:6]][4] == "edi, ecx", fn[:6]
nxt = [x for x in fn if x.address > va][:4]   # mov rcx, rbx; mov rsi, [rax+0x50]; call lookup; lea rcx, [rsi+0x35960]
assert nxt[2].mnemonic == "call" and nxt[2].op_str == hex(LOOKUP) and "0x35960" in nxt[3].op_str, nxt
assert not any(x.op_str.startswith(("edx", "rdx", "dx")) for x in nxt[:2]), nxt
loop = list(md.disasm(read(0x140ca3a67, 5), 0x140ca3a67))
assert loop[0].op_str == "ecx, dword ptr [rbx]" and loop[1].op_str == "qword ptr [r14]", loop
refs = [m.start() for m in re.finditer(rb"[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]", code)
        if base + vaddr + m.start() + 7 + struct.unpack_from("<i", code, m.start() + 3)[0] == 0x140ca22a0]
assert len(refs) == 1, refs
SITES = SITES + LIST

# caps: the cut inside is widened, no FL27 caps patch touches a site
caps = open(os.path.join(ROOT, "sider", "fl26caps.fl27.lua"), encoding="utf-8", errors="replace").read()
assert re.search(r"va=0x14151530f,", caps), "caps no longer widens 0x14151530f"
for va, n, _, _ in SITES:
    for p in re.finditer(r"va=0x([0-9a-f]+), old=\"([0-9a-f]+)\"", caps):
        pv, pl = int(p.group(1), 16), len(p.group(2)) // 2
        assert pv + pl <= va or va + n <= pv, "%x: caps patch at %x touches it" % (va, pv)
print("score sites: %d of %d calls of 0x141515300 covered; ok" % (len(seen), len(calls)))
