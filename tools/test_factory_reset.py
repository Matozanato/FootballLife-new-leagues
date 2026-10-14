r"""python test_factory_reset.py -> Put Sider back as before Mod Studio (0.2.4): every file Mod Studio
changed gets its oldest kept copy back, what it brought in is taken out, nothing is deleted, and
undo puts Sider back exactly as it was before the reset"""
import os, sys, tempfile, time, types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modstudio import backups, factory, installer as I


def write(p, text):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(text)


def read(p):
    return open(p, encoding="utf-8").read()


def tree(sd):
    out = {}
    for top, dirs, files in os.walk(sd):
        if top == sd:
            dirs[:] = [d for d in dirs if d != backups.HOME]
        for f in files:
            p = os.path.join(top, f)
            out[os.path.relpath(p, sd)] = open(p, "rb").read()
        for d in dirs:
            out[os.path.relpath(os.path.join(top, d), sd) + os.sep] = b""
    return out


with tempfile.TemporaryDirectory() as t:
    sd = os.path.join(t, "SiderAddons")
    game = types.SimpleNamespace(sider_dir=sd, livecpk_dir=os.path.join(sd, "livecpk"),
                                 content_dir=os.path.join(sd, "content"), modules_dir=os.path.join(sd, "modules"))
    # Sider as the player had it
    write(os.path.join(sd, "sider.ini"), "cpk.root = .\\livecpk\\UserMod\nlua.module = \"camera.lua\"\n"
                                         "; lua.module = \"fl26old.lua\"\ncpk.root = \".\\livecpk\\_FL26Old\"\n")
    write(os.path.join(sd, "livecpk", "_FL26Old", "fl26world.txt"), "an old world")
    write(os.path.join(sd, "modules", "camera.lua"), "camera, theirs")
    write(os.path.join(sd, "modules", "lib", "CommonLib.lua"), "commonlib, theirs")
    write(os.path.join(sd, "livecpk", "UserMod", "a.txt"), "their mod")
    write(os.path.join(sd, "content", "kit-server", "map.txt"), "1, theirs\n")
    # Mod Studio at work
    backups.snapshot(os.path.join(sd, "sider.ini"), "League Builder: install the modules", sd)
    time.sleep(1.1)
    write(os.path.join(sd, "sider.ini"), "cpk.root = .\\livecpk\\MyWorld\nlua.module = \"fl26caps.lua\"\n")
    write(os.path.join(sd, "sider.ini.before-builder"), "a later copy: not the oldest")
    os.makedirs(os.path.join(sd, "modules", "before-builder-1"))
    os.replace(os.path.join(sd, "modules", "camera.lua"), os.path.join(sd, "modules", "before-builder-1", "camera.lua"))
    write(os.path.join(sd, "modules", "camera.lua"), "camera, ours")
    write(os.path.join(sd, "modules", "lib", "CommonLib.lua.before-builder"), "commonlib, theirs")
    write(os.path.join(sd, "modules", "lib", "CommonLib.lua"), "commonlib + our leagues")
    write(os.path.join(sd, "modules", "fl26world.txt"), "world MyWorld")
    write(os.path.join(sd, "modules", "fl26caps.lua.before-builder"), "a caps module of theirs")
    write(os.path.join(sd, "modules", "fl26caps.lua"), "caps, ours")
    write(os.path.join(sd, "livecpk", "MyWorld", "fl26world.txt"), "world MyWorld")
    write(os.path.join(sd, "livecpk", "Modpack", ".modstudio"), "FL26 Modpack")
    write(os.path.join(sd, "content", "kit-server", "MyWorld", "900001", "kit.png"), "kit")
    # a kit of the world that a mod replaced later: it has a restore point, it still goes with the world
    backups.snapshot(os.path.join(sd, "content", "kit-server", "MyWorld", "900001", "kit.png"), "replaced by x", sd)
    write(os.path.join(sd, "content", "kit-server", "MyWorld", "900001", "kit.png"), "kit 2")
    write(os.path.join(sd, "content", "kit-server", "map.txt.before-builder"), "1, theirs\n")
    write(os.path.join(sd, "content", "kit-server", "map.txt"), "1, theirs\n900001, MyWorld  -- FL26\n")
    write(os.path.join(sd, "content", "ball-server", "balls", "nice", "ball.png"), "ball")
    I._save(sd, [{"name": "nice ball", "time": "20261014-200000", "parts": [],
                  "created": [os.path.join("content", "ball-server", "balls", "nice", "ball.png")],
                  "replaced": [], "ini": [], "map_added": {}, "map_removed": {}}])

    before = tree(sd)
    p = factory.plan(game)
    assert sorted(p["worlds"]) == ["Modpack", "MyWorld", "_FL26Old"], p["worlds"]
    assert p["mods"] == ["nice ball"], p["mods"]
    folder = factory.reset(game)

    assert read(os.path.join(sd, "sider.ini")).startswith("cpk.root = .\\livecpk\\UserMod"), read(os.path.join(sd, "sider.ini"))
    assert read(os.path.join(sd, "modules", "camera.lua")) == "camera, theirs"
    assert read(os.path.join(sd, "modules", "lib", "CommonLib.lua")) == "commonlib, theirs"
    assert read(os.path.join(sd, "content", "kit-server", "map.txt")) == "1, theirs\n"
    # a copy of a module of ours is of an older Mod Studio: it goes out, it does not come back
    assert not os.path.exists(os.path.join(sd, "modules", "fl26caps.lua"))
    ini = read(os.path.join(sd, "sider.ini"))
    assert "fl26" not in ini.lower() and "camera.lua" in ini and "UserMod" in ini, ini
    assert read(os.path.join(sd, "livecpk", "UserMod", "a.txt")) == "their mod"
    for gone in ("sider.ini.before-builder", "modules\\fl26world.txt", "modules\\before-builder-1",
                 "modules\\lib\\CommonLib.lua.before-builder", "livecpk\\MyWorld", "livecpk\\Modpack",
                 "content\\kit-server\\MyWorld", "content\\kit-server\\map.txt.before-builder",
                 "content\\ball-server"):
        assert not os.path.exists(os.path.join(sd, gone)), gone
    assert I.records(sd) == []
    assert factory.resets(sd) == [folder]
    # nothing deleted: the world is in the reset folder
    assert os.path.isfile(os.path.join(folder, "files", "livecpk", "MyWorld", "fl26world.txt"))

    factory.undo(sd, folder)
    after = tree(sd)
    assert after == before, sorted(set(after.items()) ^ set(before.items()))
    assert [r["name"] for r in I.records(sd)] == ["nice ball"]
    assert factory.resets(sd) == []

    # a Sider Mod Studio never touched: nothing to do, and nothing is changed
    sd2 = os.path.join(t, "clean")
    write(os.path.join(sd2, "sider.ini"), "x\n")
    g2 = types.SimpleNamespace(sider_dir=sd2, livecpk_dir=os.path.join(sd2, "livecpk"),
                               content_dir=os.path.join(sd2, "content"), modules_dir=os.path.join(sd2, "modules"))
    p2 = factory.plan(g2)
    assert not p2["back"] and not p2["out"], p2
print("factory reset: ok")
