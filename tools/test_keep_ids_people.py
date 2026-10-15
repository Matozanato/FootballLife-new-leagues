"""python tools/test_keep_ids_people.py

A rebuilt world keeps each of its own players' ids with the player, not with his place in the
squad (lbplayers._keep_ids, 0.2.4). NewLife 1.5b4 took a doubled player out of a squad (B52):
everybody after him moved one place up, and the last Build's ids went with the places to other
people -- in the Modpack r7 against r6, 1396 players kept their name and club but took another
id, and 1826 ids of the world were somebody else's (15.10.2026). An old career showed them as
the wrong players.

World A is built, then the same recipe with the doubled player taken out, with the ids file of
A: every other player keeps his id of A, and the id of the one taken out goes to nobody. A
player is found by his NewLife id, else his name and birth date, else his name when it is the
only one at the club; the place only decides for the players left over. An id of a player who
left stays out of use in the Build after that one too, until no other id is free -- then it is
given again with a NOTE in the log.
"""
import collections, copy, os, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lbplayers as L
import mkworld as W
import pesdb
import playeredit as E

N = 0
GAME_CLUB, NEW_CLUB, PLACES = 130, 900, 30
GAME_TOP = 1029                                  # the game's players: 1000..1029


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def write(d, name, raw):
    with open(os.path.join(d, name), "wb") as f:
        f.write(pesdb.wesys_pack(bytes(raw)))


def tables(d, squads):
    players, assigns, teams = bytearray(), bytearray(), bytearray()
    for tid, pids in squads.items():
        for n, pid in enumerate(pids):
            r = bytearray(L.P_REC)
            r[L.P_ID:L.P_ID + 4] = pid.to_bytes(4, "little")
            players += r
            a = bytearray(L.A_REC)
            for off, v in ((E.A_PID, pid), (E.A_TID, tid), (E.A_PACK, n << E.ORDER_SHIFT)):
                a[off:off + 4] = v.to_bytes(4, "little")
            assigns += a
        t = bytearray(W.T_REC)
        t[W.T_ID:W.T_ID + 4] = tid.to_bytes(4, "little")
        teams += t
    write(d, "Player.bin", players)
    write(d, "PlayerAssignment.bin", assigns)
    write(d, "Team.bin", teams)


def world(start=GAME_TOP + 1):
    """the game's tables (base) and a world's as mkplayers leaves them (db): the new club with
    PLACES placeholder players, ids from `start` (mkplayers hands them out in club order)"""
    base, db = tempfile.mkdtemp(), tempfile.mkdtemp()
    tables(base, {GAME_CLUB: list(range(1000, 1030))})
    tables(db, {GAME_CLUB: list(range(1000, 1030)), NEW_CLUB: list(range(start, start + PLACES))})
    return base, db


def names_of(db):
    """{player id: name} of the world's own players, and {name: [ids]}"""
    p = L.load(db, "Player.bin")
    out = {}
    for i in range(len(p) // L.P_REC):
        pid = L.u32(p, i * L.P_REC + L.P_ID)
        if pid > GAME_TOP:
            out[pid] = E.cstr(p[i * L.P_REC + E.P_NAME:i * L.P_REC + E.P_NAME + E.P_NAME_LEN])
    by = collections.defaultdict(list)
    for pid, nm in out.items():
        by[nm].append(pid)
    return out, by


def squad(people):
    """a NewLife club's edits: one per player, in squad places"""
    eds = {}
    for n, (name, extra) in enumerate(people):
        ch = {"name": name, "Registered Position": "CF" if n else "GK", "Age": "25"}
        ch.update(extra)
        eds[str(n)] = ch
    return eds


def plan(people, adds=None):
    pl = {"leagues": [{"name": "Liga", "teams": [NEW_CLUB], "club_names": ["Novi"]}],
          "players": {"Liga/0": {"edits": squad(people)}}}
    if adds:
        pl["players"][str(GAME_CLUB)] = {"add": [dict(name=n, like="1000", **x) for n, x in adds]}
    return pl


def build(pl, last=None, start=GAME_TOP + 1, **kw):
    """lbplayers.apply as leaguebuilder.build calls it; returns (db, ids file, log)"""
    import leaguebuilder as B
    base, db = world(start)
    ids, log = {}, []
    last = last or {}
    args = dict(prev=last.get("clubs"), prev_names=last.get("names"))
    if "retired" in kw:
        args.update(prev_people=last.get("people"), retired=kw["retired"])
    L.apply(copy.deepcopy(pl), base, db, 10 ** 6, log=log.append, ids=ids, **args)
    out = {"clubs": ids, "names": B.id_names(pl, ids)}
    if hasattr(B, "id_people"):
        out["people"] = B.id_people(pl, ids)
    if "retired" in kw:
        out["retired"] = sorted(kw["retired"])
    return db, out, log


def main():
    # ---- the Modpack r7 case: 24 players, the one at place 6 doubled at place 7 (the release's
    # B52); the next release takes the copy out, everybody after him moves a place up. The ids
    # file of r6 knows names only (no NewLife id, no birth date).
    people = [("Player %02d" % n, {}) for n in range(24)]
    people[6] = ("Stefan Ristovski", {})
    people.insert(7, ("Stefan Ristovski", {}))           # the copy
    people = people[:24]
    db_a, ids_a, _ = build(plan(people))
    id_a, by_a = names_of(db_a)
    copy_id = ids_a["clubs"]["Liga/0"]["7"]
    fixed = people[:7] + people[8:] + [("Player 23", {})]   # the copy out; one more real player
    db_b, ids_b, log_b = build(plan(fixed), ids_a)
    id_b, by_b = names_of(db_b)
    moved = [nm for nm, _x in people if nm != "Stefan Ristovski" and by_a[nm] != by_b[nm]]
    ok("taking a doubled player out: everybody else keeps his id (%d did not: %s)" % (len(moved), moved[:3]),
       not moved)
    ok("the player who was doubled keeps the id of the one left in his place",
       ids_a["clubs"]["Liga/0"]["6"] in by_b["Stefan Ristovski"] and len(by_b["Stefan Ristovski"]) == 1)
    other = sorted(pid for pid in id_a if pid in id_b and id_a[pid] != id_b[pid])
    ok("no id of A is somebody else's in B (%d were)" % len(other), not other)
    ok("the copy's id goes to nobody", copy_id not in id_b)
    ok("the placeholders keep theirs", all(ids_a["clubs"]["Liga/0"][str(n)] == ids_b["clubs"]["Liga/0"][str(n)]
                                            for n in range(24, PLACES)))
    ok("the new real player at place 23 takes a new id, not the copy's",
       ids_b["clubs"]["Liga/0"]["23"] not in id_a or id_a[ids_b["clubs"]["Liga/0"]["23"]] == "Player 23")

    # ---- the rest needs the 0.2.4 ids file: who the players are, and the ids of those gone
    retired = set()
    db_b, ids_b, log_b = build(plan(fixed), ids_a, retired=retired)
    ok("the ids file keeps the copy's id as nobody's", copy_id in ids_b["retired"])
    ok("the log says how the ids were kept", any("keep the id of the last Build" in l for l in log_b))
    # a third Build, mkplayers' placeholder ids where the copy's was: still nobody's
    db_c, ids_c, _ = build(plan(fixed), ids_b, retired=set(ids_b["retired"]))
    id_c, _by = names_of(db_c)
    ok("a Build later the copy's id is still nobody's", copy_id not in id_c and copy_id in ids_c["retired"])
    ok("and everybody still has his id of A",
       all(names_of(db_c)[1][nm] == by_a[nm] for nm, _x in people if nm != "Stefan Ristovski"))

    # ---- two players of one name at a club: the NewLife id says which is which, whatever
    # their places; a birth date does too
    twins = [("Luka Horvat", {"newlife_id": "501", "birth_date": "2001-01-01"}),
             ("Luka Horvat", {"newlife_id": "502", "birth_date": "1995-05-05"})] + \
            [("Igrac %02d" % n, {"newlife_id": str(600 + n)}) for n in range(20)]
    _db, ids_1, _l = build(plan(twins), retired=set())
    swapped = [twins[1], twins[0]] + twins[2:]
    _db, ids_2, _l = build(plan(swapped), ids_1, retired=set())
    a, b = ids_1["clubs"]["Liga/0"], ids_2["clubs"]["Liga/0"]
    ok("namesakes swapped in the squad: each keeps his own id (by NewLife id)", a["0"] == b["1"] and a["1"] == b["0"])
    no_nl = [(n, {"birth_date": x["birth_date"]}) for n, x in twins[:2]] + [(n, {}) for n, _x in twins[2:]]
    _db, ids_1, _l = build(plan(no_nl), retired=set())
    _db, ids_2, _l = build(plan([no_nl[1], no_nl[0]] + no_nl[2:]), ids_1, retired=set())
    a, b = ids_1["clubs"]["Liga/0"], ids_2["clubs"]["Liga/0"]
    ok("namesakes swapped, no NewLife id: the birth date says which is which", a["0"] == b["1"] and a["1"] == b["0"])
    # two names that are one without spaces and accents ("Baher El Mohamady", "Baher Elmohamady",
    # two players of one Modpack club): the name as written tells them apart
    pair = [("Baher El Mohamady", {}), ("Baher Elmohamady", {})] + [(n, {}) for n, _x in twins[2:]]
    _db, ids_1, _l = build(plan(pair), retired=set())
    _db, ids_2, _l = build(plan(pair[2:5] + [pair[1], pair[0]] + pair[5:]), ids_1, retired=set())
    a, b = ids_1["clubs"]["Liga/0"], ids_2["clubs"]["Liga/0"]
    ok("names alike but written apart: each keeps his own id", a["0"] == b["4"] and a["1"] == b["3"])
    # another man of the same name in the place of one who left is not him
    _db, ids_1, _l = build(plan(twins[:1] + twins[2:]), retired=set())
    other = [("Luka Horvat", {"newlife_id": "777", "birth_date": "1990-09-09"})] + twins[2:]
    _db, ids_2, _l = build(plan(other), ids_1, retired=set())
    ok("a namesake with another NewLife id does not take the id of the one who left",
       ids_2["clubs"]["Liga/0"]["0"] != ids_1["clubs"]["Liga/0"]["0"]
       and ids_1["clubs"]["Liga/0"]["0"] in ids_2["retired"])

    # ---- a player the release adds to a club of the game ("add", keyed "+n"): the same
    adds = [("Novak %d" % n, {"newlife_id": str(900 + n)}) for n in range(5)]
    _db, ids_1, _l = build(plan(twins, adds), retired=set())
    _db, ids_2, _l = build(plan(twins, adds[:1] + adds[2:]), ids_1, retired=set())
    a, b = ids_1["clubs"][str(GAME_CLUB)], ids_2["clubs"][str(GAME_CLUB)]
    ok("an added player taken out: the others keep their ids", [a["+0"], a["+2"], a["+3"], a["+4"]] ==
       [b["+0"], b["+1"], b["+2"], b["+3"]])
    ok("and his id goes to nobody", a["+1"] not in b.values() and a["+1"] in ids_2["retired"])

    # ---- a player who changed clubs between two Builds keeps his id by his NewLife id
    two = {"leagues": [{"name": "Liga", "teams": [NEW_CLUB, NEW_CLUB + 1], "club_names": ["Novi", "Drugi"]}],
           "players": {"Liga/0": {"edits": squad(twins)},
                       "Liga/1": {"edits": squad([("Ante %02d" % n, {"newlife_id": str(700 + n)}) for n in range(20)])}}}
    def build2(pl, last=None):
        base, db = tempfile.mkdtemp(), tempfile.mkdtemp()
        tables(base, {GAME_CLUB: list(range(1000, 1030))})
        tables(db, {GAME_CLUB: list(range(1000, 1030)), NEW_CLUB: list(range(1030, 1060)),
                    NEW_CLUB + 1: list(range(1060, 1090))})
        ids = {}
        last = last or {}
        L.apply(copy.deepcopy(pl), base, db, 10 ** 6, log=lambda *_a: None, ids=ids, prev=last.get("clubs"),
                prev_names=last.get("names"), prev_people=last.get("people"), retired=set())
        import leaguebuilder as B
        return {"clubs": ids, "names": B.id_names(pl, ids), "people": B.id_people(pl, ids)}

    f1 = build2(two)
    moved = copy.deepcopy(two)
    star = moved["players"]["Liga/0"]["edits"].pop("5")
    eds = moved["players"]["Liga/0"]["edits"]
    moved["players"]["Liga/0"]["edits"] = {str(n): ch for n, ch in enumerate(eds[k] for k in sorted(eds, key=int))}
    moved["players"]["Liga/1"]["edits"]["20"] = star
    f2 = build2(moved, f1)
    ok("a player who went to the other club keeps his id", f1["clubs"]["Liga/0"]["5"] == f2["clubs"]["Liga/1"]["20"])

    # ---- a NewLife club that moved a place in its league (a club before it left): its players'
    # ids follow it by its NewLife club id; a club that left the world keeps its ids out of use
    import leaguebuilder as B
    last = {"clubs": {"Liga/0": {"0": 2001}, "Liga/1": {"0": 2002}, "Liga/2": {"0": 2003}, "77": {"+0": 2004}},
            "names": {"Liga/1": {"0": "Ana"}}, "club_nl": {"Liga/0": "10", "Liga/1": "11", "Liga/2": "12"}}
    now = {"Liga/0": "11", "Liga/1": "12"}
    got = B.follow_clubs(last, now)
    ok("a club a place up keeps its players' ids", got["clubs"]["Liga/0"] == {"0": 2002}
       and got["clubs"]["Liga/1"] == {"0": 2003} and got["names"]["Liga/0"] == {"0": "Ana"})
    ok("a club that left: under a key no club has", got["clubs"]["gone:Liga/0"] == {"0": 2001}
       and got["clubs"]["77"] == {"+0": 2004})
    ok("an ids file of an older Build is taken as it is", B.follow_clubs({"clubs": {"Liga/0": {}}}, now)
       == {"clubs": {"Liga/0": {}}})

    # ---- the limit: no free id left, a gone player's id is given again, and the log says so
    log = []
    free = L.FreeIds(L.PID_MAX - 3, {L.PID_MAX - 2}, {L.PID_MAX - 1, 5000}, log.append)
    ok("an id of a player who left is skipped while another is free", free.take() == L.PID_MAX and not log)
    ok("then one is given again, the lowest first, with a NOTE",
       free.take() == 5000 and len(log) == 1 and "NOTE" in log[0] and "5000" in log[0])
    ok("and the next", free.take() == L.PID_MAX - 1 and len(log) == 2)
    try:
        free.take()
        ok("none left at all: Build stops", False)
    except L.Error:
        ok("none left at all: Build stops", True)
    print("%d cases passed" % N)


if __name__ == "__main__":
    main()
