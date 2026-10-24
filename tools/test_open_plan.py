r"""python tools/test_open_plan.py <tables pesdb folder>

B224 (ferraz j. 24.10.): Mod Studio crashed at every start, in My world's list
(leaguebuilder.new_club_count: 'str' object has no attribute 'get'). Open a world... had been
given a world's leaguebuilder-plan.json -- the one in the folder of a world downloaded as a zip --
and settings "last_recipe" opened it again at each start. A plan keeps a league's clubs of the game
by place (a dict), a recipe as a list, and counting the clubs walked the dict's keys. Now:
  - leaguebuilder.is_plan tells a plan from a recipe (every testdata recipe is not one, its plan is);
  - opening a plan opens the recipe it was built from (recipe_from_plan): no rid / free_ids left,
    every league's clubs count as the recipe's did, and the open world has no file of its own, so
    Save asks for a name and the world's plan is never written over;
  - with no game tables to read it back, opening a plan says what it is instead of crashing;
  - new_club_count reads a plan's league as well (the same count as its recipe league).
QT_QPA_PLATFORM=offscreen, a temp folder; no game.
"""
import glob, hashlib, json, os, sys, tempfile, types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication

N = 0
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def ok(name, cond):
    global N
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        N += 1


def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


def main(base):
    QApplication.instance() or QApplication([])
    import leaguebuilder as B
    from modstudio.project import Project
    T = tempfile.mkdtemp(prefix="openplan-")
    files = sorted(glob.glob(os.path.join(HERE, "testdata", "*", "*.json")))
    # clubs of the game in a new league (a recipe's game_clubs: a list), as ferraz's world had
    # them: two of the game's clubs that play in no league
    names = B.game_clubs(base)
    free = [t for t in B.game_others(base, B.game_leagues(base))[1] if not names[t][0].startswith("ML ")]
    tried, p = 0, None
    for f in files:
        r = B.load_recipe(f)
        if not r["leagues"] or r["leagues"][0].get("others"):
            continue
        name = os.path.basename(f)
        if tried == 0:
            L0 = r["leagues"][0]
            L0["game_clubs"] = [{"at": 0, "id": free[0]}, {"at": 1, "id": free[1]}]
            name += " (+2 clubs of the game)"
        ok("%s: a recipe is not a plan" % name, not B.is_plan(r))
        pl = json.loads(json.dumps(B.plan(r, base)))
        ok("%s: its plan is one" % name, B.is_plan(pl))
        p = os.path.join(T, "w%d" % tried, "leaguebuilder-plan.json")
        os.makedirs(os.path.dirname(p))
        json.dump(pl, open(p, "w", encoding="utf-8"), indent=1)
        before = md5(p)
        saves = []
        app = types.SimpleNamespace(settings={}, save_settings=lambda: saves.append(1))
        P = Project(app)
        P.base = base
        P.copies_dir = lambda: os.path.join(T, "recipes")     # not the real %APPDATA% copies
        P.open(p)
        rec = P.recipe
        ok("%s: opened as the recipe (no rid, no free_ids)" % name,
           not B.is_plan(rec) and all("rid" not in L for L in rec["leagues"]))
        want = sum(B.new_club_count(L) for L in r["leagues"])
        got = sum(B.new_club_count(L) for L in rec["leagues"])
        ok("%s: its new clubs count as the recipe's (%d)" % (name, want), got == want)
        ok("%s: new_club_count reads the plan's leagues too" % name,
           sum(B.new_club_count(L) for L in pl["leagues"]) == want)
        ok("%s: no file of its own, Save asks for a name" % name, P.path is None)
        P.recipe["n"] = 1
        P.touch()
        P.autosave()
        ok("%s: the world's plan is not written over" % name, md5(p) == before)
        tried += 1
        if tried >= 3:
            break
    ok("three recipes tried", tried == 3)
    P = Project(types.SimpleNamespace(settings={}, save_settings=lambda: None))
    P.base = None
    try:
        P.open(p)
        said = ""
    except B.BuildError as e:
        said = str(e)
    ok("no tables: opening a plan says it is one", "plan of a built world" in said)
    print("ALL OK" if not N else "%d FAILED" % N)
    return N


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1]))
