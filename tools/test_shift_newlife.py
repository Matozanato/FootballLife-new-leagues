"""Remove club / Insert club move the league's NewLife ids with the places (Discord, lub7628:
a removed Schalke kept its id, NewLife's two-leagues check still found it, and Build read the
ids of the clubs after it one place off)

    python tools/test_shift_newlife.py
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modstudio.project import Project

p = Project(None)
p.recipe["leagues"] = [{"name": "Bundesliga 2", "clubs": 12, "club_names": ["N%d" % i for i in range(12)],
                        "newlife": {"version": "1", "clubs": [101, 102, 103, 104]}}]
assert p.shift_places("Bundesliga 2", 1, -1)
L = p.recipe["leagues"][0]
assert L["newlife"]["clubs"] == [101, 103, 104], L["newlife"]
assert L["club_names"][:3] == ["N0", "N2", "N3"]
assert p.shift_places("Bundesliga 2", 0, 1)
assert L["newlife"]["clubs"] == [0, 101, 103, 104], L["newlife"]
assert p.shift_places("Bundesliga 2", 9, -1)             # past the NewLife ones: they stay
assert L["newlife"]["clubs"] == [0, 101, 103, 104]
print("ok")
