"""B470 (FL Testovi 20.06.2028, save b470-s2-2006): Competition Info's "Individual Titles" and
"Team of the Competition" grey for the Champions League, the CAF Champions League, the AFC
Champions League Two and the OFC Champions League, on for the CONCACAF Champions Cup. The menu's
walk (0x141590780) asks every regulation of the competition that the exe's row table does not
call "no awards" for a non-empty awards list; our cup phases (qualifying rounds, play-offs, the
world file's continental cups) have no row, so they were asked, and their lists are empty.

beta4r (18.11.): with that first gate UCL / UEL were on, but UECL, CAF CL, CAF CC, AFC CL Two,
AFC Challenge and OFC CL stayed grey. One group of a group stage (a replica, +0x76 = its master)
gets +0x84 = 1 from CompetitionKind (0x1414efb90, bits 8..10), the value a league has, so the
first gate still asked it for a list. UCL / UEL's groups have the exe's alias rows; CONCACAF and
the CAF Super Cup have no groups. The gate now takes such a group as its master is.

tools/native/test_b470_awgate.c runs the game's own bytes of the walk and of 0x1414cfb90 in a
fake image over GigaPack's records (with the loader's kinds): unpatched it answers as the game
did (UCL and CAF grey, CONCACAF on); with the first gate's rule it gives beta4r's table; with
awgate_install every continental cup is on and the leagues answer as before.

    python tools/test_b470_awgate.py

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
exe = os.path.join(tmp, "test_b470_awgate.exe")
subprocess.run([zig, "cc", "-O2", "-fno-sanitize=undefined", "-w", os.path.join(NATIVE, "test_b470_awgate.c"), "-o", exe],
               check=True, cwd=NATIVE)
r = subprocess.run([exe], capture_output=True, text=True, timeout=120)
sys.stdout.write(r.stdout)
shutil.rmtree(tmp, ignore_errors=True)
assert r.returncode == 0, "the B470 awards gate checks failed"
assert "all B470 awards gate checks passed" in r.stdout
print("ok")
