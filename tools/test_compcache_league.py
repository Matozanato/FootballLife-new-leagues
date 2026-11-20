"""Loading times with a large world (15.11.2026): fl26compcache answers the game's "which league
does this team play in" (0x141543510) in one pass over the regulations. Its league_of built
natively (tools/native/test_compcache_league.c) and compared with the game's own walk, written
out literally, on made-up regulation arrays: ids rising, repeated, out of order, more records
than the cap, an empty array. No difference is allowed.

    python tools/test_compcache_league.py

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
out = os.path.join(tempfile.mkdtemp(), "test_compcache_league.exe")
subprocess.run([zig, "cc", "-target", "x86_64-windows-gnu", "-O2", "-fno-sanitize=undefined", "-w",
                os.path.join(NATIVE, "test_compcache_league.c"), "-o", out, "-lkernel32"], check=True, cwd=NATIVE)
r = subprocess.run([out], capture_output=True, text=True, timeout=300)
sys.stdout.write(r.stdout)
assert r.returncode == 0, "league_of differs from the game's walk"
assert ", 0 differences;" in r.stdout
print("ok")
