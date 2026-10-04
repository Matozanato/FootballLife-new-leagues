"""python dayplan.py [--set NAME] [--iters N]  -> a better date-spread assignment

A calendar day holds 280 match ids and the scheduler at 0x141350290 drops the rest without
a word, so how the new leagues are spread over the seven day-shifts of the datecave stub
decides how many leagues a world can carry.  Dealing the shifts round-robin is not good
enough: the shipped competitions are not spread evenly either, so some shifts start out
much busier than others, and a round-robin that ignores that can be worse than using fewer
shifts (measured: 0..6 round-robin peaks at 261 where the four-shift cycle it replaced
peaks at 251).

This reads the season out of the running game, splits every calendar day into the shipped
load and each of our leagues' own load, and then searches for the assignment that minimises
the busiest day.  The shift is a whole number of days added to every fixture of a league,
so moving a league from shift a to shift b just moves its days by (b - a) mod 7: the search
is exact arithmetic on the measured days, not a model of the scheduler.

It prints the `--date-offsets` argument for patchset.py, so the workflow is: create a
season, measure it, regenerate the set with the assignment, create the season again.

    python dayplan.py --set teams-coaches-regs-players-dates-matches-upper-mlcopy

--demand measures from the match records instead of from the calendar, and after the first
rollover that is the only honest measurement.  Walking the calendar counts what the
scheduler accepted; once a day is full it refuses the rest without a word, so the matches
that most need moving are exactly the ones the calendar cannot show.  A record carries its
own date and that date names the calendar day exactly (checked on 22723 records, difference
zero), so --demand sees the turned-away matches too.  Measured at day 181 of a second
season: the calendar showed a tidy 280 on its busiest day, the records showed 351 wanted it.
"""
import collections, json, os, random, sys
import livedump as L

LAY = L.LAYOUT
H = L.H
ROOT = L.ROOT
CAL, DAYS, DAY, NCOUNT = 0x16038a8, 365, 0x2c4, 0x230
SHIFTS = 7


def load(setname):
    return json.load(open(os.path.join(ROOT, "patches", setname + ".json")))


def measure(st):
    """(shipped load per day, per-league load per day) out of the running game"""
    bases = {k: H(v) for k, v in st["bases_new"].items()}
    ours = set(st["date_keys"])
    a = LAY["arrays"]["rec596"]
    mt = bases.get("rec596", H(a["base_old"]))
    ms, mn = H(a["stride"]), a["cap_new"]
    m = L.Mem(L.find_pid()[0])
    owner = m.u64(H(LAY["getters"]["owner_global"]))
    blk = m.u64(owner + H(LAY["getters"]["owner_field"]))
    buf = bytearray()
    for i in range(0, mn, 512):
        n = min(512, mn - i)
        chunk = m.read(blk + mt + i * ms, n * ms)
        if chunk is None:
            raise SystemExit("could not read the match table; is a season loaded?")
        buf += chunk
    keyof = {}
    for i in range(mn):
        r = buf[i * ms:(i + 1) * ms]
        if int.from_bytes(r[0:2], "little") != 0xffff:
            keyof[i] = int.from_bytes(r[4:6], "little")
    cal = m.read(blk + CAL, DAYS * DAY)
    shipped = [0] * DAYS
    perkey = {k: [0] * DAYS for k in ours}
    for d in range(DAYS):
        r = cal[d * DAY:(d + 1) * DAY]
        for i in range(0, NCOUNT, 2):
            v = int.from_bytes(r[i:i + 2], "little")
            if v == 0xffff:
                break
            k = keyof.get(v)
            if k in ours:
                perkey[k][d] += 1
            else:
                shipped[d] += 1
    return shipped, perkey


def demand(st):
    """(shipped load per day, per-league load per day), counted from the match records

    Same shape as measure(), so the search does not care which one it was handed.  The date
    lives at +0x08 year, +0x0a month, +0x0b day-of-month, and day 0 is 1 January.  A leap
    year would push everything after February by one and is not handled -- no run has
    reached one.
    """
    CUM = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)
    bases = {k: H(v) for k, v in st["bases_new"].items()}
    ours = set(st["date_keys"])
    a = LAY["arrays"]["rec596"]
    mt = bases.get("rec596", H(a["base_old"]))
    ms, mn = H(a["stride"]), a["cap_new"]
    m = L.Mem(L.find_pid()[0])
    owner = m.u64(H(LAY["getters"]["owner_global"]))
    blk = m.u64(owner + H(LAY["getters"]["owner_field"]))
    buf = bytearray()
    for i in range(0, mn, 512):
        n = min(512, mn - i)
        chunk = m.read(blk + mt + i * ms, n * ms)
        if chunk is None:
            raise SystemExit("could not read the match table; is a season loaded?")
        buf += chunk
    shipped = [0] * DAYS
    perkey = {k: [0] * DAYS for k in ours}
    for i in range(mn):
        r = buf[i * ms:i * ms + 12]
        if int.from_bytes(r[0:2], "little") == 0xffff:
            continue
        mo, dm = r[0x0a], r[0x0b]
        if not (1 <= mo <= 12 and 1 <= dm <= 31):
            continue
        d = CUM[mo - 1] + dm - 1
        k = int.from_bytes(r[4:6], "little")
        if k in ours:
            perkey[k][d] += 1
        else:
            shipped[d] += 1
    return shipped, perkey


def totals(shipped, perkey, old, assign):
    """the per-day load for an assignment; leagues not in it are simply not placed yet"""
    tot = shipped[:]
    for k, shift in assign.items():
        row = perkey[k]
        delta = (shift - old[k]) % SHIFTS
        for d in range(DAYS):
            n = row[d]
            if n:
                tot[(d + delta) % DAYS] += n
    return tot


def main():
    a = sys.argv[1:]
    get = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    # FL26_SET is how every other tool here is told which world is installed, and this one
    # ignored it: the default below is an older set whose date_keys are a different list of
    # leagues entirely.  On 18 September that silently produced a plan for leagues 12, 13,
    # 63-78, 101 and 102 -- none of which are in the installed world -- and a "does not fit"
    # verdict computed from them.  Environment first, then the flag, then the old default.
    setname = get("--set", os.environ.get(
        "FL26_SET", "teams-coaches-regs-players-dates-matches-upper-mlcopy"))
    iters = int(get("--iters", "600"))
    st = load(setname)
    if not st.get("date_offsets"):
        raise SystemExit("%s was not generated with --date-offsets, so there is no "
                         "spread to improve" % setname)
    old = {int(k): v for k, v in st["date_offsets"].items()}
    shipped, perkey = demand(st) if "--demand" in a else measure(st)
    keys = sorted(perkey)

    peak = lambda asg: max(totals(shipped, perkey, old, asg))
    print("measured from %s: %d leagues, shipped peak %d, current peak %d (shifts %s)"
          % ("the match records" if "--demand" in a else "the calendar",
             len(keys), max(shipped), peak(old), sorted(set(old.values()))))

    # heaviest league first, each onto the shift that leaves the lowest peak
    weight = {k: sum(perkey[k]) for k in keys}
    asg = {}
    for k in sorted(keys, key=lambda k: -weight[k]):
        best = None
        for s in range(SHIFTS):
            asg[k] = s
            p = peak(asg)
            if best is None or p < best:
                best, bs = p, s
        asg[k] = bs
    print("greedy:   peak %d" % peak(asg))

    rng = random.Random(7)
    best = peak(asg)
    for _ in range(iters):
        k = rng.choice(keys)
        was = asg[k]
        asg[k] = rng.randrange(SHIFTS)
        p = peak(asg)
        if p <= best:
            best = p
        else:
            asg[k] = was
    tot = totals(shipped, perkey, old, asg)
    top = sorted(range(DAYS), key=lambda d: -tot[d])[:6]
    print("searched: peak %d   busiest: %s"
          % (best, ", ".join("day %d = %d" % (d, tot[d]) for d in top)))
    print("headroom on the busiest day: %d of 280" % (280 - best))
    if best > 280:
        print("STILL OVER: %d matches want a place that does not exist, so a day-shift "
              "alone does not fit this season" % sum(max(0, n - 280) for n in tot))
    print("\n--date-offsets %s" % ",".join("%d:%d" % (k, asg[k]) for k in keys))
    return 0


if __name__ == "__main__":
    sys.exit(main())
