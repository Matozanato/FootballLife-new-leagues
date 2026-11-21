r"""python tools/test_b399_new_world.py

B399 (beta 10.11.): New world wrote over the recipe of a world of the same name. Every new world was
called _FL26MyWorld (project.blank), had no file of its own, and its first change was saved by itself
(autosave -> keep_copy) into recipes\_FL26MyWorld.json -- the recipe of the player's own world of
that name, the name most people keep: 55 leagues became one league of Malta. Now:
  - New world takes a name no world has: _FL26MyWorld, else _FL26MyWorld2, 3, ... (a recipe copy in
    recipes\, a world folder in livecpk, a world's folder in content\<server>);
  - the empty world of a first start too (a new APPDATA, a world _FL26MyWorld in the game): it is
    not taken for that world, and once the tables are there the world in the game opens;
  - keep_copy never writes over another world's recipe copy: it is moved aside to .prev (.prev2, ...
    never one kept before), and the status bar says where; the open world's own copy is written in
    place as before (no .prev), also after Rename world moved it;
  - Construction's World name field and Rename world refuse the name of another world's recipe copy;
  - a world kept in a file of its own: Build's copy of its name is moved to one .prev, not more.
The window in this process for the last part (QT_QPA_PLATFORM=offscreen), a fake game and APPDATA in
a temp folder. No game.
"""
import hashlib, json, os, shutil, sys, tempfile, time, types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.pop("FL26_DIR", None)
T = tempfile.mkdtemp(prefix="b399-")
os.environ["APPDATA"] = os.path.join(T, "appdata")      # before modstudio.app reads it (APPDIR)
os.environ["FL26_SAVE_ROOT"] = os.path.join(T, "konami")

from test_world_manage import make_game, put

N = 0
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def md5(p):
    with open(p, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def leagues(n):
    return [{"name": "League %d" % i, "clubs": 10} for i in range(n)]


def settle(qa, secs=0.3):
    t0 = time.time()
    while time.time() - t0 < secs:
        qa.processEvents()
        time.sleep(0.02)


def project_part(qa, game, copies):
    from modstudio.project import Project
    from modstudio.pages import roots as RP
    mine = os.path.join(copies, "_FL26MyWorld.json")
    put(mine, json.dumps({"world": "_FL26MyWorld", "leagues": leagues(55), "edits": {}, "players": {}}, indent=1))
    notes = []
    app = types.SimpleNamespace(settings={"last_recipe": mine}, save_settings=lambda: None,
                                status=notes.append, game=game)
    P = Project(app)
    P.open(mine, copy=True)
    ok("the player's world opens from its copy, its own", P.recipe["world"] == "_FL26MyWorld"
       and not P.copy_taken("_FL26MyWorld"))
    P.recipe["leagues"][0]["clubs"] = 12
    P.touch()
    P.autosave()
    ok("a change of the open world is saved in its own copy, nothing moved aside",
       json.load(open(mine, encoding="utf-8"))["leagues"][0]["clubs"] == 12
       and not [n for n in os.listdir(copies) if ".prev" in n] and not notes)
    before = md5(mine)

    # the bug: New world, a league, the autosave
    P.new()
    ok("New world: a free name, _FL26MyWorld2 (the copy _FL26MyWorld.json is another world's)",
       P.recipe["world"] == "_FL26MyWorld2" and P.copy_taken("_FL26MyWorld"))
    P.recipe["leagues"].append({"name": "Malta", "clubs": 10})
    P.touch()
    P.autosave()
    second = os.path.join(copies, "_FL26MyWorld2.json")
    ok("New world + a league + autosave: the old world's json is byte for byte the same",
       md5(mine) == before)
    ok("... the new world is in a copy of its own, and the next start opens it",
       os.path.exists(second) and len(json.load(open(second, encoding="utf-8"))["leagues"]) == 1
       and app.settings["last_recipe"] == second and not P.dirty)
    P.new()
    ok("New world once more: _FL26MyWorld3", P.recipe["world"] == "_FL26MyWorld3")

    # a world folder in the game, or a world's folder in content\<server>, takes a name as well
    from modstudio import project as PR
    empty = os.path.join(T, "empty-recipes")
    os.makedirs(empty)
    real = PR.Project.copies_dir
    PR.Project.copies_dir = lambda self: empty                       # a new APPDATA: no copies
    try:
        put(os.path.join(game.livecpk_dir, "_FL26MyWorld", "fl26world.txt"), "world _FL26MyWorld\r\n")
        first = Project(types.SimpleNamespace(settings={}, save_settings=lambda: None, game=game))
        ok("first start, new APPDATA, _FL26MyWorld in the game: the empty world is _FL26MyWorld2",
           first.recipe["world"] == "_FL26MyWorld2" and first.untouched())
        put(os.path.join(game.content_dir, "kit-server", "_FL26MyWorld2", "x.txt"), "kits")
        first.new()
        ok("... a world's kits folder takes a name too: _FL26MyWorld3", first.recipe["world"] == "_FL26MyWorld3")
        ok("a Project with no app: _FL26MyWorld, as before", Project(None).recipe["world"] == "_FL26MyWorld")
    finally:
        PR.Project.copies_dir = real
        shutil.rmtree(os.path.join(game.livecpk_dir, "_FL26MyWorld"))
        shutil.rmtree(os.path.join(game.content_dir, "kit-server", "_FL26MyWorld2"))

    # the safety net: an open world that takes another world's name all the same
    P.new()
    P.recipe["world"] = "_FL26MyWorld"
    P.recipe["leagues"].append({"name": "Malta", "clubs": 10})
    P.touch()
    P.autosave()
    ok("another world's copy is moved aside to .prev, byte for byte, not written over",
       md5(mine + ".prev") == before and json.load(open(mine, encoding="utf-8"))["leagues"][0]["name"] == "Malta")
    ok("... and the status bar says where it is", notes and mine + ".prev" in notes[-1])
    P.recipe["leagues"].append({"name": "Gozo", "clubs": 10})
    P.touch()
    P.autosave()
    ok("... after that the copy is the open world's own: written in place, no .prev2",
       not os.path.exists(mine + ".prev2") and md5(mine + ".prev") == before)
    malta = md5(mine)
    Q = Project(app)
    Q.recipe["world"] = "_FL26MyWorld"
    Q.recipe["leagues"].append({"name": "Iceland", "clubs": 10})
    Q.touch()
    Q.autosave()
    ok("one more: .prev2, the .prev kept before is not replaced",
       md5(mine + ".prev2") == malta and md5(mine + ".prev") == before)

    # a world kept in a file of its own: Build's copy of its name is that world's own from before
    own_file = os.path.join(T, "docs", "_FL26Usr.json")
    put(own_file, json.dumps({"world": "_FL26Usr", "leagues": leagues(2)}, indent=1))
    put(os.path.join(copies, "_FL26Usr.json"), json.dumps({"world": "_FL26Usr", "leagues": leagues(1)}))
    for session in (1, 2):
        U = Project(app)
        U.open(own_file)
        n = len(notes)
        U.keep_copy()                                                  # what Build does
        ok("own file, Build's copy (session %d): one .prev, no .prev2, nothing said" % session,
           os.path.exists(os.path.join(copies, "_FL26Usr.json.prev"))
           and not os.path.exists(os.path.join(copies, "_FL26Usr.json.prev2")) and len(notes) == n)

    # Rename world moves the open world's copy: still its own
    ren = os.path.join(copies, "_FL26Ren.json")
    put(ren, json.dumps({"world": "_FL26Ren", "leagues": leagues(3)}, indent=1))
    R = Project(app)
    app.project = R
    R.open(ren, copy=True)
    RP.rename_recipe(app, "_FL26Ren", "_FL26Ren2")
    ren2 = os.path.join(copies, "_FL26Ren2.json")
    R.recipe["leagues"].append({"name": "X", "clubs": 10})
    R.touch()
    R.autosave()
    ok("Rename: the renamed copy is the open world's own, saved in place (no .prev)",
       R.recipe["world"] == "_FL26Ren2" and not os.path.exists(ren) and not os.path.exists(ren2 + ".prev")
       and len(json.load(open(ren2, encoding="utf-8"))["leagues"]) == 4)
    return mine


def window_part(qa, game, copies):
    """the window: New world on the Leagues page, Construction's World name field, Rename world"""
    from modstudio import app as A, theme
    from modstudio import saves as SV, ui as U
    from modstudio.pages import builder as PB, roots as RP
    from PySide6 import QtWidgets
    SV.game_running = lambda: False
    U.info = lambda *a, **k: None
    PB.ask = lambda *a, **k: True
    errors = []
    RP.error = lambda parent, title, text: errors.append(text)
    from modstudio import game as G
    G.Game.running = staticmethod(lambda: (False, False))
    theme.apply(qa)
    ms = os.path.dirname(copies)
    os.makedirs(os.path.join(ms, "tables"), exist_ok=True)
    # a fresh start for the window: the player's world only
    for n in os.listdir(copies):
        if n != "_FL26MyWorld.json.prev":
            os.remove(os.path.join(copies, n))
    mine = os.path.join(copies, "_FL26MyWorld.json")
    os.replace(mine + ".prev", mine)                    # the 55 leagues again
    before = md5(mine)
    with open(os.path.join(ms, "settings.json"), "w", encoding="utf-8") as f:
        json.dump({"game": game.folder, "tables": os.path.join(ms, "tables"), "check_updates": False,
                   "last_recipe": mine, "tour": "0.2.4"}, f)
    w = A.Main()
    w.resize(1360, 820)
    settle(qa)
    P = w.project
    page = w.pages["NewLeagues"]
    was = P.recipe["world"]
    page.new_recipe()
    ok("the window's New world (open: %s): a free name, _FL26MyWorld2" % was,
       P.recipe["world"] == "_FL26MyWorld2")
    P.recipe["leagues"].append({"name": "Malta", "clubs": 10})
    P.touch()
    settle(qa, 2.2)                                      # the autosave a moment after the change
    ok("... a league, the autosave by itself: the old world's json is the same, the new one has its own",
       not P.dirty and md5(mine) == before and os.path.exists(os.path.join(copies, "_FL26MyWorld2.json")))
    said = []
    page.say = lambda text, kind=None: said.append((text, kind))
    page.world.setText("_FL26MyWorld")
    page.set_world()
    ok("Construction's World name: another world's recipe name is refused",
       P.recipe["world"] == "_FL26MyWorld2" and said and said[-1][1] == "err"
       and "another world called _FL26MyWorld" in said[-1][0] and page.world.text() == "_FL26MyWorld2")
    page.world.setText("_FL26MyWorld9")
    page.set_world()
    ok("... a free one is taken", P.recipe["world"] == "_FL26MyWorld9")
    page.world.setText("_FL26MyWorld2")
    page.set_world()
    ok("... and its own earlier name again (its own copy)", P.recipe["world"] == "_FL26MyWorld2")
    roots = w.pages["Roots"]
    QtWidgets.QInputDialog.getText = staticmethod(lambda *a, **k: ("_FL26MyWorld", True))
    n = len(errors)
    started = roots.rename_world("_FL26Old")
    ok("Rename world to the name of another world's recipe copy: refused, nothing renamed",
       not started and len(errors) == n + 1 and "another world called _FL26MyWorld" in errors[-1]
       and os.path.isdir(os.path.join(game.livecpk_dir, "_FL26Old")) and md5(mine) == before)
    # a first start with a new APPDATA: the empty world, then the tables come (auto unpack) and the
    # world in the game opens, its recipe read back from its plan (that needs the tables)
    P.new()
    ok("New world: untouched", P.untouched() and P.recipe["world"] not in ("_FL26Live",))
    def live_after_tables(w):
        # the recipe is read in the background: wait for it the way the window does
        import time as _t
        from PySide6.QtWidgets import QApplication as _QA
        w._live_after_tables()
        end = _t.time() + 60
        while getattr(w, "_live_reading", False) and _t.time() < end:
            _QA.processEvents()
            _t.sleep(0.01)
        ok("the read after the tables ended", not getattr(w, "_live_reading", False))
    import leaguebuilder
    real_rfp, real_base = leaguebuilder.recipe_from_plan, P.base
    leaguebuilder.recipe_from_plan = lambda plan, base: {"world": plan["world"], "leagues": leagues(1),
                                                         "edits": {}, "players": {}}
    try:
        P.base = os.path.join(ms, "tables")              # the tables are there now (an empty stand-in:
        P.blockSignals(True)                             # the pages that read them stay out of it)
        live_after_tables(w)
        ok("tables there, the empty world untouched: the world in the game opens (_FL26Live)",
           P.recipe["world"] == "_FL26Live" and os.path.exists(os.path.join(copies, "_FL26Live.json")))
        P.recipe["leagues"].append({"name": "Mine", "clubs": 10})
        live_after_tables(w)
        ok("... never over a world that is open already", P.recipe["leagues"][-1]["name"] == "Mine")
        # U4 10.11.: the empty world got its free name for the game found at the start (none, or
        # another one); the game folder picked in Settings then has a world of that very name
        P.new()
        P.recipe["world"] = "_FL26Live"
        live_after_tables(w)
        ok("the empty world named like the world in the game (game folder changed): that world opens",
           P.recipe["world"] == "_FL26Live" and len(P.recipe["leagues"]) == 1 and not P.untouched())
    finally:
        leaguebuilder.recipe_from_plan, P.base = real_rfp, real_base
        P.blockSignals(False)
    w.project.dirty = False
    w.close()
    settle(qa, 0.2)


def run():
    from PySide6.QtWidgets import QApplication
    qa = QApplication.instance() or QApplication([])
    game = make_game(T)
    copies = os.path.join(os.environ["APPDATA"], "FL26ModStudio", "recipes")
    os.makedirs(copies, exist_ok=True)
    project_part(qa, game, copies)
    window_part(qa, game, copies)


def main():
    try:
        run()
    finally:
        shutil.rmtree(T, ignore_errors=True)
    print("test_b399_new_world: ok (%d)" % N)


if __name__ == "__main__":
    main()
