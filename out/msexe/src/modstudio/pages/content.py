"""the content servers: one view per server (its map files, its library, its settings), the
pages built on it, and the "Other content" page with the smaller servers and the look modules.

Nothing is written until Save: the map files are edited in memory and saved in one go, with a
restore point taken first (see backups.py).
"""
import os

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (QCheckBox, QComboBox, QCompleter, QDialog, QDialogButtonBox,
                               QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QSplitter, QTabWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
                               QWidget)

from .. import servers as S, theme
from ..i18n import _
from ..mapfile import Row
from ..ui import Page, section, hint, row, ask, error, info

ROW = Qt.UserRole


def project(app):
    return getattr(app, "project", None)


def label_for(app, kind, value):
    """"101  Arsenal FC" for a club id, the competition name for a tournament id"""
    p = project(app)
    try:
        n = int(value)
    except (TypeError, ValueError):
        return value
    if p is None or p.base is None:
        return value
    name = p.team_name(n) if kind == "team" else p.comp_name(n)
    return "%s  %s" % (value, name) if name else value


def choices(app, kind):
    """["101  Arsenal FC", ...] for a club / competition picker"""
    p = project(app)
    if p is None or p.base is None:
        return []
    teams, comps = p.names()
    src = teams if kind == "team" else comps
    return ["%d  %s" % (k, v) for k, v in sorted(src.items(), key=lambda kv: kv[1].lower())]


def number_of(text):
    t = (text or "").strip().split()
    return t[0] if t and t[0].lstrip("-").isdigit() else ""


# ---------------------------------------------------------------------------------------------
class RowDialog(QDialog):
    """add or change one line of a map file"""

    def __init__(self, view, m, r=None, preset=None):
        super().__init__(view)
        self.view, self.m = view, m
        self.setWindowTitle(_("Change the line") if r else _("Add a line"))
        self.setMinimumWidth(620)
        form = QFormLayout(self)
        form.setLabelAlignment(Qt.AlignRight)
        vals = list(r.fields) if r else [c.default for c in m.cols]
        for i, v in (preset or {}).items():
            while len(vals) <= i:
                vals.append("")
            vals[i] = v
        self.widgets = []
        lib = view.library_items()
        for i, c in enumerate(m.cols):
            v = vals[i] if i < len(vals) else ""
            w = self.widget_for(c, v, lib)
            if c.tip:
                w.setToolTip(_(c.tip))
            form.addRow(_(c.title), w)
            self.widgets.append((c, w))
        self.comment = QLineEdit(r.comment if r else "")
        self.comment.setPlaceholderText(_("optional; written after # at the end of the line"))
        form.addRow(_("Comment"), self.comment)
        self.enabled = QCheckBox(_("Line is on"))
        self.enabled.setChecked(r.enabled if r else True)
        form.addRow("", self.enabled)
        self.warn = QLabel("")
        self.warn.setObjectName("hint")
        self.warn.setWordWrap(True)
        form.addRow("", self.warn)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.check)
        bb.rejected.connect(self.reject)
        form.addRow(bb)
        self.vals = None

    def widget_for(self, c, v, lib):
        if c.kind in ("team", "comp"):
            w = QComboBox()
            w.setEditable(True)
            items = choices(self.view.app, c.kind)
            w.addItems(items)
            comp = QCompleter(items, w)
            comp.setCaseSensitivity(Qt.CaseInsensitive)
            comp.setFilterMode(Qt.MatchContains)
            w.setCompleter(comp)
            w.setEditText(label_for(self.view.app, c.kind, v))
            w.lineEdit().setPlaceholderText(_("type the id or a part of the name"))
            return w
        if c.kind == "item":
            w = QComboBox()
            w.setEditable(True)
            w.addItems(lib)
            comp = QCompleter(lib, w)
            comp.setCaseSensitivity(Qt.CaseInsensitive)
            comp.setFilterMode(Qt.MatchContains)
            w.setCompleter(comp)
            w.setEditText(v)
            w.currentTextChanged.connect(lambda t, w=w: self.item_picked(w, t))
            return w
        if c.kind == "flag":
            w = QCheckBox()
            w.setChecked(v.strip() == "1")
            return w
        if c.kind == "lang":
            w = QComboBox()
            w.setEditable(True)
            for code, name in S.LANGS:
                w.addItem("%s  %s" % (code, _(name)), code)
            w.setEditText(next(("%s  %s" % (code, _(name)) for code, name in S.LANGS if code == v), v))
            return w
        w = QLineEdit(v)
        if c.kind == "id3":
            w.setPlaceholderText("009")
        return w

    def item_picked(self, w, text):
        """a stadium or ball picked: fill in the id it was made for, and its name"""
        idx = [x for x, _w in self.widgets].index(next(c for c, ww in self.widgets if ww is w))
        folder = os.path.join(self.view.folder(), text.strip())
        if not os.path.isdir(folder):
            return
        key = self.view.server.key
        found = S.ball_id(folder) if key == "balls" else S.stadium_id(folder) if key == "stadiums" else ""
        if found and idx > 0:
            c0, w0 = self.widgets[idx - 1]
            if c0.kind == "id3":
                w0.setText(found)
        if key == "stadiums":
            for c, ww in self.widgets:
                if c.title == "Stadium name" and not ww.text().strip():
                    ww.setText(os.path.basename(text.strip()))

    def value(self, c, w):
        if c.kind in ("team", "comp"):
            return number_of(w.currentText())
        if c.kind == "item":
            return w.currentText().strip()
        if c.kind == "flag":
            return "1" if w.isChecked() else "0"
        if c.kind == "lang":
            return (w.currentText().strip().split() or [""])[0]
        return w.text().strip()

    def check(self):
        vals, bad = [], []
        for c, w in self.widgets:
            v = self.value(c, w)
            if c.kind in ("team", "comp") and not v:
                bad.append(_("%s: pick one from the list or type its id") % _(c.title))
            if c.kind == "id3" and v and not v.isdigit():
                bad.append(_("%s must be a number") % _(c.title))
            if c.kind == "id3" and v.isdigit():
                v = "%03d" % int(v)
            if c.kind in ("int",) and v and not v.lstrip("-").isdigit():
                bad.append(_("%s must be a whole number") % _(c.title))
            if c.kind == "float" and v:
                try:
                    float(v)
                except ValueError:
                    bad.append(_("%s must be a number with a dot (0.5)") % _(c.title))
            if "," in v and self.m.sep == "," and c.kind != "item":
                bad.append(_("%s cannot hold a comma") % _(c.title))
            vals.append(v)
        if bad:
            self.warn.setText("\n".join(bad))
            self.warn.setStyleSheet("color: %s;" % theme.DANGER)
            return
        self.vals = vals
        self.accept()


# ---------------------------------------------------------------------------------------------
class MapTab(QWidget):
    """one map file as a table"""

    def __init__(self, view, m):
        super().__init__()
        self.view, self.m, self.app = view, m, view.app
        self.mf = None
        self.dirty = False
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 8, 0, 0)
        top = QHBoxLayout()
        self.find = QLineEdit()
        self.find.setPlaceholderText(_("Search: club, competition, id or folder"))
        self.find.setClearButtonEnabled(True)
        self.find.textChanged.connect(lambda *_a: self._filter_later.start())
        self._filter_later = QTimer(self, singleShot=True, interval=180, timeout=self.fill)
        top.addWidget(self.find, 1)
        self.only_bad = QCheckBox(_("Only lines with problems"))
        self.only_bad.toggled.connect(self.fill)
        top.addWidget(self.only_bad)
        v.addLayout(top)
        if m.about:
            v.addWidget(hint(_(m.about)))
        self.tree = QTreeWidget()
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.tree.setHeaderLabels([_("On")] + [_(c.title) for c in m.cols] + [_("Comment")])
        self.tree.setColumnWidth(0, 40)
        for i, c in enumerate(m.cols):
            self.tree.setColumnWidth(i + 1, {"team": 230, "comp": 250, "item": 330, "id3": 60,
                                             "flag": 70, "lang": 110, "int": 90, "float": 90}.get(c.kind, 170))
        self.tree.itemDoubleClicked.connect(lambda *_a: self.edit())
        v.addWidget(self.tree, 1)
        b = []
        for text, slot, kind in ((_("Add..."), self.add, "primary"), (_("Change..."), self.edit, None),
                                 (_("Copy"), self.duplicate, None), (_("On / off"), self.toggle, None),
                                 (_("Remove"), self.remove, "danger")):
            x = QPushButton(text)
            if kind:
                x.setObjectName(kind)
            x.clicked.connect(slot)
            b.append(x)
        self.count = QLabel("")
        self.count.setObjectName("subtle")
        v.addWidget(row(*b, "stretch", self.count, stretch=False))

    def load(self):
        self.mf = self.m.open(self.view.folder())
        self.dirty = False
        self.fill()

    def problems(self, r, lib, seen):
        out = []
        for i, c in enumerate(self.m.cols):
            v = r.fields[i] if i < len(r.fields) else ""
            if c.kind == "item" and v and lib is not None and S.norm_item(v) not in lib:
                out.append(_("%s not found in the library") % v)
        if self.m.key == "team" and r.enabled and r.fields:
            if r.fields[0] in seen:
                out.append(_("this club is listed more than once; the first line counts"))
            seen.add(r.fields[0])
        return out

    def fill(self):
        if self.mf is None:
            return
        self.tree.setUpdatesEnabled(False)
        self.tree.clear()
        want = self.find.text().strip().lower()
        libset = self.view.library_set()
        seen, shown, total, bad_n = set(), 0, 0, 0
        warn = QBrush(QColor(theme.WARN))
        off = QBrush(QColor(theme.SUBTLE))
        for r in self.mf.rows():
            total += 1
            bad = self.problems(r, libset, seen)
            bad_n += bool(bad)
            cells = [label_for(self.app, c.kind, r.fields[i]) if i < len(r.fields) and c.kind in ("team", "comp")
                     else (r.fields[i] if i < len(r.fields) else "") for i, c in enumerate(self.m.cols)]
            if self.only_bad.isChecked() and not bad:
                continue
            if want and want not in (" ".join(cells) + " " + r.comment).lower():
                continue
            it = QTreeWidgetItem(["✓" if r.enabled else ""] + cells + [r.comment])
            it.setData(0, ROW, r)
            if bad:
                for c in range(it.columnCount()):
                    it.setForeground(c, warn)
                it.setToolTip(0, "\n".join(bad))
                for c in range(it.columnCount()):
                    it.setToolTip(c, "\n".join(bad))
            elif not r.enabled:
                for c in range(it.columnCount()):
                    it.setForeground(c, off)
            self.tree.addTopLevelItem(it)
            shown += 1
        self.tree.setUpdatesEnabled(True)
        self.count.setText(_("%d of %d lines") % (shown, total) + ("   ·   " + _("%d with problems") % bad_n
                                                                    if bad_n else ""))

    def selected(self):
        return [it.data(0, ROW) for it in self.tree.selectedItems()]

    def changed(self):
        self.dirty = True
        self.fill()
        self.view.update_buttons()

    def add(self, preset=None):
        if self.mf is None:
            return
        d = RowDialog(self.view, self.m, preset=preset if isinstance(preset, dict) else None)
        if d.exec() and d.vals is not None:
            r = Row(d.vals, d.comment.text().strip(), d.enabled.isChecked(),
                    quoted=[i for i in self.m.quote])
            cur = self.selected()
            self.mf.add(r, after=cur[-1] if cur else self.last_like(r))
            self.changed()

    def last_like(self, r):
        """new lines go after the last line of the same club / competition, else at the end"""
        rows = [x for x in self.mf.rows() if x.fields and x.fields[0] == r.fields[0]]
        return rows[-1] if rows else None

    def edit(self):
        sel = self.selected()
        if not sel:
            return
        r = sel[0]
        d = RowDialog(self.view, self.m, r)
        if d.exec() and d.vals is not None:
            r.fields[:len(d.vals)] = d.vals
            r.comment = d.comment.text().strip()
            r.enabled = d.enabled.isChecked()
            r.touch()
            self.changed()

    def duplicate(self):
        for r in self.selected():
            self.mf.add(r.copy(), after=r)
        self.changed()

    def toggle(self):
        sel = self.selected()
        for r in sel:
            r.enabled = not r.enabled
            r.touch()
        if sel:
            self.changed()

    def remove(self):
        sel = self.selected()
        if sel and ask(self, "Remove", _("Remove %d line(s)? Nothing is written until you press Save.") % len(sel)):
            for r in sel:
                self.mf.remove(r)
            self.changed()

    def save(self):
        if self.mf is not None and self.dirty:
            self.mf.save("%s: %s" % (self.view.server.title, self.m.file), self.app.game.sider_dir)
            self.dirty = False

    def uses(self):
        """{item path (lower): [labels]} of the lines that use each library item"""
        out = {}
        if self.mf is None:
            return out
        for r in self.mf.rows():
            for i, c in enumerate(self.m.cols):
                if c.kind == "item" and i < len(r.fields) and r.fields[i]:
                    out.setdefault(S.norm_item(r.fields[i]), []).append(
                        label_for(self.app, self.m.key, r.fields[0]))
        return out


# ---------------------------------------------------------------------------------------------
class LibraryTab(QWidget):
    """the items in the server folder and where each one is used"""

    def __init__(self, view):
        super().__init__()
        self.view, self.app = view, view.app
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 8, 0, 0)
        top = QHBoxLayout()
        self.find = QLineEdit()
        self.find.setPlaceholderText(_("Search the library"))
        self.find.setClearButtonEnabled(True)
        self.find.textChanged.connect(lambda *_a: self._later.start())
        self._later = QTimer(self, singleShot=True, interval=180, timeout=self.fill)
        top.addWidget(self.find, 1)
        self.unused = QCheckBox(_("Only items nothing uses"))
        self.unused.toggled.connect(self.fill)
        top.addWidget(self.unused)
        v.addLayout(top)
        split = QSplitter(Qt.Horizontal)
        self.tree = QTreeWidget()
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setHeaderLabels([_("Item"), _("Id"), _("Used by")])
        self.tree.setColumnWidth(0, 360)
        self.tree.setColumnWidth(1, 60)
        self.tree.currentItemChanged.connect(lambda *_a: self.inspect())
        self.tree.itemDoubleClicked.connect(lambda *_a: self.assign())
        split.addWidget(self.tree)
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(10, 0, 0, 0)
        self.pic = QLabel()
        self.pic.setAlignment(Qt.AlignCenter)
        self.pic.setMinimumHeight(140)
        rv.addWidget(self.pic)
        self.name = QLabel("")
        self.name.setObjectName("title")
        self.name.setWordWrap(True)
        rv.addWidget(self.name)
        self.detail = QLabel("")
        self.detail.setObjectName("hint")
        self.detail.setWordWrap(True)
        self.detail.setAlignment(Qt.AlignTop)
        rv.addWidget(self.detail, 1)
        b1 = QPushButton(_("Use it for..."))
        b1.setObjectName("primary")
        b1.clicked.connect(self.assign)
        b2 = QPushButton(_("Open the folder"))
        b2.clicked.connect(self.open)
        rv.addWidget(row(b1, b2))
        split.addWidget(right)
        split.setSizes([700, 380])
        v.addWidget(split, 1)
        self.count = QLabel("")
        self.count.setObjectName("subtle")
        v.addWidget(self.count)

    def fill(self):
        self.tree.setUpdatesEnabled(False)
        self.tree.clear()
        uses = self.view.uses()
        want = self.find.text().strip().lower()
        n = 0
        items = self.view.library_items()
        for p in items:
            u = uses.get(S.norm_item(p), [])
            if self.unused.isChecked() and u:
                continue
            if want and want not in p.lower():
                continue
            it = QTreeWidgetItem([p, "", (", ".join(u[:3]) + (" +%d" % (len(u) - 3) if len(u) > 3 else ""))
                                  if u else ""])
            it.setData(0, ROW, p)
            self.tree.addTopLevelItem(it)
            n += 1
        self.tree.setUpdatesEnabled(True)
        self.count.setText(_("%d of %d items") % (n, len(items)))

    def current(self):
        it = self.tree.currentItem()
        return it.data(0, ROW) if it else None

    def inspect(self):
        p = self.current()
        if not p:
            return
        folder = os.path.join(self.view.folder(), p)
        key = self.view.server.key
        found = S.ball_id(folder) if key == "balls" else S.stadium_id(folder) if key == "stadiums" else ""
        it = self.tree.currentItem()
        if found:
            it.setText(1, found)
        self.name.setText(os.path.basename(p))
        u = self.view.uses().get(S.norm_item(p), [])
        lines = [p]
        if found:
            lines.append(_("made for id %s") % found)
        lines.append("")
        lines.append(_("Used by:") if u else _("Nothing uses it yet."))
        lines += ["  " + x for x in u[:30]]
        self.detail.setText("\n".join(lines))
        from .builder import pixmap
        pm = pixmap(S.preview(folder), 180) if os.path.isdir(folder) else None
        if pm:
            self.pic.setPixmap(pm)
        else:
            self.pic.clear()
            self.pic.setText(_("no picture"))

    def assign(self):
        p = self.current()
        if not p:
            return
        tabs = self.view.map_tabs
        names = [_(t.m.title) for t in tabs if any(c.kind == "item" for c in t.m.cols)]
        if not names:
            return
        from PySide6.QtWidgets import QInputDialog
        which, ok = QInputDialog.getItem(self, _("Use it for..."), _("Add it to:"), names, 0, False)
        if not ok:
            return
        t = next(t for t in tabs if _(t.m.title) == which)
        idx = next(i for i, c in enumerate(t.m.cols) if c.kind == "item")
        preset = {idx: p}
        folder = os.path.join(self.view.folder(), p)
        found = S.ball_id(folder) if self.view.server.key == "balls" else \
            S.stadium_id(folder) if self.view.server.key == "stadiums" else ""
        if found and idx > 0 and t.m.cols[idx - 1].kind == "id3":
            preset[idx - 1] = found
        self.view.tabs.setCurrentWidget(t)
        t.add(preset)

    def open(self):
        p = self.current()
        d = os.path.join(self.view.folder(), p) if p else self.view.folder()
        if os.path.exists(d):
            os.startfile(d if os.path.isdir(d) else os.path.dirname(d))


# ---------------------------------------------------------------------------------------------
class SettingsTab(QWidget):
    def __init__(self, view):
        super().__init__()
        self.view = view
        self.ini = None
        self.form = QFormLayout(self)
        self.form.setLabelAlignment(Qt.AlignRight)
        self.widgets = {}
        for key, (label, kind, tip) in view.server.settings.items():
            w = QCheckBox() if kind == "flag" else QLineEdit()
            if tip:
                w.setToolTip(_(tip))
            if kind == "flag":
                w.toggled.connect(lambda *_a: view.update_buttons())
            else:
                w.textEdited.connect(lambda *_a: view.update_buttons())
            self.form.addRow(_(label), w)
            self.widgets[key] = (kind, w)
        self.note = hint("")
        self.form.addRow("", self.note)
        self.loaded = {}

    def load(self):
        self.ini = self.view.server.ini(self.view.content_dir())
        have = {k: v for k, v, _i in self.ini.items()} if self.ini else {}
        self.loaded = {}
        for key, (kind, w) in self.widgets.items():
            v = have.get(key, "")
            self.loaded[key] = v
            if kind == "flag":
                w.setChecked(v.strip() == "1")
            else:
                w.setText(v)
        self.note.setText(_("File: %s") % (self.ini.path if self.ini else "-"))

    def values(self):
        return {k: ("1" if w.isChecked() else "0") if kind == "flag" else w.text().strip()
                for k, (kind, w) in self.widgets.items()}

    @property
    def dirty(self):
        v = self.values()
        return any(v[k] != self.loaded.get(k, "") and not (self.widgets[k][0] == "flag" and
                   self.loaded.get(k, "") == "" and v[k] == "0") for k in v)

    def save(self):
        if not self.ini or not self.dirty:
            return
        for k, v in self.values().items():
            if v != self.loaded.get(k, ""):
                self.ini.set(k, v)
        self.ini.save(self.view.app.game.sider_dir)
        self.load()


# ---------------------------------------------------------------------------------------------
class ServerView(QWidget):
    """a content server: status line, a tab per map file, the library, the settings"""

    def __init__(self, app, key, extra_tabs=()):
        super().__init__()
        self.app, self.server = app, S.BY_KEY[key]
        self._lib = None
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        if self.server.about:
            v.addWidget(hint(_(self.server.about)))
        self.status = QLabel("")
        self.switch_btn = QPushButton(_("Switch the module on"))
        self.switch_btn.clicked.connect(self.switch_on)
        self.save_btn = QPushButton(_("Save"))
        self.save_btn.setObjectName("primary")
        self.save_btn.clicked.connect(self.save)
        self.undo_btn = QPushButton(_("Discard changes"))
        self.undo_btn.clicked.connect(self.discard)
        v.addWidget(row(self.status, "stretch", self.switch_btn, self.undo_btn, self.save_btn, stretch=False))
        self.tabs = QTabWidget()
        self.map_tabs = [MapTab(self, m) for m in self.server.maps]
        for t in self.map_tabs:
            self.tabs.addTab(t, _(t.m.title))
        self.lib_tab = None
        if self.server.library:
            self.lib_tab = LibraryTab(self)
            self.tabs.addTab(self.lib_tab, _("Library"))
        self.settings_tab = None
        if self.server.settings:
            self.settings_tab = SettingsTab(self)
            self.tabs.addTab(self.settings_tab, _("Settings"))
        for title, w in extra_tabs:
            self.tabs.addTab(w, _(title))
        self.tabs.currentChanged.connect(self.tab_changed)
        v.addWidget(self.tabs, 1)
        self.loaded = False

    # ---- where ----
    def content_dir(self):
        return self.app.game.content_dir

    def folder(self):
        return self.server.path(self.content_dir())

    def library_items(self):
        if self._lib is None:
            self._lib = S.library(self.folder(), self.server.library) if self.server.library else []
        return self._lib

    def library_set(self):
        if not self.server.library:
            return None
        return {S.norm_item(p) for p in self.library_items()}

    def uses(self):
        out = {}
        for t in self.map_tabs:
            for k, v in t.uses().items():
                out.setdefault(k, []).extend(v)
        return out

    # ---- state ----
    def dirty(self):
        return any(t.dirty for t in self.map_tabs) or bool(self.settings_tab and self.settings_tab.dirty)

    def module(self):
        return self.server.module_in(self.content_dir())

    def module_state(self):
        """(line in sider.ini or None, enabled)"""
        ini = self.app.ini()
        if ini is None:
            return None, False
        stem = self.module().lower()
        for e in ini.entries("lua.module"):
            if os.path.basename(e.value.replace("\\", "/")).lower() == stem:
                return e, e.enabled
        return None, False

    def update_buttons(self):
        d = self.dirty()
        self.save_btn.setEnabled(d)
        self.undo_btn.setEnabled(d)

    def refresh(self, force=False):
        if not self.server.installed(self.content_dir()):
            self.status.setText(_("There is no %s folder in SiderAddons\\content: this server is not installed.")
                                % self.server.folder)
            self.status.setStyleSheet("color: %s;" % theme.WARN)
            self.switch_btn.hide()
            self.tabs.setEnabled(False)
            self.update_buttons()
            return
        self.tabs.setEnabled(True)
        if force or not self.loaded or not self.dirty():
            self._lib = None
            for t in self.map_tabs:
                t.load()
            if self.settings_tab:
                self.settings_tab.load()
            if self.lib_tab and self.tabs.currentWidget() is self.lib_tab:
                self.lib_tab.fill()
            self.loaded = True
        e, on = self.module_state()
        exists = os.path.exists(os.path.join(self.app.game.modules_dir, self.module()))
        if on:
            txt, col = _("%s is on.") % self.module(), theme.GOOD
        elif e is not None:
            txt, col = _("%s is switched off in sider.ini: the game does not use these maps.") % self.module(), theme.WARN
        elif exists:
            txt, col = _("%s is not in sider.ini: the game does not use these maps.") % self.module(), theme.WARN
        else:
            txt, col = _("%s is not in the modules folder.") % self.module(), theme.WARN
        n = len(self.library_items()) if self.server.library and self.tabs.currentWidget() is self.lib_tab else None
        self.status.setText(txt + (("   " + _("%d items in the library") % n) if n is not None else ""))
        self.status.setStyleSheet("color: %s;" % col)
        self.switch_btn.setVisible(not on and exists)
        self.update_buttons()

    def tab_changed(self, i):
        if self.lib_tab is not None and self.tabs.widget(i) is self.lib_tab:
            self.lib_tab.fill()

    def switch_on(self):
        ini = self.app.ini()
        if ini is None:
            return
        e, on = self.module_state()
        if e is None:
            ini.add("lua.module", self.module())
        else:
            ini.set_enabled(e, True)
        self.app.save_ini(ini, "%s on" % self.module())
        self.refresh()

    def save(self):
        g, _s = self.app.game.running()
        try:
            for t in self.map_tabs:
                t.save()
            if self.settings_tab:
                self.settings_tab.save()
        except OSError as e:
            error(self, "Save", _("Could not save: %s") % e)
            return
        self.app.status(_("%s saved") % _(self.server.title) + ("  — " + _("restart the game to use it") if g else ""))
        self.app.bus.content_changed.emit()
        self.update_buttons()

    def discard(self):
        if ask(self, "Discard changes", _("Forget the changes you have not saved?")):
            self.refresh(force=True)


class ServerPage(Page):
    """a page that is one content server"""
    server = ""

    def __init__(self, app):
        super().__init__(app)
        self.view = ServerView(app, self.server, self.extra_tabs())
        self.outer.addWidget(self.view, 1)
        app.bus.game_changed.connect(lambda: self.view.refresh(force=True))
        app.bus.ini_changed.connect(lambda: self.view.refresh())
        if project(app) is not None:
            project(app).tables_changed.connect(lambda: [t.fill() for t in self.view.map_tabs])

    def extra_tabs(self):
        return ()

    def refresh(self):
        self.view.refresh()


# ---------------------------------------------------------------------------------------------
class LookModules(QWidget):
    """modules without map files: on or off"""

    def __init__(self, app):
        super().__init__()
        self.app = app
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 8, 0, 0)
        v.addWidget(hint(_("These modules change how matches look without map files, or read their "
                           "own folders. They can be switched on or off here; the order is on the "
                           "Lua modules page.")))
        self.tree = QTreeWidget()
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setHeaderLabels([_("On"), _("What"), _("Module"), _("What it does")])
        for c, w in enumerate((40, 170, 250)):
            self.tree.setColumnWidth(c, w)
        self.tree.itemDoubleClicked.connect(lambda *_a: self.toggle())
        v.addWidget(self.tree, 1)
        b = QPushButton(_("On / off"))
        b.clicked.connect(self.toggle)
        v.addWidget(row(b))

    def refresh(self):
        self.tree.clear()
        ini = self.app.ini()
        entries = ini.entries("lua.module") if ini else []
        files = []
        try:
            files = os.listdir(self.app.game.modules_dir)
        except OSError:
            pass
        for title, stem, what in S.FIXED:
            e = next((x for x in entries if os.path.basename(x.value.replace("\\", "/")).lower()
                      .startswith(stem.lower())), None)
            f = e.value if e else next((n for n in files if n.lower().startswith(stem.lower())
                                        and n.lower().endswith(".lua")), "")
            it = QTreeWidgetItem(["✓" if e is not None and e.enabled else "", _(title), f or _("(not installed)"),
                                  _(what)])
            it.setData(0, ROW, (e, f))
            if not f:
                for c in range(4):
                    it.setForeground(c, QBrush(QColor(theme.SUBTLE)))
            self.tree.addTopLevelItem(it)

    def toggle(self):
        it = self.tree.currentItem()
        if not it:
            return
        e, f = it.data(0, ROW)
        ini = self.app.ini()
        if ini is None or not f:
            return
        if e is None:
            ini.add("lua.module", f)
        else:
            e = next(x for x in ini.entries("lua.module") if x.value == e.value)
            ini.set_enabled(e, not e.enabled)
        self.app.save_ini(ini, "%s %s" % (f, "off" if e is not None and e.enabled else "on"))
        self.refresh()


class Servers(Page):
    title = "Other content"
    hint = ("Scoreboards, menus, referee kits, sleeve badges and weather work like the stadiums: a "
            "library and a map that says which competition or club gets what.")

    def __init__(self, app):
        super().__init__(app)
        self.tabs = QTabWidget()
        self.tabs.setObjectName("outer")
        self.views = []
        for key in ("scoreboards", "menus", "refkits", "badges", "weather"):
            w = ServerView(app, key)
            self.views.append(w)
            self.tabs.addTab(w, _(S.BY_KEY[key].title))
        self.look = LookModules(app)
        self.tabs.addTab(self.look, _("Look modules"))
        self.tabs.currentChanged.connect(lambda *_a: self.refresh())
        self.outer.addWidget(self.tabs, 1)
        app.bus.game_changed.connect(lambda: [v.refresh(force=True) for v in self.views])
        app.bus.ini_changed.connect(self.refresh)

    def refresh(self):
        w = self.tabs.currentWidget()
        if w is self.look:
            self.look.refresh()
        elif w is not None:
            w.refresh()

    def dirty(self):
        return any(v.dirty() for v in self.views)
