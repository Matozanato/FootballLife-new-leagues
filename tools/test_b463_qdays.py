"""B463 (Luka 13.11., mato 16.11.: "tjedan dana razmaka"): FL27's August qualifying rounds, the
second leg a week after the first where it fits. fl26swiss.c built natively with the
FL26_STATE_TEST harness (tools/native/test_b463_qdays.c) and run without the game: for every season
2026..2060 the six August legs between 218 and 244 (six days before FL27's own league phase on
day 250), on a Tuesday, Wednesday or Thursday, each round's legs 5..7 days apart (2026: Q2 7, Q3 5,
play-off 6; 2027 and 2028: 7 / 5 / 7), two days at least between any two matches of a club, the
fill days between the rounds and after the old layout's second legs (a save of then), no fewer
weekend days for the leagues, the July round, the league phases' first matchday and the national
cups' first round unchanged; FL26's six weeks as before.

    python tools/test_b463_qdays.py

Needs zig (ZIG, PATH, or D:/dev/tools/zig-*/zig.exe); without it the test says so and is skipped.
"""
import glob, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
NATIVE = os.path.join(HERE, "native")


def find_zig():
    z = os.environ.get("ZIG")
    if z and os.path.exists(z):
        return z
    z = shutil.which("zig")
    if z:
        return z
    found = sorted(glob.glob("D:/dev/tools/zig-*/zig.exe"))
    return found[-1] if found else None


zig = find_zig()
if not zig:
    print("SKIPPED: no zig (set ZIG to zig.exe)")
    sys.exit(0)
tmp = tempfile.mkdtemp()
exe = os.path.join(tmp, "test_b463_qdays.exe")
subprocess.run([zig, "cc", "-O2", "-fno-sanitize=undefined", "-w", os.path.join(NATIVE, "test_b463_qdays.c"), "-o", exe],
               check=True, cwd=NATIVE)
r = subprocess.run([exe], capture_output=True, text=True, timeout=120)
sys.stdout.write(r.stdout)
shutil.rmtree(tmp, ignore_errors=True)
assert r.returncode == 0, "the B463 qualifying days checks failed"
assert "all checks passed" in r.stdout
print("ok")
