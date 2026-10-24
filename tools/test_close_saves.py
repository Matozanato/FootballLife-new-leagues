r"""python tools/test_close_saves.py

Closing Mod Studio asked "Unsaved changes" while the status bar said "Your world is saved"
(970f514 in Spanish, 23.10.): the Players page set the world's dirty flag by itself, so the
autosave never came round for its changes. Project.mark() keeps and saves such a change, and
closing saves a change of the last moment instead of asking; only a write that fails still asks.
No game, no window on screen (offscreen)."""
import json, os, shutil, sys, tempfile, types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def main():
    qa = QApplication.instance() or QApplication([])
    from modstudio.project import Project
    from modstudio import app as A
    tmp = tempfile.mkdtemp(prefix="fl26_close_")
    try:
        app = types.SimpleNamespace(settings={}, save_settings=lambda: None)
        p = Project(app)
        p.path = os.path.join(tmp, "w.json")
        p.save()
        seen = []
        p.changed.connect(lambda: seen.append("changed"))
        p.players()["7"] = {"join": ["123"]}
        p.mark()
        ok("mark: the world is marked changed", p.dirty)
        ok("mark: the autosave is on its way", p._timer.isActive())
        ok("mark: no changed signal (the Players page is not filled again)", seen == [])
        ok("mark: the change can be undone", p.can_undo())
        p.autosave()
        ok("autosave: the change is in the file and the world saved",
           not p.dirty and json.load(open(p.path, encoding="utf-8"))["players"]["7"] == {"join": ["123"]})

        src = open(os.path.join(HERE, "modstudio", "pages", "players.py"), encoding="utf-8").read()
        ok("players.py: no change sets dirty by itself any more", "project.dirty = True" not in src)

        class Win(A.Main):
            def __init__(self, project):              # the window without the rest of Main
                QMainWindow.__init__(self)
                self.project, self.settings = project, {}

            def save_settings(self):
                pass

        asked = []
        real = QMessageBox.exec
        QMessageBox.exec = lambda box: asked.append(box.text()) or QMessageBox.Cancel
        try:
            p.players()["8"] = {"join": ["456"]}
            p.mark()
            w = Win(p)
            e = QCloseEvent()
            w.closeEvent(e)
            ok("close: a change of the last moment is saved without a question",
               asked == [] and e.isAccepted() and not p.dirty
               and "8" in json.load(open(p.path, encoding="utf-8"))["players"])

            p.path = os.path.join(tmp, "no such folder", "w.json")   # a write that fails
            p.players()["9"] = {}
            p.mark()
            e = QCloseEvent()
            w.closeEvent(e)
            ok("close: a write that fails still asks (and Cancel keeps it open)",
               len(asked) == 1 and not e.isAccepted() and p.dirty)
        finally:
            QMessageBox.exec = real
            p._timer.stop()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("1..%d" % N)


if __name__ == "__main__":
    main()
