r"""python tools/test_ready_spfl.py

B44 (vmican, 15.10.): the final check after Import your world said "Kits: the world brings them,
but kits.lua is not in SiderAddons\modules" (and the same for scoreboards.lua) on a game whose
sider.ini loads SPFL26's own Kit Server as common\kits.lua: the file was there, in
modules\common, and the check looked for it in modules only. It now looks where sider.ini has it.
A module that really is missing still gets its line. No game: a folder made here.
"""
import os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from modstudio import checks
from modstudio.game import Game

N = 0
W = "_FL26M2400S"


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def write(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb" if isinstance(data, bytes) else "w", encoding=None if isinstance(data, bytes) else "utf-8") as f:
        f.write(data)


def make_game(root, mods):
    g = os.path.join(root, "Football Life 2026")
    sd = os.path.join(g, "SiderAddons")
    write(os.path.join(g, "FL_2026.exe"), b"MZ")
    write(os.path.join(sd, "sider.ini"), "[sider]\nlua.enabled = 1\ncpk.root = \".\\livecpk\\%s\"\n%s" % (
        W, "".join('lua.module = "%s"\n' % m for m in mods)))
    write(os.path.join(sd, "livecpk", W, "fl26world.txt"), "world\n")
    # the world's kits and boards where SPFL26's own modules read them (content\kits, content\scoreboards)
    write(os.path.join(sd, "content", "kits", W, "Club", "order.ini"), "")
    write(os.path.join(sd, "content", "kits", "map.txt"), '72144, "%s\\Club"\n' % W)
    write(os.path.join(sd, "content", "scoreboards", W, "board", "x.dds"), b"")
    write(os.path.join(sd, "content", "scoreboards", "map_competitions.txt"), "200, %s\\board\n" % W)
    os.makedirs(os.path.join(sd, "modules", "common"), exist_ok=True)
    return g


def rows(g, title):
    return [(lv, t) for lv, t in checks.ready_check(Game(g), W) if t.startswith(title)]


def main():
    tmp = tempfile.mkdtemp(prefix="ms_readyspfl_")
    try:
        g = make_game(os.path.join(tmp, "a"), ["common\\kits.lua", "common\\scoreboards.lua"])
        for m in ("kits.lua", "scoreboards.lua"):
            write(os.path.join(g, "SiderAddons", "modules", "common", m), "-- SPFL26\n")
        kits, boards = rows(g, "Kits"), rows(g, "Scoreboards")
        ok("Kits: one line", len(kits) == 1)
        ok("Kits: common\\kits.lua counts as there and on", kits[0][0] == "ok" and "kits.lua is on" in kits[0][1])
        ok("Scoreboards: common\\scoreboards.lua counts as there and on",
           len(boards) == 1 and boards[0][0] == "ok")

        g = make_game(os.path.join(tmp, "b"), ["common\\kits.lua", "common\\scoreboards.lua"])
        write(os.path.join(g, "SiderAddons", "modules", "common", "scoreboards.lua"), "-- SPFL26\n")
        kits = rows(g, "Kits")
        ok("a kits.lua sider.ini loads but no folder has still gets its line",
           len(kits) == 1 and kits[0][0] == "err" and "not in SiderAddons" in kits[0][1])
        ok("... and the one that is there is fine", rows(g, "Scoreboards")[0][0] == "ok")

        g = make_game(os.path.join(tmp, "c"), [";common\\kits.lua", "common\\scoreboards.lua"])
        write(os.path.join(g, "SiderAddons", "modules", "common", "kits.lua"), "-- SPFL26\n")
        write(os.path.join(g, "SiderAddons", "modules", "common", "scoreboards.lua"), "-- SPFL26\n")
        ini = open(os.path.join(g, "SiderAddons", "sider.ini"), encoding="utf-8").read()
        write(os.path.join(g, "SiderAddons", "sider.ini"), ini.replace('lua.module = ";common', ';lua.module = "common'))
        kits = rows(g, "Kits")
        ok("there but switched off says switched off", len(kits) == 1 and "switched off" in kits[0][1])
        print("test_ready_spfl: ok (%d)" % N)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
