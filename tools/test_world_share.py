"""A world shared to another PC must bring the players who get a generated face: the newfaces /
faceapp lines of fl26world.txt (fl26regen.lua reads them from modules\\fl26world.txt).  Without
them every new player looks the same (08.10., the modpack world).

    python tools/test_world_share.py

Export the world -> zip -> Install mods on another Sider folder: the world folder lands under its
own name, the world file lands in modules, removing the mod puts the old world file back.  A
SiderAddons copy whose world folder lost its world file takes the one in its modules folder.
The world's kits and scoreboards (content\\<server>\\<world> and their map lines) go along.
"""
import os, shutil, sys, tempfile, zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modstudio import installer as I
from modstudio.siderini import SiderIni

WORLD = "_FL26Share"
TEXT = ("# fl26world 1\nworld %s\nleague 1 x\nnewfaces 179673-179679 179681\nnewfaces3d 179700\n"
        "faceapp 179701:36912 179702:40510\n" % WORLD)


class Game:
    def __init__(self, sd):
        self.sider_dir = sd
        self.livecpk_dir = os.path.join(sd, "livecpk")
        self.modules_dir = os.path.join(sd, "modules")
        self.content_dir = os.path.join(sd, "content")


def put(p, text):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)


def sider(root):
    sd = os.path.join(root, "SiderAddons")
    put(os.path.join(sd, "sider.ini"), '[sider]\ncpk.root = ".\\livecpk\\Other"\nlua.module = "lib.lua"\n')
    os.makedirs(os.path.join(sd, "modules"))
    os.makedirs(os.path.join(sd, "livecpk"))
    return sd


def install(sd, src):
    work = tempfile.mkdtemp(prefix="ws_")
    parts = I.detect(I.unpack(src, work), "mod")
    worlds = [p for p in parts if p.kind == "world"]
    assert len(worlds) == 1 and worlds[0].name == WORLD, parts
    ini = SiderIni.load(os.path.join(sd, "sider.ini"))
    inst = I.Installer(Game(sd), ini, "shared", replace_lines=True)
    rec = inst.run(parts)
    ini.save(backup=False)
    shutil.rmtree(work, ignore_errors=True)
    return rec, ini


def main():
    tmp = tempfile.mkdtemp(prefix="fl26_ws_")
    try:
        assert I.face_players(os.devnull) == 0
        # ---- the PC that built it ----
        a = sider(os.path.join(tmp, "a"))
        put(os.path.join(a, "livecpk", WORLD, I.WORLD_FILE), TEXT)
        put(os.path.join(a, "livecpk", WORLD, "common", "etc", "pesdb", "Team.bin"), "x")
        put(os.path.join(a, "livecpk", WORLD, ".modstudio"), "x")
        zp = os.path.join(tmp, WORLD + ".zip")
        info = I.export_world(a, WORLD, zp)
        assert info["face_players"] == 7 + 1 + 1 + 2, info
        with zipfile.ZipFile(zp) as z:
            names = set(z.namelist())
            assert "SiderAddons/livecpk/%s/fl26world.txt" % WORLD in names, names
            assert I.WORLD_README in names and I.WORLD_INFO in names
            assert not any(n.endswith(".modstudio") for n in names)
            assert I.FACE_PACK in z.read(I.WORLD_README).decode()
        # ---- another PC: an old world file in modules, no face pack ----
        b = sider(os.path.join(tmp, "b"))
        old = "# fl26world 1\nworld _FL26Old\n"
        put(os.path.join(b, "modules", I.WORLD_FILE), old)
        assert I.face_pack_missing(b)
        rec, ini = install(b, zp)
        live = os.path.join(b, "modules", I.WORLD_FILE)
        assert open(live, encoding="utf-8").read() == TEXT
        assert os.path.isfile(os.path.join(b, "livecpk", WORLD, "common", "etc", "pesdb", "Team.bin"))
        assert rec["world"] == WORLD and rec["face_players"] == 11, rec
        assert ini.find("cpk.root", ".\\livecpk\\" + WORLD)
        roots = [e.value for e in ini.entries("cpk.root")]
        assert roots[0].endswith(WORLD), roots            # above the other roots
        # removal: the old world file is back, the world folder and its root line gone
        I.uninstall(Game(b), ini, rec)
        assert open(live, encoding="utf-8").read() == old
        assert not os.path.exists(os.path.join(b, "livecpk", WORLD))
        assert not ini.find("cpk.root", ".\\livecpk\\" + WORLD)
        # ---- a SiderAddons copy by hand: world file only in modules ----
        c = os.path.join(tmp, "copy", "SiderAddons")
        put(os.path.join(c, "livecpk", WORLD, "common", "etc", "pesdb", "Team.bin"), "x")
        put(os.path.join(c, "modules", I.WORLD_FILE), TEXT)
        d = sider(os.path.join(tmp, "d"))
        rec, _ini = install(d, os.path.join(tmp, "copy"))
        assert open(os.path.join(d, "modules", I.WORLD_FILE), encoding="utf-8").read() == TEXT
        assert os.path.isfile(os.path.join(d, "livecpk", WORLD, I.WORLD_FILE))
        # ---- kits and scoreboards: content\<server>\<world> and their map lines go along ----
        tag = I.OUR_LINE
        put(os.path.join(a, "content", "kit-server", "map.txt"),
            '100, "Mine\\Club"\n'
            '72001, "%s\\L One\\Club A"   %s L One/0 made\n'
            '72002, "_FL26Other\\L\\Club"   %s L/0 made\n'
            '#71599, "Modpack\\X\\Y"  # (switched off by FL26 Mod Studio)\n' % (WORLD, tag, tag))
        put(os.path.join(a, "content", "kit-server", WORLD, "L One", "Club A", "p1", "u0001p1.ftex"), "k")
        put(os.path.join(a, "content", "kit-server", "_FL26Other", "L", "Club", "p1", "x.ftex"), "o")
        put(os.path.join(a, "content", "scoreboard-server", "map_competitions.txt"),
            "263, %s\\L One   %s L One\n" % (WORLD, tag))
        put(os.path.join(a, "content", "scoreboard-server", WORLD, "L One", "board.dds"), "b")
        zk = os.path.join(tmp, WORLD + "-kits.zip")
        info = I.export_world(a, WORLD, zk)
        assert info["kits"] == 1 and info["scoreboards"] == 1, info
        with zipfile.ZipFile(zk) as z:
            km = z.read("SiderAddons/content/kit-server/map.txt").decode()
            assert km.strip() == '72001, "%s\\L One\\Club A"   %s L One/0 made' % (WORLD, tag), km
        # a club of the world wearing another pack's kit (SPFL26's Other Europe, a modpack): it goes too
        put(os.path.join(a, "livecpk", WORLD, "leaguebuilder-plan.json"),
            '{"leagues": [{"name": "L One", "teams": [72001, 1586, 72003, 100]}]}')
        with open(os.path.join(a, "content", "kit-server", "map.txt"), "a", encoding="utf-8") as fh:
            fh.write('1586, "Other Europe\\Salzburg"\n1586, "Old\\Salzburg"\n72003, "Gone\\Nowhere"\n')
        put(os.path.join(a, "content", "kit-server", "Other Europe", "Salzburg", "p1", "s.ftex"), "s")
        put(os.path.join(a, "content", "kit-server", "Mine", "Club", "p1", "m.ftex"), "m")
        info = I.export_world(a, WORLD, zk)
        assert info["kits"] == 3 and info.get("kits_borrowed") == 2, info     # 72001 ours, 1586, 100 lent
        with zipfile.ZipFile(zk) as z:
            names = set(z.namelist())
            km = z.read("SiderAddons/content/kit-server/map.txt").decode().splitlines()
            assert '1586, "%s\\_kits\\Other Europe\\Salzburg"   %s kit of Other Europe\\Salzburg' % (WORLD, tag) in km, km
            assert '100, "%s\\_kits\\Mine\\Club"   %s kit of Mine\\Club' % (WORLD, tag) in km, km
            assert not any("Gone" in l or "Old" in l for l in km), km
            assert "SiderAddons/content/kit-server/%s/_kits/Other Europe/Salzburg/p1/s.ftex" % WORLD in names, names
            assert "SiderAddons/content/kit-server/%s/L One/Club A/p1/u0001p1.ftex" % WORLD in names
            assert not any("_FL26Other" in n for n in names), names
            assert "SiderAddons/content/scoreboard-server/%s/L One/board.dds" % WORLD in names
            assert "Kits (3 clubs)" in z.read(I.WORLD_README).decode()
        # another PC with a kit line of its own for the same club: ours replaces it, removal brings it back
        f = sider(os.path.join(tmp, "f"))
        own = '72001, "Mine\\Old"\n'
        put(os.path.join(f, "content", "kit-server", "map.txt"), own)
        rec, ini = install(f, zk)
        km = open(os.path.join(f, "content", "kit-server", "map.txt"), encoding="utf-8").read()
        assert '72001, "%s\\L One\\Club A"' % WORLD in km and tag in km, km
        assert not any(l.startswith('72001, "Mine') for l in km.splitlines()), km
        assert os.path.isfile(os.path.join(f, "content", "kit-server", WORLD, "L One", "Club A", "p1", "u0001p1.ftex"))
        assert os.path.isfile(os.path.join(f, "content", "scoreboard-server", WORLD, "L One", "board.dds"))
        I.uninstall(Game(f), ini, rec)
        km = open(os.path.join(f, "content", "kit-server", "map.txt"), encoding="utf-8").read()
        assert '72001, "Mine\\Old"' in km and WORLD not in km, km
        # SPFL26's own Kit Server (common\kits.lua reads content\kits): the kits go there (GitHub #129)
        g = sider(os.path.join(tmp, "g"))
        put(os.path.join(g, "sider.ini"), '[sider]\nlua.module = "common\\kits.lua"\n')
        put(os.path.join(g, "content", "kits", "map.txt"), "")
        install(g, zk)
        assert os.path.isfile(os.path.join(g, "content", "kits", WORLD, "L One", "Club A", "p1", "u0001p1.ftex"))
        assert WORLD in open(os.path.join(g, "content", "kits", "map.txt"), encoding="utf-8").read()
        assert not os.path.exists(os.path.join(g, "content", "kit-server"))
        # ---- a world of the same name built on this PC is not overwritten ----
        e = sider(os.path.join(tmp, "e"))
        put(os.path.join(e, "livecpk", WORLD, I.WORLD_FILE), "world %s\n" % WORLD)
        try:
            install(e, zp)
            raise AssertionError("installed over a world built here")
        except ValueError:
            pass
        print("world share: ok")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
