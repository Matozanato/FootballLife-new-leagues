r"""python tools/test_move_game_club.py [folder with the game's tables]

B95 (vmican 17.10.): Envigado and Union Magdalena, clubs of the game NewLife puts in its Colombian
Second Division, could not be put in another league of his world with either picker: Club of the
game showed them greyed ("take it out of that place first"), NewLife club... not at all, "as if
they did not exist". Now:
  - Club of the game finds a club of the game in another place of the world and moves it: out of
    its old place (a new club there now), into this one, with who takes its places in the game;
  - a club that only takes another's place in the game (swap) stays greyed;
  - NewLife club... shows the release's clubs the game has, greyed, with the way in, and Tick
    all shown does not tick them;
  - NewLife club... leaves out the clubs a league of the world has already (the ids were compared
    as numbers against text, so they were listed again).
The Clubs page in this process (QT_QPA_PLATFORM=offscreen) with the game's tables (default
%APPDATA%\FL26ModStudio\tables). No game.
"""
import os, sys, types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def league(name, country, **kw):
    return dict({"name": name, "country": country, "clubs": 4, "format": "league",
                 "club_names": ["A", "B", "C", "D"], "club_abbrs": ["AAA", "BBB", "CCC", "DDD"]}, **kw)


def main(tables):
    QApplication.instance() or QApplication([])
    import leaguebuilder as B
    from modstudio.project import Project
    from modstudio.pages import builder as PB, newlife as PN
    deep = os.path.join(tables, "common", "etc", "pesdb")     # Settings > Unpack the game's tables
    base = B.base_dir(deep if os.path.isdir(deep) else tables)
    info = B.game_info(base)
    free = [t for t in sorted(info["clubs"]) if B.game_club_problem(info, t) is None and t not in info["national"]]
    moved, swapped = free[10], free[11]
    p = Project(None)
    p.base = base
    p.game_cl = B.game_clubs(base)
    p.recipe["leagues"] = [
        league("Segunda A", "Colombia", game_clubs=[{"at": 3, "id": moved, "swap": {"name": "Filler FC"}}],
               newlife={"version": "1.5", "clubs": [900001, 900002, 900003]}),
        league("Segunda B", "Colombia", game_clubs=[{"at": 0, "id": free[12], "swap": swapped}]),
        league("Mine", "Colombia")]
    said = []
    app = types.SimpleNamespace(project=p, game=types.SimpleNamespace(ok=lambda: False, folder=""), settings={}, page=lambda n: None, pages={},
                                open_page=lambda n: None, say=lambda *a, **k: None)
    nc = PB.NewClubs(app)
    nc.say = lambda text, *a: said.append(text)
    mine = p.recipe["leagues"][2]
    nc.league = lambda: mine
    nc.current = lambda: 1
    seen = {}

    def finish(d):
        d.search.setText(str(moved))
        it = next((d.tree.topLevelItem(i) for i in range(d.tree.topLevelItemCount())
                   if d.tree.topLevelItem(i).data(0, Qt.UserRole) == moved), None)
        seen["moved"] = it is not None and bool(it.flags() & Qt.ItemIsEnabled) and "moves here" in it.text(3)
        d.search.setText(str(swapped))
        sw = [d.tree.topLevelItem(i) for i in range(d.tree.topLevelItemCount())
              if d.tree.topLevelItem(i).text(2) == str(swapped)]
        seen["swap"] = bool(sw) and not (sw[0].flags() & Qt.ItemIsEnabled)
        d.search.setText(str(moved))
        it = next(d.tree.topLevelItem(i) for i in range(d.tree.topLevelItemCount())
                  if d.tree.topLevelItem(i).data(0, Qt.UserRole) == moved)
        d.tree.setCurrentItem(it)
        seen["where"] = "Segunda A, club 4" in d.where.text() and not d.swap_club.isVisible()
        d.ok()
        return d.result is not None

    real = PB.GameClubDialog.finish
    PB.GameClubDialog.finish = finish
    try:
        nc.game_club()
    finally:
        PB.GameClubDialog.finish = real
    ok("Club of the game finds the club in Segunda A, to pick", seen.get("moved"))
    ok("a club that only takes another's place stays greyed", seen.get("swap"))
    ok("the window says where it moves from", seen.get("where"))
    A = p.recipe["leagues"][0]
    ok("it is out of its old place", not A.get("game_clubs"))
    ok("and in this one, with who takes its places in the game",
       mine.get("game_clubs") == [{"at": 1, "id": moved, "swap": {"name": "Filler FC"}}])
    ok("the bar says the old place is a new club now", said and "Segunda A, club 4" in said[-1])

    class Rel:
        meta = {"version": "1.5"}
        twins = {}
        clubs = {"900001": {"name": "Cucuta Deportivo", "league": "Colombian First Division", "in_game": "0"},
                 "900009": {"name": "Jaguares de Cordoba", "league": "Colombian First Division", "in_game": "0"},
                 str(moved): {"name": "Envigado F.C.", "league": "Colombian Second Division", "in_game": "1"}}
        squads = {}

        def use_tables(self, g):
            pass

        def use_recipe(self, r):
            pass
    nc.nl_rel = Rel()
    got = {}

    class Pick(PN.ClubPickDialog):
        def finish(self):
            got["skip"] = self.skip_arg
            self.search.setText("colombian")
            items = [self.list.item(i) for i in range(self.list.count())]
            got["grey"] = [it.text() for it in items if not it.flags() & Qt.ItemIsEnabled]
            self.tick_shown(True)
            got["ticked"] = set(self.checked)
            return False

        def __init__(self, parent, rel, skip, game=()):
            self.skip_arg = set(skip)
            super().__init__(parent, rel, skip, game)
    real = PN.ClubPickDialog
    PN.ClubPickDialog = Pick
    try:
        nc.newlife_club()
    finally:
        PN.ClubPickDialog = real
    ok("NewLife club... leaves out a club a league has already", "900001" in got.get("skip", ()))
    ok("NewLife club... shows the club of the game, greyed, with the way in",
       len(got.get("grey") or []) == 1 and "Envigado" in got["grey"][0] and "Club of the game" in got["grey"][0])
    ok("Tick all shown leaves it alone", got.get("ticked") == {"900009"})
    print("test_move_game_club: ok (%d)" % N)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ.get("APPDATA", ""), "FL26ModStudio", "tables"))
