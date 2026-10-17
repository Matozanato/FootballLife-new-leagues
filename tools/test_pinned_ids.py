"""python test_pinned_ids.py <folder with the game's tables> -- a league built before keeps its
competition, regulation and region ids when a league is added in front of it, removed before it
or the recipe is reordered (audit 12.10.: every league after a new one got new ids, and a career,
a Kit Server map.txt and the scoreboard map lost them). Team ids: test_pinned_ids.py ... --build
<game folder> builds the worlds in a temporary livecpk root of that game (nothing is switched on)."""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def league(name, country, clubs=16, **extra):
    L = {"name": name, "country": country, "clubs": clubs, "legs": 2}
    L.update(extra)
    return L


def ids(pl):
    return {p["name"]: (p["cid"], p["rid"], p["region"]) for p in pl["leagues"]}


def main(base):
    a = league("Pin Albania", "Albania", 10)
    b = league("Pin Bosnia", "Bosnia and Herzegovina", 12)
    c = league("Pin Bosnia 2", "Bosnia and Herzegovina", 12, above="Pin Bosnia")
    first = B.plan({"world": "_TestPins", "leagues": [a, b, c]}, base)
    one = ids(first)

    new = league("Pin Andorra", "Andorra", 10)
    again = B.plan({"world": "_TestPins", "leagues": [new, a, b, c]}, base, first)
    two = ids(again)
    ok("a league added in front: the others keep cid, rid and region",
       all(two[n] == one[n] for n in one))
    ok("the new league takes ids nobody had", two["Pin Andorra"][0] not in {v[0] for v in one.values()}
       and two["Pin Andorra"][1] not in {v[1] for v in one.values()})

    less = ids(B.plan({"world": "_TestPins", "leagues": [b, c]}, base, first))
    ok("a league removed before them: the others keep their ids", all(less[n] == one[n] for n in less))

    moved = ids(B.plan({"world": "_TestPins", "leagues": [c, a, b]}, base, first))
    ok("reordered: the same ids", all(moved[n] == one[n] for n in one))

    fresh = ids(B.plan({"world": "_TestPins", "leagues": [new, a, b, c]}, base))
    ok("without the last plan the old order of handing out stays (a first Build is unchanged)",
       fresh["Pin Andorra"][0] == one["Pin Albania"][0])

    renamed = dict(a, name="Pin Albania Renamed")
    r = ids(B.plan({"world": "_TestPins", "leagues": [renamed, b, c]}, base, first))
    ok("a renamed league is a new league (its old ids are not taken by another)",
       r["Pin Bosnia"] == one["Pin Bosnia"])

    # Mod Studio's Edit league... records the names before (project.rename_league: built_as)
    named = dict(a, name="Pin Albania Renamed", built_as=["Pin Albania"])
    r = ids(B.plan({"world": "_TestPins", "leagues": [new, named, b, c]}, base, first))
    ok("renamed in Mod Studio (built_as): the league keeps its cid, rid and region",
       r["Pin Albania Renamed"] == one["Pin Albania"] and r["Pin Bosnia"] == one["Pin Bosnia"])
    twice = dict(a, name="Pin Albania Third", built_as=["Pin Albania", "Pin Albania Renamed"])
    after = B.plan({"world": "_TestPins", "leagues": [named, b, c]}, base, first)
    r = ids(B.plan({"world": "_TestPins", "leagues": [twice, b, c]}, base, after))
    ok("renamed again after a Build under the new name: the ids of that Build",
       r["Pin Albania Third"] == ids(after)["Pin Albania Renamed"] == one["Pin Albania"])
    back = league("Pin Albania", "Albania", 10)
    r = ids(B.plan({"world": "_TestPins", "leagues": [named, back, b, c]}, base, first))
    ok("an old name another league has now: that league's own, not the renamed one's",
       r["Pin Albania"] == one["Pin Albania"] and r["Pin Albania Renamed"][0] != one["Pin Albania"][0])
    print("1..%d" % N)


if __name__ == "__main__":
    main(sys.argv[1])
