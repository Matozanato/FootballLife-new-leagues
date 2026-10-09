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

        c = os.path.join(tmp, "c")
        os.makedirs(c)
        ok("no Kit Server / Scoreboard Server: nothing written", S.write(pb, c, log=lambda *_: None) == (0, 0))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("%d cases passed" % N)


if __name__ == "__main__":
    main()
