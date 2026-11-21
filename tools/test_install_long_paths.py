r"""python tools/test_install_long_paths.py

B400 (GigaPack beta 1, 10.11.): Import of _FL26Megapack-beta1.zip stopped with [Errno 2] on
trophies\...\winners_platform_common.fmdl. The longest name in the zip is 217 characters; Install
unpacked it into C:\Users\<name>\AppData\Local\Temp\fl26ms_xxxx\ (~52), 269 > 259, and Windows
without long paths switched on (LongPathsEnabled 0, the default) opens nothing past MAX_PATH. This
PC has long paths on, so every test went through.

The registry cannot be switched here, so the test plays Windows without long paths itself: an
audit hook (sys.addaudithook) refuses every open / mkdir / listdir / scandir / remove / rmdir /
copy whose path is past 259 characters and not \\?\ (os.walk passes over such a folder without a
word, as Windows does). Under it, on a deep temp folder:
  - unpack puts a 217-character member of a zip in place; detect finds the world in it
  - Install copies a file past MAX_PATH into the game folder, leaves out the trophies' GzsTool
    copies (#Win\x_fpk beside #Win\x.fpk) and keeps a _fpk folder with no .fpk beside it
  - too_long names the files the game could not open from a game folder that long, and the
    message says how long the game folder may be; with a short game folder there is none
  - Remove the mod deletes every file again, export_world zips the deep file and no GzsTool copy,
    and a leftover temp folder goes with long_path
lbtrophies: Build copies a trophy folder without the GzsTool copies (copy_ignore).

A fake Sider folder in a temp folder. No game.
"""
import os, shutil, sys, tempfile, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from modstudio import installer as I
from modstudio.siderini import SiderIni
import lbtrophies as T

N = 0
LP = "\\\\?\\"
WORLD = "_FL26LongPath"
# the GigaPack's longest file, as it was in the zip after SiderAddons/livecpk/<world>/
FIX = "common/demo/fixdemoobj/winners_platform_afc_cl/#Win/"
FPK = FIX + "winners_platform_afc_cl.fpk"
GZS = FIX + "winners_platform_afc_cl_fpk/Assets/pes16/demo/fixdemoobj/winners_platform_common/winners_platform_common.fmdl"
# a deep file that does go in the game (not a GzsTool copy): it must arrive past MAX_PATH
DEEP = ("common/" + "/".join("deep_folder_of_a_mod_%02d" % i for i in range(5))
        + "/a_file_that_goes_in_the_game_past_max_path.bin")
# a _fpk folder with no .fpk beside it: not GzsTool's copy of anything there, it stays
LONE = "common/demo/fixdemoobj/lone/#Win/lone_fpk/Assets/lone.fmdl"


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


class Game:
    def __init__(self, folder):
        self.folder = folder
        self.sider_dir = os.path.join(folder, "SiderAddons")
        self.livecpk_dir = os.path.join(self.sider_dir, "livecpk")
        self.modules_dir = os.path.join(self.sider_dir, "modules")
        self.content_dir = os.path.join(self.sider_dir, "content")


def put(p, data=b"x"):
    p = I.long_path(p)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(data)


def exists(p):
    return os.path.exists(I.long_path(p))


def files_under(d):
    return sorted(os.path.relpath(os.path.join(dp, f), I.long_path(d)).replace(os.sep, "/")
                  for dp, _dn, fn in os.walk(I.long_path(d)) for f in fn)


# ---- Windows without long paths ------------------------------------------------------------------
LEGACY = [False]
CHECKED = {"open": 1, "os.mkdir": 1, "os.listdir": 1, "os.scandir": 1, "os.remove": 1, "os.rmdir": 1,
           "os.rename": 2, "shutil.copyfile": 2, "shutil.copytree": 2, "os.chmod": 1, "os.utime": 1}


def legacy(event, args):
    n = CHECKED.get(event)
    if not LEGACY[0] or not n:
        return
    for a in args[:n]:
        if isinstance(a, (str, bytes, os.PathLike)):
            p = os.fsdecode(os.fspath(a))
            if len(p) > I.GAME_MAX and not p.startswith(LP):
                raise FileNotFoundError(2, "No such file or directory (MAX_PATH, %d characters)" % len(p), p)


def main():
    sys.addaudithook(legacy)
    tmp = tempfile.mkdtemp(prefix="fl26_b400_")
    try:
        # ---- the length check, plain ----
        # 80 characters: the trophy's .fpk fits, the deep file does not (nothing is written there)
        long_game = Game("C:\\" + "G" * 77)
        short_game = Game("C:\\G")
        src = os.path.join(tmp, "src")
        put(os.path.join(src, "fl26world.txt"), ("world %s\n" % WORLD).encode())
        put(os.path.join(src, "trophies", "516", "Knockout", FPK), b"FPK")
        put(os.path.join(src, "trophies", "516", "Knockout", GZS), b"UNPACKED")
        part = I.Part("world", src, WORLD)
        part.world_file = os.path.join(src, "fl26world.txt")
        paths = I.install_paths(long_game, part)
        ok("install_paths: the trophy's .fpk goes in, GzsTool's unpacked copy beside it does not",
           any(q.replace(os.sep, "/").endswith(FPK) for q in paths)
           and not any("_fpk" in q for q in paths))
        put(os.path.join(src, "common", DEEP[len("common/"):]), b"DEEP")
        over = I.too_long(long_game, part)
        want = os.path.join(long_game.livecpk_dir, WORLD, DEEP.replace("/", os.sep))
        ok("too_long: the deep file with this game folder (%d characters)" % len(want),
           over is not None and over[0] == 1 and over[1] == len(want) and over[2] == want and len(want) > I.GAME_MAX)
        room = len(long_game.folder) - (len(want) - I.GAME_MAX)
        text = I.too_long_text(long_game, over[0], over[1])
        ok("the message says how long the game folder may be (%d) and the limit" % room,
           ("at most %d characters" % room) in text and ("only up to %d" % I.GAME_MAX) in text)
        ok("too_long: none with a short game folder", I.too_long(short_game, part) is None)
        ok("gzs_leftover: only under #Win, only beside its .fpk",
           T.gzs_leftover(os.path.join(src, "trophies", "516", "Knockout", *FIX.split("/")[:-1]), "winners_platform_afc_cl_fpk")
           and not T.gzs_leftover(os.path.join(src, "trophies", "516", "Knockout", "common"), "demo"))
        ok("world_prune: a GzsTool copy outside the world's trophies folder is the world's own business",
           not I.world_prune(os.path.join("common", "x", "#Win"), os.path.join(tmp, "nowhere", "#Win"), "a_fpk"))

        # ---- the zip, the way the GigaPack's was laid out ----
        zp = os.path.join(tmp, "world.zip")
        inner = "SiderAddons/livecpk/%s/" % WORLD
        with zipfile.ZipFile(zp, "w") as z:
            z.writestr(inner + "fl26world.txt", "world %s\n" % WORLD)
            z.writestr(inner + "common/etc/pesdb/x.txt", "db")
            z.writestr(inner + "trophies/trophies.json", "{}")
            z.writestr(inner + "trophies/516/Knockout/" + FPK, "FPK")
            z.writestr(inner + "trophies/516/Knockout/" + GZS, "UNPACKED")
            z.writestr(inner + "trophies/516/Knockout/" + LONE, "LONE")
            z.writestr(inner + DEEP, "DEEP")
        longest = max(len(n) for n in zipfile.ZipFile(zp).namelist())
        ok("the zip's longest name is the GigaPack's (%d)" % longest,
           longest == 217 == len(inner + "trophies/516/Knockout/" + GZS) and len(inner + DEEP) < 217)

        # ---- from here on: Windows without long paths ----
        LEGACY[0] = True
        probe = os.path.join(tmp, "p" * 250, "file.bin")
        try:
            open(probe, "wb").close()
            refused = False
        except FileNotFoundError:
            refused = True
        ok("the test plays Windows without long paths: a plain path past 259 is refused", refused)

        # %TEMP% of a user with a long name: work + 217 is past MAX_PATH
        temp = os.path.join(tmp, "Users", "JUANJOSE_LONGNAME", "AppData", "Local", "Temp")
        os.makedirs(temp)
        work = tempfile.mkdtemp(prefix="fl26ms_", dir=temp)
        ok("the unpack folder + the zip's longest name is past MAX_PATH (%d)" % (len(work) + 1 + longest),
           len(work) + 1 + longest > I.GAME_MAX)
        top = I.unpack(zp, work)
        ok("unpack: every member is out, the 217-character one too",
           exists(os.path.join(work, (inner + "trophies/516/Knockout/" + GZS).replace("/", os.sep)))
           and len(files_under(work)) == 7)
        parts = I.detect(top, "world")
        worlds = [p for p in parts if p.kind == "world"]
        ok("detect: the world found, its files counted past MAX_PATH too (%s)" % [(p.kind, p.files) for p in parts],
           len(worlds) == 1 and worlds[0].name == WORLD and worlds[0].files == 7)

        game = Game(os.path.join(tmp, "Games", "FL 2027"))
        os.makedirs(game.modules_dir)
        os.makedirs(game.livecpk_dir)
        os.makedirs(game.content_dir)
        with open(os.path.join(game.sider_dir, "sider.ini"), "w", encoding="utf-8") as f:
            f.write('[sider]\nlua.module = "kserv.lua"\n')
        live = os.path.join(game.livecpk_dir, WORLD)
        ok("in this game folder the deep file is past MAX_PATH (%d)" % len(os.path.join(live, DEEP)),
           len(os.path.join(live, DEEP)) > I.GAME_MAX)
        lp = I.too_long(game, worlds[0])
        ok("too_long sees it before Install (%s)" % (lp[:2] if lp else None,),
           lp is not None and lp[0] == 1 and lp[2] == os.path.join(live, DEEP.replace("/", os.sep)))

        ini = SiderIni.load(os.path.join(game.sider_dir, "sider.ini"))
        inst = I.Installer(game, ini, "world.zip", replace_lines=True)
        rec = inst.run(parts)
        ini.save()
        got = files_under(live)
        ok("Install: the file past MAX_PATH is in the game", "%s" % DEEP in got)
        ok("Install: the trophy's .fpk is in, GzsTool's copy beside it is not: %s" % [g for g in got if "trophies" in g],
           "trophies/516/Knockout/" + FPK in got and not any("winners_platform_afc_cl_fpk" in g for g in got))
        ok("Install: a _fpk folder with no .fpk beside it stays", "trophies/516/Knockout/" + LONE in got)
        ok("Install: the world file in modules", exists(os.path.join(game.modules_dir, I.WORLD_FILE)))

        # export of the installed world: the deep file goes, no GzsTool copy
        out = os.path.join(tmp, "again.zip")
        I.export_world(game.sider_dir, WORLD, out)
        names = zipfile.ZipFile(out).namelist()
        ok("export_world: the deep file is in the zip, no GzsTool copy",
           inner + DEEP in names and inner + "trophies/516/Knockout/" + FPK in names
           and not any("winners_platform_afc_cl_fpk" in n for n in names))

        notes = I.uninstall(game, ini, rec)
        ok("Remove the mod: every file it brought deleted, the deep one too (%s)" % notes,
           not notes and not exists(os.path.join(live, DEEP)) and not files_under(live))

        # Build: a trophy folder goes into the world without the GzsTool copies
        trophy = os.path.join(tmp, "trophy")
        put(os.path.join(trophy, FPK.replace("/", os.sep)), b"FPK")
        put(os.path.join(trophy, GZS.replace("/", os.sep)), b"UNPACKED")
        LEGACY[0] = False                 # copytree's own walk is the plain one; Build's tmp is short here
        built = os.path.join(tmp, "built")
        shutil.copytree(trophy, built, ignore=T.copy_ignore)
        b = files_under(built)
        ok("lbtrophies.copy_ignore: the .fpk copied, GzsTool's unpacked copy not: %s" % b, b == [FPK])
        LEGACY[0] = True

        shutil.rmtree(I.long_path(work))
        ok("the unpack folder goes with long_path", not os.path.exists(I.long_path(work)))
    finally:
        LEGACY[0] = False
        shutil.rmtree(I.long_path(tmp), ignore_errors=True)
    print("test_install_long_paths: ok (%d)" % N)


if __name__ == "__main__":
    os.environ["FL26_LEDGER_STORE"] = tempfile.mkdtemp(prefix="fl26ledgers-")   # review 3, 18.11.2026: never the real history
    main()
