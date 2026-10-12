"""python tools/test_league_edits.py

A rename of a game league (recipe edits.leagues) stays with the game's league: when that league
left the world and a new league took its regulation id, the new league keeps its own name
(Matheus 12.10.: his Serie C, rid 11, came out "Campeonato Carioca").
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import leaguebuilder as LB
import mkleague as M

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def regs_of(rids):
    regs = bytearray(M.REG * len(rids))
    for i, rid in enumerate(rids):
        regs[i * M.REG + M.R_ID:i * M.REG + M.R_ID + 2] = rid.to_bytes(2, "little")
        M.put_names(regs, i * M.REG, "OLD %d" % rid)
    return regs


edits = {"leagues": {"11": {"name": "Campeonato Carioca", "logo": "x.png"},
                     "12": {"name": "Paulistao"}}}
pl = {"leagues": [{"name": "Serie C", "rid": 11}], "edits": edits}

g = LB.game_league_edits(pl)
ok("the new league's rid drops its old rename", 11 not in g)
ok("a game league still there keeps its rename", g.get(12, {}).get("name") == "Paulistao")
ok("no new leagues: every rename applies", set(LB.game_league_edits({"edits": edits})) == {11, 12})

regs = regs_of([11, 12])
before = bytes(regs[:M.REG])
LB.apply_edits(edits, bytearray(), regs, log=lambda *a: None, leagues=g)
ok("Serie C's regulation untouched", bytes(regs[:M.REG]) == before)
ok("the game league renamed", b"Paulistao" in bytes(regs[M.REG:2 * M.REG]))

regs = regs_of([11, 12])
LB.apply_edits(edits, bytearray(), regs, log=lambda *a: None)
ok("old call (no leagues=) renames both", b"Campeonato Carioca" in bytes(regs[:M.REG]))
print("1..%d" % N)
