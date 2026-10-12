"""Emulate the generated module's patches on the real exe bytes (unicorn) and check them.

python slotsemu.py fl26slots250.lua [N]
"""
import os, re, struct, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pylib"))
from unicorn import *
from unicorn.x86_const import *
import mkslots as M

lua = sys.argv[1]
N = int(sys.argv[2]) if len(sys.argv) > 2 else 250
txt = open(lua, encoding="utf-8").read()
P = [(int(v, 16), o, n) for v, o, n in re.findall(r'va=0x([0-9a-f]+), old="([0-9a-f]*)", new="([0-9a-f]*)"', txt)]
d = open(M.EXE, "rb").read()
secs = M.sections(d)

mu = Uc(UC_ARCH_X86, UC_MODE_64)
for base, vs, raw, rs, name in secs:
    lo = base & ~0xfff
    size = ((base + vs + 0xfff) & ~0xfff) - lo
    mu.mem_map(lo, size)
    mu.mem_write(base, d[raw:raw + min(rs, vs)])
mu.mem_map(M.PAGE, 0x1000)
# pass 1 + pass 2, like the applier
for va, old, new in P:
    cur = bytes(mu.mem_read(va, len(old) // 2)).hex()
    assert cur == old, (hex(va), cur, old)
for va, old, new in P:
    mu.mem_write(va, bytes.fromhex(new))

STACK, REG = 0x300000000, 0x400000000
mu.mem_map(STACK, 0x10000)
mu.mem_map(REG - 0x10000, 0x80000)   # guard bytes either side
RET = 0x500000000
mu.mem_map(RET, 0x1000); mu.mem_write(RET, b"\xf4")

# memset hook for clear's tail jump
def memset_hook(uc, addr, size, ud):
    rcx, rdx, r8 = uc.reg_read(UC_X86_REG_RCX), uc.reg_read(UC_X86_REG_RDX), uc.reg_read(UC_X86_REG_R8)
    uc.mem_write(rcx, bytes([rdx & 0xff]) * r8)
    rsp = uc.reg_read(UC_X86_REG_RSP)
    ret = struct.unpack("<Q", uc.mem_read(rsp, 8))[0]
    uc.reg_write(UC_X86_REG_RSP, rsp + 8); uc.reg_write(UC_X86_REG_RIP, ret)
mu.hook_add(UC_HOOK_CODE, memset_hook, begin=M.MEMSET, end=M.MEMSET)

writes = []
def wr(uc, acc, addr, size, val, ud):
    writes.append((addr, size))
mu.hook_add(UC_HOOK_MEM_WRITE, wr, begin=REG - 0x10000, end=REG + 0x5a25e + 0x10000)

def call(fn, rcx=REG, rdx=0, r8=0, r9=0, keep=()):
    rsp = STACK + 0x8000
    mu.mem_write(rsp, struct.pack("<Q", RET))
    regs = dict(rcx=rcx, rdx=rdx, r8=r8, r9=r9)
    mu.reg_write(UC_X86_REG_RSP, rsp)
    mu.reg_write(UC_X86_REG_RCX, rcx); mu.reg_write(UC_X86_REG_RDX, rdx)
    mu.reg_write(UC_X86_REG_R8, r8); mu.reg_write(UC_X86_REG_R9, r9)
    for r in (UC_X86_REG_RBX, UC_X86_REG_RSI, UC_X86_REG_RDI, UC_X86_REG_R10, UC_X86_REG_R11):
        mu.reg_write(r, 0x1111222233334444)
    mu.emu_start(fn, RET, count=10_000_000)
    assert mu.reg_read(UC_X86_REG_RSP) == rsp + 8
    for name, r in () if fn == 0x1414d62e0 else (("rcx", UC_X86_REG_RCX), ("r8", UC_X86_REG_R8), ("r9", UC_X86_REG_R9)):
        assert mu.reg_read(r) == regs[name], ("clobbered", name, hex(fn))
    if "rdx" in keep:
        assert mu.reg_read(UC_X86_REG_RDX) == rdx, ("clobbered rdx", hex(fn))
    return mu.reg_read(UC_X86_REG_RAX)

GET, COUNT, CLEAR, SET, SETCNT = 0x1414d6290, 0x1414d62c0, 0x1414d62e0, 0x1414d6330, 0x1414d6360
if "--big" in sys.argv:                         # the module was made with mkslots.py --big
    M.BIG[79] = M.BIG[80] = int(sys.argv[sys.argv.index("--big") + 1])
L = M.layout(N)
caps = L["caps"]
FILLSRC = 0x14351ae44
mu.mem_write(FILLSRC, struct.pack("<I", 0xffff << 14))

# clear
mu.mem_write(REG, b"\xab" * 0x5a25e)
writes.clear()
call(CLEAR)
lo = min(a for a, s in writes); hi = max(a + s for a, s in writes)
assert lo == REG and hi == REG + L["cnt"], (hex(lo - REG), hex(hi - REG))
mem = bytes(mu.mem_read(REG, 0x5a25e))
assert mem[:L["cnt"]] == struct.pack("<I", 0xffff) * L["listdw"]
assert mem[L["cnt"]:L["cnt"] + 2 * N] == b"\0" * 2 * N
assert mem[L["cnt"] + 2 * N:] == b"\xab" * (0x5a25e - L["cnt"] - 2 * N)
print("clear ok: lists 0..0x%x filled, counts zeroed (memset), nothing past +0x%x" % (L["cnt"], L["cnt"] + 2 * N))

# model test
random.seed(1)
model = {s: [] for s in range(N)}
writes.clear()
for s in list(range(N)) + [N, N + 1, 255, 256, 0xffffffff, 0x80000000]:
    cap = caps[s] if s < N else 0
    for n in (cap, cap + 1, 0xffff, 5):
        r = call(SETCNT, rdx=s, r8=n, keep=("rdx",))
        if s < N and s != 123 and n <= cap:
            model[s] = list(range(n))
    want = min(cap, 5) if s < N and s != 123 else 0
    got = call(COUNT, rdx=s, keep=("rdx",)) & 0xffff
    assert got == (5 if s < N and s != 123 and 5 <= cap else 0), (s, got)
    for i in (0, 1, 4, 5, cap - 1, cap, cap + 7, 0xffffffff):
        call(SET, rdx=s, r8=i & 0xffffffff, r9=(s << 16) | (i & 0xffff))
for a, sz in writes:
    assert REG <= a and a + sz <= REG + L["cnt"] + 2 * N, hex(a - REG)
# every slot's list is private: what get returns is what set wrote in that slot
for s in range(N):
    c = call(COUNT, rdx=s) & 0xffff
    for i in range(c):
        v = call(GET, rdx=s, r8=i) & 0xffffffff
        exp = (s << 16) | i if i in (0, 1, 4) else 0xffff
        assert v == exp, (s, i, hex(v), hex(exp))
    assert call(GET, rdx=s, r8=c) & 0xffffffff == 0xffffffff
for s in (123, N, 255, 0xffffffff):
    assert call(GET, rdx=s, r8=0) & 0xffffffff == 0xffffffff
# a garbage count (an old save) never lets get read past the slot
mu.mem_write(REG + L["cnt"] + 2 * 10, struct.pack("<H", 0xffff))
assert call(COUNT, rdx=10) & 0xffff == caps[10]
assert call(GET, rdx=10, r8=caps[10]) & 0xffffffff == 0xffffffff
# the big slots hold what the layout gives them
if N > 80:
    assert call(SETCNT, rdx=80, r8=M.BIG[80]) is not None and call(COUNT, rdx=80) & 0xffff == M.BIG[80]
    call(SET, rdx=80, r8=1599, r9=0x1234)
    assert call(GET, rdx=80, r8=1599) & 0xffffffff == 0x1234
print("accessors ok: %d slots, caps %s, slot 123 and >= N refused, no write outside the region"
      % (N, sorted(set(caps))))

# compare/branch sites
import capstone
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
REGS = {"eax": UC_X86_REG_RAX, "ebx": UC_X86_REG_RBX, "ecx": UC_X86_REG_RCX, "edx": UC_X86_REG_RDX,
        "esi": UC_X86_REG_RSI, "edi": UC_X86_REG_RDI, "ebp": UC_X86_REG_RBP,
        "r8d": UC_X86_REG_R8, "r12d": UC_X86_REG_R12, "r14d": UC_X86_REG_R14, "r15d": UC_X86_REG_R15}
for va, kind, why in M.SITES:
    o = M.offset_of(secs, va)
    c, j = list(md.disasm(d[o:o + 24], va))[:2]
    reg = c.op_str.split(",")[0]
    tgt = int(j.op_str, 16); back = va + c.size + j.size
    for v in (0, 1, 122, 123, 124, 127, 128, 200, N - 1, N, N + 1, 255, 0x7fffffff, 0x80000000, 0xffffffff):
        mu.reg_write(REGS[reg], v)
        stop = []
        def h(uc, addr, size, ud):
            if addr in (tgt, back):
                stop.append(addr); uc.emu_stop()
        hh = mu.hook_add(UC_HOOK_CODE, h)
        mu.emu_start(va, 0, count=20)
        mu.hook_del(hh)
        sv = v - (1 << 32) if v & 0x80000000 else v
        signed = j.mnemonic in ("jl", "jge")
        x = sv if signed else v
        inrange = 0 <= x < N if not signed else x < N
        ok = inrange and (kind == "loop" or v != 123)
        taken = stop[0] == tgt
        if j.mnemonic in ("jb", "jl"):
            exp_taken = ok if kind == "guard" else inrange
        else:
            exp_taken = not ok if kind == "guard" else not inrange
        assert taken == exp_taken, (hex(va), kind, j.mnemonic, hex(v), taken)
    print("site 0x%x %-5s %s %s ok" % (va, kind, c.op_str, j.mnemonic))

# team slot
for v in list(range(0, 260)) + [0xffffffff, 0x80000000]:
    mu.reg_write(UC_X86_REG_RAX, v); mu.reg_write(UC_X86_REG_RCX, 0xdead)
    mu.emu_start(M.TEAMSLOT, M.TEAMSLOT_BACK, count=20)
    got = mu.reg_read(UC_X86_REG_RAX) & 0xffffffff
    sv = v - (1 << 32) if v & 0x80000000 else v
    exp = v if (sv < min(N, 128) and v != 123) else 7
    assert got == exp and mu.reg_read(UC_X86_REG_RCX) & 0xffffffff == exp, (v, got)
print("team slot ok: 0..%d except 123 kept, rest -> 7" % (min(N, 128) - 1))
print("ALL OK")
