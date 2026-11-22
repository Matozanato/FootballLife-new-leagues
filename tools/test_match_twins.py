"""Twins sweep (17.11.2026, notes/twins-pregled-1711.md): 15 lookups of FL 2027 hold the whole match id one
instruction before and cut it with a movzx for the lookup only; with twins live (the GigaPack: first 65536,
mask 0xffffffff) they answer another competition's match (B493: the Supercopa de Chile knockout page titled
"National 1 Groupe A"). fl26match.dll rewrites them as 32-bit reads (TWIN_WIDE in tools/native/fl26match.c).

1. tools/native/test_match_twins.c built natively: the choice on a made-up table (a supercup entry high,
   its low word a league match; a low id; no twin; 0xffff) and twin_widen on a fake image.
2. Against FL_2027.exe (FL27_DIR, read only):
   - every site holds the shipped movzx into edx, the new bytes decode as the same source read 32-bit,
     a lookup (0x1414bb280 or 0x1414bc990) follows within 3 instructions with edx untouched;
   - the source is whole: the instruction(s) before each site are the ones the sweep found (a dword
     read of the entry, `mov ebx, [rcx]` of the id list, the call of 0x1414c8fd0), no branch lands
     between them and the site, and the writers keep the id as a dword (the fillers' entry stores,
     0x141510bd0's list push, 0x1414c8fd0's `mov eax, esi`), with the vtables that name the pages;
   - the upstream widening the whole id needs is still there (caps day lists, matchid32);
   - no fl26caps FL27 module and no matchid32 patch touches a site, none is a PAGE_WIDE or PICK site;
   - CUR_SITES lists all four lookups 0x1412fd680 makes of its [rsp+0x28] (the context's word).

    python tools/test_match_twins.py

Needs zig (ZIG, PATH, or D:/dev/tools/zig-*/zig.exe) for part 1 and capstone + FL27_DIR for part 2;
a missing one is reported as SKIPPED for its part.
"""
import glob, os, re, shutil, struct, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
NATIVE = os.path.join(HERE, "native")
ROOT = os.path.dirname(HERE)
SRC = open(os.path.join(NATIVE, "fl26match.c"), encoding="utf-8").read()
LOOKUPS = {0x1414bb280, 0x1414bc990}
GETTER = 0x1414c8fd0


def find_zig():
    z = os.environ.get("ZIG")
    if z and os.path.exists(z):
        return z
    z = shutil.which("zig")
    if z:
        return z
    found = sorted(glob.glob("D:/dev/tools/zig-*/zig.exe"))
    return found[-1] if found else None


def wide_table(name):
    body = SRC[SRC.index("static const wide_t %s[]" % name):]
    body = body[:body.index("};")]
    out = []
    for va, n, old, new in re.findall(r"\{(0x[0-9a-f]+)ull,\s*(\d+),\s*\{([^}]*)\},\s*\{([^}]*)\}\}", body):
        b = lambda s: bytes(int(x, 16) for x in s.split(","))
        out.append((int(va, 16), int(n), b(old), b(new)))
    return out


def pick_spans():
    body = SRC[SRC.index("static const pick_t PICK[]"):]
    body = body[:body.index("};")]
    return [(int(a, 16), int(r, 16)) for r, a, _ in
            re.findall(r"\{(0x[0-9a-f]+)ull,\s*(0x[0-9a-f]+)ull,\s*\"([0-9a-f]+)\"\}", body)]


SITES = wide_table("TWIN_WIDE")
assert len(SITES) == 15, SITES
for va, n, old, new in SITES:
    assert len(old) == n and len(new) == n, hex(va)

# what each site's source is, as the sweep found it: the instructions right before the site
# ("getter": the call of 0x1414c8fd0, then only instructions that leave eax alone)
SOURCE = {
    0x140caa84e: ["mov eax, dword ptr [rdx + 4]", "mov dword ptr [rbp - 0x58], eax"],
    0x140caaad9: ["mov eax, dword ptr [r8 + 4]", "mov dword ptr [rsp + 0x24], eax"],
    0x140af88ba: None, 0x140af88f0: None, 0x140cacefa: None, 0x140cacf30: None,   # memory source
    0x140ca3fcb: ["mov ebx, dword ptr [rcx]"],
    0x140ca3fe3: ["mov ebx, dword ptr [rcx]"],                                      # 0x140ca3fc9, ebx kept
    0x140c8ca90: "getter", 0x140c8cbe9: "getter", 0x140cd1780: "getter", 0x1412eb4d6: "getter",
    0x14130327c: "getter", 0x141fe2b9c: "getter", 0x140cb077a: "getter",
}
assert set(SOURCE) == {va for va, _, _, _ in SITES}

# part 1
zig = find_zig()
if not zig:
    print("SKIPPED part 1: no zig (set ZIG to zig.exe)")
else:
    out = os.path.join(tempfile.mkdtemp(), "test_match_twins.exe")
    subprocess.run([zig, "cc", "-target", "x86_64-windows-gnu", "-O2", "-fno-sanitize=undefined", "-w",
                    os.path.join(NATIVE, "test_match_twins.c"), "-o", out, "-lkernel32"], check=True, cwd=NATIVE)
    r = subprocess.run([out], capture_output=True, text=True, timeout=300)
    sys.stdout.write(r.stdout)
    assert r.returncode == 0 and ", 0 failed" in r.stdout, "twins sweep test failed"
    assert "header: shipped read -> comp 273, widened read -> comp 511" in r.stdout

# part 2
exe = os.path.join(os.environ.get("FL27_DIR", "E:/FL/FL27/game"), "FL_2027.exe")
try:
    from capstone import Cs, CS_ARCH_X86, CS_MODE_64
except ImportError:
    Cs = None
if not os.path.exists(exe) or Cs is None:
    print("SKIPPED part 2: %s" % ("no capstone" if Cs is None else "no " + exe))
else:
    data = open(exe, "rb").read()
    pe = struct.unpack_from("<I", data, 0x3c)[0]
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    opt = struct.unpack_from("<H", data, pe + 20)[0]
    base = struct.unpack_from("<Q", data, pe + 24 + 24)[0]
    secs = []
    for i in range(nsec):
        o = pe + 24 + opt + 40 * i
        vsz, vaddr, rsz, raw = struct.unpack_from("<IIII", data, o + 8)
        secs.append((vaddr, max(vsz, rsz), raw))

    def read(va, n):
        rva = va - base
        for vaddr, sz, raw in secs:
            if vaddr <= rva < vaddr + sz:
                return data[raw + rva - vaddr: raw + rva - vaddr + n]
        raise KeyError(hex(va))

    def q(va):
        return struct.unpack("<Q", read(va, 8))[0]

    def call_to(va):
        b = read(va, 5)
        return b[0] == 0xe8 and va + 5 + struct.unpack("<i", b[1:])[0]

    md = Cs(CS_ARCH_X86, CS_MODE_64)

    def writes(ins, reg):                       # the instruction's first operand is that register
        if ins.mnemonic in ("cmp", "test") or ins.mnemonic.startswith("j"):
            return False
        dst = ins.op_str.split(",")[0].strip()
        fam = {"edx": ("rdx", "edx", "dx", "dl", "dh"), "eax": ("rax", "eax", "ax", "al", "ah"),
               "ebx": ("rbx", "ebx", "bx", "bl", "bh")}[reg]
        return dst in fam or ins.mnemonic == "call"

    def before(va, back):                       # the instructions that end exactly at va, from va - back
        for start in range(va - back, va):
            ins = list(md.disasm(read(start, va - start), start))
            if ins and ins[-1].address + ins[-1].size == va and sum(i.size for i in ins) == va - start:
                return ins
        return []

    for va, n, old, new in SITES:
        assert read(va, n) == old, "%x: exe has %s, not the shipped %s" % (va, read(va, n).hex(), old.hex())
        a = list(md.disasm(old, va))
        b = list(md.disasm(new, va))
        assert len(a) == 1 and a[0].size == n and a[0].mnemonic == "movzx" and a[0].op_str.startswith("edx, "), (hex(va), a)
        assert b[0].mnemonic == "mov" and b[0].op_str.startswith("edx, ") and sum(i.size for i in b) == n, (hex(va), b)
        src_a, src_b = a[0].op_str.split(", ", 1)[1], b[0].op_str.split(", ", 1)[1]
        if src_a.startswith("word ptr"):
            assert src_b == "dword ptr" + src_a[len("word ptr"):], (hex(va), src_a, src_b)
        else:
            assert src_b == "e" + src_a, (hex(va), src_a, src_b)
        nxt = list(md.disasm(read(va + n, 32), va + n))[:3]
        call = [i for i in nxt if i.mnemonic == "call"]
        assert call and int(call[0].op_str, 16) in LOOKUPS, (hex(va), [(hex(i.address), i.mnemonic, i.op_str) for i in nxt])
        for i in nxt[:nxt.index(call[0])]:
            assert not writes(i, "edx"), (hex(va), hex(i.address), i.op_str)
        # the source
        s = SOURCE[va]
        reg = "e" + src_a if not src_a.startswith("word") else None
        if s == "getter":
            # back from the site: only instructions that leave eax/ebx alone, up to the getter's call
            # (0x1412eb4d6 is reached by the jne right after `cmp eax, r12d`; 0x140cb077a through ebx)
            pre = before(va, 0x40)
            j = len(pre) - 1
            seen = []
            while j >= 0 and not (pre[j].mnemonic == "call" and pre[j].op_str == hex(GETTER)):
                i = pre[j]
                if va == 0x140cb077a and i.mnemonic == "mov" and i.op_str == "ebx, eax":
                    seen.append("ebx")
                elif i.mnemonic == "call" and va == 0x140cb077a and int(i.op_str, 16) == 0x1414bb950:
                    pass                                    # has(&dword): leaves rbx (callee-saved)
                elif i.mnemonic == "jmp":
                    pass                                    # 0x1412eb4d1: the branch away, not into
                else:
                    assert not writes(i, reg), (hex(va), hex(i.address), i.mnemonic, i.op_str)
                j -= 1
            assert j >= 0, "%x: no call of 0x%x before it" % (va, GETTER)
            if va == 0x140cb077a:
                assert seen == ["ebx"], seen
        elif s:
            pre = before(va, 0x10)
            got = ["%s %s" % (i.mnemonic, i.op_str) for i in pre[-len(s):]]
            if va == 0x140ca3fe3:                  # the second read: ebx from 0x140ca3fc9, kept since
                assert read(0x140ca3fc9, 2) == bytes.fromhex("8b19"), "0x140ca3fc9: mov ebx, [rcx]"
                for i in md.disasm(read(0x140ca3fcb, va - 0x140ca3fcb), 0x140ca3fcb):
                    assert not writes(i, "ebx") or i.mnemonic == "call", (hex(i.address), i.op_str)
            else:
                assert got == s, (hex(va), got, s)
        # no branch lands between the source and the site, apart from the vector-not-empty checks
        print("%x: %s %s -> %s; call %s" % (va, a[0].mnemonic, a[0].op_str,
                                            "; ".join("%s %s" % (i.mnemonic, i.op_str) for i in b), call[0].op_str))

    # the getter hands the whole id back; its callers' calls
    assert read(0x1414c90ec, 2) == bytes.fromhex("8bc6"), "0x1414c8fd0 returns esi"
    for c in (0x140c8ca8b, 0x140c8cbe4, 0x140cd177b, 0x140cb0750, 0x1412eb4ba, 0x141303261, 0x141fe2b93):
        assert call_to(c) == GETTER, hex(c)
    # the pages: vtables and the writers of the entries' id dwords
    assert q(0x142724c70 + 0x268) == 0x140caa7d0 and q(0x142724c70 + 0x260) == 0x140caad90, "ResultFinalTournament"
    assert q(0x142686928 + 0x280) == 0x140af8840 and q(0x142686928 + 0x260) == 0x140af89d0, "MatchResultPlayoff"
    assert q(0x1427258d0 + 0x280) == 0x140cace80 and q(0x1427258d0 + 0x260) == 0x140cacf90, "MatchDayResultsGroupStage"
    assert q(0x142686690 + 0x278) == 0x140ca3ee0 and q(0x142686690 + 0x260) == 0x140ca3e20, "MatchDayResults"
    assert call_to(0x140caa80b) == 0x140caaa70
    assert read(0x140cab4da, 3) == bytes.fromhex("8945ab"), "knockout filler: mov [rbp-0x55], eax (entry +4)"
    assert read(0x140af8b27, 3) == bytes.fromhex("8945b3"), "playoff filler: mov [rbp-0x4d], eax (entry +4)"
    assert read(0x140cad0ab, 2) == bytes.fromhex("8b03") and read(0x140cad0b0, 6) == bytes.fromhex("898583000000"), \
        "group stage filler: the list's dword into the entry's +4"
    assert call_to(0x140cad07d) == 0x141510bd0 and call_to(0x140ca3e7c) == 0x141510bd0
    assert read(0x141510cd7, 2) == bytes.fromhex("8930") and read(0x141510cb7, 2) == bytes.fromhex("890a"), \
        "0x141510bd0 pushes the id as a dword"
    # the upstream widening that makes those dwords whole
    caps = open(os.path.join(ROOT, "sider", "fl26caps.fl27.lua"), encoding="utf-8", errors="replace").read()
    for va in (0x141510c48, 0x141510c50, 0x1414c9038, 0x1414c903f):
        assert "va=0x%x," % va in caps, "fl26caps.fl27.lua no longer widens the day list read at %x" % va
    sys.path.insert(0, HERE)
    import matchid32
    tabs = {k: v for k, v in vars(matchid32).items() if isinstance(v, dict) and v and all(isinstance(x, int) for x in v)}
    allm = set().union(*[set(t) for t in tabs.values()])
    for va in (0x140cab4bb, 0x140cab4d3, 0x140af8b24, 0x140af8b3f, 0x141510c55, 0x141510c5b, 0x1414c9043, 0x140cb0766):
        assert va in allm, "matchid32 no longer widens %x" % va

    # CUR_SITES' three from the sweep: 0x1412fd680 looks up its [rsp+0x28] (the context's word, 0x1412fd904)
    # at the listed 0x1412fdb15 and at these three, with the word and the wrapper's call right before
    body = SRC[SRC.index("static const uint64_t CUR_SITES[]"):]
    cur = {int(x, 16) for x in re.findall(r"0x([0-9a-f]+)ull", body[:body.index("};")])}
    assert {0x1412fdb15, 0x1412fde56, 0x1412fde91, 0x1412fdec9} <= cur, sorted(map(hex, cur))
    assert call_to(0x1412fd8fc) == 0x141854f00 and read(0x1412fd901, 7) == bytes.fromhex("0fb7c089442428"), \
        "0x1412fd680: the context's word into [rsp+0x28]"
    assert read(0x1412fdb01, 4) == bytes.fromhex("8b4c2428") and call_to(0x1412fdb10) == 0x1414bb280
    for ret, at in ((0x1412fde56, 0x1412fde49), (0x1412fde91, 0x1412fde74), (0x1412fdec9, 0x1412fdebc)):
        assert call_to(ret - 5) == 0x1414bb280, hex(ret)
        assert read(at, 5) == bytes.fromhex("0fb7542428"), "%x: movzx edx, word ptr [rsp + 0x28]" % at
        for i in md.disasm(read(at + 5, ret - 5 - at - 5), at + 5):
            assert not writes(i, "edx"), (hex(ret), hex(i.address), i.op_str)
    print("CUR_SITES: 0x1412fd680's four lookups of [rsp+0x28] listed")

    # POST_FNS: 0x1412fd680 whole (one .pdata entry, no chained fragment), and the after-match handlers
    # it hands [rsp+0x28] to (by pointer, `lea rdx, [rsp+0x28]`) or that read the context themselves
    body = SRC[SRC.index("static const fnr_t POST_FNS[]"):]
    post = [(int(a, 16), int(b, 16)) for a, b in re.findall(r"\{(0x[0-9a-f]+),(0x[0-9a-f]+)\}", body[:body.index("};")])]
    assert post == [(0x12fd680, 0x12fe5d0)], post
    rf = []
    for vaddr, sz, raw in secs:
        blob = data[raw:raw + sz]
        for i in range(0, sz - 11, 12):
            b0, e0, u0 = struct.unpack_from("<3I", blob, i)
            if b0 == 0x12fd680 and e0 == 0x12fe5d0:
                rf.append(vaddr + i)
    assert rf, "no .pdata entry 0x12fd680..0x12fe5d0"
    assert read(0x1412fd727, 7) == bytes.fromhex("4981c760590300"), "0x1412fd727: add r15, 0x35960"
    for call, fn in ((0x1412fe2c8, 0x14133dfc0), (0x1412fe36d, 0x14132add0), (0x1412fe3e1, 0x1413365d0),
                     (0x1412fe224, 0x14134edc0)):
        assert call_to(call) == fn, (hex(call), hex(fn))
    for at in (0x1412fe2c0, 0x1412fe365):
        assert read(at, 5) == bytes.fromhex("488d542428"), "%x: lea rdx, [rsp + 0x28]" % at
    print("POST_FNS: 0x1412fd680 and its after-match handlers")

    # TODAY_FNS: the readers of today's calendar list; today's date where fl26match reads it
    body = SRC[SRC.index("static const fnr_t TODAY_FNS[]"):]
    today = [(int(a, 16), int(b, 16)) for a, b in re.findall(r"\{(0x[0-9a-f]+),(0x[0-9a-f]+)\}", body[:body.index("};")])]
    assert today == sorted(today) and all(a < b for a, b in today), "TODAY_FNS not sorted"
    def in_today(va): return any(a <= va - base < b for a, b in today)
    for va in (0x14134bd52, 0x141333ba3, 0x1412f8ee0, 0x141304810, 0x1413007d0):
        assert in_today(va), hex(va)
    assert not in_today(0x141546e78), "0x141546c70 (a competition's slots) must keep its own pick"
    assert read(0x1415765f2, 8) == bytes.fromhex("8b82242a64018903"), "0x1415765e0: mov eax, [rdx+0x1642a24]; mov [rbx], eax"
    print("TODAY_FNS: %d ranges, today's date at 0x1415765f2" % len(today))

    # nothing else patches a site byte; no site is a PAGE_WIDE or PICK site
    spans = [(va, va + n) for va, n, _, _ in SITES]
    hit = []
    for lua in glob.glob(os.path.join(ROOT, "sider", "fl26caps*fl27*.lua")):
        for m in re.finditer(r"va=0x([0-9a-f]+),\s*old=\"([0-9a-f]+)\"", open(lua, encoding="utf-8", errors="replace").read()):
            pva, plen = int(m.group(1), 16), len(m.group(2)) // 2
            hit += [(os.path.basename(lua), hex(pva)) for x, y in spans if pva < y and x < pva + plen]
    for name, tab in tabs.items():
        for k, v in tab.items():
            nn = len(v[0]) if isinstance(v[0], tuple) else 1
            size = sum(i.size for i in list(md.disasm(read(k, 16 * nn), k))[:nn])
            hit += [("matchid32." + name, hex(k)) for x, y in spans if k < y and x < k + size]
    for va, n, _, _ in wide_table("PAGE_WIDE"):
        hit += [("PAGE_WIDE", hex(va)) for x, y in spans if va < y and x < va + n]
    for at, ret in pick_spans():
        hit += [("PICK", hex(at)) for x, y in spans if at < y and x < ret]
    assert not hit, hit
    print("FL_2027.exe: %d sites hold the shipped reads of whole ids; no caps module, matchid32 patch, "
          "PAGE_WIDE or PICK site touches them" % len(SITES))
print("ok")
