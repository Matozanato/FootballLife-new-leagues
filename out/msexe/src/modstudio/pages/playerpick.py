"""the Players page's two small windows: pick players from the whole game (Sign / Call up
players), and pick the club a player moves to (Transfer to)"""
from PySide6.QtCore import Qt, QStringListModel
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QCompleter, QDialog,
                               QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout)

import leaguebuilder as B
import lbplayers as P
from ..i18n import _
from ..ui import hint

SHOWN = 1500           # rows the list shows at once; a filter narrows it down


def candidates(project):
    """[{player (a ref), name, Nationality, Registered Position, Age, rating, where}] of every
    player: the game's, and the new clubs' of the recipe (by "<league>/<k>/<place>")"""
    sq = project.squads()
    teams = project.names()[0]
    out = []
    for r in sq.summary():
        r = dict(r)
        r["where"] = ", ".join(teams.get(t, "#%d" % t) for t in r["clubs"]) or _("no club")
        out.append(r)
    proto = sq.proto()
    pl = project.players()
    for L in project.recipe["leagues"]:
        names = list(L.get("club_names") or [])
        for k in range(L.get("clubs", 0)):
            key = P.new_key(L["name"], k)
            club = names[k] if k < len(names) and names[k] else "%s %02d" % (L["name"], k + 1)
            ed = (pl.get(key) or {}).get("edits") or {}
            gone = set((pl.get(key) or {}).get("remove") or [])
            for r in proto:
                if r["player"] in gone:
                    continue
                m = dict(r)
                m.update(ed.get(r["player"], {}))
                m["player"] = P.new_ref(L["name"], k, int(r["player"]))
                m["name"] = m.get("name") or _("(numbered name)")
                m["rating"] = P.overall(m)
                m["where"] = "%s  (%s)" % (club, L["name"])
                out.append(m)
    return out


class PickPlayers(QDialog):
    """players to sign or call up: a list of the whole game, filtered by country and name"""

    def __init__(self, parent, project, title, country=None, skip=()):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(820, 620)
        self.rows = [r for r in candidates(project) if r["player"] not in set(skip)]
        v = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel(_("Nationality")))
        self.nat = QComboBox()
        self.nat.addItem(_("any country"), None)
        for name, fid in B.country_ids(project.base):
            self.nat.addItem(name, fid)
        i = self.nat.findData(country) if country is not None else 0
        self.nat.setCurrentIndex(max(0, i))
        self.nat.currentIndexChanged.connect(self.fill)
        top.addWidget(self.nat)
        self.name = QLineEdit()
        self.name.setPlaceholderText(_("Name contains..."))
        self.name.textChanged.connect(self.fill)
        top.addWidget(self.name, 1)
        self.free = QCheckBox(_("Only players with no national team"))
        self.free.toggled.connect(self.fill)
        self.free.setVisible(False)
        top.addWidget(self.free)
        v.addLayout(top)
        self.tree = QTreeWidget()
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tree.setHeaderLabels([_("Name"), _("Pos"), _("Age"), _("Rating"), _("Club")])
        for c, w in enumerate((240, 50, 40, 55, 360)):
            self.tree.setColumnWidth(c, w)
        self.tree.setSortingEnabled(True)
        self.tree.itemDoubleClicked.connect(lambda *_a: self.accept())
        v.addWidget(self.tree, 1)
        self.note = hint("")
        v.addWidget(self.note)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self.national = set(project.game_nat)
        self.fill()

    def show_free(self, on):
        self.free.setVisible(on)

    def fill(self):
        fid = self.nat.currentData()
        text = self.name.text().strip().lower()
        free = self.free.isVisible() and self.free.isChecked()
        hits = [r for r in self.rows
                if (fid is None or r.get("Nationality") == str(fid))
                and (not text or text in r["name"].lower())
                and not (free and any(t in self.national for t in r.get("clubs") or []))]
        hits.sort(key=lambda r: -int(r["rating"] or 0))
        self.tree.setSortingEnabled(False)
        self.tree.clear()
        for r in hits[:SHOWN]:
            it = QTreeWidgetItem([r["name"], r.get("Registered Position", ""), r.get("Age", ""), "", r["where"]])
            it.setData(3, Qt.DisplayRole, int(r["rating"] or 0))
            it.setData(0, Qt.UserRole, r["player"])
            self.tree.addTopLevelItem(it)
        self.tree.setSortingEnabled(True)
        self.note.setText((_("%d players") % len(hits)) +
                          ("   " + _("(the best %d shown: type a name to find others)") % SHOWN if len(hits) > SHOWN else "")
                          + "   " + _("Pick several with Ctrl or Shift."))

    def picked(self):
        return [it.data(0, Qt.UserRole) for it in self.tree.selectedItems()]


class PickClub(QDialog):
    """the club a player moves to: a new club of the recipe or one of the game's"""

    def __init__(self, parent, title, text, clubs):
        """clubs: [(label, recipe key)]"""
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(520, 150)
        v = QVBoxLayout(self)
        v.addWidget(hint(text))
        self.box = QComboBox()
        self.box.setEditable(True)
        self.box.setInsertPolicy(QComboBox.NoInsert)
        for label, key in clubs:
            self.box.addItem(label, key)
        c = QCompleter(QStringListModel([l for l, _k in clubs], self), self)
        c.setCaseSensitivity(Qt.CaseInsensitive)
        c.setFilterMode(Qt.MatchContains)
        self.box.setCompleter(c)
        self.box.setCurrentIndex(-1)
        v.addWidget(self.box)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def club(self):
        i = self.box.findText(self.box.currentText())
        return self.box.itemData(i) if i >= 0 else None
