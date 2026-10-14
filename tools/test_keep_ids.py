"""python tools/test_keep_ids.py

The world's own players keep the ids the last Build gave them (lbplayers._keep_ids, GitHub #126):
a face linked to a new player by his id was lost when a change elsewhere (a league added above)
handed the placeholder ids out in another order.

A team id under two club keys (a NewLife club listed twice: maur0's recipe had four, in two
leagues or twice in one) or a stale ids file stopped Build with a KeyError in _renumber
(Discord, 0.2.3, on the third Build): a player is moved once, every copy of him in `first`
follows, and every id stays unique.
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


def sound(players, assigns, index):
    """Player.bin ids unique and as index says, every assignment's player in Player.bin"""
    ids = [L.u32(players, i * L.P_REC + L.P_ID) for i in range(len(players) // L.P_REC)]
    held = {L.u32(assigns, i * L.A_REC + E.A_PID) for i in range(len(assigns) // L.A_REC)}
    return (len(ids) == len(set(ids)) and set(ids) == set(index)
            and all(L.u32(players, o + L.P_ID) == pid for pid, o in index.items()) and held <= set(ids))


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

    # one team id under two club keys (a NewLife club in two leagues): both keys list the same
    # players. Build 2 pins them once and the second key follows (it kept the temporary ids,
    # which the ids file then recorded) ...
    players, assigns, index = tables({702: [1001, 1002, 1003]})
    first = {"A/0": [1001, 1002, 1003], "B/0": [1001, 1002, 1003]}
    prev = {"A/0": {"0": 1003, "1": 1001, "2": 1002}, "B/0": {"0": 1003, "1": 1001, "2": 1002}}
    L._keep_ids(prev, None, {}, first, players, assigns, index, top)
    ok("a club under two keys: both follow", first["A/0"] == first["B/0"] == [1003, 1001, 1002])
    ok("a club under two keys: the tables stay sound", sound(players, assigns, index)
       and set(index) == {1001, 1002, 1003})
    # ... and Build 3 got another id for the same player under each key (the 0.2.3 KeyError)
    first = {"A/0": [1003, 1001, 1002], "B/0": [1003, 1001, 1002]}
    prev = {"A/0": {"0": 1003, "1": 1001, "2": 1002}, "B/0": {"0": 1004, "1": 1005, "2": 1006}}
    L._keep_ids(prev, None, {}, first, players, assigns, index, top)
    ok("two ids for one player: no KeyError, the first key's wins", first["A/0"] == first["B/0"] == [1003, 1001, 1002])
    ok("two ids for one player: the tables stay sound", sound(players, assigns, index) and len(index) == 3)
    # one player in the squads of two clubs, pinned to a different id by each
    players, assigns, index = tables({703: [1001, 1002], 704: [1003]})
    assigns += assigns[:L.A_REC]
    assigns[-L.A_REC + E.A_TID:-L.A_REC + E.A_TID + 4] = (704).to_bytes(4, "little")
    first = {"C/0": [1001, 1002], "D/0": [1003, 1001]}
    prev = {"C/0": {"0": 1010}, "D/0": {"1": 1011}}
    L._keep_ids(prev, None, {}, first, players, assigns, index, top)
    ok("a player in two squads takes one id, and both squads have it",
       first["C/0"][0] == first["D/0"][1] == 1010 and sound(players, assigns, index))
    # a stale ids file: a place whose player is not in Player.bin, ids out of range, junk
    players, assigns, index = tables({705: [1001, 1002]})
    a = bytearray(L.A_REC)
    for off, v in ((E.A_PID, 1009), (E.A_TID, 705), (E.A_PACK, 2 << E.ORDER_SHIFT)):
        a[off:off + 4] = v.to_bytes(4, "little")
    assigns += a
    first = {"E/0": [1001, 1002, 1009]}
    prev = {"E/0": {"0": "x", "1": 10 ** 9, "2": 1020, "7": 1021, "+3": 1022}, "Gone/0": {"0": 1023},
            "F/0": [1024], "G/0": None}
    L._keep_ids(prev, {"E/0": ["junk"]}, {}, first, players, assigns, index, top)
    ok("a stale ids file: nothing breaks, the player not in Player.bin is left as he is",
       first["E/0"] == [1001, 1002, 1009] and index == {1001: 0, 1002: L.P_REC}
       and [L.u32(assigns, i * L.A_REC + E.A_PID) for i in range(3)] == [1001, 1002, 1009])
    for junk in ([1, 2], "x", 5):
        ok("an ids file that is not {club: {key: id}} (%r): nothing moves" % (junk,),
           L._keep_ids(junk, junk, {}, first, players, assigns, index, top) == {} and first["E/0"] == [1001, 1002, 1009])
    print("%d cases passed" % N)


if __name__ == "__main__":
    main()
