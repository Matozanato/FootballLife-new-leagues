"""python tools/test_newlife_classics.py

A NewLife player who has the game's id (or name) of a legend of the Classic Teams is the namesake
playing in a lower league today, not the legend: the Megapack's Brazilian Serie C/D took Marcelo
from Monsters Classics and Fernandinho and Nene from Titans Classics (08.11.). _movers makes such
a row a new player ("copy") and leaves the Classic Teams and the ML default squads whole; a player
of a club of the game still moves to his NewLife club as before."""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lbplayers as P
from modstudio import newlife as NL

N = 0


def ok(name, cond):
    global N
    print(("ok    " if cond else "FAIL  ") + name)
    N += 0 if cond else 1


class Squads:
    """the part of lbplayers.Squads that _movers reads"""
    def __init__(self, base):
        self.names = {34908: "Marcelo", 51000: "Fernandinho", 61000: "Joao Silva", 62000: "Pedro Default"}
        self.clubs_of = {34908: [909], 51000: [910], 61000: [2452], 62000: [140]}
        self.by_club = {909: list(range(36)), 910: list(range(38)), 2452: list(range(30)), 140: list(range(28))}
        self.index = set(self.names)

    def name(self, pid):
        return self.names[pid]


def main():
    real = P.Squads
    P.Squads = Squads
    try:
        info = {"base": "x", "national": set(),
                "clubs": {909: (" Monsters Classics", ""), 910: (" Titans Classics", ""),
                          2452: ("Avai FC", ""), 140: ("ML Default Europe", "")}}
        mover, _db = NL._movers({"players": {}}, info)
        ok("Classics legend under his own id -> a new player", mover({"name": "Marcelo", "game_id": "34908"})[0] == "copy")
        ok("Classics legend under another Classics team -> a new player",
           mover({"name": "Fernandinho", "game_id": "51000"})[0] == "copy")
        ok("ML default player -> a new player", mover({"name": "Pedro Default", "game_id": "62000"})[0] == "copy")
        ok("a player of a club of the game still moves", mover({"name": "Joao Silva", "game_id": "61000"}) == ("move", "61000", False))
        mover, _db = NL._movers({"players": {}}, dict(info, clubs={}))
        ok("no club names (old caller): moves as before", mover({"name": "Marcelo", "game_id": "34908"})[0] == "move")
    finally:
        P.Squads = real
    print("%d failed" % N)
    sys.exit(1 if N else 0)


if __name__ == "__main__":
    main()
