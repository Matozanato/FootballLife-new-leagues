"""python tools/test_pack_merge.py

A league package that changes a club of the game the recipe already changes (lbpackage.add, B55):
a player both add is added once (by the id he asks for, else by name and birth date or age), the
package's "join" comes along, "remove" is the union of both, and remove() puts the recipe's own
changes back.
"""
import copy, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lbpackage as K

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def main():
    mine = {"edits": {"100": {"name": "Old Name"}},
            "add": [{"like": "100", "name": "José Pérez", "Age": "23"},
                    {"like": "100", "name": "Ivan Novi", "id": "250001", "Age": "19"}],
            "join": ["41234"], "remove": ["101", "102"], "newlife_game": True}
    recipe = {"world": "_FL26X", "leagues": [], "players": {"1924": copy.deepcopy(mine)}}
    piece = {"leagues": [], "players": {"1924": {
        "edits": {"100": {"name": "New Name"}, "103": {"Speed": "80"}},
        "add": [{"like": "103", "name": "Jose  PEREZ", "Age": "23", "Speed": "77"},   # the same man
                {"like": "103", "name": "Someone Else", "id": "250001"},              # asks for the same id
                {"like": "103", "name": "José Pérez", "Age": "31"},                   # a namesake, older
                {"like": "103", "name": "Brand New", "Age": "20"}],
        "join": ["41234", "55555", 66666, "55555"], "remove": ["102", "104"]}}}
    man = {"name": "Pack", "author": "a", "version": "1"}
    tag = K.add(recipe, man, piece, "store")
    c = recipe["players"]["1924"]
    names = [ch["name"] for ch in c["add"]]
    ok("a player both add is there once", len(c["add"]) == 4, )
    ok("in the recipe's place, the package's entry over it",
       names[:2] == ["Jose  PEREZ", "Someone Else"] and c["add"][0]["Speed"] == "77" and c["add"][1]["id"] == "250001")
    ok("a namesake of another age and a new player are added", names[2:] == ["José Pérez", "Brand New"])
    ok("the package's join comes along, once each", c["join"] == ["41234", "55555", 66666])
    ok("remove is both", c["remove"] == ["101", "102", "104"])
    ok("edits: the package's win, the recipe's others stay",
       c["edits"] == {"100": {"name": "New Name"}, "103": {"Speed": "80"}})
    ok("the recipe's flag stays", c.get("newlife_game") is True)
    ok("the piece itself is not changed", piece["players"]["1924"]["join"] == ["41234", "55555", 66666, "55555"]
       and len(piece["players"]["1924"]["add"]) == 4)
    K.add(recipe, man, piece, "store")
    c = recipe["players"]["1924"]
    ok("added again: the same, not twice", len(c["add"]) == 4 and c["join"] == ["41234", "55555", 66666])
    K.remove(recipe, tag)
    ok("removed: the recipe's own changes are back", recipe["players"]["1924"] == mine)
    fresh = {"world": "_FL26X", "leagues": [], "players": {}}
    K.add(fresh, man, piece, "store")
    ok("a club the recipe does not change takes the package's as they are",
       fresh["players"]["1924"] == piece["players"]["1924"])
    print("pack merge: ok")


if __name__ == "__main__":
    main()
