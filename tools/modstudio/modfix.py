"""Mod Studio's modules in one click (0.2.4): the line Home and Lua modules show, and the button
that puts them right. Before, the modules lived behind League Builder > Build > 0. Install the
modules, and nobody could tell whether they had them, or the right version."""
from PySide6.QtCore import QEvent, QEventLoop, QObject, Qt, QTimer
from PySide6.QtWidgets import QApplication

from . import checks
from .backups import snapshot
from .i18n import _
from .ui import error, info


def summary(state):
    """(level, text, right) of the modules line; None when there is nothing to compare"""
    if not state:
        return None
    n = state["total"]
    if checks.modules_ok(state):
        return ("ok", _("Mod Studio's modules: installed, up to date and switched on"),
                "%d / %d" % (n - len(state["left_off"]), n))
    bits = []
    if state["missing"]:
        bits.append(_("%d missing") % len(state["missing"]))
    if state["changed"]:
        bits.append(_("%d older or damaged") % len(state["changed"]))
    if state["off"]:
        bits.append(_("%d switched off") % len(state["off"]))
    return ("err", _("Mod Studio's modules need installing: %s") % ", ".join(bits), "")


class _Hold(QObject):
    """while the modules are copied: no click, key or wheel reaches the program and no window
    closes, so nothing else can start over the same files"""
    STOP = frozenset((QEvent.MouseButtonPress, QEvent.MouseButtonRelease, QEvent.MouseButtonDblClick,
                      QEvent.KeyPress, QEvent.KeyRelease, QEvent.Shortcut, QEvent.ShortcutOverride,
                      QEvent.Wheel, QEvent.Close, QEvent.ContextMenu))

    def eventFilter(self, obj, ev):
        if ev.type() in self.STOP:
            if ev.type() == QEvent.Close:
                ev.ignore()
            return True
        return False


def aside(work):
    """work() in a thread of its own while this one keeps answering Windows; back when it is
    over, with its error raised here. B476 (15.11.2026): Install the modules ran on the window's
    thread, 2 s of it a wait for the antivirus, and the window did not answer for 2.8 s"""
    import threading
    out = []

    def run():
        try:
            work()
        except BaseException as e:
            out.append(e)

    qapp = QApplication.instance()
    t = threading.Thread(target=run, name="install-modules", daemon=True)
    hold = _Hold()
    loop = QEventLoop()
    tick = QTimer()
    tick.setInterval(30)
    tick.timeout.connect(lambda: t.is_alive() or loop.quit())
    qapp.installEventFilter(hold)
    try:
        t.start()
        tick.start()
        loop.exec()
    finally:
        tick.stop()
        t.join()
        qapp.removeEventFilter(hold)
    if out:
        if isinstance(out[0], Exception):
            raise out[0]
        raise RuntimeError(str(out[0]) or type(out[0]).__name__)     # SystemExit("message") of a tool


def install_now(page):
    """copy the modules in and switch them on, then say how it went. True when it worked."""
    import leaguebuilder as B
    from . import access
    app = page.app
    if not app.game.ok():
        error(page, _("Install the modules"), _("Choose the game folder first (Settings)."))
        return False
    lines = []

    def work():
        snapshot(app.game.ini_path, "Install the modules", app.game.sider_dir)
        B.install_modules(app.game.folder, log=lines.append)
        # what Home and the header ask next, worked out here with the files just written (B480,
        # 17.11.2026: on the window's thread 1.25 s of a stopped window, the exe test of beta4p)
        from . import checks
        checks.warm_modules(app.game)

    QApplication.setOverrideCursor(Qt.WaitCursor)
    try:
        aside(work)
    except Exception as e:
        QApplication.restoreOverrideCursor()
        path = access.denied_path(e)
        if path is not None:
            access_text = _("Windows does not let Mod Studio write in %s") % (path or app.game.folder)
            error(page, _("Install the modules"), access_text)
        else:
            error(page, _("Install the modules"), str(e))
        app.bus.ini_changed.emit()
        return False
    QApplication.restoreOverrideCursor()
    app.bus.ini_changed.emit()
    app.bus.content_changed.emit()
    info(page, _("Install the modules"),
         _("Mod Studio's modules are installed and switched on. Start the game again to use them."))
    return True
