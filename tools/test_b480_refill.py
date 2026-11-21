r"""python tools/test_b480_refill.py

B480 (16.11.2026): after Make it editable, and at the end of a world zip install, the GigaPack's
world came in (Project.adopt) with every page behind the one on screen filling in that same turn
of the window -- New leagues, Leagues, Clubs, New clubs: 1.0-1.1 s of a stopped window in the
stall probe (offscreen, a copy of the GigaPack), each page 0.2-0.4 s of it. A page behind another
one now fills when it is opened (ui.Page.on_change; first, 16.11., on a later turn of its own); the
page on screen at once, as before, and New leagues' world name at once too (Build reads it there).

Here: the whole window in this process (QT_QPA_PLATFORM=offscreen), a fake game folder and
APPDATA in a temp folder, and a world of the GigaPack's shape: 317 leagues with a logo each, 20
NewLife clubs with 22 changed players each (140,000 player edits), the snapshot and the small
pictures made ahead as the workers do. Checks: the window's longest turn from adopt() to 1.5 s
after it is under 0.5 s; the pages behind are filled with the new world after it; New leagues has
its world name in the same turn; the page on screen fills in the same turn. No game.

What it does NOT do: fail on the code before B480. These made-up pages fill in 0.2-0.3 s all
together (the GigaPack's took 1.0-1.1 s: its crests, squads and the game's tables, which a fake
game folder does not have); it guards that a page filled later is still filled right.
"""
import json, os, shutil, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.pop("FL26_DIR", None)
T = tempfile.mkdtemp(prefix="b480refill-")
os.environ["APPDATA"] = os.path.join(T, "appdata")
os.environ["FL26_SAVE_ROOT"] = os.path.join(T, "konami")

from test_world_manage import make_game

LIMIT = 0.5
LEAGUES, CLUBS, CHANGED = 317, 20, 22
N = 0
FAILED = []
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def ok(name, cond):
    global N
    N += 1
    print("%s %d - %s" % ("ok" if cond else "FAIL", N, name))
    if not cond:
        FAILED.append(name)


def logo(name, i):
    """a league logo of the GigaPack's kind (512 px PNG), a new file for every world"""
    from PIL import Image
    d = os.path.join(T, "logos", name)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "%03d.png" % i)
    Image.new("RGBA", (512, 512), (i % 255, 40, 200 - i % 150, 255)).save(p)
    return p


def world(name):
    leagues, players = [], {}
    for i in range(LEAGUES):
        L = {"name": "%s League %03d" % (name, i), "country": "Country %d" % (i % 90), "clubs": CLUBS,
             "newlife": True, "above": None if i % 3 == 0 else "%s League %03d" % (name, i - 1),
             "logo": logo(name, i)}
        leagues.append(L)
        for k in range(CLUBS):
            players["%s/%d" % (L["name"], k)] = {"edits": {str(10 ** 6 + (i * CLUBS + k) * 40 + p): {"ovr": 70 + p % 9}
                                                           for p in range(CHANGED)}}
    return {"world": name, "leagues": leagues, "players": players, "edits": {}}


def main():
    # the window's watchers keep this run's temp folder until the process ends: an earlier
    # run's, empty by now, goes here
    import glob
    for d in glob.glob(os.path.join(os.path.dirname(T), "b480refill-*")):
        if d != T and not any(fs for _r, _d, fs in os.walk(d)):
            shutil.rmtree(d, ignore_errors=True)
    try:
        run()
    finally:
        shutil.rmtree(T, ignore_errors=True)
    print("all passed" if not FAILED else "%d failed" % len(FAILED))
    sys.exit(1 if FAILED else 0)


def run():
    from PySide6.QtCore import QEventLoop, QTimer
    from PySide6.QtWidgets import QApplication
    qa = QApplication.instance() or QApplication([])
    sys.setswitchinterval(0.001)                      # as modstudio.app.main
    from modstudio import app as A, saves as SV
    SV.game_running = lambda: False
    game = make_game(T)
    ms = os.path.join(os.environ["APPDATA"], "FL26ModStudio")
    os.makedirs(os.path.join(ms, "tables"))
    with open(os.path.join(ms, "settings.json"), "w", encoding="utf-8") as f:
        json.dump({"game": game.folder, "tables": os.path.join(ms, "tables"), "check_updates": False}, f)
    w = A.Main()
    w.show()
    nl = w.page("NewLeagues")

    # the window's stop: how long one turn of the event loop took (processEvents with a 5 ms cap
    # returns after the event it is in; a 10 ms QTimer is no measure here: on Windows a timer
    # waits while 0 ms timers -- in_steps, on_change -- keep coming)
    beat = {"worst": 0.0}

    def spin(secs):
        end = time.perf_counter() + secs
        while time.perf_counter() < end:
            t0 = time.perf_counter()
            qa.processEvents(QEventLoop.AllEvents, 5)
            beat["worst"] = max(beat["worst"], time.perf_counter() - t0 - 0.005)
            time.sleep(0.002)

    def adopt(rec, page):
        w.open_page(page)
        spin(0.5)
        said = {}
        snap = w.project._split(rec)        # made by a worker in Make it editable and the zip install
        from modstudio.pages import builder as PB
        PB.warm([L["logo"] for L in rec["leagues"]], (20, 28))   # as the warm-pictures thread does

        def go():
            w.project.adopt(rec, os.path.join(T, rec["world"] + ".json"), copy=True, snap=snap)
            said["world now"] = nl.world.text()
            said["leagues now"] = nl.tree.topLevelItemCount()
        beat["worst"] = 0.0
        QTimer.singleShot(0, go)
        spin(1.5)
        return beat["worst"], said

    # warm: the first adopt of a session makes the pages' widgets; the one measured is the second
    adopt(world("_FL26Warm"), "Overview")
    worst, said = adopt(world("_FL26Giga"), "Overview")
    ok("a world of %d leagues opened behind Home: the window's longest stop %.2f s (limit %.1f)"
       % (LEAGUES, worst, LIMIT), worst < LIMIT)
    ok("New leagues has the new world's name in the same turn: %r" % said.get("world now"),
       said.get("world now") == "_FL26Giga")
    # (round 2, 17.11.: a page behind another one fills when it is opened, not unseen)
    ok("... not filled behind Home (%d rows), and its %d leagues when it is opened"
       % (nl.tree.topLevelItemCount(), LEAGUES), nl.tree.topLevelItemCount() != LEAGUES
       and (w.open_page("NewLeagues") or True) and nl.tree.topLevelItemCount() == LEAGUES)
    from PySide6.QtWidgets import QTreeWidgetItemIterator
    lg, texts = w.page("Leagues"), []
    w.open_page("Leagues")
    spin(0.5)
    it = QTreeWidgetItemIterator(lg.tree)
    while it.value():
        texts.append(it.value().text(0))
        it += 1
    ok("Leagues, opened, is filled with the new world (%d rows)" % len(texts),
       any("_FL26Giga League 000" in t for t in texts) and not any("_FL26Warm" in t for t in texts))

    # the page on screen fills in the same turn, as before
    worst, said = adopt(world("_FL26Shown"), "NewLeagues")
    ok("New leagues on screen: filled in the same turn (%r leagues)" % said.get("leagues now"),
       said.get("leagues now") == LEAGUES and said.get("world now") == "_FL26Shown")
    print("# New leagues on screen: the window's longest stop %.2f s (that page alone, not checked)" % worst)
    w.project.dirty = False
    w.close()
    w.deleteLater()                                   # (its file watchers keep the temp folders open)
    spin(0.3)


if __name__ == "__main__":
    main()
