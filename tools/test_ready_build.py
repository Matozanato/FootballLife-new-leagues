r"""python tools/test_ready_build.py

B60 (16.10., our night test): while a ready world (installed from a zip, marked .modstudio) is in
the game, Build was off for every world, so NewLife or a new world could only be built after
putting another world of one's own in the game first. Now:
  - the ready world itself stays blocked: its steps are off and Build says it is built already;
  - another world (a new one, NewLife) may be built: its steps are on, and Build asks first,
    naming the ready world it switches off and how to bring it back; No stops it;
  - Check the plan switches nothing, so it runs without asking.

The whole window in this process (QT_QPA_PLATFORM=offscreen), a fake game folder and APPDATA in
a temp folder. No game.
"""
import json, os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.pop("FL26_DIR", None)
T = tempfile.mkdtemp(prefix="readybuild-")
os.environ["APPDATA"] = os.path.join(T, "appdata")
os.environ["FL26_SAVE_ROOT"] = os.path.join(T, "konami")

from test_world_manage import make_game, put

N = 0
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def main():
    try:
        run()
    finally:
        shutil.rmtree(T, ignore_errors=True)
    print("test_ready_build: ok (%d)" % N)


def run():
    from PySide6.QtWidgets import QApplication
    qa = QApplication.instance() or QApplication([])
    from modstudio import app as A, theme, saves as SV
    from modstudio.pages import builder as PB
    SV.game_running = lambda: False
    infos, asked = [], []
    PB.info = lambda parent, title, text: infos.append(text)
    theme.apply(qa)
    game = make_game(T)
    put(os.path.join(game.livecpk_dir, "_FL26Live", ".modstudio"), "{}")     # _FL26Live came from a zip
    ms = os.path.join(os.environ["APPDATA"], "FL26ModStudio")
    os.makedirs(os.path.join(ms, "tables"))
    with open(os.path.join(ms, "settings.json"), "w", encoding="utf-8") as f:
        json.dump({"game": game.folder, "tables": os.path.join(ms, "tables"), "check_updates": False}, f)
    w = A.Main()
    b = w.page("Build")
    ok("_FL26Live, the world in the game, is a ready world", b.ready_live() == ["_FL26Live"])

    # ---- the ready world open: blocked as before
    w.project.recipe["world"] = "_FL26Live"
    b.refresh()
    ok("the ready world open: Build and install off", not b.b_all.isEnabled())
    ok("... and plan, build, switch on off", not any(x.isEnabled() for x in b.steps[1:4]))
    ok("... the line says no Build needed", "no Build needed" in b.state.text())
    PB.ask = lambda *a, **k: asked.append(a) or True
    ok("Build on the ready world is blocked", b.ready_blocks() is True)
    ok("... with the note, not a question", len(infos) == 1 and "built already" in infos[0] and not asked)
    ok("Check the plan on the ready world is blocked too", b.ready_blocks(asks=False) is True)

    # ---- another world open (NewLife, a new world): allowed, after a question
    infos.clear()
    w.project.recipe["world"] = "_FL26MyWorld"
    b.refresh()
    ok("another world open: Build and install on", b.b_all.isEnabled())
    ok("... and plan, build, switch on on", all(x.isEnabled() for x in b.steps[1:4]))
    ok("... the line does not say no Build needed", "no Build needed" not in b.state.text())
    ok("Build of another world: Yes runs it", b.ready_blocks() is False)
    q = asked[-1][2] if asked else ""
    ok("... the question names the ready world, the world built and the way back: %r" % q[:80],
       "_FL26Live" in q and "_FL26MyWorld" in q and "Activate" in q and "careers" in q)
    ok("... and no note", not infos)
    PB.ask = lambda *a, **k: False
    ok("Build of another world: No stops it", b.ready_blocks() is True)
    n = len(asked)
    PB.ask = lambda *a, **k: asked.append(a) or False
    ok("Check the plan of another world runs without a question", b.ready_blocks(asks=False) is False
       and len(asked) == n)

    # ---- no ready world in the game: nothing asked
    os.remove(os.path.join(game.livecpk_dir, "_FL26Live", ".modstudio"))
    ok("no ready world: Build runs, nothing asked", b.ready_blocks() is False and len(asked) == n)
    w.close()


if __name__ == "__main__":
    main()
