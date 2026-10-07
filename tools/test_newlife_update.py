"""python test_newlife_update.py <NewLife 1.2 folder> <NewLife 1.3 folder> -- a league added from
one NewLife version, brought to the next with Update my leagues to this version: the release's
clubs and squads, and the league's own settings and what was set for a club that stays kept
(0.1.8: before, the league had to be removed and added again by hand)"""
import copy, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modstudio import newlife as N
import lbplayers as P


def league(rel, rows, name):
    return next(L for L in rows if L["name"] == name)


def main(old_dir, new_dir):
    old, new = N.Release(old_dir), N.Release(new_dir)
    cty = lambda c: "Country %s" % c
    rows_o, rows_n = old.leagues(cty), new.leagues(cty)
    want = "Polish Second Division"
    L = league(old, rows_o, want)
    r = {"world": "_FL26T", "leagues": [], "edits": {}, "players": {},
         "preseason_cups": [{"name": "Cup", "clubs": []}]}
    first = {"name": "First", "country": "X", "clubs": 10, "legs": 2}
    r["leagues"].append(first)
    name, _a, _b = N.add_league(r, old, L)
    x = r["leagues"][1]
    assert x["newlife"]["key"] == list(L["key"]) and x["newlife"]["version"] == old.meta["version"]
    # the person's settings
    x.update({"above": "First", "europe": [{"place": 1, "to": "UECL"}], "formation": "4-4-2"})
    x["club_coaches"] = ["Coach %d" % k for k in range(x["clubs"])]
    x["club_crests"] = [None] * x["clubs"]
    x["club_crests"][0] = r"C:\my\crest.png"
    r["players"][P.new_key(name, 0)]["stadium"] = {"id": 7}
    eds = r["players"][P.new_key(name, 0)]["edits"]
    faced = {}                                      # #111: faces linked on the Players page stay
    for k, ch in eds.items():
        ch["face"] = "faces/%s" % k
        faced[ch.get("name") or k] = ch["face"]
    r["preseason_cups"][0]["clubs"] = [P.new_key(name, 0), "First/3"]
    kept_club = str(x["newlife"]["clubs"][0])
    before = copy.deepcopy(r)

    assert N.outdated(r, new) == [x]
    got, _s, _e, notes = N.update_league(r, new, x, rows_n)
    z = r["leagues"][1]
    assert got == name and z["name"] == name and r["leagues"][0] is first
    assert z["newlife"]["version"] == new.meta["version"]
    assert z["above"] == "First" and z["europe"] == [{"place": 1, "to": "UECL"}] and z["formation"] == "4-4-2"
    Ln = league(new, rows_n, want)
    assert sorted(str(i) for i in z["newlife"]["clubs"]) == sorted(Ln["clubs"]), "the release's line-up"
    assert z["clubs"] == len(Ln["clubs"]) + len(Ln["in_game"])
    assert len(z["club_names"]) == len(z["newlife"]["clubs"])
    if kept_club in [str(i) for i in z["newlife"]["clubs"]]:
        j = [str(i) for i in z["newlife"]["clubs"]].index(kept_club)
        assert z["club_coaches"][j] == "Coach 0", z.get("club_coaches")
        assert z["club_crests"][j] == r"C:\my\crest.png"
        assert r["players"][P.new_key(name, j)]["stadium"] == {"id": 7}
        now = r["players"][P.new_key(name, j)]["edits"]
        stay = [n for n in faced if any(P.same_name(e.get("name", ""), n) for e in now.values()) or n in now]
        got_face = [n for n in stay if any(e.get("face") == faced[n] for e in now.values())]
        assert stay and got_face == stay, (stay, got_face)
        print("faces kept: %d of %d players who stayed" % (len(got_face), len(faced)))
        assert r["preseason_cups"][0]["clubs"] == [P.new_key(name, j), "First/3"]
    for k in range(len(z["newlife"]["clubs"])):
        assert r["players"][P.new_key(name, k)]["edits"], "a squad for every club"
    assert not any(key.startswith(name + "/") and int(key.rpartition("/")[2]) >= z["clubs"] for key in r["players"])
    assert N.outdated(r, new) == []
    old_names = set(before["leagues"][1]["club_names"])
    print("%s: %d -> %d clubs, %d new, %d gone; notes: %s" % (
        want, before["leagues"][1]["clubs"], z["clubs"], len(set(z["club_names"]) - old_names),
        len(old_names - set(z["club_names"])), notes))

    # a line-up the person made stays
    r2 = {"world": "_FL26T", "leagues": [], "edits": {}, "players": {}}
    E = dict(L, clubs=L["clubs"][:-1])
    N.add_league(r2, old, E, custom=True)
    N.update_league(r2, new, r2["leagues"][0], rows_n)
    have = {str(i) for i in r2["leagues"][0]["newlife"]["clubs"]}
    assert have <= set(E["clubs"]) and r2["leagues"][0]["newlife"]["custom"]

    # a league added before 0.1.8 (no key): the league most of its clubs are in
    r3 = {"world": "_FL26T", "leagues": [], "edits": {}, "players": {}}
    N.add_league(r3, old, L)
    del r3["leagues"][0]["newlife"]["key"]
    assert N.keeps_lineup(r3["leagues"][0]), "nothing says its clubs were not picked by hand"
    N.update_league(r3, new, r3["leagues"][0], rows_n, keep=False)
    assert sorted(str(i) for i in r3["leagues"][0]["newlife"]["clubs"]) == sorted(Ln["clubs"])

    # a club of the builder's own the person put in, before a club of the game: both stay
    r4 = {"world": "_FL26T", "leagues": [], "edits": {}, "players": {}}
    N.add_league(r4, old, dict(L, clubs=L["clubs"][:12]))
    x4 = r4["leagues"][0]
    x4["clubs"] = 14
    x4["club_names"] += ["My Own FC"]
    x4["game_clubs"] = [{"at": 13, "id": 2525, "replace": 77}]
    r4["players"][P.new_key(x4["name"], 12)] = {"edits": {"0": {"name": "Mine"}}}
    N.update_league(r4, new, x4, rows_n, keep=True)
    z4 = r4["leagues"][0]
    m = len(z4["newlife"]["clubs"])
    assert z4["clubs"] == m + 2, z4["clubs"]
    assert z4["club_names"][m] == "My Own FC", z4["club_names"]
    assert r4["players"][P.new_key(x4["name"], m)] == {"edits": {"0": {"name": "Mine"}}}
    assert z4["game_clubs"] == [{"at": m + 1, "id": 2525, "replace": 77}], z4["game_clubs"]
    print("all passed")


if __name__ == "__main__":
    main(*sys.argv[1:3])
