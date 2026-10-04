"""python tools/test_crestmatch.py -- the crest name matcher, plain asserts."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from crestmatch import match, words, score          # noqa: E402

N = 0


def check(got, want, what):
    global N
    N += 1
    assert got == want, "%s: got %r, wanted %r" % (what, got, want)


# 1. an exact name, extension and all
check(match(["Real Madrid.png"], [("Real Madrid", 7)]), [("Real Madrid.png", 7, 1.0)], "exact")

# 2. accents are folded on both sides
check(match(["Atletico Nacional.png"], [("Atlético Nacional", 3)]),
      [("Atletico Nacional.png", 3, 1.0)], "accents in the club name")
check(match(["Atlético Nacional.png"], [("Atletico Nacional", 3)]),
      [("Atlético Nacional.png", 3, 1.0)], "accents in the file name")

# 3. filler words on both sides
check(match(["cd_universidad_cesar_vallejo.png"], [("CD Universidad Cesar Vallejo", 11)]),
      [("cd_universidad_cesar_vallejo.png", 11, 1.0)], "filler words")
check(words("Club Atletico Deportivo La Coruna"), ["coruna"], "the filler list")

# 4. the crest pack's size suffixes come off
check(match(["alianza_lima_r_l.png"], [("Alianza Lima", 5)]),
      [("alianza_lima_r_l.png", 5, 1.0)], "_r_l")
check(match(["alianza_lima_r.png"], [("Alianza Lima", 5)]),
      [("alianza_lima_r.png", 5, 1.0)], "_r")
check(match(["alianza_lima_r_ll.png"], [("Alianza Lima", 5)]),
      [("alianza_lima_r_ll.png", 5, 1.0)], "_r_ll")

# 5. two clubs with similar names: the closer one wins, and it takes the file
got = match(["Sporting Cristal.png"], [("Sporting", 1), ("Sporting Cristal", 2)])
check(got, [("Sporting Cristal.png", 2, 1.0)], "the nearer of two similar clubs")

# 6. one club contains the other: 0.7, and the exact club wins 1.0
check(match(["Real Madrid.png"], [("Real Madrid Castilla", 9)]),
      [("Real Madrid.png", 9, 0.7)], "containment")
check(match(["Real Madrid.png"], [("Real Madrid Castilla", 9), ("Real Madrid", 8)]),
      [("Real Madrid.png", 8, 1.0)], "containment loses to the exact club")

# 7. nothing near enough is None, never a wrong guess
check(match(["Barcelona.png"], [("Bayern Munchen", 4)]), [("Barcelona.png", None, 0.0)], "no match")
check(match(["barcelona.png"], [("Bayern", 4)]), [("barcelona.png", None, 0.0)], "below 0.4")

# 8. a club is used once: the better of two files gets it, the other falls through
got = match(["Deportivo Cali.png", "Deportivo Cali 2.png"], [("Deportivo Cali", 6)])
assert got[0][1] == 6 and got[1][1] is None, "one club, one file: %r" % (got,)
N += 1

# 9. a file is used once: two clubs, two files, each file to its own club
got = match(["Alianza Lima.png", "Universitario.png"],
            [("Universitario de Deportes", 12), ("Alianza Lima", 13)])
check(sorted((f, i) for f, i, _s in got),
      [("Alianza Lima.png", 13), ("Universitario.png", 12)], "two files, two clubs")
check([f for f, _i, _s in got], ["Alianza Lima.png", "Universitario.png"], "output order")

# 10. numbers count as words
check(match(["1_fc_kaiserslautern.png"], [("1. FC Kaiserslautern", 2)]),
      [("1_fc_kaiserslautern.png", 2, 1.0)], "digits")

# 11. an empty side changes nothing
check(match([], [("Real Madrid", 7)]), [], "no files")
check(match(["Real Madrid.png"], []), [("Real Madrid.png", None, 0.0)], "no clubs")
check(match([], []), [], "nothing at all")

# 12. the score function on its own, including the 4-letter floor for containment
check(score(["real", "madrid"], ["real"]), 0.7, "containment score")
check(score(words("fc"), words("fc")), 0.0, "filler words leave nothing to score")
check(score(["abc"], ["abcdef"]), 0.0, "containment needs 4 letters")

print("all %d checks passed" % N)
