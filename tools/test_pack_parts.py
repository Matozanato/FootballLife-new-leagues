"""python tools/test_pack_parts.py

Adding a league package without some of its parts (lbpackage.parts_only): what is left out goes
as if the package had been made without it, the rest stays as it was.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lbpackage as K

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def main():
    piece = {"leagues": [{"name": "A", "logo": "l.png", "flag": "f.png", "club_crests": ["c.png"],
                          "club_coaches": ["X"], "club_kits": ["red"], "kit_folders": ["k0"],
                          "scoreboard": "s0", "formation": 3, "clubs": 1}],
             "players": {"A/0": {"edits": {"5": {"face": "fc", "portrait": "p", "ovr": 80}},
                                 "coach_portrait": "cp", "stadium": 7},
                         "123": {"remove": [9]}},
             "edits": {"clubs": {"123": {"crest": "g.png", "name": "Y"}}, "leagues": {"9": {"logo": "z.png"}}}}
    keep = K.parts_only(piece, K.PARTS)
    ok("all parts: nothing changes", keep == piece)
    q = K.parts_only(piece, [p for p in K.PARTS if p != "scoreboards"])
    ok("no scoreboards: the league has none", "scoreboard" not in q["leagues"][0])
    ok("and everything else stays", q["leagues"][0]["kit_folders"] == ["k0"] and q["players"] == piece["players"])
    q = K.parts_only(piece, [p for p in K.PARTS if p not in ("kitfiles", "kits")])
    ok("no kits: no kit folders, no colours", not {"kit_folders", "club_kits"} & set(q["leagues"][0]))
    q = K.parts_only(piece, [p for p in K.PARTS if p != "crests"])
    L = q["leagues"][0]
    ok("no crests: no logo, flag or crests", not {"logo", "flag", "club_crests"} & set(L))
    ok("no crests: the game's club keeps its new name, its crest and the league logo go",
       q["edits"] == {"clubs": {"123": {"name": "Y"}}})
    q = K.parts_only(piece, [p for p in K.PARTS if p != "faces"])
    ok("no faces: the player change stays, its face goes", q["players"]["A/0"]["edits"]["5"] == {"ovr": 80})
    q = K.parts_only(piece, [p for p in K.PARTS if p != "squads"])
    ok("no squads: only manager portrait and stadium are left of the club",
       q["players"] == {"A/0": {"coach_portrait": "cp", "stadium": 7}} and "formation" not in q["leagues"][0])
    q = K.parts_only(piece, [p for p in K.PARTS if p not in ("managers", "stadiums")])
    ok("no managers or stadiums", "club_coaches" not in q["leagues"][0]
       and "coach_portrait" not in q["players"]["A/0"] and "stadium" not in q["players"]["A/0"])
    ok("the piece itself is not changed", piece["leagues"][0]["scoreboard"] == "s0"
       and piece["edits"]["clubs"]["123"]["crest"] == "g.png")
    print("%d cases passed" % N)


if __name__ == "__main__":
    main()
