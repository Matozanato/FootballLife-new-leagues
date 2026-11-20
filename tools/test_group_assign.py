"""16.11.2026 (mato: "klubovi moraju po regijama ispadati ... kao u stvarnosti"): which group of a
set each relegated club, guest and border club goes to. fl26chain.c's group_assign and group_plan
built natively with tools/native/test_group_assign.c and run without the game: everyone fits; the
cascade the old one-pass rule made (1 at home, now 2); four relegated of one region and four
places; Hungary's play-off groups with no place; a club with no home; a guest coming home; two and
three guests swapping; border clubs (zone_border); random sets against trying every choice; every
league keeps its size, no club twice or missing, the same answer every time.

    python tools/test_group_assign.py

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
out = os.path.join(tempfile.mkdtemp(), "test_group_assign.exe")
subprocess.run([zig, "cc", "-O2", "-fno-sanitize=undefined", "-w",
                os.path.join(NATIVE, "test_group_assign.c"), "-o", out], check=True, cwd=NATIVE)
r = subprocess.run([out], capture_output=True, text=True, timeout=300)
sys.stdout.write(r.stdout)
assert r.returncode == 0, "the group assignment checks failed"
assert "all checks passed" in r.stdout
print("ok")
