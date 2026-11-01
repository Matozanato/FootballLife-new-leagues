"""python test_ceremony_build.py <folder with the game's tables> -- the trophy ceremony ("ceremony")
and the finals' cinematics ("cinematics"). The ceremony:
plan() takes it for a league with a national cup or playoffs of groups and refuses it for one with
no final; recipe_from_plan gives it back; a Build writes a `tmap <reg> 30` line for the national cup,
the super cup, both play-offs' finals and the grand final (noleg0: two legs), and none for a league
without the key; Mod Studio's league window (offscreen, when PySide6 loads) writes it.
The cinematics: plan() refuses a final it does not know or a folder name with | or a slash; a Build
writes `cine <reg> <final|all> <folder>` for the cup (its final), the super cup, both play-offs'
finals and the grand final (every match), says when a folder is not in content\cinematics or a
final is not there, and recipe_from_plan gives them back; cine_place puts fl26cine's line before
common\cinematics.lua in sider.ini and group_ours leaves it there; the league window lists the
folders and writes the key. The Lua side: tools/test_fl26cine.py; the DLL side: tools/test_ceremony.py."""
import json, os, re, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B

WORLD = "_TestCeremony"


def recipe(*leagues):
    return {"world": WORLD, "leagues": list(leagues)}


def dialog():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError as e:
        print("league window: skipped (%s)" % e)
        return
    app = QApplication.instance() or QApplication([])
    from modstudio.pages import builder as PB

    class Project:
        countries, recipe, game_lgs, parents, game_cl, base, confeds = ["Venezuela"], {"leagues": []}, [], [], {}, None, {}

        def formations(self):
            return []
    L = {"name": "X", "country": "Venezuela", "clubs": 12, "legs": 2, "cup": True, "ceremony": True,
         "cinematics": {"cup": "LIB", "grand_final": "Not Here"}}
    d = PB.LeagueDialog(None, Project(), dict(L))
    assert d.cine_value() == {"cup": "LIB", "grand_final": "Not Here"}, d.cine_value()
    d.cine["cup"].setCurrentIndex(0)
    assert d.cine_value() == {"grand_final": "Not Here"}, d.cine_value()
    assert d.cer.isChecked()
    d.cer.setChecked(False)
    d.ok()
    assert "ceremony" not in d.league, d.league
    d = PB.LeagueDialog(None, Project(), {"name": "Y", "country": "Venezuela", "clubs": 12, "legs": 2, "cup": True})
    assert not d.cer.isChecked()
    d.cer.setChecked(True)
    d.ok()
    assert d.league.get("ceremony") is True, d.league
    print("league window: the ceremony in and out")


def main(base):
    cine = {"cup": "ESPCF", "super_cup": "UEFA Super Cup", "final_apertura": "LIB", "final_clausura": "LIB",
            "grand_final": "UEFA Champions League F"}
    full = {"name": "Ceremony League", "country": "Venezuela", "clubs": 12, "legs": 2, "cup": True, "supercup": True,
            "ceremony": True, "apertura": {"playoff": 8, "playoff_format": "groups", "grand_final": True},
            "cinematics": cine}
    pl = B.plan(recipe(full), base)
    assert pl["leagues"][0]["ceremony"] is True
    assert B.recipe_from_plan(pl, base)["leagues"][0]["ceremony"] is True
    try:
        B.plan(recipe({"name": "Bare League", "country": "Venezuela", "clubs": 12, "legs": 2, "ceremony": True}), base)
        raise AssertionError("a league with no final took a ceremony")
    except B.BuildError as e:
        assert "trophy ceremony" in str(e), str(e)
    print("planned with finals, refused without; recipe_from_plan gives it back")
    assert B.recipe_from_plan(pl, base)["leagues"][0]["cinematics"] == cine
    for bad in ({"final": "LIB"}, {"cup": "a|b"}, {"cup": "a/b"}, {"cup": ""}, ["LIB"]):
        try:
            B.plan(recipe(dict(full, cinematics=bad)), base)
            raise AssertionError("cinematics %r taken" % (bad,))
        except B.BuildError as e:
            assert "cinematics" in str(e), str(e)
    print("cinematics: planned, refused for another final or a bad folder name, given back")

    game = tempfile.mkdtemp(prefix="fl26-ceremony-")
    try:
        os.makedirs(os.path.join(game, "SiderAddons", "livecpk"))
        for f in ("ESPCF", "LIB", "UEFA Champions League F"):          # "UEFA Super Cup" missing
            os.makedirs(os.path.join(game, "SiderAddons", "content", "cinematics", f))
        other = {"name": "Plain League", "country": "Colombia", "clubs": 12, "legs": 2, "cup": True, "supercup": True,
                 "cinematics": {"final_apertura": "LIB"}}
        pl = B.plan(recipe(full, other), base)
        log = []
        B.build(pl, base, game, False, log=log.append)
        assert any("no folder UEFA Super Cup" in l for l in log), "a missing folder is said"
        assert any("Plain League: cinematics for its final apertura, which it has not got" in l for l in log)
        world = os.path.join(B.siderdir.find(game), "livecpk", WORLD)
        text = open(os.path.join(world, "fl26world.txt"), encoding="utf-8").read()
        with open(os.path.join(world, "leaguebuilder-plan.json"), encoding="utf-8") as f:
            pl = json.load(f)
        tm = re.findall(r"^tmap (\d+) (\d+)( noleg0)?$", text, re.M)
        p, q = pl["leagues"]
        ids = pl["cup_ids"]
        want = [str(p["own_cup"]["reg"]), str(p["own_cup"]["super_reg"])]
        want += [str(ids["ccup:" + h["code"]]["ko"]) for h in pl["home_cups"]
                 if h.get("league") == p["rid"] and (h.get("final") or h.get("kind") == "grand_final")]
        assert [r for r, _t, _l in tm] == want and len(want) == 5, (tm, want)
        assert all(t == str(B.CEREMONY_TOURNAMENT) for _r, t, _l in tm)
        assert [l for _r, _t, l in tm] == ["", "", "", "", " noleg0"], tm
        assert str(q["own_cup"]["reg"]) not in [r for r, _t, _l in tm], "the league without the key: none"
        print("built: tmap lines %s" % ", ".join(r + l for r, _t, l in tm))
        cl = re.findall(r"^cine (\d+) (final|all) (.+)$", text, re.M)
        assert cl == [(want[0], "final", "ESPCF"), (want[1], "all", "UEFA Super Cup"), (want[2], "all", "LIB"),
                      (want[3], "all", "LIB"), (want[4], "all", "UEFA Champions League F")], cl
        print("built: cine lines, the cup's final only, every match of the others; a missing folder said")
    finally:
        shutil.rmtree(game, ignore_errors=True)
    place()
    dialog()
    print("all passed")


def place():
    """fl26cine's line before common\\cinematics.lua, out of Mod Studio's block"""
    lines = ['lua.module = "common\\stadiums.lua"', 'lua.module = "common\\cinematics.lua"',
             'lua.module = "common\\cinematicsB.lua"', B.OURS_HEAD, 'lua.module = "fl26swiss.lua"',
             'lua.module = "fl26cine.lua"', B.OURS_END]
    assert B.cine_place(lines)
    assert lines[1] == 'lua.module = "fl26cine.lua"' and lines[2] == 'lua.module = "common\\cinematics.lua"', lines
    assert not B.group_ours(lines) and lines[1] == 'lua.module = "fl26cine.lua"', "the block leaves it there"
    assert not B.cine_place(lines), "in place: nothing to move"
    no = ['lua.module = "fl26swiss.lua"', 'lua.module = "fl26cine.lua"']
    assert not B.cine_place(no) and no[1] == 'lua.module = "fl26cine.lua"', "no cinematics module: it stays"
    print("sider.ini: fl26cine before common\\cinematics.lua, the block leaves it")


if __name__ == "__main__":
    main(sys.argv[1])
