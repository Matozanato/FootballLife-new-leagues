r"""python tools/test_futve_fixture.py [--game <folder>] [--keep]

tools/futve_fixture.py against a copy of the real world's Player.bin and PlayerAssignment.bin
(nothing of the game is written): the fixture sets the 25 stats of the world's 30 Táchira players
to 99, changes no other record, leaves the source files untouched, passes --check, and the world's
own Player.bin fails --check. A fixture with one stat at 98 also fails.

Needs a game with the Liga FUTVE world (FL26_DIR or --game); without one it says SKIPPED and exits 0.
"""
import argparse, hashlib, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pesdb
import playeredit as E
import futve_fixture as F

REPO = os.path.dirname(HERE)
N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def run(args):
    return subprocess.run([sys.executable, os.path.join(HERE, "futve_fixture.py")] + args,
                          capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default=os.environ.get("FL26_DIR"))
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()
    base = os.path.join(a.game or "", "SiderAddons", "livecpk", "_FL26MyWorld", "common", "etc", "pesdb")
    if not a.game or not os.path.isfile(os.path.join(base, "Player.bin")):
        print("SKIPPED: no game world (set FL26_DIR or pass --game)")
        return 0
    os.makedirs(os.path.join(REPO, "out", "tmp"), exist_ok=True)
    tmp = tempfile.mkdtemp(dir=os.path.join(REPO, "out", "tmp"))
    try:
        world = os.path.join(tmp, "world")
        os.makedirs(world)
        for n in ("Player.bin", "PlayerAssignment.bin"):
            shutil.copy2(os.path.join(base, n), os.path.join(world, n))
        src_sha = sha(os.path.join(world, "Player.bin"))
        asg_sha = sha(os.path.join(world, "PlayerAssignment.bin"))
        fixout = os.path.join(tmp, "fix")
        r = run(["--make", "--world", world, "--out", fixout])
        ok("--make succeeds", r.returncode == 0)
        fix = os.path.join(fixout, "Player.bin")
        ok("the fixture and its manifest exist", os.path.isfile(fix)
           and os.path.isfile(os.path.join(fixout, "manifest.json")))
        ok("the source Player.bin is untouched", sha(os.path.join(world, "Player.bin")) == src_sha)
        ok("the source PlayerAssignment.bin is untouched",
           sha(os.path.join(world, "PlayerAssignment.bin")) == asg_sha)

        src = bytearray(pesdb.wesys_unpack(open(os.path.join(world, "Player.bin"), "rb").read()))
        out = bytearray(pesdb.wesys_unpack(open(fix, "rb").read()))
        assigns = bytearray(pesdb.wesys_unpack(open(os.path.join(world, "PlayerAssignment.bin"), "rb").read()))
        ids = F.squad(assigns, F.TEAM)
        ok("the team has its squad (%d players)" % len(ids), len(ids) >= 11)
        idx = F.index(src)
        touched = {idx[p] for p in ids}
        changed = [i for i in range(0, len(out), E.P_REC)
                   if out[i:i + E.P_REC] != src[i:i + E.P_REC]]
        ok("only the team's records changed", set(changed) <= touched and len(changed) == len(touched))
        for o in changed:
            rec = out[o:o + E.P_REC]
            ok("player %d: all 25 stats 99" % E.u32(rec, E.P_ID), F.values(rec) == [99] * 25)
            break
        # a stat at 98 fails
        bad = bytearray(out)
        o = idx[ids[0]]
        rec = bytearray(bad[o:o + E.P_REC])
        E.setf(rec, "Speed", 98)
        bad[o:o + E.P_REC] = rec
        badfile = os.path.join(tmp, "bad.bin")
        open(badfile, "wb").write(pesdb.wesys_pack(bytes(bad)))
        ok("--check passes on the fixture", run(["--check", fix, "--assignments",
                                                 os.path.join(world, "PlayerAssignment.bin")]).returncode == 0)
        ok("--check fails on the world's own Player.bin",
           run(["--check", os.path.join(world, "Player.bin"), "--assignments",
                os.path.join(world, "PlayerAssignment.bin")]).returncode != 0)
        ok("--check fails on a fixture with one stat at 98",
           run(["--check", badfile, "--assignments",
                os.path.join(world, "PlayerAssignment.bin")]).returncode != 0)
        # --from is the same as --world's Player.bin
        r = run(["--make", "--world", world, "--from", os.path.join(world, "Player.bin"),
                 "--out", os.path.join(tmp, "from")])
        ok("--from builds the same fixture", r.returncode == 0
           and sha(os.path.join(tmp, "from", "Player.bin")) == sha(fix))
        print("ok")
        return 0
    finally:
        if a.keep:
            print("kept: %s" % tmp)
        else:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
