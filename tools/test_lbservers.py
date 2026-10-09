"""python tools/test_lbservers.py

Kits and scoreboards of a world (lbservers): read from one game's Kit Server / Scoreboard Server
maps (collect), written into another's with that game's ids (write) -- a line of your own for the
same id switched off and back on, a second run changes nothing, an empty world takes ours out.
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


def kit(root, rel):
    put(os.path.join(root, S.KITS, rel, "p1", "config.txt"), "x")


def lines(path):
    with open(path, encoding="utf-8") as f:
        return f.read().splitlines()


def main():
    tmp = tempfile.mkdtemp()
    try:
        # the maker's game: two clubs with kits, one league scoreboard
        a = os.path.join(tmp, "a")
        kit(a, r"HNL\Dinamo")
        kit(a, r"HNL\Hajduk")
        put(os.path.join(a, S.KITS, "map.txt"), '701, "HNL\\Dinamo"\n702, "HNL\\Hajduk"\n')
        put(os.path.join(a, S.BOARDS, "HNL", "bg.dds"), "x")
        put(os.path.join(a, S.BOARDS, "map_competitions.txt"), "300, HNL   # mine\n")
        recipe = {"leagues": [{"name": "HNL"}]}
        pa = {"leagues": [{"name": "HNL", "teams": [701, 702, 703], "rid": 300}]}
        ok("collect finds 2 kits and 1 scoreboard", S.collect(recipe, pa, a) == (2, 1))
        L = recipe["leagues"][0]
        ok("a club without a kit gets an empty slot", len(L["kit_folders"]) == 3 and L["kit_folders"][2] == "")

        # the other game: different ids, its own line for one of them
        b = os.path.join(tmp, "b")
        os.makedirs(os.path.join(b, S.KITS))
        os.makedirs(os.path.join(b, S.BOARDS))
        put(os.path.join(b, S.KITS, "map.txt"), '901, "Old\\Kit"\n5, "Keep"\n')
        pb = {"world": "My world", "leagues": [dict(L, teams=[901, 902, 903], rid=410,
                                                     club_names=["Dinamo", "Hajduk", "Rijeka"])]}
        ok("write puts 2 kits and 1 scoreboard", S.write(pb, b, log=lambda *_: None) == (2, 1))
        km = lines(os.path.join(b, S.KITS, "map.txt"))
        ok("own line for 901 switched off", any(l.startswith('#901, "Old\\Kit"') and l.endswith(S.OFF) for l in km))
        ok("own line for another id kept", '5, "Keep"' in km)
        ok("kit line with the new id", any(l.startswith('902, "My world\\HNL\\Hajduk"') for l in km))
        ok("kit folder copied", os.path.isfile(os.path.join(b, S.KITS, "My world", "HNL", "Dinamo", "p1", "config.txt")))
        bm = lines(os.path.join(b, S.BOARDS, "map_competitions.txt"))
        ok("scoreboard line with the new regulation id", any(l.startswith("410, My world\\HNL") for l in bm))
        ok("backup of the map made", os.path.isfile(os.path.join(b, S.KITS, "map.txt.before-builder")))

        S.write(pb, b, log=lambda *_: None)
        ok("second run changes nothing", lines(os.path.join(b, S.KITS, "map.txt")) == km)

        S.write({"world": "My world", "leagues": []}, b, log=lambda *_: None)
        ok("empty world: ours out, own line back on",
           lines(os.path.join(b, S.KITS, "map.txt")) == ['901, "Old\\Kit"', '5, "Keep"'])

        # kits made for new clubs with colours or a crest of their own (kitmaker)
        from PIL import Image
        w = os.path.join(tmp, "world")
        flag = os.path.join(w, "common", "render", "symbol", "flag")
        os.makedirs(flag)
        for tid, col in ((911, (200, 0, 0, 255)), (912, (0, 0, 200, 255)), (913, (0, 150, 0, 255))):
            Image.new("RGBA", (64, 64), col).save(os.path.join(flag, "e_%06d_r_ll.png" % tid))
        pm = {"world": "My world", "leagues": [{"name": "Liga", "teams": [910, 911, 912, 913, 914], "rid": 420,
              "game_clubs": {"0": {"id": 910}},
              "club_names": ["Game club", "Red", "Blue", "Green", "Nothing"],
              "club_kits": ["", "stripes #ff0000 #ffffff #ffffff", "", "", ""],
              "club_crests": ["", "", "blue.png", "", ""]}]}
        made = S.to_make(pm, w)
        ok("kits made for a club with colours and one with only a crest",
           [(m[0], m[3]) for m in made] == [(911, "stripes #ff0000 #ffffff #ffffff"), (912, "plain #0000c8 #ffffff #ffffff")])
        ok("no kit for a game club, a club with a drawn badge only, or no crest", {m[0] for m in made} == {911, 912})
        kit(b, r"Lib\Numbers")
        for s in ("_back", "_leg", "_name"):
            put(os.path.join(b, S.KITS, "Lib", "Numbers", "p1", "u1p1%s.ftex" % s), "x")
        log = []
        S.write(pm, b, log=log.append, root=w)
        red = os.path.join(b, S.KITS, "My world", "Liga", "Red")
        ok("made kit has home, away, third and goalkeeper",
           all(os.path.isfile(os.path.join(red, v, "u911%s.ftex" % v)) for v in ("p1", "p2", "p3", "g1")))
        ok("made kit lends back numbers from the library",
           os.path.isfile(os.path.join(red, "p1", "u911p1_back.ftex")))
        km = lines(os.path.join(b, S.KITS, "map.txt"))
        ok("map lines for the made kits", any(l.startswith('911, "My world\\Liga\\Red"') for l in km)
           and any(l.startswith('912, "My world\\Liga\\Blue"') for l in km))
        log = []
        S.write(pm, b, log=log.append, root=w)
        ok("second run makes nothing again", any("(0 new or changed)" in l for l in log))
        Image.new("RGBA", (64, 64), (250, 250, 0, 255)).save(os.path.join(flag, "e_000911_r_ll.png"))
        log = []
        S.write(pm, b, log=log.append, root=w)
        ok("a changed crest makes that kit again", any("(1 new or changed)" in l for l in log))
        with open(os.path.join(b, S.KITS, "map.txt"), "a", encoding="utf-8") as f:
            f.write('912, "Mine\\Blue"\n')
        S.write(pm, b, log=lambda *_: None, root=w)
        km = lines(os.path.join(b, S.KITS, "map.txt"))
        ok("a club with a kit line of your own keeps it, no kit made",
           '912, "Mine\\Blue"' in km and not any(l.startswith('912, "My world') for l in km))
        S.write(dict(pm, make_kits=False), b, log=lambda *_: None, root=w)
        ok("make_kits false: no made kit lines", not any("911," in l for l in lines(os.path.join(b, S.KITS, "map.txt"))))

        c = os.path.join(tmp, "c")
        os.makedirs(c)
        ok("no Kit Server / Scoreboard Server: nothing written", S.write(pb, c, log=lambda *_: None) == (0, 0))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("%d cases passed" % N)


if __name__ == "__main__":
    main()
