"""Restore points: every file the program changed, as it was before each change"""
import difflib, os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QPlainTextEdit, QPushButton, QSplitter, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget)

from .. import backups
from ..i18n import _
from ..roots import human
from ..ui import Page, section, hint, row, ask, error

ROW = Qt.UserRole
TEXT_EXT = (".ini", ".txt", ".csv", ".lua", ".json", ".cfg")


def when(t):
    return "%s.%s.%s %s:%s:%s" % (t[6:8], t[4:6], t[0:4], t[9:11], t[11:13], t[13:15]) if len(t) >= 15 else t


class Restore(Page):
    title = "Restore points"
    hint = ("Before the program changes a file (sider.ini, a map, a module) it keeps a copy here. "
            "Pick one to see what changed since, and put it back if you want the old one.")

    def __init__(self, app):
        super().__init__(app)
        self.only = QComboBox()
        self.only.addItem(_("All files"), None)
        self.only.currentIndexChanged.connect(lambda *_a: self.fill())
        self.actions.insertWidget(1, self.only)
        self.action("Put this copy back", self.restore, "primary")
        self.action("Clean up...", self.clean)
        split = QSplitter(Qt.Horizontal)
        self.tree = QTreeWidget()
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setHeaderLabels([_("When"), _("File"), _("Why"), _("Size")])
        for c, w in enumerate((150, 280, 260)):
            self.tree.setColumnWidth(c, w)
        self.tree.currentItemChanged.connect(lambda *_a: self.inspect())
        split.addWidget(self.tree)
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(10, 0, 0, 0)
        rv.addWidget(section("Changes since this copy"))
        self.diff = QPlainTextEdit()
        self.diff.setObjectName("log")
        self.diff.setReadOnly(True)
        self.diff.setLineWrapMode(QPlainTextEdit.NoWrap)
        rv.addWidget(self.diff, 1)
        rv.addWidget(hint(_("Lines starting with - are in the copy, + are in the file now.")))
        split.addWidget(right)
        split.setSizes([700, 520])
        self.outer.addWidget(split, 1)
        app.bus.ini_changed.connect(self.refresh)
        app.bus.content_changed.connect(self.refresh)
        app.bus.game_changed.connect(self.refresh)

    def sd(self):
        return self.app.game.sider_dir

    def refresh(self):
        if not os.path.isdir(self.sd()):
            self.tree.clear()
            return
        files = sorted({r["file"] for r in backups.load(self.sd())}, key=str.lower)
        cur = self.only.currentData()
        self.only.blockSignals(True)
        self.only.clear()
        self.only.addItem(_("All files"), None)
        for f in files:
            self.only.addItem(f, f)
        i = self.only.findData(cur)
        self.only.setCurrentIndex(max(0, i))
        self.only.blockSignals(False)
        self.fill()

    def fill(self):
        self.tree.clear()
        for r in backups.history(self.sd(), self.only.currentData()):
            it = QTreeWidgetItem([when(r["time"]), r["file"], r.get("reason", ""), human(r.get("size", 0))])
            it.setData(0, ROW, r)
            self.tree.addTopLevelItem(it)
        if self.tree.topLevelItemCount():
            self.tree.setCurrentItem(self.tree.topLevelItem(0))

    def current(self):
        it = self.tree.currentItem()
        return it.data(0, ROW) if it else None

    def inspect(self):
        r = self.current()
        if not r:
            self.diff.clear()
            return
        now = os.path.join(self.sd(), r["file"])
        old = os.path.join(self.sd(), r["copy"])
        if not r["file"].lower().endswith(TEXT_EXT):
            self.diff.setPlainText(_("(not a text file: %s now, %s in the copy)") % (
                human(os.path.getsize(now)) if os.path.exists(now) else _("gone"), human(os.path.getsize(old))))
            return
        try:
            a = open(old, encoding="utf-8", errors="replace").read().splitlines()
            b = open(now, encoding="utf-8", errors="replace").read().splitlines() if os.path.exists(now) else []
        except OSError as e:
            self.diff.setPlainText(str(e))
            return
        d = list(difflib.unified_diff(a, b, "copy", "now", n=2, lineterm=""))
        self.diff.setPlainText("\n".join(d[2:]) if d else _("The file is the same as this copy."))

    def restore(self):
        r = self.current()
        if not r:
            return
        g, s = self.app.game.running()
        if not ask(self, "Restore points", _("Put back %s as it was on %s? The file as it is now is kept as a "
                                             "restore point too.") % (r["file"], when(r["time"])) +
                   ("\n\n" + _("The game is running: restart it afterwards.") if g else "")):
            return
        try:
            backups.restore(self.sd(), r)
        except OSError as e:
            error(self, "Restore points", str(e))
            return
        if r["file"].lower() == "sider.ini":
            self.app.bus.ini_changed.emit()
        else:
            self.app.bus.content_changed.emit()
        self.say(_("%s is back as it was on %s.") % (r["file"], when(r["time"])), "ok")
        self.refresh()

    def clean(self):
        rows = backups.load(self.sd())
        files = {r["file"] for r in rows}
        if not rows or not ask(self, "Clean up...", _("Keep the newest 20 copies of each file and delete the "
                                                      "older ones (%d copies of %d files now)?") % (len(rows), len(files))):
            return
        n = sum(backups.keep(self.sd(), f, 20) for f in files)
        self.say(_("%d old copies deleted.") % n, "ok")
        self.refresh()
