"""the small animations (modstudio/anim.py): each one ends in the state the window would have
without it, nothing of it is left behind, and none runs where there is no screen.

    python test_anim.py
"""
import os, sys, time
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.pop("FL26_ANIM", None)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, Qt
from PySide6.QtGui import QEnterEvent, QMouseEvent, QWheelEvent
from PySide6.QtWidgets import (QApplication, QDialog, QFrame, QHBoxLayout, QLabel, QListWidget, QMenu, QPushButton,
                               QScrollArea, QStackedWidget, QTabWidget, QToolButton, QVBoxLayout, QWidget)

qa = QApplication.instance() or QApplication([])
from modstudio import anim, theme

N = [0]


def ok(name, cond):
    N[0] += 1
    assert cond, name
    print("ok %2d - %s" % (N[0], name))


def wait(cap=3.0):
    t = time.time()
    while time.time() - t < cap:
        qa.processEvents()
        if not anim.busy():
            for _ in range(3):
                qa.processEvents()             # the deleteLater of what it left
            return True
        time.sleep(0.005)
    return False


def kids(w, name):
    return [c for c in w.findChildren(QWidget, name) if c.isVisible()]


def over(area):
    """the pictures that lie over area: children of its window, not of area (see anim._Shot)"""
    return [c for c in area.window().findChildren(QWidget, "animshot") if c.isVisible() and c._area is area]


def seen(win, widget):
    """the colour the window shows in the middle of widget, drawn as the screen would get it"""
    c = widget.mapTo(win, widget.rect().center())
    return win.grab().toImage().pixelColor(c)


def enter(b):
    p = QPointF(5, 5)
    g = QPointF(b.mapToGlobal(QPoint(5, 5)))
    QApplication.sendEvent(b, QEnterEvent(p, p, g))
    QApplication.sendEvent(b, QMouseEvent(QEvent.MouseMove, p, g, Qt.NoButton, Qt.NoButton, Qt.NoModifier))


def leave(b):
    QApplication.sendEvent(b, QEvent(QEvent.Leave))


def ghosts():
    return [w for w in qa.topLevelWidgets() if w.objectName() == "animghost" and w.isVisible()]


def turn(view, notches=1):
    """the mouse wheel over view, `notches` clicks down; True: somebody took it"""
    p = QPointF(10, 10)
    e = QWheelEvent(p, QPointF(view.mapToGlobal(QPoint(10, 10))), QPoint(0, 0), QPoint(0, -120 * notches),
                    Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
    QApplication.sendEvent(view, e)
    return e.isAccepted()


def more(win, stack, one, two):
    """beta 3: a slide, a tab, the line under the sections, a dialog that rises and leaves, a
    menu, the wheel, the Back and Forward icons"""
    v = win.layout()

    # ---- a page that lies to one side
    from PySide6.QtGui import QColor, QPalette
    pal = stack.palette()                 # (as the style sheet leaves the pages of Mod Studio: no ground of their own)
    pal.setColor(QPalette.Window, QColor(0, 0, 0, 0))
    stack.setPalette(pal)
    anim.cover(stack, 1)
    stack.setCurrentWidget(one)
    shot = over(stack)[0]
    c = seen(win, stack)
    for _ in range(40):
        qa.processEvents()
        if shot._next is not None:
            break
        time.sleep(0.005)
    ok("a page to the side: the old one is what is seen first (%s)" % c.name(), c.blue() > 150 and c.red() < 100)
    ok("a page to the side: a picture of the next one is taken once it is painted",
       shot._next is not None and shot._next.size() == shot._picture.size() and shot._way == 1)
    ok("... the picture is not in the picture", not shot._quiet)
    shot._o = 0.70                        # the old page has just gone, the next has hardly begun
    g, c = shot._ground, seen(win, stack)
    ok("... between the two the ground is seen, not the next page through both (ground %s, seen %s)" % (g.name(), c.name()),
       g.alpha() == 255 and abs(c.red() - g.red()) < 40 and abs(c.green() - g.green()) < 40 and abs(c.blue() - g.blue()) < 40)
    ok("... it ends and is gone", wait() and not over(stack) and stack.currentWidget() is one
       and seen(win, stack).red() > 150)
    anim.cover(stack, 1)
    stack.setCurrentWidget(two)
    qa.processEvents()
    stack.hide()
    for _ in range(20):
        qa.processEvents()
        win.grab()
        time.sleep(0.005)
    ok("what the picture lay over is hidden meanwhile: the picture goes with it",
       not [c for c in win.findChildren(QWidget, "animshot") if c.isVisible()])
    stack.show()
    wait()
    stack.setCurrentWidget(one)
    anim.cover(stack, -1)
    anim.cover(stack, 1)
    ok("... two in a row: one picture", len(over(stack)) == 1 and wait() and not over(stack))

    # ---- tabs
    tw = QTabWidget()
    tw.addTab(QLabel("first"), "First")
    tw.addTab(QLabel("second"), "Second")
    tw.addTab(QLabel("third"), "Third")
    tw.setTabEnabled(2, False)
    v.addWidget(tw)
    qa.processEvents()
    ok("a tab widget that is shown is hooked once", tw.property("_anim_tabs") is True)
    inner = tw.currentWidget().parentWidget()
    tw.tabBarClicked.emit(0)
    ok("a click on the open tab: nothing", not over(inner))
    tw.tabBarClicked.emit(2)
    ok("... on a tab that is off: nothing", not over(inner))
    tw.tabBarClicked.emit(1)
    tw.setCurrentIndex(1)
    got = over(inner)
    ok("... on another tab: its page slides, to the side the tab is on", len(got) == 1 and got[0]._way == 1)
    ok("... ends", wait() and not over(inner) and tw.currentIndex() == 1)
    sec = QTabWidget()
    sec.setObjectName("sectiontabs")
    sec.addTab(QLabel("a"), "A")
    v.addWidget(sec)
    qa.processEvents()
    ok("the sections' own tabs are left to the window (it remembers their pages)", not sec.property("_anim_tabs"))

    # ---- the line under the open section
    bar = QWidget()
    h = QHBoxLayout(bar)
    b1, b2 = QPushButton("1. My world"), QPushButton("2. Players")
    h.addWidget(b1)
    h.addWidget(b2)
    v.addWidget(bar)
    qa.processEvents()
    anim.line(bar, b1, b2, "#F5A524", "#0C1015")
    got = kids(bar, "animline")
    ok("the line under the sections travels: one widget over the bar, no clicks",
       len(got) == 1 and got[0].testAttribute(Qt.WA_TransparentForMouseEvents) and anim.busy())
    anim.line(bar, b2, b1, "#F5A524", "#0C1015")
    ok("... back before it is there: still one", len(kids(bar, "animline")) == 1)
    ok("... ends and is gone", wait() and not kids(bar, "animline"))
    anim.line(bar, b1, b1, "#F5A524", "#0C1015")
    anim.line(bar, None, b1, "#F5A524", "#0C1015")
    anim.line(bar, b1, go_outside := QPushButton("x"), "#F5A524", "#0C1015")
    ok("the same button, none before, one of another bar: nothing", not kids(bar, "animline") and not anim.busy())
    go_outside.deleteLater()

    # ---- a dialog rises into its place and fades out of it
    d = QDialog(win)
    QVBoxLayout(d).addWidget(QLabel("really? " * 6))
    d.resize(260, 120)
    d.move(100, 100)
    d.show()
    home = d.pos()
    qa.processEvents()
    ok("a dialog asks for the dark title bar when it is first shown (every dialog, not only the editors)",
       d.property("_dark_bar") is True)
    ok("a dialog starts a little under its place", d.pos().x() == home.x() and home.y() < d.pos().y() <= home.y() + anim.RISE_PX)
    ok("... and ends in it", wait() and d.pos() == home and d.windowOpacity() == 1.0)
    d.hide()
    g = ghosts()
    ok("a dialog that closes leaves a picture where it stood", len(g) == 1 and g[0].geometry() == d.geometry()
       and g[0].windowOpacity() < 1.0)
    ok("... which takes no clicks and no focus", g[0].testAttribute(Qt.WA_TransparentForMouseEvents)
       and bool(g[0].windowFlags() & Qt.WindowTransparentForInput) and bool(g[0].windowFlags() & Qt.WindowDoesNotAcceptFocus)
       and qa.focusWidget() is not g[0])
    ok("... and is gone", wait() and not ghosts())
    d.show()
    d.move(300, 200)                     # (somebody places it just after it is shown: builder.Dialog.fit)
    ok("a dialog moved while it rises stays where it was put", wait() and d.pos() == QPoint(300, 200))
    d.close()
    wait()
    quiet = QDialog(win)
    quiet.resize(200, 100)
    quiet.hide()
    ok("a dialog that was never shown leaves none", not ghosts())
    quiet.deleteLater()

    # ---- a menu
    m = QMenu(win)
    m.addAction("One")
    m.addAction("Two")
    m.popup(win.mapToGlobal(QPoint(20, 20)))
    ok("a menu fades in", 0.2 < m.windowOpacity() < 1.0)
    ok("... all there", wait() and m.windowOpacity() == 1.0)
    m.hide()
    ok("... and leaves no picture (it is no dialog)", not ghosts())

    # ---- the wheel
    area = QScrollArea()
    inside = QLabel("\n".join("line %d" % i for i in range(200)))
    area.setWidget(inside)
    area.setFixedHeight(120)
    v.addWidget(area)
    qa.processEvents()
    bar_ = area.verticalScrollBar()
    step = QApplication.wheelScrollLines() * bar_.singleStep()
    ok("the wheel over a page: taken", turn(area.viewport()) and anim.busy())
    ok("... the page is on its way, not there", bar_.value() < step)
    ok("... and gets there", wait() and bar_.value() == step)
    turn(area.viewport())
    turn(area.viewport())
    ok("two turns in a row add up", wait() and bar_.value() == 3 * step)
    bar_.setValue(bar_.maximum())
    took = turn(area.viewport())
    ok("at the end of the page the turn is left alone", not anim.busy() and bar_.value() == bar_.maximum())
    lw = QListWidget()
    lw.addItems(["row %d" % i for i in range(100)])
    lw.setFixedHeight(100)
    v.addWidget(lw)
    qa.processEvents()
    turn(lw.viewport())
    ok("a list that goes row by row is left to itself", not anim.busy() and lw.verticalScrollBar().value() > 0)

    # ---- Back and Forward
    from modstudio import icons
    from PySide6.QtCore import QSize
    from PySide6.QtGui import QIcon
    for scale in (16, 20, 24, 32):
        left = icons.chevron(-1).pixmap(QSize(scale, scale), QIcon.Normal).toImage()
        right = icons.chevron(1).pixmap(QSize(scale, scale), QIcon.Normal).toImage()
        lit = lambda im: [(x, y) for y in range(im.height()) for x in range(im.width()) if im.pixelColor(x, y).alpha() > 40]
        a, b = lit(left), lit(right)
        ok("the Back icon at %d px: drawn, the mirror of Forward, top and bottom alike" % scale,
           len(a) > scale and sorted((scale - 1 - x, y) for x, y in a) == sorted(b)
           and sorted((x, scale - 1 - y) for x, y in a) == sorted(a))
        ok("... it points left: its point is left of its ends",
           min(x for x, y in a) == min(x for x, y in a if abs(y - (scale - 1) / 2.0) <= 1.0)
           and max(x for x, y in a if y == min(yy for _x, yy in a)) > min(x for x, y in a) + scale // 8)
    off = icons.chevron(-1).pixmap(QSize(16, 16), QIcon.Disabled).toImage()
    hot = icons.chevron(-1).pixmap(QSize(16, 16), QIcon.Active).toImage()
    mid = lambda im: max((im.pixelColor(x, y) for y in range(16) for x in range(16)), key=lambda c: c.alpha())
    ok("... dim when there is nowhere to go, white under the pointer",
       mid(off).lightness() < mid(left := icons.chevron(-1).pixmap(QSize(16, 16), QIcon.Normal).toImage()).lightness() < mid(hot).lightness())
    return d, tw, area, m


def main():
    theme.apply(qa)
    win = QWidget()
    v = QVBoxLayout(win)
    stack = QStackedWidget()
    one, two = QLabel(), QLabel()
    one.setStyleSheet("background: #ff0000;")
    two.setStyleSheet("background: #0000ff;")
    stack.addWidget(one)
    stack.addWidget(two)
    v.addWidget(stack)
    row = QHBoxLayout()
    go = QPushButton("Build")
    go.setObjectName("go")
    plain = QPushButton("Plain")
    row.addWidget(go)
    row.addWidget(plain)
    v.addLayout(row)
    cards = [QFrame() for _ in range(3)]
    for c in cards:
        c.setFixedSize(60, 30)
        row.addWidget(c)
    note = QLabel("Ready")
    v.addWidget(note)
    win.resize(700, 400)
    win.show()
    qa.processEvents()

    # ---- without a screen: nothing at all
    ok("no screen (the tests): the animations are off", not anim.on())
    anim.cover(stack)
    enter(go)
    anim.notice(note)
    anim.stagger(cards, win)
    ok("... and nothing is put into the window", not kids(win, "animshot") and not kids(win, "animglow")
       and note.graphicsEffect() is None and all(c.graphicsEffect() is None for c in cards) and not anim.busy())
    leave(go)

    os.environ["FL26_ANIM"] = "1"
    anim._system = None
    ok("FL26_ANIM=1: on", anim.on())

    # ---- a page
    anim.cover(stack)
    stack.setCurrentWidget(two)
    ok("a page: the picture of the old one lies over the new", len(over(stack)) == 1 and anim.busy())
    shot = over(stack)[0]
    c = seen(win, stack)
    ok("... over it on the screen too: the stack puts its next page on top of all that is in it (%s)" % c.name(),
       c.red() > 150 and c.blue() < 100 and shot.parentWidget() is win
       and shot.geometry() == QRect(stack.mapTo(win, QPoint(0, 0)), stack.size()))
    ok("... and takes no clicks", shot.testAttribute(Qt.WA_TransparentForMouseEvents)
       and win.childAt(stack.mapTo(win, QPoint(20, 20))) is not shot)
    ok("... it ends", wait())
    ok("... and is gone", not over(stack) and stack.currentWidget() is two and seen(win, stack).blue() > 150)
    anim.cover(stack)
    anim.cover(stack)
    ok("two changes in a row: one picture", len(over(stack)) == 1)
    ok("... ends", wait() and not over(stack))

    # ---- buttons
    before = go.grab().toImage().pixelColor(6, go.height() // 2).name()
    enter(go)
    ok("a coloured button under the pointer: its old look fades out over it", len(kids(go, "animshot")) == 1)
    ok("... with a light around it, a widget of the window", len(kids(win, "animglow")) == 1)
    ok("... the button itself is drawn through no effect", go.graphicsEffect() is None)
    glow = kids(win, "animglow")[0]
    ok("... the light lies around the button", glow.geometry().adjusted(7, 7, -7, -7) == go.geometry()
       and glow.testAttribute(Qt.WA_TransparentForMouseEvents))
    ok("... the fade ends", wait())
    ok("... the light stays while the pointer does", len(kids(win, "animglow")) == 1 and not kids(go, "animshot"))
    hot = go.grab().toImage().pixelColor(6, go.height() // 2).name()
    ok("... and the button shows its hover colour (%s -> %s)" % (before, hot), hot != before)
    leave(go)
    ok("the pointer leaves: it ends", wait())
    for _ in range(30):
        qa.processEvents()
        time.sleep(0.01)
    ok("... the light is gone", not kids(win, "animglow") and not kids(go, "animshot"))
    enter(plain)
    ok("a plain button: the fade, no light", len(kids(plain, "animshot")) == 1 and not kids(win, "animglow"))
    leave(plain)
    wait()
    enter(go)
    wait()
    go.hide()
    for _ in range(40):
        qa.processEvents()
        time.sleep(0.01)
    ok("a button that is hidden under the pointer takes its light with it", not kids(win, "animglow"))
    go.show()
    go.setEnabled(False)
    enter(go)
    ok("a disabled button: nothing", not kids(go, "animshot") and not kids(win, "animglow"))
    leave(go)
    go.setEnabled(True)

    # ---- a dialog
    d = QDialog(win)
    QVBoxLayout(d).addWidget(QLabel("really?"))
    d.show()
    ok("a dialog comes in from half there", 0.3 < d.windowOpacity() < 1.0)
    ok("... ends", wait())
    ok("... all there", d.windowOpacity() == 1.0)
    d.hide()
    d.show()
    ok("shown again: again", d.windowOpacity() < 1.0 and wait() and d.windowOpacity() == 1.0)
    d.close()

    # ---- the status line
    note.setIndent(3)
    note.setText("Done")
    anim.notice(note)
    ok("new words in the status line come in", note.graphicsEffect() is not None)
    ok("... ends", wait())
    ok("... the label as it was", note.graphicsEffect() is None and note.indent() == 3)
    anim.notice(note)
    ok("lines that follow fast just change", note.graphicsEffect() is None and not anim.busy())

    # ---- cards
    anim.stagger(cards, win)
    ok("cards: all start unseen", all(c.graphicsEffect() is not None for c in cards))
    cards[1].setParent(None)
    cards[1].deleteLater()
    ok("... one of them goes meanwhile: it ends all the same", wait())
    ok("... the others are as they were", cards[0].graphicsEffect() is None and cards[2].graphicsEffect() is None)

    d2, tw, area, menu = more(win, stack, one, two)

    # ---- off
    anim.cover(stack)
    enter(go)
    d2.show()
    d2.hide()
    turn(area.viewport(), -1)
    anim.line(win, go, plain, "#F5A524", "#0C1015")
    anim.set_on(False)
    for _ in range(30):
        qa.processEvents()
        time.sleep(0.01)
    ok("Settings > Animations off: what ran is ended at once", not anim.busy() and not over(stack)
       and not kids(go, "animshot") and not ghosts() and not kids(win, "animline") and d2.windowOpacity() == 1.0)
    leave(go)
    anim.cover(stack)
    anim.cover(stack, 1)
    d = QDialog(win)
    d.move(50, 60)
    d.show()
    at = d.pos()
    qa.processEvents()
    ok("... and nothing new starts", not anim.busy() and not over(stack) and d.windowOpacity() == 1.0)
    d.close()
    before = area.verticalScrollBar().value()
    tw.tabBarClicked.emit(0)
    anim.line(win, go, plain, "#F5A524", "#0C1015")
    turn(area.viewport(), -1)            # (before the menu: Qt gives no wheel to what is under an open menu)
    menu.popup(win.mapToGlobal(QPoint(20, 20)))
    ok("... no slide, no rise, no picture of a closed dialog, no line, no menu fade, the wheel as it ever was",
       not anim.busy() and d.pos() == at and not ghosts() and not kids(win, "animline") and not kids(win, "animshot")
       and menu.windowOpacity() == 1.0 and area.verticalScrollBar().value() != before)
    menu.hide()
    anim.set_on(True)
    anim.cover(stack)
    anim.finish_all()
    ok("finish_all: every animation at its end", not anim.busy())
    print("test_anim: %d ok" % N[0])


if __name__ == "__main__":
    main()
