"""python tools/test_players_changed.py -- the Players changed column counts what was changed by hand.

Risto 05.11.2026: "40 players changed" for a club of the Worldpack nobody had touched. A club
from the NewLife Database has its whole squad among its edits (the release's players, the
stand-ins at the league's level), so the column showed the squad. Now a NewLife club counts only
the edits with something the release does not set (the rule Update my leagues keeps them by),
a club of the game that took a NewLife squad the same, and a club made by hand every edit.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from modstudio import newlife as N
from modstudio.pages import builder as BP

N_OK = 0


def ok(name, cond):
    global N_OK
    assert cond, name
    N_OK += 1
    print("ok %2d - %s" % (N_OK, name))


def main():
    field = sorted(N.RELEASE_FIELDS)[0]
    squad = {str(i): {"name": "Player %d" % i, field: 1} for i in range(40)}
    ok("a NewLife club nobody touched: 0", BP.changed_players({"edits": squad}, {"version": "1.6b4"}) == 0)
    mine = dict(squad, **{"3": {"name": "Player 3", "face": "x.dds"}})
    ok("a NewLife club with a face linked by hand: 1", BP.changed_players({"edits": mine}, {"version": "1.6b4"}) == 1)
    ok("a club of the game with a NewLife squad: 0",
       BP.changed_players({"edits": squad, "newlife_game": True}, False) == 0)
    ok("a club made by hand counts every edit", BP.changed_players({"edits": squad}, None) == 40)
    ok("no club, no edits: 0", BP.changed_players(None, None) == 0 and BP.changed_players({}, {"v": 1}) == 0)
    print("all passed")


if __name__ == "__main__":
    main()
