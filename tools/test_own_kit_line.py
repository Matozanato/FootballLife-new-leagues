"""python tools/test_own_kit_line.py

A kit line of your own wins over a league package's kit (Discord, pepponeee98, 14.10.: every
Build switched his Serie C lines in Kit Server's map.txt off "(switched off by FL26 Mod Studio)"
and put the package's kits in a folder of the world instead):

  - a club with a switched-on line of your own, to a kit that is installed, keeps it: no line of
    ours, no folder of ours, at every Build;
  - a line of yours that 0.2.3 switched off comes back on, and ours for that club goes;
  - a club without a line of its own, or with one to a kit that is not installed, still gets the
    package's kit, and a second Build changes nothing;
  - the package's kit folders stay with their clubs when a club is removed, inserted or moved to
    another league (they stayed by place: the clubs below wore the next club's kit).
"""
import os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lbservers as S

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def put(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def lines(path):
    with open(path, encoding="utf-8") as f:
        return f.read().splitlines()


def live(km, tid):
    """the switched-on lines of a team id"""
    return [l for l in km if l.startswith("%d," % tid)]


def kit_lines():
    tmp = tempfile.mkdtemp()
    try:
        game = os.path.join(tmp, "SiderAddons")
        lib = os.path.join(game, S.KITS)
        for rel in (r"Serie C\Catania FC", r"Serie C\Bari"):        # the kits he put in himself
            put(os.path.join(lib, rel, "p1", "config.txt"), "mine")
        world, league = "_FL26MyWorld 1.4B", "Italian Serie C Girone C"
        # the map as 0.2.3 left it: 71578 his line on (switched on again by hand on the Kits
        # page, ours off), 71579 his line switched off by the Build and ours after it
        put(os.path.join(lib, "map.txt"),
            '71578, "Serie C\\Catania FC"\n'
            '#71579, "Serie C\\Bari"%s\n'
            '71580, "Gone\\Foggia"\n'
            '#71578, "%s\\%s\\Catania"   %s %s/0\n'
            '71579, "%s\\%s\\Bari"   %s %s/1\n'
            % (S.OFF, world, league, S.TAG, league, world, league, S.TAG, league))
        pack = os.path.join(tmp, "packs", "seriec", "kitserver")
        folders = []
        for k in range(4):
            put(os.path.join(pack, str(k), "p1", "config.txt"), "package %d" % k)
            folders.append(os.path.join(pack, str(k)))
        pl = {"world": world, "leagues": [{"name": league, "teams": [71578, 71579, 71580, 71581], "rid": 500,
                                           "club_names": ["Catania", "Bari", "Foggia", "Picerno"],
                                           "kit_folders": folders}]}
        log = []
        S.write(pl, game, log=log.append)
        km = lines(os.path.join(lib, "map.txt"))
        ok("a line of your own stays on, no line of ours for that club",
           live(km, 71578) == ['71578, "Serie C\\Catania FC"'])
        ok("a line of yours 0.2.3 switched off is on again, ours for it gone",
           live(km, 71579) == ['71579, "Serie C\\Bari"'] and not any(S.OFF in l and "71579" in l for l in km))
        ok("no folder of ours for those clubs",
           not os.path.exists(os.path.join(lib, world, league, "Catania"))
           and not os.path.exists(os.path.join(lib, world, league, "Bari")))
        ok("a line of yours to a kit that is not installed: the package's kit, that line off",
           live(km, 71580) == ['71580, "%s\\%s\\Foggia"   %s %s/2' % (world, league, S.TAG, league)]
           and '#71580, "Gone\\Foggia"' + S.OFF in km)
        ok("a club without a line of its own gets the package's kit",
           live(km, 71581) == ['71581, "%s\\%s\\Picerno"   %s %s/3' % (world, league, S.TAG, league)]
           and os.path.isfile(os.path.join(lib, world, league, "Picerno", "p1", "config.txt")))
        ok("the log says who kept a line of their own", any("2 club(s) keep a kit line of your own" in l for l in log))
        S.write(pl, game, log=lambda *_: None)
        ok("a second Build changes nothing", lines(os.path.join(lib, "map.txt")) == km
           and sorted(os.listdir(os.path.join(lib, world, league))) == ["Foggia", "Picerno"])
        S.write({"world": world, "leagues": []}, game, log=lambda *_: None)
        ok("the world switched off: only your lines, all on",
           lines(os.path.join(lib, "map.txt")) == ['71578, "Serie C\\Catania FC"', '71579, "Serie C\\Bari"',
                                                   '71580, "Gone\\Foggia"'])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def kit_folders_follow():
    from modstudio.project import Project
    p = Project(None)
    names = ["C%d" % i for i in range(12)]
    p.recipe["leagues"] = [{"name": "A", "clubs": 12, "club_names": list(names),
                            "kit_folders": ["K%d" % i for i in range(12)]},
                           {"name": "B", "clubs": 12, "club_names": ["B%d" % i for i in range(12)]}]
    A, B = p.recipe["leagues"]
    assert p.shift_places("A", 1, -1)
    ok("Remove club: the clubs below keep their own kit",
       A["club_names"][1] == "C2" and A["kit_folders"][:3] == ["K0", "K2", "K3"] and len(A["kit_folders"]) == 11)
    assert p.shift_places("A", 0, 1)
    ok("Insert club: no kit for the new place, the others move with their clubs",
       A["kit_folders"][:3] == ["", "K0", "K2"] and len(A["kit_folders"]) == 12)
    A["club_names"][0] = "New"
    assert p.move_club("A", 2, "B") is None
    ok("Move to another league: the kit goes with the club",
       B["club_names"][12] == "C2" and B["kit_folders"][12] == "K2" and A["kit_folders"][2] == "K3")


if __name__ == "__main__":
    kit_lines()
    kit_folders_follow()
    print("all %d passed" % N)
