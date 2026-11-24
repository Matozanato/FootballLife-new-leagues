"""A continental cup's preliminary round ("europe_pre", 11.11.2026): ccup_plan with marked places, the
world file's lpre line. Offline; nothing of a game is read or written.

The generic preliminary-round planner serves cups such as the CAF competitions.
CONCACAF uses its own 27-club engine.
"""
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B
import fl26world

N = 0


def ok(label, condition):
    global N
    assert condition, label
    N += 1
    print("ok %d - %s" % (N, label))


CL, CC, CONCACAF = 6, 7, 13
L = list(range(301, 353))                 # 52 African top divisions, the strongest first

# --- the CAF Champions League: 12 champions and 4 runners-up direct, 24 champions and 8 runners-up
#     in the round; the 16 weakest champions go to the Confederation Cup's round
own, pre = [], {}
for i, r in enumerate(L):
    if i < 36:
        own.append((r, 1, CL, 0))
        if i >= 12:
            pre[(r, 1, CL)] = 100 + i
    else:
        own.append((r, 1, CC, 0))
        pre[(r, 1, CC)] = 200 + i
    if i < 12:
        own.append((r, 2, CL, 0))
        if i >= 4:
            pre[(r, 2, CL)] = 50 + i          # the runners-up of the big leagues: the strongest of the round
        own.append((r, 3, CC, 0))
        if i >= 4:
            pre[(r, 3, CC)] = 150 + i
        own.append((r, 0, CC, 0))             # the cup winner: direct
    elif i < 20:
        own.append((r, 0, CC, 0))
        pre[(r, 0, CC)] = 160 + i             # a cup winner in the round
room = {r: 16 for r in L}
cups, notes = B.ccup_plan(own, room, pre=pre)
cl = next(c for c in cups if c["number"] == CL)
cc = next(c for c in cups if c["number"] == CC)
ok("the Champions League is a cup of 32 in 8 groups", len(cl["entry"]) == 32 and cl["groups"] == 8)
ok("16 direct places, the champions before the runners-up",
   cl["entry"][:16] == [(r, 1) for r in L[:12]] + [(r, 2) for r in L[:4]])
ok("16 places for the winners of the ties, in the last two pots",
   cl["entry"][16:] == [("pre", k) for k in range(16)])
ties = cl["pre"]["ties"]
ok("16 ties of two clubs, every marked place once",
   len(ties) == 16 and sorted(tuple(e) for t in ties for e in t)
   == sorted([(r, 1) for r in L[12:36]] + [(r, 2) for r in L[4:12]]))
ok("the strongest v the weakest, the weaker club at home (first)",
   ties[0] == [(L[35], 1), (L[4], 2)] and ties[15] == [(L[20], 1), (L[19], 1)])
ok("no two clubs of a league in a tie", all(B.entry_league(a) != B.entry_league(b) for a, b in ties))
ok("the round's days", (cl["pre"]["fill"], cl["pre"]["day"]) == (B.CCUP_PRE_FILL, B.CCUP_PRE_DAY))
ok("the Confederation Cup: 4 third places and 12 cup winners direct",
   len(cc["entry"]) == 32 and sorted(map(tuple, cc["entry"][:16]), key=str)
   == sorted([(r, 3) for r in L[:4]] + [("cup", r) for r in L[:12]], key=str))
t7 = [tuple(e) for t in cc["pre"]["ties"] for e in t]
ok("its round: the 16 weakest champions, 8 third places and 8 cup winners",
   len(cc["pre"]["ties"]) == 16 and sorted(t7, key=str)
   == sorted([(r, 1) for r in L[36:]] + [(r, 3) for r in L[4:12]] + [("cup", r) for r in L[12:20]], key=str))
ok("every one of the 52 countries is in one of the two cups or their rounds",
   {B.entry_league(e) for c in (cl, cc) for e in B.ccup_all_entries(c) if e[0] != "pre"} == set(L))
ok("nothing left out", not notes)

# --- the same places with no mark: the cup as before, the places past 32 get none
plain, pnotes = B.ccup_plan(own, room)
p6 = next(c for c in plain if c["number"] == CL)
ok("without marks: 32 clubs, no round, and a note about the places that get none",
   len(p6["entry"]) == 32 and "pre" not in p6 and any("get none" in n for n in pnotes))
ok("a mark on a place the cup has not got changes nothing",
   B.ccup_plan(own, room, pre={(999, 1, CL): 1})[0] == plain)

# --- exercise the generic knockout path with a synthetic cup: the same seeds,
#     inherited entry ordering, bracket order and overflow checks.
KNOCKOUT = 90
fill = [(51, p) for p in range(1, 13)]
with patch.object(fl26world, "CCUPS", [(KNOCKOUT, "Test knockout", "TEST_KO", 6, fill)]), \
     patch.object(fl26world, "CCUP_KNOCKOUT", {KNOCKOUT}):
    K = list(range(401, 427))                 # 26 champions
    own_ko = [(r, 1, KNOCKOUT, 0) for r in K]
    cko = next(c for c in B.ccup_plan(own_ko, {r: 10 for r in K}, pre={(r, 1, KNOCKOUT): i + 1 for i, r in enumerate(K)})[0]
               if c["number"] == KNOCKOUT)
    mls = fill[:6]
    ok("a knockout of 16 with no groups, every place a tie's winner",
       cko["groups"] == 0 and len(cko["entry"]) == 16 and all(e[0] == "pre" for e in cko["entry"]))
    ok("the bracket: the first tie's winner v the last's", [e[1] for e in cko["entry"][:4]] == [0, 15, 1, 14])
    ok("16 ties: 26 champions and the first 6 shipped places",
       len(cko["pre"]["ties"]) == 16
       and sorted(tuple(e) for t in cko["pre"]["ties"] for e in t) == sorted(mls + [(r, 1) for r in K]))
    ok("the shipped places are the strongest: each meets one of the weakest champions",
       [tuple(t[1]) for t in cko["pre"]["ties"][:6]] == mls
       and [tuple(t[0]) for t in cko["pre"]["ties"][:6]] == [(r, 1) for r in K[:-7:-1]])

    # --- more marked places than the round takes: the weakest get none, and it says so
    K2 = list(range(401, 441))                # 40 champions
    c40, n40 = B.ccup_plan([(r, 1, KNOCKOUT, 0) for r in K2], {r: 10 for r in K2},
                           pre={(r, 1, KNOCKOUT): i + 1 for i, r in enumerate(K2)})
    c40 = next(c for c in c40 if c["number"] == KNOCKOUT)
    ok("40 marked places: 32 play, the 8 with the weakest seeds get none (noted)",
       len(c40["pre"]["ties"]) == 16 and (K2[32], 1) not in [tuple(e) for t in c40["pre"]["ties"] for e in t]
       and any("the last 8 get none" in n for n in n40))

# --- target 13 cannot be redirected to the generic one-match preliminary round
actual = B.ccup_plan([(401, 1, CONCACAF, 0)], {401: 10}, pre={(401, 1, CONCACAF): 1})[0][0]
ok("CONCACAF is the dedicated 27-place engine", actual["participants"] == 27
   and actual["code"] == "FL_CONCACAF" and actual["entry"] == [] and "pre" not in actual)

# --- no size fits: built without the round, with a note
few, nfew = B.ccup_plan([(301, 1, CL, 0), (302, 1, CL, 0), (303, 1, CL, 0), (304, 1, CL, 0), (305, 1, CL, 0)],
                        {r: 10 for r in range(301, 306)}, pre={(305, 1, CL): 1})
ok("4 direct places and 1 marked: no round, the cup of 4 as before",
   "pre" not in few[0] and len(few[0]["entry"]) == 4 and any("without the round" in n for n in nfew))

# --- the world file's line
pl = {"leagues": [{"rid": r, "europe": [[1, CC], [0, CC]]} for r in (501, 502)]
      + [{"rid": r, "europe": [[1, CC]]} for r in (503, 504)],
      "ccups": [{"number": CC, "name": "CAF Confederation Cup", "ko": 618,
                 "winners": [[501, 311], [502, 314]],
                 "pre": {"ties": [[(504, 1), ("cup", 501)], [(503, 1), ("cup", 502)]], "fill": 226, "day": 232,
                         "reg": 700, "cid": 61}}]}
ok("lpre line: one match, the cup winners by their cups' regulations, alt from the first free position",
   B.cup_prelim_lines(pl) == ["lpre 700 cup=618 fill=226 days=232,232 entry=504:1,311:0,503:1,314:0 single=1 alt=2:501:2,4:502:2"])
ok("a cup with no round writes no line", B.cup_prelim_lines({"leagues": [], "ccups": [{"number": CL, "ko": 616}]}) == [])
try:
    B.cup_prelim_lines({"leagues": [], "ccups": [{"number": CC, "name": "X", "ko": 1, "winners": [],
                                                  "pre": {"ties": [[(504, 1), ("cup", 501)]], "fill": 1, "day": 2, "reg": 700}}]})
    ok("a cup winner of a country with no cup is a Build error", False)
except B.BuildError:
    ok("a cup winner of a country with no cup is a Build error", True)
ok("the helper competition's code and name", (B.cup_pre_code({"number": 6}), B.cup_pre_name({"name": "CAF Champions League"}))
   == ("FL_PRE6", "CAF Champions League Preliminary Round"))
# --- the name in the competition table (24 bytes): the Build of 11.11. stopped on the long one
for nm in ("CAF Champions League", "CAF Confederation Cup", "CONCACAF Champions Cup", "AFC Champions League Two",
           "OFC Champions League", "Copa", "Ligue des Champions de la CAF ééé", "é" * 30):
    t = B.cup_pre_table_name({"name": nm})
    ok("the table name of %r is %r, 24 bytes at most" % (nm, t), 0 < len(t.encode("utf-8")) <= 24 and nm.startswith(t))
ok("a short cup name is kept whole", B.cup_pre_table_name({"name": "CONCACAF Champions Cup"}) == "CONCACAF Champions Cup")

# --- with the game's tables (a pesdb folder): the helper competition is really made, as the Build makes it
if len(sys.argv) > 1:
    import shutil
    import tempfile
    import mkeuropo
    import mkleague as M
    base = sys.argv[1]
    comp, regs = M.load(base, "Competition.bin"), M.load(base, "CompetitionRegulation.bin")
    cids = {M.comp_cid(comp[i:i + M.COMP]) for i in range(0, len(comp), M.COMP)}
    rids = {int.from_bytes(regs[i + M.R_ID:i + M.R_ID + 2], "little") for i in range(0, len(regs), M.REG)}
    cid = next(c for c in range(130, 256) if c not in cids)
    master = next(r for r in range(300, 1000) if not any((r + g * 1024) in rids for g in range(17)))
    for nm in ("CAF Champions League", "CAF Confederation Cup", "CONCACAF Champions Cup"):
        out = tempfile.mkdtemp()
        said = []
        try:
            mkeuropo.prerounds_single(base, out, cid, "FL_PRE6", B.cup_pre_table_name({"name": nm}), [(master, 16)],
                                      log=said.append, one_match=True, region=1, confederation=0)
            made = [f for _d, _s, fs in os.walk(out) for f in fs]
        finally:
            shutil.rmtree(out, ignore_errors=True)
        ok("%s: the round's competition is made on the game's tables (16 one-match ties)" % nm,
           "Competition.bin" in made and "CompetitionRegulation.bin" in made and any("16 ties" in x for x in said))
else:
    print("skip - no pesdb folder: the helper competition is not made")
print("test_ccup_pre: ok (%d)" % N)
