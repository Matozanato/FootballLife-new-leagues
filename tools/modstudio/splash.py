"""The start of Mod Studio: the name drawn over the lines of a pitch, "by Matozanato" under it,
then the card grows into the window.

The drawing runs in a process of its own (the exe again, --splash): the window builds itself in
2-8 s on its one thread, and a drawing on that thread stopped there and jumped to its end (mato
10.11.: everything froze for a moment while the opening still ran). The two talk over a local
socket: the splash says when it has run its time; the window, built and shown unseen, sends a
picture of itself, the splash grows its card into it (mato 10.11.: from that small window gradually
into the big one) and the window comes in under it. No splash process (it did not start, or never
spoke): the window fades in alone. FL26_NO_SPLASH=1 leaves it all out, as --shot does."""
import math
import os
import sys
import time

from PySide6.QtCore import Qt, QObject, QPointF, QProcess, QRectF, QTimer, QVariantAnimation
from PySide6.QtGui import (QColor, QFont, QFontMetricsF, QGuiApplication, QLinearGradient, QPainter,
                           QPainterPath, QPen, QPixmap)
from PySide6.QtWidgets import QApplication, QWidget

from modstudio import VERSION, theme

W, H = 620, 340
RUN_MS = 3800            # start to end: the drawing, then the name held (mato 06.11.: 3-4 s,
                         # so everyone sees who made it)
DRAW = 0.62              # the share of RUN_MS the drawing takes; the rest holds it
GROW_MS = 560            # the card growing into the window
WAIT_MS = RUN_MS + 4000  # a splash that has not said it is done by then is not waited for


def wanted():
    return "--shot" not in sys.argv and not os.environ.get("FL26_NO_SPLASH")


def card_rect():
    """where the splash stands: the middle of the main screen (both processes work it out alike)"""
    x = y = 0
    scr = QApplication.primaryScreen()
    if scr is not None:
        g = scr.availableGeometry()
        x, y = g.center().x() - W // 2, g.center().y() - H // 2
    return QRectF(x, y, W, H)


def _phase(t, a, b):
    """0..1 of t between a and b, eased"""
    if t <= a:
        return 0.0
    if t >= b:
        return 1.0
    x = (t - a) / (b - a)
    return 1 - (1 - x) ** 3


class Splash(QWidget):
    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowTitle("Mod Studio starting")
        r = card_rect()
        self.setGeometry(int(r.x()), int(r.y()), W, H)
        f = theme.fonts()
        self.head = f["HEAD_STACK"].split(",")[0].strip('" ')
        self.sans = f["SANS_STACK"].split(",")[0].strip('" ')
        self.t = 0.0
        self.raw = 0.0
        self.anim = QVariantAnimation(self, startValue=0.0, endValue=1.0, duration=RUN_MS)
        self.anim.valueChanged.connect(self._tick)

    def _tick(self, v):
        self.raw = float(v)
        self.t = min(1.0, self.raw / DRAW)
        self.update()

    def picture(self):
        """the card as it stands at the end (cursor shown), for the window to grow"""
        self.t, self.raw = 1.0, 0.0
        scr = QGuiApplication.primaryScreen()
        dpr = scr.devicePixelRatio() if scr is not None else 1.0
        pm = QPixmap(int(math.ceil(W * dpr)), int(math.ceil(H * dpr)))
        pm.setDevicePixelRatio(dpr)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        self.draw(p)
        p.end()
        return pm

    def _font(self, family, px, weight=QFont.Normal, spacing=0.0):
        f = QFont(family)
        f.setPixelSize(px)
        f.setWeight(weight)
        if spacing:
            f.setLetterSpacing(QFont.AbsoluteSpacing, spacing)
        return f

    def paintEvent(self, _e):
        p = QPainter(self)
        self.draw(p)
        p.end()

    def draw(self, p):
        t = self.t
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)
        card = QRectF(8, 8, W - 16, H - 16)

        # the card: the window's ground, a fine border, a shadow under it
        a_in = _phase(t, 0.0, 0.18)
        p.setOpacity(a_in)
        for i in range(6):
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 22 - i * 3))
            p.drawRoundedRect(card.adjusted(-i, -i + 3, i, i + 3), 14 + i, 14 + i)
        p.setBrush(QColor(theme.BG))
        p.setPen(QPen(QColor(theme.BORDER), 1))
        p.drawRoundedRect(card, 14, 14)

        # the pitch: halfway line, centre circle and both boxes draw themselves in
        clip = QPainterPath()
        clip.addRoundedRect(card, 14, 14)
        p.setClipPath(clip)
        line = QColor(theme.ACCENT)
        line.setAlpha(46)
        pen = QPen(line, 1.6)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        cx, cy = card.center().x(), card.center().y()
        k = _phase(t, 0.05, 0.55)
        p.drawLine(QPointF(cx, cy - (cy - card.top()) * k), QPointF(cx, cy + (card.bottom() - cy) * k))
        r = 92
        p.drawArc(QRectF(cx - r, cy - r, 2 * r, 2 * r), 90 * 16, int(-360 * 16 * _phase(t, 0.12, 0.62)))
        bw, bh = 74, 190
        kb = _phase(t, 0.2, 0.7)
        for side in (-1, 1):
            x0 = card.left() if side < 0 else card.right()
            path = QPainterPath(QPointF(x0, cy - bh / 2))
            path.lineTo(x0 - side * bw, cy - bh / 2)
            path.lineTo(x0 - side * bw, cy + bh / 2)
            path.lineTo(x0, cy + bh / 2)
            p.drawPath(_part(path, kb))
        # a soft band behind the name, so the lines pass under it
        band = QLinearGradient(card.left(), 0, card.right(), 0)
        ground = QColor(theme.BG)
        clear = QColor(theme.BG)
        clear.setAlpha(0)
        band.setColorAt(0.16, clear)          # the boxes' inner lines stay whole
        band.setColorAt(0.3, ground)
        band.setColorAt(0.7, ground)
        band.setColorAt(0.84, clear)
        p.setPen(Qt.NoPen)
        p.setBrush(band)
        p.setOpacity(0.92 * _phase(t, 0.15, 0.4))
        p.drawRect(QRectF(card.left(), cy - 40, card.width(), 112))
        p.setClipping(False)

        # >_  FL // MOD STUDIO, letter by letter, sliding up into place
        title = "FL // MOD STUDIO"
        ft = self._font(self.head, 40, QFont.DemiBold, 1.5)
        fm = QFontMetricsF(ft)
        fmark = self._font(self.head, 40, QFont.DemiBold)
        mw = QFontMetricsF(fmark).horizontalAdvance(">_") + 18
        tw = sum(fm.horizontalAdvance(ch) + 1.5 for ch in title) - 1.5
        x = cx - (mw + tw) / 2
        base = cy + 8
        km = _phase(t, 0.18, 0.36)
        p.setOpacity(km)
        p.setFont(fmark)
        p.setPen(QColor(theme.ORANGE))
        blink = 1.0 if (t < 1.0 or int(self.raw * RUN_MS / 450) % 2 == 0) else 0.0
        p.drawText(QPointF(x, base + 10 * (1 - km)), ">")
        p.setOpacity(km * blink)
        p.drawText(QPointF(x + QFontMetricsF(fmark).horizontalAdvance(">"), base + 10 * (1 - km)), "_")
        p.setFont(ft)
        xx = x + mw
        n = len(title)
        for i, ch in enumerate(title):
            a = 0.26 + 0.34 * i / n
            ki = _phase(t, a, a + 0.16)
            if ki <= 0:
                break
            p.setOpacity(ki)
            p.setPen(QColor(theme.ORANGE) if ch == "/" else QColor(theme.TEXT))
            p.drawText(QPointF(xx, base + 14 * (1 - ki)), ch)
            xx += fm.horizontalAdvance(ch) + 1.5

        # the line under the name grows from the middle, then "by Matozanato" comes up
        kl = _phase(t, 0.55, 0.8)
        p.setOpacity(1.0)
        half = (mw + tw) / 2 * kl
        grad = QColor(theme.ORANGE)
        p.setPen(QPen(grad, 2.2, Qt.SolidLine, Qt.RoundCap))
        if half > 0:
            p.drawLine(QPointF(cx - half, base + 20), QPointF(cx + half, base + 20))
        kb2 = _phase(t, 0.66, 0.92)
        p.setOpacity(kb2)
        fb = self._font(self.sans, 17, QFont.Normal, 3.0)
        p.setFont(fb)
        p.setPen(QColor(theme.SUBTLE))
        by = "by Matozanato"
        bwid = QFontMetricsF(fb).horizontalAdvance(by)
        p.drawText(QPointF(cx - bwid / 2, base + 54 + 8 * (1 - kb2)), by)

        # the version, small, in the corner
        p.setOpacity(_phase(t, 0.7, 0.95) * 0.9)
        fv = self._font(self.sans, 12)
        p.setFont(fv)
        p.setPen(QColor(theme.DIM))
        vw = QFontMetricsF(fv).horizontalAdvance(VERSION)
        p.drawText(QPointF(card.right() - 18 - vw, card.bottom() - 16), VERSION)


def _part(path, k):
    """the first k (0..1) of a path, by length"""
    if k >= 1:
        return path
    out = QPainterPath()
    if k <= 0:
        return out
    total = path.length()
    want = total * k
    out.moveTo(path.pointAtPercent(0))
    steps = max(2, int(math.ceil(want / 2)))
    for i in range(1, steps + 1):
        out.lineTo(path.pointAtPercent(path.percentAtLength(want * i / steps)))
    return out


def alone(name):
    """--splash <name>: the splash process. Draws for RUN_MS and says "done" on the socket `name`;
    "grow <picture> <frame x y w h> <client l t r b>" grows the card into that picture, then says
    "grown"; "go" fades it out. Goes when the window is gone (a minute at most)"""
    from PySide6.QtNetwork import QLocalSocket
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv[:1])
    sp = Splash()
    sock = QLocalSocket(app)
    state = {"grow": None, "buf": b""}

    def say(text):
        if sock.state() == QLocalSocket.ConnectedState:
            sock.write(text.encode() + b"\n")
            sock.flush()

    def heard():
        state["buf"] += bytes(sock.readAll())
        while b"\n" in state["buf"]:
            line, state["buf"] = state["buf"].split(b"\n", 1)
            part = line.decode("utf-8", "replace").split("\t")
            if part[0] == "grow" and state["grow"] is None:
                shot = QPixmap(part[1])
                try:
                    os.remove(part[1])
                except OSError:
                    pass
                n = [float(x) for x in part[2:10]]
                state["grow"] = Grow(QRectF(*n[:4]), tuple(n[4:]), shot, sp, lambda: say("grown"))
            elif part[0] == "go":
                if state["grow"] is not None:
                    state["grow"].leave(app.quit)
                else:
                    app.quit()
    sp.anim.finished.connect(lambda: say("done"))
    sock.readyRead.connect(heard)
    sock.disconnected.connect(app.quit)
    sock.errorOccurred.connect(lambda *_a: app.quit())
    sock.connectToServer(name)
    QTimer.singleShot(60000, app.quit)
    sp.show()
    sp.anim.start()
    return app.exec()


class Start(QObject):
    """the window's side: starts the splash process; once the window is built and the splash has
    run its time, the splash grows its card into a picture of the window and the window comes in
    under it. The window's own thread only shows itself unseen and takes the picture: everything
    that moves is drawn by the splash process"""

    def __init__(self, parent=None):
        super().__init__(parent)
        from PySide6.QtNetwork import QLocalServer
        self.t0 = time.monotonic()
        self.sock = None
        self.buf = b""
        self.said_done = False
        self.window = None
        self.picture = None
        self.sent = False
        self.over = False
        self.proc = None
        self.name = "fl26-modstudio-splash-%d" % os.getpid()
        self.server = QLocalServer(self)
        QLocalServer.removeServer(self.name)
        self.server.newConnection.connect(self._conn)
        if not self.server.listen(self.name):
            return
        if getattr(sys, "frozen", False):
            prog, args = sys.executable, ["--splash", self.name]
        else:
            prog = sys.executable
            args = [os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                 "modstudio_main.py"), "--splash", self.name]
        self.proc = QProcess(self)
        self.proc.errorOccurred.connect(lambda *_a: self._gone())
        # a splash that ends without a word (it could not connect, it crashed): not waited for either
        self.proc.finished.connect(lambda *_a: self._gone())
        self.proc.start(prog, args)

    def _conn(self):
        self.sock = self.server.nextPendingConnection()
        self.sock.readyRead.connect(self._read)
        self.sock.disconnected.connect(self._gone)

    def _say(self, text):
        try:
            self.sock.write(text.encode() + b"\n")
            self.sock.flush()
        except Exception:
            pass

    def _read(self):
        self.buf += bytes(self.sock.readAll())
        while b"\n" in self.buf:
            line, self.buf = self.buf.split(b"\n", 1)
            if line == b"done":
                self.said_done = True
                self._go()
            elif line == b"grown":            # the card has the window's size, over it
                self._reveal(fade=False)
                self._say("go")

    def _gone(self):
        """the splash process did not start or went away: nothing to wait for"""
        self.proc = None
        self.sock = None
        self._go()
        if self.sent:
            self._reveal(fade=False)

    def finish(self, window):
        """`window` comes in once the splash has run its time, grown out of its card"""
        self.window = window
        # shown unseen now, while the splash still holds the name: its first paint is white on
        # Windows and takes a moment, and the picture for the card is taken from it
        window.setWindowOpacity(0.0)
        window.show()
        window.raise_()
        window.activateWindow()
        QTimer.singleShot(0, self._take)
        left = int(WAIT_MS - (time.monotonic() - self.t0) * 1000)
        QTimer.singleShot(max(0, left), lambda: self._go(late=True))

    def _take(self):
        import tempfile
        w = self.window
        QApplication.processEvents()
        try:
            fd, path = tempfile.mkstemp(prefix="fl26-start-", suffix=".bmp")
            os.close(fd)
            if not w.grab().toImage().save(path, "BMP"):
                raise OSError("not saved")
            self.picture = path
        except Exception:
            self.picture = ""
        self._go()

    def _go(self, late=False):
        """late: the wait is over (its timer says so; the clock is not asked again, a Windows timer
        fires up to a tick early and the window then stayed unseen for good)"""
        w = self.window
        if w is None or self.picture is None or self.sent or self.over:
            return
        alive = self.proc is not None and self.sock is not None
        late = late or (time.monotonic() - self.t0) * 1000 >= WAIT_MS
        if self.proc is not None and not self.said_done and not late:
            return                            # the splash still running its time
        if alive and self.said_done and self.picture:
            f, c = w.frameGeometry(), w.geometry()
            n = (f.x(), f.y(), f.width(), f.height(), c.left() - f.left(), c.top() - f.top(),
                 f.right() - c.right(), f.bottom() - c.bottom())
            self.sent = True
            self._say("\t".join(["grow", self.picture] + [str(x) for x in n]))
            QTimer.singleShot(GROW_MS + 3000, lambda: self._reveal(fade=False))
        else:
            self._reveal(fade=True)

    def _reveal(self, fade):
        if self.over:
            return
        self.over = True
        w = self.window
        if self.picture and not self.sent:
            try:
                os.remove(self.picture)
            except OSError:
                pass
        if self.sock is not None and not self.sent:
            self._say("go")
        elif self.proc is not None and not self.sent:
            self.proc.kill()                  # started, never spoke: not left over the window
        if not fade:
            w.setWindowOpacity(1.0)
            return
        self.fade = QVariantAnimation(self, startValue=0.0, endValue=1.0, duration=280)
        self.fade.valueChanged.connect(lambda v: w.setWindowOpacity(float(v)))
        self.fade.finished.connect(lambda: w.setWindowOpacity(1.0))
        self.fade.start()


def _ease(x):
    x = min(1.0, max(0.0, x))
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def _smooth(a, b, x):
    x = min(1.0, max(0.0, (x - a) / (b - a)))
    return x * x * (3 - 2 * x)


class Grow(QWidget):
    """in the splash process: the card grows into the window's frame, the window's picture showing
    through as it grows; then it waits over the window till that is in, and fades"""

    def __init__(self, to, inner, shot, splash, grown):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.k, self.out = 0.0, 1.0
        self.to, self.inner, self.shot, self.grown = to, inner, shot, grown
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setWindowTitle("Mod Studio starting")
        self.art = splash.picture()
        self.fro = card_rect().adjusted(8, 8, -8, -8)
        area = to.united(self.fro).adjusted(-8, -8, 8, 12)
        self.setGeometry(area.toAlignedRect())
        self.off = QRectF(self.geometry()).topLeft()
        self.show()
        self.raise_()
        QTimer.singleShot(30, splash.hide)
        self.anim = QVariantAnimation(self, startValue=0.0, endValue=1.0, duration=GROW_MS)
        self.anim.valueChanged.connect(self._tick)
        self.anim.finished.connect(self.grown)
        QTimer.singleShot(30, self.anim.start)

    def _tick(self, v):
        self.k = float(v)
        self.update()

    def leave(self, then):
        """the window is in under this: fade out, then `then`"""
        self.anim2 = QVariantAnimation(self, startValue=1.0, endValue=0.0, duration=160)
        self.anim2.valueChanged.connect(lambda v: (setattr(self, "out", float(v)), self.update()))
        self.anim2.finished.connect(then)
        self.anim2.start()

    def paintEvent(self, _e):
        k = self.k
        e = _ease(k)
        a, b = self.fro.translated(-self.off), self.to.translated(-self.off)
        r = QRectF(a.left() + (b.left() - a.left()) * e, a.top() + (b.top() - a.top()) * e,
                   a.width() + (b.width() - a.width()) * e, a.height() + (b.height() - a.height()) * e)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setOpacity(self.out)
        rad = 14 + (8 - 14) * e               # the card's corners into a Windows 11 window's
        p.setPen(Qt.NoPen)
        for i in range(5):                    # the card's shadow, as the splash has it
            p.setBrush(QColor(0, 0, 0, int((20 - i * 4) * (1 - e))))
            p.drawRoundedRect(r.adjusted(-i, -i + 3, i, i + 3), rad + i, rad + i)
        clip = QPainterPath()
        clip.addRoundedRect(r, rad, rad)
        p.setClipPath(clip)
        p.fillRect(r, QColor(theme.BG))
        # the window's picture in its place inside the frame, as the frame grows
        s = r.width() / b.width()
        le, to, ri, bo = self.inner
        p.setOpacity(self.out * _smooth(0.12, 0.7, k))
        p.drawPixmap(r.adjusted(le * s, to * s, -ri * s, -bo * s), self.shot, QRectF(self.shot.rect()))
        # the card on top, stretched with the frame, fading as the window shows through
        ka = 1.0 - _smooth(0.0, 0.5, k)
        if ka > 0:
            p.setOpacity(self.out * ka)
            sc = r.width() / a.width()
            p.drawPixmap(r.adjusted(-8 * sc, -8 * sc, 8 * sc, 8 * sc), self.art, QRectF(self.art.rect()))
        p.setClipping(False)
        p.setOpacity(self.out * (1.0 - e))
        p.setPen(QPen(QColor(theme.BORDER), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r, rad, rad)
        p.end()
