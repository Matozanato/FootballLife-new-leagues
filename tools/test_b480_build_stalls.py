r"""python tools/test_b480_build_stalls.py

B480 (16.11.2026): with the GigaPack the window stood still twice after a Build click: the plan
(leaguebuilder.plan, lbplayers.check under it) and then the copy of the recipe Build keeps
(Project.keep_copy, one json.dumps of the 260 MB recipe) ran on the window's thread. The stall
probe on a copy of the GigaPack (offscreen, Mod Studio 64a80c3) measured 4.2 s and 9.2 s.
Both now run in a worker; the window answers meanwhile and the Build buttons are off.

Here: the whole window in this process (QT_QPA_PLATFORM=offscreen), a fake game folder and
APPDATA in a temp folder, a recipe of about 75 MB of text (player edits; the GigaPack's is
260 MB), and leaguebuilder.plan replaced by 1.2 s of pure-Python work (the GigaPack's plan took
2.4 s in the exe and 4.2 s in the probe). The world build itself is not run. Checks, for Build
and install and for Build alone: no stop of the window's thread over 0.5 s from the click to the
build; the copy Build keeps is byte for byte the text keep_copy writes; an error of the plan is
said as before and the buttons come back. No game.
"""
import json, os, shutil, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.pop("FL26_DIR", None)
T = tempfile.mkdtemp(prefix="b480build-")
os.environ["APPDATA"] = os.path.join(T, "appdata")
os.environ["FL26_SAVE_ROOT"] = os.path.join(T, "konami")

from test_world_manage import make_game

LIMIT = 0.5
PLAYERS = int(os.environ.get("B480_PLAYERS", "220000"))
N = 0
FAILED = []
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def ok(name, cond):
    global N
    N += 1
    print("%s %d - %s" % ("ok" if cond else "FAIL", N, name))
    if not cond:
        FAILED.append(name)


def busy_work(secs):
    """pure Python for `secs` (holds the interpreter like leaguebuilder.plan does)"""
    end, x = time.perf_counter() + secs, 0
    while time.perf_counter() < end:
        for i in range(2000):
            x += i * i
    return x


def main():
    try:
        run()
    finally:
        shutil.rmtree(T, ignore_errors=True)
    print("all passed" if not FAILED else "%d failed" % len(FAILED))
    sys.exit(1 if FAILED else 0)


def run():
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    qa = QApplication.instance() or QApplication([])
    sys.setswitchinterval(0.001)                      # as modstudio.app.main
    from modstudio import app as A, saves as SV, apart
    from modstudio.pages import builder as PB
    import leaguebuilder as B
    SV.game_running = lambda: False
    game = make_game(T)
    ms = os.path.join(os.environ["APPDATA"], "FL26ModStudio")
    os.makedirs(os.path.join(ms, "tables"))
    with open(os.path.join(ms, "settings.json"), "w", encoding="utf-8") as f:
        json.dump({"game": game.folder, "tables": os.path.join(ms, "tables"), "check_updates": False}, f)
    w = A.Main()
    b = w.page("Build")

    # what the Build buttons reach after the plan: stubs (no game, no world build)
    seen = {}

    class Switch:
        def ask_text(self):
            return ""

        def note(self):
            return ""

    class After:
        def __init__(self, page, info):
            seen["info"] = info

        def exec(self):
            seen["after"] = time.perf_counter()
    PB.AfterBuild = After
    PB.ask = lambda *a, **k: True
    PB.can_write = lambda *a, **k: True
    PB.save_switch = lambda *a, **k: Switch()
    PB.snapshot = lambda *a, **k: None
    for n in ("database_note", "exhibition_note", "kits_note"):
        setattr(PB, n, lambda *a, **k: None)
    b.ready_blocks = lambda *a, **k: False
    b.switch_with_saves = lambda *a, **k: None
    B.tables_stale = lambda *a, **k: None
    B.install_modules = lambda *a, **k: None
    B.describe = lambda *a, **k: "(the plan)"
    B.pin_newlife = lambda r, base, pl=None: False
    B.game_clubs = lambda *a, **k: {}                  # the pages that read the tables (there are none here)
    plan_secs = [1.2]
    plan_error = [None]

    def plan(r, base, prev):
        busy_work(plan_secs[0])
        if plan_error[0]:
            raise B.BuildError(plan_error[0])
        return {"world": r["world"], "leagues": []}
    B.plan = plan

    def build(pl, base, g, replace, log):
        seen["build"] = time.perf_counter()
    apart.build = build

    # a recipe of about the GigaPack's kind: its bulk is player edits
    rec = {"world": "_FL26Gap", "leagues": [{"name": "Gap League", "country": "Croatia", "clubs": 2}],
           "players": {str(100000 + i): {"edits": {"name": "Player %d " % i + "x" * 300, "ovr": 70}}
                       for i in range(PLAYERS)}}
    w.project.recipe = rec
    w.project.base = os.path.join(ms, "tables")
    w.page("NewLeagues").world.setText("_FL26Gap")
    size = len(w.project._text(rec))
    print("# recipe text %.0f MB, plan %.1f s of work" % (size / 2**20, plan_secs[0]))

    beat = {"last": time.perf_counter(), "worst": 0.0}

    def tick():
        now = time.perf_counter()
        beat["worst"] = max(beat["worst"], now - beat["last"])
        beat["last"] = now
    hb = QTimer(interval=10)
    hb.timeout.connect(tick)
    hb.start()

    def spin(cond, secs):
        end = time.perf_counter() + secs
        while time.perf_counter() < end and not cond():
            qa.processEvents()
            time.sleep(0.003)
        return cond()

    def click(fn, until):
        seen.clear()
        spin(lambda: False, 0.3)
        beat["last"], beat["worst"] = time.perf_counter(), 0.0
        QTimer.singleShot(0, fn)
        got = spin(lambda: until in seen, 120)
        spin(lambda: False, 0.3)
        return got, beat["worst"]

    # 1. Build and install: from the click to the build
    got, worst = click(b.build_all, "after")
    ok("Build and install reached the build and the window after it", got and "build" in seen)
    ok("Build and install: the window's longest stop from the click on %.2f s (limit %.1f)" % (worst, LIMIT),
       worst < LIMIT)
    kept = w.settings.get("last_recipe")
    ok("Build kept its copy of the recipe: %s" % kept, bool(kept) and os.path.isfile(kept))
    if kept and os.path.isfile(kept):
        with open(kept, "rb") as f:
            by_worker = f.read()
        again = w.project.keep_copy()                 # the copy as keep_copy writes it on the spot
        with open(again, "rb") as f:
            plain = f.read()
        ok("the kept copy is byte for byte what keep_copy writes (%d bytes)" % len(plain),
           again == kept and by_worker == plain)
        ok("... and no .keep.tmp is left", not [n for n in os.listdir(os.path.dirname(kept)) if n.endswith(".tmp")])
    ok("the Build buttons are back on after it", b.b_all.isEnabled())

    # 2. Build alone (step 2): the same
    got, worst = click(b.do_build, "build")
    spin(lambda: b.b_all.isEnabled(), 10)
    ok("Build reached the build", got)
    ok("Build: the window's longest stop from the click on %.2f s (limit %.1f)" % (worst, LIMIT), worst < LIMIT)

    # 3. an error of the plan: said in the log as before, the buttons come back
    plan_error[0] = "probe: no such league"
    plan_secs[0] = 0.2
    seen.clear()
    QTimer.singleShot(0, b.build_all)
    spin(lambda: "probe: no such league" in b.out.toPlainText(), 20)
    spin(lambda: False, 0.3)
    ok("a plan error is said in Build's log: %r" % b.out.toPlainText()[-60:],
       "error: probe: no such league" in b.out.toPlainText())
    ok("... nothing was built", "build" not in seen)
    ok("... and the Build buttons are back on", b.b_all.isEnabled())
    hb.stop()
    w.project.dirty = False
    w.close()


if __name__ == "__main__":
    main()
