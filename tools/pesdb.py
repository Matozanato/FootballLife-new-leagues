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

def reg_set_name(r, name):
    """Write name into all 20 language slots of a regulation row (bytearray)."""
    b = name.encode("utf-8")[:114]
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
