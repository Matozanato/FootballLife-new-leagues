r"""python tools/test_b390_empty_club.py

B390 (B2Y 09.11., #beta-reports): Build stopped with "players of 70924: nothing to copy a new player
from". NewLife's "Bring the game's leagues" wrote join + add without "like" for a club the game had
left with no squad, and the adds came before anyone had joined. Now an add with nothing to copy
takes the first player who joins the club. Tables made here, in a temporary folder.
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


base, db = tempfile.mkdtemp(prefix="fl26-b390b-"), tempfile.mkdtemp(prefix="fl26-b390d-")
try:
    team = bytearray()
    for tid in (4377, 4378):                                       # 4378: the game left it empty
        t = bytearray(W.T_REC)
        t[W.T_ID:W.T_ID + 4] = tid.to_bytes(4, "little")
        team += t
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
    # what NewLife's "Bring the game's leagues" writes for a club the game has no squad for
    pl = {"leagues": [],
          "players": {"4378": {"join": ["1002", "1003"],
                               "add": [{"like": "", "name": "First Added"}, {"like": "", "name": "Second Added"}]}}}
    log = []
    L.apply(pl, base, db, 10 ** 6, log=log.append)
    ok("B390: the Build goes on (no 'nothing to copy a new player from')", True)
    sq = L.Squads(db)
    names = [E.cstr(sq.players[sq.index[pid] + E.P_NAME:sq.index[pid] + E.P_NAME + E.P_NAME_LEN])
             for _o, pid, _s, _a in sq.by_club.get(4378, [])]
    ok("B390: the empty club gets its new players (%s)" % names, "First Added" in names and "Second Added" in names)
    ok("B390: and the players who join it (%s)" % names, "Club Player2" in names and "Club Player3" in names)
finally:
    shutil.rmtree(base, ignore_errors=True)
    shutil.rmtree(db, ignore_errors=True)

print("test_b390_empty_club: ok (%d)" % N)
