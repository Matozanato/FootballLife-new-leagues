r"""python mkphases.py --base <pesdb dir> --out <livecpk root> --like UEFA_CHAMPIONS_LEAGUE
                     [--teams a,b,...] [--cid N] [--name S] [--code S] [--region N]
                     [--phase N:kind:clubs:groups:role] [--dry]

Clone a competition that has more than one phase -- a play-off, then a group stage, then a
knockout -- which mkleague.py and mkcup.py cannot do, because they copy exactly one regulation
row and a continental competition is made of twenty.

How the shipped ones are built (read from _FL26G39Tri, 2026-09-21):

    UEFA Champions League, competition 2
      regulation     2  play-off,    16 clubs, plus 8 replicas 1026, 2050 ... 8194
      regulation     3  group stage, 32 clubs, plus 8 replicas 1027, 2051 ... 8195
      regulation     4  knockout,    16 clubs, no replicas
      33 entries

    UEFA Europa League, competition 3
      regulation     5  group stage, 48 clubs, plus 12 replicas 1029 ... 12293
      regulation     6  knockout,    32 clubs
      34 entries

A replica is one group of a phase. Its id is master + (group + 1) * 1024, its +0x0a is the
group number (a master carries 255 there), and its +0x06 points back at the master. So a clone
is not a copy of rows, it is a copy with three renumberings that have to agree, and that is the
whole reason for this tool: get one of them wrong and the competition exists, is listed, and
never draws a fixture.

Two earlier notes corrected by reading the data rather than the summary: the play-off phase has
replicas too, not only the group stage, and the Champions League ships 33 entries, not 32.

What this does not do is invent a calendar. Every cloned phase keeps the source's calendar
dword, so the clone's matchdays land on the same days as the competition it was copied from.
For a competition meant to run alongside its original that is wrong and needs its own dates --
fl26swiss does exactly that for the league phase, and docs/fixture-dates-arbitrary.md describes
the general case. Clone something that does not already run, or expect collisions.

    python mkphases.py --base ...\pesdb --out ...\livecpk\_FL26Conf ^
                       --like UEFA_EUROPA_LEAGUE --name "FL Conference League" --code FL_UECL

Changing a phase into something the source did not have is what --phase is for, and it is the
only way to build a shape nobody ships. Give it the phase's number in table order and the four
things that describe a phase (a dash keeps what the source had):

    --phase 2:league:36:0:regular

reads as "phase two becomes a 36-club league in no groups, the regular season". Setting the
group count to zero also drops that phase's replica rows, because a replica IS a group and
leaving them behind would contradict the count the phase declares. The kinds are league,
league2s, groups, knockout, playoff, qual1, qual2, split; the roles are league, cup, groups,
natgroups, knockout, natknockout, second, apertura, clausura, splittotal, regular, top, second2,
lower. Both vocabularies are the game's own (docs/findings.md and
docs/regulation-record-decode.md).

So the Champions League's new format -- a 36-club single table, then a play-off, then the last
sixteen -- is the shipped competition with its middle phase changed:

    python mkphases.py --base ...\pesdb --out ...\livecpk\_FL26UCL ^
                       --like UEFA_CHAMPIONS_LEAGUE --name "FL Champions League" ^
                       --code FL_UCL --phase 2:league:36:0:regular --teams <36 club ids>

--dry prints the plan and touches nothing.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mkleague as M
import mkworld as W

R_BACK, R_GROUP = 0x06, 0x0a      # replica: back-pointer to its master, and its group number
R_KIND, R_TEAMS, R_ROLE, R_GROUPS = 0x09, 0x0b, 0x0d, 0x10
REPLICA_STEP = 1024
NO_GROUP = 255

KINDS = {"playoff": 1, "groups": 2, "knockout": 3, "league": 4, "league2s": 5,
         "qual1": 6, "qual2": 7, "practice": 8, "split": 9}
ROLES = {"league": 1, "cup": 2, "groups": 4, "natgroups": 5, "knockout": 6, "natknockout": 7,
         "second": 8, "apertura": 9, "clausura": 10, "splittotal": 11, "regular": 12,
         "top": 13, "second2": 14, "lower": 15}
ROLE_SAID = {1: "domestic league", 2: "cup or qualifying round", 4: "club group stage",
             5: "national group stage", 6: "club knockout", 7: "national knockout",
             8: "second round", 9: "apertura", 10: "clausura", 11: "split total",
             12: "regular season before a split", 13: "top group of a split",
             14: "second group of a split", 15: "lower group of a split"}


def overrides(args):
    """{phase number (1-based): (kind, clubs, groups, role)}, each item None for 'keep'."""
    out = {}
    for k, v in zip(args, args[1:]):
        if k != "--phase":
            continue
        bits = v.split(":")
        if len(bits) != 5:
            raise SystemExit("--phase wants five fields, N:kind:clubs:groups:role, and a dash "
                             "where the source's value should stay -- got %r" % v)
        n, kind, clubs, groups, role = bits
        if kind != "-" and kind not in KINDS:
            raise SystemExit("no such kind %r; the game knows %s" % (kind, ", ".join(KINDS)))
        if role != "-" and role not in ROLES:
            raise SystemExit("no such role %r; the game knows %s" % (role, ", ".join(ROLES)))
        out[int(n)] = (KINDS.get(kind), None if clubs == "-" else int(clubs),
                       None if groups == "-" else int(groups), ROLES.get(role))
    return out


def apply_phase(row, over):
    """Write one --phase onto a master row. Returns a sentence about what changed."""
    kind, clubs, groups, role = over
    said = []
    if kind is not None:
        row[R_KIND] = kind
        said.append("kind %s" % [k for k, v in KINDS.items() if v == kind][0])
    if clubs is not None:
        if not 0 < clubs < 64:
            raise SystemExit("the club count is six bits wide, so %d will not fit" % clubs)
        row[R_TEAMS] = (row[R_TEAMS] & ~0x3f) | clubs
        said.append("%d clubs" % clubs)
    if groups is not None:
        if not 0 <= groups < 32:
            raise SystemExit("the group count is five bits wide, so %d will not fit" % groups)
        row[R_GROUPS] = (row[R_GROUPS] & ~0x1f) | groups
        said.append("%d group(s)" % groups)
    if role is not None:
        row[R_ROLE] = (row[R_ROLE] & 0x0f) | (role << 4)
        said.append("the %s" % ROLE_SAID[role])
    return ", ".join(said)


def rid_of(row):
    return int.from_bytes(row[M.R_ID:M.R_ID + 2], "little")


def find_cid(comp, code):
    for i in range(len(comp) // M.COMP):
        r = comp[i * M.COMP:(i + 1) * M.COMP]
        if r[M.CODE_OFF:].split(b"\0")[0].decode("latin1") == code:
            return i, r[M.CID_OFF]
    raise SystemExit("no competition coded %s" % code)


def phases(regs, cid):
    """[(master row index, [replica row indexes])], in table order."""
    rows = [i for i in range(len(regs) // M.REG) if regs[i * M.REG + M.R_CID] == cid]
    masters, replicas = [], {}
    for i in rows:
        r = regs[i * M.REG:(i + 1) * M.REG]
        if r[R_GROUP] == NO_GROUP:
            masters.append(i)
        else:
            replicas.setdefault(int.from_bytes(r[R_BACK:R_BACK + 2], "little"), []).append(i)
    return [(i, replicas.get(rid_of(regs[i * M.REG:(i + 1) * M.REG]), [])) for i in masters]


def main():
    a = sys.argv[1:]
    get = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    base, out = get("--base"), get("--out")
    like = get("--like")
    if not base or not out or not like:
        print(__doc__)
        return 1

    comp, regs, ents = (M.load(base, n) for n in
                        ("Competition.bin", "CompetitionRegulation.bin",
                         "CompetitionEntry.bin"))
    print("base: %d competitions, %d regulations, %d entries"
          % (len(comp) // M.COMP, len(regs) // M.REG, len(ents) // M.ENT))

    over = overrides(a)
    src_i, src_cid = find_cid(comp, like)
    plan = phases(regs, src_cid)
    if not plan:
        raise SystemExit("%s has no regulation rows" % like)
    if len(plan) == 1 and not plan[0][1]:
        raise SystemExit("%s is a single-phase competition -- mkleague.py or mkcup.py does "
                         "that, and does it with fewer ways to go wrong" % like)

    used_cid = {comp[i * M.COMP + M.CID_OFF] for i in range(len(comp) // M.COMP)}
    used_reg = {rid_of(regs[i * M.REG:(i + 1) * M.REG]) for i in range(len(regs) // M.REG)}
    cid = int(get("--cid", str(W.free_ids(used_cid, W.CID_MAX, 1, 130)[0])))
    if cid in used_cid:
        raise SystemExit("competition id %d is taken" % cid)
    newmasters = W.free_ids(used_reg | W.BAD_REG, W.REG_MAX, len(plan), 186)
    name = get("--name", "FL Multi-Phase Cup")

    # A phase told to have no groups keeps no replicas: a replica IS a group.
    dropped = set()
    for n, (mi, reps) in enumerate(plan, start=1):
        if n in over and over[n][2] == 0 and reps:
            dropped.update(reps)
            plan[n - 1] = (mi, [])
    if over and max(over) > len(plan):
        raise SystemExit("--phase %d, but %s has %d phases" % (max(over), like, len(plan)))

    # Work out every id before writing anything: a half-renumbered clone is worse than none.
    remap = {}
    for (mi, reps), newm in zip(plan, newmasters):
        remap[rid_of(regs[mi * M.REG:(mi + 1) * M.REG])] = newm
        for ri in reps:
            grp = regs[ri * M.REG + R_GROUP]
            new = newm + (grp + 1) * REPLICA_STEP
            if new in used_reg:
                raise SystemExit("replica id %d (master %d, group %d) is taken -- choose "
                                 "another --cid, or clone into a quieter world"
                                 % (new, newm, grp))
            remap[rid_of(regs[ri * M.REG:(ri + 1) * M.REG])] = new

    print("")
    print("%s: competition %d, %d phases" % (name, cid, len(plan)))
    n_of = {mi: n for n, (mi, _r) in enumerate(plan, start=1)}
    for (mi, reps), newm in zip(plan, newmasters):
        r = regs[mi * M.REG:(mi + 1) * M.REG]
        # +0x10's low five bits are the phase's declared group count (findings.md), and it
        # has to agree with the replicas actually present -- so both are printed.
        print("   regulation %4d -> %4d   type %d, %d clubs, %d replica(s), declares %d group(s)"
              % (rid_of(r), newm, r[M.R_TYPE], r[M.R_TEAMS] & 0x3f, len(reps), r[0x10] & 0x1f))
        if n_of.get(mi) in over:
            continue          # it is about to be overwritten; the change is printed below
        if (r[0x10] & 0x1f) != len(reps):
            print("      the prototype declares a different number of groups than it has "
                  "replicas -- the clone will carry that disagreement")

    # the competition row
    c = bytearray(comp[src_i * M.COMP:(src_i + 1) * M.COMP])
    if "--region" in a:
        c[M.REGION_OFF] = int(get("--region"))
    c[M.CID_OFF] = cid
    M.put(c, M.CODE_OFF, get("--code", "FL_MULTI_PHASE"), M.COMP - M.CODE_OFF)
    comp += c

    # every regulation row of the source, in table order, renumbered
    added = 0
    master_no = {mi: n for n, (mi, _r) in enumerate(plan, start=1)}
    for i in range(len(regs) // M.REG):
        if regs[i * M.REG + M.R_CID] != src_cid or i in dropped:
            continue
        g = bytearray(regs[i * M.REG:(i + 1) * M.REG])
        g[M.R_NAMEID:M.R_NAMEID + 2] = bytes(2)
        g[M.R_ID:M.R_ID + 2] = remap[rid_of(g)].to_bytes(2, "little")
        g[M.R_CID] = cid
        if g[R_GROUP] != NO_GROUP:
            back = int.from_bytes(g[R_BACK:R_BACK + 2], "little")
            g[R_BACK:R_BACK + 2] = remap[back].to_bytes(2, "little")
        if i in master_no and master_no[i] in over:
            said = apply_phase(g, over[master_no[i]])
            if said:
                print("   phase %d becomes %s" % (master_no[i], said))
        for k in range(M.NAME_SLOTS):
            M.put(g, M.R_NAME + k * M.NAME_SLOT, name, M.NAME_SLOT)
        regs += g
        added += 1

    # entries: the caller's clubs, or the source's own line-up
    teams = [int(x) for x in get("--teams", "").split(",") if x.strip()]
    if not teams:
        teams = [int.from_bytes(ents[i * M.ENT:i * M.ENT + 4], "little")
                 for i in range(len(ents) // M.ENT) if ents[i * M.ENT + M.E_CID] == src_cid]
        print("")
        print("no --teams given, so the %d clubs of %s are entered" % (len(teams), like))
    eid = max(int.from_bytes(ents[i * M.ENT + M.E_EID:i * M.ENT + M.E_EID + 4], "little")
              for i in range(len(ents) // M.ENT))
    for k, t in enumerate(teams):
        e = bytearray(M.ENT)
        e[M.E_TEAM:M.E_TEAM + 4] = t.to_bytes(4, "little")
        e[M.E_EID:M.E_EID + 4] = (eid + 1 + k).to_bytes(4, "little")
        e[M.E_CID], e[M.E_ORDER] = cid, k + 1
        ents += e

    if dropped:
        print("%d replica row(s) dropped, because the phase they belonged to now has no groups"
              % len(dropped))
    print("%d regulation rows, %d entries, region byte %d"
          % (added, len(teams), c[M.REGION_OFF]))
    print("calendars are the source's: give the clone its own dates before running it "
          "alongside %s" % like)

    if "--dry" in a:
        print("dry run: nothing written")
        return 0
    M.write_tables(out, comp, regs, ents)
    return 0


if __name__ == "__main__":
    sys.exit(main())
