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
        # a restore point in ModStudio\backups, nothing next to the map (mato 15.10.)
        from modstudio import backups
        ok("backup of the map made as a restore point", any(
            r["file"].lower() == os.path.join(S.KITS, "map.txt").lower() for r in backups.load(b)))
        ok("no copies next to the map", not [f for f in os.listdir(os.path.join(b, S.KITS))
                                              if f.endswith((".before-builder", ".prev"))])

        S.write(pb, b, log=lambda *_: None)
        ok("second run changes nothing", lines(os.path.join(b, S.KITS, "map.txt")) == km)

        S.write({"world": "My world", "leagues": []}, b, log=lambda *_: None)
        ok("empty world: ours out, own line back on",
           lines(os.path.join(b, S.KITS, "map.txt")) == ['901, "Old\\Kit"', '5, "Keep"'])

        # lines Install mods put in from the world's own zip -- a kit or a scoreboard of another
        # pack the world carries under <world>\_kits, <world>\_packs -- end in our tag too, but
        # Switch on (run at the end of Install mods) must not take them out (Vran, 14.10.)
        ck = '1586, "My world\\_kits\\Other\\Salzburg"   %s kit of Other\\Salzburg' % S.TAG
        cb = "76, My world\\_packs\\Modpack\\HNL   # SuperSport HNL %s scoreboard of Modpack\\HNL" % S.TAG
        put(os.path.join(b, S.KITS, "map.txt"), '901, "Old\\Kit"\n%s\n77, "Elsewhere\\X"   %s stale\n' % (ck, S.TAG))
        put(os.path.join(b, S.BOARDS, "map_competitions.txt"), "%s\n300, Other world\\HNL   %s HNL\n" % (cb, S.TAG))
        S.write(pb, b, log=lambda *_: None)
        km = lines(os.path.join(b, S.KITS, "map.txt"))
        bm = lines(os.path.join(b, S.BOARDS, "map_competitions.txt"))
        ok("a kit the world carries from another pack stays at Switch on", ck in km)
        ok("a scoreboard the world carries from another pack stays at Switch on", cb in bm)
        ok("a line of ours that is not the world's is still taken out",
           not any("Elsewhere" in l for l in km) and not any("Other world" in l for l in bm))
        ok("carried: Build's own lines still written", any(l.startswith('902, "My world\\HNL\\Hajduk"') for l in km))
        S.write({"world": "My world", "leagues": []}, b, log=lambda *_: None)
        ok("empty world: the carried lines stay too",
           ck in lines(os.path.join(b, S.KITS, "map.txt")) and cb in lines(os.path.join(b, S.BOARDS, "map_competitions.txt")))
        ok("carried: a line of another world's tag is not one", not S.carried(ck, "Other world") and S.carried(ck, "My world")
           and S.carried(cb.replace("\\", "/"), "My world"))
        # another world switched on and then this one again: the zip's lines wait switched off and
        # come back (night test 15.10.: the modpack's 86 scoreboards were gone after a switch)
        S.write({"world": "Other world", "leagues": []}, b, log=lambda *_: None)
        km = lines(os.path.join(b, S.KITS, "map.txt"))
        bm = lines(os.path.join(b, S.BOARDS, "map_competitions.txt"))
        ok("another world on: the zip's lines are kept, switched off", "#" + ck in km and "#" + cb in bm
           and ck not in km and cb not in bm)
        ok("carrier: the world a line came with", S.carrier("#" + cb) == "my world" and S.carrier(ck) == "my world"
           and S.carrier('901, "Old\\Kit"') is None)
        S.write({"world": "Other world", "leagues": []}, b, log=lambda *_: None)
        ok("another world on twice: still one switched-off copy",
           lines(os.path.join(b, S.BOARDS, "map_competitions.txt")).count("#" + cb) == 1)
        S.write({"world": "My world", "leagues": []}, b, log=lambda *_: None)
        ok("its world back on: the zip's lines are on again",
           ck in lines(os.path.join(b, S.KITS, "map.txt")) and cb in lines(os.path.join(b, S.BOARDS, "map_competitions.txt"))
           and "#" + cb not in lines(os.path.join(b, S.BOARDS, "map_competitions.txt")))
        # a world installed from its zip on another PC: the plan's kit and scoreboard sources are
        # folders of the PC it was built on, the copies under <world> came in the zip -- the
        # lines stay (Switch on at the end of Install mods dropped them as "no folder, skipped")
        pz = {"world": "My world", "leagues": [dict(L, teams=[901, 902, 903], rid=410, kit_folders=[r"X:\gone\Dinamo", r"X:\gone\Hajduk", ""],
                                                     scoreboard=r"X:\gone\HNL", club_names=["Dinamo", "Hajduk", "Rijeka"])]}
        put(os.path.join(b, S.BOARDS, "My world", "HNL", "bg.dds"), "x")
        shutil.rmtree(os.path.join(b, S.KITS, "My world", "HNL", "Hajduk"))
        log = []
        ok("zip-installed world: kits whose copy is under the world stay, a missing one is skipped",
           S.write(pz, b, log=log.append) == (1, 1) and any("HNL/1: no folder" in l for l in log))
        km = lines(os.path.join(b, S.KITS, "map.txt"))
        ok("zip-installed world: the kit line and the scoreboard line are there",
           any(l.startswith('901, "My world\\HNL\\Dinamo"') for l in km)
           and any(l.startswith("410, My world\\HNL") for l in lines(os.path.join(b, S.BOARDS, "map_competitions.txt"))))
        put(os.path.join(b, S.KITS, "map.txt"), '901, "Old\\Kit"\n5, "Keep"\n')
        put(os.path.join(b, S.BOARDS, "map_competitions.txt"), "")

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
            f.write('912, "Mine\\Blue"\n911, "Gone\\Red"\n')
        os.makedirs(os.path.join(b, S.KITS, "Mine", "Blue"))
        S.write(pm, b, log=lambda *_: None, root=w)
        km = lines(os.path.join(b, S.KITS, "map.txt"))
        ok("a club with a kit line of your own keeps it, no kit made",
           '912, "Mine\\Blue"' in km and not any(l.startswith('912, "My world') for l in km))
        ok("a line of your own to a kit that is not installed: the made kit, that line off",
           any(l.startswith('911, "My world\\Liga\\Red"') for l in km)
           and any(l.startswith('#911, "Gone\\Red"') and l.endswith(S.OFF) for l in km))
        S.write(dict(pm, make_kits=False), b, log=lambda *_: None, root=w)
        ok("make_kits false: no made kit lines", not any('911, "My world' in l for l in lines(os.path.join(b, S.KITS, "map.txt"))))

        c = os.path.join(tmp, "c")
        os.makedirs(c)
        ok("no Kit Server / Scoreboard Server: nothing written", S.write(pb, c, log=lambda *_: None) == (0, 0))

        # GitHub #129: a clean SPFL26 loads its own common\kits.lua and common\scoreboards.lua,
        # which read content\kits and content\scoreboards; a kit-server folder there is not read
        d = os.path.join(tmp, "d")
        put(os.path.join(d, "sider.ini"), 'lua.module = "common\\kits.lua"\n;lua.module = "kserv.lua"\n'
                                          'lua.module = "common\\scoreboards.lua"\n')
        put(os.path.join(d, S.SPFL_KITS, "map.txt"), '100, "Premier League\\Manchester United"\n')
        os.makedirs(os.path.join(d, S.SPFL_BOARDS))
        os.makedirs(os.path.join(d, S.KITS))
        ok("SPFL26's own servers: their folders", S.libs(d) == (S.SPFL_KITS, S.SPFL_BOARDS))
        S.write(dict(pm, leagues=[dict(pm["leagues"][0], kit_folders=[]), dict(L, name="HNL", teams=[921, 922, 923], rid=430)]),
                d, log=lambda *_: None, root=w)
        km = lines(os.path.join(d, S.SPFL_KITS, "map.txt"))
        ok("SPFL26's own Kit Server: made and package kits in content\\kits",
           any(l.startswith('911, "My world\\Liga\\Red"') for l in km) and any(l.startswith('921, "My world\\HNL') for l in km)
           and '100, "Premier League\\Manchester United"' in km)
        ok("SPFL26's own Kit Server: nothing in kit-server", not os.listdir(os.path.join(d, S.KITS)))
        ok("SPFL26's own Scoreboard Server: line in content\\scoreboards",
           any(l.startswith("430, My world\\HNL") for l in lines(os.path.join(d, S.SPFL_BOARDS, "map_competitions.txt"))))
        put(os.path.join(d, "sider.ini"), 'lua.module = "common\\kits.lua"\nlua.module = "kserv.lua"\n')
        ok("kserv.lua loaded too: kit-server", S.libs(d)[0] == S.KITS)
        # B72: the menu themes world zips bring go on and off with their world (Switch on handled
        # kits and scoreboards only: 88 eu1 menu lines stayed live under another world, 16.10.)
        e = os.path.join(tmp, "e")
        for wn in ("_FL26A", "_FL26B", "_FL26Mine"):
            os.makedirs(os.path.join(e, "livecpk", wn))
        mp = os.path.join(e, S.MENUS, "map_competitions.txt")
        a1 = "26, _FL26A\_packs\Coupe de France   # Menus for the Coupe de France # FL26 Mod Studio: menu of Coupe de France"
        b1 = "165, _FL26B\_packs\Saudi League   # FL26 Mod Studio: menu of Saudi League"
        own = "116, RPL                             # Menus for the RPL"
        gone = "77, _FL26Gone\_packs\X   # FL26 Mod Studio: menu of X"
        put(mp, "\n".join([own, "# a comment of yours", a1, b1, gone]) + "\n")
        n = S.menus(e, "_FL26A", log=lambda *_: None)
        ml = lines(mp)
        ok("menus: the world's own zip lines on, another world's off", a1 in ml and "#" + b1 in ml and n == 1)
        ok("menus: your own lines and a world no longer on disk untouched",
           own in ml and "# a comment of yours" in ml and gone in ml)
        S.menus(e, "_FL26Mine", log=lambda *_: None)
        ml = lines(mp)
        ok("menus: a world without menus switches both zips' lines off", "#" + a1 in ml and "#" + b1 in ml and own in ml)
        S.menus(e, "_FL26B", log=lambda *_: None)
        ml = lines(mp)
        ok("menus: and back on with their world", "#" + a1 in ml and b1 in ml)
        ok("menus: nothing to change, nothing written", S.menus(e, "_FL26B", log=lambda *_: None) == 0)
        ok("menus: no menu-server, nothing happens", S.menus(os.path.join(tmp, "none"), "_FL26A", log=lambda *_: None) == 0)

        # B129 (laracroft7826, 18.10.): sider.ini loads SPFL26's kits.lua but only content\kit-server is
        # there (or no kit module and only content\kits): Install mods merged the Modpack's lines into the
        # folder it picks, the switch wrote to the other one, and the Modpack's lines stayed on for the
        # clubs of the world switched on after it
        BS = chr(92)
        old = ['71653, "_FL26M2400S%sBulgarian First League%sSlavia Sofia"   %s Bulgarian First League/0' % (BS, BS, S.TAG),
               '71655, "_FL26M2400S%s2. Bundesliga%s1. FC Kaiserslautern"   %s 2. Bundesliga/1' % (BS, BS, S.TAG)]
        mine_ = '71654, "England%sForest Green"' % BS
        new = {"world": "_FL26MyWorld", "leagues": [{"name": "National League", "teams": [71653, 71654, 71655],
                                                     "club_names": ["FC Halifax Town", "Forest Green Rovers", "Gateshead"]}]}
        for name, mods, lib in (("kits.lua, only kit-server", ["common" + BS + "kits.lua"], S.KITS),
                                ("no kit module, only content kits", [], S.SPFL_KITS),
                                ("kserv.lua, only content kits", ["kserv.lua"], S.SPFL_KITS)):
            g = os.path.join(tmp, "b129-" + str(len(name)), "SiderAddons")
            put(os.path.join(g, "sider.ini"), "".join('lua.module = "%s"' % m + chr(10) for m in mods))
            mp9 = os.path.join(g, lib, "map.txt")
            put(mp9, chr(10).join([mine_, "# ---- added by FL26 Mod Studio: _FL26M2400S.zip ----"] + old) + chr(10))
            # B158: the switch now writes where Install mods merged (servers.Server.pick)
            ok("B158 %s: the switch picks the folder Install merged into" % name, S.libs(g)[0] == lib)
            S.write(new, g, log=lambda *_: None)
            ml = lines(mp9)
            ok("B129 %s: the other world's lines are gone" % name, not any("_FL26M2400S" + BS in l for l in ml))
            ok("B129 %s: your own line stays on" % name, mine_ in ml)
            ok("B129 %s: a second switch changes nothing" % name, S.write(new, g, log=lambda *_: None) == (0, 0)
               and lines(mp9) == ml)
        # B158 (jibibi 19.10.): common\kits.lua on, no content\kits: Install merged eu4's kit lines into
        # kit-server\map.txt and the Switch on of eu4 itself took every one out again
        g = os.path.join(tmp, "b158", "SiderAddons")
        put(os.path.join(g, "sider.ini"), 'lua.module = "common' + BS + 'kits.lua"' + chr(10))
        eu = {"world": "_FL26M2400E", "leagues": [{"name": "Liga", "teams": [71599], "club_names": ["AF Elbasani"],
                                                   "kit_folders": [os.path.join(tmp, "pc-that-built-it", "k")]}]}
        os.makedirs(os.path.join(g, S.KITS, "_FL26M2400E", "Liga", "AF Elbasani", "p1"))
        zl = '71599, "_FL26M2400E%sLiga%sAF Elbasani"   %s Liga/0' % (BS, BS, S.TAG)
        mp8 = os.path.join(g, S.KITS, "map.txt")
        put(mp8, chr(10).join([mine_, "# ---- added by FL26 Mod Studio: FL26-Modpack-Europe-eu4 ----", zl]) + chr(10))
        ok("B158: kits.lua on, only kit-server: kit-server", S.libs(g)[0] == S.KITS)
        S.write(eu, g, log=lambda *_: None)
        ok("B158: the world's kit line stays after its Switch on", zl in lines(mp8))
        ok("B158: your own line stays too", mine_ in lines(mp8))
        ok("B158: no content kits folder made", not os.path.exists(os.path.join(g, S.SPFL_KITS)))
        # B130 (laracroft7826, 18.10.): kserv.lua stops at its start without content\kit-server\map_comp.txt
        g = os.path.join(tmp, "b130", "SiderAddons")
        put(os.path.join(g, "sider.ini"), 'lua.module = "kserv.lua"' + chr(10))
        put(os.path.join(g, S.KITS, "map.txt"), mine_ + chr(10))
        comp = os.path.join(g, S.KITS, "map_comp.txt")
        S.write(new, g, log=lambda *_: None)
        ok("B130: an empty map_comp.txt is made", os.path.isfile(comp) and os.path.getsize(comp) == 0)
        put(comp, "101, UCL" + chr(10))
        S.write(new, g, log=lambda *_: None)
        ok("B130: a map_comp.txt that is there stays as it is", lines(comp) == ["101, UCL"])
        g = os.path.join(tmp, "b130-none", "SiderAddons")
        put(os.path.join(g, "sider.ini"), "")
        os.makedirs(os.path.join(g, S.SPFL_KITS))
        S.write(new, g, log=lambda *_: None)
        ok("B130: no kit-server folder, none made", not os.path.exists(os.path.join(g, S.KITS)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("%d cases passed" % N)


if __name__ == "__main__":
    main()
