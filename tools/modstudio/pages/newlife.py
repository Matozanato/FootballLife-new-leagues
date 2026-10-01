"""NewLife Database: pick leagues from a NewLife release and put each in the recipe in one go"""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QLabel, QLineEdit, QSplitter, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget)

import leaguebuilder as B
from .. import newlife as N
from ..i18n import _
from ..ui import hint, error, pick_dir, run_job
from .builder import BuilderPage


class NewLife(BuilderPage):
    title = "NewLife Database"
    hint = ("Real clubs and players for new leagues. Put the NewLife parts you downloaded (a continent each) "
            "in one folder, open it, pick leagues and add them: each becomes a new league with its clubs and "
            "their squads, ready to Build.")

    def __init__(self, app):
        super().__init__(app)
        self.rel = None
        self.rows = []
        self.room = None
        self.action("Open NewLife Database...", self.open_dir)
        self.b_add = self.action("Add to the recipe", self.add, "primary",
                                 tip="Each selected league becomes a new league with its clubs and players")
        self.where = hint(_("No NewLife Database opened."))
        self.outer.addWidget(self.where)
        self.search = QLineEdit()
        self.search.setPlaceholderText(_("Search leagues or countries"))
        self.search.textChanged.connect(self.fill)
        self.outer.addWidget(self.search)
        split = QSplitter(Qt.Horizontal)
        self.tree = QTreeWidget()
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tree.setHeaderLabels([_("League"), _("Country"), _("Clubs"), _("In game"), _("Players"), _("Level"), ""])
        for c, w in enumerate((300, 150, 55, 60, 65, 55, 220)):
            self.tree.setColumnWidth(c, w)
        self.tree.itemSelectionChanged.connect(self.show_league)
        split.addWidget(self.tree)
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(8, 0, 0, 0)
        self.clubs = QTreeWidget()
        self.clubs.setRootIsDecorated(False)
        self.clubs.setHeaderLabels([_("Club"), _("Players")])
        self.clubs.setColumnWidth(0, 260)
        rv.addWidget(self.clubs, 1)
        split.addWidget(right)
        split.setSizes([820, 340])
        self.outer.addWidget(split, 1)
        self.foot = hint("")
        self.outer.addWidget(self.foot)
        self.project.changed.connect(self.count)

    def shown(self):
        if self.need_tables():
            return
        if self.room is None:
            self.room = B.clubs_room(self.project.base)
        folder = self.app.settings.get("newlife")
        if self.rel is None and folder and os.path.isdir(folder):
            self.load(folder)
        self.count()

    def info(self):
        """what the game's tables say about its own clubs (leaguebuilder.game_info), None without them"""
        try:
            return B.game_info(self.project.base) if self.project.base else None
        except OSError:
            return None

    def open_dir(self):
        d = pick_dir(self, "Open NewLife Database...", self.app.settings.get("newlife", ""))
        if d:
            self.load(d)

    def load(self, folder):
        self.where.setText(_("Reading %s ...") % folder)
        self.app.busy(True)

        def done(rel):
            self.app.busy(False)
            self.rel = rel
            self.app.settings["newlife"] = folder
            text = "%s  -  %s" % (rel.version, rel.folder)
            if rel.parts:
                text += "\n" + _("Parts: %s") % ", ".join(rel.parts)
            self.where.setText(text)
            names = dict((i, n) for n, i in B.country_ids(self.project.base)) if self.project.base else {}
            self.rows = rel.leagues(lambda c: names.get(int(c), "").split(" (")[0])
            self.fill()

        def failed(tb):
            self.app.busy(False)
            self.where.setText(_("No NewLife Database opened."))
            error(self, "NewLife Database", tb.strip().splitlines()[-1])

        run_job(lambda progress: N.Release(folder), done, failed)

    def fill(self):
        q = self.search.text().strip().lower()
        info = self.info()
        self.tree.clear()
        for i, L in enumerate(self.rows):
            if q and q not in L["name"].lower() and q not in L["country"].lower():
                continue
            ok = N.fits(L, info)
            it = QTreeWidgetItem([L["name"], L["country"], str(len(L["clubs"])), str(len(L["in_game"]) or ""),
                                  str(L["players"]), str(L["strength"]), "" if ok else _("a league takes %d to %d clubs")
                                  % (B.CLUBS_MIN, B.CLUBS_MAX)])
            it.setData(0, Qt.UserRole, i)
            it.setToolTip(3, _("Clubs of this league the game already has: they join the new league with "
                               "their own names, crests, kits and players"))
            if not ok:
                for c in range(7):
                    it.setForeground(c, Qt.gray)
            self.tree.addTopLevelItem(it)
        self.count()

    def picked(self):
        return [self.rows[it.data(0, Qt.UserRole)] for it in self.tree.selectedItems()]

    def show_league(self):
        self.clubs.clear()
        sel = self.picked()
        if len(sel) != 1 or not self.rel:
            self.count()
            return
        for cid in sorted(sel[0]["clubs"], key=lambda i: self.rel.clubs[i]["name"].lower()):
            self.clubs.addTopLevelItem(QTreeWidgetItem([self.rel.clubs[cid]["name"],
                                                        str(len(self.rel.squads.get(cid, [])))]))
        for cid in sel[0]["in_game"]:
            it = QTreeWidgetItem([self.rel.clubs[cid]["name"], _("in the game")])
            for c in range(2):
                it.setForeground(c, Qt.gray)
            self.clubs.addTopLevelItem(it)
        self.count()

    def count(self):
        info = self.info()
        used = sum(B.new_club_count(L) for L in self.project.recipe["leagues"])
        sel = sum(len(L["clubs"]) for L in self.picked() if N.fits(L, info)) if self.rows else 0
        room = self.room if self.room is not None else 0
        text = _("New clubs in the recipe: %d of the %d the game takes.") % (used, room)
        if sel:
            text += "  " + _("Selected: %d more.") % sel
        self.foot.setText(text)
        self.b_add.setEnabled(bool(sel) and used + sel <= room)

    def add(self):
        info = self.info()
        sel = [L for L in self.picked() if N.fits(L, info)]
        if not sel or not self.rel:
            return
        names, swap = [], []
        for L in sel:
            if not L["country"]:
                error(self, "NewLife Database", _("%s has no country the game knows.") % L["name"])
                continue
            names.append(N.add_league(self.project.recipe, self.rel, L, info=info))
            if info:
                swap += [info["clubs"][e["id"]][0] for e in self.project.recipe["leagues"][-1].get("game_clubs") or []
                         if B.game_club_where(info, e["id"])]
        if names:
            self.project.touch()
            text = _("Added: %s. Change them on New leagues, New clubs and Players, then Build.") % ", ".join(names)
            if swap:
                text += "\n" + _("%s also play in a competition of the game: on New clubs pick each one and use "
                                 "Club of the game to choose the club that takes its place there.") % ", ".join(swap)
            self.say(text, "ok")
