"""Content folders: the cpk.root lines -- switch on/off, reorder, see what wins"""
import os, shutil
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QBrush, QFont
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QSplitter, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
                               QWidget, QHeaderView, QMenu, QStyledItemDelegate)
from .. import theme, roots as R, worlds as WL
from ..i18n import _
from ..siderini import norm, root_path
from ..ui import Page, section, hint, ask, run_job, pick_dir, row, error, can_write, denied

WORLD_PREFIX = "_fl26"


def rename_recipe(app, old, new):
    """the world's name in Mod Studio itself, after a world is renamed (or renamed back from Restore
    points): the open world's, the copy Build keeps of it (recipes\\<world>.json) and the setting
    that opens it at the next start"""
    P, st = app.project, app.settings
    was = os.path.join(P.copies_dir(), old + ".json")
    kept = WL.rename_recipe_copy(P.copies_dir(), old, new)
    if kept and os.path.normcase(os.path.abspath(st.get("last_recipe") or "")) == os.path.normcase(was):
        st["last_recipe"] = kept
    if P.recipe.get("world") == old:
        # the open world is that world: its name changes too. Saved only when nothing else waits
        # to be saved (Save recipe stays the player's for his own changes)
        was_dirty = P.dirty
        P.recipe["world"] = new
        try:
            if P.path and not was_dirty:
                P.save()
            elif not P.path:
                st["last_recipe"] = P.keep_copy()
                P.changed.emit()
            else:
                P.touch()
        except OSError:
            P.touch()
    P.drop_names()
    try:
        app.save_settings()
    except Exception:
        pass


class RowColour(QStyledItemDelegate):
    """paints a row's own background (setBackground) under its text. The theme's style sheet styles
    the list's rows (QTreeView::item) and Qt then leaves the item's background out: the live world
    was set green and looked like every other row (test_world_manage, 15.10.). Selection and
    hover are drawn over it as before"""

    def paint(self, painter, option, index):
        b = index.data(Qt.BackgroundRole)
        if isinstance(b, QBrush) and b.style() != Qt.NoBrush:
            painter.fillRect(option.rect, b)
        super().paint(painter, option, index)


class OrderTree(QTreeWidget):
    """a list whose rows can be dragged into a new order (top level only)"""

    def __init__(self, on_drop):
        super().__init__()
        self.on_drop = on_drop
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setRootIsDecorated(False)
        self.setAlternatingRowColors(True)
        self.setUniformRowHeights(True)

    def dropEvent(self, e):
        target = self.itemAt(e.position().toPoint())
        if target is not None and target.parent() is not None:
            e.ignore()
            return
        super().dropEvent(e)
        # never let a row become a child of another
        for i in range(self.topLevelItemCount()):
            it = self.topLevelItem(i)
            while it.childCount():
                ch = it.takeChild(0)
                self.insertTopLevelItem(i + 1, ch)
        self.on_drop()


class Roots(Page):
    title = "Content folders"
    hint = ("Every folder listed in sider.ini as a cpk.root. Sider looks a file up from the top down "
            "and takes the first folder that has it, so a folder higher in the list wins. Tick to switch "
            "a folder on, drag to reorder, then Apply.")
    KEY = "cpk.root"

    def __init__(self, app):
        super().__init__(app)
        self.ini, self.idx, self.conf, self.dirty = None, {}, [], False
        self.btn_apply = self.action("Apply", self.apply, "primary", "Write the changes to sider.ini")
        self.btn_discard = self.action("Discard", self.load, tip="Forget the changes")
        self.action("Rescan", self.rescan, tip="Read the folders again")

        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(_("Find a folder..."))
        self.search.textChanged.connect(self.filter)
        self.show_worlds = QCheckBox(_("Show the worlds (_FL26...)"))
        self.show_worlds.toggled.connect(self.filter)
        self.only_on = QCheckBox(_("Only switched on"))
        self.only_on.toggled.connect(self.filter)
        bar.addWidget(self.search, 1)
        bar.addWidget(self.only_on)
        bar.addWidget(self.show_worlds)
        for text, fn in (("Up", lambda: self.shift(-1)), ("Down", lambda: self.shift(1)),
                         ("To top", lambda: self.shift(-10000)), ("Add folder...", self.add_folder)):
            b = QPushButton(_(text))
            b.clicked.connect(fn)
            bar.addWidget(b)
        self.outer.addLayout(bar)

        split = QSplitter(Qt.Horizontal)
        self.tree = OrderTree(self.dropped)
        self.tree.setItemDelegate(RowColour(self.tree))
        self.tree.setHeaderLabels([_("On"), "#", _("Folder"), _("What it changes"), _("Files"),
                                   _("Size"), _("Overrides"), _("Note")])
        self.tree.itemChanged.connect(self.ticked)
        self.tree.itemSelectionChanged.connect(self.inspect)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.menu)
        h = self.tree.header()
        h.setStretchLastSection(True)
        for c, w in enumerate((40, 36, 330, 180, 60, 80, 90, 120)):
            self.tree.setColumnWidth(c, w)
        split.addWidget(self.tree)

        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(10, 0, 0, 0)
        rv.addWidget(section("Folder"))
        self.i_name = QLabel("")
        self.i_name.setObjectName("title")
        self.i_name.setWordWrap(True)
        self.i_path = hint("")
        self.i_kinds = QLabel("")
        self.i_kinds.setWordWrap(True)
        rv.addWidget(self.i_name)
        rv.addWidget(self.i_path)
        rv.addWidget(self.i_kinds)
        b_open = QPushButton(_("Open folder"))
        b_open.clicked.connect(self.open_folder)
        b_rm = QPushButton(_("Remove from the list"))
        b_rm.clicked.connect(self.remove_line)
        b_del = QPushButton(_("Delete from disk..."))
        b_del.setObjectName("danger")
        b_del.clicked.connect(self.delete_folder)
        rv.addWidget(row(b_open, b_rm))
        rv.addWidget(row(b_del))
        # 0.2.4 (mato 15.10.): a world is renamed or deleted here, safely -- see worlds.py
        self.b_wren = QPushButton(_("Rename world..."))
        self.b_wren.clicked.connect(lambda: self.rename_world())
        self.b_wdel = QPushButton(_("Delete world..."))
        self.b_wdel.setObjectName("danger")
        self.b_wdel.clicked.connect(lambda: self.delete_world())
        rv.addWidget(row(self.b_wren, self.b_wdel))
        self.b_wren.hide()
        self.b_wdel.hide()
        rv.addSpacing(8)
        rv.addWidget(section("Overrides"))
        self.i_conf = QTreeWidget()
        self.i_conf.setHeaderLabels([_("File"), _("Winner")])
        self.i_conf.setRootIsDecorated(False)
        self.i_conf.setColumnWidth(0, 260)
        rv.addWidget(self.i_conf, 1)
        split.addWidget(right)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 1)
        split.setSizes([900, 360])
        self.outer.addWidget(split, 1)
        self.foot = hint("")
        self.outer.addWidget(self.foot)
        app.bus.ini_changed.connect(self.external_change)
        app.bus.game_changed.connect(self.rescan)
        self._loading = False
        self._scanned_once = False

    # ---- data ----
    def shown(self):
        if not self._scanned_once:
            self.rescan()
        elif not self.dirty:
            self.load()

    def external_change(self):
        if not self.dirty:
            self.load()

    def rescan(self):
        g = self.app.game
        if not g.ok():
            self.say(_("Choose the game folder first (Game ▾ Choose the game folder)."), "warn")
            return
        ini = self.app.ini()
        if ini is None:
            self.say(_("There is no sider.ini in %s.") % g.sider_dir, "err")
            return
        self.app.busy(True, _("Reading the content folders..."))
        sd = g.sider_dir

        def work(progress):
            return R.scan(sd, ini)

        def done(idx):
            self.app.busy(False)
            self.idx = idx
            self._scanned_once = True
            self.load()

        def failed(tb):
            self.app.busy(False)
            self.say(_("Reading the folders failed:") + "\n" + tb.splitlines()[-1], "err")
        run_job(work, done, failed)

    def load(self):
        self.ini = self.app.ini()
        self.dirty = False
        self.fill()

    def entries(self):
        return self.ini.entries(self.KEY) if self.ini else []

    def fill(self):
        self._loading = True
        self.tree.clear()
        if not self.ini:
            self._loading = False
            return
        self.conf = R.conflicts(self.idx, self.ini) if self.idx else []
        wins, loses = {}, {}
        for c in self.conf:
            wins[c.winner] = wins.get(c.winner, 0) + 1
            for l in c.losers:
                loses[l] = loses.get(l, 0) + 1
        # the world in the game now, as sider.ini on disk has it (not the ticks not applied yet):
        # its row is green with a label (mato 15.10.: "clearly marked green", not a line of text)
        self.live = set(WL.live(self.app.game)) if self.app.game.ok() else set()
        for n, e in enumerate(self.entries()):
            k = norm(e.value)
            info = self.idx.get(k)
            it = QTreeWidgetItem()
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsDragEnabled)
            it.setFlags(it.flags() & ~Qt.ItemIsDropEnabled)
            it.setCheckState(0, Qt.Checked if e.enabled else Qt.Unchecked)
            it.setText(1, str(n + 1))
            it.setText(2, e.value)
            it.setData(2, Qt.UserRole, e.index)
            if info is not None:
                if not info.exists:
                    it.setText(3, _("missing on disk"))
                    it.setForeground(3, QBrush(QColor(theme.DANGER)))
                else:
                    kinds = sorted(info.kinds.items(), key=lambda x: -x[1])
                    it.setText(3, ", ".join(_(k) for k, _n in kinds[:3]))
                    it.setText(4, str(len(info.files)))
                    it.setText(5, R.human(info.size))
            w, l = wins.get(k, 0), loses.get(k, 0)
            if w or l:
                it.setText(6, ("▲%d" % w if w else "") + ("  ▼%d" % l if l else ""))
                it.setToolTip(6, _("wins %d file(s), loses %d file(s) to folders above it") % (w, l))
                if l:
                    it.setForeground(6, QBrush(QColor(theme.WARN)))
            it.setText(7, e.note)
            if not e.enabled:
                for c in range(1, 8):
                    it.setForeground(c, QBrush(QColor(theme.SUBTLE)))
            if self.is_live(e):
                self.mark_live(it, e)
            self.tree.addTopLevelItem(it)
        self._loading = False
        self.filter()
        on = sum(1 for e in self.entries() if e.enabled)
        self.foot.setText(_("%d folders listed, %d switched on, %d files overridden by a folder above.")
                          % (len(self.entries()), on, len(self.conf)))
        self.mark()

    def world_of(self, e):
        """the world (_FL26... folder in livecpk) a line loads, or None"""
        if e is None:
            return None
        p = root_path(self.app.game.sider_dir, e.value)
        name = os.path.basename(p)
        if WL.is_world(name) and os.path.normcase(os.path.dirname(p)) == os.path.normcase(
                os.path.normpath(self.app.game.livecpk_dir)):
            return name
        return None

    def is_live(self, e):
        return self.world_of(e) in self.live

    def mark_live(self, it, e):
        """the live world's row: green all across, its name in bold, IN THE GAME NOW in the Note
        column (the theme's ok colours, the ones of Home's green card)"""
        bg, fg = QBrush(QColor(theme.OK_BG)), QBrush(QColor(theme.GOOD))
        for c in range(self.tree.columnCount()):
            it.setBackground(c, bg)
        f = QFont(it.font(2))
        f.setBold(True)
        it.setFont(2, f)
        it.setFont(7, f)
        for c in (1, 2, 7):
            it.setForeground(c, fg)
        it.setText(7, "\u25cf " + _("IN THE GAME NOW") + ("  \u00b7  " + e.note if e.note else ""))
        tip = _("This is the world the game uses now.")
        for c in range(self.tree.columnCount()):
            it.setToolTip(c, tip)
        it.setData(0, Qt.UserRole + 1, "live")

    def filter(self):
        q = self.search.text().strip().lower()
        worlds = self.show_worlds.isChecked()
        only = self.only_on.isChecked()
        for i in range(self.tree.topLevelItemCount()):
            it = self.tree.topLevelItem(i)
            v = it.text(2)
            base = norm(v).split("\\")[-1]
            hide = (q and q not in v.lower()) or (not worlds and base.startswith(WORLD_PREFIX)) or \
                   (only and it.checkState(0) != Qt.Checked)
            it.setHidden(bool(hide))

    def mark(self):
        self.btn_apply.setEnabled(self.dirty)
        self.btn_discard.setEnabled(self.dirty)
        if self.dirty:
            self.say(_("Changes not written yet: press Apply."), "warn")
        else:
            self.say("")

    # ---- editing (in memory until Apply) ----
    def ticked(self, it, col):
        if self._loading or col != 0:
            return
        e = self._entry(it)
        if e:
            self.ini.set_enabled(e, it.checkState(0) == Qt.Checked)
            self.dirty = True
            # not now: Qt is still inside the ticked row's setData, and fill() clears the list,
            # so the row is gone under it -- Mod Studio closed with Qt6Widgets.dll c0000005
            # (Discord, vmican 15.10.)
            QTimer.singleShot(0, self.fill)

    def _entry(self, it):
        idx = it.data(2, Qt.UserRole)
        return next((e for e in self.entries() if e.index == idx), None)

    def dropped(self):
        values = [self.tree.topLevelItem(i).text(2) for i in range(self.tree.topLevelItemCount())]
        self.ini.reorder(self.KEY, values)
        self.dirty = True
        self.fill()

    def shift(self, d):
        sel = [self._entry(it) for it in self.tree.selectedItems()]
        sel = [e for e in sel if e]
        if not sel:
            return
        vals = [e.value for e in sel]
        order = [e.value for e in self.entries()]
        chosen = set(id(v) for v in vals)
        names = [e.value for e in self.entries()]
        idxs = sorted(names.index(v) for v in vals)
        if d < 0:
            for i in idxs:
                j = max(0, i + max(d, -i))
                names.insert(j, names.pop(i))
        else:
            for i in reversed(idxs):
                j = min(len(names) - 1, i + d)
                names.insert(j, names.pop(i))
        self.ini.reorder(self.KEY, names)
        self.dirty = True
        self.fill()
        for i in range(self.tree.topLevelItemCount()):
            it = self.tree.topLevelItem(i)
            if it.text(2) in vals:
                it.setSelected(True)

    def add_folder(self):
        g = self.app.game
        d = pick_dir(self, "A content folder (it holds common\\...)", g.livecpk_dir)
        if not d:
            return
        d = os.path.normpath(d)
        try:
            rel = os.path.relpath(d, g.sider_dir)
            value = rel if not rel.startswith("..") else d
        except ValueError:
            value = d
        if not value.startswith(".") and not os.path.isabs(value):
            value = ".\\" + value
        if self.ini.find(self.KEY, value):
            self.say(_("That folder is already in the list."), "warn")
            return
        self.ini.add(self.KEY, value, where="first")
        self.idx[norm(value)] = R.scan_root(d, value)
        self.dirty = True
        self.fill()

    def remove_line(self):
        e = self._current()
        if e and ask(self, "Remove", _("Take %s out of sider.ini? The folder stays on disk.") % e.value):
            self.ini.remove(e)
            self.dirty = True
            self.fill()

    def delete_folder(self):
        e = self._current()
        if not e:
            return
        p = root_path(self.app.game.sider_dir, e.value)
        if not os.path.isdir(p):
            return
        if self.world_of(e):
            # a world is never deleted for good from here: Delete world keeps it (mato 15.10.)
            self.delete_world()
            return
        if not p.lower().startswith(self.app.game.sider_dir.lower()):
            self.say(_("Only folders inside SiderAddons can be deleted from here."), "err")
            return
        if ask(self, "Delete", _("Delete the folder %s and everything in it? This cannot be undone.") % p):
            shutil.rmtree(p, ignore_errors=True)
            self.ini.remove(e)
            self.idx.pop(norm(e.value), None)
            self.app.save_ini(self.ini, "deleted content folder %s" % e.value)
            self.load()

    def apply(self):
        if not self.dirty:
            return
        self.app.save_ini(self.ini, "content folders changed")
        self.dirty = False
        self.load()

    # ---- inspector ----
    def _current(self):
        it = self.tree.currentItem()
        return self._entry(it) if it else None

    def inspect(self):
        e = self._current()
        self.i_conf.clear()
        w = self.world_of(e)
        self.b_wren.setVisible(bool(w))
        self.b_wdel.setVisible(bool(w))
        if not e:
            self.i_name.setText("")
            self.i_path.setText("")
            self.i_kinds.setText("")
            return
        k = norm(e.value)
        info = self.idx.get(k)
        self.i_name.setText(e.value.split("\\")[-1])
        self.i_path.setText(root_path(self.app.game.sider_dir, e.value))
        if info and info.exists:
            kinds = sorted(info.kinds.items(), key=lambda x: -x[1])
            self.i_kinds.setText("<br>".join("%s: %d" % (_(kk), n) for kk, n in kinds) +
                                 "<br><br>%s, %d %s" % (R.human(info.size), len(info.files), _("files")))
        else:
            self.i_kinds.setText(_("The folder is not on disk."))
        rows = 0
        for c in self.conf:
            if c.winner == k or k in c.losers:
                it = QTreeWidgetItem([c.path, self.idx[c.winner].value.split("\\")[-1]
                                      if c.winner in self.idx else c.winner])
                if c.winner != k:
                    it.setForeground(0, QBrush(QColor(theme.WARN)))
                self.i_conf.addTopLevelItem(it)
                rows += 1
                if rows >= 500:
                    break

    def open_folder(self):
        e = self._current()
        if e:
            p = root_path(self.app.game.sider_dir, e.value)
            if os.path.isdir(p):
                os.startfile(p)

    def menu(self, pos):
        it = self.tree.itemAt(pos)
        if not it:
            return
        m = QMenu(self)
        m.addAction(_("Open folder"), self.open_folder)
        m.addAction(_("Move to top"), lambda: self.shift(-10000))
        m.addAction(_("Move to bottom"), lambda: self.shift(10000))
        m.addSeparator()
        m.addAction(_("Remove from the list"), self.remove_line)
        if self.world_of(self._entry(it)):
            m.addSeparator()
            m.addAction(_("Rename world..."), lambda: self.rename_world())
            m.addAction(_("Delete world..."), lambda: self.delete_world())
        m.exec(self.tree.viewport().mapToGlobal(pos))

    # ---- worlds: rename, delete (0.2.4, mato 15.10.) ----
    def _world_ready(self, title, w=None):
        """the selected row's world (or w, a card of My world), when it can be changed now: game
        closed, no ticks waiting"""
        w = w or self.world_of(self._current())
        if not w:
            return None
        if not os.path.isdir(os.path.join(self.app.game.livecpk_dir, w)):
            error(self, title, _("The folder of %s is not on disk.") % w)
            return None
        g, s = self.app.game.running()
        if g or s:
            error(self, title, _("Close the game first: it has the world's files open."))
            return None
        if self.dirty:
            error(self, title, _("You have changes in this list that are not written yet: press Apply or "
                                 "Discard first."))
            return None
        if not can_write(self, self.app.game):
            return None
        return w

    def delete_world(self, world=None):
        """world: the one of a card of My world, else the selected row's; True when it is deleted"""
        title = "Delete world"
        w = self._world_ready(title, world)
        if not w:
            return
        if w in WL.live(self.app.game):
            # the safe way: the world in the game is never taken out from under it (worlds.delete)
            error(self, title, _("%s is the world in the game now (the green one).\n\nSwitch another world on "
                                 "first (tick it here, untick this one, press Apply), or just untick this "
                                 "one and press Apply. Then you can delete it.") % w)
            return
        named = WL.in_modules(self.app.game) == w
        where = os.path.join(os.path.basename(self.app.game.sider_dir), "ModStudio", "backups", "worlds", w)
        text = (_("Delete the world %s?") % w + "\n\n" +
                _("It goes out of the game: its folder, its kits and scoreboards, and its lines in sider.ini "
                  "and in the kit and scoreboard lists.") + "\n\n" +
                _("Nothing is lost: it is all kept in %s, and Restore points > Put this copy back brings "
                  "it back. Mod Studio keeps the last %d copies of each world.") % (where, WL.KEEP) + "\n\n" +
                _("Your leagues stay in Mod Studio (your saved world file is not deleted), so you can "
                  "build it again."))
        if named:
            text += "\n\n" + _("Mod Studio's modules still read this world. After it is deleted the game "
                                "has no world of yours until you switch one on (Build and install, or "
                                "Import your world).")
        if not ask(self, title, text):
            return
        self.app.busy(True, _("Deleting %s ...") % w)
        try:
            folder, _info = WL.delete(self.app.game, w)
        except WL.WorldError as e:
            self.app.busy(False)
            error(self, title, str(e))
            return
        except OSError as e:
            self.app.busy(False)
            if not denied(self, e):
                error(self, title, _("It stopped:") + "\n\n" + str(e) + "\n\n" +
                      _("What was done so far can be put back from Restore points."))
            self.after_world_change()
            return
        self.app.busy(False)
        self.after_world_change()
        self.say(_("%s is deleted. It is kept in %s: Restore points > Put this copy back brings it back.")
                 % (w, folder), "ok")
        return True

    def rename_world(self, world=None):
        """world: the one of a card of My world, else the selected row's; the new name when done"""
        from PySide6.QtWidgets import QInputDialog
        title = "Rename world"
        w = self._world_ready(title, world)
        if not w:
            return
        new, ok = QInputDialog.getText(self, _(title), _("New name for %s (it must start with _FL26; "
                                                          "letters, digits, - and _ only):") % w, text=w)
        new = (new or "").strip()
        if not ok or not new or new == w:
            return
        why = WL.check_name(self.app.game, new, w)
        if why:
            error(self, title, _(why))
            return
        if not ask(self, title, _("Rename %s to %s?") % (w, new) + "\n\n" +
                   _("Everything that points at the world is changed with it: its line in sider.ini (same "
                     "place, on or off as now), its kits and scoreboards and their lines, its world file, "
                     "and your leagues in Mod Studio.") + "\n\n" +
                   _("A career you play with it keeps working: the game never sees the world's name, only "
                     "the files in it, and they do not change.") + "\n\n" +
                   _("The small files it changes are kept first in Restore points; Put this copy back "
                     "renames it back.")):
            return
        try:
            WL.rename(self.app.game, w, new)
        except WL.WorldError as e:
            error(self, title, str(e))
            return
        except OSError as e:
            if not denied(self, e):
                error(self, title, _("It stopped, nothing was renamed:") + "\n\n" + str(e))
            return
        rename_recipe(self.app, w, new)
        self.after_world_change()
        self.say(_("%s is now %s.") % (w, new), "ok")
        return new

    def after_world_change(self):
        self.app.bus.ini_changed.emit()
        self.app.bus.content_changed.emit()
        self.idx = {}
        self.rescan()
