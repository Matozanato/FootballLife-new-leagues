"""Lua modules: the lua.module lines -- switch on/off, reorder, and the order rules"""
import os
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (QCheckBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSplitter,
                               QTreeWidgetItem, QVBoxLayout, QWidget, QPlainTextEdit, QMenu)
from .. import theme, modules as M
from ..i18n import _
from ..siderini import norm
from ..ui import Page, section, hint, ask, pick_file, row
from .roots import OrderTree


class Modules(Page):
    title = "Lua modules"
    hint = ("The scripts Sider loads, in the order sider.ini lists them. Content servers (stadiums, "
            "kits, balls ...) are modules too. Tick to switch one on, drag to reorder, then Apply. "
            "Rules that the modules' authors give for the order are checked below.")
    KEY = "lua.module"

    def __init__(self, app):
        super().__init__(app)
        self.ini, self.dirty = None, False
        self.btn_apply = self.action("Apply", self.apply, "primary", "Write the changes to sider.ini")
        self.btn_discard = self.action("Discard", self.load, tip="Forget the changes")

        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(_("Find a module..."))
        self.search.textChanged.connect(self.filter)
        self.hide_core = QCheckBox(_("Hide the League Builder's own modules (fl26...)"))
        self.hide_core.setChecked(True)
        self.hide_core.toggled.connect(self.filter)
        bar.addWidget(self.search, 1)
        bar.addWidget(self.hide_core)
        for text, fn in (("Up", lambda: self.shift(-1)), ("Down", lambda: self.shift(1)),
                         ("Add module...", self.add_module)):
            b = QPushButton(_(text))
            b.clicked.connect(fn)
            bar.addWidget(b)
        self.outer.addLayout(bar)

        split = QSplitter(Qt.Horizontal)
        self.tree = OrderTree(self.dropped)
        self.tree.setHeaderLabels([_("On"), "#", _("Module"), _("What it is"), _("Note")])
        for c, w in enumerate((40, 36, 250, 300, 200)):
            self.tree.setColumnWidth(c, w)
        self.tree.header().setStretchLastSection(True)
        self.tree.itemChanged.connect(self.ticked)
        self.tree.itemSelectionChanged.connect(self.inspect)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.menu)
        split.addWidget(self.tree)

        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(10, 0, 0, 0)
        rv.addWidget(section("Order rules"))
        self.rules = QLabel("")
        self.rules.setWordWrap(True)
        self.rules.setTextFormat(Qt.RichText)
        rv.addWidget(self.rules)
        rv.addSpacing(8)
        rv.addWidget(section("Module"))
        self.i_name = QLabel("")
        self.i_name.setObjectName("title")
        self.i_info = hint("")
        rv.addWidget(self.i_name)
        rv.addWidget(self.i_info)
        self.i_head = QPlainTextEdit()
        self.i_head.setObjectName("log")
        self.i_head.setReadOnly(True)
        rv.addWidget(self.i_head, 1)
        b_open = QPushButton(_("Open the file"))
        b_open.clicked.connect(self.open_file)
        rv.addWidget(row(b_open))
        split.addWidget(right)
        split.setSizes([860, 400])
        self.outer.addWidget(split, 1)
        self.foot = hint("")
        self.outer.addWidget(self.foot)
        app.bus.ini_changed.connect(lambda: None if self.dirty else self.load())
        self._loading = False

    def shown(self):
        if not self.dirty:
            self.load()

    def load(self):
        self.ini = self.app.ini()
        self.dirty = False
        self.fill()

    def entries(self):
        return self.ini.entries(self.KEY) if self.ini else []

    def fill(self):
        self._loading = True
        self.tree.clear()
        mdir = self.app.game.modules_dir
        for n, e in enumerate(self.entries()):
            it = QTreeWidgetItem()
            it.setFlags((it.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsDragEnabled) & ~Qt.ItemIsDropEnabled)
            it.setCheckState(0, Qt.Checked if e.enabled else Qt.Unchecked)
            it.setText(1, str(n + 1))
            it.setText(2, e.value)
            it.setData(2, Qt.UserRole, e.index)
            kind, desc = M.describe(e.value, mdir)
            it.setText(3, _(desc))
            it.setData(3, Qt.UserRole, kind)
            it.setText(4, e.note)
            if not M.exists(e.value, mdir):
                it.setText(3, _("the file is missing from the modules folder"))
                it.setForeground(3, QBrush(QColor(theme.DANGER if e.enabled else theme.SUBTLE)))
            if not e.enabled:
                for c in range(1, 5):
                    it.setForeground(c, QBrush(QColor(theme.SUBTLE)))
            self.tree.addTopLevelItem(it)
        self._loading = False
        self.filter()
        probs = self.order_problems()
        if probs:
            self.rules.setText("".join("<p style='color:%s'>● %s</p>" % (theme.WARN, p) for p in probs))
        else:
            self.rules.setText("<p style='color:%s'>✓ %s</p>" % (theme.GOOD, _("No problems found.")))
        on = sum(1 for e in self.entries() if e.enabled)
        self.foot.setText(_("%d modules listed, %d switched on.") % (len(self.entries()), on))
        self.btn_apply.setEnabled(self.dirty)
        self.btn_discard.setEnabled(self.dirty)
        self.say(_("Changes not written yet: press Apply.") if self.dirty else "", "warn")

    def order_problems(self):
        ini = self.ini or self.app.ini()
        if not ini:
            return []
        return [_(p) if isinstance(p, str) else _(p[0]) % p[1:]
                for p in M.check_order(ini, self.app.game.modules_dir)]

    def filter(self):
        q = self.search.text().strip().lower()
        hide = self.hide_core.isChecked()
        for i in range(self.tree.topLevelItemCount()):
            it = self.tree.topLevelItem(i)
            h = (q and q not in it.text(2).lower()) or (hide and it.data(3, Qt.UserRole) == "core")
            it.setHidden(bool(h))

    def _entry(self, it):
        idx = it.data(2, Qt.UserRole)
        return next((e for e in self.entries() if e.index == idx), None)

    def ticked(self, it, col):
        if self._loading or col != 0:
            return
        e = self._entry(it)
        if e:
            self.ini.set_enabled(e, it.checkState(0) == Qt.Checked)
            self.dirty = True
            self.fill()

    def dropped(self):
        self.ini.reorder(self.KEY, [self.tree.topLevelItem(i).text(2) for i in range(self.tree.topLevelItemCount())])
        self.dirty = True
        self.fill()

    def shift(self, d):
        it = self.tree.currentItem()
        e = self._entry(it) if it else None
        if not e:
            return
        e2 = self.ini.move(e, d)
        self.dirty = True
        self.fill()
        for i in range(self.tree.topLevelItemCount()):
            x = self.tree.topLevelItem(i)
            if x.data(2, Qt.UserRole) == e2.index:
                self.tree.setCurrentItem(x)

    def add_module(self):
        p = pick_file(self, "A Lua module", "Lua (*.lua);;All files (*.*)", self.app.game.modules_dir)
        if not p:
            return
        name = M.install_file(p, self.app.game.modules_dir)
        if self.ini.find(self.KEY, name):
            self.say(_("That module is already in the list."), "warn")
            return
        self.ini.add(self.KEY, name)
        self.dirty = True
        self.fill()

    def apply(self):
        if self.dirty:
            self.app.save_ini(self.ini, "modules changed")
            self.remember_off()
            self.load()

    def remember_off(self):
        """an optional module of ours (the regens) switched off stays off through Build"""
        mdir = self.app.game.modules_dir
        if not mdir or not os.path.isdir(mdir):
            return
        import leaguebuilder as B
        off = B.modules_off(mdir)
        for e in self.entries():
            m = os.path.basename(e.value.strip().strip('"').replace("\\", "/"))[:-4]
            if m in B.OPTIONAL_MODULES:
                (off.discard if e.enabled else off.add)(m)
        B.set_modules_off(mdir, off)

    def inspect(self):
        it = self.tree.currentItem()
        e = self._entry(it) if it else None
        if not e:
            return
        self.i_name.setText(e.value)
        p = M.path_of(e.value, self.app.game.modules_dir)
        if p and os.path.exists(p):
            self.i_info.setText("%s  ·  %d KB" % (p, os.path.getsize(p) // 1024))
            self.i_head.setPlainText(M.header(p))
        else:
            self.i_info.setText(_("the file is missing from the modules folder"))
            self.i_head.setPlainText("")

    def open_file(self):
        it = self.tree.currentItem()
        e = self._entry(it) if it else None
        p = M.path_of(e.value, self.app.game.modules_dir) if e else None
        if p and os.path.exists(p):
            os.startfile(os.path.dirname(p))

    def menu(self, pos):
        it = self.tree.itemAt(pos)
        if not it:
            return
        m = QMenu(self)
        m.addAction(_("Open the file"), self.open_file)
        m.addAction(_("Up"), lambda: self.shift(-1))
        m.addAction(_("Down"), lambda: self.shift(1))
        m.exec(self.tree.viewport().mapToGlobal(pos))
