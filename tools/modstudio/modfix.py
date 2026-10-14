"""Mod Studio's modules in one click (0.2.4): the line Home and Lua modules show, and the button
that puts them right. Before, the modules lived behind League Builder > Build > 0. Install the
modules, and nobody could tell whether they had them, or the right version."""
from PySide6.QtCore import Qt
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


def install_now(page):
    """copy the modules in and switch them on, then say how it went. True when it worked."""
    import leaguebuilder as B
    from . import access
    app = page.app
    if not app.game.ok():
        error(page, _("Install the modules"), _("Choose the game folder first (Settings)."))
        return False
    lines = []
    QApplication.setOverrideCursor(Qt.WaitCursor)
    try:
        snapshot(app.game.ini_path, "Install the modules", app.game.sider_dir)
        B.install_modules(app.game.folder, log=lines.append)
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
