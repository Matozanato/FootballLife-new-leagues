"""python test_pick_rating.py <folder with the game's tables> -- the Sign / Call up list (Players >
Sign..., lbplayers.Squads.summary) shows the rating the Players page and the game show (rating(),
B53), not Build's mean of a few abilities: a goalkeeper's five GK abilities made Ter Stegen a 91
in the list and an 85 in the game's Edit > Players (cwrti, 23.10.)."""
import os, random, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lbplayers as P

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def main(tables):
    db = os.path.join(tables, "common", "etc", "pesdb")
    sq = P.Squads(db)
    rows = sq.summary()
    ok("the list has every player", len(rows) == len(sq.index))
    keepers = [r for r in rows if r["Registered Position"] == "GK"]
    ok("goalkeepers in it", len(keepers) > 100)
    rnd = random.Random(23)
    sample = keepers[:400] + rnd.sample(rows, 1500)
    bad = [(r["player"], r["name"], r["rating"], P.rating(sq.row(int(r["player"]))))
           for r in sample if r["rating"] != P.rating(sq.row(int(r["player"])))]
    ok("the list's rating is the Players page's for %d players (%s)" % (len(sample), bad[:3]), not bad)
    gk_mean = [r for r in keepers if r["rating"] != P.overall(r)]
    ok("not the mean of the GK abilities (%d keepers differ)" % len(gk_mean), len(gk_mean) > len(keepers) // 2)
    ts = [r for r in rows if r["player"] == "61672"]
    if ts:
        ok("Ter Stegen is %s, the game's 85 within one" % ts[0]["rating"], abs(ts[0]["rating"] - 85) <= 1)
    print("%d ok" % N)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
