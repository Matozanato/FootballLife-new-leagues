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
        except Exception:
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
