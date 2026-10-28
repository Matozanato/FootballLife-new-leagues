r"""python tools/test_futve_world.py [--game <folder>] [--keep]

tools/futve_world.py against the real world of a game: both staging worlds are built in a temporary
folder (nothing of the game is written) and checked.

  - phase 1: competition 134, master 259 (group stage, 8 clubs, 2 groups), rows 1283 and 2307,
    knockout 261 copied from the Europa League's row with 4 clubs; its line names gdays but no
    adv= or kolike=;
  - phase 2: the same groups, knockout 261 with 2 clubs (the Belgium Super Cup's row) and its line
    with adv=1 and kolike=<its regulation>;
  - the Clausura cup's line, its rows and every other competition/regulation/entry row of the
    world are unchanged;
  - two runs give the same three tables and the same world file (idempotent).

Needs a game with the Liga FUTVE world (FL26_DIR or --game); without one it says SKIPPED and exits 0.
"""
import argparse, hashlib, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mkleague as M

REPO = os.path.dirname(HERE)
APERTURA = "Liga FUTVE Apertura Playoffs"
CLAUSURA = "Liga FUTVE Clausura Playoffs"
N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def rows(b, size):
    return [b[i:i + size] for i in range(0, len(b), size)]


def rid(r):
    return int.from_bytes(r[M.R_ID:M.R_ID + 2], "little")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def line_of(path, name):
    for l in open(path, encoding="utf-8", errors="replace").read().splitlines():
        if l.strip().startswith("ccup ") and l.rstrip().endswith("name=" + name):
            return l.strip()
    return None


def run(game, out):
    r = subprocess.run([sys.executable, os.path.join(HERE, "futve_world.py"), "--game", game,
                        "--out", out], capture_output=True, text=True)
    assert r.returncode == 0, "futve_world.py failed:\n%s\n%s" % (r.stdout, r.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default=os.environ.get("FL26_DIR"))
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()
    game = a.game
    base = os.path.join(game or "", "SiderAddons", "livecpk", "_FL26MyWorld", "common", "etc", "pesdb")
    world = os.path.join(game or "", "SiderAddons", "modules", "fl26world.txt")
    if not game or not os.path.isdir(base) or not os.path.isfile(world):
        print("SKIPPED: no game world (set FL26_DIR or pass --game)")
        return 0
    tmp_root = os.path.join(REPO, "out", "tmp")
    os.makedirs(tmp_root, exist_ok=True)
    tmp = tempfile.mkdtemp(dir=tmp_root)
    try:
        out1, out2 = os.path.join(tmp, "one"), os.path.join(tmp, "two")
        run(game, out1)
        run(game, out2)
        live = {n: M.load(base, n) for n in ("Competition.bin", "CompetitionRegulation.bin",
                                             "CompetitionEntry.bin")}
        live_c = rows(live["Competition.bin"], M.COMP)
        live_r = rows(live["CompetitionRegulation.bin"], M.REG)
        live_e = rows(live["CompetitionEntry.bin"], M.ENT)
        other_r = {bytes(r) for r in live_r if r[M.R_CID] != 134}
        other_e = {bytes(e) for e in live_e if e[M.E_CID] != 134}
        other_c = {bytes(c) for c in live_c if c[M.CID_OFF] != 134}
        clausula_line = line_of(world, CLAUSURA)
        for phase in (1, 2):
            d = os.path.join(out1, "world-phase%d" % phase)
            C, R, E = (M.load(os.path.join(d, "common", "etc", "pesdb"), n) for n in
                       ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin"))
            Cr, Rr, Er = rows(C, M.COMP), rows(R, M.REG), rows(E, M.ENT)
            ok("phase %d: competition 134 is there, coded FL_011_APO" % phase,
               len([c for c in Cr if c[M.CID_OFF] == 134]) == 1
               and M.find_code(C, "FL_011_APO") is not None)
            got = {rid(r): r for r in Rr}
            ok("phase %d: master 259 is a group stage of 8 clubs and 2 groups" % phase,
               got[259][M.R_CID] == 134 and got[259][M.R_TYPE] == 2
               and got[259][M.R_TEAMS] & 0x3f == 8 and got[259][0x10] & 0x1f == 2)
            for rep in (1283, 2307):
                ok("phase %d: group row %d is this cup's" % (phase, rep),
                   rep in got and got[rep][M.R_CID] == 134 and got[rep][M.R_TYPE] == 2)
            nko = 4 if phase == 1 else 2
            ok("phase %d: knockout 261 has %d clubs" % (phase, nko),
               261 in got and got[261][M.R_CID] == 134 and got[261][M.R_TYPE] == 3
               and got[261][M.R_TEAMS] & 0x3f == nko)
            line = line_of(os.path.join(d, "fl26world.txt"), APERTURA)
            ok("phase %d: its world line is a group cup with the fixed entry order and gdays" % phase,
               line is not None and "groups=2" in line and "gdays=3,5,7,9,11,13" in line
               and "entry=191:1,191:4,191:5,191:8,191:2,191:3,191:6,191:7" in line)
            if phase == 1:
                ok("phase 1: no adv= or kolike=", "adv=" not in line and "kolike=" not in line)
            else:
                ok("phase 2: adv=1 and kolike=128", "adv=1" in line and "kolike=128" in line)
            ok("phase %d: the Clausura cup's line is untouched" % phase,
               line_of(os.path.join(d, "fl26world.txt"), CLAUSURA) == clausula_line)
            ok("phase %d: every regulation of another competition is untouched" % phase,
               other_r <= {bytes(r) for r in Rr})
            ok("phase %d: every entry of another competition is untouched" % phase,
               other_e <= {bytes(e) for e in Er})
            ok("phase %d: every other competition row is untouched" % phase, other_c <= {bytes(c) for c in Cr})
            ok("phase %d: one competition was replaced, the rest kept" % phase,
               len(Cr) == len(live_c))
        for n in ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin"):
            for phase in (1, 2):
                p1 = os.path.join(out1, "world-phase%d" % phase, "common", "etc", "pesdb", n)
                p2 = os.path.join(out2, "world-phase%d" % phase, "common", "etc", "pesdb", n)
                ok("phase %d: two runs give the same %s" % (phase, n), sha(p1) == sha(p2))
        for phase in (1, 2):
            ok("phase %d: two runs give the same world file" % phase,
               sha(os.path.join(out1, "world-phase%d" % phase, "fl26world.txt"))
               == sha(os.path.join(out2, "world-phase%d" % phase, "fl26world.txt")))
        print("ok")
        return 0
    finally:
        if a.keep:
            print("kept: %s" % tmp)
        else:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
