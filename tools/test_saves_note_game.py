r"""python tools/test_saves_note_game.py

Settings > Master League careers names the folder the careers are switched in: FL26's KONAMI one,
FL27's SPGAME one. The note was written once, when the window opened, so after Settings > Game
folder was switched to the other game it still named the first game's folder (UI test of the
0.3.0 candidate 02.11.: FL27 first, then E: with FL26, the note said ...\SPGAME\Football Life\2027).
The switch of the saves itself always used the right folder (saves.root() at the time).

The whole window in this process (QT_QPA_PLATFORM=offscreen), fake FL26 and FL27 game folders and
APPDATA in a temp folder. Nothing is written in Documents (no world is switched).
"""
import json, os, shutil, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.pop("FL26_DIR", None)
os.environ.pop("FL26_SAVE_ROOT", None)
T = tempfile.mkdtemp(prefix="savesnote-")
os.environ["APPDATA"] = os.path.join(T, "appdata")      # before modstudio.app reads it (APPDIR)

from test_world_manage import make_game

N = 0
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def settle(qa, secs=0.5):
    t0 = time.time()
    while time.time() - t0 < secs:
        qa.processEvents()
        time.sleep(0.02)


def main():
    try:
        from PySide6.QtWidgets import QApplication
        qa = QApplication.instance() or QApplication([])
        from modstudio import app as A, game as G, saves, theme
        theme.apply(qa)
        g26 = make_game(T).folder
        g27 = os.path.join(T, "game27")
        shutil.copytree(g26, g27)
        os.remove(os.path.join(g27, "FL_2026.exe"))
        open(os.path.join(g27, G.FL27_EXE), "wb").write(b"MZ")
        ms = os.path.join(os.environ["APPDATA"], "FL26ModStudio")
        os.makedirs(os.path.join(ms, "tables"), exist_ok=True)
        with open(os.path.join(ms, "settings.json"), "w", encoding="utf-8") as f:
            json.dump({"game": g27, "check_updates": False, "tour": "0.2.4", "support": "9"}, f)
        w = A.Main()
        w.show()
        settle(qa)
        st = w.page("Settings")
        st.refresh()
        note = st.saves_note.text()
        ok("FL27 first: the note names FL27's save folder (%s)" % saves.root(),
           G.SAVE_DIR_FL27 in note and saves.root() in note)
        st.set_game(g26)
        settle(qa)
        note = st.saves_note.text()
        ok("switched to FL26: the note names FL26's (%s), not FL27's" % saves.root(),
           G.SAVE_DIR in note and G.SAVE_DIR_FL27 not in note and saves.root() in note)
        st.set_game(g27)
        settle(qa)
        ok("and back to FL27: FL27's again", G.SAVE_DIR_FL27 in st.saves_note.text())
        w.close()
        settle(qa, 0.2)
    finally:
        shutil.rmtree(T, ignore_errors=True)
    print("test_saves_note_game: ok (%d)" % N)


if __name__ == "__main__":
    main()
