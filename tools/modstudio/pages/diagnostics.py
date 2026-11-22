"""Diagnostics: every check the program knows, the errors in sider.log, and whether a League
Builder world was read by its modules"""
import io, os

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QGuiApplication, QTextCursor
from PySide6.QtWidgets import (QCheckBox, QLineEdit, QPlainTextEdit, QSplitter, QTabWidget,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from .. import checks, theme
from ..i18n import _
from ..ui import Page, hint, row, run_job

ROW = Qt.UserRole
COLOURS = {"err": theme.DANGER, "warn": theme.WARN, "ok": theme.GOOD}


class Diagnostics(Page):
    title = "Diagnostics"
    hint = ("Checks of the whole setup: content folders, module order, the content-server maps, the "
            "errors Sider wrote to sider.log in the last game, and your world in the game.")

    def __init__(self, app):
        super().__init__(app)
        self.action("Run the checks", self.run, "primary")
        self.action("Copy a report", self.copy_report,
                    tip="Copies the results as text, to paste when you ask somebody for help")
        self.tabs = QTabWidget()
        self.tree = QTreeWidget()
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setHeaderLabels([_("Where"), _("What")])
        self.tree.setColumnWidth(0, 180)
        self.tree.itemDoubleClicked.connect(self.jump)
        self.tabs.addTab(self.tree, _("Checks"))
        logw = QWidget()
        lv = QVBoxLayout(logw)
        lv.setContentsMargins(0, 8, 0, 0)
        self.find = QLineEdit()
        self.find.setPlaceholderText(_("Search sider.log"))
        self.find.setClearButtonEnabled(True)
        self.find.returnPressed.connect(self.show_log)
        self.only_err = QCheckBox(_("Only lines that look like errors"))
        self.only_err.setChecked(True)
        self.only_err.toggled.connect(self.show_log)
        lv.addWidget(row(self.find, self.only_err, stretch=False))
        self.log = QPlainTextEdit()
        self.log.setObjectName("log")
        self.log.setReadOnly(True)
        self.log.setLineWrapMode(QPlainTextEdit.NoWrap)
        lv.addWidget(self.log, 1)
        lv.addWidget(hint(_("sider.log is written again each time the game starts; this is the last game.")))
        self.tabs.addTab(logw, _("sider.log"))
        self.world = QPlainTextEdit()
        self.world.setObjectName("log")
        self.world.setReadOnly(True)
        self.tabs.addTab(self.world, _("Your world in the game"))
        self.manager = QPlainTextEdit()
        self.manager.setObjectName("log")
        self.manager.setReadOnly(True)
        self.tabs.addTab(self.manager, _("Rust mod manager"))
        self.outer.addWidget(self.tabs, 1)
        self.rows = []

    def refresh(self):
        if not self.rows:
            self.run()

    def run(self):
        g = self.app.game
        ini = self.app.ini() if g.ok() else None
        recipe = dict(self.app.project.recipe)
        self.app.busy(True, _("Checking"))

        def job(progress):
            rows = checks.full(g, ini, recipe)
            world = io.StringIO()
            manager = self.manager_report(g)
            try:
                import leaguebuilder as B
                missing = B.modules_missing(g.folder)
                if missing:
                    world.write(_("Mod Studio's modules not in sider.ini: %s") % ", ".join(missing) + "\n")
                B.check(g.folder, log=lambda t: world.write(t + "\n"))
            except Exception as e:
                world.write(str(e) + "\n")
            return rows, world.getvalue(), manager

        run_job(job, self.done, lambda tb: (self.app.busy(False), self.say(tb.strip().splitlines()[-1], "err")))

    def done(self, res):
        self.app.busy(False)
        rows, world, manager = res
        self.rows = rows or [("ok", "Setup", "No problems found.", None)]
        self.tree.clear()
        for level, area, text, page in self.rows:
            it = QTreeWidgetItem([_(area), _(text)])
            it.setForeground(1, QBrush(QColor(COLOURS.get(level, theme.TEXT))))
            it.setData(0, ROW, page)
            it.setToolTip(1, _(text))
            self.tree.addTopLevelItem(it)
        self.world.setPlainText(world)
        self.manager.setPlainText(manager)
        self.show_log()
        n = sum(1 for r in rows if r[0] == "err")
        self.say(_("%d problem(s), %d warning(s).") % (n, len(rows) - n) if rows else _("No problems found."),
                 "err" if n else "warn" if rows else "ok")

    @staticmethod
    def manager_report(game):
        from .. import native
        if not native.available():
            return _("The Rust manager extension is not installed. Build it with maturin to enable these reports.")
        if not os.path.isfile(game.ini_path):
            return _("No sider.ini is available for the Rust manager to inspect.")
        try:
            scan = native.scan(game.ini_path, game.sider_dir)
            verify = native.verify(game.ini_path, game.sider_dir)
        except (OSError, RuntimeError) as e:
            return _("Rust manager report failed: %s") % e

        conflicts = None
        conflict_error = None
        if os.path.isdir(game.livecpk_dir):
            try:
                conflicts = native.conflicts(game.livecpk_dir)
            except (OSError, RuntimeError) as e:
                conflict_error = str(e)
        else:
            conflict_error = _("No livecpk folder is available.")

        lines = [
            _("Active packs: %d; active modules: %d") %
            (len(scan["active_packs"]), len(scan["active_modules"])),
            _("Disabled packs: %d; disabled modules: %d") %
            (scan["disabled_packs"], scan["disabled_modules"]),
            _("Order: %d effective, %d partial, %d fully shadowed") %
            (verify["effective"], verify["partial"], verify["dead"]),
        ]
        lines.extend(_("Missing: %s") % item for item in scan["missing"])
        lines.extend(_("Duplicate: %s") % item for item in scan["duplicates"])
        for pack in verify["packs"]:
            if pack["dead"] or pack["surviving"] < pack["total"]:
                lines.append(
                    _("Shadowing: %s (%d/%d files survive)") %
                    (pack["path"], pack["surviving"], pack["total"])
                )
        if conflicts is not None:
            lines.extend(
                _("Conflict: %s <-> %s (%d differing files)") % tuple(pair)
                for pair in conflicts["pairs"][:15]
            )
            lines.append(
                _("Packs scanned: %d; %d differing shared keys; %d identical shared keys") %
                (conflicts["packs"], conflicts["differing"], conflicts["identical"])
            )
        else:
            lines.append(_("Conflict scan unavailable: %s") % conflict_error)
        return "\n".join(lines)

    def show_log(self):
        g = self.app.game
        want = self.find.text().strip().lower()
        if self.only_err.isChecked() and not want:
            lines = ["%6d  %s" % (n, t) for n, t in checks.log_problems(g)]
        else:
            try:
                all_ = open(g.log_path, encoding="utf-8", errors="replace").read().splitlines()
            except OSError:
                all_ = []
            lines = ["%6d  %s" % (i + 1, t) for i, t in enumerate(all_)
                     if (not want or want in t.lower()) and (not self.only_err.isChecked() or checks.ERR_WORDS.search(t))]
        if not lines:
            lines = [_("(nothing)") if os.path.exists(g.log_path) else _("There is no sider.log yet: start the game once.")]
        self.log.setPlainText("\n".join(lines[-3000:]))
        self.log.moveCursor(QTextCursor.End)

    def jump(self, it, col):
        page = it.data(0, ROW)
        if page and page in self.app.pages:
            self.app.open_page(page)

    def copy_report(self):
        from .. import VERSION
        g = self.app.game
        out = ["FL Mod Studio %s" % VERSION, "game version: %s" % (g.version() or "?"), ""]
        for level, area, text, page in self.rows:
            out.append("[%s] %s: %s" % (level, area, text))
        out += ["", "sider.log errors (last game):"]
        out += ["  %s" % t for _n, t in checks.log_problems(g)[-40:]]
        out += ["", self.world.toPlainText()]
        out += ["", "Rust mod manager:", self.manager.toPlainText()]
        home = os.path.expanduser("~")
        text = "\n".join(out).replace(home, "%USERPROFILE%")
        QGuiApplication.clipboard().setText(text)
        self.app.status(_("The report is on the clipboard."))
