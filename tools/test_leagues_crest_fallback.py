r"""python tools/test_leagues_crest_fallback.py

B103 (Xxspedd, closed beta a448734): the Leagues page of a world built by 0.2.3 (its recipe's crest
paths are the author's, or there are none) said "Could not show this section: name 'world_crest' is
not defined". show_crests fell back to the crest the build wrote, with the helper imported only in
show_ours. Now a league whose crest pictures are missing shows its clubs with a dash, and one with
a built world folder shows the crests from there.

The page in this process (QT_QPA_PLATFORM=offscreen), a Project with no tables, a fake game folder.
No game.
"""
import os, shutil, sys, tempfile, types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtGui import QImage, QColor

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def cells(page):
    """(text, has picture) of every club cell on the right of Leagues"""
    out = []
    for i in range(page.o_crests.count()):
        box = page.o_crests.itemAt(i).widget()
        cell = box.findChildren(QLabel)[0]
        out.append((cell.text(), not cell.pixmap().isNull()))
    return out


class FakeGame:
    def __init__(self, folder):
        self.folder, self.exe = folder, "x"
        self.livecpk_dir = os.path.join(folder, "livecpk")

    def ok(self):
        return True


def main():
    qa = QApplication.instance() or QApplication([])
    from modstudio.project import Project
    from modstudio.pages import leagues as PL
    tmp = tempfile.mkdtemp(prefix="b103_")
    try:
        p = Project(None)
        p.app = types.SimpleNamespace(settings={}, save_settings=lambda: None)
        p.path = os.path.join(tmp, "_FL26Pack.json")
        p.recipe["world"] = "_FL26Pack"
        L = {"name": "Liga Pack", "country": "Spain", "clubs": 3, "format": "league",
             "club_names": ["Uno", "Dos", "Tres"], "club_abbrs": ["UNO", "DOS", "TRE"],
             "club_crests": [r"C:\author\pc\uno.png", r"C:\author\pc\dos.png", None]}
        p.recipe["leagues"] = [L]
        game = FakeGame(tmp)
        app = types.SimpleNamespace(project=p, game=game, page=lambda n: None, open_page=lambda n: None)
        page = PL.Leagues(app)
        # 1. no built world: the author's paths are not on this PC -> a dash, no error
        page.show_ours(0)
        ok("B103: a league with missing crest pictures shows its 3 clubs", len(cells(page)) == 3)
        ok("each with a dash and no picture", all(t == "—" and not pic for t, pic in cells(page)))
        ok("League ID says not built / —", page.o_rows["League ID"].text() in ("—", "not built yet"))
        # 2. a built world folder: the crests the build wrote stand in
        wdir = os.path.join(game.livecpk_dir, "_FL26Pack")
        flag = os.path.join(wdir, "common", "render", "symbol", "flag")
        os.makedirs(flag)
        for tid in (101, 102):
            im = QImage(16, 16, QImage.Format_ARGB32)
            im.fill(QColor("red"))
            assert im.save(os.path.join(flag, "e_%06d_r.png" % tid))
        with open(os.path.join(wdir, "leaguebuilder-plan.json"), "w", encoding="utf-8") as f:
            f.write('{"leagues": [{"name": "Liga Pack", "cid": 140, "teams": [101, 102, 103]}]}')
        page.show_ours(0)
        c = cells(page)
        ok("B89: with a built world the first two clubs show the crests the build wrote", c[0][1] and c[1][1])
        ok("the third (no file) keeps the dash", c[2] == ("—", False))
        ok("League ID 140", page.o_rows["League ID"].text() == "140")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("test_leagues_crest_fallback: ok (%d)" % N)


if __name__ == "__main__":
    main()
