r"""python tools/test_base_game.py [<FL26 tables> <FL 2027 tables>]

mato 07.11.2026 (#beta-chat, a tester asked how to tell an FL26 pack from an FL 2027 one): "there
will be warning in modstudio if you are installing pack from different version of the game".
An FL26 world from before the game line (a tester's pack) went into FL 2027: Install took it, and
its leagues missed clubs FL 2027 has not (1695, 1746, 2178).

  - a world without the game line is the game whose own clubs its Team.bin has (worldgame.base_game:
    60 clubs only FL26 has, 62 only FL 2027 has, at their id and with their name); Install mods
    refuses it in the other game, and lets it in its own;
  - a world with too few of them, or none, still goes anywhere;
  - BASE_ONLY is what the two games' tables give (with both tables given, or the ones Mod Studio
    unpacked to %APPDATA%\FL26ModStudio\tables and tables27);
  - a league package says the game it was made on (manifest "game", Make a package writes it), and
    one without says it by the game's own clubs it uses; Mod Studio warns in the other game, in
    four languages.

No game: fake game folders (an empty FL_2026.exe / FL_2027.exe) in a temp folder. The parts with
the real tables are skipped (and said so) when they are not there.
"""
import json, os, shutil, struct, sys, tempfile, zipfile, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import worldgame as WG
import lbpackage as K
from modstudio import installer as I, i18n

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %2d - %s" % (N, name))


def put(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(data.encode("utf-8") if isinstance(data, str) else data)


def team_bin(clubs):
    """a packed Team.bin of (id, name) records, the rest of each record zero"""
    raw = bytearray()
    for i, name in clubs:
        r = bytearray(WG.TEAM_REC)
        r[WG.T_ID:WG.T_ID + 4] = i.to_bytes(4, "little")
        r[WG.T_NAME:WG.T_NAME + len(name)] = name
        raw += r
    c = zlib.compress(bytes(raw))
    return b"\x00\x01\x01WESYS" + struct.pack("<II", len(c), len(raw)) + c


def world(root, name, team):
    """a world built before the game line: its world file and Team.bin (raw bytes, or None)"""
    d = os.path.join(root, "SiderAddons", "livecpk", name)
    put(os.path.join(d, "fl26world.txt"), "# fl26world\r\nworld %s\r\nleague 900 4 2\r\n" % name)
    if team is not None:
        put(os.path.join(d, "common", "etc", "pesdb", "Team.bin"), team)
    return d


def game(root, exe):
    put(os.path.join(root, exe), b"")
    put(os.path.join(root, "SiderAddons", "sider.ini"), "[sider]\n")
    return root


def refused(g, src):
    """what Install mods says of the unpacked zip at src in game folder g (None: it goes in)"""
    work = tempfile.mkdtemp(prefix="bg_work_")
    try:
        parts = I.detect(I.unpack(src, work), "pack")
        said = [I.wrong_game(g, p.src, p.world_file, p.name) for p in parts if p.kind in ("world", "root")]
        return said[0] if said else "no world part"
    finally:
        shutil.rmtree(work, ignore_errors=True)


def a_pack(path, man=None, recipe=None):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("manifest.json", json.dumps(dict({"format": K.FORMAT, "format_version": 1, "name": "Liga B",
                                                      "leagues": []}, **(man or {}))))
        z.writestr("recipe.json", json.dumps(recipe or {"leagues": []}))
    return path


def tables_dir(a):
    return os.path.join(a, "common", "etc", "pesdb") if os.path.isdir(os.path.join(a, "common")) else a


def main(t26=None, t27=None):
    app = os.path.join(os.environ.get("APPDATA", ""), "FL26ModStudio")
    t26 = tables_dir(t26 or os.path.join(app, "tables"))
    t27 = tables_dir(t27 or os.path.join(app, "tables27"))
    tmp = tempfile.mkdtemp(prefix="fl26 base game ")      # a space in the path, as a player's
    try:
        g26 = game(os.path.join(tmp, "Football Life 2026"), "FL_2026.exe")
        g27 = game(os.path.join(tmp, "Football Life 2027"), "FL_2027.exe")
        # ---- the signature, on made-up clubs: names whose crc is the table's ----
        only26 = WG.BASE_ONLY["fl26"]
        ok("60 clubs only FL26 has, 62 only FL 2027 has, no id in both",
           len(only26) == 60 and len(WG.BASE_ONLY["fl27"]) == 62 and not set(only26) & set(WG.BASE_ONLY["fl27"]))
        ok("no Team.bin: base_game says nothing", WG.base_game(world(tmp, "_FL26None", None)) is None)
        ok("clubs of neither game: nothing", WG.base_game(world(tmp, "_FL26Own", team_bin(
            [(70000 + i, b"Club %d" % i) for i in range(50)]))) is None)
        # ---- with the real tables ----
        n26 = WG.team_names(os.path.join(t26, "Team.bin"))
        n27 = WG.team_names(os.path.join(t27, "Team.bin"))
        if not (n26 and n27):
            print("# skipped the real-table checks: no Team.bin in %s and %s" % (t26, t27))
        else:
            for g, a, b in (("fl26", n26, n27), ("fl27", n27, n26)):
                want = {i: zlib.crc32(a[i]) & 0xffffffff for i in set(a) - set(b)}
                ok("BASE_ONLY[%s] is what the two games' tables give (%d clubs)" % (g, len(want)),
                   WG.BASE_ONLY[g] == want)
            w26 = world(os.path.join(tmp, "zip26"), "_FL26Dales", open(os.path.join(t26, "Team.bin"), "rb").read())
            w27 = world(os.path.join(tmp, "zip27"), "_FL26Mega", open(os.path.join(t27, "Team.bin"), "rb").read())
            ok("a world on FL26's tables, no game line: FL26's (%s)" % WG.base_scores(WG.team_names(
                os.path.join(w26, "common", "etc", "pesdb", "Team.bin"))), WG.base_game(w26) == "fl26")
            ok("a world on FL 2027's tables: FL 2027's", WG.base_game(w27) == "fl27")
            ok("world_game says it, not stamped", WG.world_game(w26)[0] == "fl26" and WG.world_game(w26)[3] is False)
            said = refused(g27, os.path.join(tmp, "zip26"))
            ok("Install mods: the FL26 world in FL 2027 stays out -- %s" % said[:70],
               said and said.startswith("_FL26Dales is a world for FL26"))
            ok("  ... and goes into FL26", refused(g26, os.path.join(tmp, "zip26")) is None)
            ok("the FL 2027 world stays out of FL26, goes into FL 2027",
               refused(g26, os.path.join(tmp, "zip27")).startswith("_FL26Mega is a world for FL 2027")
               and refused(g27, os.path.join(tmp, "zip27")) is None)
            few = [(i, n) for i, n in n26.items() if i not in only26] + \
                  [(i, n26[i]) for i in sorted(only26)[:WG.BASE_MIN - 1]]
            ok("fewer than %d of them (a world that dropped clubs): it goes anywhere" % WG.BASE_MIN,
               WG.base_game(world(tmp, "_FL26Few", team_bin(few))) is None)
            mixed = list(n26.items()) + [(i, n27[i]) for i in WG.BASE_ONLY["fl27"]]
            ok("as many of the one as the other: it goes anywhere",
               WG.base_game(world(tmp, "_FL26Mix", team_bin(mixed))) is None)
        ok("renamed clubs at those ids are not the game's", WG.base_game(world(tmp, "_FL26Ren", team_bin(
            [(i, b"Renamed %d" % i) for i in only26]))) is None)
        # ---- league packages ----
        ok("a recipe's game: its \"game\"", WG.recipe_game({"game": "FL27"}) == "fl27")
        c26 = sorted(only26)[:3]
        ok("else the game's clubs it uses that only one game has",
           WG.recipe_game({"leagues": [{"game_clubs": [{"at": 1, "id": c26[0]}, {"id": 1}]}]}) == "fl26"
           and WG.recipe_game({"edits": {"clubs": {str(sorted(WG.BASE_ONLY["fl27"])[0]): {}}}}) == "fl27")
        ok("both games' clubs, or neither: it does not say",
           WG.recipe_game({"leagues": [{"game_clubs": [c26[1], sorted(WG.BASE_ONLY["fl27"])[1]]}]}) is None
           and WG.recipe_game({"leagues": [{"game_clubs": [{"id": 1}]}]}) is None)
        p = a_pack(os.path.join(tmp, "old.fl26pack"), recipe={"leagues": [{"game_clubs": [{"id": c} for c in c26]}]})
        ok("an old package (no game in its manifest): by its clubs", K.game_of(p) == "fl26")
        i18n.set_language("en")
        said = I.pack_wrong_game(g27, p)
        ok("Mod Studio warns in FL 2027 -- %s" % (said or "")[:80],
           said and "made for FL26" in said and "FL 2027 version" in said)
        ok("  ... and not in FL26, nor without a game folder",
           I.pack_wrong_game(g26, p) is None and I.pack_wrong_game(None, p) is None)
        p27 = a_pack(os.path.join(tmp, "new.fl26pack"), {"game": "fl27"})
        ok("a package that says FL 2027: warned in FL26 only",
           "made for FL 2027" in (I.pack_wrong_game(g26, p27) or "") and I.pack_wrong_game(g27, p27) is None)
        pn = a_pack(os.path.join(tmp, "none.fl26pack"))
        ok("a package that says nothing: no warning", I.pack_wrong_game(g26, pn) is None
           and I.pack_wrong_game(g27, pn) is None)
        for lang in ("hr", "es", "fr", "pt"):
            d = json.load(open(os.path.join(HERE, "modstudio", "lang", lang + ".json"), encoding="utf-8"))["text"]
            keys = [k for k in d if "is a league package made for" in k]
            ok("%s has both warnings, with their %%s" % lang,
               len(keys) == 2 and all(d[k].count("%s") == 1 for k in keys))
        # ---- Make a package writes the game ----
        sider = os.path.join(tmp, "SiderAddons")
        os.makedirs(sider, exist_ok=True)
        out = os.path.join(tmp, "made.fl26pack")
        recipe = {"world": "_FL26Made", "leagues": [{"name": "Liga M", "clubs": 2, "club_names": ["A", "B"]}]}
        man = K.export(recipe, out, {"name": "Liga M", "game": "fl27"}, log=lambda t: None)
        ok("export: the manifest says the game", man.get("game") == "fl27"
           and json.loads(zipfile.ZipFile(out).read("manifest.json"))["game"] == "fl27")
        man = K.export(dict(recipe, game="fl26"), out, {"name": "Liga M"}, log=lambda t: None)
        ok("  ... the recipe's game when Make a package does not give one", man.get("game") == "fl26")
        man = K.export(recipe, out, {"name": "Liga M"}, log=lambda t: None)
        ok("  ... and none when neither says", "game" not in man and K.game_of(out) is None)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("test_base_game: all %d passed" % N)


if __name__ == "__main__":
    main(*sys.argv[1:3])
