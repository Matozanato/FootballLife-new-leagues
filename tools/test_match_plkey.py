"""Loading times with a large world (15.11.2026): a GigaPack career made 69228 full scans of the
player array in fl26match's pl_key while it was created (12 s of the loading screen), one for
each player past 65534. A scan now fills the id map for every record. pl_key built natively
(tools/native/test_match_plkey.c) and compared with a plain search: all players loaded, moved,
removed, loaded one by one, words that are not the player's; and with all players loaded the
first question may cost one full scan, not one per player.

    python tools/test_match_plkey.py

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
out = os.path.join(tempfile.mkdtemp(), "test_match_plkey.exe")
subprocess.run([zig, "cc", "-target", "x86_64-windows-gnu", "-O2", "-fno-sanitize=undefined", "-w",
                os.path.join(NATIVE, "test_match_plkey.c"), "-o", out, "-lkernel32"], check=True, cwd=NATIVE)
r = subprocess.run([out], capture_output=True, text=True, timeout=300)
sys.stdout.write(r.stdout)
assert r.returncode == 0, "pl_key differs from the plain search"
assert ", 0 differences;" in r.stdout and "all loaded first: 1 full scans" in r.stdout
print("ok")
