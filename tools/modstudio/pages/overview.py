"""Overview: the state of the setup at a glance, what needs attention, and the usual next steps"""
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (QGridLayout, QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
                               QWidget, QHBoxLayout)

from .. import backups, checks, installer, theme
from ..i18n import _
from ..ui import Page, section, hint, card, row

ROW = Qt.UserRole
COLOURS = {"err": theme.DANGER, "warn": theme.WARN, "ok": theme.GOOD}


class Overview(Page):
    title = "Overview"
    hint = "Your game's mod setup at a glance. Double-click a problem to open the section that fixes it."

    def __init__(self, app):
        super().__init__(app)
        grid = QHBoxLayout()
        grid.setSpacing(10)
        self.c_roots = card("-", _("content folders on"))
        self.c_mods = card("-", _("Lua modules on"))
        self.c_installed = card("-", _("mods installed here"))
        self.c_world = card("-", _("League Builder world"))
        self.c_backups = card("-", _("restore points"))
        for c in (self.c_roots, self.c_mods, self.c_installed, self.c_world, self.c_backups):
            grid.addWidget(c)
        self.outer.addLayout(grid)
        acts = []
        for text, target, kind in ((_("Install a mod"), "Install", "primary"), (_("Content folders"), "Roots", None),
                                   (_("Profiles"), "Profiles", None), (_("New leagues"), "NewLeagues", None),
                                   (_("Build the leagues"), "Build", None), (_("Check everything"), "Diagnostics", None)):
            b = QPushButton(text)
            if kind:
                b.setObjectName(kind)
            b.clicked.connect(lambda _c=False, t=target: self.app.open_page(t))
            acts.append(b)
        self.outer.addWidget(row(*acts))
        self.outer.addWidget(section("Needs attention"))
        self.problems = QTreeWidget()
        self.problems.setRootIsDecorated(False)
        self.problems.setHeaderLabels([_("Where"), _("What")])
        self.problems.setColumnWidth(0, 180)
        self.problems.itemDoubleClicked.connect(self.jump)
        self.outer.addWidget(self.problems, 2)
        self.outer.addWidget(section("Last changes"))
        self.recent = QTreeWidget()
        self.recent.setRootIsDecorated(False)
        self.recent.setHeaderLabels([_("When"), _("File"), _("Why")])
        self.recent.setColumnWidth(0, 150)
        self.recent.setColumnWidth(1, 300)
        self.recent.itemDoubleClicked.connect(lambda *_a: self.app.open_page("Restore"))
        self.outer.addWidget(self.recent, 1)
        app.bus.ini_changed.connect(self.refresh_if_shown)
        app.bus.content_changed.connect(self.refresh_if_shown)
        app.bus.game_changed.connect(self.refresh_if_shown)

    def refresh_if_shown(self):
        if self.isVisible():
            self.refresh()

    def refresh(self):
        g = self.app.game
        ini = self.app.ini() if g.ok() else None
        self.problems.clear()
        rows = checks.quick(g, ini, self.app.project.recipe)
        if ini is not None:
            roots = ini.entries("cpk.root")
            mods = ini.entries("lua.module")
            self.c_roots.value.setText("%d / %d" % (sum(e.enabled for e in roots), len(roots)))
            self.c_mods.value.setText("%d / %d" % (sum(e.enabled for e in mods), len(mods)))
            worlds = [e.value for e in roots if e.enabled and os.path.basename(e.value.strip("\\/")).startswith("_FL26")]
            self.c_world.value.setText(os.path.basename(worlds[0].strip("\\/")) if worlds else _("none"))
            if len(worlds) > 1:
                rows.append(("warn", "League Builder", _("%d League Builder worlds are switched on; only one should be")
                             % len(worlds), "Roots"))
        else:
            for c in (self.c_roots, self.c_mods, self.c_world):
                c.value.setText("-")
        if g.ok() and os.path.isdir(g.sider_dir):
            self.c_installed.value.setText(str(len(installer.records(g.sider_dir))))
            hist = backups.history(g.sider_dir)
            self.c_backups.value.setText(str(len(hist)))
        else:
            hist = []
            self.c_installed.value.setText("-")
            self.c_backups.value.setText("-")
        if not rows:
            rows = [("ok", "Setup", "No problems found.", None)]
        for level, area, text, page in rows:
            it = QTreeWidgetItem([_(area), _(text)])
            it.setForeground(1, QBrush(QColor(COLOURS.get(level, theme.TEXT))))
            it.setData(0, ROW, page)
            self.problems.addTopLevelItem(it)
        self.recent.clear()
        for r in hist[:8]:
            t = r["time"]
            it = QTreeWidgetItem(["%s.%s. %s:%s" % (t[6:8], t[4:6], t[9:11], t[11:13]), r["file"], r.get("reason", "")])
            self.recent.addTopLevelItem(it)

    def jump(self, it, col):
        page = it.data(0, ROW)
        if page and page in self.app.pages:
            self.app.open_page(page)
