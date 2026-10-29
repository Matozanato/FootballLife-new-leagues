"""B278 (D1eg0Ar, Agus 29.10.): fl26chain gave the Copa Argentina its top league's 26 clubs after a
season pass, the game drew 13 first-round ties and the bracket screen crashed at 0x140b34501.
fl26chain.c's cup_fix built natively with tools/native/test_chain_cupfit.c and run without the
game: every field of 32 or fewer is one of #74's bracket sizes.

    python tools/test_chain_cupfit.py

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
out = os.path.join(tempfile.mkdtemp(), "test_chain_cupfit.exe")
subprocess.run([zig, "cc", "-O2", "-fno-sanitize=undefined", "-w",
                os.path.join(NATIVE, "test_chain_cupfit.c"), "-o", out], check=True, cwd=NATIVE)
r = subprocess.run([out], capture_output=True, text=True, timeout=120)
sys.stdout.write(r.stdout)
assert r.returncode == 0, "the cup field checks failed"
assert "all checks passed" in r.stdout
