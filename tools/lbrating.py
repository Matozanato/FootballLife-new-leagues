r"""the overall rating the game shows for a player (B53)

The game does not keep a player's rating: it works it out from his abilities each time, with a
weighting of its own for each registered position, and that is the number its squad screens
show.  Mod Studio used to show the mean of a few abilities instead (lbplayers.overall), which
is close for some players and off by six or more for others: a goalkeeper whose five GK
abilities average 70 is a 64 in the game, because his rating takes about 0.23 of GK Reach and
GK Awareness each, less of the other three, a little of Jump and Physical Contact, and then
drops some 22 points (LaraCroft, 15.10.).

WEIGHTS below is fitted, per registered position, to the ratings of 2500 players of the
game's own engine (PES 2021, the last data pack, as pesmaster.com lists them: abilities and
overall).  Non-negative least squares on the abilities, a free constant; Weak Foot Usage and
Accuracy, Form and Injury Resistance are on the game's 0-based scale (playeredit.py), the
site's 1-based numbers moved down by one.  Tried on each of those players with the weights
fitted to all the others, it gives the game's number exactly for six in ten, one off for most of
the rest and never more than two off (leave-one-out over 2500 players: 61 % exact, 98 % within one, rms 0.68).  The second striker (SS) has the fewest players
to learn from and is the one most often a point out.

Only the registered position is rated: a position he can also play costs him a few points,
and that is not what the squad screens show.

lbplayers.overall stays what Build measures squads with (fill_level, at_level, NewLife's
levels): changing it would change the abilities every world gets.  This is what Mod Studio
shows and what the Rating box sets.
"""

import playeredit as E

WEIGHTS = {
    "GK": (-23.186, {
        "GK Reach": 0.2476, "GK Awareness": 0.2376, "GK Clearing": 0.1693, "GK Reflexes": 0.1662,
        "GK Catching": 0.1604, "Jump": 0.1108, "Physical Contact": 0.0931,
        "Weak Foot Accuracy": 0.0791, "Heading": 0.0153, "Aggression": 0.0051, "Balance": 0.0050,
        "Curl": 0.0030, "Tight Possession": 0.0021, "Acceleration": 0.0016}),
    "CB": (-46.032, {
        "Jump": 0.1696, "Defensive Awareness": 0.1657, "Physical Contact": 0.1633,
        "Ball Winning": 0.1608, "Heading": 0.1605, "Stamina": 0.1168, "Speed": 0.0985,
        "Aggression": 0.0771, "Low Pass": 0.0710, "Ball Control": 0.0672,
        "Weak Foot Accuracy": 0.0620, "Finishing": 0.0595, "Kicking Power": 0.0536,
        "Acceleration": 0.0458, "Curl": 0.0418, "Place Kicking": 0.0382,
        "Offensive Awareness": 0.0379, "Form": 0.0379, "Lofted Pass": 0.0282, "Balance": 0.0259,
        "Tight Possession": 0.0214, "Dribbling": 0.0148}),
    "LB": (-47.762, {
        "Weak Foot Accuracy": 0.1951, "Weak Foot Usage": 0.1693, "Acceleration": 0.1624,
        "Stamina": 0.1351, "Lofted Pass": 0.1196, "Physical Contact": 0.1175,
        "Defensive Awareness": 0.1128, "Jump": 0.1118, "Low Pass": 0.1086, "Ball Control": 0.0966,
        "Speed": 0.0930, "Ball Winning": 0.0924, "Dribbling": 0.0904,
        "Offensive Awareness": 0.0871, "Injury Resistance": 0.0692, "Tight Possession": 0.0633,
        "Kicking Power": 0.0521, "Balance": 0.0517, "Aggression": 0.0511, "Place Kicking": 0.0390,
        "Curl": 0.0357, "Finishing": 0.0329, "Heading": 0.0299}),
    "RB": (-47.410, {
        "Weak Foot Accuracy": 0.3101, "Weak Foot Usage": 0.2186, "Stamina": 0.1776,
        "Defensive Awareness": 0.1732, "Acceleration": 0.1335, "Lofted Pass": 0.1122,
        "Physical Contact": 0.1086, "Dribbling": 0.1074, "Ball Control": 0.1057, "Jump": 0.1056,
        "Finishing": 0.0874, "Speed": 0.0846, "Balance": 0.0750, "Aggression": 0.0735,
        "Tight Possession": 0.0679, "Offensive Awareness": 0.0660, "Ball Winning": 0.0625,
        "Curl": 0.0378, "Place Kicking": 0.0313, "Low Pass": 0.0311, "Kicking Power": 0.0222,
        "Heading": 0.0193}),
    "DMF": (-44.410, {
        "Weak Foot Usage": 0.2001, "Lofted Pass": 0.1578, "Ball Control": 0.1508,
        "Low Pass": 0.1402, "Weak Foot Accuracy": 0.1295, "Dribbling": 0.1280, "Curl": 0.1250,
        "Stamina": 0.1186, "Offensive Awareness": 0.0945, "Jump": 0.0930,
        "Defensive Awareness": 0.0828, "Physical Contact": 0.0704, "Finishing": 0.0679,
        "Aggression": 0.0606, "Ball Winning": 0.0599, "Acceleration": 0.0566, "Speed": 0.0550,
        "Balance": 0.0501, "Tight Possession": 0.0403, "Heading": 0.0359, "Kicking Power": 0.0312,
        "Place Kicking": 0.0272, "Injury Resistance": 0.0100}),
    "CMF": (-40.985, {
        "Low Pass": 0.1823, "Ball Control": 0.1726, "Stamina": 0.1592, "Lofted Pass": 0.1582,
        "Weak Foot Accuracy": 0.1576, "Dribbling": 0.1440, "Offensive Awareness": 0.1132,
        "Speed": 0.0708, "Tight Possession": 0.0614, "Ball Winning": 0.0611,
        "Acceleration": 0.0561, "Kicking Power": 0.0554, "Defensive Awareness": 0.0518,
        "Balance": 0.0498, "Injury Resistance": 0.0447, "Finishing": 0.0439, "Aggression": 0.0378,
        "Physical Contact": 0.0366, "Jump": 0.0346, "Curl": 0.0303, "Place Kicking": 0.0249,
        "Heading": 0.0125}),
    "LMF": (-38.465, {
        "Dribbling": 0.3590, "Weak Foot Usage": 0.2814, "Stamina": 0.1972, "Speed": 0.1811,
        "Lofted Pass": 0.1468, "Low Pass": 0.1109, "Finishing": 0.1086, "Jump": 0.0784,
        "Acceleration": 0.0484, "Ball Control": 0.0440, "Balance": 0.0412, "Aggression": 0.0400,
        "Curl": 0.0365, "Defensive Awareness": 0.0361, "Physical Contact": 0.0289,
        "Tight Possession": 0.0184, "Ball Winning": 0.0180, "Place Kicking": 0.0142}),
    "RMF": (-44.931, {
        "Weak Foot Accuracy": 0.5352, "Speed": 0.2360, "Ball Control": 0.2068,
        "Acceleration": 0.1428, "Low Pass": 0.1162, "Curl": 0.1089, "Finishing": 0.1023,
        "Tight Possession": 0.0879, "Offensive Awareness": 0.0854, "Ball Winning": 0.0789,
        "Aggression": 0.0783, "Stamina": 0.0641, "Dribbling": 0.0561, "Jump": 0.0535,
        "Physical Contact": 0.0495, "Kicking Power": 0.0444, "Lofted Pass": 0.0366,
        "Balance": 0.0340, "Place Kicking": 0.0145, "Heading": 0.0063,
        "Defensive Awareness": 0.0012}),
    "AMF": (-46.454, {
        "Ball Control": 0.2199, "Dribbling": 0.1567, "Low Pass": 0.1383, "Lofted Pass": 0.1289,
        "Offensive Awareness": 0.1263, "Finishing": 0.1190, "Balance": 0.0954,
        "Kicking Power": 0.0907, "Acceleration": 0.0887, "Stamina": 0.0826,
        "Weak Foot Usage": 0.0687, "Heading": 0.0620, "Ball Winning": 0.0570,
        "Place Kicking": 0.0533, "Aggression": 0.0440, "Injury Resistance": 0.0429,
        "Physical Contact": 0.0428, "Jump": 0.0414, "Tight Possession": 0.0412, "Speed": 0.0352,
        "Defensive Awareness": 0.0088, "Curl": 0.0065}),
    "LWF": (-45.011, {
        "Speed": 0.1915, "Ball Control": 0.1726, "Dribbling": 0.1316, "Stamina": 0.1252,
        "Offensive Awareness": 0.1222, "Finishing": 0.1058, "Kicking Power": 0.1034,
        "Tight Possession": 0.1000, "Lofted Pass": 0.0929, "Acceleration": 0.0870,
        "Ball Winning": 0.0673, "Low Pass": 0.0640, "Curl": 0.0578, "Defensive Awareness": 0.0509,
        "Weak Foot Accuracy": 0.0497, "Aggression": 0.0445, "Weak Foot Usage": 0.0381,
        "Balance": 0.0370, "Injury Resistance": 0.0340, "Physical Contact": 0.0270,
        "Place Kicking": 0.0265, "Heading": 0.0112, "Jump": 0.0074}),
    "RWF": (-41.807, {
        "Weak Foot Usage": 0.2799, "Low Pass": 0.1891, "Dribbling": 0.1751, "Speed": 0.1717,
        "Offensive Awareness": 0.1227, "Ball Control": 0.1115, "Finishing": 0.0967,
        "Weak Foot Accuracy": 0.0923, "Tight Possession": 0.0853, "Kicking Power": 0.0847,
        "Balance": 0.0815, "Lofted Pass": 0.0711, "Acceleration": 0.0616, "Stamina": 0.0602,
        "Jump": 0.0517, "Physical Contact": 0.0454, "Ball Winning": 0.0427, "Aggression": 0.0402,
        "Place Kicking": 0.0348, "Defensive Awareness": 0.0317, "Curl": 0.0160}),
    "SS": (-41.443, {
        "Weak Foot Accuracy": 0.6155, "Form": 0.2556, "Offensive Awareness": 0.2443,
        "Speed": 0.1925, "Kicking Power": 0.1708, "Low Pass": 0.1614, "Stamina": 0.1467,
        "Dribbling": 0.1449, "Tight Possession": 0.1044, "Place Kicking": 0.0741,
        "Injury Resistance": 0.0713, "Defensive Awareness": 0.0645, "Ball Control": 0.0638,
        "Balance": 0.0612, "Acceleration": 0.0517, "Aggression": 0.0334, "Ball Winning": 0.0242}),
    "CF": (-45.635, {
        "Finishing": 0.2666, "Offensive Awareness": 0.2156, "Ball Control": 0.1857,
        "Weak Foot Accuracy": 0.1470, "Physical Contact": 0.0994, "Acceleration": 0.0788,
        "Tight Possession": 0.0777, "Dribbling": 0.0771, "Heading": 0.0663,
        "Kicking Power": 0.0602, "Speed": 0.0594, "Ball Winning": 0.0585, "Balance": 0.0581,
        "Low Pass": 0.0580, "Jump": 0.0539, "Form": 0.0433, "Stamina": 0.0427,
        "Aggression": 0.0416, "Lofted Pass": 0.0353, "Place Kicking": 0.0350,
        "Defensive Awareness": 0.0325, "Curl": 0.0293, "Weak Foot Usage": 0.0143}),
}



# a field the row does not have counts as the game's least (an ability 40, Weak Foot 1 ...),
# Form as its middle
LEAST = {"Weak Foot Usage": 1, "Weak Foot Accuracy": 1, "Form": 3, "Injury Resistance": 1}


def _val(row, n):
    v = str(row.get(n, "")).strip()
    return int(v) if v.isdigit() else LEAST.get(n, 40)


def rating(row):
    """the rating the game shows for the player of `row` (playeredit's CSV texts), at his
    registered position (a CF when the row has none)"""
    c, w = WEIGHTS.get(row.get("Registered Position") or "CF", WEIGHTS["CF"])
    return max(40, min(99, round(c + sum(k * _val(row, n) for n, k in w.items()))))


STEP = len(E.ABILITIES)


def _order(row):
    """the abilities of `row`'s position, the one that counts most for the rating first"""
    w = WEIGHTS.get(row.get("Registered Position") or "CF", WEIGHTS["CF"])[1]
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
