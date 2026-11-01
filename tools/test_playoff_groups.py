"""python test_playoff_groups.py <folder with the game's tables> -- the Apertura/Clausura play-off of
two groups of four ("apertura": {"playoff_format": "groups"}): plan() takes the format, names and
logos and refuses what the builder has not; the play-off cups are the group cups fl26swiss.dll
plays (gdays=, adv=1, kolike=) with their finals as competitions of their own, on ids the game
creates at the season's start, kept by the next Build; recipe_from_plan gives the keys back; a
knockout play-off without the keys plans as before; and Mod Studio's league window (offscreen,
when PySide6 loads) writes the keys and keeps a hand-written recipe's playoff pictures"""
import json, os, re, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B
import mkleague as M

WORLD = "_TestPlayoffGroups"


def recipe(**ap):
    return {"world": WORLD, "leagues": [{"name": "Groups League", "country": "Venezuela", "clubs": 14,
                                         "legs": 2, "apertura": dict({"playoff": 8}, **ap)}]}


def refused(rec, base, words):
    try:
        B.plan(rec, base)
    except B.BuildError as e:
        assert words in str(e), str(e)
        return
    raise AssertionError("plan() took %r" % rec["leagues"][0]["apertura"])


def build(base, game, rec):
    """rec built over the plan its world folder already has (the builder page's way)"""
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
    """the league window's playoff fields: the format only for 8 clubs, the finals only for groups"""
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
    ap = {"playoff": 8, "playoff_format": "groups", "names": {"final_apertura": "Final A"},
          "logos": {"playoff_apertura": "p.png", "final_clausura": "f.png"}}
    d = PB.LeagueDialog(None, Project(), {"name": "X", "country": "Venezuela", "clubs": 14, "legs": 2,
                                          "apertura": dict(ap)})
    assert d.apertura_value() == ap, d.apertura_value()
    assert d.po_fmt.isEnabled() and d.po_names["final_apertura"].isEnabled()
    d.po.setCurrentIndex(d.po.findData(4))
    assert not d.po_fmt.isEnabled() and not d.fa_logo.isEnabled()
    assert "playoff_format" not in d.apertura_value(), d.apertura_value()
    d = PB.LeagueDialog(None, Project(), {"name": "Y", "country": "Venezuela", "clubs": 14, "legs": 2,
                                          "apertura": {"playoff": 8}})
    assert d.apertura_value() == {"playoff": 8} and not d.po_names["final_clausura"].isEnabled()
    print("league window: format, names and the finals' logos in and out")


def main(base):
    # a knockout play-off without the new keys: the plan of before
    p = B.plan(recipe(), base)["leagues"][0]
    assert set(p["apertura"]) == {"playoff", "logo"}, p["apertura"]
    ko = B.playoff_cups(p)
    assert [c["groups"] for c in ko] == [0, 0] and not any(c.get("final") for c in ko), ko
    assert [c["name"] for c in ko] == ["Groups League Apertura Playoffs", "Groups League Clausura Playoffs"]
    print("knockout: planned as before")

    # names and a picture for a knockout play-off; the finals' keys wait for "groups"
    p = B.plan(recipe(names={"playoff_clausura": "Liguilla"}, logos={"playoff_apertura": "a.png"}),
               base)["leagues"][0]
    ko = B.playoff_cups(p)
    assert [c["name"] for c in ko] == ["Groups League Apertura Playoffs", "Liguilla"], ko
    assert [c["logo"] for c in ko] == ["a.png", None], ko
    print("knockout: its own names and pictures")

    refused(recipe(playoff_format="league"), base, "playoff_format")
    refused(recipe(playoff=4, playoff_format="groups"), base, "two groups of four")
    refused(recipe(names={"final": "x"}), base, "no playoff names final")
    refused(recipe(logos=["x"]), base, "playoff logos")
    print("refused: an unknown format, groups of other than 8 clubs, unknown name keys")

    names = {"final_apertura": "Final del Apertura"}
    rec = recipe(playoff_format="groups", names=names, logos={"final_clausura": "f.png"})
    pl = B.plan(rec, base)
    p = pl["leagues"][0]
    cups = B.playoff_cups(p)
    assert len(cups) == 2
    for c, tag in zip(cups, ("Apertura", "Clausura")):
        o = c["opts"]
        assert c["groups"] == 2 and [pos for _r, pos in c["entry"]] == list(B.PLAYOFF_GROUP_ORDER), c
        assert len(o["gdays"]) == 6 and len(o["days"]) == 1 and o["days"][0] not in o["gdays"], o
        assert o["adv"] == 1 and o["kolike"] == B.PLAYOFF_FINAL_DATES, o
        assert c["knockout"] == {"clubs": 2, "like": B.PLAYOFF_FINAL_SHAPE}, c
        assert c["final"]["code"] == "FL_%03d_%sFI" % (p["rid"], tag[0]), c["final"]
    # the same seven days a knockout of the league gets
    assert [c["opts"]["gdays"] + c["opts"]["days"] for c in cups] == [c["opts"]["days"] for c in ko]
    assert [c["final"]["name"] for c in cups] == ["Final del Apertura", "Groups League Clausura Final"]
    assert [c["final"]["logo"] for c in cups] == [None, "f.png"]
    back = B.recipe_from_plan(pl, base)["leagues"][0]["apertura"]
    assert back == {"playoff": 8, "playoff_format": "groups", "names": names,
                    "logos": {"final_clausura": "f.png"}}, back
    print("groups: planned, and recipe_from_plan gives the keys back")

    game = tempfile.mkdtemp(prefix="fl26-pogroups-")
    try:
        os.makedirs(os.path.join(game, "SiderAddons", "livecpk"))
        rec = recipe(playoff_format="groups", names=names)
        pl, text, world = build(base, game, rec)
        lines = [l for l in text.splitlines() if l.startswith("ccup ")]
        assert len(lines) == 2, lines
        db = os.path.join(world, "common", "etc", "pesdb")
        comp, regs, ents = (M.load(db, n) for n in ("Competition.bin", "CompetitionRegulation.bin",
                                                     "CompetitionEntry.bin"))
        cids = {comp[i + M.CID_OFF]: M.code_of(comp[i:i + M.COMP]) for i in range(0, len(comp), M.COMP)}
        reg_cid = {B.u16(regs[i:], M.R_ID): (regs[i + M.R_CID], bytes(regs[i + M.R_NAME:i + M.R_NAME + 40]).split(b"\0")[0])
                   for i in range(0, len(regs), M.REG)}
        bel = B.like_reg(db, B.PLAYOFF_FINAL_DATES)
        finals = []
        for line, h, final in zip(lines, pl["home_cups"], ("Final del Apertura", "Groups League Clausura Final")):
            m = re.match(r"ccup (\d+) ko=(\d+) groups=2 entry=(\S+) fill=\d+ national=1 days=(\d+) "
                         r"gdays=([\d,]+) adv=1 kolike=(\d+) name=(.+)$", line)
            assert m, line
            reg, ko, days, gdays = int(m.group(1)), int(m.group(2)), [int(m.group(4))], m.group(5).split(",")
            assert int(m.group(6)) == bel and len(gdays) == 6 and days == h["opts"]["days"], line
            assert reg_cid[reg][0] == h["cid"] != reg_cid[ko][0], (reg_cid[reg], reg_cid[ko])
            fcid = reg_cid[ko][0]
            assert fcid in B.CREATION_IDS and fcid == h["final"]["cid"], (fcid, h["final"])
            assert reg_cid[ko][1].decode() == final, reg_cid[ko]
            assert cids[fcid] == h["final"]["code"], cids[fcid]
            assert pl["cup_ids"]["final:" + h["final"]["code"]] == {"cid": fcid}
            n = [ents[i + M.E_ORDER] for i in range(0, len(ents), M.ENT) if ents[i + M.E_CID] == fcid]
            assert sorted(n) == [1, 2], n
            assert os.path.isfile(os.path.join(world, B.logo_files(fcid)[0])), fcid
            finals.append(fcid)
        print("built: group cups %s, finals %s (competitions of their own, emblems drawn)"
              % ([h["cid"] for h in pl["home_cups"]], finals))
        pl2, _text, _w = build(base, game, rec)
        assert [h["final"]["cid"] for h in pl2["home_cups"]] == finals, pl2["home_cups"]
        print("built again: the finals keep their ids")
    finally:
        shutil.rmtree(game, ignore_errors=True)
    dialog()
    print("all passed")


if __name__ == "__main__":
    main(sys.argv[1])
