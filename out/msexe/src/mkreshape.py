r"""python mkreshape.py --base <pesdb dir> --out <livecpk root>
                      [--reshape CODE:N:kind:clubs:groups:role ...] [--drop CODE ...] [--dry]

Change the shape of a phase of a competition that already exists, in place -- no clone, no new
ids -- and optionally take a whole competition out of the world.

mkphases.py builds a NEW competition from a shipped one. This is the other half of the same
job: the shipped Champions League and Europa League keep their competition ids, their
regulation ids and their entries, and only the phase named changes shape. That is what the
game needs when a competition is modified rather than added: every place in the exe that asks
for regulation 3 or 5 by number still finds it.

    python mkreshape.py --base ...\_FL26G39OwnR\common\etc\pesdb --out ...\livecpk\_FL26G39UCL36 ^
                        --reshape UEFA_CHAMPIONS_LEAGUE:2:groups:36:1:- ^
                        --reshape UEFA_EUROPE_LEAGUE:1:groups:36:1:- ^
                        --drop FL_UCL

reads as "the Champions League's second phase (the group stage) becomes ONE group of 36, the
Europa League's first phase likewise, and the FL_UCL test competition goes". The phase fields
are mkphases.py's (N:kind:clubs:groups:role, a dash keeps the source's value). A replica IS a
group, so replicas past the new group count are dropped and the kept ones get the new club
count. One group rather than none: the draw only ever puts clubs into a group, so a phase with
no groups stays empty (2026-09-23). fl26swiss.dll then schedules that single group of 36.

--drop removes the competition row, every regulation row that belongs to it and every entry
for it. Nothing else refers to a competition by row position, so nothing is renumbered.

Only the three competition tables are written to --out; the caller copies the rest of the
world first.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mkleague as M
import mkphases as P


def rows_of(tab, size):
    return [bytearray(tab[i * size:(i + 1) * size]) for i in range(len(tab) // size)]


def main():
    a = sys.argv[1:]
    get = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    base, out = get("--base"), get("--out")
    if not base or not out:
        print(__doc__)
        return 1
    reshapes = [v for k, v in zip(a, a[1:]) if k == "--reshape"]
    drops = [v for k, v in zip(a, a[1:]) if k == "--drop"]
    if not reshapes and not drops:
        raise SystemExit("nothing to do: give --reshape and/or --drop")

    comp, regs, ents = (M.load(base, n) for n in
                        ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin"))
    print("base: %d competitions, %d regulations, %d entries"
          % (len(comp) // M.COMP, len(regs) // M.REG, len(ents) // M.ENT))

    # Every change is worked out on the original tables first, then applied in one pass.
    reg_rows = rows_of(regs, M.REG)
    drop_reg_rows = set()
    for spec in reshapes:
        code, rest = spec.split(":", 1)
        _i, cid = P.find_cid(comp, code)
        over = P.overrides(["--phase", rest])
        plan = P.phases(regs, cid)
        (n, o), = over.items()
        if not 1 <= n <= len(plan):
            raise SystemExit("%s has %d phases, so phase %d does not exist" % (code, len(plan), n))
        mi, reps = plan[n - 1]
        g = reg_rows[mi]
        before = "kind %d, %d clubs, %d group(s), role %d" % (
            g[P.R_KIND], g[P.R_TEAMS] & 0x3f, g[P.R_GROUPS] & 0x1f, g[P.R_ROLE] >> 4)
        said = P.apply_phase(g, o)
        print("%s phase %d (regulation %d): %s -> %s" % (code, n, P.rid_of(g), before, said))
        # A replica IS a group: replica id = master + (group + 1) * 1024. Fewer groups drop the
        # replicas past the last one; the ones kept carry the phase's club count too, because
        # the draw fills a group up to the replica's own count.
        mid = P.rid_of(g)
        if o[2] is not None and reps:
            gone = [r for r in reps if (P.rid_of(reg_rows[r]) - mid) // 1024 - 1 >= o[2]]
            drop_reg_rows.update(gone)
            if gone:
                print("   %d replica row(s) go with the groups: %s"
                      % (len(gone), ", ".join(str(P.rid_of(reg_rows[r])) for r in gone)))
            for r in reps:
                if r in gone:
                    continue
                if o[1] is not None:
                    reg_rows[r][P.R_TEAMS] = (reg_rows[r][P.R_TEAMS] & ~0x3f) | o[1]
                print("   replica %d kept: %d clubs" % (P.rid_of(reg_rows[r]), reg_rows[r][P.R_TEAMS] & 0x3f))

    drop_cids = set()
    for code in drops:
        i, cid = P.find_cid(comp, code)
        drop_cids.add(cid)
        mine = [r for r in range(len(reg_rows)) if reg_rows[r][M.R_CID] == cid]
        drop_reg_rows.update(mine)
        n_ent = sum(1 for e in range(len(ents) // M.ENT) if ents[e * M.ENT + M.E_CID] == cid)
        print("drop %s: competition %d, regulation(s) %s, %d entries"
              % (code, cid, ", ".join(str(P.rid_of(reg_rows[r])) for r in mine), n_ent))

    new_comp = bytearray(b"".join(r for r in rows_of(comp, M.COMP) if r[M.CID_OFF] not in drop_cids))
    new_regs = bytearray(b"".join(r for k, r in enumerate(reg_rows) if k not in drop_reg_rows))
    new_ents = bytearray(b"".join(r for r in rows_of(ents, M.ENT) if r[M.E_CID] not in drop_cids))
    print("out: %d competitions, %d regulations, %d entries"
          % (len(new_comp) // M.COMP, len(new_regs) // M.REG, len(new_ents) // M.ENT))

    if "--dry" in a:
        print("dry run: nothing written")
        return 0
    M.write_tables(out, new_comp, new_regs, new_ents)
    return 0


if __name__ == "__main__":
    sys.exit(main())
