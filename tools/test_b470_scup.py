"""B470 (FL Testovi, GigaPack beta 3, season 2, 17.11.): after the first summer the UEFA Super Cup
(reg 7) was never played -- the July teardown emptied it and the game never filled it again --
and the Europa League knockout (reg 6) kept last season's 24 clubs, because the game's July list
closes 4 and 5 but not 6. fl26swiss.c built natively with the FL26_STATE_TEST harness
(tools/native/test_b470_scup.c) and run without the game: the rule that fills reg 7 from the kept
Champions League and Europa League winners (window, already filled, played, winner missing, same
club) and the ids teardown_pre adds for reg 6.

    python tools/test_b470_scup.py

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
exe = os.path.join(tmp, "test_b470_scup.exe")
subprocess.run([zig, "cc", "-O2", "-fno-sanitize=undefined", "-w", os.path.join(NATIVE, "test_b470_scup.c"), "-o", exe],
               check=True, cwd=NATIVE)
r = subprocess.run([exe], capture_output=True, text=True, timeout=120)
sys.stdout.write(r.stdout)
shutil.rmtree(tmp, ignore_errors=True)
assert r.returncode == 0, "the B470 Super Cup / reg 6 checks failed"
assert "all checks passed" in r.stdout

# B470b: with FL 2027 installed, the fact the fix rests on -- the exe's event table (251 rows of
# 20 bytes at 0x1426d2490, the region key at +0x10) gives the Champions League knockout (4) and the
# Europa League knockout (6) the same region, so 6 is on the July list with 4 and was never
# missing from it; its entries are left by the season close instead (fl26swiss.c, uel_ko_stale).
EXE = os.environ.get("FL27_EXE", r"E:/FL/FL27/game/FL_2027.exe")
try:
    import pefile, struct
except ImportError:
    pefile = None
if pefile and os.path.exists(EXE):
    pe = pefile.PE(EXE, fast_load=True)
    base = pe.OPTIONAL_HEADER.ImageBase
    raw = pe.get_data(0x1426d2490 - base, 251 * 20)
    key = {}
    for i in range(251):
        rid, = struct.unpack_from("<H", raw, i * 20)
        key[rid] = struct.unpack_from("<I", raw, i * 20 + 16)[0]
    for rid in (2, 3, 4, 5, 6, 7, 1027, 1029):
        assert rid in key, "event table: no row for reg %d (another exe?)" % rid
    assert key[4] == key[6] == key[2] == key[1029], "event table: reg 4 and 6 in different regions %r" % key
    print("event table of %s: regs 2..7, 1027, 1029 share region %d" % (os.path.basename(EXE), key[6]))
else:
    print("event table check SKIPPED (no pefile or no %s)" % EXE)
print("ok")
