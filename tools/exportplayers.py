r"""python exportplayers.py <world or tables folder> out.csv [--base <game tables folder>]

Every player of a world, with his club, in one CSV a spreadsheet opens (UTF-8 with BOM, comma
separated, so Excel keeps the accents): the game's players and the world's new ones, at every
club -- the game's own clubs too -- and the players in no club at all, marked as free agents.
For support and for players who want to check a world (which id a player has now, where he went).

<world or tables folder> is a world folder (livecpk\_FL26...: its tables are in common\etc\pesdb,
a world built here or one from a zip, Modpack, Europack), or a folder with the tables themselves
(Player.bin, PlayerAssignment.bin, Team.bin, Competition*.bin), the game's unpacked tables too.
A table the world does not bring is read from the game's tables (--base; else FL26_PESDB, else
the tables Mod Studio unpacked), as the game itself does: Country.bin, the country names, is
always the game's.

Columns: player_id, name, shirt_name, club_id, club, league, club_country, nationality, age,
height, position, rating, source.  league is the club's league in the world's competition tables
(empty for a club in no league); rating is the overall rating Mod Studio shows (lbrating.py);
source is "new" for a player the world made (an id its fl26playerids.json gives, or one the
game's tables do not have) and "game" for the game's own. A free agent has no club_id and
"Free agent" for his club. A player of a national team is listed at his club: national teams are
not clubs here.

Mod Studio: Players > More > Export all players (CSV)..., and My world > More.
"""
import csv, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pesdb
import playeredit as E
import lbplayers as LP
from lbrating import FIELDS as RATING_FIELDS, rating

COLUMNS = ["player_id", "name", "shirt_name", "club_id", "club", "league", "club_country",
           "nationality", "age", "height", "position", "rating", "source"]
FREE = "Free agent"
PESDB = ("common", "etc", "pesdb")
NEEDED = ("Player.bin", "PlayerAssignment.bin", "Team.bin")
COMPETITION = ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin")


class Error(Exception):
    pass


def tables_of(path):
    """the folder with the tables of <path>: a world's common\\etc\\pesdb, or <path> itself"""
    for sub in (PESDB, ("etc", "pesdb"), ("pesdb",), ()):
        d = os.path.join(path, *sub)
        if os.path.isfile(os.path.join(d, "Player.bin")):
            return d
    raise Error("no Player.bin in %s or its common\\etc\\pesdb" % path)


def world_root(db):
    """the world folder of a world's tables folder (...\\_FL26X\\common\\etc\\pesdb), else db"""
    parts = os.path.normpath(db).split(os.sep)
    if [p.lower() for p in parts[-3:]] == list(PESDB):
        return os.sep.join(parts[:-3])
    return db


def default_base():
    """the game's unpacked tables: FL26_PESDB, else the ones Mod Studio unpacked; None"""
    import fl26world
    app = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "FL26ModStudio", "tables")
    for d in [p for p in os.environ.get("FL26_PESDB", "").split(os.pathsep) if p] + \
            [os.path.join(app, *PESDB), app]:
        if os.path.isfile(os.path.join(d, "Player.bin")):
            try:
                return fl26world.base_dir(d)
            except SystemExit:
                continue
    return None


def _has(d, names):
    return bool(d) and all(os.path.isfile(os.path.join(d, n)) for n in names)


def world_ids(db):
    """the player ids the world's last Build gave its own players (fl26playerids.json, in the
    world folder or beside the tables); None without the file"""
    for d in (world_root(db), db):
        p = os.path.join(d, "fl26playerids.json")
        try:
            with open(p, encoding="utf-8") as f:
                got = json.load(f)
        except (OSError, ValueError):
            continue
        ids = set()
        for club in (got.get("clubs") or {}).values() if isinstance(got, dict) else ():
            for v in (club or {}).values():
                if isinstance(v, int):
                    ids.add(v)
        return ids
    return None


def club_leagues(d):
    """{team id: league name} from the competition tables at d: a club in a league and in a
    pre-season cup (a league in the tables too) gets the league"""
    import leaguebuilder as B
    codes = {c["id"]: c["code"] for c in pesdb.comp_rows(pesdb.load("Competition", d))}
    out = {}
    for _rid, cid, name, teams in B.game_leagues(d):
        real = codes.get(cid, "").endswith("_LEAGUE")
        for t in teams:
            if t not in out or (real and not out[t][0]):
                out[t] = (real, name)
    return {t: n for t, (_r, n) in out.items()}


def countries(d):
    """{Country.bin id: name} as the Players page lists them, {} without Country.bin"""
    if not _has(d, ("Country.bin",)):
        return {}
    import leaguebuilder as B
    return {fid: name for name, fid in B.country_ids(d)}


def collect(path, base=None, free=FREE, progress=None):
    """(rows, info) for the world or tables at path; rows in COLUMNS order, info: {db, base,
    players, free, new, seconds}"""
    say = progress or (lambda t: None)
    t0 = time.time()
    db = tables_of(path)
    base = base if base is not None else default_base()
    same = bool(base) and os.path.normcase(os.path.abspath(base)) == os.path.normcase(os.path.abspath(db))
    for n in NEEDED:
        if not os.path.isfile(os.path.join(db, n)):
            raise Error("no %s in %s" % (n, db))
    say("reading the players")
    sq = LP.Squads(db)
    teams = LP.teams(db)
    from leaguebuilder import game_clubs
    names = {t: n for t, (n, _a) in game_clubs(db).items()}
    comp_dir = db if _has(db, COMPETITION) else (base if _has(base, COMPETITION) else None)
    leagues = club_leagues(comp_dir) if comp_dir else {}
    cty = countries(db) or countries(base)
    new_ids = world_ids(db) if not same else None
    game_ids = None
    if same:
        game_ids = set(sq.index)
    elif _has(base, ("Player.bin",)):
        raw = pesdb.load("Player", base)
        game_ids = {int.from_bytes(raw[o + E.P_ID:o + E.P_ID + 4], "little") for o in range(0, len(raw), E.P_REC)}

    def source(pid):
        if new_ids is not None and pid in new_ids:
            return "new"
        if game_ids is None:
            return "" if new_ids is None else "game"
        return "game" if pid in game_ids else "new"

    say("writing the rows")
    club_of = {}
    for tid, v in sq.by_club.items():
        if teams.get(tid, (False, 0))[0]:
            continue                                  # a national team calls him up, it is no club
        for order, pid, _shirt, _o in v:
            club_of.setdefault(pid, (tid, order))
    want = {"Registered Position", "Age", "Height (cm)", "Nationality"}
    want |= set(RATING_FIELDS)
    fields = [(n,) + E.FIELDS[n] for n in sorted(want)]
    rows = []
    P = sq.players
    for pid, o in sq.index.items():
        v = int.from_bytes(P[o:o + E.P_REC], "little")
        r = {n: (v >> b & ((1 << w) - 1)) + add for n, b, w, add in fields}
        r["Registered Position"] = E.show("Registered Position", r["Registered Position"])
        name = E.cstr(P[o + E.P_NAME:o + E.P_NAME + E.P_NAME_LEN]).strip()
        shirt = E.cstr(P[o + E.P_NAME + E.P_NAME_LEN:o + E.P_NAME + 2 * E.P_NAME_LEN]).strip()
        tid, order = club_of.get(pid, (None, 0))
        if tid is None:
            club = ["", free, "", ""]                  # club_id, club, league, club_country
        else:
            c = teams.get(tid, (False, None))[1]
            club = [tid, names.get(tid, "").strip(), leagues.get(tid, ""), "" if c is None else cty.get(c, str(c))]
        nat = r["Nationality"]
        # the clubs by league, then the clubs in no league, then the free agents
        rows.append(((tid is None, not club[2], club[2].lower(), club[1].lower(), tid or 0, order, pid),
                     [pid, name, shirt] + club +
                     [cty.get(nat, str(nat)), r["Age"], r["Height (cm)"], r["Registered Position"],
                      rating(r), source(pid)]))
    rows.sort(key=lambda x: x[0])
    rows = [r for _k, r in rows]
    info = {"db": db, "base": base, "players": len(rows),
            "free": sum(1 for r in rows if r[3] == ""), "new": sum(1 for r in rows if r[-1] == "new"),
            "seconds": round(time.time() - t0, 1)}
    return rows, info


def write(rows, out):
    """rows to out as CSV, UTF-8 with BOM (Excel then reads the accents right); via a temp file,
    so a file open in Excel stops it before anything is half written"""
    tmp = out + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        w.writerows(rows)
    os.replace(tmp, out)


def export(path, out, base=None, free=FREE, progress=None):
    """write every player of the world or tables at path to out; returns collect's info"""
    rows, info = collect(path, base, free, progress)
    write(rows, out)
    info["out"] = out
    return info


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = list(sys.argv[1:] if argv is None else argv)
    base = None
    if "--base" in a:
        i = a.index("--base")
        base = a[i + 1]
        del a[i:i + 2]
    if len(a) != 2:
        print(__doc__)
        return 2
    try:
        info = export(a[0], a[1], base=base)
    except (Error, OSError, ValueError) as e:
        print("exportplayers: %s" % e, file=sys.stderr)
        return 1
    print("wrote %d players (%d free agents, %d new) to %s in %.1f s"
          % (info["players"], info["free"], info["new"], info["out"], info["seconds"]))
    print("tables: %s" % info["db"])
    print("game's tables: %s" % (info["base"] or "none found (source is from fl26playerids.json only)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
