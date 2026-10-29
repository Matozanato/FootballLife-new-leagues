"""python tools/test_europe_count.py -- the European places counter (pepponeee 29.10.2026, mato
"Da"): every place of the world against the clubs each league phase takes straight in, in the
European places dialog and on the Plan step."""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fl26world as W

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


shipped = [e[2] for e in W.SHIPPED_ACCESS]
c = W.europe_count(shipped)
ok("the game's own list fills the three league phases", c == {0: (28, 28), 1: (20, 20), 2: (20, 20)})
ok("text, nothing over", W.europe_count_text(c) == "Champions League 28/28, Europa League 20/20, Conference League 20/20")
c = W.europe_count(shipped + [0, 1])
ok("a new league's places count over", c[0] == (29, 28) and c[1] == (21, 20)
   and "Champions League 29/28 (1 over)" in W.europe_count_text(c))
c = W.europe_count([0] * 20)
ok("no play-offs: room 36, the rest from the big five", c[0] == (20, 36)
   and "Champions League 20/36 (16 more from the big five)" in W.europe_count_text(c))
ok("no Conference League", set(W.europe_count(shipped, uecl=False)) == {0, 1})
print("1..%d" % N)
