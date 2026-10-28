"""The league play-off's pure parts (0.2.5): fl26swiss.c's ccup_league_groups, ccup_entry_rank and
ccup_league_final built natively with the FL26_RCAL_TEST harness (tools/native/test_ccup_league.c)
and run without the game -- the entries dealt into the groups in their order, the final ordered by
the regular phase, a club that is not an entry last, the same club in two groups once.

    python tools/test_futve_playoff.py

Needs zig (ZIG, PATH, or D:/dev/tools/zig-*/zig.exe, or out/tools/py/ziglang/zig.exe of the
branch's pip install); without it the test says so and is skipped.
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
    for pat in ("D:/dev/tools/zig-*/zig.exe",
                os.path.join(os.path.dirname(HERE), "out", "tools", "py", "ziglang", "zig.exe")):
        found = sorted(glob.glob(pat))
        if found:
            return found[-1]
    return None


zig = find_zig()
if not zig:
    print("SKIPPED: no zig (set ZIG to zig.exe)")
    sys.exit(0)
tmp_root = os.path.join(os.path.dirname(HERE), "out", "tmp")
os.makedirs(tmp_root, exist_ok=True)
out = os.path.join(tempfile.mkdtemp(dir=tmp_root), "test_ccup_league.exe")
env = dict(os.environ)
env.setdefault("ZIG_GLOBAL_CACHE_DIR", os.path.join(os.path.dirname(HERE), "out", "tools", "zig-cache"))
env.setdefault("ZIG_LOCAL_CACHE_DIR", env["ZIG_GLOBAL_CACHE_DIR"])
subprocess.run([zig, "cc", "-O2", "-fno-sanitize=undefined", "-w",
                os.path.join(NATIVE, "test_ccup_league.c"), "-o", out], check=True, cwd=NATIVE, env=env)
r = subprocess.run([out], capture_output=True, text=True, timeout=120)
sys.stdout.write(r.stdout)
assert r.returncode == 0, "the league play-off checks failed"
assert "all checks passed" in r.stdout
print("ok")
