"""python test_grand_final_build.py <folder with the game's tables> -- the Apertura/Clausura grand
final ("apertura": {"playoff_format": "groups", "grand_final": ...}): plan() takes true, "two_legs"
and "single" and refuses it without a playoff of groups; recipe_from_plan gives it back; a Build of
two such leagues gives each its final of two cups -- a ccup line with src= (its play-offs' knockouts)
and cid=, on an id the game creates at the season's start, after its Clausura's final, two legs or
one, kept by the next Build -- with its regulation named after the league, the away goals rule off,
the legs mode for two legs, and no entry rows; and Mod Studio's league window (offscreen, when
PySide6 loads) writes the key. tools/test_grand_final.py checks the DLL side."""
import json, os, re, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B
import mkleague as M

WORLD = "_TestGrandFinal"


def league(name, country, gf, **ap):
    return {"name": name, "country": country, "clubs": 12, "legs": 2,
            "apertura": dict({"playoff": 8, "playoff_format": "groups", "grand_final": gf}, **ap)}


def recipe(*leagues):
    return {"world": WORLD, "leagues": list(leagues)}


def refused(rec, base, words):
    try:
        B.plan(rec, base)
    except B.BuildError as e:
        assert words in str(e), str(e)
        return
    raise AssertionError("plan() took %r" % rec["leagues"][0]["apertura"])


def build(base, game, rec):
    world = os.path.join(B.siderdir.find(game), "livecpk", WORLD)
    path = os.path.join(world, "leaguebuilder-plan.json")
    prev = None
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            prev = json.load(f)
    log = []
    try:
        B.build(B.plan(rec, base, prev), base, game, prev is not None, log=log.append)
    except Exception:
        print("\n".join("# " + l for l in log[-30:]))
        raise
    with open(path, encoding="utf-8") as f:
        pl = json.load(f)
    with open(os.path.join(world, "fl26world.txt"), encoding="utf-8") as f:
        return pl, f.read(), world


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
    L = league("X", "Venezuela", True, names={"grand_final": "Final de la Liga"})
    d = PB.LeagueDialog(None, Project(), dict(L))
    v = d.apertura_value()
    assert v["grand_final"] == "two_legs" and v["names"] == {"grand_final": "Final de la Liga"}, v
    assert d.gf.isEnabled() and d.gf_logo.isEnabled()
    d.gf.setCurrentIndex(d.gf.findData("single"))
    assert d.apertura_value()["grand_final"] == "single"
    d.po_fmt.setCurrentIndex(d.po_fmt.findData("knockout"))
    assert not d.gf.isEnabled() and "grand_final" not in d.apertura_value(), d.apertura_value()
    print("league window: the grand final in and out, only with groups")


def main(base):
    for gf, legs in ((True, 2), ("two_legs", 2), ("single", 1)):
        p = B.plan(recipe(league("GF League", "Venezuela", gf)), base)["leagues"][0]
        cups = B.playoff_cups(p)
        assert [c["kind"] for c in cups] == ["playoff", "playoff", "grand_final"], cups
        g = cups[2]
        assert g["legs"] == legs and len(g["opts"]["days"]) == legs and g["case"], g
        assert g["opts"]["days"][0] > cups[1]["opts"]["days"][-1], "after the Clausura's final"
        assert g["opts"]["src"] == [cups[0]["code"], cups[1]["code"]] and g["title"] == "GF League", g
        assert g["name"] == "GF League Grand Final"
    print("planned: true and two_legs two legs, single one match, after the Clausura's final")
    refused(recipe(league("GF League", "Venezuela", True, playoff_format="knockout")), base, "playoff of groups")
    refused(recipe(league("GF League", "Venezuela", "three")), base, "grand_final")
    pl = B.plan(recipe(league("GF League", "Venezuela", True, names={"grand_final": "Final de la Liga"})), base)
    back = B.recipe_from_plan(pl, base)["leagues"][0]["apertura"]
    assert back["grand_final"] == "two_legs" and back["names"] == {"grand_final": "Final de la Liga"}, back
    print("refused without groups or with another value; recipe_from_plan gives it back")

    game = tempfile.mkdtemp(prefix="fl26-grandfinal-")
    try:
        os.makedirs(os.path.join(game, "SiderAddons", "livecpk"))
        rec = recipe(league("GF League", "Venezuela", True, names={"grand_final": "Final de la Liga"}),
                     league("Single League", "Colombia", "single"))
        pl, text, world = build(base, game, rec)
        lines = [l for l in text.splitlines() if l.startswith("ccup ")]
        db = os.path.join(world, "common", "etc", "pesdb")
        regs, ents = M.load(db, "CompetitionRegulation.bin"), M.load(db, "CompetitionEntry.bin")
        row = {B.u16(regs[i:], M.R_ID): i for i in range(0, len(regs), M.REG)}
        grand = [h for h in pl["home_cups"] if h["kind"] == "grand_final"]
        assert len(grand) == 2
        cids = []
        for h, title, legs in zip(grand, ("GF League", "Single League"), (2, 1)):
            line = next(l for l in lines if l.endswith("name=" + h["name"]))
            m = re.match(r"ccup (\d+) ko=(\d+) groups=0 entry=\S+ fill=0 national=1 days=([\d,]+) kolike=\d+ "
                         r"src=(\d+),(\d+) cid=(\d+) name=", line)
            assert m and m.group(1) == m.group(2), line
            ko, days, src, cid = int(m.group(2)), m.group(3).split(","), (int(m.group(4)), int(m.group(5))), int(m.group(6))
            plays = [x for x in pl["home_cups"] if x["kind"] == "playoff" and x["league"] == h["league"]]
            kos = tuple(int(re.search(r"ko=(\d+)", next(l for l in lines if l.endswith("name=" + x["name"]))).group(1))
                        for x in plays)
            assert src == kos and len(days) == legs, (line, kos)
            assert cid in B.CREATION_IDS and cid == h["cid"], (cid, h)
            o = row[ko]
            assert regs[o + M.R_CID] == cid
            assert bytes(regs[o + M.R_NAME:o + M.R_NAME + 40]).split(b"\0")[0].decode() == title
            d10 = int.from_bytes(regs[o + 0x10:o + 0x14], "little")
            assert not d10 & B.AWAY_GOALS_BIT, "the away goals rule off"
            assert legs == 1 or (d10 >> B.KO_LEGS_SHIFT) & B.KO_LEGS_MASK == B.KO_LEGS_BOTH, "two legs: every tie"
            assert not any(ents[i + M.E_CID] == cid for i in range(0, len(ents), M.ENT)), "no entry rows"
            assert os.path.isfile(os.path.join(world, B.logo_files(cid)[0])), cid
            cids.append(cid)
        assert "name=Final de la Liga" in text
        print("built: grand finals on competitions %s, src= their play-offs' knockouts, named after the league" % cids)
        pl2, _t, _w = build(base, game, rec)
        assert [h["cid"] for h in pl2["home_cups"] if h["kind"] == "grand_final"] == cids
        print("built again: the grand finals keep their ids")
    finally:
        shutil.rmtree(game, ignore_errors=True)
    dialog()
    print("all passed")


if __name__ == "__main__":
    main(sys.argv[1])
