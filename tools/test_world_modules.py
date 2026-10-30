"""python tools/test_world_modules.py

B177 (Vran 20.10.): fl26regions and fl26regnames are a world's own modules (lbpack.PER_WORLD: made
at its Build in livecpk\\<world>\\modules, not in the pack). Home said "switched off: fl26regions,
fl26regnames" and sent the player to Install now, which passed them by. Now Home counts them only
when the world in the game brings them, Install now puts that world's in and switches them on, and
the Switch on of a world without them switches another world's off.
"""
import os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import leaguebuilder as B
from modstudio import checks

N = 0
NL = chr(10)

INI = "[sider]" + NL + "lua.enabled = 1" + NL + "luajit.ext.enabled = 1" + NL + 'lua.module = "kserv.lua"' + NL


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


def put(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def live(game, m):
    t = open(os.path.join(game, "SiderAddons", "sider.ini"), encoding="utf-8-sig").read()
    return (NL + 'lua.module = "%s.lua"' % m) in t


def world(game, name, mods):
    d = os.path.join(game, "SiderAddons", "livecpk", name)
    put(os.path.join(d, "fl26world.txt"), "# fl26world 1" + NL + "world " + name + NL)
    for m in mods:
        put(os.path.join(d, "modules", m + ".lua"), "-- %s of %s" % (m, name))


def in_game(game, name):
    put(os.path.join(game, "SiderAddons", "modules", "fl26world.txt"), "# fl26world 1" + NL + "world " + name + NL)


def main():
    tmp = tempfile.mkdtemp()
    old_pack = B.pack_dir
    try:
        pack = os.path.join(tmp, "pack")
        for f in ("fl26caps.lua", "fl26rank.lua"):
            put(os.path.join(pack, "modules", f), "-- " + f)
        put(os.path.join(pack, "modules.txt"), "fl26caps" + NL + "fl26rank" + NL + "fl26regions" + NL
            + "fl26regnames" + NL)
        put(os.path.join(pack, "retired.txt"), "")
        B.pack_dir = lambda: pack
        game = os.path.join(tmp, "game")
        put(os.path.join(game, "SiderAddons", "sider.ini"), INI)
        os.makedirs(os.path.join(game, "SiderAddons", "modules"))
        open(os.path.join(game, "FL_2026.exe"), "wb").close()
        g = G(game)
        quiet = lambda s: None

        # no world in the game: the world modules are not counted, Install now does not ask for them
        B.install_modules(game, log=quiet, settle=0)
        st = checks.modules_state(g)
        ok("no world: Home counts the pack's modules only", st["total"] == 2 and checks.modules_ok(st))
        ok("no world: nothing said about fl26regions", not any("fl26reg" in x for k in ("missing", "off")
                                                              for x in st[k]))

        # Vran: the world in the game has them, SiderAddons\modules has not (lines off or none)
        world(game, "_FL26A", ["fl26regions", "fl26regnames"])
        in_game(game, "_FL26A")
        st = checks.modules_state(g)
        ok("world with them: Home counts them", st["total"] == 4 and not checks.modules_ok(st))
        ok("world with them: missing, so Install now is the way",
           {"fl26regions.lua", "fl26regnames.lua"} <= set(st["missing"]) and {"fl26regions", "fl26regnames"} <= set(st["off"]))
        said = []
        B.install_modules(game, log=said.append, settle=0)
        ok("Install now puts the world's in", open(os.path.join(g.modules_dir, "fl26regions.lua")).read()
           == "-- fl26regions of _FL26A" and any("of the world in the game" in l for l in said))
        ok("Install now switches them on", live(game, "fl26regions") and live(game, "fl26regnames"))
        ok("Home agrees: all in place", checks.modules_ok(checks.modules_state(g)))

        # an older copy of them (another world's) in modules: changed, Install now replaces it
        put(os.path.join(g.modules_dir, "fl26regnames.lua"), "-- fl26regnames of another world")
        st = checks.modules_state(g)
        ok("another world's copy counts as changed", "fl26regnames.lua" in st["changed"])
        B.install_modules(game, log=quiet, settle=0)
        ok("... and Install now puts the world's back", checks.modules_ok(checks.modules_state(g)))

        # a world without them goes on: another world's switched off, Home does not ask for them
        world(game, "_FL26B", [])
        in_game(game, "_FL26B")
        gone = B.stale_world_modules(game, {"fl26regions", "fl26regnames"} - set(B.world_modules(game, "_FL26B")),
                                     "_FL26B", quiet)
        ok("Switch on of a world without them switches them off", sorted(gone) == ["fl26regions", "fl26regnames"]
           and not live(game, "fl26regions") and not live(game, "fl26regnames"))
        ok("... and leaves the other lines", live(game, "kserv") and live(game, "fl26caps"))
        st = checks.modules_state(g)
        ok("world without them: Home is fine", checks.modules_ok(st) and st["total"] == 2)
        B.install_modules(game, log=quiet, settle=0)
        ok("world without them: Install now does not switch the stale ones on",
           not live(game, "fl26regions") and not live(game, "fl26regnames"))
        ok("nothing to switch off, nothing written", B.stale_world_modules(game, set(), "_FL26B", quiet) == [])

        # back to the world with them
        in_game(game, "_FL26A")
        B.ensure_modules(game, ["fl26caps", "fl26rank", "fl26regions", "fl26regnames"],
                         list(B.world_modules(game)), quiet)
        ok("its own Switch on brings them back on", live(game, "fl26regions") and live(game, "fl26regnames"))

        # B295 (pepponeee98 30.10.): "_FL26MyWorld 1.4B" in the game beside "_FL26MyWorld" -- the name
        # was read up to its space, so Home held 1.4B's modules against the other world's
        for w in ("_FL26MyWorld", "_FL26MyWorld 1.4B"):
            world(game, w, ["fl26regions", "fl26regnames"])
        in_game(game, "_FL26MyWorld 1.4B")
        for m in ("fl26regions", "fl26regnames"):
            shutil.copy2(os.path.join(g.livecpk_dir, "_FL26MyWorld 1.4B", "modules", m + ".lua"),
                         os.path.join(g.modules_dir, m + ".lua"))
        ok("a world named with a space is the live one, all of its name",
           B.live_world(game) == "_FL26MyWorld 1.4B" and B.is_live("_FL26MyWorld 1.4B", game)
           and not B.is_live("_FL26MyWorld", game))
        ok("... Home finds its modules in place after its Switch on", checks.modules_ok(checks.modules_state(g)))
        B.install_modules(game, log=quiet, settle=0)
        ok("... and Install now keeps its own, not the other world's",
           open(os.path.join(g.modules_dir, "fl26regions.lua")).read() == "-- fl26regions of _FL26MyWorld 1.4B")
    finally:
        B.pack_dir = old_pack
        shutil.rmtree(tmp, ignore_errors=True)
    print("1..%d" % N)


if __name__ == "__main__":
    main()
