r"""Which game a League Builder world is for: FL26 or FL 2027 (mato 07.11.2026: "people must not
put this pack into FL26 by mistake, it could break their game").

An FL 2027 world (the Megapack: 204 leagues, ~103,000 players, FL 2027's 4800 clubs) does not
fit FL26, whose caps set holds 2400 clubs and 61905 players: the game reads the world's tables
past the end of its arrays. An FL26 world in FL 2027 replaces FL 2027's own tables with FL26's
(B307: the two games keep their own tables).

The stamp. Build writes the game into the world file, right after its `world` line:

    game fl27 teams=4321 players=103000

teams and players are the records of the world's Team.bin and Player.bin (what the game has to
hold). The world file travels with the world everywhere: in livecpk\<world>, in a world zip, in
modules\fl26world.txt after Switch on, and in a folder copied by hand. Mod Studio reads it before
it installs or switches on a world; fl26gameguard.lua reads it in the game.

A world without the line (built before 07.11.2026) is decided by its content: more clubs or
players than FL26 takes is FL 2027's. Else its clubs say it (mato 07.11.: an FL26 pack went into
FL 2027 and its leagues missed clubs FL 2027 has not): a world's Team.bin is the game's own with
the world's clubs added, and 60 of FL26's clubs are not in FL 2027 (62 the other way round).
Those clubs, at their id and with their name, are the game the world was built on. A world with
neither (no Team.bin, or too few of them) may go anywhere.

Nothing here knows Qt or the League Builder: Mod Studio, leaguebuilder.py and the tests use it.
"""
import os, re, struct, zlib

WORLD_FILE = "fl26world.txt"
STAMP = "game"
GAMES = ("fl26", "fl27")
TITLE = {"fl26": "FL26", "fl27": "FL 2027"}
FL26_CAPS = (2400, 61905)                # leaguebuilder.GAME_CAPS["fl26"] (test_world_game checks it)
TEAM_REC, PLAYER_REC = 1532, 312         # mkworld.T_REC, a Player.bin record
EXES = (("FL_2026.exe", "fl26"), ("FL_2027.exe", "fl27"), ("PES2021.exe", "fl26"))
_LINE = re.compile(r"^\s*game\s+(\w+)(.*)$")
# the clubs one game's stock Team.bin has and the other's has not: id -> crc32 of the name
# (the bytes at T_NAME up to the first 0). FL26 2.2 and FL 2027 1.00, test_world_game rebuilds them
BASE_ONLY = {
    "fl26": {164: 0x7717e370, 165: 0xf29ca083, 167: 0xcbcd657c, 204: 0xf194ed22, 210: 0x87432ecb,
        232: 0xcc805be3, 246: 0xf11cf102, 253: 0xb99709de, 268: 0x0fa32978, 302: 0x902ff375, 319: 0xb5d47c89,
        328: 0xd0b3b8ac, 349: 0x4128fec0, 394: 0x18086dfe, 405: 0x9ef6afc0, 1528: 0xaef7ae3c,
        1600: 0x0367aa7e, 1695: 0x135ca7dc, 1746: 0x522f1cbe, 1924: 0xe4c985e6, 1925: 0x2dfe67b2,
        1989: 0xb71d55c3, 1996: 0xa447791a, 2178: 0xf1c20a7f, 2188: 0x33afc3ba, 2218: 0x56fb4646,
        2360: 0x1fc80033, 2543: 0x79eff9fd, 2614: 0xed904175, 2616: 0xfaa42ea8, 2652: 0xbc5e1748,
        3099: 0x3c783ff7, 4115: 0x3e39a45e, 4139: 0x4b02052e, 4171: 0xa1e17001, 4200: 0x3b9fbf5c,
        4225: 0x26a8dd8a, 4252: 0x0ea2946a, 4941: 0xece8fe32, 4959: 0x3aa1107e, 5009: 0x89d06334,
        5086: 0x57c998d0, 5148: 0x7136c213, 5229: 0x2060d928, 5235: 0x69e67511, 5296: 0x37b261b5,
        5319: 0x14412751, 5376: 0x07496dee, 5573: 0x774cd575, 5652: 0x96f92775, 5909: 0xcdb35d5c,
        5912: 0x0a3716ba, 5954: 0x5dfa8f50, 6044: 0x7f373687, 6052: 0x5bf77eab, 65817: 0xf6e0c981,
        68179: 0x3e3a7dd6, 70923: 0x2eb32ff0, 70924: 0x4a307325, 71311: 0x8bd82ee2},
    "fl27": {148: 0xc82f8ea8, 161: 0x87695e3d, 184: 0x91ec94bc, 202: 0xd0ec0f4e, 243: 0x642118b0,
        255: 0x858f03ff, 317: 0x10e2b50a, 337: 0xd2662ad5, 338: 0x577f00de, 379: 0xcac21c80, 910: 0xa6f3b423,
        1328: 0xb3a784b6, 1935: 0x6b522736, 1976: 0x6b8c0797, 2013: 0x28e6f0dc, 2066: 0x842b0c54,
        2194: 0x5de59e89, 2365: 0xe37962ec, 2373: 0x89b485a2, 2465: 0x89339e4c, 2523: 0x9e141560,
        2551: 0xcaef5966, 2709: 0x87c6ab43, 4082: 0x22bc3bf9, 4147: 0xd20c225c, 4150: 0x46b14fa8,
        4152: 0x301aa8f9, 4154: 0x50af4141, 4159: 0x60ce014b, 4161: 0xcb9ac20f, 4165: 0x6f76dbe9,
        4232: 0x51685465, 4249: 0x38d33bab, 4324: 0xa9ebf74b, 4377: 0xa397c9c0, 4988: 0x9ec3fe03,
        4997: 0x1f6beb22, 5048: 0xfc3bba1e, 5063: 0x448af53e, 5072: 0xfce52547, 5168: 0x02ff57eb,
        5195: 0x002a2dd5, 5210: 0xe303b234, 5224: 0x6df2e5ab, 5249: 0x713ce1a2, 5297: 0x3aaf298c,
        5353: 0xfff1a162, 5422: 0xe19807e2, 5624: 0xd52ababf, 5659: 0xde44a02d, 5832: 0x2d576957,
        5911: 0x2c56e5c4, 5962: 0x7e3afcbb, 6081: 0x6639f531, 6084: 0x3e991882, 9009: 0x76efc71e,
        9011: 0xf3d67526, 69651: 0x3e39a45e, 69707: 0xa1e17001, 70477: 0xece8fe32, 71448: 0x0a3716ba,
        71580: 0xb3524f9f},
}
T_ID, T_NAME, T_NAME_LEN = 0x08, 0x170, 0x46   # mkworld
BASE_MIN = 10                            # of the 60 / 62: fewer says nothing (a world may drop clubs)


def game_of(folder):
    """"fl26" / "fl27" by the exe in the game folder (FL_2026.exe first, as flpaths.game_exe
    reads it), None when there is none"""
    if not folder:
        return None
    for exe, game in EXES:
        if os.path.isfile(os.path.join(folder, exe)):
            return game
    return None


def records(path, rec):
    """the records of a pesdb table (packed WESYS or not), None when it is not there. A packed
    table says its unpacked size in its header: nothing is unpacked"""
    try:
        with open(path, "rb") as f:
            head = f.read(16)
            if head[3:8] == b"WESYS" and len(head) == 16:
                return struct.unpack("<I", head[12:16])[0] // rec
            return os.path.getsize(path) // rec
    except OSError:
        return None


def counts(root):
    r"""(clubs, players) of the world's own tables at <root>\common\etc\pesdb, None for a table
    it does not bring"""
    db = os.path.join(root, "common", "etc", "pesdb")
    return records(os.path.join(db, "Team.bin"), TEAM_REC), records(os.path.join(db, "Player.bin"), PLAYER_REC)


def stamp_line(game, teams=None, players=None):
    return "%s %s" % (STAMP, game) + ("" if teams is None else " teams=%d" % teams) + \
        ("" if players is None else " players=%d" % players)


def read_stamp(path):
    """{"game": ..., "teams": n, "players": n} of the world file's game line (the line Build puts
    after the `world` line, so the reading stops at the first league), None without one"""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                m = _LINE.match(line)
                if m and m.group(1).lower() in GAMES:
                    out = {"game": m.group(1).lower()}
                    for k, v in re.findall(r"(\w+)=(\d+)", m.group(2)):
                        out[k] = int(v)
                    return out
                if line.startswith("league "):
                    return None
    except OSError:
        pass
    return None


def stamped(text, line):
    """the world file's text with `line` as its game line: an old game line goes, the new one
    comes right after the `world` line (or first, when there is none)"""
    nl = "\r\n" if "\r\n" in text else "\n"
    rows = [r for r in text.splitlines() if not _LINE.match(r)]
    at = next((i + 1 for i, r in enumerate(rows) if r.startswith("world ")), 0)
    rows.insert(at, line)
    return nl.join(rows) + nl


def stamp(root, game, world_file=None):
    """write the game line into the world file of the world at <root> (Build, export): the game
    and the world's clubs and players. Returns the line"""
    wf = world_file or os.path.join(root, WORLD_FILE)
    teams, players = counts(root)
    line = stamp_line(game, teams, players)
    with open(wf, "rb") as f:
        text = f.read().decode("utf-8", "replace")
    new = stamped(text, line)
    if new != text:
        with open(wf, "wb") as f:
            f.write(new.encode("utf-8"))
    return line


def too_big(teams, players, caps=FL26_CAPS):
    return (teams or 0) > caps[0] or (players or 0) > caps[1]


def world_game(root, world_file=None):
    """(game, clubs, players, stamped) of the world at <root>: the game line of its world file,
    else "fl27" when its tables hold more than FL26 takes, else the game its stock clubs are of
    (base_game), else None (it may go anywhere)"""
    wf = world_file or os.path.join(root, WORLD_FILE)
    s = read_stamp(wf)
    if s:
        t, p = s.get("teams"), s.get("players")
        if t is None or p is None:
            c = counts(root)
            t, p = (t if t is not None else c[0]), (p if p is not None else c[1])
        return s["game"], t, p, True
    t, p = counts(root)
    return ("fl27" if too_big(t, p) else base_game(root)), t, p, False


def team_names(path):
    """{id: name bytes} of a Team.bin (packed WESYS or not), {} when it is not there"""
    try:
        with open(path, "rb") as f:
            raw = f.read()
        if raw[3:8] == b"WESYS":
            csz = struct.unpack("<I", raw[8:12])[0]
            raw = zlib.decompress(raw[16:16 + csz])
    except (OSError, zlib.error, struct.error):
        return {}
    return {int.from_bytes(raw[o + T_ID:o + T_ID + 4], "little"): raw[o + T_NAME:o + T_NAME + T_NAME_LEN].split(b"\0")[0]
            for o in range(0, len(raw) - TEAM_REC + 1, TEAM_REC)}


def base_scores(names):
    """{game: how many of the clubs only that game's stock tables have are in `names`, at their
    id and with their name}"""
    return {g: sum(1 for i, c in only.items() if i in names and zlib.crc32(names[i]) & 0xffffffff == c)
            for g, only in BASE_ONLY.items()}


def base_game(root):
    """the game whose stock clubs the world at <root> was built on, by its Team.bin; None when it
    does not say (no Team.bin, or fewer than BASE_MIN of either game's own clubs, or both)"""
    sc = base_scores(team_names(os.path.join(root, "common", "etc", "pesdb", "Team.bin")))
    best = max(sc, key=sc.get)
    rest = max(v for g, v in sc.items() if g != best)
    return best if sc[best] >= BASE_MIN and sc[best] >= 4 * rest else None


def recipe_clubs(recipe):
    """the ids of the game's own clubs a recipe (or a league package's piece of one) uses: the
    clubs its leagues take from the game and the clubs it changes"""
    ids = set()
    for L in recipe.get("leagues") or []:
        for c in L.get("game_clubs") or []:
            i = c.get("id") if isinstance(c, dict) else c
            if str(i).isdigit():
                ids.add(int(i))
    ids.update(int(k) for k in ((recipe.get("edits") or {}).get("clubs") or {}) if str(k).isdigit())
    return ids


def recipe_game(recipe):
    """the game a recipe or package was made on: its "game", else by the game's own clubs it uses
    (clubs only one game has: FL26's in a package means FL26). None when it does not say"""
    g = str(recipe.get("game") or "").lower()
    if g in GAMES:
        return g
    ids = recipe_clubs(recipe)
    hits = {g: len(ids & set(only)) for g, only in BASE_ONLY.items()}
    on = [g for g, n in hits.items() if n]
    return on[0] if len(on) == 1 else None


def mismatch(root, game_folder, world_file=None):
    """None when the world at <root> may go into the game at game_folder; else
    (the world's game, the folder's game, clubs, players)"""
    have = game_of(game_folder)
    if have is None:
        return None
    want, t, p, _s = world_game(root, world_file)
    if want is None or want == have:
        return None
    return want, have, t, p


def why(world, m):
    """the refusal in plain English (the League Builder's; Mod Studio says it in the user's language)"""
    want, have, t, p = m
    if want == "fl27":
        return ("%s is a world for FL 2027 (%s clubs, %s players; FL26 takes %d clubs and %d players) -- "
                "it would break FL26: install it in FL 2027, or get the FL26 version of the pack"
                % (world, t if t is not None else "?", p if p is not None else "?", FL26_CAPS[0], FL26_CAPS[1]))
    return ("%s is a world for FL26 -- FL 2027 has tables of its own: install it in FL26, get the FL 2027 "
            "version of the pack, or Build it again with FL 2027 as the game" % world)
