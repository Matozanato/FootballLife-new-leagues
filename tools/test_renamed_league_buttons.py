r"""python tools/test_renamed_league_buttons.py

B161 (vmican 19.10.): on the Leagues page Remove, Edit and Add lower tier did nothing at all -- no
question, no error -- for every league of his world. A league renamed with Edit league... since the
last Build is found under the name it was built as (built_as), and New leagues' list then looked its
new name up in the last Build's order: ValueError, raised in the refresh the buttons run first.

The pages in this process (QT_QPA_PLATFORM=offscreen), a Project with no tables, a fake game folder
with a built world's plan. No game.
"""
import json, os, shutil, sys, tempfile, types

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
        self.sider_dir = folder

    def ok(self):
        return True


def league(name, country, **kw):
    return dict({"name": name, "country": country, "clubs": 4, "format": "league",
                 "club_names": ["A", "B", "C", "D"], "club_abbrs": ["AAA", "BBB", "CCC", "DDD"]}, **kw)


def main():
    qa = QApplication.instance() or QApplication([])
    from modstudio.project import Project
    from modstudio.pages import builder as PB, leagues as PL
    tmp = tempfile.mkdtemp(prefix="b161_")
    try:
        p = Project(None)
        p.app = types.SimpleNamespace(settings={}, save_settings=lambda: None)
        p.path = os.path.join(tmp, "_FL26Ren.json")
        p.recipe["world"] = "_FL26Ren"
        p.recipe["leagues"] = [league("Liga Uno", "Albania"), league("Liga Dos", "Andorra"),
                               league("Liga Tres", "Armenia")]
        game = FakeGame(tmp)
        wdir = os.path.join(game.livecpk_dir, "_FL26Ren")
        os.makedirs(wdir)
        with open(os.path.join(wdir, "leaguebuilder-plan.json"), "w", encoding="utf-8") as f:
            json.dump({"leagues": [{"name": n, "cid": 140 + i, "rid": 140 + i, "slot": 20 + i, "teams": [101 + 4 * i + k for k in range(4)]}
                                   for i, n in enumerate(("Liga Uno", "Liga Dos", "Liga Tres"))]}, f)
        pages = {}
        app = types.SimpleNamespace(project=p, game=game, settings={}, page=lambda n: pages.get(n),
                                    open_page=lambda n: None, say=lambda *a, **k: None)
        nl = PB.NewLeagues(app)
        pages["NewLeagues"] = nl
        lp = PL.Leagues(app)
        nl.refresh()
        ok("three leagues listed before", nl.tree.topLevelItemCount() == 3)
        # Edit league... renames: the name it was built as goes into built_as (project.rename_league)
        p.recipe["leagues"][1]["name"] = "Liga Dos (Victor)"
        p.rename_league("Liga Dos", "Liga Dos (Victor)")
        ok("the renamed league remembers its built name", "Liga Dos" in (p.recipe["leagues"][1].get("built_as") or []))
        nl.refresh()
        ok("B161: New leagues lists all three after a rename (no ValueError)", nl.tree.topLevelItemCount() == 3)
        asked = []
        real = PB.ask
        PB.ask = lambda parent, title, text: asked.append(text) or True
        try:
            # the button's own path: the league picked on Leagues (kind "ours", its index in the recipe)
            pick, real_current = [(None, None, "Liga Tres", "ours", 2)], lp.current
            lp.current = lambda: pick.pop() if pick else real_current()
            lp.on_ours("remove")
        finally:
            PB.ask = real
        ok("B161: Remove asks about the league picked", len(asked) == 1 and "Liga Tres" in asked[0])
        ok("B161: and takes it out", [L["name"] for L in p.recipe["leagues"]] == ["Liga Uno", "Liga Dos (Victor)"])
        # and an error in a click is written down: the exe has no console (B161 said nothing at all)
        from modstudio import app as A
        was_dir, A.APPDIR = A.APPDIR, os.path.join(tmp, "appdata")
        try:
            try:
                [].index("x")
            except ValueError:
                A.keep_error(*sys.exc_info())
            with open(os.path.join(A.APPDIR, "errors.log"), encoding="utf-8") as f:
                txt = f.read()
        finally:
            A.APPDIR = was_dir
        ok("a click's error goes to errors.log with its traceback", "ValueError" in txt and "Traceback" in txt)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("test_renamed_league_buttons: ok (%d)" % N)


if __name__ == "__main__":
    main()
