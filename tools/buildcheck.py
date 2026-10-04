"""python buildcheck.py <world pesdb dir> --base <base pesdb dir>

Offline checks of a world the league builder wrote -- its Competition*/Team tables -- before
the game ever starts. One line per check, PASS or FAIL with details (INFO for what the base
already has); exits 1 on any FAIL.

  1. names of the regulations the world introduces or changes: FAIL when it leaves a name slot
     empty that the base fills (or a new one empty) or sets a gap byte the base keeps zero; an
     emptiness the base already has is reported as INFO, not a failure (mkleague.name_at);
  2. no two regulations share an id;
  3. every team id in CompetitionEntry.bin exists in Team.bin, but FAIL only on the ids the
     world introduces; an id the base misses too is INFO;
  4. a club whose league differs from the base has a clear "Other ..." nibble (Team.bin +0x4f
     high half == 0, T_POOL in leaguebuilder.py);
  5. record counts, base vs world, for every table both have (information only).

Checks 1 and 3 are base-relative: they fail only on what the world introduces over the base,
never on a condition the shipped base already has (so a normal world passes offline).
"""
import os, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mkleague as M
import leaguebuilder as LB

T_REC, T_ID = 1532, 0x08            # Team.bin record (mkworld.T_REC, T_ID)
SPLIT_TOTAL = 9
GAP = 32                            # zero bytes between the two runs of ten name slots (mkleague)
SIZES = {"Competition.bin": M.COMP, "CompetitionRegulation.bin": M.REG,
         "CompetitionEntry.bin": M.ENT, "Team.bin": T_REC,
         "Player.bin": 312, "PlayerAssignment.bin": 16}


def rows(b, rec):
    return [b[i:i + rec] for i in range(0, len(b) - len(b) % rec, rec)]


def reg_id(g):
    return int.from_bytes(g[M.R_ID:M.R_ID + 2], "little")


def team_id(r):
    return int.from_bytes(r[T_ID:T_ID + 4], "little")


def named(g, k):
    off = M.name_at(k)
    return any(g[off:off + M.NAME_SLOT])


def tid_of(b):
    return int.from_bytes(b, "little")


def league_of(regs, ents):
    """{team id: regulation id} of the clubs in a league: the type-4 (and split-total)
    regulations of <regs>, joined to <ents> by competition id"""
    cid_league = {g[M.R_CID]: reg_id(g) for g in rows(regs, M.REG) if g[M.R_TYPE] in (4, SPLIT_TOTAL)}
    out = {}
    for e in rows(ents, M.ENT):
        rid = cid_league.get(e[M.E_CID])
        if rid is not None:
            out.setdefault(tid_of(e[M.E_TEAM:M.E_TEAM + 4]), rid)
    return out


def entry_ids(ents):
    return {tid_of(e[M.E_TEAM:M.E_TEAM + 4]) for e in rows(ents, M.ENT)}


def main():
    a = sys.argv[1:]
    if not a or a[0].startswith("-"):
        print(__doc__)
        return 2
    world = a[0]
    base = a[a.index("--base") + 1] if "--base" in a else os.environ.get("FL26_PESDB")
    for n in ("CompetitionRegulation.bin", "CompetitionEntry.bin", "Team.bin"):
        if not os.path.exists(os.path.join(world, n)):
            print("no %s in %s -- is that a world's common/etc/pesdb?" % (n, world))
            return 2

    regs = M.load(world, "CompetitionRegulation.bin")
    ents = M.load(world, "CompetitionEntry.bin")
    team = M.load(world, "Team.bin")
    world_rows = rows(regs, M.REG)
    fails = 0

    base_regs = base_ents = base_team = None
    if base and os.path.exists(os.path.join(base, "CompetitionRegulation.bin")):
        base_regs = M.load(base, "CompetitionRegulation.bin")
        base_ents = M.load(base, "CompetitionEntry.bin") if os.path.exists(
            os.path.join(base, "CompetitionEntry.bin")) else bytearray()
        base_team = M.load(base, "Team.bin") if os.path.exists(
            os.path.join(base, "Team.bin")) else bytearray()
    else:
        print("note: no base tables (%s) -- every regulation counts as new" % (base or "no --base"))

    # ---- check 1: names of the regulations the world introduces or changes (base-relative) ----
    base_by_id = {reg_id(g): g for g in rows(base_regs, M.REG)} if base_regs is not None else {}
    # a slot the game itself ships empty on some regulation (slot 3 of the European ones): a new
    # regulation copied from such a prototype keeps it empty, and the game lives with that
    shipped_empty = {k for g in base_by_id.values() for k in range(M.NAME_SLOTS) if not named(g, k)}
    changed = 0
    fail_lines, info_lines = [], []
    for g in world_rows:
        i = reg_id(g)
        br = base_by_id.get(i)
        if br is not None and bytes(g) == bytes(br):
            continue                        # identical to the base: nothing the world introduces
        changed += 1
        new = br is None
        fail_empty = [k for k in range(M.NAME_SLOTS)
                      if not named(g, k) and (named(br, k) if not new else k not in shipped_empty)]
        info_empty = [k for k in range(M.NAME_SLOTS)
                      if not named(g, k) and (not named(br, k) if not new else k in shipped_empty)]
        if fail_empty:
            fail_lines.append("reg %d: empty name slot(s) %s" % (i, fail_empty))
        if info_empty:
            info_lines.append("reg %d: empty name slot(s) %s (the base ships %s empty too)"
                              % (i, info_empty, "it" if not new else "such a slot"))
        wgap = any(g[M.NAME_RUN2 - GAP:M.NAME_RUN2])
        bgap = (not new) and any(br[M.NAME_RUN2 - GAP:M.NAME_RUN2])
        if wgap and not bgap:
            fail_lines.append("reg %d: the %d bytes before NAME_RUN2 are not zero" % (i, GAP))
        elif wgap and bgap:
            info_lines.append("reg %d: the %d bytes before NAME_RUN2 are not zero (also so in the base)"
                              % (i, GAP))
    if fail_lines:
        fails += 1
        print("FAIL check 1 (names of regulations the world introduces or changes): %d problem(s)"
              % len(fail_lines))
        for b in fail_lines[:40]:
            print("     " + b)
    else:
        print("PASS check 1: %d regulation(s) new or changed, every name slot the base fills is"
              " still filled, gap zero" % changed)
    for b in info_lines[:40]:
        print("INFO check 1: " + b)

    # ---- check 2: no shared regulation id ----
    cnt = Counter(reg_id(g) for g in world_rows)
    dups = sorted(i for i, n in cnt.items() if n > 1)
    if dups:
        fails += 1
        print("FAIL check 2 (regulation ids): shared id(s) %s" % dups[:40])
    else:
        print("PASS check 2: %d regulations, every id once" % len(world_rows))

    # ---- check 3: entry team ids exist in Team.bin (base-relative) ----
    world_ids = {team_id(r) for r in rows(team, T_REC)}
    world_missing = entry_ids(ents) - world_ids
    base_missing = (entry_ids(base_ents) - {team_id(r) for r in rows(base_team, T_REC)}) \
        if base_team is not None else set()
    introduced = sorted(world_missing - base_missing)      # missing in the world, not in the base
    in_both = sorted(world_missing & base_missing)         # missing in both: already the base's
    if introduced:
        fails += 1
        print("FAIL check 3 (CompetitionEntry -> Team.bin): %d team id(s) the world introduces: %s"
              % (len(introduced), introduced[:40]))
    else:
        print("PASS check 3: every CompetitionEntry team id the base has is in Team.bin (%d clubs)"
              % len(world_ids))
    if in_both:
        print("INFO check 3: %d team id(s) absent in both the world and the base: %s"
              % (len(in_both), in_both[:40]))

    # ---- check 4: the "Other" nibble of a club that changed league ----
    pool = LB.T_POOL
    rec_of = {team_id(r): r for r in rows(team, T_REC)}
    wl = league_of(regs, ents)
    bl = league_of(base_regs, base_ents) if base_regs is not None else {}
    bad = []
    for t in sorted(set(wl) | set(bl)):
        if wl.get(t) == bl.get(t):
            continue
        r = rec_of.get(t)
        if r is None:
            bad.append("club %d plays in a league but has no Team.bin record" % t)
        elif r[pool] & 0xf0:
            bad.append("club %d: T_POOL byte 0x%02x, high nibble should be 0 (league %s -> %s)"
                       % (t, r[pool], bl.get(t), wl.get(t)))
    if bad:
        fails += 1
        print("FAIL check 4 (T_POOL of clubs that changed league): %d club(s)" % len(bad))
        for b in bad[:40]:
            print("     " + b)
    else:
        moved = sum(1 for t in set(wl) | set(bl) if wl.get(t) != bl.get(t))
        print("PASS check 4: %d club(s) changed league, all with a clear T_POOL nibble" % moved)

    # ---- check 5: record counts (information) ----
    print("INFO check 5 (record counts, base vs world):")
    have = [n for n in SIZES
            if os.path.exists(os.path.join(world, n)) and base and os.path.exists(os.path.join(base, n))]
    if not have:
        print("     no table is in both the world and the base")
    for n in sorted(have):
        w = len(M.load(world, n)) // SIZES[n]
        b = len(M.load(base, n)) // SIZES[n]
        print("     %-26s world %6d rec  base %6d rec  (%+d)" % (n, w, b, w - b))
    for n in sorted(SIZES):
        if os.path.exists(os.path.join(world, n)) and n not in have:
            print("     %-26s world %6d rec  base -- (only the world has it)"
                  % (n, len(M.load(world, n)) // SIZES[n]))

    print("buildcheck: %s" % ("all checks passed" if not fails else "%d check(s) FAILED" % fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
