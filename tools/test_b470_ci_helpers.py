"""B470 (morpheus 15.11.): Competition Info listed every continental cup's preliminary round (its
helper competition, FL_PRE<n>) as a second item with the cup's own name, the OFC one with two
clubs and a grey bracket. fl26swiss.c built natively with the FL26_STATE_TEST harness
(tools/native/test_b470_ci_helpers.c) and run without the game: the four pre-round competitions
of GigaPack beta 3 and the modern CONMEBOL helpers are hidden; the real cups, a league cup with
its own pre-round and a pre-round whose cup the world lacks are not.

    python tools/test_b470_ci_helpers.py

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
exe = os.path.join(tmp, "test_b470_ci_helpers.exe")
subprocess.run([zig, "cc", "-O2", "-fno-sanitize=undefined", "-w", os.path.join(NATIVE, "test_b470_ci_helpers.c"), "-o", exe],
               check=True, cwd=NATIVE)
r = subprocess.run([exe], capture_output=True, text=True, timeout=120)
sys.stdout.write(r.stdout)
shutil.rmtree(tmp, ignore_errors=True)
assert r.returncode == 0, "the B470 Competition Info checks failed"
assert "all checks passed" in r.stdout
print("ok")
