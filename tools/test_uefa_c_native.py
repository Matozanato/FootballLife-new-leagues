"""FL27's UEFA qualifying, Prijedlog C (mato 07.11., notes/uefa-q1-srpanj.md): fl26swiss.c built
natively with the FL26_STATE_TEST harness (tools/native/test_uefa_c.c) and run without the game --
the Europa and Conference League's August play-offs of 32 (regulations of the world file's own),
the rounds' sizes, rooms and ways up and down, the July days of the two first rounds, the access
list (28 / 12 / 4 direct, 112 in the rounds), a first season without the July rounds, the
play-offs into the league phases (36 / 36 / 36), and the Europa League Q1's result kept and read
back after a restart. FL26, and FL27 with Prijedlog A's world file, must not change at all: the
harness's DUMP lines are compared with the same harness built against fl26swiss.c as it was
before Prijedlog C (commit BASE, from git; skipped without git).

    python tools/test_uefa_c_native.py

Needs zig (ZIG, PATH, or D:/dev/tools/zig-*/zig.exe); without it the test says so and is skipped.
"""
import glob, os, shutil, subprocess, sys, tarfile, tempfile, io

HERE = os.path.dirname(os.path.abspath(__file__))
NATIVE = os.path.join(HERE, "native")
BASE = "77f0cdc"            # test0611, the branch point: Prijedlog A, no play-offs of 32 yet


def find_zig():
    z = os.environ.get("ZIG")
    if z and os.path.exists(z):
        return z
    z = shutil.which("zig")
    if z:
        return z
    found = sorted(glob.glob("D:/dev/tools/zig-*/zig.exe"))
    return found[-1] if found else None


def build_run(zig, src_dir, exe):
    subprocess.run([zig, "cc", "-O2", "-fno-sanitize=undefined", "-w",
                    os.path.join(src_dir, "test_uefa_c.c"), "-o", exe], check=True, cwd=src_dir)
    return subprocess.run([exe], capture_output=True, text=True, timeout=120)


def dump(text):
    return [l for l in text.splitlines() if l.startswith("DUMP")]


zig = find_zig()
if not zig:
    print("SKIPPED: no zig (set ZIG to zig.exe)")
    sys.exit(0)
tmp = tempfile.mkdtemp()
r = build_run(zig, NATIVE, os.path.join(tmp, "test_uefa_c.exe"))
sys.stdout.write("\n".join(l for l in r.stdout.splitlines() if not l.startswith("DUMP")) + "\n")
assert r.returncode == 0, "the Prijedlog C checks failed"
assert "all checks passed" in r.stdout
new = dump(r.stdout)
assert len(new) > 20, "no DUMP lines"

try:
    tar = subprocess.run(["git", "archive", BASE, "tools/native"], cwd=os.path.dirname(HERE), capture_output=True, check=True).stdout
except (OSError, subprocess.CalledProcessError):
    tar = None
if tar is None:
    print("SKIPPED the FL26 comparison: no git history (%s)" % BASE)
else:
    old_root = os.path.join(tmp, "old")
    tarfile.open(fileobj=io.BytesIO(tar)).extractall(old_root)
    old_native = os.path.join(old_root, "tools", "native")
    shutil.copy(os.path.join(NATIVE, "test_uefa_c.c"), old_native)
    o = build_run(zig, old_native, os.path.join(tmp, "test_uefa_c_old.exe"))
    assert o.returncode == 0, o.stdout[-2000:]
    old = dump(o.stdout)
    for a, b in zip(old, new):
        if a != b:
            print("differs:\n  before: %s\n  now:    %s" % (a[:300], b[:300]))
    assert old == new, "FL26 / Prijedlog A is not the same as before Prijedlog C"
    print("FL26 and Prijedlog A: %d dump lines the same as at %s (rooms, days, every round's and list's clubs)" % (len(new), BASE))
shutil.rmtree(tmp, ignore_errors=True)
print("ok")
