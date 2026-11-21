r"""python tools/test_team_ids_by_name.py

B305 (evannoteven, #support 31.10.2026): on the Clubs page, after Insert club, the Team ID column
was a row off until the next Build -- the ids of the last Build were shown by place, and Insert
club moved every club under the new one a place down. The Build itself keeps a club's id by its
name (leaguebuilder.pinned_tid). The column goes by name now (project.built_team_ids).

Offline: no game, no window.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from modstudio.project import built_team_ids as ids

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


built = {"teams": [70001, 70002, 70003, 70004], "club_names": ["Alpha", "Beta", "Gamma", "Delta"]}
ok("nothing changed: the ids by place", ids(built, ["Alpha", "Beta", "Gamma", "Delta"], 4) == [70001, 70002, 70003, 70004])
ok("Insert club before the second: every club keeps its own id, the new one has none yet",
   ids(built, ["Alpha", "", "Beta", "Gamma", "Delta"], 5) == [70001, None, 70002, 70003, 70004])
ok("... and with a name typed for the new club",
   ids(built, ["Alpha", "Omega", "Beta", "Gamma", "Delta"], 5) == [70001, None, 70002, 70003, 70004])
ok("a club added last", ids(built, ["Alpha", "Beta", "Gamma", "Delta", ""], 5) == [70001, 70002, 70003, 70004, None])
ok("Remove club: the clubs under it keep their ids", ids(built, ["Alpha", "Gamma", "Delta"], 3) == [70001, 70003, 70004])
ok("names are compared as the Build compares them (case, spaces)",
   ids(built, [" alpha ", "BETA", "Gamma", "Delta"], 4) == [70001, 70002, 70003, 70004])
ok("two clubs swapped: the ids go with the clubs", ids(built, ["Beta", "Alpha", "Gamma", "Delta"], 4) == [70002, 70001, 70003, 70004])
ok("a club renamed where it stands still shows its place's id",
   ids(built, ["Alpha", "Beta United", "Gamma", "Delta"], 4) == [70001, 70002, 70003, 70004])
ok("no id is shown twice", len(set(x for x in ids(built, ["Alpha", "Alpha", "Gamma", "Delta"], 4) if x)) ==
   len([x for x in ids(built, ["Alpha", "Alpha", "Gamma", "Delta"], 4) if x]))
# clubs with no names of their own: by place, as the Build keeps them
plain = {"teams": [70001, 70002, 70003], "club_names": ["", "", ""]}
ok("unnamed clubs keep their places' ids", ids(plain, ["", "", ""], 3) == [70001, 70002, 70003])
ok("... a fourth one has none yet", ids(plain, ["", "", "", ""], 4) == [70001, 70002, 70003, None])
ok("a league not built yet: nothing", ids({}, ["Alpha"], 1) == [] and ids(None, ["Alpha"], 1) == [])
ok("a plan of before the names were kept: by place, as it was", ids({"teams": [1, 2]}, ["x", "y", "z"], 3) == [1, 2])
ok("a game club's place (no int id) shows none", ids({"teams": [70001, "g"], "club_names": ["Alpha", ""]}, ["Alpha", ""], 2) == [70001, None])
print("all %d passed" % N)
