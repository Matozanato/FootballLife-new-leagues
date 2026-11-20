"""python test_split_cid.py <folder with the game's tables> -- a split league never sits on a
competition id whose low byte is 0xff (the u8 "no competition" value), in a wide world (FL 2027)
no new league gets such an id, and a split past 255 goes under 255 (mp41). A league that is not a
split keeps the id the last Build gave it. (Bulgaria's empty groups in the 08.11.2026 Megapack
were a match id twin, fixed in fl26match; this rule stays as a guard.)"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def recipe(split):
    L = {"name": "Parva Test", "country": "Bulgaria", "clubs": 14, "legs": 2}
    if split:
        L["split"] = {"legs": 2, "groups": [4, 4, 6], "group_legs": 1}
    M = {"name": "Vtora Test", "country": "Bulgaria", "clubs": 16, "legs": 2, "above": "Parva Test"}
    return {"world": "_TestSplitCid", "leagues": [L, M]}


def cids(pl):
    return {p["name"]: p["cid"] for p in pl["leagues"]}


def main(base):
    ok("ff_cid: 255, 511, 767, 1023 and nothing else", [c for c in range(1024) if B.ff_cid(c)] == [255, 511, 767, 1023])
    first = cids(B.plan(recipe(True), base))
    print("# first Build:", first)
    ok("a first Build gives no league an id ending in 0xff", not any(B.ff_cid(c) for c in first.values()))
    # the last Build put both leagues on 255 and 511 (the plan's names keep them)
    prev = {"leagues": [{"name": "Parva Test", "cid": 255}, {"name": "Vtora Test", "cid": 511}]}
    if B.W.CID_MAX < 511:
        prev["leagues"][1]["cid"] = first["Vtora Test"]
    split = cids(B.plan(recipe(True), base, prev))
    print("# split, built on 255 before:", split)
    ok("the split leaves 255 for another id", split["Parva Test"] != 255 and not B.ff_cid(split["Parva Test"]))
    ok("the league that is not a split keeps its id", split["Vtora Test"] == prev["leagues"][1]["cid"])
    plain = cids(B.plan(recipe(False), base, prev))
    ok("the same league with no split keeps 255", plain["Parva Test"] == 255)
    # mp40 (08.11.): moved to 703, the split's low byte (191) was the Nigeria National League's id,
    # and its groups again never started. A split past 255 takes no other league's id as low byte.
    ok("split_alias: past 255 the low byte is another league's id, or 0xff",
       B.split_alias(703, {191}) and not B.split_alias(703, {190}) and not B.split_alias(191, {191})
       and B.split_alias(255, set()) and B.split_alias(768, set()) and B.split_alias(512, set()))
    B.W.set_cid_wide(True)            # FL 2027's ids past 255 (the caps set's cidwide step)
    if B.W.CID_MAX >= 703:
        prev = {"leagues": [{"name": "Parva Test", "cid": 703}, {"name": "Vtora Test", "cid": 191}]}
        moved = cids(B.plan(recipe(True), base, prev))
        print("# split on 703, the league below on 191:", moved)
        ok("the split leaves 703 for an id under 255", moved["Parva Test"] < 0xff)
        ok("... and the other league keeps 191", moved["Vtora Test"] == 191)
        kept = cids(B.plan(recipe(True), base, {"leagues": [{"name": "Parva Test", "cid": 703},
                                                             {"name": "Vtora Test", "cid": 190}]}))
        print("# split on 703, nothing on 191:", kept)
        ok("mp41: a split past 255 goes under 255 even with nothing on its low byte",
           kept["Parva Test"] < 0xff and kept["Vtora Test"] == 190)
        # no free id under 255: the split swaps with the league that is no split
        B_rest = B.W.cid_pool
        try:
            B.W.cid_pool = lambda a, b: [c for c in B_rest(a, b) if c >= 0xff or c == 190]
            swap = cids(B.plan(recipe(True), base, {"leagues": [{"name": "Parva Test", "cid": 769},
                                                                 {"name": "Vtora Test", "cid": 190}]}))
        finally:
            B.W.cid_pool = B_rest
        print("# no free id under 255, split on 769, the other on 190:", swap)
        ok("... with none free it swaps with the league that is no split",
           swap["Parva Test"] == 190 and swap["Vtora Test"] == 769)
    B.W.set_cid_wide(False)
    print("all %d passed" % N)


if __name__ == "__main__":
    main(sys.argv[1])
