r"""python vecscan.py [N] [--elem lo,hi] [--dword] -> every live vector whose capacity is exactly N

The 1,536-club wall is not a number in the executable. Three scans have said so: no array is
bounded at 1536 with any stride, `cmp reg, 0x600` appears twice and both are message-code
switches, and `mov r32, 0x600` never counts clubs (docs/bounded-arrays.md). What is left is
the hypothesis the crash sites have always pointed at -- a runtime structure with 1,536 slots
that nothing ever compares against, so a club above it simply has no record and every reader
gets rubbish.

A structure like that leaves no constant in the file, but it cannot hide in the running
process, because this engine is MSVC C++ and an MSVC vector is three pointers:

    [first] [last] [end of storage]

so its capacity is `(end - first) / element size` -- written nowhere, but computable from any
triple. This walks every committed, writable region of the live process and reports each
triple whose capacity works out to exactly N for some plausible element size. No debugger is
attached (this exe kills itself under one: see docs/findings.md, "the exe notices a
debugger"); it only opens the process for reading, the same way livedump.py does.

    python vecscan.py                 vectors whose capacity is exactly 1536
    python vecscan.py 750             the shipped club cap, as a control -- these should
                                      be real tables, which is how to read the output of the
                                      1536 run: same shapes, different number
    python vecscan.py 1536 --dword    also every plain dword 1536 that sits next to a pointer,
                                      for a capacity kept as a field rather than a pointer
    python vecscan.py --used 1523     the other way round, and the better question: every
                                      vector holding exactly as many records as the world has
                                      clubs, whatever its capacity. `blockstat.py` says what
                                      that number is. One of them holding 1523 of 1536 would
                                      be the answer outright.

What to do with a hit: note its element size and count, then read the memory at `first` with
livedump.py. If the entries look like clubs -- a name, a packed id, something recognisable --
that is the table the wall is made of, and raising it is a different job from raising a cap,
because there is no constant to patch: the allocation is sized at runtime and the size has to
be followed back to whatever computes it.

Needs the game running with a season loaded; reads memory and writes nothing.
"""
import ctypes
import ctypes.wintypes as w
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import livedump as L

k32 = ctypes.WinDLL("kernel32", use_last_error=True)

MEM_COMMIT = 0x1000
PAGE_READWRITE = 0x04
PAGE_WRITECOPY = 0x08
PAGE_EXECUTE_READWRITE = 0x40
PAGE_GUARD = 0x100
WRITABLE = (PAGE_READWRITE, PAGE_WRITECOPY, PAGE_EXECUTE_READWRITE)

USER_LO, USER_HI = 0x10000, 0x7FFFFFFFFFFF


class MEMORY_BASIC_INFORMATION64(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_ulonglong),
                ("AllocationBase", ctypes.c_ulonglong),
                ("AllocationProtect", w.DWORD),
                ("__alignment1", w.DWORD),
                ("RegionSize", ctypes.c_ulonglong),
                ("State", w.DWORD), ("Protect", w.DWORD), ("Type", w.DWORD),
                ("__alignment2", w.DWORD)]


def regions(h):
    """Every committed, writable, non-guard region of the process."""
    mbi = MEMORY_BASIC_INFORMATION64()
    addr = 0x10000
    out = []
    while addr < USER_HI:
        got = k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi),
                                 ctypes.sizeof(mbi))
        if not got:
            addr += 0x1000
            if addr > 0x7FFFFFFF0000:
                break
            continue
        if (mbi.State == MEM_COMMIT and mbi.Protect in WRITABLE
                and not (mbi.Protect & PAGE_GUARD)):
            out.append((mbi.BaseAddress, mbi.RegionSize))
        if not mbi.RegionSize:
            break
        addr = mbi.BaseAddress + mbi.RegionSize
    return out


def scan(m, base, size, n, elo, ehi, want_dword, by_used=False):
    """Triples in one region whose capacity (or, with by_used, whose length) is n."""
    buf = None
    try:
        buf = m.read(base, size)
    except Exception:
        pass
    if buf is None:                      # a region can go away between the query and the read
        return [], []
    triples, fields = [], []
    q = struct.unpack_from("<%dQ" % (len(buf) // 8), buf, 0)
    for i in range(len(q) - 2):
        a, b, c = q[i], q[i + 1], q[i + 2]
        if not (USER_LO < a <= b <= c < USER_HI):
            continue
        span = (b - a) if by_used else (c - a)
        if span == 0 or span % n:
            continue
        elem = span // n
        if not (elo <= elem <= ehi):
            continue
        if (b - a) % elem or (c - a) % elem:
            continue
        triples.append((base + i * 8, a, b, c, elem, (b - a) // elem))
    if want_dword:
        for o in range(0, len(buf) - 12, 4):
            if struct.unpack_from("<I", buf, o)[0] != n:
                continue
            # a capacity is kept beside the pointer it belongs to
            for d in (-8, 4, 8):
                p = o + d
                if 0 <= p <= len(buf) - 8:
                    v = struct.unpack_from("<Q", buf, p)[0]
                    if USER_LO < v < USER_HI and v % 8 == 0:
                        fields.append((base + o, d, v))
                        break
    return triples, fields


def selftest():
    """Plant one vector of 1536 records of 0x28 in a buffer of noise and find it again."""
    import random
    random.seed(7)
    first = 0x2000000000
    elem, n = 0x28, 1536
    words = [random.getrandbits(64) for _ in range(4096)]
    at = 1000
    words[at:at + 3] = [first, first + 700 * elem, first + n * elem]
    buf = struct.pack("<%dQ" % len(words), *words)

    class Fake:
        def read(self, base, size):
            return buf

    t, _ = scan(Fake(), 0x1000000, len(buf), n, 2, 0x2000, False)
    u, _ = scan(Fake(), 0x1000000, len(buf), 700, 2, 0x2000, False, by_used=True)
    print("self-test: --used 700 finds %d, %d of them the planted one"
          % (len(u), len([x for x in u if x[1] == first])))
    hit = [x for x in t if x[1] == first]
    print("self-test: %d triple(s), %d of them the planted one%s"
          % (len(t), len(hit), "" if hit else " -- FAILED"))
    if hit:
        _, a, b, c, e, used = hit[0]
        print("  elem 0x%x, used %d of %d" % (e, used, (c - a) // e))
    return 0 if hit else 1


def main():
    if "--selftest" in sys.argv:
        return selftest()

    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    n = int(args[0]) if args else 1536
    elo, ehi = 2, 0x2000
    if "--elem" in sys.argv:
        elo, ehi = (int(x, 0) for x in sys.argv[sys.argv.index("--elem") + 1].split(","))
    want_dword = "--dword" in sys.argv
    by_used = "--used" in sys.argv
    if by_used:
        n = int(sys.argv[sys.argv.index("--used") + 1])

    pid = L.find_pid()
    if not pid:
        raise SystemExit("FL_2026.exe is not running -- this reads the live process")
    m = L.Mem(pid)
    rs = regions(m.h)
    total = sum(r[1] for r in rs)
    print("pid %d: %d committed writable region(s), %.1f MB, looking for %s %d"
          % (pid, len(rs), total / 1048576.0, "a length of" if by_used else "capacity", n))

    triples, fields = [], []
    for base, size in rs:
        t, f = scan(m, base, size, n, elo, ehi, want_dword, by_used)
        triples += t
        fields += f

    print("%d vector(s) with %s exactly %d:"
          % (len(triples), "a length of" if by_used else "capacity", n))
    for at, a, b, c, elem, used in sorted(triples, key=lambda x: -x[4]):
        print("  at 0x%x  first 0x%x  elem 0x%x  used %d of %d  (0x%x bytes)"
              % (at, a, elem, used, (c - a) // elem, c - a))
    if want_dword:
        print("%d dword(s) equal to %d next to a pointer:" % (len(fields), n))
        for at, d, v in fields[:200]:
            print("  at 0x%x  pointer at %+d -> 0x%x" % (at, d, v))
        if len(fields) > 200:
            print("  ... and %d more" % (len(fields) - 200))
    m.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
