"""spreadregions.py -- fix "leagues missing from the Master League menu" by spreading
OUR 39 added leagues off England onto free region slots.

Root cause (measured 2026-09-19): every one of our 39 leagues, plus the 5 shipped English
competitions, sits under region England (Competition.bin +3 == 16 == id 2 x 8). That is 44
competitions in one country; no shipped region holds more than ~10-11, and the Master League
team-select menu lists competitions per country, so the overflow (FL02 among them) never
renders. Spreading our leagues across several regions, <=11 each, restores them (proven for
the Select Team list by the _FL26Reg39 experiment; here applied to the GOOD-id world so no
phase-hijack is reintroduced).

We use the four region ids that are free (no shipped competition uses them) and all sit
below the 29 parser limit, so NO exe patch is needed for the menu to accept them:

    region 11 (byte 0x58)  <- FL League 01..10   (keeps the FL01/02/03 pyramid together)
    region 13 (byte 0x68)  <- FL League 11..20
    region 14 (byte 0x70)  <- FL League 21..30
    region 20 (byte 0xa0)  <- FL League 31..39

These four ids have no entry in the region-name table (0x1426770c0), so in-game the region
HEADER renders blank (measured-safe: the table has no fallback but the game does not crash,
docs/findings.md region-name section). Custom names are a separate build (name-table
extension + sys_*.str keys); this tool only does the safe, reversible data spread.

Region is Competition.bin byte +3, bits 3-7 (value = region_id * 8); bits 0-2 are 0 in all
rows. Only OUR leagues (regulation name "FL League NN") are touched -- shipped competitions
(incl. the Scottish/Saudi comps interleaved in the same comp-id range) are left alone.

Two plans (2026-09-21):

    --plan free      the four free ids above, ten of our leagues each.  No name, no flag:
                     a region with no entry in the exe's 24-record table does not render
                     blank, it renders whatever the previous lookup left behind.
    --plan own       a region of its own for every one of our leagues -- every free id, in
                     order, the four below 29 first.  With 39 leagues and 39 free ids this is
                     an exact fit, and it needs sider/fl26reg64.lua for everything above 28
                     (the engine reads 64 regions once that byte is in, but only 29 without).
    --plan shipped   spread them over the shipped country regions instead, at most three of
                     ours per region and never taking a region past eight competitions in
                     total.  They inherit a real name and a real flag, and they take nothing
                     from anyone: European places are granted per competition and only
                     filtered by region, so our leagues get none of France's places and
                     France keeps all of its own (docs/regions-plan.md).

  python spreadregions.py --root <livecpk-root>                  # apply the spread (default plan: free)
  python spreadregions.py --root <livecpk-root> --plan own       # one region per league
  python spreadregions.py --root <livecpk-root> --plan shipped   # spread over named regions
  python spreadregions.py --root <livecpk-root> --restore  # put our leagues back on England
  python spreadregions.py --root <livecpk-root> --preview   # what the shipped plan would do
  python spreadregions.py --root <livecpk-root> --show      # print current region per league
"""
import os, sys, re, shutil
import pesdb

REC = 36
REGION_OFF = 3
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mkleague as M
enc_region, dec_region = M.enc_region, M.dec_region
REGION_TABLE = 0x1426770c0    # the exe table that gives a region its name and flag
ENGLAND_ID = 2
# FL number range (inclusive) -> free region id
PLAN = [((1, 10), 11), ((11, 20), 13), ((21, 30), 14), ((31, 39), 20)]


def our_comps(root):
    """Return {comp_id: fl_number} for our 39 leagues, read from CompetitionRegulation."""
    p = os.path.join(root, "common", "etc", "pesdb", "CompetitionRegulation.bin")
    reg = pesdb.reg_rows(pesdb.wesys_unpack(open(p, "rb").read()))
    out = {}
    for r in reg:
        m = re.fullmatch(r"FL League (\d+)", r["name"])
        if m:
            out[r["comp"]] = int(m.group(1))
    return out


# Regions that must be left alone whatever the plan.  Read off the exe's own region table
# (0x1426770c0, 24 records, dumped 2026-09-21): ids 1 interClub, 22 PEU, 23 PLA, 24 PAS,
# 25 interNational and 26 event are groupings, not countries -- a domestic league filed
# under "Europe" or "event" reads as a mistake even though the menu would accept it.
# England (2) is the crowd we are spreading away from.  The four ids with no entry in that
# table at all (11, 13, 14, 20) exclude themselves: no shipped competition uses them, so
# they never appear in the count below.
NOT_A_COUNTRY = {1, 2, 22, 23, 24, 25, 26}
PER_REGION_MAX = 3          # of ours
REGION_TOTAL_MAX = 8        # ours plus whatever the region already holds


REGION_NAMES = {}      # region id -> the texture key the menus use, read from the exe


def region_names():
    """{region id: name} from the exe's own 24-record table, or {} if the exe is not here.

    Read rather than hard-coded, so a different build cannot make this quietly wrong. The
    names are texture keys (compeCategory-england); the country part is what we print.
    """
    global REGION_NAMES
    if REGION_NAMES:
        return REGION_NAMES
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import struct, boundscan
        d, secs, base = boundscan.image()
        def off(va):
            for _, sva, vsz, rp, rsz in secs:
                if sva + base <= va < sva + base + vsz:
                    return va - base - sva + rp
        for i in range(24):
            nameptr, ident, _ = struct.unpack_from("<QII", d, off(REGION_TABLE + i * 16))
            o = off(nameptr)
            key = d[o:d.find(bytes(1), o, o + 64)].decode("ascii", "replace")
            REGION_NAMES[ident] = key.replace("compeCategory-", "")
    except Exception as e:
        print("  (region names unavailable: %s)" % e)
    return REGION_NAMES


def preview(raw, ours):
    """What --plan shipped would do, printed, with nothing written."""
    from collections import Counter
    nm = region_names()
    held = Counter()
    for i in range(len(raw) // REC):
        r = raw[i * REC:(i + 1) * REC]
        if r[5] not in ours:
            held[dec_region(r[REGION_OFF])] += 1
    print("")
    print("shipped competitions per region:")
    for rid in sorted(held):
        why = ""
        if rid == ENGLAND_ID:
            why = "   (left alone: this is the crowd we are spreading away from)"
        elif rid in NOT_A_COUNTRY:
            why = "   (left alone: a grouping, not a country)"
        print("  %3d %-22s %2d%s" % (rid, nm.get(rid, "<no entry in the exe table>"),
                                     held[rid], why))
    plan = shipped_plan(raw, ours)
    per = Counter(plan.values())
    print("")
    print("where our %d leagues would land:" % len(ours))
    for rid in sorted(per):
        fls = sorted(fl for fl, r in plan.items() if r == rid)
        print("  %3d %-22s +%d ours, %d in total   FL %s"
              % (rid, nm.get(rid, "?"), per[rid], held[rid] + per[rid],
                 ", ".join(str(f) for f in fls)))
    print("")
    print("nothing written. Re-run with --plan shipped and no --preview to apply it.")


def region_for(fl_num):
    for (lo, hi), rid in PLAN:
        if lo <= fl_num <= hi:
            return rid
    raise ValueError("no region planned for FL %d" % fl_num)


def own_plan(raw, ours):
    """{fl_number: region_id} -- a region of its OWN for every one of our leagues.

    Free means no shipped competition uses the id and it is not one of the groupings. Ids
    below 29 come first, because those work on an unpatched exe; everything from 29 up needs
    sider/fl26reg64.lua, and this says so rather than assuming it.
    """
    used = set()
    for i in range(len(raw) // REC):
        r = raw[i * REC:(i + 1) * REC]
        if r[5] not in ours:
            used.add(dec_region(r[REGION_OFF]))
    # Anything of ours already sitting in a shipped country's region was put there on
    # purpose -- deepen.py does it to hang a third division under Ligue 2 -- so it keeps
    # the region it has and does not ask for one of its own.
    settled = {}
    for i in range(len(raw) // REC):
        r = raw[i * REC:(i + 1) * REC]
        if r[5] in ours and dec_region(r[REGION_OFF]) in used:
            settled[ours[r[5]]] = dec_region(r[REGION_OFF])
    if settled:
        print("  leaving %d league(s) where they are, inside a shipped country: %s"
              % (len(settled), ", ".join("FL %d in region %d" % (fl, rid)
                                         for fl, rid in sorted(settled.items()))))
    free = [rid for rid in range(1, 64) if rid not in used and rid not in NOT_A_COUNTRY]
    wants = [fl for fl in sorted(ours.values()) if fl not in settled]
    if len(free) < len(wants):
        raise SystemExit("only %d free regions for %d leagues" % (len(free), len(wants)))
    plan = dict(settled)
    for fl, rid in zip(wants, free):
        plan[fl] = rid
    high = [fl for fl, rid in plan.items() if rid > 28]
    if high:
        print("  %d of them land above region 28, so this world needs sider/fl26reg64.lua;"
              % len(high))
        print("  without it the game reads those regions as 32 lower than they are.")
    return plan


def shipped_plan(raw, ours):
    """{fl_number: region_id} spreading our leagues over the shipped country regions.

    Counted from the file rather than from a list, so a world with different shipped
    competitions plans itself.  Regions fill in order of how much room they have, which
    keeps the busiest countries out of it.
    """
    from collections import Counter
    n = len(raw) // REC
    held = Counter()
    for i in range(n):
        r = raw[i * REC:(i + 1) * REC]
        if r[5] in ours:
            continue                      # ours are being moved; do not count them
        held[dec_region(r[REGION_OFF])] += 1
    targets = sorted((rid for rid in held if rid not in NOT_A_COUNTRY),
                     key=lambda rid: (held[rid], rid))
    plan, mine = {}, Counter()
    for fl in sorted(ours.values()):
        for rid in targets:
            if mine[rid] < PER_REGION_MAX and held[rid] + mine[rid] < REGION_TOTAL_MAX:
                plan[fl] = rid
                mine[rid] += 1
                break
        else:
            raise SystemExit("no room: %d regions cannot hold %d leagues at %d each"
                             % (len(targets), len(ours), PER_REGION_MAX))
    return plan


def main():
    a = sys.argv[1:]
    def opt(name, d=None):
        return a[a.index(name) + 1] if name in a else d
    root = opt("--root")
    if not root:
        print(__doc__); return 1
    restore = "--restore" in a
    show = "--show" in a
    prev = "--preview" in a
    plan_name = opt("--plan", "free")
    if plan_name not in ("free", "shipped", "own"):
        print("--plan takes free, shipped or own"); return 1

    comp_path = os.path.join(root, "common", "etc", "pesdb", "Competition.bin")
    raw = bytearray(pesdb.wesys_unpack(open(comp_path, "rb").read()))
    n = len(raw) // REC
    ours = our_comps(root)
    print("our leagues: %d" % len(ours))
    if prev:
        preview(raw, ours)
        return 0
    plan = None
    if not restore:
        if plan_name == "shipped":
            plan = shipped_plan(raw, ours)
        elif plan_name == "own":
            plan = own_plan(raw, ours)

    if show:
        for i in range(n):
            r = raw[i * REC:(i + 1) * REC]
            cid = r[5]
            if cid in ours:
                print("  FL %2d  comp %3d  region byte 0x%02x (id %d)"
                      % (ours[cid], cid, r[REGION_OFF], dec_region(r[REGION_OFF])))
        return 0

    changed = 0
    for i in range(n):
        base = i * REC
        cid = raw[base + 5]
        if cid not in ours:
            continue
        if restore:
            rid = ENGLAND_ID
        elif plan is not None:
            rid = plan[ours[cid]]
        else:
            rid = region_for(ours[cid])
        newbyte = enc_region(rid)
        if raw[base + REGION_OFF] != newbyte:
            raw[base + REGION_OFF] = newbyte
            changed += 1

    if not restore:
        bak = comp_path + ".preSpread"
        if not os.path.exists(bak):
            shutil.copy2(comp_path, bak)
            print("backup -> %s" % bak)
    packed = pesdb.wesys_pack(bytes(raw))
    open(comp_path, "wb").write(packed)
    print("%s: %d league rows updated in %s"
          % ("RESTORE" if restore else "SPREAD", changed, comp_path))

    # verify by re-reading
    from collections import Counter
    comp = pesdb.comp_rows(pesdb.wesys_unpack(open(comp_path, "rb").read()))
    c = Counter(dec_region(x["raw"][3]) for x in comp if x["id"] in ours)
    print("our leagues now per region id: %s" % dict(sorted(c.items())))
    allc = Counter(dec_region(x["raw"][3]) for x in comp)
    over = {k: v for k, v in sorted(allc.items()) if v > 11}
    print("any region with >11 competitions: %s" % (over or "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
