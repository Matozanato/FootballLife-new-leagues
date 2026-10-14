"""python tools/test_regs_recount.py

Checks reports a world with more competition regulations than the game counts. The game counts its
regulation records again after every load and looks at the first 300 only (0x1414bc0a0); the array
is sorted by id, so in a bigger world the last ties of the European rounds (ids + 7168 / + 8192)
drop out and are never played -- a February play-off of 16 shows 7 ties (Discord 13.10.,
Micarodvzla22, the 0.2.1 Modpack world: 334 rows, 0.2.1 modules without fl26regs600).
"""
import os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mkleague as M
from modstudio import checks
from modstudio.siderini import SiderIni

N = 0

WORLD = "_FL26RecountTest"
INI = """[sider]
lua.enabled = 1
luajit.ext.enabled = 1
cpk.root = ".\\livecpk\\%s"
lua.module = "fl26caps.lua"
%s
lua.module = "fl26swiss.lua"
"""


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


class Game:
    def __init__(self, root):
        self.sider_dir = os.path.join(root, "SiderAddons")


def world(root, rows):
    """a world whose regulation table holds `rows` rows: reg 2 and its eight ties, then plain ids"""
    d = os.path.join(root, "SiderAddons", "livecpk", WORLD)
    ids = [2 + 1024 * k for k in range(9)] + list(range(3, 3 + rows - 9))
    regs = bytearray()
    for i in ids:
        r = bytearray(M.REG)
        r[M.R_ID:M.R_ID + 2] = i.to_bytes(2, "little")
        r[M.R_CID] = 2
        regs += r
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()):
        M.write_tables(d, bytearray(), regs, bytearray())
    with open(os.path.join(d, "fl26world.txt"), "w", encoding="utf-8") as f:
        f.write("world %s\nleague 140 cid=140 region=29 name=Test League\nuefa 140 1 0 0\n" % WORLD)


def problems(root, module_line):
    p = os.path.join(root, "SiderAddons", "sider.ini")
    with open(p, "w", encoding="utf-8") as f:
        f.write(INI % (WORLD, module_line))
    ini = SiderIni.load(p)
    return [r for r in checks.world_problems(Game(root), ini) if "regulations" in r[2]]


def main():
    root = tempfile.mkdtemp()
    try:
        world(root, 334)
        got = problems(root, ";lua.module = \"fl26regs600.lua\"")
        ok("334 rows without fl26regs600: reported", len(got) == 1 and got[0][0] == "err")
        ok("the report names the module and the count", got and "fl26regs600" in got[0][2] and "334" in got[0][2]
           and "300" in got[0][2])
        ok("it points at the modules page", got and got[0][3] == "Modules")
        ok("334 rows with fl26regs600 on: nothing", not problems(root, "lua.module = \"fl26regs600.lua\""))
        ok("loaded from a subfolder still counts", not problems(root, "lua.module = \"x\\fl26regs600.lua\""))
        world(root, 300)
        ok("300 rows without fl26regs600: nothing (the game counts them all)",
           not problems(root, ";lua.module = \"fl26regs600.lua\""))
        ok("recount_rows reads the module's number", checks.recount_rows(SiderIni.load(
            os.path.join(root, "SiderAddons", "sider.ini"))) == 300)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("1..%d" % N)


if __name__ == "__main__":
    main()
