"""B49 (0.2.4): the final tables and cup winners fl26swiss keeps at the season's end outlive the
game session -- fl26swiss.c built natively with the FL26_STATE_TEST harness
(tools/native/test_state_keep.c) and run without the game: the July teardown writes them to the
save folder's fl26swiss-state.bin, the game is quit, a save of 26 July is loaded and the Europe
places come from the kept tables, not squad strength; a later save, an older save loaded in the
same session, another club's career and a new career each get what is theirs.

    python tools/test_state_keep.py

Needs zig (ZIG, PATH, or D:/dev/tools/zig-*/zig.exe); without it the test says so and is skipped.
The file is written in the temp folder, never in the game's save folder.
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
out = os.path.join(tempfile.mkdtemp(), "test_state_keep.exe")
subprocess.run([zig, "cc", "-O2", "-fno-sanitize=undefined", "-w",
                os.path.join(NATIVE, "test_state_keep.c"), "-o", out], check=True, cwd=NATIVE)
r = subprocess.run([out], capture_output=True, text=True, timeout=120)
sys.stdout.write(r.stdout)
assert r.returncode == 0, "the kept-state checks failed"
assert "all checks passed" in r.stdout
print("ok")
