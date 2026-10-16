"""python tools/test_newlife_keep_players.py

B67 (16.10., antoniodias_pt): Joao Cancelo was a free agent in the game while Mod Studio had him
at Barcelona. NewLife 1.4 has 60 players at Barcelona (its B team in it); a squad from the release
is the club's best 30 (Release.squad), and Cancelo was 42nd, so nobody took him -- yet Bring the
game's leagues to this season still took him away from Al Hilal, the club he had.

No game, no NewLife folder: small tables and a small release made here. Checks that:
  - a player the release has at a club but left out of its 30 stays at the club he has (Cancelo
    at Al Hilal), and so does one of the club's own the release left out;
  - the release's squad still comes whole, and no club goes past 40 players (B46);
  - when a club has no room for such a player, he goes as before, and Build's log says so in a
    NOTE that names him, his club and the release's;
  - undoing the refresh takes the note away with the rest.
"""
import csv, json, os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lbplayers as L
import mkworld as W
import pesdb
import playeredit as E

N = 0
BARCA, HILAL, FULL = 100, 200, 300
CANCELO = 2000
CF = L.RATED["CF"]


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def write(d, name, raw):
    with open(os.path.join(d, name), "wb") as f:
        f.write(pesdb.wesys_pack(bytes(raw)))


def tables(d, squads, names, pnames):
    """Player.bin, PlayerAssignment.bin and Team.bin: squads {team: [player id]}"""
    players, assigns, teams = bytearray(), bytearray(), bytearray()
    for tid, pids in squads.items():
        for n, pid in enumerate(pids):
            r = bytearray(L.P_REC)
            r[L.P_ID:L.P_ID + 4] = pid.to_bytes(4, "little")
            nm = pnames[pid].encode("utf-8")
            r[E.P_NAME:E.P_NAME + len(nm)] = nm
            players += r
            a = bytearray(L.A_REC)
            for off, v in ((E.A_PID, pid), (E.A_TID, tid), (E.A_PACK, n << E.ORDER_SHIFT)):
                a[off:off + 4] = v.to_bytes(4, "little")
            assigns += a
    for tid, nm in names.items():
        t = bytearray(W.T_REC)
        t[W.T_ID:W.T_ID + 4] = tid.to_bytes(4, "little")
        t[W.T_NAME:W.T_NAME + len(nm)] = nm.encode("utf-8")
        teams += t
    write(d, "Player.bin", players)
    write(d, "PlayerAssignment.bin", assigns)
    write(d, "Team.bin", teams)


def release(folder, clubs, rows):
    """clubs {id: name} (all of the game), rows [(newlife id, game id or "", name, club, rating)]"""
    os.makedirs(folder)
    with open(os.path.join(folder, "clubs.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["newlife_id", "in_game", "name", "country", "league"])
        for cid, nm in clubs.items():
            w.writerow([cid, 1, nm, "1", "Liga"])
    with open(os.path.join(folder, "players.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["newlife_id", "game_id", "name", "birth_date", "club_id", "Registered Position"] + CF)
        for nid, g, nm, club, o in rows:
            w.writerow([nid, g, nm, "2000-01-01", club, "CF"] + [o] * len(CF))
    json.dump({"name": "NewLife Database", "version": "t67", "format": 1},
              open(os.path.join(folder, "newlife.json"), "w", encoding="utf-8"))


def main():
    tmp = tempfile.mkdtemp(prefix="nl-b67-")
    os.environ["APPDATA"] = tmp                    # the crest cache, if anything is unpacked
    from modstudio import newlife as NL
    try:
        base, rel_dir, out = (os.path.join(tmp, x) for x in ("base", "rel", "out"))
        os.makedirs(base)
        os.makedirs(out)
        game = {BARCA: list(range(1000, 1020)),          # 20
                HILAL: list(range(2000, 2025)),          # 25, Cancelo the first
                FULL: list(range(3000, 3040))}           # 40
        pnames = {p: "Player %d" % p for ps in game.values() for p in ps}
        pnames[CANCELO] = "Joao Cancelo"
        names = {BARCA: "FC Barcelona", HILAL: "Al Hilal", FULL: "Full FC"}
        tables(base, game, names, pnames)
        rows = []
        # Barcelona: 35 in the release. Its best 30: 19 of the game's own and 11 new; left out:
        # Cancelo (from Al Hilal), one of its own (1019) and three new
        rows += [("n%d" % p, p, pnames[p], BARCA, 80) for p in range(1000, 1019)]
        rows += [("b%d" % k, "", "Barca New %s" % chr(65 + k), BARCA, 78) for k in range(11)]
        rows += [("n2000", CANCELO, "Joao Cancelo", BARCA, 68), ("n1019", 1019, pnames[1019], BARCA, 50)]
        rows += [("bb%d" % k, "", "Barca B %s" % chr(65 + k), BARCA, 55) for k in range(3)]
        # Al Hilal: 22 of its own; Cancelo and 2024 are at other clubs, 2023 is in no club of the release
        rows += [("n%d" % p, p, pnames[p], HILAL, 70) for p in range(2001, 2023)]
        # Full FC: its best 30 are 29 of its own and 2024 from Al Hilal; 11 of its own left out,
        # and the club has room for 10 of them (40 at most)
        rows += [("n%d" % p, p, pnames[p], FULL, 75) for p in range(3000, 3029)]
        rows += [("n2024", 2024, pnames[2024], FULL, 74)]
        rows += [("n%d" % p, p, pnames[p], FULL, 60 - (p - 3029)) for p in range(3029, 3040)]
        release(rel_dir, {str(t): nm for t, nm in names.items()}, rows)
        rel = NL.Release(rel_dir)
        info = {"base": base, "national": set()}
        recipe = {"leagues": []}
        n = NL._game_squads(recipe, rel, info, {BARCA: str(BARCA), HILAL: str(HILAL), FULL: str(FULL)})
        pl = recipe["players"]
        removed = {t: set(c.get("remove") or []) for t, c in pl.items()}
        joined = {str(p) for c in pl.values() for p in c.get("join") or []}
        ok("Barcelona's squad from the release is its best 30: Cancelo not in it",
           len(rel.squad(str(BARCA))) == 30 and str(CANCELO) not in joined)
        ok("Cancelo, left out of Barcelona's 30, is not taken away from Al Hilal",
           str(CANCELO) not in removed.get(str(HILAL), set()))
        ok("a club's own player the release left out of its 30 stays too (1019)",
           "1019" not in removed.get(str(BARCA), set()))
        ok("the release's squad still comes: 11 new at Barcelona, 2024 joins Full FC",
           len(pl[str(BARCA)].get("add") or []) == 11 and "2024" in (pl[str(FULL)].get("join") or []))
        ok("a player the release has at no club still leaves, as before (2023)",
           removed.get(str(HILAL), set()) == {"2023"})

        def size(t):
            c = pl.get(str(t)) or {}
            have = [p for p in game[t] if str(p) not in (c.get("remove") or []) and str(p) not in joined]
            return len(have) + len(c.get("join") or []) + len(c.get("add") or [])
        ok("no club past %d players (B46): %s" % (L.CLUB_MAX, {t: size(t) for t in game}),
           all(size(t) <= L.CLUB_MAX for t in game))
        ok("Full FC has room for 10 of the 11 it was left: the best stay, the worst (3039) goes",
           removed.get(str(FULL)) == {"3039"} and size(FULL) == L.CLUB_MAX)
        ok("the one with no room is named for Build's note (player and the release's club)",
           pl[str(FULL)].get("newlife_left") == {"3039": "Full FC"})
        ok("counts: %s" % dict(n), n["kept"] == 12 and n["no_room"] == 1)

        # Build: Cancelo still at Al Hilal, and the note in the log
        log = []
        L.apply({"leagues": [], "players": recipe["players"]}, base, out, 10 ** 6, log=log.append)
        sq = L.Squads(out)
        at = {p: t for t, v in sq.by_club.items() for _o, p, _s, _x in v}
        ok("after Build Cancelo plays for Al Hilal, not a free agent", at.get(CANCELO) == HILAL)
        ok("after Build 1019 is still at Barcelona", at.get(1019) == BARCA)
        ok("after Build no club past %d" % L.CLUB_MAX, all(len(v) <= L.CLUB_MAX for v in sq.by_club.values()))
        note = [x for x in log if "NOTE" in x and "3039" in x]
        ok("Build's log names him, his club and the release's: %s" % (note[:1],),
           len(note) == 1 and "Player 3039" in note[0] and "Full FC" in note[0] and "free agent" in note[0])

        # undo takes the note away with the rest of the refresh
        r = {"leagues": [], "players": json.loads(json.dumps(pl)),
             "newlife_game": {"version": "t67", "swaps": [], "replaced": {}, "clubs": [BARCA, HILAL, FULL]}}
        ok("undo takes back the squads and the note", NL.undo_game_leagues(r) and not r.get("players"))
        print("1..%d" % N)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
