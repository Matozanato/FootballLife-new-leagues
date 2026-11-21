r"""python test_standings.py  -> the standings step (standings.py) run on the exe's own code

Needs the exe (FL26_EXE, FL_2027.exe or FL26 2.2: the standings code is the same), capstone,
keystone and unicorn.  Nothing is written anywhere but memory.

The copier 0x1413fb0b0 is run, patched, in unicorn over a live object laid out the way the step
lays it out (header of N, T tables at 0x3a2ef0) and over copy slots:

  * copy A save (live -> A, through the stub) puts the header at +0 and every one of the T
    tables at the compact base, writes nothing past them, and clears the flag;
  * copy A load (A -> a second live object) gives back every byte the copier copies;
  * copy B (the plain call) takes the first tables that fit the 0x39a8f0 slot and writes
    nothing past +0x39a5f0;
  * the allocator 0x14158f350 scans all T tables: with every table but the last one taken it
    returns T - 1, with all taken -1;
  * the three numbers fl26swiss and fl26join read from the patched code (table base, table
    count, header count) come out as the step planned, in the shapes those readers accept, and
    the FL 2027 copy of fl26hdr255 sees the condition it stands down on.
"""
import os, random, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

FAILS = []


def ok(what, cond):
    print("%s  %s" % ("ok  " if cond else "FAIL", what))
    if not cond:
        FAILS.append(what)


def main():
    try:
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_MEM_WRITE
        from unicorn.x86_const import (UC_X86_REG_RSP, UC_X86_REG_RCX, UC_X86_REG_RDX,
                                       UC_X86_REG_RAX, UC_X86_REG_R8, UC_X86_REG_R9)
    except ImportError:
        print("skip: no unicorn")
        return 0
    import calwiden, standings as S

    exe = calwiden.Exe()
    T, N = S.DEFAULT_T, S.DEFAULT_N
    ps = S.patches(exe.read, T, N)
    CB, NB = S.compact_base(N), S.slot_tables(N)

    TRACE, TRACE_N = 0x140001000, 0x252D800
    mu = Uc(UC_ARCH_X86, UC_MODE_64)
    mu.mem_map(TRACE & ~0xFFF, (TRACE_N + 0x1FFF) & ~0xFFF)
    mu.mem_write(TRACE, bytes(exe.read(TRACE, TRACE_N)))
    page = S.OWNER & ~0xFFF
    mu.mem_map(page, 0x1000)
    mu.mem_map(S.CAVE, 0x1000)
    for p in ps:
        va, old, new = int(p["va"], 16), bytes.fromhex(p["old"]), bytes.fromhex(p["new"])
        if bytes(mu.mem_read(va, len(old))) != old:
            raise SystemExit("%s: not the shipped bytes" % p["va"])
        mu.mem_write(va, new)

    OWN = 0x200000000
    LIVE, LIVE2 = 0x210000000, 0x230000000
    A, B = 0x250000000, 0x270000000
    size = S.TOP + T * S.STRIDE
    a_len = CB + T * S.STRIDE
    for base, n in ((OWN, 0x1000), (LIVE, size), (LIVE2, size), (A, a_len), (B, S.SLOT)):
        mu.mem_map(base, (n + 0x10FFF) & ~0xFFF)          # 64 KB of guard behind each
    STACK, RET = 0x2A0000000, 0x2B0000000
    mu.mem_map(STACK, 0x10000)
    mu.mem_map(RET, 0x1000)
    mu.mem_write(RET, b"\xf4")
    mu.mem_write(S.OWNER, struct.pack("<Q", OWN))

    def set_live(obj):
        mu.mem_write(OWN + 0x78, struct.pack("<Q", obj))

    def call(fn, rcx, rdx=0, r8=0, r9=0, until=RET):
        rsp = STACK + 0x8000
        mu.mem_write(rsp, struct.pack("<Q", RET))
        for r, v in ((UC_X86_REG_RSP, rsp), (UC_X86_REG_RCX, rcx), (UC_X86_REG_RDX, rdx),
                     (UC_X86_REG_R8, r8), (UC_X86_REG_R9, r9)):
            mu.reg_write(r, v)
        mu.emu_start(fn, until, count=200_000_000)
        return mu.reg_read(UC_X86_REG_RAX)

    writes = []
    mu.hook_add(UC_HOOK_MEM_WRITE, lambda uc, acc, addr, sz, val, ud: writes.append((addr, sz)),
                begin=A, end=B + S.SLOT + 0x10000)

    rnd = random.Random(26)
    hdr = bytes(rnd.getrandbits(8) for _ in range(N * S.HDR))
    mu.mem_write(LIVE, hdr)
    # every table: random bytes, its index in the id word and the year word
    for i in range(T):
        t = bytearray(rnd.getrandbits(8) for _ in range(64)) * (S.STRIDE // 64 + 1)
        t = t[: S.STRIDE]
        t[0:4] = struct.pack("<HH", i, 2000 + i % 7)
        mu.mem_write(LIVE + S.TOP + i * S.STRIDE, bytes(t))

    # copy A save: live -> A through the stub
    set_live(LIVE)
    del writes[:]
    call(S.CAVE_STUB_A, A, LIVE)
    ok("copy A save: the flag is clear afterwards", bytes(mu.mem_read(S.CAVE_FLAG, 1)) == b"\0")
    ok("copy A save: the header is copied whole (%d entries)" % N, bytes(mu.mem_read(A, N * S.HDR)) == hdr)
    ids = [struct.unpack("<HH", bytes(mu.mem_read(A + CB + i * S.STRIDE, 4))) for i in range(T)]
    ok("copy A save: all %d tables at the compact base +0x%x, in order" % (T, CB),
       all(ids[i] == (i, 2000 + i % 7) for i in range(T)))
    hi = max(a + s for a, s in writes) if writes else 0
    ok("copy A save: nothing written past the last table (+0x%x of +0x%x)" % (hi - A, a_len),
       writes and min(a for a, _ in writes) >= A and hi <= A + a_len)
    ok("copy A save: the slot grows by 0x%x, enough for it" % S.slot_growth(T, N),
       S.SLOT + S.slot_growth(T, N) >= a_len and S.slot_growth(T, N) % 0x40 == 0)

    # copy A load: A -> a zeroed second live object
    set_live(LIVE2)
    call(S.CAVE_STUB_A, LIVE2, A)
    ok("copy A load: the header comes back", bytes(mu.mem_read(LIVE2, N * S.HDR)) == hdr)
    same = True
    for i in range(T):
        src = bytes(mu.mem_read(LIVE + S.TOP + i * S.STRIDE, S.STRIDE))
        got = bytes(mu.mem_read(LIVE2 + S.TOP + i * S.STRIDE, S.STRIDE))
        if got[:4] != src[:4] or any(g not in (0, s) for g, s in zip(got, src)):
            same = False
            break
    ok("copy A load: every table back at +0x%x, each byte the copier copies equal" % S.TOP, same)
    ok("copy A load: the old pool area stays untouched (zero)",
       not any(mu.mem_read(LIVE2 + CB, 0x10000)) and not any(mu.mem_read(LIVE2 + 0x390000, 0x8000)))

    # copy B: the plain call, live -> B
    set_live(LIVE)
    del writes[:]
    call(S.COPIER, B, LIVE)
    hi = max(a + s for a, s in writes) if writes else 0
    ok("copy B save: %d tables, nothing written past +0x39a5f0 (last +0x%x)" % (NB, hi - B),
       writes and min(a for a, _ in writes) >= B and hi <= B + S.SLOT_TABLES_END)
    ids = [struct.unpack("<H", bytes(mu.mem_read(B + CB + i * S.STRIDE, 2)))[0] for i in range(NB)]
    ok("copy B save: tables 0..%d at the compact base" % (NB - 1), ids == list(range(NB)))
    ok("copy B: the flag stays clear", bytes(mu.mem_read(S.CAVE_FLAG, 1)) == b"\0")

    # the allocator: first free table of T
    ALLOC = 0x14158F350
    set_live(LIVE2)
    for i in range(T):
        mu.mem_write(LIVE2 + S.TOP + i * S.STRIDE, struct.pack("<HH", 5, 2030))
    mu.mem_write(LIVE2 + S.TOP + (T - 1) * S.STRIDE, struct.pack("<I", 0xFFFFFFFF))
    mu.mem_write(OWN + 0x100, struct.pack("<IH", 0, 2031))     # the year at +4 of rdx
    # stopped at its call of the table's clear 0x1414ff000 (which reads globals not mapped here):
    # rcx is the table found, ebx its index
    call(ALLOC, 77, OWN + 0x100, until=0x1414FF000)
    from unicorn.x86_const import UC_X86_REG_RBX
    r = mu.reg_read(UC_X86_REG_RBX) & 0xFFFFFFFF
    ok("allocator: with all but the last taken it takes %d (got %d)" % (T - 1, r),
       r == T - 1 and mu.reg_read(UC_X86_REG_RCX) == LIVE2 + S.TOP + (T - 1) * S.STRIDE)
    ok("allocator: and stamps it (id 77, 2031)",
       struct.unpack("<HH", bytes(mu.mem_read(LIVE2 + S.TOP + (T - 1) * S.STRIDE, 4))) == (77, 2031))
    r = call(ALLOC, 78, OWN + 0x100) & 0xFFFFFFFF
    ok("allocator: with all %d taken it returns -1 (got 0x%x)" % (T, r), r == 0xFFFFFFFF)

    # what the DLLs read
    rd = lambda va, n: bytes(mu.mem_read(va, n))
    lea, cmp_, mov = rd(0x14158DF91, 7), rd(0x14158F381, 6), rd(0x1414FD4E3, 6)
    base = struct.unpack("<I", lea[3:])[0]
    cnt = struct.unpack("<I", cmp_[2:])[0]
    nh = struct.unpack("<I", mov[2:])[0]
    shapes = lea[:3] == b"\x49\x8d\x82" and cmp_[:2] == b"\x81\xfb" and mov[:2] == b"\x41\xb9"
    ok("fl26swiss/fl26join: the shapes they check (lea 49 8d 82, cmp 81 fb, mov 41 b9)", shapes)
    accept = (100 <= nh <= 4096 and 1 <= cnt <= 8192 and base >= nh * 0xB4
              and not (base + cnt * 0x187C > 0x39A8F0 and base < 0x3A2EF0))
    ok("fl26swiss/fl26join: base 0x%x, %d tables, %d entries -- accepted" % (base, cnt, nh),
       (base, cnt, nh) == (S.TOP, T, N) and accept)
    ok("fl26swiss table_pool_old_slots: the release function's lea names the same base",
       struct.unpack("<I", rd(0x14158F870 + 0x73, 4))[0] == base)
    ok("fl26hdr255.fl27: stands down (entries > 0xff, base >= 0x3a2ef0)", nh > 0xFF and base >= 0x3A2EF0)
    shipped = (struct.unpack("<I", exe.read(0x14158DF94, 4))[0], struct.unpack("<I", exe.read(0x14158F383, 4))[0],
               struct.unpack("<I", exe.read(0x1414FD4E5, 4))[0])
    ok("the shipped exe reads 0x4650 / 600 / 100 the same way", shipped == (0x4650, 600, 100))

    print("%d failed" % len(FAILS) if FAILS else "all passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
