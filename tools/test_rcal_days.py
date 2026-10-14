"""A club never plays two matches on consecutive days (0.2.4): fl26swiss.c's league schedulers
built natively with the FL26_RCAL_TEST harness (tools/native/test_rcal_days.c) and run without the
game -- Uruguay against the Libertadores, Korea and Saudi Arabia against the AFC Champions League,
Norway against the Champions League qualifying rounds, the Club World Cup, a continental cup of
ours reached by a cup winner, and both schedulers on one list of busy days.

    python tools/test_rcal_days.py

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
out = os.path.join(tempfile.mkdtemp(), "test_rcal_days.exe")
subprocess.run([zig, "cc", "-O2", "-fno-sanitize=undefined", "-w",
                os.path.join(NATIVE, "test_rcal_days.c"), "-o", out], check=True, cwd=NATIVE)
r = subprocess.run([out], capture_output=True, text=True, timeout=120)
sys.stdout.write(r.stdout)
assert r.returncode == 0, "the calendar checks failed"
assert "all checks passed" in r.stdout
print("ok")
