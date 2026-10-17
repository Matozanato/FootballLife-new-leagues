"""Build in a process of its own (0.2.4, exe test 15.10.: on the Modpack the window went "Not
Responding" for minutes when a tab was opened during Build -- the build ran in a thread of the
window's process and the two took turns at Python, the window waiting up to 5 ms after every file
it looked at). The window's process now only waits on a pipe, which costs it nothing."""
import multiprocessing
import sys
import traceback


def _child(conn, preferred, args):
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
