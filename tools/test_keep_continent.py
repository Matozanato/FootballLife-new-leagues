"""python test_keep_continent.py -> a drag on the Leagues page keeps each continent's Build places

The Leagues page groups by continent; before, saving its order sorted the whole recipe that way,
so North American and Oceanian leagues always ended last and lost their Select Team places."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from modstudio.pages.leagues import keep_continent_places

confeds = {"Mexico": 6, "Serbia": 2, "Fiji": 7, "Spain": 2, "Guatemala": 6}
L = lambda n, c: {"name": n, "country": c}
recipe = [L("Liga MX", "Mexico"), L("SuperLiga", "Serbia"), L("OFC", "Fiji"),
          L("Segunda", "Spain"), L("Guatemala", "Guatemala")]
# on screen: Europe first, Segunda dragged above SuperLiga; N. America Guatemala above Liga MX
keys = ["oSegunda", "oSuperLiga", "oGuatemala", "oLiga MX", "oOFC"]
got = [x["name"] for x in keep_continent_places(recipe, keys, confeds)]
want = ["Guatemala", "Segunda", "OFC", "SuperLiga", "Liga MX"]
assert got == want, got
# nothing dragged: the recipe stays as it is
keys = ["oSuperLiga", "oSegunda", "oLiga MX", "oGuatemala", "oOFC"]
assert [x["name"] for x in keep_continent_places(recipe, keys, confeds)] == [x["name"] for x in recipe]
print("ok")
