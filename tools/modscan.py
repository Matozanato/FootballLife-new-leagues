r"""python modscan.py --mod <livecpk root | .cpk> [--base <pesdb dir>] [--quiet]

Say what importing somebody else's mod would take over.

This is the first brick of the importer (docs: the long-term goal is a tool that adds other
people's leagues to a world ADDITIVELY). Almost every league mod in circulation is written to
replace: it ships a `Competition.bin` with its own league sitting on a shipped competition id,
and installing it means the shipped competition is simply gone. Before anything can be
remapped, somebody has to be able to answer "what exactly does this mod claim, and what does
it collide with" -- for a folder of loose files or for a `.cpk`, without installing it.

What it reads. Any of the five tables that carry ids:

    Competition.bin            competition ids
    CompetitionRegulation.bin  regulation ids
    CompetitionEntry.bin       which competition each club is entered into
    Team.bin                   club ids
    Player.bin                 player ids
    PlayerAssignment.bin       which club each player is signed to
    Coach.bin                  manager ids (a club names its manager at Team +0x00)
    Tactics.bin                one row per club, naming the club at +0x04
    TacticsFormation.bin       one row per tactics row, sharing its key
    Derby.bin                  a pair of clubs and the derby's number
    SpecialPlayerAssignment.bin  a club's special players

It also says what the pack brings in words rather than numbers -- "a 20-club league", "a
32-club group stage in 8 groups" -- read from the kind and role fields of each new
competition's phases.

For each, every id in the mod is one of four things: NEW (no shipped row has it, so importing
it adds), CHANGED (a shipped row has that id and the mod's bytes differ, so the shipped row
would be replaced), UNTOUCHED (the id is there but byte-identical -- which is what a mod that
ships a whole table looks like), or DROPPED (shipped rows the mod leaves out entirely, which is
how a table rebuilt wholesale quietly deletes things).

Comparing the bytes and not just the ids is the point. Everything this project builds ships the
complete table with its own rows appended, so an id-only comparison would call our own additive
worlds hostile takeovers of all 91 shipped competitions.

The base to compare against is the game's own data, composed the way the download folder
composes it: for each table, the copy from the archive with the highest priority that carries
it (tools/spfilelist.py explains the ordering). It is extracted once into FL26_OUT/base-pesdb
and reused. Pass --base to compare against something else, such as a world this project built.

Reads only. Nothing is installed, extracted into the game, or written outside FL26_OUT.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import flpaths
import pesdb
import spfilelist

# table -> (record size, offset of the id, id width)
TABLES = {
    "Competition.bin":           (36, 5, 1),
    "CompetitionRegulation.bin": (2352, 2, 2),
    "Team.bin":                  (1532, 8, 4),
    "Player.bin":                (312, 8, 4),
    "PlayerAssignment.bin":      (16, 0, 4),
    "Coach.bin":                 (100, 0, 4),
    "Tactics.bin":               (24, 4, 4),     # keyed by the club it belongs to, one row each
    "TacticsFormation.bin":      (792, 0, 4),   # keyed by the Tactics row's own key at +0x00
    "SpecialPlayerAssignment.bin": (16, 0, 4),  # the player at +0x00
    # A derby has no id column of its own: the low nine bits of +0x08 number it and the bits
    # above are flags, and taken whole the field is unique across all 254 shipped rows.
    "Derby.bin":                 (12, 8, 4),
}
ENTRY = ("CompetitionEntry.bin", 12, 8, 1)      # name, record, competition id offset, width

# What a phase is, in the game's own words. The kind comes from CompetitionKind.bin and the
# role from the high nibble of regulation +0x0d; both are measured (docs/findings.md and
# docs/regulation-record-decode.md).
KIND = {1: "play-off", 2: "group stage", 3: "knockout", 4: "league", 5: "two-season league",
        6: "qualifying 1", 7: "qualifying 2", 8: "practice", 9: "split total"}
ROLE = {0: "", 1: "domestic league", 2: "cup or qualifying", 4: "club group stage",
        5: "national group stage", 6: "club knockout", 7: "national knockout",
        8: "second round", 9: "apertura", 10: "clausura", 11: "split total",
        12: "regular season", 13: "top group", 14: "second group", 15: "lower group"}
REG_REC, R_ID, R_CID, R_KIND, R_GROUP, R_TEAMS, R_ROLE, R_GROUPS = 2352, 2, 8, 9, 0x0a, 0x0b, 0x0d, 0x10
NO_GROUP = 255
PESDB = os.path.join("common", "etc", "pesdb")


def ids(raw, rec, off, width):
    """id -> the whole record, so a shared id can be compared byte for byte."""
    out = {}
    for i in range(len(raw) // rec):
        r = raw[i * rec:(i + 1) * rec]
        out.setdefault(int.from_bytes(r[off:off + width], "little"), r)
    return out


def load_dir(d, name):
    p = os.path.join(d, name)
    if not os.path.isfile(p):
        p = os.path.join(d, PESDB, name)
    if not os.path.isfile(p):
        return None
    raw = open(p, "rb").read()
    try:
        return pesdb.wesys_unpack(raw)
    except AssertionError:
        # Not every table is packed. Derby.bin and SpecialPlayerAssignment.bin are plain
        # arrays of records with no WESYS header, and refusing to read them would be a bug
        # in the reader, not a property of the file.
        return raw


def base_dir():
    """The shipped tables, extracted once, composed in priority order."""
    out = os.path.join(flpaths.out_dir(), "base-pesdb")
    want = list(TABLES) + [ENTRY[0]]
    if all(os.path.isfile(os.path.join(out, n)) for n in want):
        return out
    folder = os.path.join(flpaths.GAME_DIR, "download")
    listing, _ = spfilelist.read(os.path.join(folder, "spFileList.bin"))
    os.makedirs(out, exist_ok=True)
    # highest priority last, so a later write wins
    for idx, _g, _t, name in sorted(listing, reverse=True):
        arc = os.path.join(folder, name)
        if not os.path.isfile(arc):
            continue
        # Every listed archive is tried, the multi-gigabyte ones included: reading an archive's
        # table of contents costs a seek, not a read. Measured 2026-09-21, only the four
        # data_s2526 patches carry pesdb tables at all -- the add-ons are faces and menus.
        os.system('%s "%s" "%s" "%s" %s > %s' % (
            sys.executable, os.path.join(HERE, "cpkx.py"), arc,
            os.path.join(out, "_x"), " ".join('"%s"' % n for n in want), os.devnull))
        src = os.path.join(out, "_x", PESDB)
        if not os.path.isdir(src):
            continue
        for n in os.listdir(src):
            if n in want:
                os.replace(os.path.join(src, n), os.path.join(out, n))
    return out


def codes(raw):
    """competition id -> its code, so a takeover can be named and not just numbered."""
    out = {}
    for i in range(len(raw) // 36):
        r = raw[i * 36:(i + 1) * 36]
        out[r[5]] = r[8:].split(bytes(1))[0].decode("latin1")
    return out


def lineups(raw):
    """competition id -> the set of clubs entered in it."""
    out = {}
    for i in range(len(raw) // 12):
        r = raw[i * 12:(i + 1) * 12]
        out.setdefault(r[8], set()).add(int.from_bytes(r[0:4], "little"))
    return out


def report(label, mod, base, quiet, rowcount=None, baserows=None):
    """One table: what is new, what is taken over, what disappears."""
    if mod is None:
        return
    if base is None:
        print("  %-28s %5d rows, and the game ships no such table" % (label, len(mod)))
        return
    m, b = set(mod), set(base)
    new = sorted(m - b)
    shared = sorted(m & b)
    over = [x for x in shared if mod[x] != base[x]]
    same = len(shared) - len(over)
    gone = sorted(b - m)
    print("  %-28s %5d ids: %d new, %d changed, %d identical, %d shipped rows dropped"
          % (label, len(mod), len(new), len(over), same, len(gone)))
    # A table can repeat a key: two tactics rows for one club, two formations under one
    # tactics key. The comparison above cannot see those, because a dictionary keeps one row
    # per id, so they are counted here instead -- a repeat of a SHIPPED key is the game being
    # asked which of two rows it meant.
    # Some of these tables repeat keys by design: the shipped Tactics.bin has 772 rows for
    # 730 clubs. So the number that matters is how many MORE repeats the mod has than the
    # game does, not the repeats themselves.
    if rowcount is not None and baserows is not None:
        extra = (rowcount - len(mod)) - (baserows - len(base))
        if extra > 0:
            print("      and %d row(s) repeat a key more often than the shipped table does"
                  % extra)
    if new and not quiet:
        print("      new:     %s%s" % (", ".join(str(x) for x in new[:20]),
                                       " ..." if len(new) > 20 else ""))
    if over and not quiet:
        print("      changed: %s%s" % (", ".join(str(x) for x in over[:20]),
                                       " ..." if len(over) > 20 else ""))
    if gone and not quiet:
        print("      dropped: %s%s" % (", ".join(str(x) for x in gone[:20]),
                                       " ..." if len(gone) > 20 else ""))
    return len(over), len(gone)


def shapes(mraw, braw, comp_raw, base_comp):
    """[(competition id, code, [phase description])] for the competitions the mod adds.

    Says what a pack actually brings in the language somebody asks the question in -- "a
    20-club league" rather than "regulation 186, type 4" -- using the kind and role fields.
    """
    if not mraw:
        return []
    have = set()
    if base_comp:
        have = {base_comp[i * 36 + 5] for i in range(len(base_comp) // 36)}
    code = codes(comp_raw) if comp_raw else {}
    out = {}
    for i in range(len(mraw) // REG_REC):
        r = mraw[i * REG_REC:(i + 1) * REG_REC]
        if r[R_GROUP] != NO_GROUP or r[R_CID] in have:
            continue
        groups = r[R_GROUPS] & 0x1f
        out.setdefault(r[R_CID], []).append(
            "%d-club %s%s%s" % (r[R_TEAMS] & 0x3f, KIND.get(r[R_KIND], "type %d" % r[R_KIND]),
                                " in %d groups" % groups if groups else "",
                                ", the %s" % ROLE[r[R_ROLE] >> 4] if ROLE.get(r[R_ROLE] >> 4) else ""))
    return [(c, code.get(c, str(c)), v) for c, v in sorted(out.items())]


def managers(mteam, bteam, mcoach, bcoach):
    """The mod's clubs (new, or changed from the shipped row) whose manager is missing from both
    Coach.bin files, and those whose manager also works at another club of the result."""
    if not mteam:
        return None
    TR, CR = 1532, 100
    u = lambda b, o: int.from_bytes(b[o:o + 4], "little")
    have = set()
    for raw in (bcoach, mcoach):
        if raw:
            have |= {u(raw, i) for i in range(0, len(raw) - CR + 1, CR)}
    base_rows = {u(bteam, o + 8): bteam[o:o + TR] for o in range(0, len(bteam or b""), TR)}
    theirs = [mteam[o:o + TR] for o in range(0, len(mteam), TR)
              if base_rows.get(u(mteam, o + 8)) != mteam[o:o + TR]]
    # the clubs of the result: the base, with the mod's rows in place of the same id
    result = dict((k, u(r, 0)) for k, r in base_rows.items())
    result.update((u(r, 8), u(r, 0)) for r in (mteam[o:o + TR] for o in range(0, len(mteam), TR)))
    by_mgr = {}
    for club, k in result.items():
        by_mgr.setdefault(k, []).append(club)
    missing = [u(r, 8) for r in theirs if u(r, 0) not in have] if have else []
    shared = [(u(r, 8), next(c for c in by_mgr[u(r, 0)] if c != u(r, 8)))
              for r in theirs if len(by_mgr.get(u(r, 0), ())) > 1]
    return (missing, shared) if missing or shared else None


def main():
    a = sys.argv[1:]
    get = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    mod = get("--mod")
    if not mod:
        print(__doc__)
        return 1
    quiet = "--quiet" in a

    if mod.lower().endswith(".cpk"):
        work = os.path.join(flpaths.out_dir(), "modscan", os.path.basename(mod))
        names = list(TABLES) + [ENTRY[0]]
        os.system('%s "%s" "%s" "%s" %s > %s' % (
            sys.executable, os.path.join(HERE, "cpkx.py"), mod, work,
            " ".join('"%s"' % n for n in names), os.devnull))
        mod = work
        print("unpacked the archive into %s" % work)

    base = get("--base") or base_dir()
    print("mod:  %s" % mod)
    print("base: %s" % base)
    print("")

    damage, seen = [], 0
    for name, (rec, off, width) in TABLES.items():
        mraw, braw = load_dir(mod, name), load_dir(base, name)
        seen += mraw is not None
        r = report(name, ids(mraw, rec, off, width) if mraw else None,
                   ids(braw, rec, off, width) if braw else None, quiet,
                   len(mraw) // rec if mraw else None,
                   len(braw) // rec if braw else None)
        if r:
            damage.append((name,) + r)
        if name == "Competition.bin" and mraw and braw and r and r[0]:
            mc, bc = codes(mraw), codes(braw)
            for cid in sorted(set(mc) & set(bc)):
                if mc[cid] != bc[cid]:
                    print("      competition %d was %s and becomes %s" % (cid, bc[cid], mc[cid]))

    entry_damage = []
    name, rec, off, width = ENTRY
    mraw, braw = load_dir(mod, name), load_dir(base, name)
    if mraw is not None:
        seen += 1
        mc = sorted(ids(mraw, rec, off, width))
        bc = sorted(ids(braw, rec, off, width)) if braw is not None else []
        print("  %-28s %5d rows, entering clubs into %d competitions (%d of them shipped)"
              % (name, len(mraw) // rec, len(mc), len(set(mc) & set(bc))))
        # A mod can leave every id alone and still take a shipped league over, simply by
        # entering different clubs into it. That is invisible to the id comparison above.
        if braw is not None:
            ml, bl = lineups(mraw), lineups(braw)
            moved = [c for c in sorted(set(ml) & set(bl)) if ml[c] != bl[c]]
            if moved:
                entry_damage.append(len(moved))
                print("      the line-up changes in %d shipped competition(s): %s"
                      % (len(moved), ", ".join(str(c) for c in moved[:20])))
                if not quiet:
                    for c in moved[:5]:
                        print("         competition %d: %d clubs in, %d out"
                              % (c, len(ml[c] - bl[c]), len(bl[c] - ml[c])))

    shape = shapes(load_dir(mod, "CompetitionRegulation.bin"),
                   load_dir(base, "CompetitionRegulation.bin"),
                   load_dir(mod, "Competition.bin"), load_dir(base, "Competition.bin"))
    if shape:
        print("")
        print("what it brings that the game does not have:")
        for cid, cd, phases in shape[:20]:
            print("  %-3d %-26s %s" % (cid, cd[:26], "; ".join(phases)))
        if len(shape) > 20:
            print("  ... and %d more" % (len(shape) - 20))

    mgr = managers(load_dir(mod, "Team.bin"), load_dir(base, "Team.bin"),
                   load_dir(mod, "Coach.bin"), load_dir(base, "Coach.bin"))
    if mgr:
        missing, shared = mgr
        print("")
        if missing:
            print("managers: %d of the mod's clubs name a manager neither Coach.bin has (the game"
                  % len(missing))
            print("  shows a copy of its first coach, Jorge Jesus, at each): %s"
                  % ", ".join(str(t) for t in missing[:12]) + (" ..." if len(missing) > 12 else ""))
        if shared:
            print("managers: %d of the mod's clubs share a manager with another club: %s"
                  % (len(shared), ", ".join("%d (with %d)" % p for p in shared[:8])
                     + (" ..." if len(shared) > 8 else "")))
        print("  give each of them a manager of its own (a Coach.bin record) before playing a season.")

    print("")
    if not seen:
        print("this mod carries none of the six tables, so there is nothing to collide with:")
        print("it changes pictures, sounds or menus and can be installed as it is. What it")
        print("replaces among THOSE files is a different question and this tool does not")
        print("answer it.")
        return 0
    if not any(d[1] or d[2] for d in damage) and not entry_damage:
        print("verdict: additive. Nothing this mod carries stands on a shipped id, so it can")
        print("be imported as it is.")
    else:
        print("verdict: NOT additive as it stands.")
        for n, over, gone in damage:
            if over or gone:
                print("   %s: %d shipped rows changed, %d dropped" % (n, over, gone))
        for n in entry_damage:
            print("   CompetitionEntry.bin: %d shipped competitions get a different line-up" % n)
        print("Importing it means remapping those ids first -- which is what the importer is")
        print("for. Run again with the remapped copy to check the remap did its job.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
