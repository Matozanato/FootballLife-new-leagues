"""Small animations (0.3.1, mato 10.11.: "da izgleda profesionalnije"): a page fades into the next,
a button's hover comes softly (a glow on the coloured ones), a dialog fades in, a new status line
slides in, the world cards come one after another. Settings > Animations turns them off.

More of them (beta 3, mato 11.11.: "premalo animacija ... mora to fluidnije sve biti"): a page or a
tab slides to the side it lies on while the next one slides in, a dialog rises into its place and
fades out when it closes, a menu and a combo box's list fade in, the wheel glides a page instead
of jumping it, the orange line under the open section travels to the next one.

Rules they all keep:
- nothing waits for an animation: the new page, the dialog, the button are there and answer at
  once; what moves is a picture of the old state fading out over them, or their opacity;
- an animation that cannot run (its widget is gone, the window stands still) leaves the end state:
  nothing stays half shown;
- none at all without a screen (the tests' offscreen platform) or in a remote desktop session.
  Windows' own switch (Settings > Accessibility > Visual effects > Animation effects) is not
  followed: many PCs for games have it off for speed, mato's too (11.11.), and theirs would be a
  Mod Studio without what its changelog shows. Settings > Animations is the switch.
"""
import os
import sys
import time

from PySide6.QtCore import (Property, QEasingCurve, QPoint, QPointF, QPropertyAnimation, QRect, QRectF, QTimer,
                            QVariantAnimation, Qt)
from PySide6.QtGui import QColor, QPainter, QPen, QRegion
from PySide6.QtWidgets import (QAbstractItemView, QAbstractScrollArea, QApplication, QGraphicsOpacityEffect,
                               QScrollArea, QWidget)

PAGE_MS, HOVER_MS, DIALOG_MS, NOTICE_MS, CARD_MS, CARD_STEP_MS = 150, 110, 130, 240, 170, 45
SLIDE_MS, SLIDE_PX, RISE_PX, LEAVE_MS, MENU_MS, SCROLL_MS, LINE_MS = 240, 34, 12, 130, 120, 210, 220
GLOW = {"go": "#3ECF8E", "primary": "#4AA3FF", "play": "#F5A524", "blue": "#4AA3FF"}

_on = True
_system = None
_running = []          # the animations alive, so finish_all() can end them
_waiting = []          # pictures on screen whose fade starts with their first paint


def set_on(on):
    global _on
    _on = bool(on)
    if not _on:
        finish_all()


def _system_ok():
    """once: is there a screen that shows animations as they are meant"""
    global _system
    if _system is None:
        app = QApplication.instance()
        ok = app is not None and app.platformName() != "offscreen"
        if os.environ.get("FL26_ANIM") == "1":            # a test of the animations themselves
            ok = app is not None
        elif ok and sys.platform == "win32":
            try:
                import ctypes
                if ctypes.windll.user32.GetSystemMetrics(0x1000):      # SM_REMOTESESSION
                    ok = False
            except Exception:
                pass
        _system = ok
    return _system


def on():
    return _on and _system_ok()


def busy():
    """how many animations run now (the UI tour waits for none before it takes a picture)"""
    _running[:] = [a for a in _running if _alive(a) and a.state() != a.State.Stopped]
    _waiting[:] = [s for s in _waiting if _alive(s)]
    return len(_running) + len(_waiting)


def finish_all():
    """every animation to its end state, now"""
    for a in list(_running):
        try:
            a.setCurrentTime(a.totalDuration())
            a.stop()
            a.finished.emit()
        except RuntimeError:
            pass
    _running[:] = []
    for s in list(_waiting):
        try:
            s._over()
        except RuntimeError:
            pass
    _waiting[:] = []


def _alive(obj):
    try:
        from shiboken6 import isValid
        return isValid(obj)
    except Exception:
        return True


def _start(a):
    _running.append(a)
    a.finished.connect(lambda: a in _running and _running.remove(a))
    a.start()
    return a


def _safe(fn):
    """fn for a signal: a widget that went away meanwhile is nothing to tell anybody"""
    def call(*args):
        try:
            return fn(*args)
        except RuntimeError:
            return None
    return call


def _ground(w):
    """the colour behind w's words: the first one up from w that hides what is under it. A page
    dressed by the style sheet answers "none" (black, see-through) for its own; a slide painted
    on that painted on nothing, and the next page was read through both of its pictures"""
    try:
        at = w
        while at is not None:
            c = at.palette().window().color()
            if c.alpha() == 255:
                return QColor(c)
            at = at.parentWidget()
        c = QApplication.instance().palette().window().color()
        return QColor(c.red(), c.green(), c.blue())
    except Exception:
        return QColor(0, 0, 0)


class _Shot(QWidget):
    """a picture of how a widget looked, over the widget as it is now, fading out. It takes no
    clicks: what is under it answers from the first moment"""

    def __init__(self, parent, picture, way=0, area=None):
        super().__init__(parent)
        self._picture, self._o, self._armed = picture, 1.0, 0
        # way: -1 / 1, the side the next page lies on. Then the old picture slides away from it and
        # a picture of the next page slides in from it (taken once that page has painted itself)
        self._way, self._next, self._quiet = way, None, False
        # area: the widget this picture lies over when it is not its child but a child of the
        # window (cover()). A stack of pages puts the page it shows next on top of everything else
        # in it, a picture of the old page included: until beta 3 the picture was the stack's
        # child, lay under the new page from the first moment and nobody ever saw a page fade
        self._area = area
        self._ground = _ground(area or parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.NoFocus)
        self.setObjectName("animshot")
        self.setGeometry(parent.rect() if area is None else QRect(area.mapTo(parent, QPoint(0, 0)), area.size()))
        self.raise_()
        self.show()

    def _get(self):
        return self._o

    def _set(self, o):
        self._o = o
        self.update()

    o = Property(float, _get, _set)

    def paintEvent(self, _event):
        if self._quiet:                # the page under this one is being drawn into a picture
            return
        if self._area is not None and not (_alive(self._area) and self._area.isVisible()):
            QTimer.singleShot(0, _safe(self._over))        # what it lay over is gone: so is this
            return
        p = QPainter(self)
        if self._next is None:
            p.setOpacity(self._o)
            p.drawPixmap(0, 0, self._picture)
        else:
            # the old page goes first and fast, the next comes behind it and slows into its place.
            # The old one is gone in the first third and the next starts as it goes: the words of
            # the two are never read through each other (they were, on the first try: mud)
            t = 1.0 - self._o
            e = 1.0 - (1.0 - t) ** 3
            p.fillRect(self.rect(), self._ground)
            go = max(0.0, 1.0 - t / 0.34)
            if go > 0.0:
                p.setOpacity(go * go)
                p.drawPixmap(QPointF(-self._way * SLIDE_PX * 0.6 * e, 0.0), self._picture)
            come = min(1.0, max(0.0, (t - 0.26) / 0.56))
            if come > 0.0:
                p.setOpacity(come)
                p.drawPixmap(QPointF(self._way * SLIDE_PX * (1.0 - e), 0.0), self._next)
        p.end()
        if self._armed:
            ms, self._armed = self._armed, 0
            QTimer.singleShot(0, _safe(lambda: self._go(ms)))

    def arm(self, ms):
        """fade from the first time this picture is painted: the page under it may take the
        window a moment to build and to paint, and a fade timed from before that would be over
        before anybody saw it"""
        self._armed = ms
        _waiting.append(self)
        QTimer.singleShot(600, _safe(self._late))
        self.update()

    def _go(self, ms):
        if self in _waiting:
            _waiting.remove(self)
            if self._way:
                try:
                    self._quiet = True
                    self._next = (self._area if self._area is not None else self.parentWidget()).grab()
                except Exception:
                    self._next = None
                finally:
                    self._quiet = False
            self.fade(ms)

    def _late(self):
        if self in _waiting:               # never painted (the window is hidden, minimised)
            self._over()

    def fade(self, ms):
        a = QPropertyAnimation(self, b"o", self)
        a.setDuration(ms)
        a.setStartValue(1.0)
        a.setEndValue(0.0)
        # (a slide eases its own way in paintEvent)
        a.setEasingCurve(QEasingCurve.Linear if self._next is not None else QEasingCurve.OutCubic)
        a.finished.connect(_safe(self._over))
        return _start(a)

    def _over(self):
        if self in _waiting:
            _waiting.remove(self)
        self.hide()
        self.deleteLater()


def _drop_shot(owner):
    shot = owner.__dict__.pop("_anim_shot", None) if hasattr(owner, "__dict__") else None
    if shot is not None and _alive(shot):
        try:
            shot.hide()
            shot.deleteLater()
        except RuntimeError:
            pass


# ---- 1. pages -------------------------------------------------------------------------------
def cover(area, way=0):
    """call just before `area` shows something else (another page, another tab): a picture of what
    it shows now stays over it and fades out. way 1 / -1: the next one lies to the right / left of
    this one (a later tab, an earlier section): the old slides out to the other side while the
    next slides in"""
    if not on() or not area.isVisible() or area.width() < 8 or area.height() < 8:
        return
    try:
        _drop_shot(area)
        host = area.window()
        shot = _Shot(area, area.grab(), way) if host is area else _Shot(host, area.grab(), way, area)
        area._anim_shot = shot
        shot.arm(SLIDE_MS if way else PAGE_MS)
    except Exception:
        pass


def tabs(tw):
    """a tab widget, the first time it is shown: from now a click on another tab slides its pages.
    (The sections' own tabs do it in app.py: their pages are in the history too.)"""
    if tw.property("_anim_tabs") or tw.objectName() == "sectiontabs":
        return
    tw.setProperty("_anim_tabs", True)

    def clicked(i):
        at = tw.currentIndex()
        if 0 <= i != at and tw.isTabEnabled(i) and tw.currentWidget() is not None:
            cover(tw.currentWidget().parentWidget(), 1 if i > at else -1)
    tw.tabBarClicked.connect(_safe(clicked))


class _Line(QWidget):
    """the line under the open section on its way from one button to the next. It lies over the
    strip where both buttons draw theirs, so the one already drawn under the next button is not
    seen before this one gets there"""

    def __init__(self, bar, old, new, colour, ground):
        super().__init__(bar)
        self._old = QRect(old.mapTo(bar, QPoint(0, 0)), old.size())
        self._new, self._bar, self._colour, self._ground, self._t = new, bar, QColor(colour), QColor(ground), 0.0
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.NoFocus)
        self.setObjectName("animline")
        self.setGeometry(bar.rect())
        self.raise_()
        self.show()

    def _get(self):
        return self._t

    def _set(self, t):
        self._t = t
        self.update()

    t = Property(float, _get, _set)

    def paintEvent(self, _event):
        if not _alive(self._new):
            return
        a, t = self._old, self._t
        b = QRect(self._new.mapTo(self._bar, QPoint(0, 0)), self._new.size())     # (its words may just have changed)
        y, h = b.bottom() - 1, 2
        p = QPainter(self)
        p.fillRect(QRect(QPoint(min(a.left(), b.left()), y), QPoint(max(a.right(), b.right()), y + h - 1)), self._ground)
        # the end that leads runs ahead, the other follows: the line stretches on its way
        lead, tail = 1.0 - (1.0 - t) ** 3, t * t * (3.0 - 2.0 * t)
        right = b.left() > a.left()
        x0 = a.left() + (b.left() - a.left()) * (tail if right else lead)
        x1 = a.right() + (b.right() - a.right()) * (lead if right else tail)
        p.fillRect(QRectF(x0, y, max(2.0, x1 - x0 + 1.0), h), self._colour)
        p.end()


def line(bar, old, new, colour, ground):
    """the checked section button changed from old to new, both in `bar`: the line under the old
    one travels to the new one"""
    if (not on() or bar is None or old is None or new is None or old is new or not bar.isVisible()
            or not old.isVisible() or not new.isVisible() or not bar.isAncestorOf(old) or not bar.isAncestorOf(new)):
        return
    try:
        was = bar.__dict__.pop("_anim_line", None)
        if was is not None and _alive(was):
            was.hide()
            was.deleteLater()
        w = bar._anim_line = _Line(bar, old, new, colour, ground)
        a = QPropertyAnimation(w, b"t", w)
        a.setDuration(LINE_MS)
        a.setStartValue(0.0)
        a.setEndValue(1.0)

        def over():
            w.hide()
            w.deleteLater()
        a.finished.connect(_safe(over))
        _start(a)
    except Exception:
        pass


# ---- 2. buttons -----------------------------------------------------------------------------
def _in_effect(w):
    """is w, or a widget it sits in, drawn through an effect already (two do not go together)"""
    for _ in range(8):
        if w is None:
            return False
        if w.graphicsEffect() is not None:
            return True
        w = w.parentWidget()
    return False


def hover(button, entered):
    """called before the button itself hears that the pointer came or went: a picture of how it
    looks now fades out over how it looks after. The coloured ones (Build, Activate, Start the
    game) glow while the pointer is on them"""
    if not on() or not button.isEnabled() or not button.isVisible():
        return
    if button.width() * button.height() > 120000 or _in_effect(button):
        return
    try:
        _drop_shot(button)
        shot = _Shot(button, button.grab())
        button._anim_shot = shot
        shot.fade(HOVER_MS)
        colour = GLOW.get(button.objectName())
        if colour:
            glow = button.__dict__.get("_anim_glow")
            if glow is not None and not _alive(glow):
                glow = None
            if entered and glow is None:
                button._anim_glow = glow = _Glow(button, colour)
            if glow is not None:
                glow.turn(entered)
    except RuntimeError:
        pass


class _Glow(QWidget):
    """a soft light around a button, drawn by a widget of the window that lies over it and paints
    only outside the button. Not an effect on the button: through an effect its words are drawn
    without the screen's sub-pixel smoothing and change their look while the pointer is on them.
    It looks every 80 ms whether the button is still there, where it was, with the pointer on it
    (a list scrolled by the wheel moves a button without telling anybody) and goes when not"""
    SPREAD = 7

    def __init__(self, button, colour):
        super().__init__(button.window())
        self.button, self.colour, self._o, self._anim = button, QColor(colour), 0.0, None
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.NoFocus)
        self.setObjectName("animglow")
        self._at = self._place()
        self.raise_()
        self.show()
        self._watch = QTimer(self, interval=80, timeout=_safe(self._look))
        self._watch.start()

    def _spot(self):
        b = self.button
        return (b.mapTo(b.window(), QPoint(0, 0)), b.size())

    def _place(self):
        at = self._spot()
        s = self.SPREAD
        self.setGeometry(QRect(at[0], at[1]).adjusted(-s, -s, s, s))
        # what a list the button sits in does not show of it, the light does not show either
        clip, w = QRect(QPoint(0, 0), self.button.window().size()), self.button.parentWidget()
        while w is not None and not w.isWindow():
            up = w.parentWidget()
            if isinstance(up, QAbstractScrollArea) and up.viewport() is w:
                clip = clip.intersected(QRect(w.mapTo(w.window(), QPoint(0, 0)), w.size()))
            w = up
        self._clip = clip.translated(-self.geometry().topLeft())
        return at

    def _look(self):
        b = self.button
        if not _alive(b) or not b.isVisible() or not b.isEnabled() or b.window() is not self.parentWidget()                 or self._spot() != self._at:
            return self._gone()
        if not b.underMouse() and (self._anim is None or self._anim.state() == self._anim.State.Stopped):
            self._gone()

    def _gone(self):
        self._watch.stop()
        if self._anim is not None and _alive(self._anim):
            self._anim.stop()
        if _alive(self.button) and self.button.__dict__.get("_anim_glow") is self:
            del self.button.__dict__["_anim_glow"]
        self.hide()
        self.deleteLater()

    def _get(self):
        return self._o

    def _set(self, o):
        self._o = o
        self.update()

    o = Property(float, _get, _set)

    def turn(self, up):
        if self._anim is not None and _alive(self._anim):
            self._anim.stop()
        a = self._anim = QPropertyAnimation(self, b"o", self)
        a.setDuration(HOVER_MS + 50)
        a.setStartValue(self._o)
        a.setEndValue(1.0 if up else 0.0)
        a.setEasingCurve(QEasingCurve.OutCubic)
        if not up:
            a.finished.connect(_safe(lambda: self._o <= 0.01 and self._gone()))
        _start(a)

    def paintEvent(self, _event):
        s = self.SPREAD
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        inner = self.rect().adjusted(s, s, -s, -s)
        p.setClipRegion(QRegion(self.rect().intersected(self._clip)) - QRegion(inner))
        p.setBrush(Qt.NoBrush)
        for k in range(1, s + 1):
            c = QColor(self.colour)
            c.setAlphaF(0.42 * self._o * (1.0 - (k - 1) / float(s)) ** 2)
            p.setPen(QPen(c, 1.0))
            p.drawRoundedRect(QRectF(inner).adjusted(-k + 0.5, -k + 0.5, k - 0.5, k - 0.5), k, k)
        p.end()


# ---- 3. dialogs and the status line ------------------------------------------------------------
def dialog(d, rise=True):
    """a dialog about to be shown comes in softly, rising a little into its place. From half
    there, not from nothing: one shown just before a long piece of work in the window's own thread
    is readable all the same (and stands where it belongs: the rise starts with the next turn of
    the event loop, when the dialog has been put where it goes)"""
    if not on() or not d.isWindow() or d.property("_anim_on"):
        return
    try:
        d.setProperty("_anim_on", True)
        d.setProperty("_anim_seen", True)
        d.setWindowOpacity(0.45)
        a = QPropertyAnimation(d, b"windowOpacity", d)
        a.setDuration(DIALOG_MS + 40)
        a.setStartValue(0.45)
        a.setEndValue(1.0)
        a.setEasingCurve(QEasingCurve.OutCubic)
        def over():
            d.setWindowOpacity(1.0)
            d.setProperty("_anim_on", False)
        a.finished.connect(_safe(over))
        _start(a)
        if rise:
            QTimer.singleShot(0, _safe(lambda: _rise(d)))
    except RuntimeError:
        pass


def _rise(d):
    if not on() or not d.isVisible() or d.isMaximized() or d.isFullScreen():
        return
    home = d.pos()
    m = QVariantAnimation(d)
    m.setDuration(DIALOG_MS + 40)
    m.setStartValue(float(RISE_PX))
    m.setEndValue(0.0)
    m.setEasingCurve(QEasingCurve.OutCubic)
    state = {"at": home + QPoint(0, RISE_PX)}

    def step(v):
        if d.pos() != state["at"]:           # somebody else moved it meanwhile: it is theirs now
            return
        state["at"] = QPoint(home.x(), home.y() + int(round(v)))
        d.move(state["at"])
    d.move(state["at"])
    m.valueChanged.connect(_safe(step))
    m.finished.connect(_safe(lambda: step(0.0)))
    _start(m)


def popup(w):
    """a menu or the list of a combo box about to be shown: it fades in where it is"""
    if not on() or not w.isWindow() or w.property("_anim_on"):
        return
    try:
        w.setProperty("_anim_on", True)
        w.setWindowOpacity(0.3)
        a = QPropertyAnimation(w, b"windowOpacity", w)
        a.setDuration(MENU_MS)
        a.setStartValue(0.3)
        a.setEndValue(1.0)
        a.setEasingCurve(QEasingCurve.OutCubic)
        def over():
            w.setWindowOpacity(1.0)
            w.setProperty("_anim_on", False)
        a.finished.connect(_safe(over))
        _start(a)
    except RuntimeError:
        pass


_GHOST_MARK = "fl26_anim_ghost"
_user32 = None


def _win():
    """user32 with the handful of calls the picture of a closed dialog needs, or None (not Windows,
    no screen)"""
    global _user32
    if _user32 is None:
        _user32 = False
        try:
            import sys
            if sys.platform == "win32" and QApplication.platformName() == "windows":
                import ctypes
                from ctypes import wintypes
                u = ctypes.WinDLL("user32")
                u.IsWindow.argtypes = [wintypes.HWND]
                u.IsWindow.restype = wintypes.BOOL
                u.SetPropW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.HANDLE]
                u.SetPropW.restype = wintypes.BOOL
                u.GetPropW.argtypes = [wintypes.HWND, wintypes.LPCWSTR]
                u.GetPropW.restype = wintypes.HANDLE
                u.RemovePropW.argtypes = [wintypes.HWND, wintypes.LPCWSTR]
                u.RemovePropW.restype = wintypes.HANDLE
                u.SetLayeredWindowAttributes.argtypes = [wintypes.HWND, wintypes.DWORD, wintypes.BYTE, wintypes.DWORD]
                u.SetLayeredWindowAttributes.restype = wintypes.BOOL
                _user32 = u
        except Exception:
            _user32 = False
    return _user32 or None


def _fade_native(w, ms, start):
    """Windows: the picture of a closed dialog is faded from a thread of its own as well. What the
    dialog was closed for often starts at once in the window's own thread (a world put in the
    game, a Build): the picture would stand there half faded until that is over and look like a
    dialog that hangs. The thread only sets how much of the window is seen, which Windows takes
    from any thread, and only of a window that still carries our mark"""
    u = _win()
    if u is None:
        return
    try:
        import threading
        hwnd = int(w.winId())
        if not hwnd or not u.SetPropW(hwnd, _GHOST_MARK, 1):
            return

        def ours():
            return bool(u.IsWindow(hwnd)) and bool(u.GetPropW(hwnd, _GHOST_MARK))

        def run():
            t0 = time.perf_counter()
            while True:
                t = (time.perf_counter() - t0) * 1000.0 / ms
                if t >= 1.0 or not ours():
                    break
                u.SetLayeredWindowAttributes(hwnd, 0, int(255 * start * (1.0 - t) ** 3), 2)
                time.sleep(0.012)
            if ours():
                u.SetLayeredWindowAttributes(hwnd, 0, 0, 2)
        threading.Thread(target=run, name="anim-ghost", daemon=True).start()
    except Exception:
        pass


def _unmark(w):
    u = _win()
    if u is not None:
        try:
            u.RemovePropW(int(w.winId()), _GHOST_MARK)
        except Exception:
            pass


class _Ghost(QWidget):
    """a picture of a dialog that has just closed, where it stood, fading out. A window of its
    own that takes no clicks and no focus: the dialog is gone and has answered already"""

    def __init__(self, picture, rect, over):
        super().__init__(over, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowDoesNotAcceptFocus
                         | Qt.WindowTransparentForInput | Qt.NoDropShadowWindowHint)
        self._picture = picture
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setFocusPolicy(Qt.NoFocus)
        self.setObjectName("animghost")
        self.setGeometry(rect)
        self.setWindowOpacity(0.8)
        self.show()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.drawPixmap(0, 0, self._picture)
        p.end()


def leave(d):
    """a dialog that was shown through dialog() has just been hidden: a picture of it fades out
    in its place and sinks a little"""
    if not d.property("_anim_seen"):
        return
    d.setProperty("_anim_seen", False)
    app = QApplication.instance()
    if not on() or app is None or app.closingDown() or not d.isWindow() or d.width() < 60 or d.height() < 40:
        return
    try:
        over = d.parentWidget().window() if d.parentWidget() is not None else None
        if over is not None and (not over.isVisible() or over.isMinimized()):
            return
        home = d.geometry()
        g = _Ghost(d.grab(), home, over)
        a = QVariantAnimation(g)
        a.setDuration(LEAVE_MS)
        a.setStartValue(0.0)
        a.setEndValue(1.0)
        a.setEasingCurve(QEasingCurve.OutCubic)

        def step(t):
            g.setWindowOpacity(0.8 * (1.0 - t))
            g.move(home.x(), home.y() + int(round(RISE_PX * 0.7 * t)))

        def over_():
            _unmark(g)
            g.hide()
            g.deleteLater()
        a.valueChanged.connect(_safe(step))
        a.finished.connect(_safe(over_))
        _fade_native(g, LEAVE_MS, 0.8)
        _start(a)
    except Exception:
        pass


def wheel(view, ev):
    """a turn of the mouse wheel over a list that is counted in pixels (a page; a table that goes
    row by row is left to itself): the list glides to where the turn takes it. True: taken, the
    event goes no further. A touchpad sends its own small steps and is left alone, and at the end
    of the list the turn goes on to whatever holds it, as ever"""
    if not on():
        return False
    try:
        area = view.parentWidget()
        if not isinstance(area, QAbstractScrollArea) or area.viewport() is not view:
            return False
        if isinstance(area, QAbstractItemView):
            if area.verticalScrollMode() != QAbstractItemView.ScrollPerPixel:
                return False
        elif not isinstance(area, QScrollArea):
            return False
        d = ev.angleDelta()
        if (not d.y() or d.x() or not ev.pixelDelta().isNull() or ev.phase() != Qt.NoScrollPhase
                or ev.modifiers() != Qt.NoModifier):
            return False
        bar = area.verticalScrollBar()
        if bar.maximum() <= bar.minimum() or bar.isSliderDown() or not bar.isEnabled():
            return False
        a = bar.findChild(QPropertyAnimation, "animscroll")
        running = a is not None and a.state() == a.State.Running
        at = bar.property("_anim_to") if running else bar.value()
        to = int(round(at - d.y() / 120.0 * QApplication.wheelScrollLines() * bar.singleStep()))
        to = max(bar.minimum(), min(bar.maximum(), to))
        if to == bar.value() and not running:
            return False
        if a is None:
            a = QPropertyAnimation(bar, b"value", bar)
            a.setObjectName("animscroll")
            a.setEasingCurve(QEasingCurve.OutCubic)
        a.stop()
        a.setDuration(SCROLL_MS)
        a.setStartValue(bar.value())
        a.setEndValue(to)
        bar.setProperty("_anim_to", to)
        if a not in _running:
            _running.append(a)
        a.start()
        ev.accept()
        return True
    except Exception:
        return False


def notice(label):
    """a label that just got new words (the status line): they slide in from the right a little
    and come up from pale"""
    if not on() or not label.isVisible() or _in_effect(label):
        return
    now = time.monotonic()
    if now - (label.property("_anim_at") or 0.0) < 1.5:      # lines that follow each other fast
        label.setProperty("_anim_at", now)                    # (a build's progress) just change
        return
    label.setProperty("_anim_at", now)
    try:
        eff = QGraphicsOpacityEffect(label)
        eff.setOpacity(0.2)
        label.setGraphicsEffect(eff)
        was = label.indent()
        a = QVariantAnimation(label)
        a.setDuration(NOTICE_MS)
        a.setStartValue(0.0)
        a.setEndValue(1.0)
        a.setEasingCurve(QEasingCurve.OutCubic)

        def step(t):
            eff.setOpacity(min(0.99, 0.2 + 0.8 * t))       # (never 1.0 under an effect: see stagger)
            label.setIndent(int(round(14 * (1.0 - t))))

        def over():
            label.setIndent(was)
            if label.graphicsEffect() is eff:
                label.setGraphicsEffect(None)
        a.valueChanged.connect(_safe(step))
        a.finished.connect(_safe(over))
        _start(a)
    except RuntimeError:
        pass


# ---- 4. cards ---------------------------------------------------------------------------------
def stagger(widgets, owner):
    """the widgets (world cards) come up one after another. owner: a widget that outlives them"""
    widgets = [w for w in widgets if _alive(w)][:12]
    if not on() or not widgets or not owner.isVisible() or any(_in_effect(w) for w in widgets):
        return
    try:
        effects = []
        for w in widgets:
            eff = QGraphicsOpacityEffect(w)
            eff.setOpacity(0.0)
            w.setGraphicsEffect(eff)
            effects.append((w, eff))
        total = CARD_MS + CARD_STEP_MS * (len(widgets) - 1)
        a = QVariantAnimation(owner)
        a.setDuration(total)
        a.setStartValue(0.0)
        a.setEndValue(1.0)

        def step(t):
            for i, (w, eff) in enumerate(effects):
                if eff is None or not _alive(w) or not _alive(eff):
                    continue
                o = (t * total - i * CARD_STEP_MS) / CARD_MS
                if o < 1.0:
                    eff.setOpacity(max(0.0, o))
                else:
                    # all there: without the effect from here on. (A card left under an effect of
                    # opacity 1.0 was not painted at all until the last card was in: the first
                    # card came up and went away again, the film of 11.11.)
                    effects[i] = (w, None)
                    if w.graphicsEffect() is eff:
                        w.setGraphicsEffect(None)

        def over():
            for w, eff in effects:
                if eff is not None and _alive(w) and w.graphicsEffect() is eff:
                    w.setGraphicsEffect(None)
        a.valueChanged.connect(_safe(step))
        a.finished.connect(_safe(over))
        _start(a)
    except RuntimeError:
        pass
