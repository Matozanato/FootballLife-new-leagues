r"""python test_competition_room.py <the game's tables (pesdb)> [a built world's pesdb] -- the
Competitions counter of My world says how many competitions the world can have, not 255 (B279,
gianito9 29.10.: Modpack r12 read "212 / 255" and its Build found no free competition id: the ids
under 130 are the game's, a new league or cup only gets one from 130 up). The room is what the
world has plus the ids plan() would still hand out."""
import os, sys, types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
qa = QApplication.instance() or QApplication([])
import leaguebuilder as B
from modstudio.pages import myworld as MW

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def project(world, base):
    return types.SimpleNamespace(world_tables=lambda: [world] if world else [], base=base)


def main(base, world=None):
    game = {c[0] for c in B.competition_ids(base)}
    have, room = MW.competition_room(project(None, base))
    ok("the game alone: its own competitions", have == len(game))
    pool = [c for c in B.W.cid_pool(B.CID_FROM) if c not in game and c != B.UECL_CID]
    ok("the game alone: room = its own + the ids from 130 a Build gives", room == have + len(pool))
    ok("the game alone: room is under 255 (the low ids are the game's)", room < B.W.CID_MAX)
    ok("competitions() is the count", MW.competitions(project(None, base)) == have)
    ok("no tables: unknown", MW.competition_room(project(None, None)) is None)
    if world:
        ids = {c[0] for c in B.competition_ids(world)}
        have, room = MW.competition_room(project(world, base))
        ok("a world: its competitions", have == len(ids))
        low = any(c < B.CID_FROM and c not in game for c in ids)
        free = [c for c in B.W.cid_pool(B.CID_FROM, low) if c not in ids and c != B.UECL_CID]
        ok("a world: room = what it has + the free ids", room == have + len(free))
        print("# world: %d / %d (free %s)" % (have, room, free))
    print("all %d passed" % N)


if __name__ == "__main__":
    main(*sys.argv[1:3])
