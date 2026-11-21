r"""python tools/test_b480_path_stalls.py

B480 / A7e (17.11.2026): on the biggest world the window must not stop for more than 0.5 s on
Install the modules -> Install a world zip (look inside it, install it) -> My world > Make it
editable -> BUILD AND INSTALL. The exe test of beta4o (GigaPack, FL26_STALLS) still had stops on
it, each put down to its line by the stall recorder:

  look inside the zip   0.81 s  installer.work_dir -> zipfile reading the zip's 160,000 names,
                                on the window's thread (install.py, look)
  end of the install    0.93 s  the five content-server pages behind the one on screen reading
                                their maps again on every sider.ini save (content.py, ServerPage),
                                the Install page's list reading installed.json (install.py, refresh)
  Make it editable      3.1 s, 2.8 s, 7.2 s  the plan and the recipes freed in one call of C
                                (worlds.make_editable's plan, filecache.forget_under, the job's two
                                recipes, project.adopt's `self.recipe = new` on the window's thread)
  end of Build          1.30 s  ini_changed -> the content-server pages again

Here: the whole window in this process (QT_QPA_PLATFORM=offscreen), a fake game folder and
APPDATA in a temp folder, the window's own stall recorder (app.record_stalls, as FL26_STALLS in
the exe) and a world of the GigaPack's shape made up: 317 leagues of 20 clubs with squads in the
plan, the GigaPack's kit map (4,500 lines, notes\test-gp2\b4o\a\map_before.txt, when it is there),
an install record of 160,000 files and a recipe of 220,000 changed players (B480_PLAYERS). For
looking inside a zip the biggest GigaPack zip on this PC (E:\FL\gigapack, B480_ZIP), only its list
of names is read: the unpack is left out. Big objects carry a marker that notes the thread that
frees it: none of them may go on the window's thread. A real message box open for 1.5 s is no
stop (the recorder's clock ticks in the box's own loop). No game.

Found here as well (17.11.), with 220,000 players: a worker thread that never stops makes every call
Qt makes back into Python on the window's thread wait one switch interval for the lock -- a Select
Team combo of Leagues 154 ms instead of 0.8 ms next to one busy bigjson reader, 0.6-0.9 s stops at the
end of the install and after Make it editable. bigjson's readers (bigjson.GENTLE, as app.main sets
it) and letgo's thread rest between their steps now. And the pages behind the one on screen fill one
per turn of the window (ui._OWED): three timers of 0 s posted together ran in the same turn.

Round 2 (17.11., the exe test of beta4p still stopped 0.5-4 s, and 9 s on Leagues after it): the
players have the GigaPack's shape and fields (B480_FIELDS, 100), as many as the free memory takes
(B480_PLAYERS, up to 220,000); the real module pack is installed by the real install_modules and
compared by the real checks; a league logo file each; a kit server of B480_KITS folders, walked by
content's worker; the Build writes the plan anew. And three more steps of the exe test (c): Leagues
opened with the plan not read yet (as after a start), Leagues > Edit, and Edit > OK.

What this does not do: page the objects out. Most of the exe's seconds were Windows reading
freed memory back from the page file; here everything is in RAM, so the code before measures
less than the exe did. The markers catch the freeing on the window's thread anyway.
"""
import glob, json, os, shutil, sys, tempfile, threading, time, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.pop("FL26_DIR", None)
REAL_APPDATA = os.environ.get("APPDATA", "")
if __name__ != "__mp_main__":          # (not again in My world's plan process, apart.numbers)
    T = tempfile.mkdtemp(prefix="b480path-")
    os.environ["APPDATA"] = os.path.join(T, "appdata")
    os.environ["FL26_SAVE_ROOT"] = os.path.join(T, "konami")

from test_world_manage import make_game, put

LIMIT = 0.5
PLAYERS = int(os.environ.get("B480_PLAYERS", "220000"))
LEAGUES, CLUBS, SQUAD = 317, 20, 25
WORLD = "_FL26Old"                     # the world the zip brings (make_game has it, off)
N = 0
FAILED = []
FREED = []                             # (marker name, thread) as markers go
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# Round 2: what the exe test's stops were made of, counted on the window's thread, whatever the
# disk and the size here make of the time: the module files read (checks._same_file, modules.links),
# the world's plan read with nothing kept of it, and a page filled behind another one.
ON_WINDOW = []


def watch_window(PB):
    import threading
    from modstudio import filecache as FCw
    from modstudio.pages import leagues as PLw, trophies as PTw
    import traceback
    main = threading.main_thread()
    real_by, real_json = FCw.by_files, FCw.json_file

    def where():
        st = [f for f in traceback.extract_stack()[:-3] if "test_b480" not in f.filename]
        return " <- ".join("%s:%d %s" % (os.path.basename(f.filename), f.lineno, f.name) for f in st[::-1][:4])

    def by_files(name, paths, make):
        def made():
            if threading.current_thread() is main and name in ("same_file", "module-links", "check-dlls", "dll-names"):
                ON_WINDOW.append(("read (%s)" % name, where()))
            return make()
        return real_by(name, paths, made)

    def json_file(path):
        if threading.current_thread() is main and str(path).endswith("leaguebuilder-plan.json"):
            got = FCw._KEPT.get(("json", path))
            if got is None or got[0] != FCw.stamp(path):
                ON_WINDOW.append(("the plan read", where()))
        return real_json(path)
    FCw.by_files, FCw.json_file = by_files, json_file
    for cls, name in ((PB.NewLeagues, "refresh"), (PLw.Leagues, "fill"), (PTw.Trophies, "refresh")):
        def wrap(self, *a, _real=getattr(cls, name), _n="%s.%s" % (cls.__name__, name), **k):
            if threading.current_thread() is main and not self.isVisible():
                ON_WINDOW.append(("filled behind another page", _n + " <- " + where()))
            return _real(self, *a, **k)
        setattr(cls, name, wrap)


def nothing_on_window(what):
    seen = sorted(set(ON_WINDOW))
    ok("... %s: nothing of it on the window's thread %s" % (what, seen[:6]), not seen)
    del ON_WINDOW[:]


def ok(name, cond):
    global N
    N += 1
    print("%s %d - %s" % ("ok" if cond else "FAIL", N, name), flush=True)
    if not cond:
        FAILED.append(name)


class Marker(dict):
    """a dict that says which thread freed it (put inside a big object: it goes when that goes)"""

    def __del__(self):
        FREED.append((self.get("what", "?"), threading.current_thread().name))


def biggest_zip():
    if os.environ.get("B480_ZIP"):
        return os.environ["B480_ZIP"]
    zips = sorted(glob.glob(r"E:\FL\gigapack\_FL26Megapack-*.zip"), key=lambda p: os.path.getsize(p))
    return zips[-1] if zips else None


def made_zip():
    """a zip with 160,000 names (the GigaPack's count) when there is no GigaPack zip here"""
    p = os.path.join(T, "big.zip")
    with zipfile.ZipFile(p, "w", zipfile.ZIP_STORED) as z:
        for i in range(160000):
            z.writestr("SiderAddons/livecpk/%s/common/x/%06d.bin" % (WORLD, i), b"")
    return p


def big_plan(world):
    leagues = []
    for i in range(LEAGUES):
        teams = [200000 + i * CLUBS + k for k in range(CLUBS)]
        leagues.append({
            "name": "%s League %03d" % (world, i), "rid": 400 + i, "country": 50 + i % 90, "clubs": CLUBS,
            "teams": teams, "club_names": ["Club %d-%d" % (i, k) for k in range(CLUBS)],
            "kit_folders": [os.path.join(T, "nowhere", str(t)) for t in teams],
            "scoreboard": os.path.join(T, "nowhere", "board%d" % i),
            "squads": [[{"id": 3000000 + (i * CLUBS + k) * SQUAD + p, "name": "Player %d-%d-%d" % (i, k, p),
                         "ovr": 60 + p % 20, "pos": p % 13, "age": 18 + p % 17} for p in range(SQUAD)]
                       for k in range(CLUBS)]})
    return {"world": world, "leagues": leagues, "others": []}


def free_ram():
    import ctypes

    class MS(ctypes.Structure):
        _fields_ = [("len", ctypes.c_ulong), ("load", ctypes.c_ulong), ("total", ctypes.c_ulonglong),
                    ("avail", ctypes.c_ulonglong), ("tp", ctypes.c_ulonglong), ("ap", ctypes.c_ulonglong),
                    ("tv", ctypes.c_ulonglong), ("av", ctypes.c_ulonglong), ("ext", ctypes.c_ulonglong)]
    m = MS()
    m.len = ctypes.sizeof(MS)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.avail


# 17.11. (round 2, the exe test of beta4p): the GigaPack's recipe has 220,000 players of ~100 fields
# each (_FL26Megapack.json, 260 MB): 22 million objects for letgo's thread and the collector, where
# a player of two fields here was 0.7 million -- the stall test said 0.00 s and the exe 4 s. Its
# players have the real shape now ("League/club": {"edits": {slot: {field: "value"}}}), B480_FIELDS
# fields each; B480_PLAYERS of them, by default as many as the free memory takes for the six copies
# Make it editable holds at once (220,000 at most)
FIELDS = int(os.environ.get("B480_FIELDS", "100"))
_FIELD_NAMES = ["Field %02d" % f for f in range(FIELDS)]
if "B480_PLAYERS" not in os.environ and __name__ != "__mp_main__":
    PLAYERS = max(20000, min(PLAYERS, int(free_ram() * 0.55 / (FIELDS * 95 * 6))))


def players_of(world):
    out, n, k = {}, 0, 0
    names = ["%s League %03d" % (world, i) for i in range(LEAGUES)]
    while n < PLAYERS:
        club = "%s/%d" % (names[k // CLUBS], k % CLUBS) if k < LEAGUES * CLUBS else "%s Extra/%d" % (world, k)
        slots = {}
        for s in range(min(SQUAD, PLAYERS - n)):
            v = {f: str((n + j) % 99) for j, f in enumerate(_FIELD_NAMES)}
            v["name"] = "Player %d" % n
            slots[str(s)] = v
            n += 1
        out[club] = {"edits": slots}
        k += 1
    return out


def recipe_of(pl, base):
    """leaguebuilder.recipe_from_plan's stand-in (the fake game has no tables): the plan's leagues,
    and the GigaPack's bulk, its players' changes, with a marker in it"""
    leagues = [{"name": L["name"], "country": "Croatia", "clubs": L["clubs"], "legs": 2, "exchange": 3,
                "club_names": list(L["club_names"]), "logo": os.path.join(T, "logos", "%03d.png" % i)}
               for i, L in enumerate(pl.get("leagues") or [])]
    players = players_of(pl.get("world"))
    players["zz"] = Marker(what="recipe of %s" % pl.get("world"))
    return {"world": pl.get("world"), "leagues": leagues, "players": players, "edits": {}}


def main():
    for d in glob.glob(os.path.join(os.path.dirname(T), "b480path-*")):
        if d != T and not any(fs for _r, _d, fs in os.walk(d)):
            shutil.rmtree(d, ignore_errors=True)
    try:
        run()
    finally:
        shutil.rmtree(T, ignore_errors=True)
    print("all passed" if not FAILED else "%d failed" % len(FAILED))
    sys.exit(1 if FAILED else 0)


def run():
    import faulthandler
    faulthandler.dump_traceback_later(int(os.environ.get("B480_DUMP", "900")), exit=True)  # a box nobody closes: where
    from PySide6.QtCore import QEventLoop, QTimer
    from PySide6.QtWidgets import QApplication, QMessageBox
    qa = QApplication.instance() or QApplication([])
    sys.setswitchinterval(0.001)                      # as modstudio.app.main
    from modstudio import gentlejson
    gentlejson.install()                              # as modstudio.app.main: big texts read in pieces
    import bigjson
    bigjson.GENTLE = os.environ.get("B480_GENTLE", "1") == "1"   # as modstudio.app.main
    from modstudio import app as A, saves as SV, apart, installer as I, letgo, game as G, theme
    from modstudio.pages import builder as PB, myworld as M
    import leaguebuilder as B
    SV.game_running = lambda: False
    G.Game.running = staticmethod(lambda: (False, False))   # the real game may run on this PC
    watch_window(PB)                                  # (before the window: its slots bind the methods)
    theme.apply(qa)
    game = make_game(T)
    sd = game.sider_dir
    ms = os.path.join(os.environ["APPDATA"], "FL26ModStudio")
    os.makedirs(os.path.join(ms, "tables"))
    # the game's tables, unpacked on this PC by Mod Studio (Settings > Unpack the game's tables): a
    # copy, as the pages and the checks read them
    for cand in (os.environ.get("B480_TABLES"),
                 os.path.join(REAL_APPDATA, "FL26ModStudio", "tables"),
                 os.path.join(REAL_APPDATA, "FL26ModStudio", "tables27", "common", "etc", "pesdb")):
        if cand and os.path.isfile(os.path.join(cand, "Country.bin")):
            for n in os.listdir(cand):
                if n.endswith(".bin"):
                    shutil.copy2(os.path.join(cand, n), os.path.join(ms, "tables", n))
            print("# the game's tables: a copy of %s" % cand, flush=True)
            break
    else:
        sys.exit("no unpacked game tables on this PC (Country.bin): set B480_TABLES")
    with open(os.path.join(ms, "settings.json"), "w", encoding="utf-8") as f:
        json.dump({"game": game.folder, "tables": os.path.join(ms, "tables"), "check_updates": False}, f)

    # ---- the GigaPack's shape on the fake game ----
    src_map = os.path.join(HERE, "..", "notes", "test-gp2", "b4o", "a", "map_before.txt")
    if not os.path.isfile(src_map):
        src_map = r"D:\dev\fl26\notes\test-gp2\b4o\a\map_before.txt"
    kit_map = os.path.join(sd, "content", "kit-server", "map.txt")
    if os.path.isfile(src_map):
        with open(src_map, encoding="utf-8", errors="replace") as f:
            lines = f.read()
    else:
        lines = "".join('%d, "%s\\League %d\\Club %d"\n' % (200000 + i, WORLD, i // 20, i) for i in range(4500))
    with open(kit_map, "a", encoding="utf-8") as f:
        f.write(lines)
    n_kits = lines.count("\n")
    with open(os.path.join(sd, "livecpk", WORLD, "leaguebuilder-plan.json"), "w", encoding="utf-8") as f:
        json.dump(big_plan(WORLD), f, indent=1)
    plan_mb = os.path.getsize(os.path.join(sd, "livecpk", WORLD, "leaguebuilder-plan.json")) / 2**20
    put(os.path.join(sd, "livecpk", WORLD, ".modstudio"), "GigaPack shape (test)")
    rows = I.records(sd)
    for r in rows:
        if r.get("world") == WORLD:
            r["created"] += [os.path.join("livecpk", WORLD, "common", "x", "%06d.bin" % i) for i in range(160000)]
    I._save(sd, rows)
    print("# plan %.0f MB, kit map %d lines, installed.json %.0f MB, recipe %d players"
          % (plan_mb, n_kits, os.path.getsize(I.db_path(sd)) / 2**20, PLAYERS), flush=True)

    # round 2: a league logo file each (the pages ask the disk about them), a kit server of
    # B480_KITS club folders (content's library walk runs in a worker through the end of Make it
    # editable, as in the exe), and the real module pack installed by the real install_modules (the
    # header's and Home's checks read and compare its files)
    from PIL import Image
    os.makedirs(os.path.join(T, "logos"))
    for i in range(LEAGUES):
        Image.new("RGBA", (64, 64), (i % 256, 80, 160, 255)).save(os.path.join(T, "logos", "%03d.png" % i))
    kits = int(os.environ.get("B480_KITS", "6000"))
    kit_root = os.path.join(sd, "content", "kit-server", "GDB", "uniform", "team")
    for i in range(kits):
        d = os.path.join(kit_root, WORLD, "League %d" % (i // 20), "Club %d" % i)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "config.txt"), "w") as f:
            f.write("[h1]\n")
    pack = None
    for cand in (os.environ.get("B480_PACK"), os.path.join(HERE, "..", "out", "lbpack"),
                 r"D:\dev\fl26\wt\beta2\out\lbpack",
                 r"E:\FL\FL27\modstudio\beta4p\FL26 Mod Studio\pack"):
        if cand and os.path.isfile(os.path.join(cand, "modules.txt")):
            pack = os.path.join(T, "pack")
            shutil.copytree(cand, pack)
            break
    real_install = B.install_modules
    if pack:
        B.pack_dir = lambda: pack
        print("# the module pack: a copy of %s (%d files)" % (cand, len(os.listdir(os.path.join(pack, "modules")))),
              flush=True)
    else:
        B.install_modules = lambda *a, **k: None      # no module pack on this PC
        print("# no module pack here: Install the modules left out (set B480_PACK)", flush=True)
    print("# %d players of %d fields, %d kit folders, %d league logos" % (PLAYERS, FIELDS, kits, LEAGUES), flush=True)

    B.recipe_from_plan = recipe_of
    B.tables_stale = lambda *a, **k: None
    B.describe = lambda *a, **k: "(the plan)"
    B.pin_newlife = lambda r, base, pl=None: False
    B.game_clubs = lambda *a, **k: {}
    from modstudio import checks as CK
    CK.short_squads = lambda *a, **k: []             # (it reads the world's Player.bin)

    w = A.Main()
    w.show()
    w.project.base = os.path.join(ms, "tables")
    A.record_stalls(w, os.path.join(T, "stalls.txt"))

    # message boxes: real ones, closed by a click 0.3 s after they open (the person reading them)
    boxes = []

    def open_box():
        return next((x for x in QApplication.topLevelWidgets() if isinstance(x, QMessageBox) and x.isVisible()), None)

    def closer():
        m = open_box()
        if m is not None:
            # (a Qt property: the Python wrapper of a box made by QMessageBox.information is a new
            # one each time it is looked up)
            if not m.property("b480_seen"):
                m.setProperty("b480_seen", time.perf_counter())
                boxes.append(m.text())
            elif time.perf_counter() - m.property("b480_seen") > 0.3:
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

    def measured(what, start, until, secs=180, after=1.0):
        """start() on a turn of the window's own, run until until(), then `after` s more; the longest
        stop the recorder saw, and where"""
        spin(lambda: False, 0.5)
        del w._stall_gaps[:]
        t0 = time.perf_counter()
        QTimer.singleShot(0, start)
        got = spin(until, secs)
        spin(lambda: False, after)
        spin(lambda: False, 0.4)                     # the recorder writes a stop when it is over
        gaps = [g for g in w._stall_gaps if g[0] >= t0 - 0.2]
        worst = max(gaps, key=lambda g: g[1]) if gaps else (0, 0.0, [])
        print("#   %s: %.1f s, longest stop %.2f s%s" % (what, time.perf_counter() - t0, worst[1],
              (" at " + "; ".join("%dx %s" % (n, s) for s, n in worst[2][:2])) if worst[2] else ""), flush=True)
        return got, worst[1]

    # 0. the recorder itself: a message box open 1.5 s with the window idle is no stop
    QTimer.singleShot(0, lambda: QMessageBox.information(w, "B480", "an idle box"))
    t0 = time.perf_counter()
    held = {}

    def keep_open():
        m = open_box()
        if m is not None and m.text() == "an idle box":
            m.setProperty("b480_seen", time.perf_counter() + 1.2)        # the closer clicks it after 1.5 s
            held["box"] = True
    QTimer.singleShot(30, keep_open)
    spin(lambda: held and open_box() is None, 10)
    spin(lambda: False, 0.5)
    gaps = [g[1] for g in w._stall_gaps if g[0] >= t0]
    ok("an idle message box open %.1f s is no stop for the recorder (stops %s)"
       % (time.perf_counter() - t0 - 0.5, ["%.2f" % g for g in gaps]), held and not [g for g in gaps if g >= 0.3])
    # ... and a real stop under it still is one
    del w._stall_gaps[:]
    t0 = time.perf_counter()

    def busy():
        end = time.perf_counter() + 0.9
        while time.perf_counter() < end:
            pass
    QTimer.singleShot(0, busy)
    spin(lambda: False, 1.2)
    gaps = [g[1] for g in w._stall_gaps if g[0] >= t0 - 0.2]
    ok("0.9 s of work on the window's thread is a stop of 0.9 s for it (%s)" % ["%.2f" % g for g in gaps],
       any(0.8 <= g <= 1.2 for g in gaps))

    # 1. Install the modules (Home's Install now)
    from modstudio import modfix
    home = w.page("Overview")
    w.open_page("Overview")
    res = {}
    del ON_WINDOW[:]
    got, worst = measured("Install the modules", lambda: res.setdefault("r", modfix.install_now(home)),
                          lambda: "r" in res)
    from modstudio import checks as CK2
    st = CK2.modules_state(game)
    ok("Install the modules: done (%s), the window's longest stop %.2f s (limit %.1f); the header: %s"
       % (res.get("r"), worst, LIMIT, w.stats["modules"].text()),
       got and worst < LIMIT and (not pack or (CK2.modules_ok(st) and "ON" in w.stats["modules"].text())))
    nothing_on_window("Install the modules")
    if pack:
        # a module changed behind Mod Studio's back is seen at the next look (the cache's key is the
        # folder's listing: size and time of each file)
        f = sorted(n for n in B.shipped_files(os.path.join(pack, "modules")) if n.endswith(".lua")
                   and os.path.isfile(os.path.join(game.modules_dir, n)))[0]
        p = os.path.join(game.modules_dir, f)
        with open(p, "ab") as fh:
            fh.write(b"\n-- changed\n")
        st2 = CK2.modules_state(game)
        ok("a module changed behind its back (%s) is seen at once: changed %s" % (f, st2 and st2["changed"]),
           bool(st2) and f in st2["changed"])
        shutil.copy2(B.shipped_source(os.path.join(pack, "modules"), f, game.folder), p)
        ok("... and put back, the modules are right again", CK2.modules_ok(CK2.modules_state(game)))

    # 2a. Import your world: look inside the biggest zip (its list of names; the unpack left out)
    ip = w.page("Install")
    w.open_page("Install")
    zp = biggest_zip() or made_zip()
    t1 = time.perf_counter()
    I.unpacked_size(zp)
    on_gui = time.perf_counter() - t1
    print("# zip %s (%.1f GB): reading its list of names took %.2f s (on the window's thread before)"
          % (zp, os.path.getsize(zp) / 2**30, on_gui), flush=True)
    seen = {}
    real_unpack, real_detect, real_looked = I.unpack, I.detect, ip.looked

    def unpack(src, work, progress=None):
        seen["work"] = work
        return work
    I.unpack, I.detect = unpack, lambda top, label: []
    ip.looked = lambda parts: (seen.setdefault("looked", parts), ip.app.busy(False))
    got, worst = measured("look inside the zip", lambda: ip.look(zp), lambda: "looked" in seen, after=0.5)
    I.unpack, I.detect, ip.looked = real_unpack, real_detect, real_looked
    ok("look inside %s: it went on to the unpack in %s, the window's longest stop %.2f s (limit %.1f)"
       % (os.path.basename(zp), seen.get("work"), worst, LIMIT),
       got and bool(seen.get("work")) and ip.work == seen.get("work") and worst < LIMIT)
    ip.cleanup()

    # 2b. the end of the install: sider.ini saved, the world switched on, read, final check, box
    checked = []
    real_check = ip.final_check

    def final(world):
        real_check(world)
        checked.append(world)
    ip.final_check = final

    ini = w.ini()
    ini.save(reason="installed %s" % WORLD)           # what install()'s worker does last (round 2)
    running = G.Game.running()

    def installed():
        try:
            w.save_ini(ini, "installed %s" % WORLD, saved=True, running=running)   # ... and its done() first
        except TypeError:                                                         # (the code before round 2)
            w.save_ini(ini, "installed %s" % WORLD)
        w.bus.content_changed.emit()
        ip.world_on({"world": WORLD})
    del ON_WINDOW[:]
    got, worst = measured("end of the install", installed, lambda: bool(checked), after=1.5)
    ip.final_check = real_check
    ok("end of the install: %s on, its recipe open (%s), the window's longest stop %.2f s (limit %.1f)"
       % (WORLD, w.project.recipe.get("world"), worst, LIMIT),
       got and w.project.recipe.get("world") == WORLD and worst < LIMIT)
    nothing_on_window("end of the install")
    ok("... the Install page's list was read again (%d rows)" % ip.done.topLevelItemCount(),
       ip.done.topLevelItemCount() == len(I.records(sd)))

    # 3. My world > Make it editable
    mw = w.my_world
    w.open_page("Leagues")
    M.ask = lambda *a, **k: True
    M.can_write = lambda *a, **k: True
    ok("before: %s is a ready world, its recipe open" % WORLD,
       I.ready_world(game, WORLD) and w.project.recipe.get("world") == WORLD)
    n_boxes = len(boxes)
    del FREED[:]
    del ON_WINDOW[:]
    got, worst = measured("Make it editable", mw.make_editable,
                          lambda: any("can be changed now" in t for t in boxes[n_boxes:]), after=2.0)
    ok("Make it editable: done, the window's longest stop %.2f s (limit %.1f)" % (worst, LIMIT),
       got and worst < LIMIT and not I.ready_world(game, WORLD))
    nothing_on_window("Make it editable")
    letgo.wait(120)
    import gc
    gc.collect()
    on_main = [x for x in FREED if x[1] == "MainThread"]
    ok("no big object was freed on the window's thread (%d freed: %s)"
       % (len(FREED), sorted(set(FREED))), FREED and not on_main)

    # 4. BUILD AND INSTALL (the build itself left out, as in test_b480_build_stalls)
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
        # what a Build leaves: the world's plan written anew (round 2: opened after Build, Leagues
        # read the GigaPack's 286 MB plan on the window's thread, 9 s in the exe test of beta4p)
        path = os.path.join(sd, "livecpk", WORLD, "leaguebuilder-plan.json")
        with open(path + ".tmp", "w", encoding="utf-8") as f:
            json.dump(big_plan(WORLD), f, indent=1)
        os.replace(path + ".tmp", path)
        after.setdefault("build", time.perf_counter())
    apart.build = build
    w.open_page("Build")
    del ON_WINDOW[:]
    got, worst = measured("Build and install", b.build_all, lambda: "at" in after, after=1.5)
    ok("Build and install: to the box after it, the window's longest stop %.2f s (limit %.1f)" % (worst, LIMIT),
       got and "build" in after and worst < LIMIT)
    nothing_on_window("Build and install")

    # 5. Leagues opened the first time after a start (the plan the Build wrote not read yet: what
    # Build's worker read of it is dropped here, as a new start of Mod Studio has nothing)
    from modstudio import filecache as FC
    gone = [FC._KEPT.pop(k) for k in list(FC._KEPT) if k[0] == "json" and str(k[1]).endswith("leaguebuilder-plan.json")]
    letgo.drop(gone)
    del gone
    lp = w.page("Leagues")
    del ON_WINDOW[:]
    got, worst = measured("Leagues opened after Build", lambda: w.open_page("Leagues"),
                          lambda: lp.tree.topLevelItemCount() > 0, after=1.0)
    ok("Leagues opened after Build: %d rows, the window's longest stop %.2f s (limit %.1f)"
       % (lp.tree.topLevelItemCount(), worst, LIMIT), got and worst < LIMIT)
    nothing_on_window("Leagues opened after Build")
    plan_path = os.path.join(sd, "livecpk", WORLD, "leaguebuilder-plan.json")
    kept = lambda: FC._KEPT.get(("json", plan_path), (None,))[0] == FC.stamp(plan_path)
    spin(lambda: kept() and "Select Team" in lp.count.text(), 120)
    ok("... the plan read by a worker meanwhile, and the page filled with it: %r" % lp.count.text()[-60:],
       kept() and "Select Team" in lp.count.text())

    # 6. Leagues > one of ours > Edit (New leagues' button on it; the box closed without a change)
    seen_edit = {}

    class NoEdit:
        said = False

        change = False

        def __init__(self, page, project, L=None, **k):
            seen_edit["league"] = (L or {}).get("name")
            self.league = json.loads(json.dumps(L))
            if self.change:
                self.league["b480_probe"] = self.league.get("b480_probe", 0) + 1

        def finish(self):
            return self.said
    real_dialog = PB.LeagueDialog
    PB.LeagueDialog = NoEdit
    key = "o%s League %03d" % (WORLD, 5)
    lp.show_key(key)
    del ON_WINDOW[:]
    got, worst = measured("Leagues > Edit, Cancel", lambda: lp.on_ours("edit"), lambda: "league" in seen_edit, after=1.0)
    ok("Leagues > Edit opens the league picked there (%s), the window's longest stop %.2f s (limit %.1f)"
       % (seen_edit.get("league"), worst, LIMIT), got and seen_edit.get("league") == key[1:] and worst < LIMIT)
    nothing_on_window("Leagues > Edit")
    # ... OK in it with nothing changed: the recipe as it was (B480 round 3, beta4r: the dialog's sorted
    # European places and the touch() after it wrote the GigaPack's recipe and took 6.2-6.6 s)
    NoEdit.said = True
    seen_edit.clear()
    gen = getattr(w.project, "_gen", 0)
    del ON_WINDOW[:]
    got, worst = measured("Leagues > Edit, OK as it was", lambda: lp.on_ours("edit"), lambda: "league" in seen_edit,
                          after=1.0)
    ok("Leagues > Edit > OK with nothing changed: the recipe not touched (%s), the window's longest stop "
       "%.2f s (limit %.1f)" % (getattr(w.project, "_gen", 0) == gen, worst, LIMIT),
       got and getattr(w.project, "_gen", 0) == gen and worst < LIMIT)
    # ... and OK with a change: the recipe touched (Undo's look at what changed, the pages on screen again)
    NoEdit.change = True
    seen_edit.clear()
    gen = getattr(w.project, "_gen", 0)
    del ON_WINDOW[:]
    got, worst = measured("Leagues > Edit, OK", lambda: lp.on_ours("edit"), lambda: "league" in seen_edit, after=1.5)
    PB.LeagueDialog = real_dialog
    ok("Leagues > Edit > OK: the recipe touched (%s), the window's longest stop %.2f s (limit %.1f)"
       % (getattr(w.project, "_gen", 0) != gen, worst, LIMIT), got and getattr(w.project, "_gen", 0) != gen and worst < LIMIT)
    nothing_on_window("Leagues > Edit > OK")
    letgo.wait(120)
    shut.stop()
    if os.environ.get("B480_STALLS_COPY"):           # the recorder's own lines, for a closer look
        w._stalls.flush()
        shutil.copy(os.path.join(T, "stalls.txt"), os.environ["B480_STALLS_COPY"])
    w.project.dirty = False
    w.close()


if __name__ == "__main__":
    main()
