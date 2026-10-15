"""python tools/test_stale_pack.py

B37 (a tester's 0.2.4 beta, 15.10.): Mod Studio updated over an older one keeps the old pack's
single modules a bundle has since replaced (fl26deep4.lua, fl26reg64.lua ...). Install the modules
copied them in and moved them out again, and Home said "2 modules missing" for ever, Install now or
not. A retired module in the pack is now neither installed nor counted.
"""
import os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import leaguebuilder as B
from modstudio import checks

N = 0

INI = """[sider]
lua.enabled = 1
luajit.ext.enabled = 1
"""


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


class G:
    def __init__(self, folder):
        self.folder = folder
        self.sider_dir = os.path.join(folder, "SiderAddons")
        self.modules_dir = os.path.join(self.sider_dir, "modules")
        self.livecpk_dir = os.path.join(self.sider_dir, "livecpk")


def main():
    tmp = tempfile.mkdtemp()
    old_pack = B.pack_dir
    try:
        pack = os.path.join(tmp, "pack")
        os.makedirs(os.path.join(pack, "modules"))
        for f in ("fl26deeprank.lua", "fl26reg128.lua", "fl26deep4.lua", "fl26reg64.lua"):
            open(os.path.join(pack, "modules", f), "w").write("-- " + f)
        open(os.path.join(pack, "modules.txt"), "w").write("fl26deeprank\nfl26reg128\n")
        open(os.path.join(pack, "retired.txt"), "w").write("fl26deep4 fl26deeprank\nfl26reg64 fl26reg128\n")
        B.pack_dir = lambda: pack
        game = os.path.join(tmp, "game")
        os.makedirs(os.path.join(game, "SiderAddons", "modules"))
        open(os.path.join(game, "FL_2026.exe"), "wb").close()
        open(os.path.join(game, "SiderAddons", "sider.ini"), "w", encoding="utf-8").write(INI)

        ok("the retired files are left out of what ships", B.shipped_files(os.path.join(pack, "modules"))
           == ["fl26deeprank.lua", "fl26reg128.lua"])
        B.install_modules(game, log=lambda s: None, settle=0)
        mods = os.listdir(os.path.join(game, "SiderAddons", "modules"))
        ok("the bundles are installed", "fl26deeprank.lua" in mods and "fl26reg128.lua" in mods)
        ok("the retired ones are not", "fl26deep4.lua" not in mods and "fl26reg64.lua" not in mods)
        ok("no old copies made for them", not any(m.startswith("before-builder") for m in mods))
        st = checks.modules_state(G(game))
        ok("nothing missing after Install (was 2 for ever)", st is not None and st["missing"] == [])
        ok("nothing changed or off", not st["changed"] and not st["off"] and checks.modules_ok(st))
        B.install_modules(game, log=lambda s: None, settle=0)
        ok("a second install changes nothing", checks.modules_ok(checks.modules_state(G(game))))
    finally:
        B.pack_dir = old_pack
        shutil.rmtree(tmp, ignore_errors=True)
    print("1..%d" % N)


if __name__ == "__main__":
    main()
