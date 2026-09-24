r"""python mksizes.py --src <livecpk world> --out <new livecpk world> --plan <plan.json> [--dry]

Give our leagues the sizes real leagues have: ten clubs playing each other four times,
twelve playing three times, sixteen, eighteen, twenty-two, twenty-four -- instead of
thirty-nine copies of twenty clubs playing twice.

The plan is a JSON object keyed by regulation id:

    { "11":  { "clubs": 10, "legs": 4, "name": "Croatia D1" },
      "62":  { "clubs": 12, "legs": 3 },
      ... }

For every league named in it this writes, in the league's master regulation row,

    +0x0b bits 0-5    the club count
    +0x10 bits 12-14  how many times each pair meets (1..7)
    +0x14 ...         the name, in all twenty language slots, when "name" is given

and makes CompetitionEntry.bin agree: a league that shrinks gives up its last clubs, a league
that grows takes clubs from that pool, in plan order, and every league's positions are
renumbered 1..n. Clubs nobody takes stay in Team.bin with no league, as the shipped game's
unattached clubs do. Nothing shipped is touched and no id changes.

How many rounds the season then has is (clubs - 1) * legs, and fl26swiss.dll resamples the
calendar to that many dates (league_dates); without it a short league stops in spring and a
long one runs out of dates.

    python mksizes.py --src E:\...\livecpk\_FL26G39EPO --out E:\...\livecpk\_FL26G39Size --plan sizes.json
"""
import json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mkleague as M

PESDB = os.path.join("common", "etc", "pesdb")
R_GROUP, R_RULES = 0x0a, 0x10
LEGS_SHIFT, LEGS_MASK = 12, 7


def rid(row):
    return int.from_bytes(row[M.R_ID:M.R_ID + 2], "little")


def main():
    a = sys.argv[1:]
    get = lambda k: a[a.index(k) + 1] if k in a else None
    src, out, planf = get("--src"), get("--out"), get("--plan")
    if not src or not out or not planf:
        print(__doc__)
        return 1
    plan = {int(k): v for k, v in json.load(open(planf, encoding="utf-8")).items() if not k.startswith("_")}
    base = os.path.join(src, PESDB)
    comp, regs, ents = (M.load(base, n) for n in
                        ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin"))
    regs = bytearray(regs)
    nreg = len(regs) // M.REG
    rows = {}
    for i in range(nreg):
        o = i * M.REG
        if regs[o + M.R_TYPE] == 4 and regs[o + R_GROUP] == 255:
            rows.setdefault(rid(regs[o:o + M.REG]), o)
    for r in plan:
        if r not in rows:
            raise SystemExit("regulation %d is not a league master row in %s" % (r, src))

    entries = [bytearray(ents[i * M.ENT:(i + 1) * M.ENT]) for i in range(len(ents) // M.ENT)]
    by_cid = {}
    for e in entries:
        by_cid.setdefault(e[M.E_CID], []).append(e)
    for lst in by_cid.values():
        lst.sort(key=lambda e: e[M.E_ORDER])

    # a club that also plays somewhere else (a European entry, a cup) is kept before one that
    # does not, so shrinking a league never leaves a Champions League club without a league
    elsewhere = {}
    for e in entries:
        elsewhere.setdefault(int.from_bytes(e[M.E_TEAM:M.E_TEAM + 4], "little"), set()).add(e[M.E_CID])
    pool, keep = [], {}
    for r, p in plan.items():
        o = rows[r]
        cid = regs[o + M.R_CID]
        mine = sorted(by_cid.get(cid, []), key=lambda e: (
            len(elsewhere[int.from_bytes(e[M.E_TEAM:M.E_TEAM + 4], "little")]) == 1, e[M.E_ORDER]))
        n = int(p["clubs"])
        if not 4 <= n <= 63:
            raise SystemExit("reg %d: %d clubs is outside 4..63" % (r, n))
        keep[r] = mine[:n]
        pool += [int.from_bytes(e[M.E_TEAM:M.E_TEAM + 4], "little") for e in mine[n:]]
    eid = max(int.from_bytes(e[M.E_EID:M.E_EID + 4], "little") for e in entries)
    grown = {}
    for r, p in plan.items():
        want = int(p["clubs"]) - len(keep[r])
        if want > len(pool):
            raise SystemExit("reg %d needs %d more clubs, only %d are free" % (r, want, len(pool)))
        cid = regs[rows[r] + M.R_CID]
        for t in pool[:want]:
            eid += 1
            e = bytearray(M.ENT)
            e[M.E_TEAM:M.E_TEAM + 4] = t.to_bytes(4, "little")
            e[M.E_EID:M.E_EID + 4] = eid.to_bytes(4, "little")
            e[M.E_CID] = cid
            keep[r].append(e)
        grown[r] = want
        pool = pool[want:]

    planned = {regs[rows[r] + M.R_CID] for r in plan}
    new_ents = bytearray()
    for e in entries:
        if e[M.E_CID] not in planned:
            new_ents += e
    for r, p in plan.items():
        o = rows[r]
        for k, e in enumerate(keep[r]):
            e[M.E_ORDER] = k + 1
            new_ents += e
        n, legs = int(p["clubs"]), int(p.get("legs", 2))
        if not 1 <= legs <= LEGS_MASK:
            raise SystemExit("reg %d: legs %d is outside 1..7" % (r, legs))
        regs[o + M.R_TEAMS] = (regs[o + M.R_TEAMS] & 0xc0) | n
        rules = int.from_bytes(regs[o + R_RULES:o + R_RULES + 4], "little")
        rules = (rules & ~(LEGS_MASK << LEGS_SHIFT)) | (legs << LEGS_SHIFT)
        regs[o + R_RULES:o + R_RULES + 4] = rules.to_bytes(4, "little")
        if p.get("name"):
            for k in range(M.NAME_SLOTS):
                M.put(regs, o + M.R_NAME + k * M.NAME_SLOT, p["name"], M.NAME_SLOT)
        rounds = (n - 1 if n % 2 == 0 else n) * legs
        name = regs[o + M.R_NAME:o + M.R_NAME + M.NAME_SLOT].split(b"\0")[0].decode("utf-8", "replace")
        print("reg %3d  %-26s %2d clubs x %d = %2d rounds%s" % (
            r, name, n, legs, rounds, "  (+%d clubs)" % grown[r] if grown[r] > 0 else ""))
    print("%d clubs left without a league" % len(pool))

    if "--dry" in a:
        print("dry run: nothing written")
        return 0
    if os.path.exists(out):
        raise SystemExit("%s exists -- pick a new name, worlds are not overwritten" % out)
    shutil.copytree(src, out, ignore=shutil.ignore_patterns("*.pre*", "*.retiered", "*.bak*"))
    M.write_tables(out, comp, regs, new_ents)
    return 0


if __name__ == "__main__":
    sys.exit(main())
