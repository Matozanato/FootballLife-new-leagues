"""python tools/test_support.py [en|es|fr|pt|hr]

The Ko-fi reminder (mato 19.10.: "samo kod prvog otvaranja", no long text): Main.ask_support in a
temp APPDATA, no game, offscreen:
  - the first start of a version shows it, with Support on Ko-fi and Not now, in the language;
  - "support" in settings.json then holds the version, and the next start does not show it again;
  - a start after an older version's reminder shows it once more;
  - while the quick tour runs it waits, and comes after the tour;
  - Support on Ko-fi opens ko-fi.com/mata28, Not now opens nothing.
"""
import json, os, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ENV0 = dict(os.environ)               # the children need the real APPDATA (user site: PySide6)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.pop("FL26_DIR", None)
T = tempfile.mkdtemp(prefix="support-")
os.environ["APPDATA"] = os.path.join(T, "appdata")      # before modstudio.app reads it (APPDIR)
os.environ["FL26_SAVE_ROOT"] = os.path.join(T, "konami")

from test_world_manage import make_game, put

LANG = sys.argv[1] if len(sys.argv) > 1 else "en"
assert LANG in ("en", "es", "fr", "pt", "hr"), "usage: test_support.py [en|es|fr|pt|hr]"
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
        qa.sendPostedEvents(None, QEvent.DeferredDelete.value)
        time.sleep(0.02)


def run():
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import QApplication
    qa = QApplication.instance() or QApplication([])
    from modstudio import app as A, theme, i18n, VERSION
    from modstudio import saves as SV, ui as U
    SV.game_running = lambda: False
    U.info = lambda *a, **k: None
    opened = []
    QDesktopServices.openUrl = staticmethod(lambda url: opened.append(url.toString()) or True)
    theme.apply(qa)
    game = make_game(T)
    ms = os.path.join(os.environ["APPDATA"], "FL26ModStudio")
    os.makedirs(os.path.join(ms, "tables"))
    put(os.path.join(ms, "recipes", "_FL26Live.json"), json.dumps({"world": "_FL26Live", "leagues": []}))

    def start(extra):
        d = {"game": game.folder, "tables": os.path.join(ms, "tables"), "check_updates": False, "lang": LANG}
        d.update(extra)
        with open(os.path.join(ms, "settings.json"), "w", encoding="utf-8") as f:
            json.dump(d, f)
        w = A.Main()
        w.resize(1360, 820)
        w.show()
        settle(qa, 0.3)
        return w

    def saved():
        with open(os.path.join(ms, "settings.json"), encoding="utf-8") as f:
            return json.load(f)

    w = start({})
    w.ask_support()
    settle(qa)
    box = getattr(w, "_support", None)
    ok("the first start of %s shows the reminder" % VERSION, box is not None and box.isVisible())
    names = [b.text().replace("&", "") for b in box.buttons()]
    ok("its buttons in %s: %s" % (LANG, names),
       sorted(names) == sorted([i18n._("Support on Ko-fi"), i18n._("Not now")]))
    import html, re
    msg = html.escape(i18n._("FL26 Mod Studio is free and donating is never required, but a small "
                             "donation on Ko-fi makes it easier for us to keep the project maintained "
                             "and updated. Thank you!"))
    shown = re.sub(r"<[^>]+>", " ", box.text())
    ok("its text in %s, short, with the Ko-fi link" % LANG,
       box.text().startswith(msg) and len(shown) < 240
       and '<a href="https://ko-fi.com/mata28">ko-fi.com/mata28</a>' in box.text())
    if os.environ.get("FL26_SHOT"):
        box.grab().save(os.path.join(os.environ["FL26_SHOT"], "k_support_%s.png" % LANG))
    ok("settings.json remembers it for %s" % VERSION, saved().get("support") == VERSION)
    [b for b in box.buttons() if b.text().replace("&", "") == i18n._("Not now")][0].click()
    settle(qa)
    ok("Not now: closed, nothing opened", not box.isVisible() and opened == [])
    w.kofi_btn.click()
    settle(qa)
    ok("the Ko-fi button next to Credits opens ko-fi.com/mata28",
       opened == ["https://ko-fi.com/mata28"])
    del opened[:]
    w.close()

    w = start({"support": VERSION})
    w._support = None
    w.ask_support()
    settle(qa)
    ok("the next start of the same version: not shown again", w._support is None)
    w.close()

    w = start({"support": "0.2.3"})
    w._tour = object()                      # the quick tour on the screen
    w._support = None
    w.ask_support()
    settle(qa)
    ok("while the quick tour runs it waits", w._support is None and saved().get("support") == "0.2.3")
    w._tour = None
    settle(qa, 2.5)
    box = w._support
    ok("after the tour (and after an older version's reminder) it shows", box is not None and box.isVisible())
    [b for b in box.buttons() if b.text().replace("&", "") == i18n._("Support on Ko-fi")][0].click()
    settle(qa)
    ok("Support on Ko-fi opens ko-fi.com/mata28", opened == ["https://ko-fi.com/mata28"])
    w.close()


if __name__ == "__main__":
    import subprocess
    if len(sys.argv) > 1:
        import shutil
        try:
            run()
        finally:
            shutil.rmtree(T, ignore_errors=True)
        print("test_support: ok (%d)" % N)
    else:
        for lang in ("en", "es", "fr", "pt", "hr"):
            r = subprocess.run([sys.executable, os.path.abspath(__file__), lang], env=ENV0)
            if r.returncode:
                sys.exit(r.returncode)
        print("test_support: ok (en, es, fr, pt, hr)")
