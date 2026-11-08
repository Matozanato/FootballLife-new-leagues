"""Domestic cups and continental competitions of the open world."""
import os
from copy import deepcopy
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QSizePolicy)
from ..i18n import _
from .. import filecache, i18n
from ..editor_containers import SectionTabs
from ..ui import hint
from .builder import BuilderPage, PictureField
from .cup_editors import GameCupsEditor, OurCupsEditor, CupConflict
from .continental import ContinentalEditor


class Cups(BuilderPage):
    title = "Cups"
    help = "Manage domestic cups and continental competitions. Apply keeps changes in your world; Build and install brings them into the game."

    def __init__(self, app):
        super().__init__(app)
        # Reuse the empty bottom inset for the new content gap, retaining the
        # compact list's viewport even at the minimum supported window height.
        self.outer.setContentsMargins(18, 12, 18, 3)
        self.outer.setSpacing(6)
        self.discard_button = self.action("Discard changes", lambda: self.discard_section(self.current_section()))
        self.apply_button = self.action("Apply", lambda: self.apply_section(self.current_section()), "primary")
        self.discard_button.setEnabled(False)
        self.apply_button.setEnabled(False)
        self.more_button = self.more([("Competition names", lambda: app.page("NewLeagues").competition_names()),
                   ("Competition IDs", lambda: app.page("NewLeagues").competition_ids()),
                   ("Trophies", lambda: app.open_page("Trophies"))])
        # Keep the shared theme's original action dimensions and the 8px
        # title/help separation, independent of the page's vertical spacing.
        self.outer.takeAt(0)
        self.actions.setParent(None)
        self.header = QWidget(self)
        self.header.setObjectName("cupsHeader")
        self.header.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.header.setLayout(self.actions)
        self.actions.setContentsMargins(0, 0, 0, 0)
        self.actions.setSpacing(8)
        self.title_label = self.actions.itemAt(0).widget()
        self.help_button = self.actions.itemAt(1).widget()
        for widget in (self.title_label, self.help_button):
            self.actions.setAlignment(widget, Qt.AlignVCenter)
            widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.outer.insertWidget(0, self.header)
        self.tabs = SectionTabs()
        self.outer.addWidget(self.tabs, 1)
        self.sections = []
        for title, factory in (("Game Countries", GameCupsEditor), ("Our Countries", OurCupsEditor),
                               ("Continental", ContinentalEditor)):
            body = QWidget()
            layout = QVBoxLayout(body)
            # Real space outside the tab bar, not padding inside its labels.
            layout.setContentsMargins(0, 9 if factory is ContinentalEditor else 10, 0, 0)
            message = hint("")
            message.hide()
            layout.addWidget(message)
            section = dict(body=body, layout=layout, message=message, apply=self.apply_button,
                           discard=self.discard_button, factory=factory, editor=None, inputs=None, pictures={})
            if factory is ContinentalEditor:
                self.continental_section = section
            else:
                self.sections.append(section)
            self.tabs.addTab(body, _(title))
        self.all_sections = self.sections + [self.continental_section]
        self.tabs.currentChanged.connect(self.section_changed)
        self._recipe = None
        self._key = None
        # Only detached widget values and cup fields: no retained project/league/player copies.
        self._drafts = {}
        self._refresh_timer = QTimer(self, singleShot=True, interval=0, timeout=self.refresh)
        self.project.changed.connect(self.queue_refresh)

    def current_section(self):
        return self.all_sections[self.tabs.currentIndex()]

    def heightForWidth(self, width):
        # Status/banner text wraps, so the outer scroll area queries height-for-width.
        # QVBoxLayout's preferred height includes the detail scroll area's whole
        # sizeHint; only its minimum viewport belongs in the page minimum.
        return self.outer.minimumHeightForWidth(width)

    def section_changed(self, _index):
        self.tabs.updateGeometry()
        self.update_buttons(self.current_section())

    @staticmethod
    def message(section, text):
        section["message"].setText(text)
        section["message"].setVisible(bool(text))

    def queue_refresh(self):
        # A plan may depend on fields outside the identity/access controls (e.g.
        # club sources). Invalidate even while hidden; never accept a stale worker
        # result just because the same editor now survives page navigation.
        editor = self.continental_section["editor"]
        if editor is not None:
            editor.invalidate_plan()
        # Player and club edits can emit changed very often. Do not rebuild hidden cup
        # tables for those; switching projects still captures and isolates pending drafts.
        if self.isVisible() or self._recipe is not self.project.recipe:
            self._refresh_timer.start()

    def _tables(self):
        # A reload can keep the same base path (also used for custom table overlays).
        for section in getattr(self, "all_sections", ()):
            section["inputs"] = None
        super()._tables()

    def table_inputs(self):
        base = self.project.base
        return (base, tuple(filecache.stamp(os.path.join(base, name)) for name in
                            ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin"))
                if base else ())

    def section_inputs(self, section, tables):
        factory = section["factory"]
        return (i18n.CODE, tables if factory is not OurCupsEditor else self.project.base,
                factory.refresh_inputs(self.project))

    def refresh_pictures(self, section, stamps):
        # A file can be replaced in-place outside this page. Refresh just its
        # preview, not hundreds of table widgets. Stat each distinct path once.
        editor = section["editor"]
        if editor is None:
            return
        for picture in editor.findChildren(PictureField):
            path = picture.path
            if path and path not in stamps:
                stamps[path] = filecache.stamp(path)
            value = (path, stamps.get(path))
            previous = section["pictures"].get(picture)
            if previous is not None and previous != value:
                picture.show_it()
            section["pictures"][picture] = value

    def project_key(self):
        path = self.project.path
        return (os.path.normcase(os.path.abspath(path)) if path else None,
                self.project.recipe.get("world", ""))

    def capture(self):
        if self._key is None:
            return
        drafts = {i: s["editor"].draft() for i, s in enumerate(self.all_sections)
                  if s["editor"] is not None and s["editor"].dirty_keys()}
        if drafts:
            self._drafts[self._key] = drafts
        else:
            self._drafts.pop(self._key, None)

    def has_drafts(self):
        self.capture()
        return bool(self._drafts)

    def replace_editor(self, section, draft=None):
        old = section["editor"]
        view = old.view_state() if old is not None else {}
        if old is not None:
            section["layout"].removeWidget(old)
            old.hide()
            old.deleteLater()
        section["editor"] = None
        section["pictures"] = {}
        if section["factory"] is GameCupsEditor and self.project.base is None and draft is None:
            self.message(section, _("The game's tables are not unpacked yet."))
        else:
            editor = section["factory"](section["body"], self.project, draft=draft)
            section["editor"] = editor
            if draft:
                editor.restore_draft(draft)
            else:
                editor.restore_view(view)
            editor.changed.connect(lambda s=section: self.update_section(s))
            section["layout"].addWidget(editor, 1)
            self.update_section(section)
        self.update_buttons(section)
        # Snapshot only this section's small input projection; unrelated player/
        # team data is never copied. Widget drafts have their own conflict baseline.
        section["inputs"] = deepcopy(self.section_inputs(section, self.table_inputs()))

    def update_buttons(self, section):
        if section is not self.current_section():
            return
        editor = section["editor"]
        dirty = editor is not None and bool(editor.dirty_keys())
        section["apply"].setEnabled(dirty and (not editor.requires_tables or self.project.base is not None))
        section["discard"].setEnabled(dirty)
        status = _("Unapplied changes (kept until closing).") if dirty else ""
        section["apply"].setToolTip(status)
        section["discard"].setToolTip(status)

    def update_section(self, section):
        editor = section["editor"]
        dirty = editor is not None and bool(editor.dirty_keys())
        self.message(section, _("No leagues available.") if not dirty and editor is not None and not editor.rows else "")
        self.update_buttons(section)

    def refresh(self):
        if not hasattr(self, "sections"):
            return
        self._refresh_timer.stop()
        key = self.project_key()
        if self._recipe is not self.project.recipe:
            self.capture()
            self._recipe, self._key = self.project.recipe, key
            drafts = self._drafts.get(key, {})
            for i, section in enumerate(self.all_sections):
                self.replace_editor(section, drafts.get(i))
        else:
            # Save As / world rename changes the key, not the owner of the draft.
            if key != self._key:
                self.capture()
                saved = self._drafts.pop(self._key, {})
                self._key = key
                if saved:
                    self._drafts[key] = saved
            tables = self.table_inputs()
            for section in self.all_sections:
                inputs = self.section_inputs(section, tables)
                if inputs == section["inputs"]:
                    continue
                editor = section["editor"]
                if editor is None or not editor.dirty_keys():
                    self.replace_editor(section)
                else:
                    if hasattr(editor, "reconcile"):
                        editor.reconcile()
                    self.message(section, _("Your draft is kept. Apply checks changes made elsewhere; Discard reloads the current project."))
                    self.update_buttons(section)
                    section["inputs"] = deepcopy(inputs)
        stamps = {}
        for section in self.all_sections:
            self.refresh_pictures(section, stamps)
        other = [k[1] for k in self._drafts if k != self._key]
        self.say(_("Other worlds have unapplied cup drafts, kept until closing. Reopen their project to resume: %s") % ", ".join(other) if other else "")

    def apply_section(self, section):
        if self._recipe is not self.project.recipe:
            self.refresh()
            return
        editor = section["editor"]
        if editor is None:
            return
        try:
            changed = editor.apply(self.project.recipe)
        except CupConflict as exc:
            self.message(section, str(exc))
            return
        # Reset this editor before touch emits changed; the other section's draft stays intact.
        self.replace_editor(section)
        self.capture()
        if changed:
            self.project.touch()

    def discard_section(self, section):
        if self._recipe is not self.project.recipe:
            self.refresh()
            return
        self.replace_editor(section)
        self.capture()

    def shown(self):
        self.refresh()
