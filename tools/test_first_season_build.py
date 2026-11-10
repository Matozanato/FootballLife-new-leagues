"""python test_first_season_build.py <folder with the game's tables> -- nobody abroad in a league's
first season ("first_season_abroad": false): plan() takes it for the January-December
Apertura/Clausura league and refuses it on another league or with a value that is not true or false;
recipe_from_plan gives it back; a Build writes `firstabroad <reg> 0` and a world without the key none;
the league window (offscreen, when PySide6 loads) takes it for that league and refuses it on an
August-May one. fl26swiss.dll reads it (fl26_swiss_firstabroad, tools/test_first_season.py): without
the line the first season goes by squad strength, as before."""
import os, re, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B
import test_conmebol_modern as T


def recipe(**extra):
    r = T.modern()
    v = next(L for L in r["leagues"] if L["country"] == "Venezuela")
    v.update({"season": "calendar", "cup": True, "supercup": True,
              "apertura": {"playoff": 8, "playoff_format": "groups", "grand_final": True}}, **extra)
    return r, v


def refused(r, base, words):
    try:
        B.plan(r, base)
    except B.BuildError as e:
        assert words in str(e), str(e)
        return
    raise AssertionError("taken")


def main(base):
    r, v = recipe(first_season_abroad=False)
    pl = B.plan(r, base)
    p = next(x for x in pl["leagues"] if x["name"] == v["name"])
    assert p["first_season_abroad"] is False and B.firstabroad_lines(pl) == ["firstabroad %d 0" % p["rid"]]
    back = next(x for x in B.recipe_from_plan(pl, base)["leagues"] if x["name"] == v["name"])
    assert back["first_season_abroad"] is False, back
    print("planned: first_season_abroad false for the January-December league, firstabroad line, given back")
    r2, _v = recipe(first_season_abroad=True)
    pl2 = B.plan(r2, base)
    assert B.firstabroad_lines(pl2) == [], "true: no line"
    assert "first_season_abroad" not in next(x for x in B.recipe_from_plan(pl2, base)["leagues"] if x["name"] == v["name"])
    r4, v4 = recipe(first_season_abroad=False)
    v4.pop("season")
    refused(r4, base, "first_season_abroad false is for the January-December")
    r5, _v5 = recipe(first_season_abroad="no")
    refused(r5, base, "true or false")
    print("refused: on an August-May league, another value; true writes nothing")

    game = tempfile.mkdtemp(prefix="fl26-firstabroad-")
    try:
        os.makedirs(os.path.join(game, "SiderAddons", "livecpk"))
        pl = B.plan(r, base)
        B.build(pl, base, game, False, log=lambda *a: None)
        text = open(os.path.join(B.siderdir.find(game), "livecpk", r["world"], "fl26world.txt"), encoding="utf-8").read()
        p = next(x for x in pl["leagues"] if x["name"] == v["name"])
        assert re.findall(r"^firstabroad (\d+) 0$", text, re.M) == [str(p["rid"])], "the line in the world file"
        print("built: firstabroad %d 0 in the world file" % p["rid"])
    finally:
        shutil.rmtree(game, ignore_errors=True)
    dialog()
    print("all passed")


def dialog():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError as e:
        print("league window: skipped (%s)" % e)
        return
    app = QApplication.instance() or QApplication([])
    from modstudio.pages import builder as PB
    said = []
    PB.error = lambda *a: said.append(a[-1])

    class Project:
        countries, recipe, game_lgs, parents, game_cl, base, confeds = ["Venezuela"], {"leagues": []}, [], [], {}, None, {}

        def formations(self):
            return []
    L = {"name": "Cal", "country": "Venezuela", "clubs": 14, "legs": 2, "season": "calendar", "cup": True,
         "apertura": {"playoff": 8, "playoff_format": "groups", "grand_final": True}, "first_season_abroad": False}
    d = PB.LeagueDialog(None, Project(), dict(L))
    assert d.noabroad.isChecked()
    d.ok()
    assert not said and d.league["first_season_abroad"] is False, (said, d.league)
    d = PB.LeagueDialog(None, Project(), dict(L))
    d.noabroad.setChecked(False)
    d.ok()
    assert not said and "first_season_abroad" not in d.league, (said, d.league)
    d = PB.LeagueDialog(None, Project(), {"name": "Aug", "country": "Venezuela", "clubs": 14, "legs": 2})
    d.noabroad.setChecked(True)
    d.ok()
    assert said and "first season" in said[-1], said
    print("league window: the option in and out, refused on an August-May league")


if __name__ == "__main__":
    main(sys.argv[1])
