"""python tools/test_squad_cap.py

A club past the most players the game holds (40, a national team 26) after the recipe's joins
keeps its first 40: the last to come are left out with a note that names the club -- its name,
its league and its id -- and, when the club is in the world twice, both leagues. 0.2.4 beta
stopped the Build on "players of 130: 42 players -- a club has at most 40", and nobody could
tell which club that was: it was the same one twice in the world (B46, vmican 15.10.).
"""
import os, sys, tempfile

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
    with open(os.path.join(d, name), "wb") as f:
        f.write(pesdb.wesys_pack(bytes(raw)))


def tables(d, squads, names):
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
    for tid, nm in names.items():
        t = bytearray(W.T_REC)
        t[W.T_ID:W.T_ID + 4] = tid.to_bytes(4, "little")
        t[W.T_NAME:W.T_NAME + len(nm)] = nm.encode("utf-8")
        teams += t
    write(d, "Player.bin", players)
    write(d, "PlayerAssignment.bin", assigns)
    write(d, "Team.bin", teams)


def squad(d, tid):
    a = L.load(d, "PlayerAssignment.bin")
    rows = sorted((L.u32(a, i * L.A_REC + E.A_PACK) & E.ORDER_MASK) >> E.ORDER_SHIFT
                  for i in range(len(a) // L.A_REC) if L.u32(a, i * L.A_REC + E.A_TID) == tid)
    return rows


def run(leagues):
    base, db = tempfile.mkdtemp(), tempfile.mkdtemp()
    tables(base, {130: list(range(1000, 1030)), 131: list(range(2000, 2015))},
           {130: "Club Cent", 131: "Club Donor"})
    pl = {"leagues": leagues, "players": {"130": {"join": [str(p) for p in range(2000, 2012)]}}}
    log = []
    L.apply(pl, base, db, 10 ** 6, log=log.append)
    return db, log


def main():
    one = {"name": "Liga A", "teams": [130], "game_clubs": {"0": {"id": 130}}, "club_names": [""]}
    two = {"name": "Liga B", "teams": [130], "game_clubs": {"0": {"id": 130}}, "club_names": [""]}
    db, log = run([one, two])
    note = [l for l in log if "at most 40" in l]
    ok("42 players: Build goes on, the club keeps 40 in order", squad(db, 130) == list(range(40)))
    ok("the note names the club, its league and its id", len(note) == 1 and "Club Cent (Liga A, id 130)" in note[0])
    ok("it says which 2 are left out", "the last 2 to come are left out (2010, 2011)" in note[0])
    ok("the same club twice: both leagues named", "in your world 2 times (Liga A, Liga B)" in note[0])
    ok("the donor club lost the 12 who left", squad(db, 131) == list(range(3)))

    db, log = run([one])
    note = [l for l in log if "at most 40" in l]
    ok("once in the world: no 'twice' part", len(note) == 1 and "times" not in note[0])

    print("1..%d" % N)


if __name__ == "__main__":
    main()
