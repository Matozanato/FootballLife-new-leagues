"""python test_keep_continental.py <folder with the game's tables> -- a club of the game moved into
a new league can keep its continental places (#84, "keep"): no club has to take its place when
the continent is all it plays, and with a swap the other club gets only the league and cup rows
(0.1.8: Build asked for a swap, and the swap took the Libertadores place as well)"""
import os, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B
import mkleague as M


def entries(db, tid):
    ents = M.load(db, "CompetitionEntry.bin")
    return sorted(ents[o + M.E_CID] for o in range(0, len(ents), M.ENT)
                  if int.from_bytes(ents[o + M.E_TEAM:o + M.E_TEAM + 4], "little") == tid)


def recipe(gc):
    return {"world": "_TestKeep84", "leagues": [{"name": "Test League", "country": "Croatia", "clubs": 12, "legs": 2,
                                                 "game_clubs": gc}]}


def build(base, game, gc):
    pl = B.plan(recipe(gc), base)
    B.build(pl, base, game, replace=True, log=lambda *a: None)
    return os.path.join(B.siderdir.find(game), "livecpk", "_TestKeep84", "common", "etc", "pesdb")


def main(base):
    info = B.game_info(base)
    cont = lambda t: set(info["entries"].get(t) or []) - info["friendly_cids"]
    only = next(t for t in sorted(info["entries"]) if cont(t) and cont(t) <= B.CONTINENTAL_CIDS
                and not B.game_club_problem(info, t))
    both = next(t for t in sorted(info["entries"]) if cont(t) & B.CONTINENTAL_CIDS and cont(t) & info["league_cids"]
                and not B.game_club_problem(info, t))
    free = next(t for t in sorted(info["clubs"]) if not info["entries"].get(t) and not B.game_club_problem(info, t))
    game = tempfile.mkdtemp(prefix="keep84-")
    try:
        try:
            B.plan(recipe([{"at": 0, "id": only}]), base)
            raise AssertionError("no keep, no swap: Build must ask for one")
        except B.BuildError:
            pass
        db = build(base, game, [{"at": 0, "id": only, "keep": True}])
        assert set(entries(db, only)) >= cont(only), (entries(db, only), cont(only))
        print("only continental: %s keeps %s" % (info["clubs"][only][0], sorted(cont(only))))

        try:
            B.plan(recipe([{"at": 0, "id": both, "keep": True}]), base)
            raise AssertionError("its league still needs a club in its place")
        except B.BuildError:
            pass
        db = build(base, game, [{"at": 0, "id": both, "keep": True, "swap": free}])
        mine, theirs = set(entries(db, both)), set(entries(db, free))
        assert cont(both) & B.CONTINENTAL_CIDS <= mine, mine
        assert not theirs & B.CONTINENTAL_CIDS and cont(both) - B.CONTINENTAL_CIDS <= theirs, theirs
        print("league and continent: %s keeps %s, %s takes %s"
              % (info["clubs"][both][0], sorted(mine & B.CONTINENTAL_CIDS), info["clubs"][free][0], sorted(theirs)))

        db = build(base, game, [{"at": 0, "id": both, "swap": free}])
        assert cont(both) <= set(entries(db, free)), "without keep the swap takes every place, as before"
    finally:
        shutil.rmtree(game, ignore_errors=True)
    print("all passed")


if __name__ == "__main__":
    main(sys.argv[1])
