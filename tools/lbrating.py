r"""the overall rating the game shows for a player (B53)

The game does not keep a player's rating: it works it out from his abilities each time, and that
is the number its squad screens show.  Mod Studio used to show the mean of a few abilities
instead (lbplayers.overall), which is close for some players and off by six or more for others:
a goalkeeper whose five GK abilities average 70 is a 64 in the game (LaraCroft, 15.10.).

Now this is the game's own formula, as TEditor (teditor.app, Antony Siu Ming, the PES 2020/2021
editor) works out its "Rating:" box (mato 07.11.2026: ratings in Mod Studio more precise).  The
weights fitted before were the game's number for 55 % of players and up to three off; this gives
the game's number for all 535 players of PES 2021's last data pack tried (pesmaster.com, every
position), and for the 26 of test_lbrating.py.

  position part P = round(( sum over the 20 outfield abilities (a - 25) * w
                            + (floor((GK Awareness + GK Reach) / 2) - 25) * wA
                            + (floor((GK Catching + GK Clearing + GK Reflexes) / 3) - 25) * wR
                            + Weak Foot Accuracy (0-3, playeredit's scale) * wW ) / 100)
  registered position: P + REG[pos]; a goalkeeper is that, an outfield player
      round(0.6 * (P + REG[pos]) + 0.4 * G), G the mean of the 22 (20 abilities, the two GK
      means) spread out by GENERAL -- so every ability moves an outfield rating a little
  another position: P + what an A / B there adds (PROF_A, B two less, C nothing)
  never under 40.  Form, Injury Resistance, Weak Foot Usage, age, skills: nothing.

TEditor has +12 for a mean of 74; the game has +11 (every one of 1621 such rows of pesmaster's).
LB/RB, LMF/RMF and LWF/RWF share a set of weights.

lbplayers.overall stays what Build measures squads with in FL26 (fill_level, at_level, NewLife's
levels): changing it would change the abilities every world gets. In FL 2027 Build measures and
sets them with this (lbplayers.level, EXACT; mato 07.11.2026).  This is what Mod Studio
shows, what the Rating box sets and what checkratings' rule A (90+) reads.
"""

import playeredit as E

# the 20 outfield abilities in the order of the weights below
OUTFIELD = [n for n, _b in E.ABILITIES if not n.startswith("GK ")]
GK_A = ("GK Awareness", "GK Reach")
GK_R = ("GK Catching", "GK Clearing", "GK Reflexes")
WFA = "Weak Foot Accuracy"
# every field rating() reads (for a reader that fetches only those)
FIELDS = ["Registered Position"] + OUTFIELD + list(GK_A) + list(GK_R) + [WFA]


def _w(gkA=0, gkR=0, wfa=0, **k):
    """({ability: weight}, (the GK Awareness/Reach mean's, the other three's, Weak Foot Accuracy's))"""
    out = {n: k.pop(n.replace(" ", "_"), 0) for n in OUTFIELD}
    assert not k, k
    return out, (gkA, gkR, wfa)


WEIGHTS = {
    "GK": _w(Jump=11, Physical_Contact=11, gkA=50, gkR=48),
    "CB": _w(Heading=22, Speed=10, Jump=19, Physical_Contact=19, Stamina=9, Defensive_Awareness=25,
             Ball_Winning=17, Aggression=8, wfa=23),
    "FB": _w(Offensive_Awareness=6, Ball_Control=9, Dribbling=9, Tight_Possession=5, Lofted_Pass=14,
             Speed=16, Acceleration=14, Jump=11, Physical_Contact=8, Balance=4, Stamina=14,
             Defensive_Awareness=14, Ball_Winning=8, Aggression=5, wfa=56),
    "DMF": _w(Offensive_Awareness=7, Ball_Control=18, Dribbling=10, Tight_Possession=5, Low_Pass=18,
              Lofted_Pass=19, Curl=12, Speed=3, Acceleration=3, Jump=5, Physical_Contact=9, Balance=4,
              Stamina=14, Defensive_Awareness=7, Ball_Winning=3, Aggression=1, wfa=23),
    "CMF": _w(Offensive_Awareness=5, Ball_Control=23, Dribbling=16, Tight_Possession=8, Low_Pass=23,
              Lofted_Pass=21, Speed=4, Acceleration=6, Physical_Contact=3, Balance=2, Stamina=17,
              Defensive_Awareness=3, wfa=23),
    "MF": _w(Offensive_Awareness=7, Ball_Control=15, Dribbling=17, Tight_Possession=8, Low_Pass=7,
             Lofted_Pass=12, Curl=4, Speed=24, Acceleration=21, Stamina=13, wfa=56),
    "AMF": _w(Offensive_Awareness=14, Ball_Control=23, Dribbling=17, Tight_Possession=7, Low_Pass=21,
              Lofted_Pass=14, Finishing=17, Speed=5, Acceleration=7, Physical_Contact=2, Balance=3,
              Stamina=3, wfa=37),
    "WF": _w(Offensive_Awareness=17, Ball_Control=19, Dribbling=15, Tight_Possession=7, Low_Pass=5,
             Lofted_Pass=9, Finishing=11, Speed=15, Acceleration=15, Kicking_Power=5, Physical_Contact=2,
             Balance=4, Stamina=6, wfa=47),
    "SS": _w(Offensive_Awareness=15, Ball_Control=19, Dribbling=13, Tight_Possession=6, Low_Pass=9,
             Lofted_Pass=9, Finishing=14, Speed=9, Acceleration=21, Kicking_Power=6, Physical_Contact=2,
             Balance=5, Stamina=4, wfa=37),
    "CF": _w(Offensive_Awareness=31, Ball_Control=23, Dribbling=9, Tight_Possession=5, Finishing=36,
             Heading=3, Speed=5, Acceleration=5, Kicking_Power=3, Jump=3, Physical_Contact=8, Balance=2,
             wfa=38),
}
KIND = {"GK": "GK", "CB": "CB", "LB": "FB", "RB": "FB", "DMF": "DMF", "CMF": "CMF", "LMF": "MF",
        "RMF": "MF", "AMF": "AMF", "LWF": "WF", "RWF": "WF", "SS": "SS", "CF": "CF"}
# what the registered position adds, and an A at another position (a B two less, a C nothing)
REG = {"GK": 8, "CB": 8, "LB": 9, "RB": 9, "DMF": 9, "CMF": 8, "LMF": 8, "RMF": 8, "AMF": 8,
       "LWF": 10, "RWF": 10, "SS": 9, "CF": 8}
PROF_A = {"GK": 5, "CB": 5, "LB": 4, "RB": 4, "DMF": 4, "CMF": 5, "LMF": 5, "RMF": 5, "AMF": 5,
          "LWF": 4, "RWF": 4, "SS": 5, "CF": 5}
# the general rating: the mean m of the 22, and what is added up to each m (78 and over: 14)
GENERAL = ((61, -9), (62, -6), (63, -4), (64, -2), (65, 0), (66, 1), (67, 3), (68, 5), (69, 6),
           (70, 7), (71, 8), (73, 10), (74, 11), (75, 12), (77, 13))


def _val(row, n):
    """a field the row does not have counts as the game's least: an ability 40, Weak Foot 0"""
    v = str(row.get(n, "")).strip()
    return int(v) if v.isdigit() else (0 if n == WFA else 40)


def _weights(pos):
    return WEIGHTS[KIND.get(pos, "CF")]


def _gk(row):
    return sum(_val(row, n) for n in GK_A) // 2, sum(_val(row, n) for n in GK_R) // 3


def position_part(row, pos):
    w, (wa, wr, ww) = _weights(pos)
    a, r = _gk(row)
    n = sum((_val(row, f) - 25) * k for f, k in w.items()) + (a - 25) * wa + (r - 25) * wr
    return (n + _val(row, WFA) * ww + 50) // 100


def general(row):
    a, r = _gk(row)
    m = ((sum(_val(row, n) for n in OUTFIELD) + a + r) * 100 // 22 + 50) // 100
    return m + next((add for top, add in GENERAL if m <= top), 14)


def rating(row, pos=None, prof=None):
    """the rating the game shows for the player of `row` (playeredit's CSV texts), at his
    registered position (a CF when the row has none), or at `pos` played as `prof` ("A", "B",
    anything else C)"""
    reg = row.get("Registered Position") or "CF"
    pos = pos or reg
    p = position_part(row, pos)
    if pos != reg:
        p += {"A": PROF_A.get(pos, 0), "B": PROF_A.get(pos, 0) - 2}.get(prof, 0)
    elif pos == "GK":
        p += REG["GK"]
    else:
        p = ((p + REG.get(pos, 8)) * 60 + general(row) * 40 + 50) // 100
    return max(40, min(99, p))


STEP = len(E.ABILITIES)


def _order(row):
    """the abilities of `row`'s position, the one that counts most for the rating first"""
    w, (wa, wr, _ww) = _weights(row.get("Registered Position") or "CF")
    w = dict(w, **{n: wa / 2 for n in GK_A}, **{n: wr / 3 for n in GK_R})
    return sorted((n for n, _b in E.ABILITIES), key=lambda n: -w.get(n, 0))


def move(t):
    """(d, k, e): a move of size t is every ability by d and the k that count most by e more.
    One ability point moves a rating by about one and a half, so a whole point for everyone
    steps over half the ratings; t counts in 1/25 of a point (an ability at a time)."""
    q, k = divmod(abs(t), STEP)
    s = 1 if t >= 0 else -1
    return s * q, k, s


def shifted(row, t):
    """{ability: text}: the abilities of `row` after the move t (see move), stopping at 40 and 99"""
    d, k, e = move(t)
    top = set(_order(row)[:k])
    return {n: str(max(40, min(99, _val(row, n) + d + (e if n in top else 0)))) for n, _b in E.ABILITIES}


def shift_to(rows, want):
    """the move (see move) that brings the mean rating of `rows` to `want`: the smallest that
    comes closest (an ability held at 40 or 99 can leave it short).  One row is the Rating box,
    a squad is Squad level.  The mean only grows with t, so it is a halving search."""
    def mean(t):
        return round(sum(rating(dict(r, **shifted(r, t))) for r in rows) / len(rows))
    now = mean(0)
    if now == want:
        return 0
    s, end = (1, 59 * STEP) if want > now else (-1, -59 * STEP)
    # the first t from 0 towards `end` whose mean is at or past want
    lo, hi = 0, end
    if (mean(hi) - want) * s < 0:
        return hi                      # out of reach: as far as the abilities go
    while abs(hi - lo) > 1:
        mid = (lo + hi) // 2 if s > 0 else -((-lo - hi) // 2)
        if (mean(mid) - want) * s >= 0:
            hi = mid
        else:
            lo = mid
    # hi reaches it; lo, one step short, may be as close and smaller
    return lo if lo and abs(mean(lo) - want) <= abs(mean(hi) - want) else hi
