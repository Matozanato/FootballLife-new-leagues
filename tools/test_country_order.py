"""League order (0.2.0) reads the recipe's country_order, never league_order -- the Leagues
page's drag order since 0.1.8, league keys that matched no country and still reordered Kick Off

    python tools/test_country_order.py
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as LB

LB.order_countries = lambda pl, base, confed: [("England", 2), ("Spain", 2), ("Argentina", 4), ("Japan", 3)]

drag = {"league_order": ["g17", "oPrva NL", "g7"]}
assert LB.country_rank(drag, None, {}) is None, "the drag order must not rank countries"
assert LB.kickorder_lines(drag, None, {}) == []

az = {"country_order": "az", "league_order": ["g7"]}
assert LB.country_rank(az, None, {}) == {"Argentina": 0, "England": 1, "Japan": 2, "Spain": 3}

own = {"country_order": ["Japan", "Spain"]}
assert LB.country_rank(own, None, {}) == {"Japan": 0, "Spain": 1, "England": 2, "Argentina": 3}
print("ok")
