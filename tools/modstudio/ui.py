"""small building blocks every page uses: headers, banners, cards, a background runner"""
import traceback
from PySide6.QtCore import Qt, QObject, QRunnable, QThreadPool, Signal
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QMessageBox, QPushButton,
                               QVBoxLayout, QWidget, QSizePolicy, QFileDialog, QToolButton)
from .i18n import _


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
