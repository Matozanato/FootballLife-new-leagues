"""The header's PACK box names the pack of the world in the game (B168, 20.10.2026: after Activate
of r12 it still said FL26-Modpack-Europe-eu4, the zip installed last, while ACTIVE WORLD said
_FL26M2400S). installer.header_pack, no window and no game folder.

    python tools/test_header_pack.py
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modstudio import installer as I

R12 = {"name": "FL26-Modpack-NL15B7-r12", "time": "2026-10-18T10:00:00", "world": "_FL26M2400S"}
EU4 = {"name": "FL26-Modpack-Europe-eu4", "time": "2026-10-19T10:00:00", "world": "_FL26M2400E"}
R12_OLD = {"name": "FL26-Modpack-NL15B6-r11", "time": "2026-10-10T10:00:00", "world": "_FL26M2400S"}
BOARDS = {"name": "Scoreboards 86", "time": "2026-10-17T10:00:00", "parts": [["scoreboard", "x"]]}
NL = {"name": "NewLife 1.5b7", "time": "2026-10-16T10:00:00", "parts": [["world", "_FL26NL15"], ["kits", "k"]]}
N = 0


def check(got, want, what):
    global N
    N += 1
    assert got is want, "%s: got %r, wanted %r" % (what, got and got.get("name"), want and want.get("name"))


check(I.header_pack([R12, EU4], ["_FL26M2400S"]), R12, "Activate of r12 after eu4 was installed: r12")
check(I.header_pack([R12, EU4], ["_FL26M2400E"]), EU4, "eu4 in the game: eu4")
check(I.header_pack([R12_OLD, R12, EU4], ["_FL26M2400S"]), R12, "the newest install of the world in the game")
check(I.header_pack([R12, NL, EU4], ["_FL26NL15"]), NL, "a world among a record's parts")
check(I.header_pack([R12, EU4, BOARDS], ["_FL26Mine"]), BOARDS,
      "a world built on this PC: the newest pack that brought no world, not another world's")
check(I.header_pack([R12, EU4], ["_FL26Mine"]), None, "a world built here and only other worlds' packs: none")
check(I.header_pack([R12, EU4, BOARDS], []), BOARDS, "no world in the game: the newest pack without one")
check(I.header_pack([], ["_FL26M2400S"]), None, "nothing installed")
print("header pack: %d checks passed" % N)
