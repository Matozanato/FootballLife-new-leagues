r"""python tools/test_carry_added.py

B146 (Tysonche35 18.10.): leagues added to a zip world before "Make it editable" were gone after it,
because the recipe is read again from the world's leaguebuilder-plan.json, which only has the
leagues the world was built with. carry_added puts the added ones back at the end of the new recipe.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from modstudio.pages.myworld import carry_added

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


before = {"world": "_FL26M2400E", "leagues": [
    {"name": "Premier League", "clubs": 20},
    {"name": "Ligue 3", "clubs": 16},
    {"others": True, "name": "Other teams"},
    {"clubs": 12},
    {"name": "Liga Portugal 2", "clubs": 18}]}
rec = {"world": "_FL26M2400E", "leagues": [{"name": "Premier League", "clubs": 20, "from": "plan"}]}
keep = json.loads(json.dumps(before))

got = carry_added(before, rec)
names = [L.get("name") for L in rec["leagues"]]
ok("the added leagues are said in order", got == ["Ligue 3", "Liga Portugal 2"])
ok("they go on at the end", names == ["Premier League", "Ligue 3", "Liga Portugal 2"])
ok("a league the plan has keeps the plan's copy", rec["leagues"][0].get("from") == "plan")
ok("'other teams' and a league with no name are not carried",
   "Other teams" not in names and len(names) == 3)
ok("the old recipe is not changed", before == keep)
ok("nothing twice when run again", carry_added(before, rec) == [] and len(rec["leagues"]) == 3)

rec2 = {"world": "_FL26M2400E"}
ok("a recipe with no leagues yet gets them", carry_added(before, rec2) == ["Premier League", "Ligue 3", "Liga Portugal 2"]
   and len(rec2["leagues"]) == 3)
ok("no old recipe (another world) carries nothing", carry_added({}, {"leagues": []}) == []
   and carry_added(None, {"leagues": []}) == [])
print("test_carry_added: ok (%d)" % N)
