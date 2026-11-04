"""B313 (pepponeee, 03.11.): a place the top-up gives goes to the next club of the league, and a
club of that league already in a lower competition by its league position goes up to it, as at
UEFA -- England's 7th from the Conference League to the Europa League's free place and the 8th to
the Conference League, not the 8th to the Europa League. fl26swiss.c built natively with the
FL26_STATE_TEST harness (tools/native/test_access_lift.c) and run without the game.

    python tools/test_access_lift.py

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
out = os.path.join(tempfile.mkdtemp(), "test_access_lift.exe")
subprocess.run([zig, "cc", "-O2", "-fno-sanitize=undefined", "-w",
                os.path.join(NATIVE, "test_access_lift.c"), "-o", out], check=True, cwd=NATIVE)
r = subprocess.run([out], capture_output=True, text=True, timeout=120)
sys.stdout.write(r.stdout)
assert r.returncode == 0, "the access lift checks failed"
assert "all checks passed" in r.stdout
print("ok")
