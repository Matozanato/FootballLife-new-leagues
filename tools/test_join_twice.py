"""python tools/test_join_twice.py

B274 (juanjose6124 29.10.2026): leagues of two packs put into one world, each moving the same
player of the game to a club of its own, and Build stopped after minutes of work on "player
141487 joins two clubs (2373 and 164)". Now the first club of the recipe keeps him and the
second transfer is skipped with a note that names both clubs; the rest of the Build goes on.
"""
import os, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lbplayers as L
from test_squad_cap import tables, ok, squad
import test_squad_cap as T
import playeredit as E


def club_of(d, pid):
    a = L.load(d, "PlayerAssignment.bin")
    return [L.u32(a, i * L.A_REC + E.A_TID) for i in range(len(a) // L.A_REC)
            if L.u32(a, i * L.A_REC + E.A_PID) == pid]


def main():
    base, db = tempfile.mkdtemp(), tempfile.mkdtemp()
    tables(base, {130: list(range(1000, 1020)), 131: list(range(2000, 2020)), 132: list(range(3000, 3020))},
           {130: "Club A", 131: "Club B", 132: "Club Donor"})
    leagues = [{"name": "Liga A", "teams": [130], "game_clubs": {"0": {"id": 130}}, "club_names": [""]},
               {"name": "Liga B", "teams": [131], "game_clubs": {"0": {"id": 131}}, "club_names": [""]}]
    pl = {"leagues": leagues, "players": {"130": {"join": ["3000", "3001"]}, "131": {"join": ["3001", "3002"]}}}
    log = []
    L.apply(pl, base, db, 10 ** 6, log=log.append)
    note = [l for l in log if "already joins" in l]
    ok("Build goes on: one note for the player both clubs take", len(note) == 1)
    ok("it names him and both clubs", "player 3001 already joins 130" in note[0] and "players of 131" in note[0])
    ok("the first club of the recipe keeps him", club_of(db, 3001) == [130])
    ok("the other transfers of both clubs are made", club_of(db, 3000) == [130] and club_of(db, 3002) == [131])
    ok("each player once", all(len(club_of(db, p)) == 1 for p in range(3000, 3020)))
    print("1..%d" % T.N)


if __name__ == "__main__":
    main()
