r"""python tools/test_club_money_recipe.py [<the game's tables: the pesdb folder>]

FL 2027 (mato 07.11.2026: "budzete moramo srediti i prihode klubova"): a recipe can give its clubs,
new ones and the game's own, the money it has for them ("club_money", keyed "<league name>/<k>" or
a team id): the transfer budget base, the followers base, the ranking class and the share of
followers of the club's "fans" line. Without the key a club gets Build's estimate by squad and
division as before. A club of the game keeps followers of its own; one with money of its own takes
the recipe's budget. A bad entry is reported and the estimate taken.

The tables default to Mod Studio's (%APPDATA%\FL26ModStudio\tables\common\etc\pesdb); the squads
are stand-ins. Everything is written in a temp folder.
"""
import os, shutil, struct, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import leaguebuilder as B
import lbplayers, pesdb
import mkworld as W

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ.get("APPDATA", ""), "FL26ModStudio",
                                                         "tables", "common", "etc", "pesdb")
if not os.path.isfile(os.path.join(src, "Team.bin")):
    print("SKIPPED: no Team.bin in %s (give the game's pesdb folder)" % src)
    sys.exit(0)
db = tempfile.mkdtemp(prefix="recipemoney-")
shutil.copy(os.path.join(src, "Team.bin"), db)


def records():
    raw = pesdb.wesys_unpack(open(os.path.join(db, "Team.bin"), "rb").read())
    out = {}
    for o in range(0, len(raw) - W.T_REC + 1, W.T_REC):
        tid = int.from_bytes(raw[o + W.T_ID:o + W.T_ID + 4], "little")
        out[tid] = (struct.unpack_from("<I", raw, o + 0x34)[0], struct.unpack_from("<I", raw, o + 0x38)[0])
    return out


before = records()
ZALGIRIS, CELTIC, DINAMO = 199, 131, 1203
NEW = max(t for t in before if t < 65536)
NEW2 = max(t for t in before if t < NEW)
ok("Zalgiris has no money in the game, Celtic and Dinamo have",
   before[ZALGIRIS][0] & 0xffffff == 0 and before[CELTIC][0] & 0xffffff and before[DINAMO][0] & 0xffffff)

# the keys: a place of a league, or a team id
clubs = {"leagues": [{"name": "A Lyga", "teams": [NEW, ZALGIRIS, NEW2]}]}
filled = {"club_money": {
    "A Lyga/0": {"budget": 4200, "followers": 25000, "fame": 2, "fans": 30},
    "A Lyga/1": {"budget": 9100, "fame": 4, "fans": 60},
    str(CELTIC): {"budget": 77700},
    str(DINAMO): {"budget": 55500, "fame": 5, "fans": 80},
    "A Lyga/2": {"budget": -1, "fans": 50},
    "A Lyga/9": {"budget": 1},
}}
money, bad = B.money_refs(filled, clubs)
ok("places and team ids found: %s" % sorted(money), set(money) == {NEW, ZALGIRIS, CELTIC, DINAMO, NEW2})
ok("a place past the league reported", any("A Lyga/9" in b for b in bad))
ok("a negative budget reported, the estimate kept", any("budget -1" in b for b in bad) and "budget" not in money[NEW2])
ok("a share with no class reported and left out", any("needs a class" in b for b in bad) and not money[NEW2])
ok("a boolean is no number", B.money_refs({"club_money": {"A Lyga/0": {"budget": True}}}, clubs)[0][NEW] == {})


class Squads:                             # stand-in squads: one rough overall per club
    def __init__(self, _db):
        pass

    def squad(self, tid):
        return [{"q": 70}] * 11


lbplayers.Squads = Squads
B.club_strength = lambda rows: 70.0
lbplayers.tier_of = lambda p, mine: p["tier"]
top = {"name": "A Lyga", "tier": 1}
pl = {"leagues": [top]}
said = []
lines = B.club_money({NEW: top, NEW2: top}, pl, db, said.append, game_of={ZALGIRIS: top}, money=money)
after = records()
ok("the new club takes the recipe's budget and followers",
   after[NEW][0] & 0xffffff == 4200 and after[NEW][1] & 0x7fffff == 25000)
ok("the other new club (a bad entry) the estimate",
   after[NEW2][0] & 0xffffff == B.money_base(70, 1))
ok("Zalgiris (B298) the recipe's budget, followers as before",
   after[ZALGIRIS][0] & 0xffffff == 9100 and after[ZALGIRIS][1] & 0x7fffff == 10000)
ok("Celtic: the recipe's budget, its own followers",
   after[CELTIC][0] & 0xffffff == 77700 and after[CELTIC][1] == before[CELTIC][1])
ok("Dinamo: the recipe's budget", after[DINAMO][0] & 0xffffff == 55500 and after[DINAMO][1] == before[DINAMO][1])
ok("the bits around the budget are the game's",
   all(after[t][0] >> 24 == before[t][0] >> 24 for t in (NEW, ZALGIRIS, CELTIC, DINAMO)))
ids = {int(t): (int(c), int(p)) for l in lines for c, p, *ts in [l.split()[1:]] for t in ts}
ok("fans lines: %s" % lines, ids.get(NEW) == (2, 30) and ids.get(ZALGIRIS) == (4, 60) and ids.get(DINAMO) == (5, 80))
ok("Celtic, with no class in the recipe, has no line", CELTIC not in ids)
ok("the new club with no class keeps the estimate's line", ids.get(NEW2) == (next(c for m, c in B.FAME_CLASS if 70 >= m)
                                                                               if 70 >= B.FAME_CLASS[-1][0] else 0, 100))
ok("the log counts the recipe's clubs: %s" % said, any("club_money) for 4 club(s)" in x for x in said))
ok("only the recipe's money: still written", B.club_money({}, pl, db, said.append, money={CELTIC: {"budget": 100}}) == []
   and records()[CELTIC][0] & 0xffffff == 100)

# 11.11.2026: a finer share ("share", of 10,000): the fans line's whole percent and a fansx line, FL 2027 only
m2, bad2 = B.money_refs({"club_money": {"A Lyga/0": {"fame": 0, "share": 37}, "A Lyga/1": {"fame": 1, "share": 2550},
                                         "A Lyga/2": {"share": 40}}}, clubs)
ok("a fine share with no class reported and left out", any("needs a class" in b for b in bad2) and not m2[NEW2])
ok("a share of 0 reported", any("share 0" in b for b in B.money_refs({"club_money": {"A Lyga/0": {"fame": 0, "share": 0}}}, clubs)[1]))


def fan_lines(fl27):
    was, B.FL27 = B.FL27, fl27
    try:
        lx = B.club_money({NEW: top}, pl, db, said.append, game_of={ZALGIRIS: top}, money=m2)
    finally:
        B.FL27 = was
    fa = {int(t): (int(l.split()[1]), int(l.split()[2])) for l in lx if l.startswith("fans ") for t in l.split()[3:]}
    fx = {int(t): int(l.split()[1]) for l in lx if l.startswith("fansx ") for t in l.split()[2:]}
    return fa, fx


fa, fx = fan_lines(True)
ok("FL 2027: the percent an older module reads, and the fine share: %s %s" % (fa, fx),
   fa.get(NEW) == (0, 1) and fa.get(ZALGIRIS) == (1, 26) and fx == {NEW: 37, ZALGIRIS: 2550})
fa, fx = fan_lines(False)
ok("FL 2026: the percent only", fa.get(NEW) == (0, 1) and fa.get(ZALGIRIS) == (1, 26) and not fx)
shutil.rmtree(db, ignore_errors=True)
print("all %d checks passed" % N)
