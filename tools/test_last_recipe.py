r"""python tools/test_last_recipe.py

B107 (jibibi 17.10.): a world deleted, then New world (left untouched), close and open Mod
Studio: the deleted world was open again. New world and Open did not touch settings
"last_recipe", which the next start opens. Now:
  - New world clears it, and the settings are saved;
  - Open (and adopt) of a recipe puts its path there, the copy Build keeps too;
  - opening the recipe it names already writes no settings;
  - a Project with no app (tests, tools) still works.
QT_QPA_PLATFORM=offscreen, a temp folder; no game.
"""
import json, os, sys, tempfile, types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication

N = 0
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def ok(name, cond):
    global N
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        N += 1


def main():
    QApplication.instance() or QApplication([])
    from modstudio.project import Project
    T = tempfile.mkdtemp(prefix="lastrec-")
    old = os.path.join(T, "_FL26Dale.json")
    other = os.path.join(T, "_FL26Other.json")
    for p, w in ((old, "_FL26Dale"), (other, "_FL26Other")):
        json.dump({"world": w, "leagues": []}, open(p, "w", encoding="utf-8"))
    saves = []
    app = types.SimpleNamespace(settings={"last_recipe": old}, save_settings=lambda: saves.append(1))
    P = Project(app)
    P.open(old)
    ok("opening the recipe last_recipe names writes no settings", saves == [])
    P.new()
    ok("New world clears last_recipe", app.settings["last_recipe"] is None)
    ok("... and saves the settings", len(saves) == 1)
    P.open(other)
    ok("Open puts the recipe in last_recipe", app.settings["last_recipe"] == other)
    P.open(old, copy=True)
    ok("Open of Build's kept copy puts that copy there", app.settings["last_recipe"] == old and P.path is None)
    P2 = Project(None)
    P2.new()
    P2.open(other)
    ok("a Project with no app works", P2.recipe.get("world") == "_FL26Other")
    # Undo / Redo (0.2.5) next to it: B107's helper first took the name of the undo step's one
    # and broke every change (touch)
    import time
    U = Project(None)
    U.open(other)
    for n in (1, 2, 3):
        U.recipe["n"] = n
        U.touch()
        time.sleep(0.35)               # touches within a third of a second are one step
    ok("three changes, three steps back", U.can_undo() and not U.can_redo())
    U.undo()
    U.undo()
    ok("undo twice: the first change", U.recipe.get("n") == 1 and U.can_redo())
    U.redo()
    ok("redo: the second", U.recipe.get("n") == 2)
    U.recipe["n"] = 9
    U.touch()
    ok("a change after undo cuts redo", not U.can_redo() and U.recipe.get("n") == 9)
    U.new()
    ok("New world forgets the steps", not U.can_undo() and not U.can_redo())
    print("ALL OK" if not N else "%d FAILED" % N)
    return N


if __name__ == "__main__":
    sys.exit(main())
