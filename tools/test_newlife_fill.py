"""python test_newlife_fill.py -- a prototype player who stays at a NewLife club comes to the
club's level (Risto 04.10.: clubs under 18 players had a top club's clones)"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lbplayers as N
import lbplayers as P
import playeredit as E


def main():
    assert N.fill_level([60, 62, 64, 70, 75], []) == 62
    assert N.fill_level([80], [55, 58, 60, 66]) == 58, "too few of its own: the league's"
    assert N.fill_level([], []) is None
    row = {n: "77" for n, _b in E.ABILITIES}
    row["Registered Position"] = "CF"
    got = dict(row, **N.at_level(row, 62))
    assert P.overall(got) == 62, P.overall(got)
    print("all passed")


if __name__ == "__main__":
    main()
