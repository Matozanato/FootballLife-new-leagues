"""python test_newlife_link.py <NewLife folder> <folder with the game's tables> -- B314 (03.11.): a
NewLife league of a country the game has a league of goes in as the division below that league
(link_below_game), so Greek Super League 2 has promotion and relegation with the game's Greek
league; a second league of the same country, a country with no league of the game, a league with
a division of its own and an exhibition league are left as they are"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B
from modstudio import newlife as N


def synthetic():
    parents = [(117, "Super League"), (50, "Bundesliga"), (7, "Liga A"), (8, "Liga B")]
    countries = {117: "Greece", 50: "Germany", 7: "Chile (12)", 8: "Chile"}
    r = {"leagues": [{"name": "SL2", "country": "Greece"}, {"name": "Gamma", "country": "Greece"},
                     {"name": "Own", "country": "Germany", "above": "Mine"},
                     {"name": "Show", "country": "Germany", "exhibition": True},
                     {"name": "Two", "country": "Chile"}, {"name": "None", "country": "Iceland"}]}
    out = N.link_below_game(r, [("Gamma", 40), ("SL2", 55), ("Own", 50), ("Show", 50), ("Two", 50),
                                ("None", 50)], parents, countries)
    x = {L["name"]: L for L in r["leagues"]}
    assert out == [("SL2", 117, "Super League")], out
    assert x["SL2"]["above"] == 117, "the strongest Greek league goes under the game's"
    assert "above" not in x["Gamma"], "one league under a league: the second stays a division of its own"
    assert x["Own"]["above"] == "Mine", "a division the person set stays"
    assert "above" not in x["Show"], "an exhibition league stands alone"
    assert "above" not in x["Two"], "two leagues of the game in the country (a duplicate name): no guess"
    assert "above" not in x["None"], "no league of the game in the country"
    # a league already under the game's league: the next one added does not go there too
    r2 = {"leagues": [{"name": "A", "country": "Greece", "above": "117"}, {"name": "B", "country": "Greece"}]}
    assert N.link_below_game(r2, [("B", 50)], parents, countries) == [] and "above" not in r2["leagues"][1]


def real(folder, base):
    rel, info = N.Release(folder), B.game_info(base)
    names = dict((i, n) for n, i in B.country_ids(base))
    rows = rel.leagues(lambda c: names.get(int(c), "").split(" (")[0], info)
    # the release's own Greek Super League 1 is the game's league: the NewLife page does not add it
    # (gamekeys, _game_targets), it comes in by Bring the game's leagues
    game = {tuple(L["key"]) for L in N._game_targets(rel, info)[0].values()}
    greek = [L for L in rows if L["country"] == "Greece" and N.fits(L, info) and tuple(L["key"]) not in game]
    assert greek, "the release has a Greek league to add"
    L = greek[0]                                   # strongest first within a country
    r = {"leagues": []}
    name, _s, _e = N.add_league(r, rel, L, info=info)
    parents = B.shipped_parents(base)
    countries = B.game_league_countries(base)
    up = [rid for rid, _n in parents if (countries.get(rid) or "").split(" (")[0] == "Greece"]
    assert len(up) == 1, "the game has one Greek league with no league below it: %s" % up
    out = N.link_below_game(r, [(name, L["strength"])], parents, countries)
    assert out and out[0][:2] == (name, up[0]), out
    assert r["leagues"][0]["above"] == up[0]
    print("%s goes under %s [%d]" % (name, out[0][2], up[0]))


if __name__ == "__main__":
    synthetic()
    if len(sys.argv) > 2:
        real(*sys.argv[1:3])
    print("all passed")
