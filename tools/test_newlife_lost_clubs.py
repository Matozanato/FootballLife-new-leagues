"""python tools/test_newlife_lost_clubs.py -- B324 (Risto 05.11.: "Wisla as 1695???"): a world made
with FL26 opened on FL27. FL27 has 60 clubs of FL26 no more (Wisla Krakow 1695, Wolfsburg 232,
Leicester 204, CFR Cluj 1746, APOEL 2178...), so a NewLife league that had one as a club of the game
showed an empty "club 1695" and Build stopped on it. The release marks such a club a new club of its
own (Release.use_tables), so:

  lost()        finds the NewLife leagues with a club of the game the tables have not got,
  to_update()   offers them for Update my leagues,
  lineup()      (keeping the line-up) moves the club from in_game to the release's new clubs.

Checked with a fake release and tables; a league of our own (no NewLife) is left alone.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modstudio import newlife as N

N_OK = 0


def ok(name, cond):
    global N_OK
    assert cond, name
    N_OK += 1
    print("ok %2d - %s" % (N_OK, name))


class Rel:
    """the parts of Release lost() and lineup() use; the tables said 1695 is not in the game"""
    def __init__(self):
        self.meta = {"version": "1.6b4"}
        self.clubs = {"1695": {"in_game": "0", "country": "Poland", "league": "PKO"},
                      "1700": {"in_game": "1", "country": "Poland", "league": "PKO"},
                      "90001": {"in_game": "", "country": "Poland", "league": "PKO"}}
        self.used = []

    def use_tables(self, info):
        self.used.append(info)


def recipe():
    pko = {"name": "PKO", "newlife": {"version": "1.6b4", "key": ["Poland", "PKO"], "clubs": [90001]},
           "game_clubs": [{"id": 1695, "at": 0}, {"id": 1700, "at": 1}]}
    fine = {"name": "Fine", "newlife": {"version": "1.6b4", "key": ["Poland", "PKO"], "clubs": [90001]},
            "game_clubs": [{"id": 1700, "at": 0}]}
    own = {"name": "Own", "game_clubs": [{"id": 1695, "at": 0}]}
    return {"leagues": [pko, fine, own]}


def main():
    info = {"clubs": {1700: {}}, "base": "tables27"}
    r, rel = recipe(), Rel()
    ok("lost: the NewLife league with 1695, not the one without, not our own league",
       [x["name"] for x in N.lost(r, rel, info)] == ["PKO"])
    ok("lost reads the clubs by the tables in use", rel.used == [info])
    ok("no tables: nothing lost", N.lost(r, Rel(), None) == [] and N.lost(r, Rel(), {}) == [])
    ok("FL26's tables (1695 there): nothing lost", N.lost(r, Rel(), {"clubs": {1695: {}, 1700: {}}}) == [])
    ok("to_update offers it", [x["name"] for x in N.to_update(r, rel, info)] == ["PKO"])
    ok("to_update without tables as before", N.to_update(r, Rel()) == [])
    rows = [{"key": ["Poland", "PKO"], "clubs": ["90001", "1695", "1700"], "in_game": ["1700"]}]
    _L, E = N.lineup(rel, r["leagues"][0], rows, keep=True)
    ok("lineup: 1695 is a new club of the release now (%s)" % E["clubs"], E["clubs"] == ["1695", "90001"])
    ok("and no club of the game; 1700 still is (%s)" % E["in_game"], E["in_game"] == ["1700"])
    print("all passed")


if __name__ == "__main__":
    main()
