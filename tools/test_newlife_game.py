"""python test_newlife_game.py <NewLife folder> <folder with the game's tables> -- the game's own
leagues brought to the NewLife season (0.1.8): clubs that went up and down between two leagues
of the game swap, clubs that went down out of the game's world hand their place to a club the
release brings up, every club gets the release's squad, a club the recipe changes by hand stays
as it is, and undoing (or doing it again) takes back exactly what it did"""
import copy, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B
import lbplayers as P
from modstudio import newlife as N


def main(folder, base):
    rel = N.Release(folder)
    info = B.game_info(base)
    plan = N.game_league_plan({"leagues": []}, rel, info)
    assert plan, "the release has none of the game's leagues"
    swaps = {(a, b) for p in plan for a, b in p["swaps"]}
    assert all((b, a) in swaps for a, b in swaps), "a swap goes both ways"
    for p in plan:
        n = len(next(ts for _r, c, _n, ts in B.game_leagues(base) if c == p["cid"]))
        assert len(p["clubs"]) + len(p["replace"]) <= n, p["name"]
    hand = next(t for p in plan for t in p["clubs"])
    r = {"leagues": [], "players": {str(hand): {"remove": [str(P.Squads(base).by_club[hand][0][1])]}},
         "edits": {"clubs": {"101": {"name": "Mine"}}}}
    before = copy.deepcopy(r)
    n = N.refresh_game_leagues(r, rel, info, [p["cid"] for p in plan])
    assert n["clubs"] and n["join"], n
    assert B.swap_problems(r, base) == [], B.swap_problems(r, base)
    assert P.check(r) == [], P.check(r)[:5]
    assert r["players"][str(hand)] == before["players"][str(hand)], "a club changed by hand stays"
    assert r["edits"]["clubs"]["101"]["name"] == "Mine" or "101" in r["newlife_game"]["replaced"]
    for k, c in r["players"].items():
        if c.get("newlife_game"):
            assert not set(c.get("join") or []) & set(c.get("remove") or []), k
    joined = [g for c in r["players"].values() for g in c.get("join") or []]
    assert len(joined) == len(set(joined)), "a player joins two clubs"
    again = copy.deepcopy(r)
    N.refresh_game_leagues(again, rel, info, [p["cid"] for p in plan])
    assert json.dumps(again, sort_keys=True) == json.dumps(r, sort_keys=True), "doing it again changes nothing"
    assert N.undo_game_leagues(r)
    assert r == before, "undo takes back exactly what it did"
    assert not N.undo_game_leagues(r)
    print("ok: %d leagues, %s" % (len(plan), dict(n)))


if __name__ == "__main__":
    main(*sys.argv[1:3])
