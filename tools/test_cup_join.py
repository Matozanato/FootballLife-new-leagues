"""python test_cup_join.py <folder with the game's tables> -- B228 (jibibi 24.10.): a new third
division under a shipped second one can put its first clubs into the country's cup next to the
game's two divisions, as the real Coupe de France takes the lower leagues: Ligue 1 + Ligue 2 +
the first clubs of National, 48. Build raises the cup's bracket to the field, the third
division's line carries cupthird= and cupn=, fl26chain.lua sends them to fl26chain.dll
(fl26_chain_cupthird). Without the tick nothing changes."""
import glob, os, re, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fl26world
import leaguebuilder as B
import mkleague as M

N = 0
HERE = os.path.dirname(os.path.abspath(__file__))
CHAIN_LUA = os.path.join(HERE, "..", "sider", "experimental", "fl26chain.lua")
CHAIN_C = os.path.join(HERE, "native", "fl26chain.c")
LIGUE1, LIGUE2, COUPE = 20, 81, 26


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def lua_cups(leagues):
    """fl26chain.lua's from_world cups, with the sixth field (None without lupa)"""
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


def build(base, join):
    L = {"name": "Test National", "country": "France", "clubs": 18, "legs": 2, "exchange": 3, "above": LIGUE2}
    if join:
        L["cup_join"] = True
    recipe = {"world": "_FL26CupJoin", "leagues": [L]}
    game = tempfile.mkdtemp(prefix="fl26-cupjoin-")
    try:
        for d in ("livecpk", "modules", "content"):
            os.makedirs(os.path.join(game, "SiderAddons", d))
        with open(os.path.join(game, "SiderAddons", "sider.ini"), "w") as f:
            f.write("[sider]\n")
        pl = B.plan(recipe, base)
        said = []
        B.build(pl, base, game, False, log=lambda t: said.append(str(t)))
        world = os.path.join(game, "SiderAddons", "livecpk", "_FL26CupJoin")
        _name, leagues = fl26world.read_world(os.path.join(world, "fl26world.txt"))
        reg = glob.glob(os.path.join(world, "**", "CompetitionRegulation.bin"), recursive=True)
        regs = M.load(os.path.dirname(reg[0]), "CompetitionRegulation.bin")
        teams = {B.u16(regs, i * M.REG + M.R_ID): regs[i * M.REG + M.R_TEAMS] & 0x3f
                 for i in range(len(regs) // M.REG)}
        return pl, leagues, teams, B.describe(pl), B.recipe_from_plan(pl, base)
    finally:
        shutil.rmtree(game, ignore_errors=True)


def main(base):
    ok("the field: Ligue 1 18 + Ligue 2 20 + 18 of National -> 48", B.cup_join_field(COUPE, 38, 18) == 48)
    ok("44 + 4 -> 48", B.cup_join_field(COUPE, 44, 4) == 48)
    ok("44 + 3: no field past 44 it fills -> none", B.cup_join_field(COUPE, 44, 3) == 0)
    ok("36 + 6 -> 40", B.cup_join_field(COUPE, 36, 6) == 40)
    ok("a cup whose calendar is not known: none", B.cup_join_field(999, 36, 18) == 0)
    ok("48 is the most fl26chain.dll's lists hold",
       max(B.CUP_JOIN_SIZES) == int(re.search(r"#define MAX_CLUBS\s+(\d+)", open(CHAIN_C, encoding="utf-8").read()).group(1)))
    ok("every field leaves 64 - n byes, a layout the bracket screen has",
       all(64 - n in B.BRACKET_SIZES for n in B.CUP_JOIN_SIZES))

    pl, leagues, teams, said, recipe = build(base, True)
    p = next(q for q in pl["leagues"] if q["name"] == "Test National")
    ok("Check the plan says it", "and the first %d of this league: 48 clubs" % (48 - p["cup_two"]) in said)
    ok("plan: the Coupe de France (%d) is the cup of the region" % COUPE, p.get("cupfield") and p["cupfield"][0] == COUPE)
    ok("plan: National joins it, 48 clubs (%s)" % p.get("cup_join"), p.get("cup_join") == 48)
    ok("Ligue 1 18 + Ligue 2 20 (its 21st entry is no club of the league): 38", p.get("cup_two") == 38)
    line = next(L for L in leagues if L["id"] == p["rid"])
    ok("its line: cup=, cuptop=, cuplow= the game's (%s)" % {k: line.get(k) for k in ("cup", "cuptop", "cuplow")},
       (line.get("cup"), line.get("cuptop"), line.get("cuplow"), line.get("cupall")) == (COUPE, LIGUE1, LIGUE2, 1))
    ok("its line: cupthird= itself, cupn=48", line.get("cupthird") == p["rid"] and line.get("cupn") == 48)
    ok("the cup's bracket raised to 48 in the world's tables (%s)" % teams.get(COUPE), teams.get(COUPE) == 48)
    ok("fl26world.cup_thirds", fl26world.cup_thirds(leagues) == [(COUPE, p["rid"])])
    got = lua_cups(leagues)
    if got is None:
        print("skip - Lua from_world (pip install lupa to run it)")
    else:
        ok("fl26chain.lua sends the cup with its third division (%s)" % got,
           any(c[0] == COUPE and c[5] == p["rid"] and c[4] == 48 and c[3] for c in got))
    ok("the recipe keeps the tick", next(L for L in recipe["leagues"] if L["name"] == "Test National").get("cup_join"))

    pl, leagues, teams, said, recipe = build(base, False)
    p = next(q for q in pl["leagues"] if q["name"] == "Test National")
    line = next(L for L in leagues if L["id"] == p["rid"])
    ok("no tick: the cup keeps the game's two divisions, as before",
       (line.get("cup"), line.get("cuptop"), line.get("cuplow")) == (COUPE, LIGUE1, LIGUE2)
       and line.get("cupthird") is None and line.get("cupn") is None and "cup_join" not in p)
    ok("no tick: the cup's bracket is the game's (%s)" % teams.get(COUPE), teams.get(COUPE) == 18)
    ok("no tick: the recipe has none", "cup_join" not in next(L for L in recipe["leagues"] if L["name"] == "Test National"))
    print("1..%d" % N)


if __name__ == "__main__":
    main(sys.argv[1])
