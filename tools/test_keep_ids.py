"""python tools/test_keep_ids.py

The world's own players keep the ids the last Build gave them (lbplayers._keep_ids, GitHub #126):
a face linked to a new player by his id was lost when a change elsewhere (a league added above)
handed the placeholder ids out in another order.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lbplayers as L
import playeredit as E

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def tables(squads):
    """Player.bin and PlayerAssignment.bin bytes for {team id: [player id ...]}"""
    players, assigns = bytearray(), bytearray()
    for tid, pids in squads.items():
        for n, pid in enumerate(pids):
            r = bytearray(L.P_REC)
            r[L.P_ID:L.P_ID + 4] = pid.to_bytes(4, "little")
            players += r
            a = bytearray(L.A_REC)
            for off, v in ((E.A_PID, pid), (E.A_TID, tid), (E.A_PACK, n << E.ORDER_SHIFT)):
                a[off:off + 4] = v.to_bytes(4, "little")
            assigns += a
    index = {L.u32(players, i * L.P_REC + L.P_ID): i * L.P_REC for i in range(len(players) // L.P_REC)}
    return players, assigns, index


def team_of(assigns, pid):
    return next(L.u32(assigns, i * L.A_REC + E.A_TID) for i in range(len(assigns) // L.A_REC)
                if L.u32(assigns, i * L.A_REC + E.A_PID) == pid)


def main():
    top = 1000
    # this Build: a league added above handed out 1001-1003 to its club, so Liga/0 now has 1004-1006
    players, assigns, index = tables({700: [1001, 1002, 1003], 701: [1004, 1005, 1006]})
    first = {"New/0": [1001, 1002, 1003], "Liga/0": [1004, 1005, 1006]}
    changes = {"Liga/0": {"edits": {"0": {"name": "Planic"}, "2": {"name": "Somebody else"}},
                          "add": [{"name": "Added"}]}}
    prev = {"Liga/0": {"0": 1001, "1": 1002, "2": 1003, "+0": 1007}}
    names = {"Liga/0": {"0": "Planic", "2": "Bala"}}
    later = L._keep_ids(prev, names, changes, first, players, assigns, index, top)
    ok("a player keeps the id of the last Build", first["Liga/0"][0] == 1001 and team_of(assigns, 1001) == 701)
    ok("a placeholder keeps his too", first["Liga/0"][1] == 1002 and team_of(assigns, 1002) == 701)
    ok("a place now held by another player keeps nothing of it", first["Liga/0"][2] == 1006)
    ok("the club in the way moves to free ids", all(p > 1006 for p in first["New/0"][:2]))
    ok("every id once", len(index) == 6 and len(set(first["New/0"] + first["Liga/0"])) == 6)
    ok("Player.bin follows", set(index) == {L.u32(players, o + L.P_ID) for o in index.values()})
    ok("an added player's id waits for him", later == {("Liga/0", "+0"): 1007})

    # an id the recipe sets itself, or one at or below the game's, is never handed out again
    players, assigns, index = tables({701: [1004, 1005]})
    first = {"Liga/0": [1004, 1005]}
    changes = {"Liga/0": {"edits": {"1": {"id": "1001"}}}}
    L._keep_ids({"Liga/0": {"0": 1001, "1": 999}}, None, changes, first, players, assigns, index, top)
    ok("an id set in the recipe and one of the game's are left alone", first["Liga/0"] == [1004, 1005])
    ok("no last Build: nothing moves", L._keep_ids({}, None, changes, first, players, assigns, index, top) == {}
       and first["Liga/0"] == [1004, 1005])
    print("%d cases passed" % N)


if __name__ == "__main__":
    main()
