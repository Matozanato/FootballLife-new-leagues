r"""python tools/test_player_id_gaps.py

The limits branch (a ~150-country FL27 world, ~120,000 new players): Mod Studio handed out
player ids only above the game's highest one, 186534 in FL27, which leaves 75,609 below
PID_MAX (262143). The 160,139 ids in the gaps between the game's own players below that top
were never used. Now, once the ids above the top are gone, mkplayers and lbplayers.FreeIds go on
with the gaps, lowest first; a world that fits above the top gets the ids it got before.

What has to hold: no id of the game's is ever given, nothing past PID_MAX, Player.bin stays in id
order (the game's binary search by id, 0x1414b80f0), the world's players in the gaps get their
pack faces (newfaces lines), and a rebuild keeps every id the last Build gave -- above the top or
in a gap -- even when a club added in front of them takes the placeholder ids first.
Runs on tables made here, in a temporary folder.
"""
import os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lbplayers as L
import leaguebuilder as B
import mkplayers
import pesdb
import playeredit as E
from test_short_squads import write, team_bin, tables

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def ids_in(db):
    raw = pesdb.wesys_unpack(open(os.path.join(db, "Player.bin"), "rb").read())
    return [L.u32(raw, i * L.P_REC + L.P_ID) for i in range(len(raw) // L.P_REC)]


def held(db):
    raw = pesdb.wesys_unpack(open(os.path.join(db, "PlayerAssignment.bin"), "rb").read())
    return {L.u32(raw, i * L.A_REC + E.A_PID) for i in range(len(raw) // L.A_REC)}


def main():
    # FreeIds on its own: above the top first, then the gaps lowest first, then a gone player's id
    shipped = {3, 5, 6, 10}
    free = L.FreeIds(L.PID_MAX - 2, {L.PID_MAX - 1}, {4}, None, shipped | {L.PID_MAX - 2})
    got = [free.take() for _ in range(6)]
    ok("above the top first, then the gaps (not the game's, not busy, not a gone player's)",
       got == [L.PID_MAX, 1, 2, 7, 8, 9])
    nxt = [free.take() for _ in range(2)]
    ok("the gaps run to the game's top", nxt == [11, 12])
    free = L.FreeIds(L.PID_MAX - 2, {L.PID_MAX - 1}, {4}, None)
    ok("without the game's ids: no gaps, as before (the gone player's id once the rest is taken)",
       [free.take(), free.take()] == [L.PID_MAX, 4])

    tmp = tempfile.mkdtemp(prefix="fl26-gaps-")
    try:
        # the game: one club of 22, its ids 10, 20 ... 210 and the top at PID_MAX - 5, so 5 ids
        # are left above it
        top = L.PID_MAX - 5
        game_ids = [10 * k for k in range(1, 22)] + [top]
        players, assigns = tables({100: game_ids})
        base = os.path.join(tmp, "base")
        write(base, "Player.bin", players)
        write(base, "PlayerAssignment.bin", assigns)
        write(base, "Team.bin", team_bin([100]))

        def build(clubs, leagues, prev=None):
            out = os.path.join(tmp, "world")
            db = os.path.join(out, "common", "etc", "pesdb")
            shutil.rmtree(out, ignore_errors=True)
            write(db, "Team.bin", team_bin([100] + clubs))
            per = 22
            said = B.call(mkplayers, ["--base", base, "--out", out, "--per", per,
                                      "--cap", len(game_ids) + len(clubs) * per])
            assert B.squads_cut(said) is None, said
            pl = {"world": "_FL26Gaps", "leagues": [{"name": n, "teams": t} for n, t in leagues], "players": {}}
            ids = {}
            L.apply(pl, base, db, 10 ** 6, lambda *_a: None, [], ids=ids, prev=prev, retired=set())
            return db, ids

        db, ids = build([201, 202], [("Liga", [201, 202])])
        got = ids_in(db)
        world = [p for p in got if p not in game_ids]
        ok("44 new players fit: 5 above the game's top and 39 in the gaps below it",
           len(world) == 44 and sum(p > top for p in world) == 5 and sum(p < top for p in world) == 39)
        ok("no id of the game's is given, none past PID_MAX, each once",
           len(got) == len(set(got)) == 66 and not set(world) & set(game_ids) and max(got) <= L.PID_MAX)
        ok("the gaps lowest first: 1..9, 11..19, ...", sorted(p for p in world if p < top)[:10]
           == [1, 2, 3, 4, 5, 6, 7, 8, 9, 11])
        ok("Player.bin is in id order, the game's records among the world's", got == sorted(got))
        ok("every assignment's player is in Player.bin", held(db) <= set(got))
        faces = L.new_face_lines(base, db)
        listed = set()
        for line in faces:
            for w in line.split()[1:]:
                a, _s, b = w.partition("-")
                listed |= set(range(int(a), int(b or a) + 1))
        ok("the world's players in the gaps get pack faces too, the game's do not", listed == set(world))

        # the same world again: every id stays
        db, ids2 = build([201, 202], [("Liga", [201, 202])], prev=ids)
        ok("built again: every player keeps his id", ids2 == ids)
        ok("  ... and Player.bin is the same", ids_in(db) == got)

        # a new club in front takes the placeholder ids first (mkplayers goes by club id): the
        # players of the last Build keep theirs, in a gap or above the top
        db, ids3 = build([150, 201, 202], [("New", [150]), ("Liga", [201, 202])], prev=ids)
        ok("a club added in front: Liga's 44 players keep their ids", ids3["Liga/0"] == ids["Liga/0"]
           and ids3["Liga/1"] == ids["Liga/1"])
        new = set(ids3["New/0"].values())
        got3 = ids_in(db)
        ok("  ... the new club's 22 take free ids in the gaps, none of the game's or Liga's",
           len(new) == 22 and all(p < top and p not in game_ids for p in new)
           and not new & set(world))
        ok("  ... every id once, in id order", got3 == sorted(set(got3)) and len(got3) == 88)

        # a world that fits above the top is built as before: nothing in the gaps
        game_ids[:] = [10 * k for k in range(1, 22)] + [1000]
        players, assigns = tables({100: game_ids})
        write(base, "Player.bin", players)
        write(base, "PlayerAssignment.bin", assigns)
        db, ids4 = build([201], [("Liga", [201])])
        ok("room above the top: the new ids are 1001.. as before",
           sorted(ids4["Liga/0"].values()) == list(range(1001, 1023)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("all passed (%d)" % N)


if __name__ == "__main__":
    main()
