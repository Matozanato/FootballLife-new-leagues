r"""python test_stadium_find.py -> a modpack's home stadium is found in a player's stadium pack also when
that pack keeps it under another region folder; one the player does not have is skipped and counted (0.2.4)"""
import os, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lbstadiums as S

with tempfile.TemporaryDirectory() as t:
    lib = os.path.join(t, "content", "stadium-server")
    os.makedirs(os.path.join(lib, "Europe", "Air Albania Stadium"))
    os.makedirs(os.path.join(lib, "Other Euro", "Serres Municipal Stadium"))
    assert S.find(lib, "Europe\\Air Albania Stadium") == "Europe\\Air Albania Stadium"
    assert S.find(lib, "Greece\\Serres Municipal Stadium") == "Other Euro\\Serres Municipal Stadium"
    assert S.find(lib, "Greece\\Levadia National Stadium") is None
    pl = {"leagues": [{"name": "Albanian Superleague", "teams": [900001, 900002, 900003]}],
          "players": {"Albanian Superleague/0": {"stadium": {"folder": "Europe\\Air Albania Stadium", "slot": "009"}},
                      "Albanian Superleague/1": {"stadium": {"folder": "Greece\\Serres Municipal Stadium", "slot": "009"}},
                      "Albanian Superleague/2": {"stadium": {"folder": "Greece\\Levadia National Stadium", "slot": "009"}}}}
    assert S.coverage(pl, t) == (3, 2), S.coverage(pl, t)
    log = []
    assert S.write(pl, t, log.append) == 2, log
    text = open(os.path.join(lib, "map_teams.txt"), encoding="utf-8").read()
    assert "Other Euro\\Serres Municipal Stadium" in text and "Levadia" not in text, text
print("stadium find: ok")
