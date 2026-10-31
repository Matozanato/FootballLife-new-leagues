r"""python tools/test_savedir.py

B296 (GiorgiM 30.10.): a Documents folder named in Georgian letters (C:\Users\...\დოკუმენტები) --
fl26edit could not write its side file and fl26swiss its kept tables: both built the path with the
ANSI calls, so the folder came back as ??? and did not exist. And the game saves under ...\0\save,
not ...\2026\save, when the Steam stand-in does not read sys.ini.

The modules (tools/native/fl26savedir.h, built here with its FL26_SAVEDIR_TEST harness
tools/native/test_savedir.c) and Mod Studio (modstudio/game.py save_root) find the save folder the
same way: Documents with any letters, sys.ini's SteamID, else the numbered folder whose
SYSTEM00000000 was written last. Every case is checked on both, and they must agree.

Needs zig (ZIG, PATH, or D:/dev/tools/zig-*/zig.exe); without it the C half is skipped. Everything
happens in a temp folder, never in the real Documents.
"""
import glob, os, shutil, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
NATIVE = os.path.join(HERE, "native")
sys.path.insert(0, HERE)
from modstudio import game as G

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def find_zig():
    z = os.environ.get("ZIG")
    if z and os.path.exists(z):
        return z
    z = shutil.which("zig")
    if z:
        return z
    found = sorted(glob.glob("D:/dev/tools/zig-*/zig.exe"))
    return found[-1] if found else None


T = tempfile.mkdtemp(prefix="savedir-")
DOCS = os.path.join(T, "Users", "გიორგი", "დოკუმენტები")      # Georgian: outside every ANSI code page
BASE = os.path.join(DOCS, "KONAMI", "eFootball PES 2021 SEASON UPDATE")
GAME = os.path.join(T, "fútbol life 2026")                     # the exe's folder: sys.ini next to it
os.makedirs(BASE)
os.makedirs(GAME)
G.SAVE_DIR = BASE

zig = find_zig()
exe = None
if zig:
    exe = os.path.join(GAME, "test_savedir.exe")
    build = os.path.join(T, "test_savedir.exe")
    subprocess.run([zig, "cc", "-O2", "-fno-sanitize=undefined", "-w",
                    os.path.join(NATIVE, "test_savedir.c"), "-o", build], check=True, cwd=NATIVE)
    shutil.copy(build, exe)
else:
    print("C half SKIPPED: no zig (set ZIG to zig.exe)")


def native(*args):
    env = dict(os.environ, FL26_TEST_DOCS=DOCS)
    r = subprocess.run([exe] + list(args), capture_output=True, env=env, timeout=30)
    return r.returncode, r.stdout.decode("utf-8").strip()


def sysini(steam_id):
    p = os.path.join(GAME, "sys.ini")
    if steam_id is None:
        if os.path.exists(p):
            os.remove(p)
        return
    with open(p, "w", encoding="utf-8") as f:
        f.write("[Settings]\nLanguage=english\nSavePath=%%DEFAULT_SYS_DIR%%\nSteamID=%s\n" % steam_id)


def system(name, age):
    d = os.path.join(BASE, name, "save")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "SYSTEM00000000")
    with open(p, "wb") as f:
        f.write(b"sys")
    t = time.time() - age
    os.utime(p, (t, t))


def case(name, want):
    want = os.path.join(BASE, want)
    py = G.save_root(GAME)
    ok("%s: Mod Studio -> %s" % (name, os.path.relpath(py, BASE)), os.path.normcase(py) == os.path.normcase(want))
    if exe:
        rc, out = native("dir")
        ok("%s: the modules -> the same folder" % name,
           rc == 0 and os.path.normcase(out) == os.path.normcase(os.path.join(want, "save")))


sysini(2026)
case("a new player, nothing saved yet", "2026")
sysini(None)
case("no sys.ini", "2026")
sysini(777)
case("another SteamID in sys.ini", "777")
sysini(2026)
system("0", 100)
case("the game saved under 0 (sys.ini not read)", "0")
system("2026", 50)
case("2026 holds a save too: sys.ini's folder wins", "2026")
system("0", 1)
case("... even when 0's is newer", "2026")
shutil.rmtree(os.path.join(BASE, "2026"))
system("12", 10)
case("no save under sys.ini's: the newest of the numbered folders", "0")
os.makedirs(os.path.join(BASE, "WEPES", "save"))
with open(os.path.join(BASE, "WEPES", "save", "SYSTEM00000000"), "wb") as f:
    f.write(b"x")
case("a folder that is not a number is not a save folder", "0")

if exe:
    rc, out = native("put")
    probe = os.path.join(BASE, "0", "save", "probe.fl26x.moved")
    ok("written, moved and read back in the Georgian folder", rc == 0 and out == "written" and os.path.isfile(probe))
    ok("... and nowhere else", not os.path.exists(os.path.join(BASE, "0", "save", "probe.fl26x")))

os.environ.pop("FL26_SAVE_ROOT", None)
G.SAVE_DIR = BASE
import flpaths
flpaths.GAME_DIR = GAME
ok("edit_file: the Edit save in the folder the game saves in",
   os.path.normcase(G.edit_file()) == os.path.normcase(os.path.join(BASE, "0", "save", "EDIT00000000")))
from modstudio import saves as S
ok("saves.root: the same folder", os.path.normcase(S.root()) == os.path.normcase(os.path.join(BASE, "0")))
ok("Documents: Windows' own folder, an existing one", os.path.isdir(G.documents()))

# FL27 (31.10.): the same exe as FL_2027.exe, saving under Documents\SPGAME\Football Life\<id>,
# sys.ini SteamID=2027. The test program is copied in as FL_2027.exe: the modules go by the exe's name.
BASE27 = os.path.join(DOCS, "SPGAME", "Football Life")
GAME27 = os.path.join(T, "FL27 game")
os.makedirs(BASE27)
os.makedirs(GAME27)
G.SAVE_DIR_FL27 = BASE27
exe27 = None
if exe:
    exe27 = os.path.join(GAME27, "FL_2027.exe")
    shutil.copy(os.path.join(T, "test_savedir.exe"), exe27)
else:
    open(os.path.join(GAME27, "FL_2027.exe"), "wb").close()
ok("FL27: the folder is FL27's", G.is_fl27(GAME27) and not G.is_fl27(GAME))


def case27(name, want, ini):
    p = os.path.join(GAME27, "sys.ini")
    if ini is None:
        if os.path.exists(p):
            os.remove(p)
    else:
        with open(p, "w", encoding="utf-8") as f:
            f.write("[Settings]\nLanguage=english\nSavePath=%%DEFAULT_SYS_DIR%%\nSteamID=%s\n" % ini)
    want = os.path.join(BASE27, want)
    py = G.save_root(GAME27)
    ok("FL27, %s: Mod Studio -> SPGAME\\Football Life\\%s" % (name, os.path.relpath(py, BASE27)),
       os.path.normcase(py) == os.path.normcase(want))
    if exe27:
        r = subprocess.run([exe27, "dir"], capture_output=True, env=dict(os.environ, FL26_TEST_DOCS=DOCS), timeout=30)
        out = r.stdout.decode("utf-8").strip()
        ok("FL27, %s: the modules -> the same folder" % name,
           r.returncode == 0 and os.path.normcase(out) == os.path.normcase(os.path.join(want, "save")))


case27("sys.ini SteamID=2027", "2027", 2027)
case27("no sys.ini", "2027", None)
d = os.path.join(BASE27, "0", "save")
os.makedirs(d)
open(os.path.join(d, "SYSTEM00000000"), "wb").close()
case27("saved under 0 only", "0", 2027)
ok("FL26 next to it still saves under KONAMI", os.path.normcase(os.path.dirname(G.save_root(GAME))) == os.path.normcase(BASE))
shutil.rmtree(T, ignore_errors=True)
print("all %d checks passed" % N)
