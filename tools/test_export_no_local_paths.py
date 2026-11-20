"""B430 (12.11.2026): a world zip names no folder of the PC that built it.

    python tools/test_export_no_local_paths.py

Build writes the pictures, kit folders and trophies a world was made from into
leaguebuilder-plan.json and trophies/trophies.json by their full path ("C:/Users/<name>/...").
Export cuts every such path down to "source/d<n>/<last part>" in the zip's copy; the world on the
maker's disk keeps its files. Another PC never had those folders, so Install reads the same there.
"""
import json, os, re, shutil, sys, tempfile, zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modstudio import installer as I
from modstudio.siderini import SiderIni
from test_world_share import Game, put, sider

WORLD = "_FL26NoPaths"
BS = chr(92)
QUOTE = chr(34)
N = [0]


def ok(name, cond):
    N[0] += 1
    assert cond, name
    print("ok %d - %s" % (N[0], name))


def install(sd, src):
    work = tempfile.mkdtemp(prefix="np_")
    parts = I.detect(I.unpack(src, work), "mod")
    worlds = [p for p in parts if p.kind == "world"]
    assert len(worlds) == 1 and worlds[0].name == WORLD, parts
    ini = SiderIni.load(os.path.join(sd, "sider.ini"))
    rec = I.Installer(Game(sd), ini, "shared", replace_lines=True).run(parts)
    ini.save(backup=False)
    shutil.rmtree(work, ignore_errors=True)
    return rec, ini


def drive(text):
    """the strings of a JSON text that still start as a path of a disk or a share"""
    return re.findall(QUOTE + "(?:[A-Za-z]:[/" + BS * 2 + "]|" + BS * 4 + ")[^" + QUOTE + "]*" + QUOTE, text)


def main():
    # ---- the cut itself
    home = "C:/Users/Ana Marić"
    plan = {"world": WORLD, "note": "D: is a letter, 1:0 a score, http://x/y a link",
            "leagues": [{"name": "L One", "logo": home + "/Pictures/logos/l one.png",
                         "scoreboard": "D:" + BS + "pack" + BS + "sb" + BS + "AUS",
                         "kit_folders": [home + "/kits/L One/Club A", home.lower() + "/KITS/L One/Club B/"],
                         "club_crests": {"72001": home + "/crests/a/1.png", "72002": home + "/crests/b/1.png"},
                         "share": BS * 2 + "nas" + BS + "football" + BS + "cup.png",
                         "quote": "E:/a " + QUOTE + "b" + QUOTE + "/c.png"}],
            home + "/key.png": 1, "trophies": ["F:/"]}
    for form in (dict(indent=1, ensure_ascii=False), dict(ensure_ascii=True), dict(indent=None, ensure_ascii=False)):
        text = json.dumps(plan, **form)
        out, n = I.no_local_paths(text)
        got = json.loads(out)
        G = got["leagues"][0]
        ok("still JSON, 10 paths cut, none left (%s)" % sorted(form.items()),
           n == 10 and not drive(out) and "Ana" not in out and "nas" not in out and "Mari" not in out)
        ok("... what is no path stays", got["world"] == WORLD and got["note"] == plan["note"] and G["name"] == "L One")
        ok("... the last part of each stays", G["logo"].endswith("/l one.png") and G["scoreboard"].endswith("/AUS")
           and [k.rsplit("/", 1)[1] for k in G["kit_folders"]] == ["Club A", "Club B"] and G["share"].endswith("/cup.png")
           and G["quote"].endswith("/c.png"))
        ok("... every one begins with source/d<n>", all(re.match("source/d[0-9]{3}(/|$)", v) for v in
           [G["logo"], G["scoreboard"], G["share"], G["quote"], got["trophies"][0]] + G["kit_folders"]
           + list(G["club_crests"].values())))
        ok("... one folder, one n (capitals or not); two folders, two",
           G["kit_folders"][0].rsplit("/", 1)[0] == G["kit_folders"][1].rsplit("/", 1)[0]
           and G["club_crests"]["72001"] != G["club_crests"]["72002"])
        ok("... a key that is a path is cut too", any(k.startswith("source/") and k.endswith("/key.png") for k in got))
    plain = {"a": "b/c.png", "d": "x: y", "e": 3, "f": "A:" + chr(10) + "B"}
    same, n = I.no_local_paths(json.dumps(plain))
    ok("a text without such paths comes back as it is", n == 0 and same == json.dumps(plain))

    # ---- Export
    tmp = tempfile.mkdtemp(prefix="fl26_np_")
    try:
        a = sider(os.path.join(tmp, "a"))
        root = os.path.join(a, "livecpk", WORLD)
        put(os.path.join(root, I.WORLD_FILE), "# fl26world 1\nworld %s\nleague 1 x\n" % WORLD)
        put(os.path.join(root, "common", "etc", "pesdb", "Team.bin"), "x")
        ptext = json.dumps(plan, indent=1, ensure_ascii=False)
        ttext = json.dumps({"14": {"rids": [22], "from": "D:" + BS + "incoming" + BS + "trophies" + BS + "Liga"}}, indent=1)
        itext = json.dumps({"recipe": home + "/Documents/my world.json", "leagues": 1}, ensure_ascii=False)
        other = json.dumps({"path": "C:/kept/as/it/is.png"})
        for rel, text in (("leaguebuilder-plan.json", ptext), ("leaguebuilder-input.json", itext),
                          ("trophies/trophies.json", ttext), ("fl26playerids.json", other)):
            p = os.path.join(root, *rel.split("/"))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8", newline="") as f:
                f.write(text)
        said = []
        zp = os.path.join(tmp, WORLD + ".zip")
        I.export_world(a, WORLD, zp, log=said.append)
        pre = "SiderAddons/livecpk/%s/" % WORLD
        with zipfile.ZipFile(zp) as z:
            zplan = z.read(pre + "leaguebuilder-plan.json").decode("utf-8")
            ztro = z.read(pre + "trophies/trophies.json").decode("utf-8")
            zin = z.read(pre + "leaguebuilder-input.json").decode("utf-8")
            zother = z.read(pre + "fl26playerids.json").decode("utf-8")
        ok("the zip's plan, trophies and input: no path of the maker's PC",
           not drive(zplan) and not drive(ztro) and not drive(zin) and "Ana" not in zplan + zin and "incoming" not in ztro)
        ok("... they are the same files otherwise", json.loads(ztro)["14"]["rids"] == [22]
           and json.loads(ztro)["14"]["from"].endswith("/Liga") and json.loads(zplan)["leagues"][0]["name"] == "L One"
           and json.loads(zin)["leagues"] == 1)
        ok("... Export says how many it cut (%s)" % [t for t in said if "path(s)" in t],
           any("12 path(s) of this PC left out" in t for t in said))
        ok("a file that is not one of the three goes as it is", zother == other)
        # tools/checkworldzip.py reads the whole zip: it finds that one, and nothing once it is gone
        import checkworldzip
        nread, bad = checkworldzip.check(zp)
        ok("checkworldzip: only the file Export does not cut is named (%s)" % [b[0].rsplit("/", 1)[1] for b in bad],
           nread >= 5 and [b[0] for b in bad] == [pre + "fl26playerids.json"])
        nread, bad = checkworldzip.check(zp, ["l one"])
        ok("... and a word given is found in the texts", any("'l one'" in b[1] for b in bad))
        inside = json.dumps({"League" + BS + "club" + BS + "kitmaker.txt": 1, "x": BS + "demo" + BS + "cup" + BS + "a.ftex"})
        ok("... a path inside a pack, written with backslashes, is no share; a share is",
           checkworldzip.paths(inside, True) == [] and checkworldzip.paths("share = " + BS * 2 + "nas" + BS + "a" + BS + "b.png")
           and checkworldzip.paths(json.dumps({"p": BS * 2 + "nas" + BS + "a" + BS + "b.png"}), True))
        os.remove(os.path.join(root, "fl26playerids.json"))
        zc = os.path.join(tmp, WORLD + "-clean.zip")
        I.export_world(a, WORLD, zc)
        ok("... a zip without it passes", checkworldzip.check(zc)[1] == [])
        put(os.path.join(root, "fl26playerids.json"), other)
        # review 2/3, 18.11.2026: the export writes the world's lineage into its plan (stamp_plan), nothing else
        disk = json.load(open(os.path.join(root, "leaguebuilder-plan.json"), encoding="utf-8"))
        lin = (disk.get("settings") or {}).pop("id_lineage", None)
        if disk.get("settings") == {} and "settings" not in json.loads(ptext):
            disk.pop("settings")
        ok("the world on the maker's disk keeps its files (its plan gets only its lineage, %s)" % lin,
           lin and disk == json.loads(ptext)
           and open(os.path.join(root, "trophies", "trophies.json"), encoding="utf-8", newline="").read() == ttext)
        b = sider(os.path.join(tmp, "b"))
        rec, _ini = install(b, zp)
        got = open(os.path.join(b, "livecpk", WORLD, "leaguebuilder-plan.json"), encoding="utf-8", newline="").read()
        ok("Install on another PC: the world lands with the cut plan",
           rec["world"] == WORLD and got == zplan and I.ready_world(Game(b), WORLD))
        # exported again from there (a world installed from a zip): nothing left to cut
        z2 = os.path.join(tmp, WORLD + "-again.zip")
        said2 = []
        I.export_world(b, WORLD, z2, log=said2.append)
        with zipfile.ZipFile(z2) as z:
            ok("exported again from there: the same plan, nothing said",
               z.read(pre + "leaguebuilder-plan.json").decode("utf-8") == zplan
               and not any("left out of the world's plan" in t for t in said2))
        # a plan that is no text at all does not stop Export
        odd = bytes([255, 254, 0, 1]) * 8
        with open(os.path.join(root, "leaguebuilder-plan.json"), "wb") as f:
            f.write(odd)
        z3 = os.path.join(tmp, WORLD + "-odd.zip")
        I.export_world(a, WORLD, z3)
        with zipfile.ZipFile(z3) as z:
            ok("a plan that cannot be read as text goes as it is", z.read(pre + "leaguebuilder-plan.json") == odd)
        print("all %d checks passed" % N[0])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    os.environ["FL26_LEDGER_STORE"] = tempfile.mkdtemp(prefix="fl26ledgers-")   # review 3, 18.11.2026: never the real history
    main()
