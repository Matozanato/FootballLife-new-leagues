"""python test_newlife_gameclubs.py <NewLife folder> <folder with the game's tables> -- a NewLife
league's clubs the game already has (game_clubs) get the release's squad too, as a league of the
game does under Bring the game's leagues to this season (13.10.: they kept the game's own, so
Iker Almena sat at Hajduk while the release had him at Dinamo); Update my leagues gives it
again rather than twice, and Remove league takes it away"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B
import lbplayers as P
from modstudio import newlife as N
from modstudio import project


def main(folder, base):
    rel, info = N.Release(folder), B.game_info(base)
    rows = rel.leagues(str)
    L = next(x for x in rows if len(x["in_game"]) >= 2 and rel.squad(x["in_game"][0]))
    r = {"leagues": []}
    name, _s, _e = N.add_league(r, rel, L, info=info)
    x = r["leagues"][-1]
    gcs = [str(e["id"]) for e in x["game_clubs"]]
    assert gcs, "the league has clubs of the game"
    pl = r["players"]
    for t in gcs:
        c = pl[t]
        assert c.get("newlife_game") and c.get("edits"), "club of the game %s got the release's squad" % t
        assert any(set(ch) & set(P.FIELDS) for ch in c["edits"].values()), "with the release's fields"
    nl_only = [k for k in pl if k.rpartition("/")[0] == name]
    assert len(nl_only) == len(L["clubs"]), "and the NewLife clubs keep theirs"
    # the same player is not at a NewLife club and at a club of the game at once
    joins = [g for c in pl.values() for g in c.get("join") or []]
    assert len(joins) == len(set(joins)), "a player joins one club"

    before = {t: dict(pl[t]) for t in gcs}
    N.update_league(r, rel, x, rows, info=info)
    x = r["leagues"][-1]
    assert sorted(str(e["id"]) for e in x["game_clubs"]) == sorted(gcs), "the same clubs of the game"
    for t in gcs:
        assert pl[t].get("newlife_game"), "update gives the squad again"
        assert sorted(pl[t].get("join") or []) == sorted(before[t].get("join") or []), "the same joins, not twice"

    p = project.Project.__new__(project.Project)
    p.recipe = r
    p.drop_league(name)
    for t in gcs:
        assert t not in pl, "Remove league takes the release's squad of %s away" % t
    print("all passed")


if __name__ == "__main__":
    main(*sys.argv[1:3])
