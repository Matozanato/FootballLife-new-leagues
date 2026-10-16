"""python test_newlife_twoleagues.py

B62 (16.10., Discord): adding a NewLife league said "Milton Keynes Dons would play in two leagues
(the recipe and Sky Bet League One)" and the person could not find the club in any league of the
world: a club renamed in a league keeps its NewLife link. Now the message names the world's league
and the name the club has there. No game, no NewLife folder: the page's add() with stand-ins."""
import os, sys
from types import SimpleNamespace as NS

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from modstudio.pages import newlife as PN

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def run(recipe, sel):
    said = []
    PN.error = lambda parent, title, text: said.append(text)
    me = NS(info=lambda: None, addable=lambda info: sel, project=NS(recipe=recipe),
            rel=NS(clubs={"100267": {"name": "Milton Keynes Dons"}, "5": {"name": "Five"}}))
    PN.NewLife.add(me)
    return said


def main():
    two = {"name": "Sky Bet League Two", "clubs": 3, "club_names": ["A", "Bletchley Town", "C"],
           "newlife": {"clubs": [7, 100267, 0]}}
    said = run({"leagues": [two]}, [{"name": "Sky Bet League One", "clubs": ["100267", "5"], "country": 204}])
    ok("one message", len(said) == 1)
    ok("... names the league of the world and the name the club has there: %r" % said[:1],
       "Sky Bet League Two" in said[0] and "Bletchley Town" in said[0] and "Sky Bet League One" in said[0]
       and "Milton Keynes Dons" in said[0])
    two["club_names"][1] = ""
    said = run({"leagues": [two]}, [{"name": "Sky Bet League One", "clubs": ["100267"], "country": 204}])
    ok("a place with no name: the league alone, no dangling colon: %r" % said[:1],
       "Sky Bet League Two" in said[0] and ":" not in said[0].split("(")[1])
    said = run({"leagues": []}, [{"name": "L1", "clubs": ["100267"], "country": 204},
                                 {"name": "L2", "clubs": ["100267"], "country": 204}])
    ok("two picked leagues with one club: both named, as before", len(said) == 1 and "L1" in said[0]
       and "L2" in said[0])
    print("test_newlife_twoleagues: ok (%d)" % N)


if __name__ == "__main__":
    main()
