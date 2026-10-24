"""python tools/test_newlife_no_game_id.py <folder with the game's tables>

B102 (David 17.10., JamesNotLike 19.10., Cala79 24.10.): NewLife 1.5b8 gives no game id for some
1100 players the game has. Elliot Anderson, at Manchester City in the release and at Nottingham
Forest in the game, became a new player at City, and the game's Anderson lost his club and was a
free agent beside him: 447 such pairs in one world.

The test makes a release of the game's Premier League, each club's squad the game's own with the
game's ids, and in it:
  - Elliot Anderson at Manchester City and Aaron Wan-Bissaka at Aston Villa, no game id, a year
    younger (the release's season): both are the game's, and come to their clubs;
  - a namesake with another first name, one with the same name four years older, one the release
    has at two clubs, one whose name a row with the game's id has already: all new players.
Both ways in: Bring the game's leagues (_game_squads) and a NewLife league's mover (add_league).
"""
import csv, json, os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import leaguebuilder as B
import lbplayers as P

N = 0
CITY, FOREST, WEST_HAM, VILLA = 173, 389, 105, 107
ANDERSON, WAN_BISSAKA = 140816, 114876
GUNN = SELS = None                                  # the game's, release() finds them


def ok(cond, what):
    global N
    assert cond, what
    N += 1
    print("ok %d - %s" % (N, what))


def by_name(db, t, name):
    return next(p for _o, p, _s, _x in db.by_club[t] if db.name(p) == name)


def release(folder, base):
    """the game's Premier League as a release, with the rows the test is about"""
    global GUNN, SELS
    db = P.Squads(base)
    GUNN, SELS = by_name(db, FOREST, "Angus Gunn"), by_name(db, FOREST, "Matz Sels")
    clubs = next(ts for _r, _c, _n, ts in B.game_leagues(base) if CITY in ts)
    milenkovic = by_name(db, FOREST, "Nikola Milenković")
    gunn, twice = GUNN, SELS
    dias = by_name(db, CITY, "Rúben Dias")
    left_out = {ANDERSON, WAN_BISSAKA, gunn, twice}      # the game's rows the release has not got
    special = []                                         # (club, name, the game's player, age change)
    special += [(CITY, "Elliot Anderson", ANDERSON, -1), (VILLA, "Aaron Wan-Bissaka", WAN_BISSAKA, -1),
                (CITY, "Marko Milenković", milenkovic, 0), (CITY, "Angus Gunn", gunn, 4),
                (CITY, "Matz Sels", twice, 0), (VILLA, "Matz Sels", twice, 0), (VILLA, "Rúben Dias", dias, 0)]
    os.makedirs(folder)
    with open(os.path.join(folder, "clubs.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["newlife_id", "in_game", "name", "country", "league", "home_kit", "away_kit"])
        for t in sorted(clubs):
            w.writerow([t, 1, "club %d" % t, "204", "English Premier Division", "plain #ffffff #000000 #000000", ""])
    with open(os.path.join(folder, "players.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["newlife_id", "game_id", "name", "birth_date", "club_id"] + list(P.FIELDS))
        for t in sorted(clubs):
            for _o, pid, _s, _x in db.by_club.get(t, []):
                if pid in db.index and pid not in left_out:
                    r = db.row(pid)
                    w.writerow([pid, pid, r["name"], "", t] + [r[k] for k in P.FIELDS])
        for k, (t, name, pid, older) in enumerate(special):
            r = db.row(pid)
            r["Age"] = str(int(r["Age"]) + older)
            w.writerow([900000 + k, "", name, "", t] + [r[f] for f in P.FIELDS])
    json.dump({"name": "NewLife Database", "version": "t102", "format": 1},
              open(os.path.join(folder, "newlife.json"), "w", encoding="utf-8"))


def main(base):
    tmp = tempfile.mkdtemp(prefix="nl-b102-")
    os.environ["APPDATA"] = tmp
    from modstudio import newlife as NL
    try:
        info = B.game_info(base)
        release(os.path.join(tmp, "rel"), base)
        rel = NL.Release(os.path.join(tmp, "rel"))
        rel.use_tables(info)
        db = P.Squads(base)
        twin = NL.game_twin(rel, db)
        row = lambda t, name: [r for r in rel.squads[str(t)] if r["name"] == name and not r["game_id"]]
        ok(twin(row(CITY, "Elliot Anderson")[0]) == str(ANDERSON),
           "Elliot Anderson, no game id, a year younger: the game's Anderson")
        ok(twin(row(VILLA, "Aaron Wan-Bissaka")[0]) == str(WAN_BISSAKA), "and Wan-Bissaka the game's")
        ok(twin(row(CITY, "Marko Milenković")[0]) == "", "another first name: not the game's Milenković")
        ok(twin(row(CITY, "Angus Gunn")[0]) == "", "four years older: not the game's Gunn")
        ok(twin(row(CITY, "Matz Sels")[0]) == twin(row(VILLA, "Matz Sels")[0]) == "",
           "a name the release has at two clubs: neither is the game's")
        ok(twin(row(VILLA, "Rúben Dias")[0]) == "", "the game's player a row names by his id already: nobody else's")
        ok(NL.game_twin(rel, P.Squads(base)) is twin, "read once for the same release and tables")

        recipe = {"leagues": []}
        n = NL._game_squads(recipe, rel, info, {t: str(t) for t in (CITY, FOREST, WEST_HAM, VILLA)})
        pl = recipe["players"]
        adds = [a["name"] for c in pl.values() for a in c.get("add") or []]
        ok(str(ANDERSON) in pl[str(CITY)].get("join", []) and "Elliot Anderson" not in adds,
           "Bring: the game's Anderson joins City, no second Anderson made")
        ok(str(WAN_BISSAKA) in pl[str(VILLA)].get("join", []) and "Aaron Wan-Bissaka" not in adds,
           "Bring: the game's Wan-Bissaka joins Villa")
        ok(not any(str(ANDERSON) in c.get("remove", []) for c in pl.values()),
           "and Anderson is let go by nobody: he is signed")
        joined = {g for c in pl.values() for g in c.get("join") or []}
        ok("Marko Milenković" in adds and "Rúben Dias" in adds and str(GUNN) not in joined and
           str(SELS) not in joined, "the others are new players, as before (Gunn too, if he made the squad)")

        mover, _db = NL._movers({"players": {}}, info, rel)
        ok(mover(row(CITY, "Elliot Anderson")[0])[:2] == ("move", str(ANDERSON)),
           "a NewLife league: Anderson moves to his club")
        ok(mover(row(CITY, "Marko Milenković")[0])[:2] == ("copy", None), "and the namesake is copied")
        print("counts", dict(n))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("1..%d" % N)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1])
