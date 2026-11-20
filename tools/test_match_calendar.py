"""B470/B465 (17.11.2026): FL 2027's Be a Legend Calendrier keeps a day's match id as a WORD, and the
matchday page opened from it with cross looked that word up as the low twin: another competition's
matchday ("Tercera Division A J22" for EFL Championship J22). fl26match.dll takes the user's club's twin
at the Calendrier's lookup, remembers it, and gives it to the matchday page's lookups of the same word
(PICK in tools/native/fl26match.c).

1. tools/native/test_match_calendar.c built natively: the choice through the real return addresses
   (a fake image with the shipped bytes), before and after a pick, other words, unclear picks, sites
   whose bytes differ, mask 0xffff.
2. Against FL_2027.exe (FL27_DIR, read only):
   - every PICK site holds its bytes: a read of the id into edx (movzx / pextrw) and the call of the
     lookup wrapper 0x1414bb280 right before the return address, edx untouched in between;
   - the data flow the fix relies on: the Schedule builder keeps the day's word (0x140caea84) in the
     entry's +4, the Calendrier's cross handler (vtable 0x14268bda8 +0x188 = 0x140b05930) hands that dword
     to the "chosen match" setter 0x140e40f90, the matchday page (vtable 0x142725490) takes it from the
     getter 0x140e3d470 into +0xb8 and its +0x260 / +0x268 methods are the ones with the reads;
   - no fl26caps FL27 module and no matchid32 patch touches a PICK byte, and no PICK return address is
     on another fl26match site list.

    python tools/test_match_calendar.py

Needs zig (ZIG, PATH, or D:/dev/tools/zig-*/zig.exe) for part 1 and capstone + FL27_DIR for part 2;
a missing one is reported as SKIPPED for its part.
"""
import glob, os, re, shutil, struct, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
NATIVE = os.path.join(HERE, "native")
ROOT = os.path.dirname(HERE)
SRC = open(os.path.join(NATIVE, "fl26match.c"), encoding="utf-8").read()
WRAP = 0x1414bb280


def find_zig():
    z = os.environ.get("ZIG")
    if z and os.path.exists(z):
        return z
    z = shutil.which("zig")
    if z:
        return z
    found = sorted(glob.glob("D:/dev/tools/zig-*/zig.exe"))
    return found[-1] if found else None


def pick():
    body = SRC[SRC.index("static const pick_t PICK[]"):]
    body = body[:body.index("};")]
    return [(int(r, 16), int(a, 16), bytes.fromhex(h))
            for r, a, h in re.findall(r"\{(0x[0-9a-f]+)ull,\s*(0x[0-9a-f]+)ull,\s*\"([0-9a-f]+)\"\}", body)]


def site_list(name):
    body = SRC[SRC.index("static const uint64_t %s[]" % name):]
    body = body[:body.index("};")]
    return {int(x, 16) for x in re.findall(r"0x([0-9a-f]+)ull", body)}


SITES = pick()
assert len(SITES) == 5, SITES
for ret, at, hx in SITES:
    assert at + len(hx) == ret - 4 and hx[-1] == 0xe8, (hex(ret), hex(at))

# part 1
zig = find_zig()
if not zig:
    print("SKIPPED part 1: no zig (set ZIG to zig.exe)")
else:
    out = os.path.join(tempfile.mkdtemp(), "test_match_calendar.exe")
    subprocess.run([zig, "cc", "-target", "x86_64-windows-gnu", "-O2", "-fno-sanitize=undefined", "-w",
                    os.path.join(NATIVE, "test_match_calendar.c"), "-o", out, "-lkernel32"], check=True, cwd=NATIVE)
    r = subprocess.run([out], capture_output=True, text=True, timeout=300)
    sys.stdout.write(r.stdout)
    assert r.returncode == 0 and ", 0 failed" in r.stdout, "Calendrier / matchday page test failed"
    assert "page reads comp 325" in r.stdout and "page reads comp 79" in r.stdout

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

    def rip_target(va, n):                     # the rip-relative operand of the instruction at va, n bytes long
        return va + n + struct.unpack("<i", read(va + n - 4, 4))[0]

    md = Cs(CS_ARCH_X86, CS_MODE_64)
    for ret, at, hx in SITES:
        assert read(at, len(hx)) == hx, "%x: exe has %s, not %s" % (at, read(at, len(hx)).hex(), hx.hex())
        assert call_to(ret - 5) == WRAP, "%x: not a call of 0x%x" % (ret - 5, WRAP)
        ins = list(md.disasm(read(at, ret - at), at))
        assert sum(i.size for i in ins) == ret - at, (hex(at), ins)
        assert ins[0].mnemonic in ("movzx", "pextrw") and ins[0].op_str.startswith("edx, "), (hex(at), ins[0].op_str)
        for i in ins[1:-1]:
            assert not re.match(r"(e|r)?dx\b|dl\b", i.op_str.split(",")[0]), (hex(i.address), i.op_str)
        print("%x: %s %s; ... call 0x%x; return %x" % (at, ins[0].mnemonic, ins[0].op_str, WRAP, ret))

    # the data flow
    assert read(0x140caea84, 3) == bytes.fromhex("0fb7f0"), "builder: movzx esi, ax"          # the day's word
    assert read(0x140caea94, 3) == bytes.fromhex("897503"), "builder: mov [rbp+3], esi"       # entry +4
    assert read(0x140caec8d, 7) == bytes.fromhex("0f1045ff0f1100"), "builder: the entry pushed"
    assert q(0x14268bda8 + 0x188) == 0x140b05930, "Calendrier vtable +0x188"
    assert read(0x140b05979, 7) == bytes.fromhex("0f10818c000000")                            # the entry
    assert read(0x140b059c9, 5) == bytes.fromhex("660f73d804")                                # psrldq xmm0, 4
    assert read(0x140b059d9, 4) == bytes.fromhex("660f7ec2")                                  # movd edx, xmm0: +4 as a dword
    assert call_to(0x140b059ee) == 0x140e40f90
    assert read(0x140e40f90, 2) == bytes.fromhex("8915") and read(0x140e3d470, 2) == bytes.fromhex("8b05")
    chosen = rip_target(0x140e40f90, 6)
    assert chosen == rip_target(0x140e3d470, 6), "setter and getter: one dword"
    assert call_to(0x140cab9ce) == 0x140e3d470 and read(0x140cab9d3, 6) == bytes.fromhex("8983b8000000")
    assert read(0x140cab9d9, 2) == bytes.fromhex("8bd0") and call_to(0x140cab9de) == 0x140cabb60
    vt = 0x140cab9b6 + struct.unpack("<i", read(0x140cab9b2, 4))[0]
    assert read(0x140cab9af, 3) == bytes.fromhex("488d05") and vt == 0x142725490, hex(vt)
    assert q(vt + 0x260) == 0x140cacbe0 and q(vt + 0x268) == 0x140cac3d0
    print("data flow: day word -> entry +4 -> 0x140e40f90 (dword %x) -> page +0xb8 -> the page's reads" % chosen)

    # nothing else patches a PICK byte; no PICK return address is on another list
    spans = [(at, ret) for ret, at, _ in SITES]
    hit = []
    for lua in glob.glob(os.path.join(ROOT, "sider", "fl26caps*fl27*.lua")):
        for m in re.finditer(r"va=0x([0-9a-f]+),\s*old=\"([0-9a-f]+)\"", open(lua, encoding="utf-8", errors="replace").read()):
            pva, plen = int(m.group(1), 16), len(m.group(2)) // 2
            hit += [(os.path.basename(lua), hex(pva)) for a, b in spans if pva < b and a < pva + plen]
    sys.path.insert(0, HERE)
    import matchid32
    for name, tab in vars(matchid32).items():
        if not (isinstance(tab, dict) and tab and all(isinstance(k, int) for k in tab)):
            continue
        for k, v in tab.items():
            n = len(v[0]) if isinstance(v[0], tuple) else 1
            size = sum(i.size for i in list(md.disasm(read(k, 16 * n), k))[:n])
            hit += [("matchid32." + name, hex(k)) for a, b in spans if k < b and a < k + size]
    assert not hit, hit
    others = set()
    for name in ("USER_SITES", "DAY_SITES", "CUR_PAGE_SITES", "CUR_SITES"):
        others |= site_list(name)
    assert not others & {ret for ret, _, _ in SITES}, others & {ret for ret, _, _ in SITES}
    print("FL_2027.exe: %d sites hold the shipped reads; no caps module or matchid32 patch touches them" % len(SITES))
print("ok")
