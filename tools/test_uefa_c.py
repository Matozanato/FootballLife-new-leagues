r"""FL 2027's UEFA qualifying, "Prijedlog C" (mato 07.11., notes/uefa-q1-srpanj.md), the League
Builder's side: fl26world.C_CONFIG's rounds, sizes, rooms and ways down, the direct entrants
28 / 12 / 4, c_places (Conference League qualifying places moved up to the Europa League's 40),
pick_rounds_c, the notes uefa_places gives, mkeuropo's play-offs of 32 (`qround 11 0` /
`qround 12 0`) in FL 2027's tables, and leaguebuilder's choice of rounds for an FL 2027 world.
FL 2026 and Prijedlog A must not change at all: the same dump (rooms, rounds, the uefa lines and
their notes, the qualifying rounds' table rows) is made with the tools as they were before
(commit BASE, from git) and compared.

    python tools/test_uefa_c.py [--tables <FL26 tables folder>] [--tables27 <FL27 tables folder>]
                                [--plan27 <an FL27 world's leaguebuilder-plan.json>]

The tables default to Mod Studio's (%APPDATA%/FL26ModStudio/tables, tables27) and the plan to the
Megapack test world's on E:\FL\FL27 (read only); a part whose files are missing says so and is skipped.
The native side (the DLL) is tools/test_uefa_c_native.py.
"""
import io, json, os, shutil, subprocess, sys, tarfile, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "77f0cdc"            # test0611, the branch point: Prijedlog A, no play-offs of 32 yet
APPDATA = os.environ.get("APPDATA", "")


def arg(k, default):
    a = sys.argv[1:]
    return a[a.index(k) + 1] if k in a else default


def pesdb_of(d):
    for p in (os.path.join(d, "common", "etc", "pesdb"), d):
        if os.path.exists(os.path.join(p, "CompetitionRegulation.bin")):
            return p
    return None


T26 = pesdb_of(arg("--tables", os.path.join(APPDATA, "FL26ModStudio", "tables")))
T27 = pesdb_of(arg("--tables27", os.path.join(APPDATA, "FL26ModStudio", "tables27")))
PLAN27 = arg("--plan27", r"E:\FL\FL27\game\SiderAddons\livecpk\_FL26MegaP\leaguebuilder-plan.json")

# --- the dump of FL 2026 and Prijedlog A: run in a child process, sys.path at a tools folder --------
DUMP = r'''
import hashlib, json, os, shutil, sys, contextlib, io, glob
tools, t26, t27, tmp = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
sys.path.insert(0, tools)
import fl26world as W, leaguebuilder as LB
out = {}
cfgs = W.QCONFIGS + [W.Q1_CONFIG]
out["rooms"] = [[sorted(W.qual_room(c).items()), [(W.q_room(c, r), W.q_size(c, r)) for r in c]] for c in cfgs]
out["down"] = [[W.q_down(c, r), W.q_up(c, r)] for c in cfgs for r in c]
out["text"] = [W.rounds_text(c) for c in cfgs]
out["numbers"] = sorted((k, v) for k, v in W.QROUND_NUMBER.items() if k)
cases = [[], [(900, 1, 10, 0)], [(900 + i, 1, 10, 0) for i in range(40)],
         [(900 + i, 1 + i % 3, (10, 11, 12)[i % 3], 0) for i in range(60)],
         [(900 + i, 1, 0, 0) for i in range(10)] + [(950 + i, 2, 1, 0) for i in range(10)],
         [(900 + i, 1, 10, 0) for i in range(40)] + [(1000 + i, 2, 12, 0) for i in range(16)]]
x = [(1100 + i, 1, 10, 0) for i in range(5)]
for k, own in enumerate(cases):
    rank = {900 + i: 30 + i for i in range(60)} if k == 3 else None
    for uecl in (True, False):
        u, over = W.uefa_places(own, uecl=uecl, rank=rank)
        out["places %d %s" % (k, uecl)] = [u, sorted(over.items()), W.pick_rounds(u, uecl), W.pick_rounds_q1(u, uecl),
                                           sorted(W.qual_places(u).items()), sorted(W.direct_room(u).items()),
                                           sorted(W.europe_count([e[2] for e in u or W.SHIPPED_ACCESS], uecl).items())]
    u, over = W.uefa_places(own, rank=rank, extra=x, rounds=W.Q1_CONFIG)
    out["places A %d" % k] = [u, sorted(over.items()), W.pick_rounds_q1(u)]
for f in sorted(glob.glob(os.path.join(tools, "testdata", "*", "*.json"))):
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            pl = LB.plan(LB.load_recipe(f), t26)
    except Exception as e:
        out[os.path.basename(f)] = "plan: %s" % e
        continue
    u, over = W.uefa_places(LB.all_places(pl), pl.get("game_replace") or [], bool(pl.get("uecl")), LB.place_rank(pl))
    out[os.path.basename(f)] = [LB.qual_rounds(pl), u, sorted(over.items()), LB.europe_rounds(pl, t26, None)]
for tag, base, rounds in (("26", t26, W.QCONFIGS[0]), ("27 A", t27, W.Q1_CONFIG)):
    if not base:
        continue
    w = os.path.join(tmp, "w" + tag[-1])
    db = os.path.join(w, "common", "etc", "pesdb")
    shutil.copytree(base, db)
    said = []
    with contextlib.redirect_stdout(io.StringIO()):
        _c, q = LB.europe(w, db, log=said.append, uecl=True, rounds=rounds)
    out["qlines " + tag] = q
    out["said " + tag] = [s for s in said if "qualifying" in s]
    # #154 renamed the Conference League (mkuecl.NAME); the unpacked table is otherwise compared byte for byte
    out["regs " + tag] = hashlib.md5(__import__("pesdb").wesys_unpack(open(os.path.join(db, "CompetitionRegulation.bin"), "rb").read()).replace(
        b"UEFA Conference League", b"FL Conference League" + bytes(2))).hexdigest()
print(json.dumps(out, sort_keys=True, default=str))
'''

fails = []


def ok(what, cond):
    print("%s  %s" % ("ok  " if cond else "FAIL", what))
    if not cond:
        fails.append(what)


def run_dump(tools):
    tmp = tempfile.mkdtemp()
    try:
        r = subprocess.run([sys.executable, "-c", DUMP, tools, T26 or "", T27 or "", tmp], capture_output=True,
                           text=True, cwd=tools, timeout=1800)
        if r.returncode:
            raise SystemExit("the dump failed in %s:\n%s" % (tools, r.stderr[-3000:]))
        return json.loads(r.stdout.strip().splitlines()[-1])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


sys.path.insert(0, HERE)
import fl26world as W
import leaguebuilder as LB
import mkeuropo as E
import mkleague as M

# --- fl26world: the rounds -------------------------------------------------------------------------
C = W.C_CONFIG
print("Prijedlog C: %s" % W.rounds_text(C))
ok("C_CONFIG: UCL Q1-PO, UEL Q1-PO, UECL Q2-PO (11 rounds)", len(C) == 11 and (2, 3) not in C and W.c_world(C))
ok("not C: Prijedlog A, the August sets, none", not W.c_world(W.Q1_CONFIG) and not any(W.c_world(c) for c in W.QCONFIGS)
   and not W.c_world(None))
SIZE = {(0, 0): 16, (0, 1): 16, (0, 2): 32, (0, 3): 32, (1, 0): 32, (1, 1): 32, (1, 2): 16, (1, 3): 16,
        (2, 0): 32, (2, 1): 32, (2, 2): 32}
ok("sizes as mato's table: %s" % [(r, W.q_size(C, r)) for r in C], all(W.q_size(C, r) == SIZE[r] for r in C))
ROOM = {(0, 0): 8, (0, 1): 0, (0, 2): 16, (0, 3): 32, (1, 0): 8, (1, 1): 8, (1, 2): 8, (1, 3): 16,
        (2, 0): 0, (2, 1): 8, (2, 2): 8}
ok("new clubs per round: %s" % [(r, W.q_room(C, r)) for r in C], all(W.q_room(C, r) == ROOM[r] for r in C))
ok("new qualifying clubs 56 / 40 / 16, 112 in all (A 88)",
   W.qual_room(C) == {W.UCLQ: 56, W.UELQ: 40, W.UECLQ: 16} and sum(W.qual_room(C).values()) == 112)
WAY = {(0, 3): ((0, 2), (2, 2)), (0, 2): ((0, 1), (1, 1)), (0, 1): ((0, 0), (1, 0)), (0, 0): (None, "phase"),
       (1, 3): ((1, 2), (2, 2)), (1, 2): ((1, 1), (2, 1)), (1, 1): ((1, 0), (2, 0)), (1, 0): (None, "phase"),
       (2, 2): ((2, 1), None), (2, 1): ((2, 0), None), (2, 0): (None, None)}
for r in C:
    ok("%s: winners %s, losers %s" % (r, W.q_up(C, r), W.q_down(C, r)), (W.q_up(C, r), W.q_down(C, r)) == WAY[r])
for r in C:
    fed = sum(W.q_size(C, j) // 2 for j in C if j != r and r in (W.q_up(C, j), W.q_down(C, j)))
    ok("round %s: %d new + %d sent = %d" % (r, W.q_room(C, r), fed, W.q_size(C, r)), W.q_room(C, r) + fed == W.q_size(C, r))
ok("direct entrants 28 / 12 / 4 (listed or not), 28 / 20 / 20 without C",
   W.direct_room([], C) == {0: 28, 1: 12, 2: 4} and W.direct_room(W.SHIPPED_ACCESS, C) == {0: 28, 1: 12, 2: 4}
   and W.direct_room(W.SHIPPED_ACCESS) == {0: 28, 1: 20, 2: 20}
   and W.direct_room(W.SHIPPED_ACCESS, W.Q1_CONFIG) == {0: 28, 1: 20, 2: 20})
lp = {c: W.direct_room([], C)[c] for c in range(3)}
lp[0] += W.q_size(C, (0, 0)) // 2
lp[1] += W.q_size(C, (0, 0)) // 2 + W.q_size(C, (1, 0)) // 2
lp[2] += W.q_size(C, (1, 0)) // 2 + W.q_size(C, (2, 0)) // 2
ok("league phases 36 / 36 / 36 with the play-offs' winners and losers (%s)" % lp, lp == {0: 36, 1: 36, 2: 36})
ok("qround line round 0 for the play-offs of 32, the rest as before",
   W.QROUND_NUMBER == {0: 0, 1: 3, 2: 2, 3: 1})

# --- the places ------------------------------------------------------------------------------------
sh = list(W.SHIPPED_ACCESS)
have = W.qual_places(sh, C)
ok("the shipped list in C: 16 / 24 / 32 for the rounds (%s)" % sorted(have.items()),
   have == {W.UCLQ: 16, W.UELQ: 24, W.UECLQ: 32})
cp, moved = W.c_places(sh)
ecl = [e for e in sh if e[2] == W.UECLQ]
ok("c_places: the first 16 Conference League qualifying places become the Europa League's, after its own",
   moved == ecl[:16] and [e for e in cp if e[2] == W.UELQ][-16:] == [(e[0], e[1], W.UELQ, e[3]) for e in moved]
   and W.qual_places(cp, C) == {W.UCLQ: 16, W.UELQ: 40, W.UECLQ: 16} and len(cp) == len(sh))
ok("c_places: the competitions' order kept (0, 10, 1, 11, 2, 12)",
   [e[2] for e in cp] == sorted((e[2] for e in cp), key=[0, 10, 1, 11, 2, 12].index))
ok("c_places: nothing to move when the Europa League has its 40", W.c_places(cp) == (cp, []))
need = [(900 + i, 1, W.UCLQ, 0) for i in range(40)]
u, over = W.uefa_places(need, rounds=C)
ok("uefa_places with C: 56 / 40 / 16, no notes (%s)" % sorted(over.items()),
   W.qual_places(u, C) == {W.UCLQ: 56, W.UELQ: 40, W.UECLQ: 16} and not over)
ok("pick_rounds_c: 56 Champions League qualifying places and the shipped rest fill it", W.pick_rounds_c(u) == C)
u1, _ = W.uefa_places(need[W.C_TOPUP:], rounds=C)
ok("pick_rounds_c: up to C_TOPUP (%d) Champions League places fewer -> still C (the big five top them up)" % W.C_TOPUP, W.pick_rounds_c(u1) == C)
u1, _ = W.uefa_places(need[W.C_TOPUP + 1:], rounds=C)
ok("pick_rounds_c: one more fewer -> None", W.pick_rounds_c(u1) is None)
ok("pick_rounds_c: without the Conference League -> None", W.pick_rounds_c(u, False) is None)
few = [e for e in sh if e[2] != W.UECLQ][:-1]
ok("pick_rounds_c: a list short of the Europa League's 40 -> None",
   W.pick_rounds_c(W.c_places(few + need)[0]) is None)
x = [(1100 + i, 1, W.UCLQ, 0) for i in range(5)]
u, _ = W.uefa_places(need, extra=x, rounds=C)
cl = [e for e in u if e[2] == W.UCLQ]
ok("extra: the champions go last in the Champions League qualifying", cl[-5:] == x)
mine = [(950 + i, 3, W.UECLQ, 0) for i in range(4)]
u, over = W.uefa_places(need + mine, rounds=C)
ok("a world's own Conference League places, the first in the list, move up and count as the Europa League's (%s)"
   % sorted(over.items()), all((e[0], e[1], W.UELQ, e[3]) in u for e in mine) and not over)
u, over = W.uefa_places([(900 + i, 1, W.UCLQ, 0) for i in range(50)], rounds=C)
ok("the notes count C's room: 50 own Champions League qualifying places fit its 56 (%s)"
   % sorted(over.items()), W.UCLQ not in over)
u, over = W.uefa_places([(900 + i, 1, W.UCLQ, 0) for i in range(60)], rounds=C)
ok("60 own Champions League qualifying places: 4 past C's 56 (%s)" % sorted(over.items()), over.get(W.UCLQ) == (60, 56))
u, _ = W.uefa_places(need, rank={900 + i: i for i in range(40)}, rounds=C)
blk = [e for e in u if e[2] == W.UELQ]
ok("with a ranking: the Europa League qualifying block in rank order",
   [W.place_league(e) for e in blk] == [W.place_league(e) for e in
                                         sorted(blk, key=lambda e: {900 + i: i for i in range(40)}.get(W.place_league(e), W.UNRANKED))])

# --- mkeuropo / leaguebuilder.europe: the rounds in FL 2027's tables ------------------------------
if not T27:
    print("SKIPPED the FL 2027 tables part: no tables27 (--tables27)")
else:
    tmp = tempfile.mkdtemp()
    try:
        db = os.path.join(tmp, "common", "etc", "pesdb")
        shutil.copytree(T27, db)
        said = []
        _c, qlines = LB.europe(tmp, db, log=said.append, uecl=True, rounds=C)
        print("  %s" % qlines)
        ok("C world: 10 qround lines, the play-offs of 32 as `qround 11 0` and `qround 12 0`, not the Champions "
           "League's (reg 2)", len(qlines) == 10 and sorted((c, n) for c, n, _r in qlines if n == 0) == [(11, 0), (12, 0)])
        ok("both first rounds in July (round 1): 10 and 11",
           sorted(c for c, n, _r in qlines if n == 1) == [10, 11])
        regs = M.load(db, "CompetitionRegulation.bin")
        rows = [regs[i * M.REG:(i + 1) * M.REG] for i in range(len(regs) // M.REG)]
        stage = {v: k for k, v in W.QROUND_NUMBER.items()}
        cid = {}
        for c, n, reg in qlines:
            mine = [r for r in rows if E.rid(r) & 0x3ff == reg]
            ties = W.q_size(C, (c - 10, stage[n])) // 2
            ids = sorted(E.rid(r) for r in mine)
            cid[(c, n)] = {M.reg_cid(r) for r in mine}
            ok("qround %d %d %d: %d rows, %d clubs, %d ties on every row, groups 0..%d, ids reg + k*1024" %
               (c, n, reg, len(mine), 2 * ties, ties, ties - 1),
               len(mine) == ties + 1 and all(r[M.R_TEAMS] & 0x3f == 2 * ties and r[0x10] == ties for r in mine)
               and sorted(r[E.R_GROUP] for r in mine) == list(range(ties)) + [255]
               and ids == [reg + k * 1024 for k in range(ties + 1)]
               and all(int.from_bytes(r[6:8], "little") == reg for r in mine if r[E.R_GROUP] != 255)
               and len(cid[(c, n)]) == 1)
        ok("the play-offs of 32 in their competitions: the Europa League's (%d) and the Conference League's, as "
           "their other rounds" % E.UEL_CID, cid[(11, 0)] == {E.UEL_CID} and cid[(12, 0)] == cid[(12, 2)]
           and cid[(12, 0)] != {E.UEL_CID})
        ok("188 and 189 kept (February's)", any(E.rid(r) == 188 for r in rows) and any(E.rid(r) == 189 for r in rows))
        ok("the build log names the play-offs of 32 and the July rounds",
           any("play-off of 32" in s and "first, July" in s for s in said))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

# --- leaguebuilder: the choice of rounds -----------------------------------------------------------
if not (T27 and os.path.exists(PLAN27)):
    print("SKIPPED the FL 2027 plan part: no %s" % PLAN27)
else:
    pl = json.load(open(PLAN27, encoding="utf-8"))
    real = LB.is_fl27
    try:
        LB.is_fl27 = lambda g: True
        rounds, extra = LB.europe_rounds(pl, T27, "an FL 2027 game")
        LB.is_fl27 = lambda g: False
        r26, x26 = LB.europe_rounds(pl, T27, "an FL 2026 game")
    finally:
        LB.is_fl27 = real
    ok("FL 2026 game: the August rounds, nothing added", r26 == LB.qual_rounds(pl) and x26 == [])
    ok("FL 2027 world %s: Prijedlog C, %d champions added" % (pl.get("world"), len(extra)), rounds == C and extra)
    u, over = W.uefa_places(LB.all_places(pl), pl.get("game_replace") or [], True, LB.place_rank(pl),
                            pl.get("access_alias"), extra=extra, rounds=rounds)
    have = W.qual_places(u, C)
    ok("the world's places fill C: %s, notes %s" % (sorted(have.items()), sorted(over.items())),
       have[W.UCLQ] >= 56 and have[W.UELQ] >= 40 and have[W.UECLQ] >= 16)
    n = {c: sum(1 for e in u if e[2] == c) for c in (0, 1, 2)}
    print("  direct places listed %s for 28 / 12 / 4: the rest into the rounds" % n)
    small = dict(pl, leagues=[p for p in pl["leagues"] if not p.get("europe")][:3], game_europe=[],
                 association_access=[], uefa_seed=[])
    LB.is_fl27 = lambda g: True
    try:
        rs, xs = LB.europe_rounds(small, T27, "an FL 2027 game")
    finally:
        LB.is_fl27 = real
    ok("FL 2027 world with too few places: neither C nor A (%s)" % W.rounds_text(rs),
       not W.c_world(rs) and (0, 3) not in rs and xs == [])

# --- FL 2026 and Prijedlog A: the same as before Prijedlog C ---------------------------------------
if not T26:
    print("SKIPPED the comparison with %s: no FL 2026 tables (--tables)" % BASE)
else:
    try:
        tar = subprocess.run(["git", "archive", BASE, "tools"], cwd=os.path.dirname(HERE),
                             capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        tar = None
    if tar is None:
        print("SKIPPED the comparison: no git history (%s)" % BASE)
    else:
        old_root = tempfile.mkdtemp()
        try:
            tarfile.open(fileobj=io.BytesIO(tar)).extractall(old_root)
            old = run_dump(os.path.join(old_root, "tools"))
            new = run_dump(HERE)
            added = sorted(k for k in set(new) - set(old) if k.endswith(".json"))
            for k in added:
                new.pop(k)
            for k in sorted(set(old) | set(new)):
                if old.get(k) != new.get(k):
                    print("  differs: %s\n    before: %.300s\n    now:    %.300s" % (k, old.get(k), new.get(k)))
            ok("FL 2026 and Prijedlog A: %d dump entries the same as at %s (rooms, ways, uefa lines and notes, "
               "the testdata plans, the rounds' table rows: md5 %s / %s)" % (len(new), BASE, new.get("regs 26"),
                                                                          new.get("regs 27 A")), old == new)
        finally:
            shutil.rmtree(old_root, ignore_errors=True)

print("%d failed" % len(fails) if fails else "all checks passed")
sys.exit(1 if fails else 0)
