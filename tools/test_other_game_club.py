r"""python tools/test_other_game_club.py

B311 (Xxspedd 02.11., #beta-chat): a world made with FL26's tables, built for FL27, stopped with
"players of 319: nothing to copy a new player from". 319 is FL26's SSC Bari; FL27 has other clubs
(SS Arezzo, 4377, and no 319), so the players the recipe added there had no squad to be copied
from. Now a club of the game the game does not have is skipped, and the log says so; a
club it has still gets its players. Tables made here, in a temporary folder.
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


def write(d, name, raw):
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name), "wb") as f:
        f.write(pesdb.wesys_pack(bytes(raw)))


def player(pid, name, pos):
    r = bytearray(L.P_REC)
    r[L.P_ID:L.P_ID + 4] = pid.to_bytes(4, "little")
    r[E.P_NAME:E.P_NAME + 4 * E.P_NAME_LEN] = E.name_slots(name)
    E.setf(r, "Registered Position", E.POSITIONS.index(pos))
    return r


base, db = tempfile.mkdtemp(prefix="fl26-b311b-"), tempfile.mkdtemp(prefix="fl26-b311d-")
try:
    team = bytearray(W.T_REC)
    team[W.T_ID:W.T_ID + 4] = (4377).to_bytes(4, "little")       # the game has 4377, not 319
    write(base, "Team.bin", team)
    players, assigns = bytearray(), bytearray()
    for n, pos in enumerate(["GK", "CB", "CMF", "CF"]):
        players += player(1000 + n, "Club Player%d" % n, pos)
        a = bytearray(L.A_REC)
        for off, v in ((E.A_EID, n + 1), (E.A_PID, 1000 + n), (E.A_TID, 4377),
                       (E.A_PACK, E.with_shirt(n << E.ORDER_SHIFT, n + 1))):
            a[off:off + 4] = v.to_bytes(4, "little")
        assigns += a
    write(base, "Player.bin", players)
    write(base, "PlayerAssignment.bin", assigns)
    pl = {"leagues": [],
          "players": {"319": {"add": [{"like": "99999", "name": "Old Game Signing"}]},
                      "4377": {"add": [{"like": "1003", "name": "New Signing"}]}}}
    log = []
    L.apply(pl, base, db, 10 ** 6, log=log.append)
    ok("B311: the Build goes on past the club the game does not have", True)
    ok("B311: the log names it (%s)" % [l for l in log if "319" in l],
       any("players of 319" in l and "no club 319" in l for l in log))
    sq = L.Squads(db)
    names = [E.cstr(sq.players[sq.index[pid] + E.P_NAME:sq.index[pid] + E.P_NAME + E.P_NAME_LEN])
             for _o, pid, _s, _a in sq.by_club[4377]]
    ok("B311: the club the game has still gets its new player (%s)" % names, "New Signing" in names)
    ok("B311: nothing went to a club 319", 319 not in sq.by_club)
finally:
    shutil.rmtree(base, ignore_errors=True)
    shutil.rmtree(db, ignore_errors=True)

print("test_other_game_club: ok (%d)" % N)
