r"""python tools/test_game_club_money.py [<the game's tables: the pesdb folder>]

B298 (vanni11 30.10.): in the Europe pack, clubs of the game the world put into a league that were
in none of the game's -- Zalgiris, HJK, RFS -- bought Endrick for 75M and Estevao for 66M. Team.bin
gives them no money and no following (base 0, followers 0), and out of the game's club ranking they
counted as its top class. Build now treats them as it treats its new clubs (leaguebuilder.club_money):
money by squad and division, and a "fans" line for fl26clubs. A club of the game with money of
its own keeps it; one with followers and no money (Rakow) gets the money and keeps the followers.

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
db = tempfile.mkdtemp(prefix="gamemoney-")
shutil.copy(os.path.join(src, "Team.bin"), db)


def records():
    raw = pesdb.wesys_unpack(open(os.path.join(db, "Team.bin"), "rb").read())
    out = {}
    for o in range(0, len(raw) - W.T_REC + 1, W.T_REC):
        tid = int.from_bytes(raw[o + W.T_ID:o + W.T_ID + 4], "little")
        out[tid] = (struct.unpack_from("<I", raw, o + 0x34)[0], struct.unpack_from("<I", raw, o + 0x38)[0])
    return out


before = records()
ZALGIRIS, HJK, CELTIC, DINAMO, RAKOW = 199, 1733, 131, 1203, 5288
for t in (ZALGIRIS, HJK):
    ok("the game gives club %d no money and no following" % t,
       before[t][0] & 0xffffff == 0 and before[t][1] & 0x7fffff == 0)
for t in (CELTIC, DINAMO):
    ok("... and club %d money of its own" % t, before[t][0] & 0xffffff > 0)
ok("Rakow: followers but no money", before[RAKOW][0] & 0xffffff == 0 and before[RAKOW][1] & 0x7fffff == 10000)
NEW = max(t for t in before if t < 65536 and t not in (0xffffffff,))   # a stand-in new club: one with money


class Squads:                             # stand-in squads: one rough overall per club
    def __init__(self, _db):
        pass

    def squad(self, tid):
        return [{"q": 70}] * 11


lbplayers.Squads = Squads
B.club_strength = lambda rows: 70.0
lbplayers.tier_of = lambda p, mine: p["tier"]
top = {"name": "A Lyga", "tier": 1}
second = {"name": "Ykkosliiga", "tier": 2}
pl = {"leagues": [top, second]}
said = []
lines = B.club_money({NEW: top}, pl, db, said.append,
                     game_of={ZALGIRIS: top, HJK: second, CELTIC: top, DINAMO: second, NEW: second, RAKOW: top})
after = records()
ok("Zalgiris (top flight): the money of a top-flight squad of 70", after[ZALGIRIS][0] & 0xffffff == B.money_base(70, 1))
ok("HJK (second division): less", after[HJK][0] & 0xffffff == B.money_base(70, 2) < B.money_base(70, 1))
ok("both: followers of their own", after[ZALGIRIS][1] & 0x7fffff == 10000 and after[HJK][1] & 0x7fffff == 10000)
ok("the bits around the two fields are the game's",
   all(after[t][0] >> 24 == before[t][0] >> 24 and after[t][1] & ~0x7fffff == before[t][1] & ~0x7fffff
       for t in (ZALGIRIS, HJK)))
ok("Rakow: the money of a top-flight squad, and its own followers",
   after[RAKOW][0] & 0xffffff == B.money_base(70, 1) and after[RAKOW][1] == before[RAKOW][1])
ok("Celtic and Dinamo keep the game's money and followers",
   after[CELTIC] == before[CELTIC] and after[DINAMO] == before[DINAMO])
ok("a new club listed as both is a new club (its league from new_of)",
   after[NEW][0] & 0xffffff == B.money_base(70, 1))
ids = {int(t): (int(c), int(p)) for l in lines for c, p, *ts in [l.split()[1:]] for t in ts}
ok("fans lines: Zalgiris, HJK, Rakow and the new club, not Celtic or Dinamo: %s" % lines,
   set(ids) == {ZALGIRIS, HJK, RAKOW, NEW})
ok("HJK's share is a second division's", ids[HJK][1] == B.FANS_PCT[1] and ids[ZALGIRIS][1] == 100)
ok("the log counts the new club and the game's apart: %s" % said,
   "money and following for 1 new club(s), by squad and division" in said[0]
   and "3 club(s) of the game" in said[1])
ok("nothing to do: no lines", B.club_money({}, pl, db, said.append, game_of={CELTIC: top}) == [])
shutil.rmtree(db, ignore_errors=True)
print("all %d checks passed" % N)
