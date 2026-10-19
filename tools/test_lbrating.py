r"""python tools/test_lbrating.py

B53 (LaraCroft, 15.10. and 19.10.2026): the Rating box said 70 for a goalkeeper the game shows as
64, and a forward was off too: Mod Studio showed the mean of a few abilities, the game rates a
player with weights of its own per registered position.  lbrating.rating is fitted to the game's
ratings; these are players of the game (PES 2021's last data pack, pesmaster.com), the lower and
the upper quarter of each position, and the game's rating of each.
  - rating() is the game's number, or one off (the fit is not exact: about six in ten exact);
  - a goalkeeper of five GK abilities at 70 is well under 70, as in the game;
  - shift_to lands on the rating asked for exactly (or the closest one: abilities stop at 40
    and 99), for one player (the Rating box) and a squad's mean (Squad level), moving every
    ability by one amount and the ones that count most for the rating by one more;
  - a row with no position is rated as a CF, missing fields as the game's least;
  - lbplayers.overall, Build's yardstick, is not changed.

No game.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import lbplayers as P
import lbrating as R

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1


# the fields of each sample, in this order (Weak Foot, Form, Injury Resistance on the game's scale)
FIELDS = ['Offensive Awareness', 'Ball Control', 'Dribbling', 'Tight Possession', 'Low Pass', 'Lofted Pass', 'Finishing', 'Heading', 'Place Kicking', 'Curl', 'Speed', 'Acceleration', 'Kicking Power', 'Jump', 'Physical Contact', 'Balance', 'Stamina', 'Defensive Awareness', 'Ball Winning', 'Aggression', 'GK Awareness', 'GK Catching', 'GK Clearing', 'GK Reflexes', 'GK Reach', 'Weak Foot Usage', 'Weak Foot Accuracy', 'Form', 'Injury Resistance']
# (pesmaster's name of the player, registered position, the game's rating, the fields)
GAME = [
    ("a-krul", "GK", 64, [42, 57, 53, 45, 56, 62, 40, 60, 44, 47, 59, 54, 77, 72, 75, 57, 53, 56, 45, 47, 75, 71, 68, 69, 74, 1, 1, 3, 1]),
    ("o-vlachodimos", "GK", 80, [58, 55, 50, 51, 62, 64, 48, 70, 63, 53, 71, 74, 77, 82, 78, 62, 75, 62, 53, 53, 88, 79, 85, 90, 88, 1, 1, 6, 2]),
    ("m-dawson", "CB", 69, [59, 70, 60, 64, 72, 74, 50, 76, 51, 56, 53, 51, 70, 79, 79, 64, 70, 79, 74, 75, 40, 40, 40, 40, 40, 1, 1, 4, 1]),
    ("g-chiellini", "CB", 86, [61, 72, 70, 67, 74, 75, 62, 85, 60, 66, 76, 73, 79, 87, 90, 64, 80, 91, 93, 87, 40, 40, 40, 40, 40, 1, 1, 5, 0]),
    ("g-bong", "LB", 71, [62, 72, 67, 69, 73, 70, 54, 67, 57, 65, 76, 73, 68, 70, 73, 64, 76, 71, 73, 78, 40, 40, 40, 40, 40, 0, 1, 3, 1]),
    ("c-biraghi", "LB", 78, [67, 75, 74, 73, 74, 76, 62, 68, 61, 71, 79, 77, 78, 71, 68, 71, 80, 75, 76, 74, 40, 40, 40, 40, 40, 2, 2, 4, 2]),
    ("yan-couto", "RB", 69, [61, 66, 68, 63, 62, 66, 56, 58, 62, 65, 85, 81, 66, 70, 63, 86, 72, 61, 64, 64, 40, 40, 40, 40, 40, 1, 1, 4, 1]),
    ("d-dumfries", "RB", 81, [71, 72, 74, 71, 75, 76, 69, 85, 55, 62, 84, 81, 77, 83, 83, 65, 84, 68, 74, 78, 40, 40, 40, 40, 40, 1, 2, 5, 2]),
    ("d-glazer", "DMF", 72, [63, 73, 66, 71, 72, 75, 60, 63, 58, 65, 66, 69, 73, 66, 72, 65, 79, 68, 76, 83, 40, 40, 40, 40, 40, 1, 1, 3, 1]),
    ("i-soro", "DMF", 82, [64, 79, 75, 76, 79, 73, 65, 74, 70, 74, 79, 76, 77, 72, 79, 74, 86, 75, 86, 83, 40, 40, 40, 40, 40, 2, 1, 4, 1]),
    ("li-ke", "CMF", 71, [67, 72, 72, 68, 73, 70, 66, 60, 55, 63, 76, 78, 69, 75, 66, 80, 79, 70, 70, 72, 40, 40, 40, 40, 40, 1, 1, 3, 1]),
    ("a-ramsey", "CMF", 83, [77, 84, 83, 81, 85, 83, 76, 63, 68, 72, 72, 74, 78, 71, 69, 80, 86, 72, 75, 70, 40, 40, 40, 40, 40, 1, 1, 4, 1]),
    ("d-efremov", "LMF", 72, [70, 75, 77, 74, 72, 70, 60, 63, 60, 67, 81, 77, 77, 61, 65, 71, 77, 67, 73, 67, 40, 40, 40, 40, 40, 1, 2, 3, 2]),
    ("m-cornet", "LMF", 79, [76, 73, 79, 75, 74, 75, 76, 69, 66, 71, 86, 85, 76, 72, 75, 80, 82, 57, 59, 66, 40, 40, 40, 40, 40, 2, 2, 4, 1]),
    ("a-ndiaye", "RMF", 69, [66, 72, 74, 68, 72, 66, 69, 64, 60, 62, 83, 80, 70, 67, 62, 77, 75, 52, 51, 51, 40, 40, 40, 40, 40, 1, 2, 4, 1]),
    ("roberto-torres", "RMF", 77, [75, 78, 78, 75, 78, 80, 75, 69, 82, 82, 73, 74, 84, 67, 69, 74, 79, 65, 68, 70, 40, 40, 40, 40, 40, 1, 1, 5, 1]),
    ("d-gazdag", "AMF", 70, [74, 69, 71, 67, 69, 67, 70, 67, 69, 65, 77, 79, 75, 77, 69, 75, 80, 57, 59, 68, 40, 40, 40, 40, 40, 1, 2, 4, 1]),
    ("j-toornstra", "AMF", 86, [81, 81, 78, 80, 84, 85, 83, 68, 83, 82, 77, 74, 91, 77, 77, 80, 91, 73, 67, 91, 40, 40, 40, 40, 40, 1, 1, 5, 2]),
    ("i-atiemwen", "LWF", 70, [67, 71, 75, 65, 61, 53, 66, 60, 67, 65, 85, 89, 72, 70, 72, 79, 79, 50, 52, 62, 40, 40, 40, 40, 40, 0, 1, 3, 1]),
    ("a-griezmann", "LWF", 90, [92, 92, 87, 87, 86, 83, 87, 84, 83, 90, 81, 85, 81, 82, 69, 81, 87, 54, 56, 56, 40, 40, 40, 40, 40, 1, 1, 5, 2]),
    ("lirim-kastrati", "RWF", 70, [71, 75, 78, 74, 69, 62, 69, 60, 66, 72, 78, 81, 70, 68, 63, 72, 71, 50, 50, 61, 40, 40, 40, 40, 40, 2, 2, 3, 1]),
    ("r-mahrez", "RWF", 89, [82, 91, 93, 95, 84, 84, 81, 62, 81, 87, 86, 91, 82, 64, 67, 89, 79, 56, 54, 62, 40, 40, 40, 40, 40, 0, 2, 7, 2]),
    ("dentinho", "SS", 72, [71, 81, 76, 77, 73, 66, 67, 67, 63, 73, 77, 82, 76, 58, 74, 81, 71, 44, 42, 63, 40, 40, 40, 40, 40, 2, 2, 3, 0]),
    ("p-dybala", "SS", 91, [87, 91, 90, 92, 86, 83, 87, 67, 88, 91, 87, 88, 88, 72, 66, 93, 82, 51, 54, 60, 40, 40, 40, 40, 40, 0, 1, 6, 1]),
    ("s-plaza", "CF", 69, [72, 64, 67, 63, 62, 64, 76, 71, 62, 62, 75, 82, 78, 78, 86, 63, 84, 53, 45, 49, 40, 40, 40, 40, 40, 1, 1, 3, 1]),
    ("roberto-firmino", "CF", 87, [87, 89, 85, 89, 84, 79, 80, 75, 74, 80, 81, 79, 80, 82, 76, 86, 87, 50, 52, 71, 40, 40, 40, 40, 40, 1, 2, 5, 1]),
]


def row(pos, vals):
    return dict({"Registered Position": pos}, **{f: str(v) for f, v in zip(FIELDS, vals)})


def main():
    for name, pos, want, vals in GAME:
        got = R.rating(row(pos, vals))
        ok("%s (%s): the game says %d, rating() %d" % (name, pos, want, got), abs(got - want) <= 1)
    exact = sum(R.rating(row(pos, vals)) == want for _n, pos, want, vals in GAME)
    ok("most of them exactly (%d of %d)" % (exact, len(GAME)), exact * 2 > len(GAME))

    gk = {"Registered Position": "GK", "GK Awareness": "70", "GK Catching": "70", "GK Clearing": "70",
          "GK Reflexes": "70", "GK Reach": "70", "Jump": "65", "Physical Contact": "60"}
    ok("Build's yardstick is still the mean: 70", P.overall(gk) == 70)
    ok("the game's rating of that keeper is well under it (%d)" % R.rating(gk), 55 <= R.rating(gk) <= 66)

    for name, pos, want, vals in GAME[:6]:
        r = row(pos, vals)
        for target in (want - 7, want + 5):
            t = R.shift_to([r], target)
            moved = dict(r, **R.shifted(r, t))
            d, k, e = R.move(t)
            ok("%s to %d: lands on it" % (name, target), R.rating(moved) == target)
            was = [int(r.get(n) or 40) for n in R._order(r)]
            ok("%s to %d: the %d that count most by %+d, the rest by %+d (stopping at 40 and 99)"
               % (name, target, k, d + e, d),
               [int(moved[n]) for n in R._order(r)]
               == [max(40, min(99, v + d + (e if i < k else 0))) for i, v in enumerate(was)])
    squad = [row(pos, vals) for _n, pos, _w, vals in GAME]
    mean = lambda rows: round(sum(R.rating(x) for x in rows) / len(rows))
    for want in range(mean(squad) - 6, mean(squad) + 7):
        t = R.shift_to(squad, want)
        ok("Squad level to %d: the mean is %d" % (want, want), mean([dict(x, **R.shifted(x, t)) for x in squad]) == want)
    ok("the same rating asked again moves nothing", R.shift_to([squad[0]], R.rating(squad[0])) == 0)
    top = dict(squad[0], **{n: "99" for n, _b in P.E.ABILITIES})
    ok("abilities stop at 99: as close as it goes", R.rating(dict(top, **R.shifted(top, R.shift_to([top], 99)))) <= 99)
    ok("no position: a CF", R.rating({k: v for k, v in squad[-1].items() if k != "Registered Position"})
       == R.rating(dict(squad[-1], **{"Registered Position": "CF"})))
    ok("an empty row is the least there is", R.rating({}) == 40)
    print("all %d passed" % N)


if __name__ == "__main__":
    main()
