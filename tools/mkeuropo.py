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

build(pesdb, out) does the same inside a world that is being built (the league builder), with
no copy; build(..., uecl=False) gives the Europa League its play-off alone, for a world built
without the Conference League (its league phase of 36 is still reshaped, see leaguebuilder
europe()).

The same copy of reg 2 makes the qualifying rounds in front of the August play-offs (0.1.7): the
league builder asks qualifying(pesdb, out, rounds, ids) for the third and second qualifying rounds
it picked (fl26world.pick_rounds), under free ids of its own, and writes them to the world file as
`qround <competition> <round> <regulation>` lines -- fl26swiss.dll fills, dates and plays them in
August like 188 and 189.

And a league cup's pre-round (0.1.7): prerounds(pesdb, out, rounds) copies reg 2 under the cup's
competition id, one tie row per pair of clubs past the cup's 16, 8 or 4 (the master holds
2 x ties clubs; the other tie rows stay empty); the world file's `lpre` line names it.
"""
import contextlib, io, os, shutil, sys

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


def playoffs(regs, where="the world", uecl=True):
    """the play-off rows to append to CompetitionRegulation.bin <regs>, and one line per
    competition saying what they are; uecl=False: the Europa League's only. SystemExit when the
    world is not ready for them."""
    rows = [bytearray(regs[i * M.REG:(i + 1) * M.REG]) for i in range(len(regs) // M.REG)]
    used = {rid(r) for r in rows}
    tpl = _template(rows)

    targets = [(UEL_CID, PLAYOFFS[0])]
    if uecl:
        phase = [r for r in rows if rid(r) == UECL_REG]
        if not phase:
            raise SystemExit("no regulation %d (the Conference League's league phase) in %s -- run "
                             "mkuecl.py first" % (UECL_REG, where))
        targets.append((phase[0][M.R_CID], PLAYOFFS[1]))

    added, said = bytearray(), []
    for cid, new in targets:
        own = [r for r in rows if r[M.R_CID] == cid]
        if not own:
            raise SystemExit("no competition %d in %s" % (cid, where))
        if any(r[M.R_TYPE] == tpl[0][M.R_TYPE] and r[0x0d] >> 4 == tpl[0][0x0d] >> 4 for r in own):
            raise SystemExit("competition %d already has a play-off phase" % cid)
        name = own[0][M.R_NAME:M.NAME_END]
        ids = [new + g * STEP for g in range(TIES + 1)]
        if used & set(ids):
            raise SystemExit("ids %s are taken" % sorted(used & set(ids)))
        added += _copy(tpl, new, cid, name)
        said.append("competition %3d: play-off %d, ties %s" % (cid, new, ", ".join(map(str, ids[1:]))))
    return added, said


def _template(rows):
    tpl = [r for r in rows if rid(r) & 0x3ff == TEMPLATE and rid(r) <= TEMPLATE + TIES * STEP
           and r[M.R_CID] == 2]
    if len(tpl) != 1 + TIES:
        raise SystemExit("reg 2 should have one master and %d replicas, found %d rows" % (TIES, len(tpl)))
    return tpl


def _copy(tpl, new, cid, name):
    """reg 2 and its replicas as regulation new of competition cid, named name"""
    out = bytearray()
    for t in tpl:
        g = bytearray(t)
        grp = g[R_GROUP]
        g[M.R_ID:M.R_ID + 2] = (new if grp == 255 else new + (grp + 1) * STEP).to_bytes(2, "little")
        if grp != 255:
            g[R_BACK:R_BACK + 2] = new.to_bytes(2, "little")
        g[M.R_CID] = cid
        g[M.R_NAME:M.R_NAME + len(name)] = name
        out += g
    return out


def qualifying(base, out, rounds, ids, log=print):
    """add the qualifying rounds rounds -- (competition 0..2, stage 1 the third qualifying round
    or 2 the second) -- to the tables in <base>, each a copy of reg 2 and its eight replicas under
    the next of ids (free regulation ids), and write the competition tables to <out> as build()
    does. Returns the world file's (competition code 10..12, round 3 or 2, regulation) triples."""
    comp, regs, ents = (M.load(base, n) for n in
                        ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin"))
    rows = [bytearray(regs[i * M.REG:(i + 1) * M.REG]) for i in range(len(regs) // M.REG)]
    used = {rid(r) for r in rows}
    tpl = _template(rows)
    phase = [r for r in rows if rid(r) == UECL_REG]
    cids = {0: 2, 1: UEL_CID, 2: phase[0][M.R_CID] if phase else None}
    added, lines, ids = bytearray(), [], list(ids)
    for c, stage in sorted(rounds, key=lambda r: (r[0], -r[1])):
        if stage not in (1, 2):
            continue
        if cids[c] is None:
            raise SystemExit("no regulation %d (the Conference League's league phase): no Conference "
                             "League qualifying" % UECL_REG)
        own = [r for r in rows if r[M.R_CID] == cids[c]]
        if not own:
            raise SystemExit("no competition %d" % cids[c])
        if not ids:
            raise SystemExit("no free regulation id left for the qualifying rounds")
        new = ids.pop(0)
        taken = used & {new + g * STEP for g in range(TIES + 1)}
        if taken:
            raise SystemExit("ids %s are taken" % sorted(taken))
        added += _copy(tpl, new, cids[c], own[0][M.R_NAME:M.NAME_END])
        lines.append((10 + c, 3 if stage == 1 else 2, new))
    if added:
        with contextlib.redirect_stdout(io.StringIO()):
            M.write_tables(out, comp, regs + added, ents)
        log("  qualifying rounds: %s" % ", ".join("%d (%s %s)" % (r, ("Champions League", "Europa League",
            "Conference League")[q - 10], "third" if n == 3 else "second") for q, n, r in lines))
    return lines


def prerounds(base, out, rounds, log=print):
    """add the league cups' pre-rounds rounds -- (regulation, competition, cup name, ties 1..8) --
    to the tables in <base>, each a copy of reg 2 and its eight replicas under that id, the
    master holding 2 x ties clubs, and write the competition tables to <out> as qualifying()
    does. The competition need not be in Competition.bin yet: the league builder adds the
    pre-round first and its cup (mkccup.py) after it, as the cup's entries name the ties."""
    comp, regs, ents = (M.load(base, n) for n in
                        ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin"))
    rows = [bytearray(regs[i * M.REG:(i + 1) * M.REG]) for i in range(len(regs) // M.REG)]
    used = {rid(r) for r in rows}
    tpl = _template(rows)
    added = bytearray()
    for new, cid, name, ties in rounds:
        if not 1 <= ties <= TIES:
            raise SystemExit("%s: a pre-round of %d ties -- 1 to %d" % (name, ties, TIES))
        taken = used & {new + g * STEP for g in range(TIES + 1)}
        if taken:
            raise SystemExit("ids %s are taken" % sorted(taken))
        rows_new = _copy(tpl, new, cid, b"")
        for i in range(0, len(rows_new), M.REG):
            M.put_names(rows_new, i, name)
            if rows_new[i + R_GROUP] == 255:
                rows_new[i + M.R_TEAMS] = (rows_new[i + M.R_TEAMS] & ~0x3f) | 2 * ties
        added += rows_new
        used |= {new + g * STEP for g in range(TIES + 1)}
    with contextlib.redirect_stdout(io.StringIO()):
        M.write_tables(out, comp, regs + added, ents)
    log("  league cup pre-rounds: %s" % ", ".join("%d (%s, %d tie%s)" % (r, n, t, "" if t == 1 else "s")
                                                  for r, _c, n, t in rounds))


def build(base, out, log=print, uecl=True):
    """add both play-offs (uecl=False: the Europa League's alone) to the tables in <base> and
    write the three competition tables to the world <out> (in place when <base> is <out>'s own
    pesdb): the league builder's way in"""
    comp, regs, ents = (M.load(base, n) for n in
                        ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin"))
    added, said = playoffs(regs, base, uecl)
    with contextlib.redirect_stdout(io.StringIO()):
        M.write_tables(out, comp, regs + added, ents)
    if uecl:
        log("  Europa / Conference League play-offs: regulations %d and %d" % PLAYOFFS)
    else:
        log("  Europa League play-off: regulation %d" % PLAYOFFS[0])
    return said


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
    added, said = playoffs(regs, src)
    for line in said:
        print(line)

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
