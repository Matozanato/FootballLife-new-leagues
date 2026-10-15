r"""python test_world_stadiums.py -> the home stadiums of a ready world: picked by hand or found
automatically in the player's stadium pack, kept in livecpk\<world>\fl26stadiums.json, written to
map_teams.txt in place of the world's (0.2.4)"""
import os, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lbstadiums as S


def stadium(lib, rel, slot="009"):
    os.makedirs(os.path.join(lib, rel, "AddOn", "fog", slot))
    os.makedirs(os.path.join(lib, rel, "common"))


with tempfile.TemporaryDirectory() as t:
    sider = os.path.join(t, "SiderAddons")
    lib = os.path.join(sider, "content", "stadium-server")
    root = os.path.join(sider, "livecpk", "_FL26Pack")
    os.makedirs(root)
    # the player's pack: other names and regions than the maker's
    stadium(lib, "Greece\\Levadia Municipal Stadium", "031")             # the maker's "Levadia National Stadium"
    stadium(lib, "Belgium\\Jan Breydelstadion (Club Brugge)")
    stadium(lib, "Argentina\\El Monumental - River")                     # not Boston River's
    stadium(lib, "Other Euro\\NSK Olimpiyskiy (Dynamo)")                  # not Dynamo Douala's
    stadium(lib, "Poland\\Stadion Miejski Krakow")
    stadium(lib, "Poland\\Stadion Miejski Bialystok")
    stadium(lib, "Europe\\Air Albania Stadium")
    stadium(lib, "Konami\\Air Albania Stadium")                           # the same stadium twice: one
    os.makedirs(os.path.join(lib, "0000 Flags & Tifo", "Notes"))           # not a stadium
    with open(os.path.join(lib, S.FILE), "w") as f:
        f.write("5001, 004, Old Ground, Belgium\\Old Ground   # theirs\n")
    pl = {"leagues": [{"name": "Super League", "teams": [5001, 5002, 5003, 5004, 5005, 5006],
                       "club_names": ["Club Brugge KV", "Levadiakos", "Boston River", "Dynamo Club de Douala",
                                      "Miejski", "Tirana"]}],
          "players": {"Super League/1": {"stadium": {"folder": "Greece\\Levadia National Stadium", "slot": "009",
                                                     "name": "Levadia Municipal Stadium"}},
                      "Super League/4": {"stadium": {"folder": "Poland\\Stadion Miejski", "slot": "009"}},
                      "Super League/5": {"stadium": {"folder": "Albania\\Air Albania Stadium", "slot": "009"}}}}
    assert [c[0] for c in S.clubs(pl)] == [5001, 5002, 5003, 5004, 5005, 5006]
    assert S.coverage(pl, sider) == (3, 1)                                 # Air Albania: another region, found
    # ---- Find automatically ----
    got = S.suggest(pl, lib)
    assert set(got) == {5001, 5002}, got
    assert got[5002] == ({"folder": "Greece\\Levadia Municipal Stadium", "slot": "031",
                          "name": "Levadia Municipal Stadium"}, "name"), got[5002]
    assert got[5001][0]["folder"] == "Belgium\\Jan Breydelstadion (Club Brugge)" and got[5001][1] == "club"
    # Boston River / Dynamo Douala: a word of the club is not the club; Stadion Miejski: two stadiums
    # ---- picked: kept by team id, in place of the world's ----
    edits = {5002: got[5002][0], 5001: got[5001][0], 5006: None,
             5003: {"folder": "Argentina\\El Monumental - River", "slot": "027", "name": "Monumental"}}
    S.save_edits(root, edits)
    assert S.load_edits(root) == edits
    assert S.suggest(pl, lib, edits) == {}                                 # a club picked by hand is left alone
    w = S.wanted(pl, edits)
    assert set(w) == {5001, 5002, 5003, 5005} and w[5002][0] == "Super League/1" and w[5003][0] == "Super League/2", w
    assert S.coverage(pl, sider, edits) == (4, 3)                          # Miejski still missing
    assert S.write(pl, sider, lambda m: None, edits) == 3
    with open(os.path.join(lib, S.FILE)) as f:
        lines = f.read().splitlines()
    assert lines[0].startswith("#5001, 004, Old Ground") and lines[0].endswith(S.OFF), lines   # theirs, off for ours
    assert "5002, 031, Levadia Municipal Stadium, Greece\\Levadia Municipal Stadium   %s Super League/1" % S.TAG in lines
    assert "5001, 009, Jan Breydelstadion (Club Brugge), Belgium\\Jan Breydelstadion (Club Brugge)   %s Super League/0" \
        % S.TAG in lines, lines
    assert "5003, 027, Monumental, Argentina\\El Monumental - River   %s Super League/2" % S.TAG in lines
    assert not any(l.startswith(("5006,", "5005,")) for l in lines)       # the game's stadium; Tirana's off
    # ---- back to the world's: no file, the plan's lines again ----
    S.save_edits(root, {})
    assert not os.path.exists(os.path.join(root, S.EDITS)) and S.load_edits(root) == {}
    assert S.write(pl, sider, lambda m: None, S.load_edits(root)) == 1    # Air Albania only
    with open(os.path.join(lib, S.FILE)) as f:
        lines = f.read().splitlines()
    assert lines[0] == "5001, 004, Old Ground, Belgium\\Old Ground   # theirs", lines
    assert any(l.startswith("5006, 009, Air Albania Stadium, Europe\\Air Albania Stadium") for l in lines), lines
    # a broken file is no picks
    with open(os.path.join(root, S.EDITS), "w") as f:
        f.write("{not json")
    assert S.load_edits(root) == {}
    print("world stadiums: ok")
