r"""deepen.py -- put one of OUR leagues underneath a shipped pyramid as its third division

France and Italy ship two divisions each (Ligue 1 / Ligue 2, Serie A / Serie BKT). This takes
a league we built and makes it the tier below: same region, the parent's calendar shape, tier
3, and the promotion link written both ways.

What it changes, exactly:

  our league's regulation   region byte (Competition.bin +3) -> the parent's
                            +0x10 dword -> the parent's, with the tier set to 3
                            +0x04 (promotes into) -> the parent's regulation id
  the parent's regulation    +0x00 (relegates into) -> our regulation id

That last line is the first time this project writes into a SHIPPED competition's record, and
it is worth being plain about: it does not replace or remove anything, but it does change how
Ligue 2 behaves -- its bottom clubs now have somewhere to fall. It is written into your own
livecpk copy of the table, never into the game's files, so removing the root undoes it.

Why three and not five: the tier is two bits at runtime. The setter at 0x1414c9cc0 is

    and dword [rcx+0x304], 0x3fffffff ; movzx eax, dl ; shl eax, 30 ; or [rcx+0x304], eax

so whatever the file holds, only two bits survive: 1, 2, 3. A fourth division cannot be
expressed as a tier of its own, and every reader (0x141510430, 0x1415141c0, 0x14131f430 ...)
compares against 0x40000000 / 0x80000000 / 0xc0000000 and nothing else. So a shipped
two-division country can be given exactly one more division, and a country of ours can be
three deep. Anything beyond that needs a different mechanism, not a bigger number.

    python deepen.py --root <livecpk root> --league 49 --below 81     # FL 02 -> Ligue 3
    python deepen.py --root <livecpk root> --show                     # every pyramid, as it stands
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

    league, below = get("--league"), get("--below")
    if not league or not below:
        print(__doc__)
        return 1
    league, below = int(league), int(below)
    ri, ci = reg_index(regs), comp_index(comp)
    for rid in (league, below):
        if rid not in ri:
            raise SystemExit("no regulation %d in this world" % rid)

    parent = row(regs, ri[below])
    child = row(regs, ri[league])
    ptier = M.get_tier(parent)
    if ptier != 2:
        raise SystemExit("regulation %d is tier %d; a third division goes under a SECOND one"
                         % (below, ptier))
    if u16(parent, R_BELOW):
        raise SystemExit("regulation %d already relegates into %d" % (below, u16(parent, R_BELOW)))

    pcomp_i, pcode, pregion = ci[parent[M.R_CID]]
    ccomp_i, ccode, cregion = ci[child[M.R_CID]]
    print("parent: " + describe(regs, comp, below))
    print("child : " + describe(regs, comp, league))

    # the child inherits the parent's calendar shape, and is one tier lower
    pdword = struct.unpack_from("<I", parent, 0x10)[0]
    struct.pack_into("<I", child, 0x10, pdword)
    M.set_tier(child, 3)
    set_u16(child, R_ABOVE, below)
    set_u16(child, R_BELOW, 0)
    set_u16(parent, R_BELOW, league)

    newcomp = bytearray(comp[ccomp_i * M.COMP:(ccomp_i + 1) * M.COMP])
    newcomp[M.REGION_OFF] = pregion

    print("after :")
    print("  child  region %d -> %d, F+0x10 %08x -> %08x, tier 3, promotes into %d"
          % (cregion, pregion, struct.unpack_from("<I", row(regs, ri[league]), 0x10)[0],
             struct.unpack_from("<I", child, 0x10)[0], below))
    print("  parent %s (SHIPPED) now relegates into %d" % (pcode, league))

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
