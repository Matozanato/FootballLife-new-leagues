"""python tools/test_tour.py [en|es|fr|pt|hr]      (no language: all five, one after the other)

The quick tour of 0.2.4 (tour.py): at the first start the window shows, one step at a time, where
things are now. This test opens the whole window (QT_QPA_PLATFORM=offscreen, a fake game folder and
APPDATA in a temp folder, no game) and walks the tour:

  - due() until the tour is finished or skipped in this version, not after;
  - every step after the first points at a widget that is there and visible;
  - at the smallest size of the window, at its first size and at 1920x1032 the card of every step
    is inside the window, shows all of its text and does not cover the widget it talks about;
  - Back, Next and Done; Done and Skip the tour write "tour" in settings.json, the card and the
    frame are gone, and Help > Quick tour shows it again (once, not twice over itself);
  - Install a Modpack, step by step (Help, and the button on the last card of the quick tour): seven
    steps, the frame on 2. My world, + Add... (My world opened for it) and Start the game, the card
    inside the window with all of its text at the smallest and the largest size, Close and Done end
    it, and it does not count as the quick tour seen;
  - Edit a Modpack, step by step (Help, and the button on the last card of the Modpack guide): seven
    steps, the frame on 2. My world, Make it editable... (shown as for a world from a zip), the
    Leagues tab, Build and install (the Build tab opened for it), Start the game and 4. Tools, the
    card inside the window with all of its text.
"""
import json, os, shutil, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ENV0 = dict(os.environ)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.pop("FL26_DIR", None)
T = tempfile.mkdtemp(prefix="tour-")
os.environ["APPDATA"] = os.path.join(T, "appdata")      # before modstudio.app reads it (APPDIR)
os.environ["FL26_SAVE_ROOT"] = os.path.join(T, "konami")

from test_world_manage import make_game, put

LANG = sys.argv[1] if len(sys.argv) > 1 else "en"
assert LANG in ("en", "es", "fr", "pt", "hr"), "usage: test_tour.py [en|es|fr|pt|hr]"
N = 0
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def settle(qa, secs=0.2):
    from PySide6.QtCore import QEvent
    t0 = time.time()
    while time.time() - t0 < secs:
        qa.processEvents()
        qa.sendPostedEvents(None, QEvent.DeferredDelete.value)     # deleteLater, as the event loop does
        time.sleep(0.02)


def saved(ms):
    with open(os.path.join(ms, "settings.json"), encoding="utf-8") as f:
        return json.load(f)


def run():
    from PySide6.QtCore import QPoint, QRect
    from PySide6.QtWidgets import QApplication, QWidget
    qa = QApplication.instance() or QApplication([])
    from modstudio import app as A, theme, tour as TR, i18n
    from modstudio import saves as SV, ui as U
    SV.game_running = lambda: False
    U.info = lambda *a, **k: None
    theme.apply(qa)
    game = make_game(T)
    ms = os.path.join(os.environ["APPDATA"], "FL26ModStudio")
    os.makedirs(os.path.join(ms, "tables"))
    put(os.path.join(ms, "recipes", "_FL26Live.json"), json.dumps({"world": "_FL26Live", "leagues": []}))
    with open(os.path.join(ms, "settings.json"), "w", encoding="utf-8") as f:
        json.dump({"game": game.folder, "tables": os.path.join(ms, "tables"), "check_updates": False,
                   "lang": LANG}, f)

    ok("due with no tour seen", TR.due({}))
    ok("due after the tour of an older version", TR.due({"tour": "0.2.3"}))
    ok("not due after this version's", not TR.due({"tour": TR.TOUR}))

    w = A.Main()
    ok("the window speaks %s" % LANG, i18n.CODE == LANG or LANG == "en")
    ok("not due in a new APPDATA", TR.due(w.settings))
    w.resize(1360, 820)
    w.show()
    settle(qa, 0.5)

    w.start_tour()
    settle(qa)
    t = w._tour
    ok("the tour starts", t is not None and t.card.isVisible() and t.i == 0)
    first = t
    w.start_tour()
    ok("a second start while it runs is not a second tour", w._tour is first)
    n = len(t.steps)
    ok("ten steps", n == 10)
    for i, (title, text, target) in enumerate(t.steps[1:], 2):
        ok("step %d (%s) points at a widget" % (i, title), target is not None)
    if LANG != "en":
        ok("the steps are in %s" % LANG, t.steps[0][0] != "Welcome to Mod Studio 0.2.4"
           and t.skip.text() != "Skip the tour")

    def check(size):
        w.resize(*size)
        settle(qa, 0.3)
        W, H = w.width(), w.height()
        for i in range(n):
            t.show_step(i)
            settle(qa, 0.05)
            c = t.card.geometry()
            name = "%dx%d step %d" % (W, H, i + 1)
            ok(name + ": the card is inside the window %s" % [c.x(), c.y(), c.width(), c.height()],
               c.left() >= 0 and c.top() >= 0 and c.right() < W and c.bottom() < H)
            need = t.text.heightForWidth(t.text.width()) if t.text.width() > 0 else 0
            ok(name + ": all of the text shows (%d of %d px)" % (t.text.height(), need), t.text.height() >= need)
            ok(name + ": the buttons show", t.next.isVisible() and t.skip.isVisible()
               and t.next.geometry().bottom() <= t.card.height())
            tg = t.target()
            if i == 0:
                ok(name + ": no frame on the welcome", not t.frame.isVisible())
            else:
                ok(name + ": the frame shows", tg is not None and t.frame.isVisible())
                r = QRect(tg.mapTo(w, QPoint(0, 0)), tg.size())
                ok(name + ": the card does not cover what it talks about", not c.intersects(r))
                ok(name + ": the frame is around it", t.frame.geometry().contains(r))
    for size in ((1080, 640), (1360, 820), (1920, 1032)):
        check(size)

    t.show_step(0)
    ok("Back is off on the first step", not t.back.isEnabled())
    t.forward()
    ok("Next goes on", t.i == 1 and t.back.isEnabled())
    t.back.click()
    ok("Back goes back", t.i == 0)
    t.show_step(n - 1)
    ok("the last step says Done", t.next.text() == i18n._("Done"))
    ok("not saved before the end", saved(ms).get("tour") is None)
    t.next.click()
    settle(qa)
    ok("Done: seen in settings.json", saved(ms).get("tour") == TR.TOUR and not TR.due(w.settings))
    ok("Done: the tour is gone", w._tour is None and not w.findChildren(QWidget, "tourcard"))

    help_menu = w.help_btn.menu()
    quick = [a for a in help_menu.actions() if a.text() == i18n._("Quick tour")]
    ok("Help has Quick tour", len(quick) == 1)
    quick[0].trigger()
    settle(qa)
    ok("Help > Quick tour shows it again", w._tour is not None and w._tour.card.isVisible() and w._tour.i == 0)
    w._tour.forward()
    w._tour.forward()
    w._tour.skip.click()
    settle(qa)
    ok("Skip the tour closes it", w._tour is None and not w.findChildren(QWidget, "tourcard")
       and not w.findChildren(QWidget, "tourframe"))
    ok("... and it stays seen", saved(ms).get("tour") == TR.TOUR)

    # Install a Modpack, step by step (mato 18.10.)
    w.settings.pop("tour", None)          # (save_settings keeps what the file has: out of the file too)
    w._seen.pop("tour", None)
    d = saved(ms)
    d.pop("tour", None)
    with open(os.path.join(ms, "settings.json"), "w", encoding="utf-8") as f:
        json.dump(d, f)
    mp = [a for a in help_menu.actions() if a.text() == i18n._("Install a Modpack, step by step")]
    ok("Help has Install a Modpack, step by step", len(mp) == 1)
    names = [a.text() for a in help_menu.actions()]
    ok("Help in order: User guide, Quick tour, Install a Modpack, Edit a Modpack, Check for updates at start, "
       "Check for updates..., About %s" % names,
       names[:7] == [i18n._(x) for x in ("User guide", "Quick tour", "Install a Modpack, step by step",
                                          "Edit a Modpack, step by step",
                                          "Check for updates at start", "Check for updates...",
                                          "About FL26 Mod Studio")])
    w.open_page("Overview")
    settle(qa)
    mp[0].trigger()
    settle(qa)
    g = w._tour
    ok("the Modpack guide starts", g is not None and g.guide == "modpack" and g.card.isVisible() and g.i == 0)
    w.start_tour()
    ok("the quick tour does not start over it", w._tour is g)
    ok("seven steps", len(g.steps) == 7)
    ok("its first button is Close", g.skip.text() == i18n._("Close"))
    if LANG != "en":
        ok("the Modpack guide is in %s" % LANG, g.steps[0][0] != "Install a Modpack, step by step")
    points = {1: "2. My world", 2: "+ Add...", 5: "Start the game", 6: "2. My world"}
    for size in ((1080, 640), (1920, 1032)):
        w.resize(*size)
        w.open_page("Overview")
        settle(qa, 0.3)
        W, H = w.width(), w.height()
        for i in range(len(g.steps)):
            g.show_step(i)
            settle(qa, 0.05)
            c = g.card.geometry()
            name = "Modpack guide %dx%d step %d" % (W, H, i + 1)
            ok(name + ": the card is inside the window %s" % [c.x(), c.y(), c.width(), c.height()],
               c.left() >= 0 and c.top() >= 0 and c.right() < W and c.bottom() < H)
            need = g.text.heightForWidth(g.text.width()) if g.text.width() > 0 else 0
            ok(name + ": all of the text shows (%d of %d px)" % (g.text.height(), need), g.text.height() >= need)
            ok(name + ": the buttons show", g.next.isVisible() and g.skip.isVisible()
               and g.next.geometry().bottom() <= g.card.height())
            tg = g.target()
            if i in points:
                ok(name + ": the frame is on %s" % points[i], tg is not None and g.frame.isVisible())
                r = QRect(tg.mapTo(w, QPoint(0, 0)), tg.size())
                ok(name + ": the card does not cover it", not c.intersects(r))
                ok(name + ": the frame is around it", g.frame.geometry().contains(r))
            else:
                ok(name + ": no frame, the card in the middle", tg is None and not g.frame.isVisible())
            if i == 2:
                ok(name + ": My world is open, the frame on its + Add...",
                   w.my_world.isVisible() and tg is w.my_world.add_btn)
    ok("the Modpack guide's last step says Done", g.next.text() == i18n._("Done"))
    ok("... and offers the edit guide", g.then.isVisible() and g.then.text() == i18n._("Show me how to edit a Modpack"))
    g.next.click()
    settle(qa)
    ok("Done closes the Modpack guide", w._tour is None and not w.findChildren(QWidget, "tourcard")
       and not w.findChildren(QWidget, "tourframe"))
    ok("... and it is not the quick tour seen", saved(ms).get("tour") is None)
    mp[0].trigger()
    settle(qa)
    w._tour.skip.click()
    settle(qa)
    ok("Close closes it too", w._tour is None and not w.findChildren(QWidget, "tourcard"))

    w.resize(1080, 640)
    settle(qa, 0.3)
    w.start_tour()
    settle(qa)
    t = w._tour
    ok("the quick tour's first card does not offer the Modpack guide", not t.then.isVisible())
    t.show_step(len(t.steps) - 1)
    settle(qa, 0.05)
    c = t.card.geometry()
    ok("its last card offers it", t.then.isVisible() and t.then.text() == i18n._("Show me how to install a Modpack"))
    ok("... inside the card and the window", t.then.geometry().bottom() <= t.card.height()
       and c.bottom() < w.height() and c.top() >= 0)
    t.then.click()
    settle(qa)
    ok("the button ends the quick tour (seen) and starts the Modpack guide",
       w._tour is not None and w._tour.guide == "modpack" and w._tour.i == 0
       and saved(ms).get("tour") == TR.TOUR and len(w.findChildren(QWidget, "tourcard")) == 1)
    w._tour.skip.click()
    settle(qa)
    ok("... which closes as well", w._tour is None and not w.findChildren(QWidget, "tourcard"))

    # Edit a Modpack, step by step (mato 18.10.)
    ed = [a for a in help_menu.actions() if a.text() == i18n._("Edit a Modpack, step by step")]
    ok("Help has Edit a Modpack, step by step", len(ed) == 1)
    mp[0].trigger()
    settle(qa)
    w._tour.show_step(len(w._tour.steps) - 1)
    settle(qa, 0.05)
    w._tour.then.click()
    settle(qa)
    e = w._tour
    ok("the Modpack guide's last card starts the edit guide", e is not None and e.guide == "edit" and e.i == 0
       and len(w.findChildren(QWidget, "tourcard")) == 1)
    ok("seven steps in the edit guide", len(e.steps) == 7)
    if LANG != "en":
        ok("the edit guide is in %s" % LANG, e.steps[0][0] != "Edit a Modpack, step by step")
    w.my_world._open_zipped = True          # as for a world from a zip: Make it editable... shows
    w.my_world.update_note()
    epoints = {1: "2. My world", 2: "Make it editable...", 3: "the Leagues tab", 4: "Build and install",
               5: "Start the game", 6: "4. Tools"}
    for size in ((1080, 640), (1920, 1032)):
        w.resize(*size)
        w.open_page("Overview")
        settle(qa, 0.3)
        W, H = w.width(), w.height()
        for i in range(len(e.steps)):
            e.show_step(i)
            settle(qa, 0.05)
            c = e.card.geometry()
            name = "edit guide %dx%d step %d" % (W, H, i + 1)
            ok(name + ": the card is inside the window %s" % [c.x(), c.y(), c.width(), c.height()],
               c.left() >= 0 and c.top() >= 0 and c.right() < W and c.bottom() < H)
            need = e.text.heightForWidth(e.text.width()) if e.text.width() > 0 else 0
            ok(name + ": all of the text shows (%d of %d px)" % (e.text.height(), need), e.text.height() >= need)
            ok(name + ": the buttons show", e.next.isVisible() and e.skip.isVisible()
               and e.next.geometry().bottom() <= e.card.height())
            tg = e.target()
            if i in epoints:
                ok(name + ": the frame is on %s" % epoints[i], tg is not None and e.frame.isVisible())
                r = QRect(tg.mapTo(w, QPoint(0, 0)), tg.size())
                ok(name + ": the card does not cover it", not c.intersects(r))
                ok(name + ": the frame is around it", e.frame.geometry().contains(r))
            else:
                ok(name + ": no frame, the card in the middle", tg is None and not e.frame.isVisible())
            if i == 2:
                ok(name + ": the frame on My world's Make it editable...", tg is w.my_world.b_edit)
            if i == 4:
                ok(name + ": the frame on the Build tab's Build and install", tg is w.page("Build").b_all)
    w.my_world._open_zipped = False
    w.my_world.update_note()
    ok("the edit guide's last step says Done, nothing more", e.next.text() == i18n._("Done") and not e.then.isVisible())
    e.next.click()
    settle(qa)
    ok("Done closes the edit guide", w._tour is None and not w.findChildren(QWidget, "tourcard")
       and not w.findChildren(QWidget, "tourframe"))
    ed[0].trigger()
    settle(qa)
    ok("Help > Edit a Modpack starts it", w._tour is not None and w._tour.guide == "edit" and w._tour.i == 0)
    w._tour.skip.click()
    settle(qa)
    ok("Close closes it", w._tour is None and not w.findChildren(QWidget, "tourcard"))
    w.resize(1400, 900)
    settle(qa)
    ok("the window still resizes after the tour", w.width() == 1400)
    w.close()
    i18n.set_language("en")


def main():
    if len(sys.argv) < 2:
        shutil.rmtree(T, ignore_errors=True)
        import subprocess
        bad = [c for c in ("en", "es", "fr", "pt", "hr")
               if subprocess.call([sys.executable, os.path.abspath(__file__), c], env=ENV0) != 0]
        assert not bad, "test_tour failed for: %s" % ", ".join(bad)
        print("test_tour: ok (en, es, fr, pt, hr)")
        return
    try:
        run()
    finally:
        shutil.rmtree(T, ignore_errors=True)
    print("test_tour: ok (%d)" % N)


if __name__ == "__main__":
    main()
