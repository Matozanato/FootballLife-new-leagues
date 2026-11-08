"""One integrated qualification view and ranking-preview workflow for all confederations."""
from copy import deepcopy
from shiboken6 import isValid
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QTreeWidget,
                              QTreeWidgetItem, QLabel, QPushButton, QCheckBox, QScrollArea,
                              QSplitter, QDialog, QDialogButtonBox,
                              QListWidget, QListWidgetItem, QAbstractItemView,
                              QComboBox, QSizePolicy)
import leaguebuilder as B
import fl26world as W
from .. import qualification_data as Q
from .. import conmebol_allocation as A
from ..editor_containers import EditorStack
from ..i18n import _
from ..ui import hint, row, run_job, Fold, error
from .qualification_presentation import PresetPreview, AllocationOverview, allocation_rows
from .builder import EuropeTable


class RankingPreviewDialog(QDialog):
    """Shared calculations/confirmation; each tool supplies its own presentation."""
    title_text = "Generate qualification preset"
    intro_text = "Rank strongest first, drag or use Up/Down; untick sources to exclude them. Preview replacements before confirming. Confirmation changes only the unsaved CUPS draft."
    confirm_text = "Use preset draft"
    uefa_ranking = False

    def __init__(self, parent, recipe, sources, conf):
        super().__init__(parent)
        self.setObjectName("adddialog")
        self.setWindowTitle(_(self.title_text))
        self.recipe, self.sources, self.conf = recipe, sources, conf
        self.proposal = {}
        self.notes = []
        self.complete = False
        self.resize(940, 520)
        self.setMinimumSize(640, 360)
        layout = QVBoxLayout(self)
        self.instructions = hint(_(self.intro_text))
        layout.addWidget(self.instructions)
        splitter = QSplitter(Qt.Horizontal)
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        self.list = QListWidget()
        self.list.setDragDropMode(QAbstractItemView.InternalMove)
        self.list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list.setMinimumWidth(160)
        on, off = Q.ranked_sources(sources, recipe, conf)
        for source, enabled in [(s, True) for s in on] + [(s, False) for s in off]:
            item = QListWidgetItem("%s (%s)" % (source.name, source.country))
            item.setData(Qt.UserRole, source)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if enabled else Qt.Unchecked)
            self.list.addItem(item)
        lv.addWidget(self.list, 1)
        up, down = QPushButton(_("Up")), QPushButton(_("Down"))
        up.clicked.connect(lambda: self.move(-1))
        down.clicked.connect(lambda: self.move(1))
        reset = QPushButton(_("UEFA's order"))
        reset.setVisible(conf == 2)
        reset.clicked.connect(self.reset_uefa)
        lv.addWidget(row(up, down, reset, "stretch", stretch=False))
        self.sizes = {}
        if conf not in (2, 4):
            for target, title in Q.destinations(conf, recipe):
                if target == 5:
                    continue
                field = QComboBox()
                options = [n for n in B.CCUP_SIZES if target not in W.CCUP_KNOCKOUT or n <= B.CCUP_KNOCKOUT_MAX]
                for size in options:
                    field.addItem(str(size), size)
                field.setToolTip(_("Explicit allocations to generate. Native fill can enlarge the final supported field; Check the plan shows its actual size."))
                field.currentIndexChanged.connect(self.refresh)
                self.sizes[target] = field
                label = QLabel(_(title))
                label.setWordWrap(True)
                lv.addWidget(row(label, field, stretch=False))
        splitter.addWidget(left)
        self.preview = PresetPreview(uefa_ranking=self.uefa_ranking)
        splitter.addWidget(self.preview)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Ok).setText(_(self.confirm_text))
        self.buttons.accepted.connect(self.confirm)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.list.itemChanged.connect(self.refresh)
        self.list.model().rowsMoved.connect(self.refresh)
        self.refresh()

    def ranking(self):
        items = [self.list.item(i) for i in range(self.list.count())]
        return ([it.data(Qt.UserRole) for it in items if it.checkState() == Qt.Checked],
                [it.data(Qt.UserRole) for it in items if it.checkState() != Qt.Checked])

    def move(self, direction):
        selected = [i for i in range(self.list.count()) if self.list.item(i).isSelected()]
        for i in (selected if direction < 0 else reversed(selected)):
            j = i + direction
            if not 0 <= j < self.list.count() or self.list.item(j).isSelected():
                continue
            item = self.list.takeItem(i)
            self.list.insertItem(j, item)
            item.setSelected(True)
        self.refresh()

    def reset_uefa(self):
        recipe = {k: v for k, v in self.recipe.items() if k not in ("uefa_rank", "uefa_off")}
        on, off = Q.ranked_sources(self.sources, recipe, 2)
        self.list.blockSignals(True)
        items = {self.list.item(i).data(Qt.UserRole).draft_key: self.list.item(i)
                 for i in range(self.list.count())}
        detached = [self.list.takeItem(0) for _i in range(self.list.count())]
        for source, enabled in [(s, True) for s in on] + [(s, False) for s in off]:
            item = items[source.draft_key]
            item.setCheckState(Qt.Checked if enabled else Qt.Unchecked)
            self.list.addItem(item)
        self.list.blockSignals(False)
        self.refresh()

    def refresh(self, *_args):
        if not hasattr(self, "buttons"):
            return
        on, off = self.ranking()
        try:
            self.proposal, self.notes, self.complete = Q.generate(
                self.recipe, self.sources, self.conf, on, off, {c: w.currentData() for c, w in self.sizes.items()})
        except (B.BuildError, TypeError, ValueError, IndexError) as exc:
            self.proposal, self.notes, self.complete = {}, [str(exc)], False
        after = Q.preview(self.recipe, self.proposal)
        notes = list(self.notes)
        if self.conf == 2:
            notes.append(_("UEFA association order, exclusions and qualifying seeding are included in this proposal."))
        elif self.conf not in (2, 4):
            notes.append(_("Selected fields specify explicit allocations. Existing fill and the current plan may change the final field; review before Build."))
        self.preview.display(on + off, len(on), self.recipe, after, self.conf, self.proposal, notes, self.complete,
                             all_sources=self.sources, warning_count=len(self.notes))
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(self.complete and bool(self.proposal))

    def confirm(self):
        self.refresh()
        if self.complete and self.proposal:
            self.accept()


class PresetDialog(RankingPreviewDialog):
    """Existing generic tool for confederations that retain ranking presets."""


class UefaRankingDialog(RankingPreviewDialog):
    title_text = "UEFA Ranking"
    intro_text = "Arrange the UEFA associations to determine their qualification priority. Drag or use Up/Down; untick associations to exclude them. Ranking changes may update qualification places and seeding. Review the changes before applying them to your unsaved CUPS draft."
    confirm_text = "Apply UEFA ranking to draft"
    uefa_ranking = True

    def __init__(self, parent, recipe, sources, conf=2):
        if conf != 2:
            raise ValueError("UEFA Ranking requires UEFA sources")
        super().__init__(parent, recipe, sources, 2)


class QualificationEditor(QWidget):
    GROUPS = (("game", "Game leagues"), ("league", "Our leagues"), ("association", "Associations without playable leagues"))

    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.sources = ()
        self.conf = owner.confederation.currentData()
        self._signature = None
        self._token = 0
        self._loading = False
        self._mounting = False
        self._selected = None
        self._saved_view = {}
        self._queries = {}
        self._selections = {}
        self.first = None
        self._pending_tool = None
        self._auto_running = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        self.toolbar = QWidget()
        tools = QHBoxLayout(self.toolbar)
        tools.setContentsMargins(0, 0, 0, 0)
        tools.setSpacing(6)
        self.generate_button = QPushButton(_("Generate preset..."))
        self.generate_button.setObjectName("primary")
        self.generate_button.clicked.connect(self.generate_preset)
        self.rank_button = QPushButton(_("UEFA ranking..."))
        self.rank_button.clicked.connect(self.open_uefa_ranking)
        self.first_button = QPushButton(_("First-season clubs..."))
        self.first_button.clicked.connect(self.show_first)
        self.plan_button = QPushButton(_("Check current competition plan"))
        self.plan_button.clicked.connect(owner.request_plan)
        for button in (self.generate_button, self.rank_button, self.first_button, self.plan_button):
            tools.addWidget(button)
        tools.addStretch()
        layout.addWidget(self.toolbar)
        self.stack = EditorStack()
        layout.addWidget(self.stack, 1)
        self.splitter = QSplitter(Qt.Horizontal)
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        self.search = QLineEdit()
        self.search.setPlaceholderText(_("Find a league or association..."))
        self.search.textChanged.connect(self.filter_sources)
        lv.addWidget(self.search)
        self.list = QTreeWidget()
        self.list.setHeaderHidden(True)
        self.list.setMinimumSize(160, 0)
        self.list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        self.list.setIndentation(12)
        self.list.currentItemChanged.connect(self.select_source)
        lv.addWidget(self.list, 1)
        self.splitter.addWidget(left)
        self.scroll = QScrollArea()
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.scroll.setWidgetResizable(True)
        self.scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        right = QWidget()
        self.right_layout = QVBoxLayout(right)
        self.right_layout.setContentsMargins(12, 0, 4, 4)
        self.title = QLabel()
        self.title.setObjectName("cardtitle")
        self.title.setWordWrap(True)
        self.right_layout.addWidget(self.title)
        self.description = hint("")
        self.right_layout.addWidget(self.description)
        self.removed_notice = hint("")
        self.right_layout.addWidget(self.removed_notice)
        self.discard_removed = QPushButton(_("Discard removed league drafts"))
        self.discard_removed.clicked.connect(owner.discard_removed_drafts)
        self.discard_removed.hide()
        self.right_layout.addWidget(self.discard_removed)
        self.own = QCheckBox(_("Own places for this league"))
        self.own.toggled.connect(self.toggle_own)
        self.right_layout.addWidget(self.own)
        self.legacy_association = QPushButton(_("Review saved association allocations..."))
        self.legacy_association.clicked.connect(self.review_linked_association)
        self.legacy_association.hide()
        self.right_layout.addWidget(self.legacy_association)
        self.table_host = QWidget()
        self.table_layout = QVBoxLayout(self.table_host)
        self.table_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.addWidget(self.table_host)
        self.table = None
        self.warning = hint("")
        self.right_layout.addWidget(self.warning)
        self.summary_title = QLabel(_("Allocation overview"))
        self.summary_title.setObjectName("section")
        self.right_layout.addWidget(self.summary_title)
        self.summary = AllocationOverview()
        self.right_layout.addWidget(self.summary)
        self.explanation = Fold("How qualification works")
        self.explanation_text = hint("")
        self.explanation.body.addWidget(self.explanation_text)
        self.right_layout.addWidget(self.explanation)
        self.empty_state = hint("")
        self.right_layout.insertWidget(self.right_layout.indexOf(self.table_host), self.empty_state)
        self.right_layout.addStretch()
        self.scroll.setWidget(right)
        self.splitter.addWidget(self.scroll)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 3)
        self.splitter.setSizes([240, 650])
        self.stack.addWidget(self.splitter)
        self.state = hint("")
        self.state.hide()
        layout.addWidget(self.state)

    def set_state(self, text):
        self.state.setText(text)
        self.state.setVisible(bool(text))

    def table_stamp(self):
        return Q.table_signature(self.owner.project.base)

    def recipe(self):
        return self.owner.preview()

    def activate(self, conf):
        if conf != self.conf:
            self._queries[self.conf] = self.search.text()
            self._selections[self.conf] = self._selected
            self.search.setText(self._queries.get(conf, ""))
            self._selected = self._selections.get(conf)
        self.conf = conf
        recipe = self.recipe()
        self.generate_button.setVisible(conf != 2)
        self.generate_button.setText(_("Auto set continental places") if conf == 4 else _("Generate preset..."))
        self.generate_button.setToolTip(_("Fixed quotas for all ten playable CONMEBOL top divisions. Requires Modern CONMEBOL; changes only the CUPS draft.") if conf == 4 else "")
        self.rank_button.setVisible(conf == 2)
        self.first_button.setVisible(conf == 2)
        self.plan_button.setEnabled(self.owner.project.base is not None and not self.owner._checking)
        if conf != 2 and self.first is not None and self.stack.currentWidget() is self.first:
            self.back_to_sources()
        fields = ("name", "country", "clubs", "above", "cup", "exhibition", "others")
        leagues = [{k: L[k] for k in fields if k in L} for L in recipe.get("leagues") or []]
        signature = (self.owner.project.base, self.table_stamp(), leagues,
                     Q.modern(recipe), list((recipe.get("game_europe") or {}).keys()),
                     list((recipe.get("conmebol_associations") or {}).keys()))
        if signature != self._signature:
            self._signature = deepcopy(signature)
            self._token += 1
            token, owner, base = self._token, self.owner.project.recipe, self.owner.project.base
            fallback = dict(self.owner.project.confeds)
            # Mode inference needs existing stage rows, but no players/rosters.
            snapshot = {"leagues": [dict(L, europe=deepcopy(actual.get("europe") or []))
                                     for L, actual in zip(leagues, recipe.get("leagues") or [])],
                        "game_europe": deepcopy(recipe.get("game_europe") or {}),
                        "conmebol_associations": deepcopy(recipe.get("conmebol_associations") or {}),
                        "conmebol": recipe.get("conmebol")}
            if snapshot["conmebol"] is None:
                snapshot.pop("conmebol")
            self._loading = True
            self.generate_button.setEnabled(False)
            self.rank_button.setEnabled(False)
            self.set_state(_("Loading qualification sources..."))
            names = {L["name"] for L in leagues}
            self.sources = tuple(s for s in self.sources if
                                 (s.kind != "league" or s.key in names) and
                                 (not s.linked_to or s.linked_to[1] != "league" or s.linked_to[2] in names))
            self.fill_sources()

            def done(result):
                if not isValid(self) or token != self._token or owner is not self.owner.project.recipe or base != self.owner.project.base:
                    return
                self.sources = result
                self._loading = False
                self.set_state("")
                self.fill_sources()

            def failed(trace):
                if not isValid(self) or token != self._token or owner is not self.owner.project.recipe or base != self.owner.project.base:
                    return
                self.sources = Q.sources(snapshot, None, fallback)
                self._loading = False
                self.fill_sources()
                self.set_state(_("Original league/association data could not be read. Stored values are preserved. %s") % trace.strip().splitlines()[-1])
            run_job(lambda _progress: Q.sources(snapshot, base, fallback), done, failed)
        elif not self._loading:
            self.fill_sources()
        if self.first is not None and self.stack.currentWidget() is self.first:
            self.first.activate()

    def current_source(self):
        return next((s for s in self.sources if s.draft_key == self._selected), None)

    def fill_sources(self):
        requested = self._selected
        self.list.blockSignals(True)
        self.list.clear()
        selected = None
        recipe = self.recipe()
        for kind, title in self.GROUPS:
            group_sources = [s for s in self.sources if s.kind == kind and s.confederation == self.conf and not s.linked_to]
            if not group_sources:
                continue
            group = QTreeWidgetItem([_(title)])
            group.setFlags(group.flags() & ~Qt.ItemIsSelectable)
            self.list.addTopLevelItem(group)
            for source in group_sources:
                custom = Q.state(recipe, source.draft_key)[0][0]
                item = QTreeWidgetItem([("● " if custom else "") + source.name])
                item.setData(0, Qt.UserRole, source.draft_key)
                item.setToolTip(0, source.country)
                group.addChild(item)
                if source.draft_key == self._selected:
                    selected = item
            group.setExpanded(True)
        self.list.blockSignals(False)
        self.filter_sources()
        if selected is None and self.list.topLevelItemCount():
            selected = self.list.topLevelItem(0).child(0)
        if selected:
            self.list.blockSignals(True)
            self.list.setCurrentItem(selected)
            self.list.blockSignals(False)
            self.select_source(selected)
            linked = next((s for s in self.sources if s.draft_key == requested and s.linked_to), None)
            if linked:
                self._selected = linked.draft_key
                self.mount_source()
        else:
            self._selected = None
            self.title.setText(_("No eligible qualification sources in this confederation."))
            self.description.clear()
            self.own.hide()
            self.legacy_association.hide()
            self.table_host.hide()
            self.empty_state.hide()
            self.warning.clear()
        self.refresh_summary()
        self.generate_button.setEnabled(not self._loading and not self._auto_running and
                                        (self.conf == 4 or bool(self.list.topLevelItemCount())))
        self.rank_button.setEnabled(not self._loading and bool(self.list.topLevelItemCount()))
        if self._pending_tool and not self._loading:
            tool, self._pending_tool = self._pending_tool, None
            self.open_tool(tool)

    def open_tool(self, tool):
        if tool == "first":
            self.show_first()
        elif self._loading:
            self._pending_tool = tool
        elif self.generate_button.isEnabled():
            self.generate_preset()

    def filter_sources(self, *_args):
        query = self.search.text().casefold().strip()
        for i in range(self.list.topLevelItemCount()):
            group = self.list.topLevelItem(i)
            shown = 0
            for j in range(group.childCount()):
                item = group.child(j)
                show = query in (item.text(0) + " " + item.toolTip(0)).casefold()
                item.setHidden(not show)
                shown += show
            group.setHidden(not shown)

    def select_source(self, item, *_args):
        if item is None or not item.data(0, Qt.UserRole):
            return
        self._selected = tuple(item.data(0, Qt.UserRole))
        self.mount_source()

    def mount_source(self):
        source = self.current_source()
        if source is None:
            return
        self._mounting = True
        recipe = self.recipe()
        present = Q.state(recipe, source.draft_key)[0][0]
        self.title.setText("%s — %s" % (source.name, source.country))
        kind = _("Stored association allocations") if source.linked_to else {"game": _("Original game league"), "league": _("Mod Studio league"), "association": _("Association without playable league")}[source.kind]
        explanation = Q.inherited_text(source, recipe)
        if source.kind == "game":
            mode = _("Set custom qualification places") if present else _("Use the game's default qualification places")
            text = kind + " — " + mode
            if not present:
                text += "\n" + _("Read-only. Turn on custom places to edit the table.")
            # Keep special native-access limitations visible, with full explanations below.
            generic = _("Native access is retained. The rows below are read-only reference; enable Own places to replace them.")
            if explanation != generic:
                retained = _("This backend retains native access for empty or generated-cup-only overrides. The table edits your stored rows only; inherited entries still count in the overview. Explicit native destinations replace native access.")
                text += "\n" + (_("Some game defaults remain active alongside these custom places. See How qualification works.")
                                 if explanation == retained else explanation)
        elif source.kind == "league":
            text = kind + "\n" + _("Changes are shared with Edit League.")
        else:
            text = kind + "\n" + _("Ranks select eligible clubs automatically; they are not league positions.")
        self.description.setText(text)
        self.legacy_association.setVisible(bool(source.linked_to or any(s.linked_to == source.draft_key for s in self.sources)))
        self.legacy_association.setText(_("Back to playable league allocations") if source.linked_to else _("Review saved association allocations..."))
        self.own.setVisible(source.kind != "league")
        self.own.setText(_("Own places for this association") if source.kind == "association" else _("Set custom qualification places"))
        self.own.setChecked(present)
        if self.table is not None:
            self.table_layout.removeWidget(self.table)
            self.table.hide()
            self.table.deleteLater()
        rows = Q.editable_rows(source, recipe)
        choices = Q.destinations(source.confederation, recipe)
        try:
            self.table = EuropeTable(rows, source.clubs, competitions=choices,
                                     cup_winner=source.cup,
                                     position_label="Association rank" if source.kind == "association" else "League position",
                                     modern=Q.modern(recipe), preserve_legacy=True)
        except (ValueError, TypeError, IndexError):
            self.table = EuropeTable([], source.clubs, competitions=choices, cup_winner=source.cup, preserve_legacy=True)
            self.warning.setText(_("Malformed stored rows are retained. Remove or replace them explicitly before applying this source."))
        self.table.preset.hide()
        self.table.changed = self.places_changed
        self.table_layout.addWidget(self.table)
        self.table.setEnabled((source.kind == "league" or present) and not source.invalid_link)
        self.table_host.show()
        empty = not rows
        self.empty_state.setText(_("No places yet. Use Add place to assign a competition.") if source.kind == "league" or present else
                                 _("No editable rows. The game's inherited access is explained in How qualification works."))
        self.empty_state.setVisible(empty)
        self._mounting = False
        self.resize_table()
        self.refresh_summary()

    def review_linked_association(self):
        source = self.current_source()
        if source is None:
            return
        target = source.linked_to or next((s.draft_key for s in self.sources if s.linked_to == source.draft_key), None)
        if target:
            self._selected = target
            self.mount_source()

    def resize_table(self):
        if self.table is None:
            return
        table = self.table.table
        table.ensurePolished()
        table.horizontalHeader().ensurePolished()
        # One vertical scroll owner (the source detail panel), even for 40 ranks.
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setFixedHeight(table.horizontalHeader().sizeHint().height() + 2 * table.frameWidth()
                             + sum(table.rowHeight(i) for i in range(table.rowCount())) + 2)

    def toggle_own(self, enabled):
        if self._mounting:
            return
        source = self.current_source()
        if source is None:
            return
        rows = self.table.places() if self.table else []
        self.owner.set_qualification(source.draft_key, (True, rows) if enabled else (False, None))
        self.mount_source()
        self.mark_sources()

    def places_changed(self):
        if self._mounting or self.table is None:
            return
        source = self.current_source()
        if source is None or (source.kind != "league" and not self.own.isChecked()):
            return
        rows = self.table.places()
        self.owner.set_qualification(source.draft_key, (True, rows))
        self.resize_table()
        self.refresh_summary()
        self.mark_sources()

    def mark_sources(self):
        recipe = self.recipe()
        by_key = {s.draft_key: s for s in self.sources}
        for i in range(self.list.topLevelItemCount()):
            group = self.list.topLevelItem(i)
            for j in range(group.childCount()):
                item = group.child(j)
                source = by_key[tuple(item.data(0, Qt.UserRole))]
                item.setText(0, ("● " if Q.state(recipe, source.draft_key)[0][0] else "") + source.name)

    def refresh_summary(self):
        recipe = self.recipe()
        removed = self.owner.removed_draft_keys()
        self.removed_notice.setText(_("Drafts for removed leagues are kept: %s. Undo the deletion to recover them, or discard only those drafts.")
                                    % ", ".join(sorted(str(k[2]) for k in removed)) if removed else "")
        self.removed_notice.setVisible(bool(removed))
        self.discard_removed.setVisible(bool(removed))
        self.summary.display(allocation_rows(self.sources, recipe, self.conf))
        explanation = Q.inherited_text(self.current_source(), recipe) if self.current_source() else ""
        self.explanation_text.setText(explanation + "\n\n" + "\n".join(Q.overview(self.sources, recipe, self.conf)))
        source = self.current_source()
        if source:
            warnings = Q.row_errors(source, Q.effective(source, recipe), recipe)
            if self.owner._plan:
                warnings.append(_("Current plan: %s") % str(self.owner._plan))
            self.warning.setText("\n".join(warnings))
            self.warning.setVisible(bool(warnings))
            if self.table is not None:
                self.empty_state.setVisible(self.table.table.rowCount() == 0)

    def generate_preset(self):
        if self.conf == 2:
            self.open_uefa_ranking()
            return
        if self.conf == 4:
            self.auto_set_conmebol()
            return
        self.review_ranking(PresetDialog)

    def open_uefa_ranking(self):
        if self.conf == 2:
            self.review_ranking(UefaRankingDialog)

    def review_ranking(self, dialog_type):
        if self._loading:
            return
        owner, base = self.owner.project.recipe, self.owner.project.base
        baseline = {k: Q.state(owner, k)[1] for k in Q.keys(owner)}
        draft_before = deepcopy(self.owner._values)
        tables = self.table_stamp()
        dialog = dialog_type(self, self.recipe(), self.sources, self.conf)
        accepted = dialog.exec() == QDialog.Accepted
        proposal = deepcopy(dialog.proposal)
        dialog.deleteLater()
        if accepted:
            current = {k: Q.state(self.owner.project.recipe, k)[1] for k in Q.keys(self.owner.project.recipe)}
            if owner is not self.owner.project.recipe or base != self.owner.project.base or tables != self.table_stamp() or current != baseline or self.owner._values != draft_before:
                self.set_state(_("The project changed while reviewing UEFA Ranking. Open the ranking again; nothing was applied.") if self.conf == 2 else
                               _("The project changed while previewing. Generate the preset again; nothing was applied."))
                return
            self.owner.set_qualification_batch(proposal)
            self.activate(self.conf)

    def auto_set_conmebol(self):
        if self.conf != 4 or self._loading or self._auto_running:
            return
        recipe = self.recipe()
        if not Q.modern(recipe):
            error(self, "Cannot auto-set continental places", _("Enable Modern CONMEBOL competitions before using automatic allocation.")
                  + "\n\n" + _("No qualification places were changed."))
            return
        owner, base = self.owner.project.recipe, self.owner.project.base
        snapshot = A.snapshot(recipe)
        draft = deepcopy(self.owner._values)
        tables = self.table_stamp()
        self._auto_running = True
        self.generate_button.setEnabled(False)

        def calculate(_progress):
            try:
                return True, A.generate(snapshot, base)
            except A.AllocationError as exc:
                return False, str(exc)

        def done(result):
            if not isValid(self):
                return
            self._auto_running = False
            if owner is not self.owner.project.recipe or base != self.owner.project.base:
                return
            self.generate_button.setEnabled(not self._loading)
            if tables != self.table_stamp() or draft != self.owner._values or snapshot != A.snapshot(self.recipe()):
                error(self, "Cannot auto-set continental places", _("The world changed during automatic allocation. Try again; no qualification places were changed."))
                return
            success, value = result
            if not success:
                error(self, "Cannot auto-set continental places", value)
                return
            if value:
                self.owner.set_qualification_batch(value)
            self.activate(self.conf)
            self.set_state(_("All 89 CONMEBOL places are set in the CUPS draft. Review them, then Apply to save or Discard changes to restore."))

        def failed(trace):
            import logging
            logging.getLogger(__name__).error("CONMEBOL automatic allocation failed:\n%s", trace)
            done((False, _("The game or league data could not be verified. No qualification places were changed.")))

        run_job(calculate, done, failed)

    def show_first(self):
        if self.conf != 2:
            return
        if self.first is None:
            from .first_season import FirstSeasonEditor
            self.first = FirstSeasonEditor(self)
            self.stack.addWidget(self.first)
            self.first.restore_view(self._saved_view.get("first_view", {}))
        self.stack.setCurrentWidget(self.first)
        self.toolbar.hide()
        self.first.activate()

    def back_to_sources(self):
        self.stack.setCurrentWidget(self.splitter)
        self.toolbar.show()

    def view_state(self):
        return {"selected": self._selected, "search": self.search.text(),
                "first": self.first is not None and self.stack.currentWidget() is self.first,
                "first_view": self.first.view_state() if self.first else {}, "sizes": self.splitter.sizes(),
                "queries": dict(self._queries), "selections": dict(self._selections)}

    def restore_view(self, state):
        self._saved_view = state
        self._queries = dict(state.get("queries", {}))
        self._selections = dict(state.get("selections", {}))
        selected = state.get("selected")
        self._selected = tuple(selected) if selected else None
        self.search.setText(state.get("search", ""))
        if state.get("sizes"):
            self.splitter.setSizes(state["sizes"])
        if state.get("first"):
            self.show_first()
