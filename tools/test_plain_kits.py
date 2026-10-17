"""python test_plain_kits.py [<the game's tables, with UniformParameter.bin; default Mod Studio's>]
-- B120 (ZeDosCaes 17.10.): a world
built with Plain kits to change in Edit mode (editable_kits) gives its new clubs plain, unlicensed
kits, and Kit Server leaves an unlicensed club undressed ("the team is unlicensed. Disabling
kits"). Kits imported for those clubs were not worn and nothing said so. Now Build says it: the
new clubs with a kit folder in the recipe or a line in Kit Server's map.txt are named in a warning.
Worlds are built in temporary game folders (nothing is switched on)."""
import json, os, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def game_folder(lines=None):
    g = tempfile.mkdtemp(prefix="fl26-plain-")
    for d in ("livecpk", "modules", "content"):
        os.makedirs(os.path.join(g, "SiderAddons", d))
    with open(os.path.join(g, "SiderAddons", "sider.ini"), "w") as f:
        f.write("[sider]\n")
    if lines is not None:
        os.makedirs(os.path.join(g, "SiderAddons", "content", "kit-server"))
        with open(os.path.join(g, "SiderAddons", "content", "kit-server", "map.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    return g


def build(base, game, r):
    said = []
    B.build(B.plan(r, base, None), base, game, False, log=said.append)
    with open(os.path.join(game, "SiderAddons", "livecpk", r["world"], "leaguebuilder-plan.json"), encoding="utf-8") as f:
        pl = json.load(f)
    return "\n".join(str(s) for s in said), pl


def recipe(plain):
    r = {"world": "_FL26PlainTest", "players": {}, "edits": {"leagues": {}, "clubs": {}},
         "leagues": [{"name": "Plain Albania", "country": "Albania", "clubs": 10, "legs": 2}]}
    if plain:
        r["editable_kits"] = True
    return r


def main(base):
    # the helper alone: lines switched on count, a "#" line does not, nor a club of another world
    g = game_folder(["# Kitserver map", "71600, \"Imported/Club A\"", "#71601, \"Imported/Club B\"",
                     "  101 ,\"Premier League/Arsenal\""])
    try:
        ok("kit_server_clubs reads the lines switched on", B.kit_server_clubs(g) == {71600, 101})
        pl = {"leagues": [{"teams": [71600, 71601, 71602, 71603], "kit_folders": ["", "", "L/C", ""]}]}
        ok("plain_but_dressed: a map line or a recipe kit folder, ours only",
           B.plain_but_dressed(pl, [71600, 71601, 71602, 71603], g) == [71600, 71602])
        ok("plain_but_dressed: a club not ours is never named", B.plain_but_dressed(pl, [71601], g) == [])
    finally:
        shutil.rmtree(g, ignore_errors=True)
    ok("no sider folder, no game: nothing", B.kit_server_clubs(None) == set())

    # a real Build: the first one learns the clubs' ids, the second has a map line for one of them
    games = []
    try:
        g0 = game_folder()
        games.append(g0)
        log, pl = build(base, g0, recipe(True))
        ok("plain world, no Kit Server kits: no warning", "WARNING" not in log and "kits: plain" in log)
        tid = pl["leagues"][0]["teams"][3]
        g1 = game_folder(["%d, \"Imported/Club\"" % tid])
        games.append(g1)
        log, _pl = build(base, g1, recipe(True))
        ok("plain world, a new club with an imported kit: Build warns and names it",
           "WARNING: 1 new clubs have Kit Server kits (%d)" % tid in log and "untick Plain kits" in log)
        g2 = game_folder(["%d, \"Imported/Club\"" % tid])
        games.append(g2)
        log, _pl = build(base, g2, recipe(False))
        ok("lent kits (Plain off): no warning", "WARNING: " not in log or "Kit Server kits" not in log)
    finally:
        for g in games:
            shutil.rmtree(g, ignore_errors=True)
    print("%d cases passed" % N)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ.get("APPDATA", ""), "FL26ModStudio", "tables", "common", "etc", "pesdb"))
