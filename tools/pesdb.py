"""FL26 / PES2021 pesdb helpers: WESYS pack/unpack + table record access."""
import struct, zlib, sys, os

import flpaths

# Extracted pesdb directories, newest data CPK first. Set FL26_PESDB (see flpaths.py).
PESDB_DIRS = flpaths.PESDB_DIRS

# The engine's own schema, read out of the exe rather than guessed: the lazy table loader
# at 0x14125f310 indexes a name array at 0x1434d6630 and a record-size array at 0x1428bb100,
# both by table id, and bounds the id with `cmp edx, 0x1c`. See docs/pesdb-schema.txt.
TABLES = ["Ball", "BallCondition", "Boots", "Coach", "CoachDeleteList", "Competition",
          "CompetitionEntry", "CompetitionKind", "CompetitionRegulation", "Country", "Derby",
          "Glove", "MyclubCoach", "MyclubTactics", "MyclubTacticsFromation", "Player",
          "PlayerAssignment", "PlayerDeleteList", "SpecialPlayerAssignment", "Stadium",
          "StadiumOrder", "StadiumOrderInConfederation", "StadiumWeight", "Tactics",
          "TacticsFormation", "Team", "PlayerWeekno", "TeamWeekno"]

REC = {"Ball":140, "BallCondition":8, "Boots":304, "Coach":100, "CoachDeleteList":4,
       "Competition":36, "CompetitionEntry":12, "CompetitionKind":88,
       "CompetitionRegulation":2352, "Country":1420, "Derby":12, "Glove":204,
       "MyclubCoach":192, "MyclubTactics":12, "MyclubTacticsFromation":12, "Player":312,
       "PlayerAssignment":16, "PlayerDeleteList":4, "SpecialPlayerAssignment":16,
       "Stadium":392, "StadiumOrder":8, "StadiumOrderInConfederation":8, "StadiumWeight":8,
       "Tactics":12, "TacticsFormation":12, "Team":1532, "PlayerWeekno":12, "TeamWeekno":8}

TABLE_ID = {n: i for i, n in enumerate(TABLES)}

def wesys_unpack(d):
    assert d[3:8] == b"WESYS", d[:8]
    csz, usz = struct.unpack("<II", d[8:16])
    out = zlib.decompress(d[16:16+csz])
    assert len(out) == usz
    return out

def wesys_pack(raw, hdr=b"\x00\x01\x01"):
    c = zlib.compress(raw, 9)
    return hdr + b"WESYS" + struct.pack("<II", len(c), len(raw)) + c

def load(table, where=None):
    """Return decompressed bytes of the newest copy of a table."""
    for d in ([where] if where else PESDB_DIRS):
        p = os.path.join(d, table + ".bin")
        if os.path.exists(p):
            d = open(p, "rb").read()
            return wesys_unpack(d) if d[3:8] == b"WESYS" else d
    raise FileNotFoundError(
        "%s.bin not found in %s. Extract the pesdb tables from the data CPKs "
        "and set FL26_PESDB (see flpaths.py)." % (table, PESDB_DIRS or "<FL26_PESDB unset>"))

def rows(raw, size):
    assert len(raw) % size == 0, (len(raw), size)
    return [raw[i:i+size] for i in range(0, len(raw), size)]

def cstr(b):
    return b.split(b"\0")[0].decode("utf-8", "replace")

# --- Competition (36 B) ---
def comp_rows(raw=None):
    raw = raw if raw is not None else load("Competition")
    out = []
    for r in rows(raw, 36):
        out.append(dict(raw=r, area=r[3] >> 3, parent=r[4],
                        id=r[5], flags=r[6], conf=r[6] & 0xf, code=cstr(r[8:36])))
    return out

# --- CompetitionEntry (12 B) ---
def entry_rows(raw=None):
    raw = raw if raw is not None else load("CompetitionEntry")
    out = []
    for r in rows(raw, 12):
        team, rowid, cs = struct.unpack("<III", r)
        out.append(dict(raw=r, team=team, rowid=rowid, comp=cs & 0xff, slot=cs >> 8))
    return out

def entry_pack(team, rowid, comp, slot):
    return struct.pack("<III", team, rowid, comp | (slot << 8))

# --- CompetitionRegulation (2352 B) ---
REG_TYPE = {1:"playoff",2:"group",3:"knockout",4:"league",5:"conf-league",8:"practice",9:"split-total"}
def reg_rows(raw=None):
    raw = raw if raw is not None else load("CompetitionRegulation")
    out = []
    for r in rows(raw, 2352):
        releg, rid, sub, promo, parent = struct.unpack_from("<HBBHH", r, 0)
        names = []
        for k in range(20):                      # 20 language slots, NUL-terminated, 115 B each
            o = 0x14 + k * 115
            names.append(cstr(r[o:o+115]))
        out.append(dict(raw=r, releg=releg, id=rid, sub=sub, promo=promo, parent=parent,
                        comp=r[8], type=r[9], group=r[0xa], teams=r[0xb],
                        hdr=r[0xc:0x14].hex(" "), names=names, name=names[0]))
    return out


# --- names the game can draw (B173) ---
# The letters U+00A0..U+20FF the game's fonts have, all four of them (pes, match, LPsm, plname
# _fnt.bin of dt11_x64.cpk; a glyph's code is its UTF-8 bytes): Latin-1 and Latin Extended-A
# whole, of Extended-B only Ə, ƒ and pinyin's ǎ ǐ ǒ ǔ ǖ ǘ ǚ ǜ, basic Greek and Cyrillic, some
# punctuation. Anything else in there is drawn as a box: Azerbaijani ə, Romanian ș ț, Vietnamese
# ơ ư ạ ế. Above U+20FF (Chinese, Japanese, Korean ...) nothing is changed.
FONT_RANGES = ((0x00A1, 0x017F), (0x018F, 0x018F), (0x0192, 0x0192), (0x01CE, 0x01CE), (0x01D0, 0x01D0),
               (0x01D2, 0x01D2), (0x01D4, 0x01D4), (0x01D6, 0x01D6), (0x01D8, 0x01D8), (0x01DA, 0x01DA),
               (0x01DC, 0x01DC), (0x02C6, 0x02C7), (0x02D9, 0x02D9), (0x02DC, 0x02DC), (0x0384, 0x0386),
               (0x0388, 0x038A), (0x038C, 0x038C), (0x038E, 0x03A1), (0x03A3, 0x03CE), (0x0401, 0x040C),
               (0x040E, 0x044F), (0x0451, 0x045C), (0x045E, 0x045F), (0x0490, 0x0491), (0x2010, 0x2010),
               (0x2013, 0x2016), (0x2018, 0x201A), (0x201C, 0x201E), (0x2020, 0x2022), (0x2025, 0x2026),
               (0x2030, 0x2030), (0x2032, 0x2033), (0x2039, 0x203B), (0x203E, 0x203E), (0x20AC, 0x20AC))
# a letter the fonts lack written as one they have, before taking accents off: ə as UEFA spells
# it (Məmmədov -> Mammadov), Romanian's comma below as the cedilla the fonts have (ș -> ş)
FONT_SPELL = {"\u0259": "a", "\u0218": "\u015e", "\u0219": "\u015f", "\u021a": "\u0162", "\u021b": "\u0163",
              "\u01e7": "\u011f", "\u01e6": "\u011e", "\u04e7": "\u00f6", "\u04e6": "\u00d6", "\u04d9": "a",
              "\u04d8": "\u018f", "\u00a0": " "}


def font_has(ch):
    c = ord(ch)
    if c < 0xA0 or c > 0x20FF:
        return c >= 0x20 or c in (9, 10, 13)
    return any(a <= c <= b for a, b in FONT_RANGES)


def game_text(s):
    """s as the game can draw it (B173): a letter its fonts lack becomes one they have (FONT_SPELL,
    or the same letter with fewer accents: ế -> ê, ứ -> ú, ạ -> a), invisible marks go; Mod Studio keeps
    the name as it was, only the game's tables get this"""
    if not s or s.isascii():
        return s
    import itertools, unicodedata
    out = []
    for ch in unicodedata.normalize("NFC", s):
        ch = FONT_SPELL.get(ch, ch)
        if font_has(ch):
            out.append(ch)
            continue
        if unicodedata.category(ch) in ("Mn", "Me", "Cf", "Cc"):
            continue                                  # a loose accent, a right-to-left mark
        d = unicodedata.normalize("NFD", ch)
        like = [t for k in range(len(d) - 1, -1, -1) for marks in itertools.combinations(d[1:], k)
                for t in [unicodedata.normalize("NFC", d[0] + "".join(marks))] if len(t) == 1 and font_has(t)]
        out.append(like[0] if like else ch)           # the most accents kept; none like it: as it was
    return "".join(out)


def reg_set_name(r, name):
    """Write name into all 20 language slots of a regulation row (bytearray)."""
    b = game_text(name).encode("utf-8")[:114]
    b = b.decode("utf-8", "ignore").encode("utf-8")       # never half a letter
    for k in range(20):
        o = 0x14 + k * 115
        r[o:o+115] = b + bytes(115 - len(b))

# --- Team (1532 B) ---
def team_rows(raw=None):
    raw = raw if raw is not None else load("Team")
    out = {}
    for r in rows(raw, 1532):
        tid = struct.unpack_from("<I", r, 8)[0]
        out[tid] = dict(raw=r, id=tid, name=cstr(r[368:368+70]))
    return out

if __name__ == "__main__":
    t = team_rows()
    print(len(t), "teams")
