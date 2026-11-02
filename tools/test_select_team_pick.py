r"""python tools/test_select_team_pick.py [folder with the game's tables]

A league takes the Select Team place of one of the game's "other" groups when its recipe says so
(select_team; vmican 02.11.: "a dropdown on the Build table to pick the others slot -- with the
South American world the Other South Americans slot is of no use"):
  1. without it nothing changes: one league gets a slot of its own, no group is hidden;
  2. "latam" puts the league on the Other Latin American Teams' slot (73), "europe" on 69,
     "africa" on 75, "other" on 71, whatever the league order, and the plan text says which
     group it hides;
  3. a league built before on another id moves there (the pick wins over the pin), and the
     league that held the id before goes elsewhere;
  4. two leagues on one group, an exhibition league, an unknown word and a "latam" pick in a
     world with CONMEBOL associations (they take their clubs from that group) stop the plan;
  5. a recipe read back from the plan keeps the pick.
The game's tables (default %APPDATA%\FL26ModStudio\tables). No game.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import leaguebuilder as B
import fl26world

N = 0
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def league(name, **kw):
    return dict({"name": name, "country": "Colombia", "clubs": 16, "legs": 2}, **kw)


def slots(pl):
    return {p["name"]: p["slot"] for p in pl["leagues"]}


def stops(r, base):
    try:
        B.plan(r, base)
    except (B.BuildError, B.PlanProblems) as e:
        return str(e) or repr(e)
    return None


def main(tables):
    deep = os.path.join(tables, "common", "etc", "pesdb")
    base = B.base_dir(deep if os.path.isdir(deep) else tables)

    plain = B.plan({"world": "_FL26Pick", "leagues": [league("Liga Uno"), league("Liga Dos")]}, base)
    s = slots(plain)
    ok("1. without a pick no league is on a group's place",
       not any(v in fl26world.POOL_SLOTS for v in s.values()))

    for key, want in fl26world.POOL_PICK.items():
        pl = B.plan({"world": "_FL26Pick", "leagues": [league("Liga Uno"), league("Liga Dos", select_team=key)]}, base)
        s = slots(pl)
        ok("2. %s: the second league is on slot %d, the first on a slot of its own" % (key, want),
           s["Liga Dos"] == want and s["Liga Uno"] not in fl26world.POOL_SLOTS)
        text = B.describe(pl)
        ok("2. %s: the plan says which group it hides" % key,
           "Liga Dos takes the place of the game's \"%s\"" % fl26world.POOL_SLOTS[want] in text)

    # 3. built before: Liga Uno held the Other Latin American Teams' id, Liga Dos had its own
    rid_latam = fl26world.pool_rid(fl26world.POOL_PICK["latam"])
    first = B.plan({"world": "_FL26Pick", "leagues": [league("Liga Uno"), league("Liga Dos")]}, base)
    prev = {"leagues": [dict(p) for p in first["leagues"]]}
    for p in prev["leagues"]:
        if p["name"] == "Liga Uno":
            p["rid"], p["slot"] = rid_latam, fl26world.DEFAULT_SLOT[rid_latam]
    r = {"world": "_FL26Pick", "leagues": [league("Liga Uno"), league("Liga Dos", select_team="latam")]}
    s = slots(B.plan(r, base, prev=prev))
    ok("3. the pick wins over the pin: Liga Dos on 73, Liga Uno moved off it",
       s["Liga Dos"] == 73 and s["Liga Uno"] != 73)

    why = stops({"world": "_FL26Pick", "leagues": [league("Liga Uno", select_team="latam"),
                                                    league("Liga Dos", select_team="latam")]}, base)
    ok("4. two leagues on one group stop the plan", why and "one each" in why)
    why = stops({"world": "_FL26Pick", "leagues": [league("Liga Uno", select_team="latam", exhibition=True)]}, base)
    ok("4. an exhibition league keeps its own place", why and "exhibition" in why)
    why = stops({"world": "_FL26Pick", "leagues": [league("Liga Uno", select_team="asia")]}, base)
    ok("4. an unknown word stops the plan", why and "select_team" in why)
    why = stops({"world": "_FL26Pick", "conmebol_associations": {"lib": [[5, 19]]},
                 "leagues": [league("Liga Uno", select_team="latam")]}, base)
    ok("4. the CONMEBOL associations keep the Other Latin American Teams' place", why and "associations" in why)

    pl = B.plan({"world": "_FL26Pick", "leagues": [league("Liga Uno", select_team="europe")]}, base)
    back = B.recipe_from_plan(pl, base)
    ok("5. the recipe read back from the plan keeps the pick",
       [L.get("select_team") for L in back["leagues"]] == ["europe"])
    print("all %d ok" % N)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.expandvars(r"%APPDATA%\FL26ModStudio\tables"))
