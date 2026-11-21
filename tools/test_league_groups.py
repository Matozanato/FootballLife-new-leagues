"""python test_league_groups.py [<folder with the game's tables>] -- groups of one division and
promotion play-offs in the League Builder (GitHub #98).

Several leagues with the same "above" are groups of one division: three Serie C groups under
Serie B, nine Serie D groups under the three of them. plan() makes them a set (group_sets): the
league above sends down what the groups send up, only the group with the lowest regulation id is
linked to it in the tables (the game follows one link each way), and the world file carries the
set as gset/ghome lines that fl26chain.lua sends to fl26chain.dll, which moves the whole set at
once (tools/native/test_chain_groups.c). "playoff" adds a knockout of the league's places
(kind "promo") and a poff line; its winner takes the place. Without the tables only the world
file and Lua parts run."""
import contextlib
import copy
import glob
import io
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
COMPTAB_LUA = os.path.join(ROOT, "sider", "experimental", "fl26comptab.lua")
CHAIN_C = os.path.join(HERE, "native", "fl26chain.c")
SERIE_B = 82
N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def lua():
    try:
        from lupa import luajit21 as lj
    except ImportError:
        try:
            from lupa import lua54 as lj
        except ImportError:
            return None
    return lj.LuaRuntime()


def lua_groups(lines):
    """fl26chain.lua's group_line on these lines: (gsets, homes, poffs) as fl26world.read_groups
    gives them (None without lupa)"""
    rt = lua()
    if rt is None:
        return None
    src = open(CHAIN_LUA, encoding="utf-8").read()
    head = re.search(r"^local GSETS, GHOMES, POFFS = \{\}, \{\}, \{\}$.*?^local function group_line\(line\).*?^end$",
                     src, re.S | re.M).group(0)
    f = rt.execute(head + "\nreturn function(ls) for _, l in ipairs(ls) do group_line(l) end "
                   "return GSETS, GHOMES, POFFS end")
    gs, gh, po = f(rt.table_from(lines))
    tl = lambda t: [tuple(t[i][k] for k in range(1, len(t[i]) + 1)) for i in range(1, len(t) + 1)]
    gsets = [(tl(gs[i].ups), tl(gs[i].lows)) for i in range(1, len(gs) + 1)]
    homes = {}
    for t, lid in tl(gh):
        homes.setdefault(lid, []).append(t)
    poffs = [(po[i][1], po[i][2], po[i][3], (po[i][4], po[i][5]) if po[i][4] else None, tl(po[i][6]))
             for i in range(1, len(po) + 1)]
    return gsets, homes, poffs


def lua_borders(lines):
    """fl26chain.lua's GBORDERS after group_line on these lines: [(group, team id, neighbour)]"""
    rt = lua()
    if rt is None:
        return None
    src = open(CHAIN_LUA, encoding="utf-8").read()
    head = re.search(r"^local GSETS, GHOMES, POFFS = \{\}, \{\}, \{\}$.*?^local function group_line\(line\).*?^end$",
                     src, re.S | re.M).group(0)
    f = rt.execute(head + "\nreturn function(ls) for _, l in ipairs(ls) do group_line(l) end return GBORDERS end")
    g = f(rt.table_from(lines))
    return [tuple(g[i][k] for k in range(1, 4)) for i in range(1, len(g) + 1)]


def lua_from_world(leagues):
    """fl26chain.lua's from_world on these league lines: its chains (None without lupa)"""
    rt = lua()
    if rt is None:
        return None
    src = open(CHAIN_LUA, encoding="utf-8").read()
    fn = re.search(r"^local function from_world\(world\).*?^end$", src, re.S | re.M).group(0)
    f = rt.execute(fn + "\nreturn function(w) local chains = from_world(w) return chains end")
    out = f(rt.table_from([rt.table_from(L) for L in leagues]))
    return [tuple(out[i][k] for k in range(1, 5)) for i in range(1, len(out) + 1)]


def lua_shipped_demote(leagues):
    """fl26comptab.lua's apply_world: its SHIPPED_DEMOTE (None without lupa)"""
    rt = lua()
    if rt is None:
        return None
    src = open(COMPTAB_LUA, encoding="utf-8").read()
    fn = re.search(r"^local function apply_world\(world\).*?^end$", src, re.S | re.M).group(0)
    f = rt.execute("local OUR_IDS, RESLOT, APPEND, COUNTS, SHIPPED_DEMOTE, ID_COUNTRY\nlocal RESHAPE = {}\n"
                   "local PROTECTED = {}\nlocal function log() end\n" + fn
                   + "\nreturn function(w) apply_world(w) return SHIPPED_DEMOTE end")
    got = f(rt.table_from([rt.table_from(L) for L in leagues]))
    return {k: got[k] for k in got.keys()}


def offline():
    c = open(CHAIN_C, encoding="utf-8").read()
    import leaguebuilder as B
    ok("MAX_GSETS / MAX_GSIDE the same in fl26chain.c and leaguebuilder",
       int(re.search(r"#define MAX_GSETS\s+(\d+)", c).group(1)) == B.MAX_GSETS
       and int(re.search(r"#define MAX_GSIDE\s+(\d+)", c).group(1)) == B.MAX_GSIDE)
    ok("fl26world writes group=", "group" in fl26world.KEYS)
    sets = [([(82, 4)], [(300, 1, 82), (301, 1, 82), (302, 2, 82)]),
            ([(300, 3), (301, 3), (302, 3)], [(310, 1, 300), (311, 1, 300), (312, 1, 301), (313, 1, 0)])]
    homes = {300: [1000, 1001], 310: [2000]}
    poffs = [(900, 82, 302, (302, 2), [(302, 2), (302, 5), (302, 3), (302, 4)]), (901, 81, 303, None, [(81, 16), (303, 3)])]
    lines = fl26world.group_lines(sets, homes, poffs)
    ok("group_lines: gset, ghome and poff lines (%s)" % lines[0],
       lines[0] == "gset 0 up=82:4 low=300:1:82,301:1:82,302:2:82"
       and "ghome 300 1000,1001" in lines and "poff 901 up=81 low=303 entry=81:16,303:3" in lines
       and "poff 900 up=82 low=302 hold=302:2 entry=302:2,302:5,302:3,302:4" in lines)
    # zone_clubs: the clubs above whose region a group is (Bayern's to Regionalliga Bayern)
    zl = lambda: {"leagues": [
        {"rid": 82, "name": "3. Liga", "teams": [500, 501, 502], "club_names": ["Ingolstadt", "Rostock", "Aue"]},
        {"rid": 300, "name": "RL Bayern", "teams": [1000, 1001], "club_names": ["Bayreuth", "Unterhaching"],
         "zone_clubs": ["ingolstadt", 77, "Unterhaching"]},
        {"rid": 301, "name": "RL Nordost", "teams": [1100], "club_names": ["Chemnitz"], "zone_clubs": ["Rostock", "Aue"]}]}
    pl, hm = zl(), {300: [1000, 1001], 301: [1100]}
    B.zone_homes(pl, hm)
    ok("zone_homes: a name of the leagues and a team id join the group's homes; its own club stays",
       hm == {300: [1000, 1001, 500, 77], 301: [1100, 501, 502]})
    for bad, why in (("Ingolstad", "a name no league has"), ("Rostock", "a club of two groups")):
        pl = zl()
        pl["leagues"][1]["zone_clubs"] = [bad]
        try:
            B.zone_homes(pl, {300: [1000, 1001], 301: [1100]})
            ok("zone_homes: %s is a BuildError" % why, False)
        except B.BuildError:
            ok("zone_homes: %s is a BuildError" % why, True)
    # a club has a home in each set (08.11.2026: the TFF 2. Lig groups and the TFF 3. Lig groups below)
    pl = zl()
    pl["leagues"].append({"rid": 310, "name": "Bayernliga Nord", "teams": [2000], "club_names": ["Ansbach"],
                          "zone_clubs": ["Ingolstadt", "Bayreuth"]})
    hm = {300: [1000, 1001], 301: [1100], 310: [2000]}
    B.zone_homes(pl, hm, {300: 0, 301: 0, 310: 1})
    ok("zone_homes: a club named in groups of two sets gets a home in each, a group's club too in the set below",
       hm[300] == [1000, 1001, 500, 77] and hm[310] == [2000, 500, 1000])
    d = tempfile.mkdtemp(prefix="fl26-groups-")
    try:
        path = os.path.join(d, "fl26world.txt")
        fl26world.write_world(path, "_T", [{"id": 300, "tier": 3, "clubs": 20, "above": 82, "promote": 1, "group": 0}],
                              groups=lines)
        ok("read_groups gives back what group_lines wrote", fl26world.read_groups(path) == (sets, homes, poffs))
        _n, L = fl26world.read_world(path)
        ok("read_world: group=0 on the league line", L[0].get("group") == 0)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    # 16.11.2026: zone_border -> gborder lines (the border clubs of a group, in the recipe's order)
    bpl = {"leagues": [
        {"rid": 300, "name": "Girone A", "group": 0, "teams": [1000, 1001, 1002], "club_names": ["Pro Patria", "Lecco", "Novara"],
         "zone_border": [{"club": "novara", "to": "Girone B"}, {"club": 1000, "to": "Girone B"}]},
        {"rid": 301, "name": "Girone B", "group": 0, "teams": [1100], "club_names": ["Rimini"]}]}
    bd = B.zone_borders(bpl)
    ok("zone_borders: a name and a team id of the group, its neighbour's rid, in the recipe's order (%s)" % bd,
       bd == {300: [(1002, 301), (1000, 301)]})
    for bad in ({"club": "Rimini", "to": "Girone B"}, {"club": 1100, "to": "Girone B"}, {"club": "Lecco", "to": "Girone Z"}):
        bp = copy.deepcopy(bpl)
        bp["leagues"][0]["zone_border"] = [bad]
        try:
            B.zone_borders(bp)
            ok("zone_borders: %r is a BuildError" % bad, False)
        except B.BuildError:
            ok("zone_borders: %r is a BuildError" % bad, True)
    blines = fl26world.group_lines(sets, homes, poffs, bd)
    ok("group_lines: a gborder line after the others (%s)" % blines[-1],
       blines[:-1] == lines and blines[-1] == "gborder 300 1002:301,1000:301")
    d = tempfile.mkdtemp(prefix="fl26-groups-")
    try:
        path = os.path.join(d, "fl26world.txt")
        fl26world.write_world(path, "_T", [{"id": 300, "tier": 3, "clubs": 20, "above": 82, "promote": 1, "group": 0}],
                              groups=blines)
        ok("read_borders gives back what group_lines wrote, read_groups the rest as before",
           fl26world.read_borders(path) == bd and fl26world.read_groups(path) == (sets, homes, poffs))
        fl26world.write_world(path, "_T", [{"id": 300, "tier": 3, "clubs": 20, "above": 82, "promote": 1, "group": 0}],
                              groups=lines)
        ok("read_borders: a world without gborder lines (every world before 16.11.2026) has none",
           fl26world.read_borders(path) == {})
    finally:
        shutil.rmtree(d, ignore_errors=True)
    got = lua_groups(lines)
    if got is None:
        print("skip - Lua (pip install lupa to run it)")
        return
    ok("fl26chain.lua reads the lines as fl26world.read_groups does", got == (sets, homes, poffs))
    ok("fl26chain.lua reads the gset/ghome/poff lines the same with a gborder line among them",
       lua_groups(blines) == (sets, homes, poffs))
    ok("fl26chain.lua reads the gborder line as fl26world.read_borders does (%s)" % lua_borders(blines),
       lua_borders(blines) == [(300, 1002, 301), (300, 1000, 301)] and lua_borders(lines) == [])
    world = [{"id": 300, "tier": 3, "clubs": 20, "above": 82, "promote": 1, "group": 0},
             {"id": 301, "tier": 3, "clubs": 20, "above": 82, "promote": 1, "group": 0},
             {"id": 302, "tier": 3, "clubs": 20, "above": 82, "promote": 2, "group": 0},
             {"id": 320, "tier": 2, "clubs": 18, "demote": 3},
             {"id": 321, "tier": 3, "clubs": 18, "above": 320, "promote": 3}]
    ch = lua_from_world(world)
    ok("fl26chain.lua: no chain for a group, the plain pair keeps its own (%s)" % ch,
       [c[:2] for c in ch] == [(320, 321)])
    sd = lua_shipped_demote(world + [{"id": 330, "tier": 3, "clubs": 20, "above": 81, "promote": 2}])
    ok("fl26comptab.lua: Serie B sends down the sum of its groups (%s), Ligue 2 a plain pair's 2" % sd,
       sd.get(82) == 4 and sd.get(81) == 2)


def quiet_plan(B, recipe, base):
    with contextlib.redirect_stdout(io.StringIO()):
        return B.plan(copy.deepcopy(recipe), base)


def problems(B, recipe, base):
    try:
        quiet_plan(B, recipe, base)
    except (B.BuildError, B.PlanProblems) as e:
        return str(e)
    return ""


def lg(name, clubs=20, **k):
    return dict({"name": name, "country": "Italy", "clubs": clubs, "legs": 2}, **k)


def plans(B, base):
    # 1. three groups under Serie B of the game
    r = {"world": "_FL26Groups", "leagues": [lg("Grp A", above=SERIE_B, exchange=1), lg("Grp B", above=SERIE_B, exchange=1),
                                             lg("Grp C", above=SERIE_B, exchange=2)]}
    pl = quiet_plan(B, r, base)
    by = {p["name"]: p for p in pl["leagues"]}
    rids = sorted(p["rid"] for p in pl["leagues"])
    ok("1. one set: Serie B sends 4 down, the three groups 1, 1 and 2 up (%s)" % pl["gsets"],
       pl["gsets"] == [{"ups": [(SERIE_B, 4)], "lows": [(by[n]["rid"], by[n]["exchange"], SERIE_B)
                                                         for n in sorted(by, key=lambda n: by[n]["rid"])]}])
    ok("1. only the group of the lowest id is linked to Serie B",
       [p["link"] for p in sorted(pl["leagues"], key=lambda p: p["rid"])] == [True, False, False]
       and min(rids) == next(p["rid"] for p in pl["leagues"] if p["link"]))
    ok("1. all three in set 0, on one division", {p["group"] for p in pl["leagues"]} == {0}
       and len({p["tier"] for p in pl["leagues"]}) == 1)
    rec = B.recipe_from_plan(pl, base)
    ok("1. the recipe given back is the same set", quiet_plan(B, rec, base)["gsets"] == pl["gsets"])

    # 2. nine under three under a league of the recipe
    L = [lg("Top", 20), lg("C1", above="Top", exchange=1), lg("C2", above="Top", exchange=1), lg("C3", above="Top", exchange=1)]
    for k in range(9):
        L.append(lg("D%d" % (k + 1), 18, above="C%d" % (k // 3 + 1), exchange=1))
    pl = quiet_plan(B, {"world": "_FL26Groups2", "leagues": L}, base)
    by = {p["name"]: p for p in pl["leagues"]}
    s = pl["gsets"]
    ok("2. two sets: Top over the C groups, the C groups over the nine D groups",
       len(s) == 2 and s[0]["ups"] == [(by["Top"]["rid"], 3)]
       and sorted(r for r, _n in s[1]["ups"]) == sorted(by["C%d" % k]["rid"] for k in (1, 2, 3))
       and all(n == 3 for _r, n in s[1]["ups"]) and len(s[1]["lows"]) == 9)
    ok("2. each D group's league above is in its low= (the pref)",
       all(a == by["C%d" % ((int(n[1:]) - 1) // 3 + 1)]["rid"] for r, _x, a in s[1]["lows"]
           for n in [next(k for k, p in by.items() if p["rid"] == r)]))
    ok("2. the C groups and D groups are in their sets", {by["C%d" % k]["group"] for k in (1, 2, 3)} == {0}
       and {by["D%d" % k]["group"] for k in range(1, 10)} == {1} and by["Top"].get("group") is None)
    ok("2. one link per set", sum(1 for p in pl["leagues"] if p.get("group") == 0 and p["link"]) == 1
       and sum(1 for p in pl["leagues"] if p.get("group") == 1 and p["link"]) == 1)
    L2 = copy.deepcopy(L)
    L2[1]["relegate"] = 5
    pl = quiet_plan(B, {"world": "_FL26Groups2", "leagues": L2}, base)
    by = {p["name"]: p for p in pl["leagues"]}
    ok("2. relegate 5 on C1: the other two share the 4 left (%s)" % pl["gsets"][1]["ups"],
       dict(pl["gsets"][1]["ups"]) == {by["C1"]["rid"]: 5, by["C2"]["rid"]: 2, by["C3"]["rid"]: 2})

    # 3. what is refused
    L3 = copy.deepcopy(L)
    L3[4]["exchange"] = 2                       # 10 up from the D groups: not 3 a C group
    ok("3. counts that do not share out evenly", "do not share out evenly" in problems(B, {"world": "_W", "leagues": L3}, base))
    L3 = copy.deepcopy(L)
    for x in L3[1:4]:
        x["relegate"] = 4
    ok("3. relegate that does not add up", "must add up" in problems(B, {"world": "_W", "leagues": L3}, base))
    r3 = {"world": "_W", "leagues": [lg("A", 18, above=SERIE_B, exchange=1),
                                     lg("B", 18, above=SERIE_B, exchange=1, apertura=True)]}
    ok("3. Apertura/Clausura in a set", "groups of one division cannot have" in problems(B, r3, base))
    r3 = {"world": "_W", "leagues": [lg("A", 10, above=SERIE_B, exchange=10), lg("B", above=SERIE_B, exchange=0)]}
    ok("3. a group that would send all its clubs", "would send all its clubs" in problems(B, r3, base))

    # 3c. 16.11.2026: zone_border, the border clubs a group may move to a neighbour for a club of its region
    na = ["A club %d" % i for i in range(1, 21)]
    zr = lambda zb, **k: {"world": "_FL26Border", "leagues": [
        lg("Grp A", above=SERIE_B, exchange=1, club_names=na, zone_border=zb), lg("Grp B", above=SERIE_B, exchange=1),
        lg("Grp C", above=SERIE_B, exchange=1)] + k.get("more", [])}
    pl = quiet_plan(B, zr([{"club": "A club 7", "to": "Grp B"}, {"club": "a club 3", "to": "Grp C"}]), base)
    by = {p["name"]: p for p in pl["leagues"]}
    ok("3c. zone_border goes through the plan as the recipe gives it", by["Grp A"]["zone_border"] ==
       [{"club": "A club 7", "to": "Grp B"}, {"club": "a club 3", "to": "Grp C"}])
    dl = B.describe(pl)
    ok("3c. the plan's summary names the border clubs", "border clubs of Grp A" in dl and "A club 7 -> Grp B" in dl)
    rec = B.recipe_from_plan(pl, base)
    ok("3c. the recipe given back keeps zone_border",
       next(L for L in rec["leagues"] if L["name"] == "Grp A").get("zone_border") == by["Grp A"]["zone_border"])
    for zb, want in (([{"club": "A club 77", "to": "Grp B"}], "Grp A: zone_border names 'A club 77', not a club of this group"),
                     ([{"club": "A club 7", "to": "Grp Z"}], "Grp A: zone_border sends A club 7 to 'Grp Z', not another group of its division (Grp B, Grp C)"),
                     ([{"club": "A club 7", "to": "Grp A"}], "not another group of its division"),
                     ([{"club": "A club 7"}], "each entry is {\"club\": a club of this group"),
                     ("Grp B", "zone_border is a list")):
        ok("3c. a plan problem in plain words: %s" % want, want in problems(B, zr(zb), base))
    lone = {"world": "_FL26Border2", "leagues": [lg("Solo", above=SERIE_B, exchange=1, club_names=na,
                                                     zone_border=[{"club": "A club 7", "to": "Grp B"}])]}
    ok("3c. zone_border on a league that is not a group is a plan problem",
       "Solo: zone_border is for a group of a division" in problems(B, lone, base))

    # 3b. B404: a set that plays February to December all of it -- two zones under the game's
    # Brazilian second division (163, a calendar-year region), two under a new country's calendar league
    br = {"world": "_FL26Zones", "leagues": [lg("Zona A", 18, country="Brazil", above=163, exchange=1),
                                             lg("Zona B", 18, country="Brazil", above=163, exchange=1)]}
    ok("3b. FL26 refuses a February-December set (new in FL 2027)",
       "a February-December season (that is for FL 2027 only)" in problems(B, br, base))
    B.FL27 = True
    pl = quiet_plan(B, br, base)
    by = {p["name"]: p for p in pl["leagues"]}
    ok("3b. two zones under a February-December league of the game are a set (%s)" % pl["gsets"],
       pl["gsets"] == [{"ups": [(163, 2)], "lows": sorted((by[n]["rid"], 1, 163) for n in by)}]
       and all(p.get("follows_calendar") for p in pl["leagues"]))
    nc = {"world": "_FL26Zones2", "leagues": [lg("Cal Top", 20, country="Mongolia", season="calendar"),
                                              lg("Cal A", 16, country="Mongolia", above="Cal Top", exchange=1),
                                              lg("Cal B", 16, country="Mongolia", above="Cal Top", exchange=1)]}
    pl = quiet_plan(B, nc, base)
    ok("3b. two groups under a new country's February-December league are a set",
       len(pl["gsets"]) == 1 and pl["gsets"][0]["ups"][0][1] == 2)
    B.FL27 = False

    # 4. play-offs
    r = {"world": "_FL26Po", "leagues": [lg("Top", 20), lg("P A", above="Top", exchange=1,
                                                             playoff={"places": [1, 1], "with": ["P B"]}),
                                         lg("P B", above="Top", exchange=0), lg("P C", 24, above="Top", exchange=3,
                                                                                  playoff={"places": [3, 6]}),
                                         lg("Under", 18, above="P C", exchange=2, playoff={"tie": True})]}
    pl = quiet_plan(B, r, base)
    by = {p["name"]: p for p in pl["leagues"]}
    cups = {c["code"]: c for c in pl["home_cups"] if c["kind"] == "promo"}
    a, b, c, u, t = (by[n]["rid"] for n in ("P A", "P B", "P C", "Under", "Top"))
    w = cups.get("FL_%03d_UPO" % a)
    ok("4. group winners: A's 1st v B's 1st, A's place (%s)" % (w and w["entry"]),
       w and w["entry"] == [(a, 1), (b, 1)] and w["promo_hold"] == (a, 1) and w["promo_up"] == t)
    w = cups.get("FL_%03d_UPO" % c)
    ok("4. the EFL's: 3rd v 6th, 4th v 5th, for the 3rd's place (%s)" % (w and w["entry"]),
       w and w["entry"] == [(c, 3), (c, 6), (c, 4), (c, 5)] and w["promo_hold"] == (c, 3))
    w = cups.get("FL_%03d_RPO" % u)
    ok("4. the tie: the C group's 2nd from the bottom v Under's 2nd, no hold (%s)" % (w and w["entry"]),
       w and w["entry"] == [(c, 24 - 2 + 1), (u, 2)] and w["promo_hold"] is None and w["promo_up"] == c)
    ok("4. filled after the last round, played before July", all(
        B.season_ord(x["opts"]["fill"]) > B.season_ord((B.league_days(x["league"], 2 * B.rounds_of(by[n]["clubs"]))
                                                        or [B.PROMO_LAST_DAY])[-1])
        and B.season_ord(x["opts"]["days"][-1]) < 360 and len(x["opts"]["days"]) >= 7
        for x, n in ((cups["FL_%03d_UPO" % c], "P C"), (cups["FL_%03d_RPO" % u], "Under"))))
    ok("4. the recipe given back has the play-offs", sorted(c["code"] for c in quiet_plan(
        B, B.recipe_from_plan(pl, base), base)["home_cups"] if c["kind"] == "promo") == sorted(cups))
    r4 = copy.deepcopy(r)
    r4["leagues"][3]["playoff"] = {"places": [4, 6]}
    ok("4. a play-off that does not hold the exchange-th place", "it must be one of them" in problems(B, r4, base))
    r4["leagues"][3]["playoff"] = {"places": [3, 5]}
    ok("4. a play-off of 3 clubs", "2, 4, 8, 16 or 32" in problems(B, r4, base))
    r4["leagues"][3]["playoff"] = {"places": [3, 6], "with": ["Under"]}
    ok("4. with= a league that is not a group of the division", "not another group" in problems(B, r4, base))
    r4["leagues"][3]["playoff"] = {"places": [3, 6]}
    r4["leagues"][4]["apertura"] = True
    ok("4. a play-off on Apertura/Clausura", "not Apertura/Clausura" in problems(B, r4, base))

    # 5. play-offs of a February-December season (FL 2027, 11.11.2026: Norway's tie, Iceland's
    # and Chile's places): after the leagues' real last weekend, in December, before New Year
    cal = lambda country, **k: {"world": "_FL26PoCal", "leagues": [
        dict(lg("North", 16), country=country, season="calendar"),
        dict(lg("North 2", 16, above="North", exchange=3, **k), country=country)]}
    r = cal("Norway", playoff={"tie": True})
    ok("5. FL26: a play-off in a February-December season is refused", "FL 2027 only" in problems(B, r, base))
    B.FL27 = True
    try:
        import realcal
        pl = quiet_plan(B, r, base)
        by = {p["name"]: p for p in pl["leagues"]}
        w = next(c for c in pl["home_cups"] if c["kind"] == "promo")
        o, last = w["opts"], realcal.day("11-29")                      # Eliteserien's last weekend
        ok("5. the tie: North's 14th v North 2's 3rd (%s)" % (w["entry"],),
           w["entry"] == [(by["North"]["rid"], 14), (by["North 2"]["rid"], 3)] and w["promo_up"] == by["North"]["rid"])
        ok("5. filled four days after the real last weekend, played from the third day on (%s)" % (o,),
           o["fill"] == last + 4 and o["days"][0] >= o["fill"] + 2 and o["days"] == sorted(o["days"]))
        ok("5. seven days three apart, the last before New Year, a day clear of the country's cup",
           len(o["days"]) == 7 and all(b - a >= 3 for a, b in zip(o["days"], o["days"][1:]))
           and o["days"][-1] <= B.CAL_PROMO_END
           and not any(abs(d - x) <= 1 for d in o["days"] for x in B.CALENDAR_CUP_DATE_DAYS))
        ok("5. the recipe given back has the play-off", [c["code"] for c in quiet_plan(
            B, B.recipe_from_plan(pl, base), base)["home_cups"] if c["kind"] == "promo"] == [w["code"]])
        r = cal("Bolivia", playoff={"places": [2, 5]})
        r["leagues"][1]["exchange"] = 2
        pl = quiet_plan(B, r, base)
        w = next(c for c in pl["home_cups"] if c["kind"] == "promo")
        rid = next(p["rid"] for p in pl["leagues"] if p["name"] == "North 2")
        ok("5. places 2 to 5 for the 2nd's place, South America's December (%s)" % (w["opts"],),
           w["entry"] == [(rid, 2), (rid, 5), (rid, 3), (rid, 4)] and w["promo_hold"] == (rid, 2)
           and w["opts"]["fill"] == realcal.day("12-06") + 4 and w["opts"]["days"][-1] <= B.CAL_PROMO_END)
        late = {"first": "02-21", "last": "12-13", "break": None}
        r["leagues"][0]["real_calendar"] = r["leagues"][1]["real_calendar"] = late
        # B450/B446: fl26swiss takes seven days or none; four clubs play the last three of them
        pl = quiet_plan(B, r, base)
        w = next(c for c in pl["home_cups"] if c["kind"] == "promo")
        d, end = w["opts"]["days"], realcal.day("12-13")
        ok("5. a season that ends on 13 December holds four clubs' play-off: seven days, the last three "
           "after the league, three apart (%s)" % (d,),
           len(d) == 7 and d == sorted(d) and len(set(d)) == 7 and d[4] >= w["opts"]["fill"] + 2 > end
           and all(b - a >= 3 for a, b in zip(d[4:], d[5:])) and d[-1] <= B.CAL_PROMO_END)
        r["leagues"][1].update(playoff={"tie": True})
        pl = quiet_plan(B, r, base)
        w = next(c for c in pl["home_cups"] if c["kind"] == "promo")
        d = w["opts"]["days"]
        ok("5. the same season's tie: seven days, its match on the last (%s)" % (d,),
           len(d) == 7 and d == sorted(d) and d[-1] >= w["opts"]["fill"] + 2 and d[-1] <= B.CAL_PROMO_END)
        r["leagues"][1].update(playoff={"places": [2, 17]}, clubs=18)
        ok("5. a play-off of sixteen clubs after 13 December says there are no days",
           "before New Year" in problems(B, r, base))
        r = cal("Norway", playoff={"tie": True})
        r["leagues"][0]["split"] = {"groups": [8, 8]}
        ok("5. under a split of a February-December season: refused", problems(B, r, base) != "")
    finally:
        B.FL27 = False


def build(B, M, base):
    r = {"world": "_FL26Groups", "leagues": [lg("Grp A", above=SERIE_B, exchange=1), lg("Grp B", above=SERIE_B, exchange=1),
                                             lg("Grp C", above=SERIE_B, exchange=2, playoff={"places": [2, 5]})]}
    game = tempfile.mkdtemp(prefix="fl26-groups-")
    try:
        for d in ("livecpk", "modules", "content"):
            os.makedirs(os.path.join(game, "SiderAddons", d))
        with open(os.path.join(game, "SiderAddons", "sider.ini"), "w") as f:
            f.write("[sider]\n")
        with contextlib.redirect_stdout(io.StringIO()):
            pl = B.plan(copy.deepcopy(r), base)
            said = []
            B.build(pl, base, game, False, log=lambda t: said.append(str(t)))
        world = os.path.join(game, "SiderAddons", "livecpk", "_FL26Groups")
        path = os.path.join(world, "fl26world.txt")
        _name, leagues = fl26world.read_world(path)
        gsets, homes, poffs = fl26world.read_groups(path)
        reg = glob.glob(os.path.join(world, "**", "CompetitionRegulation.bin"), recursive=True)
        regs = M.load(os.path.dirname(reg[0]), "CompetitionRegulation.bin")
        rows = {B.u16(regs, i * M.REG + M.R_ID): i * M.REG for i in range(len(regs) // M.REG)}
        desc = B.describe(pl)
    finally:
        shutil.rmtree(game, ignore_errors=True)
    by = {p["name"]: p for p in pl["leagues"]}
    a, b, c = (by[n]["rid"] for n in ("Grp A", "Grp B", "Grp C"))
    first = min(a, b, c)
    line = {L["id"]: L for L in leagues}
    ok("build: every group line has group=0, above=82 and its own promote",
       all(line[x].get("group") == 0 and line[x].get("above") == SERIE_B for x in (a, b, c))
       and (line[a]["promote"], line[b]["promote"], line[c]["promote"]) == (1, 1, 2))
    ok("build: the gset line (%s)" % gsets, gsets == [([(SERIE_B, 4)], sorted([(a, 1, SERIE_B), (b, 1, SERIE_B), (c, 2, SERIE_B)]))])
    ok("build: a ghome line per group with its 20 clubs",
       sorted(homes) == sorted((a, b, c)) and all(homes[x] == by[n]["teams"] for x, n in ((a, "Grp A"), (b, "Grp B"), (c, "Grp C"))))
    ko = (pl.get("cup_ids") or {}).get("ccup:FL_%03d_UPO" % c, {}).get("ko")
    ok("build: the poff line names the play-off's knockout (%s)" % poffs,
       ko and poffs == [(ko, SERIE_B, c, (c, 2), [(c, 2), (c, 5), (c, 3), (c, 4)])])
    R_ABOVE = B.R_ABOVE
    above = {x: B.u16(regs, rows[x] + R_ABOVE) for x in (a, b, c)}
    ok("build: only group %d linked up to Serie B in the tables (%s), Serie B down to it" % (first, above),
       above[first] == SERIE_B and all(above[x] != SERIE_B for x in (a, b, c) if x != first)
       and B.u16(regs, rows[SERIE_B] + M.R_BELOW) == first)
    ok("build: the three on one division", len({M.get_tier(regs[rows[x]:rows[x] + M.REG]) for x in (a, b, c)}) == 1)
    ok("Check the plan names the play-off", "play-off for a place in the league above" in desc)
    ok("Check the plan names the set: 4 down, 1 + 1 + 2 up",
       any(l.startswith("  groups of one division:") and "-- 4 down, 1 + 1 + 2 up" in l for l in desc.splitlines()))


def main():
    offline()
    if len(sys.argv) < 2:
        print("skip - the plans and the build (give the folder with the game's tables)")
        print("all passed (%d)" % N)
        return
    import leaguebuilder as B
    import mkleague as M
    t = sys.argv[1]
    deep = os.path.join(t, "common", "etc", "pesdb")
    base = B.base_dir(deep if os.path.isdir(deep) else t)
    plans(B, base)
    build(B, M, base)
    print("all passed (%d)" % N)


if __name__ == "__main__":
    main()
