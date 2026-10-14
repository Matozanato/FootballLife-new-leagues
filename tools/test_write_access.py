"""python tools/test_write_access.py

B14 (Konkubent, 13.10.): a game under C:\\Program Files (x86) -- Install mods stopped with a raw
PermissionError [WinError 5] on livecpk\\_FL26Modpack. modstudio/access.py finds a game folder
Windows does not let Mod Studio write in (a small file tried in each folder it writes in), tells
a refused write from other errors (an exception, a BuildError carrying its text, or a
traceback's last line), and says what to do; checks.quick shows it on Home.

The read-only folder is made with icacls (a deny-write entry for Everyone on a temporary
folder, taken off again at the end): a folder's read-only attribute means nothing on Windows.
No window, no game.
"""
import os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from modstudio import access as A, checks
from modstudio.game import Game
import leaguebuilder as B

N = 0
EVERYONE = "*S-1-1-0"


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def icacls(*args):
    r = subprocess.run(["icacls"] + list(args), capture_output=True, text=True)
    return r.returncode == 0


def deny(d):
    return icacls(d, "/deny", EVERYONE + ":(OI)(CI)(W,D,DC)")


def allow(d):
    icacls(d, "/remove:d", EVERYONE, "/T", "/C")


def game_at(root):
    g = os.path.join(root, "Football Life 2026")
    sd = os.path.join(g, "SiderAddons")
    for sub in ("modules", "livecpk", "content"):
        os.makedirs(os.path.join(sd, sub))
    open(os.path.join(g, "FL_2026.exe"), "wb").write(b"MZ")
    open(os.path.join(sd, "sider.ini"), "w", encoding="utf-8").write("[sider]\nlua.enabled = 1\n")
    return g


def main():
    tmp = tempfile.mkdtemp(prefix="fl26ms_access_")
    locked = []
    try:
        g = Game(game_at(tmp))
        ok("the game is found", g.ok())
        ok("a writable folder probes True", A.probe(g.folder) is True)
        ok("the probe leaves nothing behind", not [f for f in os.listdir(g.folder) if f.startswith(A.PROBE)])
        ok("a missing folder is not a refusal", A.probe(os.path.join(tmp, "nope")) is None)
        ok("nothing blocked in a writable game", A.blocked(g) is None)
        ok("Home says nothing then", checks.write_problems(g) == [])

        # the Sider folder of a game under Program Files: Windows refuses a new file there
        sd = g.sider_dir
        if not deny(sd):
            print("SKIP icacls not usable here: the read-only part is not tested")
        else:
            locked.append(sd)
            ok("the denied folder probes False", A.probe(sd) is False)
            ok("blocked() names the Sider folder", os.path.normcase(A.blocked(g) or "") == os.path.normcase(sd))
            rows = checks.write_problems(g)
            ok("Home shows one error row for it", len(rows) == 1 and rows[0][0] == "err" and sd in rows[0][2])
            ok("the row says run as administrator / move the game",
               "administrator" in rows[0][2] and "Program Files" in rows[0][2])
            # a real refused write, as Install mods hit it
            target = os.path.join(sd, "livecpk", "fl26world.txt")
            try:
                open(target, "wb").close()
                err = None
            except OSError as e:
                err = e
            ok("Windows refuses the write (PermissionError)", isinstance(err, PermissionError))
            ok("it is told as a refused write", A.is_denied(err))
            ok("its path comes out", os.path.normcase(A.denied_path(err) or "").startswith(os.path.normcase(sd)))
            # wrapped the way export_world / Build hand it on: a BuildError with the OSError's text
            try:
                try:
                    shutil.copy2(__file__, os.path.join(sd, "x.lua"))
                except OSError as e:
                    raise B.BuildError(str(e))
            except B.BuildError as e:
                wrapped = e
            ok("a BuildError carrying it is a refused write too", A.is_denied(wrapped))
            ok("... and names the file", A.denied_path(wrapped).lower().endswith("x.lua"))
            # the module pack's install, into a modules folder Windows refuses
            pack = os.path.join(tmp, "pack")
            os.makedirs(os.path.join(pack, "modules"))
            open(os.path.join(pack, "modules.txt"), "w").write("fl26caps\n")
            open(os.path.join(pack, "modules", "fl26caps.lua"), "w").write("-- caps\n")
            keep = B.pack_dir
            B.pack_dir = lambda: pack
            try:
                B.install_modules(g.folder, log=lambda t: None, settle=0)
                got = None
            except Exception as e:
                got = e
            finally:
                B.pack_dir = keep
            ok("Install the modules into a refused folder raises a refused write", got is not None and A.is_denied(got))
            allow(sd)
            locked.remove(sd)
            ok("writable again once the deny entry is gone", A.probe(sd) is True)

        # tracebacks as a background job hands them to the page (ui.Job: failed(text))
        tb = ('Traceback (most recent call last):\n  File "x.py", line 1, in <module>\n'
              "PermissionError: [WinError 5] Access is denied: 'C:\\\\Program Files (x86)\\\\FL 2026\\\\"
              "SiderAddons\\\\livecpk\\\\_FL26Modpack'\n")
        p = A.denied_path(tb)
        ok("a traceback's refused write is found", p is not None)
        ok("... with its path", p == r"C:\Program Files (x86)\FL 2026\SiderAddons\livecpk\_FL26Modpack")
        ok("another traceback is not", A.denied_path("Traceback ...\nValueError: bad value\n") is None)
        ok("PermissionError in an earlier line only does not count",
           A.denied_path("PermissionError: [WinError 5] x\nDuring handling...\nKeyError: 3\n") is None)
        ok("errno 13 counts", A.denied_path("PermissionError: [Errno 13] Permission denied: 'D:\\\\a\\\\b'") == r"D:\a\b")
        busy = PermissionError(13, "in use")
        busy.winerror = 32
        ok("a file in use (WinError 32) is not a refused write", not A.is_denied(busy))
        ok("an ordinary error is not", A.denied_path(ValueError("x")) is None)
        ok("FileNotFoundError is not", not A.is_denied(FileNotFoundError(2, "gone")))

        # what it says
        pf = os.environ.get("ProgramFiles(x86)") or r"C:\Program Files (x86)"
        game_pf = os.path.join(pf, "Football Life 2026")
        ok("Program Files is recognised", A.in_program_files(game_pf))
        ok("D:\\Games is not", not A.in_program_files(r"D:\Games\Football Life 2026"))
        msg = A.message(os.path.join(game_pf, "SiderAddons"), game_pf)
        ok("the message names the folder", os.path.join(game_pf, "SiderAddons") in msg)
        ok("the message says administrator and moving the game",
           "administrator" in msg and "move the game out of Program Files" in msg)
        ok("no traceback words in it", "Traceback" not in msg and "WinError" not in msg)
        exe, args = A.relaunch_command()
        ok("restart: the same program, marked --elevated once",
           exe == sys.executable and args.count("--elevated") == 1)
        ok("quote keeps a path with spaces whole", A.quote(r"C:\Program Files\x.py") == r'"C:\Program Files\x.py"')
    finally:
        for d in locked:
            allow(d)
        allow(tmp)
        shutil.rmtree(tmp, ignore_errors=True)
    print("all %d passed" % N)


if __name__ == "__main__":
    main()
