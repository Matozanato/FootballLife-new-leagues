"""B315 (huliaanos, 03.11.): promotion and relegation between January-December leagues of ours in
a country of ours (Finland, four tiers, `season 29 1`), which no season-end pass of the game's
has: fl26join exchanges each pair at the New Year teardown. Its cal_swap built natively with
FL26_JOIN_TEST (tools/native/test_cal_exchange.c) and run without the game.

    python tools/test_cal_exchange.py

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
out = os.path.join(tempfile.mkdtemp(), "test_cal_exchange.exe")
subprocess.run([zig, "cc", "-O2", "-fno-sanitize=undefined", "-w",
                os.path.join(NATIVE, "test_cal_exchange.c"), "-o", out], check=True, cwd=NATIVE)
r = subprocess.run([out], capture_output=True, text=True, timeout=120)
sys.stdout.write(r.stdout)
assert r.returncode == 0, "the New Year exchange checks failed"
assert "all checks passed" in r.stdout
print("ok")
