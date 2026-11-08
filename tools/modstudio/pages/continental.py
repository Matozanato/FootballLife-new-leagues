"""Master-detail continental competition editor; qualification is intentionally separate."""
from dataclasses import replace
from html import escape
from copy import deepcopy
from PySide6.QtCore import Qt, Signal, QEvent
from shiboken6 import isValid
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
                              QListWidget, QListWidgetItem, QSplitter, QLineEdit, QLabel,
                              QFormLayout, QScrollArea, QCheckBox, QPushButton, QSizePolicy,
                              QLayout)

import leaguebuilder as B
from .. import competition_catalog as C
from .. import competition_guides as G
from .. import qualification_data as Q
from ..editor_containers import SectionTabs
from ..i18n import _
from ..ui import hint, row, ask, run_job
from .builder import PictureField, CompetitionLogoVariant
from .cup_editors import CupConflict


class CompetitionList(QListWidget):
    """Content-height list inside a full-height splitter pane, aligned at the top."""
    MAX_HEIGHT = 320

    def __init__(self, pane):
        super().__init__(pane)
        self.setMinimumWidth(160)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        pane.installEventFilter(self)
        self.model().rowsInserted.connect(self.fit_height)
        self.model().rowsRemoved.connect(self.fit_height)
        self.model().dataChanged.connect(self.fit_height)

    def content_height(self):
        rows = sum(max(0, self.sizeHintForRow(i)) + 2 * self.spacing() for i in range(self.count()))
        margins = self.contentsMargins()
        viewport = self.viewportMargins()
        frame = max(2 * self.frameWidth(), margins.top() + margins.bottom())
        horizontal = (self.horizontalScrollBar().sizeHint().height()
                      if self.sizeHintForColumn(0) > self.viewport().width() else 0)
        return rows + frame + viewport.top() + viewport.bottom() + horizontal

    def fit_height(self, *_args):
        self.ensurePolished()
        self.doItemsLayout()
        available = max(1, self.parentWidget().contentsRect().height())
        height = min(self.content_height(), self.MAX_HEIGHT, available)
        if self.height() != height or self.minimumHeight() != height:
            self.setFixedHeight(height)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Resize:
            self.fit_height()
        return super().eventFilter(watched, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_height()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.FontChange, QEvent.StyleChange):
            self.fit_height()


class ContinentalEditor(QWidget):
    changed = Signal()
    requires_tables = False

    @staticmethod
    def refresh_inputs(project):
        # Only the identity/settings/access fields displayed here. Never retain a
        # whole recipe, club roster or player database just to detect UI changes.
        recipe = project.recipe
        keys = ("uecl", "uecl_name", "uecl_logo", "ccup_names", "ccup_logos", C.E.ROOT,
                "conmebol", "game_europe", "conmebol_associations", "caf_super_cup",
                "caf_super_cup_logo", "samerica_super_cup", "samerica_super_cup_logo",
                "samerica_super_cup_first", "sudamericana_calendar", "uefa_rank", "uefa_off", "uefa_seed", "europe_first")
        fields = ("name", "country", "clubs", "above", "season", "exhibition", "others", "europe", "cup", "club_names")
        return ({k: recipe[k] for k in keys if k in recipe},
                (recipe.get("edits") or {}).get("competitions"),
                [dict({k: L[k] for k in fields if k in L},
                      club_sources=[(g.get("at"), g.get("id"), isinstance(g.get("swap"), dict))
                                    for g in L.get("game_clubs") or []]) for L in recipe.get("leagues") or []],
                Q.table_signature(project.base))

    def __init__(self, parent, project, draft=None):
        super().__init__(parent)
        self.project = project
        self.rows = C.catalog(project.base)
        self.competitions = {c.key: c for c in self.rows}
        self._values, self._sources = self.read(project.recipe)
        self._initial = dict(self._values)
        self._base = project.base
        self._loading = False
        self._generation = 0
        self._plan = None
        self._checking = False
        self._selected = None
        self.qualification = None
        self._qualification_view = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.confederation = QComboBox()
        for number, name in C.CONFEDERATIONS:
            self.confederation.addItem(name, number)
        selector = row(QLabel(_("Confederation")), self.confederation, "stretch", stretch=False)
        layout.addWidget(selector)
        self.settings_body = QWidget()
        settings_layout = QHBoxLayout(self.settings_body)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        self.settings = {}
        for setting in C.SETTINGS:
            checkbox = QCheckBox(_(setting.label))
            checkbox.setChecked(self._values[("setting", setting.key)])
            checkbox.toggled.connect(lambda on, key=setting.key: self.setting_changed(key, on))
            settings_layout.addWidget(checkbox)
            self.settings[setting.key] = checkbox
        selector.layout().insertWidget(2, self.settings_body)
        self.tabs = SectionTabs()
        layout.addWidget(self.tabs, 1)
        self.splitter = QSplitter(Qt.Horizontal)
        list_pane = QWidget()
        list_pane.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Ignored)
        left = QVBoxLayout(list_pane)
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(0)
        self.list = CompetitionList(list_pane)
        left.addWidget(self.list)
        left.addStretch(1)
        self.splitter.addWidget(list_pane)
        self.detail_scroll = scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        detail = QWidget()
        right = QVBoxLayout(detail)
        right.setContentsMargins(12, 0, 4, 4)
        right.setSizeConstraint(QLayout.SetMinimumSize)
        self.original_name = QLabel()
        self.original_name.setObjectName("cardtitle")
        self.original_name.setWordWrap(True)
        right.addWidget(self.original_name)
        self.identity_body = QWidget()
        identity_form = QFormLayout(self.identity_body)
        identity_form.setContentsMargins(0, 0, 0, 0)
        identity_form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.name = QLineEdit()
        self.name.setMaxLength(60)
        self.name.textChanged.connect(self.name_changed)
        identity_form.addRow(_("Name"), self.name)
        self.logo = PictureField(None, 64)
        self.logo.changed = self.logo_changed
        identity_form.addRow(_("Logo"), self.logo)
        self.variant_logos = {}
        for mode, label in (("dark", "Dark Mode Logo"), ("light", "Light Mode Logo")):
            picture = CompetitionLogoVariant(mode)
            picture.changed = lambda mode=mode: self.variant_changed(mode)
            self.variant_logos[mode] = picture
            identity_form.addRow(_(label), picture)
        right.addWidget(self.identity_body)
        right.addWidget(hint(_("Empty name or logo uses the existing default. Changes reach the game after Build and install.")))
        self.details = {}
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        for key in ("Type", "Source", "Format and stages", "Availability", "Qualification overview", "Current plan"):
            label = QLabel()
            label.setWordWrap(True)
            label.setTextFormat(Qt.PlainText)
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            form.addRow(_(key), label)
            self.details[key] = label
        right.addLayout(form)
        self.check_plan = QPushButton(_("Check current competition plan"))
        self.check_plan.clicked.connect(self.request_plan)
        self.plan_note = hint(_("Exact generated fields are available from the current plan. Checking it does not build or save the world."))
        right.addWidget(self.plan_note)
        right.addWidget(self.check_plan)
        self.system_title = QLabel(_("How this system works"))
        self.system_title.setObjectName("section")
        right.addWidget(self.system_title)
        self.system_guide = QLabel()
        self.system_guide.setWordWrap(True)
        self.system_guide.setTextFormat(Qt.RichText)
        self.system_guide.setTextInteractionFlags(Qt.TextSelectableByMouse)
        right.addWidget(self.system_guide)
        right.addStretch()
        scroll.setWidget(detail)
        self.splitter.addWidget(scroll)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 3)
        self.splitter.setSizes([240, 650])
        self.tabs.addTab(self.splitter, _("Competitions"))
        self.qualification_host = QWidget()
        pending = QVBoxLayout(self.qualification_host)
        pending.setContentsMargins(0, 0, 0, 0)
        self.tabs.addTab(self.qualification_host, _("Qualification"))
        self.tabs.currentChanged.connect(self.qualification_tab)
        self.confederation.currentIndexChanged.connect(self.show_confederation)
        self.list.currentItemChanged.connect(self.show_competition)
        self.show_confederation()

    def read(self, recipe):
        values, sources = {}, {}
        for c in self.rows:
            for field in ("name", "logo", *C.E.MODES):
                key = ("identity", c.key, field)
                values[key] = C.identity(recipe, c, field)
                sources[key] = C.fingerprint(recipe, c, field)
        for setting in C.SETTINGS:
            key = ("setting", setting.key)
            values[key] = C.setting_value(recipe, setting)
            sources[key] = C.slot(recipe, (setting.key,))
        tracked = {k for k in getattr(self, "_values", {}) if k[0] == "qualification"}
        for key in Q.keys(recipe) | tracked:
            values[key], sources[key] = Q.state(recipe, key)
        return values, sources

    def preview(self):
        return C.preview_recipe(self.project.recipe, self.changes(), self.competitions)

    def qualification_tab(self, index):
        if index != 1:
            return
        if self.qualification is None:
            from .qualification import QualificationEditor
            self.qualification = QualificationEditor(self)
            self.qualification_host.layout().addWidget(self.qualification)
            self.qualification.restore_view(self._qualification_view)
        self.qualification.activate(self.confederation.currentData())

    def set_qualification(self, key, value):
        if key not in self._values:
            self._values[key], self._sources[key] = Q.state(self.project.recipe, key)
            self._initial[key] = deepcopy(self._values[key])
        self._values[key] = deepcopy(value)
        self.edited()

    def set_qualification_batch(self, changes):
        for key, value in changes.items():
            if key not in self._values:
                self._values[key], self._sources[key] = Q.state(self.project.recipe, key)
                self._initial[key] = deepcopy(self._values[key])
            self._values[key] = deepcopy(value)
        self.edited()

    def dirty_keys(self):
        return {k for k, v in self._values.items() if v != self._initial[k]}

    def removed_draft_keys(self):
        names = {L.get("name") for L in self.project.recipe.get("leagues") or []}
        return {k for k in self.dirty_keys() if k[:2] == ("qualification", "league") and k[2] not in names}

    def discard_removed_drafts(self):
        # Explicit action: preserve all edits for sources that still exist.
        for key in self.removed_draft_keys():
            self._values[key], self._sources[key] = Q.state(self.project.recipe, key)
            self._initial[key] = deepcopy(self._values[key])
        self.edited()
        if self.qualification is not None:
            self.qualification.activate(self.confederation.currentData())

    def normalized(self, key, value):
        if key[0] == "qualification":
            return value
        if key[0] == "setting":
            return value
        if key[2] in ("logo", *C.E.MODES):
            return value or None
        c = self.competitions[key[1]]
        name = value.strip()
        return None if not name or (c.storage != "uecl" and name == c.name) else name

    def changes(self):
        return {key: self.normalized(key, self._values[key]) for key in self.dirty_keys()}

    def view_state(self):
        return {"confederation": self.confederation.currentData(), "selected": self._selected,
                "tab": self.tabs.currentIndex(), "sizes": self.splitter.sizes(),
                "qualification": self.qualification.view_state() if self.qualification else self._qualification_view}

    def restore_view(self, view):
        self._qualification_view = view.get("qualification", {})
        self._selected = view.get("selected")
        index = self.confederation.findData(view.get("confederation"))
        self.confederation.setCurrentIndex(max(0, index))
        self.show_confederation()
        for i in range(self.list.count()):
            if self.list.item(i).data(Qt.UserRole) == view.get("selected"):
                self.list.setCurrentRow(i)
                break
        self.tabs.setCurrentIndex(view.get("tab", 0))
        if self.tabs.currentIndex() == 1:
            self.qualification_tab(1)
        if view.get("sizes"):
            self.splitter.setSizes(view["sizes"])

    def draft(self):
        return {"values": deepcopy(self._values), "initial": deepcopy(self._initial),
                "sources": deepcopy(self._sources), "base": self._base, "view": self.view_state()}

    def restore_draft(self, draft):
        self._values.update(draft["values"])
        self._initial.update(draft["initial"])
        self._sources.update(draft["sources"])
        self._base = draft["base"]
        self.sync_settings()
        self.restore_view(draft["view"])
        self.show_confederation()

    def sync_settings(self):
        self._loading = True
        for key, checkbox in self.settings.items():
            checkbox.setChecked(self._values[("setting", key)])
        self._loading = False

    def reconcile(self):
        """Refresh unedited fields; retain the original conflict baseline of edited fields."""
        dirty = self.dirty_keys()
        latest = list(C.catalog(self.project.base))
        found = {c.key for c in latest}
        latest += [replace(c, available=False) for c in self.rows if c.key not in found]
        self.rows = tuple(latest)
        self.competitions = {c.key: c for c in self.rows}
        values, sources = self.read(self.project.recipe)
        for key in values:
            if key not in dirty:
                self._values[key] = self._initial[key] = values[key]
                self._sources[key] = sources[key]
        self.invalidate_plan()
        self.sync_settings()
        self.show_confederation()

    def show_confederation(self, *_args):
        conf = self.confederation.currentData()
        for setting in C.SETTINGS:
            self.settings[setting.key].setVisible(setting.confederation == conf)
        self.settings_body.setVisible(any(s.confederation == conf for s in C.SETTINGS))
        selected = self._selected
        preview = C.preview_recipe(self.project.recipe, self.changes(), self.competitions)
        self.list.blockSignals(True)
        self.list.clear()
        for c in self.rows:
            if c.confederation != conf or not C.visible(c, preview):
                continue
            item = QListWidgetItem(self.list_title(c))
            item.setData(Qt.UserRole, c.key)
            self.list.addItem(item)
            if c.key == selected:
                self.list.setCurrentItem(item)
        if self.list.currentRow() < 0:
            self.list.setCurrentRow(0)
        self.list.fit_height()
        self.list.blockSignals(False)
        self.show_competition(self.list.currentItem())
        if self.qualification is not None:
            self.qualification.activate(conf)

    def list_title(self, c):
        title = self._values[("identity", c.key, "name")] or c.title or c.name
        pending = any(("identity", c.key, f) in self.dirty_keys() for f in ("name", "logo", *C.E.MODES))
        return title + (" *" if pending else "")

    def show_competition(self, item, *_args):
        if item is None:
            return
        self._selected = item.data(Qt.UserRole)
        c = self.competitions[self._selected]
        self._loading = True
        self.original_name.setText(c.title or c.name)
        self.name.setPlaceholderText(c.name)
        self.name.setText(self._values[("identity", c.key, "name")])
        self.logo.path = self._values[("identity", c.key, "logo")]
        self.logo.empty = "(the game's own)" if c.storage == "game" else "(made for you)"
        self.logo.show_it()
        for mode, picture in self.variant_logos.items():
            picture.path = self._values[("identity", c.key, mode)]
            picture.show_it()
        self.identity_body.setEnabled(c.available)
        self._loading = False
        self.refresh_information()

    def edited(self):
        self.invalidate_plan()
        item = self.list.currentItem()
        if item:
            item.setText(self.list_title(self.competitions[self._selected]))
        self.refresh_information()
        self.changed.emit()

    def name_changed(self, text):
        if not self._loading and self._selected:
            self._values[("identity", self._selected, "name")] = text
            self.edited()

    def logo_changed(self):
        if not self._loading and self._selected:
            self._values[("identity", self._selected, "logo")] = self.logo.path
            self.edited()

    def variant_changed(self, mode):
        if not self._loading and self._selected:
            self._values[("identity", self._selected, mode)] = self.variant_logos[mode].path
            self.edited()

    def setting_changed(self, key, on):
        if not self._loading:
            self._values[("setting", key)] = on
            self.invalidate_plan()
            self.show_confederation()
            self.changed.emit()

    def invalidate_plan(self):
        self._generation += 1
        self._plan = None
        self.details["Current plan"].setText(_("Not checked for the current values."))
        self.plan_note.setText(_("Values changed while checking. Check the plan again for current information.")
                               if self._checking else
                               _("Exact generated fields are available from the current plan. Checking it does not build or save the world."))
        self.check_plan.setEnabled(self.project.base is not None and not self._checking)

    def refresh_information(self):
        if self._selected is None:
            return
        recipe = C.preview_recipe(self.project.recipe, self.changes(), self.competitions)
        data = dict(C.information(self.competitions[self._selected], recipe, self._plan))
        for key, label in self.details.items():
            label.setText(data.get(key, _("Not checked for the current values.") if key == "Current plan" else ""))
        sections = G.sections(self.confederation.currentData(), recipe, C.modern(recipe))
        self.system_title.setVisible(bool(sections))
        self.system_guide.setVisible(bool(sections))
        self.system_guide.setText("".join(
            "<h3>%s</h3><ul>%s</ul>" % (escape(title), "".join("<li>%s</li>" % escape(p) for p in paragraphs))
            for title, paragraphs in sections))
        self.check_plan.setEnabled(self.project.base is not None and not self._checking)
        if self.qualification is not None and self.tabs.currentIndex() == 1:
            self.qualification.refresh_summary()

    def request_plan(self):
        if self._checking or not self.project.base:
            return
        generation, owner, base = self._generation, self.project.recipe, self.project.base
        recipe = C.preview_recipe(owner, self.changes(), self.competitions)
        self._checking = True
        self.check_plan.setEnabled(False)
        self.plan_note.setText(_("Checking the current competition plan..."))

        def done(result):
            if not isValid(self):
                return
            self._checking = False
            if owner is self.project.recipe and base == self.project.base and generation == self._generation:
                self._plan = result
                self.plan_note.setText(_("Plan checked for the current values. Nothing was built or saved."))
            else:
                self.plan_note.setText(_("Values changed while checking. Check the plan again for current information."))
            self.refresh_information()

        run_job(lambda _progress: C.plan_summary(recipe, base), done,
                lambda tb: done({"error": tb.strip().splitlines()[-1]}))

    def apply(self, recipe):
        changes = self.changes()
        if not changes:
            return False
        if self.removed_draft_keys():
            raise CupConflict(_("Some draft leagues were removed: %s. Undo the deletion to recover them, or use Discard removed league drafts in Qualification. Other edits are kept.")
                              % ", ".join(sorted(str(k[2]) for k in self.removed_draft_keys())))
        if self._base != self.project.base:
            raise CupConflict(_("The game tables changed. Your draft is kept; Discard to reload the current project."))
        current, sources = self.read(recipe)
        live = {c.key: c for c in C.catalog(self.project.base)}
        patches = {}
        for key, value in changes.items():
            if key[0] == "identity" and (key[1] not in live or not live[key[1]].available):
                raise CupConflict(_("This competition is not in the selected game's tables. Your draft is kept."))
            if current[key] == value or (not current[key] and value is None):
                continue
            if sources[key] != self._sources[key]:
                raise CupConflict(_("Competition settings changed elsewhere. Your draft is kept; Discard reloads the current project."))
            patches[key] = value
        proposed = C.preview_recipe(recipe, patches, self.competitions)
        qchanges = {k: v for k, v in patches.items() if k[0] == "qualification"}
        if qchanges:
            available = self.qualification.sources if self.qualification else ()
            if any(k[1] in ("game", "league", "association") for k in qchanges):
                try:
                    available = Q.sources(proposed, self.project.base, self.project.confeds)
                except (OSError, ValueError, B.BuildError) as exc:
                    raise CupConflict(_("Qualification sources could not be validated; the draft is kept. %s") % str(exc))
            first = self.qualification.first if self.qualification else None
            errors = Q.validate_changes(recipe, proposed, qchanges, available, first.aliases if first else None)
            if errors:
                raise CupConflict("\n".join(errors))
        before_cleanup = C.preview_recipe(recipe, {k: v for k, v in patches.items()
                                                  if k != ("setting", "conmebol")}, self.competitions)
        if patches.get(("setting", "conmebol")) is False and C.modern(before_cleanup):
            gone = B.modern_conmebol_places(before_cleanup)
            if gone and not ask(self, "South American places", _(C.MODERN_WARNING) % len(gone)):
                raise CupConflict(_("Modern CONMEBOL was not disabled. Your draft is kept."))
        # All conflict checks and the destructive-change warning precede every mutation.
        for key, value in patches.items():
            if key[0] == "qualification":
                Q.write(recipe, key, value)
            elif key[0] == "identity":
                C.write_identity(recipe, self.competitions[key[1]], key[2], value)
            elif key[1] == "conmebol":
                continue
            else:
                recipe[key[1]] = value
        if ("setting", "conmebol") in patches:
            C.set_modern_mode(recipe, patches[("setting", "conmebol")], lambda _n: True)
        return bool(patches)
