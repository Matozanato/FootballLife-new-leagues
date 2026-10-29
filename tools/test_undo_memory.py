"""python tools/test_undo_memory.py

Undo and Redo of the whole world (0.2.5) kept a full copy of the recipe for each of its 30
steps. A world of 1,300 new clubs is about 160 MB in memory, nearly all of it its players, so a
session of edits took Mod Studio past 11 GB (B267, JoJofiaz 29.10.2026). The steps are now kept
packed. This checks that Undo and Redo still give back exactly each state, and that a step costs
a small part of the recipe.

B270 (the same tester, the same night): copying the whole recipe on each change froze the window
for a Rating typed on Players. A change now costs a compare and a copy of what it touched; checked
here against a copy of the recipe, with keys and clubs added, removed and changing type.
"""
import os, pickle, sys, time

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
        if not ok_ or pr.recipe != pickle.loads(states[34 - k]):
            ok("Undo %d gives back the state before change %d" % (k + 1, 35 - k), False)
    ok("30 Undos give back each earlier state exactly", True)
    ok("a 31st Undo has nothing left", not pr.undo())
    ok("the pages keep the same recipe dict", pr.recipe is recipe_dict)
    for k in range(30):
        pr.redo()
    ok("30 Redos come back to the last state", pr.recipe == pickle.loads(after))
    ok("Redo steps are packed too", all(isinstance(b, bytes) for b in pr._undo + pr._redo))
    pr.undo()
    pr.recipe["edits"]["new"] = 1
    pr._snap_at = 0.0
    pr._remember()
    ok("a new change after Undo clears Redo", not pr.can_redo())
    by_club()
    print("%d cases passed" % N)


def by_club():
    """the recipe as Mod Studio keeps it: players by club"""
    pr = P.Project(App())
    r = big_recipe()
    clubs = {}
    for p in r["players"]:
        clubs.setdefault(str(p["club"]), []).append(p)
    r["players"] = clubs
    pr.recipe.clear()
    pr.recipe.update(r)
    pr._forget()
    t = time.perf_counter()
    pr._clone(pr.recipe)
    whole = time.perf_counter() - t
    before = pickle.dumps(pr.recipe, protocol=pickle.HIGHEST_PROTOCOL)
    pr.recipe["players"]["71213"][0]["ovr"] = 99
    pr._snap_at = 0.0
    t = time.perf_counter()
    pr._remember()
    one = time.perf_counter() - t
    ok("a Rating costs a small part of copying the world (%.3f s, a copy %.3f s)" % (one, whole), one * 3 < whole)
    ok("its step holds the one club", [(k, k2) for k, k2, _t, _v in pr._unpack(pr._undo[-1])] == [("players", "71213")])
    steps = len(pr._undo)
    pr.recipe["players"]["71213"][0]["ovr"] = 98                  # typed on within 0.3 s
    pr._remember()
    ok("touches close together stay one step", len(pr._undo) == steps)
    states = [before]
    edits = [lambda: pr.recipe["players"].pop("71214"),
             lambda: pr.recipe["players"].__setitem__("99999", [{"id": 1, "name": "New"}]),
             lambda: pr.recipe.__setitem__("stadiums", {"5": "Arena"}),
             lambda: pr.recipe.pop("edits"),
             lambda: pr.recipe.__setitem__("leagues", {"now": "a dict"}),
             lambda: pr.recipe.__setitem__("stadiums", ["a list now"])]
    for f in edits:
        states.append(pickle.dumps(pr.recipe, protocol=pickle.HIGHEST_PROTOCOL))
        f()
        pr._snap_at = 0.0
        pr._remember()
    last = pickle.loads(pickle.dumps(pr.recipe, protocol=pickle.HIGHEST_PROTOCOL))
    players = pr.recipe["players"]
    good = True
    for k in range(len(edits) + 1):
        pr.undo()
        good = good and pr.recipe == pickle.loads(states[len(edits) - k])
    ok("Undo gives back clubs and keys removed, added and changing type", good)
    ok("a club page keeps the same players dict", pr.recipe["players"] is players)
    while pr.redo():
        pass
    ok("Redo comes back to the last state", pr.recipe == last)
    pr.recipe["players"]["71213"][1]["name"] = "Not kept yet"
    pr.undo()
    ok("Undo takes back a change not yet kept first", pr.recipe["players"]["71213"][1]["name"] != "Not kept yet")


if __name__ == "__main__":
    main()
