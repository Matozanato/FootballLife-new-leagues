"""python test_conmebol_days.py <folder with the game's tables> -- the modern CONMEBOL rounds' days by
hand ("conmebol_days") alongside a January-December Apertura/Clausura league: conmebol_days takes a
piece's days and keeps the shipped ones for the rest, and refuses a piece it has not got, the wrong
number of days, days out of order or out of the piece's room; plan() refuses them without the modern
competitions; cal_layout lays the league clear of them (modern_busy); a day of the league by hand
next to one of them is a note of the Build (modern_clashes); recipe_from_plan gives them back,
drop_modern_conmebol takes them out; a Build writes them in the lpre lines and gives the finals and
the modern helper competitions ids of their own; the South American places window (offscreen, when
PySide6 loads) takes them and refuses bad ones."""
import os, re, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B
import test_conmebol_modern as T


def recipe(days=None, **extra):
    r = T.modern()
    v = next(L for L in r["leagues"] if L["country"] == "Venezuela")
    v.update({"season": "calendar", "cup": True, "supercup": True,
              "apertura": {"playoff": 8, "playoff_format": "groups", "grand_final": True}}, **extra)
    if days:
        r["conmebol_days"] = days
    return r, v


def refused(f, words):
    try:
        f()
    except B.BuildError as e:
        assert words in str(e), str(e)
        return
    raise AssertionError("taken")


def main(base):
    d = B.conmebol_days({})
    assert d == {k: tuple(v[3]) for k, v in B.CONMEBOL_DAYS.items()}, d
    assert d["sudamericana_playoff"] == B.SPO_DAYS and B.modern_busy({}) == tuple(sorted(B.CAL_MODERN_CONMEBOL))
    d = B.conmebol_days({"conmebol_days": {"sudamericana_playoff": [144, 161]}})
    assert d["sudamericana_playoff"] == (144, 161) and d["libertadores_1"] == (6, 13)
    for bad, words in (({"recopa": [50]}, "no recopa"), ({"sudamericana_playoff": [144]}, "2 day(s)"),
                       ({"sudamericana_playoff": [161, 144]}, "in order"), ({"libertadores_2": [12, 25]}, "between 15 and 33"),
                       ({"sudamericana_playoff": [150, 205]}, "between 141 and 199"), ({"sudamericana_first": ["x"]}, "days, not")):
        refused(lambda: B.conmebol_days({"conmebol_days": bad}), words)
    print("conmebol_days: by hand and shipped, a wrong piece, count, order or room refused")

    busy = B.modern_busy({"conmebol_days": {"sudamericana_playoff": [144, 161]}})
    lay = B.cal_layout("T", 14, 7, 2, True, busy)
    mine = {x for v in lay.values() for x in v}
    assert all(abs(a - b) >= B.CAL_GAP for a in mine for b in busy), "the layout clear of the days"
    print("cal_layout: clear of the modern days by hand")

    r, v = recipe({"sudamericana_playoff": [144, 158]}, calendar_days={"final_apertura": [157]})
    pl = B.plan(r, base)
    notes = [t for t in pl["skipped"] if "modern CONMEBOL" in t]
    assert notes == ["%s: its final_apertura day 157 is 1 day(s) from the modern CONMEBOL sudamericana_playoff day 158"
                     % v["name"]], notes
    assert "note: " + notes[0] in B.describe(pl)
    back = B.recipe_from_plan(pl, base)
    assert back["conmebol_days"] == {"sudamericana_playoff": [144, 158]}, back.get("conmebol_days")
    b2 = dict(back)
    B.drop_modern_conmebol(b2)
    assert "conmebol_days" not in b2
    print("plan: a day by hand next to one of them noted, given back, dropped with the modern competitions")

    r2, _v2 = recipe({"sudamericana_playoff": [144, 161]})
    B.drop_modern_conmebol(r2)
    r2["conmebol_days"] = {"sudamericana_playoff": [144, 161]}
    refused(lambda: B.plan(r2, base), "conmebol: modern")
    r3, _v3 = recipe({"libertadores_1": [1, 2]})
    refused(lambda: B.plan(r3, base), "conmebol_days libertadores_1")
    print("refused: without the modern competitions, days out of room")

    r, v = recipe({"sudamericana_playoff": [144, 161], "libertadores_1": [5, 12]})
    game = tempfile.mkdtemp(prefix="fl26-conmebol-days-")
    try:
        os.makedirs(os.path.join(game, "SiderAddons", "livecpk"))
        pl = B.plan(r, base)
        B.build(pl, base, game, False, log=lambda *a: None)
        text = open(os.path.join(B.siderdir.find(game), "livecpk", r["world"], "fl26world.txt"), encoding="utf-8").read()
        assert re.search(r"^lpre \d+ cup=\d+ fill=140 days=144,161 entry=\S+ poko=1$", text, re.M), "the play-off's days"
        assert re.search(r"^lpre \d+ cup=0 fill=2 days=5,12 ", text, re.M), "phase 1's days"
        assert re.search(r"^lpre \d+ cup=0 fill=14 days=18,25 ", text, re.M), "phase 2's shipped days"
        ids = pl.get("cup_ids") or {}
        cids = [v["cid"] for v in ids.values() if v.get("cid")]
        regs = [x for v in ids.values() for k, x in v.items() if k.startswith("reg") and x]
        assert len(cids) == len(set(cids)) and len(regs) == len(set(regs)), ids
        assert any(k.startswith("conmebol:") for k in ids), ids
        print("built: the days in the lpre lines; %d competitions and %d regulations of cups and helpers, each its own"
              % (len(cids), len(regs)))
    finally:
        shutil.rmtree(game, ignore_errors=True)
    dialog(base)
    print("all passed")


def dialog(base):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError as e:
        print("South American places window: skipped (%s)" % e)
        return
    app = QApplication.instance() or QApplication([])
    from modstudio.pages import builder as PB
    said = []
    PB.error = lambda *a: said.append(a[-1])

    class Project:
        countries, game_lgs, parents, game_cl, confeds = ["Venezuela"], [], [], {}, {}
        recipe = {"leagues": [], "conmebol": B.CONMEBOL_MODERN}
        touched = 0

        def formations(self):
            return []

        def touch(self):
            Project.touched += 1
    p = Project()
    p.base = base
    d = PB.SouthAmericaDialog(None, p)
    d.mdays.setText("sudamericana_playoff=144,161")
    d.ok()
    assert not said and p.recipe["conmebol_days"] == {"sudamericana_playoff": [144, 161]}, (said, p.recipe)
    d = PB.SouthAmericaDialog(None, p)
    assert d.mdays.text() == "sudamericana_playoff=144,161", d.mdays.text()
    d.mdays.setText("sudamericana_playoff=144")
    d.ok()
    assert said and "2 day(s)" in said[-1], said
    d.mdays.setText("recopa=50")
    d.ok()
    assert "recopa=50" in said[-1], said
    d = PB.SouthAmericaDialog(None, p)
    d.mdays.setText("")
    d.ok()
    assert "conmebol_days" not in p.recipe
    print("South American places window: the days in and out, bad ones refused")


if __name__ == "__main__":
    main(sys.argv[1])
