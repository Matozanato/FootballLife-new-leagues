r"""python tools/test_gui_export.py [<folder with the game's tables>]

The Build page's Export, the way a click on it runs (FL Testovi 18.11.2026, candidate beta4t: every
GUI export of every world stopped with

    unexpected error: ui.py:564 run -> builder.py:5979 job -> builder.py:6368 go
    NameError: name 'rpath' is not defined

-- rpath was a local of do_export, and export_as's go() used it. test_ledger_world did not see it: it
calls installer.export_world itself, never the page; its probe of the page only reads the source).

Here the whole path runs in Mod Studio's window (offscreen), with nothing stubbed between the click and
installer.export_world:

  do_export -> QFileDialog.getSaveFileName (answered: the zip's path) -> look() in a worker (ui.run_job)
  -> looked() on the window's thread -> export_as -> the version dialog (exec answered OK, the version
  typed in its line) -> self.run(go, background=True) -> go() in a worker -> installer.export_world
  -> done() (the "Saved ..." box, answered) -> keep()

The event loop is pumped until no job is left (ui._JOBS, ui._OWED, the page's busy), as
test_modstudio_build does. Checked for each export: the zip is there, it holds fl26ids-ledger.json with
the version typed, the page's log has no "unexpected error" and no "error:", and export_world got
recipe_path = the open recipe's file (mine) or None (a world on disk that is not the open recipe).

  mine=True,  v1  the open recipe's world, its first version
  mine=True,  v2  the same world again: the recipe names v1's ledger by a path relative to the recipe's
                  folder (id_ledger), which only recipe_path finds -- the zip says careers of v1 go on
  mine=False      another world on disk (a card of My world), not the open recipe

Offline: a temporary game folder, APPDATA, FL26_SAVE_ROOT and FL26_LEDGER_STORE of their own (no real
ledger history is read or written), QT_QPA_PLATFORM=offscreen. No game is started.
<folder with the game's tables> defaults to %APPDATA%\FL26ModStudio\tables27\common\etc\pesdb.
"""
import json, os, shutil, sys, tempfile, time, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
REAL_APPDATA = os.environ.get("APPDATA", "")
TMP = tempfile.mkdtemp(prefix="fl26-guiexport-")
os.environ["APPDATA"] = os.path.join(TMP, "appdata")
os.environ["FL26_SAVE_ROOT"] = os.path.join(TMP, "KONAMI", "eFootball PES 2021 SEASON UPDATE", "2026")
STORE = os.path.join(TMP, "store", "ledgers")
os.environ["FL26_LEDGER_STORE"] = STORE             # never this PC's real history of shared worlds
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import leaguebuilder as B
import idledger as D
from modstudio import installer as I
from modstudio.pages import builder as BP

N = 0
MINE = "_FL26GuiExport"
OTHER = "_FL26GuiOther"


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def league(name, country, names, cups=False):
    q = {"name": name, "country": country, "clubs": len(names), "legs": 2, "club_names": list(names)}
    if cups:
        q.update(cup=True, supercup=True)
    return q


def recipe_of(world, tag):
    A = ["%s Alba %d" % (tag, i) for i in range(11)]
    Dn = ["%s Andor %d" % (tag, i) for i in range(10)]
    squad = {str(k): {"name": "%s Player %d" % (tag, k), "Registered Position": "CF" if k else "GK", "Age": "24",
                      "birth_date": "2001-02-%02d" % (k + 1)} for k in range(18)}
    return {"world": world, "leagues": [league(tag + " Albania", "Albania", A, True),
                                        league(tag + " Andorra", "Andorra", Dn)],
            "players": {tag + " Albania/0": {"edits": squad}}}


def build(g, base, recipe):
    """the world on disk, as Mod Studio's Build makes it (plan_of, then leaguebuilder.build)"""
    from types import SimpleNamespace
    stub = SimpleNamespace(ok=lambda: True, livecpk_dir=os.path.join(g, "SiderAddons", "livecpk"), folder=g)
    pl = BP.plan_of(recipe, base, stub)
    B.build(pl, base, g, True, log=lambda *a: None)
    assert os.path.isfile(os.path.join(g, "SiderAddons", "livecpk", recipe["world"], I.WORLD_FILE)), recipe["world"]


def main(base):
    try:
        run(base)
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
    print("test_gui_export: ok (%d)" % N)


def run(base):
    # ---- the game folder with two built worlds; the open recipe is MINE's
    g = os.path.join(TMP, "game")
    for d in ("livecpk", "modules", "content"):
        os.makedirs(os.path.join(g, "SiderAddons", d))
    with open(os.path.join(g, "SiderAddons", "sider.ini"), "w") as f:
        f.write("[sider]\n")
    mine, other = recipe_of(MINE, "Gx"), recipe_of(OTHER, "Gy")
    build(g, base, mine)
    build(g, base, other)
    with open(os.path.join(g, "FL_2026.exe"), "wb") as f:
        f.write(b"MZ")
    ms = os.path.join(os.environ["APPDATA"], "FL26ModStudio")
    os.makedirs(os.path.join(ms, "recipes"))
    rdir = os.path.join(TMP, "my recipes")       # a recipe the author saved (not Mod Studio's kept copy)
    os.makedirs(rdir)
    rfile = os.path.join(rdir, MINE + ".json")
    with open(rfile, "w", encoding="utf-8") as f:
        json.dump(mine, f, indent=1)
    os.makedirs(os.path.join(ms, "tables"))
    with open(os.path.join(ms, "settings.json"), "w", encoding="utf-8") as f:
        json.dump({"game": g, "tables": os.path.join(ms, "tables"), "check_updates": False, "tour": "0.2.4",
                   "last_recipe": rfile}, f)
    for k in ("FL26_DIR", "FL26_EXE", "FL26_SIDER"):
        os.environ.pop(k, None)

    from PySide6.QtWidgets import QApplication, QDialog, QLineEdit
    qa = QApplication.instance() or QApplication([])
    from modstudio import app as A, theme, ui as UI, saves as SV
    SV.game_running = lambda: False
    theme.apply(qa)

    # ---- what a player answers; nothing between the click and export_world is stubbed
    answer = {"out": None, "version": None}
    boxes = []
    BP.QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (answer["out"], "Zip (*.zip)"))

    class VersionDialog(QDialog):
        """export_as's dialog: the version typed in its line, then OK"""
        def exec(self):
            edits = self.findChildren(QLineEdit)
            assert len(edits) == 1, "the version dialog has %d lines" % len(edits)
            boxes.append(("version shown", edits[0].text()))
            edits[0].setText(answer["version"])
            return QDialog.Accepted
    BP.QDialog = VersionDialog
    BP.info = lambda parent, title, text: boxes.append(("info", text))
    BP.error = lambda parent, title, text: boxes.append(("error", text))
    BP.ask = lambda parent, title, text: boxes.append(("ask", text)) or True
    calls = []
    real_export = I.export_world

    def export_world(*a, **k):
        calls.append(k)
        return real_export(*a, **k)
    I.export_world = export_world

    w = A.Main()
    page = w.page("Build")
    page.ask_lineage = lambda *a, **k: boxes.append(("lineage", a)) or False
    ok("the open recipe is %s, its file %s (%s %s)" % (MINE, rfile, w.project.recipe.get("world"), w.project.path),
       w.project.recipe.get("world") == MINE and os.path.normcase(w.project.path or "") == os.path.normcase(rfile))

    def export(world, version, out):
        """the Export click of the Build page (world None) or of a card of My world (a world on disk)"""
        answer.update(out=out, version=version)
        boxes.clear()
        calls.clear()
        page.do_export(world)
        t0 = time.time()
        while time.time() - t0 < 300:
            qa.processEvents()
            time.sleep(0.02)
            idle = not UI._JOBS and not UI._OWED and not w._busy
            said = page.out.toPlainText()
            if idle and (any(k in ("info", "error") for k, _t in boxes) or "unexpected error" in said
                         or "error:" in said):
                break
        for _i in range(20):                     # what the last job still posted (keep(), refresh)
            qa.processEvents()
            time.sleep(0.01)
        log = page.out.toPlainText()
        print("  log: " + " | ".join(l for l in log.splitlines() if l.strip())[-600:])
        ok("%s %s: no 'unexpected error' (NameError: rpath) in the page's log" % (world or "open", version),
           "unexpected error" not in log and "NameError" not in log and "Traceback" not in log)
        ok("%s %s: no error in the log and no error box (%s)" % (world or "open", version,
                                                                 [t[:160] for k, t in boxes if k == "error"]),
           "error:" not in log and not [1 for k, _t in boxes if k == "error"])
        ok("%s %s: the version dialog was shown, the 'Saved' box came" % (world or "open", version),
           [1 for k, _t in boxes if k == "version shown"] and
           [t for k, t in boxes if k == "info" and out in t])
        ok("%s %s: export_world ran once from the page" % (world or "open", version), len(calls) == 1)
        with zipfile.ZipFile(out) as z:
            names = z.namelist()
            w_ = world or MINE
            led = json.loads(z.read("SiderAddons/livecpk/%s/%s" % (w_, D.LEDGER)))
            winfo = json.loads(z.read(I.WORLD_INFO))
        ok("%s %s: the zip holds fl26ids-ledger.json with version %r" % (world or "open", version, version),
           "SiderAddons/livecpk/%s/%s" % (w_, D.LEDGER) in names and led.get("version") == version
           and led.get("world") == w_ and winfo.get("pack_version") == version)
        return calls[0], led, winfo, log

    # ---- mine=True, v1: the open recipe's world
    z1 = os.path.join(TMP, "out", MINE + "-1.zip")
    os.makedirs(os.path.dirname(z1))
    k1, led1, info1, _log = export(None, "Gui 1", z1)
    ok("mine v1: export_world got recipe_path = the open recipe's file (%s)" % k1.get("recipe_path"),
       os.path.normcase(k1.get("recipe_path") or "") == os.path.normcase(rfile))
    ok("mine v1: the first version (%s), kept in FL26_LEDGER_STORE" % info1.get("careers"),
       (info1.get("careers") or {}).get("first") and any(x[2].startswith(STORE) for x in D.store_files(MINE)))
    ok("mine v1: no lineage question", not [1 for k, _t in boxes if k == "lineage"])

    # ---- mine=True, v2: the recipe names v1's ledger next to the recipe file (only recipe_path finds it)
    v1file = D.store_files(MINE)[-1][2]
    shutil.copy2(v1file, os.path.join(rdir, "gx-v1.fl26ids"))
    for _n, _l, p in D.store_files(MINE):
        os.remove(p)                             # the history is empty: id_ledger is the only way to v1
    ok("mine v2: v1's ledger is only next to the recipe now", not D.store_files(MINE)
       and os.path.normcase(os.path.dirname(D.store_dir())) != os.path.normcase(rdir))
    w.project.recipe[D.LEDGER_KEY] = "gx-v1.fl26ids"
    z2 = os.path.join(TMP, "out", MINE + "-2.zip")
    k2, led2, info2, _log = export(None, "Gui 2", z2)
    ok("mine v2: recipe_path = the recipe's file again", os.path.normcase(k2.get("recipe_path") or "")
       == os.path.normcase(rfile))
    ok("mine v2: careers of Gui 1 go on (the id_ledger beside the recipe was found: %s)" % info2.get("careers"),
       (info2.get("careers") or {}).get("continue_from") == "Gui 1" and led2.get("number") == 2
       and led2.get("lineage") == led1.get("lineage"))
    ok("mine v2: the version dialog offered a version after Gui 1 (%r)" %
       [t for k, t in boxes if k == "version shown"], [t for k, t in boxes if k == "version shown"])

    # ---- mine=False: another world on disk, not the open recipe
    z3 = os.path.join(TMP, "out", OTHER + "-1.zip")
    k3, led3, info3, _log = export(OTHER, "Other 1", z3)
    ok("mine=False: export_world got recipe_path None and the world's own recipe (%s)" % k3.get("recipe_path"),
       k3.get("recipe_path") is None and (k3.get("recipe") or {}).get("world") == OTHER)
    ok("mine=False: its first version, the open recipe untouched",
       (info3.get("careers") or {}).get("first") and w.project.recipe.get("world") == MINE
       and w.project.recipe.get(D.LEDGER_KEY) == "gx-v1.fl26ids")
    w.close()


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    base = args[0] if args else os.path.join(REAL_APPDATA, "FL26ModStudio", "tables27", "common", "etc", "pesdb")
    if not os.path.isdir(base):
        raise SystemExit(__doc__ + "\nno tables folder " + base)
    main(base)
