"""python test_rigcheck.py -- rigcheck.py tells a test game that runs the pack's modules from one
that does not (B408: a module of ours in the test game that the pack did not have)"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rigcheck

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def w(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8", newline="\n").write(s)


def rig(d, lines, files, fl27=True):
    game = os.path.join(d, "game")
    if fl27:
        w(os.path.join(game, "FL_2027.exe"), "")
    w(os.path.join(game, "SiderAddons", "sider.ini"), "\n".join(lines) + "\n")
    for f, s in files.items():
        w(os.path.join(game, "SiderAddons", "modules", f), s)
    return game


d = tempfile.mkdtemp(prefix="fl26-rig-")
try:
    pack = os.path.join(d, "pack")
    w(os.path.join(pack, "modules.txt"), "fl26caps\nfl26match\nfl26chain\n")
    for f, s in {"fl26caps.lua": "caps", "fl26caps.fl27.lua": "caps27", "fl26match.lua": "m26",
                 "fl26match.fl27.lua": "m27", "fl26chain.lua": "chain", "fl26match.dll": "dll"}.items():
        w(os.path.join(pack, "modules", f), s)
    good = ['lua.module = "fl26caps.lua"', 'lua.module = "fl26match.lua"', 'lua.module = "fl26regions.lua"',
            'lua.module = "fl26chain.lua"', '\tlua.module = "common\\kits.lua"', 'lua.module = "ML_FastForward.lua"']
    files = {"fl26caps.lua": "caps27", "fl26match.lua": "m27", "fl26chain.lua": "chain", "fl26match.dll": "dll"}
    q = lambda *a: rigcheck.check(*a, log=lambda s: None)
    ok("the pack's modules (FL 2027 copies), a world's fl26regions and others' modules: no difference",
       q(rig(os.path.join(d, "a"), good, files), pack) == [])
    extra = good + ['lua.module = "fl26appcap.lua"']
    ok("a module of ours the pack does not have (B408) is a difference",
       any("fl26appcap.lua is loaded but is not in the pack" in b for b in q(rig(os.path.join(d, "b"), extra, files), pack)))
    off = [l for l in good if "fl26match" not in l] + [';lua.module = "fl26match.lua"']
    ok("a module of the pack without its line is a difference",
       any("fl26match.lua of the pack has no lua.module line" in b for b in q(rig(os.path.join(d, "c"), off, files), pack)))
    ok("an FL26 game takes the plain copy: the FL 2027 one there is a difference",
       any("fl26caps.lua is not the pack's" in b for b in q(rig(os.path.join(d, "e"), good, files, fl27=False), pack)))
    ok("a DLL that is not the pack's is a difference",
       any("fl26match.dll is not the pack's" in b
           for b in q(rig(os.path.join(d, "f"), good, dict(files, **{"fl26match.dll": "old"})), pack)))
    swap = [good[1], good[0]] + good[2:]
    ok("our modules in another order are a difference",
       any("another order" in b for b in q(rig(os.path.join(d, "g"), swap, files), pack)))
    g = rig(os.path.join(d, "h"), good, files)
    w(os.path.join(g, "SiderAddons", "sider.log"), "Loading module: fl26caps.lua ...\n")
    ok("--log: a sider.log that loaded other modules is a difference",
       any("sider.log loaded" in b for b in q(g, pack, True)))
finally:
    shutil.rmtree(d, ignore_errors=True)
print("%d cases passed" % N)
