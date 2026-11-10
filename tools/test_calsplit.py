"""python test_calsplit.py <folder with the game's tables> -- a January-December Apertura/Clausura
league ("season": "calendar" with "apertura", fase 6): cal_layout lays every piece clear of the
game's busy days (CAL_GAP) and of each other (CAL_SPACE), in order, Saturdays for the rounds, the cup
spread through the year; a day by hand ("calendar_days") is kept and the rest laid around it; too
many clubs, a wrong count or an unknown key are refused; plan() takes the league with playoffs of
groups and refuses it with a knockout, refuses calendar_days on another league, and recipe_from_plan
gives them back; playoff_cups dates the play-offs, finals and grand final by the layout; and a
Build writes the world file's `season <region> 1`, `splitdays` of both phases, the play-offs' and
grand final's days and the cup's and super cup's `dates ... days=` from it; Mod Studio's league window
(offscreen, when PySide6 loads) takes the league and its days by hand and refuses what plan() would."""
import os, re, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B


def refused(fn, words):
    try:
        fn()
    except B.BuildError as e:
        assert words in str(e), str(e)
        return
    raise AssertionError("taken: %s" % words)


def check(d, modern):
    busy = set(B.CAL_WINDOWS) | set(B.CAL_LIBERTADORES) | set(B.CAL_CLUB_WORLD_CUP) | (set(B.CAL_MODERN_CONMEBOL) if modern else set())
    days = sorted(x for v in d.values() for x in v)
    assert all(abs(a - b) >= B.CAL_GAP for a in days for b in busy), "a day too near a busy one"
    assert all(b - a >= B.CAL_SPACE for a, b in zip(days, days[1:])), "two days too near: %s" % days
    seq = [x for k in ("apertura", "groups_apertura", "final_apertura", "clausura", "groups_clausura",
                       "final_clausura", "grand_final") for x in d.get(k, [])]
    assert seq == sorted(seq)
    sat = sum(1 for x in d["apertura"] + d["clausura"] if x % 7 == B.CAL_SAT)
    assert sat >= 0.6 * (len(d["apertura"]) + len(d["clausura"])), "the rounds on Saturdays first"


def main(base):
    for n, modern in ((14, True), (16, False), (10, True), (12, False)):
        d = B.cal_layout("T", n, 7, 2, True, modern)
        assert len(d["apertura"]) == len(d["clausura"]) == B.rounds_of(n)
        assert len(d["groups_apertura"]) == 6 and len(d["final_apertura"]) == 1 and len(d["grand_final"]) == 2
        assert len(d["cup"]) == 7 and d["supercup"] == [30]
        check(d, modern)
    print("laid: 10 to 16 clubs, clear of the busy days and of each other, in order")
    d = B.cal_layout("T", 14, 7, 2, True, True, {"final_apertura": [157], "grand_final": [342, 345]})
    assert d["final_apertura"] == [157] and d["grand_final"] == [342, 345] and 157 not in d["cup"]
    print("by hand: the Final del Apertura on 157 and the grand final on 342/345 kept, the rest around them")
    refused(lambda: B.cal_layout("T", 20, 7, 2, True, True), "no room for 19 apertura")
    refused(lambda: B.cal_layout("T", 14, 7, 2, True, True, {"final_apertura": [157, 160]}), "calendar_days final_apertura")
    refused(lambda: B.cal_layout("T", 14, 0, 0, False, True, {"cup": [70] * 7}), "no calendar_days cup")
    refused(lambda: B.cal_layout("T", 14, 7, 2, True, True, {"final_apertura": [96]}), "out of order")
    print("refused: too many clubs, a wrong count, a piece it has not got, out of order")

    L = {"name": "Cal League", "country": "Venezuela", "clubs": 14, "legs": 2, "season": "calendar", "cup": True,
         "supercup": True, "apertura": {"playoff": 8, "playoff_format": "groups", "grand_final": True},
         "calendar_days": {"final_apertura": [157]}}
    pl = B.plan({"world": "_TestCal", "leagues": [L]}, base)
    p = pl["leagues"][0]
    assert p["calendar"] and p["cal_days"]["final_apertura"] == [157]
    assert B.recipe_from_plan(pl, base)["leagues"][0]["calendar_days"] == {"final_apertura": [157]}
    cups = B.playoff_cups(p)
    c = p["cal_days"]
    assert cups[0]["opts"]["gdays"] == c["groups_apertura"] and cups[0]["opts"]["days"] == [157]
    assert cups[0]["opts"]["fill"] == c["apertura"][-1] + 1 and cups[1]["opts"]["fill"] == c["clausura"][-1] + 1
    assert cups[2]["opts"]["days"] == c["grand_final"]
    print("planned: the league, its days given back, its play-offs and grand final dated by the layout")
    refused(lambda: B.plan({"world": "_TestCal", "leagues": [dict(L, apertura={"playoff": 8})]}, base), "two groups of four")
    refused(lambda: B.plan({"world": "_TestCal", "leagues": [dict(L, apertura={"playoff": 8, "playoff_format": "groups"})]},
                           base), "and a grand_final")
    two = dict(L, name="Other League", country="Colombia")
    refused(lambda: B.plan({"world": "_TestCal", "leagues": [L, two]}, base), "one Apertura/Clausura league playing January")
    aug = dict(L, season="august")
    refused(lambda: B.plan({"world": "_TestCal", "leagues": [aug]}, base), "calendar_days are the days")
    print("refused: a knockout play-off, no grand final, two such leagues, calendar_days on an August-May league")

    game = tempfile.mkdtemp(prefix="fl26-calsplit-")
    try:
        os.makedirs(os.path.join(game, "SiderAddons", "livecpk"))
        pl = B.plan({"world": "_TestCal", "leagues": [L]}, base)
        B.build(pl, base, game, False, log=lambda *a: None)
        text = open(os.path.join(B.siderdir.find(game), "livecpk", "_TestCal", "fl26world.txt"), encoding="utf-8").read()
        c = pl["leagues"][0]["cal_days"]
        sd = dict(re.findall(r"^splitdays (\d+) ([\d,]+)$", text, re.M))
        sp = re.search(r"^split (\d+) regular=(\d+) groups=(\d+)", text, re.M)
        assert sp and sd == {sp.group(2): ",".join(map(str, c["apertura"])), sp.group(3): ",".join(map(str, c["clausura"]))}, sd
        assert re.search(r"^season %d 1$" % pl["leagues"][0]["region"], text, re.M)
        oc = pl["leagues"][0]["own_cup"]
        assert "dates %d like=" % oc["reg"] in text and "days=%s" % ",".join(map(str, c["cup"])) in text
        assert re.search(r"^dates %d like=\d+ days=30$" % oc["super_reg"], text, re.M)
        assert "days=157 gdays=%s" % ",".join(map(str, c["groups_apertura"])) in text
        assert "days=%s kolike=" % ",".join(map(str, c["grand_final"])) in text
        print("built: season, splitdays of both phases, the play-offs', grand final's, cup's and super cup's days")
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
         "apertura": {"playoff": 8, "playoff_format": "groups", "grand_final": True},
         "calendar_days": {"final_apertura": [157], "grand_final": [342, 345]}}
    d = PB.LeagueDialog(None, Project(), dict(L))
    assert d.calendar_days_value() == L["calendar_days"], d.calendar_days_value()
    d.ok()
    assert not said and d.league["season"] == "calendar" and d.league["calendar_days"] == L["calendar_days"], (said, d.league)
    d = PB.LeagueDialog(None, Project(), dict(L))
    d.caldays.setText("final=1")
    d.ok()
    assert said and "Days by hand" in said[-1], said
    d = PB.LeagueDialog(None, Project(), dict(L, apertura={"playoff": 8, "playoff_format": "groups"}))
    d.ok()
    assert "grand final" in said[-1], said
    print("league window: the league and its days by hand in, a bad field and no grand final refused")


if __name__ == "__main__":
    main(sys.argv[1])
