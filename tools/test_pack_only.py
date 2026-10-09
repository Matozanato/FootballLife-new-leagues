"""python tools/test_pack_only.py

Adding only some leagues of a league package (lbpackage.only): the leagues picked, every league
of the package they sit below, and only their players; changes to the game's own clubs stay.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lbpackage as K

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def main():
    piece = {"leagues": [{"name": "A"}, {"name": "B", "above": "A"}, {"name": "C", "above": "B"},
                         {"name": "D", "above": "155"}],
             "players": {"A/0": 1, "B/0": 2, "C/1": 3, "D/0": 4, "12345": 5}, "edits": {"clubs": {"1": {}}}}
    q, b = K.only(piece, ["A"])
    ok("one league", [L["name"] for L in q["leagues"]] == ["A"] and b == [])
    ok("only its players and the game's clubs", sorted(q["players"]) == ["12345", "A/0"])
    ok("edits kept", q["edits"] == piece["edits"])
    q, b = K.only(piece, ["C"])
    ok("a lower league brings the ones above it", [L["name"] for L in q["leagues"]] == ["A", "B", "C"] and b == ["A", "B"])
    q, b = K.only(piece, ["D"])
    ok("below a league of the game: alone", [L["name"] for L in q["leagues"]] == ["D"] and b == [])
    ok("piece itself unchanged", len(piece["leagues"]) == 4 and len(piece["players"]) == 5)
    print("%d cases passed" % N)


if __name__ == "__main__":
    main()
