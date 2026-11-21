r"""python tools/test_splash_start.py

The start of Mod Studio (mato 10.11.: the move from the opening animation into the program was not
smooth, everything froze for a moment while the opening still ran; it should grow from the small
window into the big one).
Through the exe the drawing stopped after ">_ FL" while the main window built itself (2-8 s on the
one thread), jumped to its end, the window flashed white and was there at once, and then the cards
of My world read every built world's plan in a thread: json.load of a big one holds all of Python
for seconds. Now:
- the splash runs in a process of its own and says when it has run its time; the window, shown
  unseen, sends it a picture of itself, the splash grows its card into it and the window comes in
  under it (splash.Start / splash.alone)
- no splash process: the window fades in alone
- My world's plan numbers are read in a process of their own (apart.numbers), kept till the file
  changes; the window's thread is not held while a big plan is read

Everything in this process and its children (QT_QPA_PLATFORM=offscreen), a plain widget for the
window, plans written to a temporary folder. No game.
"""
import json, os, shutil, sys, tempfile, threading, time, types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication, QWidget

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def until(qa, cond, secs):
    t = time.time()
    while time.time() - t < secs and not cond():
        qa.processEvents()
        time.sleep(0.005)
    return cond()


def start_grows(qa):
    from modstudio import splash as S
    heard = []
    st = S.Start(qa)
    st._say_real = st._say
    st._say = lambda text: (heard.append(text.split("\t")[0]), st._say_real(text))
    ok("the splash process starts", st.proc is not None and until(qa, lambda: st.sock is not None, 15))
    time.sleep(1.0)                               # the window building itself, the thread held
    w = QWidget()
    w.resize(900, 600)
    st.finish(w)
    ok("the window shown unseen at once (its first paint under the splash)",
       w.isVisible() and w.windowOpacity() == 0.0)
    ok("its picture taken for the card", until(qa, lambda: st.picture, 5) and os.path.isfile(st.picture))
    pic = st.picture
    ok("... and it waits for the splash to have run its time",
       not st.said_done and not st.sent and w.windowOpacity() == 0.0)
    t = time.monotonic()
    ok("the splash says it is done after its time",
       until(qa, lambda: st.said_done, 10) and (time.monotonic() - st.t0) * 1000 >= S.RUN_MS * 0.95)
    ok("the card is told to grow into the window's picture", st.sent and heard[:1] == ["grow"])
    ok("the window comes in once the card has its size, the splash told to go",
       until(qa, lambda: st.over, 5) and w.windowOpacity() == 1.0 and heard[-1] == "go"
       and (time.monotonic() - t) * 1000 >= S.GROW_MS * 0.9)
    ok("the splash process ends, the picture with it",
       until(qa, lambda: st.proc is None or st.proc.state() == S.QProcess.NotRunning, 5)
       and not os.path.exists(pic))
    w.close()


def start_alone(qa):
    from modstudio import splash as S
    real = sys.executable
    sys.executable = os.path.join(tempfile.gettempdir(), "no-such-python.exe")
    try:
        st = S.Start(qa)
    finally:
        sys.executable = real
    until(qa, lambda: st.proc is None, 5)
    w = QWidget()
    w.resize(600, 400)
    t = time.monotonic()
    st.finish(w)
    ok("no splash process: the window fades in alone, without waiting for it",
       until(qa, lambda: w.windowOpacity() == 1.0 and st.over, 3) and time.monotonic() - t < 2 and not st.sent)
    w.close()


def plan(n_leagues, clubs):
    return {"world": "_FL26X", "leagues": [
        {"name": "L%d" % i, "country": "Spain", "clubs": clubs, "format": "league", "region": 300 + i % 3,
         "club_names": ["C%d" % j for j in range(clubs)], "club_abbrs": ["C%02d" % j for j in range(clubs)],
         "players": [{"id": 900000 + i * 1000 + j, "name": "Player %d %d" % (i, j), "ratings": list(range(40))}
                     for j in range(clubs * 23)]}
        for i in range(n_leagues)]}


def numbers_apart(qa):
    from modstudio import apart, filecache
    from modstudio.pages import myworld as MW
    tmp = tempfile.mkdtemp(prefix="startfreeze_")
    try:
        game = types.SimpleNamespace(livecpk_dir=tmp)
        plans = {"_FL26Big": plan(400, 22), "_FL26Small": plan(2, 10)}
        for w, pl in plans.items():
            os.makedirs(os.path.join(tmp, w))
            with open(os.path.join(tmp, w, MW.PLAN), "w", encoding="utf-8") as f:
                json.dump(pl, f)
        size = os.path.getsize(os.path.join(tmp, "_FL26Big", MW.PLAN)) / 1e6
        t = time.monotonic()
        json.load(open(os.path.join(tmp, "_FL26Big", MW.PLAN), encoding="utf-8"))
        here = time.monotonic() - t
        got, gaps = {}, []

        def work():
            got.update(MW.plan_summaries(game, ["_FL26Big", "_FL26Small", "_FL26None"]))
        th = threading.Thread(target=work)
        last = time.monotonic()
        th.start()
        while th.is_alive():
            time.sleep(0.005)
            now = time.monotonic()
            gaps.append(now - last)
            last = now
        ok("the plans' numbers as read here", got["_FL26Big"] == apart.plan_numbers(plans["_FL26Big"])
           and got["_FL26Small"] == {"leagues": 2, "clubs": 20, "regions": 2} and got["_FL26None"] is None)
        ok("the window's thread never held while a %.0f MB plan is read (json.load here %.2f s, longest wait %.3f s)"
           % (size, here, max(gaps)), max(gaps) < max(0.15, here / 3))
        t = time.monotonic()
        again = MW.plan_summaries(game, ["_FL26Big", "_FL26Small"])
        ok("kept: read again without a process (%.3f s)" % (time.monotonic() - t),
           again["_FL26Big"] == got["_FL26Big"] and time.monotonic() - t < 0.2)
        p = os.path.join(tmp, "_FL26Small", MW.PLAN)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(plan(3, 10), f)
        ok("a plan changed: read again", MW.plan_summaries(game, ["_FL26Small"])["_FL26Small"]["leagues"] == 3)
        filecache.forget_under(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    qa = QApplication.instance() or QApplication([])
    numbers_apart(qa)
    start_grows(qa)
    start_alone(qa)
    print("test_splash_start: ok (%d)" % N)


if __name__ == "__main__":
    main()
