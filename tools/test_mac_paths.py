"""python tools/test_mac_paths.py -- B288 (evannoteven 29.10.2026): Mod Studio run from source on a
Mac (the game in CrossOver) read sider.ini's cpk.root lines, written with backslashes, as one file
name: every content folder "missing on disk" and the world in the game "none". A sider.ini path
now takes the system's separator (siderini.on_disk); on Windows nothing changes.
"""
import ntpath, os, posixpath, sys, types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modstudio import modules, siderini

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def as_system(path, sep):
    fake = types.SimpleNamespace(**{k: getattr(os, k) for k in dir(os) if not k.startswith("__")})
    fake.path, fake.sep = path, sep
    siderini.os = modules.os = fake


mac = "/Volumes/Steam PC Games/Games/Football Life 26 Test/SiderAddons"
win = r"E:\instalacija\SiderAddons"
try:
    as_system(posixpath, "/")
    ok("a Mac: a world in livecpk, written with backslashes",
       siderini.root_path(mac, r".\livecpk\_FL26M2400S") == mac + "/livecpk/_FL26M2400S")
    ok("a Mac: a name with spaces",
       siderini.root_path(mac, r".\livecpk\FL26 Regen Faces") == mac + "/livecpk/FL26 Regen Faces")
    ok("a Mac: forward slashes too",
       siderini.root_path(mac, "./content/Stadium_CornerFlag") == mac + "/content/Stadium_CornerFlag")
    ok("a Mac: a module in a subfolder",
       modules.path_of(r"kits\kserv.lua", mac + "/modules") == mac + "/modules/kits/kserv.lua")
    as_system(ntpath, "\\")
    ok("Windows: as before", siderini.root_path(win, r".\livecpk\_FL26M2400S") == win + r"\livecpk\_FL26M2400S"
       and siderini.root_path(win, "./livecpk/_FL26M2400S") == win + r"\livecpk\_FL26M2400S")
    ok("Windows: an absolute root stays", siderini.root_path(win, r"D:\mods\x") == r"D:\mods\x")
    ok("Windows: a module", modules.path_of("kits/kserv.lua", win + r"\modules") == win + r"\modules\kits\kserv.lua")
finally:
    siderini.os = modules.os = os
print("1..%d" % N)
