"""python test_fl26cine.py -- sider/experimental/fl26cine.lua, the finals' cinematics, run in a Lua
of Python (lupa; skipped without it) against a world file of its own: the `cine` lines read (a
folder with spaces, a line with no folder left out), a match of a final taken from its folder --
every match with `all`, only the final (match_info 53) with `final` --, any other competition's
left to the next module, and nothing registered for a world with no `cine` line."""
import os, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
LUA = os.path.join(os.path.dirname(HERE), "sider", "experimental", "fl26cine.lua")


def load(world):
    from lupa import LuaRuntime
    L = LuaRuntime(unpack_returned_tuples=True)
    logs = []
    L.globals().log = logs.append
    m = L.execute(open(LUA, encoding="utf-8").read())
    d = tempfile.mkdtemp()
    sider = os.path.join(d, "sider")
    # the module joins the paths with backslashes: on Linux they are one file name
    open(sider + "\\modules\\fl26world.txt", "w", encoding="utf-8").write(world)
    regs = {}
    ctx = L.table_from({"sider_dir": sider + "\\"})
    ctx.register = lambda name, f: regs.__setitem__(name, f)
    m.init(ctx)
    return L, regs, logs, sider


def main():
    try:
        import lupa  # noqa: F401
    except ImportError:
        print("skip - no lupa (pip install lupa to run it)")
        return
    L, regs, logs, sider = load("world _FL26X\ncine 261 all LIB\ncine 255 final UEFA Champions League F\ncine 262 all \n")
    root = sider + "\\content\\cinematics\\"

    def ask(tid, mi, fn):
        c = L.table_from({"tournament_id": tid, "match_info": mi})
        k = regs["livecpk_make_key"](c, fn)
        return regs["livecpk_get_filepath"](c, fn, k) if k else None
    assert ask(261, 1, "common/demo/x.gani") == root + "LIB\\common\\demo\\x.gani"
    assert ask(255, 1, "a.fpk") is None and ask(255, 53, "a.fpk") == root + "UEFA Champions League F\\a.fpk"
    assert ask(262, 53, "a.fpk") is None and ask(11, 53, "a.fpk") is None
    assert any("reg 261 (every match) -- the scenes of LIB" in l for l in logs), logs
    print("cine lines: every match, the final only, another competition left to the next module")
    _L, regs, logs, _s = load("world _FL26X\n")
    assert not regs and any("no cine line" in l for l in logs), (regs, logs)
    print("no cine line: nothing registered")
    print("all passed")


if __name__ == "__main__":
    main()
