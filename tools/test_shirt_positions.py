r"""python tools/test_shirt_positions.py

ismael 22.10. (#general): new clubs had "strikers wearing number 1 or goalkeepers wearing number
10" -- a new club kept the numbers of the squad Build cloned for it. lbplayers.position_shirts now
numbers a new club's squad by position: the eleven by their places (keeper 1, full backs 2 and 3,
centre backs 4 and 5, striker 9 ...), the rest by their line. No game needed.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lbplayers as L
import playeredit as E

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def main():
    # the 4-2-3-1 eleven in place order, then a bench
    eleven = ["GK", "CB", "CB", "RB", "LB", "DMF", "CMF", "RWF", "LWF", "AMF", "CF"]
    bench = ["GK", "CB", "LB", "CMF", "DMF", "AMF", "LMF", "CF", "SS", "GK", "RB", "CB", "CMF"]
    sq = [("p%d" % n, n, pos) for n, pos in enumerate(eleven + bench)]
    got = L.position_shirts(sq)
    ok("every player has a number", set(got) == {k for k, _o, _p in sq})
    ok("each number once", len(set(got.values())) == len(sq))
    ok("all numbers 1-99", all(1 <= n <= 99 for n in got.values()))
    by = {k: got[k] for k, _o, _p in sq}
    ok("the first keeper wears 1", by["p0"] == 1)
    ok("centre backs 4 and 5", {by["p1"], by["p2"]} == {4, 5})
    ok("right back 2, left back 3", (by["p3"], by["p4"]) == (2, 3))
    ok("DMF 6, CMF 8", (by["p5"], by["p6"]) == (6, 8))
    ok("wingers 7 and 11", (by["p7"], by["p8"]) == (7, 11))
    ok("AMF 10, striker 9", (by["p9"], by["p10"]) == (10, 9))
    keepers = [by[k] for k, _o, pos in sq if pos == "GK"]
    ok("every keeper wears a keeper's number", all(n in E.KEEPER_SHIRTS for n in keepers))
    ok("no outfielder wears a keeper's number",
       all(by[k] not in E.KEEPER_SHIRTS for k, _o, pos in sq if pos != "GK"))
    # the order the squad lists them in, not the list's: the eleven are orders 0-10
    rev = [(k, o, p) for k, o, p in reversed(sq)]
    ok("order, not list position", L.position_shirts(rev) == got)
    # another formation: a 4-4-2 eleven
    lu = ["GK", "CB", "CB", "RB", "LB", "RMF", "CMF", "CMF", "LMF", "CF", "CF"]
    sq2 = [("q%d" % n, n, pos) for n, pos in enumerate(lu)]
    g2 = L.position_shirts(sq2, lu)
    ok("4-4-2: two strikers 9 and 10 (or 11)", g2["q9"] == 9 and g2["q10"] in (10, 11))
    ok("4-4-2: right mid 7, left mid 11", g2["q5"] == 7 and g2["q8"] in (11, 10))
    # a squad of 40 (the most a club holds): still one number each, none past 99
    big = [("b%d" % n, n, ["GK", "CB", "CMF", "CF"][n % 4]) for n in range(40)]
    gb = L.position_shirts(big)
    ok("40 players: one number each", len(set(gb.values())) == 40 and max(gb.values()) <= 99)
    ok("40 players: outfielders still off keepers' numbers while others are free",
       all(gb[k] not in E.KEEPER_SHIRTS for k, _o, pos in big if pos != "GK"))
    print("all %d ok" % N)


if __name__ == "__main__":
    main()
