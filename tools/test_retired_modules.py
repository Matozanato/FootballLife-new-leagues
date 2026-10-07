"""python tools/test_retired_modules.py

ensure_modules switches a module a bundle took over (fl26nullguard ... -> fl26guards) off only when
the bundle is loaded too. Switch on hands in the world's modules alone: it turned every guard off
with no fl26guards line in sider.ini (07.10., the modpack world), and the game had no guards.
"""
import os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import leaguebuilder as B
import lbpack

N = 0

INI = """[sider]
lua.enabled = 1
luajit.ext.enabled = 1
lua.module = "fl26nullguard.lua"
lua.module = "fl26nullguard2.lua"
lua.module = "fl26superguard.lua"
lua.module = "fl26regions.lua"
"""


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def live(game, m):
    t = open(os.path.join(game, "SiderAddons", "sider.ini"), encoding="utf-8-sig").read()
    return ('\nlua.module = "%s.lua"' % m) in t


def main():
    retired = B.retired_modules()
    if "fl26nullguard" not in retired:
        print("skip - no retired.txt in the pack (run lbpack first)")
        return
    game = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(game, "SiderAddons", "modules"))
        open(os.path.join(game, "FL_2026.exe"), "wb").close()
        open(os.path.join(game, "SiderAddons", "sider.ini"), "w", encoding="utf-8").write(INI)
        B.ensure_modules(game, lbpack.ORDER, ["fl26regions", "fl26regnames"], log=lambda s: None)
        ok("world modules only: the guards stay on", live(game, "fl26nullguard") and live(game, "fl26superguard"))
        ok("world modules only: no fl26guards line made up", not live(game, "fl26guards"))
        B.ensure_modules(game, lbpack.ORDER, ["fl26guards"], log=lambda s: None)
        ok("with fl26guards: its line is on", live(game, "fl26guards"))
        ok("with fl26guards: the guards it bundles go off", not live(game, "fl26nullguard") and not live(game, "fl26nullguard2"))
    finally:
        shutil.rmtree(game, ignore_errors=True)
    print("1..%d" % N)


if __name__ == "__main__":
    main()
