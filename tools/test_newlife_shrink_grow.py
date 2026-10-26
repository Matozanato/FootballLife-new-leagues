r"""python tools/test_newlife_shrink_grow.py <NewLife folder> [folder with the game's tables]

B249 (jibibi 26.10.): a NewLife league taken from 15 clubs to 6 and back to 15 on Leagues > Edit
kept the clubs' names and NewLife ids but not their squads, so Build gave clubs 7-15 numbered
players. Now going back up puts those clubs in again from the release, with their squads; without
the release the bar says which clubs have no squad and how to get them back. The Leagues page in
this process (QT_QPA_PLATFORM=offscreen) with the real release and tables. No game.
"""
import copy, os, sys, types

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
    from modstudio.pages import builder as PB
    deep = os.path.join(tables, "common", "etc", "pesdb")
    base = B.base_dir(deep if os.path.isdir(deep) else tables)
    info = B.game_info(base)
    rel = N.Release(folder)
    rel.use_tables(info)
    picks = [cid for cid, c in sorted(rel.clubs.items()) if c.get("league") and c.get("in_game") != "1"
             and rel.squad(cid)][:15]
    p = Project(None)
    p.base = base
    x = {"name": "Ligue 3", "country": "France", "clubs": 15, "legs": 2, "format": "league",
         "club_names": ["Club %d" % i for i in range(15)], "club_coaches": ["Coach %d" % i for i in range(15)]}
    p.recipe["leagues"] = [x]
    for k, cid in enumerate(picks):
        N.put_club(p.recipe, rel, x, k, cid, info)
    full = {k: copy.deepcopy(p.recipe["players"][P.new_key("Ligue 3", k)]) for k in range(15)}
    names = list(x["club_names"])
    said = []
    app = types.SimpleNamespace(project=p, game=types.SimpleNamespace(ok=lambda: False, folder=""), settings={},
                                page=lambda n: None, pages={"NewLife": types.SimpleNamespace(rel=None)},
                                open_page=lambda n: None, say=lambda *a, **k: None, busy=lambda *a: None)
    page = PB.NewLeagues(app)
    page.say = lambda text, *a: said.append((text, a[0] if a else "warn"))
    page.selected = lambda: 0

    class Dlg:
        to = 15

        def __init__(self, parent, project, L=None, **kw):
            self.league = dict(copy.deepcopy(L), clubs=Dlg.to)

        def finish(self):
            return True
    real = PB.LeagueDialog
    PB.LeagueDialog = Dlg
    try:
        def edit(n):
            Dlg.to = n
            page.edit()
            return p.recipe["leagues"][0]

        edit(6)
        gone = [k for k in range(6, 15) if P.new_key("Ligue 3", k) in p.recipe["players"]]
        assert not gone, "6 clubs: the squads of places 7-15 go (as before) %s" % gone
        # no release open and no NewLife folder in Settings: the bar says it
        L = edit(15)
        assert N.emptied(p.recipe, L) == list(range(6, 15))
        assert said and said[-1][1] == "warn" and "7, 8, 9" in said[-1][0] and "NewLife page" in said[-1][0], said
        # with the release open on the NewLife page
        L = edit(6)
        app.pages["NewLife"].rel = rel
        L = edit(15)
        assert N.emptied(p.recipe, L) == [], N.emptied(p.recipe, L)
        assert L["club_names"] == names, "the same clubs at the same places"
        assert L["newlife"]["clubs"] == [int(c) for c in picks]
        for k in range(15):
            got = p.recipe["players"][P.new_key("Ligue 3", k)]
            assert got == full[k], "the same squad at place %d" % (k + 1)
        assert L["club_coaches"] == ["Coach %d" % i for i in range(15)], "what was set for a club stays"
        assert said[-1][1] == "ok" and "9 clubs of Ligue 3" in said[-1][0], said[-1]
        # a league made bigger with empty new places is left alone
        n = len(said)
        L = edit(17)
        assert len(said) == n and L["clubs"] == 17
    finally:
        PB.LeagueDialog = real
    print("test_newlife_shrink_grow: ok (%s ... %s)" % (names[6], names[14]))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.environ.get("APPDATA", ""), "FL26ModStudio", "tables"))
