"""python test_squad_places.py -- a new club gets 30 players again, and its places are the squad
Build makes (pepponeee98, 14.10.2026: 0.2.2/0.2.3 built 22 while NewLife and Players lined up 30,
and places 23-30 came out as "no player N, skipped"; 22 had never been agreed)"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import leaguebuilder as B
import lbplayers as P
import playeredit as E
from modstudio import newlife as NL

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def row(pos, level):
    r = {n: str(level) for n, _b in E.ABILITIES}
    r["Registered Position"] = pos
    return r


def main():
    ok("the Players page and NewLife take the squad Build makes, 30", P.SQUAD == B.SQUAD == 30)
    ok("a world of the shipped tables gets 30 a club", B.squad_size(27927, 1100) == 30)
    ok("only when 30 each would pass the player records, fewer", B.squad_size(27927, 1400) == (61905 - 27927) // 1400)
    ok("never below 22", B.squad_size(27927, 5000) == B.SQUAD_FIT == 22)
    src = open(os.path.join(HERE, "leaguebuilder.py"), encoding="utf-8").read()
    sites = re.findall(r"(?m)^( +)import lbplayers\n(.*)\n", src)
    ok("every Build step hands its squad size on (run3's 30 for the Modpack too)",
       sites and all(nxt.strip().startswith(("lbplayers.SQUAD = SQUAD", "SQUAD = lbplayers.SQUAD = squad_of("))
                     for _i, nxt in sites))      # the second: use_squad, the world's 30-35 (0.2.5)

    rel = NL.Release.__new__(NL.Release)
    rel.squads = {1: [row("GK", 40), row("GK", 41), row("GK", 42), row("GK", 43)]
                     + [row("CF", 70 + n % 10) for n in range(27)]}
    sq = rel.squad(1)
    ok("NewLife picks %d players for a club" % B.SQUAD, len(sq) == B.SQUAD)
    ok("weak goalkeepers still make the squad, three of them",
       sum(r["Registered Position"] == "GK" for r in sq) == 3)
    print("%d cases passed" % N)


if __name__ == "__main__":
    main()
