"""python test_checktwins.py -- checktwins.py, the hard check for the same man twice in a built
world (B421, 11.11.2026: a Reddit report of "many duplicate players" and "top players without
clubs"; NewLife 1.6b4 on FL 2027 had some 230 pairs of a game player without a club beside a new
player who is him under another spelling). Small made-up tables in a temporary folder, no game
needed: a world that added nobody's twin passes; the game's player without a club beside an added
one at his old club fails, under his surname alone too; elsewhere a name cut short fails and a
single word, another nationality, three years or two centimetres apart do not; two added
players who fit one of the game's are nobody's; a legend of the classics is nobody's twin; the
game's player still at a club is a note, not a failure; and who lost his club is counted."""
import contextlib, io, os, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import checktwins as T
import pesdb
import playeredit as E

N = 0
GAME_A, GAME_B, CLASSICS, NATION, NEW = 100, 101, 102, 30, 72000
TEAMS = [(GAME_A, "Game FC", False), (GAME_B, "Other FC", False), (CLASSICS, "Storm Classics", False),
         (NATION, "Freedonia", True), (NEW, "New FC", False)]


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def record(pid, name, pos="CMF", nat=10, age=25, cm=180):
    rec = bytearray(E.P_REC)
    rec[E.P_ID:E.P_ID + 4] = pid.to_bytes(4, "little")
    rec[E.P_NAME:E.P_NAME + 4 * E.P_NAME_LEN] = E.name_slots(name)
    E.setf(rec, "Registered Position", E.POSITIONS.index(pos))
    for f, v in (("Nationality", nat), ("Age", age), ("Height (cm)", cm)):
        E.setf(rec, f, v)
    for n, _b in E.ABILITIES:
        E.setf(rec, n, 80 if (pos == "GK") == n.startswith("GK") else 40)
    return bytes(rec)


def tables(root, name, players):
    """a pesdb folder: players [(pid, name, [teams], {record fields})]"""
    db = os.path.join(root, name, "common", "etc", "pesdb")
    os.makedirs(db)
    open(os.path.join(db, "Player.bin"), "wb").write(
        pesdb.wesys_pack(b"".join(record(p, n, **kw) for p, n, _t, kw in players)))
    rows = [(p, t) for p, _n, ts, _kw in players for t in ts]
    open(os.path.join(db, "PlayerAssignment.bin"), "wb").write(pesdb.wesys_pack(b"".join(
        i.to_bytes(4, "little") + p.to_bytes(4, "little") + t.to_bytes(4, "little") + i.to_bytes(4, "little")
        for i, (p, t) in enumerate(rows))))
    team = bytearray()
    for tid, tname, national in TEAMS:
        rec = bytearray(E.T_REC)
        rec[E.T_ID:E.T_ID + 4] = tid.to_bytes(4, "little")
        rec[E.T_NAME:E.T_NAME + len(tname)] = tname.encode("utf-8")
        if national:
            rec[T.C.T_NATIONAL] |= 0x80
        team += rec
    open(os.path.join(db, "Team.bin"), "wb").write(pesdb.wesys_pack(bytes(team)))
    return os.path.join(root, name)


def run(world, game):
    lines = []
    passed, fails = T.check(world, game, out=lines.append)
    return passed, {(p, a) for p, a in fails}, "\n".join(lines)


def main():
    tmp = tempfile.mkdtemp(prefix="checktwins_")
    try:
        # the game: its players, the clubs they have
        G = [(1, "M. ter Stegen", [GAME_A], dict(pos="GK", age=34, cm=187)),
             (2, "Rafael Monteiro", [GAME_A], dict(pos="GK", age=37, cm=192, nat=11)),
             (3, "Leo Palestina", [GAME_B], dict(age=20, cm=181)),
             (4, "Gabriel Franca", [GAME_B], dict(age=31, cm=180, nat=11)),
             (5, "Ivan Horvat", [GAME_B, NATION], dict(age=28, cm=185, nat=12)),
             (6, "Marko Maric", [GAME_B], dict(age=24, cm=178, nat=12)),
             (7, "Pedro Alves", [GAME_B], dict(age=26, cm=176, nat=11)),
             (8, "Roberto Ayala", [CLASSICS], dict(age=30, cm=177, nat=13)),
             (9, "Luka Stay", [GAME_A], dict(age=27, cm=183, nat=12)),
             (10, "Ante Still", [GAME_B], dict(age=29, cm=188, nat=12)),
             (11, "Josip Juric", [GAME_B], dict(age=22, cm=190, nat=12))]
        game = tables(tmp, "game", G)
        at = lambda rows, **move: [(p, n, move.get("t%d" % p, ts), kw) for p, n, ts, kw in rows]
        new = lambda pid, name, **kw: (pid, name, [NEW], kw)

        clean = tables(tmp, "clean", G + [new(200001, "Nobody Else", nat=12)])
        passed, fails, text = run(clean, game)
        ok("a world that adds nobody's twin passes", passed and not fails and "PASS" in text)

        # the game's players of clubs A and B lose their clubs (the world rewrote those squads),
        # Horvat keeps his national team; Stay and Still keep their clubs
        gone = at(G, t1=[], t2=[], t3=[], t4=[], t5=[NATION], t6=[], t7=[], t11=[])
        W = gone + [
            (200001, "Marc-André ter Stegen", [GAME_A], dict(pos="GK", age=33, cm=187)),      # his old club
            (200002, "Rafael", [GAME_A], dict(pos="GK", age=36, cm=190, nat=11)),               # his old club, one word
            new(200003, "Leonardo Palestina", age=21, cm=181),                                  # elsewhere, a name cut short
            new(200004, "Gabriel", age=30, cm=180, nat=11),                                     # elsewhere, a single word
            new(200005, "Ivan Horvat", age=27, cm=186, nat=12),                                 # the international
            new(200006, "Marko Maric", age=24, cm=178, nat=13),                                 # another nationality
            new(200007, "Pedro Alves", age=29, cm=176, nat=11),                                 # three years apart
            new(200008, "Roberto Ayala", age=30, cm=177, nat=13),                               # a legend's namesake
            new(200009, "Luka Stay", age=27, cm=183, nat=12),                                   # the game's is at his club
            (200010, "Ante Still", [GAME_B], dict(age=29, cm=188, nat=12)),                     # beside the game's
            new(200011, "Josip Juric", age=22, cm=190, nat=12),                                 # two fit one
            (200012, "Josip Juric", [GAME_A], dict(age=23, cm=190, nat=12)),
            new(200013, "FL P00013", age=24, cm=178, nat=12)]
        world = tables(tmp, "world", W)
        passed, fails, text = run(world, game)
        ok("the world with twins fails", not passed and "FAIL, 5 pair(s)" in text)
        ok("at his old club under another spelling: ter Stegen", (1, 200001) in fails)
        ok("at his old club under one word of his name, 2 cm apart: Rafael", (2, 200002) in fails)
        ok("elsewhere with his name cut short: Palestina", (3, 200003) in fails)
        ok("elsewhere under a single word: not enough", not any(p == 4 for p, _a in fails))
        ok("in his national team only and a year, a centimetre apart: Horvat", (5, 200005) in fails)
        ok("another nationality, three years apart: nobody", not any(p in (6, 7) for p, _a in fails))
        ok("a legend of the classics is nobody's twin", not any(p == 8 for p, _a in fails))
        ok("beside the added one in the same squad: Still", (10, 200010) in fails)
        ok("two added players fit one of the game's: neither", not any(p == 11 for p, _a in fails))
        tw, maybe, lost = T.find(T.C.Table(world), T.C.Table(game))
        ok("the game's player at another club: a note, not a failure", maybe == [(9, 200009)])
        ok("who had a club and has none now is counted", sorted(lost) == [1, 2, 3, 4, 5, 6, 7, 11])
        ok("the report names both players and their clubs",
           "Marc-André ter Stegen" in text and "M. ter Stegen" in text and "(no club)" in text and "Game FC" in text)

        with contextlib.redirect_stdout(io.StringIO()):
            ok("the command: 1 for the world with twins, 0 for the clean one",
               T.main([world, game]) == 1 and T.main([clean, game, "--all"]) == 0)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("all %d checks passed" % N)


if __name__ == "__main__":
    main()
