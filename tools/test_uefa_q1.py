r"""FL 2027's first qualifying round in July (mato 06.11., notes/uefa-q1-srpanj.md "Prijedlog A"),
the League Builder's side: fl26world's rounds and rooms, mkeuropo's rounds of 32, leaguebuilder's
champions of the European leagues with no place (q1_tail) and its choice of rounds. FL 2026 must
not change at all: the same dump (rooms, rounds, the uefa lines and their notes, the
qualifying rounds' table rows) is made with the tools as they were before (commit BASE, from git)
and compared.

    python tools/test_uefa_q1.py [--tables <FL26 tables folder>] [--tables27 <FL27 tables folder>]
                                 [--plan27 <an FL27 world's leaguebuilder-plan.json>]

The tables default to Mod Studio's (%APPDATA%/FL26ModStudio/tables, tables27) and the plan to the
Megapack test world's on E:\FL\FL27 (read only); a part whose files are missing says so and is skipped.
The native side (the DLL) is tools/test_uefa_q1_native.py.
"""
import hashlib, io, json, os, shutil, subprocess, sys, tarfile, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "b1e6884"            # limits-all, the branch point: no first qualifying round yet
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

# --- the dump: run by this script in a child process, with sys.path at a tools folder ----------
DUMP = r'''
import hashlib, json, os, shutil, sys, contextlib, io
tools, base, tmp = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, tools)
import fl26world as W, leaguebuilder as LB
out = {}
out["rooms"] = [[sorted(W.qual_room(c).items()), [W.q_room(c, r) for r in c]] for c in W.QCONFIGS]
out["text"] = [W.rounds_text(c) for c in W.QCONFIGS]
out["down"] = [[W.q_down(c, r), W.q_up(c, r)] for c in W.QCONFIGS for r in c]
# the uefa lines for a range of worlds: none, a few, many new champions in the qualifying
cases = [[], [(900, 1, 10, 0)], [(900 + i, 1, 10, 0) for i in range(40)],
         [(900 + i, 1 + i % 3, (10, 11, 12)[i % 3], 0) for i in range(60)],
         [(900 + i, 1, 0, 0) for i in range(10)] + [(950 + i, 2, 1, 0) for i in range(10)]]
for k, own in enumerate(cases):
    for uecl in (True, False):
        u, over = W.uefa_places(own, uecl=uecl, rank={900 + i: 30 + i for i in range(60)} if k == 3 else None)
        out["places %d %s" % (k, uecl)] = [u, sorted(over.items()), W.pick_rounds(u, uecl)]
# the testdata recipes' plans: their rounds and uefa lines
import glob
for f in sorted(glob.glob(os.path.join(tools, "testdata", "*", "*.json"))):
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            pl = LB.plan(LB.load_recipe(f), base)
    except Exception as e:
        out[os.path.basename(f)] = "plan: %s" % e
        continue
    u, over = W.uefa_places(LB.all_places(pl), pl.get("game_replace") or [], bool(pl.get("uecl")), LB.place_rank(pl))
    out[os.path.basename(f)] = [LB.qual_rounds(pl), u, sorted(over.items())]
    if hasattr(LB, "europe_rounds"):
        # FL 2026 (no game, or a game that is not FL 2027): the rounds as ever, nothing added
        r, x = LB.europe_rounds(pl, base, None)
        assert (r, x) == (LB.qual_rounds(pl), []), f
        real = LB.is_fl27
        LB.is_fl27 = lambda g: False
        try:
            assert LB.europe_rounds(pl, base, "an FL 2026 game") == (LB.qual_rounds(pl), []), f
        finally:
            LB.is_fl27 = real
# the qualifying rounds' table rows, all nine rounds (FL 2026's most), in a copy of the tables
w = os.path.join(tmp, "w")
shutil.copytree(base, os.path.join(w, "common", "etc", "pesdb"))
db = os.path.join(w, "common", "etc", "pesdb")
with contextlib.redirect_stdout(io.StringIO()):
    _c, q = LB.europe(w, db, log=lambda *a: None, uecl=True, rounds=W.QCONFIGS[0])
out["qlines"] = q
# #154 renamed the Conference League (mkuecl.NAME); the unpacked table is otherwise compared byte for byte
out["regs"] = hashlib.md5(__import__("pesdb").wesys_unpack(open(os.path.join(w, "common", "etc", "pesdb", "CompetitionRegulation.bin"), "rb").read()).replace(
    b"UEFA Conference League", b"FL Conference League" + bytes(2))).hexdigest()
print(json.dumps(out, sort_keys=True, default=str))
'''

fails = []


def ok(what, cond):
    print("%s  %s" % ("ok  " if cond else "FAIL", what))
    if not cond:
        fails.append(what)


def run_dump(tools, base):
    tmp = tempfile.mkdtemp()
    try:
        r = subprocess.run([sys.executable, "-c", DUMP, tools, base, tmp], capture_output=True, text=True,
                           cwd=tools, timeout=1200)
        if r.returncode:
            raise SystemExit("the dump failed in %s:\n%s" % (tools, r.stderr[-3000:]))
        return json.loads(r.stdout.strip().splitlines()[-1])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


sys.path.insert(0, HERE)
import fl26world as W
import leaguebuilder as LB
import mkleague as M
import mkeuropo as E

# --- fl26world: the July rounds ----------------------------------------------------------------
q1 = W.Q1_CONFIG
ok("Q1: 56 / 0 / 32 new qualifying clubs, 88 in all",
   W.qual_room(q1) == {W.UCLQ: 56, W.UELQ: 0, W.UECLQ: 32} and sum(W.qual_room(q1).values()) == 88)
ok("Q1 rooms: CL play-off 8, Q3 0, Q2 16, Q1 32; EL none; ECL Q1 32 only",
   [W.q_room(q1, r) for r in q1] == [8, 0, 16, 32, 0, 0, 0, 0, 0, 32])
ok("rounds of 32: both first rounds and the second rounds after them, the rest 16",
   {r for r in q1 if W.q_size(q1, r) == 32} == {(0, 2), (0, 3), (2, 2), (2, 3)})
ok("the Champions League Q1's losers go to the Conference League Q2, its winners to the CL Q2",
   W.q_down(q1, (0, 3)) == (2, 2) and W.q_up(q1, (0, 3)) == (0, 2))
ok("CL Q2 losers -> EL Q3, CL Q3 losers -> EL play-off, EL Q3 losers -> ECL play-off",
   W.q_down(q1, (0, 2)) == (1, 1) and W.q_down(q1, (0, 1)) == (1, 0) and W.q_down(q1, (1, 1)) == (2, 0))
ok("ECL Q1 winners -> ECL Q2, losers out", W.q_up(q1, (2, 3)) == (2, 2) and W.q_down(q1, (2, 3)) is None)
# every round's clubs: new ones plus those sent to it make its size
for r in q1:
    fed = sum(W.q_size(q1, j) // 2 for j in q1 if j != r and r in (W.q_up(q1, j), W.q_down(q1, j)))
    ok("round %s: %d new + %d sent = %d" % (r, W.q_room(q1, r), fed, W.q_size(q1, r)),
       W.q_room(q1, r) + fed == W.q_size(q1, r))
ok("rounds_text names the first qualifying round",
   W.rounds_text(q1).startswith("Champions League: first qualifying round, second qualifying round"))
ok("qround line round 1 for stage 3", W.QROUND_NUMBER[3] == 1)
need = [(900 + i, 1, W.UCLQ, 0) for i in range(56 - 16)] + [(1000 + i, 2, W.UECLQ, 0) for i in range(16)]
u, _ = W.uefa_places(need)
ok("pick_rounds_q1: 56 Champions League and 32 Europa/Conference League qualifying places fill it",
   W.pick_rounds_q1(u) == q1)
u, _ = W.uefa_places(need[1:])
ok("pick_rounds_q1: one Champions League place fewer -> None (the August rounds)", W.pick_rounds_q1(u) is None)
ok("pick_rounds_q1: without the Conference League -> None", W.pick_rounds_q1(W.uefa_places(need)[0], False) is None)
x = [(1100 + i, 1, W.UCLQ, 0) for i in range(5)]
u, _ = W.uefa_places(need, extra=x, rounds=q1)
cl = [e for e in u if e[2] == W.UCLQ]
ok("extra: the champions go last in the Champions League qualifying, nothing else moves",
   cl[-5:] == x and [e for e in u if e not in x] == W.uefa_places(need)[0])
_u, over = W.uefa_places(need, extra=x, rounds=q1)
_u, over8 = W.uefa_places(need, extra=x)
ok("the room the notes count: 45 own Champions League qualifying places fit the July rounds' 56, "
   "not the August rounds' 32 (%s / %s)" % (over.get(W.UCLQ), over8.get(W.UCLQ)),
   W.UCLQ not in over and over8.get(W.UCLQ) == (45, 32))
many = need + [(1200 + i, 3, W.UELQ, 0) for i in range(20)]
_u, over = W.uefa_places(many, rounds=q1)
ok("the Europa League's qualifying places count against the Conference League Q1's 32 (%s)" % sorted(over.items()),
   over.get(W.UECLQ) == (36, 32) and W.UELQ not in over)

# --- mkeuropo / leaguebuilder.europe: the rounds of 32 in FL 2027's tables ------------------------
if not T27:
    print("SKIPPED the FL 2027 tables part: no tables27 (--tables27)")
else:
    tmp = tempfile.mkdtemp()
    try:
        db = os.path.join(tmp, "common", "etc", "pesdb")
        shutil.copytree(T27, db)
        said = []
        _c, qlines = LB.europe(tmp, db, log=said.append, uecl=True, rounds=q1)
        ok("Q1 world: 7 qround lines, rounds 1 for both first rounds (%s)" % qlines,
           len(qlines) == 7 and sorted((c, n) for c, n, _r in qlines if n == 1) == [(10, 1), (12, 1)]
           and not any(c == 11 and n == 2 for c, n, _r in qlines))
        regs = M.load(db, "CompetitionRegulation.bin")
        rows = [regs[i * M.REG:(i + 1) * M.REG] for i in range(len(regs) // M.REG)]
        for c, n, reg in qlines:
            mine = [r for r in rows if E.rid(r) & 0x3ff == reg]
            big = n == 1 or (n == 2 and c in (10, 12))
            ties = 16 if big else 8
            ids = sorted(E.rid(r) for r in mine)
            ok("qround %d %d %d: %d rows, %d clubs, %d ties on every row, groups 0..%d, ids reg + k*1024" %
               (c, n, reg, len(mine), 2 * ties, ties, ties - 1),
               len(mine) == ties + 1 and all(r[M.R_TEAMS] & 0x3f == 2 * ties and r[0x10] == ties for r in mine)
               and sorted(r[E.R_GROUP] for r in mine) == list(range(ties)) + [255]
               and ids == [reg + k * 1024 for k in range(ties + 1)]
               and all(int.from_bytes(r[6:8], "little") == reg for r in mine if r[E.R_GROUP] != 255)
               and len({M.reg_cid(r) for r in mine}) == 1)
        ok("the build log names the July rounds", any("first, July" in s for s in said))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

# --- leaguebuilder: the champions tail and the choice of rounds ------------------------------------
if not (T27 and os.path.exists(PLAN27)):
    print("SKIPPED the FL 2027 plan part: no %s" % PLAN27)
else:
    import mkflags, uefakey
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
    # Prijedlog C (fl26world.C_CONFIG, tools/test_uefa_c.py) comes first when the places fill it
    ok("FL 2027 world %s: the July first qualifying round (%s), %d champions added"
       % (pl.get("world"), "Prijedlog C" if W.c_world(rounds) else "Prijedlog A", len(extra)),
       rounds in (q1, W.C_CONFIG) and extra)
    cty = mkflags.countries(mkflags.table("Country", [T27]))
    country = {p["rid"]: mkflags.title((cty.get(p.get("country")) or ("", None))[0] or "") for p in pl["leagues"]}
    names = [country[e[0]] for e in extra]
    plain, _o = W.uefa_places(LB.all_places(pl), pl.get("game_replace") or [], True, LB.place_rank(pl))
    placed = {country.get(W.place_league(e), W.ACCESS_COUNTRY.get(W.place_league(e))) for e in plain}
    ok("the champions: one per country, UEFA's, none with a place already, in association order",
       len(set(names)) == len(names) and all(n in uefakey.DEFAULT_ORDER for n in names)
       and not set(names) & placed and [uefakey.default_rank(n) for n in names] ==
       sorted(uefakey.default_rank(n) for n in names) and "Russia" not in names)
    ok("the champions are top divisions, not exhibitions",
       all(not p.get("above") and not p.get("exhibition") for p in pl["leagues"] if p["rid"] in {e[0] for e in extra}))
    u, over = W.uefa_places(LB.all_places(pl), pl.get("game_replace") or [], True, LB.place_rank(pl),
                            extra=extra, rounds=rounds)
    have, need = W.qual_places(u, rounds), W.qual_room(rounds)
    ok("the world's places fill the July rounds: %s for %s" % (sorted(have.items()), sorted(need.items())),
       have[W.UCLQ] >= 56 and (all(have[q] >= need[q] for q in need) if W.c_world(rounds)
                               else have[W.UELQ] + have[W.UECLQ] >= 32))
    # a world with few places keeps the August rounds even in FL 2027
    small = dict(pl, leagues=[p for p in pl["leagues"] if not p.get("europe")][:3], game_europe=[],
                 association_access=[], uefa_seed=[])
    LB.is_fl27 = lambda g: True
    try:
        rs, xs = LB.europe_rounds(small, T27, "an FL 2027 game")
    finally:
        LB.is_fl27 = real
    ok("FL 2027 world with too few places: the August rounds, nothing added", (0, 3) not in rs and xs == [])

# --- FL 2026: the same as before the first qualifying round ----------------------------------------
if not T26:
    print("SKIPPED the FL 2026 comparison: no FL 2026 tables (--tables)")
else:
    try:
        tar = subprocess.run(["git", "archive", BASE, "tools"], cwd=os.path.dirname(HERE),
                             capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        tar = None
    if tar is None:
        print("SKIPPED the FL 2026 comparison: no git history (%s)" % BASE)
    else:
        old_root = tempfile.mkdtemp()
        try:
            tarfile.open(fileobj=io.BytesIO(tar)).extractall(old_root)
            old = run_dump(os.path.join(old_root, "tools"), T26)
            new = run_dump(HERE, T26)
            # a testdata recipe added since BASE (another request's) has no plan there to compare with
            added = sorted(k for k in set(new) - set(old) if k.endswith(".json"))
            if added:
                print("  new since %s, not compared: %s" % (BASE, ", ".join(added)))
            for k in added:
                new.pop(k)
            for k in sorted(set(old) | set(new)):
                if old.get(k) != new.get(k):
                    print("  differs: %s\n    before: %.300s\n    now:    %.300s" % (k, old.get(k), new.get(k)))
            ok("FL 2026: %d dump entries the same as at %s (rooms, rounds, uefa lines, the testdata plans, "
               "the qualifying rounds' rows, md5 %s)" % (len(new), BASE, new.get("regs")), old == new)
        finally:
            shutil.rmtree(old_root, ignore_errors=True)

print("%d failed" % len(fails) if fails else "all ok")
sys.exit(1 if fails else 0)
