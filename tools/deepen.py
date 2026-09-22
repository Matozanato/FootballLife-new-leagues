r"""deepen.py -- put one of OUR leagues underneath an existing pyramid, one division lower

France and Italy ship two divisions each (Ligue 1 / Ligue 2, Serie A / Serie BKT). This takes
a league we built and makes it the tier below: same region, the parent's calendar shape, a
rank one step below the parent, and the promotion link written both ways. Run it again on the
league it just created and you get a fourth division, and again for a fifth.

With --deep-rank the child gets the parent's rank plus one, which is only readable with
sider/fl26rank.lua installed (the shipped rank field is two bits and stops at 3). Without the
flag every league below a second division is marked 3, as before -- and three leagues all
marked 3 is exactly why the League Info panel shows France D4 as its own lower league.

What it changes, exactly:

  our league's regulation   region byte (Competition.bin +3) -> the parent's
                            +0x10 dword -> the parent's, with the tier set one below it
                            +0x04 (promotes into) -> the parent's regulation id
  the parent's regulation    +0x00 (relegates into) -> our regulation id

That last line is the first time this project writes into a SHIPPED competition's record, and
it is worth being plain about: it does not replace or remove anything, but it does change how
Ligue 2 behaves -- its bottom clubs now have somewhere to fall. It is written into your own
livecpk copy of the table, never into the game's files, so removing the root undoes it.

How deep it can go, and what the fourth division costs. The tier is two bits at runtime,
unless sider/fl26rank.lua is installed to widen it to three -- the shipped setter at
0x1414c9cc0 is

    and dword [rcx+0x304], 0x3fffffff ; movzx eax, dl ; shl eax, 30 ; or [rcx+0x304], eax

so whatever the file holds, only 1, 2 and 3 exist. That turns out not to be the thing that
stops a fourth division: what matters is which gates 0x141510430 uses to answer "where does
this club move to". Promotion is gated on tier >= 2 and then simply returns the +0x7c link,
so a fourth-level league marked tier 3 promotes into the third level with no patch at all.
Relegation is gated twice -- tier == 1, or (this == 2 and the one below == 3) -- and a
tier-3 league matches neither, so the third level never sends anybody down.

So: a fourth (and fifth) division works one-way out of the box, clubs climbing but never
falling, and becomes symmetric with one byte at 0x141510617 (jne -> jb), which is what
sider/fl26deep4.lua writes. This tool lets you build the chain either way and says which
of the two you are getting.

    python deepen.py --root <livecpk root> --league 49 --below 81     # FL 02 -> Ligue 3
    python deepen.py --root <livecpk root> --league 60 --below 49     # and FL 03 -> Ligue 4
    python deepen.py --root <livecpk root> --show                     # every pyramid, as it stands
    python deepen.py --root <livecpk root> --retier 20,18,11          # renumber built chains 1,2,3,4,5
    python deepen.py --root <livecpk root> --league 49 --below 81 --dry

Nothing here has been run in a game.
"""
import os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pesdb
import mkleague as M

R_BELOW, R_ABOVE = 0x00, 0x04           # u16 each: the division under / over this one
PESDB = os.path.join("common", "etc", "pesdb")


def load(root):
    d = os.path.join(root, PESDB)
    out = {}
    for n in ("Competition.bin", "CompetitionRegulation.bin"):
        out[n] = bytearray(pesdb.wesys_unpack(open(os.path.join(d, n), "rb").read()))
    return out


def save(root, tables):
    d = os.path.join(root, PESDB)
    for n, b in tables.items():
        open(os.path.join(d, n), "wb").write(pesdb.wesys_pack(bytes(b)))
        print("  wrote %s" % n)


def comp_index(comp):
    """competition id -> (row index, code, region byte)"""
    out = {}
    for i in range(len(comp) // M.COMP):
        r = comp[i * M.COMP:(i + 1) * M.COMP]
        out[r[M.CID_OFF]] = (i, r[M.CODE_OFF:].split(b"\0")[0].decode("latin1"), r[M.REGION_OFF])
    return out


def reg_index(regs):
    """regulation id -> row index"""
    out = {}
    for i in range(len(regs) // M.REG):
        rid = int.from_bytes(regs[i * M.REG + M.R_ID:i * M.REG + M.R_ID + 2], "little")
        out[rid] = i
    return out


def row(regs, i):
    return bytearray(regs[i * M.REG:(i + 1) * M.REG])


def put_row(regs, i, r):
    regs[i * M.REG:(i + 1) * M.REG] = r


def u16(r, off):
    return int.from_bytes(r[off:off + 2], "little")


def set_u16(r, off, v):
    r[off:off + 2] = v.to_bytes(2, "little")


def describe(regs, comp, rid):
    ci, ri = comp_index(comp), reg_index(regs)
    r = row(regs, ri[rid])
    code, region = ci.get(r[M.R_CID], (0, "?", 0))[1:]
    return ("reg %-4d %-22s region %3d tier %d clubs %2d  above=%-4s below=%-4s"
            % (rid, code, region, M.get_tier(r), r[M.R_TEAMS] & 0x3f,
               u16(r, R_ABOVE) or "-", u16(r, R_BELOW) or "-"))


def show(regs, comp):
    ri = reg_index(regs)
    linked = []
    for rid, i in sorted(ri.items()):
        r = row(regs, i)
        if u16(r, R_ABOVE) or u16(r, R_BELOW):
            linked.append(rid)
    print("%d regulations carry a tier link:" % len(linked))
    for rid in linked:
        print("  " + describe(regs, comp, rid))


def retier(root, tables, regs, comp, roots, dry):
    """Walk each named pyramid from the top and give every division its real rank.

    A chain that was built before the rank was widened has every league below the second
    marked 3, because 3 was as high as the field went. This renumbers them 1, 2, 3, 4, 5 by
    where they actually sit, which is only readable with sider/fl26rank.lua installed.

    The roots are named explicitly -- `--retier 20,18,11` -- so a chain whose shape is still
    an open question (J1 relegating into our reg 145, say) is never renumbered by accident.
    """
    if not roots:
        raise SystemExit("--retier needs the top division of each pyramid, e.g. --retier 20,18,11")
    ri = reg_index(regs)
    changed = 0
    for top in [int(x) for x in roots.replace(" ", "").split(",") if x]:
        if top not in ri:
            raise SystemExit("no regulation %d in this world" % top)
        rid, depth, seen = top, 1, set()
        while rid and rid in ri and rid not in seen:
            seen.add(rid)
            r = row(regs, ri[rid])
            was = M.get_tier(r)
            if was != depth:
                M.set_tier(r, depth)
                put_row(regs, ri[rid], r)
                changed += 1
                print("  reg %-4d tier %d -> %d" % (rid, was, depth))
            else:
                print("  reg %-4d tier %d" % (rid, was))
            rid, depth = u16(r, R_BELOW), depth + 1
    if not changed:
        print("every division already carries its real rank; nothing written")
        return 0
    if dry:
        print("--dry: %d change(s) not written" % changed)
        return 0
    save(root, tables)
    return 0


def main(argv):
    get = lambda k, d=None: argv[argv.index(k) + 1] if k in argv else d
    root = get("--root")
    if not root:
        print(__doc__)
        return 1
    tables = load(root)
    comp, regs = tables["Competition.bin"], tables["CompetitionRegulation.bin"]

    if "--show" in argv:
        show(regs, comp)
        return 0

    if "--retier" in argv:
        return retier(root, tables, regs, comp, get("--retier"), "--dry" in argv)

    league, below = get("--league"), get("--below")
    if not league or not below:
        print(__doc__)
        return 1
    league, below = int(league), int(below)
    deep_rank = "--deep-rank" in argv
    ri, ci = reg_index(regs), comp_index(comp)
    for rid in (league, below):
        if rid not in ri:
            raise SystemExit("no regulation %d in this world" % rid)

    parent = row(regs, ri[below])
    child = row(regs, ri[league])
    ptier = M.get_tier(parent)
    if ptier < 2 or ptier > 6:
        raise SystemExit("regulation %d is tier %d; a new division goes under a second one or "
                         "lower, and the rank field stops at 7" % (below, ptier))
    ctier = ptier + 1 if deep_rank else 3
    if u16(parent, R_BELOW):
        raise SystemExit("regulation %d already relegates into %d" % (below, u16(parent, R_BELOW)))

    pcomp_i, pcode, pregion = ci[parent[M.R_CID]]
    ccomp_i, ccode, cregion = ci[child[M.R_CID]]
    print("parent: " + describe(regs, comp, below))
    print("child : " + describe(regs, comp, league))

    # the child inherits the parent's calendar shape, and is one tier lower
    pdword = struct.unpack_from("<I", parent, 0x10)[0]
    struct.pack_into("<I", child, 0x10, pdword)
    M.set_tier(child, ctier)
    set_u16(child, R_ABOVE, below)
    set_u16(child, R_BELOW, 0)
    set_u16(parent, R_BELOW, league)

    newcomp = bytearray(comp[ccomp_i * M.COMP:(ccomp_i + 1) * M.COMP])
    newcomp[M.REGION_OFF] = pregion

    print("after :")
    print("  child  region %d -> %d, F+0x10 %08x -> %08x, tier %d, promotes into %d"
          % (cregion, pregion, struct.unpack_from("<I", row(regs, ri[league]), 0x10)[0],
             struct.unpack_from("<I", child, 0x10)[0], ctier, below))
    print("  parent %s now relegates into %d" % (pcode, league))
    if ptier >= 3 and not deep_rank:
        print("  NOTE: the parent is already a third division, so this is a fourth (or deeper),")
        print("        and without --deep-rank the child is marked tier 3 as well, which is")
        print("        what makes the League Info panel confuse the two. Promotion up works as")
        print("        it stands. Relegation down from the parent does NOT, until")
        print("        sider/fl26deeprank.lua is installed -- see its header.")
    elif deep_rank:
        print("  NOTE: tier %d is only readable with sider/fl26rank.lua installed, which moves"
              % ctier)
        print("        the runtime rank field down to bits 29-31. Without it the game reads")
        print("        this league as tier %d." % (ctier & 3))

    if "--dry" in argv:
        print("--dry: nothing written")
        return 0

    put_row(regs, ri[league], child)
    put_row(regs, ri[below], parent)
    comp[ccomp_i * M.COMP:(ccomp_i + 1) * M.COMP] = newcomp
    save(root, tables)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
