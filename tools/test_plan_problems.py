r"""python tools/test_plan_problems.py [folder with the game's tables]

Build simplifications (jibibi, vmican 19.10.; mato 21.10.: all in 0.2.5):
  1. Check the plan / Build lists every problem at once (PlanProblems), not the first one only:
     problems of two leagues, of a club of the game in a place, and of the player changes;
  2. each says where it is, for Go there: a league and its place, a league, a club of the game, the
     players of a club; a league under one with a problem is not listed again;
  3. a swap the game's tables made out of date (both clubs in the same league now: Fortaleza and
     Remo) is left out with a note, the plan goes on;
  4. a club of the game is named with its team id, both (the ids stay visible).
The game's tables (default %APPDATA%\FL26ModStudio\tables). No game.
"""
import collections, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import leaguebuilder as B

N = 0
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def league(name, **kw):
    return dict({"name": name, "country": "Colombia", "clubs": 16, "legs": 2}, **kw)


def main(tables):
    deep = os.path.join(tables, "common", "etc", "pesdb")
    base = B.base_dir(deep if os.path.isdir(deep) else tables)
    info = B.game_info(base)
    by = collections.defaultdict(list)
    for t, c in info["league_of"].items():
        by[c].append(t)
    lg = sorted(by)
    a, b = sorted(by[lg[0]])[:2]                 # two clubs of one league of the game
    c = sorted(by[lg[1]])[0]                     # and one of another
    other = sorted(by[lg[2]])[0]
    good = {"world": "_FL26Plan", "leagues": [league("Liga Buena")]}
    ok("a recipe with no problem plans", B.plan(good, base)["leagues"])

    r = {"world": "_FL26Plan", "edits": {"swaps": [[a, b]]},
         "leagues": [league("Liga Uno", clubs=2),
                     league("Liga Dos", country="Nowhereland"),
                     league("Liga Tres", above="Liga Dos"),
                     league("Liga Cuatro", game_clubs=[{"at": 3, "id": c}]),
                     league("Liga Cinco")],
         "players": {"Liga Cinco/40": {"remove": ["1"]}}}
    try:
        B.plan(r, base)
        got = None
    except B.PlanProblems as e:
        got = e
    ok("1. the plan stops with all its problems at once", got is not None and len(got.problems) == 4)
    texts = [t for t, _w in got.problems]
    print("   " + "\n   ".join(texts))
    where = dict(got.problems)
    ok("Liga Uno's size, at Liga Uno", any(t.startswith("Liga Uno:") and w == {"league": "Liga Uno"}
                                         for t, w in got.problems))
    ok("Liga Dos's country, at Liga Dos", any("Nowhereland" in t and w == {"league": "Liga Dos"}
                                             for t, w in got.problems))
    ok("2. Liga Tres under it is not listed again", not any("Liga Tres" in t for t in texts))
    gc = next((t for t in texts if t.startswith("Liga Cuatro, club 4")), "")
    ok("the club of the game with no club for its old place, at Liga Cuatro club 4",
       where.get(gc) == {"league": "Liga Cuatro", "place": 3})
    ok("4. named with its team id: %s" % gc, "%s (%d)" % (info["clubs"][c][0], c) in gc)
    pt = next((t for t in texts if t.startswith("players of Liga Cinco/40")), "")
    ok("the player changes, at that club's players", where.get(pt) == {"players": "Liga Cinco/40"})
    ok("3. the out-of-date swap is no problem", not any("swap" in t for t in texts))
    # the same swap in a recipe that plans: left out, with a note naming both clubs and ids
    g = dict(good, edits={"swaps": [[a, b]]})
    pl = B.plan(g, base)
    ok("3. the out-of-date swap is left out of the plan", not (pl["edits"].get("swaps")))
    ok("... and the original recipe keeps it", g["edits"]["swaps"] == [[a, b]])
    note = (pl.get("skipped") or [""])[0]
    ok("4. the note names both clubs with their ids: %s" % note,
       "(%d)" % a in note and "(%d)" % b in note and info["clubs"][a][0] in note)
    ok("Check the plan prints the note", "note: " + note in B.describe(pl))
    # a swap that is wrong, not out of date, is still a problem, with names and ids
    g = dict(good, edits={"swaps": [[a, other], [other, c]]})
    try:
        B.plan(g, base)
        e = None
    except B.PlanProblems as x:
        e = x
    t = e.problems[0][0] if e else ""
    ok("a club in two swaps stays a problem, by name and id: %s" % t,
       e is not None and "%s (%d) is in two swaps" % (info["clubs"][other][0], other) in t)
    ok("... at that club", e.problems[0][1] == {"club": other})
    one = {"world": "_FL26Plan", "leagues": [league("Liga Sola", clubs=2)]}
    try:
        B.plan(one, base)
    except B.BuildError as x:
        ok("one problem reads as before (no count)", str(x).startswith("Liga Sola: 2 clubs"))
    print("test_plan_problems: ok (%d)" % N)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ.get("APPDATA", ""), "FL26ModStudio", "tables"))
