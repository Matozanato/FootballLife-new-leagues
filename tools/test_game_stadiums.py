r"""python test_game_stadiums.py -> the game's own stadiums for the new clubs (0.2.4): the pick a
league gets (its size, its look, variety, the same every time), a club's stadium chosen by hand,
Team.bin +0x3C written and read back, and a ready world's picks (Stadiums > Your world's clubs)
kept in livecpk\<world>\fl26stadiums.json"""
import os, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lbgamestadiums as G
import lbstadiums as L
import mkworld as W
import pesdb

ENGLAND, SPAIN, GERMANY, BRAZIL = 204, 236, 210, 400

# ---- a league's pick ----
top = G.league(20, 1, ENGLAND)
assert top == G.league(20, 1, ENGLAND), "the same pick Build after Build"
assert len(top) == 20 and all(s in G.FICTIONAL for s in top), top
assert len(set(top)) >= 10, "a league plays in many stadiums: %s" % top
assert G.FICTIONAL[top[0]][2] == "en", "an English club gets an English-looking stadium first: %s" % top
assert G.FICTIONAL[G.league(1, 1, SPAIN)[0]][2] == "latin"
assert G.FICTIONAL[G.league(1, 1, GERMANY)[0]][2] == "de"
assert G.FICTIONAL[G.league(1, 1, BRAZIL, {BRAZIL: 4})[0]][2] == "latin", "CONMEBOL looks latin"
assert G.look_of(BRAZIL) is None and G.league(3, 1, BRAZIL)                 # no confederation: any look
cap = lambda sids: sum(G.FICTIONAL[s][1] for s in sids) / len(sids)
assert cap(G.league(6, 4, ENGLAND)) < cap(G.league(6, 1, ENGLAND)), "a lower tier plays in smaller stadiums"
assert G.league(4, "x", ENGLAND) == G.league(4, 1, ENGLAND)                 # a broken tier is the top one
assert G.league(0, 1, ENGLAND) == []

# ---- chosen by hand: Edit club > Game stadium ----
p = {"name": "Premier", "clubs": 4, "teams": [7001, 7002, 7003, 7004]}
pl = {"leagues": [p], "players": {"Premier/1": {"game_stadium": 7},             # Old Trafford: a real one
                                  "Premier/2": {"game_stadium": 69},            # not a stadium of the game
                                  "Premier/3": {"stadium": {"folder": "x"}}}}
assert G.fixed_of(pl, p) == {1: 7}
got = G.league(4, 1, ENGLAND, None, G.fixed_of(pl, p))
assert got[1] == 7 and all(s in G.FICTIONAL for i, s in enumerate(got) if i != 1), got
assert G.name(7) == "Old Trafford" and G.name(54) == "Stadio Nazionale" and G.name(99) == "stadium 99"

# ---- Team.bin +0x3C ----
def record(tid, sid=54):
    r = bytearray(W.T_REC)
    r[W.T_ID:W.T_ID + 4] = tid.to_bytes(4, "little")
    r[G.T_STADIUM] = sid
    return bytes(r)


with tempfile.TemporaryDirectory() as t:
    team = os.path.join(t, "Team.bin")
    with open(team, "wb") as f:
        f.write(pesdb.wesys_pack(b"".join(record(i) for i in (101, 7001, 7002, 7003, 7004)), b"\x00\x01\x01"))
    assert G.read_team_bin(team) == {101: 54, 7001: 54, 7002: 54, 7003: 54, 7004: 54}
    assert G.write_team_bin(team, {7001: 13, 7002: 54, 7003: 69, 9999: 13}) == 1    # 54 already, 69 not one
    assert G.read_team_bin(team)[7001] == 13 and G.read_team_bin(team)[101] == 54
    assert os.path.exists(team + ".before-stadiums")
    assert G.read_team_bin(team + ".before-stadiums")[7001] == 54                   # the copy is the first one
    G.write_team_bin(team, {7001: 20})
    assert G.read_team_bin(team + ".before-stadiums")[7001] == 54
    with open(team, "rb") as f:
        assert f.read(3) == b"\x00\x01\x01"
    assert G.write_team_bin(team, {7001: 20}) == 0                                   # nothing to change

    # ---- a ready world: its new clubs, the automatic pick, the hand on top ----
    world = {"leagues": [{"name": "Premier", "country": str(ENGLAND), "tier": 1, "teams": [7001, 7002, 7003, 7004],
                          "game_clubs": {"0": {"team": 7001}}},
                         {"name": "Liga", "country": SPAIN, "tier": 2, "teams": [8001, 8002, 7002]}],
             "others": [{"name": "Cup group", "teams": [9001]}]}
    new = G.new_clubs(world)
    assert set(new) == {7002, 7003, 7004, 8001, 8002, 9001} and new[7002][1] == 1, new    # 7001: a game club
    a = G.auto(world)
    assert set(a) == set(new) and a == G.auto(world)
    assert a[7002] == G.league(4, 1, ENGLAND)[1], "the first league a club plays in gives its stadium"
    assert all(G.FICTIONAL[a[t]][2] == "latin" for t in (8001, 8002)), a
    assert G.world_picks(world, {}, {}, False) == {}
    assert G.world_picks(world, {}, {7003: 7, 7001: 2, 7004: 69}, False) == {7003: 7}    # new clubs, the game's ids
    both = G.world_picks(world, {}, {7003: 7}, True)
    assert both[7003] == 7 and set(both) == set(new), both
    assert both[7002] != 7 or G.FICTIONAL.get(7) is None

    # ---- kept in fl26stadiums.json, next to the stadium pack picks ----
    root = os.path.join(t, "livecpk", "_World")
    os.makedirs(root)
    assert L.load_game(root) == ({}, False)
    L.save_game(root, {7003: 7}, True)
    assert L.load_game(root) == ({7003: 7}, True)
    L.save_edits(root, {8001: None})
    assert L.load_game(root) == ({7003: 7}, True) and L.load_edits(root) == {8001: None}
    L.save_game(root, {}, False)
    assert L.load_game(root) == ({}, False) and L.load_edits(root) == {8001: None}     # the pack picks stay
    L.save_edits(root, {})
    assert not os.path.exists(os.path.join(root, L.EDITS)), "nothing picked: no file"
    L.save_game(root, {}, True)
    assert L.load_game(root) == ({}, True)
print("game stadiums: ok")
