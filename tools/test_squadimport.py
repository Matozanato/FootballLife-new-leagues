"""python test_squadimport.py -- the table import reads the game's player id and our own fields
(JamesNotLike 04.10.: a table with real ids took players' places instead of the players)"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import squadimport as Q


class Model:
    also, body, usual = {}, {}, {}

    def overall_of(self, pos, have):
        return 70

    def predict(self, pos, ovr):
        return {a: ovr for a in Q.ABILITIES}


def main():
    # our own Export CSV: "player" (a number) and "player_id"
    head = ["player", "player_id", "name", "Registered Position", "Form", "Playing Style", "Captaincy", "Speed"]
    rows = [["59801", "59801", "Youri Tielemans", "CMF", "6", "3", "1", "71"],
            ["", "", "Made Up", "CB", "9", "", "0", "60"]]
    g = Q.guess(head, rows)
    assert g[0] == "id", g
    assert g[2] == "name" and g[4] == "Form" and g[5] == "Playing Style" and g[6] == "Captaincy", g
    out, warn = Q.convert(head, rows, g, Model(), None)
    assert out[0]["_id"] == "59801" and "_id" not in out[1], out
    assert out[0]["Form"] == "6" and out[0]["Captaincy"] == "1" and out[0]["Speed"] == "71", out[0]
    assert "Form" not in out[1] or out[1]["Form"] != "9", "an invalid Form is not taken"
    assert any("Form" in w for w in warn), warn
    # a table with a PES editor's "ID" column
    g = Q.guess(["ID", "Name", "Pos"], [["123", "A B", "CF"]])
    assert g == {0: "id", 1: "name", 2: "position"}, g
    print("all passed")


if __name__ == "__main__":
    main()
