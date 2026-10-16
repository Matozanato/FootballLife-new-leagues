r"""python tools/test_install_stop.py

B29 (ELBastos, 14.10.): Install mods of a big zip (the Modpack) stopped half way -- Mod Studio
closed while it seemed to hang -- and left kit and scoreboard map lines pointing at folders that
were never copied (Kits: 653 lines with problems). Now:
  - Install mods copies every part's files first and merges the map lines only after the last
    copy, so a stop during the copy leaves no line of the zip in a map;
  - Diagnostics names the zip (or the world) whose lines point at files that are not there and
    says to install it again (a world built on this PC: Build it again).

A fake Sider folder in a temp folder; the stop is an exception from the last file copy. No game.
"""
import os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from modstudio import installer as I, checks as C
from modstudio.siderini import SiderIni

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


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
    put(os.path.join(sd, "sider.ini"), '[sider]\nlua.module = "kserv.lua"\nlua.module = "ScoreboardServer.lua"\n')
    os.makedirs(os.path.join(sd, "modules"))
    os.makedirs(os.path.join(sd, "livecpk"))
    put(os.path.join(sd, "content", "kit-server", "map.txt"), '100, "Mine\\Club"\n')
    put(os.path.join(sd, "content", "kit-server", "Mine", "Club", "order.ini"), "x")
    os.makedirs(os.path.join(sd, "content", "scoreboard-server"))
    return sd


def the_zip(root):
    """a pack of kits and scoreboards, unpacked: SiderAddons\\content\\<server> with its map"""
    c = os.path.join(root, "Pack", "SiderAddons", "content")
    lines = []
    for k, club in enumerate(("A", "B", "C")):
        put(os.path.join(c, "kit-server", "Pack", "L", club, "order.ini"), "x")
        put(os.path.join(c, "kit-server", "Pack", "L", club, "p1", "u%d.ftex" % k), "k")
        lines.append('7200%d, "Pack\\L\\%s"' % (k, club))
    put(os.path.join(c, "kit-server", "map.txt"), "\n".join(lines) + "\n")
    put(os.path.join(c, "scoreboard-server", "Pack", "L", "config.txt"), "x")
    put(os.path.join(c, "scoreboard-server", "map_competitions.txt"), "263, Pack\\L\n")
    return os.path.join(root, "Pack")


class Stop(Exception):
    pass


def install(sd, src, stop_at=None):
    """Install mods of src; stop_at: the copy (1, 2 ...) that raises (Mod Studio closed then).
    The files it copied, in order"""
    work = tempfile.mkdtemp(prefix="stop_")
    parts = I.detect(I.unpack(src, work), "mod")
    ini = SiderIni.load(os.path.join(sd, "sider.ini"))
    inst = I.Installer(Game(sd), ini, "Pack.zip", replace_lines=True)
    real, done = inst.copy_file, []

    def copy(a, b):
        if len(done) + 1 == stop_at:
            raise Stop()
        done.append(b)
        real(a, b)
    inst.copy_file = copy
    try:
        inst.run(parts)
    except Stop:
        pass
    shutil.rmtree(work, ignore_errors=True)
    return done


def map_lines(sd, server, name):
    p = os.path.join(sd, "content", server, name)
    return [l.strip() for l in open(p, encoding="utf-8") if l.strip() and not l.startswith("#")] \
        if os.path.exists(p) else []


def main():
    tmp = tempfile.mkdtemp(prefix="fl26_stop_")
    try:
        src = the_zip(tmp)
        # the whole install: the lines and the files
        a = sider(os.path.join(tmp, "a"))
        copies = install(a, src)
        last = max(i for i, d in enumerate(copies, 1) if not os.path.basename(d).startswith("map"))
        ok("a whole install: 3 kit lines and the scoreboard line",
           len(map_lines(a, "kit-server", "map.txt")) == 4
           and map_lines(a, "scoreboard-server", "map_competitions.txt") == ["263, Pack\\L"])
        ok("Diagnostics: nothing wrong with the maps", C.map_problems(Game(a)) == [])

        # stopped at the last file it copies: no line of the zip in any map
        b = sider(os.path.join(tmp, "b"))
        install(b, src, stop_at=last)       # the last file of the zip (a map file is no file of it)
        ok("B29: an install stopped at its last copy wrote no kit line: %s" % map_lines(b, "kit-server", "map.txt"),
           map_lines(b, "kit-server", "map.txt") == ['100, "Mine\\Club"'])
        ok("B29: nor a scoreboard line", map_lines(b, "scoreboard-server", "map_competitions.txt") == [])

        # a game an older Mod Studio left that way: Diagnostics says which zip, and what to do
        shutil.rmtree(os.path.join(a, "content", "kit-server", "Pack", "L", "B"))
        shutil.rmtree(os.path.join(a, "content", "kit-server", "Pack", "L", "C"))
        rows = C.map_problems(Game(a))
        ok("Diagnostics: 2 lines that Pack.zip added point at files that are not there: %s" % rows,
           len(rows) == 1 and rows[0][0] == "err" and rows[0][3] == "Install"
           and "2 line(s) that Pack.zip added" in rows[0][2] and "Install that zip again" in rows[0][2])

        # a world's own lines (our tag): a world from a zip -> install it again; built here -> Build
        tag = I.OUR_LINE
        with open(os.path.join(a, "content", "kit-server", "map.txt"), "w", encoding="utf-8") as f:
            f.write('100, "Mine\\Club"\n72101, "_FL26Zip\\L\\A"   %s L/0 made\n'
                    '72201, "_FL26Here\\L\\A"   %s L/0 made\n72202, "_FL26Here\\L\\B"   %s L/1 made\n'
                    '555, "Somebody\\Else"\n' % (tag, tag, tag))
        put(os.path.join(a, "livecpk", "_FL26Zip", ".modstudio"), "x")
        os.makedirs(os.path.join(a, "livecpk", "_FL26Here"))
        rows = {r[2]: r for r in C.map_problems(Game(a))}
        zipped = [r for t, r in rows.items() if "_FL26Zip" in t]
        here = [r for t, r in rows.items() if "_FL26Here" in t]
        other = [r for t, r in rows.items() if "not in the library" in t]
        ok("the world from a zip: 1 line, install the world's zip again: %s" % zipped,
           len(zipped) == 1 and "1 line(s) of the world _FL26Zip" in zipped[0][2]
           and "zip again" in zipped[0][2] and zipped[0][3] == "Install")
        ok("the world built here: 2 lines, Build it again: %s" % here,
           len(here) == 1 and "2 line(s) of the world _FL26Here" in here[0][2] and here[0][3] == "Build")
        ok("a line of your own is the usual warning: %s" % other,
           len(other) == 1 and other[0][0] == "warn" and "Somebody" in other[0][2])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("test_install_stop: ok (%d)" % N)


if __name__ == "__main__":
    main()
