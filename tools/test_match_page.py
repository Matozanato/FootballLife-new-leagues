"""B465/B470 (16.11.2026): FL 2027's result page reads its matches' ids as words and gets another
competition's match when twins are live (morpheus' UEL page titled "Liga BetPlay DIMAYOR I").
fl26match.dll rewrites the four reads as dword reads (PAGE_WIDE in tools/native/fl26match.c).

1. tools/native/test_match_page.c built natively: the twin choice on a made-up table (league + cup
   with the same word, no third twin, a reader with the competition, one without) and page_widen
   on a fake image.
2. Against FL_2027.exe (FL27_DIR, read only): every PAGE_WIDE site holds the shipped bytes, they
   decode as a movzx of the id into edx right before a call of the lookup wrapper 0x1414bb280 (or
   two instructions before it), the new bytes decode as the same operand read as a dword, and the
   lengths match. The entries are whole ids: matchid32 widens the fillers' slot reads, and no
   fl26caps FL27 module patches a PAGE_WIDE byte.

    python tools/test_match_page.py

Needs zig (ZIG, PATH, or D:/dev/tools/zig-*/zig.exe) for part 1 and capstone + FL27_DIR for part 2;
a missing one is reported as SKIPPED for its part.
"""
import glob, os, re, shutil, struct, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
NATIVE = os.path.join(HERE, "native")
ROOT = os.path.dirname(HERE)
SRC = open(os.path.join(NATIVE, "fl26match.c"), encoding="utf-8").read()


def find_zig():
    z = os.environ.get("ZIG")
    if z and os.path.exists(z):
        return z
    z = shutil.which("zig")
    if z:
        return z
    found = sorted(glob.glob("D:/dev/tools/zig-*/zig.exe"))
    return found[-1] if found else None


def page_wide():
    body = SRC[SRC.index("static const wide_t PAGE_WIDE[]"):]
    body = body[:body.index("};")]
    out = []
    for va, n, old, new in re.findall(r"\{(0x[0-9a-f]+)ull,\s*(\d+),\s*\{([^}]*)\},\s*\{([^}]*)\}\}", body):
        b = lambda s: bytes(int(x, 16) for x in s.split(","))
        out.append((int(va, 16), int(n), b(old), b(new)))
    return out


SITES = page_wide()
assert len(SITES) == 4, SITES
for va, n, old, new in SITES:
    assert len(old) == n and len(new) == n, hex(va)

# part 1
zig = find_zig()
if not zig:
    print("SKIPPED part 1: no zig (set ZIG to zig.exe)")
else:
    out = os.path.join(tempfile.mkdtemp(), "test_match_page.exe")
    subprocess.run([zig, "cc", "-target", "x86_64-windows-gnu", "-O2", "-fno-sanitize=undefined", "-w",
                    os.path.join(NATIVE, "test_match_page.c"), "-o", out, "-lkernel32"], check=True, cwd=NATIVE)
    r = subprocess.run([out], capture_output=True, text=True, timeout=300)
    sys.stdout.write(r.stdout)
    assert r.returncode == 0 and ", 0 failed" in r.stdout, "twin choice / page_widen test failed"
    assert "word read -> comp 0x1a3, dword read -> comp 0x51" in r.stdout

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

    md = Cs(CS_ARCH_X86, CS_MODE_64)
    for va, n, old, new in SITES:
        assert read(va, n) == old, "%x: exe has %s, not the shipped %s" % (va, read(va, n).hex(), old.hex())
        a = list(md.disasm(old, va))
        b = list(md.disasm(new, va))
        assert len(a) == 1 and a[0].size == n and a[0].mnemonic == "movzx", (hex(va), a)
        assert a[0].op_str.startswith("edx, "), (hex(va), a[0].op_str)
        assert b[0].mnemonic == "mov" and b[0].op_str.startswith("edx, ") and sum(i.size for i in b) == n, (hex(va), b)
        src_a = a[0].op_str.split(", ", 1)[1]
        src_b = b[0].op_str.split(", ", 1)[1]
        if src_a.startswith("word ptr"):
            assert src_b == "dword ptr" + src_a[len("word ptr"):], (hex(va), src_a, src_b)
        else:                                   # a register: bx -> ebx
            assert src_b == "e" + src_a, (hex(va), src_a, src_b)
        # the lookup wrapper is called within the next 3 instructions, edx untouched before it
        nxt = list(md.disasm(read(va + n, 24), va + n))[:3]
        call = [i for i in nxt if i.mnemonic == "call"]
        assert call and call[0].op_str == "0x1414bb280", (hex(va), [(hex(i.address), i.mnemonic, i.op_str) for i in nxt])
        for i in nxt[:nxt.index(call[0])]:
            assert "edx" not in i.op_str.split(",")[0] and not i.op_str.startswith("rdx") and not i.op_str.startswith("dx"), (hex(va), i.op_str)
        print("%x: %s %s -> %s; call 0x1414bb280 at %x" % (va, a[0].mnemonic, a[0].op_str,
                                                             "; ".join("%s %s" % (i.mnemonic, i.op_str) for i in b), call[0].address))
    # the entries are whole ids: the fillers' slot reads are widened by matchid32
    sys.path.insert(0, HERE)
    import matchid32
    widened = set(matchid32.ROUND2) | set(getattr(matchid32, "SITES", {}))
    for va in (0x140cab4bb, 0x140cab4d3, 0x140cabe3f, 0x140cabe57, 0x140cac162, 0x140cac179):
        assert va in widened, "matchid32 no longer widens the result page filler at %x" % va
    # no FL27 caps module patches a PAGE_WIDE byte
    hit = []
    for lua in glob.glob(os.path.join(ROOT, "sider", "fl26caps*fl27*.lua")):
        for m in re.finditer(r"va=0x([0-9a-f]+),\s*old=\"([0-9a-f]+)\"", open(lua, encoding="utf-8", errors="replace").read()):
            pva, plen = int(m.group(1), 16), len(m.group(2)) // 2
            for va, n, _, _ in SITES:
                if pva < va + n and va < pva + plen:
                    hit.append((os.path.basename(lua), hex(pva)))
    assert not hit, hit
    print("FL_2027.exe: %d sites hold the shipped reads; fillers widened by matchid32; no caps module touches them" % len(SITES))
print("ok")
