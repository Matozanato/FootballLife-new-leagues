"""GitHub #98: groups of one division (three Serie C groups under Serie B, nine Serie D groups
under the three of Serie C) and the promotion / relegation play-offs. fl26chain.c's group sets and
play-offs built natively with tools/native/test_chain_groups.c and run without the game, on a fake
image: sizes kept, every club in one league, the refusals and the play-off winners.

    python tools/test_chain_groups.py

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
out = os.path.join(tempfile.mkdtemp(), "test_chain_groups.exe")
subprocess.run([zig, "cc", "-O2", "-fno-sanitize=undefined", "-w",
                os.path.join(NATIVE, "test_chain_groups.c"), "-o", out], check=True, cwd=NATIVE)
r = subprocess.run([out], capture_output=True, text=True, timeout=120)
sys.stdout.write(r.stdout)
assert r.returncode == 0, "the group set checks failed"
assert "all checks passed" in r.stdout
