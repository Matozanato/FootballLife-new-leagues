"""python tools/test_unicolor.py [<the game's UniColor.bin>]

UniColor.bin (mkkits.unicolor): the kit menus offer a team as many kits as its record there says,
home and away for a team without one -- every new club had only two to pick, its third kit made
but never offered (mato 08.11.). Build now adds a record per club of ours: 85 bytes, u32 id, u8
the number of kits, 10 slots of u16 kind (0 1st, 1 2nd, 2 3rd, 16 GK) and two RGB triples, the
records sorted by team id. The game's records stay byte for byte.

Without an argument the file is made up (three game teams); with one, the game's own is used."""
import os, struct, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mkkits as K
import pesdb

N = 0


def ok(name, cond):
    global N
    print(("ok    " if cond else "FAIL  ") + name)
    N += 0 if cond else 1


def rec(tid, kinds):
    out = bytearray(struct.pack("<IB", tid, len(kinds)))
    for k in range(10):
        out += struct.pack("<H", kinds[k]) + b"\x11\x22\x33\x44\x55\x66" if k < len(kinds) else b"\0\0" + b"\xff" * 6
    return bytes(out)


def blob(shirt, second):
    return bytes(4) + bytes(shirt) + bytes(second) + bytes(9) + bytes(100)


def main():
    d = tempfile.mkdtemp(prefix="fl26-unicolor-")
    if len(sys.argv) > 1:
        game = sys.argv[1]
    else:
        game = os.path.join(d, "UniColor.bin")
        open(game, "wb").write(pesdb.wesys_pack(rec(1, (0, 1, 2, 16)) + rec(2, (0, 1, 16)) + rec(71580, (0, 1, 16)),
                                                b"\x00\x10\x81"))
    raw = open(game, "rb").read()
    hdr = raw[:3] if raw[3:8] == b"WESYS" else None
    shipped = K.unicolor_records(pesdb.wesys_unpack(raw) if hdr else raw)
    three = {"1st_realUni": blob((200, 0, 0), (255, 255, 255)), "2nd_realUni": blob((255, 255, 255), (200, 0, 0)),
             "3rd_realUni": blob((0, 0, 0), (255, 215, 0)), "GK1st_realUni": blob((0, 160, 0), (0, 0, 0))}
    plain = {"1st": blob((1, 2, 3), (4, 5, 6)), "2nd": blob((7, 8, 9), (1, 1, 1)), "GK1st": blob((9, 9, 9), (0, 0, 0))}
    some = next(iter(shipped))
    pairs = [((72289, "Adelaide"), (5, three)), ((72163, "Plain"), (6, plain)),
             ((71590, "Other mod's kit"), (7, {})), ((some, "a game club"), (8, three))]
    out, added = K.unicolor(game, pairs)
    ok("the file keeps the game's wesys prefix", (out[:3] == hdr) if hdr else out[3:8] != b"WESYS")
    data = pesdb.wesys_unpack(out) if hdr else out
    ok("records of 85 bytes", len(data) % 85 == 0)
    recs = K.unicolor_records(data)
    ids = [struct.unpack_from("<I", data, i)[0] for i in range(0, len(data), 85)]
    ok("sorted by team id, each once", ids == sorted(set(ids)))
    ok("the game's records byte for byte", all(recs[t] == r for t, r in shipped.items()))
    ok("two clubs of ours added (no kits: none; a game club keeps its own)", added == 2
       and len(recs) == len(shipped) + 2 and 71590 not in recs or 71590 in shipped)
    r = recs[72289]
    slots = [struct.unpack_from("<H", r, 5 + 8 * k)[0] for k in range(r[4])]
    ok("a club with a third kit: 4 kits, 1st 2nd 3rd GK: %s" % slots, r[4] == 4 and slots == [0, 1, 2, 16])
    ok("its colours: shirt and second colour of each kit", r[7:13] == bytes((200, 0, 0, 255, 255, 255))
       and r[5 + 8 * 2 + 2:5 + 8 * 2 + 8] == bytes((0, 0, 0, 255, 215, 0)))
    ok("unused slots as the game's: kind 0, white", r[5 + 8 * 4:5 + 8 * 5] == b"\0\0" + b"\xff" * 6)
    p = recs[72163]
    ok("plain kits: 3 kits, 1st 2nd GK", p[4] == 3 and [struct.unpack_from("<H", p, 5 + 8 * k)[0] for k in range(3)] == [0, 1, 16])
    # through write(): the file lands beside UniformParameter.bin
    root = os.path.join(d, "root")
    items = [("1_DEF_1st_realUni.bin", b"x" * 120)]
    rc = K.write(["mkkits.py", "--archive", "--unicolor", game], root, False, b"", [], None, pairs[:1], items)
    f = os.path.join(root, K.TEAM_DIR.replace("/", os.sep), "UniColor.bin")
    ok("write() puts UniColor.bin beside UniformParameter.bin", rc == 0 and os.path.isfile(f)
       and os.path.isfile(os.path.join(os.path.dirname(f), "UniformParameter.bin")))
    kit_server_colours(d)
    print("%d failed" % N)
    sys.exit(1 if N else 0)


def kit_server_colours(d):
    """B444: a new club without club_kits but with a Kit Server folder is lent the shipped kit
    nearest its p1\\config.txt colours (the menus show the lent kit); without a config, as before"""
    import kitpics, leaguebuilder
    green = os.path.join(d, "Green FC")
    os.makedirs(os.path.join(green, "p1"))
    open(os.path.join(green, "p1", "config.txt"), "w").write(
        "KitFile=u72483p1\nShirtColor1=#008331 ; body\nShirtColor2=#ffffff\nShortsColor=#ffffff\n")
    bare = os.path.join(d, "No config FC")
    os.makedirs(os.path.join(bare, "p1"))
    odd = os.path.join(d, "Odd FC")
    os.makedirs(os.path.join(odd, "p1"))
    open(os.path.join(odd, "p1", "config.txt"), "w").write("KitFile=x\nTightKit=1\n")
    ok("config_colours: ShirtColor1/2 of p1", kitpics.config_colours(green) == "plain #008331 #ffffff #008331")
    ok("config_colours: none without config.txt or without a colour",
       kitpics.config_colours(bare) is None and kitpics.config_colours(odd) is None
       and kitpics.config_colours(os.path.join(d, "missing")) is None)
    pl = {"leagues": [{"teams": [72001, 72002, 72003, 72004, 72005],
                       "club_kits": ["plain #c80000 #ffffff #c80000", "", "", "", ""],
                       "club_away_kits": ["plain #ffffff #c80000 #ffffff"],
                       "kit_folders": [green, green, bare, "", odd]}]}
    cols = leaguebuilder.kit_colours(pl)
    ok("kit_colours: club_kits first, the folder only for a club without them",
       cols == {72001: ["plain #c80000 #ffffff #c80000", "plain #ffffff #c80000 #ffffff"],
                72002: ["plain #008331 #ffffff #008331", "", "kit server"]})
    pool = [(t, {"1st_realUni": blob(s, (255, 255, 255)), "2nd_realUni": blob((255, 255, 255), s)})
            for t, s in ((11, (0, 0, 200)), (12, (200, 0, 0)), (13, (240, 240, 0)), (14, (0, 130, 50)), (15, (90, 90, 90)))]
    clubs = [(t, "c%d" % t) for t in (72001, 72002, 72003, 72004, 72005)]
    before = K.matched(clubs, pool, {72001: cols[72001]})       # what Build gave before B444
    now = K.matched(clubs, pool, cols)
    donor = {c[0]: x[0] for c, x in now}
    ok("the Kit Server club gets the green kit: donor %s" % donor[72002], donor[72002] == 14
       and K.colours_of(dict(now)[clubs[1]][1]["1st_realUni"])[0] == (0, 131, 49))
    ok("a club_kits club and the clubs without a config keep their kits",
       [x for c, x in now if c[0] != 72002] == [x for c, x in before if c[0] != 72002])
    # B482: a world from a zip -- the folder is its maker's, the copy is in the game's Kit Server
    import lbservers, shutil, siderdir
    game = os.path.join(d, "the game")
    sider = siderdir.find(game)
    klib = lbservers.libs(sider)[0]
    copy = os.path.join(sider, klib, "World", "League", "Green FC")
    shutil.copytree(green, copy)
    os.makedirs(os.path.join(sider, klib, "World", "League", "Gone FC"))
    open(os.path.join(sider, klib, "map.txt"), "w", encoding="utf-8").write(
        '72002, "World\\League\\Green FC"\n72003, "World\\League\\Gone FC"\n72005, "World\\League\\Nowhere"\n')
    pz = {"leagues": [{"teams": [72001, 72002, 72003, 72004, 72005],
                       "club_kits": ["plain #c80000 #ffffff #c80000", "", "", "", ""],
                       "club_away_kits": ["plain #ffffff #c80000 #ffffff"],
                       "kit_folders": ["source/d001/Red", "source/d001/Green FC", "source/d001/Gone FC", "",
                                       "source/d001/Nowhere"]}]}
    ok("B482: served_kits reads the kit folders the game's map names", leaguebuilder.served_kits(game) == {72002: copy}
       and leaguebuilder.served_kits(None) == {} and leaguebuilder.served_kits(os.path.join(d, "no game")) == {})
    ok("B482: a folder of the maker's PC is read from the world's copy in Kit Server: the same colours",
       leaguebuilder.kit_colours(pz, game) == cols)
    open(os.path.join(sider, klib, "map.txt"), "w", encoding="utf-8").write(
        '# 72002, "World\\League\\Green FC"\n# a comment\n')
    ok("B482: and from a line that is switched off", leaguebuilder.kit_colours(pz, game) == cols)
    ok("B482: without the game, or with the folder on this PC, as before",
       leaguebuilder.kit_colours(pz) == {72001: cols[72001]} and leaguebuilder.kit_colours(pl, game) == cols)
    pl["leagues"][0]["kit_folders"][1] = bare
    ok("the same club without its config.txt: every club's kit as before, it the donor its place gives",
       K.matched(clubs, pool, leaguebuilder.kit_colours(pl)) == before and before[1][1][0] == pool[1][0])


if __name__ == "__main__":
    main()
