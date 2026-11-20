r"""python tools/test_group_zones.py [--keep]

B458 (13.11.2026, a closed-beta tester's Italy in an FL27 world): Serie C Girone A showed its
promotion place in the standings, Girone B and C showed nothing, and the same for every set of
groups. The game links one league to one league, so only the first group of a set has the game's
own up / down link and its colours; the others are moved by fl26chain from the world file's

  gset <k> up=<id>:<n>,... low=<id>:<n>:<pref>,...

lines (an upper league's n clubs go down, a lower group's n go up). fl26swiss.lua now reads the
same lines (world_gzones) and hands them to fl26swiss.dll (fl26_swiss_gzone), which colours a
row by them wherever the game has no link of its own (zone_group).

Checked here, with the loader's own Lua (LuaJIT through lupa) and fl26swiss.c built natively
(tools/native/test_group_zones.c):
  - a hand-written world: three groups under one league, groups that are below one set and
    above another, a group that sends nobody up (n = 0);
  - every row of every league of every set: up for the first n rows of a lower group, down for
    the last n of an upper league, nothing in between -- against fl26world.read_groups, the
    builder's own reading of the same lines, not the Lua's;
  - a side the game links itself is left to the game (no colour from the sets);
  - a league in no set, and a world without gset lines: no colour;
  - the _FL26Megapack world under E:/FL/FL27/game when it is there (read only): Serie C Girone
    A, B and C (389, 390, 391) each show their promotion place.

Needs zig (ZIG, PATH, or D:/dev/tools/zig-*/zig.exe) and lupa; without either it says so and is
skipped.
"""
import os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
NATIVE = os.path.join(HERE, "native")
LUA = os.path.join(os.path.dirname(HERE), "sider", "experimental", "fl26swiss.lua")
sys.path.insert(0, HERE)
import fl26world as W
from test_zone_colours import find_zig

UP, DOWN, NONE = 3, 5, -1
CLUBS = 20
N = 0

HAND = """world 1
league 300 tier=2 promote=0 demote=3 clubs=20 name=Second
league 400 tier=3 above=300 promote=1 demote=4 clubs=20 group=0 name=Third A
league 401 tier=3 above=300 promote=1 demote=4 clubs=20 group=0 name=Third B
league 402 tier=3 above=300 promote=1 demote=4 clubs=20 group=0 name=Third C
league 500 tier=4 above=400 promote=2 demote=0 clubs=20 group=1 name=Fourth A
league 501 tier=4 above=400 promote=0 demote=0 clubs=20 group=1 name=Fourth B
gset 0 up=300:3 low=400:1:300,401:1:300,402:1:300
gset 1 up=400:4,401:4,402:4 low=500:2:400,501:0:401
"""


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def lua_gzones():
    try:
        from lupa import luajit21 as lj
    except ImportError:
        try:
            from lupa import lua54 as lj
        except ImportError:
            return None
    with open(LUA, encoding="utf-8") as f:
        src = f.read()
    blk = re.search(r"^local function world_gzones\(ctx\)\n.*?^end\n", src, re.S | re.M)
    assert blk, "world_gzones not found in fl26swiss.lua"
    lua = lj.LuaRuntime()
    return lua, lua.execute(blk.group(0) + "\nreturn world_gzones")


def triples(reader, text):
    """the loader's buffer for this world file: [league, up, down, ...]"""
    lua, fn = reader
    tmp = tempfile.mkdtemp(prefix="fl26-gzone-")
    try:
        os.makedirs(os.path.join(tmp, "modules"))
        with open(os.path.join(tmp, "modules", "fl26world.txt"), "w", encoding="utf-8") as f:
            f.write(text)
        out = fn(lua.table_from({"sider_dir": tmp}))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return [out[i][j] for i in range(1, len(out) + 1) for j in (1, 2, 3)]


def expected(text):
    """{league: [up, down]} by the builder's own reading of the gset lines"""
    tmp = tempfile.mkdtemp(prefix="fl26-gzone-")
    try:
        path = os.path.join(tmp, "fl26world.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        gsets, _homes, _poffs = W.read_groups(path)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    want = {}
    for ups, lows in gsets:
        for u in ups:
            want.setdefault(u[0], [0, 0])[1] = u[1]
        for l in lows:
            want.setdefault(l[0], [0, 0])[0] = l[1]
    return want


def run(exe, tmp, buf, checks):
    data = os.path.join(tmp, "gzone.txt")
    with open(data, "w") as f:
        f.write("gzone %d\n%s\n" % (len(buf) // 3, " ".join(map(str, buf))))
        for c in checks:
            f.write("expect %d %d %d %d %d %d\n" % c)
    r = subprocess.run([exe, data], capture_output=True, text=True, timeout=120, cwd=tmp)
    said = [l.strip() for l in r.stdout.splitlines() if not l.startswith("fl26swiss:")]
    print("\n".join("#   " + l for l in said))
    return r.returncode == 0 and "all checks passed" in said


def rows(want, n=CLUBS):
    """every row of every league of the sets, with no link of the game's"""
    out = []
    for reg, (up, down) in sorted(want.items()):
        for i in range(n):
            out.append((reg, i, n, 0, 0, UP if i < up else DOWN if i + down >= n else NONE))
    return out


def main(keep=False):
    zig, reader = find_zig(), lua_gzones()
    if not zig or not reader:
        print("SKIPPED: %s" % ("no zig (set ZIG to zig.exe)" if not zig else "no Lua runtime (pip install lupa)"))
        return
    tmp = tempfile.mkdtemp(prefix="fl26-gzonetest-")
    try:
        exe = os.path.join(tmp, "test_group_zones.exe")
        subprocess.run([zig, "cc", "-O2", "-fno-sanitize=undefined", "-w", os.path.join(NATIVE, "test_group_zones.c"),
                        "-o", exe], check=True, cwd=NATIVE)
        want = expected(HAND)
        ok("hand-written world: the builder reads six leagues in two sets",
           want == {300: [0, 3], 400: [1, 4], 401: [1, 4], 402: [1, 4], 500: [2, 0], 501: [0, 0]})
        buf = triples(reader, HAND)
        got = {}
        for i in range(0, len(buf), 3):
            g = got.setdefault(buf[i], [0, 0])
            g[0] += buf[i + 1]
            g[1] += buf[i + 2]
        ok("fl26swiss.lua reads the same places from the gset lines", got == want)
        ok("every row of every group: first n up, last n down, nothing between", run(exe, tmp, buf, rows(want)))
        ok("Third B and Third C (not the first group) show their promotion place",
           run(exe, tmp, buf, [(401, 0, 20, 0, 0, UP), (402, 0, 20, 0, 0, UP), (401, 1, 20, 0, 0, NONE)]))
        ok("a side the game links itself is the game's: no colour from the sets",
           run(exe, tmp, buf, [(400, 0, 20, 1, 0, NONE), (400, 19, 20, 1, 0, DOWN),
                               (400, 0, 20, 0, 1, UP), (400, 19, 20, 0, 1, NONE), (400, 19, 20, 1, 1, NONE)]))
        ok("a group that sends nobody up, a league in no set, a table with no clubs: no colour",
           run(exe, tmp, buf, [(501, 0, 20, 0, 0, NONE), (501, 19, 20, 0, 0, NONE), (999, 0, 20, 0, 0, NONE),
                               (999, 19, 20, 0, 0, NONE), (300, 0, 0, 0, 0, NONE)]))
        ok("the relegation places follow the table's size (18 and 24 clubs)",
           run(exe, tmp, buf, [(300, 14, 18, 0, 0, NONE), (300, 15, 18, 0, 0, DOWN), (300, 17, 18, 0, 0, DOWN),
                               (300, 20, 24, 0, 0, NONE), (300, 21, 24, 0, 0, DOWN)]))
        none = "world 1\nleague 300 tier=2 clubs=20 name=Second\n"
        ok("a world without gset lines: nothing handed over, no colour",
           triples(reader, none) == [] and run(exe, tmp, [], [(300, 0, 20, 0, 0, NONE), (300, 19, 20, 0, 0, NONE)]))
        mega = "E:/FL/FL27/game/SiderAddons/livecpk/_FL26Megapack/fl26world.txt"
        if os.path.exists(mega):
            with open(mega, encoding="utf-8") as f:
                text = f.read()
            want = expected(text)
            buf = triples(reader, text)
            ok("_FL26Megapack: %d leagues in its sets, every row right" % len(want),
               len(want) > 20 and run(exe, tmp, buf, rows(want)))
            if all(r in want for r in (389, 390, 391)):
                ok("_FL26Megapack: Serie C Girone A, B and C each show their promotion place",
                   all(want[r][0] >= 1 for r in (389, 390, 391))
                   and run(exe, tmp, buf, [(r, 0, 20, 0, 0, UP) for r in (389, 390, 391)]))
        else:
            print("# no _FL26Megapack world under E:/FL/FL27/game: skipped")
    finally:
        if not keep:
            shutil.rmtree(tmp, ignore_errors=True)
    print("1..%d" % N)
    print("all passed")


if __name__ == "__main__":
    main("--keep" in sys.argv[1:])
