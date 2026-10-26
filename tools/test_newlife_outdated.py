"""python test_newlife_outdated.py -- Update my leagues to this version is offered only for a league
from an OLDER NewLife version than the release loaded (B251, 26.10.: a pack built on 1.5b8 with the
public 1.5b7 loaded was offered a downgrade); a final version counts as newer than its betas"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modstudio import newlife as N


class Rel:
    def __init__(self, v):
        self.meta = {"version": v}


def flagged(cur, versions):
    r = {"leagues": [{"name": str(v), "newlife": {"version": v}} for v in versions] + [{"name": "own"}]}
    return [x["name"] for x in N.outdated(r, Rel(cur))]


def main():
    assert flagged("1.5b7", ["1.5b8", "1.5b6", "1.5", "1.4", "1.5b7", "1.3.2"]) == ["1.5b6", "1.4", "1.3.2"]
    assert flagged("1.5", ["1.5b8", "1.5b9", "1.4", "1.5", "1.6b1"]) == ["1.5b8", "1.5b9", "1.4"]
    assert flagged("1.5b10", ["1.5b9", "1.5b10", "1.5"]) == ["1.5b9"], "b10 after b9"
    assert flagged("1.3", ["1.2", 1.2, "1.3"]) == ["1.2", "1.2"], "a number from an old recipe"
    # what does not read as a version still counts when it differs, as before
    assert flagged("1.5b7", ["custom"]) == ["custom"]
    assert flagged("dev", ["1.5b7", "dev"]) == ["1.5b7"]
    print("ok")


if __name__ == "__main__":
    main()
