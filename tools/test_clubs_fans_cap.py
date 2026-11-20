r"""python tools/test_clubs_fans_cap.py [<fl26clubs.dll>]

fl26clubs.dll took at most 4096 of a world's "fans" lines (League Builder: one per new club and per
club of the game with no money of its own). A world with more new clubs than that (4277 in a
league pack of 07.11.2026) lost the rest without a word: those clubs, out of the game's club
ranking, counted as its top class again -- x40 followers and the top broadcasting fee (B298). The
table now holds 16384. Here 6000 rows go in and all 6000 must be taken; a bad row (class 10, share
0, team 0) is still left out. Windows only (loads the DLL); nothing is installed in any game.
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
f = d.fl26_clubs_fans
f.argtypes, f.restype = [ctypes.POINTER(ctypes.c_uint32), ctypes.c_int], ctypes.c_int


def take(rows):
    arr = (ctypes.c_uint32 * (2 * len(rows)))(*[v for t, c, p in rows for v in (t, c << 8 | p)])
    return f(arr, len(rows))


big = [(200000 + k, k % 10, 5 + k % 96) for k in range(6000)]
ok("6000 followers lines all taken", take(big) == 6000)
ok("a full table of 16384", take([(100000 + k, 3, 40) for k in range(16384)]) == 16384)
ok("bad rows left out", take([(1, 10, 50), (2, 3, 0), (0, 3, 50), (3, 9, 100)]) == 1)
print("all %d passed" % N)
