r"""python tools/test_clubs_fansx.py [<fl26clubs.dll>]

A finer followers share and the season's income by it (11.11.2026, FL 2027 worlds). A whole percent
with a floor of 1,000 left half of a big world's clubs on one followers figure, and every club out
of the game's ranking was paid like its 450th club: a second-division side with wages of EUR 1.4M
got EUR 4.1M a season. The world's "fansx <share of 10,000> <ids>" lines give a listed club a finer
share (base down to 100), and its broadcasting fee and sponsors are scaled by it -- never below
what its wages need.

Here: the rows fl26_clubs_fans2 takes, the base fans_post answers, and the sum of a payment
(fl26_clubs_pay) with the figures measured in the game. Windows only (loads the DLL); no game.
"""
import ctypes, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DLL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "native", "fl26clubs.dll")
N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


if os.name != "nt":
    print("skip - Windows only")
    sys.exit(0)
d = ctypes.CDLL(DLL)
U32P = ctypes.POINTER(ctypes.c_uint32)
d.fl26_clubs_fans.argtypes, d.fl26_clubs_fans.restype = [U32P, ctypes.c_int], ctypes.c_int
d.fl26_clubs_fans2.argtypes, d.fl26_clubs_fans2.restype = [U32P, ctypes.c_int], ctypes.c_int
d.fans_post.argtypes, d.fans_post.restype = [ctypes.c_uint32, ctypes.c_int], ctypes.c_int
d.fl26_clubs_pay.argtypes, d.fl26_clubs_pay.restype = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint32], ctypes.c_int


def fans(rows):
    arr = (ctypes.c_uint32 * (2 * len(rows)))(*[v for t, c, p in rows for v in (t, c << 8 | p)])
    return d.fl26_clubs_fans(arr, len(rows))


def fans2(rows):
    arr = (ctypes.c_uint32 * (2 * len(rows)))(*[v for t, sh in rows for v in (t, sh)])
    return d.fl26_clubs_fans2(arr, len(rows))


base = lambda tid, b: d.fans_post(tid << 14, b)
A, B, C, D = 75633, 75634, 75635, 75636
ok("four fans lines", fans([(A, 0, 6), (B, 0, 5), (C, 0, 1), (D, 3, 100)]) == 4)
ok("the whole percent and its floor of 1,000, as before", (base(A, 22983), base(B, 22983), base(C, 22983)) == (1378, 1149, 1000))
ok("a club with the whole share keeps its base", base(D, 150000) == 150000)
ok("a club with no line keeps its base", base(1234, 22983) == 22983)
ok("fansx rows: a club with no fans line, a share of 0 and one above 10,000 are left out",
   fans2([(A, 600), (B, 266), (C, 40), (99999, 500), (D, 0), (D, 10001)]) == 3)
ok("the finer share: %s" % [base(t, 22983) for t in (A, B, C)], (base(A, 22983), base(B, 22983), base(C, 22983)) == (1378, 611, 100))
ok("its floor is 100", base(C, 10000) == 100 and base(C, 100000) == 400)
ok("fans lines read again drop the finer shares", fans([(A, 0, 6), (C, 0, 1)]) == 2 and base(C, 22983) == 1000)

pay = d.fl26_clubs_pay
# measured 11.11.: Andranik FC Sevan, salary budget 14,380, broadcasting 10,900 and sponsors 30,670, share 600
tv, sp = pay(10900, 30670, 14380, 600), pay(30670, 10900, 14380, 600)
ok("the game's figures: broadcasting 10900 -> %d, sponsors 30670 -> %d" % (tv, sp), (tv, sp) == (4623, 13008))
need = 14380 * 112 // 100
ok("the two together: what the wages need and the share of the rest", abs(tv + sp - (need + (41570 - need) * 600 // 10000)) <= 1)
ok("never below what the wages need", pay(10000, 30670, 14380, 1) + pay(30670, 10000, 14380, 1) >= need - 1)
ok("a club whose wages take it all keeps the game's payment", pay(10000, 30670, 40000, 600) == 10000)
ok("no salary budget: the game's payment", pay(10000, 30670, 0, 600) == 10000)
ok("the whole share: the game's payment", pay(10000, 30670, 14380, 10000) == 10000)
ok("a bigger share pays more", pay(10000, 30670, 14380, 600) < pay(10000, 30670, 14380, 4000) < 10000)
ok("a payment is never nothing", pay(1, 5000000, 10, 1) == 1)
print("all %d passed" % N)
