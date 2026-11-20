"""python test_cups_more.py [<folder with the game's tables>] -- request #4 (06.11.2026, FL 2027
only): more cups for a country's lower divisions.

- A third cup (trophy) on a division of ours below the top one, the way the EFL Trophy, the FA
  Trophy or the Copa RFEF are played: the league cup's single-match knockout of that division and
  the one below it, on days of its own (TROPHY_DAYS), its world line carrying lcup= for fl26chain
  as a league cup does.
- A new country's third division can join its national cup (cup_join, as B228 does for a third
  division under the game's second one): the two divisions and its first clubs, a field the
  bracket screen draws (own_join_field: never 48, B334), cupthird= on the top division's line.
- The league cup and the third cup on days of their own (league_cup_days, trophy_days).
FL26 keeps its cups as they are: the trophy and the days are refused there, a third division's
cup_join of a new country does nothing, as before. Without the tables only the plan-free
parts run."""
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fl26world
import leaguebuilder as B
import mkleague as M
import realcal

CHAIN_LUA = os.path.join(HERE, "..", "sider", "experimental", "fl26chain.lua")
N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def raises(fn, part):
    try:
        fn()
    except B.BuildError as e:
        return part in str(e)
    return False


def lua_cups(leagues):
    """fl26chain.lua's from_world cups (None without lupa)"""
    try:
        from lupa import luajit21 as lj
    except ImportError:
        try:
            from lupa import lua54 as lj
        except ImportError:
            return None
    src = open(CHAIN_LUA, encoding="utf-8").read()
    fn = re.search(r"^local function from_world\(world\).*?^end$", src, re.S | re.M).group(0)
    lua = lj.LuaRuntime()
    f = lua.execute(fn + "\nreturn function(w) local _, _, cups = from_world(w) return cups end")
    out = f(lua.table_from([lua.table_from(L) for L in leagues]))
    return [tuple(out[i][k] for k in (1, 2, 3, 4, 5, 6)) for i in range(1, len(out) + 1)]


def offline():
    days = B.TROPHY_DAYS
    ok("the third cup has the league cup's six day slots", len(days) == B.CUP_DAY_SLOTS == 6)
    ok("its days go in the season's order, after its fill day",
       [B.season_ord(d) for d in days] == sorted(B.season_ord(d) for d in days)
       and B.season_ord(days[0]) > B.season_ord(B.TROPHY_FILL) + 2)
    ok("none is a European day", not set(days) & B.EURO_DAYS)
    ok("each is three days or more from the league cup's and the national cups'",
       all(min(abs(d - x), 365 - abs(d - x)) >= 3 for d in days for x in B.LEAGUE_KO_DAYS + list(B.NATCUP_DAYS)))
    ok("rounds on Tuesdays, the final on a Sunday (2026: day 0 a Thursday)",
       all(d % 7 == 5 for d in days[:-1]) and days[-1] % 7 == 3)
    ok("cup_days reads its own dates", B.cup_days(["10-06", "11-10", "12-01", "02-03", "03-03", "04-05"],
                                                  "L", "the third cup") == days)
    ok("day_md is cup_days the other way round", [B.day_md(d) for d in days]
       == ["10-06", "11-10", "12-01", "02-03", "03-03", "04-05"])
    ok("five dates are refused", raises(lambda: B.cup_days(["10-06"] * 5, "L", "x"), "takes 6 dates"))
    ok("a date that is none is refused", raises(lambda: B.cup_days(["10-06", "11-10", "12-01", "02-30", "03-03",
                                                                    "04-05"], "L", "x"), "not a date"))
    ok("a European day is refused (16 September, day %d)" % realcal.day("09-16"),
       realcal.day("09-16") in B.EURO_DAYS
       and raises(lambda: B.cup_days(["09-16", "11-10", "12-01", "02-03", "03-03", "04-05"], "L", "x"), "European"))
    ok("a national cup day is refused (8 September, day 250, next to 251)",
       raises(lambda: B.cup_days(["09-08", "11-10", "12-01", "02-03", "03-03", "04-05"], "L", "x"), "national cups"))
    ok("dates out of order are refused",
       raises(lambda: B.cup_days(["11-10", "10-06", "12-01", "02-03", "03-03", "04-05"], "L", "x"), "in order"))
    ok("June is past the season", raises(lambda: B.cup_days(["10-06", "11-10", "12-01", "02-03", "03-03",
                                                              "06-07"], "L", "x"), "played from"))
    ok("a calendar-year league's: September to December",
       B.cup_days(["09-22", "10-06", "10-27", "11-17", "12-01", "12-22"], "L", "x", True)
       == [realcal.day(x) for x in ("09-22", "10-06", "10-27", "11-17", "12-01", "12-22")]
       and raises(lambda: B.cup_days(["09-22", "10-06", "10-27", "11-17", "12-01", "02-03"], "L", "x", True),
                  "played from"))
    # the national cup of a new country with its third division (own_join_field)
    ok("18 + 20 and a third of 20: 44 (6 of the third)", B.own_join_field(38, 20) == 44)
    ok("never 48, whatever the third has (B334)", B.own_join_field(40, 20) == 44 and B.own_join_field(44, 20) == 0)
    ok("36 and 40 are fields too", B.own_join_field(34, 2) == 36 and B.own_join_field(38, 2) == 40)
    ok("10 + 10 and a third of 12: 32", B.own_join_field(20, 12) == 32)
    ok("10 + 12 and a third of 3: 24, a field the screen draws", B.own_join_field(22, 3) == 24)
    ok("33..43 that is not 36 or 40 is never a field", not {B.own_join_field(t, 1) for t in range(32, 44)}
       & (set(range(33, 44)) - {36, 40}))
    ok("every field leaves a bye layout the bracket screen has",
       all(k in B.BRACKET_SIZES or 64 - k in B.BRACKET_SIZES
           for k in {B.own_join_field(t, x) for t in range(20, 45) for x in range(1, 33)} - {0}))


def game_dir():
    game = tempfile.mkdtemp(prefix="fl26-cupsmore-")
    for d in ("livecpk", "modules", "content"):
        os.makedirs(os.path.join(game, "SiderAddons", d))
    with open(os.path.join(game, "SiderAddons", "sider.ini"), "w") as f:
        f.write("[sider]\n")
    return game


def build(recipe, base):
    game, fl27 = game_dir(), B.FL27      # build() takes the game's own (use_game): this folder is none
    try:
        pl = B.plan(recipe, base)
        said = []
        B.build(pl, base, game, False, log=lambda t: said.append(str(t)))
        world = os.path.join(game, "SiderAddons", "livecpk", recipe["world"])
        path = os.path.join(world, "fl26world.txt")
        _name, leagues = fl26world.read_world(path)
        text = open(path, encoding="utf-8").read()
        ccups = {int(m.group(1)): m.group(0) for m in re.finditer(r"^ccup (\d+) .*$", text, re.M)}
        regf = [os.path.join(r, f) for r, _d, fs in os.walk(world) for f in fs if f == "CompetitionRegulation.bin"]
        regs = M.load(os.path.dirname(regf[0]), "CompetitionRegulation.bin")
        teams = {B.u16(regs, i * M.REG + M.R_ID): regs[i * M.REG + M.R_TEAMS] & 0x3f
                 for i in range(len(regs) // M.REG)}
        B.FL27 = fl27
        return pl, leagues, ccups, teams, B.describe(pl), B.recipe_from_plan(pl, base)
    finally:
        B.FL27 = fl27
        shutil.rmtree(game, ignore_errors=True)


def efl(trophy=True, days=None):
    """League One and Two of ours under the Championship (79), the EFL Trophy on League One"""
    one = {"name": "Test League One", "country": "England", "clubs": 24, "legs": 2, "exchange": 3, "above": 79}
    if trophy:
        one.update(trophy=True, trophy_name="Test Trophy")
    if days:
        one["trophy_days"] = days
    return {"world": "_FL26CupsMore", "leagues": [
        one, {"name": "Test League Two", "country": "England", "clubs": 24, "legs": 2, "exchange": 4,
              "above": "Test League One"}]}


def zelia(join=True):
    """a new country of three divisions, the third's best clubs in the national cup"""
    third = {"name": "Zel Three", "country": "San Marino", "clubs": 20, "legs": 2, "exchange": 3, "above": "Zel Two"}
    if join:
        third["cup_join"] = True
    return {"world": "_FL26CupsMore", "leagues": [
        {"name": "Zel Top", "country": "San Marino", "clubs": 18, "legs": 2, "exchange": 3, "cup": True,
         "league_cup": True, "league_cup_days": ["09-01", "10-06", "11-11", "12-15", "02-03", "03-22"]},
        {"name": "Zel Two", "country": "San Marino", "clubs": 20, "legs": 2, "exchange": 3, "above": "Zel Top"},
        third]}


def built(base):
    # FL26: refused, or nothing new
    B.FL27 = False
    ok("FL26: a third cup is refused", raises(lambda: B.plan(efl(), base), "FL 2027 only"))
    r = zelia()
    r["leagues"][0].pop("league_cup_days")
    pl = B.plan(r, base)
    top = next(p for p in pl["leagues"] if p["name"] == "Zel Top")
    ok("FL26: a new country's third division leaves its cup as before (%d clubs, no third)"
       % top["own_cup"]["clubs"], top["own_cup"]["clubs"] == 32 and not top["own_cup"].get("third"))
    ok("FL26: own cup days are refused", raises(lambda: B.plan(zelia(), base), "FL 2027 only"))

    B.FL27 = True
    try:
        ok("a third cup on a top division is refused",
           raises(lambda: B.plan({"world": "_X", "leagues": [{"name": "T", "country": "San Marino", "clubs": 18,
                                                              "trophy": True}]}, base), "below the top one"))
        r = efl()
        r["leagues"][1]["trophy"] = True
        ok("two divisions in a row with a third cup are refused", raises(lambda: B.plan(r, base), "in a row"))

        pl, leagues, ccups, teams, said, recipe = build(efl(), base)
        rid = {p["name"]: p["rid"] for p in pl["leagues"]}
        t = next(c for c in pl["home_cups"] if c.get("trophy"))
        ok("the trophy is planned: League One's 24 and the first 20 of League Two, 44",
           t["entry"] == [(rid["Test League One"], k) for k in range(1, 25)]
           + [(rid["Test League Two"], k) for k in range(1, 21)])
        ok("on its own days, filled with the league cup, a copy of the FA Cup's row",
           t["opts"]["days"] == B.TROPHY_DAYS and t["opts"]["fill"] == B.LEAGUE_KO_FILL
           and t["opts"]["like"] == B.LEAGUE_KO_LIKE and t["opts"]["draw"] == "byes" and not t["opts"]["reserve"])
        ok("its name", t["name"] == "Test Trophy" and t["code"] == "FL_%03d_TCUP" % rid["Test League One"])
        one = next(L for L in leagues if L["id"] == rid["Test League One"])
        ok("League One's line: lcup= the trophy, lcuplow= League Two, lcupn=44 (%s)"
           % {k: one.get(k) for k in ("lcup", "lcuplow", "lcupn")},
           one.get("lcup") in ccups and one.get("lcuplow") == rid["Test League Two"] and one.get("lcupn") == 44)
        ok("its ccup line has the trophy's days and like=",
           "days=%s" % ",".join(map(str, B.TROPHY_DAYS)) in ccups[one["lcup"]]
           and "like=%d" % B.LEAGUE_KO_LIKE in ccups[one["lcup"]] and "national=1" in ccups[one["lcup"]])
        ok("the FA Cup line stays on League One's line", one.get("cup") is not None and one.get("cuptop") == 17)
        ok("fl26chain gets it after the national cups",
           (one["lcup"], rid["Test League One"], rid["Test League Two"], True, 44) == fl26world.chain_cups(leagues)[-1])
        got = lua_cups(leagues)
        if got is None:
            print("skip - Lua from_world (pip install lupa to run it)")
        else:
            ok("fl26chain.lua sends it (%s)" % (got[-1],),
               got[-1][:5] == (one["lcup"], rid["Test League One"], rid["Test League Two"], True, 44))
        ok("Check says what it is", "Test Trophy: third cup (trophy)" in said)
        r1 = next(L for L in recipe["leagues"] if L["name"] == "Test League One")
        ok("the recipe keeps it", r1.get("trophy") and r1.get("trophy_name") == "Test Trophy"
           and "trophy_days" not in r1)
        ok("an unticked trophy gives its ids back",
           "ccup:FL_%03d_TCUP" % rid["Test League One"] not in B.ticked_cups(
               {"ccup:FL_%03d_TCUP" % rid["Test League One"]: {"cid": 1}}, efl(False)["leagues"],
               ["Test League One", "Test League Two"], {"test league one": {"rid": rid["Test League One"]}}))

        own = ["10-07", "11-12", "11-27", "01-29", "02-24", "04-12"]
        pl = B.plan(efl(days=own), base)
        t = next(c for c in pl["home_cups"] if c.get("trophy"))
        ok("its own days", t["opts"]["days"] == [realcal.day(x) for x in own])
        ok("the recipe keeps them", next(L for L in B.recipe_from_plan(pl, base)["leagues"]
                                         if L["name"] == "Test League One").get("trophy_days") == own)

        pl, leagues, ccups, teams, said, recipe = build(zelia(), base)
        rid = {p["name"]: p["rid"] for p in pl["leagues"]}
        c = next(p for p in pl["leagues"] if p["name"] == "Zel Top")["own_cup"]
        ok("the national cup: 18 + 20 and the first 6 of the third division, 44 (%d)" % c["clubs"],
           c["clubs"] == 44 and c["third"] == rid["Zel Three"] and c["like"] == B.NATIONAL_CUP_ANY[0])
        top = next(L for L in leagues if L["id"] == rid["Zel Top"])
        ok("the top line: cup=, cuptop=, cuplow=, cupthird=, cupn=44 (%s)"
           % {k: top.get(k) for k in ("cup", "cuptop", "cuplow", "cupthird", "cupn")},
           (top.get("cup"), top.get("cuptop"), top.get("cuplow"), top.get("cupthird"), top.get("cupn"), top.get("cupall"))
           == (c["reg"], rid["Zel Top"], rid["Zel Two"], rid["Zel Three"], 44, 1))
        ok("the cup's bracket in the world's tables is 44 (%s)" % teams.get(c["reg"]), teams.get(c["reg"]) == 44)
        ok("fl26world.cup_thirds has it", (c["reg"], rid["Zel Three"]) in fl26world.cup_thirds(leagues))
        got = lua_cups(leagues)
        if got is not None:
            ok("fl26chain.lua sends the third division with it",
               any(x[0] == c["reg"] and x[5] == rid["Zel Three"] and x[4] == 44 for x in got))
        ok("Check says it", "the two divisions and the first 6 of Zel Three" in said)
        lc = next(h for h in pl["home_cups"] if h["code"] == "FL_%03d_LCUP" % rid["Zel Top"])
        ok("the league cup on its own days", lc["opts"]["days"] == [realcal.day(x) for x in zelia()["leagues"][0]
                                                                     ["league_cup_days"]])
        ok("the recipe keeps the tick and the days",
           next(L for L in recipe["leagues"] if L["name"] == "Zel Three").get("cup_join")
           and next(L for L in recipe["leagues"] if L["name"] == "Zel Top").get("league_cup_days")
           == zelia()["leagues"][0]["league_cup_days"])

        r = zelia(False)
        pl = B.plan(r, base)
        c = next(p for p in pl["leagues"] if p["name"] == "Zel Top")["own_cup"]
        ok("no tick: the two divisions, 38 on the shipped field of 36 under it (FL 2027, mato 08.11.; was 32), no third (%d)" % c["clubs"],
           c["clubs"] == 36 and not c.get("third"))

        # B445 (b2y6421, 12.11.2026): the Saudi King's Cup is 32 clubs -- the Pro League's 18 and the
        # first 14 of the First Division. 18 + 18 = 36 is no field for a game's cup, so the recipe
        # names the field (cup_field)
        def saudi(**kw):
            L = {"name": "Saudi Two", "country": "Saudi Arabia", "clubs": 18, "legs": 2, "above": 162, "exchange": 3}
            L.update(kw)
            return {"world": "_X", "leagues": [L]}
        p = B.plan(saudi(), base)["leagues"][0]
        ok("18 under the Saudi league: 36 is no field, the cup stays the top league's", p["cup"] == 164 and not p.get("cup_all"))
        pl, leagues, _cc, teams, _said, recipe = build(saudi(cup_field=32), base)
        p = pl["leagues"][0]
        line = next(L for L in leagues if L["id"] == p["rid"])
        ok("cup_field 32: the cup takes both, 32 in all", p.get("cup_all") == 32 and p.get("cup_field") == 32)
        ok("its line: cup=164 cupall=1 cupn=32 (%r)" % ((line.get("cup"), line.get("cupall"), line.get("cupn")),),
           (line.get("cup"), line.get("cupall"), line.get("cupn")) == (164, 1, 32))
        ok("the cup's bracket in the world's tables is 32 (%s)" % teams.get(164), teams.get(164) == 32)
        ok("fl26world.chain_cups has it", (164, 162, p["rid"], True, 32) in fl26world.chain_cups(leagues))
        ok("the recipe keeps cup_field", recipe["leagues"][0].get("cup_field") == 32)
        for bad in (36, 18, 31, 40, "32"):
            ok("cup_field %r is refused" % (bad,), raises(lambda: B.plan(saudi(cup_field=bad), base), "cup_field"))
    finally:
        B.FL27 = False


if __name__ == "__main__":
    offline()
    if len(sys.argv) > 1:
        built(sys.argv[1])
    else:
        print("skip - the build (give the folder with the game's tables)")
    print("1..%d" % N)
