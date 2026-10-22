"""python test_unknown_formation.py <folder with the game's tables> -- B105 (17.10., Dee Jay;
18.10. Micarodvzla22): a league from another pack named formation '161', which these tables do not
have, and Build stopped on "Liga 2: no formation '161'". Now the formation goes (the clubs play the
one their squad fits, as "Picked from each club's squad") and the plan's notes say so; a formation
the tables have stays."""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def main(base):
    good = B.formations(base)[0]["label"]
    ok("'161' is not a formation of these tables", B.formation_club(base, "161") is None)
    recipe = {"world": "_FL26B105",
              "leagues": [{"name": "Liga 2", "country": "Albania", "clubs": 10, "legs": 2, "formation": "161",
                           "club_formations": ["", "161", good]},
                          {"name": "Liga Bona", "country": "Andorra", "clubs": 10, "legs": 2, "formation": good}]}
    pl = B.plan(recipe, base)
    a, b = pl["leagues"]
    ok("the plan is made (Build does not stop)", len(pl["leagues"]) == 2)
    ok("the unknown league formation goes", a["formation"] == "")
    ok("the unknown club formation goes, the known one stays", a["club_formations"] == ["", "", good])
    ok("another league's formation stays", b["formation"] == good)
    notes = [t for t in pl["skipped"] if "161" in t]
    ok("the notes name the league and the formation (%d)" % len(notes),
       len(notes) == 2 and all(t.startswith("Liga 2:") for t in notes))
    ok("the plan's description shows them", "no formation '161'" in B.describe(pl))
    print("test_unknown_formation: ok (%d)" % N)


if __name__ == "__main__":
    main(sys.argv[1])
