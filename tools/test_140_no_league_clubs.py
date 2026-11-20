r"""python tools/test_140_no_league_clubs.py

GitHub #140 (B2Y26Arabia), in the exe: since 0.1.8 the Leagues page hides the game's leagues panel's
own list (pages/leagues.py, self.game.list), and only that list had the game's "Other clubs (no
league)". My World > Leagues listed the game's leagues and ours only -- "Other" found 0 of 343 -- so
a club of the game in no league could not be given a crest or a name with Edit club.
test_game_club_crest.py builds the game's leagues panel by itself, its list on screen, and never
saw it.

This test goes the way the exe does: the Leagues page as it is shown, its search, its list, the
panel on the right and its Edit club button. The group is found by the search, its club is picked,
Edit club gives it a crest (the row shows it at once, the club stays picked, the world's file has it
a moment later), Undo club changes takes it out again. The game's own league keeps its row as before.

The page in this process (QT_QPA_PLATFORM=offscreen), a Project with no tables (the game's clubs set
by hand), the club dialog replaced by one that answers at once. No game.
"""
import json, os, shutil, sys, tempfile, time, types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication, QPushButton, QToolButton
from PySide6.QtGui import QImage, QColor

N = 0
CREST = [None]


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


class FakeDialog:
    """ClubDialog that gives the crest at once"""
    def __init__(self, parent, name, abbr, crest, **kw):
        self.result = (name, abbr, CREST[0])
        self.portrait_path = kw.get("portrait") or ""
        self.stadium_value = kw.get("stadium") or {}
        self.coach_name = kw.get("coach") or ""

    def finish(self):
        return True


class FakeGame:
    def __init__(self, folder):
        self.folder, self.exe = folder, "x"
        self.livecpk_dir = os.path.join(folder, "livecpk")

    def ok(self):
        return True


def settle(qa, secs):
    t0 = time.time()
    while time.time() - t0 < secs:
        qa.processEvents()
        time.sleep(0.02)


def on_disk(path):
    with open(path, encoding="utf-8") as f:
        return ((json.load(f).get("edits") or {}).get("clubs") or {}).get("5001", {})


def rows(page):
    """the entries of the Leagues list on screen, [(key, name, kind)]"""
    out = []
    for i in range(page.tree.topLevelItemCount()):
        h = page.tree.topLevelItem(i)
        for j in range(h.childCount()):
            k, _c, name, kind, _p = h.child(j).data(0, page_role())
            out.append((k, name, kind))
    return out


def page_role():
    from modstudio.pages import leagues as PL
    return PL.ROLE


def clubs(game):
    return {game.tree.topLevelItem(i).data(0, 0x0100): game.tree.topLevelItem(i)
            for i in range(game.tree.topLevelItemCount())}


def main():
    qa = QApplication.instance() or QApplication([])
    from modstudio.project import Project, OTHERS
    from modstudio.pages import builder as PB
    from modstudio.pages import leagues as PL
    PB.ClubDialog = FakeDialog
    PB.stadium_lib = lambda app: None
    tmp = tempfile.mkdtemp(prefix="t140_")
    try:
        CREST[0] = os.path.join(tmp, "al_foo.png")
        im = QImage(32, 32, QImage.Format_ARGB32)
        im.fill(QColor("green"))
        assert im.save(CREST[0])
        p = Project(None)
        p.app = types.SimpleNamespace(settings={}, save_settings=lambda: None)
        p.path = os.path.join(tmp, "_FL26MyWorld.json")
        p._write(p.path)
        p.game_cl = {5001: ("Al Foo", "ALF"), 5002: ("Al Bar", "ALB"), 5003: ("Al Hilal", "HIL"),
                     9001: ("Saudi Arabia", "KSA")}
        p.game_lgs = [(7, 17, "Saudi Pro League", [5003])]
        p.game_other = [5001, 5002]
        p.game_nat = [9001]
        app = types.SimpleNamespace(project=p, game=FakeGame(tmp), page=lambda n: None, open_page=lambda n: None)
        page = PL.Leagues(app)
        # the tables are set by hand above: the pages' "not unpacked yet" check stands aside
        page.need_tables = page.game.need_tables = lambda offer=False: False
        page.show()
        page.shown()                        # what the exe does when the page opens
        ok("the panel's own list stays hidden, as in the exe", page.game.list.parentWidget().isHidden())
        got = rows(page)
        ok("the game's league keeps its row", ("g17", "Saudi Pro League", "game") in got)
        ok("#140: the game's clubs in no league are a row of the list", ("x%d" % OTHERS, "Other clubs (no league)",
                                                                       "group") in got)
        ok("national teams are not (Players > National teams)", not any("National" in n for _k, n, _t in got))
        ok("the count is of leagues, the group said apart",
           "1 leagues" in page.count.text() and "1 group of clubs in no league" in page.count.text())
        # the game's league: shown on the right as before
        page.show_key("g17")
        ok("the game's league on the right, its club listed", page.right.currentWidget() is page.game
           and set(clubs(page.game)) == {5003} and page.game.lname.isEnabled())
        # find the group by the search
        page.search.setText("other")
        settle(qa, 0.5)
        got = rows(page)
        ok("the search 'other' finds the group", [k for k, _n, _t in got] == ["x%d" % OTHERS])
        it = page.tree.topLevelItem(0).child(0)
        page.tree.setCurrentItem(it)
        qa.processEvents()
        ok("the group on the right: its two clubs, no league name to change",
           page.right.currentWidget() is page.game and set(clubs(page.game)) == {5001, 5002}
           and not page.game.lname.isEnabled())
        ok("the row cannot be dragged", not (it.flags() & PL.Qt.ItemIsDragEnabled))
        game = page.game
        game.tree.setCurrentItem(clubs(game)[5001])
        edit = next(b for b in game.findChildren(QPushButton) if b.text() == "Edit club")
        ok("Edit club is a button in sight", edit.isVisible())
        edit.click()
        ok("the crest is in the open world", p.edits("clubs").get("5001", {}).get("crest") == CREST[0])
        cur = game.tree.currentItem()
        ok("the row shows it at once (tooltip, icon), Al Foo still picked",
           cur is not None and cur.data(0, 0x0100) == 5001 and "al_foo.png" in cur.toolTip(1)
           and not cur.icon(1).isNull())
        ok("the group still the one picked in the list", page.current() and page.current()[0] == "x%d" % OTHERS)
        settle(qa, 2.0)
        ok("a moment later the crest is in the world's file", on_disk(p.path).get("crest") == CREST[0]
           and not p.dirty)
        more = next(b for b in game.findChildren(QToolButton) if b.menu() and
                    any(a.text() == "Undo club changes" for a in b.menu().actions()))
        next(a for a in more.menu().actions() if a.text() == "Undo club changes").trigger()
        ok("Undo club changes: gone from the open world", "5001" not in p.edits("clubs"))
        cur = game.tree.currentItem()
        ok("the row without it, Al Foo still picked", cur is not None and cur.data(0, 0x0100) == 5001
           and "al_foo.png" not in cur.toolTip(1) and cur.icon(1).isNull())
        settle(qa, 2.0)
        ok("and gone from the world's file", on_disk(p.path) == {} and not p.dirty)
        page.search.setText("")
        settle(qa, 0.5)
        ok("the search emptied: both rows again", {k for k, _n, _t in rows(page)} == {"g17", "x%d" % OTHERS})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("test_140_no_league_clubs: ok (%d)" % N)


if __name__ == "__main__":
    main()
