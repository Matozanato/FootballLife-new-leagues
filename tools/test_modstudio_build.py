r"""python tools/test_modstudio_build.py <game folder> [<tables folder>] [--recipe <json>] [--keep]

Build and install through Mod Studio itself -- the Build page's *Build and install*, run offscreen
-- on a PC set up like a player's, not like ours:

  * the game is in a folder of its own (a temporary "Football Life Ž test\Juego", with a space and
    a letter outside ASCII), never C:\Football Life 2026;
  * FL26_DIR, FL26_EXE and FL26_SIDER are not set; Mod Studio has only its Settings;
  * Mod Studio's settings folder (%APPDATA%\FL26ModStudio) is a fresh one with the tables only.

0.2.2 went out tested through the command line only, on our PC where FL26_DIR is always set:
Build closed the program (a SystemExit in the worker thread), then stopped with
"FL_2026.exe not found at C:\Football Life 2026" for everyone whose game is elsewhere (OneDrive).
This test fails on both.

<game folder> gives FL_2026.exe (linked or copied into the temporary folder). <tables folder> is
Mod Studio's unpacked tables, %APPDATA%\FL26ModStudio\tables by default. --recipe defaults to
testdata/regress018/eu_places.json (three leagues with European places, so the cup dates are read
from the exe). --keep leaves the temporary folders for a look.
"""
import json, os, shutil, site, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
FAKE = os.path.join("Football Life \u017d test", "Juego")


def child(game, recipe):
    """runs inside the clean environment: Mod Studio's window, Build and install, then checks"""
    for k in ("FL26_DIR", "FL26_EXE", "FL26_SIDER"):
        assert k not in os.environ, k
    sys.path.insert(0, HERE)
    from PySide6.QtWidgets import QApplication
    qt = QApplication(sys.argv)
    from modstudio import app as A, VERSION
    import modstudio.pages.builder as PB
    PB.ask = lambda *a, **k: True                     # "Build ... and make it the live world?": yes
    seen = {}

    class After:                                       # the after-build window: note it, don't wait
        def __init__(self, page, info):
            seen["info"] = info

        def exec(self):
            seen["shown"] = True
    PB.AfterBuild = After
    w = A.Main()
    import flpaths
    print("Mod Studio %s, game %s" % (VERSION, w.game.folder))
    assert os.path.normcase(w.game.folder) == os.path.normcase(game), w.game.folder
    assert os.path.normcase(flpaths.EXE) == os.path.normcase(os.path.join(game, "FL_2026.exe")), \
        "the exe readers look at %s, not the game folder from Settings" % flpaths.EXE
    print("ok flpaths points at the game folder from Settings")
    world = json.load(open(recipe, encoding="utf-8"))["world"]
    assert w.project.recipe.get("world") == world, w.project.recipe.get("world")
    p = w.page("Build")
    p.build_all()
    t0 = time.time()
    while time.time() - t0 < 1800:
        qt.processEvents()
        time.sleep(0.05)
        if "shown" in seen or (not w._busy and time.time() - t0 > 5):
            break
    out = p.out.toPlainText()
    print("\n".join(l for l in out.splitlines() if "no player" not in l)[-3000:])
    assert "unexpected error" not in out, "Build stopped with an unexpected error"
    assert "error:" not in out, "Build stopped with an error"
    assert "cup dates could not be read" not in out, "Build could not read the exe in the game folder"
    assert seen.get("shown"), "Build and install did not finish (no after-build window)"
    print("ok Build and install finished in %ss" % seen["info"].get("secs"))
    mods = os.path.join(w.game.sider_dir, "modules")
    assert os.path.isfile(os.path.join(mods, "fl26world.txt")), "no fl26world.txt in " + mods
    assert os.path.isdir(os.path.join(w.game.sider_dir, "livecpk", world)), "no world folder"
    ini = open(w.game.ini_path, encoding="utf-8", errors="replace").read()
    assert "livecpk\\%s" % world in ini, "the world is not switched on in sider.ini"
    print("ok %s built, its world file in modules, switched on in sider.ini" % world)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    recipe = os.path.join(HERE, "testdata", "regress018", "eu_places.json")
    if "--recipe" in sys.argv:
        recipe = sys.argv[sys.argv.index("--recipe") + 1]
        args.remove(recipe)
    if not args:
        raise SystemExit(__doc__)
    src_game = args[0]
    tables = args[1] if len(args) > 1 else os.path.join(os.environ.get("APPDATA", ""), "FL26ModStudio", "tables")
    exe = os.path.join(src_game, "FL_2026.exe")
    assert os.path.isfile(exe), "no FL_2026.exe in " + src_game
    assert os.path.isdir(tables), "no tables folder " + tables

    tmp = tempfile.mkdtemp(prefix="fl26msbuild-")
    game = os.path.join(tmp, FAKE)
    sider = os.path.join(game, "SiderAddons")
    os.makedirs(os.path.join(sider, "livecpk"))
    os.makedirs(os.path.join(sider, "modules"))          # a Sider install has both
    try:
        os.link(exe, os.path.join(game, "FL_2026.exe"))
    except OSError:                                    # another drive: a copy
        shutil.copy2(exe, os.path.join(game, "FL_2026.exe"))
    with open(os.path.join(sider, "sider.ini"), "w", encoding="utf-8") as f:
        f.write("[sider]\ndebug = 0\n")
    appdata = os.path.join(tmp, "appdata")
    msdir = os.path.join(appdata, "FL26ModStudio")
    shutil.copytree(tables, os.path.join(msdir, "tables"))
    os.makedirs(os.path.join(msdir, "recipes"))
    rc = os.path.join(msdir, "recipes", os.path.basename(recipe))
    shutil.copy2(recipe, rc)
    json.dump({"game": game, "last_recipe": rc}, open(os.path.join(msdir, "settings.json"), "w", encoding="utf-8"))

    env = {k: v for k, v in os.environ.items() if k not in ("FL26_DIR", "FL26_EXE", "FL26_SIDER")}
    env.update(APPDATA=appdata, PYTHONUSERBASE=site.USER_BASE, QT_QPA_PLATFORM="offscreen",
               PYTHONIOENCODING="utf-8")
    try:
        r = subprocess.run([sys.executable, os.path.abspath(__file__), "--child", game, rc], env=env)
    finally:
        if "--keep" in sys.argv:
            print("kept", tmp)
        else:
            shutil.rmtree(tmp, ignore_errors=True)
    if r.returncode:
        raise SystemExit("FAIL: Build through Mod Studio (see above)")
    print("test_modstudio_build: ok")


if __name__ == "__main__":
    if "--child" in sys.argv:
        i = sys.argv.index("--child")
        child(sys.argv[i + 1], sys.argv[i + 2])
    else:
        main()
