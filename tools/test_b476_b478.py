"""B476: Install the modules (Home, Lua modules) does not stand the window still.
B478: opening a dialog of League Builder leaves the page's widgets as they were (none turned
into a native window), so the glow of a button does not take the button's clicks.

    python test_b476_b478.py
"""
import os, sys, threading, time, types
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PySide6.QtCore import QEvent, QPoint, Qt, QTimer
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget

qa = QApplication.instance() or QApplication([])
from modstudio import modfix, theme
from modstudio.pages import builder
import leaguebuilder as B

theme.apply(qa)
N = [0]


def ok(name, cond):
    N[0] += 1
    assert cond, name
    print("ok %2d - %s" % (N[0], name))


def natives(root):
    return [w for w in [root] + root.findChildren(QWidget)
            if not w.isWindow() and w.testAttribute(Qt.WA_NativeWindow)]


# ---- B478 ----
main = QWidget()
lay = QVBoxLayout(main)
page = QWidget()
lay.addWidget(page)
pl = QVBoxLayout(page)
btn = QPushButton("Build and install")
pl.addWidget(btn)
main.show()
qa.processEvents()
ok("B478: before a dialog no widget of the page is a native window", not natives(main))
d = builder.Dialog(page, "Club")
seen = {}


def close():
    seen["dark"] = bool(d.property("_dark_bar"))
    seen["visible"] = d.isVisible()
    d.reject()


QTimer.singleShot(200, close)
r = d.finish()
qa.processEvents()
ok("B478: the dialog was shown and Cancel gives False", seen.get("visible") and r is False)
ok("B478: the dialog still gets its dark title bar, when it is shown", seen.get("dark"))
ok("B478: after the dialog no widget of the page is a native window (%d)" % len(natives(main)),
   not natives(main))
src = open(os.path.join(os.path.dirname(os.path.abspath(builder.__file__)), "builder.py"), encoding="utf-8").read()
fin = src[src.index("    def finish(self):"):src.index("    def add_buttons(self, bb):")]
code = "\n".join(l for l in fin.splitlines() if not l.strip().startswith("#"))
ok("B478: Dialog.finish asks for no window handle before the dialog is shown",
   "dark_title_bar(" not in code and "winId" not in code)

# ---- B476 ----
on, ticks, clicks, told = [], [0], [0], []
game = types.SimpleNamespace(ok=lambda: True, ini_path="x.ini", sider_dir="x", folder="x")
bus = types.SimpleNamespace(ini_changed=types.SimpleNamespace(emit=lambda: told.append("ini")),
                            content_changed=types.SimpleNamespace(emit=lambda: told.append("content")))
stub = types.SimpleNamespace(app=types.SimpleNamespace(game=game, bus=bus))
modfix.snapshot = lambda *a, **k: on.append(("snapshot", threading.current_thread() is threading.main_thread()))
modfix.info = lambda *a, **k: told.append("info")
modfix.error = lambda page, title, text: told.append("error: " + text)


def slow(folder, log=print, **k):
    on.append(("install", threading.current_thread() is threading.main_thread()))
    time.sleep(0.6)
    log("modules: all 43 already there")


B.install_modules = slow
beat = QTimer()
beat.setInterval(20)
beat.timeout.connect(lambda: ticks.__setitem__(0, ticks[0] + 1))
beat.start()
btn.clicked.connect(lambda: clicks.__setitem__(0, clicks[0] + 1))


def poke():
    c = btn.rect().center()
    for t in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease):
        qa.sendEvent(btn, QMouseEvent(t, c, btn.mapToGlobal(c), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
    main.close()


QTimer.singleShot(200, poke)
t0 = time.time()
res = modfix.install_now(stub)
took = time.time() - t0
ok("B476: install_now still answers True when it worked", res is True)
ok("B476: the restore point and the copy ran off the window's thread (%s)" % on,
   on == [("snapshot", False), ("install", False)])
ok("B476: the window's thread went on meanwhile (%d turns in %.2f s)" % (ticks[0], took), ticks[0] >= 15)
ok("B476: a click meanwhile starts nothing and the window stays open", clicks[0] == 0 and main.isVisible())
ok("B476: Home is told and the notice comes after the copy (%s)" % told, told == ["ini", "content", "info"])
ok("B476: the wait cursor is taken back", QApplication.overrideCursor() is None)
poke_ok = []
c = btn.rect().center()
for t in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease):
    qa.sendEvent(btn, QMouseEvent(t, c, btn.mapToGlobal(c), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
ok("B476: afterwards the buttons take clicks again", clicks[0] == 1)

del told[:]


def bad(folder, log=print, **k):
    raise B.BuildError("fl26swiss.dll: blocked")


B.install_modules = bad
res = modfix.install_now(stub)
ok("B476: an error of the copy is shown as before and gives False (%s)" % told,
   res is False and told == ["error: fl26swiss.dll: blocked", "ini"])
ok("B476: ... and the wait cursor is taken back", QApplication.overrideCursor() is None)
ok("B476: no thread of the install is left", not [t for t in threading.enumerate() if t.name == "install-modules"])
print("all %d ok" % N[0])
