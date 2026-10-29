"""B250 (monkusgigus 26.10.): a world with no UEFA ranking of its own lists the qualifying's places
by association rank, the world's and the shipped ones alike -- the Europack's 31 new Champions
League qualifying places came first and the Greek champion, Portugal's second and Belgium's got
nothing. With a ranking (uefa_seed) or no rank at all the order stands as it was.

    python tools/test_uefa_rank.py
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fl26world as W
import leaguebuilder as LB

# forty new champions, each a weak association's, all in the Champions League qualifying
own = [(900 + i, 1, W.UCLQ, 0) for i in range(40)]
greece = (W._GRE, 1, W.UCLQ, 0)

old, _ = W.uefa_places(own)
q = [e for e in old if e[2] == W.UCLQ]
assert q[:40] == own, "no rank: the world's own places still come first"

rank = {r: n for n, r in enumerate([W._ENG, W._ITA, W._ESP, W._GER, W._FRA, W._NED, W._POR, W._BEL,
                                     W._TUR, W._GRE, W._SCO, W._DEN])}
rank.update({900 + i: 30 + i for i in range(40)})
new, _ = W.uefa_places(own, rank=rank)
q = [e for e in new if e[2] == W.UCLQ]
assert greece in q
assert q.index(greece) < q.index(own[0]), "ranked: the Greek champion goes before the new leagues"
ranks = [rank.get(W.place_league(e), W.UNRANKED) for e in q]
assert ranks == sorted(ranks), ranks
assert sorted(new) == sorted(old), "the rank only reorders, it never adds or drops a place"
assert [e for e in new if e[2] != W.UCLQ and e[2] not in W.PLAYOFFS] == \
       [e for e in old if e[2] != W.UCLQ and e[2] not in W.PLAYOFFS], "direct places keep their order"

# the plan carries the rank as JSON (string keys); a seeded world ignores it
assert LB.place_rank({"assoc_rank": {"117": 11, "900": 30}}) == {117: 11, 900: 30}
assert LB.place_rank({"assoc_rank": {"117": 11}, "uefa_seed": {"x": 1}}) is None
assert LB.place_rank({}) is None
assert LB.place_rank({"assoc_rank": ["bad"]}) is None
assert W.ACCESS_COUNTRY[W._GRE] == "Greece"
print("ok")
