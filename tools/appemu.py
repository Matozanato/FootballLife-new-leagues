"""Run the game's own appearance-table code on the real exe bytes (unicorn) with fl26appcap.

python appemu.py [sider/experimental/fl26appcap.lua] [--records N] [--stock]

Maps the exe, checks and applies the module's patches exactly as the Lua applier does, adds
fl26regen's app_guard (the loader's head clamped at cap - 1), and then calls, in order:

  1. the object's constructor 0x1414bce10           -- writes stay inside the new size
  2. the PlayerAppearance.bin loader 0x1414bd7a0    -- N records of 60 bytes, sorted ids;
     it tail-calls the recount 0x1414bd870         -- count = every record loaded, data intact
  3. lookup by id 0x1414bd220 and copy-out 0x1414bd160 for ids on both sides of 30,024
  4. insert 0x1414bd5c0 of a new id in the middle    -- order kept, count + 1
  5. remove by id 0x1414bce50                        -- order kept, count - 1
  6. the backup copy 0x1414b7170 and the restore 0x1414b6df0 through a fake owner
     ([owner+0x60] / [owner+0x88])                  -- the whole object, byte for byte
  7. a file with more records than the cap           -- clamped at cap - 1, nothing past

Every write to the object's allocation is watched: one byte past the new size fails the run.
--stock runs the shipped bytes (no module) as the control: the load stops at 30,023.
"""
import os, re, struct, sys
from unicorn import *
from unicorn.x86_const import *
import flpaths

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
IMG = 0x140000000
args = [a for a in sys.argv[1:] if not a.startswith("--")]
LUA = args[0] if args else os.path.join(ROOT, "sider", "experimental", "fl26appcap.lua")
STOCK = "--stock" in sys.argv
NREC = int(sys.argv[sys.argv.index("--records") + 1]) if "--records" in sys.argv else 60000

d = open(flpaths.need_exe(), "rb").read()
pe = struct.unpack_from("<I", d, 0x3c)[0]
nsec = struct.unpack_from("<H", d, pe + 6)[0]
opt = struct.unpack_from("<H", d, pe + 20)[0]
mu = Uc(UC_ARCH_X86, UC_MODE_64)
for i in range(nsec):
    p = pe + 24 + opt + i * 40
    nm = d[p:p + 8].rstrip(b"\0").decode("latin1")
    vsz, va, rsz, ro = struct.unpack_from("<IIII", d, p + 8)
    if nm == ".impdata":
        continue                      # 400 MB of moved functions; none of this code calls it
    lo = (IMG + va) & ~0xfff
    hi = (IMG + va + max(vsz, rsz) + 0xfff) & ~0xfff
    mu.mem_map(lo, hi - lo)
    mu.mem_write(IMG + va, d[ro:ro + min(rsz, max(vsz, rsz))])

P = [(int(v, 16), bytes.fromhex(o), bytes.fromhex(n))
     for v, o, n in re.findall(r'va=0x([0-9a-f]+), old="([0-9a-f]*)", new="([0-9a-f]*)"',
                               open(LUA, encoding="utf-8").read())]
if not STOCK:
    for va, old, new in P:
        assert bytes(mu.mem_read(va, len(old))) == old, "mismatch at %x" % va
    for va, old, new in P:
        mu.mem_write(va, new)

rd32 = lambda a: struct.unpack("<I", mu.mem_read(a, 4))[0]
rd16 = lambda a: struct.unpack("<H", mu.mem_read(a, 2))[0]
CAP = rd32(0x1414bd17f + 1)
CNT1 = rd32(0x1414bd3b9 + 3)
CNT2 = rd32(0x1414bd16f + 3)
TAB = rd32(0x1414bd1bd + 3)
SIZE = rd32(0x1414b6fde + 1)
assert CNT2 == CNT1 + 2 and SIZE == CNT1 + 4 and TAB + CAP * 0x48 == CNT1, "inconsistent layout"
print("%s: cap %d, object 0x%x, counts +0x%x/+0x%x, table +0x%x"
      % ("stock" if STOCK else os.path.basename(LUA), CAP, SIZE, CNT1, CNT2, TAB))

# fl26regen's app_guard, the same 28 bytes (fl26regen.c)
LOAD = 0x1414bd7ad
SIG = bytes.fromhex("48b88988888888888888" "488bfa" "49f7e0" "33db" "4c8bf1" "488bea" "48c1ed05")
assert bytes(mu.mem_read(LOAD, 28)) == SIG
g = bytearray.fromhex("4c8bf1488bfa33dbb8000000004c3bc0490f42c0996a3c59f7f18be8")
g[9:13] = struct.pack("<I", (CAP - 1) * 60)
mu.mem_write(LOAD, bytes(g))

# the heap: a bump allocator; the object gets a region of its own with a canary behind it
HEAP, STACK, RET, OWNER = 0x600000000, 0x300000000, 0x500000000, 0x510000000
mu.mem_map(HEAP, 0x4000000)
mu.mem_map(STACK, 0x100000)
mu.mem_map(RET, 0x1000); mu.mem_write(RET, b"\xf4")
mu.mem_map(OWNER, 0x1000)
heap = [HEAP]
allocs = []


def alloc(n):
    a = (heap[0] + 0xfff) & ~0xfff
    heap[0] = a + n
    allocs.append((a, n))
    pad = ((a + n + 0xfff) & ~0xfff) + 0x1000 - (a + n)
    mu.mem_write(a, b"\xab" * n + b"\xee" * pad)   # canary up to the next page and one more
    heap[0] = a + n + pad
    return a


def ret_from(uc, value=None):
    rsp = uc.reg_read(UC_X86_REG_RSP)
    uc.reg_write(UC_X86_REG_RIP, struct.unpack("<Q", uc.mem_read(rsp, 8))[0])
    uc.reg_write(UC_X86_REG_RSP, rsp + 8)
    if value is not None:
        uc.reg_write(UC_X86_REG_RAX, value)


def hook(addr, fn):
    mu.hook_add(UC_HOOK_CODE, lambda uc, a, s, u: fn(uc), begin=addr, end=addr)


R = lambda r: mu.reg_read(r)
hook(0x1415a1720, lambda uc: (uc.mem_write(R(UC_X86_REG_RCX), bytes([R(UC_X86_REG_RDX) & 0xff]) * R(UC_X86_REG_R8)),
                              ret_from(uc, R(UC_X86_REG_RCX))))                                   # memset
hook(0x1415a1708, lambda uc: (uc.mem_write(R(UC_X86_REG_RCX), bytes(uc.mem_read(R(UC_X86_REG_RDX), R(UC_X86_REG_R8)))),
                              ret_from(uc, R(UC_X86_REG_RCX))))                                   # memcpy
hook(0x1403fb410, lambda uc: ret_from(uc, alloc(R(UC_X86_REG_RDX) & 0xffffffff)))                # new (tag, size)
for a in (0x1403fb5b0, 0x1403fb730, 0x1403fb710, 0x141794410, 0x140227930):                      # free, scope, dtor, sized delete
    hook(a, lambda uc: ret_from(uc, 0))

watch = {}


def on_write(uc, acc, addr, size, val, ud):
    for a, n in allocs:
        if a <= addr < ((a + n + 0xfff) & ~0xfff) + 0x1000 and addr + size > a + n:
            raise SystemExit("WRITE PAST THE ALLOCATION: %x (+0x%x, size 0x%x) at rip %x"
                             % (addr, addr - a, n, uc.reg_read(UC_X86_REG_RIP)))
mu.hook_add(UC_HOOK_MEM_WRITE, on_write, begin=HEAP, end=HEAP + 0x4000000)


def call(fn, rcx=0, rdx=0, r8=0, r9=0):
    rsp = STACK + 0x80000
    mu.mem_write(rsp, struct.pack("<Q", RET))
    mu.reg_write(UC_X86_REG_RSP, rsp)
    for r, v in ((UC_X86_REG_RCX, rcx), (UC_X86_REG_RDX, rdx), (UC_X86_REG_R8, r8), (UC_X86_REG_R9, r9)):
        mu.reg_write(r, v)
    mu.emu_start(fn, RET, count=2_000_000_000)
    return mu.reg_read(UC_X86_REG_RAX)


def canary_ok(a, n):
    end = ((a + n + 0xfff) & ~0xfff) + 0x1000
    return bytes(mu.mem_read(a + n, end - (a + n))) == b"\xee" * (end - (a + n))


def rec(i):                                   # the i-th file record: id, 56 bytes
    rid = 1000 + 7 * i
    return rid, struct.pack("<I", rid) + bytes(((i * 31 + k * 7) & 0xff) for k in range(56))


ok = True
def check(cond, what):
    global ok
    print("  %-4s %s" % ("ok" if cond else "FAIL", what))
    ok = ok and cond

# 1. constructor
obj = alloc(SIZE)
call(0x1414bce10, obj)
check(rd16(obj + CNT1) == 0 and rd16(obj + CNT2) == 0, "constructor: both counts 0")
check(canary_ok(obj, SIZE), "constructor: nothing written past 0x%x" % SIZE)

# 2. load N records
n = NREC
buf = alloc(n * 60)
mu.mem_write(buf, b"".join(rec(i)[1] for i in range(n)))
call(0x1414bd7a0, obj, buf, n * 60)
want = min(n, CAP - 1)
cnt = rd16(obj + CNT2)
check(cnt == want, "load of %d records: count %d (expected %d)" % (n, cnt, want))
bad = 0
for i in range(want):
    rid, r = rec(i)
    e = bytes(mu.mem_read(obj + TAB + i * 0x48, 0x48))
    if struct.unpack_from("<I", e)[0] != rid or e[0xc:0xc + 56] != r[4:]:
        bad += 1
check(bad == 0, "load: all %d records in place, id and 56 bytes (%d wrong)" % (want, bad))
check(canary_ok(obj, SIZE), "load: nothing written past the object")

# 3. lookups
for i in (0, 30022, 30023, 30024, want // 2, want - 1):
    if i >= want:
        continue
    rid, r = rec(i)
    p = call(0x1414bd220, obj, rid << 32)
    check(p == obj + TAB + i * 0x48, "lookup id %d (record %d) -> %s" % (rid, i, "found" if p else "0"))
p = call(0x1414bd220, obj, (rec(want - 1)[0] + 1) << 32)
check(p == 0, "lookup of an id that is not there -> 0")
out = alloc(0x48)
i = want - 1
al = call(0x1414bd160, obj, out, rec(i)[0] << 32) & 0xff
check(al == 1 and bytes(mu.mem_read(out + 0xc, 56)) == rec(i)[1][4:], "copy-out lookup of the last record")

# 4. insert a new id in the middle (only room for it if the load left room)
if want < CAP - 1:
    newid = rec(want // 2)[0] + 3
    src = alloc(0x48)
    mu.mem_write(src, struct.pack("<I", newid) + b"\0" * 8 + b"\x5a" * 56 + b"\0" * 4)
    call(0x1414bd5c0, obj, src)
    check(rd16(obj + CNT2) == want + 1, "insert id %d: count %d" % (newid, rd16(obj + CNT2)))
    p = call(0x1414bd220, obj, newid << 32)
    ids = [rd32(obj + TAB + k * 0x48) for k in range(want + 1)]
    check(p == obj + TAB + (want // 2 + 1) * 0x48 and ids == sorted(ids), "insert: found at its place, order kept")
    # 5. remove it again
    call(0x1414bce50, obj, newid << 32)
    ids = [rd32(obj + TAB + k * 0x48) for k in range(want)]
    check(rd16(obj + CNT2) == want and ids == [rec(k)[0] for k in range(want)], "remove id %d: count back to %d, order kept" % (newid, want))
    check(canary_ok(obj, SIZE), "insert/remove: nothing written past the object")

# 6. backup and restore through a fake owner
mu.mem_write(OWNER, b"\0" * 0x1000)
mu.mem_write(OWNER + 0x60, struct.pack("<Q", obj))
before = bytes(mu.mem_read(obj, SIZE))
call(0x1414b7170, OWNER)
bk = struct.unpack("<Q", mu.mem_read(OWNER + 0x88, 8))[0]
check(bk != 0 and [n for a, n in allocs if a == bk] == [SIZE], "backup: allocated with the new size")
check(bytes(mu.mem_read(bk, SIZE)) == before, "backup: the whole object copied, counts included")
check(canary_ok(bk, SIZE), "backup: nothing written past it")
mu.mem_write(obj + TAB, b"\x77" * 0x48 * 4)
mu.mem_write(obj + CNT2, b"\x01\x00")
call(0x1414b6df0, OWNER)
check(bytes(mu.mem_read(obj, SIZE)) == before, "restore: the object is back, byte for byte")
check(canary_ok(obj, SIZE), "restore: nothing written past the object")

# 7. more records than the cap
n2 = CAP + 500
obj2 = alloc(SIZE)
call(0x1414bce10, obj2)
buf2 = alloc(n2 * 60)
mu.mem_write(buf2, b"".join(rec(i)[1] for i in range(n2)))
call(0x1414bd7a0, obj2, buf2, n2 * 60)
check(rd16(obj2 + CNT2) == CAP - 1, "load of %d records: clamped at %d" % (n2, rd16(obj2 + CNT2)))
check(canary_ok(obj2, SIZE), "over-long load: nothing written past the object")

print("ALL OK" if ok else "FAILED")
sys.exit(0 if ok else 1)
