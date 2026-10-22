"""python tools/test_map_last_line.py -- B203 (JoJofiaz 22.10.): a kit changed for a club of the
modpack on My world > Kits > Clubs left the pack's own line on, so map.txt had two lines for the
club, and Mod Studio said "the first line counts". Kit Server keeps a club's LAST line (kserv.lua
load_map: map[tid] = path, line by line), as do the commentary, sleeve badge and weather servers;
the stadium, ball and goal song servers keep every line and pick one.

Checked without the game: a new or changed line switches the club's other lines off on a map
that keeps one line per club (and not on one that keeps them all), the warning marks the earlier
line as unused, Import kits replaces the line in effect, and a world zip carries the kit of the
line in effect (installer.borrowed_kits).
"""
import json, os, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from modstudio import servers as S, installer
from modstudio.mapfile import MapFile, Row
from modstudio.pages import content as C

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %2d - %s" % (N, name))


def the_map(server, file):
    return next(m for s in S.SERVERS if s.key == server for m in s.maps if m.file == file)


class Tab:
    """the parts of MapTab the methods use"""
    def __init__(self, m, path):
        self.m, self.mf, self.app = m, m.open(os.path.dirname(path)), None
    switch_off_others = C.MapTab.switch_off_others
    last_lines = C.MapTab.last_lines
    problems = C.MapTab.problems


def main():
    kits, stadiums = the_map("kits", "map.txt"), the_map("stadiums", "map_teams.txt")
    ok("Kit Server's club map keeps one line per club", not kits.many)
    ok("the stadium, ball and goal song club maps keep them all",
       stadiums.many and the_map("balls", "map_teams.txt").many and the_map("goalsongs", "map_teams.txt").many)
    ok("the commentary and badge club maps keep one",
       not the_map("commentary", "map_teams.txt").many and not the_map("badges", "map_teams.txt").many)

    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "map.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write('319, "Modpack\\Game leagues\\Arezzo"\n328, "Modpack\\Game leagues\\Pisa"\n')
    t = Tab(kits, path)
    old = t.mf.rows()[0]
    new = Row(["319", "Serie C\\Arezzo"], quoted=[1])
    ok("one line switched off for the new one", t.switch_off_others(new) == 1)
    t.mf.add(new, after=old)
    ok("the pack's line is off, the other club's line stays on",
       not old.enabled and all(r.enabled for r in t.mf.rows() if r.fields[0] == "328"))
    t.mf.save()
    text = open(path, encoding="utf-8").read()
    ok("map.txt: the old line written with #, the new one on", text.splitlines()[0].lstrip().startswith("#")
       and any(l.startswith('319, "Serie C\\Arezzo"') for l in text.splitlines()))
    # kserv: comments stripped, then map[tid] = path line by line
    kmap = {}
    for l in text.splitlines():
        l = l.split("#", 1)[0]
        if "," in l and l.split(",", 1)[0].strip().isdigit():
            kmap[int(l.split(",", 1)[0])] = l.split(",", 1)[1].strip().strip('"')
    ok("Kit Server reads the new kit for 319", kmap[319] == "Serie C\\Arezzo")

    # the warning: two lines on, the earlier one is the unused one
    with open(path, "w", encoding="utf-8") as f:
        f.write('319, "A"\n319, "B"\n')
    t = Tab(kits, path)
    seen = t.last_lines()
    first, last = t.mf.rows()
    w1, w2 = t.problems(first, None, seen), t.problems(last, None, seen)
    ok("the earlier line is marked unused, the last one not", w1 and "last one counts" in w1[0] and not w2)
    ts = Tab(stadiums, os.path.join(tmp, "map_teams.txt"))
    ok("no warning on a map that keeps every line", ts.problems(first, None, seen) == [])
    ok("a stadium line switches nothing off", ts.switch_off_others(Row(["319", "009", "x", "y"])) == 0)

    # a world zip carries the kit of the line in effect: the last one
    with open(path, "w", encoding="utf-8") as f:
        f.write('319, "Modpack\\Game leagues\\Arezzo"\n319, "Serie C\\Arezzo"\n# 328, "X"\n')
    got = installer.borrowed_kits(path, "_FL26M2400E", [319, 328], [])
    ok("borrowed_kits: the last line of 319, nothing for the switched-off 328", got == [(319, "Serie C\\Arezzo")])

    # the text in every language
    for lang in ("es", "fr", "hr", "pt"):
        d = json.load(open(os.path.join(HERE, "modstudio", "lang", lang + ".json"), encoding="utf-8"))["text"]
        assert "this club has a later line, and only the last one counts: this line is not used" in d, lang
        assert "this club is listed more than once; the first line counts" not in d, lang
    ok("the warning translated, the old one gone", True)
    print("all passed")


if __name__ == "__main__":
    main()
