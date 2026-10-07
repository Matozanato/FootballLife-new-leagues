"""The country cups' draw (0.2.0): the recipe's cup_draw becomes the world file's cupdraw line,
seeded unless the recipe says otherwise, and anything but seeded/random/off is refused

    python tools/test_cup_draw.py
"""
import os, re, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as LB
import fl26world

assert LB.cup_draw({}) == "seeded"
assert LB.cup_draw({"cup_draw": "Random "}) == "random"
assert LB.cup_draw({"cup_draw": "off"}) == "off"
try:
    LB.cup_draw({"cup_draw": "pots"})
    raise AssertionError("an unknown draw must be refused")
except LB.BuildError:
    pass

# the line the Lua side reads: `cupdraw seeded|random|off` (fl26swiss.lua read_world)
lua = open(os.path.join(os.path.dirname(__file__), "..", "sider", "experimental", "fl26swiss.lua"),
           encoding="utf-8").read()
assert 'line:match("^%s*cupdraw%s+(%S+)%s*(%S*)")' in lua
for v in LB.CUP_DRAWS:
    p = os.path.join(tempfile.mkdtemp(), "w.txt")
    fl26world.write_world(p, "_FL26_t", [], ccups=["cupdraw %s" % v])
    assert re.search(r"^cupdraw %s\r?$" % v, open(p, encoding="utf-8").read(), re.M)
print("ok")
