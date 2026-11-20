r"""python tools/test_caps_per_game.py -- the club and player caps follow the game folder.

FL26 keeps the 0.3.0 set (2400 clubs, 61905 players), FL27 gets the limits set (4800 clubs,
123825 player records, of which a career reaches 65533: leaguebuilder.PLAYER_KEY_MAX): leaguebuilder.use_game picks them from the game's exe. Mod Studio builds in a
process of its own (modstudio/apart.py, spawn), which imports leaguebuilder afresh with FL26's
caps, so build() has to set them itself. Without that the first FL27 test world (04.11.2026,
~87,000 players) was cut to fit 61905: its squads came out smaller, then "the player table is
full ... the game takes 61905". Checked without a game: an empty FL_2027.exe / FL_2026.exe in a
temporary folder, and a build that stops at its first check (the world folder is there already).

Also: no page the caps modules reserve lies inside the exe. datecave.IMAGE_END was 0x150000000
while both exes end at 0x15b9a6000, so a patch inside .impdata put 0x15b784000 on the FL27
module's PAGES list; VirtualAlloc never gets an image page, and fl26caps aborted on every start.
"""
import os, re, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import leaguebuilder as B
import datecave

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %2d - %s" % (N, name))


def game(exe):
    d = tempfile.mkdtemp()
    open(os.path.join(d, exe), "wb").close()
    os.makedirs(os.path.join(d, "SiderAddons", "livecpk", "_FL26Caps"))
    open(os.path.join(d, "SiderAddons", "sider.ini"), "w").close()
    return d


def build_caps(folder, start):
    """the caps after a build() that stops at its first check, from the given caps"""
    B.TEAM_CAP, B.PLAYER_CAP = start
    try:
        B.build({"world": "_FL26Caps", "leagues": []}, None, folder, log=lambda *a: None)
    except B.BuildError as e:
        assert "exists" in str(e), e
    return B.TEAM_CAP, B.PLAYER_CAP


def main():
    fl26, fl27 = game("FL_2026.exe"), game("FL_2027.exe")
    B.use_game(fl27)
    ok("use_game: FL27 takes 4800 clubs and 65533 players (the set reserves 123825; a career key's index is a word)",
       (B.TEAM_CAP, B.PLAYER_CAP) == (4800, 65533))
    B.use_game(fl26)
    ok("use_game: FL26 keeps 2400 and 61905", (B.TEAM_CAP, B.PLAYER_CAP) == (2400, 61905))
    ok("build() in a fresh process (FL26's caps) sets FL27's",
       build_caps(fl27, B.GAME_CAPS["fl26"]) == (4800, 65533))
    ok("and after an FL27 build, FL26's again", build_caps(fl26, B.GAME_CAPS["fl27"]) == (2400, 61905))

    # the installed set's own caps (its `Caps:` line, patchset.py 06.11.2026 on) win over GAME_CAPS
    mdir = os.path.join(fl27, "SiderAddons", "modules")
    os.makedirs(mdir)

    def installed(caps, players_step=None):
        with open(os.path.join(mdir, "fl26caps.lua"), "w", encoding="utf-8") as f:
            f.write("--[[\nSet:     x\nSummary: y\n%s]]\nlocal PATCHES = {}\n" % ("Caps:    %s\n" % caps if caps else ""))
        m = os.path.join(mdir, "fl26match.lua")
        if players_step is None:
            if os.path.exists(m):
                os.remove(m)
        else:
            with open(m, "w", encoding="utf-8") as f:
                f.write("local PLAYERS = %s -- players past 65535\n" % ("true" if players_step else "false"))
        B.use_game(fl27)
        return B.TEAM_CAP, B.PLAYER_CAP

    ok("an installed set without a Caps line: GAME_CAPS", installed(None) == (4800, 65533))
    big = "teams=8000 coaches=10000 regulations=1200 players=123825 pk32=1"
    ok("the P150 set with pk32 and fl26match's player step on: 8000 clubs, 123825 players",
       installed(big, True) == (8000, 123825))
    ok("  ... the player step off: 8000 and 65533", installed(big, False) == (8000, 65533))
    ok("  ... no fl26match.lua: 8000 and 65533", installed(big, None) == (8000, 65533))
    ok("  ... the step on, but a set without pk32: 65533",
       installed(big.replace("pk32=1", "pk32=0"), True) == (8000, 65533))
    ok("a set below the key's wall keeps its own count", installed(
        "teams=2400 coaches=3400 regulations=600 players=61905 pk32=0") == (2400, 61905))
    ok("build() reads it too", (installed(big, True), build_caps(fl27, B.GAME_CAPS["fl26"]))[1] == (8000, 123825))
    os.remove(os.path.join(mdir, "fl26caps.lua"))
    for name in ("fl26caps.lua", "fl26caps.fl27.lua"):
        lua = open(os.path.join(os.path.dirname(HERE), "sider", name), encoding="utf-8").read()
        pages = [int(x, 16) for x in re.search(r"local PAGES = \{([^}]*)\}", lua).group(1).split(",") if x.strip()]
        ok("%s reserves no page inside the exe (%s)" % (name, ", ".join(hex(p) for p in pages)),
           pages and all(p >= datecave.IMAGE_END for p in pages))
    lua = open(os.path.join(os.path.dirname(HERE), "sider", "fl26caps.fl27.lua"), encoding="utf-8").read()
    # two switches read their byte table as [image base + i + rva]; the rva is inside the lower
    # tail's span by arithmetic only, and moving it sent Master League setup into the heap
    ok("the switch byte tables at 0x14180b3ce and 0x1417f3857 are left alone",
       "va=0x14180b3ce" not in lua and "va=0x1417f3857" not in lua)
    exe = os.environ.get("FL26_EXE")
    if exe and os.path.exists(exe):
        import pefile
        pe = pefile.PE(exe, fast_load=True)
        end = pe.OPTIONAL_HEADER.ImageBase + pe.OPTIONAL_HEADER.SizeOfImage
        ok("IMAGE_END is where %s ends (0x%x)" % (os.path.basename(exe), end), datecave.IMAGE_END >= end)
    print("all passed")


if __name__ == "__main__":
    main()
