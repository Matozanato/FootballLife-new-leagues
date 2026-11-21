"""FL27's wide Conference League (Prijedlog C with a Conference League Q1 of 62): fl26swiss.c built
natively with the FL26_STATE_TEST harness (tools/native/test_uecl_wide.c) and run without the
game -- the world file's `qround 12 1` line (qcw_world), the rounds' sizes (UECL 62 / 62 / 40 / 40),
rooms and ways, the July days, the access list (28 / 12 / 0 direct, 170 in the rounds), a first
season without the July rounds (139), the play-offs into the league phases (36 / 36 / 36), the
UECL Q1's 31 + 31 kept in the state file as two records and read back after a restart, and a
Prijedlog C world without the line and FL26 as before (tools/test_uefa_c_native.py compares
those with the source before Prijedlog C).

    python tools/test_uecl_wide_native.py

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
exe = os.path.join(tmp, "test_uecl_wide.exe")
subprocess.run([zig, "cc", "-O2", "-fno-sanitize=undefined", "-w", os.path.join(NATIVE, "test_uecl_wide.c"), "-o", exe],
               check=True, cwd=NATIVE)
r = subprocess.run([exe], capture_output=True, text=True, timeout=120)
sys.stdout.write(r.stdout)
shutil.rmtree(tmp, ignore_errors=True)
assert r.returncode == 0, "the wide Conference League checks failed"
assert "all checks passed" in r.stdout
print("ok")
