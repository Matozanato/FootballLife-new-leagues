"""python tools/native/test_nullguard15.py [exe ...] -- nullguard15 (B491) offline.

The player value lookup 0x140f56320 (and the std::map::at it calls, 0x140f59f40) is run in an
emulator (unicorn) from the real exe, original and with sider/fl26nullguard15.lua's bytes, over a
map of player keys {u16 index, u32 id} -> u32 value built in memory the way MSVC lays one out:

  - every key the map holds: both give the same value;
  - a key it does not hold (index or id off by one, a gone player, the "none" key {0xffff, 0}):
    the original reaches the throw (call _Xout_of_range at 0x140f59fbc, the c0000409 of B491),
    the patched one returns 0;
  - callee-saved registers and the stack pointer come back as they went in.

It also checks the patch's old bytes against the exe, the dword 0 at 0x14260ce80, that the only
branches into the rewritten bytes are the function's own two to 0x140f59fb5, and that no rel32
jump or call of the exe lands inside them.

Exes: the arguments, else FL 2027's and FL26's of the test rigs (E:\\FL\\...). A missing exe is
skipped; none at all = SKIPPED. Needs unicorn and capstone (pip install unicorn capstone).
"""
import os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
LUA = os.path.join(HERE, "..", "..", "sider", "fl26nullguard15.lua")
DEFAULT_EXES = [r"E:\FL\FL27\clean\Football Life 2027\FL_2027.exe", r"E:\FL\FL27\game\FL_2027.exe",
                r"E:\FL\FL26\game\FL_2026.exe"]

try:
    import unicorn as U
    from unicorn import x86_const as X
    import capstone
except ImportError as e:
    print("SKIPPED: %s (pip install unicorn capstone)" % e)
    sys.exit(0)

VALUE_FN = 0x140f56320          # value of a player key: the map at +0x78 of +0x140 / +0x148 / +0xa0
AT_FN, AT_END = 0x140f59f40, 0x140f59fc2
BLOCK = 0x140f59fb5
THROW_CALL = 0x140f59fbc        # call [__imp_?_Xout_of_range]
ZERO = 0x14260ce80

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


STACK, OBJ, NODES, KEY, RET = 0x10000000, 0x20000000, 0x30000000, 0x40000000, 0x50000000

# the map: player keys as the game makes them (index word, id) and a value each
HELD = [(0, 28728, 120), (1, 28730, 80), (2, 28736, 2232251), (3, 28750, 4500), (4772, 177874, 197447),
        (4773, 177875, 900), (30000, 61000, 333), (65533, 77229, 10), (0xffff, 77212, 77),
        (0xffff, 146923, 55), (0xffff, 185015, 999)]
MISSING = [(0xffff, 0), (5, 28750), (4772, 177875), (4774, 177874), (30001, 61000), (0, 0),
           (0xffff, 146924), (65534, 77229), (1, 28731)]


def build_map(mu):
    """MSVC std::map: head node (isnil) whose +8 is the root; every absent child is the head.
    Node: +0 left, +8 parent, +0x10 right, +0x19 isnil, key word +0x1c, id +0x20, value +0x24."""
    keys = sorted(HELD)
    head = NODES
    addr = [NODES + 0x40 * (i + 1) for i in range(len(keys))]

    def node(lo, hi, parent):
        if lo >= hi:
            return head
        mid = (lo + hi) // 2
        a = addr[mid]
        left = node(lo, mid, a)
        right = node(mid + 1, hi, a)
        w, i, v = keys[mid]
        mu.mem_write(a, struct.pack("<QQQBB", left, parent, right, 1, 0) + b"\0\0"
                     + struct.pack("<H", w) + b"\0\0" + struct.pack("<II", i, v))
        return a

    root = node(0, len(keys), head)
    mu.mem_write(head, struct.pack("<QQQBB", addr[0], root, addr[-1], 1, 1) + b"\0" * 0x26)
    mu.mem_write(OBJ, b"\xcc" * 0x200)                  # garbage, as a live object's other fields
    mu.mem_write(OBJ + 0x140, struct.pack("<QQ", 0, 0))  # no +0x140 / +0x148: the map at +0xa0+0x78
    mu.mem_write(OBJ + 0xa0 + 0x78, struct.pack("<QQ", head, len(keys)))


def machine(exe, patched):
    mu = U.Uc(U.UC_ARCH_X86, U.UC_MODE_64)
    for sva, vs, rs, raw, ch in exe.secs:
        size = (max(vs, rs) + 0xfff) & ~0xfff
        mu.mem_map(exe.base + sva, size)
        mu.mem_write(exe.base + sva, exe.data[raw:raw + min(rs, size)])
    mu.mem_write(PVA, NEW if patched else OLD)
    for a in (STACK, OBJ, NODES, KEY, RET):
        mu.mem_map(a, 0x10000)
    build_map(mu)
    threw = []
    if not patched:
        def on_throw(uc, addr, size, _):
            threw.append(addr)
            uc.emu_stop()
        mu.hook_add(U.UC_HOOK_CODE, on_throw, begin=THROW_CALL, end=THROW_CALL)
    return mu, threw


def emulate(mach, word, pid):
    """0x140f56320(OBJ, &key); returns (threw, eax, registers kept)"""
    mu, threw = mach
    del threw[:]
    mu.mem_write(KEY, struct.pack("<HHI", word, 0xcccc, pid))
    sp0 = STACK + 0x8000
    mu.mem_write(sp0, struct.pack("<Q", RET))
    keep = {X.UC_X86_REG_RBX: 0x1111, X.UC_X86_REG_RBP: 0x2222, X.UC_X86_REG_RDI: 0x3333,
            X.UC_X86_REG_RSI: 0x4444, X.UC_X86_REG_R12: 0x5555, X.UC_X86_REG_R14: 0x7777,
            X.UC_X86_REG_R15: 0x6666}
    for r, v in keep.items():
        mu.reg_write(r, v)
    mu.reg_write(X.UC_X86_REG_RSP, sp0)
    mu.reg_write(X.UC_X86_REG_RCX, OBJ)
    mu.reg_write(X.UC_X86_REG_RDX, KEY)
    mu.reg_write(X.UC_X86_REG_RAX, 0xdeadbeef)
    err = None
    try:
        mu.emu_start(VALUE_FN, RET, count=10000)
    except U.UcError as e:
        err = e
    if threw:
        return True, None, False
    if err is not None or mu.reg_read(X.UC_X86_REG_RIP) != RET:
        return None, None, False
    kept = all(mu.reg_read(r) == v for r, v in keep.items()) and mu.reg_read(X.UC_X86_REG_RSP) == sp0 + 8
    return False, mu.reg_read(X.UC_X86_REG_EAX), kept


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

ok(PVA == BLOCK and len(OLD) == len(NEW) == AT_END - BLOCK, "the patch rewrites 0x140f59fb5..0x140f59fc2 (%d bytes)" % len(NEW))
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
new_asm = [("%s %s" % (i.mnemonic, i.op_str)).strip() for i in md.disasm(NEW, BLOCK)]
ok(new_asm == ["lea rax, [rip + 0x16b2ec4]", "add rsp, 0x28", "ret", "int3"], "new bytes: %s" % new_asm)
seen = set()
for path in exes:
    exe = Exe(path)
    key = exe.read(VALUE_FN, 0x36) + exe.read(AT_FN, AT_END - AT_FN) + exe.read(ZERO, 4)
    if key in seen:
        print("---- %s: the same functions as an exe above, skipped" % path)
        continue
    seen.add(key)
    print("---- %s" % path)
    ok(exe.read(PVA, len(OLD)) == OLD, "old bytes are the exe's")
    ok(exe.read(ZERO, 4) == b"\0\0\0\0", "0x14260ce80 holds a dword 0")
    into = sorted((a, t) for a, t in branch_targets(exe.read(AT_FN, BLOCK - AT_FN), AT_FN) if BLOCK <= t < AT_END)
    ok([t for a, t in into] == [BLOCK, BLOCK], "the function's branches into the block: two, both to its start %s" % [(hex(a), hex(t)) for a, t in into])
    hits = rel32_into(exe, BLOCK, AT_END)
    ok(not hits, "no rel32 jump or call of the exe lands inside the block %s" % [hex(h) for h in hits[:5]])
    callers = [a for a in rel32_into(exe, AT_FN - 1, AT_FN + 1)]
    ok(callers == [0x140f5634a], "0x140f59f40 is called from 0x140f5634a only %s" % [hex(c) for c in callers])
    orig, fixed = machine(exe, False), machine(exe, True)
    bad = []
    for w, i, v in HELD:
        t0, v0, k0 = emulate(orig, w, i)
        t1, v1, k1 = emulate(fixed, w, i)
        if not (t0 is False and t1 is False and v0 == v1 == v and k0 and k1):
            bad.append("held {%#x, %d}: original %s/%s, patched %s/%s (want %d)" % (w, i, t0, v0, t1, v1, v))
    ok(not bad, "%d held keys: the same value, original and patched%s" % (len(HELD), "" if not bad else ":\n  " + "\n  ".join(bad)))
    bad = []
    for w, i in MISSING:
        t0, v0, k0 = emulate(orig, w, i)
        t1, v1, k1 = emulate(fixed, w, i)
        if not (t0 is True and t1 is False and v1 == 0 and k1):
            bad.append("missing {%#x, %d}: original threw %s, patched threw %s value %s kept %s" % (w, i, t0, t1, v1, k1))
    ok(not bad, "%d missing keys (the none key too): original throws, patched gives 0%s" % (len(MISSING), "" if not bad else ":\n  " + "\n  ".join(bad)))

print("FAILED %d" % fails if fails else "all ok")
sys.exit(1 if fails else 0)
