"""python test_league_size.py <folder with the game's tables> -- request #7 (06.11.): how big a
league of ours can be. A league plays ROUNDS_MAX (54) rounds at most -- 28 clubs meeting twice,
the most a played league had (30 lost its 55th round, 25.10.) -- so 29 to 32 clubs meet once, and
32 is the end (a fixture round holds 16 matches). Before this, 28 clubs meeting four times (108
rounds) went through the plan untouched."""
import glob, os, re, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fl26world
import leaguebuilder as B
import mkleague as M

N = 0
HERE = os.path.dirname(os.path.abspath(__file__))


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def plan_error(base, clubs, legs):
    recipe = {"world": "_FL26Size", "leagues": [{"name": "Size League", "country": "Iceland", "clubs": clubs,
                                                   "legs": legs, "exchange": 3}]}
    try:
        B.plan(recipe, base)
        return None
    except B.BuildError as e:
        return str(e)


def main(base):
    ok("the limits: 10..32 clubs, 54 rounds", (B.CLUBS_MIN, B.CLUBS_MAX, B.ROUNDS_MAX) == (10, 32, 54))
    ok("max_legs: 10 -> 4, 14 -> 4, 18 -> 3, 20 -> 2, 28 -> 2, 29 -> 1, 32 -> 1",
       [B.max_legs(n) for n in (10, 14, 18, 20, 28, 29, 32)] == [4, 4, 3, 2, 2, 1, 1])
    ok("max_legs is 0 outside the sizes", B.max_legs(9) == 0 and B.max_legs(33) == 0)
    ok("every size of 10..32 meets at least once", all(B.max_legs(n) >= 1 for n in range(10, 33)))
    ok("a round of 32 clubs is 16 matches, what a fixture round holds", B.CLUBS_MAX // 2 == 16)
    # the UI's spin box and message read the same constants
    ui = open(os.path.join(HERE, "modstudio", "pages", "builder.py"), encoding="utf-8").read()
    ok("the league dialog checks the times against max_legs", "B.max_legs(L[\"clubs\"])" in ui)
    for clubs, legs in ((28, 2), (32, 1), (29, 1), (10, 4)):
        e = plan_error(base, clubs, legs)
        ok("%d clubs x %d: planned (%s)" % (clubs, legs, e), e is None)
    for clubs, legs, rounds in ((30, 2, 58), (28, 4, 108), (18, 4, 68), (29, 2, 58)):
        e = plan_error(base, clubs, legs) or ""
        ok("%d clubs x %d: %d rounds refused, the message says so (%s)" % (clubs, legs, rounds, e),
           ("play %d rounds" % rounds) in e and "54 at most" in e)
    e = plan_error(base, 33, 1) or ""
    ok("33 clubs: refused (%s)" % e, "10..32" in e)
    # FL 2027 takes 8 and 9 too (mato 07.11.: the Ýokary Liga, 8 clubs meeting four times); FL26 stays at 10
    g27 = tempfile.mkdtemp(prefix="fl27-size-")
    try:
        open(os.path.join(g27, "FL_2027.exe"), "wb").close()
        B.use_game(g27)
        ok("FL 2027: 8..32 clubs", (B.FL27, B.CLUBS_MIN, B.CLUBS_MAX) == (True, 8, 32))
        e = plan_error(base, 8, 4)
        ok("FL 2027: 8 clubs x 4, 28 rounds: planned (%s)" % e, e is None)
        ok("FL 2027: max_legs 8 -> 4, 9 -> 4", (B.max_legs(8), B.max_legs(9)) == (4, 4))
        e = plan_error(base, 7, 4) or ""
        ok("FL 2027: 7 clubs refused (%s)" % e, "8..32" in e)
    finally:
        B.use_game(None)
        shutil.rmtree(g27, ignore_errors=True)
    e = plan_error(base, 8, 4) or ""
    ok("FL26: 8 clubs refused, 10 the least (%s)" % e, B.CLUBS_MIN == 10 and "10..32" in e)
    # a whole Build of 32 clubs meeting once: the regulation holds 32 teams, the world line 31 rounds
    recipe = {"world": "_FL26Size", "leagues": [{"name": "Size League", "country": "Iceland", "clubs": 32,
                                                   "legs": 1, "exchange": 3}]}
    game = tempfile.mkdtemp(prefix="fl26-size-")
    try:
        for d in ("livecpk", "modules", "content"):
            os.makedirs(os.path.join(game, "SiderAddons", d))
        with open(os.path.join(game, "SiderAddons", "sider.ini"), "w") as f:
            f.write("[sider]\n")
        pl = B.plan(recipe, base)
        B.build(pl, base, game, False, log=lambda t: None)
        world = os.path.join(game, "SiderAddons", "livecpk", "_FL26Size")
        reg = glob.glob(os.path.join(world, "**", "CompetitionRegulation.bin"), recursive=True)
        regs = M.load(os.path.dirname(reg[0]), "CompetitionRegulation.bin")
        rid = pl["leagues"][0]["rid"]
        row = next(regs[i * M.REG:(i + 1) * M.REG] for i in range(len(regs) // M.REG)
                   if B.u16(regs, i * M.REG + M.R_ID) == rid)
        ok("built: the regulation of 32 clubs holds 32 teams", row[M.R_TEAMS] & 0x3f == 32)
        _n, lines = fl26world.read_world(os.path.join(world, "fl26world.txt"))
        L = next(x for x in lines if x.get("id") == rid)
        ok("built: the world line says 32 clubs, once (%s)" % {k: L.get(k) for k in ("clubs", "legs")},
           int(L.get("clubs", 0)) == 32 and int(L.get("legs", 0) or 1) == 1)
    finally:
        shutil.rmtree(game, ignore_errors=True)
    doc = open(os.path.join(HERE, "..", "guides", "en", "mod-studio-guide.md"), encoding="utf-8").read()
    ok("the guide's limits say 10 - 32, and 8 in FL 2027", re.search(r"\| Clubs per league \| 10 – 32", doc) is not None
       and "FL 2027 also takes 8 and 9" in doc)
    print("1..%d" % N)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ["APPDATA"], "FL26ModStudio", "tables",
                                                             "common", "etc", "pesdb"))
