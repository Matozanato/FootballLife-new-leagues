"""python test_helper_boards.py -- the Libertadores' phases 1 and 2 of a modern CONMEBOL world (the
"Pre-Libertadores", a competition of their own) get the scoreboard the map gives the game's
Libertadores qualifying round (regulation 8). With none their matches had no board where the
game's own Libertadores has one (B227, antonimus 24.10.)."""
import os, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lbservers as S

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


GAME = ["# scoreboard-to-competition map",
        "8, CONMEBOL\\Copa Libertadores\\ESPN              # playoff",
        "1032, CONMEBOL\\Copa Libertadores\\ESPN           # playoff",
        "9, CONMEBOL\\Copa Libertadores\\ESPN              # group stage",
        "17, EPL\\Default"]
PL = {"world": "_FL26Conmebol", "leagues": [],
      "cup_ids": {S.LIBQ_KEY: {"cid": 143, "reg": 902, "reg2": 903}}}


def keys(path):
    return {int(l.split(",")[0]): l for l in open(path, encoding="utf-8-sig").read().splitlines()
            if l[:1].isdigit()}


def main():
    tmp = tempfile.mkdtemp()
    try:
        sider = os.path.join(tmp, "SiderAddons")
        boards = os.path.join(sider, S.BOARDS)
        os.makedirs(boards)
        path = os.path.join(boards, "map_competitions.txt")
        open(path, "w", encoding="utf-8").write("\n".join(GAME) + "\n")

        want = sorted([902 + 1024 * k for k in range(4)] + [903 + 1024 * k for k in range(9)])
        got = S.helper_boards(PL, path)
        ok("phase 1 and its 3 ties, phase 2 and its 8 ties: 13 lines", sorted(k for k, _t in got) == want)
        ok("each wears the qualifying round's board",
           all("CONMEBOL\\Copa Libertadores\\ESPN" in t and S.TAG in t for _k, t in got))

        S.write(PL, sider, log=lambda *a: None)
        k1 = keys(path)
        ok("Switch on writes them into the map", all(k in k1 for k in want))
        ok("the game's own lines stay as they were", all(k1.get(int(g.split(",")[0])) == g for g in GAME[1:]))
        S.write(PL, sider, log=lambda *a: None)
        k2 = keys(path)
        ok("a second Switch on: the same lines, once each", k2 == k1 and
           sum(1 for l in open(path, encoding="utf-8-sig") if l.startswith("902,")) == 1)

        S.write({"world": "_FL26Other", "leagues": []}, sider, log=lambda *a: None)
        ok("another world on: they are gone", not any(k in keys(path) for k in want))

        own = GAME + ["903, My Boards\\Pre-Lib"]
        open(path, "w", encoding="utf-8").write("\n".join(own) + "\n")
        got = dict(S.helper_boards(PL, path))
        ok("a line of your own for a phase keeps it", 903 not in got and 902 in got)

        open(path, "w", encoding="utf-8").write("\n".join(l for l in GAME if not l.startswith("8,")) + "\n")
        ok("no board for the qualifying round: none for the phases", S.helper_boards(PL, path) == [])
        open(path, "w", encoding="utf-8").write("\n".join(GAME) + "\n")
        ok("a world without the phases: nothing", S.helper_boards({"leagues": []}, path) == [])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("1..%d" % N)


if __name__ == "__main__":
    main()
