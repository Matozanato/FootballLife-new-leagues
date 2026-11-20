r"""python tools/test_club_money_rename.py

D17 (FL Testovi, 20.11.2026, rc2): a league renamed with Edit league... kept its clubs' money under
the old name. The recipe's "club_money" (FL 2027: budget, fame, fans, keyed "<league>/<n>" like the
squads) was not renamed with the league, so after a Build the ten clubs of the renamed league had
lost their money and got the estimate. The same section stayed by place on Insert club, Remove club,
Move club and when a league's clubs were dropped: a club got the money of the club next to it.

Now every section keyed by a club of the league moves with the club (project.rename_in,
Project.shift_places, move_club, drop_league). Offline: a Project with no tables, no game, no window.
"""
import os, sys, types

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


def recipe():
    names = ["C%d" % i for i in range(12)]
    return {"world": "_FL26MoneyRen", "edits": {}, "leagues": [
        {"name": "Liga Uno", "country": "Albania", "clubs": 12, "legs": 2, "club_names": list(names)},
        {"name": "Liga Dos", "country": "Albania", "clubs": 12, "legs": 2, "above": "Liga Uno",
         "club_names": ["D%d" % i for i in range(12)]}],
        "players": {"Liga Uno/%d" % i: {"squad": ["p%d" % i]} for i in range(12)},
        "club_money": dict({"Liga Uno/%d" % i: {"budget": 1000 + i} for i in range(12)},
                           **{"Liga Dos/0": {"budget": 5}})}


def money(p, key):
    return (p.recipe["club_money"].get(key) or {}).get("budget")


def main():
    QApplication.instance() or QApplication([])
    from modstudio.project import Project, rename_in

    def project():
        p = Project(None)
        p.app = types.SimpleNamespace(settings={}, save_settings=lambda: None)
        p.recipe = recipe()
        return p

    p = project()
    p.recipe["leagues"][0]["name"] = "Superliga"
    p.rename_league("Liga Uno", "Superliga")
    cm = p.recipe["club_money"]
    ok("rename: the money goes with the league's new name",
       all(money(p, "Superliga/%d" % i) == 1000 + i for i in range(12)))
    ok("rename: nothing is left under the old name", not any(k.startswith("Liga Uno/") for k in cm))
    ok("rename: the squads too, the other league untouched",
       "Superliga/3" in p.recipe["players"] and money(p, "Liga Dos/0") == 5)

    r = recipe()
    rename_in(r, "Liga Uno", "Liga Uno")
    ok("rename to the same name changes nothing", r == recipe())

    p = project()
    ok("insert club before place 2", p.shift_places("Liga Uno", 2, 1))
    ok("insert: clubs above keep their money", money(p, "Liga Uno/0") == 1000 and money(p, "Liga Uno/1") == 1001)
    ok("insert: the new club has none (the estimate)", money(p, "Liga Uno/2") is None)
    ok("insert: the clubs below take theirs down one place",
       all(money(p, "Liga Uno/%d" % (i + 1)) == 1000 + i for i in range(2, 12)))

    p = project()
    ok("remove the club at place 4", p.shift_places("Liga Uno", 4, -1))
    ok("remove: its money goes with it, the next one keeps its own",
       money(p, "Liga Uno/4") == 1005 and money(p, "Liga Uno/10") == 1011 and money(p, "Liga Uno/11") is None
       and 1004 not in [v.get("budget") for v in p.recipe["club_money"].values()])

    p = project()
    p.recipe["leagues"][1]["clubs"] = 11
    p.recipe["leagues"][1]["club_names"] = p.recipe["leagues"][1]["club_names"][:11]
    p.recipe["club_money"].pop("Liga Dos/0")
    said = p.move_club("Liga Uno", 3, "Liga Dos")
    ok("move club: done (%s)" % said, said is None)
    ok("move club: its money moves with it to the end of the other league",
       money(p, "Liga Dos/11") == 1003 and money(p, "Liga Uno/3") == 1004 and money(p, "Liga Uno/11") is None)

    p = project()
    p.drop_league("Liga Uno", keep=10)
    ok("drop from place 10: the money of 10 and 11 goes, the rest stays",
       money(p, "Liga Uno/9") == 1009 and money(p, "Liga Uno/10") is None and money(p, "Liga Uno/11") is None)
    p.drop_league("Liga Uno")
    ok("drop all: no money left for the league", not any(k.startswith("Liga Uno/") for k in p.recipe["club_money"])
       and money(p, "Liga Dos/0") == 5)
    print("all %d passed" % N)


if __name__ == "__main__":
    main()
