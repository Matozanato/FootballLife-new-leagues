"""Read-only presentation of existing qualification calculations and preset results."""
from dataclasses import dataclass
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QCheckBox, QTreeWidget,
                              QTreeWidgetItem, QHeaderView, QAbstractItemView,
                              QPlainTextEdit)
import fl26world as W
from .. import qualification_data as Q, i18n
from ..i18n import _
from ..ui import hint, Fold

CHANGE_COLOR = "#f5ad40"


def destination_name(target, recipe):
    names = dict(W.COMPETITIONS)
    if target in (3, 9) and Q.modern(recipe):
        return _("%s — group stage") % _(names[target])
    return _(names[target]) if target in names else _("Unavailable destination")


def position_name(position, association=False):
    if association:
        return _("Association rank %d") % position
    if position == 0:
        return _("Cup winner")
    if position < 0 or i18n.CODE != "en":
        return _("Position %d") % position
    suffix = "th" if 10 <= position % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(position % 10, "th")
    return _("%s place") % (str(position) + suffix)


@dataclass(frozen=True)
class AllocationRow:
    target: int
    name: str
    places: str
    status: str
    problem: bool = False


def allocation_rows(sources, recipe, conf):
    """Render the shared counter and actual UEFA direct-room calculation unchanged."""
    counts, _notes = Q.allocation_counts(sources, recipe, conf)
    allowed = dict(Q.destinations(conf, recipe))
    rows = []
    if conf == 2:
        comps = [c for c, n in counts.items() for _i in range(n)] + [e[2] for e in W.HOLDERS]
        for c, (n, capacity) in W.europe_count(comps, bool(recipe.get("uecl", True))).items():
            status = (_("%d automatically filled") % (capacity - n) if n < capacity else
                      _("%d above direct places; qualifying/access rules apply") % (n - capacity) if n > capacity else
                      _("Direct places filled"))
            rows.append(AllocationRow(c, destination_name(c, recipe), "%d / %d" % (n, capacity), status))
        for c in (10, 11, 12):
            if c in allowed:
                rows.append(AllocationRow(c, destination_name(c, recipe), str(counts[c]), _("Resolved by access list and seeding")))
    elif conf == 4 and Q.modern(recipe):
        for c, capacity in Q.MODERN_TOTALS.items():
            if c == 18:
                continue
            n = counts[c]
            status = (_("Complete") if n == capacity else _("%d still to assign") % (capacity - n)
                      if n < capacity else _("%d above capacity") % (n - capacity))
            rows.append(AllocationRow(c, destination_name(c, recipe), "%d / %d" % (n, capacity), status, n != capacity))
    else:
        for c in allowed:
            status = _("Check plan for final field")
            places = str(counts[c])
            if conf == 4:
                status = _("Game defaults and custom places")
                places = _("%d explicit places") % counts[c]
            elif c == 5:
                status = _("Native access retained; check plan")
            rows.append(AllocationRow(c, destination_name(c, recipe), places, status))
    return rows


class AllocationOverview(QTreeWidget):
    """Content-height table: the source detail scroll area owns vertical scrolling."""
    def __init__(self):
        super().__init__()
        self.setColumnCount(3)
        self.setHeaderLabels([_("Competition"), _("Places"), _("Status")])
        self.setRootIsDecorated(False)
        self.setSelectionMode(QAbstractItemView.NoSelection)
        self.setWordWrap(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.header().setSectionResizeMode(2, QHeaderView.Stretch)

    def display(self, rows):
        self.clear()
        for row in rows:
            item = QTreeWidgetItem([row.name, row.places, row.status])
            for col, text in enumerate((row.name, row.places, row.status)):
                item.setToolTip(col, text)
            if row.problem:
                item.setForeground(2, QColor("#f5ad40"))
            self.addTopLevelItem(item)
        self.fit_height()

    def fit_height(self):
        self.doItemsLayout()
        total = self.header().height() + 2 * self.frameWidth()
        total += sum(max(24, self.sizeHintForRow(i)) for i in range(self.topLevelItemCount()))
        if self.horizontalScrollBar().maximum():
            total += self.horizontalScrollBar().sizeHint().height()
        self.setFixedHeight(total + 2)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_height()


class PresetPreview(QWidget):
    def __init__(self, uefa_ranking=False):
        super().__init__()
        self.uefa_ranking = uefa_ranking
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.summary = hint("")
        layout.addWidget(self.summary)
        self.show_unchanged = QCheckBox(_("Show associations without qualification changes") if uefa_ranking else _("Show unchanged sources"))
        self.show_unchanged.toggled.connect(self.populate)
        layout.addWidget(self.show_unchanged)
        self.legend = hint(_("Highlighted in orange: changed qualification places"))
        self.legend.setStyleSheet("color: %s;" % CHANGE_COLOR)
        layout.addWidget(self.legend)
        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels([_("Qualification source"), _("Current"), _("Proposed")])
        self.tree.setWordWrap(True)
        self.tree.setMinimumHeight(0)
        for col in range(3):
            self.tree.header().setSectionResizeMode(col, QHeaderView.Stretch)
        layout.addWidget(self.tree, 1)
        self.details = Fold("Show technical details")
        self.technical = QPlainTextEdit()
        self.technical.setReadOnly(True)
        self.technical.setMaximumHeight(150)
        self.details.body.addWidget(self.technical)
        layout.addWidget(self.details)
        self._data = None

    def display(self, sources, included, before, after, conf, changes, notes, complete, all_sources=None, warning_count=None):
        self._data = sources, before, after, conf, changes
        self._all_sources = sources if all_sources is None else all_sources
        changed_places = sum(sum(old.get(p) != new.get(p) for p in old.keys() | new.keys())
                             for s in sources for old, new in [(self.assignments(s, before), self.assignments(s, after))])
        conf_name = {2: "UEFA", 3: "AFC", 4: "CONMEBOL", 5: "CAF", 6: "CONCACAF", 7: "OFC"}[conf]
        status = (_("Ranking validated for the CUPS draft") if self.uefa_ranking else _("Ready for draft")) if complete else _("Review required — proposal cannot be confirmed")
        warnings = len(notes) if warning_count is None else warning_count
        problems = [r.name + ": " + r.status for r in allocation_rows(self._all_sources, after, conf) if r.problem]
        summary = (_("UEFA ranking · %d included associations · %d qualification changes") % (included, changed_places) if self.uefa_ranking else
                   _("%s · %d included sources · %d changed places") % (conf_name, included, changed_places))
        self.summary.setText(summary + "\n" + status + ("\n" + "; ".join(problems) if problems else "")
                             + ("\n" + _("%d warnings — review technical details before confirming.") % warnings if warnings and complete else "")
                             + ("\n" + _("UEFA ranking and seeding will also be updated.") if conf == 2 and any(k[:2] == ("qualification", "root") for k in changes) else "")
                             + ("\n" + _("Review validation warnings in Show technical details.") if notes and not complete else ""))
        raw = []
        for source in sources:
            raw.extend([source.name, "Current: %r" % Q.effective(source, before), "Proposed: %r" % Q.effective(source, after)])
        raw += Q.overview(self._all_sources, after, conf) + notes
        if self.uefa_ranking:
            for key, label in (("uefa_rank", _("UEFA association order")), ("uefa_off", _("Excluded UEFA associations")), ("uefa_seed", _("UEFA seeding"))):
                raw.extend([label, _("Current: %s") % repr(before.get(key)), _("Proposed: %s") % repr(after.get(key))])
        self.technical.setPlainText("\n".join(raw))
        self.populate()

    @staticmethod
    def assignments(source, recipe):
        result = {}
        for row in Q.effective(source, recipe):
            try:
                p, target = map(int, row)
                result.setdefault(p, []).append(target)
            except (TypeError, ValueError):
                continue
        return result

    def populate(self, *_args):
        if self._data is None:
            return
        sources, before, after, conf, changes = self._data
        self.tree.clear()
        totals = QTreeWidgetItem([_("Allocation overview"), _("Current"), _("Proposed")])
        old_totals = {r.target: r for r in allocation_rows(self._all_sources, before, conf)}
        for row in allocation_rows(self._all_sources, after, conf):
            old = old_totals.get(row.target)
            values = [row.name, (old.places + " · " + old.status) if old else _("No place"), row.places + " · " + row.status]
            child = QTreeWidgetItem(values)
            for col, value in enumerate(values):
                child.setToolTip(col, value)
            totals.addChild(child)
        self.tree.addTopLevelItem(totals)
        totals.setExpanded(True)
        groups = []
        for source in sources:
            old, new = self.assignments(source, before), self.assignments(source, after)
            changed = old != new or source.draft_key in changes
            if not changed and not self.show_unchanged.isChecked():
                continue
            group = QTreeWidgetItem([source.name + " — " + source.country,
                                     _("Changed") if changed else _("Unchanged"), ""])
            group.setToolTip(0, group.text(0))
            for pos in sorted(old.keys() | new.keys(), key=lambda p: (p == 0, p)):
                current = ", ".join(destination_name(c, before) for c in old.get(pos, [])) or _("No place")
                proposed = ", ".join(destination_name(c, after) for c in new.get(pos, [])) or _("No place")
                child = QTreeWidgetItem([position_name(pos, source.kind == "association"), current, proposed])
                different = old.get(pos) != new.get(pos)
                child.setData(0, Qt.UserRole, different)
                for col, text in enumerate((child.text(0), current, proposed)):
                    child.setToolTip(col, text)
                    child.setForeground(col, QColor(CHANGE_COLOR if different else "#98a5b5"))
                group.addChild(child)
            if not group.childCount():
                group.addChild(QTreeWidgetItem([_("No explicit places"), _("No place"), _("No place")]))
            groups.append((not changed, source.name.casefold(), group))
        for _unchanged, _name, group in sorted(groups, key=lambda g: g[:2]):
            self.tree.addTopLevelItem(group)
            group.setExpanded(True)
