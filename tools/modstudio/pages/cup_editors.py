"""Domestic cup widgets shared by the Cups page and the legacy dialog entry points.

Drafts contain only cup fields, never whole leagues, players or project snapshots.
"""
from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLineEdit, QTableWidget,
                              QTableWidgetItem, QCheckBox, QHeaderView)
import leaguebuilder as B
from ..i18n import _
from ..ui import hint
from .builder import PictureField, OWN_CUP_FIELDS, own_cup_values

OUR_FIELDS = OWN_CUP_FIELDS
GAME_FIELDS = ("league_cup", "super_cup", "name", "logo", "super_name", "super_logo")


def league_source(league):
    return {k: league[k] for k in OUR_FIELDS + ("name", "above", "season", "exhibition", "others")
            if k in league}


class CupConflict(ValueError):
    pass


class CupTable(QTableWidget):
    """Share spare width between names, retaining readable fields on narrow pages."""
    name_columns = ()

    def edit(self, index, *args):
        # QAbstractItemView.mouseMoveEvent calls edit(NoEditTriggers) even for
        # button-free hover. With setCellWidget(), Qt focuses the persistent
        # editor before checking the trigger, scrolling a clipped row into view.
        # Keep the normal mouse-move path (hover/selection/drag auto-scroll), but
        # don't activate an editor merely because the pointer passed over it.
        if len(args) == 2:
            trigger, event = args
            if (trigger == self.EditTrigger.NoEditTriggers and event is not None
                    and event.type() == QEvent.MouseMove
                    and event.buttons() == Qt.NoButton):
                return False
        return super().edit(index, *args)

    def fit_names(self):
        if not self.name_columns:
            return
        fixed = sum(self.columnWidth(c) for c in range(self.columnCount()) if c not in self.name_columns)
        width = max(160, (self.viewport().width() - fixed) // len(self.name_columns))
        for col in self.name_columns:
            if self.columnWidth(col) != width:
                self.setColumnWidth(col, width)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_names()


class CupEditor(QWidget):
    changed = Signal()
    requires_tables = False

    def __init__(self, parent, project):
        super().__init__(parent)
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(0, 0, 0, 0)
        self.project = project

    def setup(self):
        self.search = QLineEdit()
        self.search.setPlaceholderText(_("Find a league..."))
        self.search.textChanged.connect(self.filter_rows)
        self.v.insertWidget(1, self.search)
        # Let the table own horizontal scrolling, not the outer page. Names share spare width.
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        self.table.name_columns = (2, 5) if isinstance(self, GameCupsEditor) else (2, 5, 8)
        for col in self.table.name_columns:
            header.setSectionResizeMode(col, QHeaderView.Interactive)
        self.table.fit_names()
        self.table.setMinimumWidth(0)
        self._initial = self.state()
        self._sources = self.sources(self.project.recipe)
        self._values = self.row_values()
        self._base = self.project.base
        for row in range(self.table.rowCount()):
            for col in range(1, self.table.columnCount()):
                widget = self.table.cellWidget(row, col)
                if isinstance(widget, QCheckBox):
                    widget.toggled.connect(self.changed)
                elif isinstance(widget, QLineEdit):
                    widget.textChanged.connect(self.changed)
                elif isinstance(widget, PictureField):
                    widget.changed = self.changed.emit

    def keys(self):
        return [r[0] for r in self.rows] if isinstance(self, GameCupsEditor) else [L["name"] for L, _ in self.rows]

    def state(self):
        result = {}
        for row, key in enumerate(self.keys()):
            values = []
            for col in range(1, self.table.columnCount()):
                widget = self.table.cellWidget(row, col)
                values.append(widget.isChecked() if isinstance(widget, QCheckBox) else
                              widget.text() if isinstance(widget, QLineEdit) else widget.path)
            result[key] = tuple(values)
        return result

    def restore(self, state):
        for row, key in enumerate(self.keys()):
            if key not in state:
                continue
            for col, value in enumerate(state[key], 1):
                widget = self.table.cellWidget(row, col)
                if isinstance(widget, QCheckBox):
                    widget.setChecked(value)
                elif isinstance(widget, QLineEdit):
                    widget.setText(value)
                else:
                    widget.path = value
                    widget.show_it()

    def filter_rows(self, text):
        want = text.strip().casefold()
        for row in range(self.table.rowCount()):
            self.table.setRowHidden(row, want not in self.table.item(row, 0).text().casefold())

    def dirty_keys(self):
        return {k for k, v in self.state().items() if v != self._initial.get(k)}

    def draft(self):
        return {"state": self.state(), "initial": self._initial, "sources": self._sources,
                "search": self.search.text(), "base": self._base, "values": self._values,
                "tops": getattr(self, "tops", None), "leagues": getattr(self, "leagues", None)}

    def view_state(self):
        return {"search": self.search.text()}

    def restore_view(self, view):
        self.search.setText(view.get("search", ""))

    def restore_draft(self, draft):
        # Rebuild from the original sources first: even a league removed externally remains
        # visible until the user explicitly discards its draft. apply() detects the conflict.
        self._initial = draft["initial"]
        self._sources = draft["sources"]
        self._base = draft["base"]
        self._values = draft["values"]
        self.restore(draft["state"])
        self.search.setText(draft["search"])

    def row_values(self):
        return ({c["league"]: c for c in self.value()} if isinstance(self, GameCupsEditor) else self.value())

    def sources(self, recipe):
        if isinstance(self, GameCupsEditor):
            return {int(c["league"]): dict(c) for c in recipe.get("game_cups") or []
                    if str(c.get("league")).isdigit()}
        return {L["name"]: league_source(L) for L in recipe.get("leagues") or []
                if L.get("above") in (None, "") and not L.get("exhibition") and not L.get("others")}

    def apply(self, recipe):
        dirty = self.dirty_keys()
        if not dirty:
            return False
        if self._base != self.project.base:
            raise CupConflict(_("The game tables changed. Your draft is kept; Discard to reload the current project."))
        if isinstance(self, GameCupsEditor):
            live_tops = {rid: has_super for rid, _name, has_super in B.game_tops(self.project.base)}
            old_tops = {rid: has_super for rid, _name, has_super in self.tops}
            if any(k not in live_tops or live_tops[k] != old_tops[k] for k in dirty):
                raise CupConflict(_("The game's leagues changed. Discard to reload the current project."))
        current = self.sources(recipe)
        fields = GAME_FIELDS if isinstance(self, GameCupsEditor) else OUR_FIELDS
        values = self.row_values()
        patches = {}
        missing = object()
        for key in dirty:
            before, now = self._sources.get(key, {}), current.get(key, {})
            desired = values.get(key, {})
            # Context changes (renaming/removal, division or season) require an explicit reload.
            if isinstance(self, OurCupsEditor) and (key not in current or any(
                    now.get(k) != before.get(k) for k in ("above", "season", "exhibition", "others"))):
                raise CupConflict(_("A league was removed, renamed or changed its season/division. Discard to reload the current project."))
            if isinstance(self, GameCupsEditor) and ((key not in values and now != before)
                    or (key in self._sources and key not in current and key in values)):
                raise CupConflict(_("Cup settings changed elsewhere. Your draft is kept; Discard to reload the current project."))
            patch = {}
            for field in fields:
                old, new, live = before.get(field, missing), desired.get(field, missing), now.get(field, missing)
                # Compare to the initial widget serialization, so merely editing a name does
                # not normalize untouched legacy flags or names elsewhere in the same row.
                if new == self._values.get(key, {}).get(field, missing):
                    continue
                if live != old and live != new:
                    raise CupConflict(_("Cup settings changed elsewhere. Your draft is kept; Discard to reload the current project."))
                patch[field] = new
            merged = dict(now)
            for field, value in patch.items():
                if value is missing:
                    merged.pop(field, None)
                else:
                    merged[field] = value
            if isinstance(self, OurCupsEditor) and merged.get("supercup") and not merged.get("cup"):
                raise CupConflict(_("The national cup changed elsewhere. Discard to reload the current project before enabling its super cup."))
            patches[key] = patch
        changed = False
        if isinstance(self, GameCupsEditor):
            cups = [dict(c) for c in recipe.get("game_cups") or []]
            for key, patch in patches.items():
                item = next((c for c in cups if str(c.get("league")) == str(key)), None)
                if item is None:
                    item = {"league": key}
                    cups.append(item)
                for field, value in patch.items():
                    if value is missing:
                        item.pop(field, None)
                    else:
                        item[field] = value
                if key not in values:
                    cups.remove(item)
            if cups != (recipe.get("game_cups") or []):
                if cups:
                    recipe["game_cups"] = cups
                else:
                    recipe.pop("game_cups", None)
                changed = True
        else:
            by_name = {L["name"]: L for L in recipe.get("leagues") or []}
            for key, patch in patches.items():
                league = by_name[key]
                for field, value in patch.items():
                    if value is missing:
                        if field in league:
                            league.pop(field)
                            changed = True
                    elif league.get(field, missing) != value:
                        league[field] = value
                        changed = True
        return changed


class GameCupsEditor(CupEditor):
    """the recipe's game_cups: a league cup, and a super cup where the game has none, for the
    game's own top divisions (the Carabao Cup for the Premier League)"""
    requires_tables = True

    @staticmethod
    def refresh_inputs(project):
        return [{k: cup[k] for k in ("league",) + GAME_FIELDS if k in cup}
                for cup in project.recipe.get("game_cups") or []]

    def __init__(self, parent, project, draft=None):
        super().__init__(parent, project)
        self.tops = draft["tops"] if draft else B.game_tops(project.base)
        have = {int(c["league"]): c for c in project.recipe.get("game_cups") or [] if str(c.get("league")).isdigit()}
        self.v.insertWidget(0, hint(_("A league cup is the league and the one below it, up to 44 clubs (the "
                                      "Premier League and the Championship), one match a round from late "
                                      "August to mid-March (a calendar-year league: September to December), drawn at random; the league's own clubs get the "
                                      "byes and start in the second round. A super cup -- the "
                                      "champion v the cup winner in late July (a calendar-year league: at the end "
                                      "of January) -- only where the game has none. "
                                      "Empty name = the league's name and League Cup / Super Cup; "
                                      "no logo = an emblem with the cup's initials.")))
        self.table = CupTable(len(self.tops), 7)
        self.table.setHorizontalHeaderLabels([_("League"), _("League cup"), _("Name"), _("Logo"),
                                              _("Super cup"), _("Name"), _("Logo")])
        self.table.verticalHeader().hide()
        self.rows = []
        for i, (rid, name, has_super) in enumerate(self.tops):
            c = have.get(rid, {})
            item = QTableWidgetItem(name)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 0, item)
            lc, ln = QCheckBox(), QLineEdit(c.get("name", ""))
            lc.setChecked(bool(c) and bool(c.get("league_cup", True)))
            sc, sn = QCheckBox(), QLineEdit(c.get("super_name", ""))
            sc.setChecked(bool(c.get("super_cup")) and not has_super)
            ln.setPlaceholderText(name + " League Cup")
            sn.setPlaceholderText(_("the game has one") if has_super else name + " Super Cup")
            lg = PictureField(c.get("logo"), 32, compact=True)
            sg = PictureField(c.get("super_logo"), 32, compact=True)
            sc.setEnabled(not has_super)
            sn.setEnabled(not has_super)
            sg.setEnabled(not has_super)
            for col, w in ((1, lc), (2, ln), (3, lg), (4, sc), (5, sn), (6, sg)):
                self.table.setCellWidget(i, col, w)
            self.table.setRowHeight(i, 52)
            self.rows.append((rid, lc, ln, lg, sc, sn, sg))
        self.table.resizeColumnsToContents()
        pic = PictureField(None, 32, compact=True).sizeHint().width() + 12
        for col, w in ((2, 220), (5, 220), (3, pic), (6, pic)):
            self.table.setColumnWidth(col, w)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setMinimumSize(0, 300)
        self.v.insertWidget(1, self.table, 1)
        self.setup()

    def value(self):
        cups = []
        for rid, lc, ln, lg, sc, sn, sg in self.rows:
            if not (lc.isChecked() or sc.isChecked()):
                continue
            c = {"league": rid, "league_cup": lc.isChecked(), "super_cup": sc.isChecked()}
            for key, w in (("name", ln), ("super_name", sn)):
                if w.text().strip():
                    c[key] = w.text().strip()
            for key, f in (("logo", lg), ("super_logo", sg)):
                if f.path:
                    c[key] = f.path
            cups.append(c)
        return cups


class OurCupsEditor(CupEditor):
    """the cups of the world's own leagues in one table -- the national cup, the super cup and the
    league cup of every top division (no league above it, not an exhibition league, not the clubs
    in no league): the same recipe fields Edit league writes"""

    @staticmethod
    def refresh_inputs(project):
        return [league_source(L) for L in project.recipe.get("leagues") or []
                if L.get("above") in (None, "") and not L.get("exhibition") and not L.get("others")]

    def __init__(self, parent, project, draft=None):
        super().__init__(parent, project)
        self.leagues = draft["leagues"] if draft else [league_source(L) for L in project.recipe.get("leagues") or []
                        if L.get("above") in (None, "") and not L.get("exhibition") and not L.get("others")]
        self.v.insertWidget(0, hint(_("The cups of your own leagues in one place: for each top division its "
                                      "national cup (the league and the division below it), the super cup "
                                      "(champion v cup winner, it needs the national cup) and a league cup. "
                                      "The same as Edit league. Empty name = the league's name and Cup / "
                                      "Super Cup / League Cup; no logo = an emblem with the cup's initials.")))
        heads = [_("League"), _("National cup"), _("Name"), _("Logo"), _("Super cup"), _("Name"), _("Logo"),
                 _("League cup"), _("Name"), _("Logo")]
        self.table = CupTable(len(self.leagues), len(heads))
        self.table.setHorizontalHeaderLabels(heads)
        self.table.verticalHeader().hide()
        self.rows = []
        for i, L in enumerate(self.leagues):
            item = QTableWidgetItem(L.get("name", ""))
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 0, item)
            name = L.get("name", "")
            cells = []
            for key, ph in (("cup", " Cup"), ("supercup", " Super Cup"), ("league_cup", " League Cup")):
                on = QCheckBox()
                on.setChecked(bool(L.get(key)))
                nm = QLineEdit(L.get(key + "_name", ""))
                nm.setPlaceholderText(name + ph)
                lg = PictureField(L.get(key + "_logo"), 32, compact=True)
                cells += [on, nm, lg]
            cup, scup, lcup = cells[0], cells[3], cells[6]

            def follow(_on=False, cup=cup, scup=scup):
                scup.setEnabled(cup.isChecked())
            cup.toggled.connect(follow)
            follow()
            if L.get("season") == "calendar":
                lcup.setChecked(bool(L.get("league_cup")))
                lcup.setEnabled(bool(L.get("league_cup")))
                lcup.setToolTip(_("A league playing February to December has no split, Apertura/Clausura or league cup yet."))
            for col, w in enumerate(cells, 1):
                self.table.setCellWidget(i, col, w)
            self.table.setRowHeight(i, 52)
            self.rows.append((L, cells))
        self.table.resizeColumnsToContents()
        pic = PictureField(None, 32, compact=True).sizeHint().width() + 12
        for col in (2, 5, 8):
            self.table.setColumnWidth(col, 200)
        for col in (3, 6, 9):
            self.table.setColumnWidth(col, pic)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setMinimumSize(0, 300)
        self.v.insertWidget(1, self.table, 1)
        self.setup()

    def value(self):
        result = {}
        for source, cells in self.rows:
            result[source["name"]] = own_cup_values([
                (cells[n].isChecked(), cells[n + 1].text(), cells[n + 2].path)
                for n in (0, 3, 6)
            ])
        return result
