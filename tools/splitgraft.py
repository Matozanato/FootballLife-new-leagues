r"""python splitgraft.py <world pesdb dir> --base <base pesdb dir> --ours <total reg id>
                        --game 133 --offsets 0x0f[,0x10-0x13,...] [--dry-run]

Give our split rows the game's own bytes, for an in-game test.

At the end of a season the game finds no final table for our split league's total row, so
nobody is promoted or relegated. tools/splitdiff.py found byte +0x0f = 0x25 on all four of
the game's Scottish split rows (133 total, 134 regular, 135 top, 136 bottom) and 0 on all of
ours, and the 32-bit word at +0x10 differs too. This tool copies the game's bytes at the
named offsets into our rows, so a world can be tried in the game to see whether those bytes
are what is missing.

The rows and the pairs are found exactly as tools/splitdiff.py finds them (it is imported,
not copied): the total row on each side, then every phase format against the game row of the
same format -- total-total, regular-regular, top-top, bottom-bottom.

    --offsets  single hex offsets and inclusive hex ranges, comma-separated: 0x0f,0x10-0x13
    --dry-run  print every byte that would change and write nothing

Every byte it changes is printed as "reg <id> +0xNN  XX -> YY". An offset inside a name slot
(mkleague.NAME_SLOT..NAME_END, which splitdiff leaves out) or beyond the record size is
refused with exit 2. The file is written back the way mkleague / mksplit write it -- the
WESYS pack mkleague.load undoes -- with the original header kept, so CompetitionRegulation.bin
loads back byte-for-byte identical except at the grafted offsets.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mkleague as M
import pesdb
import splitdiff as SD


def parse_offsets(s):
    """[int] from "0x0f,0x10-0x13": single hex offsets and inclusive hex ranges"""
    out = []
    for tok in s.split(","):
        tok = tok.strip()
        if not tok:
            continue
        if "-" in tok:
            lo, _dash, hi = tok.partition("-")
            lo, hi = int(lo, 16), int(hi, 16)
            if hi < lo:
                raise SystemExit("--offsets %r: the range end is below its start" % tok)
            out += list(range(lo, hi + 1))
        else:
            out.append(int(tok, 16))
    if not out:
        raise SystemExit("--offsets %r holds no offset" % s)
    return out


def pairs(wrows, brows, ours, game):
    """[(our row, game row, label)]: the total row against the total row, then each of our
    phase rows against the game row of the same format -- the way splitdiff pairs them"""
    wtotal, gtotal = SD.find(wrows, ours), SD.find(brows, game)
    if wtotal is None:
        raise SystemExit("no regulation %d in %s" % (ours, "the world"))
    if gtotal is None:
        raise SystemExit("no regulation %d in %s" % (game, "the base"))
    out = [(wtotal, gtotal, "total reg %d vs reg %d" % (ours, game))]
    gfmt = {SD.fmt(g): g for g in SD.phases_of(brows, gtotal)}
    for g in SD.phases_of(wrows, wtotal):
        if SD.fmt(g) in gfmt:
            out.append((g, gfmt[SD.fmt(g)],
                        "phase fmt %d: reg %d vs reg %d" % (SD.fmt(g), SD.rid(g), SD.rid(gfmt[SD.fmt(g)]))))
        else:
            print("phase fmt %d: reg %d vs reg -- (the game has no such phase, not grafted)"
                  % (SD.fmt(g), SD.rid(g)))
    return out


def main():
    a = sys.argv[1:]
    if not a or a[0].startswith("-"):
        print(__doc__)
        return 1
    world = a[0]
    get = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    base = get("--base")
    if not base or get("--ours") is None or not get("--offsets"):
        print(__doc__)
        return 1
    ours, game = int(get("--ours")), int(get("--game", "133"))
    dry = "--dry-run" in a
    offs = parse_offsets(get("--offsets"))
    for o in offs:
        if o >= M.REG:
            raise SystemExit("offset +0x%02x is beyond the record (%d bytes)" % (o, M.REG))
        if SD.in_name(o):
            raise SystemExit("offset +0x%02x falls inside a name slot (M.NAME_SLOT..M.NAME_END)" % o)

    regs = M.load(world, "CompetitionRegulation.bin")
    wrows = [regs[i * M.REG:(i + 1) * M.REG] for i in range(len(regs) // M.REG)]
    brows = SD.rows(base)

    changed = 0
    for w, g, label in pairs(wrows, brows, ours, game):
        for o in offs:
            if w[o] != g[o]:
                print("reg %d +0x%02x  %02x -> %02x" % (SD.rid(w), o, w[o], g[o]))
                w[o] = g[o]
                changed += 1
    if not changed:
        print("nothing to change: our rows already hold the game's bytes at %s"
              % ",".join("0x%02x" % o for o in offs))
    print("%d byte(s) %s" % (changed, "would change" if dry else "changed"))
    if dry:
        print("dry run: nothing written")
        return 0

    path = os.path.join(world, "CompetitionRegulation.bin")
    with open(path, "rb") as f:
        hdr = f.read(3)                     # the three header bytes wesys_unpack ignores
    with open(path, "wb") as f:
        f.write(pesdb.wesys_pack(bytes(b"".join(wrows)), hdr))
    print("wrote %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
