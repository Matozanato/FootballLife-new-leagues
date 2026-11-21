r"""python tools/test_b410_league_search.py

B410 (Vicentico, closed beta 10.11.): the search on the Leagues page was very slow with the GigaPack
(343 leagues). Every key refilled the list, the places table (one box in each of its 317 rows) and
showed the crests of the current league twice: 0.4-1.3 s a key, measured on its recipe. Now a key
waits for the next a quarter of a second, then refills the list only; the right side is shown again
only when another league is the current one. A change of the world still refills everything.

The page in this process (QT_QPA_PLATFORM=offscreen), a Project with no tables, a fake game folder.
No game.
"""
import os, shutil, sys, tempfile, time, types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


class FakeGame:
    def __init__(self, folder):
        self.folder, self.exe = folder, "x"
        self.livecpk_dir = os.path.join(folder, "livecpk")

    def ok(self):
        return True


def settle(qa, secs):
    t = time.time()
    while time.time() - t < secs:
        qa.processEvents()
        time.sleep(0.01)


def main():
    qa = QApplication.instance() or QApplication([])
    from modstudio.project import Project
    from modstudio.pages import leagues as PL
    tmp = tempfile.mkdtemp(prefix="b410_")
    try:
        p = Project(None)
        p.app = types.SimpleNamespace(settings={}, save_settings=lambda: None)
        p.path = os.path.join(tmp, "_FL26Pack.json")
        p.recipe["world"] = "_FL26Pack"
        p.recipe["leagues"] = [{"name": n, "country": "Spain", "clubs": 2, "format": "league",
                                "club_names": ["A", "B"], "club_abbrs": ["AAA", "BBB"]}
                               for n in ("Primera Uno", "Primera Dos", "Segunda Tres")]
        app = types.SimpleNamespace(project=p, game=FakeGame(tmp), page=lambda n: None, open_page=lambda n: None)
        page = PL.Leagues(app)
        page.show()              # (B480 round 2: a page behind another one fills when it is opened)
        page.fill()
        settle(qa, 0.3)          # (B480: the places table, not on screen, on a turn of its own)
        calls = {"places": 0, "crests": 0}
        real_places, real_crests = page.fill_places, page.show_crests

        def places(*a, **k):
            calls["places"] += 1
            return real_places(*a, **k)

        def crests(*a, **k):
            calls["crests"] += 1
            return real_crests(*a, **k)
        page.fill_places, page.show_crests = places, crests
        names = lambda: [page.tree.topLevelItem(i).child(j).data(0, PL.ROLE)[2]
                         for i in range(page.tree.topLevelItemCount())
                         for j in range(page.tree.topLevelItem(i).childCount())]
        ok("three leagues of ours in the list", sorted(names()) == ["Primera Dos", "Primera Uno", "Segunda Tres"])
        cur = page.current()[2]
        for i in range(1, len("primera") + 1):
            page.search.setText("primera"[:i])
            qa.processEvents()
        ok("typing: the list waits for the last key", sorted(names()) == ["Primera Dos", "Primera Uno", "Segunda Tres"])
        settle(qa, 0.5)
        ok("... then shows the leagues found", sorted(names()) == ["Primera Dos", "Primera Uno"])
        ok("the places table is not refilled by the search", calls["places"] == 0)
        ok("the current league (%s) still found: its crests not shown again" % cur,
           page.current()[2] == cur and calls["crests"] == 0)
        page.search.setText("segunda")
        settle(qa, 0.5)
        ok("another league current: shown once", names() == ["Segunda Tres"] and calls["crests"] == 1
           and page.current()[2] == "Segunda Tres")
        page.filter.button(1).click()
        qa.processEvents()
        ok("the Ours chip: the list only", calls["places"] == 0 and calls["crests"] == 1)
        page.search.setText("")
        settle(qa, 0.5)
        n = calls["crests"]
        p.changed.emit()
        settle(qa, 0.3)
        ok("a change of the world: the places table and the league on the right, once",
           calls["places"] == 1 and calls["crests"] == n + 1)
        # B480 (17.11.2026): the places table off screen is filled on a turn of its own (317 rows
        # were up to 0.31 s of the turn of Make it editable), and at once when it is asked for
        page.fill()
        ok("B480: places table not on screen: not filled in fill()'s own turn", calls["places"] == 1)
        page.b_places.setChecked(True)
        ok("B480: ... and filled at once when Places in Select Team is pressed", calls["places"] == 2)
        settle(qa, 0.3)
        ok("B480: ... not again on the turn it was left for", calls["places"] == 2)
        page.b_places.setChecked(False)
        # the game's leagues panel: the league picked once per fill (it was shown twice)
        shown, real_show = [], page.game.show_league
        page.game.show_league = lambda: (shown.append(1), real_show())
        page.game.fill()
        ok("B480: the game's leagues panel shows its league once per fill (%d)" % len(shown), len(shown) == 1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("test_b410_league_search: ok (%d)" % N)


if __name__ == "__main__":
    main()
