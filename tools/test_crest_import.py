r"""python tools/test_crest_import.py

Import crests (Vicentico, 18.10.): with Match to "All clubs" a folder of Polish crests from
football-logos.cc gave "poland_1-liga_1500x1500.football-logos.cc.png" to the national team
Poland and "poland_bruk-bet-termalica-nieciecza..." to Mali ("mali" inside "termalica"), both at
70 % and ticked. Now a national team takes a picture by its team ID only, and one name contains
the other only from the start of a word to the end of one.

B139 (David's Africa crests, 18.10.): "United Sport FC" (UAE) took nine "X United" crests and
Rangers "rangers-kinshasa", ticked. Now one name inside the other is never ticked, and a club of
the folder's country goes first; one of another country is never ticked.

The dialog in this process (QT_QPA_PLATFORM=offscreen), a stand-in project with no tables. No game.
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


def ticked(d):
    """{picture: (team id or league, ticked)} of the dialog's list"""
    out = {}
    for i in range(d.tree.topLevelItemCount()):
        it = d.tree.topLevelItem(i)
        key = it.data(0, Qt.UserRole)
        if key:
            out[it.text(0)] = (key[1] if key[0] == "game" else (key[1], key[2]), it.checkState(0) == Qt.Checked)
    return out


def b139():
    from modstudio.pages import builder as PB
    cty = {"United Arab Emirates": 230, "Scotland": 231, "Usa": 232, "Netherlands": 233, "South Africa": 234}
    PB.B.country_ids = lambda base: sorted(cty.items())
    PB.B.club_countries = lambda base: {1: 230, 2: 231, 3: 232, 4: 233, 5: 234}
    PB.B.game_league_countries = lambda base, leagues=None: {}
    PB.B.national_teams = lambda base: set()
    project = types.SimpleNamespace(
        base="tables", countries=sorted(cty), game_lgs=[],
        recipe={"leagues": [{"name": "Betway Premiership", "country": "South Africa", "clubs": 2,
                             "club_names": ["Kaizer Chiefs", "TS Galaxy Football Club"]}]},
        game_cl={1: ("United Sport FC", "USF"), 2: ("Rangers", "RAN"), 3: ("LA Galaxy", "LAG"),
                 4: ("Vitesse Arnhem", "VIT"), 5: ("Orlando Pirates", "ORL")},
        edits=lambda what: {}, league=lambda name: None)
    d = PB.CrestImportDialog(None, project)
    d.files = ["chippa-united.webp", "doma-united.webp", "rangers-kinshasa.webp", "ts-galaxy.webp",
               "vitesse.webp", "kaizer-chiefs.webp", "orlando-pirates.webp"]
    d.folder.setText(os.path.join("C:" + os.sep, "crests", "Africa", "South Africa", "betway-premiership"))
    d.fill()
    got = ticked(d)
    ok("chippa-united: no tick for United Sport FC", not got.get("chippa-united.webp", (0, False))[1])
    ok("doma-united: no tick for United Sport FC", not got.get("doma-united.webp", (0, False))[1])
    ok("rangers-kinshasa: no tick for Rangers", not got.get("rangers-kinshasa.webp", (0, False))[1])
    ok("ts-galaxy goes to the South African club, ticked",
       got.get("ts-galaxy.webp") == (("Betway Premiership", 1), True))
    ok("vitesse: no tick for Vitesse Arnhem", not got.get("vitesse.webp", (0, False))[1])
    ok("a new club of the folder's country, ticked", got.get("kaizer-chiefs.webp") == (("Betway Premiership", 0), True))
    ok("a game club of the folder's country, ticked", got.get("orlando-pirates.webp") == (5, True))
    d.files = ["Vitesse Arnhem.png", "Rangers.png"]
    d.fill()
    ok("an exact name of another country: shown, not ticked", ticked(d) == {"Vitesse Arnhem.png": (4, False),
                                                                         "Rangers.png": (2, False)})
    d.folder.setText(os.path.join("C:" + os.sep, "crests"))
    d.fill()
    ok("no country for the folder: the exact names tick as before",
       ticked(d) == {"Vitesse Arnhem.png": (4, True), "Rangers.png": (2, True)})


def main():
    QApplication.instance() or QApplication([])
    from modstudio.pages import builder as PB
    PB.B.national_teams = lambda base: {19, 1067}
    project = types.SimpleNamespace(
        base="tables", recipe={"leagues": []}, countries=["Poland", "Mali"], game_lgs=[],
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
    d.files = ["poland_cracovia_1500x1500.football-logos.cc.png"]
    d.fill()
    ok("football-logos.cc's Cracovia is ticked", ticked(d) == {d.files[0]: (4800, True)})
    b139()
    print("test_crest_import: ok (%d)" % N)


if __name__ == "__main__":
    main()
