"""python tools/native/test_nullguard14.py [exe ...] -- nullguard14 (B475) offline.

The cup bracket screen's bye function 0x140b344a0 is run in an emulator (unicorn) from the real
exe, original and with sider/fl26nullguard14.lua's bytes, for every club count n from 0 to 127:

  - a field the game has a bye layout for (2-16, 18, 20, 24, 28, 30, 32): the patched block shows
    and hides exactly the places the original does;
  - any other field below 32: the original reads NULL at 0x140b34501 (the crash of B475 / B278),
    the patched one shows places 0..n-1 and hides n..31;
  - 32 and above: the patched one shows all 32 and hides none;
  - callee-saved registers and the stack pointer come back as they went in.

It also checks the patch's old bytes against the exe, the 0..31 table at 0x14260ce80, and that no
branch of the function, nor any rel32 jump or call of the exe, lands inside the rewritten block.

Exes: the arguments, else FL 2027's and FL26's of the test rigs (E:\\FL\\...). A missing exe is
skipped; none at all = SKIPPED. Needs unicorn and capstone (pip install unicorn capstone).
"""
import os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
LUA = os.path.join(HERE, "..", "..", "sider", "fl26nullguard14.lua")
DEFAULT_EXES = [r"E:\FL\FL27\clean\Football Life 2027\FL_2027.exe", r"E:\FL\FL27\game\FL_2027.exe",
                r"E:\FL\FL26\game\FL_2026.exe"]

try:
    import unicorn as U
    from unicorn import x86_const as X
    import capstone
except ImportError as e:
    print("SKIPPED: %s (pip install unicorn capstone)" % e)
    sys.exit(0)

FN, FN_END = 0x140b344a0, 0x140b34567
BLOCK = 0x140b344b8
FAULT = 0x140b34501
TABLE = 0x14260ce80
STUBS = {0x140e3d4f0: "ui", 0x140e5a790: "element", 0x140e4c240: "hide1", 0x140e4bba0: "hide2"}
SUPPORTED = set(range(2, 17)) | {18, 20, 24, 28, 30, 32}

src = open(LUA, encoding="utf-8").read()
m = re.search(r'va=0x([0-9a-f]+),\s*old="([0-9a-f]+)",\s*new="([0-9a-f]+)"', src)
PVA, OLD, NEW = int(m.group(1), 16), bytes.fromhex(m.group(2)), bytes.fromhex(m.group(3))
fails = 0


def ok(cond, what):
    global fails
    print(("ok   " if cond else "FAIL ") + what)
    fails += not cond


class Exe:
    def __init__(self, path):
        self.data = open(path, "rb").read()
        d = self.data
        pe = struct.unpack_from("<I", d, 0x3c)[0]
        n = struct.unpack_from("<H", d, pe + 6)[0]
        osz = struct.unpack_from("<H", d, pe + 20)[0]
        self.base = struct.unpack_from("<Q", d, pe + 24 + 24)[0]
        self.secs = []
        for i in range(n):
            o = pe + 24 + osz + i * 40
            vs, va, rs, raw = struct.unpack_from("<IIII", d, o + 8)
            ch = struct.unpack_from("<I", d, o + 36)[0]
            self.secs.append((va, vs, rs, raw, ch))

    def read(self, va, size):
        rva = va - self.base
        for sva, vs, rs, raw, ch in self.secs:
            if sva <= rva < sva + max(vs, rs):
                return self.data[raw + rva - sva:raw + rva - sva + size]
        raise KeyError(hex(va))


STACK, OBJ, ELEM, RET = 0x10000000, 0x20000000, 0x30000000, 0x50000000


def machine(exe, patched):
    """the exe's sections mapped once (original or with the patch: one machine each, unicorn
    keeps code it has translated), the four calls of the loop stubbed (the element call records
    the place it is asked for)"""
    mu = U.Uc(U.UC_ARCH_X86, U.UC_MODE_64)
    for sva, vs, rs, raw, ch in exe.secs:
        size = (max(vs, rs) + 0xfff) & ~0xfff
        mu.mem_map(exe.base + sva, size)
        mu.mem_write(exe.base + sva, exe.data[raw:raw + min(rs, size)])
    mu.mem_write(PVA, NEW if patched else OLD)
    for a in (STACK, OBJ, ELEM, RET):
        mu.mem_map(a, 0x10000)
    hidden = []

    def on_code(uc, addr, size, _):
        what = STUBS.get(addr)
        if what is None:
            return
        if what == "element":
            hidden.append(uc.reg_read(X.UC_X86_REG_EDX))
            uc.reg_write(X.UC_X86_REG_RAX, ELEM)
        elif what == "ui":
            uc.reg_write(X.UC_X86_REG_RAX, ELEM + 0x100)
        sp = uc.reg_read(X.UC_X86_REG_RSP)
        ret = struct.unpack("<Q", uc.mem_read(sp, 8))[0]
        uc.reg_write(X.UC_X86_REG_RSP, sp + 8)
        uc.reg_write(X.UC_X86_REG_RIP, ret)

    for a in STUBS:
        mu.hook_add(U.UC_HOOK_CODE, on_code, begin=a, end=a)
    return mu, hidden


def emulate(mach, n):
    """run 0x140b344a0 with a screen whose club count is n; returns (fault, shown flags, hidden
    places, registers kept) -- fault is the address of the faulting read, or None"""
    mu, hidden = mach
    del hidden[:]
    mu.mem_write(OBJ, b"\xcc" * 0x200)                  # garbage, as a live screen's other fields
    mu.mem_write(OBJ + 0x94, struct.pack("<I", n))
    sp0 = STACK + 0x8000
    mu.mem_write(sp0, struct.pack("<Q", RET))
    keep = {X.UC_X86_REG_RBX: 0x1111, X.UC_X86_REG_RBP: 0x2222, X.UC_X86_REG_RDI: 0x3333,
            X.UC_X86_REG_RSI: 0x4444, X.UC_X86_REG_R12: 0x5555, X.UC_X86_REG_R15: 0x6666}
    for r, v in keep.items():
        mu.reg_write(r, v)
    mu.reg_write(X.UC_X86_REG_RSP, sp0)
    mu.reg_write(X.UC_X86_REG_RCX, OBJ)
    fault = None
    try:
        mu.emu_start(FN, RET, count=200000)
    except U.UcError:
        fault = mu.reg_read(X.UC_X86_REG_RIP)
    flags = bytes(mu.mem_read(OBJ + 0x99, 32))
    kept = fault is None and all(mu.reg_read(r) == v for r, v in keep.items()) \
        and mu.reg_read(X.UC_X86_REG_RSP) == sp0 + 8
    return fault, flags, list(hidden), kept


def branch_targets(code, at):
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    md.detail = True
    for ins in md.disasm(code, at):
        if ins.group(capstone.CS_GRP_JUMP) or ins.group(capstone.CS_GRP_CALL):
            try:
                yield ins.address, int(ins.op_str, 16)
            except ValueError:
                pass


def rel32_into(exe, lo, hi):
    """every E8/E9/0F 8x rel32 of the executable sections that lands in (lo, hi)"""
    hits = []
    for sva, vs, rs, raw, ch in exe.secs:
        if not ch & 0x20000000:
            continue
        blob = exe.data[raw:raw + rs]
        for mm in re.finditer(rb"[\xe8\xe9]|\x0f[\x80-\x8f]", blob, re.S):
            p = mm.start(); k = len(mm.group(0))
            if p + k + 4 > len(blob):
                continue
            tgt = exe.base + sva + p + k + 4 + struct.unpack_from("<i", blob, p + k)[0]
            if lo < tgt < hi:
                hits.append(exe.base + sva + p)
    return hits


exes = [p for p in (sys.argv[1:] or DEFAULT_EXES) if os.path.exists(p)]
if not exes:
    print("SKIPPED: no FL_2027.exe / FL_2026.exe (pass the exe as an argument)")
    sys.exit(0)

ok(PVA == BLOCK and len(OLD) == len(NEW) == FAULT - BLOCK, "the patch rewrites 0x140b344b8..0x140b34501 (%d bytes)" % len(NEW))
seen = set()
for path in exes:
    exe = Exe(path)
    key = exe.read(FN, FN_END - FN) + exe.read(TABLE, 128)
    if key in seen:
        print("---- %s: the same function as an exe above, skipped" % path)
        continue
    seen.add(key)
    print("---- %s" % path)
    ok(exe.read(PVA, len(OLD)) == OLD, "old bytes are the exe's")
    ok(exe.read(TABLE, 128) == b"".join(struct.pack("<I", i) for i in range(32)), "0x14260ce80 holds dwords 0..31")
    lo, hi = BLOCK, FAULT
    inner = [(a, t) for a, t in branch_targets(exe.read(FN, FN_END - FN), FN) if not lo <= a < hi and lo < t < hi]
    ok(not inner, "no branch of 0x140b344a0 outside the block lands inside it %s" % inner)
    newt = [(a, t) for a, t in branch_targets(NEW, BLOCK)]
    ok(sorted(t for a, t in newt) == [0x140b344eb, 0x140b34552], "the block's own jumps: 0x140b344eb, 0x140b34552 %s" % [hex(t) for a, t in newt])
    hits = rel32_into(exe, lo, hi)
    ok(not hits, "no rel32 jump or call of the exe lands inside the block %s" % [hex(h) for h in hits[:5]])
    bad = []
    orig, fixed = machine(exe, False), machine(exe, True)
    for n in range(0, 128):
        f0, fl0, h0, k0 = emulate(orig, n)
        f1, fl1, h1, k1 = emulate(fixed, n)
        if n in SUPPORTED:
            good = f0 is None and k0 and f1 is None and k1 and fl1 == fl0 and h1 == h0
            want = "as the original (%d hidden)" % len(h0)
        elif n < 32:
            exp_fl = bytes(1 if i < n else 0 for i in range(32))
            good = f0 == FAULT and f1 is None and k1 and fl1 == exp_fl and h1 == list(range(n, 32))
            want = "original crashes at 0x%x, patched hides %d..31" % (f0 or 0, n)
        else:
            good = f0 == FAULT and f1 is None and k1 and fl1 == b"\x01" * 32 and h1 == []
            want = "original crashes at 0x%x, patched hides none" % (f0 or 0)
        if not good:
            bad.append("n=%d: original fault %s hidden %s; patched fault %s hidden %s kept %s" % (
                n, hex(f0) if f0 else None, h0, hex(f1) if f1 else None, h1, k1))
        elif n in (16, 17, 22, 26, 30, 31, 32, 44):
            print("     n=%-3d %s" % (n, want))
    ok(not bad, "n = 0..127 in the emulator%s" % ("" if not bad else ":\n  " + "\n  ".join(bad[:8])))

print("FAILED %d" % fails if fails else "all ok")
sys.exit(1 if fails else 0)
