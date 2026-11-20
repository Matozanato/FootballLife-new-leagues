r"""python tools/test_b480_big_world.py [--big]          (opt-in: B480_BIG=1 or --big; slow, ~10 min)

B480 round 3 (17.11.2026): the stall tests before this one (test_b480_path_stalls, _build_stalls)
said 0.00 s while the exe test of beta4r on the GigaPack still stopped the window for 0.5-6.2 s:
their world was made up and small next to the real one, and Python freed and read it in RAM. Here
the REAL GigaPack world: its plan (leaguebuilder-plan.json, 286 MB, 317 leagues, 4,500 new clubs,
109,000 players) and the files next to it are copied out of a built world on this PC (read only:
B480_WORLD, by default E:\FL\FL27\game\SiderAddons\livecpk\_FL26Megapack), and the recipe is read
back from that plan by the real leaguebuilder.recipe_from_plan with the game's real tables, as
Make it editable does it. The whole window runs in this process (offscreen), on a fake game folder
and APPDATA in a temp folder; no game.

Measured, per step, the window's longest stop (app.record_stalls: the exe's own FL26_STALLS
recorder) and the longest wait of a probe thread for its turn at Python (a worker holding Python's
lock -- freeing a world's plan in one C call, json, pickle -- stops the whole process, the window
and the recorder too: "my longest wait for a turn 1.79 s, the window's thread 0.00 s CPU" in the
exe). Each must stay under LIMIT (0.5 s). Also counted: My world's plan processes running at once
(apart.numbers: each reads the 286 MB plan, about 0.6 GB of memory each, while the window's
process was paged out), and the work the exe test put on the window's thread: who signs whom over the whole
recipe (Leagues' first opening) and Undo's compare of the whole recipe (Edit league > OK).

Steps (as in the exe test, notes\test-gp2\b4r\A):
  1. end of the zip install   world switched on, its recipe read back from the plan
  2. Make it editable         to the box "can be changed now", and 3 s after it
  3. end of Build             the build itself stubbed: the world's plan written anew, then what
                              Build's worker does after it (the new plan read, the old one freed)
  4. Leagues, first opening   (the game's leagues tab: squad sizes, who signs whom)
  5. Leagues > Edit > OK      (the league as it was: before round 3 Undo's compare and a save; now nothing)

B480_TRIM=1 (default): before each step the process's working set is emptied (psapi.EmptyWorkingSet),
as Windows does to a window left alone while a Build or a copy takes the memory; what the step then
touches comes back from the standby list (soft faults; the exe's were from the page file, slower).
B480_SETTLE=<s> (default 3): the seconds between that and the click -- in the exe test the clicks came
after the Build or the copy that had taken the memory was over (0: the click at once, harsher).
B480_KEEP=<dir>: the recorder's lines copied there. The test needs about 8 GB of free memory.

Without --big / B480_BIG=1 it says why it is skipped and passes (the suites run it as any test).
"""
import ctypes, glob, json, os, shutil, sys, tempfile, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.pop("FL26_DIR", None)
REAL_APPDATA = os.environ.get("APPDATA", "")
BIG = "--big" in sys.argv or os.environ.get("B480_BIG") == "1"
CHILD = __name__ == "__mp_main__"          # My world's plan process (apart.numbers) imports this file
if BIG and not CHILD:
    T = tempfile.mkdtemp(prefix="b480big-")
    os.environ["APPDATA"] = os.path.join(T, "appdata")
    os.environ["FL26_SAVE_ROOT"] = os.path.join(T, "konami")

LIMIT = 0.5
WORLD = "_FL26Megapack"
SRC_WORLDS = [os.environ.get("B480_WORLD"),
              r"E:\FL\FL27\game\SiderAddons\livecpk\_FL26Megapack",
              r"E:\FL\FL27\clean\Football Life 2027\SiderAddons\livecpk\_FL26Megapack"]
TABLES = [os.environ.get("B480_TABLES"),
          os.path.join(REAL_APPDATA, "FL26ModStudio", "tables27", "common", "etc", "pesdb"),
          r"E:\FL\FL27\appdata\novi_b4r_a_off\FL26ModStudio\tables27\common\etc\pesdb"]
N = 0
FAILED = []
RESULTS = []                                # (step, stop, gil wait)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def ok(name, cond):
    global N
    N += 1
    print("%s %d - %s" % ("ok" if cond else "FAIL", N, name), flush=True)
    if not cond:
        FAILED.append(name)


class _PMC(ctypes.Structure):
    _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong)] + \
               [(n, ctypes.c_size_t) for n in ("PeakWorkingSetSize", "WorkingSetSize", "a", "b", "c", "d",
                                               "PagefileUsage", "PeakPagefileUsage", "PrivateUsage")]


def private_mb():
    p = _PMC()
    p.cb = ctypes.sizeof(p)
    # the process handle as a pointer (-1; a plain int went over as 32 bits and the call failed: 0 MB)
    ctypes.windll.kernel32.K32GetProcessMemoryInfo(ctypes.c_void_p(-1), ctypes.byref(p), p.cb)
    return p.PrivateUsage / 2**20


def free_mb():
    class MS(ctypes.Structure):
        _fields_ = [("len", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [(n, ctypes.c_ulonglong) for n in
                                                                          ("total", "avail", "tp", "ap", "tv", "av", "x")]
    m = MS()
    m.len = ctypes.sizeof(MS)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.avail / 2**20


def trim():
    if os.environ.get("B480_TRIM", "1") == "1":
        k = ctypes.windll.kernel32
        ctypes.windll.psapi.EmptyWorkingSet(k.GetCurrentProcess())


class Probe(threading.Thread):
    """a thread that asks for its turn at Python every 5 ms: the longest it waited (a worker holding
    the lock stops it, as it stops the window and the exe's recorder)"""

    def __init__(self):
        super().__init__(name="gilprobe", daemon=True)
        self.worst, self.at, self.go = 0.0, None, True
        self.mark = None

    def run(self):
        import faulthandler, io
        while self.go:
            t = time.perf_counter()
            time.sleep(0.005)
            d = time.perf_counter() - t - 0.005
            if d > self.worst:
                self.worst, self.at = d, time.strftime("%H:%M:%S")

    def reset(self):
        self.worst, self.at = 0.0, None


def main():
    if CHILD:
        return
    if not BIG:
        print("skipped: the real GigaPack world, ~10 min and ~8 GB of memory -- run with --big or B480_BIG=1")
        sys.exit(0)
    try:
        run()
    finally:
        shutil.rmtree(T, ignore_errors=True)
    print("\n# step                         longest stop   longest wait for Python's lock")
    for step, stop, gil in RESULTS:
        print("#  %-28s %6.2f s        %6.2f s" % (step, stop, gil))
    print("all passed" if not FAILED else "%d failed" % len(FAILED))
    sys.exit(1 if FAILED else 0)


def run():
    import faulthandler
    faulthandler.dump_traceback_later(int(os.environ.get("B480_DUMP", "1800")), exit=True)
    src = next((d for d in SRC_WORLDS if d and os.path.isfile(os.path.join(d, "leaguebuilder-plan.json"))), None)
    tables = next((d for d in TABLES if d and os.path.isfile(os.path.join(d, "Country.bin"))), None)
    if not src or not tables:
        sys.exit("no built GigaPack world (B480_WORLD) or no FL27 tables (B480_TABLES) on this PC")
    from PySide6.QtCore import QEventLoop, QTimer
    from PySide6.QtWidgets import QApplication, QMessageBox
    qa = QApplication.instance() or QApplication([])
    sys.setswitchinterval(0.001)                      # as modstudio.app.main
    try:
        from modstudio import procstat                # ... and its memory keeper (round 3; not in beta4r)
        procstat.keep_in()
    except ImportError:
        pass
    from modstudio import gentlejson
    gentlejson.install()
    import bigjson
    bigjson.GENTLE = True
    from modstudio import app as A, saves as SV, apart, installer as I, letgo, game as G, theme
    from modstudio import filecache as FC
    from modstudio.pages import builder as PB, myworld as M
    import leaguebuilder as B
    from test_world_manage import make_game, put
    SV.game_running = lambda: False
    real_names = G._process_names
    # the real look at the process list (the exe's "running" thread), but never "the game runs"
    G.Game.running = staticmethod(lambda: (real_names() is None and False, False))
    theme.apply(qa)
    game = make_game(T)
    sd = game.sider_dir
    ms = os.path.join(os.environ["APPDATA"], "FL26ModStudio")
    os.makedirs(os.path.join(ms, "tables"))
    for n in os.listdir(tables):
        if n.endswith(".bin"):
            shutil.copy2(os.path.join(tables, n), os.path.join(ms, "tables", n))
    with open(os.path.join(ms, "settings.json"), "w", encoding="utf-8") as f:
        json.dump({"game": game.folder, "tables": os.path.join(ms, "tables"), "check_updates": False}, f)

    # ---- the real world, as a zip install leaves it (a ready world: .modstudio) ----
    wd = os.path.join(sd, "livecpk", WORLD)
    os.makedirs(wd)
    for n in ("leaguebuilder-plan.json", "fl26world.txt", "fl26playerids.json", "leaguebuilder-input.json",
              "leaguebuilder-files.txt"):
        if os.path.isfile(os.path.join(src, n)):
            shutil.copy2(os.path.join(src, n), os.path.join(wd, n))
    # its tables (the window knows a world in the game by its common\etc\pesdb\Team.bin)
    shutil.copytree(os.path.join(src, "common", "etc", "pesdb"), os.path.join(wd, "common", "etc", "pesdb"))
    put(os.path.join(wd, ".modstudio"), "GigaPack (test)")
    put(os.path.join(wd, "modules", "fl26regions.lua"), "-- regions\n")
    # the world on in sider.ini, as the install's worker leaves it (the Live world's line off)
    with open(game.ini_path, encoding="utf-8", newline="") as f:
        t = f.read()
    t = t.replace('cpk.root = ".\\livecpk\\_FL26Live"', '#cpk.root = ".\\livecpk\\_FL26Live"')
    with open(game.ini_path, "w", encoding="utf-8", newline="") as f:
        f.write(t + 'cpk.root = ".\\livecpk\\%s"\r\n' % WORLD)
    rows = I.records(sd)
    rec0 = dict(next(r for r in rows if r.get("world") == "_FL26Old"))
    rec0.update(world=WORLD, name="GigaPack by MatoZanato (test)",
                created=[os.path.join("livecpk", WORLD, "common", "x", "%06d.bin" % i) for i in range(160000)])
    rows.append(rec0)
    I._save(sd, rows)
    plan_path = os.path.join(wd, "leaguebuilder-plan.json")
    print("# the world: a copy of %s (plan %.0f MB); tables %s; free memory %.1f GB"
          % (src, os.path.getsize(plan_path) / 2**20, tables, free_mb() / 1024), flush=True)

    # what a fake game folder cannot do, left out (as test_b480_path_stalls)
    B.install_modules = lambda *a, **k: None
    B.tables_stale = lambda *a, **k: None
    B.describe = lambda *a, **k: "(the plan)"
    B.pin_newlife = lambda r, base, pl=None: False
    from modstudio import checks as CK
    CK.short_squads = lambda *a, **k: []
    real_switch_on = B.switch_on

    def switch_on(w, folder, log=print):
        # the sider.ini line on (the maps of a fake game are not the GigaPack's)
        p = os.path.join(sd, "sider.ini")
        with open(p, encoding="utf-8", newline="") as fh:
            t = fh.read()
        t = t.replace('cpk.root = ".\\livecpk\\_FL26Live"', '#cpk.root = ".\\livecpk\\_FL26Live"')
        t = t.replace('#cpk.root = ".\\livecpk\\%s"' % w, 'cpk.root = ".\\livecpk\\%s"' % w)
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write(t)
    B.switch_on = switch_on

    # plan processes at once (apart.numbers)
    numbers_real = apart.numbers
    inflight, most = [0], [0]

    def numbers(paths):
        inflight[0] += 1
        most[0] = max(most[0], inflight[0])
        try:
            return numbers_real(paths)
        finally:
            inflight[0] -= 1
    apart.numbers = numbers

    # the window's thread doing what the exe test caught it at: who signs whom over the recipe,
    # Undo's compare of all of it
    ON_WINDOW = []
    main_t = threading.main_thread()
    sb_real = PB.signed_by

    def signed_by(pl, nat):
        # (4 ms in RAM with the GigaPack: counted when it took long, as Undo's compare below)
        t0 = time.perf_counter()
        got = sb_real(pl, nat)
        took = time.perf_counter() - t0
        if threading.current_thread() is main_t and took > 0.1:
            ON_WINDOW.append("signed_by over %d clubs' changes %.2f s" % (len(pl), took))
        return got
    PB.signed_by = signed_by
    from modstudio import project as PJ
    ch_real = PJ.Project._changes

    def changes(self):
        t0 = time.perf_counter()
        got = ch_real(self)
        took = time.perf_counter() - t0
        if threading.current_thread() is main_t and took > 0.1:
            ON_WINDOW.append("Undo's compare %.2f s" % took)
        return got
    PJ.Project._changes = changes

    probe = Probe()
    probe.start()
    w = A.Main()
    w.show()
    w.project.base = os.path.join(ms, "tables")
    A.record_stalls(w, os.path.join(T, "stalls.txt"))

    boxes = []

    def open_box():
        return next((x for x in QApplication.topLevelWidgets() if isinstance(x, QMessageBox) and x.isVisible()), None)

    def closer():
        m = open_box()
        if m is not None:
            if not m.property("b480_seen"):
                m.setProperty("b480_seen", time.perf_counter())
                boxes.append(m.text())
            elif time.perf_counter() - m.property("b480_seen") > float(os.environ.get("B480_BOX_S", "3.0")):
                b = m.defaultButton() or (m.buttons()[0] if m.buttons() else None)
                if b is not None:
                    b.click()
                else:
                    m.done(0)
    shut = QTimer(interval=50)
    shut.timeout.connect(closer)
    shut.start()

    def spin(cond, secs):
        end = time.perf_counter() + secs
        while time.perf_counter() < end and not cond():
            qa.processEvents(QEventLoop.AllEvents, 5)
            time.sleep(0.002)
        return cond()

    def measured(what, start, until, secs=float(os.environ.get("B480_STEP_S", "900")), after=3.0):
        spin(lambda: False, 1.0)
        trim()
        spin(lambda: False, float(os.environ.get("B480_SETTLE", "3")))
        del w._stall_gaps[:]
        del ON_WINDOW[:]
        probe.reset()
        t0 = time.perf_counter()
        QTimer.singleShot(0, start)
        got = spin(until, secs)
        if not got:
            print("#   %s: not done in %.0f s; the recipe open: %r; boxes: %s" % (
                what, secs, w.project.recipe.get("world"), [b[:120] for b in boxes[-3:]]), flush=True)
            out = getattr(w.page("Build"), "out", None)
            print("#   Build page says: %r" % (out.toPlainText()[-600:] if out is not None else None), flush=True)
            faulthandler.dump_traceback(sys.stdout, all_threads=True)
        spin(lambda: False, after)
        spin(lambda: False, 0.4)
        gaps = [g for g in w._stall_gaps if g[0] >= t0 - 0.2]
        worst = max(gaps, key=lambda g: g[1]) if gaps else (0, 0.0, [])
        gil = probe.worst
        RESULTS.append((what, worst[1], gil))
        print("#   %s: %.1f s, longest stop %.2f s%s; longest wait for the lock %.2f s (%s); private %.0f MB, "
              "free %.1f GB; plan processes at once %d" % (
                  what, time.perf_counter() - t0, worst[1],
                  (" at " + "; ".join("%dx %s" % (n, s) for s, n in worst[2][:2])) if worst[2] else "",
                  gil, probe.at, private_mb(), free_mb() / 1024, most[0]), flush=True)
        seen = sorted(set(ON_WINDOW))
        ok("%s: done (%s), the window's longest stop %.2f s, the longest wait for Python's lock %.2f s "
           "(limit %.1f); on the window's thread: %s" % (what, got, worst[1], gil, LIMIT, seen[:4]),
           got and worst[1] < LIMIT and gil < LIMIT and not seen)
        most[0] = 0
        return got

    # 1. the end of the zip install: the world switched on, its recipe read back from its plan
    ip = w.page("Install")
    w.open_page("Install")
    checked = []
    real_check = ip.final_check

    def final(world):
        real_check(world)
        checked.append(world)
    ip.final_check = final
    ini = w.ini()
    ini.save(reason="installed %s" % WORLD)

    def installed():
        w.save_ini(ini, "installed %s" % WORLD, saved=True, running=(False, False))
        w.bus.content_changed.emit()
        ip.world_on({"world": WORLD})
    measured("end of the install", installed, lambda: bool(checked) and w.project.recipe.get("world") == WORLD)
    ip.final_check = real_check
    ok("the world in the game: %s, its recipe open: %d leagues, %d clubs' player changes"
       % (WORLD, len(w.project.recipe.get("leagues") or []), len(w.project.recipe.get("players") or {})),
       w.project.recipe.get("world") == WORLD and len(w.project.recipe.get("leagues") or []) > 300)

    # 2. My world > Make it editable
    mw = w.my_world
    w.open_page("Leagues")
    M.ask = lambda *a, **k: True
    M.can_write = lambda *a, **k: True
    n_boxes = len(boxes)
    measured("Make it editable", mw.make_editable,
             lambda: any("can be changed now" in t for t in boxes[n_boxes:]) and open_box() is None, after=4.0)
    ok("... the world is editable now", not I.ready_world(game, WORLD))

    # 3. the end of BUILD AND INSTALL (the build stubbed: the plan written anew)
    b = w.page("Build")
    after = {}

    class Switch:
        def ask_text(self):
            return ""

        def note(self):
            return ""

    class After:
        def __init__(self, page, info):
            after["info"] = info

        def exec(self):
            after["at"] = time.perf_counter()
    PB.AfterBuild = After
    PB.ask = lambda *a, **k: True
    PB.can_write = lambda *a, **k: True
    PB.save_switch = lambda *a, **k: Switch()
    PB.snapshot = lambda *a, **k: None
    for n in ("database_note", "exhibition_note", "kits_note"):
        setattr(PB, n, lambda *a, **k: None)
    b.ready_blocks = lambda *a, **k: False
    b.switch_with_saves = lambda *a, **k: None
    B.plan = lambda r, base, prev: {"world": r["world"], "leagues": []}

    def build(pl, base, g, replace, log):
        shutil.copyfile(os.path.join(src, "leaguebuilder-plan.json"), plan_path + ".tmp")
        os.replace(plan_path + ".tmp", plan_path)
        after.setdefault("build", time.perf_counter())
    apart.build = build
    w.open_page("Build")
    # the plan as the window had it before Build (the pages read it): kept, so Build's worker
    # reads the new one over it as in the exe
    PB.built_plan(game, WORLD)
    measured("end of Build", b.build_all, lambda: "at" in after, after=4.0)

    # 4. Leagues, the first opening after Build (the game's leagues: squads, who signs whom)
    lp = w.page("Leagues")
    measured("Leagues, first opening", lambda: w.open_page("Leagues"),
             lambda: lp.tree.topLevelItemCount() > 0, after=3.0)

    # 5. Leagues > one of ours > Edit > OK, the league as it was
    seen_edit = {}

    class SameEdit:
        def __init__(self, page, project, L=None, **k):
            seen_edit["league"] = (L or {}).get("name")
            self.league = json.loads(json.dumps(L))

        def finish(self):
            return True
    real_dialog = PB.LeagueDialog
    PB.LeagueDialog = SameEdit
    first = next(L for L in w.project.recipe["leagues"] if not L.get("others"))
    lp.show_key("o" + first["name"])
    gen = getattr(w.project, "_gen", 0)
    measured("Leagues > Edit > OK", lambda: lp.on_ours("edit"), lambda: "league" in seen_edit, after=3.0)
    PB.LeagueDialog = real_dialog
    # (B480 round 3: OK with nothing changed leaves the recipe as it was -- no touch, no Undo step)
    ok("... the recipe not touched (OK with nothing changed)", getattr(w.project, "_gen", 0) == gen)
    letgo.wait(300)
    shut.stop()
    probe.go = False
    if os.environ.get("B480_KEEP"):
        w._stalls.flush()
        os.makedirs(os.environ["B480_KEEP"], exist_ok=True)
        shutil.copy(os.path.join(T, "stalls.txt"), os.path.join(os.environ["B480_KEEP"], "stalls.txt"))
    w.project.dirty = False
    w.close()


if __name__ == "__main__":
    main()
