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
R_NAMEID, R_ID, R_CID, R_TYPE, R_TEAMS, R_NAME = 0x00, 0x02, 0x08, 0x09, 0x0b, 0x14
NAME_SLOTS, NAME_SLOT = 20, 0x73
E_TEAM, E_EID, E_CID, E_ORDER = 0x00, 0x04, 0x08, 0x09


def load(d, n):
    return bytearray(pesdb.wesys_unpack(open(os.path.join(d, n), "rb").read()))


def put(b, off, s, n):
    v = s.encode("utf-8")[:n - 1]
    b[off:off + n] = v + b"\0" * (n - len(v))


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
    """
    if tier not in (1, 2, 3):
        raise SystemExit("tier %r is not 1, 2 or 3" % (tier,))
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

    src = None
    for i in range(ncomp):
        r = comp[i * COMP:(i + 1) * COMP]
        if r[CODE_OFF:].split(b"\0")[0].decode("latin1") == proto_code:
            src = i
            break
    if src is None:
        raise SystemExit("no competition row coded %s to copy" % proto_code)
    c = bytearray(comp[src * COMP:(src + 1) * COMP])
    if not quiet:
        print("competition row copied from %s (region %d, flag %d)"
              % (proto_code, c[REGION_OFF], c[FLAG_OFF]))
    scid = c[CID_OFF]
    c[REGION_OFF], c[CID_OFF] = region, cid
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
    for k in range(NAME_SLOTS):
        put(g, R_NAME + k * NAME_SLOT, name, NAME_SLOT)
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
