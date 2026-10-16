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
    # a league package's kit folder per club (lbservers): it stays with its club, not its place
    x["kit_folders"] = ["kit of %s" % i for i in x["newlife"]["clubs"]]
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
    old_ids = {str(i) for i in before["leagues"][1]["newlife"]["clubs"]}
    kits = (list(z.get("kit_folders") or []) + [""] * z["clubs"])[:len(z["newlife"]["clubs"])]
    assert kits == ["kit of %s" % i if str(i) in old_ids else "" for i in z["newlife"]["clubs"]], kits
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
    # a league package's kit folders stay with their clubs when the release's line-up moves them
    # (pepponeee98, 14.10.: they stayed by place, so clubs wore the next club's kit)
    r5 = {"world": "_FL26T", "leagues": [], "edits": {}, "players": {}}
    N.add_league(r5, old, dict(L, clubs=L["clubs"][1:]))
    x5 = r5["leagues"][0]
    x5["kit_folders"] = ["kit of %s" % i for i in x5["newlife"]["clubs"]]
    had = {str(i) for i in x5["newlife"]["clubs"]}
    N.update_league(r5, new, x5, rows_n, keep=False)
    z5 = r5["leagues"][0]
    ids = [str(i) for i in z5["newlife"]["clubs"]]
    assert set(ids) - had, "the release brings back the club left out"
    kits = (list(z5.get("kit_folders") or []) + [""] * len(ids))[:len(ids)]
    assert kits == ["kit of %s" % i if i in had else "" for i in ids], kits
    # B79: a club of the game whose place in the game another club took (newlife_game
    # "replaced") and which the person put in a league as a new club stays in it (16.10.: the
    # Modpack's Primera Federacion lost 3 such clubs, its Serie C 4) ...
    gone = next(i for i in sorted(new.clubs) if new.clubs[i].get("in_game") == "1" and i in old.clubs
                and not new.clubs[i].get("twin") and i not in L["clubs"] + L["in_game"])
    r6 = {"world": "_FL26T", "leagues": [], "edits": {}, "players": {},
          "newlife_game": {"version": old.meta["version"], "swaps": [], "clubs": [],
                           "replaced": {gone: {"name": "Another club", "abbr": "ANO"}}}}
    old.use_recipe(r6)                              # as the page has it: the club is a new club
    N.add_league(r6, old, dict(L, clubs=L["clubs"][:-1] + [gone]), custom=True)
    n6 = r6["leagues"][0]["clubs"]
    assert gone in [str(i) for i in r6["leagues"][0]["newlife"]["clubs"]]
    N.update_league(r6, new, r6["leagues"][0], rows_n)
    have = [str(i) for i in r6["leagues"][0]["newlife"]["clubs"]]
    assert gone in have and r6["leagues"][0]["clubs"] == n6, (gone, have)
    assert int(gone) not in [e["id"] for e in r6["leagues"][0].get("game_clubs") or []]
    # ... and a league the release lines up with that club of the game takes it as a new club,
    # not as the club of the game at a place another club has now
    new.use_recipe({"leagues": []})
    Lg = next(x for x in new.leagues(cty) if x["in_game"])
    t = Lg["in_game"][0]
    new.use_recipe({"leagues": [], "newlife_game": {"replaced": {t: {"name": "Another club"}}}})
    Lg2 = next(x for x in new.leagues(cty) if x["key"] == Lg["key"])
    assert t in Lg2["clubs"] and t not in Lg2["in_game"], (t, Lg2["clubs"], Lg2["in_game"])
    new.use_recipe({"leagues": []})
    assert new.clubs[t]["in_game"] == "1", "undone with the record"
    print("a club whose game place was taken stays a new club: %s, %s" % (new.clubs[gone]["name"], new.clubs[t]["name"]))
    print("all passed")


if __name__ == "__main__":
    main(*sys.argv[1:3])
