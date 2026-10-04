"""python mkleague.py --base <dir> --out <root> [--cid N] [--reg N] [--region N] [--tier N] ...

Add one competition to the game's data, the way the game itself stores competitions.

Three tables under common/etc/pesdb describe every competition, and a league needs a row in
each:

  Competition.bin            36 bytes.  b0/b1 are 100/200 in every row, b3 is the region
                             slot the menus group by, b5 is the competition id, b6 a flag,
                             and a code string like ENGLAND_D1_LEAGUE from +0x08.
  CompetitionRegulation.bin  2352 bytes.  reg id at +0x02, competition id at +0x08, type at
                             +0x09 (4 = league), team count at +0x0b, and then the name
                             twenty times over from +0x14, one 0x73-byte slot per language.
                             Writing only the first slot gives a league that still calls
                             itself Premier League on screen.
  CompetitionEntry.bin       12 bytes per club: club id at +0x00, a unique entry id at
                             +0x04, the competition id at +0x08 and the club's position in
                             it at +0x09.

The region slot is the part that is not free. Shipped rows use it in steps of eight -- 16
England, 24 France, 32 Spain, 40 Italy, 128 Brazil, 192 Japan -- and the menus know those
slots and no others. An earlier attempt gave the Croatian league slot 88, which no shipped
row uses; the league loads into the block and appears nowhere on screen. So the default
here is to put a new league in a slot the menus already have.
"""
import os, sys

import pesdb

COMP, REG, ENT = 36, 2352, 12
REGION_OFF, CID_OFF, FLAG_OFF, CODE_OFF = 3, 5, 6, 8
# +0x00 was called R_NAMEID here until 2026-09-21. It is not a name: it is the id of the
# division this one RELEGATES into (deepen.py writes it, and all eleven shipped links read
# right that way -- England 17 -> 79, Italy 18 -> 82, France 20 -> 81 ...). Zeroing it, which
# is what add_league does below, means "nothing below me", which is correct for a new league.
R_BELOW, R_ID, R_CID, R_TYPE, R_TEAMS, R_NAME = 0x00, 0x02, 0x08, 0x09, 0x0b, 0x14
R_NAMEID = R_BELOW               # old name, kept so mkphases.py and any local script still run
NAME_SLOTS, NAME_SLOT = 20, 0x73
# the names are two runs of ten, not twenty in a row: slots 0..9 from R_NAME (9 is an internal
# label, ENGLAND_D1_LEAGUE), 32 zero bytes, then slots 10..19 from NAME_RUN2 to the record's end.
# Writing twenty in a row put the second run 0x20 bytes early, and those ten languages read empty.
NAME_RUN2 = 0x4b2
NAME_END = NAME_RUN2 + 10 * NAME_SLOT
E_TEAM, E_EID, E_CID, E_ORDER = 0x00, 0x04, 0x08, 0x09


def load(d, n):
    return bytearray(pesdb.wesys_unpack(open(os.path.join(d, n), "rb").read()))


# the competition id every shipped code has. A database mod can rename a competition's code
# (GitHub #54: UEFA_EUROPE_LEAGUE came out under another code and the build stopped), the id
# stays, so the tools look a code up by name first and by this id second
SHIPPED_CID = {
    "FIFA_CLUB_WORLD_CUP": 1, "UEFA_CHAMPIONS_LEAGUE": 2, "UEFA_EUROPE_LEAGUE": 3,
    "UEFA_SUPER_CUP": 4, "COPA_LIBERTADORES": 5, "AFC_CHAMPIONS_LEAGUE": 8,
    "ENGLAND_D1_LEAGUE": 9, "ITALY_D1_LEAGUE": 10, "SPAIN_D1_LEAGUE": 11, "FRANCE_D1_LEAGUE": 12,
    "NETHERLANDS_D1_LEAGUE": 13, "PORTUGAL_D1_LEAGUE": 14, "ENGLAND_D1_CUP": 15,
    "ITALY_D1_CUP": 16, "SPAIN_D1_CUP": 17, "FRANCE_D1_CUP": 18, "NETHERLANDS_D1_CUP": 19,
    "PORTUGAL_D1_CUP": 20, "BRAZIL_D1_LEAGUE": 21, "ARGENTINA_D1_LEAGUE": 22,
    "CHILE_D1_LEAGUE": 23, "BRAZIL_D1_CUP": 24, "FIFA_WORLD_CUP": 27, "FIFA_WORLD_CUP_EUROPE": 28,
    "FIFA_WORLD_CUP_NCAMERICA": 29, "FIFA_WORLD_CUP_SAMERICA": 30, "FIFA_WORLD_CUP_ASIA": 31,
    "FIFA_WORLD_CUP_AFRICA": 32, "EURO": 33, "COPA_AMERICA": 34, "AFC_ASIA_CUP": 35,
    "AFRICA_NATIONS_CUP": 36, "CUSTOM_CUP": 37, "GERMANY_D1_LEAGUE": 39, "US_D1_LEAGUE": 40,
    "JAPAN_D1_LEAGUE": 41, "GERMANY_D1_CUP": 42, "US_D1_CUP": 43, "JAPAN_D1_CUP": 44,
    "SPE_FRIENDLY_MATCH": 45, "SPE_PRACTICE_MATCH": 46, "SPE_RETIREMENT_MATCH": 47,
    "ARGENTINA_D1_CUP": 49, "CHILE_D1_CUP": 56, "ENGLAND_D2_LEAGUE": 66, "SPAIN_D2_LEAGUE": 67,
    "FRANCE_D2_LEAGUE": 68, "ITALY_D2_LEAGUE": 69, "ENGLAND_D2_PLAYOFF": 70,
    "SPAIN_D2_PLAYOFF": 71, "ITALY_D2_PLAYOFF": 72, "ENGLAND_SUPER_CUP": 73,
    "SPAIN_SUPER_CUP": 74, "FRANCE_SUPER_CUP": 75, "ITALY_SUPER_CUP": 76,
    "NETHERLANDS_SUPER_CUP": 77, "PORTUGAL_SUPER_CUP": 78, "ARGENTINA_SUPER_CUP": 79,
    "GERMANY_SUPER_CUP": 82, "JAPAN_SUPER_CUP": 84, "CUSTOM_LEAGUE": 86, "BRAZIL_D2_LEAGUE": 90,
    "SPE_ML_RETIREMENT_MATCH": 97, "CHAMPIONS_CUP_NA": 100, "CHAMPIONS_CUP_SA": 101,
    "CHAMPIONS_CUP_ASIA": 102, "WORLD_SELECTION": 103, "BELGIUM_D1_LEAGUE": 111,
    "BELGIUM_CUP": 112, "BELGIUM_SUPER_CUP": 113, "RUSSIA_D1_LEAGUE": 114, "RUSSIA_CUP": 115,
    "RUSSIA_SUPER_CUP": 116, "GREECE_D1_LEAGUE": 117, "GREECE_CUP": 118, "TURKEY_D1_LEAGUE": 119,
    "TURKEY_CUP": 120, "TURKEY_SUPER_CUP": 121, "COLOMBIA_D1_LEAGUE": 122, "COLOMBIA_CUP": 123,
    "COLOMBIA_SUPER_CUP": 124, "CHINA_D1_LEAGUE": 125, "CHINA_CUP": 126, "CHINA_SUPER_CUP": 127,
    "DENMARK_D1_LEAGUE": 128, "DENMARK_CUP": 129, "SCOTLAND_D1_LEAGUE": 137, "SCOTLAND_CUP": 138,
    "KSA_D1_LEAGUE": 139, "KSA_CUP": 140, "KSA_SUPER_CUP": 141}


def code_of(row):
    return row[CODE_OFF:].split(b"\0")[0].decode("latin1")


def find_code(comp, code):
    """the row index of the competition coded `code` -- or, when a database mod renamed it, of
    the row with that code's shipped id; None when neither is there"""
    n = len(comp) // COMP
    for i in range(n):
        if code_of(comp[i * COMP:(i + 1) * COMP]) == code:
            return i
    cid = SHIPPED_CID.get(code)
    for i in range(n if cid is not None else 0):
        if comp[i * COMP + CID_OFF] == cid:
            return i
    return None


def put(b, off, s, n):
    v = s.encode("utf-8")[:n - 1].decode("utf-8", "ignore").encode("utf-8")   # never half a letter
    b[off:off + n] = v + b"\0" * (n - len(v))


def name_at(k):
    """offset of name slot k (0..19) in a regulation record"""
    return R_NAME + k * NAME_SLOT if k < 10 else NAME_RUN2 + (k - 10) * NAME_SLOT


def put_names(b, off, s, skip=()):
    """the regulation at b[off:] called s in every name slot but those in skip"""
    for k in range(NAME_SLOTS):
        if k not in skip:
            put(b, off + name_at(k), s, NAME_SLOT)


def enc_region(rid):
    """Competition.bin +3 from a region id.

    Bits 3..7 hold the region and bits 0..2 are zero in every shipped row, so ids 0..31 are
    just rid * 8, exactly as they have always been. Bit 0 carries the sixth bit, which the
    game only reads once sider/fl26reg64.lua is installed -- without it a region above 31
    silently decodes as rid - 32, so the module and the data go together.
    """
    if not 0 <= rid < 64:
        raise ValueError("region %d is outside 0..63" % rid)
    return ((rid & 0x1f) << 3) | ((rid >> 5) & 1)


def dec_region(byte):
    """The region id in a Competition.bin +3 byte, read the way fl26reg64 makes the game read it."""
    return ((byte >> 3) & 0x1f) | ((byte & 1) << 5)


R_TIER = 0x10                    # dword; bits 15-17 hold the division (1 = D1, 2 = D2, 3 = D3)
TIER_SHIFT, TIER_MASK = 15, 7


def set_tier(g, tier):
    """write the division into a regulation record in place

    The field is read at runtime as +0x304 bits 30-31 and is what the game means by "first
    division". It decides more than a label: European places are handed to tier-1 leagues of
    a region (0x141358bd0, 0x141359a60, 0x1413b7910), and the promotion resolver only looks
    for the league above when the lower one is tier 2 or more (0x141510430, 0x14131f430).
    Every league this project has built so far was copied from ENGLAND_D1_LEAGUE and was
    therefore a first division, all thirty-nine of them -- see docs/findings.md.

    The file field is three bits wide and the loader passes all three (0x1414f82a8), but the
    shipped setter shifts them into bits 30-31, so only 1, 2 and 3 survive -- a 4 written here
    arrives at runtime as 0. Ranks above 3 therefore mean nothing unless sider/experimental/fl26rank.lua is
    installed, which moves the runtime field down to bits 29-31.
    """
    if tier not in (1, 2, 3, 4, 5, 6, 7):
        raise SystemExit("tier %r is not 1..7" % (tier,))
    if tier > 3:
        print("  note: tier %d needs sider/experimental/fl26rank.lua; without it the game reads it as %d"
              % (tier, tier & 3))
    v = int.from_bytes(g[R_TIER:R_TIER + 4], "little")
    v = (v & ~(TIER_MASK << TIER_SHIFT)) | (tier << TIER_SHIFT)
    g[R_TIER:R_TIER + 4] = v.to_bytes(4, "little")


def get_tier(g):
    return (int.from_bytes(g[R_TIER:R_TIER + 4], "little") >> TIER_SHIFT) & TIER_MASK


def add_league(comp, regs, ents, cid, reg, region, name, code, teams,
               proto_code="ENGLAND_D1_LEAGUE", quiet=False, tier=None):
    """append one league to the three tables in place

    Split out of main() so a whole confederation can be built in one pass, without the
    three files being written out and read back between every league.
    """
    ncomp, nreg, nent = len(comp) // COMP, len(regs) // REG, len(ents) // ENT
    cids = {comp[i * COMP + CID_OFF] for i in range(ncomp)}
    regids = {int.from_bytes(regs[i * REG + R_ID:i * REG + R_ID + 2], "little")
              for i in range(nreg)}
    if cid in cids:
        raise SystemExit("competition id %d is taken" % cid)
    if reg in regids:
        raise SystemExit("regulation id %d is taken" % reg)

    src = find_code(comp, proto_code)
    if src is None:
        raise SystemExit("no competition row coded %s to copy" % proto_code)
    c = bytearray(comp[src * COMP:(src + 1) * COMP])
    if not quiet:
        print("competition row copied from %s (region %d, flag %d)"
              % (proto_code, c[REGION_OFF], c[FLAG_OFF]))
    scid = c[CID_OFF]
    c[REGION_OFF], c[CID_OFF] = region, cid       # a byte, not an id: see enc_region
    put(c, CODE_OFF, code, COMP - CODE_OFF)
    comp += c

    # the regulation to copy is the one belonging to that same competition
    rsrc = next(i for i in range(nreg) if regs[i * REG + R_CID] == scid)
    g = bytearray(regs[rsrc * REG:(rsrc + 1) * REG])
    # +0x00 is a text id: non-zero means the menus look the name up and ignore the string
    # at +0x14.  Copying the Premier League's 79 gave a league called Premier League with
    # ten placeholder clubs in it.  Zero falls back to the inline name.
    g[R_NAMEID:R_NAMEID + 2] = bytes(2)
    g[R_ID:R_ID + 2] = reg.to_bytes(2, "little")
    g[R_CID] = cid
    g[R_TEAMS] = (g[R_TEAMS] & 0xc0) | (len(teams) & 0x3f)
    if tier is not None:
        set_tier(g, tier)
    put_names(g, 0, name)
    regs += g

    eid = max(int.from_bytes(ents[i * ENT + E_EID:i * ENT + E_EID + 4], "little")
              for i in range(nent))
    for k, t in enumerate(teams):
        e = bytearray(ENT)
        e[E_TEAM:E_TEAM + 4] = t.to_bytes(4, "little")
        e[E_EID:E_EID + 4] = (eid + 1 + k).to_bytes(4, "little")
        e[E_CID], e[E_ORDER] = cid, k + 1
        ents += e
    if not quiet:
        print("%s: competition %d, regulation %d, region %d, %d clubs, division %d"
              % (name, cid, reg, region, len(teams), get_tier(g)))
    return cid, reg


def write_tables(out, comp, regs, ents):
    d = os.path.join(out, "common", "etc", "pesdb")
    os.makedirs(d, exist_ok=True)
    sizes = {"Competition.bin": COMP, "CompetitionRegulation.bin": REG,
             "CompetitionEntry.bin": ENT}
    for n, b in (("Competition.bin", comp), ("CompetitionRegulation.bin", regs),
                 ("CompetitionEntry.bin", ents)):
        open(os.path.join(d, n), "wb").write(pesdb.wesys_pack(bytes(b)))
        print("  wrote %s (%d records)" % (n, len(b) // sizes[n]))


def main():
    a = sys.argv[1:]
    get = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    base, out = get("--base"), get("--out")
    if not base or not out:
        print(__doc__)
        return 1
    comp, regs, ents = (load(base, n) for n in
                        ("Competition.bin", "CompetitionRegulation.bin",
                         "CompetitionEntry.bin"))
    print("base: %d competitions, %d regulations, %d entries"
          % (len(comp) // COMP, len(regs) // REG, len(ents) // ENT))
    add_league(comp, regs, ents,
               int(get("--cid", "7")), int(get("--reg", "12")),
               int(get("--region", "16")), get("--name", "FL Test League"),
               get("--code", "FL_TEST_LEAGUE"),
               [int(x) for x in get("--teams", "").split(",") if x],
               get("--like", "ENGLAND_D1_LEAGUE"),
               tier=(int(get("--tier")) if get("--tier") else None))
    write_tables(out, comp, regs, ents)
    return 0


if __name__ == "__main__":
    sys.exit(main())
