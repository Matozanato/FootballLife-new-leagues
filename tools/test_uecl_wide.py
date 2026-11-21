"""FL 2027's wide Conference League (fl26world.CW_CONFIG: Prijedlog C and a Conference League Q1 of
62, mato 07.11.: "kvalifikacije za europu prosiriti ako je to moguce"): the rounds' sizes, new clubs
(56 / 40 / 74 = 170) and direct room (28 / 12 / 0), c_places with CW's room, pick_rounds_cw and the
order europe_rounds tries them in, the access_alias in the count (Belgium's 155 / 115), mkeuropo's
rounds of 31 ties in FL 2027's tables -- the master's six-bit club count, ids reg + k * 1024 -- and
CW's own round taking an id after C's and none of the last Build's cups'. The DLL side:
tools/test_uecl_wide_native.py.

    python tools/test_uecl_wide.py [--tables27 <FL27 tables folder>]
"""
import os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
APPDATA = os.environ.get("APPDATA", "")


def arg(k, default):
    a = sys.argv[1:]
    return a[a.index(k) + 1] if k in a else default


def pesdb_of(d):
    for p in (os.path.join(d, "common", "etc", "pesdb"), d):
        if os.path.exists(os.path.join(p, "CompetitionRegulation.bin")):
            return p
    return None


T27 = pesdb_of(arg("--tables27", os.path.join(APPDATA, "FL26ModStudio", "tables27")))

import fl26world as W
import leaguebuilder as LB
import mkeuropo as E
import mkleague as M

fails = []


def ok(what, cond):
    print("%s  %s" % ("ok  " if cond else "FAIL", what))
    if not cond:
        fails.append(what)


C, CW = W.C_CONFIG, W.CW_CONFIG
ok("CW_CONFIG: C's rounds and the Conference League's first", CW == C + [(2, 3)] and W.cw_world(CW) and W.c_world(CW)
   and not W.cw_world(C) and not W.cw_world(W.Q1_CONFIG) and not W.cw_world(None))
sizes = {r: W.q_size(CW, r) for r in CW}
ok("sizes: UCL 32 / 32 / 16 / 16, UEL 16 / 16 / 32 / 32, UECL 62 / 62 / 40 / 40 (%s)" % sorted(sizes.items()),
   [sizes[(0, s)] for s in (3, 2, 1, 0)] == [32, 32, 16, 16] and [sizes[(1, s)] for s in (3, 2, 1, 0)] == [16, 16, 32, 32]
   and [sizes[(2, s)] for s in (3, 2, 1, 0)] == [62, 62, 40, 40])
ok("no round past QROUND_MAX (62: 31 ties, the six-bit club count)", max(sizes.values()) == W.QROUND_MAX == 62)
ok("C's sizes as before", [W.q_size(C, (2, s)) for s in (2, 1, 0)] == [32, 32, 32] and W.q_size(C, (0, 0)) == 16)
room = W.qual_room(CW)
ok("new clubs 56 / 40 / 74 (%s)" % sorted(room.items()), room == {W.UCLQ: 56, W.UELQ: 40, W.UECLQ: 74})
ok("C's new clubs as before: 56 / 40 / 16", W.qual_room(C) == {W.UCLQ: 56, W.UELQ: 40, W.UECLQ: 16})
if hasattr(W, "direct_room"):
    ok("direct entrants 28 / 12 / 0 (C: 28 / 12 / 4)", W.direct_room([], CW) == {0: 28, 1: 12, 2: 0}
       and W.direct_room([], C) == {0: 28, 1: 12, 2: 4})

# the uefa lines: 56 UCLQ, 32 UELQ, 74 UECLQ and 20 direct of the Conference League
ucl = [(500 + i, 1, W.UCLQ, 0) for i in range(56)]
uel = [(600 + i, 3, W.UELQ, 0) for i in range(32)]
ecl = [(700 + i, 4, W.UECLQ, 0) for i in range(90)]
lines = ucl + uel + ecl
cw_lines, moved = W.c_places(lines, rounds=CW)
c_lines, moved_c = W.c_places(lines)
ok("c_places with CW: 8 Conference League places up to the Europa League's 40, 74 left (C: 8 up too)",
   len(moved) == 8 and W.qual_places(cw_lines, CW)[W.UELQ] == 40 and W.qual_places(cw_lines, CW)[W.UECLQ] == 82
   and len(moved_c) == 8)
ok("pick_rounds_cw: the lines fill CW", W.pick_rounds_cw(cw_lines) == CW and W.pick_rounds_cw(cw_lines, False) is None)
few = [e for e in cw_lines if e[2] != W.UECLQ] + [e for e in cw_lines if e[2] == W.UECLQ][:73]
ok("pick_rounds_cw: one Conference League place short of 74 -> None, C still", W.pick_rounds_cw(few) is None
   and W.pick_rounds_c(few) == C)
short = cw_lines[W.C_TOPUP:]
ok("pick_rounds_cw: up to C_TOPUP Champions League places short -> CW (the big five top them up)",
   W.pick_rounds_cw(short) == CW and W.pick_rounds_cw(cw_lines[W.C_TOPUP + 1:]) is None)

# leaguebuilder.europe_rounds: CW first, and the alias in the count
real = LB.is_fl27
try:
    LB.is_fl27 = lambda g: True
    import inspect
    src = inspect.getsource(LB.europe_rounds)
    ok("europe_rounds tries CW before C and counts with access_alias",
       src.index("pick_rounds_cw") < src.index("pick_rounds_c(") and "access_alias" in src)
finally:
    LB.is_fl27 = real

# mkeuropo: CW's rounds in FL 2027's tables
if not T27:
    print("SKIPPED the FL 2027 tables part: no tables27 (--tables27)")
else:
    tmp = tempfile.mkdtemp()
    try:
        db = os.path.join(tmp, "common", "etc", "pesdb")
        shutil.copytree(T27, db)
        said = []
        _c, qc = LB.europe(tmp, db, log=said.append, uecl=True, rounds=C)
        shutil.rmtree(db)
        shutil.copytree(T27, db)
        c_ids = [r for _c2, _n, r in qc]
        avoid = {max(c_ids) + 1, max(c_ids) + 2}
        said = []
        _c, qw = LB.europe(tmp, db, log=said.append, uecl=True, rounds=CW, avoid=avoid)
        print("  C: %s\n  CW: %s" % (qc, qw))
        ok("CW: 11 qround lines, C's 10 with the same regulations and `qround 12 1`",
           len(qw) == 11 and qw[:10] == qc and qw[10][:2] == (12, 1))
        ok("CW's own round: an id after C's and none of the last Build's cups' (%s)" % sorted(avoid),
           qw[10][2] > max(c_ids) and qw[10][2] not in avoid)
        regs = M.load(db, "CompetitionRegulation.bin")
        rows = [regs[i * M.REG:(i + 1) * M.REG] for i in range(len(regs) // M.REG)]
        stage = {v: k for k, v in W.QROUND_NUMBER.items()}
        for c, n, reg in qw:
            mine = [r for r in rows if E.rid(r) & 0x3ff == reg]
            ties = W.q_size(CW, (c - 10, stage[n])) // 2
            ids = sorted(E.rid(r) for r in mine)
            good = (len(mine) == ties + 1 and all(r[M.R_TEAMS] & 0x3f == 2 * ties and r[0x10] == ties for r in mine)
                    and sorted(r[E.R_GROUP] for r in mine) == list(range(ties)) + [255]
                    and ids == [reg + k * 1024 for k in range(ties + 1)] and max(ids) < 0x8000)
            if ties > 16 or not good:
                ok("qround %d %d %d: %d rows, %d clubs, %d ties on every row, ids reg + k*1024 below 0x8000"
                   % (c, n, reg, len(mine), 2 * ties, ties), good)
        uecl = {M.reg_cid(r) for r in rows if E.rid(r) & 0x3ff in [r2 for c2, _n, r2 in qw if c2 == 12]}
        ok("the Conference League's four rounds in one competition", len(uecl) == 1)
        ok("the build log names the 62s", any("Conference League first, July, 62 clubs" in s for s in said))
        try:
            E._copy_ties([], bytearray(), 0, b"", 32)
            ok("_copy_ties refuses 32 ties", False)
        except SystemExit:
            ok("_copy_ties refuses 32 ties (64 clubs: past the six-bit count)", True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

print("\n%d failed" % len(fails) if fails else "\nall checks passed")
sys.exit(1 if fails else 0)
