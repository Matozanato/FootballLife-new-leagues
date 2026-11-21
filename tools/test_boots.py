"""The boots and gloves of a world's new players (lbboots; mato 13.11.2026: every new player of
the GigaPack wore the same black boots): the world's lists keep the game's lines, give every new
player a model a player of the game wears, the same at every Build, in the order the game
searches by.

    python tools/test_boots.py
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lbboots

ok = 0


def check(what, cond):
    global ok
    if not cond:
        raise SystemExit("FAIL: " + what)
    ok += 1


game = [(10, 1010), (20, 2020), (30, 3030), (40, 62), (50, 2020), (900, 5019), (70000, 4021)]
game_ids = {10, 20, 30, 40, 50}                 # 900 and 70000: lines of players the game no longer has
packed = lbboots.write(game)
check("packed as the game's own (ff 10 81 WESYS)", packed[:8] == b"\xff\x10\x81WESYS")
check("read gives the lines back", lbboots.read(packed) == sorted(game))
check("unpacked bytes read too", lbboots.read(b"".join(__import__("struct").pack("<II", *l) for l in game)) == game)
try:
    lbboots.read(b"123")
    check("a list that is not records of 8 bytes is refused", False)
except ValueError:
    check("a list that is not records of 8 bytes is refused", True)

new = [60, 61, 62, 900, 70000, 150000]
lines, n = lbboots.merged(game, game_ids, new, {62, 1010, 2020, 3030})
d = dict(lines)
check("every new player got a line", n == len(new) and all(p in d for p in new))
check("the game's lines stay as they are", all(d[p] == m for p, m in game if p in game_ids))
check("the order of the ids, each id once", lines == sorted(lines) and len(d) == len(lines))
check("a new player wears what a player of the game wears", all(d[p] in {62, 1010, 2020, 3030} for p in new))
check("a line the game kept for an id that is a new player's now is not his",
      d[900] != 5019 and d[70000] != 4021)
again, _n = lbboots.merged(list(reversed(game)), game_ids, list(reversed(new)), {62, 1010, 2020, 3030})
check("the same at every Build", again == lines)

many = list(range(1000, 3000))
lines, _n = lbboots.merged(game, game_ids, many, None)
worn = {dict(lines)[p] for p in many}
check("the makes are spread: every model of the game is worn", worn == {1010, 2020, 3030, 62})
share = sum(1 for p in many if dict(lines)[p] == 2020) / len(many)
check("as often as in the game (2020 is worn by two of five)", 0.33 < share < 0.47)

lines, _n = lbboots.merged(game, game_ids, new, {7777})
check("no model of the table is worn: the pool is the whole list's", all(dict(lines)[p] in {1010, 2020, 3030, 62} for p in new))
lines, n = lbboots.merged([], set(), new, None)
check("a game without a list: nothing made up", (lines, n) == ([], 0))
lines, n = lbboots.merged(game, game_ids, [], None)
check("a world without new players: the game's list", n == 0 and lines == sorted(game))

import struct
table = b"".join(struct.pack("<HH", i, k) + bytes(300) for k, i in enumerate((62, 1010, 5019)))
check("the models of Boots.bin", lbboots.models(table, lbboots.BOOTS_REC) == {62, 1010, 5019})
check("a 16-bit model: the game reads the low word", all(0 < m < 65536 for _p, m in lbboots.read(packed)))
print("test_boots: %d ok" % ok)
