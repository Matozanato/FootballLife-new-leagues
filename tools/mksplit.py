r"""python mksplit.py --base <pesdb dir> --out <overlay root>
                    --split 60:16x2:8x1:8x1 [--split ...] [--ids 191,192,...] [--dry]

Turn one of our plain leagues into a split season, the way the Scottish Premiership ships.

How the shipped split is built (Scotland, competition 137, read 2026-09-25):

    reg 133  type 9 (split total), format 11, 12 clubs, rounds 0     "Scottish Premiership"
    reg 134  type 4 (league),      format 12, 12 clubs, rounds 3     "First Phase"
    reg 135  type 4,               format 13,  6 clubs, rounds 1     "Top Six"
    reg 136  type 4,               format 14,  6 clubs, rounds 1     "Bottom six"

Nothing in any of the four rows says which positions go where: the phases are found through
the competition id, their part is the format (12 regular, 13 top, 14 second, 15 lower), and
their size is the club count. No chain bits (+0x10 bits 18-20), no parent (+0x06), no
promotion links on the phases. Denmark and Belgium ship the same pattern with more groups.

Dates: the date switch sends 134-136 to case 42, which asks the row's format and hands a
regular phase 33 dates (days 226..100, rounds 0..32) and a top or bottom phase 5 more (days
107..142, rounds 0..4). The total, 133, gets no dates at all. A new phase id has no case, so
fl26swiss gives our phases their dates (see split_dates there); this tool only writes the rows.

What is written, per --split TOTAL:REGULAR:TOP[:SECOND[:LOWER...]] (each part CLUBSxROUNDS):

    the league's own row TOTAL becomes the split total: type 9, format 11, rounds 0, and the
    regular phase's club count. Everything else stays -- its region, tier, matchday template,
    names, promotion links, and its competition, so every module keyed on the competition or
    on TOTAL (Select Team, slot names, clubs, join) still finds it.

    one new row per phase, copied from TOTAL's original row, directly after it in the table:
    type 4, the phase's format, clubs and rounds, a fresh id, no promotion links, and the
    league name with the phase's name after it.

The competition row and the entries are not touched: a competition has one entry list, and
all its phases draw from it.

Output is an overlay root holding only the three competition tables. Put it ABOVE the world
in sider.ini (the first root that has a file wins) and remove the line to go back.

    python mksplit.py --base ...\livecpk\_FL26MyWorld\common\etc\pesdb ^
                      --out ...\livecpk\_FL26Split ^
                      --split 60:16x2:8x1:8x1 --split 93:12x2:6x2:6x2 --ids 191,192,193,194,195,196
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mkleague as M
import mkworld as W

R_PROMO, R_PARENT, R_FMT, R_RND = 0x04, 0x06, 0x0c, 0x10
TOTAL_TYPE, LEAGUE_TYPE = 9, 4
F_TOTAL, F_REGULAR, F_TOP, F_SECOND, F_LOWER = 11, 12, 13, 14, 15
PHASE_NAME = {F_REGULAR: "Regular Season", F_TOP: "Championship Round",
              F_SECOND: "Relegation Round", F_LOWER: "Lower Round"}


def rid(row):
    return int.from_bytes(row[M.R_ID:M.R_ID + 2], "little")


def set_u32_bits(row, off, shift, width, value):
    v = int.from_bytes(row[off:off + 4], "little")
    mask = ((1 << width) - 1) << shift
    v = (v & ~mask) | ((value << shift) & mask)
    row[off:off + 4] = v.to_bytes(4, "little")


def set_shape(row, kind, fmt, clubs, rounds):
    if not 0 < clubs < 64:
        raise SystemExit("the club count is six bits wide, so %d will not fit" % clubs)
    if not 0 <= rounds < 8:
        raise SystemExit("the round-robin count is three bits wide, so %d will not fit" % rounds)
    row[M.R_TYPE] = kind
    row[M.R_TEAMS] = (row[M.R_TEAMS] & ~0x3f) | clubs
    set_u32_bits(row, R_FMT, 12, 6, fmt)
    set_u32_bits(row, R_RND, 12, 3, rounds)


def parse_split(s):
    bits = s.split(":")
    if len(bits) < 3:
        raise SystemExit("--split wants TOTAL:REGULAR:TOP[:SECOND...], got %r" % s)
    parts = []
    for b in bits[1:]:
        c, _x, r = b.partition("x")
        parts.append((int(c), int(r)))
    return int(bits[0]), parts


def main():
    a = sys.argv[1:]
    get = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    base, out = get("--base"), get("--out")
    splits = [parse_split(v) for k, v in zip(a, a[1:]) if k == "--split"]
    if not base or not out or not splits:
        print(__doc__)
        return 1
    comp, regs, ents = (M.load(base, n) for n in
                        ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin"))
    rows = [bytearray(regs[i * M.REG:(i + 1) * M.REG]) for i in range(len(regs) // M.REG)]
    used = {rid(r) & 0x3ff for r in rows}

    need = sum(len(p) for _t, p in splits)
    if get("--ids"):
        ids = [int(x) for x in get("--ids").split(",")]
    else:
        ids = W.free_ids(used | W.BAD_REG | set(W.MOVED_REG.values()), 255, need, 191)
    if len(ids) < need:
        raise SystemExit("%d phase ids needed, %d given" % (need, len(ids)))
    for i in ids:
        if i in used or i in W.BAD_REG:
            raise SystemExit("regulation id %d is taken or known bad" % i)

    k = 0
    for total, parts in splits:
        at = [n for n, r in enumerate(rows) if rid(r) == total]
        if len(at) != 1:
            raise SystemExit("regulation %d: %d rows, expected one" % (total, len(at)))
        src = rows[at[0]]
        if src[M.R_TYPE] != LEAGUE_TYPE:
            raise SystemExit("regulation %d is type %d, not a plain league (already split?)"
                             % (total, src[M.R_TYPE]))
        name = M.pesdb.cstr(src[M.R_NAME:M.R_NAME + M.NAME_SLOT])
        (rc, rr), mini = parts[0], parts[1:]
        if sum(c for c, _r in mini) != rc:
            print("note: regulation %d -- the groups hold %d clubs, the regular phase %d"
                  % (total, sum(c for c, _r in mini), rc))
        fmts = [F_REGULAR, F_TOP] + [F_SECOND] + [F_LOWER] * max(0, len(mini) - 2)
        new = []
        for (clubs, rounds), fmt in zip(parts, fmts):
            g = bytearray(src)
            g[M.R_ID:M.R_ID + 2] = ids[k].to_bytes(2, "little")
            g[0:2] = bytes(2)                          # relegates into nothing
            g[R_PROMO:R_PROMO + 2] = bytes(2)          # promotes into nothing
            g[R_PARENT:R_PARENT + 2] = bytes(2)
            set_shape(g, LEAGUE_TYPE, fmt, clubs, rounds)
            for s in range(M.NAME_SLOTS):
                M.put(g, M.R_NAME + s * M.NAME_SLOT, "%s %s" % (name, PHASE_NAME[fmt]), M.NAME_SLOT)
            new.append(g)
            print("  reg %3d  %-20s %2d clubs x %d = %2d rounds" % (
                ids[k], PHASE_NAME[fmt], clubs, rounds, (clubs - 1 if clubs % 2 == 0 else clubs) * rounds))
            k += 1
        set_shape(src, TOTAL_TYPE, F_TOTAL, rc, 0)
        print("reg %d %s -> split total over %d clubs, phases %s"
              % (total, name, rc, ",".join(str(rid(g)) for g in new)))
        rows[at[0] + 1:at[0] + 1] = new

    regs = bytearray(b"".join(rows))
    print("%d regulation rows (%d added)" % (len(rows), need))
    if "--dry" in a:
        print("dry run: nothing written")
        return 0
    M.write_tables(out, comp, regs, ents)
    return 0


if __name__ == "__main__":
    sys.exit(main())
