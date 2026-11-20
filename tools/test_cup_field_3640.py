"""python test_cup_field_3640.py -- a new country's national cup of 33..43 clubs (its two divisions)
that no shipped cup has exactly: FL 2026 cuts it to the 32 the bracket screen draws (#95), FL 2027
keeps the larger shipped field under it, 36 or 40 (the Coupe de France's, as cup_join plays them),
mato 08.11.: "play cups of 33-43 as 36/40 instead of cutting them to 32"."""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B

N = 0


def ok(name, cond):
    global N
    print(("ok    " if cond else "FAIL  ") + name)
    N += 0 if cond else 1


def field(top, low, fl27):
    B.FL27 = fl27
    p = {"own_cup": {}, "clubs": top, "rid": 900}
    below = {"clubs": low, "rid": 901}
    B.national_cup(p, below)
    return p["own_cup"]["clubs"], p["own_cup"]["like"]


def main():
    try:
        for top, low, f26, f27 in ((18, 20, 32, 36), (20, 22, 32, 40), (16, 17, 32, 32), (20, 23, 32, 40),
                                   (18, 18, 32, 36), (22, 22, 44, 44), (16, 16, 32, 32)):
            a = field(top, low, False)[0]
            b, like = field(top, low, True)
            ok("%d + %d: FL26 %d (%d), FL27 %d (%d)" % (top, low, f26, a, f27, b), a == f26 and b == f27)
            if b in B.CUP_JOIN_SIZES:
                ok("  FL27 %d is the FA Cup copy, whose calendar dates every round" % b, like == B.NATIONAL_CUP_ANY[0])
        ok("every FL27 field past 32 leaves 64 - n byes the bracket screen has",
           all(64 - k in B.BRACKET_SIZES for k in B.CUP_JOIN_SIZES))
    finally:
        B.FL27 = False
    print("%d failed" % N)
    sys.exit(1 if N else 0)


if __name__ == "__main__":
    main()
