r"""python tools/test_import_transfers_page.py <game tables folder>

Players > More > Import transfers... (jibibi 23.10.) on a world over the game's tables: the
Players page's own handler, with the file dialog and the message boxes answered at once. Game
players move to a game club and to a new club, a new club's player moves to a game club, a line
to his own club calls off a move he had, and the moves stand where Transfer to... puts them (the
"join" list of the club he goes to, one club at a time). No game, no window (offscreen)."""
import os, shutil, sys, tempfile, types

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


def main(base):
    qa = QApplication.instance() or QApplication([])
    from modstudio.project import Project
    from modstudio.pages import players as PP
    tmp = tempfile.mkdtemp(prefix="fl26_trpage_")
    said = []
    PP.info = lambda parent, title, text: said.append(("info", text))
    PP.error = lambda parent, title, text: said.append(("error", text))
    try:
        p = Project(types.SimpleNamespace(settings={}, save_settings=lambda: None))
        p.load_tables(base)
        sq = p.squads()
        p.recipe["leagues"] = [{"name": "Ligue 3", "clubs": 2, "club_names": ["Stade Briochin FC", "FC Rouen"]}]
        nat = set(p.game_nat)
        teams = sorted({t for r, c, n, ts in p.game_lgs for t in ts} & set(p.game_cl))
        names = {}                                     # one name a player: no doubles in the test
        for pid, tids in sq.clubs_of.items():
            names.setdefault(sq.name(pid), []).append(pid)
        club_a, club_b = teams[0], teams[1]

        def lone(tid):
            return next(pid for o, pid, s, ao in sq.by_club[tid]
                        if len(names.get(sq.name(pid), [])) == 1 and sq.name(pid)
                        and [t for t in sq.clubs_of[pid] if t not in nat] == [tid])
        a1, a2 = [pid for o, pid, s, ao in sq.by_club[club_a]
                  if len(names.get(sq.name(pid), [])) == 1 and sq.name(pid)
                  and [t for t in sq.clubs_of[pid] if t not in nat] == [club_a]][:2]
        b1 = lone(club_b)
        proto = sq.proto()[0]["player"]
        newref = "Ligue 3/1/%s" % proto
        p.players()["Ligue 3/1"] = {"edits": {proto: {"name": "Jean Test"}}}
        p.players()[str(club_b)] = {"join": [str(a2)]}             # a2 was going to club B
        csvp = os.path.join(tmp, "moves.csv")
        with open(csvp, "w", encoding="utf-8", newline="") as f:
            f.write("player;to;from\n")
            f.write("%s;%s;\n" % (sq.name(a1), p.game_cl[club_b][0]))   # a game player to a game club
            f.write("%s;Stade Briochin;\n" % sq.name(b1))                       # to a new club, no FC
            f.write("Jean Test;%d;\n" % club_a)                          # a new club's player, a team id
            f.write("%s;%s;\n" % (sq.name(a2), p.game_cl[club_a][0]))   # back home: B's move called off
            f.write("Nobody At All;%d;\n" % club_a)
        PP.QFileDialog = types.SimpleNamespace(getOpenFileName=lambda *a, **k: (csvp, ""))

        class Fake:
            pass
        for m in ("import_transfers", "is_national", "new_names", "game_name", "home_of", "moves", "club_label"):
            setattr(Fake, m, getattr(PP.Players, m))
        page = Fake()
        page.project, page.app, page.club = p, types.SimpleNamespace(settings={}), None
        page.import_transfers()
        pl = p.players()
        join = lambda k: [str(r) for r in (pl.get(k) or {}).get("join") or []]
        ok("a game player joins a game club", str(a1) in join(str(club_b)))
        ok("a game player joins a new club (Stade Briochin without FC)", str(b1) in join("Ligue 3/0"))
        ok("a new club's player joins a game club by its id", newref in join(str(club_a)))
        ok("a line to his own club calls off the move he had", str(a2) not in join(str(club_b))
           and str(a2) not in join(str(club_a)))
        ok("one club at a time: each player in one join list", all(
            sum(r in join(k) for k in pl) == 1 for r in (str(a1), str(b1), newref)))
        ok("the world is marked changed and its autosave on the way", p.dirty and p._timer.isActive())
        ok("one message: 3 move, 1 already there, 1 line left out", len(said) == 1 and said[0][0] == "info"
           and said[0][1].startswith("3 ") and "1 are at that club" in said[0][1] and "1 lines left out" in said[0][1])
        print("#", said[0][1].replace("\n", " | "))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("1..%d" % N)


if __name__ == "__main__":
    main(sys.argv[1])
