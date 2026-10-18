r"""python tools/test_crest_import.py

Import crests (Vicentico, 18.10.): with Match to "All clubs" a folder of Polish crests from
football-logos.cc gave "poland_1-liga_1500x1500.football-logos.cc.png" to the national team
Poland and "poland_bruk-bet-termalica-nieciecza..." to Mali ("mali" inside "termalica"), both at
70 % and ticked. Now a national team takes a picture by its team ID only, and one name contains
the other only from the start of a word to the end of one.

The dialog in this process (QT_QPA_PLATFORM=offscreen), a stand-in project with no tables. No game.
"""
import os, sys, types

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


def main():
    QApplication.instance() or QApplication([])
    from modstudio.pages import builder as PB
    PB.B.national_teams = lambda base: {19, 1067}
    project = types.SimpleNamespace(
        base="tables", recipe={"leagues": []},
        game_cl={19: ("Poland", "POL"), 1067: ("Mali", "MLI"), 70937: ("Port FC", "PFC"),
                 4800: ("Cracovia", "CRA"), 4801: ("Bruk-Bet Termalica Nieciecza", "BBT")})
    d = PB.CrestImportDialog(None, project)
    d.files = ["poland_1-liga_1500x1500.football-logos.cc.png",
               "poland_bruk-bet-termalica-nieciecza_1500x1500.football-logos.cc.png",
               "poland_cracovia_1500x1500.football-logos.cc.png",
               "poland_sport_1500x1500.football-logos.cc.png"]
    got = {f: (key[1], sc) for f, ((_n, key), sc) in d.matches().items()}
    ok("the league's picture goes to no national team", got.get(d.files[0], (None,))[0] != 19)
    ok("Termalica's picture goes to Termalica, not to Mali", got.get(d.files[1], (None,))[0] == 4801)
    ok("Cracovia's picture still goes to Cracovia", got.get(d.files[2], (None,))[0] == 4800)
    ok("\"sport\" is not Port FC", got.get(d.files[3], (None,))[0] != 70937)
    ok("Mali gets no picture at all", all(k != 1067 for k, _s in got.values()))
    d.files = ["19.png"]
    got = {f: (key[1], sc) for f, ((_n, key), sc) in d.matches().items()}
    ok("a national team still takes a picture named by its team ID", got.get("19.png") == (19, 1.0))
    print("test_crest_import: ok (%d)" % N)


if __name__ == "__main__":
    main()
