"""python test_newlife_put.py <NewLife folder> <folder with a Team.bin> -- NewLife clubs put in the
places of a league made by hand (#83, New clubs > NewLife club...): name, short name, kits, NewLife
id and squad at that place, a club of the game there goes, the other places stay new clubs and the
world ids come out (0.1.8: NewLife clubs could only come as a whole league from the NewLife page)"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B
import lbplayers as P
from modstudio import newlife as N


def main(folder, base):
    rel = N.Release(folder)
    picks = [cid for cid, c in sorted(rel.clubs.items()) if c.get("league") and c.get("in_game") != "1"
             and rel.squad(cid)][:3]
    x = {"name": "Hand League", "country": 200, "clubs": 12, "legs": 2,
         "club_names": ["Club %d" % i for i in range(12)], "game_clubs": [{"at": 3, "id": 101}]}
    r = {"leagues": [x]}
    for j, cid in enumerate(picks):
        N.put_club(r, rel, x, 2 + j, cid, B.game_info(base))
    assert x["newlife"]["clubs"] == [0, 0] + [int(c) for c in picks] + [0] * 7, x["newlife"]["clubs"]
    assert "version" not in x["newlife"], "no version: Update my leagues leaves it alone"
    assert x["club_names"][2:5] == [rel.clubs[c]["name"] for c in picks] and x["club_names"][5] == "Club 5"
    assert "game_clubs" not in x, "the club of the game at place 3 went"
    for j in range(3):
        assert r["players"][P.new_key("Hand League", 2 + j)], "a squad at place %d" % (2 + j)
    assert not N.outdated(r, rel)
    m, _free = B.newlife_tids(r["leagues"], base)
    assert sorted(m) == sorted(int(c) for c in picks), m
    try:
        N.put_club(r, rel, x, 12, picks[0])
        raise AssertionError("place 13 of 12")
    except N.Error:
        pass
    ing = next((cid for cid, c in rel.clubs.items() if c.get("in_game") == "1"), None)
    if ing is not None:
        try:
            N.put_club(r, rel, x, 0, ing)
            raise AssertionError("a club of the game")
        except N.Error:
            pass
    print("all passed")


if __name__ == "__main__":
    main(*sys.argv[1:3])
