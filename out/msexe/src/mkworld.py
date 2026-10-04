"""python mkworld.py --base <pesdb dir> --out <livecpk root> [--leagues N] [--clubs M]
                    [--cid-from N] [--reg-from N] [--sizes A,B,C] [--regions A,B,C]
                    [--tiers 1,2,3] [--group-regions N]
                    [--reg-ids A,B,C]

Build a whole set of new leagues, and the placeholder clubs to fill them, in one pass.

mkteams.py adds clubs and mkleague.py adds one competition, and running them by hand once
per league is how a set of thirty ends up with a duplicated id in the middle of it.  This
does the arithmetic instead: it reads the shipped tables once, hands out club ids from
above the highest in use, competition ids and regulation ids from the free lists it works
out from those same tables, and writes Team.bin next to the three competition tables so a
single livecpk root carries the lot -- and Coach.bin, with a placeholder manager for every new
club (see mkcoaches.py), when the base folder has the shipped one.

Everything it writes is a placeholder -- "FL League 03", "FL 0042" -- because that is the
whole point of the exercise: proving the shape of the data holds at scale, without
inventing a single real club.

The free ids are not guesses.  A competition id is one byte in all three tables, so the
ceiling is 255, and the ids Football Life already uses run to 141; free ids are simply the
ones no shipped row claims.  Regulation ids are two bytes and the same rule applies.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pesdb
import mkleague as M
import mkcoaches

T_REC = 1532
T_ID, T_ALT = 0x08, 0x00
T_NAME, T_NAME_LEN = 0x170, 0x46
T_ABBR, T_ABBR_LEN = 0x372, 3

CID_MAX, REG_MAX = 255, 600

# Regulation ids that are free in the tables but not free in the game: a league built on one
# of these shows Libertadores and Asian clubs in its table, so the exe knows them.  14, 32 and
# 33 were found that way one at a time; the other sixteen were measured together, by building
# two worlds of twenty-three leagues that differ in nothing but the ids they were given and
# taking both through a whole season creation.  Every good id produced a correct league and
# not one of these did.  See docs/findings.md, "It is the regulation id, and the league count
# has nothing to do with it".
BAD_REG = {14, 32, 33,
           12, 13, 63, 64, 65, 66, 69, 70, 71, 72, 73, 75, 77, 78, 101, 102,
           # found on 2026-09-17 by the same method, in a world of thirty-nine
           152, 153, 154,
           # 177 is a different failure: it is dropped from the live regulation
           # array at Master League setup, so its clubs never arrive at all
           177}

# Regulation ids that work but belong to someone else.  145 has no row in the regulation
# file, yet the shipped J1 League relegates into it (the exe's competition table still has a
# row for 145, the old J2), so a league of ours on 145 is where J1's relegated clubs would be
# sent.  In our runs J1 never actually moved a club there, but the link is real, so the id
# is not used.  Such an id is swapped for its replacement in place, so every other league
# keeps the id it always had -- the modules, the fixture-date table and existing worlds all
# key on those ids.  190 sits above the European phases 186-189, and it is in the
# fixture-date table with 145's shift (2026-09-25).  Worlds built before then keep 145 and
# still run; they just keep the link from J1 too.
MOVED_REG = {145: 190}


def free_ids(used, hi, want, prefer_from=0):
    """ids no shipped row claims, taken from prefer_from upward"""
    out = [i for i in range(prefer_from, hi + 1) if i not in used]
    if len(out) < want:
        raise SystemExit("only %d free ids from %d, %d wanted" % (len(out), prefer_from, want))
    return out[:want]


def main():
    a = sys.argv[1:]
    get = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    base, out = get("--base"), get("--out")
    if not base or not out:
        print(__doc__)
        return 1
    nleague = int(get("--leagues", "6"))
    nclub = int(get("--clubs", "20"))
    # Real leagues are not all one size: England's second tier has 24 clubs, Spain's has 22,
    # the Eredivisie 18.  --sizes takes a list and cycles it over the run, so one world can
    # carry several shapes at once.  That also separates two things every earlier run had
    # welded together -- how big a league is, and how many leagues there are -- because a
    # short run of big leagues can now be built without a long list to hide behind.
    sizes = [int(x) for x in get("--sizes", "").split(",") if x.strip()] or [nclub]
    # Which division each league is. Every league this project built before 2026-09-21 was a
    # copy of ENGLAND_D1_LEAGUE and therefore a FIRST division, all thirty-nine of them, which
    # is not a cosmetic detail: the engine hands European places to the tier-1 leagues of a
    # region, and its promotion resolver only looks for the league above when the lower one is
    # tier 2 or more. --tiers 1,2,3 cycles over the run, so leagues 1,4,7... are top flights
    # and the ones between them are the tiers below. Left empty, nothing is written and the
    # prototype's own division (D1) stands, which is what every earlier world has.
    tiers = [int(x) for x in get("--tiers", "").split(",") if x.strip()]
    # Spreading the leagues over regions was tried as a fix for the leagues that come up
    # holding another league's clubs, and it is not one: thirty-nine leagues dealt over
    # twenty-two regions fail exactly as thirty-nine leagues all filed under England do.
    # --regions is kept anyway, because forty-four competitions in one region is still more
    # than any shipped region holds and the menus group countries by it.  See
    # docs/findings.md, "The region is not it either".
    regions = ([int(r) for r in get("--regions").split(",")] if "--regions" in a
               else [int(get("--region", "16"))])
    # How many consecutive leagues share a region. One (the default) deals the regions out
    # league by league, which is what every earlier world did. Three, together with
    # --tiers 1,2,3, builds PYRAMIDS: leagues 1-3 are the three divisions of the first
    # region, 4-6 of the second, and so on. That pairing is the one the engine understands --
    # it promotes between a tier-2 and the tier-1 above it, and between a tier-3 and the
    # tier-2 above that -- and it also keeps our leagues from being extra FIRST divisions of
    # a shipped country, which is how they come to be offered European places.
    group = max(1, int(get("--group-regions", "1")))
    # Football Life's own added leagues live at 111-141, and the free ids inside that range
    # are the ones a new league has been carried into a playable season on.
    cid_from = int(get("--cid-from", "130"))
    # Regulation ids are handed out from the bottom of the free list by default, which means
    # a new league lands on an id the shipped file happens not to use -- but the exe does.
    # A league built on 70 or 75 comes back as European Qualifiers or a Champions League
    # play-off bracket instead of a league table, clubs and all.  --reg-from moves the whole
    # run above everything the shipped data claims, where no exe table has an opinion.
    reg_from = int(get("--reg-from", "1"))
    # Club count and club id moved together in every test so far -- new clubs always took
    # ids just above the highest shipped one -- so nothing has yet said which of the two the
    # 1303-club season ceiling is really counting.  --id-from separates them: the same number
    # of clubs, carrying ids from somewhere else entirely.
    id_from = int(get("--id-from", "0"))
    # Extra clubs go into the last league only, so a pair of worlds built with and without
    # them differ in exactly one league and one club.  Comparing 40x14 against 33x17 to ask
    # what one more club does confounds the club count with a different league list and a
    # different club under the cursor; this does not.
    extra = int(get("--extra", "0"))
    # Orphans belong to no competition at all.  They raise the club count and change nothing
    # else -- no league gains a member, no competition list grows, the league the walk
    # selects is untouched -- which is the only way to ask what the club count on its own
    # does.  Every earlier attempt moved the count by changing a league, so the two were
    # never separable.
    orphans = int(get("--orphans", "0"))
    lname = get("--league-name", "FL League %02d")
    cname = get("--club-name", "FL %04d")

    comp, regs, ents = (M.load(base, n) for n in
                        ("Competition.bin", "CompetitionRegulation.bin",
                         "CompetitionEntry.bin"))
    raw = bytearray(pesdb.wesys_unpack(open(os.path.join(base, "Team.bin"), "rb").read()))
    if len(raw) % T_REC:
        raise SystemExit("Team.bin is %d bytes, not a whole number of records" % len(raw))
    nteam = len(raw) // T_REC
    print("base: %d clubs, %d competitions, %d regulations, %d entries"
          % (nteam, len(comp) // M.COMP, len(regs) // M.REG, len(ents) // M.ENT))

    ids = [int.from_bytes(raw[i * T_REC + T_ID:i * T_REC + T_ID + 4], "little")
           for i in range(nteam)]
    alts = [int.from_bytes(raw[i * T_REC + T_ALT:i * T_REC + T_ALT + 4], "little")
            for i in range(nteam)]
    top_id, top_alt = max(ids), max(alts)
    if id_from:
        if id_from <= top_id:
            raise SystemExit("--id-from %d is not above the highest shipped id %d"
                             % (id_from, top_id))
        top_id = top_alt = id_from - 1

    used_cid = {comp[i * M.COMP + M.CID_OFF] for i in range(len(comp) // M.COMP)}
    used_reg = {int.from_bytes(regs[i * M.REG + M.R_ID:i * M.REG + M.R_ID + 2], "little")
                for i in range(len(regs) // M.REG)}
    cids = free_ids(used_cid, CID_MAX, nleague, cid_from)
    # Which regulation ids a world uses is the one variable that has ever changed whether a
    # league comes up holding its own clubs, so it has to be nameable rather than derived.
    # --reg-ids takes the list verbatim, in league order, and checks it against the file
    # instead of the free list, because the point of naming it is usually to try ids the
    # default allocator would have refused.
    if "--reg-ids" in a:
        rids = [int(r) for r in get("--reg-ids").split(",")]
        if len(rids) != nleague:
            raise SystemExit("--reg-ids has %d ids, %d leagues" % (len(rids), nleague))
        clash = sorted(set(rids) & used_reg)
        if clash:
            raise SystemExit("--reg-ids %s are already claimed by shipped regulations"
                             % ", ".join(str(c) for c in clash))
    else:
        rids = free_ids(used_reg | BAD_REG, REG_MAX, nleague, reg_from)
        for i, r in enumerate(rids):
            to = MOVED_REG.get(r)
            if to is not None:
                if to in used_reg or to in rids:
                    raise SystemExit("regulation %d should move to %d, but %d is taken"
                                     % (r, to, to))
                rids[i] = to
    print("competition ids %s" % (", ".join(str(c) for c in cids[:8])
                                  + (" ..." if nleague > 8 else "")))
    print("regulation  ids %s" % (", ".join(str(r) for r in rids[:8])
                                  + (" ..." if nleague > 8 else "")))

    proto = raw[(nteam - 1) * T_REC:nteam * T_REC]
    made = 0
    for L in range(nleague):
        teams = []
        n_here = sizes[L % len(sizes)] + (extra if L == nleague - 1 else 0)
        for k in range(n_here):
            r = bytearray(proto)
            cid_team = top_id + 1 + made
            r[T_ID:T_ID + 4] = cid_team.to_bytes(4, "little")
            r[T_ALT:T_ALT + 4] = (top_alt + 1 + made).to_bytes(4, "little")
            nm = (cname % (made + 1)).encode("utf-8")[:T_NAME_LEN - 1]
            ab = ("%03d" % ((made + 1) % 1000)).encode("utf-8")[:T_ABBR_LEN]
            r[T_NAME:T_NAME + T_NAME_LEN] = nm + b"\x00" * (T_NAME_LEN - len(nm))
            r[T_ABBR:T_ABBR + T_ABBR_LEN] = ab + b"\x00" * (T_ABBR_LEN - len(ab))
            raw += r
            teams.append(cid_team)
            made += 1
        M.add_league(comp, regs, ents, cids[L], rids[L], regions[(L // group) % len(regions)],
                     lname % (L + 1), "FL_LEAGUE_%02d" % (L + 1), teams, quiet=True,
                     tier=(tiers[L % len(tiers)] if tiers else None))
        print("  %-16s competition %-4d regulation %-4d %2d clubs %d-%d  region %3d  division %d"
              % (lname % (L + 1), cids[L], rids[L], len(teams), teams[0], teams[-1],
                 regions[(L // group) % len(regions)], tiers[L % len(tiers)] if tiers else 1))

    for k in range(orphans):
        r = bytearray(proto)
        r[T_ID:T_ID + 4] = (top_id + 1 + made).to_bytes(4, "little")
        r[T_ALT:T_ALT + 4] = (top_alt + 1 + made).to_bytes(4, "little")
        nm = (cname % (made + 1)).encode("utf-8")[:T_NAME_LEN - 1]
        ab = ("%03d" % ((made + 1) % 1000)).encode("utf-8")[:T_ABBR_LEN]
        r[T_NAME:T_NAME + T_NAME_LEN] = nm + bytes(T_NAME_LEN - len(nm))
        r[T_ABBR:T_ABBR + T_ABBR_LEN] = ab + bytes(T_ABBR_LEN - len(ab))
        raw += r
        made += 1
    if orphans:
        print("  %d orphan clubs, in no competition" % orphans)

    d = os.path.join(out, "common", "etc", "pesdb")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "Team.bin"), "wb").write(pesdb.wesys_pack(bytes(raw)))
    print("  wrote Team.bin (%d records)" % (len(raw) // T_REC))
    # Each new club names a manager id at +0x00 that no Coach record has, and the game fills
    # every such gap with a copy of the first coach -- one "Jorge Jesus" at every added club.
    # So the world also carries Coach.bin: the shipped one plus a placeholder manager per club.
    cpath = os.path.join(base, "Coach.bin")
    if os.path.exists(cpath):
        craw = open(cpath, "rb").read()
        coaches = pesdb.wesys_unpack(craw)
        add, st = mkcoaches.add_coaches(coaches, bytes(raw), top_id + 1)
        open(os.path.join(d, "Coach.bin"), "wb").write(pesdb.wesys_pack(coaches + add, craw[:3]))
        print("  wrote Coach.bin (%d records, %d new managers)"
              % ((len(coaches) + len(add)) // mkcoaches.C_REC, st["added"]))
    else:
        print("  no Coach.bin in --base: every new club will show the same made-up manager"
              " (run mkcoaches.py later)")
    M.write_tables(out, comp, regs, ents)
    print("\n%d leagues, %d clubs added; %d clubs in all"
          % (nleague, made, len(raw) // T_REC))
    return 0


if __name__ == "__main__":
    sys.exit(main())
