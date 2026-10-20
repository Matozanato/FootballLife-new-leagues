r"""python tools/test_build_problems.py [folder with the game's tables]

Build simplifications on the Build page (jibibi, vmican 19.10.; mato 21.10.): Check the plan lists
every problem of the plan above the log, each with where it is (a league and club, a club of the
game by name and team id), and Go there opens its page: Clubs at the league and club, Leagues at
the league, Leagues at the game's league of a club of the game. A plan with no problem hides the
list. The pages in this process (QT_QPA_PLATFORM=offscreen) with the game's tables (default
%APPDATA%\FL26ModStudio\tables); a fake game folder. No game.
"""
import collections, os, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

N = 0
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


class FakeGame:
    def __init__(self, folder):
        self.folder, self.exe = folder, "x"
        self.sider_dir = os.path.join(folder, "SiderAddons")
        self.livecpk_dir = os.path.join(self.sider_dir, "livecpk")
        self.ini_path = os.path.join(self.sider_dir, "sider.ini")

    def ok(self):
        return True


class Noop:
    """the rest of the main window: every attribute and call does nothing"""

    def __getattr__(self, name):
        return Noop()

    def __call__(self, *a, **k):
        return None


class FakeApp(Noop):
    def __init__(self, **kw):
        self.__dict__.update(kw)


def league(name, **kw):
    return dict({"name": name, "country": "Colombia", "clubs": 16, "legs": 2}, **kw)


def main(tables):
    QApplication.instance() or QApplication([])
    import leaguebuilder as B
    from modstudio.project import Project
    from modstudio.pages import builder as PB, leagues as PL
    deep = os.path.join(tables, "common", "etc", "pesdb")
    base = B.base_dir(deep if os.path.isdir(deep) else tables)
    info = B.game_info(base)
    by = collections.defaultdict(list)
    for t, c in info["league_of"].items():
        by[c].append(t)
    lg = sorted(by)
    c = sorted(by[lg[1]])[0]
    a, other = sorted(by[lg[0]])[0], sorted(by[lg[2]])[0]
    tmp = tempfile.mkdtemp(prefix="buildprob-")
    os.makedirs(os.path.join(tmp, "SiderAddons", "livecpk"))
    open(os.path.join(tmp, "SiderAddons", "sider.ini"), "w").write("")
    p = Project(None)
    p.base = base
    p.game_cl = B.game_clubs(base)
    p.game_lgs = B.game_leagues(base)
    p.recipe["world"] = "_FL26Prob"
    p.recipe["leagues"] = [league("Liga Uno", clubs=2), league("Liga Cuatro", game_clubs=[{"at": 3, "id": c}])]
    p.recipe["edits"] = {"swaps": [[a, other], [other, c]]}
    pages = {}
    opened = []

    def open_page(n):
        opened.append(n)
        pg = pages.get(n)
        if pg is not None and hasattr(pg, "shown"):
            pg.shown()
    app = FakeApp(project=p, game=FakeGame(tmp), settings={}, page=lambda n: pages[n], pages=pages,
                  open_page=open_page)
    nl = PB.NewLeagues(app)
    pages["NewLeagues"] = nl
    nc = PB.NewClubs(app)
    pages["NewClubs"] = nc
    lp = PL.Leagues(app)
    pages["Leagues"] = lp
    bp = PB.Build(app)
    pages["Build"] = bp
    bp.ready_blocks = lambda asks=True: False
    bp.do_plan()
    rows = [(bp.problems.topLevelItem(i).text(0), bp.problems.topLevelItem(i).text(1),
             bp.problems.topLevelItem(i).data(0, Qt.UserRole)) for i in range(bp.problems.topLevelItemCount())]
    print("   " + "\n   ".join("%s | %s" % (w, t) for w, t, _d in rows))
    ok("Check the plan lists every problem at once (%d)" % len(rows), len(rows) == 4 and not bp.prob_box.isHidden())
    ok("the title counts them", "4" in bp.prob_title.text())
    ok("a league's problem shows the league", any(w == "Liga Uno" for w, _t, _d in rows))
    ok("a club's problem shows its league and club", any(w == "Liga Cuatro, club 4" for w, _t, _d in rows))
    lab = "%s (%d)" % (info["clubs"][other][0], other)
    ok("a club of the game shows its name and team id: %s" % lab, any(w == lab for w, _t, _d in rows))
    # Go there: the club of the game's place in Liga Cuatro
    k = next(i for i, r in enumerate(rows) if r[0] == "Liga Cuatro, club 4")
    bp.problems.setCurrentItem(bp.problems.topLevelItem(k))
    ok("Go there is on", bp.b_go.isEnabled())
    bp.go_there()
    ok("Go there opens Clubs at Liga Cuatro, club 4",
       opened[-1] == "NewClubs" and nc.combo.currentText() == "Liga Cuatro" and nc.current() == 3)
    k = next(i for i, r in enumerate(rows) if r[0] == "Liga Uno")
    bp.problems.setCurrentItem(bp.problems.topLevelItem(k))
    bp.go_there()
    cur = lp.current()
    ok("Go there opens Leagues at Liga Uno", opened[-1] == "Leagues" and cur and cur[0] == "oLiga Uno")
    k = next(i for i, r in enumerate(rows) if r[0] == lab)
    bp.problems.setCurrentItem(bp.problems.topLevelItem(k))
    bp.go_there()
    cur = lp.current()
    it = lp.game.tree.currentItem()
    ok("Go there opens Leagues at the game's league of %s, the club picked" % lab,
       cur and cur[0].startswith("g") and it is not None and it.data(0, Qt.UserRole) == other)
    # all put right: the list goes
    p.recipe["leagues"] = [league("Liga Uno"), league("Liga Cuatro")]
    p.recipe["edits"] = {}
    bp.do_plan()
    ok("a plan with no problem hides the list", bp.prob_box.isHidden() and "error" not in bp.out.toPlainText())
    print("test_build_problems: ok (%d)" % N)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ.get("APPDATA", ""), "FL26ModStudio", "tables"))
