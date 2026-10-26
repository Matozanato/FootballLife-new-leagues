r"""python tools/test_newlife_club_pick.py <NewLife folder> [folder with the game's tables]

B252 (26.10.): New clubs > NewLife club... ended every pick in "'set' object has no attribute
'get'" -- B95 gave the release's clubs of the game the name game, the name that held the tables'
info put_club reads. Now the picked clubs go in with name and squad, the Clubs page in this process
(QT_QPA_PLATFORM=offscreen) with the real release and tables. No game.
"""
import os, sys, types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication


def main(folder, tables):
    QApplication.instance() or QApplication([])
    import leaguebuilder as B
    import lbplayers as P
    from modstudio import newlife as N
    from modstudio.project import Project
    from modstudio.pages import builder as PB, newlife as PN
    deep = os.path.join(tables, "common", "etc", "pesdb")
    base = B.base_dir(deep if os.path.isdir(deep) else tables)
    p = Project(None)
    p.base = base
    p.game_cl = B.game_clubs(base)
    mine = {"name": "Mine", "country": "England", "clubs": 4, "format": "league",
            "club_names": ["A", "B", "C", "D"], "club_abbrs": ["AAA", "BBB", "CCC", "DDD"]}
    p.recipe["leagues"] = [mine]
    said = []
    app = types.SimpleNamespace(project=p, game=types.SimpleNamespace(ok=lambda: False, folder=""), settings={},
                                page=lambda n: None, pages={}, open_page=lambda n: None, say=lambda *a, **k: None,
                                busy=lambda *a: None)
    nc = PB.NewClubs(app)
    nc.say = lambda text, *a: said.append(text)
    nc.league = lambda: mine
    nc.current = lambda: 1
    nc.nl_rel = N.Release(folder)
    got = {}

    class Pick(PN.ClubPickDialog):
        def finish(self):
            free = [cid for _n, _l, cid in self.all if cid not in self.game_set]
            self.picked = free[:2]
            got["picked"] = list(self.picked)
            return True

        def __init__(self, parent, rel, skip, game=()):
            self.game_set = set(game)
            super().__init__(parent, rel, skip, game)
    real = PN.ClubPickDialog
    PN.ClubPickDialog = Pick
    try:
        nc.newlife_club()
    finally:
        PN.ClubPickDialog = real
    picked = got.get("picked") or []
    assert len(picked) == 2, picked
    rel = nc.nl_rel
    assert mine["newlife"]["clubs"][1:3] == [int(c) for c in picked], mine.get("newlife")
    assert mine["club_names"][1:3] == [rel.clubs[c]["name"] for c in picked], mine["club_names"]
    for k in (1, 2):
        e = p.recipe["players"].get(P.new_key("Mine", k)) or {}
        assert e, "a squad at place %d" % k
    assert said and "2 NewLife clubs put in Mine" in said[-1], said
    print("test_newlife_club_pick: ok (%s)" % ", ".join(mine["club_names"][1:3]))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.environ.get("APPDATA", ""), "FL26ModStudio", "tables"))
