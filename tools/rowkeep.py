r"""rowkeep.py -- an Update of a world keeps the competition rows of the version before it.

mato 18.11.2026: an Update of a world must never break a career saved on the version before it.
New leagues, cups and clubs are fine; they only have to work in a new Master League.

A career holds the world's competitions by their rows. A world's next version had one league more,
and Build put it in the middle of the three competition tables (mkleague.add_league appends the
leagues in the plan's order, and the plan's order is not the recipe's): every row of
Competition.bin and CompetitionRegulation.bin after it moved down by one, and 3792 of 9698
CompetitionEntry ids (+4, numbered by row: mkleague.add_league, max + 1) got another club. A
career of the version before crashed after the Update (FL_2027+0x1333485, a cup tie with no club,
04.07.); with that league taken out again it went on (check_update_ids.py says which).

So a Build that follows a version shared before (its id ledger, idledger.find) lays the three
tables out as that version had them (keep):

  Competition.bin            every row of the version before at its index (by competition id),
  CompetitionRegulation.bin  ... by regulation id,
  CompetitionEntry.bin       ... by the competition and club, with its entry id and position:
                             the same entry id is the same club, competition and place (Build
                             orders a league's clubs by name: a renamed club keeps its place);
  then the rows the version before did not have, in the order Build made them, and new entry ids
  above the version before's highest.

What keep cannot keep is reported, not hidden (report_of):
  - careers of the version before do NOT go on (ok False: the export's "careers", Install offers
    Replace) when a row of it is gone (a career holds the entry id: the beta 3 career's crash was a
    cup tie whose entry id held no club of it), when an entry id of it holds another club, or when
    a club new to the world is entered in a competition it had (a career of it has none of the
    club's players: the 356 new players of beta 4 were not in the career after the load, so the
    club plays with an empty squad -- check_update_ids.py);
  - a warning only, as idledger.structure_changes is (a running season of it laid out the old way
    "may not go right"; Install's changed_text): a row of it whose bytes changed (legs, the link to
    the league below...) and a new place in a competition it had for a club the world had.
A club new to the world only in new competitions is listed (new_clubs_new): a career of the
version before does not play those competitions, they come only in a new Master League.

The rows of a version (rows_of) go into its id ledger at the export (idledger.ROWS_KEY): the
competition and regulation ids in row order with a crc of each row, and every entry whole. A
ledger of before 18.11.2026 has none; Build then reads the rows from that version's zip (the
recipe's "id_tables") or from the world in the game when it came from that zip (prev_tables).

    python tools/rowkeep.py rows <world zip or world folder>
    python tools/rowkeep.py check <prev: zip, world folder or ledger> <new: zip or world folder>
"""
import json, os, struct, sys, zipfile, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import pesdb                                    # noqa: E402

COMP, REG, ENT = 36, 2352, 12
TABLES = ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin")
TEAM = "Team.bin"
T_REC, T_ID = 1532, 8                           # playeredit.T_REC, T_ID
PESDB = "common/etc/pesdb/"
KINDS = ("competitions", "regulations", "entries")
FORMAT = 1


class RowsError(Exception):
    """rows that cannot be read, or tables of another version than the one Build follows"""


# ---- one row's key ----

def comp_cid(r):
    return r[5] | r[7] << 8                    # mkleague.comp_cid: +0x05, high byte +0x07


def reg_id(r):
    return r[2] | r[3] << 8                    # mkleague.R_ID


def reg_cid(r):
    return r[8] | r[0x910] << 8                # mkleague.reg_cid


def ent_fields(r):
    """[entry id, club, competition id, position, flag] of a CompetitionEntry row: its 12 bytes"""
    return [struct.unpack_from("<I", r, 4)[0], struct.unpack_from("<I", r, 0)[0],
            r[8] | r[11] << 8, r[9], r[10]]


def ent_row(f):
    """the 12 bytes of an entry [entry id, club, competition id, position, flag]"""
    e = bytearray(ENT)
    struct.pack_into("<I", e, 0, f[1])
    struct.pack_into("<I", e, 4, f[0])
    e[8], e[9], e[10], e[11] = f[2] & 0xff, f[3], f[4], f[2] >> 8
    return e


def _split(raw, size):
    return [bytes(raw[i:i + size]) for i in range(0, len(raw) - len(raw) % size, size)]


def crc(b):
    return zlib.crc32(bytes(b)) & 0xffffffff


# ---- the rows of a version ----

def rows_of(comp, regs, ents):
    """the rows of a world's three competition tables (raw, unpacked), as a ledger keeps them:
    {"format", "competitions": [[cid, crc]], "regulations": [[rid, cid, crc]], "entries": [[entry
    id, club, cid, position, flag]]}, in row order"""
    return {"format": FORMAT,
            "competitions": [[comp_cid(r), crc(r)] for r in _split(comp, COMP)],
            "regulations": [[reg_id(r), reg_cid(r), crc(r)] for r in _split(regs, REG)],
            "entries": [ent_fields(r) for r in _split(ents, ENT)]}


def valid(rows):
    """whether `rows` is a whole rows_of (a ledger's, read from a file)"""
    if not isinstance(rows, dict):
        return False
    try:
        return (all(len(x) == 2 and all(isinstance(v, int) for v in x) for x in rows["competitions"])
                and all(len(x) == 3 and all(isinstance(v, int) for v in x) for x in rows["regulations"])
                and all(len(x) == 5 and all(isinstance(v, int) for v in x) for x in rows["entries"]))
    except (KeyError, TypeError):
        return False


def _unpack(d):
    return pesdb.wesys_unpack(d) if d[3:8] == b"WESYS" else d


def tables_dir(db, names=TABLES):
    """{name: raw table} of a pesdb folder; RowsError when one of them is not there"""
    out = {}
    for n in names:
        p = os.path.join(db, n)
        try:
            with open(p, "rb") as f:
                out[n] = _unpack(f.read())
        except (OSError, AssertionError) as e:
            raise RowsError("%s cannot be read: %s" % (p, e))
    return out


def world_db(root):
    return os.path.join(root, "common", "etc", "pesdb")


def tables_zip(path, names=TABLES):
    """({name: raw table}, the zip's id ledger or None) of a world zip (export_world's layout)"""
    out, led = {}, None
    try:
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                m = n.replace("\\", "/")
                base = m.rsplit("/", 1)[-1]
                if ("/" + m).lower().endswith("/" + PESDB.lower() + base.lower()) and base in names and base not in out:
                    out[base] = _unpack(z.read(n))
                elif base == "fl26ids-ledger.json" and led is None:
                    led = json.loads(z.read(n).decode("utf-8"))
    except (OSError, zipfile.BadZipFile, ValueError, AssertionError) as e:
        raise RowsError("%s cannot be read: %s" % (path, e))
    missing = [n for n in names if n not in out]
    if missing:
        raise RowsError("%s has no %s" % (path, ", ".join(missing)))
    return out, led


def rows_of_tables(t):
    return rows_of(t[TABLES[0]], t[TABLES[1]], t[TABLES[2]])


def rows_of_world(root):
    """rows_of the world built in folder `root`; None when it has no competition tables"""
    try:
        return rows_of_tables(tables_dir(world_db(root)))
    except RowsError:
        return None


def team_ids(raw):
    return {struct.unpack_from("<I", raw, i + T_ID)[0] for i in range(0, len(raw) - len(raw) % T_REC, T_REC)}


# ---- the rows of the version a Build follows ----

LEDGER = "fl26ids-ledger.json"                  # idledger.LEDGER
ROWS_KEY = "rows"                               # idledger.ROWS_KEY


def same_version(a, b):
    """two ledgers of one version: the same lineage, number and ids (digest)"""
    if not isinstance(a, dict) or not isinstance(b, dict):
        return False
    try:
        return (a.get("lineage") == b.get("lineage") and int(a.get("number") or 0) == int(b.get("number") or 0)
                and a.get("digest") == b.get("digest"))
    except (TypeError, ValueError):
        return False


def _version(led):
    return "%s (number %s)" % ((led or {}).get("version"), (led or {}).get("number"))


def prev_rows(led, tables=None, world=None, notes=None):
    """(rows, club ids, where) of the version whose id ledger `led` a Build follows, or (None, None,
    None) when Build cannot tell them:
      - the ledger's own "rows" (an export of 18.11.2026 evening and later);
      - else `tables`, the recipe's id_tables: that version's world zip, or a world folder of it --
        its own ledger must be `led` (same_version), else RowsError: the order of another version
        would be kept;
      - else `world`, the world in the game, when it is that version installed from its zip (its
        fl26ids-ledger.json is `led`: a Build on this PC takes that file out, leaguebuilder.keep_added).
    notes: a list that gets a line for a place looked at and left out"""
    notes = notes if notes is not None else []
    if valid((led or {}).get(ROWS_KEY)):
        return led[ROWS_KEY], None, "its id ledger"
    for path, named in ((tables, True), (world, False)):
        if not path:
            continue
        try:
            if os.path.isdir(path):
                lp = os.path.join(path, LEDGER)
                if not os.path.isfile(lp):
                    if named:
                        raise RowsError("%s has no %s: it is not a world from a zip of %s" % (path, LEDGER, _version(led)))
                    continue
                with open(lp, encoding="utf-8") as f:
                    theirs = json.load(f)
                t = tables_dir(world_db(path), TABLES + (TEAM,))
            elif named:
                t, theirs = tables_zip(path, TABLES + (TEAM,))
            else:
                continue
        except (OSError, ValueError) as e:
            if named:
                raise RowsError("%s cannot be read: %s" % (path, e))
            notes.append("rows: %s is left out: %s" % (path, e))
            continue
        except RowsError as e:
            if named:
                raise
            notes.append("rows: %s is left out: %s" % (path, e))
            continue
        if not same_version(theirs, led):
            text = "%s is %s, not %s, the version this Build follows" % (path, _version(theirs) if theirs else
                                                                          "a world without an id ledger", _version(led))
            if named:
                raise RowsError(text + ": its rows would be kept for the wrong version")
            notes.append("rows: " + text + ": left out")
            continue
        return rows_of_tables(t), team_ids(t[TEAM]), path
    return None, None, None


# ---- keep ----

def _take(pos, key):
    q = pos.get(key)
    return q.pop(0) if q else None


def keep(prev, comp, regs, ents, known_teams=None):
    """(comp, regs, ents, report): the three tables (raw) laid out as the version before had them
    (prev: rows_of it). Every row of prev at its index, by key (competition id, regulation id; an
    entry by its competition and club, else by its competition: another club in that place); the
    entry there gets prev's entry id and position; the other rows after them, in the order they are
    in, their entry ids above prev's highest (a new place in a competition of prev: after its places). known_teams: the club ids
    the version before had (its Team.bin, or the clubs of its ledger and the game's); the clubs of
    prev's entries count too. report: see report_of"""
    rep = {"gone": {k: [] for k in KINDS}, "changed": {"competitions": [], "regulations": []},
           "other_club": [], "new_competitions": [], "new_regulations": [], "new_places": [],
           "new_clubs_old": [], "new_clubs_new": [], "back": {k: 0 for k in KINDS}}
    out = []
    # competitions and regulations: by their id
    for kind, raw, size, key, pk in (("competitions", comp, COMP, comp_cid, 0), ("regulations", regs, REG, reg_id, 0)):
        rows = _split(raw, size)
        pos = {}
        for i, r in enumerate(rows):
            pos.setdefault(key(r), []).append(i)
        used, laid = set(), []
        for p in prev[kind]:
            i = _take(pos, p[pk])
            if i is None:
                rep["gone"][kind].append(p[pk])
                continue
            if i != len(laid):
                rep["back"][kind] += 1
            used.add(i)
            laid.append(rows[i])
            if crc(rows[i]) != p[-1]:
                rep["changed"][kind].append(p[pk])
        new = [rows[i] for i in range(len(rows)) if i not in used]
        rep["new_" + kind] = [key(r) for r in new]
        out.append(b"".join(laid + new))
    # entries: a club prev had in a competition keeps prev's entry there (its entry id and place:
    # Build orders a league's entries by the clubs' names, so a renamed club would move); a place
    # of prev whose club is not in it now goes to a club of the competition prev did not have there
    # (another club: other_club); what is left is new, after prev's places and entry ids
    rows = [ent_fields(r) for r in _split(ents, ENT)]
    by_club, free = {}, {}
    for i, f in enumerate(rows):
        by_club.setdefault((f[2], f[1]), []).append(i)
    slot = [None] * len(prev["entries"])                 # prev's entry k -> the row laid there
    for k, p in enumerate(prev["entries"]):
        i = _take(by_club, (p[2], p[1]))
        if i is not None:
            slot[k] = i
    used = {i for i in slot if i is not None}
    for i, f in enumerate(rows):
        if i not in used:
            free.setdefault(f[2], []).append(i)
    laid = []
    for k, p in enumerate(prev["entries"]):
        i = slot[k]
        if i is None:
            i = _take(free, p[2])
            if i is None:
                rep["gone"]["entries"].append(p[0])
                continue
            used.add(i)
            rep["other_club"].append(p[0])
        if i != len(laid) or rows[i][0] != p[0] or rows[i][3] != p[3]:
            rep["back"]["entries"] += 1
        f = list(rows[i])
        f[0], f[3] = p[0], p[3]
        laid.append(ent_row(f))
    top = max([p[0] for p in prev["entries"]] or [0])
    old_cids = {p[0] for p in prev["competitions"]} | {p[2] for p in prev["entries"]}
    known = set(known_teams or ()) | {p[1] for p in prev["entries"]}
    last = {}                                             # the highest place of prev in a competition
    for p in prev["entries"]:
        last[p[2]] = max(last.get(p[2], 0), p[3])
    new = []
    for i in range(len(rows)):
        if i in used:
            continue
        f = list(rows[i])
        top += 1
        if f[0] != top:
            rep["back"]["entries"] += 1
        f[0] = top
        if f[2] in last:                                  # a new place after prev's in its competition
            last[f[2]] += 1
            f[3] = last[f[2]]
        new.append(ent_row(f))
        if f[2] in old_cids:
            rep["new_places"].append((f[2], f[3], f[1]))
            if f[1] not in known:
                rep["new_clubs_old"].append(f[1])
        elif f[1] not in known:
            rep["new_clubs_new"].append(f[1])
    out.append(b"".join(laid + new))
    for k in ("new_clubs_old", "new_clubs_new"):
        rep[k] = sorted(set(rep[k]))
    rep["new_clubs_new"] = [t for t in rep["new_clubs_new"] if t not in set(rep["new_clubs_old"])]
    return out[0], out[1], out[2], report_of(rep)


def report_of(rep):
    """the report with its verdict: "ok" -- careers of the version before go on: no row of it gone,
    no entry id of it with another club, no club new to the world in a competition it had. Rows of it
    changed in place and new places of known clubs are warnings ("warn"), as structure_changes is"""
    rep["ok"] = not (any(rep["gone"].values()) or rep["other_club"] or rep["new_clubs_old"])
    rep["warn"] = bool(any(rep["changed"].values()) or rep["new_places"])
    return rep


def check(prev, comp, regs, ents, known_teams=None):
    """keep's report of tables already built, and "moved": {kind: how many rows of prev are not at
    their index (or, an entry, not under its entry id)}. ok only when none moved either"""
    c2, r2, e2, rep = keep(prev, comp, regs, ents, known_teams)
    moved = {}
    for kind, raw, size, key in (("competitions", comp, COMP, comp_cid), ("regulations", regs, REG, reg_id)):
        rows = _split(raw, size)
        moved[kind] = sum(1 for i, p in enumerate(prev[kind]) if i >= len(rows) or key(rows[i]) != p[0])
    rows = [ent_fields(r) for r in _split(ents, ENT)]
    moved["entries"] = sum(1 for i, p in enumerate(prev["entries"])
                           if i >= len(rows) or rows[i][0] != p[0] or rows[i][2:4] != p[2:4])
    rep["moved"] = moved
    rep["ok"] = rep["ok"] and not any(moved.values())
    return rep


def summary(rep):
    """the report in numbers, for a plan, a ledger's "careers" and a log: {"ok", "gone": {kind: n},
    "changed": {kind: n}, "other_club", "new_places", "new_clubs_old", "new_clubs_new",
    "new_competitions", "moved" (check only)}"""
    out = {"ok": rep["ok"], "warn": rep.get("warn", False), "gone": {k: len(v) for k, v in rep["gone"].items() if v},
           "changed": {k: len(v) for k, v in rep["changed"].items() if v},
           "other_club": len(rep["other_club"]), "new_places": len(rep["new_places"]),
           "new_clubs_old": len(rep["new_clubs_old"]), "new_clubs_new": len(rep["new_clubs_new"]),
           "new_competitions": len(rep["new_competitions"])}
    if "moved" in rep:
        out["moved"] = {k: n for k, n in rep["moved"].items() if n}
    return out


def _ids(xs, n=12):
    xs = list(xs)
    return " ".join(map(str, xs[:n])) + (" ..." if len(xs) > n else "")


def lines(rep, version):
    """what the report says, a line each (Build's log, the export's)"""
    v = version or "the version before"
    out = []
    for kind in KINDS:
        if rep["gone"][kind]:
            out.append("%d %s of %s are gone (%s): careers of it do not go on" % (
                len(rep["gone"][kind]), kind, v, _ids(rep["gone"][kind])))
    for kind in ("competitions", "regulations"):
        if rep["changed"][kind]:
            out.append("%d %s of %s are not as they were (%s): a season of them running in a career of it was "
                       "laid out the old way and may not go right (not checked in the game)"
                       % (len(rep["changed"][kind]), kind, v, _ids(rep["changed"][kind])))
    if rep["other_club"]:
        out.append("%d entry ids of %s hold another club now (%s): careers of it do not go on" % (
            len(rep["other_club"]), v, _ids(rep["other_club"])))
    if rep["new_places"]:
        cids = sorted({c for c, _o, _t in rep["new_places"]})
        known = len(rep["new_places"]) - sum(1 for _c, _o, t in rep["new_places"] if t in set(rep["new_clubs_old"]))
        out.append("%d new places in %d competitions %s has (%s)%s" % (
            len(rep["new_places"]), len(cids), v, _ids(cids),
            ": %d clubs new to the world (%s), a career of it has none of their players, so careers of it do not go "
            "on" % (len(rep["new_clubs_old"]), _ids(rep["new_clubs_old"])) if rep["new_clubs_old"] else
            ": a season of them running in a career of it may not go right (not checked in the game)"))
        if rep["new_clubs_old"] and known:
            out.append("... %d of those places for clubs the world had" % known)
    if rep["new_clubs_new"]:
        out.append("%d clubs new to the world play only in competitions %s does not have (%s): a career of it has "
                   "none of their players" % (len(rep["new_clubs_new"]), v, _ids(rep["new_clubs_new"])))
    if rep.get("moved") and any(rep["moved"].values()):
        out.append("rows of %s not where they were: %s" % (v, ", ".join("%d %s" % (n, k) for k, n in rep["moved"].items() if n)))
    return out


# ---- the command line ----

def _rows_any(path):
    """(rows, team ids) of a zip, a world folder or a ledger file (rows only, no team ids)"""
    if os.path.isdir(path):
        t = tables_dir(world_db(path), TABLES + (TEAM,))
        return rows_of_tables(t), team_ids(t[TEAM])
    if zipfile.is_zipfile(path):
        t, _led = tables_zip(path, TABLES + (TEAM,))
        return rows_of_tables(t), team_ids(t[TEAM])
    with open(path, encoding="utf-8") as f:
        led = json.load(f)
    if not valid(led.get("rows")):
        raise RowsError("%s has no rows (a ledger of before 18.11.2026)" % path)
    return led["rows"], set()


def main(argv):
    if len(argv) >= 2 and argv[0] == "rows":
        rows, teams = _rows_any(argv[1])
        print("%s: %d competitions, %d regulations, %d entries (top entry id %d), %d clubs" % (
            argv[1], len(rows["competitions"]), len(rows["regulations"]), len(rows["entries"]),
            max([e[0] for e in rows["entries"]] or [0]), len(teams)))
        return 0
    if len(argv) >= 3 and argv[0] == "check":
        prev, teams = _rows_any(argv[1])
        if os.path.isdir(argv[2]):
            t = tables_dir(world_db(argv[2]))
        else:
            t, _led = tables_zip(argv[2])
        rep = check(prev, t[TABLES[0]], t[TABLES[1]], t[TABLES[2]], teams)
        for line in lines(rep, os.path.basename(argv[1])):
            print(line)
        print(json.dumps(summary(rep)))
        print("careers go on" if rep["ok"] else "careers do not go on")
        return 0 if rep["ok"] else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
