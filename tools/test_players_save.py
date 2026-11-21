r"""python tools/test_players_save.py

pop1806, 14.11.2026: on the Players page a name typed for a player was taken when the field was
left -- nothing to press, nothing that said it had been kept. The page has a Save button now
(Players.save_player): what is typed and not taken yet is taken, the world is written to its
file at once, and the page says "Saved. The game shows it after Build."

The page's own method on a stand-in with no window; no game, no tables (offscreen).
"""
import json, os, shutil, sys, tempfile, types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication, QLineEdit, QSpinBox

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def main():
    qa = QApplication.instance() or QApplication([])
    from modstudio.project import Project
    from modstudio.pages import players as PP
    import inspect
    src = inspect.getsource(PP.Players)
    ok("the page has a Save button beside Undo, wired to save_player",
       'self.b_save = QPushButton(_("Save"))' in src and "self.b_save.clicked.connect(self.save_player)" in src
       and "row(self.b_save, self.b_undo)" in src)
    for lang in ("es", "fr", "pt", "hr"):
        with open(os.path.join(HERE, "modstudio", "lang", lang + ".json"), encoding="utf-8") as f:
            text = json.load(f)["text"]
        ok("%s: Save, its hint and both answers are translated" % lang,
           all(text.get(k) and text[k] != k for k in
               ("Save", "Saved. The game shows it after Build.",
                "Keep what you changed for this player now. The game shows it after Build.",
                "Could not save your world: check the folder it is saved in.")))

    class Page:
        save_player = PP.Players.save_player
    tmp = tempfile.mkdtemp(prefix="fl26-psave-")
    try:
        p = Project(types.SimpleNamespace(settings={}, save_settings=lambda: None))
        p.recipe["leagues"] = [{"name": "L", "clubs": 10, "club_names": ["A"]}]
        path = os.path.join(tmp, "world.json")
        p.save(path)
        page = Page()
        page.project, page._filling, page.cur, page.club = p, False, "3", "L/0"
        name, shirt, age = QLineEdit(), QLineEdit(), QSpinBox()
        page.ed = {"name": name, "shirt": shirt, "Age": age}
        taken, said = [], []

        def edited(key):
            taken.append(key)
            p.players().setdefault("L/0", {}).setdefault("edits", {}).setdefault("3", {})[key] = page.ed[key].text()
            p.mark()
        page.edited, page.say = edited, lambda t, kind="": said.append((t, kind))

        # a name typed, the field not left yet: Save takes it and writes the world
        name.setText("old")                       # filled by the page: not "typed"
        name.insert(" name typed")                # typed by the person
        ok("the field knows it was typed in", name.isModified() and not shirt.isModified())
        page.save_player()
        ok("Save takes the field that was typed in, and only that one", taken == ["name"])
        ok("the world's file has it at once", json.load(open(path, encoding="utf-8"))["players"]["L/0"]["edits"]["3"]["name"]
           == "old name typed" and not p.dirty)
        ok("and the page says so", said[-1][1] == "ok" and said[-1][0])
        ok("the field is not taken twice", not name.isModified())
        page.save_player()
        ok("Save with nothing new: nothing taken again, still says saved", taken == ["name"] and said[-1][1] == "ok")

        # a change the page took already (a field that was left) and that is not on disk yet
        p.players()["L/0"]["edits"]["3"]["shirt"] = "9"
        p.mark()
        ok("a change taken but not written yet", p.dirty)
        page.save_player()
        ok("Save writes it", json.load(open(path, encoding="utf-8"))["players"]["L/0"]["edits"]["3"]["shirt"] == "9"
           and not p.dirty)

        # no player picked: nothing is taken, the world is still saved
        page.cur = None
        shirt.insert("7")
        n = len(taken)
        p.mark()
        page.save_player()
        ok("no player picked: no field is taken, the world is saved", len(taken) == n and not p.dirty)

        # the file cannot be written: the page says that, not "Saved"
        page.cur = "3"
        p.path = os.path.join(tmp, "no-such-folder", "deeper", "world.json")
        p.mark()
        page.save_player()
        ok("a world that cannot be written: an error, not Saved", said[-1][1] == "err" and p.dirty)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    in_window(qa)
    print("1..%d" % N)
    print("all passed")


def in_window(qa):
    """UI test 15.11.2026 (beta 4f, 1920x1080 maximized): Save showed only after scrolling the
    page -- the page's scroll area asked the page's preferred height (the whole Basics form and
    the pitch). The whole window, its Players page with a player's texts in it: no outer scroll,
    Save inside the page's view. Offscreen fonts are smaller than Windows' (the page there had
    ~60 px less room at 1001), so 900 and 1366 x 768 stand in for the real 1920 x 1080."""
    from unittest.mock import patch
    root = tempfile.mkdtemp(prefix="fl26-psave-win-")
    try:
        with patch.dict(os.environ, {"APPDATA": root, "FL26_DIR": ""}):
            from modstudio import app as A
            with patch.object(A, "APPDIR", os.path.join(root, "FL26ModStudio")),                     patch.object(A, "SETTINGS", os.path.join(root, "FL26ModStudio", "settings.json")),                     patch.object(A, "guess_folders", return_value=[]):
                os.makedirs(A.APPDIR, exist_ok=True)
                with open(A.SETTINGS, "w", encoding="utf-8") as f:
                    json.dump({"check_updates": False, "page": "Settings", "lang": "en"}, f)
                w = A.Main()
                w.show()
                w.open_page("Players")
                p, holder = w.page("Players"), w.holder_of["Players"]
                p.i_title.setText("Yannick Pandor")
                p.i_sub.setText("place 1 in the squad")
                p.face_note.setText("A face is moved to this player's id when you Build, so it can come from any face mod.")
                p.foot.setText("30 players; the first eleven by squad order (bold) start.   52 changes in this club.   "
                               "New clubs start with the same squad, and Build picks its best eleven unless you set "
                               "the order here.")
                for width, height in ((1920, 1001), (1920, 900), (1366, 768)):
                    w.resize(width, height)
                    for _i in range(6):
                        qa.processEvents()
                    vp = holder.viewport()
                    at = p.b_save.mapTo(vp, p.b_save.rect().topLeft())
                    ok("Players %dx%d: the page does not scroll (outer %d)" % (width, height, holder.verticalScrollBar().maximum()),
                       holder.verticalScrollBar().maximum() == 0)
                    ok("Players %dx%d: Save and Undo in sight, not cut" % (width, height),
                       p.b_save.isVisible() and at.y() >= 0 and at.y() + p.b_save.height() <= vp.height()
                       and p.b_undo.mapTo(vp, p.b_undo.rect().bottomRight()).y() < vp.height())
                w.project.dirty = False
                w.close()
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    main()
