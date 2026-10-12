"""Tests of the two-row Nordeste runtime (pure exports, no game): fixtures, quarter-finals, tie-break."""
import ctypes, itertools, random
from pathlib import Path

DLL = Path(__file__).resolve().parent.parent / "native" / "fl26swiss.dll"   # build-swiss.sh
d = ctypes.CDLL(str(DLL))
U16, U32 = ctypes.c_uint16, ctypes.c_uint32
d.fl26_nd_engine_config.argtypes = [ctypes.POINTER(U16), ctypes.POINTER(U32), ctypes.POINTER(U16)]
d.fl26_nd_fixture.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.POINTER(U32), ctypes.POINTER(U32), ctypes.POINTER(U32)]

class Match(ctypes.Structure):
    _fields_ = [("home", U32), ("away", U32), ("reg", U16), ("hg", ctypes.c_uint8), ("ag", ctypes.c_uint8), ("played", ctypes.c_uint8)]

class Stat(ctypes.Structure):
    _fields_ = [("played", ctypes.c_int), ("points", ctypes.c_int), ("wins", ctypes.c_int), ("gd", ctypes.c_int), ("gf", ctypes.c_int)]

d.fl26_nd_quarters.argtypes = [ctypes.POINTER(Match), ctypes.c_uint, ctypes.POINTER(U32)]
d.fl26_nd_stats.argtypes = [ctypes.POINTER(Match), ctypes.c_uint, ctypes.POINTER(Stat), ctypes.c_int]

G = 560
CLUBS = [101 + i for i in range(20)]           # A 101-105, B 106-110, C 111-115, D 116-120
ok = d.fl26_nd_engine_config((U16 * 3)(600, G, 601), (U32 * 20)(*CLUBS), (U16 * 10)(83, 86, 97, 104, 118, 125, 139, 146, 153, 157))
assert ok == 1, "config"
fails = 0
def check(cond, what):
    global fails
    print(("ok   " if cond else "FAIL ") + what)
    if not cond: fails += 1

def fixtures():
    out = []
    for row in (0, 1):
        for k in range(25):
            r, h, a = U32(), U32(), U32()
            assert d.fl26_nd_fixture(row, k, ctypes.byref(r), ctypes.byref(h), ctypes.byref(a))
            out.append((row, r.value, h.value, a.value))
    return out

F = fixtures()
grp = lambda i: i // 5
check(len(F) == 50 and len({(h, a) for _, _, h, a in F}) == 50, "50 matches, none repeated")
check(all({grp(h), grp(a)} in ({0, 1}, {2, 3}) for _, _, h, a in F), "only A v B and C v D")
check(all(sum(1 for _, _, h, a in F if c in (h, a)) == 5 for c in range(20)), "five matches a club")
check(all(len({c for _, rr, h, a in F if rr == r for c in (h, a)}) == 20 for r in range(5)), "every club once a round")
homes = [sum(1 for _, _, h, _ in F if h == c) for c in range(20)]
check(all(homes[c] == (3 if grp(c) in (0, 2) else 2) for c in range(20)), "A and C at home three times, B and D twice")
pairs = {(min(h, a), max(h, a)) for _, _, h, a in F}
check(pairs == {(a, b) for a in range(0, 5) for b in range(5, 10)} | {(a, b) for a in range(10, 15) for b in range(15, 20)},
      "every A plays every B, every C every D")

def season(results):
    ms = [Match(CLUBS[h], CLUBS[a], G + 1024 * (row + 1), hg, ag, 1) for (row, r, h, a), (hg, ag) in zip(F, results)]
    return (Match * len(ms))(*ms), len(ms)

rnd = random.Random(7)
for trial in range(200):
    res = [(rnd.randint(0, 3), rnd.randint(0, 3)) for _ in F]
    ms, n = season(res)
    out = (U32 * 8)()
    assert d.fl26_nd_quarters(ms, n, out) == 1
    out2 = (U32 * 8)()
    assert d.fl26_nd_quarters(ms, n, out2) == 1 and list(out) == list(out2)
    # reference ranking in Python (points, wins, gd, gf; equal -> the DLL's draw decides, checked below)
    st = (Stat * 20)()
    assert d.fl26_nd_stats(ms, n, st, 1) == 1
    key = lambda c: (st[c].points, st[c].wins, st[c].gd, st[c].gf)
    ranks = []
    for g in range(4):
        order = sorted(range(g * 5, g * 5 + 5), key=key, reverse=True)
        ranks.append(order)
    q = list(out)
    for k, (g1, g2) in enumerate(((0, 2), (1, 3), (2, 0), (3, 1))):
        first, second = CLUBS.index(q[2 * k]), CLUBS.index(q[2 * k + 1])
        if key(ranks[g1][0]) != key(ranks[g1][1]):
            assert first == ranks[g1][0], (trial, k)
        if len({key(c) for c in ranks[g2][:3]}) == 3:
            assert second == ranks[g2][1], (trial, k)
        assert grp(first) == g1 and grp(second) == g2
check(True, "200 random seasons: quarter-finals A1-C2, B1-D2, C1-A2, D1-B2, the same answer twice")

# a group where everything is level: the draw must still decide, and the same way twice
res = [(1, 1)] * 50
ms, n = season(res)
out = (U32 * 8)(); out2 = (U32 * 8)()
check(d.fl26_nd_quarters(ms, n, out) == 1 and d.fl26_nd_quarters(ms, n, out2) == 1 and list(out) == list(out2),
      "all level: decided by the draw, never blocked, reproducible")
# an unplayed match: no quarter-finals yet
ms2 = (Match * 50)(*[Match(m.home, m.away, m.reg, m.hg, m.ag, m.played) for m in ms]); ms2[3].played = 0
check(d.fl26_nd_quarters(ms2, 50, (U32 * 8)()) == 0, "a group match unplayed: no quarter-finals")
# a match that is not in the schedule (wrong row): refused
ms3 = (Match * 50)(*[Match(m.home, m.away, m.reg, m.hg, m.ag, m.played) for m in ms]); ms3[0].reg = G + 2048
check(d.fl26_nd_quarters(ms3, 50, (U32 * 8)()) == 0, "a match outside the schedule: refused")
# the knockout's entry list: quarter-finals 1, 4, 2, 3 (semi-finals 1 v 4, 2 v 3)
d.fl26_nd_bracket.argtypes = [ctypes.POINTER(U32), ctypes.POINTER(U32)]
q = (U32 * 8)(*range(1, 9)); b = (U32 * 8)()
check(d.fl26_nd_bracket(q, b) == 1 and list(b) == [1, 2, 7, 8, 3, 4, 5, 6], "bracket order QF1, QF4, QF2, QF3")
# a table row as the game writes it (read live 2026-10-12, reg 51 row 4: 2 won 1 drawn, 6-1, 7 points;
# byte 11 is the fourth six-bit count, which is not written)
d.fl26_nd_row.argtypes = [ctypes.c_char_p, U32, ctypes.c_uint, ctypes.POINTER(Stat)]
row = ctypes.create_string_buffer(20)
d.fl26_nd_row(row, 0x059a80cc, 4, ctypes.byref(Stat(3, 7, 2, 5, 6)))
live = bytes.fromhex("cc809a0504000000070210" + "0c" + "06100003" + "02000000")
got = row.raw
check(got[:11] == live[:11] and got[12:16] == live[12:16] and got[11] == 0, "table row packing matches the game's")
d.fl26_nd_row(row, 0x0410c0d7, 1, ctypes.byref(Stat(3, 9, 3, 7, 7)))
live = bytes.fromhex("d7c01004010000000903000c0700000301000000")
check(row.raw[:11] == live[:11] and row.raw[12:16] == live[12:16], "table row: 3 won, 7-0")
print("FAILED %d" % fails if fails else "all passed")
