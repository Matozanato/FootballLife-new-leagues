r"""python tools/test_pack_zip_world.py

B148 (Biancopr 18.10.): Make a league package on a world installed from a zip (Make it editable)
stopped on "picture D:\dev\fl26\notes\...\Albanian_Superleague.png is missing": the recipe read
back from the world keeps the picture and kit paths of the PC that built it. Now a picture not on
this PC is taken from the world as built (the league's emblem, the club's crest), a kit folder
from the Kit Server map of the game, and what is in neither is left out with a line in the log.
"""
import json, os, shutil, sys, tempfile, zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lbpackage as K
from PIL import Image

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def png(path, colour):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.new("RGBA", (8, 8), colour).save(path)


def main():
    tmp = tempfile.mkdtemp(prefix="fl26-b148-")
    try:
        sider = os.path.join(tmp, "SiderAddons")
        world = os.path.join(sider, "livecpk", "_FL26Zip")
        os.makedirs(world)
        open(os.path.join(sider, "sider.ini"), "w").close()
        json.dump({"leagues": [{"name": "Liga A", "cid": 130, "rid": 11, "teams": [70001, 70002]}]},
                  open(os.path.join(world, "leaguebuilder-plan.json"), "w"))
        png(os.path.join(world, K.EMBLEM % 130), (1, 2, 3, 255))
        png(os.path.join(world, K.CREST % 70001), (4, 5, 6, 255))
        kits = os.path.join(sider, "content", "kit-server")
        os.makedirs(os.path.join(kits, "_FL26Zip", "Liga A", "Club One", "p1"))
        open(os.path.join(kits, "_FL26Zip", "Liga A", "Club One", "p1", "u0001p1.ftex"), "wb").close()
        with open(os.path.join(kits, "map.txt"), "w", encoding="utf-8") as f:
            f.write('70001, "%s"\n' % os.sep.join(["_FL26Zip", "Liga A", "Club One"]))
        here = os.path.join(tmp, "mine.png")
        png(here, (7, 8, 9, 255))
        gone = os.path.join(tmp, "nowhere", "pc-that-built-it")      # paths of the PC that built it
        recipe = {"world": "_FL26Zip", "leagues": [{
            "name": "Liga A", "clubs": 2, "club_names": ["Club One", "Club Two"],
            "logo": os.path.join(gone, "Liga_A.png"), "flag": os.path.join(gone, "flag.png"), "cup_logo": here,
            "club_crests": [os.path.join(gone, "1.png"), os.path.join(gone, "2.png")],
            "kit_folders": [os.path.join(gone, "kits", "1"), os.path.join(gone, "kits", "2")],
            "scoreboard": os.path.join(gone, "board")}]}
        out = os.path.join(tmp, "a.fl26pack")
        log = []
        K.export(recipe, out, {"name": "Liga A"}, log=log.append, sider=sider)
        z = zipfile.ZipFile(out)
        r = json.loads(z.read("recipe.json"))
        L = r["leagues"][0]
        names = z.namelist()

        def pixel(rel):
            return Image.open(z.open(rel)).convert("RGBA").getpixel((0, 0))

        ok("the package is made (it stopped before)", os.path.isfile(out))
        ok("the logo is the world's emblem", L["logo"].startswith("assets/") and pixel(L["logo"]) == (1, 2, 3, 255))
        ok("club 1's crest is the world's", pixel(L["club_crests"][0]) == (4, 5, 6, 255))
        ok("club 2's crest, in neither place, is left out", L["club_crests"][1] == "")
        ok("a flag with no world file is left out", L["flag"] == "")
        ok("a picture on this PC goes in as before", pixel(L["cup_logo"]) == (7, 8, 9, 255))
        ok("club 1's kits come from the game's Kit Server map",
           L["kit_folders"][0] == "kitserver/0" and any(n.startswith("kitserver/0/p1") for n in names))
        ok("club 2 has no kits, the scoreboard none: left out, no stop",
           L["kit_folders"][1] == "" and not L.get("scoreboard"))
        ok("the log says what was taken and what left out",
           any("world's own taken" in l for l in log) and any("left out" in l for l in log))
        ok("the recipe itself is not changed", recipe["leagues"][0]["logo"].startswith(gone))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("%d cases passed" % N)


if __name__ == "__main__":
    main()
