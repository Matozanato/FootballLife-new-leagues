r"""python tools/test_newlife_picks.py <NewLife folder> [folder with the game's tables]

NewLife > Choose the players (mato 27.10.2026: "Radimo oboje" -- pick a club's players on the
NewLife page). The real release and tables, the NewLife page in this process (offscreen). No game.
  - Release.squad gives the players picked, best first, at most P.SQUAD; none of them left in the
    release: the best ones, as before;
  - a league added with players picked for a club: its squad is those players, and the league
    keeps the picks ("newlife" "picks"); Build's plan and the recipe read back from it keep them;
  - a pick of fewer than P.MIN_SQUAD: stand-in players up to P.MIN_SQUAD, as a small squad gets;
  - Update my leagues (a newer release) and Put the club in again keep the picks;
  - a club already in the world (repick): only its squad changes -- its name in the world, the
    manager's portrait and a face linked by hand on a player who stays are kept; picking the best
    ones again takes the pick away;
  - the page: Choose the players... is there for a new club and greyed for a club of the game; a
    pick made before the league is added goes in with Add to your world, one for a club in the
    world goes in the world straight away; the dialog ticks the best ones, says when there are
    too many, none, too few or no goalkeeper, and gives back None for the best ones.
"""
import copy, os, sys, types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

K = 0


def ok(name, cond):
    global K
    assert cond, name
    K += 1
    print("ok %d - %s" % (K, name))


def ids(entry):
    return {str(ch.get("newlife_id")) for ch in (entry.get("edits") or {}).values() if ch.get("newlife_id")}


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
    # a league of the release with 10-24 new clubs, the first of them with 55 players or more
    L = next(r for r in rows if r["country"] and not r["in_game"] and 10 <= len(r["clubs"]) <= 24
             and len(rel.squads.get(sorted(r["clubs"], key=lambda i: rel.clubs[i]["name"].lower())[0], [])) >= 55
             and N.fits(r, info))
    clubs = sorted(L["clubs"], key=lambda i: rel.clubs[i]["name"].lower())
    cid = clubs[0]
    every = sorted(rel.squads[cid], key=lambda r: -P.overall(r))
    nid = lambda r: str(r["newlife_id"]).strip()
    best = [nid(r) for r in rel.squad(cid)]
    worst = [nid(r) for r in every if nid(r) not in best][-20:]    # 20 of the weakest: none of the best

    # ---- Release.squad
    ok("%s (%s): %d players, the best %d" % (rel.clubs[cid]["name"], L["name"], len(every), len(best)),
       len(best) == P.SQUAD and not set(best) & set(worst))
    got = rel.squad(cid, worst)
    ok("a pick: those players, best first", [nid(r) for r in got] == worst)
    ok("a pick of more than P.SQUAD: the best P.SQUAD of it",
       [nid(r) for r in rel.squad(cid, [nid(r) for r in every])] == [nid(r) for r in every[:P.SQUAD]])
    ok("players the release has not got any more: the best ones", [nid(r) for r in rel.squad(cid, ["nobody"])] == best)

    # ---- add_league with a pick
    r = {"world": "_FL26Picks", "leagues": [], "edits": {}, "players": {}}
    name, _st, _el = N.add_league(r, rel, L, info=info, picks={cid: worst, "12345678": ["x"]})
    x = r["leagues"][0]
    k = x["newlife"]["clubs"].index(int(cid))
    ok("the league keeps the pick, of its own clubs only", x["newlife"]["picks"] == {str(int(cid)): worst})
    ok("the club's squad is the 20 picked", ids(r["players"][P.new_key(name, k)]) == set(worst))
    other = clubs[1]
    ok("a club with no pick has its best ones",
       ids(r["players"][P.new_key(name, x["newlife"]["clubs"].index(int(other)))]) == {nid(q) for q in rel.squad(other)})
    pl = B.plan(copy.deepcopy(r), base)
    back = B.recipe_from_plan(pl, base)
    ok("Build's plan and the recipe read back keep the pick",
       next(y for y in back["leagues"] if y["name"] == name)["newlife"].get("picks") == {str(int(cid)): worst})

    # ---- fewer than MIN_SQUAD
    r2 = {"world": "_FL26Picks2", "leagues": [], "edits": {}, "players": {}}
    name2, _s, _e = N.add_league(r2, rel, L, info=info, picks={cid: worst[:10]})
    c2 = r2["players"][P.new_key(name2, r2["leagues"][0]["newlife"]["clubs"].index(int(cid)))]
    kept = P.SQUAD - len(c2.get("remove") or [])
    ok("10 picked: those 10 and stand-ins up to %d (kept %d)" % (P.MIN_SQUAD, kept),
       ids(c2) == set(worst[:10]) and kept == P.MIN_SQUAD)

    # ---- Update my leagues and Put the club in again keep it
    x["newlife"]["version"] = "1.4"
    N.update_league(r, rel, x, rows, info=info, keep=True)
    x = r["leagues"][0]
    k = x["newlife"]["clubs"].index(int(cid))
    ok("after Update my leagues: the pick is kept, and the squad", x["newlife"].get("picks") == {str(int(cid)): worst}
       and ids(r["players"][P.new_key(name, k)]) == set(worst))
    del r["players"][P.new_key(name, k)]
    ok("Put in again (B249 refill) gives the picked squad",
       N.refill(r, rel, x, [k], info) and ids(r["players"][P.new_key(name, k)]) == set(worst))

    # ---- a club in the world: repick
    x["club_names"][k] = "My Own Name"
    entry = r["players"][P.new_key(name, k)]
    stay = next(n for n, ch in entry["edits"].items() if ch.get("newlife_id") == worst[0])
    entry["edits"][stay]["face_link"] = "12345"
    entry["coach_portrait"] = "C:/portrait.png"
    pick = worst[:5] + best[:20]
    N.repick(r, rel, x, k, pick, info)
    e = r["players"][P.new_key(name, k)]
    ok("repick: the squad is the new pick", ids(e) == set(pick))
    ok("... the club keeps its name in the world and the manager's portrait",
       x["club_names"][k] == "My Own Name" and e.get("coach_portrait") == "C:/portrait.png")
    ok("... a face linked by hand stays on the player who stays",
       any(ch.get("face_link") == "12345" and ch.get("newlife_id") == worst[0] for ch in e["edits"].values()))
    ok("... the league keeps the new pick", N.picks_of(x, cid) == pick)
    N.repick(r, rel, x, k, None, info)
    ok("the best ones again: the pick goes, the squad is the best", "picks" not in x["newlife"]
       and ids(r["players"][P.new_key(name, k)]) == set(best))
    ok("placed() finds the club in the world", N.placed(r, rel, cid) == (x, k))
    game = next((i for R in rows for i in R["in_game"]), None)
    if game:
        gx = {"name": "G", "club_names": ["Game club"], "newlife": {"clubs": [int(game)]}}
        try:
            N.repick({"leagues": [gx], "players": {}}, rel, gx, 0, best, info)
            refused = False
        except N.Error:
            refused = True
        ok("a club of the game: refused", refused)

    # ---- the page
    p = Project(None)
    p.base = base
    said = []
    app = types.SimpleNamespace(project=p, game=types.SimpleNamespace(ok=lambda: False, folder=""),
                                settings={}, page=lambda n: None, pages={}, open_page=lambda n: None,
                                say=lambda *a, **kw: None, busy=lambda *a: None)
    page = PN.NewLife(app)
    page.say = lambda text, *a: said.append(text)
    page.rel = rel
    page.read_rows()
    page.fill()
    row = next(n for n in range(page.tree.topLevelItemCount())
               if page.rows[page.tree.topLevelItem(n).data(0, Qt.UserRole)]["key"] == L["key"])
    page.tree.setCurrentItem(page.tree.topLevelItem(row))
    items = {page.clubs.topLevelItem(n).data(0, Qt.UserRole)[0]: page.clubs.topLevelItem(n)
             for n in range(page.clubs.topLevelItemCount())}
    page.clubs.setCurrentItem(items[cid])
    ok("Choose the players... is there for a new club", page.b_players.isEnabled())
    d = PN.PlayerPickDialog(page, rel, cid, None)
    ok("the dialog ticks the best ones", d.ticked == set(best) and len(d.order) == len(every))
    d.ok()
    ok("OK with the best ones: None (no pick)", d.picked is None and d.result() == 1)
    d = PN.PlayerPickDialog(page, rel, cid, worst)
    ok("a pick made before comes back ticked", d.ticked == set(worst))
    for n in range(d.list.topLevelItemCount()):
        d.list.topLevelItem(n).setCheckState(0, Qt.Checked)
    ok("all %d ticked: it says untick %d, OK does nothing" % (len(every), len(every) - P.SQUAD),
       ("%d" % (len(every) - P.SQUAD)) in d.n.text() and (d.ok() or d.picked is None and d.result() == 0))
    d.reset()
    ok("The best ones ticks the best again", d.ticked == set(best))
    for n in range(d.list.topLevelItemCount()):
        d.list.topLevelItem(n).setCheckState(0, Qt.Unchecked)
    d.ok()
    ok("none ticked: OK does nothing", d.picked is None and d.result() == 0)
    gks = [i for i in d.order if i in d.gk]
    outs = [i for i in d.order if i not in d.gk][:12]
    for n in range(d.list.topLevelItemCount()):
        it = d.list.topLevelItem(n)
        it.setCheckState(0, Qt.Checked if it.data(0, Qt.UserRole) in outs else Qt.Unchecked)
    ok("12 outfield players: stand-ins up to %d and no goalkeeper, said" % P.MIN_SQUAD,
       str(P.MIN_SQUAD) in d.n.text() and "goalkeeper" in d.n.text() and gks)
    d.ok()
    ok("... and OK gives them, best first", d.picked == outs)

    page.use_players(cid, worst)
    ok("a pick before the league is added waits on the page", page.picks == {cid: worst} and "20" in said[-1])
    ok("the club list says it", "20 of %d" % len(every) in items_text(page, cid))
    PN.error = lambda *a: said.append(a[-1])
    page.add()
    x = p.recipe["leagues"][-1]
    k = x["newlife"]["clubs"].index(int(cid))
    ok("Add to your world puts the pick in the league", N.picks_of(x, cid) == worst
       and ids(p.recipe["players"][P.new_key(x["name"], k)]) == set(worst))
    page.read_rows()
    page.fill()
    page.tree.setCurrentItem(page.tree.topLevelItem(row))
    for n in range(page.clubs.topLevelItemCount()):
        if page.clubs.topLevelItem(n).data(0, Qt.UserRole)[0] == cid:
            page.clubs.setCurrentItem(page.clubs.topLevelItem(n))
    page.use_players(cid, best[:25])
    ok("a club in the world: its squad changes straight away", N.picks_of(x, cid) == best[:25]
       and ids(p.recipe["players"][P.new_key(x["name"], k)]) == set(best[:25]) and "Build again" in said[-1])
    G = next((R for R in page.rows if R["in_game"]), None)
    if G:
        n = next(n for n in range(page.tree.topLevelItemCount())
                 if page.rows[page.tree.topLevelItem(n).data(0, Qt.UserRole)]["key"] == G["key"])
        page.tree.setCurrentItem(page.tree.topLevelItem(n))
        page.clubs.setCurrentItem(items_item(page, G["in_game"][0]))
        ok("a club of the game (%s): Choose the players... greyed" % rel.clubs[G["in_game"][0]]["name"],
           not page.b_players.isEnabled())
    print("test_newlife_picks: %d cases passed" % K)


def items_item(page, cid):
    for n in range(page.clubs.topLevelItemCount()):
        if page.clubs.topLevelItem(n).data(0, Qt.UserRole)[0] == cid:
            return page.clubs.topLevelItem(n)


def items_text(page, cid):
    it = items_item(page, cid)
    return it.text(1) if it else ""


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.environ.get("APPDATA", ""), "FL26ModStudio", "tables"))
