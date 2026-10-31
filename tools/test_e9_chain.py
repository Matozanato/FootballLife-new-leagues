"""FL27 (31.10.2026): SmokePatch hooks set_clubs (0x141522b50) itself with `jmp rel32` + nops, and
fl26chain / fl26swiss refused it (only their own `jmp [rip]` was chained). Both modules' hook_or_chain
built natively with tools/native/test_e9_chain.c and run on a fake function hooked their way: ours
goes in front, theirs and the original still run, their return point is untouched.

    python tools/test_e9_chain.py

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
for name, flags in (("fl26chain", []), ("fl26swiss", ["-DSWISS"])):
    out = os.path.join(tempfile.mkdtemp(), "test_e9_%s.exe" % name)
    subprocess.run([zig, "cc", "-O2", "-fno-sanitize=undefined", "-w"] + flags +
                   [os.path.join(NATIVE, "test_e9_chain.c"), "-o", out], check=True, cwd=NATIVE)
    r = subprocess.run([out], capture_output=True, text=True, timeout=120)
    print("== %s" % name)
    sys.stdout.write(r.stdout)
    assert r.returncode == 0, "%s: the e9 chain checks failed" % name
    assert "all checks passed" in r.stdout
print("both modules: all checks passed")
