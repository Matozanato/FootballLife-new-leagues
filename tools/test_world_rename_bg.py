r"""python tools/test_world_rename_bg.py

B66 / B75 (0.2.4, exe test 16.10.): My world > Rename of a big world (1146 clubs, a 128 MB
leaguebuilder-plan.json, a 126 MB recipe) froze the whole window for 13 minutes, and after a
rename the cards changed order, so the same Rename button opened another world.
  - worlds.rename edits the big json files as bytes: the same bytes as line by line, in seconds;
  - the recipe copy (recipes\<world>.json) gets its "world" line changed, the rest byte for byte,
    the same file json.load + json.dump gave;
  - Rename world runs in the background: rename_world returns at once, the window keeps answering
    (a timer keeps ticking), its buttons are off meanwhile, done(new) comes when it is over;
  - the renamed world's folder keeps its time, so My world keeps the cards in the same order.

Fake game folders in a temp folder, QT_QPA_PLATFORM=offscreen. No game.
"""
import json, os, re, shutil, sys, tempfile, time, types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.pop("FL26_DIR", None)

from modstudio import worlds as WL, theme
from test_world_manage import make_game, put, FakeProject, wait_rename, QUIET

N = 0
BIG = 1600000           # clubs in the fake plan: ~2.5 million lines, ~40 MB


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def big_plan(world):
    """a plan of the shape Build writes (indent=1), millions of lines"""
    return json.dumps({"world": world, "leagues": [
        {"name": "League %d" % i, "clubs": 20, "club_names": ["Club %d" % (i * 20 + k) for k in range(20)],
         "kit_folders": ["C:\\nowhere\\%d" % (i * 20 + k) for k in range(2)], "rid": 300 + i}
        for i in range(BIG // 20)]}, indent=1, ensure_ascii=False)


def by_lines(text, old, new):
    """what rename did before B66: the regex on every line"""
    jw = re.compile(r'("world"\s*:\s*")' + re.escape(old) + '"')
    return "".join(jw.sub(lambda m: m.group(1) + new + '"', l) for l in text.splitlines(True))


def core(t):
    game = make_game(os.path.join(t, "core"))
    w = os.path.join(game.livecpk_dir, "_FL26Old")
    plan = big_plan("_FL26Old")
    put(os.path.join(w, "leaguebuilder-plan.json"), plan)
    old_time = time.time() - 30 * 86400
    os.utime(w, (old_time, old_time))
    t0 = time.perf_counter()
    WL.rename(game, "_FL26Old", "_FL26Older", QUIET)
    took = time.perf_counter() - t0
    w2 = os.path.join(game.livecpk_dir, "_FL26Older")
    with open(os.path.join(w2, "leaguebuilder-plan.json"), "rb") as f:
        got = f.read()
    ok("rename: the big plan (%d MB, %d lines) as line by line, byte for byte"
       % (len(plan) // 2 ** 20, plan.count("\n")), got == by_lines(plan, "_FL26Old", "_FL26Older").encode("utf-8"))
    ok("rename: a big world in reasonable time (%.1f s)" % took, took < 30)
    ok("rename: the world folder keeps its time (B75)", abs(os.path.getmtime(w2) - old_time) < 2)
    with open(os.path.join(w2, "fl26playerids.json"), encoding="utf-8") as f:
        ok("rename: fl26playerids.json", json.load(f)["world"] == "_FL26Older")

    # the recipe copy: one line, the rest as it was; the same file as the long way
    rd = os.path.join(t, "recipes")
    r = {"world": "_FL26A", "leagues": [{"name": "L", "world": "_FL26A", "x": "ü"}], "edits": {}}
    put(os.path.join(rd, "_FL26A.json"), json.dumps(r, indent=1, ensure_ascii=False))
    got = WL.rename_recipe_copy(rd, "_FL26A", "_FL26B")
    want = dict(r, world="_FL26B")
    with open(got, encoding="utf-8") as f:
        text = f.read()
    ok("recipe copy: renamed, the world key changed, the league's own 'world' not",
       got == os.path.join(rd, "_FL26B.json") and json.loads(text) == want
       and text == json.dumps(want, indent=1, ensure_ascii=False) and not os.path.exists(os.path.join(rd, "_FL26A.json")))
    put(os.path.join(rd, "_FL26C.json"), json.dumps({"leagues": [], "world": "_FL26C"}))      # not Project's layout
    got = WL.rename_recipe_copy(rd, "_FL26C", "_FL26D")
    ok("recipe copy: another layout goes the long way", json.load(open(got, encoding="utf-8"))["world"] == "_FL26D")


def pages(t):
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from PySide6 import QtWidgets
    qa = QApplication.instance() or QApplication([])
    theme.apply(qa)
    from modstudio.app import Bus
    from modstudio.siderini import SiderIni
    from modstudio import roots as R
    from modstudio.pages import roots as RP, myworld as M
    game = make_game(os.path.join(t, "pages"))
    game.running = lambda: (False, False)
    lc = game.livecpk_dir
    put(os.path.join(lc, "_FL26Old", "leaguebuilder-plan.json"), big_plan("_FL26Old"))
    put(os.path.join(lc, "_FL26Third", "fl26world.txt"), "world _FL26Third\r\n")
    now = time.time()
    os.utime(os.path.join(lc, "_FL26Old"), (now - 3000, now - 3000))
    os.utime(os.path.join(lc, "_FL26Third"), (now - 1000, now - 1000))      # newer than _FL26Old
    rd = os.path.join(t, "pages-recipes")
    app = types.SimpleNamespace(game=game, bus=Bus(), settings={}, project=FakeProject(rd, "_FL26Live"))
    app.ini = lambda: SiderIni.load(game.ini_path)
    busy = []
    app.busy = lambda on, text=None: busy.append((on, text))
    app.status = QUIET
    app.save_settings = QUIET
    app.open_page = QUIET
    errors = []
    RP.ask = lambda parent, title, text: True
    RP.error = lambda parent, title, text: errors.append(text)
    page = RP.Roots(app)

    def rescan():
        page.idx = R.scan(game.sider_dir, app.ini())
        page.load()
    page.rescan = rescan
    rescan()
    order = [r["world"] for r in M.world_rows(app)]
    ok("My world's order: the live world, then the newest first: %s" % order,
       order == ["_FL26Live", "_FL26Third", "_FL26Old"])

    QtWidgets.QInputDialog.getText = staticmethod(lambda *a, **k: ("_FL26Older", True))
    beats, last = [], [time.perf_counter()]

    def beat():
        n = time.perf_counter()
        beats.append(n - last[0])
        last[0] = n
    hb = QTimer()
    hb.timeout.connect(beat)
    hb.start(20)
    got = []
    t0 = time.perf_counter()
    started = page.rename_world("_FL26Old", done=got.append)
    back = time.perf_counter() - t0
    ok("Rename world: started, back at once (%.2f s), the work still running" % back,
       started is True and not got and page.renaming == "_FL26Old")
    ok("Rename world: the bottom bar says Renaming _FL26Old...", busy and busy[-1] == (True, "Renaming _FL26Old..."))
    ok("Rename world: its buttons are off meanwhile", not page.b_wren.isEnabled() and not page.b_wdel.isEnabled())
    n = len(errors)
    page.rename_world("_FL26Live")
    ok("Rename world: a second one meanwhile is refused", len(errors) == n + 1 and "Renaming" in errors[-1])
    beats.clear()
    last[0] = time.perf_counter()
    t0 = time.perf_counter()
    wait_rename(qa, page)
    took = time.perf_counter() - t0
    hb.stop()
    ok("Rename world: the window kept answering (%d ticks in %.1f s, longest gap %.2f s)"
       % (len(beats), took, max(beats or [0])), beats and max(beats) < 2.0)
    ok("Rename world: done('_FL26Older') when it is over", got == ["_FL26Older"])
    ok("Rename world: buttons back on, bottom bar cleared",
       page.b_wren.isEnabled() and page.b_wdel.isEnabled() and busy[-1][0] is False)
    ok("Rename world: the world is renamed", os.path.isdir(os.path.join(lc, "_FL26Older"))
       and not os.path.exists(os.path.join(lc, "_FL26Old")) and not errors[n + 1:])
    order = [r["world"] for r in M.world_rows(app)]
    ok("B75: the renamed world keeps its place among the cards: %s" % order,
       order == ["_FL26Live", "_FL26Third", "_FL26Older"])

    # a rename refused in the background (a folder taken meanwhile) ends the same way, with the error
    QtWidgets.QInputDialog.getText = staticmethod(lambda *a, **k: ("_FL26Taken", True))
    real = WL.rename
    WL.rename = lambda *a, **k: (_ for _ in ()).throw(WL.WorldError("There is a world called _FL26Taken already."))
    try:
        got.clear()
        page.rename_world("_FL26Third", done=got.append)
        wait_rename(qa, page)
    finally:
        WL.rename = real
    ok("Rename world refused in the background: the same error box, done(None), buttons back on",
       errors and "_FL26Taken already" in errors[-1] and got == [None] and page.b_wren.isEnabled())
    page.deleteLater()
    qa.processEvents()


def main():
    t = tempfile.mkdtemp(prefix="worldrename-")
    try:
        core(t)
        pages(t)
    finally:
        shutil.rmtree(t, ignore_errors=True)
    print("test_world_rename_bg: ok (%d)" % N)


if __name__ == "__main__":
    main()
