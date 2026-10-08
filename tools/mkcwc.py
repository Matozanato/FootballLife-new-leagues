r"""python mkcwc.py --base <pesdb dir> --out <livecpk root> [--ko 200] [--dry]

Reshape the FIFA Club World Cup (competition 1) into the 2025 format: 32 clubs in eight groups
of four, each group played once round, then a single-match knockout of sixteen.

The shipped Club World Cup is one row, regulation 1: a four-club single-match knockout played
in mid-December (date case 0, days 348-352). Nothing about it is kept except its identity --
the competition row, its id, and the name in all twenty language slots. The two phases are
borrowed from shapes the engine already plays:

  regulation 1        the group stage.  Copied from the Copa Libertadores group stage (reg 9:
                      a CLUB competition, 32 clubs, eight groups, eight replicas), with one
                      change: rounds (+0x10 bits 12-14) 2 -> 1, so each group is played once
                      round, as the World Cup's group stage (reg 34) declares it.  Its replicas
                      become 1025, 2049 ... 8193 (master + (group + 1) * 1024), each pointing
                      back at 1 on +0x06.
  regulation --ko     the knockout.  The shipped regulation 1 row itself -- single match, the
                      Club World Cup's own format template -- with its club count 4 -> 16.

The group stage keeps id 1 on purpose: the game's own Club World Cup code (0x141366200 and the
pools it calls, findings.md) hands its entrants to competition 1 and starts regulation 1, and
fl26swiss.dll turns that moment into the 32-club draw.  The knockout has an id the exe has never
heard of; fl26swiss fills and starts it when the groups end, and dates both phases.

Entries (CompetitionEntry) are not touched: the field is chosen from league tables at run time
(fl26swiss CWC access list), not from a fixed list.

--dry prints the plan and writes nothing.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mkleague as M

R_BACK, R_GROUP, R_ROUNDS_DW = 0x06, 0x0a, 0x10
REPLICA_STEP, NO_GROUP = 1024, 255
NAMES = slice(M.R_NAME, M.R_NAME + M.NAME_SLOTS * M.NAME_SLOT)
CWC_CID, CWC_REG, GROUPS_FROM = 1, 1, 9          # 9 = Copa Libertadores group stage
GROUPS, CLUBS = 8, 32


def rid(r):
    return int.from_bytes(r[M.R_ID:M.R_ID + 2], "little")


def rows(regs):
    return [bytearray(regs[i:i + M.REG]) for i in range(0, len(regs), M.REG)]


def main():
    a = sys.argv[1:]
    get = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    base, out = get("--base"), get("--out")
    if not base or (not out and "--dry" not in a):
        print(__doc__)
        return 1
    ko = int(get("--ko", "200"))
    comp, regs, ents = (M.load(base, n) for n in
                        ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin"))
    R = rows(regs)
    used = {rid(r) for r in R}
    if ko in used:
        raise SystemExit("regulation %d is taken in this world; pick another --ko" % ko)
    if not 175 < ko < REPLICA_STEP:
        raise SystemExit("--ko wants a free id between 176 and 1023")

    cwc = [r for r in R if r[M.R_CID] == CWC_CID]
    if len(cwc) != 1 or rid(cwc[0]) != CWC_REG:
        raise SystemExit("competition 1 is not the shipped one-row Club World Cup here "
                         "(%d rows: %s) -- already reshaped?" % (len(cwc), [rid(r) for r in cwc]))
    old = cwc[0]
    src = [r for r in R if rid(r) & 0x3ff == GROUPS_FROM and r[M.R_CID] == 5]
    master = [r for r in src if r[R_GROUP] == NO_GROUP]
    reps = sorted((r for r in src if r[R_GROUP] != NO_GROUP), key=lambda r: r[R_GROUP])
    if len(master) != 1 or len(reps) != GROUPS or (master[0][M.R_TEAMS] & 0x3f) != CLUBS:
        raise SystemExit("the Libertadores group stage is not 32 clubs in 8 replicas here "
                         "(%d master, %d replicas)" % (len(master), len(reps)))

    new = []
    for r in master + reps:
        g = bytearray(r)
        g[M.R_BELOW:M.R_BELOW + 2] = bytes(2)
        g[M.R_CID] = CWC_CID
        grp = g[R_GROUP]
        g[M.R_ID:M.R_ID + 2] = (CWC_REG if grp == NO_GROUP
                                else CWC_REG + (grp + 1) * REPLICA_STEP).to_bytes(2, "little")
        if grp != NO_GROUP:
            g[R_BACK:R_BACK + 2] = CWC_REG.to_bytes(2, "little")
        dw = int.from_bytes(g[R_ROUNDS_DW:R_ROUNDS_DW + 4], "little")
        dw = (dw & ~(7 << 12)) | (1 << 12)                       # once round
        g[R_ROUNDS_DW:R_ROUNDS_DW + 4] = dw.to_bytes(4, "little")
        g[NAMES] = old[NAMES]
        # +0x0f bits 0-5 (runtime +0x310 bits 0-5) differ per competition and not per shape --
        # 1 Champions League, 5 Europa League, 7 Libertadores, 13 AFC, 0 the Club World Cup and
        # the World Cup -- so they are the competition's own, not the borrowed stage's
        g[0x0f] = (g[0x0f] & 0xc0) | (old[0x0f] & 0x3f)
        new.append(g)
    k = bytearray(old)
    k[M.R_ID:M.R_ID + 2] = ko.to_bytes(2, "little")
    k[M.R_TEAMS] = (k[M.R_TEAMS] & ~0x3f) | 16
    new.append(k)

    for g in new:
        if rid(g) != CWC_REG and rid(g) in used:
            raise SystemExit("regulation %d is taken in this world" % rid(g))

    print("Club World Cup (competition 1), %d rows replace the shipped one:" % len(new))
    for g in new:
        dw = int.from_bytes(g[R_ROUNDS_DW:R_ROUNDS_DW + 4], "little")
        print("   reg %5d  kind %d  clubs %2d  group %3d  back %d  groups %d  rounds %d  single %d"
              % (rid(g), g[M.R_TYPE], g[M.R_TEAMS] & 0x3f, g[R_GROUP],
                 int.from_bytes(g[R_BACK:R_BACK + 2], "little"), dw & 0x1f, (dw >> 12) & 7,
                 (dw >> 29) & 1))
    if "--dry" in a:
        print("dry run: nothing written")
        return 0

    # the shipped row's place in the table is where the group stage goes; the rest follows it
    out_regs = bytearray()
    for r in R:
        if r[M.R_CID] == CWC_CID:
            for g in new:
                out_regs += g
        else:
            out_regs += r
    M.write_tables(out, comp, out_regs, ents)
    print("written to %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
