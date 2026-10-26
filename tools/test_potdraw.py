"""B243 (0.2.5): the modern Sudamericana's group draw keeps clubs of one association apart --
fl26swiss.c's pot_draw built natively with the FL26_RCAL_TEST harness (tools/native/test_potdraw.c)
and run without the game over thousands of draws: one club of every pot in each group, every club
once, no two clubs of one association in a group whenever a draw can manage it, and a single pair
when nine clubs of one association share 32 places.

    python tools/test_potdraw.py

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
out = os.path.join(tempfile.mkdtemp(), "test_potdraw.exe")
subprocess.run([zig, "cc", "-O2", "-fno-sanitize=undefined", "-w",
                os.path.join(NATIVE, "test_potdraw.c"), "-o", out], check=True, cwd=NATIVE)
r = subprocess.run([out], capture_output=True, text=True, timeout=120)
sys.stdout.write(r.stdout)
assert r.returncode == 0, "the pot draw checks failed"
assert "all checks passed" in r.stdout
print("ok")
