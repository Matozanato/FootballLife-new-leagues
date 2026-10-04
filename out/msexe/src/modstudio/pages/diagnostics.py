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
            "errors Sider wrote to sider.log in the last game, and the League Builder world.")

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
        self.tabs.addTab(self.world, _("League Builder world"))
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
            try:
                import leaguebuilder as B
                missing = B.modules_missing(g.folder)
                if missing:
                    world.write(_("League Builder modules not in sider.ini: %s") % ", ".join(missing) + "\n")
                B.check(g.folder, log=lambda t: world.write(t + "\n"))
            except Exception as e:
                world.write(str(e) + "\n")
            return rows, world.getvalue()

        run_job(job, self.done, lambda tb: (self.app.busy(False), self.say(tb.strip().splitlines()[-1], "err")))

    def done(self, res):
        self.app.busy(False)
        rows, world = res
        self.rows = rows or [("ok", "Setup", "No problems found.", None)]
        self.tree.clear()
        for level, area, text, page in self.rows:
            it = QTreeWidgetItem([_(area), _(text)])
            it.setForeground(1, QBrush(QColor(COLOURS.get(level, theme.TEXT))))
            it.setData(0, ROW, page)
            it.setToolTip(1, _(text))
            self.tree.addTopLevelItem(it)
        self.world.setPlainText(world)
        self.show_log()
        n = sum(1 for r in rows if r[0] == "err")
        self.say(_("%d problem(s), %d warning(s).") % (n, len(rows) - n) if rows else _("No problems found."),
                 "err" if n else "warn" if rows else "ok")

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
        out = ["FL26 Mod Studio %s" % VERSION, "game version: %s" % (g.version() or "?"), ""]
        for level, area, text, page in self.rows:
            out.append("[%s] %s: %s" % (level, area, text))
        out += ["", "sider.log errors (last game):"]
        out += ["  %s" % t for _n, t in checks.log_problems(g)[-40:]]
        out += ["", self.world.toPlainText()]
        home = os.path.expanduser("~")
        text = "\n".join(out).replace(home, "%USERPROFILE%")
        QGuiApplication.clipboard().setText(text)
        self.app.status(_("The report is on the clipboard."))
