r"""python tools/test_recipe_shirts.py [<pesdb>]

Megapack (mato 06.11.): a pack names every player's club number. A number the recipe (or a
NewLife-format release's "shirt" column) gives is the player's own in the squad
(lbplayers.unique_shirts): anybody else who wore it -- a prototype stand-in, a player of the game
the recipe does not name -- takes a free one of his line's numbers, a keeper's only for a keeper,
and a number given twice stays with the first. A club with no number in the recipe is numbered as
before (position_shirts for a new club, the game's own numbers for a game club). A national
team's numbers are its own: a club number never reaches the call-up. Contracts and loans are not
in the game's tables (docs/research/player-record.md), so nothing here writes them.

Pure checks, then apply() on tables made here, then one Build of a world in a temporary game
folder (never the game's own) from the game's tables (<pesdb>, default %APPDATA%\FL26ModStudio\
tables\common\etc\pesdb).
"""
import collections, os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "modstudio"))
import lbplayers as L
import leaguebuilder as B
import mkworld as W
import pesdb
import playeredit as E

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


# ---- given_shirt, unique_shirts (pure) ----
ok("given_shirt reads 1-99", [L.given_shirt({"shirt": v}) for v in ("7", " 99 ", "1")] == [7, 99, 1])
ok("given_shirt: nothing, 0, 100 and words are none",
   all(L.given_shirt(c) is None for c in ({}, {"shirt": ""}, {"shirt": "0"}, {"shirt": "100"}, {"shirt": "ten"}, None)))

sq = [("a", 1, "GK"), ("b", 9, "CF"), ("c", 9, "CB"), ("d", 4, "CB"), ("e", 1, "CMF")]
got = L.unique_shirts(sq, {"c", "e"})
ok("the given numbers stay with their players", "c" not in got and "e" not in got)
ok("who else wore one takes another (%s)" % got, set(got) == {"a", "b"})
ok("a keeper takes a keeper's number", got["a"] in E.KEEPER_SHIRTS and got["a"] != 1)
ok("an outfielder one of his line's, never a keeper's", got["b"] in L.LINE_SHIRTS["FWD"] and got["b"] not in E.KEEPER_SHIRTS)
nums = {k: got.get(k, s) for k, s, _p in sq}
ok("no number twice", len(set(nums.values())) == len(sq))
ok("nothing given, nothing clashing: nobody moves", L.unique_shirts([("a", 1, "GK"), ("b", 2, "CB")], {"a"}) == {})
twice = L.unique_shirts([("a", 10, "AMF"), ("b", 10, "CF"), ("c", 11, "LWF")], {"a", "b"})
ok("a number given twice stays with the first", list(twice) == ["b"] and twice["b"] not in (10, 11))
full = [("p%d" % n, n, "CMF") for n in range(1, 100)] + [("x", 5, "CMF")]
ok("a squad that wears every number still gets one", L.unique_shirts(full[:98] + [("x", 5, "CMF")], {"x"})["p5"] == 99)

# ---- the NewLife format's "shirt" column ----
import newlife as NL
row = {"name": "A B", "Registered Position": "CF", "Speed": "80", "shirt": "17", "contract_end": "2028-06-30",
       "loan_from": "nl:1", "loan_end": "2027-06-30"}
ch = NL.release_fields(row)
ok("a release's shirt column is read", ch.get("shirt") == "17")
ok("contract and loan columns are not (the tables have no place for them)",
   not set(ch) & {"contract_end", "loan_from", "loan_end"})
ok("a release without the column reads as before", "shirt" not in NL.release_fields({"name": "A", "Speed": "80"}))
ok("an empty or bad number is left out", all("shirt" not in NL.release_fields({"shirt": v}) for v in ("", "0", "x")))
ok("check() takes the recipe's shirt as before",
   not L.check({"leagues": [{"name": "Liga S", "clubs": 2}], "players": {"Liga S/0": {"edits": {"0": {"shirt": "17"}}}}}))


# ---- apply on tables made here ----
def write(d, name, raw):
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name), "wb") as f:
        f.write(pesdb.wesys_pack(bytes(raw)))


def player(pid, name, pos):
    r = bytearray(L.P_REC)
    r[L.P_ID:L.P_ID + 4] = pid.to_bytes(4, "little")
    r[E.P_NAME:E.P_NAME + 4 * E.P_NAME_LEN] = E.name_slots(name)
    E.setf(r, "Registered Position", E.POSITIONS.index(pos))
    E.setf(r, "Age", 25)
    return r


def tables(base, squads, national=()):
    """squads {tid: [(pid, pos, shirt)]}; national: team ids marked national in Team.bin"""
    team = bytearray()
    for tid in squads:
        t = bytearray(W.T_REC)
        t[W.T_ID:W.T_ID + 4] = tid.to_bytes(4, "little")
        if tid in national:
            t[L.T_NATIONAL] |= 0x80
        team += t
    players, assigns, seen, eid = bytearray(), bytearray(), set(), 1
    for tid, rows in squads.items():
        for order, (pid, pos, shirt) in enumerate(rows):
            if pid not in seen:
                players += player(pid, "Player%d" % pid, pos)
                seen.add(pid)
            a = bytearray(L.A_REC)
            for off, v in ((E.A_EID, eid), (E.A_PID, pid), (E.A_TID, tid),
                           (E.A_PACK, E.with_shirt(order << E.ORDER_SHIFT, shirt))):
                a[off:off + 4] = v.to_bytes(4, "little")
            assigns += a
            eid += 1
    recs = sorted((players[o:o + L.P_REC] for o in range(0, len(players), L.P_REC)), key=lambda r: L.u32(r, L.P_ID))
    write(base, "Team.bin", team)
    write(base, "Player.bin", b"".join(recs))
    write(base, "PlayerAssignment.bin", assigns)


def numbers(db, tid):
    sq = L.Squads(db)
    return {pid: shirt for _o, pid, shirt, _a in sq.by_club[tid]}


tmp = tempfile.mkdtemp(prefix="fl26-rshirts-")
try:
    base, db = os.path.join(tmp, "base"), os.path.join(tmp, "db")
    os.makedirs(db)
    clone = [(3000 + n, pos, n + 1) for n, pos in enumerate(["GK", "CB", "CB", "RB", "LB", "DMF", "CMF", "AMF", "RWF", "LWF", "CF", "GK"])]
    game = [(100 + n, pos, s) for n, (pos, s) in enumerate([("GK", 1), ("CB", 4), ("CB", 5), ("CMF", 8), ("CF", 9), ("AMF", 10)])]
    nat = [(103, "CMF", 8), (104, "CF", 21)]                # two of the game club's players called up
    tables(base, {300: clone, 50: game, 7: nat}, national={7})
    pl = {"leagues": [{"name": "Liga S", "teams": [300], "club_names": ["Shirts"]}],
          "players": {"Liga S/0": {"edits": {"0": {"shirt": "22"}, "10": {"shirt": "1"}, "4": {"shirt": "9"}}},
                      "50": {"edits": {"103": {"shirt": "9"}, "104": {"Speed": "80"}}}}}
    said = []
    L.apply(pl, base, db, 10 ** 6, log=said.append)
    new = numbers(db, 300)
    ok("the new club's given numbers (%s)" % new, (new[3000], new[3010], new[3004]) == (22, 1, 9))
    ok("the new club: no number twice", len(set(new.values())) == len(new))
    ok("the stand-ins who wore 1 and 9 moved, the others kept theirs",
       new[3008] != 9 and all(new[3000 + n] == n + 1 for n in (1, 2, 3, 5, 6, 7, 9, 11) if n + 1 not in (22, 1, 9)))
    g = numbers(db, 50)
    ok("the game club's player takes the given 9 (%s)" % g, g[103] == 9)
    ok("the one who wore it takes a forward's free number", g[104] != 9 and g[104] in L.LINE_SHIRTS["FWD"])
    ok("the rest of the game club as it was", all(g[p] == s for p, _pos, s in game if p not in (103, 104)))
    ok("the national team's numbers are its own", numbers(db, 7) == {103: 8, 104: 21})
    ok("the log says who was renumbered", any("took a free number" in str(x) for x in said))

    # a recipe without a number: as before (position_shirts; the game's numbers stay)
    db2 = os.path.join(tmp, "db2")
    os.makedirs(db2)
    pl2 = {"leagues": [{"name": "Liga S", "teams": [300], "club_names": ["Shirts"]}],
           "players": {"Liga S/0": {"edits": {"0": {"name": "Ivan Primjer"}}}, "50": {"edits": {"103": {"Speed": "80"}}}}}
    said = []
    L.apply(pl2, base, db2, 10 ** 6, log=said.append)
    pos_of = {pid: pos for pid, pos, _s in clone}
    want = L.position_shirts([(pid, order, pos_of[pid]) for order, pid, _s, _a in L.Squads(db2).by_club[300]])
    ok("no number given: numbered by position, as before", numbers(db2, 300) == want)
    ok("no number given: the game club keeps the game's", numbers(db2, 50) == {p: s for p, _pos, s in game})
    ok("no number given: nobody renumbered", not any("took a free number" in str(x) for x in said))
finally:
    shutil.rmtree(tmp, ignore_errors=True)


# ---- one Build in a temporary game folder ----
pes = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ.get("APPDATA", ""), "FL26ModStudio", "tables",
                                                          "common", "etc", "pesdb")
if not os.path.exists(os.path.join(pes, "Player.bin")):
    print("test_recipe_shirts: %d ok (no game tables at %s: the Build part skipped)" % (N, pes))
    sys.exit(0)
gsq = L.Squads(pes)
kinds = L.teams(pes)
# a club of the game with a player called up by a national team
club = next(t for t, v in sorted(gsq.by_club.items()) if not kinds.get(t, (True, 0))[0] and len(v) >= 20
            and all(p in gsq.index for _o, p, _s, _x in v)
            and any(kinds.get(x, (False, 0))[0] for _o, p, _s, _x in v for x in gsq.clubs_of[p]))
csq = {pid: shirt for _o, pid, shirt, _x in gsq.by_club[club]}
called = next(p for p in csq if any(kinds.get(x, (False, 0))[0] for x in gsq.clubs_of[p]))
nteam = next(x for x in gsq.clubs_of[called] if kinds.get(x, (False, 0))[0])
nshirt = next(s for _o, p, s, _x in gsq.by_club[nteam] if p == called)
other = next(p for p in csq if p != called and csq[p] != csq[called])
WORLD = "_FL26RecipeShirts"
gamedir = tempfile.mkdtemp(prefix="fl26-rshirts-game-")
try:
    for d in ("livecpk", "modules", "content"):
        os.makedirs(os.path.join(gamedir, "SiderAddons", d))
    with open(os.path.join(gamedir, "SiderAddons", "sider.ini"), "w") as f:
        f.write("[sider]" + chr(10))
    every = {str(n): {"shirt": str(99 - n)} for n in range(L.SQUAD)}            # 99, 98 ... every place
    recipe = {"world": WORLD,
              "players": {"Shirts Albania/0": {"edits": every},
                          "Shirts Albania/1": {"edits": {"3": {"shirt": "1"}, "5": {"shirt": "9"}}},
                          str(club): {"edits": {str(called): {"shirt": str(csq[other])}}}},
              "leagues": [{"name": "Shirts Albania", "country": "Albania", "clubs": 10, "legs": 2}]}
    said = []
    pl = B.plan(recipe, pes)
    B.build(pl, pes, gamedir, False, log=said.append)
    db = os.path.join(gamedir, "SiderAddons", "livecpk", WORLD, "common", "etc", "pesdb")
    ids = B.last_build_ids(gamedir, WORLD).get("clubs") or {}
    a = pl["leagues"][0]["teams"]
    built = L.Squads(db)
    shirt = lambda t: {pid: s for _o, pid, s, _x in built.by_club[t]}
    s0, i0 = shirt(a[0]), ids.get("Shirts Albania/0") or {}
    ok("build: the ids file keys the first club's players by place", len(i0) >= 18)
    ok("build: every place of the first club wears the recipe's number",
       all(s0[pid] == 99 - int(k) for k, pid in i0.items()))
    s1, i1 = shirt(a[1]), ids.get("Shirts Albania/1") or {}
    ok("build: the second club's two given numbers", s1[i1["3"]] == 1 and s1[i1["5"]] == 9)
    ok("build: the second club wears no number twice", len(set(s1.values())) == len(s1))
    ok("build: the clubs without numbers are numbered by position, no number twice",
       all(len(set(shirt(t).values())) == len(shirt(t)) for t in a[2:]))
    ok("build: ... and keep a keeper on the 1",
       all(any(s == 1 and E.getf(built.players[built.index[p]:built.index[p] + L.P_REC], "Registered Position") == 0
               for p, s in shirt(t).items()) for t in a[2:]))
    g = shirt(club)
    ok("build: the game club's player wears the given number", g[called] == csq[other])
    ok("build: his teammate who wore it another, nobody twice", g[other] != csq[other] and len(set(g.values())) == len(g))
    ok("build: the rest of the game club as the game has it",
       all(g[p] == s for p, s in csq.items() if p not in (called, other) and p in g))
    ok("build: his national team number stays", shirt(nteam)[called] == nshirt)
finally:
    shutil.rmtree(gamedir, ignore_errors=True)
print("test_recipe_shirts: %d ok" % N)
