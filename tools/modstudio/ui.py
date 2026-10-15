"""small building blocks every page uses: headers, banners, cards, a background runner"""
import traceback
from PySide6.QtCore import Qt, QObject, QPoint, QRect, QRunnable, QSize, QThreadPool, Signal
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QMessageBox, QPushButton,
                               QVBoxLayout, QWidget, QSizePolicy, QFileDialog, QToolButton, QLayout)
from .i18n import _
from . import theme


class FlowLayout(QLayout):
    """widgets in a row that goes on in the next line when the window is too narrow for them all
    (0.2.4: a page with many buttons ran out of the window at 1280 px)"""

    def __init__(self, parent=None, spacing=6):
        super().__init__(parent)
        self._items = []
        self._gap = spacing
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, i):
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i):
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientations(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, w):
        return self._place(QRect(0, 0, w, 0), False)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._place(rect, True)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for it in self._items:
            size = size.expandedTo(it.minimumSize())
        m = self.contentsMargins()
        return size + QSize(m.left() + m.right(), m.top() + m.bottom())

    def _place(self, rect, move):
        m = self.contentsMargins()
        r = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x, y, line = r.x(), r.y(), 0
        for it in self._items:
            if it.widget() is not None and it.widget().isHidden():
                continue
            hint = it.sizeHint()
            if x + hint.width() > r.right() + 1 and line > 0:
                x, y, line = r.x(), y + line + self._gap, 0
            if move:
                it.setGeometry(QRect(QPoint(x, y), hint))
            x += hint.width() + self._gap
            line = max(line, hint.height())
        return y + line - rect.y() + m.bottom()


class Stat(QFrame):
    """one state box of the top bar: a small caption, a value in its colour (state ok / err /
    info), the full text in its tip; a click opens the page where it is put right"""

    def __init__(self, caption, open_=None):
        super().__init__()
        self.setObjectName("stat")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.open_ = open_
        if open_:
            self.setCursor(Qt.PointingHandCursor)
        v = QVBoxLayout(self)
        v.setContentsMargins(10, 3, 10, 4)
        v.setSpacing(1)
        self.cap = QLabel(caption)
        self.cap.setObjectName("statcap")
        theme.caps(self.cap)
        self.val = QLabel("")
        self.val.setObjectName("statval")
        self.val.setMinimumWidth(40)
        self.val.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        v.addWidget(self.cap)
        v.addWidget(self.val)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumWidth(70)
        self._full = ""

    def set(self, text, state="", tip=""):
        self._full = text or ""
        self.val.setProperty("state", state)
        self.setProperty("state", state)
        self.setToolTip(tip or text or "")
        theme.repolish(self.val)
        theme.repolish(self)
        self._elide()

    def text(self):
        return self._full

    def _elide(self):
        w = max(30, self.val.width())
        self.val.setText(self.val.fontMetrics().elidedText(self._full, Qt.ElideMiddle, w))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._elide()

    def mouseReleaseEvent(self, e):
        if self.open_ and e.button() == Qt.LeftButton:
            self.open_()


class Page(QWidget):
    """one section of the window.  title/hint/help are English (translated when shown); help
    puts a "?" next to the title that says what the page is for"""
    title = ""
    hint = ""
    help = ""

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setObjectName("page")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(18, 14, 18, 12)
        self.outer.setSpacing(10)
        head = QHBoxLayout()
        t = QLabel(_(self.title))
        t.setObjectName("pagetitle")
        theme.caps(t)
        head.addWidget(t)
        if self.help:
            head.addWidget(helpmark(self.help, self.title))
        head.addStretch(1)
        self.actions = head
        self.outer.addLayout(head)
        if self.hint:
            h = QLabel(_(self.hint))
            h.setObjectName("hint")
            h.setWordWrap(True)
            self.outer.addWidget(h)
        self.banner = QLabel()
        self.banner.setWordWrap(True)
        self.banner.hide()
        self.banner.linkActivated.connect(self.banner_link)
        self.outer.addWidget(self.banner)

    def action(self, text, slot, kind=None, tip=None):
        b = QPushButton(_(text))
        if kind:
            b.setObjectName(kind)
        if tip:
            b.setToolTip(_(tip))
        b.clicked.connect(slot)
        self.actions.addWidget(b)
        return b

    def more(self, items):
        """0.2.4: the page's other buttons in one "More" menu next to its main ones;
        items = [(English text, slot, tip or None) or None for a separator]"""
        from PySide6.QtWidgets import QMenu
        t = QToolButton()
        t.setText(_("More") + "  \u25be")
        t.setPopupMode(QToolButton.InstantPopup)
        m = QMenu(t)
        m.setToolTipsVisible(True)
        t.acts = []                # the menu's actions in order (setEnabled works on them as on a button)
        for it in items:
            if it is None:
                m.addSeparator()
                continue
            text, slot, tip = (tuple(it) + (None,))[:3]
            act = m.addAction(_(text))
            if tip:
                act.setToolTip(_(tip))
            act.triggered.connect(lambda _c=False, f=slot: f())
            t.acts.append(act)
        t.setMenu(m)
        self.actions.addWidget(t)
        return t

    def say(self, text, kind="warn"):
        """a banner under the title: kind warn / err / ok; empty text hides it"""
        if not text:
            self.banner.hide()
            return
        self.banner.setObjectName("banner_" + kind)
        self.banner.setText(text)
        self.banner.style().unpolish(self.banner)
        self.banner.style().polish(self.banner)
        self.banner.show()

    def banner_link(self, href):
        """a link in the banner: page:<name> opens that page; a page answers its own links"""
        if href.startswith("page:"):
            self.app.open_page(href[5:])

    def refresh(self):
        pass

    def shown(self):
        """called each time the page is opened"""
        self.refresh()


class HelpMark(QToolButton):
    """a small "?" next to a control, a dialog or a page: the pointer on it shows what the thing
    is for, a click shows the same text in a box (a tooltip is easy to miss, and some people
    never hover)"""

    def __init__(self, text, title=None):
        super().__init__()
        self.setText("?")
        self.setObjectName("helpmark")
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setToolTip("<p style='white-space:pre-wrap'>%s</p>" % text.replace("&", "&amp;").replace("<", "&lt;"))
        self.help_text, self.help_title = text, title
        self.clicked.connect(self.explain)

    def explain(self):
        QMessageBox.information(self.window(), _(self.help_title) if self.help_title else _("What is this?"),
                                self.help_text)


def helpmark(text, title=None):
    """the "?" for one English text (translated here)"""
    return HelpMark(_(text), title)


def helped(widget, text, title=None):
    """widget and its "?" side by side, for a form row or a layout"""
    return row(widget, helpmark(text, title))


class Fold(QWidget):
    """a "More options" line that opens what is behind it (0.2.4: every page shows its one main
    thing; everything else is still there, one click away). fold.body is the layout to fill;
    key: the open/closed state is kept per window in app.settings["folds"]"""

    def __init__(self, text, app=None, key=None, open_=False):
        super().__init__()
        self.app, self.key, self.text = app, key, _(text)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        self.head = QPushButton()
        self.head.setObjectName("fold")
        self.head.setCursor(Qt.PointingHandCursor)
        self.head.clicked.connect(lambda: self.set_open(not self.inner.isVisible(), True))
        v.addWidget(self.head)
        self.inner = QFrame()
        self.inner.setObjectName("foldbody")
        self.body = QVBoxLayout(self.inner)
        self.body.setContentsMargins(12, 8, 12, 10)
        self.body.setSpacing(8)
        v.addWidget(self.inner, 1)
        saved = (app.settings.get("folds") or {}).get(key) if app is not None and key else None
        self.set_open(open_ if saved is None else saved)

    def set_open(self, on, save=False):
        self.inner.setVisible(bool(on))
        self.head.setText(("\u25be  " if on else "\u25b8  ") + self.text)
        if save and self.app is not None and self.key:
            self.app.settings.setdefault("folds", {})[self.key] = bool(on)
            try:
                self.app.save_settings()
            except Exception:
                pass


def section(text):
    l = QLabel(_(text).upper())
    l.setObjectName("section")
    return l


def hint(text):
    l = QLabel(text)
    l.setObjectName("hint")
    l.setWordWrap(True)
    return l


def card(value, label, tip=None):
    f = QFrame()
    f.setObjectName("card")
    v = QVBoxLayout(f)
    v.setContentsMargins(14, 10, 14, 10)
    a = QLabel(str(value))
    a.setObjectName("cardvalue")
    b = QLabel(label)
    b.setObjectName("cardlabel")
    v.addWidget(a)
    v.addWidget(b)
    f.value, f.label = a, b
    if tip:
        f.setToolTip(tip)
    f.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    return f


def row(*widgets, stretch=True):
    w = QWidget()
    h = QHBoxLayout(w)
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(6)
    for x in widgets:
        if x == "stretch":
            h.addStretch(1)
        else:
            h.addWidget(x)
    if stretch:
        h.addStretch(1)
    return w


def ask(parent, title, text):
    return QMessageBox.question(parent, _(title), text) == QMessageBox.Yes


def info(parent, title, text):
    QMessageBox.information(parent, _(title), text)


def error(parent, title, text):
    QMessageBox.critical(parent, _(title), text)


def denied_box(parent, path, game_folder=None, title="Windows refused the write"):
    """Windows did not let Mod Studio write in the game folder (B14: a game under Program Files):
    what to do, and a button that starts Mod Studio again as administrator"""
    from . import access
    from PySide6.QtWidgets import QApplication
    # the main window (it has the game), not a dialog the box may sit on
    app = next((w for w in QApplication.topLevelWidgets() if hasattr(w, "game") and hasattr(w, "bus")), None)
    if game_folder is None:
        game_folder = getattr(getattr(app, "game", None), "folder", None)
    box = QMessageBox(QMessageBox.Warning, _(title), access.message(path, game_folder), QMessageBox.NoButton,
                      parent)
    again = None
    if not access.is_admin():
        again = box.addButton(_("Restart as administrator"), QMessageBox.AcceptRole)
    box.addButton(QMessageBox.Close)
    box.exec()
    if again is not None and box.clickedButton() is again:
        if access.restart_as_admin():
            if app is not None:
                app.close()
        else:
            QMessageBox.warning(parent, _(title), _("Mod Studio could not start itself as administrator. "
                                                    "Close it, right-click FL26ModStudio.exe and choose "
                                                    "Run as administrator."))


def denied(parent, err, game_folder=None):
    """when `err` (an exception or a traceback's text) is Windows refusing a write, show
    denied_box and return True; else False (the caller says what went wrong as before)"""
    from . import access
    path = access.denied_path(err)
    if path is None:
        return False
    denied_box(parent, path, game_folder)
    return True


def can_write(parent, game):
    """before a write into the game folder: True when Windows lets Mod Studio write there, else
    denied_box and False"""
    from . import access
    if not game or not game.folder:
        return True
    d = access.blocked(game)
    if d is None:
        return True
    denied_box(parent, d, game.folder)
    return False


def pick_file(parent, title, filt, start=""):
    p, _f = QFileDialog.getOpenFileName(parent, _(title), start, filt)
    return p


def pick_dir(parent, title, start=""):
    return QFileDialog.getExistingDirectory(parent, _(title), start)


class _Signals(QObject):
    done = Signal(object)
    failed = Signal(str)
    progress = Signal(object)


class Job(QRunnable):
    """fn(progress) in a worker thread; done(result) / failed(traceback text) on the GUI thread"""

    def __init__(self, fn, done=None, failed=None, progress=None):
        super().__init__()
        self.fn, self.s = fn, _Signals()
        if done:
            self.s.done.connect(done)
        if failed:
            self.s.failed.connect(failed)
        if progress:
            self.s.progress.connect(progress)

    def run(self):
        try:
            r = self.fn(self.s.progress.emit)
        except (Exception, SystemExit):
            # the builder's tools stop with SystemExit("message"); let through a worker thread it
            # ends the whole program with no window (0.2.2: "the app closes on Build")
            self.s.failed.emit(traceback.format_exc())
            return
        self.s.done.emit(r)


_JOBS = []


def run_job(fn, done=None, failed=None, progress=None):
    j = Job(fn, done, failed, progress)
    _JOBS.append(j)                      # keep the signals alive until the job is over
    j.s.done.connect(lambda *_a: _JOBS.remove(j) if j in _JOBS else None)
    j.s.failed.connect(lambda *_a: _JOBS.remove(j) if j in _JOBS else None)
    j.setAutoDelete(False)
    QThreadPool.globalInstance().start(j)
    return j
