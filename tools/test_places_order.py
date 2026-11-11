"""python test_places_order.py <folder with the game's tables> -- continental places in the order of
the finals ("places_order": "finals"): plan() takes it for the January-December Apertura/Clausura
league of a world with the modern CONMEBOL competitions and refuses it without them, on another
league or with another value; recipe_from_plan gives it back; a Build writes `contorder <reg> finals`
and a world without the key none; the league window (offscreen, when PySide6 loads) takes it for
that league and refuses it on an August-May one. fl26swiss.dll reads it (fl26_swiss_contorder): without the line
the places follow the table, as before."""
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
    r, v = recipe(places_order="finals")
    pl = B.plan(r, base)
    p = next(x for x in pl["leagues"] if x["name"] == v["name"])
    assert p["places_order"] == "finals" and B.contorder_lines(pl) == ["contorder %d finals" % p["rid"]]
    back = next(x for x in B.recipe_from_plan(pl, base)["leagues"] if x["name"] == v["name"])
    assert back["places_order"] == "finals", back
    print("planned: places_order finals for the January-December league, contorder line, given back")
    r2, _v = recipe()
    assert B.contorder_lines(B.plan(r2, base)) == [], "no key: no line"
    r3, v3 = recipe(places_order="finals")
    B.drop_modern_conmebol(r3)
    refused(r3, base, "modern")
    r4, v4 = recipe(places_order="finals")
    v4.pop("season")
    refused(r4, base, "places_order finals is for the January-December")
    r5, _v5 = recipe(places_order="order")
    refused(r5, base, "table or finals")
    print("refused: without modern CONMEBOL, on an August-May league, another value")

    game = tempfile.mkdtemp(prefix="fl26-contorder-")
    try:
        os.makedirs(os.path.join(game, "SiderAddons", "livecpk"))
        pl = B.plan(r, base)
        B.build(pl, base, game, False, log=lambda *a: None)
        text = open(os.path.join(B.siderdir.find(game), "livecpk", r["world"], "fl26world.txt"), encoding="utf-8").read()
        p = next(x for x in pl["leagues"] if x["name"] == v["name"])
        assert re.findall(r"^contorder (\d+) finals$", text, re.M) == [str(p["rid"])], "the line in the world file"
        print("built: contorder %d finals in the world file" % p["rid"])
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
         "apertura": {"playoff": 8, "playoff_format": "groups", "grand_final": True}, "places_order": "finals"}
    d = PB.LeagueDialog(None, Project(), dict(L))
    assert d.porder.isChecked()
    d.ok()
    assert not said and d.league["places_order"] == "finals", (said, d.league)
    d = PB.LeagueDialog(None, Project(), dict(L))
    d.porder.setChecked(False)
    d.ok()
    assert not said and "places_order" not in d.league, (said, d.league)
    d = PB.LeagueDialog(None, Project(), {"name": "Aug", "country": "Venezuela", "clubs": 14, "legs": 2})
    d.porder.setChecked(True)
    d.ok()
    assert said and "order of the finals" in said[-1], said
    print("league window: the option in and out, refused on an August-May league")


if __name__ == "__main__":
    main(sys.argv[1])
