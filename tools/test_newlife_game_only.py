"""python test_newlife_game_only.py <NewLife folder> <folder with the game's tables> -- "Bring the
game's leagues" with only the game's own players (Aleperfe87 22.10.): a club of the game that keeps
its place gets no new player and lets nobody go (a player the release names otherwise, Zambo
Anguissa / Anguissa, is not made twice), its transfers and ratings still come; a club that came up
into a place gets its whole squad; undo takes back exactly what it did"""
import copy, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B
import lbplayers as P
from modstudio import newlife as N


def main(folder, base):
    rel = N.Release(folder)
    info = B.game_info(base)
    plan = N.game_league_plan({"leagues": []}, rel, info)
    assert plan, "the release has none of the game's leagues"
    cids = [p["cid"] for p in plan]
    full = {"leagues": []}
    a = N.refresh_game_leagues(full, rel, info, cids)
    r = {"leagues": []}
    n = N.refresh_game_leagues(r, rel, info, cids, new_players=False)
    assert r["newlife_game"].get("game_players_only") and not full["newlife_game"].get("game_players_only")
    assert n["join"] and n["skipped"], dict(n)
    assert P.check(r) == [], P.check(r)[:5]
    db = P.Squads(base)
    replaced = {int(t) for t in r["newlife_game"]["replaced"]}
    stay = [t for t in r["newlife_game"]["clubs"] if t not in replaced]
    assert stay and replaced, (len(stay), len(replaced))
    for t in stay:
        c = r["players"][str(t)]
        assert not c.get("add"), ("a club of the game got new players", t)
        over = len(db.by_club.get(t, [])) + len(c.get("join") or []) - P.CLUB_MAX
        assert len(c.get("remove") or []) <= max(over, 0), ("a club let players go", t, c.get("remove"))
    for t in replaced:                 # a club that came up still gets its squad
        c = r["players"].get(str(t)) or {}
        assert c.get("add") or c.get("join"), ("a club that came up got no squad", t)
    made = sum(len(c.get("add") or []) for c in r["players"].values())
    made_full = sum(len(c.get("add") or []) for c in full["players"].values())
    assert made < made_full, (made, made_full)
    joined = [g for c in r["players"].values() for g in c.get("join") or []]
    assert len(joined) == len(set(joined)), "a player joins two clubs"
    # the same as the full Bring for joins and ratings
    assert n["join"] == a["join"], (n["join"], a["join"])
    assert N.undo_game_leagues(r) and r in ({"leagues": []}, {"leagues": [], "players": {}}),         "undo takes back exactly what it did"
    print("ok: %d leagues, %d clubs keep their place, %d came up; new players %d (full Bring %d), "
          "let go %d (full %d), %d left out" % (len(plan), len(stay), len(replaced), made, made_full,
                                                n["remove"], a["remove"], n["skipped"]))


if __name__ == "__main__":
    main(*sys.argv[1:3])
