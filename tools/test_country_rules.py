"""country_rules (23.11.2026, Argentina): the recipe key, the zones' smaller size, the league package carrying it, and
the Argentine rules' own pieces. Plain asserts: python tools/test_country_rules.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B
import lbpackage as P

# the key is a recipe setting: a world made editable again keeps it, and it counts as an edit
assert "country_rules" in B.RECIPE_SETTINGS
assert B.has_edits({"country_rules": ["argentina"]})

# a zone a regional pyramid moves clubs between may be small; any other league keeps the minimum
assert B.clubs_min({"mover": "regional"}) == B.CLUBS_MIN_ZONE == 2
assert B.clubs_min({}) == B.CLUBS_MIN
assert B.max_legs(3, B.clubs_min({"mover": "regional"})) > 0
assert B.max_legs(3) == 0 or B.CLUBS_MIN <= 3

# a league package brings the rules its leagues need, and takes back only what it brought
recipe = {"world": "_FL26Test", "leagues": []}
man = {"name": "Argentina", "author": "t", "version": "1"}
piece = {"leagues": [{"name": "Primera Nacional", "country": "Argentina", "clubs": 18}], "country_rules": ["argentina"]}
tag = P.add(recipe, man, piece, "x")
assert recipe["country_rules"] == ["argentina"]
P.remove(recipe, tag)
assert "country_rules" not in recipe and recipe["leagues"] == []
recipe = {"world": "_FL26Test", "leagues": [], "country_rules": ["argentina"]}   # there before: it stays
tag = P.add(recipe, man, piece, "x")
P.remove(recipe, tag)
assert recipe["country_rules"] == ["argentina"]

# the Argentine rules: the Copa Argentina is a knockout of 64 in six rounds (the 2026 real draw: 32 ties), the
# Recopa a triangular, the Sudamericana's field six Argentine and six Brazilian places at most
import argentina
from argentina import copas
ca = next(c for c in copas.CUPS if c["code"] == "CA")
assert len(ca["rounds"]) == 6 and len(ca["ties"]) == 63 and len(ca["y1"][1]) == 32
rc = next(c for c in copas.CUPS if c["code"] == "RC")
assert rc["flags"] == 4 and len(rc["ties"]) == 3 and len(rc["groups"][0]) == 6
line = ("ccup 255 ko=256 groups=8 entry=" + ",".join("30:%d" % k for k in range(1, 14)) + ",29:7,29:13,67:3,168:3"
        + " fill=49 name=Copa Sudamericana")
out = argentina.sud_field(line)
ent = out.split("entry=")[1].split(" ")[0].split(",")
assert sum(e.startswith("30:") for e in ent) == 6 and "29:13" not in ent and len(ent) == 17
assert argentina.sud_field("league 11 cid=130") == "league 11 cid=130"
print("test_country_rules: ok")
