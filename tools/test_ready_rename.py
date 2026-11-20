r"""python tools/test_ready_rename.py

B487 (pop1806 16.11.2026: "when I change the name of a league it makes a new league instead of
saving it"): a league of a ready world (a world from a zip) renamed with Edit league... BEFORE
"Make it editable..." ended up twice. Make it editable reads the recipe again from the world's
leaguebuilder-plan.json, where the league still has its old name, and carry_added (B146) put the
renamed one on at the end as a league the player had added: the plan's league under the old name
stayed, and the renamed one had no players.

Now the plan's league takes the new name (pages.myworld.carry_added -> project.rename_in, the
rename Edit league does): one league, under the player's name, with what the plan has for it, and
built_as = the old name, so Build gives it the ids it has. A league really added is carried as
before. Offline: a Project with no tables, recipes as dicts, no game, no window.
"""
import copy, os, sys, types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


W = "_FL26ReadyRen"


def plan_recipe():
    """what leaguebuilder.recipe_from_plan gives for the ready world: two tiers, the second under
    the first, a pre-season cup and a league package naming the top one, players of its clubs"""
    return {"world": W, "edits": {}, "leagues": [
        {"name": "Liga Uno", "country": "Albania", "clubs": 4, "legs": 2, "exchange": 2,
         "club_names": ["A", "B", "C", "D"], "logo": "uno.png"},
        {"name": "Liga Dos", "country": "Albania", "clubs": 4, "legs": 2, "exchange": 2, "above": "Liga Uno",
         "club_names": ["E", "F", "G", "H"]},
        {"name": "Other teams", "country": "", "clubs": 0, "others": "rest"}],
        "players": {"Liga Uno/0": {"squad": ["p1", "p2"]}, "Liga Uno/3": {"squad": ["p3"]},
                    "Liga Dos/1": {"squad": ["p4"]}, "12345": {"newlife_game": True}},
        "preseason_cups": [{"name": "Copa", "clubs": ["Liga Uno/0", "Liga Dos/1", 777]}],
        "packs": {"pk": {"leagues": ["Liga Uno"], "players": ["Liga Uno/3", "Liga Dos/1"]}}}


def main():
    QApplication.instance() or QApplication([])
    from modstudio.project import Project, rename_in
    from modstudio.pages.myworld import carry_added

    # the ready world open in Mod Studio: its recipe read from the plan, Edit league... renames
    p = Project(None)
    p.app = types.SimpleNamespace(settings={}, save_settings=lambda: None)
    p.recipe = plan_recipe()
    p.recipe["leagues"][0] = dict(p.recipe["leagues"][0], name="Superliga")    # LeagueDialog's league
    p.rename_league("Liga Uno", "Superliga")
    ok("Edit league... renamed it in the open recipe (built_as, players, the league under it)",
       p.league("Superliga")["built_as"] == ["Liga Uno"] and "Superliga/0" in p.recipe["players"]
       and p.league("Liga Dos")["above"] == "Superliga")
    # and the player adds a league of their own, under the renamed one
    p.recipe["leagues"].append({"name": "Liga Tres", "country": "Albania", "clubs": 4, "above": "Liga Dos"})
    before = copy.deepcopy(p.recipe)
    keep = copy.deepcopy(before)

    # Make it editable: the recipe read again from the plan (old name), then carry_added
    rec = plan_recipe()
    said = carry_added(before, rec)
    names = [L["name"] for L in rec["leagues"]]
    ok("one league under the new name, none under the old, no second copy",
       names.count("Superliga") == 1 and "Liga Uno" not in names)
    ok("the leagues as before, in their order, the added one at the end",
       names == ["Superliga", "Liga Dos", "Other teams", "Liga Tres"])
    top = rec["leagues"][0]
    ok("it is the plan's league (its clubs, its logo)", top["club_names"] == ["A", "B", "C", "D"]
       and top.get("logo") == "uno.png" and top["clubs"] == 4)
    ok("built_as = the old name: Build gives it the ids it has", top.get("built_as") == ["Liga Uno"])
    ok("its players' keys moved to the new name",
       rec["players"].get("Superliga/0") == {"squad": ["p1", "p2"]} and rec["players"].get("Superliga/3") == {"squad": ["p3"]}
       and not any(k.startswith("Liga Uno/") for k in rec["players"]))
    ok("the other players untouched", rec["players"].get("Liga Dos/1") == {"squad": ["p4"]}
       and rec["players"].get("12345") == {"newlife_game": True})
    ok("the lower tier's `above` follows", rec["leagues"][1]["above"] == "Superliga")
    ok("pre-season cups and league packages follow",
       rec["preseason_cups"][0]["clubs"] == ["Superliga/0", "Liga Dos/1", 777]
       and rec["packs"]["pk"]["leagues"] == ["Superliga"]
       and rec["packs"]["pk"]["players"] == ["Superliga/3", "Liga Dos/1"])
    ok("the league really added is still carried, under the renamed one's lower tier",
       rec["leagues"][3]["above"] == "Liga Dos" and rec["leagues"][3]["clubs"] == 4)
    ok("'Kept the leagues you added before' names only the added one, not the renamed one", said == ["Liga Tres"])
    ok("the recipe open before is not changed", before == keep)
    ok("run again: nothing more", carry_added(before, rec) == [] and len(rec["leagues"]) == 4)

    # renamed twice before Make it editable: the name in the plan is the one that counts
    b2 = plan_recipe()
    b2["leagues"][1] = dict(b2["leagues"][1], name="Liga B")
    rename_in(b2, "Liga Dos", "Liga B")
    b2["leagues"][1] = dict(b2["leagues"][1], name="Liga Segunda")
    rename_in(b2, "Liga B", "Liga Segunda")
    r2 = plan_recipe()
    ok("renamed twice: one league, the last name", carry_added(b2, r2) == []
       and [L["name"] for L in r2["leagues"]] == ["Liga Uno", "Liga Segunda", "Other teams"]
       and r2["leagues"][1]["built_as"] == ["Liga Dos"] and "Liga Segunda/1" in r2["players"])

    # renamed, then a new league given the old name: the old name is that league's own (as Build has it)
    b3 = plan_recipe()
    b3["leagues"][1] = dict(b3["leagues"][1], name="Liga Nueva")
    rename_in(b3, "Liga Dos", "Liga Nueva")
    b3["leagues"].append({"name": "Liga Dos", "country": "Albania", "clubs": 6})
    r3 = plan_recipe()
    ok("an old name a league has now is that league's: the renamed one is carried as added (as Build pins it)",
       carry_added(b3, r3) == ["Liga Nueva"] and [L["name"] for L in r3["leagues"]] == ["Liga Uno", "Liga Dos", "Other teams", "Liga Nueva"])

    # a league added and then renamed has a built_as the plan does not know: added, as before
    b4 = plan_recipe()
    b4["leagues"].append({"name": "Liga X", "country": "Albania", "clubs": 4, "built_as": ["Liga Y"]})
    r4 = plan_recipe()
    ok("an added league renamed is still an added league", carry_added(b4, r4) == ["Liga X"]
       and [L["name"] for L in r4["leagues"]][-1] == "Liga X")

    # B487 (pop1806 16.11., "I changed players' names, it did not apply"): the players and the edit
    # tab changed in the ready world before Make it editable go with it now (carry_edits)
    from modstudio.pages.myworld import carry_edits
    ok("nothing changed but a league's name: no edit carried", carry_edits(before, rec) == 0)
    b5 = plan_recipe()
    b5["edits"] = {"clubs": {"101": {"name": "Plan FC"}}, "swaps": [[1, 2]]}
    pristine = copy.deepcopy(b5)
    b5["leagues"][0] = dict(b5["leagues"][0], name="Superliga")
    rename_in(b5, "Liga Uno", "Superliga")
    b5["players"]["Superliga/0"] = {"squad": ["p1", "p2"], "edits": {"p1": {"name": "My Name"}}}
    b5["players"]["Liga Dos/2"] = {"edits": {"p9": {"name": "Another"}}}
    b5["edits"]["clubs"]["101"] = {"name": "My FC"}
    b5["edits"]["clubs"]["202"] = {"name": "Second FC"}
    b5["edits"]["swaps"].append([3, 4])
    b5["edits"]["leagues"] = {"17": {"name": "My game league"}}
    r5 = copy.deepcopy(pristine)
    carry_added(b5, r5)
    n5 = carry_edits(b5, r5)
    ok("a player renamed in a renamed league is carried, under the league's new name",
       r5["players"]["Superliga/0"]["edits"] == {"p1": {"name": "My Name"}} and r5["players"]["Superliga/0"]["squad"] == ["p1", "p2"])
    ok("a player of another league, and the plan's other players, as they are",
       r5["players"]["Liga Dos/2"] == {"edits": {"p9": {"name": "Another"}}} and r5["players"]["Liga Dos/1"] == {"squad": ["p4"]})
    ok("the edit tab: a club changed and one added, a swap added, a game league changed",
       r5["edits"]["clubs"] == {"101": {"name": "My FC"}, "202": {"name": "Second FC"}}
       and r5["edits"]["swaps"] == [[1, 2], [3, 4]] and r5["edits"]["leagues"] == {"17": {"name": "My game league"}})
    ok("counted: 2 players' entries, 2 clubs, 1 swap, 1 league kind", n5 == 6)
    ok("run again: nothing more", carry_edits(b5, r5) == 0)
    ok("nothing before (no recipe open): nothing", carry_edits({}, copy.deepcopy(pristine)) == 0)

    # Project.rename_league is rename_in on the open recipe, as it was
    q = Project(None)
    q.app = p.app
    q.recipe = plan_recipe()
    q.recipe["leagues"][0] = dict(q.recipe["leagues"][0], name="Superliga")
    q.rename_league("Liga Uno", "Superliga")
    plain = plan_recipe()
    plain["leagues"][0] = dict(plain["leagues"][0], name="Superliga")
    rename_in(plain, "Liga Uno", "Superliga")
    ok("Project.rename_league and rename_in do the same", q.recipe == plain)
    q.rename_league("Superliga", "Superliga")
    ok("a rename to the same name changes nothing", q.recipe == plain)
    print("test_ready_rename: ok (%d)" % N)


if __name__ == "__main__":
    main()
