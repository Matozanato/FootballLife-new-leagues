"""python test_league_cup_chain.py [<folder with the game's tables>] -- a world's own league cup
goes to fl26chain like its national cup (B32, Discord Erax 2026-10-15): the game fills a league
cup from the region's league with the lowest regulation id, not from its entry list, so Zelia's
Copa Rey Alverio (Liga Pro Zeliana 20 + Liga Nacional 22, a cup of 32) held the 22 of the second
division alone and Competition Info -> the cup -> Fixtures crashed (#74). The top league's world
line now carries lcup=, lcuplow=, lcupn=; fl26chain.lua sends those after the national cups, and
no more than fl26chain.dll's MAX_CUPS. Without the tables only the world-file and Lua parts run."""
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fl26world

ROOT = os.path.dirname(HERE)
CHAIN_LUA = os.path.join(ROOT, "sider", "experimental", "fl26chain.lua")
CHAIN_C = os.path.join(HERE, "native", "fl26chain.c")
N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def lua_from_world(leagues):
    """fl26chain.lua's from_world on these league lines, in Lua (None without lupa)"""
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
    return [tuple(out[i][k] for k in (1, 2, 3, 4, 5)) for i in range(1, len(out) + 1)]


def offline():
    # the cap is the DLL's
    c = open(CHAIN_C, encoding="utf-8").read()
    lua = open(CHAIN_LUA, encoding="utf-8").read()
    ok("MAX_CUPS 16 in fl26chain.c, fl26chain.lua and fl26world",
       re.search(r"#define MAX_CUPS (\d+)", c).group(1) == "16"
       and re.search(r"^local MAX_CUPS = (\d+)", lua, re.M).group(1) == "16"
       and fl26world.MAX_CHAIN_CUPS == 16)
    ok("fl26chain.lua leaves the cups past MAX_CUPS to the game, with a log line",
       re.search(r"for i = #CUPS, MAX_CUPS \+ 1, -1 do\s+log\(.*?\)\s+CUPS\[i\] = nil", lua, re.S) is not None)
    ok("fl26world writes lcup, lcuplow, lcupn", {"lcup", "lcuplow", "lcupn"} <= set(fl26world.KEYS))

    # Zelia: the national cup and the league cup on the top league's line
    zelia = [{"id": 49, "tier": 1, "clubs": 20, "cup": 264, "cuptop": 49, "cuplow": 11, "cupall": 1,
              "cupn": 32, "lcup": 266, "lcuplow": 11, "lcupn": 32},
             {"id": 11, "tier": 2, "clubs": 22, "above": 49}]
    want = [(264, 49, 11, True, 32), (266, 49, 11, True, 32)]
    ok("chain_cups: national cup, then the league cup of both leagues", fl26world.chain_cups(zelia) == want)
    one = [{"id": 60, "tier": 1, "clubs": 16, "lcup": 270, "lcuplow": 0, "lcupn": 16}]
    ok("a league cup of one league: lcuplow=0", fl26world.chain_cups(one) == [(270, 60, 0, True, 16)])
    ok("no lcupn, no league cup", fl26world.chain_cups([{"id": 60, "lcup": 270}]) == [])

    # 12 countries with both cups: the league cups go after all 12 national cups, the last 8
    # are past the DLL's 16
    many = []
    for k in range(12):
        many += [{"id": 100 + k, "tier": 1, "clubs": 18, "cup": 200 + k, "cuptop": 100 + k, "cuplow": 0,
                  "cupall": 1, "cupn": 18, "lcup": 220 + k, "lcuplow": 0, "lcupn": 18}]
    got = fl26world.chain_cups(many)
    ok("national cups first, league cups after", [c[0] for c in got] == list(range(200, 212)) + list(range(220, 232)))
    ok("the first 16 keep every national cup", {c[0] for c in got[:16]} >= set(range(200, 212)))

    # the old lines read as before
    old = [{"id": 180, "tier": 2, "above": 81, "cup": 55}, {"id": 181, "tier": 3, "above": 180, "cup": 23,
                                                          "cuptop": 17, "cuplow": 81}]
    ok("old cup lines unchanged", fl26world.chain_cups(old) == [(55, 81, 180, False, None), (23, 17, 81, True, None)])

    # B122 (Jabo9 17.10.): the Carabao Cup of the game's Premier League (17) on our League One's
    # line (reg 11, under the Championship 79), next to the FA Cup's cup=/cuptop=/cuplow=
    eng = [{"id": 11, "tier": 3, "clubs": 24, "above": 79, "cup": 23, "cuptop": 17, "cuplow": 79,
            "lcup": 266, "lcuptop": 17, "lcuplow": 79, "lcupn": 44},
           {"id": 49, "tier": 4, "clubs": 24, "above": 11}]
    ok("fl26world writes lcuptop", "lcuptop" in fl26world.KEYS)
    ok("chain_cups: a game league's league cup is the game's top league and the one below",
       fl26world.chain_cups(eng) == [(23, 17, 79, True, None), (266, 17, 79, True, 44)])

    for name, L in (("Zelia", zelia), ("one league", one), ("12 countries", many), ("old lines", old),
                    ("England", eng)):
        got = lua_from_world(L)
        if got is None:
            print("skip - Lua from_world (pip install lupa to run it)")
            break
        ok("fl26chain.lua from_world = fl26world.chain_cups (%s)" % name, got == fl26world.chain_cups(L))


def built(base):
    import leaguebuilder as B
    recipe = {"world": "_FL26LcupChain", "leagues": [
        {"name": "Lcup Top", "country": "San Marino", "clubs": 20, "legs": 2, "exchange": 3,
         "cup": True, "league_cup": True},
        {"name": "Lcup Second", "country": "San Marino", "clubs": 22, "legs": 2, "exchange": 3,
         "above": "Lcup Top"}]}
    game = tempfile.mkdtemp(prefix="fl26-lcup-")
    try:
        for d in ("livecpk", "modules", "content"):
            os.makedirs(os.path.join(game, "SiderAddons", d))
        with open(os.path.join(game, "SiderAddons", "sider.ini"), "w") as f:
            f.write("[sider]\n")
        said = []
        pl = B.plan(recipe, base)
        B.build(pl, base, game, False, log=lambda t: said.append(str(t)))
        path = os.path.join(game, "SiderAddons", "livecpk", "_FL26LcupChain", "fl26world.txt")
        _name, leagues = fl26world.read_world(path)
        rid = {p["name"]: p["rid"] for p in pl["leagues"]}
        top = next(L for L in leagues if L["id"] == rid["Lcup Top"])
        ccups = {int(m.group(1)): m.group(2).count(":") for m in
                 re.finditer(r"^ccup (\d+) .*?entry=(\S+)", open(path, encoding="utf-8").read(), re.M)}
        ok("the top league's line has lcup= (%s)" % top.get("lcup"), top.get("lcup") in ccups)
        ok("lcuplow= is the league below", top.get("lcuplow") == rid["Lcup Second"])
        ok("lcupn= is the cup's field (%s), a size the bracket screen draws" % top.get("lcupn"),
           top.get("lcupn") == ccups.get(top.get("lcup")) and top.get("lcupn") in B.LEAGUE_KO_SIZES)
        ok("the national cup line as before", top.get("cup") and top.get("cuplow") == rid["Lcup Second"])
        ok("both cups go to fl26chain", [c[0] for c in fl26world.chain_cups(leagues)] == [top["cup"], top["lcup"]])
        ok("no warning about too many cups", not any("more than 16" in t for t in said))
    finally:
        shutil.rmtree(game, ignore_errors=True)


def built_game(base):
    """B122: the Premier League's league cup (game_cups) with League One and Two of ours under the
    Championship -- the cup's line names the Premier League and the Championship, not ours"""
    import leaguebuilder as B
    recipe = {"world": "_FL26LcupGame", "game_cups": [{"league": 17, "league_cup": True, "name": "Carabao Cup"}],
              "leagues": [
                  {"name": "Test League One", "country": "England", "clubs": 24, "legs": 2, "exchange": 3, "above": 79},
                  {"name": "Test League Two", "country": "England", "clubs": 24, "legs": 2, "exchange": 4,
                   "above": "Test League One"}]}
    game = tempfile.mkdtemp(prefix="fl26-lcupg-")
    try:
        for d in ("livecpk", "modules", "content"):
            os.makedirs(os.path.join(game, "SiderAddons", d))
        with open(os.path.join(game, "SiderAddons", "sider.ini"), "w") as f:
            f.write("[sider]\n")
        said = []
        pl = B.plan(recipe, base)
        B.build(pl, base, game, False, log=lambda t: said.append(str(t)))
        path = os.path.join(game, "SiderAddons", "livecpk", "_FL26LcupGame", "fl26world.txt")
        _name, leagues = fl26world.read_world(path)
        ccups = {int(m.group(1)): m.group(2).count(":") for m in
                 re.finditer(r"^ccup (\d+) .*?entry=(\S+)", open(path, encoding="utf-8").read(), re.M)}
        got = [c for c in fl26world.chain_cups(leagues) if c[0] in ccups]
        ok("the Carabao Cup goes to fl26chain once (%s)" % got, len(got) == 1)
        ok("its top league is the Premier League, the one below the Championship", got and got[0][1:3] == (17, 79))
        ok("its field is the cup's (%s), a size the bracket screen draws" % (got and got[0][4]),
           got and got[0][4] == ccups[got[0][0]] and got[0][4] in B.LEAGUE_KO_SIZES)
        ok("no league of ours is under 17 in it", not any(L.get("lcuptop") and L["lcuptop"] != 17 for L in leagues))
    finally:
        shutil.rmtree(game, ignore_errors=True)


if __name__ == "__main__":
    offline()
    if len(sys.argv) > 1:
        built(sys.argv[1])
        built_game(sys.argv[1])
    else:
        print("skip - the build (give the folder with the game's tables)")
    print("all passed (%d)" % N)
