r"""python splitdiff.py <world pesdb dir> --base <base pesdb dir> --ours <total reg id> --game 133

How one of our split leagues differs from the game's own (Scotland: regulations 133 total,
134 regular, 135 top six, 136 bottom six; Denmark and Belgium the same pattern).

At the end of a season the game finds no final table for our split total row, so nobody is
promoted or relegated. This tool only prints bytes, it does not say what a field means:

  1. a table of every row of the pair -- the total row and its phase rows on each side -- by
     id, type, format, clubs, rounds, region, tier, the words at +0x04, +0x06 and +0x7e (the
     "league below" link the task names) and the 32-bit words at +0x10 and +0x30c;
  2. per pair (total vs total, then each phase format against the same format) every byte
     offset where our row differs from the game's, as "+0xNNN  game XX  ours YY", the name
     slots (mkleague.name_at .. +NAME_SLOT, twenty runs) left out and neighbouring offsets
     grouped into one line;
  3. under "candidates" every offset that is non-zero on ALL the game's split rows and zero on
     all of ours -- a field our split rows may lack.

The rows are found the way mkleague and mksplit store them: the regulation id at M.R_ID, the
competition id at M.R_CID, the type at M.R_TYPE, the club count at M.R_TEAMS, the format and
the rounds in the word at 0x0c / 0x10 (mksplit.R_FMT, R_RND), the tier in the word at 0x10
(mkleague.R_TIER). The phases are the rows of the total's own competition id whose format is
12..15. The region is Competition.bin's, decoded with mkleague.dec_region.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mkleague as M

R_FMT, R_RND = 0x0c, 0x10                       # mksplit.R_FMT, R_RND: bits 12..17 / 12..14
R_PROMO, R_PARENT = 0x04, 0x06
R_BELOW_LINK = 0x7e                             # the offset the task names the "league below"
PHASE_FMTS = (12, 13, 14, 15)                   # regular, top, second, lower (mksplit)
NAME_OFFS = [M.name_at(k) for k in range(M.NAME_SLOTS)]


def rows(d):
    regs = M.load(d, "CompetitionRegulation.bin")
    return [regs[i * M.REG:(i + 1) * M.REG] for i in range(len(regs) // M.REG)]


def rid(g):
    return int.from_bytes(g[M.R_ID:M.R_ID + 2], "little")


def u16(g, o):
    return int.from_bytes(g[o:o + 2], "little")


def u32(g, o):
    return int.from_bytes(g[o:o + 4], "little")


def fmt(g):
    return (u32(g, R_FMT) >> 12) & 0x3f


def rounds(g):
    return (u32(g, R_RND) >> 12) & 7


def in_name(o):
    """whether offset o lies inside one of the twenty name slots (mkleague.name_at)"""
    return any(a <= o < a + M.NAME_SLOT for a in NAME_OFFS)


def regions(d):
    """{competition id: region id} from Competition.bin (mkleague.dec_region)"""
    comp = M.load(d, "Competition.bin")
    return {comp[i * M.COMP + M.CID_OFF]: M.dec_region(comp[i * M.COMP + M.REGION_OFF])
            for i in range(len(comp) // M.COMP)}


def find(rs, want):
    for g in rs:
        if rid(g) == want:
            return g
    return None


def phases_of(rs, total):
    """the rows of the total's own competition id whose format is 12..15, sorted by format,
    the total itself left out"""
    cid = total[M.R_CID]
    return sorted((g for g in rs if g[M.R_CID] == cid and fmt(g) in PHASE_FMTS
                   and g is not total and rid(g) != rid(total)), key=fmt)


def describe(side, g, region):
    return ("  %-5s reg %3d  type %d  fmt %2d  clubs %2d  rounds %d  region %s  tier %d"
            "  +0x04=0x%04x  +0x06=0x%04x  +0x7e=0x%04x  +0x10=0x%08x  +0x30c=0x%08x"
            % (side, rid(g), g[M.R_TYPE], fmt(g), g[M.R_TEAMS] & 0x3f, rounds(g),
               region.get(g[M.R_CID], "-"), M.get_tier(g), u16(g, R_PROMO), u16(g, R_PARENT),
               u16(g, R_BELOW_LINK), u32(g, R_RND), u32(g, 0x30c)))


def runs_of(offs):
    """group runs of neighbouring offsets"""
    runs, cur = [], []
    for o in offs:
        if cur and o == cur[-1] + 1:
            cur.append(o)
        else:
            if cur:
                runs.append(cur)
            cur = [o]
    if cur:
        runs.append(cur)
    return runs


def show_diff(title, ours, game):
    print(title)
    runs = runs_of([o for o in range(M.REG) if not in_name(o) and ours[o] != game[o]])
    if not runs:
        print("  (identical outside the name slots)")
        return
    for run in runs:
        lo, hi = run[0], run[-1]
        gb = " ".join("%02x" % game[o] for o in run)
        ob = " ".join("%02x" % ours[o] for o in run)
        span = "+0x%03x" % lo if lo == hi else "+0x%03x..0x%03x" % (lo, hi)
        print("  %-18s  game %s  ours %s" % (span, gb, ob))


def main():
    a = sys.argv[1:]
    if not a or a[0].startswith("-"):
        print(__doc__)
        return 1
    world = a[0]
    get = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    base = get("--base")
    game = int(get("--game", "133"))
    if not base or get("--ours") is None:
        print(__doc__)
        return 1
    ours = int(get("--ours"))

    world_region, base_region = regions(world), regions(base)
    wrows, brows = rows(world), rows(base)
    wtotal, gtotal = find(wrows, ours), find(brows, game)
    if wtotal is None:
        print("no regulation %d in %s" % (ours, world))
        return 2
    if gtotal is None:
        print("no regulation %d in %s" % (game, base))
        return 2

    wph, gph = phases_of(wrows, wtotal), phases_of(brows, gtotal)

    print("world %s: total reg %d, phases %s (fmts %s)"
          % (world, ours, [rid(g) for g in wph], [fmt(g) for g in wph]))
    print("base  %s: total reg %d, phases %s (fmts %s)"
          % (base, game, [rid(g) for g in gph], [fmt(g) for g in gph]))
    print()

    print("rows (the total row and its phase rows, both sides):")
    print(describe("ours", wtotal, world_region))
    print(describe("game", gtotal, base_region))
    for g in wph:
        print(describe("ours", g, world_region))
    for g in gph:
        print(describe("game", g, base_region))
    print()

    print("byte differences (name slots left out):")
    show_diff("total reg %d vs reg %d:" % (ours, game), wtotal, gtotal)
    gfmt = {fmt(g): g for g in gph}
    for g in wph:
        if fmt(g) in gfmt:
            show_diff("phase fmt %d: reg %d vs reg %d:" % (fmt(g), rid(g), rid(gfmt[fmt(g)])),
                      g, gfmt[fmt(g)])
        else:
            print("phase fmt %d: reg %d vs reg -- (the game has no such phase)" % (fmt(g), rid(g)))
    print()

    print("candidates (non-zero on all the game's split rows, zero on all of ours):")
    allg = [gtotal] + gph
    allw = [wtotal] + wph
    cruns = runs_of([o for o in range(M.REG) if not in_name(o)
                     and all(g[o] for g in allg) and all(not w[o] for w in allw)])
    if not cruns:
        print("  none")
    else:
        for run in cruns:
            lo, hi = run[0], run[-1]
            vals = " ".join("%02x" % g[lo] for g in allg)
            rng = "+0x%03x" % lo if lo == hi else "+0x%03x..+0x%03x" % (lo, hi)
            print("  %-18s game %s  ours 00" % (rng, vals))
    return 0


if __name__ == "__main__":
    sys.exit(main())
