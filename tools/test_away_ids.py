"""python test_away_ids.py <folder with the game's tables> -- B287 (pepponeee98 29.10.2026): a league
taken out of a world and added again came back with other team ids and other player ids, so the
Edit made with it (it lists both) no longer fitted, and the game asked for a new one. The plan now
keeps the team ids of the leagues the recipe left out (away_leagues) and the ids file their
players' (its "away" part): the league added again gets both back, and no other new club takes
them meanwhile while another id is free.

Three Builds of one world in a temporary game folder: with the league, without it, with it again.
"""
import json, os, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B

N = 0
WORLD = "_FL26AwayIds"


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def league(name, country, clubs):
    return {"name": name, "country": country, "clubs": clubs, "legs": 2}


def build(game, base, leagues):
    """the plan and the ids file of a Build of leagues, on top of the world's last Build"""
    w = os.path.join(game, "SiderAddons", "livecpk", WORLD)
    prev = None
    if os.path.exists(os.path.join(w, "leaguebuilder-plan.json")):
        with open(os.path.join(w, "leaguebuilder-plan.json"), encoding="utf-8") as f:
            prev = json.load(f)
    B.build(B.plan({"world": WORLD, "leagues": leagues}, base, prev), base, game, True, log=lambda t: None)
    with open(os.path.join(w, "leaguebuilder-plan.json"), encoding="utf-8") as f:
        pl = json.load(f)
    with open(os.path.join(w, B.PLAYER_IDS), encoding="utf-8") as f:
        return pl, json.load(f)


def teams(pl, name):
    return [p["teams"] for p in pl["leagues"] if p["name"] == name][0]


def players(ids, name):
    return {k: v for k, v in ids["clubs"].items() if k.startswith(name + "/")}


def main(base):
    game = tempfile.mkdtemp(prefix="fl26-away-")
    try:
        for d in ("livecpk", "modules", "content"):
            os.makedirs(os.path.join(game, "SiderAddons", d))
        with open(os.path.join(game, "SiderAddons", "sider.ini"), "w") as f:
            f.write("[sider]\n")
        stay, ex = league("Away Albania", "Albania", 10), league("Away Andorra", "Andorra", 10)
        pl1, ids1 = build(game, base, [stay, ex])
        pl2, ids2 = build(game, base, [stay])
        ok("taken out: the plan keeps its team ids", [q["teams"] for q in pl2.get("away_leagues") or []
                                                      if q["name"] == "Away Andorra"] == [teams(pl1, "Away Andorra")])
        ok("and the ids file its players' (%d clubs)" % len(players(ids1, "Away Andorra")),
           {k: v for k, v in (ids2.get("away") or {}).get("clubs", {}).items() if k.startswith("Away Andorra/")}
           == players(ids1, "Away Andorra") and not players(ids2, "Away Andorra"))
        ok("the league that stayed keeps its ids", teams(pl2, "Away Albania") == teams(pl1, "Away Albania")
           and players(ids2, "Away Albania") == players(ids1, "Away Albania"))
        other = league("Away Armenia", "Armenia", 10)
        pl3, ids3 = build(game, base, [stay, other])
        ok("a league added meanwhile takes none of its team ids",
           not set(teams(pl3, "Away Armenia")) & set(teams(pl1, "Away Andorra")))
        ok("nor its players' ids", not {i for v in players(ids3, "Away Armenia").values() for i in v.values()}
           & {i for v in players(ids1, "Away Andorra").values() for i in v.values()})
        pl4, ids4 = build(game, base, [stay, other, ex])
        ok("added again: the same team ids", teams(pl4, "Away Andorra") == teams(pl1, "Away Andorra"))
        ok("and the same player ids", players(ids4, "Away Andorra") == players(ids1, "Away Andorra"))
        ok("no longer away", not [q for q in pl4.get("away_leagues") or [] if q["name"] == "Away Andorra"]
           and not any(k.startswith("Away Andorra/") for k in (ids4.get("away") or {}).get("clubs", {})))
        ok("the others keep theirs", teams(pl4, "Away Armenia") == teams(pl3, "Away Armenia")
           and players(ids4, "Away Armenia") == players(ids3, "Away Armenia"))
    finally:
        shutil.rmtree(game, ignore_errors=True)
    print("1..%d" % N)


if __name__ == "__main__":
    main(sys.argv[1])
