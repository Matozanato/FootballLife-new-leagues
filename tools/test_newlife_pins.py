"""python test_newlife_pins.py <folder with a Team.bin> -- a NewLife club keeps the world id it was
built with when a league before it changes or goes (0.1.8: the ids counted up in recipe order, so
removing or updating a league moved every later NewLife club's id and a Kit Server map.txt keyed
on it dressed the wrong club)"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B

NL = B.NEWLIFE_TEAMS[0]


def lg(name, nl, own=0):
    return {"name": name, "clubs": len(nl) + own, "newlife": {"clubs": list(nl) + [0] * own}}


def main(base):
    r = {"leagues": [lg("A", range(NL, NL + 12)), lg("B", range(NL + 100, NL + 112))]}
    m0, _f = B.newlife_tids(r["leagues"], base)
    assert B.pin_newlife(r, base) and not B.pin_newlife(r, base), "pinned once"
    assert B.newlife_tids(r["leagues"], base, r["newlife_ids"])[0] == m0, "the first Build's ids are kept"
    b_ids = {k: m0[k] for k in range(NL + 100, NL + 112)}

    del r["leagues"][0]                                    # A goes: B keeps its ids
    m1, _f = B.newlife_tids(r["leagues"], base, r["newlife_ids"])
    assert m1 == b_ids, (m1, b_ids)
    assert B.newlife_tids(r["leagues"], base)[0] != b_ids, "without pins they would move"

    r["leagues"].insert(0, lg("C", range(NL + 200, NL + 214), own=2))   # a new league before B
    m2, _f = B.newlife_tids(r["leagues"], base, r["newlife_ids"])
    assert all(m2[k] == v for k, v in b_ids.items())
    new = [m2[k] for k in range(NL + 200, NL + 214)]
    assert len(set(new) | set(b_ids.values())) == 26, "no id twice"
    B.pin_newlife(r, base)
    r["leagues"].insert(0, lg("A", range(NL, NL + 12)))     # A comes back: its old ids
    m3, _f = B.newlife_tids(r["leagues"], base, r["newlife_ids"])
    assert all(m3[k] == m0[k] for k in range(NL, NL + 12))
    assert len(set(m3.values())) == len(m3)
    print("all passed")


if __name__ == "__main__":
    main(sys.argv[1])
