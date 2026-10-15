"""A scoreboard pack made for another world keys its league by that world's id: the FL26 Modpack
scoreboard zips on Discord carry "map line.txt" with "182, Modpack\\ENG4   # Sky Bet League Two",
and 182 is Liga Nacional Guatemala in today's Modpack world (League Two is 245).  quicksite
(15.10.) installed it and kept the game's own scoreboard.

    python tools/test_scoreboard_line.py

Install mods reads a loose "map line.txt" beside the server folder, and puts each competition line
on the competition its comment names in the world in the game; a name the world has not is kept
as it is and reported; with no world names given (a world zip) the lines stay as they are.
"""
import os, shutil, sys, tempfile, zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modstudio import installer as I
from modstudio.siderini import SiderIni
from test_world_share import Game, put, sider

COMPS = {182: "Liga Nacional Guatemala", 245: "Sky Bet League Two", 17: "Premier League"}
ok = 0


def check(cond, what):
    global ok
    print(("ok   " if cond else "FAIL ") + what)
    ok += bool(cond)
    return cond


def pack(root, line, name="Scoreboard-Sky-Bet-League-Two.zip"):
    z = os.path.join(root, name)
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("scoreboard-server/Modpack/ENG4/preview.dds", b"x")
        f.writestr("map line.txt", line)
    return z


def install(sd, src, comps):
    work = tempfile.mkdtemp(prefix="sb_")
    parts = I.detect(I.unpack(src, work), "mod")
    ini = SiderIni.load(os.path.join(sd, "sider.ini"))
    inst = I.Installer(Game(sd), ini, "sb", replace_lines=True, comps=comps)
    rec = inst.run(parts)
    shutil.rmtree(work, ignore_errors=True)
    return parts, rec


def lines(sd):
    p = os.path.join(sd, "content", "scoreboard-server", "map_competitions.txt")
    return [l.strip() for l in open(p, encoding="utf-8") if l.strip() and not l.startswith("#")] if os.path.exists(p) else []


def main():
    tmp = tempfile.mkdtemp(prefix="fl26_sb_")
    try:
        # 1. the Discord zip on a game whose map has other lines already
        sd = sider(os.path.join(tmp, "a"))
        put(os.path.join(sd, "content", "scoreboard-server", "map_competitions.txt"), "17, EPL\\Board   # Premier League\n")
        parts, rec = install(sd, pack(tmp, "182, Modpack\\ENG4   # Sky Bet League Two\r\n"), COMPS)
        check(any(p.kind == "content" and p.map_line for p in parts), "map line.txt is found beside scoreboard-server")
        got = lines(sd)
        check(any(l.startswith("245,") and "ENG4" in l for l in got), "League Two goes on 245, its id in this world: %s" % got)
        check(not any(l.startswith("182,") for l in got), "nothing lands on 182 (Guatemala)")
        check(any(l.startswith("17,") for l in got), "the line that was there stays")
        check(os.path.exists(os.path.join(sd, "content", "scoreboard-server", "Modpack", "ENG4", "preview.dds")), "the board's files are copied")
        check(not rec.get("unmatched"), "nothing unmatched")
        # 2. no map file yet in the game
        sd = sider(os.path.join(tmp, "b"))
        install(sd, pack(tmp, "182, Modpack\\ENG4   # Sky Bet League Two\n"), COMPS)
        check([l.split(",")[0] for l in lines(sd)] == ["245"], "a new map file gets the line on 245: %s" % lines(sd))
        # 3. a league this world has not: kept, reported
        sd = sider(os.path.join(tmp, "c"))
        _p, rec = install(sd, pack(tmp, "300, Modpack\\XYZ   # Some Other League\n", "x.zip"), COMPS)
        check(rec.get("unmatched") == ["Some Other League"], "an unknown league is reported: %s" % rec.get("unmatched"))
        check([l.split(",")[0] for l in lines(sd)] == ["300"], "and its line kept as it was")
        # 4. no world names (a world zip): the line as the pack has it
        sd = sider(os.path.join(tmp, "d"))
        install(sd, pack(tmp, "182, Modpack\\ENG4   # Sky Bet League Two\n", "y.zip"), None)
        check([l.split(",")[0] for l in lines(sd)] == ["182"], "without world names the pack's id stays")
        # 5. a pack with its own map_competitions.txt is matched the same way
        sd = sider(os.path.join(tmp, "e"))
        z = os.path.join(tmp, "own.zip")
        with zipfile.ZipFile(z, "w") as f:
            f.writestr("scoreboard-server/Modpack/ENG4/preview.dds", b"x")
            f.writestr("scoreboard-server/map_competitions.txt", "182, Modpack\\ENG4   # sky bet  league two\n")
        install(sd, z, COMPS)
        check([l.split(",")[0] for l in lines(sd)] == ["245"], "the pack's own map file too (name case and spaces ignored): %s" % lines(sd))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("%d/11" % ok)
    return 0 if ok == 11 else 1


if __name__ == "__main__":
    sys.exit(main())
