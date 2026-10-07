"""python test_febdec_division.py <folder with the game's tables> -- a division under the game's
own February-December league (Colombia's) plays that season, so Build refuses a split or
Apertura/Clausura on it as it does on a Feb-Dec top division (Discord, aaron 07.10.: a split
Primera B under Liga BetPlay)"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B


def recipe(**extra):
    L = {"name": "Primera B Test", "country": "Colombia", "clubs": 16, "legs": 2, "above": 168}
    L.update(extra)
    return {"world": "_TestFebDec", "leagues": [L]}


def main(base):
    pl = B.plan(recipe(), base)
    assert pl["leagues"][0].get("follows_calendar"), "a division under Liga BetPlay follows its calendar"
    for bad in ({"split": {"legs": 2, "groups": [8, 8], "group_legs": 2}},
                {"apertura": {"playoff": 0}}):
        try:
            B.plan(recipe(**bad), base)
            raise AssertionError("Build took %s on a Feb-Dec division" % list(bad))
        except B.BuildError as e:
            assert "February to December" in str(e), e
            print("refused:", e)
    print("all passed")


if __name__ == "__main__":
    main(sys.argv[1])
