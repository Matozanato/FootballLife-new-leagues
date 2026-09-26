r"""python mkeuropo.py --src <livecpk world> --out <new livecpk world> [--dry]

Give the Europa League and the Conference League the knockout play-off the Champions League
has: since 2024 ranks 9-24 of the league phase play two-legged ties in February and only the
top eight go straight to the round of 16.

The Champions League has a regulation for it already (reg 2, the old August play-off, which
fl26swiss.dll uses a second time in February). The other two have nothing, so each gets a copy
of reg 2 and its eight replicas -- one replica per tie -- under a free id:

    Europa League       competition 3    play-off 188, ties 1212, 2236 ... 8380
    Conference League   (see below)      play-off 189, ties 1213, 2237 ... 8381

Those are the ids fl26swiss.dll expects (UEL_PO / UECL_PO); the script refuses to run if they
are taken. The Conference League is found through its league phase, regulation 186, the id
mkuecl.py gives it: its competition id is whatever mkphases.py found free (174 in a world with
39 added leagues, 130 in one without any), so it is read, not assumed. The rows are appended at the end of the table, as mkphases.py appends a clone, so no
existing row moves. Nothing drives them but the DLL: the stage progression and the calendar are
switches on the regulation id that stop well short of 188, so the game never starts, dates or
fills them on its own. Europa League is a shipped competition and gains rows -- modifying it is
allowed, and nothing it had is changed or removed.

    python mkeuropo.py --src E:\...\livecpk\_FL26G39UECL --out E:\...\livecpk\_FL26G39EPO
"""
import os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mkleague as M

PESDB = os.path.join("common", "etc", "pesdb")
R_BACK, R_GROUP = 0x06, 0x0a
STEP, TIES = 1024, 8
TEMPLATE = 2                              # the Champions League play-off
UEL_CID = 3                               # the Europa League, a shipped competition
UECL_REG = 186                            # the Conference League's league phase (mkuecl.py)
PLAYOFFS = (188, 189)                     # (Europa League, Conference League) play-off ids


def rid(row):
    return int.from_bytes(row[M.R_ID:M.R_ID + 2], "little")


def main():
    a = sys.argv[1:]
    get = lambda k: a[a.index(k) + 1] if k in a else None
    src, out = get("--src"), get("--out")
    if not src or not out:
        print(__doc__)
        return 1
    base = os.path.join(src, PESDB)
    comp, regs, ents = (M.load(base, n) for n in
                        ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin"))
    rows = [bytearray(regs[i * M.REG:(i + 1) * M.REG]) for i in range(len(regs) // M.REG)]
    used = {rid(r) for r in rows}
    tpl = [r for r in rows if rid(r) & 0x3ff == TEMPLATE and rid(r) <= TEMPLATE + TIES * STEP
           and r[M.R_CID] == 2]
    if len(tpl) != 1 + TIES:
        raise SystemExit("reg 2 should have one master and %d replicas, found %d rows" % (TIES, len(tpl)))

    uecl = [r for r in rows if rid(r) == UECL_REG]
    if not uecl:
        raise SystemExit("no regulation %d (the Conference League's league phase) in %s -- run "
                         "mkuecl.py first" % (UECL_REG, src))
    targets = ((UEL_CID, PLAYOFFS[0]), (uecl[0][M.R_CID], PLAYOFFS[1]))

    added = bytearray()
    for cid, new in targets:
        own = [r for r in rows if r[M.R_CID] == cid]
        if not own:
            raise SystemExit("no competition %d in %s" % (cid, src))
        if any(r[M.R_TYPE] == tpl[0][M.R_TYPE] and r[0x0d] >> 4 == tpl[0][0x0d] >> 4 for r in own):
            raise SystemExit("competition %d already has a play-off phase" % cid)
        name = own[0][M.R_NAME:M.R_NAME + M.NAME_SLOTS * M.NAME_SLOT]
        ids = [new + g * STEP for g in range(TIES + 1)]
        if used & set(ids):
            raise SystemExit("ids %s are taken" % sorted(used & set(ids)))
        for t in tpl:
            g = bytearray(t)
            grp = g[R_GROUP]
            g[M.R_ID:M.R_ID + 2] = (new if grp == 255 else new + (grp + 1) * STEP).to_bytes(2, "little")
            if grp != 255:
                g[R_BACK:R_BACK + 2] = new.to_bytes(2, "little")
            g[M.R_CID] = cid
            g[M.R_NAME:M.R_NAME + len(name)] = name
            added += g
        print("competition %3d: play-off %d, ties %s" % (cid, new, ", ".join(map(str, ids[1:]))))

    if "--dry" in a:
        print("dry run: nothing written")
        return 0
    if os.path.exists(out):
        raise SystemExit("%s exists -- pick a new name, worlds are not overwritten" % out)
    shutil.copytree(src, out, ignore=shutil.ignore_patterns("*.pre*", "*.retiered", "*.bak*"))
    M.write_tables(out, comp, regs + added, ents)
    print("%d regulation rows added, %d in all" % (len(added) // M.REG, (len(regs) + len(added)) // M.REG))
    return 0


if __name__ == "__main__":
    sys.exit(main())
