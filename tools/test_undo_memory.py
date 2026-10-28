"""python tools/test_undo_memory.py

Undo and Redo of the whole world (0.2.5) kept a full copy of the recipe for each of its 30
steps. A world of 1,300 new clubs is about 160 MB in memory, nearly all of it its players, so a
session of edits took Mod Studio past 11 GB (B267, JoJofiaz 29.10.2026). The steps are now kept
packed. This checks that Undo and Redo still give back exactly each state, and that a step costs
a small part of the recipe.
"""
import os, pickle, sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from modstudio import project as P

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


class App:
    settings = None


def big_recipe():
    players = [{"id": 900000 + i, "name": "Player %d" % i, "club": 71213 + i // 30,
                "pos": ["GK", "CB", "CMF", "CF"][i % 4], "ovr": 50 + i % 40,
                "stats": [60 + (i * k) % 30 for k in range(40)]} for i in range(40000)]
    return {"world": "_FL26UndoTest", "leagues": [{"name": "League %d" % i, "clubs": 18} for i in range(80)],
            "players": players, "edits": {}}


def main():
    pr = P.Project(App())
    pr.recipe.clear()
    pr.recipe.update(big_recipe())
    pr._forget()
    size = len(pickle.dumps(pr.recipe, protocol=pickle.HIGHEST_PROTOCOL))
    states = []
    for i in range(35):
        states.append(pickle.dumps(pr.recipe, protocol=pickle.HIGHEST_PROTOCOL))
        pr.recipe["edits"]["step"] = i
        pr.recipe["players"][i]["name"] = "Changed %d" % i
        pr._snap_at = 0.0                      # as if a third of a second had passed
        pr._remember()
    ok("30 steps are kept, no more", len(pr._undo) == 30)
    ok("each step is packed bytes, not a copy of the recipe", all(isinstance(b, bytes) for b in pr._undo))
    biggest = max(len(b) for b in pr._undo)
    ok("a step takes under a fifth of the recipe (%d of %d bytes)" % (biggest, size), biggest * 5 < size)
    after = pickle.dumps(pr.recipe, protocol=pickle.HIGHEST_PROTOCOL)
    recipe_dict = pr.recipe
    for k in range(30):
        ok_ = pr.undo()
        if not ok_ or pickle.dumps(pr.recipe, protocol=pickle.HIGHEST_PROTOCOL) != states[34 - k]:
            ok("Undo %d gives back the state before change %d" % (k + 1, 35 - k), False)
    ok("30 Undos give back each earlier state exactly", True)
    ok("a 31st Undo has nothing left", not pr.undo())
    ok("the pages keep the same recipe dict", pr.recipe is recipe_dict)
    for k in range(30):
        pr.redo()
    ok("30 Redos come back to the last state", pickle.dumps(pr.recipe, protocol=pickle.HIGHEST_PROTOCOL) == after)
    ok("Redo steps are packed too", all(isinstance(b, bytes) for b in pr._undo + pr._redo))
    pr.undo()
    pr.recipe["edits"]["new"] = 1
    pr._snap_at = 0.0
    pr._remember()
    ok("a new change after Undo clears Redo", not pr.can_redo())
    print("%d cases passed" % N)


if __name__ == "__main__":
    main()
