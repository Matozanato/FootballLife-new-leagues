"""python tools/test_game_supercups.py <folder with the game's tables> -- the super cup Build adds
to a league of the game (Build > Cups of the game's countries > Super cup) is a two-club super
cup, and in a February-December country it is played after the season, in January, between the
champion and the cup winner of the season just ended (Discord, Vicentico 13.10.: the Supercopa
de Chile and Rei came out as 16- and 26-club knockouts drawn in July from a league still running,
and then were never played properly and kept no stats).

Checked without the game: the plan, the tables Build writes (a copy of the base tables in a
temporary folder), the world file's dates and gsuper lines, and that the season modules read
the gsuper line. Base tables: D:/dev/fl26-modding-research/out/base-pesdb
"""
import os, re, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B
import mkleague as M
import fl26world

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
CHILE, BRAZIL, SCOTLAND = 67, 29, 133            # regulation ids of the game's top divisions


def recipe(leagues=(), **extra):
    r = {"world": "_TestGameSuperCups", "leagues": list(leagues),
         "game_cups": [{"league": rid, "league_cup": False, "super_cup": True}
                       for rid in (CHILE, BRAZIL, SCOTLAND)]}
    r.update(extra)
    return r


def tables(base):
    comp, regs = M.load(base, "Competition.bin"), M.load(base, "CompetitionRegulation.bin")
    regrow = {B.u16(regs[i * M.REG:], M.R_ID): regs[i * M.REG:(i + 1) * M.REG] for i in range(len(regs) // M.REG)}
    region_of_cid = {comp[i * M.COMP + M.CID_OFF]: M.dec_region(comp[i * M.COMP + M.REGION_OFF])
                     for i in range(len(comp) // M.COMP)}
    return regrow, region_of_cid


def main(base):
    regrow, region_of_cid = tables(base)
    pl = B.plan(recipe(), base)

    # 1. not a fl26swiss knockout on the FA Cup's row (0.2.3: filled with every club of the
    #    country, drawn in July from the table of a league still running)
    bad = [c["name"] for c in pl.get("home_cups") or [] if c.get("code", "").endswith("_SCUP")]
    assert not bad, "super cups of the game's leagues planned as knockouts: %s" % bad
    sup = {s["league"]: s for s in pl.get("game_supers") or []}
    assert sorted(sup) == sorted((CHILE, BRAZIL, SCOTLAND)), sup
    for rid, cal in ((CHILE, True), (BRAZIL, True), (SCOTLAND, False)):
        s = sup[rid]
        region = region_of_cid[regrow[rid][M.R_CID]]
        assert s["region"] == region, (rid, s)
        assert s["calendar"] is cal, "%d: calendar %r" % (rid, s["calendar"])
        # the champion's league and the region's cup, whose winner plays (fl26swiss)
        assert s["cup"] == (B.home_cup(regrow, region_of_cid, region) or 0), (rid, s)
        assert s["conf"] == B.comp_conf(base, regrow[rid][M.R_CID]), (rid, s)
    assert sup[CHILE]["cup"] and sup[BRAZIL]["cup"], "Copa Chile / Copa do Brasil not found"
    assert sup[CHILE]["conf"] == 4 and sup[SCOTLAND]["conf"] == 2, (sup[CHILE]["conf"], sup[SCOTLAND]["conf"])
    print("plan: three two-club super cups, Chile and Brazil February-December")

    # 2. the tables: a copy of SUPER_CUP_LIKE, two clubs, in the league's region
    tmp = tempfile.mkdtemp()
    try:
        db = os.path.join(tmp, "common", "etc", "pesdb")
        os.makedirs(db)
        for f in os.listdir(base):
            if f.endswith(".bin"):
                shutil.copy(os.path.join(base, f), db)
        B.game_super_cups(pl, tmp, db, log=lambda *a: None)
        regs, comp, ents = (M.load(db, n) for n in ("CompetitionRegulation.bin", "Competition.bin",
                                                    "CompetitionEntry.bin"))
        for s in pl["game_supers"]:
            assert s["cid"] >= 130, "competition id %d below 130" % s["cid"]
            rows = [regs[i * M.REG:(i + 1) * M.REG] for i in range(len(regs) // M.REG)
                    if B.u16(regs, i * M.REG + M.R_ID) == s["reg"]]
            assert len(rows) == 1, (s["name"], len(rows))
            g = rows[0]
            assert g[M.R_TYPE] == 3 and g[M.R_TEAMS] & 0x3f == 2, \
                "%s: type %d, %d clubs -- not a two-club cup" % (s["name"], g[M.R_TYPE], g[M.R_TEAMS] & 0x3f)
            assert g[M.R_CID] == s["cid"]
            n = sum(1 for i in range(0, len(ents), M.ENT) if ents[i + M.E_CID] == s["cid"])
            assert n == 2, "%s: %d entries" % (s["name"], n)
            rc = [M.dec_region(comp[i * M.COMP + M.REGION_OFF]) for i in range(len(comp) // M.COMP)
                  if comp[i * M.COMP + M.CID_OFF] == s["cid"]]
            assert rc == [s["region"]], (s["name"], rc)
        print("tables: two clubs each, in the league's region")

        # 3. the dates: end of January after a February-December season, else the European super cup's
        dates = B.dates_lines(pl, db)
        cal_like, eu_like = B.like_reg(db, B.CALENDAR_SUPER_DATE_LIKE), B.like_reg(db, B.SUPER_CUP_LIKE)
        days = ",".join(map(str, B.CALENDAR_SUPER_DATE_DAYS))
        for s in pl["game_supers"]:
            want = ("dates %d like=%d days=%s" % (s["reg"], cal_like, days) if s["calendar"]
                    else "dates %d like=%d" % (s["reg"], eu_like))
            assert want in dates, "%s: %r not in %r" % (s["name"], want, dates)
        assert all(int(d) <= 45 for d in days.split(",")), days       # January / early February
        print("dates:", [d for d in dates])

        # 4. the gsuper lines: what puts a February-December one into the New Year season
        #    (fl26joindll) and fills it with the champion and the cup winner (fl26swiss)
        gl = B.gsuper_lines(pl)
        for s in pl["game_supers"]:
            want = "gsuper %d league=%d cup=%d region=%d conf=%d" % (s["reg"], s["league"], s["cup"],
                                                                    s["region"], s["conf"])
            assert want in gl, (want, gl)
        path = os.path.join(tmp, "fl26world.txt")
        fl26world.write_world(path, "_FL26_t", [], ccups=dates + gl)
        text = open(path, encoding="utf-8").read()
        got = {}
        for line in text.splitlines():              # as the Lua modules read it
            m = re.match(r"^\s*gsuper\s+(\d+)(.*)$", line)
            if m:
                got[int(m.group(1))] = {k: int(v) for k, v in re.findall(r"([A-Za-z]+)=(-?\d+)", m.group(2))}
        assert got[sup[CHILE]["reg"]] == {"league": CHILE, "cup": sup[CHILE]["cup"], "region": 18, "conf": 4}, got
        assert fl26world.read_world(path)[1] == [], "a gsuper line read as a league"
        print("world file:", gl)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # the modules read the line: fl26joindll adds a calendar-region one to the New Year season's
    # builder (with its confederation), fl26swiss fills it with the champion and the cup winner
    join = open(os.path.join(ROOT, "sider", "fl26joindll.lua"), encoding="utf-8").read()
    swiss = open(os.path.join(ROOT, "sider", "experimental", "fl26swiss.lua"), encoding="utf-8").read()
    assert 'line:match("^%s*gsuper%s+(%d+)(.*)$")' in join and 'line:match("^%s*gsuper%s+(%d+)(.*)$")' in swiss
    assert re.search(r"cal_region\(G\.region\).*\n\s*BUILDER_EXTRA\[#BUILDER_EXTRA \+ 1\] = G\.id", join)
    assert "scups[#scups + 1] = { G.id, G.league, G.cup }" in swiss
    print("modules: fl26joindll and fl26swiss read gsuper")

    # 5. a country the recipe moves to August-May plays it on the European date
    pl2 = B.plan(recipe(game_seasons=["Chile"]), base)
    assert not next(s for s in pl2["game_supers"] if s["league"] == CHILE)["calendar"]
    print("game_seasons Chile: the super cup follows %s" % B.SUPER_CUP_LIKE)

    # 6. no new league: fl26joindll does not install, so Build says the January one is not played
    text = B.describe(pl)
    assert "NOTE:" in text and "at least one new league" in text, text
    print("all passed")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "D:/dev/fl26-modding-research/out/base-pesdb")
