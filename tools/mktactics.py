r"""Formations for new clubs: Tactics.bin and TacticsFormation.bin.

The game's clubs each carry tactics; the clubs the League Builder adds have none, and the engine
then lines them up in a fixed 4-2-3-1 (the first eleven by squad order, lbplayers.LINEUP). This
gives a new club the tactics of a club of the game with the formation wanted: the same rows under
new keys, naming the new club.

    Tactics.bin           12 bytes a row: key u32, club u32, the team's strategy (4 bytes,
                          copied as they are). Most clubs have two rows.
    TacticsFormation.bin  12 bytes a row: tactics key u32, role u32 (ROLES), depth u8 (3 = the
                          goal line .. 46 = up front), width u8 (0 left .. 100 right, as the team
                          attacks), place u8 (low four bits: the place 0-10, high four: which of
                          the three variants 0-2), 0. 33 rows per tactics key: 3 x 11.

The place is the order in the squad the engine puts there, so the club's first eleven should
follow the formation's roles place by place (roles(); lbplayers.best_eleven takes them).

    python mktactics.py --base <pesdb> --list
    python mktactics.py --base <pesdb> --out <world pesdb> --club 71578=4-1-2-3 --club 71579=103

A formation is named by its lines, counted from the back (4-1-2-3 = four defenders, a
defensive midfielder, two central midfielders, three forwards), or given as the id of a club of
the game whose tactics to copy.
"""
import collections, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pesdb

ROLES = ["GK", "CB", "LB", "RB", "DMF", "CMF", "LMF", "RMF", "AMF", "LWF", "RWF", "SS", "CF"]
T_REC = F_REC = 12
PLACES = 11


def read(base):
    """(tactics rows [(key, club, strategy bytes)], {key: [[(place, role, depth, width)] x 3]},
    the two tables' WESYS headers)"""
    out = []
    for name in ("Tactics", "TacticsFormation"):
        p = os.path.join(base, name + ".bin")
        raw = open(p, "rb").read()
        out.append((pesdb.wesys_unpack(raw) if raw[3:8] == b"WESYS" else raw, raw[:3]))
    (t, th), (f, fh) = out
    rows = [(struct.unpack_from("<I", t, o)[0], struct.unpack_from("<I", t, o + 4)[0], t[o + 8:o + 12])
            for o in range(0, len(t), T_REC)]
    forms = collections.defaultdict(lambda: [[], [], []])
    for o in range(0, len(f), F_REC):
        k, role, depth, width, place = struct.unpack_from("<IIBBB", f, o)
        forms[k][(place >> 4) % 3].append((place & 15, role, depth, width))
    for v in forms.values():
        for s in v:
            s.sort()
    return rows, dict(forms), (th, fh)


def name_of(places):
    """4-2-3-1 and so on, from the roles of one variant: defenders, defensive midfielders,
    midfielders, attacking midfielders, forwards (wingers count as forwards; wide midfielders
    join the attacking midfielders when there are any, as in a 4-2-3-1)"""
    roles = [ROLES[r] for _p, r, _d, _w in places]
    n = collections.Counter(roles)
    am = n["AMF"] + n["SS"]
    wide = n["LMF"] + n["RMF"]
    lines = [n["CB"] + n["LB"] + n["RB"], n["DMF"], n["CMF"] + (0 if am else wide),
             am + (wide if am else 0), n["CF"] + n["LWF"] + n["RWF"]]
    return "-".join(str(x) for x in lines if x)


def roles(places):
    """the role of each place 0-10"""
    return [ROLES[r] for _p, r, _d, _w in sorted(places)]


def catalogue(rows, forms, names=None, skip=()):
    """[{name, club, key, places, clubs}] -- one entry per shape the game's clubs use (the roles
    of the first variant of their first tactics), most used first; club = the lowest club id
    with it, whose tactics a new club copies. Two shapes with one name get the club's name too.
    skip: teams left out (the national teams, for club formations)."""
    first = {}
    for k, club, _s in rows:
        if club not in skip:
            first.setdefault(club, k)
    shapes = collections.OrderedDict()
    for club in sorted(first):
        k = first[club]
        if k not in forms or len(forms[k][0]) != PLACES:
            continue
        sig = tuple(sorted(roles(forms[k][0])))
        e = shapes.setdefault(sig, {"name": name_of(forms[k][0]), "club": club, "key": k,
                                    "places": forms[k][0], "clubs": 0})
        e["clubs"] += 1
    out = sorted(shapes.values(), key=lambda e: -e["clubs"])
    seen = collections.Counter(e["name"] for e in out)
    for e in out:
        e["label"] = e["name"]
        if seen[e["name"]] > 1:
            e["label"] = "%s (%s)" % (e["name"], (names or {}).get(e["club"], "#%d" % e["club"]))
    return out


def find(cat, rows, want):
    """the club whose tactics give formation `want` (a label, a name or a club id)"""
    w = str(want).strip()
    for e in cat:
        if w in (e["label"], e["name"]):
            return e["club"]
    if w.isdigit() and any(c == int(w) for _k, c, _s in rows):
        return int(w)
    raise SystemExit("no formation %r; --list shows them" % want)


def add(rows, forms, clubs):
    """clubs: {new club id: club of the game to copy}. Returns (Tactics rows to append as bytes,
    TacticsFormation rows to append as bytes, {new club: first variant's places})"""
    by_club = collections.defaultdict(list)
    for k, c, s in rows:
        by_club[c].append((k, s))
    have = {c for _k, c, _s in rows}
    nxt = max(max(k for k, _c, _s in rows), max(forms)) + 1
    t, f, shown = bytearray(), bytearray(), {}
    for new, donor in sorted(clubs.items()):
        if new in have:
            raise SystemExit("club %d already has tactics" % new)
        for k, s in by_club[donor]:
            t += struct.pack("<II", nxt, new) + s
            for v, places in enumerate(forms[k]):
                for place, role, depth, width in places:
                    f += struct.pack("<IIBBBB", nxt, role, depth, width, (v << 4) | place, 0)
            shown.setdefault(new, forms[k][0])
            nxt += 1
    return bytes(t), bytes(f), shown


def write(base, out, clubs):
    """append tactics for `clubs` ({new club: donor}) to base's tables, written into out"""
    rows, forms, (th, fh) = read(base)
    t, f, shown = add(rows, forms, clubs)
    for name, hdr, extra in (("Tactics", th, t), ("TacticsFormation", fh, f)):
        raw = open(os.path.join(base, name + ".bin"), "rb").read()
        body = pesdb.wesys_unpack(raw) if raw[3:8] == b"WESYS" else raw
        data = body + extra
        open(os.path.join(out, name + ".bin"), "wb").write(
            pesdb.wesys_pack(data, hdr) if raw[3:8] == b"WESYS" else data)
    return shown


def main():
    a = sys.argv[1:]

    def get(k, d=None):
        return a[a.index(k) + 1] if k in a else d
    base = get("--base")
    if not base:
        raise SystemExit(__doc__)
    rows, forms, _h = read(base)
    cat = catalogue(rows, forms)
    if "--list" in a:
        for e in cat:
            print("%-22s %4d clubs  copies club %-6d %s" % (e["label"], e["clubs"], e["club"],
                                                             " ".join(roles(e["places"]))))
        return
    clubs = {}
    for i, x in enumerate(a):
        if x == "--club":
            c, _e, want = a[i + 1].partition("=")
            clubs[int(c)] = find(cat, rows, want)
    if not clubs or not get("--out"):
        raise SystemExit(__doc__)
    shown = write(base, get("--out"), clubs)
    for c in sorted(shown):
        print("club %d: %s (%s)" % (c, name_of(shown[c]), " ".join(roles(shown[c]))))


if __name__ == "__main__":
    main()
