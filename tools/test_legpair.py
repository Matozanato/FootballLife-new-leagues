"""B246 (antonimus 26.10.): the Libertadores phase 3 hand-over gives each match record of a tie
its new pair whole, in its leg's order, even when the new pair shares a club with the old one
(Deportes La Serena v Deportes La Serena, Lanus gone). fl26swiss.c's libq_leg_pair built natively
with the FL26_RCAL_TEST harness (tools/native/test_legpair.c) and run without the game.

    python tools/test_legpair.py

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
out = os.path.join(tempfile.mkdtemp(), "test_legpair.exe")
subprocess.run([zig, "cc", "-O2", "-fno-sanitize=undefined", "-w",
                os.path.join(NATIVE, "test_legpair.c"), "-o", out], check=True, cwd=NATIVE)
r = subprocess.run([out], capture_output=True, text=True, timeout=120)
sys.stdout.write(r.stdout)
assert r.returncode == 0, "the phase 3 hand-over checks failed"
assert "all checks passed" in r.stdout
