"""python test_newlife_fill.py -- a prototype player who stays at a NewLife club comes to the
club's level (Risto 04.10.: clubs under 18 players had a top club's clones). B299 (Risto 30.10.):
one with no rated player to go by, at its club or in its league, comes to its division's level"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lbplayers as N
import lbplayers as P
import playeredit as E


def main():
    assert N.fill_level([60, 62, 64, 70, 75], []) == 62
    assert N.fill_level([80], [55, 58, 60, 66]) == 58, "too few of its own: the league's"
    assert N.fill_level([], []) is None
    row = {n: "77" for n, _b in E.ABILITIES}
    row["Registered Position"] = "CF"
    got = dict(row, **N.at_level(row, 62))
    assert P.overall(got) == 62, P.overall(got)
    b299()
    print("all passed")


class Proto:
    """stand-in tables: a 30-man squad of clones at 78, as a top club's"""
    def __init__(self, _base):
        pass

    def proto(self, per=None):
        r = {n: "78" for n, _b in E.ABILITIES}
        r["Registered Position"] = "CB"
        return [dict(r) for _ in range(N.SQUAD)]


def b299():
    was = N.Squads
    N.Squads = Proto
    try:
        top = {"name": "Polish First Division", "rid": "a", "newlife": {"clubs": [1]}}
        third = {"name": "Polish Third Division Group 4", "rid": "c", "above": "b", "newlife": {"clubs": [1, 2, 3]}}
        second = {"name": "Polish Second Division", "rid": "b", "above": "a"}
        fourth = {"name": "Polish Fourth Division", "rid": "d", "above": "c", "newlife": {"clubs": [1, 2]}}
        rated = {"Registered Position": "CB"}
        rated.update({n: "60" for n, _b in E.ABILITIES})
        players = {
            "Polish First Division/0": {"edits": {"0": dict(rated)}, "join": ["x/0/0"]},
            # a club of the third division with an empty squad and none rated in its league
            "Polish Third Division Group 4/0": {"edits": {}},
            "Polish Third Division Group 4/1": {"edits": {}, "remove": ["5"]},
            # the game's players fill its places: not touched
            "Polish Third Division Group 4/2": {"join": ["y/0/0"]},
            # no entry at all (a league whose squads never came from the release)
        }
        pl = {"leagues": [top, second, third, fourth], "players": players}
        said = []
        out = N.fill_newlife(pl, "nowhere", said.append)
        assert pl["players"] is players and players["Polish Third Division Group 4/0"] == {"edits": {}},             "the plan is left as it was"
        c = out["Polish Third Division Group 4/0"]["edits"]
        assert len(c) == N.SQUAD and all(P.overall(dict(Proto(0).proto()[0], **e)) == N.TIER_LEVEL[2]
                                         for e in c.values()), "third division: 63, not 78"
        c = out["Polish Third Division Group 4/1"]["edits"]
        assert "5" not in c and len(c) == N.SQUAD - 1, "a removed place stays removed"
        assert "edits" not in out["Polish Third Division Group 4/2"], "the game's players' club is left alone"
        for k in (0, 1):
            c = out["Polish Fourth Division/%d" % k]["edits"]
            assert all(P.overall(dict(Proto(0).proto()[0], **e)) == N.TIER_LEVEL[3] for e in c.values()),                 "a club with no entry gets one: fourth division, 60"
        c = out["Polish First Division/0"]["edits"]
        assert all(P.overall(dict(Proto(0).proto()[0], **e)) == 60 for k, e in c.items() if k != "0"),             "a club with a rated player: its own level, as before"
        assert any("division's level" in s for s in said) and any("club's level" in s for s in said), said
    finally:
        N.Squads = was


if __name__ == "__main__":
    main()
