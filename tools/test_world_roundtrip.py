r"""python test_world_roundtrip.py <folder with the game's tables> [--exe <FL_2026.exe>] [--keep]

A built world read back into a recipe (leaguebuilder.recipe_from_plan) and built again over a copy
of its folder -- what "make a copy for editing" does with a ready world from a zip, the FL26
Modpack -- is the same world, ids and all (0.2.4). A Master League career, Kit Server's map.txt and
the scoreboard and menu maps hold those ids: competition id (cid, one byte), regulation id (rid),
region, Select Team slot, the clubs' team ids (by League/place), the NewLife clubs' (newlife_ids),
the players' ids (fl26playerids.json), the cups'.

 1. plan level, every recipe of testdata\ and the ones here: plan(recipe_from_plan(plan)) is the
    plan again, also for a plan written before plan() kept the recipe's settings (the Modpack r6);
    the keys Build never reads (uefa_rank, league_order, NewLife's version and key) come back too
 2. every country of Country.bin comes back as the same flag id: the region pin wants it
 3. a world built, its folder copied under a new name and built again from recipe_from_plan: every
    league's cid, rid, slot, region and tier, every club's team id per League/place, the NewLife
    ids, the player ids, the cups' ids, every table byte for byte, fl26world.txt but for its world
    line; the kit and scoreboard map lines (lbservers.write, Switch on) give the same clubs and
    leagues the same folders
 4. the copy with one league taken out: every other league, club and player keeps its ids, and
    the league's map lines go -- a line the world carries from another pack (a modpack's
    scoreboard, <world>\_packs) too, so a league added later on that free id does not get it

The worlds are built offline into a temporary game folder (nothing of the real game is touched).
--exe gives FL_2026.exe for the cup dates (FL26_EXE); without it both builds date them the same
way and still compare. --keep leaves the temporary folder.
"""
import copy, filecmp, glob, json, os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

N = 0
NOTES = []


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def norm(x):
    """x as it comes back from leaguebuilder-plan.json (tuples as lists, int keys as text)"""
    return json.loads(json.dumps(x))


def diff(a, b, path="", out=None):
    """where a and b differ, as lines (the first 20)"""
    out = [] if out is None else out
    if len(out) >= 20:
        return out
    if type(a) != type(b):
        out.append("%s: %r | %r" % (path, str(a)[:60], str(b)[:60]))
    elif isinstance(a, dict):
        for k in sorted(set(a) | set(b), key=str):
            if k not in a or k not in b:
                out.append("%s/%s: only in the %s" % (path, k, "first" if k in a else "second"))
            else:
                diff(a[k], b[k], "%s/%s" % (path, k), out)
    elif isinstance(a, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            diff(x, y, "%s[%d]" % (path, i), out)
    elif a != b:
        out.append("%s: %r | %r" % (path, str(a)[:60], str(b)[:60]))
    return out


def game_tops(B, base):
    """(a top division of the game with no division below it, an English one, the Saudi one)"""
    M = B.M
    regs = M.load(base, "CompetitionRegulation.bin")
    regrow = {B.u16(regs[i * M.REG:], M.R_ID): regs[i * M.REG:(i + 1) * M.REG] for i in range(len(regs) // M.REG)}
    tops = [r for r, _c, _n, _t in B.game_leagues(base) if r in regrow and M.get_tier(regrow[r]) == 1
            and regrow[r][M.R_TYPE] == 4]
    alone = next(r for r in tops if B.u16(regrow[r], M.R_BELOW) not in regrow and r not in B.CALENDAR_REGIONS
                 and r != B.SHARED_SLOT_REG)
    return alone, 17 if 17 in tops else tops[0], B.fl26world._SPL


def synthetic(B, base):
    """recipes for what testdata\\ does not have: Apertura/Clausura, an exhibition league, a
    February-December season, real calendars, a cup of the top division only, the game's leagues'
    European places and cups, pre-season cups, the keys only Mod Studio reads"""
    alone, eng, spl = game_tops(B, base)
    egypt = {"name": "RT Egypt", "country": "Egypt", "clubs": 12, "legs": 2, "cup": True, "cup_name": "RT Egypt Cup",
             "supercup": True, "europe": [[1, 6], [2, 6], [3, 7], [4, 7], [5, 6], [6, 7], [7, 6], [8, 7]],
             "newlife": {"clubs": [], "version": "9.9", "key": ["EGY", 1]}}
    return [
        ("apertura and exhibition", {"world": "_FL26RtSyn1", "leagues": [
            {"name": "RT Peru", "country": "Peru", "clubs": 14, "legs": 2, "apertura": {"playoff": 4},
             "playoff_logo": "x:/nowhere/playoff.png", "real_calendar": False},
            {"name": "RT Legends", "country": "Andorra", "clubs": 10, "legs": 1, "exhibition": True},
            {"name": "RT Japan 3", "country": "Iceland", "clubs": 10, "legs": 2, "season": "calendar",
             "real_calendar": {"first": "03-01", "last": "11-20", "break": None, "days": "sat sun"}},
            {"name": "RT Under", "country": "Iceland", "clubs": 12, "legs": 2, "above": alone, "cup_top_only": True}]}),
        ("game leagues' places, cups and the settings", {"world": "_FL26RtSyn2", "leagues": [
            egypt, {"name": "RT Egypt 2", "country": "Egypt", "clubs": 14, "legs": 2, "above": "RT Egypt"},
            {"name": "RT Armenia", "country": "Armenia", "clubs": 10, "legs": 3, "league_cup": True,
             "league_cup_name": "RT Armenia LC", "europe": [[1, 0], [2, 1], [0, 2]], "cup": True}],
            "game_europe": {str(eng): [[1, 0], [2, 0], [3, 1], [0, 2]], str(spl): [[5, 8], [6, 8]]},
            "uefa_seed": [["RT Armenia", 2, 1], ["g%d" % eng, 3, 1]],
            "uefa_rank": ["g%d" % eng, "RT Armenia"], "league_order": ["RT Armenia", "RT Egypt", "RT Egypt 2"],
            "preseason_cups": [{"name": "RT Summer", "clubs": ["RT Egypt/0", "RT Egypt/1", "RT Armenia/0", "RT Armenia/1"],
                                "logo": "x:/nowhere/summer.png"}],
            "europe_first": {"uel": ["RT Armenia/3"], "uecl": ["RT Egypt/4"]},
            "ccup_names": {"6": "RT African League"}, "ccup_logos": {"7": "x:/nowhere/cafcc.png"},
            "caf_super_cup": False, "cup_draw": "random", "country_order": "az",
            "game_cups": [{"league": B.fl26world._BRA, "league_cup": False, "super_cup": True, "super_name": "RT Brazil Super"},
                          {"league": eng, "league_cup": True, "super_cup": False, "name": "RT English LC"}]})]


def plan_level(B, base):
    recipes = [(os.path.basename(f), B.load_recipe(f)) for f in sorted(glob.glob(os.path.join(HERE, "testdata", "*", "*.json")))]
    recipes += synthetic(B, base)
    for name, r in recipes:
        first = norm(B.plan(r, base))
        for old in (False, True):
            pl = norm(first)
            if old:          # a plan from before plan() kept the settings (the Modpack r6)
                pl.pop("settings")
                for p in pl["leagues"] + pl["others"]:
                    p["newlife"] = {"clubs": p["newlife"]["clubs"]}
                    p.pop("cup_top_only", None)
            back = B.recipe_from_plan(pl, base)
            again = norm(B.plan(back, base))
            a, b = dict(first), dict(again)
            if old:
                a.pop("settings"), b.pop("settings")
                for p in a["leagues"] + a["others"]:
                    p["newlife"] = {"clubs": p["newlife"]["clubs"]}
            ok("%s%s: recipe_from_plan builds the same plan%s" % (name, " (an older plan)" if old else "",
               "" if a == b else ": " + "; ".join(diff(a, b))), a == b)
    syn = dict(recipes)["game leagues' places, cups and the settings"]
    back = B.recipe_from_plan(norm(B.plan(syn, base)), base)
    ok("the keys only Mod Studio reads come back (uefa_rank, league_order, NewLife's version and key)",
       back.get("uefa_rank") == syn["uefa_rank"] and back.get("league_order") == syn["league_order"]
       and back["leagues"][0]["newlife"].get("version") == "9.9" and back["leagues"][0]["newlife"].get("key") == ["EGY", 1])


def countries(B, base):
    import mkflags
    cty = mkflags.countries(mkflags.table("Country", [base]))
    bad = []
    for fid in cty:
        pl = {"world": "_x", "leagues": [{"name": "C", "country": fid, "clubs": 10, "rid": 1, "cid": 1}]}
        name = B.recipe_from_plan(pl, base)["leagues"][0]["country"]
        if mkflags.by_name(cty, name) != fid:
            bad.append((fid, name))
    ok("every country (%d) comes back as its own flag id%s" % (len(cty), ": %r" % bad if bad else ""), not bad)


# ---- worlds built --------------------------------------------------------------------------------

def free_game_clubs(B, base, n):
    """n clubs of the game usable in a league: n//2 that play nowhere, the rest playing in a league
    (they need a club to take their places)"""
    info = B.game_info(base)
    usable = [t for t in sorted(info["clubs"]) if not B.game_club_problem(info, t)]
    idle = [t for t in usable if not info["entries"].get(t)]
    busy = [t for t in usable if set(info["entries"].get(t) or []) & info["league_cids"]
            and not set(info["entries"].get(t) or []) & B.CONTINENTAL_CIDS]
    return idle[:n // 2], busy[:n - n // 2]


def scenario(B, base, src):
    """the recipe of world A: two countries with a division below, a national cup and super cup,
    clubs of the game (one taking a place, one with a new club in its), a club id of the recipe's
    own, NewLife clubs, clubs in no league, player changes, Kit Server and scoreboard folders"""
    idle, busy = free_game_clubs(B, base, 4)
    raw = B.pesdb.wesys_unpack(open(os.path.join(base, "Team.bin"), "rb").read())
    top = max(int.from_bytes(raw[o + B.W.T_ID:o + B.W.T_ID + 4], "little") for o in range(0, len(raw), B.W.T_REC))
    kit = []
    for k in range(3):
        d = os.path.join(src, "kits", "club%d" % k, "p1")
        os.makedirs(d)
        open(os.path.join(d, "u0%d.txt" % k), "w").write("kit %d" % k)
        kit.append(os.path.dirname(d))
    board = os.path.join(src, "boards", "Albania")
    os.makedirs(board)
    open(os.path.join(board, "board.txt"), "w").write("board")
    nl = list(range(B.NEWLIFE_TEAMS[0] + 7, B.NEWLIFE_TEAMS[0] + 7 + 10))
    return {"world": "_FL26RtA", "make_kits": False, "replaced_kits": False, "leagues": [
        {"name": "RT Albania", "country": "Albania", "clubs": 12, "legs": 2, "cup": True, "cup_name": "RT Cup",
         "supercup": True, "supercup_name": "RT Super", "europe": [[1, 0], [2, 1]],
         "club_names": ["Tirana RT", "Vllaznia RT", "", "Partizani RT"],
         "kit_folders": [kit[0], "", "", kit[1]], "scoreboard": board,
         "game_clubs": [{"at": 5, "id": idle[0]}, {"at": 7, "id": busy[0], "swap": {"name": "RT Takes Its Place"}}]},
        {"name": "RT Albania 2", "country": "Albania", "clubs": 10, "legs": 2, "above": "RT Albania",
         "club_ids": ["", "", str(top + 400)]},
        {"name": "RT Bosnia", "country": "Bosnia and Herzegovina", "clubs": 10, "legs": 2,
         "game_clubs": [{"at": 1, "id": busy[1], "swap": {"name": "RT Second Swap"}}],
         "kit_folders": ["", "", kit[2]]},
        {"name": "RT NewLife", "country": "Armenia", "clubs": 12, "legs": 2,
         "newlife": {"clubs": nl + [0, 0], "version": "9.9", "key": ["ARM", 1]},
         "club_names": ["NL %d" % k for k in range(12)]},
        {"name": "RT Andorra", "country": "Andorra", "clubs": 10, "legs": 2, "cup": True},
        {"name": "RT Others", "country": "Andorra", "clubs": 3, "others": "europe",
         "club_names": ["Lone One", "Lone Two", "Lone Three"]}],
        "players": {"RT Albania/0": {"edits": {"0": {"name": "Ivo Kruzni"}, "3": {"name": "Ante Put"}}},
                    "RT Bosnia/4": {"edits": {"1": {"name": "Edin Natrag"}}, "remove": ["5"]},
                    "RT NewLife/2": {"edits": {"0": {"name": "Aram Novi"}}},
                    "RT Andorra/9": {"edits": {"2": {"name": "Pere Ultim"}}}}}


def sider(game):
    return os.path.join(game, "SiderAddons")


def world_dir(game, world):
    return os.path.join(sider(game), "livecpk", world)


def read_plan(game, world):
    with open(os.path.join(world_dir(game, world), "leaguebuilder-plan.json"), encoding="utf-8") as f:
        return json.load(f)


def build(B, base, game, recipe, log):
    """recipe built over the plan its world folder already has (the builder page's way)"""
    prev = None
    if os.path.exists(os.path.join(world_dir(game, recipe["world"]), "leaguebuilder-plan.json")):
        prev = read_plan(game, recipe["world"])
    B.build(B.plan(recipe, base, prev), base, game, prev is not None, log=log)
    return read_plan(game, recipe["world"])


def copy_world(game, a, b):
    """world a's folder as world b's: what Make a copy for editing will do"""
    shutil.copytree(world_dir(game, a), world_dir(game, b))


def ids(pl):
    """{league: its ids} and {League/place: team id} of a built plan"""
    leagues = {p["name"]: {k: p.get(k) for k in ("cid", "rid", "slot", "region", "tier", "above", "country")}
               for p in pl["leagues"]}
    clubs = {"%s/%d" % (p["name"], k): t for p in pl["leagues"] + pl["others"] for k, t in enumerate(p.get("teams") or [])}
    swaps = {"%s/%s" % (p["name"], at): g.get("swap_id") for p in pl["leagues"] for at, g in (p.get("game_clubs") or {}).items()}
    return leagues, clubs, swaps


def tables(game, world):
    d = os.path.join(world_dir(game, world), "common", "etc", "pesdb")
    return {f: open(os.path.join(d, f), "rb").read() for f in sorted(os.listdir(d))}


def world_lines(game, world):
    with open(os.path.join(world_dir(game, world), "fl26world.txt"), encoding="utf-8") as f:
        return [l.rstrip("\n") for l in f if not l.startswith("world ")]


def player_ids(game, world):
    with open(os.path.join(world_dir(game, world), "fl26playerids.json"), encoding="utf-8") as f:
        return json.load(f)


def team_records(B, game, world):
    raw = B.pesdb.wesys_unpack(tables(game, world)["Team.bin"])
    return {int.from_bytes(raw[o + B.W.T_ID:o + B.W.T_ID + 4], "little"): raw[o:o + B.W.T_REC]
            for o in range(0, len(raw), B.W.T_REC)}


def player_records(game, world):
    import lbplayers as L
    import pesdb
    raw = pesdb.wesys_unpack(tables(game, world)["Player.bin"])
    return {L.u32(raw, o + L.P_ID): raw[o:o + L.P_REC] for o in range(0, len(raw), L.P_REC)}


def map_lines(game):
    """{"kits": {team id: folder}, "boards": {competition id: folder}} of the lines in effect"""
    import lbservers
    out = {}
    for key, rel in (("kits", os.path.join("content", "kit-server", "map.txt")),
                     ("boards", os.path.join("content", "scoreboard-server", "map_competitions.txt"))):
        out[key] = lbservers._read_map(os.path.join(sider(game), rel))
    return out


def carry(game, world, kit_tid, board_ids):
    """lines Install mods puts in from a world zip: a kit and scoreboards of another pack the world
    carries (<world>\\_kits, <world>\\_packs)"""
    with open(os.path.join(sider(game), "content", "kit-server", "map.txt"), "a", encoding="utf-8") as f:
        f.write('%d, "%s\\_kits\\Lent Kit"   # FL26 Mod Studio: kit of Lent Kit\n' % (kit_tid, world))
    with open(os.path.join(sider(game), "content", "scoreboard-server", "map_competitions.txt"), "a", encoding="utf-8") as f:
        for c in board_ids:
            f.write("%d, %s\\_packs\\Board %d   # FL26 Mod Studio: scoreboard of Board %d\n" % (c, world, c, c))


def switch_on(game, world, log):
    import lbservers
    lbservers.write(read_plan(game, world), sider(game), log, world_dir(game, world))


def same_world(B, game, a, b, label):
    pa, pb = read_plan(game, a), read_plan(game, b)
    la, ca, sa = ids(pa)
    lb_, cb, sb = ids(pb)
    ok("%s: every league keeps cid, rid, slot, region, tier, above, country%s"
       % (label, "" if la == lb_ else ": " + "; ".join(diff(la, lb_))), la == lb_)
    ok("%s: every club keeps its team id (%d clubs, League/place)%s"
       % (label, len(ca), "" if ca == cb else ": " + "; ".join(diff(ca, cb))), ca == cb)
    ok("%s: the clubs taking a game club's places keep theirs%s" % (label, "" if sa == sb else ": %r %r" % (sa, sb)),
       sa == sb)
    nla = pa["leagues"][0].get("newlife_tid")
    ok("%s: the NewLife clubs keep their world ids (%d)" % (label, len(nla or {})), nla and nla == pb["leagues"][0].get("newlife_tid"))
    ok("%s: the cups keep their ids%s" % (label, "" if pa.get("cup_ids") == pb.get("cup_ids") else ": " + "; ".join(
        diff(pa.get("cup_ids"), pb.get("cup_ids")))), pa.get("cup_ids") == pb.get("cup_ids"))
    ok("%s: free ids left the same (%d)" % (label, pa["free_ids"]), pa["free_ids"] == pb["free_ids"])
    ia, ib = player_ids(game, a), player_ids(game, b)
    ok("%s: every player keeps his id (fl26playerids.json, %d clubs)" % (label, len(ia["clubs"])),
       ia["clubs"] == ib["clubs"] and ia["names"] == ib["names"])
    ta, tb = tables(game, a), tables(game, b)
    bad = [f for f in ta if ta[f] != tb.get(f)]
    ok("%s: every table the same, byte for byte (%s)%s" % (label, ", ".join(ta), ": not " + ", ".join(bad) if bad else ""),
       sorted(ta) == sorted(tb) and not bad)
    wa, wb = world_lines(game, a), world_lines(game, b)
    ok("%s: fl26world.txt the same but for its world line (%d lines)" % (label, len(wa)), wa == wb)
    # leaguebuilder-input.json: the record of what Build was given (incremental Build), the world's name in it
    keep = ("leaguebuilder-plan.json", "fl26world.txt", "fl26playerids.json", "leaguebuilder-files.txt",
            "leaguebuilder-input.json")
    fa = {os.path.relpath(os.path.join(d, f), world_dir(game, a)) for d, _s, fs in os.walk(world_dir(game, a)) for f in fs}
    fb = {os.path.relpath(os.path.join(d, f), world_dir(game, b)) for d, _s, fs in os.walk(world_dir(game, b)) for f in fs}
    same = all(filecmp.cmp(os.path.join(world_dir(game, a), f), os.path.join(world_dir(game, b), f), shallow=False)
               for f in fa & fb if os.path.basename(f) not in keep)
    ok("%s: the other files of the world folder the same (%d: crests, logos, modules)" % (label, len(fa)), fa == fb and same)
    pa2, pb2 = norm(pa), norm(pb)
    for p in (pa2, pb2):
        p.pop("world")
    # recipe_from_plan pins every NewLife club to the id it was built with (newlife_ids): the copy's
    # recipe has them where the first had none -- the same ids, as the plan's newlife_tid
    pins = (pb2.get("settings") or {}).pop("newlife_ids", None)
    first = (pa2.get("settings") or {}).pop("newlife_ids", None) or {}
    ok("%s: the copy's recipe pins the NewLife clubs to the ids they had" % label,
       pins == dict(first, **{str(k): int(v) for k, v in (nla or {}).items()}))
    ok("%s: leaguebuilder-plan.json the same but for the world%s" % (label, "" if pa2 == pb2 else ": " + "; ".join(diff(pa2, pb2))),
       pa2 == pb2)


def built(B, base, game, log):
    src = os.path.join(game, "src")
    for d in ("livecpk", "modules", os.path.join("content", "kit-server"), os.path.join("content", "scoreboard-server")):
        os.makedirs(os.path.join(sider(game), d))
    with open(os.path.join(sider(game), "sider.ini"), "w") as f:
        f.write("[sider]\n")
    for rel in (os.path.join("content", "kit-server", "map.txt"), os.path.join("content", "scoreboard-server", "map_competitions.txt")):
        with open(os.path.join(sider(game), rel), "w", encoding="utf-8") as f:
            f.write("# a line of your own\n1, \"Somebody\\Else\"\n")
    ra = scenario(B, base, src)
    pa = build(B, base, game, ra, log)
    switch_on(game, "_FL26RtA", log)
    lines_a = map_lines(game)
    la, ca, _sa = ids(pa)
    want_kits = {ca["RT Albania/0"], ca["RT Albania/3"], ca["RT Bosnia/2"]}
    ok("world A: a kit line for each club with a Kit Server folder, by its team id",
       want_kits <= set(lines_a["kits"]) and lines_a["kits"][ca["RT Albania/0"]].endswith("RT Albania\\Tirana RT"))
    ok("world A: the scoreboard line by the league's regulation id",
       lines_a["boards"].get(la["RT Albania"]["rid"], "").endswith("RT Albania"))
    # the zip of world A carried a kit and scoreboards of another pack (a modpack's)
    carry(game, "_FL26RtA", ca["RT Bosnia/3"], [la["RT Bosnia"]["rid"], la["RT Bosnia"]["cid"], la["RT Andorra"]["rid"]])
    switch_on(game, "_FL26RtA", log)
    got = map_lines(game)
    ok("world A switched on again: the lines it carries from another pack stay",
       got["kits"].get(ca["RT Bosnia/3"]) == "_FL26RtA\\_kits\\Lent Kit"
       and got["boards"].get(la["RT Bosnia"]["rid"]) == "_FL26RtA\\_packs\\Board %d" % la["RT Bosnia"]["rid"])

    # 3. a copy under a new name, built from the recipe read back from A's plan
    copy_world(game, "_FL26RtA", "_FL26RtB")
    rb = B.recipe_from_plan(read_plan(game, "_FL26RtB"), base)
    ok("the recipe read back has the kit and scoreboard folders and the NewLife pins",
       rb["leagues"][0].get("kit_folders") == ra["leagues"][0]["kit_folders"]
       and rb["leagues"][0].get("scoreboard") == ra["leagues"][0]["scoreboard"]
       and len(rb.get("newlife_ids") or {}) == 10)
    rb["world"] = "_FL26RtB"
    build(B, base, game, rb, log)
    same_world(B, game, "_FL26RtA", "_FL26RtB", "copy B")
    switch_on(game, "_FL26RtB", log)
    lines_b = map_lines(game)
    kb = {t: f.split("\\", 1)[1] for t, f in lines_b["kits"].items() if f.startswith("_FL26RtB\\")}
    ka = {t: f.split("\\", 1)[1] for t, f in lines_a["kits"].items() if f.startswith("_FL26RtA\\")}
    ok("copy B switched on: its kit lines give the same clubs (team ids) the same folders", ka == kb and len(kb) == 3)
    bb = {t: f.split("\\", 1)[1] for t, f in lines_b["boards"].items() if f.startswith("_FL26RtB\\")}
    ba = {t: f.split("\\", 1)[1] for t, f in lines_a["boards"].items() if f.startswith("_FL26RtA\\")}
    ok("copy B switched on: its scoreboard line, the same league (regulation id)", ba == bb and len(bb) == 1)
    ok("lines of your own stay", lines_b["kits"].get(1) == "Somebody\\Else" and lines_b["boards"].get(1) == "Somebody\\Else")
    if not any(f.startswith("_FL26RtA\\_") for f in list(lines_b["kits"].values()) + list(lines_b["boards"].values())):
        NOTES.append("switching on another world (here copy B) takes out the lines world A carries from other "
                     "packs (_kits, _packs): carried() knows only the live world's; switched on again, A does "
                     "not get them back (a reinstall does). The copy carries none of its own yet (step 3)")

    # 4. the copy with one league taken out (C), then one added (D)
    copy_world(game, "_FL26RtA", "_FL26RtC")
    rc = B.recipe_from_plan(read_plan(game, "_FL26RtC"), base)
    rc["world"] = "_FL26RtC"
    gone = "RT Bosnia"
    rc["leagues"] = [L for L in rc["leagues"] if L["name"] != gone]
    rc["players"] = {k: v for k, v in rc["players"].items() if not k.startswith(gone + "/")}
    carry(game, "_FL26RtC", ca[gone + "/3"], [la[gone]["rid"], la[gone]["cid"], la["RT Andorra"]["rid"]])
    pc = build(B, base, game, rc, log)
    lc, cc, sc = ids(pc)
    _la, _ca, sa = ids(read_plan(game, "_FL26RtA"))
    ok("one league out: every other league keeps its ids%s" % "".join(
        "; %s %s" % (n, diff(la[n], lc[n])) for n in lc if la[n] != lc[n]), all(la[n] == lc[n] for n in lc))
    moved = {k: (ca[k], t) for k, t in cc.items() if ca.get(k) != t}
    ok("one league out: every other club keeps its team id (%d)%s" % (len(cc), ": moved %r" % moved if moved else ""), not moved)
    smoved = {k: (sa[k], v) for k, v in sc.items() if sa.get(k) != v}
    if smoved:
        NOTES.append("one league out: a new club taking a game club's places got another id: %r" % smoved)
    ia, ic = player_ids(game, "_FL26RtA")["clubs"], player_ids(game, "_FL26RtC")["clubs"]
    pmoved = [k for k in ic if ia.get(k) != ic[k]]
    ok("one league out: every other club's players keep their ids (%d clubs)%s" % (len(ic), ": " + ", ".join(pmoved[:5]) if pmoved else ""),
       not pmoved and not any(k.startswith(gone + "/") for k in ic))
    ra_, rc_ = player_records(game, "_FL26RtA"), player_records(game, "_FL26RtC")
    mine = {pid for keys in ic.values() for pid in keys.values()}
    import playeredit as PE
    span = slice(PE.P_NAME, PE.P_NAME + PE.P_NAME_LEN * PE.P_NAME_SLOTS)

    def placeholder(rec):
        return bytes(rec[PE.P_NAME:PE.P_NAME + 4]) == b"FL P"

    def masked(rec):
        return rec[:span.start] + rec[span.stop:] if rec and placeholder(rec) else rec
    pdiff = [pid for pid in mine if masked(ra_.get(pid)) != masked(rc_.get(pid))]
    renamed = [pid for pid in mine if ra_.get(pid) != rc_.get(pid) and pid not in pdiff]
    ok("one league out: those players' records the same, byte for byte (%d)%s"
       % (len(mine), ": %d differ" % len(pdiff) if pdiff else ""), not pdiff)
    if renamed:
        NOTES.append("one league out: %d placeholder players (no name in the recipe) keep their ids but are "
                     "numbered again (FL P%%05d counts in Build order, mkplayers): e.g. %s -> %s"
                     % (len(renamed), PE.cstr(ra_[renamed[0]][span][:PE.P_NAME_LEN]),
                        PE.cstr(rc_[renamed[0]][span][:PE.P_NAME_LEN])))
    tr_a, tr_c = team_records(B, game, "_FL26RtA"), team_records(B, game, "_FL26RtC")
    kept = set(cc.values())
    tdiff = sorted(t for t in kept if tr_a.get(t) != tr_c.get(t))
    if tdiff:
        alt = [t for t in tdiff if tr_a[t][4:] == tr_c[t][4:]]
        more = [t for t in tdiff if t not in alt]
        offs = sorted({i for t in more for i, (x, y) in enumerate(zip(tr_a[t], tr_c[t])) if x != y and i >= 4})
        names = {t: k for k, t in cc.items()}
        NOTES.append("one league out: Team.bin records of %d kept clubs differ, %d of them only in the first 4 bytes "
                     "(T_ALT, the second id Build counts up in league order)%s" % (len(tdiff), len(alt),
                     "; %d more at bytes %s (%s; 882-884 is the abbreviation, made unique in Build order)" % (len(more), offs[:24], ", ".join(names.get(t, str(t)) for t in more[:10]))
                     if more else ""))
    pa_ = read_plan(game, "_FL26RtA")
    game_at = {int(at) for p in pa_["leagues"] if p["name"] == gone for at in p.get("game_clubs") or {}}
    own = {ca["%s/%d" % (gone, k)] for k in range(next(p["clubs"] for p in pa_["leagues"] if p["name"] == gone))
           if k not in game_at}
    ok("one league out: its own clubs are gone from Team.bin (%d)" % len(own), own and not own & set(tr_c))
    switch_on(game, "_FL26RtC", log)
    got = map_lines(game)
    ok("one league out: the other clubs' kit lines the same", all(got["kits"].get(t, "").replace("_FL26RtC\\", "") ==
                                                                  lines_a["kits"][t].replace("_FL26RtA\\", "")
                                                                  for t in ka if t in kept))
    gone_ids = {la[gone]["rid"], la[gone]["cid"]}
    gone_teams = {ca[k] for k in ca if k.startswith(gone + "/")}
    ok("one league out: no kit line left on its clubs' ids (the carried one too)", not gone_teams & set(got["kits"]))
    ok("one league out: no scoreboard line left on its rid or cid (the carried ones too)", not gone_ids & set(got["boards"]))
    ok("one league out: the carried scoreboard of a league still there stays",
       got["boards"].get(la["RT Andorra"]["rid"]) == "_FL26RtC\\_packs\\Board %d" % la["RT Andorra"]["rid"])
    rd = B.recipe_from_plan(read_plan(game, "_FL26RtC"), base)
    rd["leagues"].append({"name": "RT Latecomer", "country": "Montenegro", "clubs": 10, "legs": 2})
    pd = build(B, base, game, rd, log)
    ld, cd, _sd = ids(pd)
    took = sorted(k for k in ("cid", "rid") if ld["RT Latecomer"][k] == la[gone][k])
    ok("a league added later: the others keep their ids", all(ld[n] == lc[n] for n in lc)
       and all(cd[k] == cc[k] for k in cc))
    switch_on(game, "_FL26RtC", log)
    got = map_lines(game)
    late = {ld["RT Latecomer"]["rid"], ld["RT Latecomer"]["cid"]}
    ok("a league added later on the taken-out league's %s: no line of that league on it" % ("/".join(took) or "-- (other ids)"),
       not any("Board" in got["boards"].get(c, "") for c in late))
    if took:
        NOTES.append("a league added after one was taken out took its free %s; only the Switch on in between "
                     "(Build of the live world does one) took the carried line off it: built twice without a "
                     "Switch on, the new league would get the old one's scoreboard (step 3: keep who held each id)"
                     % "/".join(took))


def main(base, keep=False):
    import leaguebuilder as B
    plan_level(B, base)
    countries(B, base)
    game = tempfile.mkdtemp(prefix="fl26-roundtrip-")
    log_lines = []
    try:
        built(B, base, game, log_lines.append)
    except Exception:
        print("\n".join("# " + l for l in log_lines[-30:]))
        raise
    finally:
        if keep:
            print("# kept %s" % game)
        else:
            shutil.rmtree(game, ignore_errors=True)
    for n in NOTES:
        print("# NOTE: " + n)
    print("1..%d" % N)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0].startswith("-"):
        sys.exit(__doc__)
    if "--exe" in a:
        os.environ["FL26_EXE"] = a[a.index("--exe") + 1]
    main(a[0], "--keep" in a)
