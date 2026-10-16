r"""python tools/test_game_club_crest.py

GitHub #140 (B2Y26Arabia), the rest of it: a crest picked with Edit club for a club of the game
in "Other clubs (no league)" did not stay (his recipe had none). Edit club on Leagues (a league of
the game, or one of the groups of clubs in no league) put the crest in the open world but only
marked it unsaved: 0.2.4 keeps a world by itself a moment after each change (Project.touch), and
this change never reached the file, nor the other pages. Undo club changes was the same. Both now
touch the world: the crest is in the world's file a moment later, and the club stays selected.

The page in this process (QT_QPA_PLATFORM=offscreen), a Project with no tables, the club dialog
replaced by one that answers at once. No game.
"""
import json, os, shutil, sys, tempfile, time, types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication

N = 0
CREST = r"D:\crests\al_foo.png"


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


class FakeDialog:
    """ClubDialog that gives the crest at once"""
    def __init__(self, parent, name, abbr, crest, **kw):
        self.result = (name, abbr, CREST)
        self.portrait_path = kw.get("portrait") or ""
        self.stadium_value = kw.get("stadium") or {}

    def finish(self):
        return True


def settle(qa, secs):
    t0 = time.time()
    while time.time() - t0 < secs:
        qa.processEvents()
        time.sleep(0.02)


def on_disk(path):
    with open(path, encoding="utf-8") as f:
        return ((json.load(f).get("edits") or {}).get("clubs") or {}).get("5001", {})


def main():
    qa = QApplication.instance() or QApplication([])
    from modstudio.project import Project, OTHERS
    from modstudio.pages import builder as PB
    PB.ClubDialog = FakeDialog
    PB.stadium_lib = lambda app: None
    tmp = tempfile.mkdtemp(prefix="crest_")
    try:
        p = Project(None)
        p.app = types.SimpleNamespace(settings={}, save_settings=lambda: None)
        p.path = os.path.join(tmp, "_FL26MyWorld.json")
        p._write(p.path)
        p.game_cl = {5001: ("Al Foo", "ALF"), 5002: ("Al Bar", "ALB")}
        p.game_other = [5001, 5002]
        page = PB.GameLeagues(types.SimpleNamespace(project=p))
        page.fill()
        row = next(i for i, x in enumerate(page.shown_rows) if x[0] == OTHERS)
        page.list.setCurrentRow(row)
        items = {page.tree.topLevelItem(i).data(0, PB.Qt.UserRole): page.tree.topLevelItem(i)
                 for i in range(page.tree.topLevelItemCount())}
        ok("Other clubs (no league) lists Al Foo and Al Bar", set(items) == {5001, 5002})
        page.tree.setCurrentItem(items[5001])
        seen = []
        p.changed.connect(lambda: seen.append(1))
        page.edit_club()
        ok("the crest is in the open world", p.edits("clubs").get("5001", {}).get("crest") == CREST)
        ok("the other pages hear of it (Project.changed)", len(seen) >= 1)
        cur = page.tree.currentItem()
        ok("the page shows it, Al Foo still selected", cur is not None and cur.data(0, PB.Qt.UserRole) == 5001
           and "al_foo.png" in cur.toolTip(1))
        settle(qa, 2.0)
        ok("#140: a moment later the crest is in the world's file", on_disk(p.path).get("crest") == CREST
           and not p.dirty)
        page.undo_club()
        ok("Undo club changes: gone from the open world", "5001" not in p.edits("clubs"))
        settle(qa, 2.0)
        ok("and from the world's file", on_disk(p.path) == {} and not p.dirty)
        cur = page.tree.currentItem()
        ok("Al Foo still selected", cur is not None and cur.data(0, PB.Qt.UserRole) == 5001)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("test_game_club_crest: ok (%d)" % N)


if __name__ == "__main__":
    main()
