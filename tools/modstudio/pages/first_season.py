"""Integrated first-season European clubs view; all edits enter Continental's draft."""
from copy import deepcopy
from shiboken6 import isValid
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLineEdit, QListWidget,
                              QListWidgetItem, QAbstractItemView, QPushButton, QLabel,
                              QTabWidget, QSplitter, QSizePolicy)
import leaguebuilder as B
from .. import qualification_data as Q
from ..i18n import _
from ..ui import hint, row, run_job


class FirstSeasonEditor(QWidget):
    def __init__(self, qualification):
        super().__init__()
        self.qualification = qualification
        self.owner = qualification.owner
        self.labels, self.aliases = {}, {}
        self._signature = None
        self._loading = False
        self._token = 0
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        back = QPushButton(_("Back to Qualification"))
        back.clicked.connect(qualification.back_to_sources)
        controls = row(back, "stretch", stretch=False)
        layout.addWidget(controls)
        self.note = _("Initial participants of a new career only. These are separate from subsequent-season qualification places. The game automatically fills the remaining slots.")
        back.setToolTip(self.note + "\n" + _("When qualifying is enabled, manual clubs beyond the direct slots enter the existing qualifying rounds. Build resolves those rounds."))
        splitter = QSplitter(Qt.Horizontal)
        left = QWidget()
        pool_layout = QVBoxLayout(left)
        pool_layout.setContentsMargins(0, 0, 0, 0)
        self.search = QLineEdit()
        self.search.setPlaceholderText(_("Club, league, country or team ID"))
        self.search.textChanged.connect(self.fill_pool)
        pool_layout.addWidget(row(QLabel(_("Available clubs")), self.search, stretch=False))
        self.pool = QListWidget()
        self.pool.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.pool.setMinimumSize(0, 0)
        self.pool.setSizePolicy(self.pool.sizePolicy().horizontalPolicy(), QSizePolicy.Ignored)
        pool_layout.addWidget(self.pool, 1)
        self.add_button = QPushButton(_("Add selected clubs"))
        self.add_button.clicked.connect(self.add_selected)
        controls.layout().insertWidget(1, self.add_button)
        splitter.addWidget(left)
        right = QWidget()
        picked_layout = QVBoxLayout(right)
        picked_layout.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        self.lists = []
        for _key, title in B.EUROPE_FIRST:
            view = QListWidget()
            view.setMinimumSize(0, 0)
            view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
            view.setSelectionMode(QAbstractItemView.ExtendedSelection)
            self.tabs.addTab(view, _(title))
            self.lists.append(view)
        picked_layout.addWidget(self.tabs, 1)
        self.counter = QLabel()
        controls.layout().insertWidget(2, self.counter, 1)
        self.remove_button = QPushButton(_("Remove selected clubs"))
        self.remove_button.clicked.connect(self.remove_selected)
        controls.layout().insertWidget(2, self.remove_button)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)
        self.warning = hint("")
        layout.addWidget(self.warning)
        self.tabs.currentChanged.connect(self.update_controls)

    def recipe(self):
        return self.owner.preview()

    def show_warning(self, text):
        self.warning.setText(text)
        self.warning.setVisible(bool(text))

    def selected(self):
        first = self.recipe().get("europe_first") or {}
        return [list(first.get(k) or []) for k, _title in B.EUROPE_FIRST]

    def activate(self):
        recipe = self.recipe()
        # Small labels/source projection, never players or a complete recipe copy.
        leagues = [{k: deepcopy(L[k]) for k in ("name", "country", "clubs", "club_names", "above", "others", "exhibition") if k in L}
                   | {"game_clubs": [{k: g[k] for k in ("at", "id") if k in g} |
                                     ({"swap": {}} if isinstance(g.get("swap"), dict) else {})
                                     for g in L.get("game_clubs") or []]}
                   for L in recipe.get("leagues") or []]
        signature = (self.owner.project.base, self.qualification.table_stamp(), leagues)
        if signature != self._signature:
            self._signature = deepcopy(signature)
            self._token += 1
            token, owner, base = self._token, self.owner.project.recipe, self.owner.project.base
            self._loading = True
            self.show_warning(_("Loading eligible clubs..."))

            def done(result):
                if not isValid(self) or token != self._token or owner is not self.owner.project.recipe or base != self.owner.project.base:
                    return
                self._loading = False
                self.labels, self.aliases = result
                self.refresh()

            def failed(trace):
                if isValid(self) and token == self._token and owner is self.owner.project.recipe and base == self.owner.project.base:
                    self._loading = False
                    self.labels, self.aliases = {}, {}
                    self.refresh()
                    self.show_warning(_("Club data could not be read. Stored selections are preserved. %s") % trace.strip().splitlines()[-1])
            if base:
                run_job(lambda _progress: Q.club_choices({"leagues": leagues}, base), done, failed)
            else:
                failed(_("The game's tables are not unpacked yet."))
        self.refresh()

    def refresh(self):
        picked = self.selected()
        unknown = []
        seen = set()
        duplicates = []
        for index, view in enumerate(self.lists):
            view.clear()
            for number, ref in enumerate(picked[index]):
                lookup = Q.reference_key(ref)
                label = self.labels.get(lookup)
                if label is None:
                    unknown.append(str(ref))
                    label = _("Unresolved reference — %s (preserved)") % str(ref)
                canonical = Q.canonical_ref(ref, self.aliases)
                if canonical in seen:
                    duplicates.append(str(ref))
                seen.add(canonical)
                item = QListWidgetItem(label)
                item.setData(Qt.UserRole, number)
                item.setToolTip(str(ref))
                view.addItem(item)
        enabled = bool(self.recipe().get("uecl", True))
        self.tabs.setTabEnabled(2, enabled)
        if not enabled and self.tabs.currentIndex() == 2:
            self.tabs.setCurrentIndex(0)
        warnings = []
        if self._loading:
            warnings.append(_("Loading eligible clubs..."))
        elif unknown:
            warnings.append(_("Unresolved saved references are preserved until explicitly removed: %s") % ", ".join(unknown))
            warnings.append(_("Build may reject unresolved references. Review or remove them explicitly before building."))
        if duplicates:
            warnings.append(_("Duplicate saved club references require review: %s") % ", ".join(duplicates))
        if not enabled:
            warnings.append(_("Conference League is disabled; its stored first-season clubs are retained and reserved."))
        self.show_warning("\n".join(warnings))
        self.fill_pool()
        self.update_controls()

    def fill_pool(self, *_args):
        self.pool.clear()
        taken = {Q.canonical_ref(ref, self.aliases) for refs in self.selected() for ref in refs}
        query = self.search.text().strip().casefold()
        for ref, label in sorted(self.labels.items(), key=lambda pair: pair[1].casefold()):
            if Q.canonical_ref(ref, self.aliases) in taken or (query and query not in label.casefold()):
                continue
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, ref)
            self.pool.addItem(item)

    def update_controls(self, *_args):
        index = max(0, self.tabs.currentIndex())
        count = len(self.selected()[index])
        self.counter.setText(_("Manually selected: %d / %d\nAutomatic fill: up to %d") % (count, B.FIRST_MAX, max(0, B.FIRST_MAX - count)))
        self.counter.setToolTip(self.note)
        self.add_button.setEnabled(not self._loading and bool(self.labels) and count < B.FIRST_MAX)
        self.remove_button.setEnabled(not self._loading and bool(count))

    def add_selected(self):
        index = self.tabs.currentIndex()
        if index < 0 or self._loading or (index == 2 and not self.recipe().get("uecl", True)):
            return
        picked = self.selected()
        used = {Q.canonical_ref(ref, self.aliases) for rows in picked for ref in rows}
        incoming = []
        for item in self.pool.selectedItems():
            ref = item.data(Qt.UserRole)
            canonical = Q.canonical_ref(ref, self.aliases)
            if canonical not in used:
                used.add(canonical)
                incoming.append(ref)
        if len(picked[index]) + len(incoming) > B.FIRST_MAX:
            self.show_warning(_("Selection exceeds the competition's capacity; nothing was added."))
            return
        if incoming:
            key = B.EUROPE_FIRST[index][0]
            self.owner.set_qualification(("qualification", "first", key), (True, picked[index] + incoming))
            self.refresh()

    def remove_selected(self):
        index = self.tabs.currentIndex()
        if index < 0 or self._loading or (index == 2 and not self.recipe().get("uecl", True)):
            return
        drop = {it.data(Qt.UserRole) for it in self.lists[index].selectedItems()}
        if drop:
            rows = [ref for i, ref in enumerate(self.selected()[index]) if i not in drop]
            self.owner.set_qualification(("qualification", "first", B.EUROPE_FIRST[index][0]), (bool(rows), rows if rows else None))
            self.refresh()

    def view_state(self):
        return {"search": self.search.text(), "tab": self.tabs.currentIndex()}

    def restore_view(self, state):
        self.search.setText(state.get("search", ""))
        self.tabs.setCurrentIndex(state.get("tab", 0))
