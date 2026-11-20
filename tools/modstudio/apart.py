"""Build in a process of its own (0.2.4, exe test 15.10.: on the Modpack the window went "Not
Responding" for minutes when a tab was opened during Build -- the build ran in a thread of the
window's process and the two took turns at Python, the window waiting up to 5 ms after every file
it looked at). The window's process now only waits on a pipe, which costs it nothing."""
import multiprocessing
import sys
import traceback


def _low():
    # B480 round 3: a child's memory and the files it reads are what Windows takes back first when
    # the PC is short of memory, not Mod Studio's window (Build's 19 minutes in beta4r's exe test put
    # all but 50-300 MB of its 3.2 GB out to the disk)
    try:
        from . import procstat
        procstat.low_memory_priority()
    except Exception:
        pass


def _child(conn, preferred, args):
    _low()
    import leaguebuilder as B
    import siderdir
    siderdir.PREFERRED = preferred
    try:
        B.build(*args, log=lambda t: conn.send(("log", str(t))))
    except BaseException as e:
        tb = traceback.format_exc()
        try:
            conn.send(("raise", e, tb))
        except Exception:                 # an exception that does not pickle
            conn.send(("raise", RuntimeError(str(e)), tb))
    else:
        conn.send(("done", None))
    conn.close()


class ChildError(Exception):
    """the build process's own traceback, chained under the exception it raised"""


def build(pl, base, game, replace, log):
    """leaguebuilder.build(pl, base, game, replace, log=log) in a new process; log lines and the
    exception (BuildError, a refused write ...) come back as if it ran here.
    A world from a zip made editable on this PC (worlds.make_editable) goes into a world backup
    first, all of it (Restore points > Put this copy back): it is someone else's world, and a
    Build changes it in place"""
    import siderdir
    from . import worlds
    from .game import Game
    g = Game(game)
    if replace and worlds.edited_world(g, pl.get("world")):
        log("a copy of %s before this Build: %s" % (pl["world"], worlds.backup(g, pl["world"], "built")))
    ctx = multiprocessing.get_context("spawn")
    here, there = ctx.Pipe(duplex=False)
    p = ctx.Process(target=_child, args=(there, siderdir.PREFERRED, (pl, base, game, replace)), daemon=True)
    p.start()
    there.close()
    try:
        while True:
            try:
                what = here.recv()
            except EOFError:
                p.join()
                raise RuntimeError("the build process stopped (exit code %s) without saying why" % p.exitcode)
            if what[0] == "log":
                log(what[1])
            elif what[0] == "done":
                return
            else:
                raise what[1] from ChildError(what[2])
    finally:
        here.close()
        p.join(10)
        if p.is_alive():
            p.kill()
        # B480 round 3: what Windows put out of this process while the build ran comes back here,
        # in Build's worker with Python's lock let go, not page by page under the lock in the steps
        # after it (the end of Build 3.9 s, Leagues' first opening 1.2 s, Edit league > OK 6.6 s)
        try:
            from . import procstat
            procstat.bring_back()
        except Exception:
            pass


def plan_numbers(pl):
    """leagues, new clubs and new countries of a built world's plan (My world's cards)"""
    import leaguebuilder as B
    leagues = pl.get("leagues") or []
    # the plan keeps a league's clubs of the game by place; new_club_count reads them as a list
    clubs = sum(B.new_club_count(dict(p, game_clubs=list(B.game_places(p).values())))
                for p in leagues + (pl.get("others") or []))
    regions = {p.get("region") for p in leagues
               if isinstance(p.get("region"), int) and p["region"] >= B.REGION_FIRST}
    return {"leagues": len(leagues), "clubs": clubs, "regions": len(regions)}


def _numbers_of(path):
    import json
    try:
        with open(path, encoding="utf-8") as f:
            return plan_numbers(json.load(f))
    except (OSError, ValueError):
        return None


def _numbers_child(conn, paths):
    _low()
    try:
        conn.send(("done", [_numbers_of(p) for p in paths]))
    except BaseException:
        conn.send(("raise", None, traceback.format_exc()))
    conn.close()


def numbers(paths):
    """plan_numbers of each plan file (None where it cannot be read), read in a process of its own.
    10.11. (mato: the program froze for a moment while it started): My world read every built
    world's plan in a thread, and json.load of a big one (the GigaPack's, 128 MB) holds all of
    Python, the window's thread too, for seconds"""
    ctx = multiprocessing.get_context("spawn")
    here, there = ctx.Pipe(duplex=False)
    p = ctx.Process(target=_numbers_child, args=(there, list(paths)), daemon=True)
    p.start()
    there.close()
    try:
        what = here.recv()
    except EOFError:
        p.join()
        raise RuntimeError("the plan process stopped (exit code %s) without saying why" % p.exitcode)
    finally:
        here.close()
        p.join(10)
        if p.is_alive():
            p.kill()
    if what[0] != "done":
        raise ChildError(what[2])
    return what[1]
