"""Boots and goalkeeper gloves for the new players of a world (mato 13.11.2026: every new player
of the GigaPack wore the same black boots).

The game does not keep a player's boots with the player. It reads two lists, player id -> model:

    common/character0/model/character/boots/BootsList.bin
    common/character0/model/character/glove/GloveList.bin

packed (WESYS), records of 8 bytes: u32 player id, u32 model id, in the order of the player ids.
The game looks a player up with a halving search (FL_2027.exe 0x1414e0400) and takes the model
from the low 16 bits; a player without a line wears model 62 (the plain black boots) and glove 1.
The list is as long as the file says: the game allots what the file holds and counts size / 8
(0x1414e0270), no top to it.

Every player of the game has a line; a new player of a world has none (a few have one by chance:
the list keeps lines of ids the game no longer has). Build writes both lists into the world: the
game's lines as they are, and for every new player a model a player of the game wears -- drawn
by his id, so a Build after gives him the same, and so the makes are spread as they are in the
game. Gloves for the goalkeepers alone.
"""
import glob, hashlib, os, struct

BOOTS = "common/character0/model/character/boots/BootsList.bin"
GLOVES = "common/character0/model/character/glove/GloveList.bin"
BOOTS_TABLE, GLOVES_TABLE = "common/etc/pesdb/Boots.bin", "common/etc/pesdb/Glove.bin"
BOOTS_REC, GLOVES_REC = 304, 204
HEAD = b"\xff\x10\x81"            # the three bytes before WESYS in the game's own two lists


def _unpack(d):
    import pesdb
    return pesdb.wesys_unpack(d) if d[3:8] == b"WESYS" else d


def read(data):
    """[(player id, model id)] of a list's bytes, packed or not"""
    raw = _unpack(data)
    if len(raw) % 8:
        raise ValueError("a boots / glove list is records of 8 bytes; this one has %d bytes" % len(raw))
    return [struct.unpack_from("<II", raw, o) for o in range(0, len(raw), 8)]


def write(lines, head=HEAD):
    """the packed bytes of [(player id, model id)], in the order of the ids the game searches by"""
    import pesdb
    raw = b"".join(struct.pack("<II", p, m) for p, m in sorted(lines))
    return pesdb.wesys_pack(raw, head)


def models(data, rec):
    """the model ids of the game's Boots.bin / Glove.bin (u16 at the start of every record)"""
    raw = _unpack(data)
    return {struct.unpack_from("<H", raw, o)[0] for o in range(0, len(raw) - rec + 1, rec)}


def pick(pid, pool, salt):
    """the model player pid gets from `pool` (models, one for every player of the game who
    wears it): by his id, the same at every Build"""
    h = hashlib.sha1(("%s:%d" % (salt, pid)).encode("ascii")).digest()
    return pool[int.from_bytes(h[:8], "little") % len(pool)]


def merged(game_lines, game_ids, new_ids, known=None, salt="boots"):
    """(the list for the world, how many new players got a line): the game's lines, and a line for
    every id of new_ids. game_ids: the players of the game -- the models they wear are the pool;
    a line the game's list holds for an id that is a new player's now (a player the game dropped)
    is not his. known: the models the game has a table row for; a model outside it is not drawn
    for anybody (the pool is the whole list's when that leaves nothing)."""
    new = set(new_ids)
    worn = [m for p, m in game_lines if p in game_ids and p not in new]
    pool = sorted(m for m in worn if not known or m in known) or sorted(worn)
    if not pool:
        return list(game_lines), 0
    out = {p: m for p, m in game_lines if p not in new}
    for p in new:
        out[p] = pick(p, pool, salt)
    return sorted(out.items()), len(new)


def game_files(game, into, season_cpks):
    """{BOOTS / GLOVES / BOOTS_TABLE / GLOVES_TABLE: path} of the game's own copies, taken out of
    its archives into the folder `into` (download over Data, the later archive over the earlier,
    as the game reads them); a file the game has none of is left out"""
    import cpkread
    want = (BOOTS, GLOVES, BOOTS_TABLE, GLOVES_TABLE)
    cpks = (sorted(glob.glob(os.path.join(game, "Data", "*.cpk"))) + season_cpks(os.path.join(game, "download")) +
            sorted(glob.glob(os.path.join(game, "download", "data_extra*.cpk"))))
    for c in cpks:
        try:
            have = set(cpkread.names(c))
            hit = [w for w in want if w in have]
            if hit:
                cpkread.extract(c, into, hit)
        except (OSError, ValueError, KeyError):
            pass
    return {w: os.path.join(into, w.replace("/", os.sep)) for w in want
            if os.path.isfile(os.path.join(into, w.replace("/", os.sep)))}
