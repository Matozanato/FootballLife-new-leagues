"""python test_finished_cap.py <folder with the game's tables> -- the player table's cap is for the
finished world (exe test 14.10.: the Modpack, 1212 new clubs and 60488 players when built, stopped
with "the player table is full (61905)" because the recipe's own players went in before the
placeholders they replaced were deleted). Build now puts them in with room to spare and checks
the finished table: a world that fits when done is built with squads of 30; one that does not
gets smaller squads, by what was over, and the players go in again. The worlds are built in a
temporary game folder (nothing is switched on); PLAYER_CAP is set just above the shipped players."""
import os, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B
import pesdb
import playeredit as E

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def free_agents(base, n):
    _p, players = E.load(base, "Player.bin")
    _a, assigns = E.load(base, "PlayerAssignment.bin")
    taken = {E.u32(assigns, o + E.A_PID) for o in range(0, len(assigns), E.A_REC)}
    return sorted({E.u32(players, o + E.P_ID) for o in range(0, len(players), E.P_REC)} - taken)[:n]


def recipe(world, joins):
    # club 0 of the first league: ten placeholders out, ten players of the game with no club in --
    # the placeholders go only at the end, so halfway through the Build the table holds ten more
    # players than when it is done (the Modpack: 8818 more)
    players = {"Cap Albania/0": {"remove": [str(n) for n in range(10)], "join": [str(j) for j in joins]}}
    return {"world": world, "players": players,
            "leagues": [{"name": "Cap Albania", "country": "Albania", "clubs": 10, "legs": 2},
                        {"name": "Cap Andorra", "country": "Andorra", "clubs": 10, "legs": 2}]}


def count(path):
    return len(pesdb.wesys_unpack(open(path, "rb").read())) // 312


def build(base, game, world, cap):
    B.PLAYER_CAP = cap
    said = []
    pl = B.plan(recipe(world, free_agents(base, 10)), base)
    B.build(pl, base, game, False, log=said.append)
    n = count(os.path.join(game, "SiderAddons", "livecpk", world, "common", "etc", "pesdb", "Player.bin"))
    return n, "\n".join(str(s) for s in said)


def main(base):
    have = count(os.path.join(base, "Player.bin"))
    game = tempfile.mkdtemp(prefix="fl26-cap-")
    real = B.PLAYER_CAP
    try:
        for d in ("livecpk", "modules", "content"):
            os.makedirs(os.path.join(game, "SiderAddons", d))
        with open(os.path.join(game, "SiderAddons", "sider.ini"), "w") as f:
            f.write("[sider]\n")

        n, said = build(base, game, "_FL26CapFits", have + 20 * 30 - 10)
        ok("over the cap halfway, at it when done: built", n == have + 20 * 30 - 10)
        ok("with squads of 30", "squads of 30 for 20 clubs" in said and "instead" not in said)

        n, said = build(base, game, "_FL26CapSmaller", have + 20 * 25)
        ok("over the cap when done: built again with smaller squads, and it fits", n == have + 20 * 25 - 10)
        ok("the log says by how much and what squads", "90 more than the game takes: squads of 25" in said
           and "squads of 25 for 20 clubs" in said)

        try:
            build(base, game, "_FL26CapNever", have + 400)
            ok("a world that does not fit even at the smallest squad is refused", False)
        except B.BuildError as e:
            ok("a world that does not fit even at the smallest squad is refused", "table" in str(e) or "room" in str(e))
    finally:
        B.PLAYER_CAP = real
        shutil.rmtree(game, ignore_errors=True)
    print("1..%d" % N)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1])
