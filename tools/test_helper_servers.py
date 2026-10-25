"""python test_helper_servers.py -- the Pre-Libertadores' matches get what every other Sider server
gives the game's Libertadores qualifying round (regulation 8): Menu Server's theme, ball, referee,
commentary... (their map_competitions.txt) and Soundtrack Server's music (its folders named by
the id). The scoreboard alone came with B227; antonimus 25.10.: still the generic menu and menu
song (B230)."""
import os, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lbservers as S

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


MENU = ["# Menu server map",
        "17, EPL                              # Menus for the EPL",
        "8, Copa Lib                          # Menus for the Copa Lib PlayOffs",
        "# 8, Copa Lib Old",
        "9, Copa Lib                          # Menus for the Copa Lib GroupStage",
        "500, _FL26M2400S\\Theme   # FL26 Mod Studio: menus of a world zip"]
BALL = ["8, 951, Puma Cumbre Copa Libertadores 2025, , , ,     # playoff",
        "9, 951, Puma Cumbre Copa Libertadores 2025, , , ,"]
REF = ["\t8,\t\tLibertadores", "\t9,\t\tLibertadores"]
PL = {"world": "_FL26Conmebol", "leagues": [],
      "cup_ids": {S.LIBQ_KEY: {"cid": 143, "reg": 902, "reg2": 903}}}
KEYS = sorted([902 + 1024 * k for k in range(4)] + [903 + 1024 * k for k in range(9)])


def put(path, lines):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def keyed(path):
    out = {}
    for l in open(path, encoding="utf-8-sig").read().splitlines():
        m = S.REST.match(l)
        if m:
            out.setdefault(int(m.group(1)), []).append(l)
    return out


def main():
    tmp = tempfile.mkdtemp()
    try:
        sider = os.path.join(tmp, "SiderAddons")
        c = os.path.join(sider, "content")
        menu = os.path.join(c, "menu-server", "map_competitions.txt")
        ball = os.path.join(c, "ball-server", "map_competitions.txt")
        ref = os.path.join(c, "referee", "map_competitions.txt")
        board = os.path.join(c, "scoreboard-server", "map_competitions.txt")
        put(menu, MENU)
        put(ball, BALL)
        put(ref, REF)
        put(board, ["8, CONMEBOL\\Copa Libertadores\\ESPN"])
        spfl = os.path.join(c, "scoreboards", "map_competitions.txt")
        put(spfl, ["8, Libertadores\\Fox"])
        ccl = os.path.join(c, "soundtrack-server", "4_Competitions_Specific", "CCL")
        os.makedirs(ccl)
        for i in (1, 2):
            open(os.path.join(ccl, "Track_%d.mp3" % i), "wb").write(b"ID3" + bytes([i]) * 64)
        mine17 = os.path.join(c, "soundtrack-server", "4_Competitions_Specific", "17")
        os.makedirs(mine17)
        open(os.path.join(mine17, "Track_1.mp3"), "wb").write(b"mine")

        got = S.helper_lines(PL, menu)
        ok("menu: the 13 regulations of the phases and their ties, the round's theme",
           sorted(k for k, _t in got) == KEYS and all(", Copa Lib" in t.split("#")[0] or ",Copa Lib" in t
                                                      or " Copa Lib" in t.split("#")[0] for _k, t in got))
        ok("menu: the line switched off is not copied", not any("Old" in t for _k, t in got))
        g = dict(S.helper_lines(PL, ball))
        ok("ball: every field of the line comes along",
           g[902].split("#")[0].strip() == "902, 951, Puma Cumbre Copa Libertadores 2025, , , ,")
        ok("referee: a tab-separated line", dict(S.helper_lines(PL, ref))[903].split("#")[0].strip()
           == "903,\t\tLibertadores")

        S.write(PL, sider, log=lambda *a: None)
        km = keyed(menu)
        ok("Switch on: menu, ball and referee maps have the phases",
           all(k in km for k in KEYS) and all(k in keyed(ball) for k in KEYS) and all(k in keyed(ref) for k in KEYS))
        ok("the menu map's own lines and a world zip's theme line stay as they were",
           all(l in open(menu, encoding="utf-8-sig").read().splitlines() for l in MENU))
        ok("the scoreboard map is helper_boards' (B227), one line a regulation, not two",
           all(len(v) == 1 for k, v in keyed(board).items() if k in KEYS) and all(k in keyed(board) for k in KEYS))
        ok("both scoreboard modules on: the map common\\scoreboards.lua reads has the phases too (antonimus)",
           all(keyed(spfl).get(k) == ["%d, Libertadores\\Fox   %s Pre-Libertadores (as 8)" % (k, S.TAG)]
               for k in KEYS))
        sound = os.path.join(c, "soundtrack-server", "4_Competitions_Specific")
        ok("soundtrack: a folder of the round's tracks for each regulation",
           all(sorted(f for f in os.listdir(os.path.join(sound, str(k))) if f.endswith(".mp3"))
               == ["Track_1.mp3", "Track_2.mp3"] for k in KEYS))
        ok("soundtrack: the same music", open(os.path.join(sound, "903", "Track_2.mp3"), "rb").read()
           == open(os.path.join(ccl, "Track_2.mp3"), "rb").read())

        S.write(PL, sider, log=lambda *a: None)
        ok("a second Switch on: each line once", keyed(menu) == km)

        own = MENU + ["903, My Pre-Lib Menu"]
        put(menu, own)
        S.write(PL, sider, log=lambda *a: None)
        ok("a line of your own for a phase keeps it, the others get the round's",
           keyed(menu)[903] == ["903, My Pre-Lib Menu"] and 902 in keyed(menu))
        mine = os.path.join(sound, "1927")
        shutil.rmtree(mine)
        os.makedirs(mine)
        open(os.path.join(mine, "Track_1.mp3"), "wb").write(b"mine")
        S.write(PL, sider, log=lambda *a: None)
        ok("a music folder of your own for an id is not touched",
           os.listdir(mine) == ["Track_1.mp3"] and open(os.path.join(mine, "Track_1.mp3"), "rb").read() == b"mine")

        S.write({"world": "_FL26Other", "leagues": []}, sider, log=lambda *a: None)
        ok("another world on: the lines are gone, yours stay",
           not any(k in keyed(menu) for k in KEYS if k != 903) and keyed(menu)[903] == ["903, My Pre-Lib Menu"]
           and not any(k in keyed(ball) for k in KEYS) and not any(k in keyed(spfl) for k in KEYS))
        ok("and the music folders we made, not yours (1927, 17) or CCL",
           sorted(os.listdir(sound)) == ["17", "1927", "CCL"])
        ok("no phases, no line: nothing to do", S.helper_lines({"leagues": []}, menu) == [])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("1..%d" % N)


if __name__ == "__main__":
    main()
