"""python tools/test_dll_check.py

B15 (bikolunar42, 13.10.): an antivirus quarantined fl26swiss.dll, fl26join.dll ... in
SiderAddons\\modules right after Install modules. The .lua files stayed, the game started
without the European draws and cups, sider.log said LoadLibraryA failed (error 126), and Mod
Studio said nothing.

Install the modules now checks every DLL of the pack after the copy (there, and the shipped
bytes) and stops with a message that names the file and says what to do; Home / Diagnostics
(checks.dll_problems) and 4. Check (leaguebuilder.check) say the same while a DLL a
switched-on module of ours loads is missing. The antivirus is played by the test: it deletes or
empties the DLL while the install waits for it. No window, no game.
"""
import os, shutil, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import leaguebuilder as B
from modstudio import checks
from modstudio.game import Game
from modstudio.siderini import SiderIni

N = 0
SWISS = b"MZ swiss dll " * 50
JOIN = b"MZ join dll " * 40


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def write(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(data if isinstance(data, bytes) else data.encode("utf-8"))


def make_pack(root):
    pack = os.path.join(root, "pack")
    m = os.path.join(pack, "modules")
    write(os.path.join(pack, "modules.txt"), "fl26caps\nfl26joindll\nfl26swiss\n")
    write(os.path.join(m, "fl26caps.lua"), "-- caps, no DLL\nlocal m = {}\nreturn m\n")
    write(os.path.join(m, "fl26joindll.lua"),
          '-- loader\nlocal dllpath = sider_dir .. sep .. "modules" .. sep .. "fl26join.dll"\n'
          'log("is fl26old.dll next to this file in modules?")\n')
    write(os.path.join(m, "fl26swiss.lua"), 'local p = dir .. "fl26swiss.dll"\n')
    write(os.path.join(m, "fl26join.dll"), JOIN)
    write(os.path.join(m, "fl26swiss.dll"), SWISS)
    return pack


def make_game(root):
    g = os.path.join(root, "Football Life 2026")
    write(os.path.join(g, "FL_2026.exe"), b"MZ")
    write(os.path.join(g, "SiderAddons", "sider.ini"), "[sider]\nlua.enabled = 1\n")
    os.makedirs(os.path.join(g, "SiderAddons", "modules"))
    return g


def install(game, antivirus=None):
    """install_modules with `antivirus` run while it waits for one; (log lines, error or None)"""
    log = []
    keep = time.sleep
    if antivirus:
        time.sleep = lambda s: antivirus()
    try:
        B.install_modules(game, log=log.append, settle=0.01)
        err = None
    except B.BuildError as e:
        err = e
    finally:
        time.sleep = keep
    return log, err


def main():
    tmp = tempfile.mkdtemp(prefix="fl26ms_dll_")
    keep = B.pack_dir
    try:
        pack = make_pack(tmp)
        B.pack_dir = lambda: pack
        game = make_game(tmp)
        mdir = os.path.join(game, "SiderAddons", "modules")

        ok("dll_names reads the DLL a loader's Lua loads, not one named in a sentence",
           B.dll_names(os.path.join(pack, "modules", "fl26joindll.lua")) == ["fl26join.dll"])
        ok("a module with no DLL names none", B.dll_names(os.path.join(pack, "modules", "fl26caps.lua")) == [])

        log, err = install(game)
        ok("a clean install goes through", err is None)
        ok("... and says the DLLs are in place", any("all 2 DLLs in place" in l for l in log))
        ok("check_dlls finds nothing wrong", B.check_dlls(mdir, ["fl26join.dll", "fl26swiss.dll"],
                                                           os.path.join(pack, "modules")) == [])

        g = Game(game)
        ini = SiderIni.load(g.ini_path)
        ok("the install switched the modules on", {e.value for e in ini.entries("lua.module") if e.enabled}
           >= {"fl26joindll.lua", "fl26swiss.lua"})
        ok("Home: no DLL row while they are there", checks.dll_problems(g, ini) == [])

        # the antivirus takes fl26swiss.dll a moment after the copy
        os.remove(os.path.join(mdir, "fl26swiss.dll"))           # so the next install copies it again
        log, err = install(game, antivirus=lambda: os.remove(os.path.join(mdir, "fl26swiss.dll")))
        ok("Install the modules stops when the antivirus took a DLL", err is not None)
        msg = str(err)
        ok("... and names the file", "fl26swiss.dll" in msg and "fl26join.dll" not in msg)
        ok("... and says an antivirus probably removed it", "antivirus" in msg and "quarantined" in msg)
        ok("... and says what to do: exclusion, install again",
           "exclusion" in msg and "Install the modules again" in msg and os.path.join(game, "SiderAddons") in msg)
        ok("... no Python words in it", "Traceback" not in msg and "Error" not in msg)
        ok("the log has it too", any("fl26swiss.dll" in l for l in log))

        rows = checks.dll_problems(g, ini)
        ok("Home / Diagnostics: one error row", len(rows) == 1 and rows[0][0] == "err")
        ok("... naming the DLL, the module and the antivirus",
           "fl26swiss.dll" in rows[0][2] and "fl26swiss.lua" in rows[0][2] and "antivirus" in rows[0][2])
        ok("... and the row leads to Build", rows[0][3] == "Build")
        ok("checks.quick has the row", any("fl26swiss.dll" in r[2] for r in checks.quick(g, ini)))

        # 4. Check (after starting the game) says it as well
        write(g.log_path, "[fl26swiss.lua] LoadLibraryA failed (err 126)\n")
        out = []
        ok("4. Check fails", B.check(game, log=out.append) is False)
        ok("... and names the missing DLL with the antivirus", any("fl26swiss.dll" in l and "antivirus" in l for l in out))

        # a switched-off module: its DLL is not needed
        text = open(g.ini_path, encoding="utf-8").read().replace('lua.module = "fl26swiss.lua"',
                                                                  ';lua.module = "fl26swiss.lua"')
        write(g.ini_path, text)
        ini_off = SiderIni.load(g.ini_path)
        ok("a module switched off needs no DLL", checks.dll_problems(g, ini_off) == [])
        write(g.ini_path, text.replace(';lua.module = "fl26swiss.lua"', 'lua.module = "fl26swiss.lua"'))

        # the antivirus empties a DLL instead (some "clean" files to 0 bytes)
        log, err = install(game, antivirus=lambda: write(os.path.join(mdir, "fl26join.dll"), b""))
        ok("an emptied DLL stops the install too", err is not None and "fl26join.dll" in str(err))
        ok("... said as not the file Mod Studio installed", "not the file Mod Studio installed" in str(err))
        ini = SiderIni.load(g.ini_path)
        rows = checks.dll_problems(g, ini)
        ok("Home: a warning for the emptied DLL", any(r[0] == "warn" and "fl26join.dll" in r[2] for r in rows))

        # a DLL of another size than the pack's, with the pack's Lua: a damaged copy
        write(os.path.join(mdir, "fl26join.dll"), JOIN + b"x")
        bad = B.check_dlls(mdir, ["fl26join.dll"], os.path.join(pack, "modules"))
        ok("check_dlls: other bytes than the pack's are 'changed'", bad == [("fl26join.dll", "changed")])
        # ... but a module of another version (its Lua not the pack's) is only checked for being there
        write(os.path.join(mdir, "fl26joindll.lua"),
              '-- an older loader\nlocal p = "fl26join.dll"\n')
        rows = checks.dll_problems(g, ini)
        ok("another version's DLL is not compared with the pack", not any("fl26join.dll" in r[2] for r in rows))

        # clean again: Install the modules puts everything back, no rows
        log, err = install(game)
        ok("installing again with nothing in the way goes through", err is None)
        ini = SiderIni.load(g.ini_path)
        ok("Home: nothing to say", checks.dll_problems(g, ini) == [])
        ok("the DLLs are the pack's bytes", open(os.path.join(mdir, "fl26swiss.dll"), "rb").read() == SWISS
           and open(os.path.join(mdir, "fl26join.dll"), "rb").read() == JOIN)
    finally:
        B.pack_dir = keep
        shutil.rmtree(tmp, ignore_errors=True)
    print("all %d passed" % N)


if __name__ == "__main__":
    main()
