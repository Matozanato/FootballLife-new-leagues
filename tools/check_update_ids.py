"""check_update_ids.py -- can a career of the previous release of a world go on with the new one?

    python check_update_ids.py PREV.zip NEW.zip [--json OUT.json]

Exit 1 (FAIL) on anything a running career of PREV breaks on (18.11.2026: the beta 3 career
b470-3006 crashed on the beta 4 world, Tajikistan Cup 04.07.2027, a tie with no club):

  competitions  the rows of PREV's Competition.bin, CompetitionRegulation.bin and CompetitionEntry.bin
                must stay at their row index (new rows only after them), and every entry id
                (CompetitionEntry +4) must still mean the same club, competition and place. Beta 4
                inserted USL League One in the middle: regulation rows 596.. moved by one (Tajik
                Cup 851 -> 852) and 3792 of 9698 entry ids got another club.
  new places    an entry in a competition PREV has that PREV did not have (a club more in a running
                league or cup), and
  new clubs     a club PREV does not have, entered in a competition: a career of PREV has none of
                its players (the save brings its own players; the 356 new ones of beta 4 were not in
                the career after the load), so it plays with an empty squad. Said apart: in a
                competition PREV has (its season changes), or only in competitions new in NEW (a
                career of PREV does not play them: only a new Master League has them, rowkeep.py;
                what a running career does with such a club is not checked in the game).
  ages          a kept player whose Age is higher than in PREV: fl26regen takes him for a regen at
                the load and renames him ("60 regens named again" with beta 4).

Reported, not failed: new clubs in no competition (a group of clubs in no league), new player / club
/ coach ids below PREV's max (a career makes no players of
its own: a regen is the same id in place, fl26regen.c), kept players renamed, and per pesdb table
whether it is the same, only appended to, or changed inside.
"""
import json, os, struct, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pesdb                                    # noqa: E402
import playeredit as pe                         # noqa: E402

PESDB = "/common/etc/pesdb/"
KEYED = {"Competition.bin": 36, "CompetitionRegulation.bin": 2352, "CompetitionEntry.bin": 12}


def tables(path):
    out = {}
    with zipfile.ZipFile(path) as z:
        for n in z.namelist():
            m = n.replace("\\", "/")
            if PESDB in "/" + m and m.endswith(".bin"):
                d = z.read(n)
                out[m.rsplit("/", 1)[1]] = pesdb.wesys_unpack(d) if d[3:8] == b"WESYS" else d
    return out


def recs(raw, size):
    return [raw[i:i + size] for i in range(0, len(raw), size)]


def ids(raw, size, off=8):
    return [struct.unpack_from("<I", raw, i + off)[0] for i in range(0, len(raw), size)]


def check(prev, new):
    a, b = tables(prev), tables(new)
    rep = {"fail": [], "info": [], "tables": {}}
    fail = lambda s: rep["fail"].append(s)
    info = lambda s: rep["info"].append(s)

    for n in sorted(set(a) | set(b)):
        x, y = a.get(n), b.get(n)
        if x is None or y is None:
            rep["tables"][n] = "only in " + ("new" if x is None else "prev")
            continue
        size = pesdb.REC.get(n[:-4]) or 1
        if x == y:
            st = "same"
        elif y[:len(x)] == x:
            st = "appended (+%d rows)" % ((len(y) - len(x)) // size)
        else:
            k = next(i for i in range(min(len(x), len(y))) if x[i] != y[i])
            st = "CHANGED inside from row %d (%d -> %d rows)" % (k // size, len(x) // size, len(y) // size)
        rep["tables"][n] = st

    # competitions: rows stay where they are, entry ids keep their meaning
    for n, size in KEYED.items():
        x, y = recs(a[n], size), recs(b[n], size)
        moved = [i for i in range(len(x)) if i >= len(y) or x[i] != y[i]]
        if n == "CompetitionEntry.bin":
            ka = {struct.unpack_from("<I", r, 4)[0]: r for r in x}
            kb = {struct.unpack_from("<I", r, 4)[0]: r for r in y}
            other = [k for k in ka if kb.get(k) != ka[k]]
            if other:
                fail("%s: %d of %d entry ids of prev mean another club / competition / place now (first %d)"
                     % (n, len(other), len(ka), min(other)))
        if moved:
            fail("%s: %d of %d rows of prev are not where they were (first row %d)" % (n, len(moved), len(x), moved[0]))

    # new places and new clubs: in competitions prev has, or only in new ones (18.11.2026 evening)
    cid = lambda r: r[8] | r[11] << 8
    place = lambda r: (cid(r), r[9])
    old_cids = {r[5] | r[7] << 8 for r in recs(a["Competition.bin"], 36)} | {cid(r) for r in recs(a["CompetitionEntry.bin"], 12)}
    old_places = {place(r) for r in recs(a["CompetitionEntry.bin"], 12)}
    added = [r for r in recs(b["CompetitionEntry.bin"], 12) if cid(r) in old_cids and place(r) not in old_places]
    if added:
        fail("CompetitionEntry.bin: %d new places in %d competitions prev has (a running league or cup changes): "
             "competition %s" % (len(added), len({cid(r) for r in added}), " ".join(map(str, sorted({cid(r) for r in added})))))
    ta, tb = set(ids(a["Team.bin"], pe.T_REC)), set(ids(b["Team.bin"], pe.T_REC))
    where = {}
    for r in recs(b["CompetitionEntry.bin"], 12):
        where.setdefault(struct.unpack_from("<I", r, 0)[0], set()).add(cid(r))
    newclubs = sorted(tb - ta)
    in_old = [t for t in newclubs if where.get(t, set()) & old_cids]
    in_new = [t for t in newclubs if where.get(t) and not where[t] & old_cids]
    if in_old:
        fail("Team.bin: %d new clubs play in competitions prev has; a career of prev has no players for them: %s"
             % (len(in_old), " ".join(map(str, in_old))))
    if in_new:
        fail("Team.bin: %d new clubs play only in competitions prev does not have (%s); a career of prev has no "
             "players for them, and what it does with them is not checked in the game: %s"
             % (len(in_new), " ".join(map(str, sorted({c for t in in_new for c in where[t]}))),
                " ".join(map(str, in_new))))
    idle = [t for t in newclubs if t not in where]
    if idle:
        info("Team.bin: %d new clubs are in no competition (a group of clubs in no league): %s"
             % (len(idle), " ".join(map(str, idle))))
    for n, size, off in (("Team.bin", pe.T_REC, pe.T_ID), ("Coach.bin", 100, 0x00), ("Player.bin", pe.P_REC, pe.P_ID)):
        ia, ib = set(ids(a[n], size, off)), set(ids(b[n], size, off))
        low = sorted(i for i in ib - ia if i <= max(ia))
        info("%s: prev %d, new %d, kept %d, gone %d, new %d (%d of them below prev's max %d)"
             % (n, len(ia), len(ib), len(ia & ib), len(ia - ib), len(ib - ia), len(low), max(ia)))
    pa = {struct.unpack_from("<I", r, 8)[0]: r for r in recs(a["Player.bin"], pe.P_REC)}
    pb = {struct.unpack_from("<I", r, 8)[0]: r for r in recs(b["Player.bin"], pe.P_REC)}
    older = sorted(i for i in pa.keys() & pb.keys() if pe.getf(pb[i], "Age") > pe.getf(pa[i], "Age"))
    if older:
        fail("Player.bin: %d kept players are older than in prev (fl26regen renames them at a load): %s%s"
             % (len(older), " ".join(map(str, older[:20])), " ..." if len(older) > 20 else ""))
    nm = lambda r: pe.cstr(r[pe.P_NAME:pe.P_NAME + pe.P_NAME_LEN])
    renamed = [i for i in pa.keys() & pb.keys() if nm(pa[i]) != nm(pb[i])]
    info("Player.bin: %d kept players have another name" % len(renamed))
    rep["result"] = "FAIL" if rep["fail"] else "PASS"
    return rep


def main(argv):
    if len(argv) < 2 or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    rep = check(argv[0], argv[1])
    for n, st in rep["tables"].items():
        print("  %-30s %s" % (n, st))
    for s in rep["info"]:
        print("info: " + s)
    for s in rep["fail"]:
        print("FAIL: " + s)
    print(rep["result"])
    if "--json" in argv:
        json.dump(rep, open(argv[argv.index("--json") + 1], "w", encoding="utf-8"), indent=1)
    return 1 if rep["fail"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
