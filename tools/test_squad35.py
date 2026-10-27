r"""python tools/test_squad35.py <folder with the game's tables> <NewLife folder>

World options > Players per new club (mato 27.10.2026: "Radimo oboje" -- up to 35 players at a
new club, 30 as before when it is not set). Real Builds into a game folder of their own:
  - a world of 35 gives every new club 35 players, one of 30 (no setting) 30;
  - a NewLife league added at 30 and built after the world went to 35 keeps its own squads and
    gets no prototype ("FL P") players in the five places it never knew (lbplayers.fit_places);
  - NewLife > Update my leagues offers that league (newlife.resized) and takes its squads again
    at 35; a club with 35 players or more in the release then has 35.
"""
import copy, os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import leaguebuilder as B
import lbplayers as P
from modstudio import newlife as N

K = 0


def ok(name, cond):
    global K
    assert cond, name
    K += 1
    print("ok %d - %s" % (K, name))


def game_folder():
    g = tempfile.mkdtemp(prefix="fl26-squad35-")
    for d in ("livecpk", "modules", "content"):
        os.makedirs(os.path.join(g, "SiderAddons", d))
    with open(os.path.join(g, "SiderAddons", "sider.ini"), "w") as f:
        f.write("[sider]\n")
    return g


def build(recipe, base, log):
    g = game_folder()
    pl = B.plan(copy.deepcopy(recipe), base)
    B.build(pl, base, g, False, log.append)
    db = os.path.join(g, "SiderAddons", "livecpk", recipe["world"], "common", "etc", "pesdb")
    return g, pl, P.Squads(db)


def teams(pl, name):
    return [int(t) for p in pl["leagues"] if p["name"] == name for t in p["teams"]]


def main(tables, folder):
    deep = os.path.join(tables, "common", "etc", "pesdb")
    base = B.base_dir(deep if os.path.isdir(deep) else tables)
    games = []
    try:
        # the setting itself
        ok("no setting: 30", B.squad_of({}) == 30 and B.squad_of(None) == 30)
        ok("33 stays 33", B.squad_of({"squad": 33}) == 33)
        ok("never above 35, never below 30, junk is 30",
           B.squad_of({"squad": 40}) == 35 and B.squad_of({"squad": 22}) == 30 and B.squad_of({"squad": "x"}) == 30)
        ok("use_squad sets it for Build and lbplayers", B.use_squad({"squad": 34}) == 34 and B.SQUAD == P.SQUAD == 34)
        B.use_squad({})
        ok("and back to 30", B.SQUAD == P.SQUAD == 30)
        c = {"edits": {"0": {}}, "remove": ["25", "26"]}
        B.use_squad({"squad": 35})
        P.fit_places(c)
        ok("an entry made at 30 loses places 30-34 at 35, its own removals kept",
           c["remove"] == ["25", "26", "30", "31", "32", "33", "34"])
        c = {"edits": {}, "squad_places": 35}
        P.fit_places(c)
        ok("an entry made at 35 is left alone", "remove" not in c)
        B.use_squad({})

        # a plain world, 30 and 35
        plain = {"world": "_FL26Squad30", "leagues": [{"name": "Squad Albania", "country": "Albania",
                                                       "clubs": 10, "legs": 2}]}
        log = []
        g, pl, sq = build(plain, base, log)
        games.append(g)
        ok("no setting: every new club has 30", {len(sq.by_club[t]) for t in teams(pl, "Squad Albania")} == {30})
        big = dict(plain, world="_FL26Squad35", squad=35)
        log = []
        g, pl, sq = build(big, base, log)
        games.append(g)
        ok("the plan carries the world's 35", pl["squad"] == 35)
        ok("35: every new club has 35", {len(sq.by_club[t]) for t in teams(pl, "Squad Albania")} == {35})
        ok("the Build log says squads of 35", any("squads of 35 for 10 clubs" in l for l in log))
        ok("a recipe read back from the plan keeps 35", B.recipe_from_plan(pl, base).get("squad") == 35)
        B.use_squad({})

        # a NewLife league added at 30, then the world goes to 35
        info = B.game_info(base)
        rel = N.Release(folder)
        rel.use_tables(info)
        picks = [cid for cid, c in sorted(rel.clubs.items()) if c.get("league") and c.get("in_game") != "1"
                 and len(rel.squads.get(cid, [])) >= 36][:10]
        ok("the release has 10 clubs of 36 players or more to test with", len(picks) == 10)
        names = dict((i, n) for n, i in B.country_ids(base))
        rows = rel.leagues(lambda c: names.get(int(c), "").split(" (")[0], info)
        L = next(r for r in rows if picks[0] in r["clubs"])
        E = dict(L, clubs=picks, in_game=[])
        r = {"world": "_FL26SquadNL", "leagues": [], "edits": {}, "players": {}}
        name, _st, _el = N.add_league(r, rel, E, info=info, custom=True, name="Squad NewLife")
        x = r["leagues"][0]
        ok("added at 30: no squad_places written (as every recipe before 0.2.5)",
           all("squad_places" not in (r["players"].get(P.new_key(name, k)) or {}) for k in range(10)))
        ok("at 30 nothing to update", N.resized(r, rel) == [])
        r["squad"] = 35
        B.use_squad(r)
        ok("at 35 Update my leagues offers it", N.resized(r, rel) == [x] and N.to_update(r, rel) == [x])
        log = []
        g, pl, sq = build(r, base, log)
        games.append(g)
        mine = teams(pl, name)
        sizes = [len(sq.by_club[t]) for t in mine]
        ok("built at 35 before the update: its clubs keep their squads of 30", sizes == [30] * 10)
        fl = [sq.row(pid)["name"] for t in mine for _o, pid, _s, _a in sq.by_club[t]
              if sq.row(pid)["name"].startswith("FL P")]
        ok("and no FL P player anywhere in them", fl == [])

        B.use_squad(r)
        N.update_league(r, rel, x, rows, info=info, keep=True)
        x = r["leagues"][0]
        ok("after Update my leagues nothing is left to update", N.resized(r, rel) == [])
        ok("its entries say 35", all((r["players"].get(P.new_key(name, k)) or {}).get("squad_places") == 35
                                     for k in range(10)))
        log = []
        g, pl, sq = build(r, base, log)
        games.append(g)
        mine = teams(pl, name)
        ok("built after the update: 35 a club", [len(sq.by_club[t]) for t in mine] == [35] * 10)
        fl = [sq.row(pid)["name"] for t in mine for _o, pid, _s, _a in sq.by_club[t]
              if sq.row(pid)["name"].startswith("FL P")]
        ok("still no FL P player", fl == [])
    finally:
        B.use_squad({})
        for g in games:
            shutil.rmtree(g, ignore_errors=True)
    print("%d cases passed" % K)


if __name__ == "__main__":
    main(*sys.argv[1:3])
