"""python test_team_ids_stable.py <folder with the game's tables> -- pop1806, 14.11.2026: "the ids
must not change with every update". Measured on three builds of a pack: every club that was
renamed between two Builds got a new team id (the last Build's ids were kept by the club's name in
its league), and a Build later the id it had went to ANOTHER club -- so a kit, a crest or a face
somebody had made for that id turned up on the wrong club.

Now (leaguebuilder.pinned_tid, used_tids, prev_clubs):
  - a club renamed where it stands keeps its id;
  - a club moved to another league of the world keeps its id;
  - an id a club once had is never given to another club while a free one is left: the plan
    keeps them (retired_tids), Build after Build.

Builds of one world in a temporary game folder, each on top of the last, as the Build button does.
"""
import json, os, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B

N = 0
WORLD = "_FL26StableIds"


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def league(name, country, names):
    return {"name": name, "country": country, "clubs": len(names), "legs": 2, "club_names": list(names)}


def build(game, base, leagues):
    w = os.path.join(game, "SiderAddons", "livecpk", WORLD)
    prev = None
    if os.path.exists(os.path.join(w, "leaguebuilder-plan.json")):
        with open(os.path.join(w, "leaguebuilder-plan.json"), encoding="utf-8") as f:
            prev = json.load(f)
    B.build(B.plan({"world": WORLD, "leagues": leagues}, base, prev), base, game, True, log=lambda t: None)
    with open(os.path.join(w, "leaguebuilder-plan.json"), encoding="utf-8") as f:
        return json.load(f)


def ids(pl):
    """{club name: team id} of the whole world"""
    return {n: t for p in pl["leagues"] for n, t in zip(p["club_names"], p["teams"])}


def main(base):
    game = tempfile.mkdtemp(prefix="fl26-stable-")
    try:
        for d in ("livecpk", "modules", "content"):
            os.makedirs(os.path.join(game, "SiderAddons", d))
        with open(os.path.join(game, "SiderAddons", "sider.ini"), "w") as f:
            f.write("[sider]\n")
        A = ["Alba %d" % i for i in range(11)]
        D = ["Andor %d" % i for i in range(10)]
        i1 = ids(build(game, base, [league("Stable Albania", "Albania", A), league("Stable Andorra", "Andorra", D)]))
        ok("twenty-one new clubs, twenty-one ids", len(set(i1.values())) == 21)

        # Build 2: two clubs renamed where they stand, in both leagues
        A2, D2 = list(A), list(D)
        A2[3], D2[0] = "Alba Three FC", "Andor Zero"
        pl2 = build(game, base, [league("Stable Albania", "Albania", A2), league("Stable Andorra", "Andorra", D2)])
        i2 = ids(pl2)
        ok("a renamed club keeps its id", i2["Alba Three FC"] == i1["Alba 3"] and i2["Andor Zero"] == i1["Andor 0"])
        ok("and nobody else's id moved", all(i2[n] == i1[n] for n in i1 if n in i2))
        ok("nothing was retired by a rename", not pl2.get("retired_tids"))

        # Build 3: a club goes from one league to the other (the two swap a club), one is renamed again
        A3, D3 = list(A2), list(D2)
        A3[9], D3[9] = D2[9], A2[9]
        A3[3] = "Alba III"
        pl3 = build(game, base, [league("Stable Albania", "Albania", A3), league("Stable Andorra", "Andorra", D3)])
        i3 = ids(pl3)
        ok("two clubs that swapped leagues took their ids with them",
           i3["Andor 9"] == i1["Andor 9"] and i3["Alba 9"] == i1["Alba 9"])
        ok("renamed a second time: still the first id", i3["Alba III"] == i1["Alba 3"])
        ok("the others as they were", sorted(i3.values()) == sorted(i1.values()))

        # Build 4: a club is taken out (the league is one smaller), a league is added in front
        A4 = [n for n in A3 if n != "Alba 5"]
        front = ["Arme %d" % i for i in range(10)]
        pl4 = build(game, base, [league("Stable Armenia", "Armenia", front), league("Stable Albania", "Albania", A4),
                                 league("Stable Andorra", "Andorra", D3)])
        i4 = ids(pl4)
        gone = i1["Alba 5"]
        ok("a league added in front and a club taken out: every club that stayed keeps its id",
           all(i4[n] == i3[n] for n in i3 if n in i4))
        ok("the id of the club that left is retired, not given to a new club",
           gone in (pl4.get("retired_tids") or []) and gone not in i4.values())

        # Build 5: more new clubs; the retired id stays out, Build after Build
        more = ["Aze %d" % i for i in range(10)]
        pl5 = build(game, base, [league("Stable Armenia", "Armenia", front), league("Stable Albania", "Albania", A4),
                                 league("Stable Andorra", "Andorra", D3), league("Stable Azerbaijan", "Azerbaijan", more)])
        i5 = ids(pl5)
        ok("a Build later it is still nobody else's (it was the next club's before)",
           gone in (pl5.get("retired_tids") or []) and gone not in i5.values())
        ok("forty clubs, forty ids, the old ones unchanged",
           len(set(i5.values())) == 40 == len(i5) and all(i5[n] == i4[n] for n in i4))

        # Build 6: a club is added in a new place: an id nobody ever had
        A6 = A4 + ["Alba 5"]
        pl6 = build(game, base, [league("Stable Armenia", "Armenia", front), league("Stable Albania", "Albania", A6),
                                 league("Stable Andorra", "Andorra", D3), league("Stable Azerbaijan", "Azerbaijan", more)])
        i6 = ids(pl6)
        ok("everybody else as before", all(i6[n] == i5[n] for n in i5))
        ok("a new place gets an id nobody had", i6["Alba 5"] not in set(i5.values()))

        # a club REPLACED by another where it stood takes the place's id, as the Clubs page shows
        # it (project.built_team_ids); a club renamed AND moved in one go is a new club
        A7 = list(A6)
        A7[0] = "Somebody Else"
        i7 = ids(build(game, base, [league("Stable Armenia", "Armenia", front), league("Stable Albania", "Albania", A7),
                                    league("Stable Andorra", "Andorra", D3), league("Stable Azerbaijan", "Azerbaijan", more)]))
        ok("the Clubs page and the Build agree on a club renamed where it stands", i7["Somebody Else"] == i1["Alba 0"])

        # the functions by themselves
        prev = {"leagues": [{"name": "L", "teams": [70001, 70002, "g"], "club_names": ["One", "Two", "Game"]},
                            {"name": "M", "teams": [70003, 70004], "club_names": ["One", "Three"]}],
                "away_leagues": [{"name": "Z", "teams": [70010], "club_names": ["Zed"]}], "retired_tids": [70020]}
        ok("used_tids: the last Build's, the away leagues', the retired ones",
           B.used_tids(prev) == [70001, 70002, 70003, 70004, 70010, 70020] and B.used_tids(None) == [])
        ok("prev_clubs: a name two clubs share says nothing", B.prev_clubs(prev) == {"two": 70002, "three": 70004}
           and B.prev_clubs(None) == {})
    finally:
        shutil.rmtree(game, ignore_errors=True)
    print("1..%d" % N)


if __name__ == "__main__":
    main(sys.argv[1])
