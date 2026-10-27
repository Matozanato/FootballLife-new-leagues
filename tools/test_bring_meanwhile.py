r"""python tools/test_bring_meanwhile.py <NewLife folder> [folder with the game's tables]

B260 (gianito9, 27.10.2026): four NewLife leagues added to a Modpack world had only "FL P" players.
Bring the game's leagues to this season works on a copy of the recipe in the background (minutes on
the Modpack) while the window stays open; a league added on the NewLife page meanwhile kept its
place, but when Bring finished its copy of the players replaced the recipe's, and the league's
squads were gone. Now what was added meanwhile stays (newlife.take_bring), and the NewLife page's
buttons wait while Bring works. The real release and tables, the page offscreen. No game.
"""
import copy, os, sys, types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication

K = 0


def ok(name, cond):
    global K
    assert cond, name
    K += 1
    print("ok %d - %s" % (K, name))


def main(folder, tables):
    QApplication.instance() or QApplication([])
    import leaguebuilder as B
    import lbplayers as P
    from modstudio import newlife as N
    from modstudio.project import Project
    from modstudio.pages import newlife as PN
    deep = os.path.join(tables, "common", "etc", "pesdb")
    base = B.base_dir(deep if os.path.isdir(deep) else tables)
    info = B.game_info(base)
    names = dict((i, n) for n, i in B.country_ids(base))
    rel = N.Release(folder)
    rel.use_tables(info)
    rows = rel.leagues(lambda c: names.get(int(c), "").split(" (")[0], info)
    recipe = {"world": "_FL26Bring", "leagues": [], "edits": {}, "players": {}}
    plan = N.game_league_plan(recipe, rel, info)
    ok("the release brings %d leagues of the game" % len(plan), plan)
    cids = [plan[0]["cid"]]

    # Bring starts: its copy, and what the recipe has
    keys = ("leagues", "edits", "players", "newlife_game")
    work = {k: copy.deepcopy(recipe[k]) for k in keys if k in recipe}
    start = N.bring_start(recipe)
    # meanwhile a NewLife league goes in (the NewLife page's Add to your world), and a club edit
    L = next(r for r in rows if r["country"] and not r["in_game"] and 10 <= len(r["clubs"]) <= 20 and N.fits(r, info))
    name, _s, _e = N.add_league(recipe, rel, L, info=info)
    mine = {k: copy.deepcopy(v) for k, v in recipe["players"].items() if k.rpartition("/")[0] == name}
    ok("%s added meanwhile: %d squads" % (name, len(mine)), len(mine) == len(L["clubs"]))
    recipe["edits"].setdefault("clubs", {})["99999"] = {"name": "Meanwhile FC"}
    n = N.refresh_game_leagues(work, rel, info, cids, True)
    ok("Bring did its work on the copy (%d squads)" % n["clubs"], n["clubs"] and work.get("newlife_game"))
    old = copy.deepcopy(recipe)
    for k in ("edits", "players", "newlife_game"):           # as 0.2.4 / f469319 put it back
        if k in work:
            old[k] = copy.deepcopy(work[k])
        else:
            old.pop(k, None)
    ok("before: the league's squads went (what gianito9 saw)",
       not any(k.rpartition("/")[0] == name for k in old["players"]))
    brought = copy.deepcopy(work)
    N.take_bring(recipe, work, start)
    ok("now: the league added meanwhile keeps every squad",
       {k: v for k, v in recipe["players"].items() if k.rpartition("/")[0] == name} == mine)
    ok("... and the club edit made meanwhile", recipe["edits"]["clubs"].get("99999") == {"name": "Meanwhile FC"})
    ok("Bring's squads and its record are in the recipe",
       all(recipe["players"].get(k) == v for k, v in brought["players"].items())
       and recipe["newlife_game"] == brought["newlife_game"])
    clash = {"world": "w", "leagues": [], "players": {"5": {"edits": {"0": {"name": "mine"}}}}}
    st = N.bring_start({"players": {}})
    N.take_bring(clash, {"players": {"5": {"edits": {"0": {"name": "Bring's"}}}}}, st)
    ok("a club Bring set itself: Bring's", clash["players"]["5"]["edits"]["0"]["name"] == "Bring's")
    gone = {"world": "w", "leagues": [], "players": {"A/0": {"edits": {"1": {}}}}}
    N.take_bring(gone, {"players": {}}, N.bring_start(gone))
    ok("a squad there before Bring that Bring took out stays out", "A/0" not in gone["players"])

    # the page: its buttons wait while Bring works
    p = Project(None)
    p.base = base
    app = types.SimpleNamespace(project=p, game=types.SimpleNamespace(ok=lambda: False, folder=""),
                                settings={}, page=lambda n: None, pages={}, open_page=lambda n: None,
                                say=lambda *a, **kw: None, busy=lambda *a: None)
    page = PN.NewLife(app)
    page.rel = rel
    page.read_rows()
    page.fill()
    page.tree.setCurrentItem(page.tree.topLevelItem(0))
    page.count()
    ok("Bring the game's leagues... can be pressed", page.b_game.isEnabled())
    page.bringing = True
    page.count()
    ok("while Bring works: Add, Update, Bring and Undo wait",
       not (page.b_add.isEnabled() or page.b_update.isEnabled() or page.b_game.isEnabled() or page.b_undo.isEnabled()))
    page.bringing = False
    page.count()
    ok("and come back after", page.b_game.isEnabled())
    print("test_bring_meanwhile: %d cases passed" % K)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.environ.get("APPDATA", ""), "FL26ModStudio", "tables"))
