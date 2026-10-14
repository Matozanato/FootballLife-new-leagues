r"""python tools/test_short_squads.py

B28: a world was built with 65 clubs that had no players at all (the Modpack: 1212 new clubs
with squads of 30 run past the player table's cap, and mkplayers stops handing out placeholder
squads in club-id order without the Build saying so). Picking such a club crashes the game, and
Become a Legend does not start. Build now stops twice over: when mkplayers' output says the cap
cut the squads short (leaguebuilder.squads_cut), and at the end when any new club has fewer than
lbplayers.MIN_SQUAD players (lbplayers.short_squads); Mod Studio's checks say the same of a world
already built (checks.short_squads). Runs on tables made here, in a temporary folder.
"""
import json, os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lbplayers as L
import leaguebuilder as B
import mkplayers
import mkworld as W
import pesdb
import playeredit as E

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def write(d, name, raw):
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name), "wb") as f:
        f.write(pesdb.wesys_pack(bytes(raw)))


def team_bin(tids):
    raw = bytearray()
    for t in tids:
        r = bytearray(W.T_REC)
        r[W.T_ID:W.T_ID + 4] = t.to_bytes(4, "little")
        raw += r
    return raw


def tables(squads):
    """Player.bin and PlayerAssignment.bin for {team id: [player id ...]}"""
    players, assigns = bytearray(), bytearray()
    for tid, pids in squads.items():
        for n, pid in enumerate(pids):
            r = bytearray(L.P_REC)
            r[L.P_ID:L.P_ID + 4] = pid.to_bytes(4, "little")
            players += r
            a = bytearray(L.A_REC)
            for off, v in ((E.A_EID, len(assigns) // L.A_REC + 1), (E.A_PID, pid), (E.A_TID, tid),
                           (E.A_PACK, E.with_shirt(n << E.ORDER_SHIFT, n + 1))):
                a[off:off + 4] = v.to_bytes(4, "little")
            assigns += a
    return players, assigns


def main():
    tmp = tempfile.mkdtemp(prefix="fl26-b28-")
    try:
        # the counting itself: a club with nobody, one short, one with the least, one with more
        db = os.path.join(tmp, "pesdb")
        players, assigns = tables({100: list(range(1, 23)), 101: list(range(23, 28)), 102: list(range(28, 46))})
        write(db, "Player.bin", players)
        write(db, "PlayerAssignment.bin", assigns)
        got = L.short_squads(db, [100, 101, 102, 103])
        ok("a club with no players and one with five are short, 18 and 22 are not", got == {101: 5, 103: 0})
        ok("only the clubs asked about", L.short_squads(db, [100]) == {})

        # mkplayers through Build's call: a cap with room for two of three new clubs
        base = os.path.join(tmp, "base")
        write(base, "Player.bin", players)
        write(base, "PlayerAssignment.bin", assigns)
        write(base, "Team.bin", team_bin([100, 101, 102]))
        out = os.path.join(tmp, "world")
        outdb = os.path.join(out, "common", "etc", "pesdb")
        write(outdb, "Team.bin", team_bin([100, 101, 102, 201, 202, 203]))
        per, shipped = 22, len(players) // L.P_REC
        said = B.call(mkplayers, ["--base", base, "--out", out, "--per", per, "--cap", shipped + 2 * per])
        ok("mkplayers says the cap cut the squads to two of three clubs", B.squads_cut(said) == (2, 3))
        ok("and the third new club has no players", L.short_squads(outdb, [201, 202, 203]) == {203: 0})
        said = B.call(mkplayers, ["--base", base, "--out", out, "--per", per, "--cap", shipped + 3 * per])
        ok("with room for all three nothing is cut", B.squads_cut(said) is None)
        ok("and every new club has its squad", L.short_squads(outdb, [201, 202, 203]) == {})
        ok("no output, nothing cut", B.squads_cut("") is None and B.squads_cut(None) is None)

        # Mod Studio's check reads the plan the world was built from: a club of the game in the
        # league is the game's business, a new club with no players is reported
        from modstudio import checks
        plan = {"world": "_FL26Test", "leagues": [{"name": "Liga", "teams": [201, 202, 100, 203],
                                                   "game_clubs": {"2": {"id": 100}}}]}
        write(outdb, "PlayerAssignment.bin", tables({201: list(range(1, 23)), 202: list(range(23, 45))})[1])
        with open(os.path.join(out, "leaguebuilder-plan.json"), "w", encoding="utf-8") as f:
            json.dump(plan, f)
        ok("the check names the new club with no players", checks.short_squads(out) == {203: 0})
        os.remove(os.path.join(out, "leaguebuilder-plan.json"))
        ok("no plan, no check", checks.short_squads(out) == {})
        ok("no world folder, no check", checks.short_squads(os.path.join(tmp, "nowhere")) == {})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("all passed (%d)" % N)


if __name__ == "__main__":
    main()
