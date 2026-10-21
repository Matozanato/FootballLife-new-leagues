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

# B35: leaguebuilder keeps a split league's playoffs off our continental cups' days -- every day
# of the DLL's tables (CCUP_GROUP_DAYS, CCUP_KO_DAYS, all three regions), no more, no fewer
import re
sys.path.insert(0, HERE)
import leaguebuilder
src = open(os.path.join(NATIVE, "fl26swiss.c"), encoding="utf-8").read()
tables = [re.search(r"%s\[CR_N\]\[2\]\[%d\] = \{(.*?)\};" % (name, k), src, re.S).group(1)
          for name, k in (("CCUP_GROUP_DAYS", 6), ("CCUP_KO_DAYS", 7))]
days = sorted({int(d) for t in tables for d in re.findall(r"\d+", t)})
assert days == leaguebuilder.CCUP_DAYS, (days, leaguebuilder.CCUP_DAYS)
print("leaguebuilder.CCUP_DAYS = the DLL's %d continental cup days" % len(days))
print("ok")
