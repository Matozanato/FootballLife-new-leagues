r"""python tools/test_shirt_numbers.py

jibibi 18.10. (#beta-chat): "out-of-position players wearing the number 1". Build gave a player it
adds to a squad (sign_keepers' free agents, a transfer, a new player) the lowest free shirt number,
whatever his position: a club whose keeper had moved on handed its 1 to an outfielder. Now a
keeper takes a free keeper's number (1, 12, 13 ...) and anyone else another, the old way only when
nothing else is free. Tables made here, in a temporary folder.
"""
import os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lbplayers as L
import mkworld as W
import pesdb
import playeredit as E

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def packs(*shirts):
    return [E.with_shirt(i << E.ORDER_SHIFT, s) for i, s in enumerate(shirts)]


# free_shirt itself
ok("an outfielder skips a free 1", E.free_shirt(packs(2, 3, 4), keeper=False) == 5)
ok("a keeper takes the free 1", E.free_shirt(packs(2, 3, 4), keeper=True) == 1)
ok("a keeper takes 12 when 1 is worn", E.free_shirt(packs(1, 2, 3), keeper=True) == 12)
ok("an outfielder skips 12 and 13 too", E.free_shirt(packs(*range(1, 12)), keeper=False) == 14)
ok("no position given: the lowest, as before", E.free_shirt(packs(2, 3)) == 1)
ok("every other number worn: a keeper's number after all",
   E.free_shirt(packs(*[n for n in range(1, 100) if n != 13]), keeper=False) == 13)


# sign_keepers: a club with ten outfielders (2-11, its keeper gone) and free agents
def write(d, name, raw):
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name), "wb") as f:
        f.write(pesdb.wesys_pack(bytes(raw)))


def player(pid, name, pos, age=25):
    r = bytearray(L.P_REC)
    r[L.P_ID:L.P_ID + 4] = pid.to_bytes(4, "little")
    r[E.P_NAME:E.P_NAME + 4 * E.P_NAME_LEN] = E.name_slots(name)
    E.setf(r, "Registered Position", E.POSITIONS.index(pos))
    E.setf(r, "Age", age)
    return r


tmp = tempfile.mkdtemp(prefix="fl26-shirts-")
try:
    db = os.path.join(tmp, "pesdb")
    team = bytearray(W.T_REC)
    team[W.T_ID:W.T_ID + 4] = (100).to_bytes(4, "little")
    write(db, "Team.bin", team)
    players, assigns = bytearray(), bytearray()
    outfield = ["CB", "CB", "LB", "RB", "DMF", "CMF", "AMF", "LWF", "RWF", "CF"]
    for n, pos in enumerate(outfield):
        players += player(1 + n, "Field Player%d" % n, pos)
        a = bytearray(L.A_REC)
        for off, v in ((E.A_EID, n + 1), (E.A_PID, 1 + n), (E.A_TID, 100),
                       (E.A_PACK, E.with_shirt(n << E.ORDER_SHIFT, n + 2))):
            a[off:off + 4] = v.to_bytes(4, "little")
        assigns += a
    free = [("GK", "Free Keeper%d" % i) for i in range(3)] + \
           [(pos, "Free Agent%d" % i) for i, pos in enumerate(["CB", "LB", "CMF", "CF", "RB", "DMF", "SS", "AMF"] * 2)]
    for i, (pos, name) in enumerate(free):
        players += player(500 + i, name, pos)
    write(db, "Player.bin", players)
    write(db, "PlayerAssignment.bin", assigns)

    signed = L.sign_keepers(db, log=lambda *a: None)
    ok("the club signed its keepers and the rest of a squad", len(signed.get(100, [])) >= 2)
    sq = L.Squads(db)
    rows = [(pid, shirt, E.POSITIONS[E.getf(sq.players[sq.index[pid]:sq.index[pid] + L.P_REC],
                                             "Registered Position")])
            for _o, pid, shirt, _a in sq.by_club[100]]
    keepers = sorted(s for pid, s, pos in rows if pos == "GK")
    others = [s for pid, s, pos in rows if pos != "GK"]
    ok("the keepers wear 1 and 12 (%s)" % keepers, keepers == [1, 12])
    ok("no outfielder wears 1, 12 or 13 (%s)" % sorted(others), not set(others) & {1, 12, 13})
    ok("no number twice", len({s for _p, s, _q in rows}) == len(rows))
finally:
    shutil.rmtree(tmp, ignore_errors=True)


# B157 (jibibi 18.10., Bourg-en-Bresse): a new club's places keep the numbers of the squad Build
# cloned for it, whoever the recipe puts there -- a NewLife centre forward got the 1. Now the 1
# goes to the first keeper, who swaps numbers with whoever wore it; since 0.2.5 the whole squad is
# numbered by position (lbplayers.position_shirts).
def b157(edits):
    base, db = tempfile.mkdtemp(prefix="fl26-b157b-"), tempfile.mkdtemp(prefix="fl26-b157d-")
    try:
        team = bytearray(W.T_REC)
        team[W.T_ID:W.T_ID + 4] = (200).to_bytes(4, "little")
        write(base, "Team.bin", team)
        players, assigns = bytearray(), bytearray()
        for n, pos in enumerate(["GK", "CB", "CB", "CMF", "CF", "GK"]):     # the cloned squad, 1..6
            players += player(3000 + n, "Clone Player%d" % n, pos)
            a = bytearray(L.A_REC)
            for off, v in ((E.A_EID, n + 1), (E.A_PID, 3000 + n), (E.A_TID, 200),
                           (E.A_PACK, E.with_shirt(n << E.ORDER_SHIFT, n + 1))):
                a[off:off + 4] = v.to_bytes(4, "little")
            assigns += a
        write(base, "Player.bin", players)
        write(base, "PlayerAssignment.bin", assigns)
        pl = {"leagues": [{"name": "Liga N", "teams": [200], "club_names": ["Bourg"]}],
              "players": {"Liga N/0": {"edits": edits}}}
        log = []
        L.apply(pl, base, db, 10 ** 6, log=log.append)
        sq = L.Squads(db)
        return {pid: (shirt, E.POSITIONS[E.getf(sq.players[sq.index[pid]:sq.index[pid] + L.P_REC],
                                                "Registered Position")])
                for _o, pid, shirt, _a in sq.by_club[200]}, log
    finally:
        shutil.rmtree(base, ignore_errors=True)
        shutil.rmtree(db, ignore_errors=True)


got, log = b157({"0": {"Registered Position": "CF"}, "1": {"Registered Position": "GK"},
                 "5": {"Registered Position": "CB"}})
# 0.2.5 (ismael 22.10.): the whole squad of a new club is numbered by position (test_shirt_positions)
ok("B157: the keeper the recipe put at place 1 wears the 1 (%s)" % got, got[3001] == (1, "GK"))
ok("B157: the forward at the 1's place wears another number", got[3000][0] != 1)
ok("B157: the centre backs wear 4 and 5", {got[3002][0], got[3005][0]} == {4, 5})
ok("B157: no number twice", len({s for s, _p in got.values()}) == len(got))
ok("B157: the log says it", any("numbered by position" in l for l in log))
got, log = b157({"0": {"Registered Position": "CF", "shirt": "9"}, "1": {"Registered Position": "GK"}})
ok("B157: a recipe that gives numbers keeps them", got[3000][0] == 9 and got[3001][0] == 2)
got, log = b157({"3": {"Registered Position": "AMF"}})
ok("B157: the first keeper wears 1, the second a keeper's number",
   got[3000][0] == 1 and got[3005][0] in E.KEEPER_SHIRTS and got[3005][0] != 1)
ok("B157: no outfielder wears a keeper's number",
   all(s not in E.KEEPER_SHIRTS for s, pos in got.values() if pos != "GK"))

print("test_shirt_numbers: ok (%d)" % N)
