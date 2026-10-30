"""B290 (Micarodvzla22 30.10.): a group of clubs in no league -- the Europack's "Croatian clubs
(no league)" -- is no league of the UEFA key. It took rank 21 when the ranking was OKed, the
places the key gave it were lost at Build (a group has no table: plan() keeps it out of the
leagues), and the real Croatian league came one rank lower.

    python tools/test_uefa_others.py
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B
import mkleague as M
import uefakey as U

B.game_europe_tops = lambda base: []
B.game_league_countries = lambda base: {}
B.country_confederations = lambda base: {"Croatia": 2, "Serbia": 2, "Venezuela": 4}
M.load = lambda base, name: b""

recipe = {"leagues": [{"name": "SuperSport HNL", "country": "Croatia", "clubs": 10},
                      {"name": "Croatian clubs (no league)", "country": "Croatia", "clubs": 5,
                       "others": "europe"},
                      {"name": "Mozzart Bet SuperLiga", "country": "Serbia", "clubs": 16},
                      {"name": "Liga FUTVE 2", "country": "Venezuela", "clubs": 16}]}
ids = [c["id"] for c in U.candidates(recipe, None)]
assert ids == ["SuperSport HNL", "Mozzart Bet SuperLiga"], ids

# a ranking saved with the group in it (OK pressed in 0.2.5) drops it the next time
recipe["uefa_rank"] = ["SuperSport HNL", "Croatian clubs (no league)", "Mozzart Bet SuperLiga"]
on, off = U.ranked(recipe, None)
assert [c["id"] for c in on] == ["SuperSport HNL", "Mozzart Bet SuperLiga"], on
assert off == [], off
print("ok")
