"""python tools/test_keep_ids_room.py

B282 (juanjose6124 29.10., 80 new leagues, 1174 new clubs): a world's first Build went in, the
next one stopped with "no free player id left below 262144". Every player who keeps his id was
moved to a spare id first and then to his own, and both the spare and the id he left stayed
taken: a world whose ids fill most of the room between the game's last id and PID_MAX ran out
on its second Build although it needs no more ids than on the first.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lbplayers as L
import playeredit as E
from test_keep_ids import tables, sound

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def ids_of(assigns):
    return [L.u32(assigns, i * L.A_REC + E.A_PID) for i in range(len(assigns) // L.A_REC)]


def main():
    top = L.PID_MAX - 100                              # room for 100 ids above the game's own
    # the same squad of 60 again, on the same ids: nobody needs to move
    pids = list(range(top + 1, top + 61))
    players, assigns, index = tables({5000: pids})
    first = {"L/0": list(pids)}
    prev = {"L/0": {str(k): pid for k, pid in enumerate(pids)}}
    L._keep_ids(prev, None, {}, first, players, assigns, index, top)
    ok("60 of 100 ids, the same again: every player keeps his id", first["L/0"] == pids
       and ids_of(assigns) == pids and sound(players, assigns, index))

    # the last Build had them on top+41..top+100, this one's tables top+1..top+60: all 100 ids are
    # someone's now or wanted, and they still fit, each on his own
    players, assigns, index = tables({5000: pids})
    first = {"L/0": list(pids)}
    want = list(range(top + 41, top + 101))
    prev = {"L/0": {str(k): w for k, w in enumerate(want)}}
    L._keep_ids(prev, None, {}, first, players, assigns, index, top)
    ok("60 players onto the last Build's 60 ids with no spare left: each takes his own",
       first["L/0"] == want and ids_of(assigns) == want and sound(players, assigns, index))

    # 90 players, 50 of them kept on top+51..top+100, 40 new ones: the new ones take the ids the
    # kept ones left, not ids past PID_MAX and not the gone players' ones
    pids = list(range(top + 1, top + 91))
    players, assigns, index = tables({5000: pids})
    first = {"L/0": list(pids)}
    prev = {"L/0": {str(k): top + 51 + k for k in range(50)}, "Gone/0": {"0": top + 45}}
    retired = set()
    L._keep_ids(prev, None, {}, first, players, assigns, index, top, retired=retired)
    got = first["L/0"]
    ok("90 of 100 ids, 50 kept: all fit, the kept ones on their ids",
       got[:50] == list(range(top + 51, top + 101)) and len(set(got)) == 90
       and all(top < p <= L.PID_MAX for p in got) and sound(players, assigns, index))
    ok("  ... and nobody gets the gone player's id while another is free", top + 45 in retired and top + 45 not in got)
    print("%d cases passed" % N)


if __name__ == "__main__":
    main()
