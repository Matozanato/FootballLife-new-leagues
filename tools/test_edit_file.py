r"""python tools/test_edit_file.py

The Edit save Mod Studio looks at (modstudio/game.py edit_file, old_edit, edit_aside) is the one in
the save folder in use: with FL26_SAVE_ROOT set (tests, the build test, coldstart's new player) it
is that folder's save\EDIT00000000, never the PC's real one in Documents\KONAMI. Coldstart 26.10.:
the real EDIT00000000 showed "Move the Edit save aside" on a "new player's" PC.

A fake save folder in a temp folder; the real save folder is never written.
"""
import os, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
T = tempfile.mkdtemp(prefix="editfile-")
os.environ["FL26_SAVE_ROOT"] = os.path.join(T, "2026")

from modstudio import game as G

N = 0
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


ef = os.path.join(T, "2026", "save", "EDIT00000000")
ok("with FL26_SAVE_ROOT the Edit save is that folder's", os.path.normcase(G.edit_file()) == os.path.normcase(ef))
ok("... and not the PC's real one", os.path.normcase(G.edit_file()) != os.path.normcase(G.EDIT_FILE))
ok("no Edit save there: nothing old", G.old_edit(time.time() + 60) is None)
os.makedirs(os.path.dirname(ef))
with open(ef, "wb") as f:
    f.write(b"old edit")
old = time.time() - 3600
os.utime(ef, (old, old))
ok("an Edit save older than the Build: found", os.path.normcase(G.old_edit(time.time()) or "") == os.path.normcase(ef))
ok("... newer than `since`: not old", G.old_edit(old - 10) is None)
name = G.edit_aside("w1")
ok("moved aside next to it, nothing deleted", not os.path.exists(ef)
   and os.path.isfile(os.path.join(os.path.dirname(ef), name)) and name.startswith("EDIT00000000.before-w1-"))
del os.environ["FL26_SAVE_ROOT"]
ok("without FL26_SAVE_ROOT: the game's save folder", G.edit_file() == G.EDIT_FILE)
print("all %d checks passed" % N)
