"""python test_checkratings.py -- checkratings.py, the hard check of a built world's player ratings
(step 2 before a world zip goes out; B64: NewLife 1.5b5 and the Europe Modpack eu1 shipped Ryan
Sessegnon at ~100 instead of ~75). Small made-up worlds in a temporary folder, no game needed:
the overall on Sessegnon's real abilities (r10 and eu1), a clean world passes, a new club's 95
fails rule A, the same player on the stars list passes, a rewritten game player (the plan's
edits, where B64 was) and an added player are held to it, a game player left as shipped is not,
and against an older world a rise of more than 8 fails rule B -- an id now naming someone else,
and a move to keeper, do not."""
import contextlib, io, json, os, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import checkratings as C
import pesdb
import playeredit as E

N = 0
GAME_CLUB, NEW_CLUB = 100, 72000

# Ryan Sessegnon (LB) as Modpack r10 has him, and as eu1 had him (B64)
SESS_R10 = {"Offensive Awareness": 69, "Ball Control": 77, "Dribbling": 79, "Tight Possession": 73,
            "Low Pass": 74, "Lofted Pass": 76, "Finishing": 63, "Heading": 60, "Place Kicking": 65,
            "Curl": 73, "Speed": 89, "Acceleration": 88, "Kicking Power": 73, "Jump": 70,
            "Physical Contact": 64, "Balance": 78, "Stamina": 84, "Defensive Awareness": 67,
            "Ball Winning": 70, "Aggression": 73}
SESS_EU1 = {"Offensive Awareness": 83, "Ball Control": 91, "Dribbling": 93, "Tight Possession": 87,
            "Low Pass": 88, "Lofted Pass": 90, "Finishing": 77, "Heading": 74, "Place Kicking": 79,
            "Curl": 87, "Speed": 99, "Acceleration": 99, "Kicking Power": 87, "Jump": 84,
            "Physical Contact": 78, "Balance": 92, "Stamina": 98, "Defensive Awareness": 81,
            "Ball Winning": 84, "Aggression": 87}


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def record(pid, name, pos, level, abilities=None):
    """a player record: every ability `level` (keeping ones 40 for an outfield player), or as given"""
    rec = bytearray(E.P_REC)
    rec[E.P_ID:E.P_ID + 4] = pid.to_bytes(4, "little")
    rec[E.P_NAME:E.P_NAME + 4 * E.P_NAME_LEN] = E.name_slots(name)
    E.setf(rec, "Registered Position", E.POSITIONS.index(pos))
    for n, _b in E.ABILITIES:
        v = level if (pos == "GK") == n.startswith("GK") else 40
        E.setf(rec, n, (abilities or {}).get(n, v))
    return bytes(rec)


def team(tid, name):
    rec = bytearray(E.T_REC)
    rec[E.T_ID:E.T_ID + 4] = tid.to_bytes(4, "little")
    rec[E.T_NAME:E.T_NAME + len(name)] = name.encode("utf-8")
    return bytes(rec)


def world(root, name, players, plan=None, packed=True):
    """a world folder: players [(pid, name, pos, level, club, abilities)], and its plan"""
    d = os.path.join(root, name)
    db = os.path.join(d, "common", "etc", "pesdb")
    os.makedirs(db)
    wrap = pesdb.wesys_pack if packed else (lambda b: b)
    open(os.path.join(db, "Player.bin"), "wb").write(
        wrap(b"".join(record(p, n, pos, lv, ab) for p, n, pos, lv, _c, ab in players)))
    open(os.path.join(db, "PlayerAssignment.bin"), "wb").write(wrap(b"".join(
        i.to_bytes(4, "little") + p.to_bytes(4, "little") + c.to_bytes(4, "little") + i.to_bytes(4, "little")
        for i, (p, _n, _pos, _lv, c, _ab) in enumerate(players))))
    open(os.path.join(db, "Team.bin"), "wb").write(wrap(team(GAME_CLUB, "Game FC") + team(NEW_CLUB, "New FC")))
    json.dump(plan or {"leagues": [{"name": "Test League", "teams": [NEW_CLUB], "game_clubs": {}}],
                       "others": [], "players": {}},
              open(os.path.join(d, "leaguebuilder-plan.json"), "w", encoding="utf-8"))
    return d


def main_quiet(argv):
    """checkratings.main(argv), its report kept off the test's output"""
    with contextlib.redirect_stdout(io.StringIO()):
        return C.main(argv)


def run(w, **kw):
    lines = []
    passed, fails = C.check(w, out=lines.append, **kw)
    return passed, fails, "\n".join(lines)


def main():
    tmp = tempfile.mkdtemp(prefix="checkratings_")
    try:
        nostars = os.path.join(tmp, "none.txt")
        open(nostars, "w").close()

        # the overall, on Sessegnon's real abilities
        r10 = C.overall(int.from_bytes(record(114021, "Ryan Sessegnon", "LB", 0, SESS_R10), "little"))
        eu1 = C.overall(int.from_bytes(record(114021, "Ryan Sessegnon", "LB", 0, SESS_EU1), "little"))
        ok("Sessegnon in r10 is about 75 (%d)" % r10, 73 <= r10 <= 78)
        ok("Sessegnon in eu1 is 95 or more (%d)" % eu1, eu1 >= 95)
        ok("an ordinary player is far below 90",
           C.overall(int.from_bytes(record(1, "A", "CMF", 70), "little")) < 75)

        base = [(200001, "Ivan Keeper", "GK", 75, NEW_CLUB, None),
                (200002, "Marko Middle", "CMF", 70, NEW_CLUB, None),
                (200003, "Luka Forward", "CF", 72, NEW_CLUB, None),
                (5000, "Old Legend", "SS", 97, GAME_CLUB, None)]       # the game's, as shipped

        # pass: the world's players are ordinary; a shipped 97 is not the world's
        w = world(tmp, "_Pass", base)
        passed, fails, text = run(w, stars=nostars)
        ok("a clean world passes", passed and not fails["a"])
        ok("the summary counts every player", "players 4, written by the world 3" in text)
        ok("the summary lists the top 15", "top 15, all players:" in text and "Old Legend" in text)
        ok("a shipped player left as the game ships him is not the world's", 5000 not in fails["a"])
        ok("main() exits 0 on a pass", main_quiet([w, "--stars", nostars]) == 0)
        w_raw = world(tmp, "_Raw", base, packed=False)
        ok("tables that are not WESYS-packed read the same", run(w_raw, stars=nostars)[0])
        ok("a Player.bin path works as well as a world folder",
           run(os.path.join(w, "common", "etc", "pesdb", "Player.bin"), stars=nostars)[0])

        # rule A: a new club's 95 fails
        star = (200009, "Big Star", "CF", 95, NEW_CLUB, None)
        w = world(tmp, "_RuleA", base + [star])
        passed, fails, text = run(w, stars=nostars)
        ok("rule A: a new club's player at 95 fails", not passed and fails["a"] == [200009])
        ok("rule A: the offender is named in the report", "Big Star" in text and "FAIL" in text)
        ok("main() exits 1 on a fail", main_quiet([w, "--stars", nostars]) == 1)

        # the same player on the stars list passes
        stars = os.path.join(tmp, "stars.txt")
        open(stars, "w", encoding="utf-8").write("# stars\n200009  # Big Star\n")
        passed, fails, _ = run(w, stars=stars)
        ok("rule A: a player on the stars list passes", passed and not fails["a"])
        ok("main() exits 0 with the stars list", main_quiet([w, "--stars", stars]) == 0)

        # B64's own case: a game player the recipe rewrites (the NewLife refresh) is held to it
        sess = (114021, "Ryan Sessegnon", "LB", 0, GAME_CLUB, SESS_EU1)
        plan = {"leagues": [{"name": "Test League", "teams": [NEW_CLUB], "game_clubs": {}}], "others": [],
                "players": {str(GAME_CLUB): {"edits": {"114021": {"Speed": "99"}}}}}
        w = world(tmp, "_B64", base + [sess], plan)
        passed, fails, _ = run(w, stars=nostars)
        ok("rule A: a rewritten game player at 96 fails (B64)", not passed and fails["a"] == [114021])
        w = world(tmp, "_B64noplan", base + [sess])
        ok("the same game player the recipe does not rewrite is the game's", run(w, stars=nostars)[0])

        # an added player (an id after the game's last) at a game club is the world's
        added = (C.GAME_LAST_PID + 50, "Joined Star", "CB", 96, GAME_CLUB, None)
        passed, fails, _ = run(world(tmp, "_Added", base + [added]), stars=nostars)
        ok("rule A: an added player at a game club is held to it", fails["a"] == [C.GAME_LAST_PID + 50])

        # a club of the plan's leagues that is not a kept game club is new, whatever its id
        plan = {"leagues": [{"name": "L", "teams": [GAME_CLUB, NEW_CLUB], "game_clubs": {}}],
                "others": [], "players": {}}
        passed, fails, _ = run(world(tmp, "_PlanClub", base + [(5001, "X", "CF", 95, GAME_CLUB, None)], plan),
                               stars=nostars)
        ok("a plan league's club counts as new", 5001 in fails["a"] and 5000 in fails["a"])
        plan["leagues"][0]["game_clubs"] = {"0": {"id": GAME_CLUB, "keep": True}}
        passed, fails, _ = run(world(tmp, "_KeptClub", base + [(5001, "X", "CF", 95, GAME_CLUB, None)], plan),
                               stars=nostars)
        ok("a game club the plan keeps does not", passed)

        # rule B: against an older world
        old = world(tmp, "_Old", base + [(114021, "Ryan Sessegnon", "LB", 0, GAME_CLUB, SESS_R10),
                                         (200020, "Someone Else", "CMF", 50, NEW_CLUB, None),
                                         (200021, "Moved Keeper", "CMF", 70, NEW_CLUB, None)])
        new = world(tmp, "_New", base + [(114021, "Ryan Sessegnon", "LB", 0, GAME_CLUB, SESS_EU1),
                                         (200020, "Another Man", "CMF", 75, NEW_CLUB, None),
                                         (200021, "Moved Keeper", "GK", 70, NEW_CLUB,
                                          dict((n, 70) for n, _b in E.ABILITIES))])
        passed, fails, text = run(new, old=old, stars=stars, max_ovr=101)
        ok("rule B: Sessegnon +20 against r10 fails", not passed and fails["b"] == [114021])
        ok("rule B: the report says how much", "was 76, +20" in text)
        ok("rule B: an id now naming someone else is skipped", 200020 not in fails["b"]
           and "1 ids now name someone else" in text)
        ok("rule B: a move to keeper is not a rise", 200021 not in fails["b"])
        ok("rule B: a world against itself passes", run(old, old=old, stars=stars)[0])
        ok("main() takes --old", main_quiet([new, "--old", old, "--stars", stars, "--max", "101"]) == 1)
        ok("rule B: --rise 25 lets +20 through", run(new, old=old, stars=stars, max_ovr=101, max_rise=25)[0])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("test_checkratings: ok (%d)" % N)


if __name__ == "__main__":
    main()
