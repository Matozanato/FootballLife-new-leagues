"""Embedded trophy assignments, reusing the dialog's temporary editing semantics."""
import os
from copy import deepcopy
from shiboken6 import isValid
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTreeWidget, QLineEdit, QPushButton,
                              QFileDialog, QHeaderView, QSizePolicy, QLabel)
import leaguebuilder as B
import lbtrophies
from .. import filecache
from ..i18n import _, tr
from ..ui import hint, row, error, run_job
from .builder import BuilderPage, _IdItem

HELP = ("Pair a trophy folder of your own with a competition: Build copies it into the world and FL26's "
        "Entrance.lua shows that trophy in the competition's matches and its final. The folder is laid out "
        "as FL26's content\\Entrance ones (the files at its top or in a phase folder, the final's in "
        "Final; they replace the AFC Champions League trophy's files). A competition with no folder keeps "
        "what it had.")


def mapping(recipe):
    value = recipe.get("trophies")
    return {} if value is None else value if isinstance(value, dict) else None


def canonical(values):
    return {str(k): deepcopy(v) for k, v in (values or {}).items()}


def slot(values, cid):
    return deepcopy([(k, v) for k, v in (values or {}).items() if str(k) == cid])


def value(values, cid):
    return cid in values, values.get(cid)


def competition_rows(db, base):
    if not db:
        return []
    paths = [os.path.join(p, "CompetitionRegulation.bin") for p in (db, base) if p]
    return filecache.by_files("trophy-competition-rows", paths, lambda: B.competition_ids(db, base))


class TrophyItem(_IdItem):
    def __lt__(self, other):
        if self.treeWidget() and self.treeWidget().sortColumn() == 2:
            def order(text):
                return (0, int(text)) if text.isdigit() else (1, text.casefold())
            return order(self.text(2)) < order(other.text(2))
        return super().__lt__(other)


class TrophyEditor(QWidget):
    """Shared controls; only a temporary mapping, never a mutable Project reference."""
    changed = Signal()

    def __init__(self, trophies=None, rows=(), long_help=False):
        super().__init__()
        self.trophies = canonical(trophies)
        self.rows = rows
        self._selected = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if long_help:
            layout.addWidget(hint(_(HELP)))
        self.note = hint("")
        layout.addWidget(self.note)
        self.find = QLineEdit()
        self.find.setPlaceholderText(_("Find..."))
        self.find.textChanged.connect(self.fill)
        layout.addWidget(self.find)
        self.table = QTreeWidget()
        self.table.setHeaderLabels([_("Name"), _("Kind"), _("Competition ID"), _("Regulation IDs"), _("Trophy folder")])
        self.table.setRootIsDecorated(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.setMinimumSize(0, 0)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        self.table.itemDoubleClicked.connect(lambda *_args: self.pick())
        self.table.currentItemChanged.connect(self.selection_changed)
        for col in (1, 2, 3):
            self.table.header().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.table.header().setSectionResizeMode(0, QHeaderView.Interactive)
        self.table.setColumnWidth(0, 230)
        self.table.header().setSectionResizeMode(4, QHeaderView.Stretch)
        layout.addWidget(self.table, 1)
        self.b_pick = QPushButton(_("Pick a trophy folder..."))
        self.b_pick.clicked.connect(self.pick)
        self.b_clear = QPushButton(_("No trophy of its own"))
        self.b_clear.clicked.connect(self.clear)
        layout.addWidget(row(self.b_pick, self.b_clear, "stretch", stretch=False))
        self.warning = hint("")
        self.warning.hide()
        layout.addWidget(self.warning)
        self.fill()
        self.table.sortByColumn(2, Qt.AscendingOrder)

    def current(self):
        item = self.table.currentItem()
        return item.data(0, Qt.UserRole) if item else None

    def selection_changed(self, item, *_args):
        cid = item.data(0, Qt.UserRole) if item else None
        if cid is not None:
            self._selected = cid
        self.b_pick.setEnabled(cid is not None)
        self.b_clear.setEnabled(cid in self.trophies)

    def fill(self, *_args):
        selected = self.current() or self._selected
        query = self.find.text().strip().casefold()
        self.table.blockSignals(True)
        self.table.clear()
        known, selected_item = set(), None
        lines = []
        for cid, regs, name, kind, _new in self.rows:
            cid = str(cid)
            known.add(cid)
            lines.append((cid, [name, _(kind), cid, ", ".join(map(str, regs)), str(self.trophies.get(cid, ""))]))
        lines += [(cid, [_("(not in these tables)"), "", cid, "", str(folder)])
                  for cid, folder in self.trophies.items() if cid not in known]
        for cid, line in lines:
            if query and query not in " ".join(line).casefold():
                continue
            item = TrophyItem(line)
            item.setData(0, Qt.UserRole, cid)
            for col, text in enumerate(line):
                item.setToolTip(col, text)
            self.table.addTopLevelItem(item)
            if cid == selected:
                selected_item = item
        if selected_item is not None:
            self.table.setCurrentItem(selected_item)
        self.table.blockSignals(False)
        self.selection_changed(self.table.currentItem())
        # Do not stat asset folders while filtering/navigating: stored paths may
        # point to slow or disconnected drives. Pick/Apply use the real backend
        # filesystem validator; untouched legacy references remain preserved.
        unavailable = [cid for cid, path in self.trophies.items() if
                       not cid.isdigit() or cid not in known or not isinstance(path, str) or not path]
        self.warning.setText(_("Stored trophy references need review: %s. They are preserved until you explicitly change or clear them.") % ", ".join(sorted(unavailable)))
        self.warning.setVisible(bool(unavailable))

    def set_values(self, values):
        self.trophies = deepcopy(values)
        self.fill()

    def pick(self):
        cid = self.current()
        if cid is None:
            return
        old = self.trophies.get(cid)
        folder = QFileDialog.getExistingDirectory(self, _("Pick a trophy folder..."), old if isinstance(old, str) else "")
        if not folder:
            return
        problems = lbtrophies.problems({"trophies": {cid: folder}})
        if problems:
            error(self, "Trophies", "\n".join(tr(line) for line in problems))
            return
        self.trophies[cid] = os.path.normpath(folder)
        self.fill()
        self.changed.emit()

    def clear(self):
        cid = self.current()
        if cid is not None and cid in self.trophies:
            self.trophies.pop(cid)
            self.fill()
            self.changed.emit()

    def view_state(self):
        return {"search": self.find.text(), "selected": self.current() or self._selected}

    def restore_view(self, state):
        self._selected = state.get("selected")
        self.find.setText(state.get("search", ""))
        self.fill()


class Trophies(BuilderPage):
    title = "Trophies"
    hint = "Trophy assignments for the selected world. A competition with no folder keeps its existing trophy."
    help = HELP

    def __init__(self, app):
        super().__init__(app)
        self.discard_button = self.action("Discard changes", self.discard)
        self.apply_button = self.action("Apply", self.apply, "primary")
        self.world_label = QLabel()
        self.world_label.setObjectName("cardtitle")
        self.outer.addWidget(self.world_label)
        self.editor = TrophyEditor()
        self.outer.addWidget(self.editor, 1)
        self.status = hint("")
        self.outer.addWidget(self.status)
        self._owner = None
        self._key = None
        self._initial, self._sources, self._drafts = {}, {}, {}
        self._draft_base = None
        self._metadata = None
        self._token = 0
        self.editor.changed.connect(self.update_buttons)
        self._timer = QTimer(self, singleShot=True, interval=0, timeout=self.refresh)
        self.project.changed.connect(self.queue_refresh)
        app.bus.content_changed.connect(self.queue_refresh)
        app.bus.game_changed.connect(self.queue_refresh)
        self.update_buttons()

    def key(self):
        path = self.project.path
        return (os.path.normcase(os.path.abspath(path)) if path else None, self.project.recipe.get("world", ""))

    def dirty_keys(self):
        return {cid for cid in self._initial.keys() | self.editor.trophies.keys()
                if value(self._initial, cid) != value(self.editor.trophies, cid)}

    def capture(self):
        if self._key is None:
            return
        if self.dirty_keys():
            self._drafts[self._key] = deepcopy(dict(initial=self._initial, sources=self._sources,
                                                   values=self.editor.trophies, base=self._draft_base,
                                                   view=self.editor.view_state()))
        else:
            self._drafts.pop(self._key, None)

    def has_drafts(self):
        self.capture()
        return bool(self._drafts)

    def queue_refresh(self):
        if self._owner is not None and (self.isVisible() or self._owner is not self.project.recipe):
            self._timer.start()

    def refresh(self):
        if not hasattr(self, "editor"):
            return
        self._timer.stop()
        raw = mapping(self.project.recipe)
        current = canonical(raw)
        key = self.key()
        if self._owner is not self.project.recipe:
            self.capture()
            self._owner, self._key = self.project.recipe, key
            saved = self._drafts.get(key)
            self._initial = deepcopy(current)
            self._sources = {cid: slot(raw, cid) for cid in current}
            self._draft_base = self.project.base
            self.editor.set_values(current)
            self.editor.restore_view({})
            if saved:
                dirty = {cid for cid in saved["initial"].keys() | saved["values"].keys()
                         if value(saved["initial"], cid) != value(saved["values"], cid)}
                for cid in dirty:
                    for target, source in ((self._initial, saved["initial"]), (current, saved["values"])):
                        if cid in source:
                            target[cid] = deepcopy(source[cid])
                        else:
                            target.pop(cid, None)
                    self._sources[cid] = deepcopy(saved["sources"].get(cid, []))
                self._draft_base = saved["base"]
                self.editor.set_values(current)
                self.editor.restore_view(saved["view"])
            self._metadata = None
        else:
            if key != self._key:
                self.capture()
                saved = self._drafts.pop(self._key, None)
                self._key = key
                if saved:
                    self._drafts[key] = saved
            dirty = self.dirty_keys()
            values = deepcopy(self.editor.trophies)
            for cid in self._initial.keys() | current.keys():
                if cid in dirty:
                    continue
                for target in (values, self._initial):
                    if cid in current:
                        target[cid] = deepcopy(current[cid])
                    else:
                        target.pop(cid, None)
                self._sources[cid] = slot(raw, cid)
            if not dirty:
                self._draft_base = self.project.base
            if values != self.editor.trophies:
                self.editor.set_values(values)
        self.world_label.setText(_("Editing world: %s") % (self.project.recipe.get("world") or "—"))
        self.say(_("Stored trophy configuration is invalid. It has been preserved; fix the recipe before applying trophy changes.") if raw is None else "")
        self.load_rows()
        self.update_buttons()

    def database(self):
        sider = getattr(getattr(self.app, "game", None), "sider_dir", None)
        world = self.project.recipe.get("world")
        if sider and world:
            db = os.path.join(sider, "livecpk", world, "common", "etc", "pesdb")
            if os.path.isfile(os.path.join(db, "CompetitionRegulation.bin")):
                return db
        return self.project.base

    def load_rows(self):
        db, base = self.database(), self.project.base
        paths = [os.path.join(p, "CompetitionRegulation.bin") for p in (db, base) if p]
        signature = db, base, tuple(filecache.stamp(p) for p in paths)
        if signature == self._metadata:
            return
        self._metadata = signature
        self._token += 1
        token, owner = self._token, self.project.recipe
        self.editor.rows = []
        self.editor.fill()
        self.editor.note.setText(_("Loading competitions..."))

        def done(rows):
            if not isValid(self) or token != self._token or owner is not self.project.recipe:
                return
            if (db, base) != (self.database(), self.project.base) or signature[2] != tuple(filecache.stamp(p) for p in paths):
                self._metadata = None
                self._timer.start()
                return
            self.editor.rows = rows
            self.editor.fill()
            self.editor.note.setText(_("The world's new cups are listed after its first Build.") if db == base else
                                     _("Competitions from this world's built tables."))

        def failed(trace):
            if isValid(self) and token == self._token and owner is self.project.recipe:
                self._metadata = None  # retry a transient read failure on the next visit
                self.editor.note.setText(_("Competition tables could not be read. Stored trophy assignments are preserved. %s") % trace.strip().splitlines()[-1])
        if db:
            run_job(lambda _progress: competition_rows(db, base), done, failed)
        else:
            self.editor.note.setText(_("The game's tables are not unpacked yet."))

    def update_buttons(self):
        dirty = bool(self.dirty_keys())
        self.discard_button.setEnabled(dirty)
        self.apply_button.setEnabled(dirty and mapping(self.project.recipe) is not None)
        text = (_("Unapplied trophy changes. Apply keeps them in this world's recipe; Build copies the assets into the world.") if dirty else
                _("No unapplied trophy changes."))
        others = [key[1] for key in self._drafts if key != self._key]
        if others:
            text += "\n" + _("Other worlds have unapplied trophy changes: %s.") % ", ".join(others)
        self.status.setText(text)

    def apply(self):
        if self._owner is not self.project.recipe:
            self.refresh()
            return
        self.refresh()
        dirty = self.dirty_keys()
        raw = mapping(self.project.recipe)
        if not dirty or raw is None:
            return
        if self._draft_base != self.project.base:
            self.say(_("The game tables changed. Your trophy draft is kept; Discard changes reloads the current world."), "err")
            return
        patches = {}
        for cid in dirty:
            desired = value(self.editor.trophies, cid)
            if desired == value(canonical(raw), cid):
                continue
            if slot(raw, cid) != self._sources.get(cid, []):
                self.say(_("Trophy assignments changed elsewhere. Your draft is kept; Discard changes reloads the current world."), "err")
                return
            if desired[0]:
                path = desired[1]
                if not isinstance(path, str):
                    self.say(_("The trophy folder is invalid. Your draft is kept."), "err")
                    return
                problems = lbtrophies.problems({"trophies": {cid: path}})
                if problems:
                    self.say("\n".join(tr(line) for line in problems), "err")
                    return
            patches[cid] = desired
        result = dict(raw)
        for cid, (present, path) in patches.items():
            aliases = [k for k in result if str(k) == cid]
            if present:
                if len(aliases) > 1:
                    self.say(_("This competition has ambiguous trophy keys. Clear its assignment explicitly before assigning another folder."), "err")
                    return
                result[aliases[0] if aliases else cid] = path
            else:
                for key in aliases:
                    result.pop(key)
        if patches:
            if result:
                self.project.recipe["trophies"] = result
            else:
                self.project.recipe.pop("trophies", None)
        self._initial = canonical(result)
        self._sources = {cid: slot(result, cid) for cid in self._initial}
        self.editor.set_values(self._initial)
        self.capture()
        self.say("")
        self.update_buttons()
        if patches:
            self.project.touch()

    def discard(self):
        if self._owner is not self.project.recipe:
            self.refresh()
            return
        raw = mapping(self.project.recipe)
        self._initial = canonical(raw)
        self._sources = {cid: slot(raw, cid) for cid in self._initial}
        self._draft_base = self.project.base
        self.editor.set_values(self._initial)
        self.capture()
        self.say("")
        self.refresh()

    def shown(self):
        self.refresh()
