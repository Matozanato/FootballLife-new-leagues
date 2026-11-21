r"""python tools/test_zip_league_logo.py

A world installed from a zip (the GigaPack), made editable: Leagues > Kategoria e Parë > Edit
league... said "(file moved or deleted)" at Logo, while the list showed the logo and Build made the
right world. The recipe names the picture "source/d004/albania_2_league_kategoria_e_pare.png": Export
cuts the maker's paths down to that (installer.no_local_paths, B430), and no PC has such a file, so
there is no folder to read it from. Build keeps the world's own copy then (leaguebuilder.have_picture,
B85) and the Leagues page shows it (B89, world_logo). The dialog now shows that copy too, and says in
its tooltip that the path is not on this PC.

OK without touching the logo keeps the recipe as it was, the path relative, byte for byte. A logo
picked or cleared is the new one; a league with no built copy still says the file is gone.

The New leagues page in this process (QT_QPA_PLATFORM=offscreen), a Project with no tables, a fake
game folder holding the built world (its plan and the emblem Build wrote). No game.
"""
import copy, json, os, shutil, sys, tempfile, types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage, QColor

N = 0
WORLD = "_FL26Megapack"
LOGO = "source/d004/albania_2_league_kategoria_e_pare.png"
TOP_LOGO = "source/d004/albania_1_league_kategoria_superiore.png"


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


def dump(r):
    return json.dumps(r, ensure_ascii=False, sort_keys=False).encode("utf-8")


def main():
    QApplication.instance() or QApplication([])
    from modstudio.project import Project
    from modstudio.pages import builder as PB
    tmp = tempfile.mkdtemp(prefix="ziplogo_")
    cwd = os.getcwd()
    try:
        os.chdir(tmp)                            # "source/..." is not found from here either
        game = FakeGame(tmp)
        wdir = os.path.join(game.livecpk_dir, WORLD)
        emb = os.path.join(wdir, "common", "render", "symbol", "emblemLc")
        os.makedirs(emb)
        im = QImage(64, 64, QImage.Format_ARGB32)
        im.fill(QColor("red"))
        assert im.save(os.path.join(emb, "emb_0323_l.png"))
        with open(os.path.join(wdir, "leaguebuilder-plan.json"), "w", encoding="utf-8") as f:
            json.dump({"leagues": [{"name": "Kategoria Superiore", "cid": 322, "teams": list(range(100, 110))},
                                   {"name": "Kategoria e Parë", "cid": 323, "teams": list(range(110, 120))}]}, f)
        p = Project(None)
        p.app = types.SimpleNamespace(settings={}, save_settings=lambda: None, game=game)
        p.path = os.path.join(tmp, WORLD + ".json")
        p.countries = ["Albania"]
        p.recipe["world"] = WORLD
        p.recipe["leagues"] = [
            {"name": "Kategoria Superiore", "country": "Albania", "clubs": 10, "legs": 4, "format": "league",
             "logo": TOP_LOGO, "cup": True, "europe": [[1, 10], [2, 1], [3, 2]],
             "club_names": ["S%d" % k for k in range(10)]},
            {"name": "Kategoria e Parë", "country": "Albania", "clubs": 10, "legs": 2, "format": "league",
             "above": "Kategoria Superiore", "exchange": 2, "logo": LOGO,
             "club_names": ["P%d" % k for k in range(10)]}]
        before = dump(p.recipe)
        app = types.SimpleNamespace(project=p, game=game, settings={}, page=lambda n: None,
                                    pages={"NewLife": types.SimpleNamespace(rel=None)},
                                    open_page=lambda n: None, say=lambda *a, **k: None, busy=lambda *a: None)
        page = PB.NewLeagues(app)
        seen = {}
        real_finish = PB.LeagueDialog.finish

        def finish(d):                           # Edit league...: look at the dialog, then press OK
            v = d.logo.view
            seen[d.league["name"]] = (not v.pixmap().isNull(), v.text(), v.toolTip(), d.logo.path)
            d.ok()
            return d.result() == PB.QDialog.Accepted
        PB.LeagueDialog.finish = finish
        try:
            page.selected = lambda: 1
            page.edit()
            pic, text, tip, path = seen["Kategoria e Parë"]
            ok("the logo shows: the world's own copy (emb_0323)", pic and "moved or deleted" not in text)
            ok("its tooltip says the recipe's picture is not on this PC", LOGO in tip and "not on this PC" in tip)
            ok("the field keeps the recipe's path", path == LOGO)
            ok("OK unchanged: the recipe byte for byte as it was", dump(p.recipe) == before)
            ok("the path still relative", p.recipe["leagues"][1]["logo"] == LOGO)
            # the top league: no emblem in the world folder -> the old words
            page.selected = lambda: 0
            page.edit()
            pic, text, tip, path = seen["Kategoria Superiore"]
            ok("no built copy: still (file moved or deleted)", not pic and text == "(file moved or deleted)")
            ok("... and OK keeps its path as it was", p.recipe["leagues"][0]["logo"] == TOP_LOGO)
            # (the dialog's OK writes Up / down's 3 into a top league that had none, and the cups'
            # fields after the rest: the same league, as before this change)
            was = json.loads(before)["leagues"][0]
            ok("the rest of that league as OK always wrote it", p.recipe["leagues"][0] == dict(was, exchange=3))
            before = dump(p.recipe)
        finally:
            PB.LeagueDialog.finish = real_finish
        # Clear and Pick after the world's own copy: the new choice, not the copy
        d = PB.LeagueDialog(None, p, p.recipe["leagues"][1])
        ok("the dialog on its own shows the copy too", not d.logo.view.pixmap().isNull())
        d.logo.clear()
        ok("Clear: empty, the made-for-you words, no copy's tooltip",
           d.logo.view.pixmap().isNull() and d.logo.view.text() == "(made for you)"
           and "not on this PC" not in d.logo.view.toolTip())
        d.ok()
        ok("... and OK with it cleared takes the logo out", "logo" not in d.league)
        mine = os.path.join(tmp, "mine.png")
        assert im.save(mine)
        d = PB.LeagueDialog(None, p, p.recipe["leagues"][1])
        d.logo.path = mine
        d.logo.show_it()
        ok("a picked picture shows itself", not d.logo.view.pixmap().isNull()
           and "not on this PC" not in d.logo.view.toolTip())
        d.ok()
        ok("... and OK keeps it", d.league["logo"] == mine)
        ok("the open recipe untouched by the dialogs not kept", dump(p.recipe) == before)
        # a league of the game renamed with a logo in that world: the game's leagues panel (the
        # right side of Leagues) the same way
        assert im.save(os.path.join(emb, "emb_0017_l.png"))
        p.game_cl = {5003: ("Al Hilal", "HIL")}
        p.game_lgs = [(7, 17, "Saudi Pro League", [5003])]
        p.recipe["edits"] = {"leagues": {"7": {"name": "Roshn League", "logo": "source/d009/roshn.png"}}}
        gl = PB.GameLeagues(app)
        gl.show()
        gl.fill()
        gl.list.setCurrentRow(next(i for i, x in enumerate(gl.shown_rows) if x[0] == 7))
        ok("a game league's logo from the zip: the world's own copy shows",
           not gl.logo.view.pixmap().isNull() and "not on this PC" in gl.logo.view.toolTip())
        gl.keep_league()
        ok("Keep league changes keeps its path as it was",
           p.recipe["edits"]["leagues"]["7"] == {"name": "Roshn League", "logo": "source/d009/roshn.png"})
        gl.close()
    finally:
        os.chdir(cwd)
        shutil.rmtree(tmp, ignore_errors=True)
    print("test_zip_league_logo: ok (%d)" % N)


if __name__ == "__main__":
    main()
