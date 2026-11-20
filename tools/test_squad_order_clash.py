"""python tools/test_squad_order_clash.py

B331 (snellejelle_2, #support 05.11.2026, FL27, Mod Studio 0.3.0): Build stopped with "squad
orders clash: club 71584: two players have squad order 25". Jong KAA Gent was ordered on the
Players page over FL26's tables, which kept an order only where it differed from the game's; FL27's
base squad numbers its places otherwise (place 25: order 28 in FL26 1.3, 25 in FL27), so El Hadji
Seck, with no order of his own, landed on Alexandre Chaidron's 25. The same class on 04.11.
(pepponeee, FL27): a game club ordered over the other game's squad, with players FL27 does not
have. Now such a squad closes up -- orders 0, 1, 2 ... by the order it had, ties by the place
each player had before the recipe, newcomers after -- with a note naming the club, and the
Build goes on; _check_orders still stops anything left broken. Tables made here.
"""
import os, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lbplayers as L
import playeredit as E
from test_squad_cap import tables
import test_squad_cap as T

ok = T.ok


def squad(d, tid):
    """[player id] of a club by squad order, and [order]"""
    a = L.load(d, "PlayerAssignment.bin")
    v = sorted(((L.u32(a, i * L.A_REC + E.A_PACK) & E.ORDER_MASK) >> E.ORDER_SHIFT, L.u32(a, i * L.A_REC + E.A_PID))
               for i in range(len(a) // L.A_REC) if L.u32(a, i * L.A_REC + E.A_TID) == tid)
    return [p for _o, p in v], [o for o, _p in v]


def set_orders(d, tid, orders):
    """the base squad's orders as FL27 ships them for a new club's prototype: 0-26, then 35 36 37"""
    a = L.load(d, "PlayerAssignment.bin")
    n = 0
    for i in range(len(a) // L.A_REC):
        o = i * L.A_REC
        if L.u32(a, o + E.A_TID) == tid:
            pack = L.u32(a, o + E.A_PACK) & ~E.ORDER_MASK | orders[n] << E.ORDER_SHIFT
            a[o + E.A_PACK:o + E.A_PACK + 4] = pack.to_bytes(4, "little")
            n += 1
    T.write(d, "PlayerAssignment.bin", a)


def main():
    base, db = tempfile.mkdtemp(), tempfile.mkdtemp()
    tables(base, {130: list(range(1000, 1006)), 131: list(range(2000, 2005)), 200: list(range(5000, 5030))},
           {130: "Game Club", 131: "Other Club", 200: "Jong KAA Gent"})
    set_orders(base, 200, list(range(27)) + [35, 36, 37])
    leagues = [{"name": "Belgian Challenger Pro League", "teams": [200], "club_names": ["Jong KAA Gent"]},
               {"name": "Liga A", "teams": [130, 131], "game_clubs": {"0": {"id": 130}, "1": {"id": 131}},
                "club_names": ["", ""]}]
    new = "Belgian Challenger Pro League/0"
    pl = {"leagues": leagues, "players": {
        # snellejelle's club: place 24 ordered 25, place 25 kept no order (FL26 1.3: 28, FL27: 25)
        new: {"edits": {"24": {"order": "25"}, "23": {"order": "23"}}},
        # ordered over the other game's squad: 9999 is not in this game, 1003 has no order of his own
        # and keeps his game order 3, which the recipe gave 1002; 1004 leaves for 131
        "130": {"edits": {"9999": {"order": "0"}, "1000": {"order": "1"}, "1001": {"order": "2"},
                          "1002": {"order": "3"}}},
        # a newcomer the recipe put on order 0, and one the game does not have
        "131": {"join": ["1004", "9998"], "edits": {"1004": {"order": "0"}, "9998": {"order": "1"}}},
    }}
    log = []
    try:
        L.apply(pl, base, db, 10 ** 6, log=log.append)
        went = True
    except L.Error as e:
        went = False
        print("# old code: %s" % e)
    ok("B331: the Build goes on past clashing squad orders", went)
    notes = [l for l in log if "closed up" in l]
    print("#", "\n# ".join(notes))
    pids, orders = squad(db, 200)
    ok("the new club's squad is closed up: orders 0-29", orders == list(range(30)))
    ok("ties go by the place each had: place 24 before place 25, the rest in order",
       pids == list(range(5000, 5030)))
    ok("the note names the club, its league and its id, and the order",
       any("Jong KAA Gent (Belgian Challenger Pro League, id 200)" in l and "squad order (25)" in l for l in notes))
    pids, orders = squad(db, 130)
    ok("a game club ordered over the other game's squad closes up (%s)" % pids,
       orders == [0, 1, 2, 3, 4] and pids == [1000, 1001, 1002, 1003, 1005])
    ok("its note names it", any("Game Club (Liga A, id 130)" in l for l in notes))
    pids, orders = squad(db, 131)
    ok("a newcomer on an order taken comes after the one who had it (%s)" % pids,
       orders == list(range(6)) and pids == [2000, 1004, 2001, 2002, 2003, 2004])
    ok("a joiner the game does not have is skipped and clashes with nobody",
       any("no player 9998 in the game" in l for l in log) and 9998 not in pids)
    ok("three clubs closed up, three notes", len(notes) == 3)
    # the safety net stays: anything still broken stops the Build
    a = L.load(db, "PlayerAssignment.bin")
    a += a[:L.A_REC]
    try:
        L._check_orders(a)
        stopped = False
    except L.Error as e:
        stopped = "two players have squad order" in str(e)
    ok("_check_orders still stops a clash left over", stopped)
    print("1..%d" % T.N)


if __name__ == "__main__":
    main()
