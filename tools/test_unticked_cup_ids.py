r"""python tools/test_unticked_cup_ids.py [<folder with the game's tables>]

B273 (juanjose6124 29.10.2026): the Worldpack with new leagues on top stopped Build with "no free
competition ids left". He unticked the national cups and super cups of leagues he did not need,
and Build still said the same: the cups' ids of the last Build stayed held for every league still
in the recipe, ticked or not, until one more Build. An unticked cup now gives its id back at once;
a ticked one keeps its own, as a career needs (audit 12.10.).
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import leaguebuilder as B
import mkleague as M

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def league(name, cup, supercup=False, league_cup=False):
    return {"name": name, "country": {"A": "Croatia", "B": "Serbia"}[name], "clubs": 12, "legs": 2,
            "cup": cup, "supercup": supercup, "league_cup": league_cup}


def main(base):
    ids = {"cup:A": {"cid": 1}, "super:A": {"cid": 2}, "ccup:FL_007_LCUP": {"cid": 3},
           "cup:B": {"cid": 4}, "super:B": {"cid": 5}, "ccup:FL_008_LCUP": {"cid": 6},
           "gsuper:X": {"cid": 7}, "ccup:FL_UCL": {"cid": 8}}
    pins = {"a": {"rid": 7}, "b": {"rid": 8}}
    got = B.ticked_cups(ids, [league("A", False, True, False), league("B", True, True, True)], ["A", "B"], pins)
    ok("an unticked cup, its super cup and league cup give their ids back",
       not {"cup:A", "super:A", "ccup:FL_007_LCUP"} & set(got))
    ok("ticked cups keep theirs, and the game's and continental cups stay", got == {k: ids[k] for k in
       ("cup:B", "super:B", "ccup:FL_008_LCUP", "gsuper:X", "ccup:FL_UCL")})
    got = B.ticked_cups(ids, [league("A", True, False), league("B", True, True)], ["A", "B"], pins)
    ok("the super cup alone unticked: the cup keeps its id", "cup:A" in got and "super:A" not in got)
    ok("the input is not changed", len(ids) == 8)

    # a world with every free id held: the last Build's cups of league A take what is left
    comp = M.load(base, "Competition.bin")
    used = {comp[i + M.CID_OFF] for i in range(0, len(comp), M.COMP)}
    pool = [c for c in B.W.cid_pool(B.CID_FROM, False) if c not in used and c != B.UECL_CID]
    fill = {"ccup:FILL%d" % i: {"cid": c} for i, c in enumerate(pool[2:])}
    prev = {"leagues": [], "cup_ids": dict({"cup:A": {"cid": pool[0]}, "super:A": {"cid": pool[1]}}, **fill)}
    try:
        B.plan({"world": "_FL26CupIds", "leagues": [league("A", True, True), league("B", False)]}, base, prev)
        ok("cups ticked: no id for the leagues", False)
    except B.BuildError as e:
        ok("cups ticked: no id for the leagues (%s)" % e, "no free competition ids" in str(e))
    pl = B.plan({"world": "_FL26CupIds", "leagues": [league("A", False), league("B", False)]}, base, prev)
    cids = sorted(p["cid"] for p in pl["leagues"])
    ok("cups unticked: the two leagues take the cups' ids (%s)" % cids, cids == sorted(pool[:2]))
    ok("and the plan holds them no more for the cups", not {"cup:A", "super:A"} & set(pl["prev_cup_ids"]))
    print("test_unticked_cup_ids: ok (%d)" % N)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "D:/dev/fl26-modding-research/out/base-pesdb")
