r"""python tools/test_squad_count.py

B69 (16.10., our test): Game's leagues and clubs, the Changed column said "51 players" for KV
Kortrijk, whose squad in the world has 30: it counted the recipe's changes (edits + add +
remove), and a signed player is both in join and in edits. It now shows the squad as it will
be: the club's players in the tables, less the ones removed or signed by another club, plus the
ones added and signed. A call-up to a national team takes no one from his club.

The page in this process (QT_QPA_PLATFORM=offscreen), a Project with no tables and a fake
squads reader. No game.
"""
import os, sys, types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication, QTreeWidgetItem

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


class FakeSquads:
    """lbplayers.Squads' by_club and index for three clubs and a national team"""
    def __init__(self, clubs):
        self.by_club = {t: [(k, pid, k + 1, 0) for k, pid in enumerate(pids)] for t, pids in clubs.items()}
        self.index = {pid: 0 for pids in clubs.values() for pid in pids}


def main():
    QApplication.instance() or QApplication([])
    from modstudio.project import Project
    from modstudio.pages import builder as PB
    p = Project(None)
    p.game_cl = {2013: ("KV Kortrijk", "KVK"), 174: ("RSC Anderlecht", "AND"), 269: ("Club Brugge KV", "BRU"),
                 9: ("Belgium", "BEL")}
    p.game_other = [2013, 174, 269]
    p.game_nat = [9]
    p._squads = FakeSquads({2013: list(range(1000, 1030)), 174: list(range(2000, 2028)),
                            269: list(range(3000, 3025)), 9: [1000, 2000, 3000]})
    pl = p.players()
    # Kortrijk: 2 signed from Anderlecht (each with an edit too, as the Players page keeps them),
    # 1 added, 3 removed, 5 of its own edited
    pl["2013"] = {"join": ["2000", "2001"], "add": [{"like": "1000"}], "remove": ["1001", "1002", "1003"],
                  "edits": dict({"2000": {"Age": "20"}, "2001": {"Age": "21"}},
                                **{str(1010 + i): {"Age": "25"} for i in range(5)})}
    pl["269"] = {"join": ["1020"]}                    # Brugge signs one of Kortrijk's
    pl["9"] = {"join": ["1021", "2002"]}              # Belgium calls two up: they stay at their clubs
    ok("Kortrijk: 30 - 3 removed - 1 to Brugge + 1 added + 2 signed = 29",
       PB.squad_size(p, 2013) == 29)
    ok("Anderlecht: 28 - 2 to Kortrijk = 26 (the call-up does not count)", PB.squad_size(p, 174) == 26)
    ok("Brugge: 25 + 1 = 26", PB.squad_size(p, 269) == 26)
    ok("Belgium: 3 + 2 called up = 5", PB.squad_size(p, 9) == 5)

    page = PB.GameLeagues(types.SimpleNamespace(project=p))
    it = QTreeWidgetItem()
    page.club_row(it, 2013)
    ok("the Changed column shows the squad, not the 13 changes: %r" % it.text(4), it.text(4) == "29 players")
    it = QTreeWidgetItem()
    page.club_row(it, 174)
    ok("a club with no changes of its own shows nothing: %r" % it.text(4), it.text(4) == "")
    p._squads = None
    p.base = None
    p.squads = lambda: None
    it = QTreeWidgetItem()
    page.club_row(it, 2013)
    ok("no tables read: squad changed, no number: %r" % it.text(4), it.text(4) == "squad changed")
    print("test_squad_count: ok (%d)" % N)


if __name__ == "__main__":
    main()
