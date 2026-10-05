"""NewLife Database: pick leagues from a NewLife release and put each in the recipe in one go"""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QPushButton, QSplitter, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

import leaguebuilder as B
from .. import newlife as N
from ..i18n import _, tr
from ..ui import hint, error, pick_dir, run_job
from .builder import BuilderPage, Dialog


def key(L):
    return (L["country"], L["name"])


class ClubPickDialog(Dialog):
    """clubs of the release to add to a league: a search over every club, with its league"""

    def __init__(self, parent, rel, skip):
        super().__init__(parent, "Add a club from another league")
        self.v.insertWidget(0, QLabel(_("Search a club or a league; tick one or more.")))
        self.search = QLineEdit()
        self.search.textChanged.connect(self.fill)
        self.v.insertWidget(1, self.search)
        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.v.insertWidget(2, self.list, 1)
        self.scroll.hide()
        self.all = sorted(((c["name"], c.get("league", ""), cid) for cid, c in rel.clubs.items()
                           if cid not in skip and c.get("league")), key=lambda x: (x[0].lower(), x[1]))
        self.list.itemChanged.connect(self.toggled)
        self.n = QLabel("")
        self.v.insertWidget(3, self.n)
        self.picked = []
        self.checked = set()
        self.fill()
        self.setMinimumSize(520, 480)

    def fill(self):
        q = self.search.text().strip().lower()
        self.list.blockSignals(True)
        self.list.clear()
        for name, league, cid in self.all:
            if q and q not in name.lower() and q not in league.lower():
                continue
            it = QListWidgetItem("%s  (%s)" % (name, league))
            it.setData(Qt.UserRole, cid)
            # a box per club, kept across searches (victormican, #83: "checks para agregar de
            # varios a la vez"); Ctrl/Shift+click still work and count as picked too
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if cid in self.checked else Qt.Unchecked)
            self.list.addItem(it)
            if self.list.count() >= 500 and not q:
                break
        self.list.blockSignals(False)
        self.count()

    def toggled(self, it):
        cid = it.data(Qt.UserRole)
        if it.checkState() == Qt.Checked:
            self.checked.add(cid)
        else:
            self.checked.discard(cid)
        self.count()

    def count(self):
        self.n.setText(_("%d picked") % len(self.checked) if self.checked else "")

    def ok(self):
        sel = [it.data(Qt.UserRole) for it in self.list.selectedItems()]
        self.picked = [cid for _n, _l, cid in self.all if cid in self.checked or cid in sel]
        self.accept()


class UpdateDialog(Dialog):
    """the leagues an update brings to a newer NewLife, each with what happens to its clubs and
    a choice: this version's clubs for the league, or the person's own line-up"""

    def __init__(self, parent, rel, leagues, rows):
        super().__init__(parent, "Update my leagues to this version")
        self.form.addRow(hint(_("Clubs and players come from %s. Each league keeps its name, division, format, "
                                "European places and cups, and a club that stays keeps its manager and the crest "
                                "you picked. Player changes you made on the Players page for these clubs are "
                                "replaced.") % rel.version))
        self.boxes = []
        for x in leagues:
            mine = {str(i) for i in (x.get("newlife") or {}).get("clubs") or []} | \
                   {str(e["id"]) for e in x.get("game_clubs") or []}
            try:
                _L, E = N.lineup(rel, x, rows, keep=False)
            except N.Error as e:
                self.form.addRow(QLabel(x["name"]), QLabel(tr(str(e))))
                continue
            theirs = set(E["clubs"]) | set(E["in_game"])
            own = max(int(x.get("clubs") or 0) - len(mine), 0)       # the person's own clubs stay either way
            text = _("%d clubs now, %d in %s") % (len(mine) + own, len(theirs) + own, rel.version)
            if mine != theirs:
                text += "  " + _("(%d new, %d not in it)") % (len(theirs - mine), len(mine - theirs))
            box = QCheckBox(_("Keep my clubs"))
            box.setChecked(N.keeps_lineup(x))
            box.setToolTip(_("Ticked: the league keeps the clubs it has (their squads still come from this "
                             "version). Unticked: it gets the clubs it has in this version."))
            box.setEnabled(mine != theirs)
            if mine == theirs:
                box.setChecked(False)
            w = QWidget()
            h = QVBoxLayout(w)
            h.setContentsMargins(0, 0, 0, 0)
            h.addWidget(QLabel(text))
            h.addWidget(box)
            self.form.addRow(QLabel(x["name"]), w)
            self.boxes.append((x, box))
        self.keep = {}

    def ok(self):
        self.keep = {id(x): box.isChecked() for x, box in self.boxes}
        self.accept()


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
        self.custom = {}          # (country, league) -> {"off": {club ids left out}, "extra": [club ids]}
        self.action("Open NewLife Database...", self.open_dir)
        self.b_add = self.action("Add to the recipe", self.add, "primary",
                                 tip="Each selected league becomes a new league with its clubs and players")
        self.b_update = self.action("Update my leagues to this version", self.update,
                                    tip="Leagues you added from another NewLife version get this version's clubs "
                                        "and players; their division, format, European places and cups stay")
        self.b_update.setEnabled(False)
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
        self.clubs.itemChanged.connect(self.club_ticked)
        rv.addWidget(hint(_("Untick a club to leave it out; add clubs of other leagues (two promoted ones, say).")))
        rv.addWidget(self.clubs, 1)
        self.b_extra = QPushButton(_("Add a club from another league..."))
        self.b_extra.clicked.connect(self.add_extra)
        self.b_extra.setEnabled(False)
        rv.addWidget(self.b_extra)
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
            self.custom = {}
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
            E = self.effective(L)
            ok = N.fits(E, info)
            it = QTreeWidgetItem([L["name"] + ("  *" if key(L) in self.custom else ""), L["country"],
                                  str(len(E["clubs"])), str(len(E["in_game"]) or ""),
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

    def effective(self, L):
        """league L with the clubs left out and the ones added from other leagues (self.custom)"""
        c = self.custom.get(key(L))
        if not c:
            return L
        extra = [i for i in c["extra"] if self.rel and i in self.rel.clubs]
        new = [i for i in L["clubs"] if i not in c["off"]] + [i for i in extra if self.rel.clubs[i].get("in_game") != "1"]
        game = [i for i in L["in_game"] if i not in c["off"]] + [i for i in extra if self.rel.clubs[i].get("in_game") == "1"]
        return dict(L, clubs=sorted(new), in_game=sorted(game))

    def show_league(self):
        self.clubs.blockSignals(True)
        self.clubs.clear()
        sel = self.picked()
        self.b_extra.setEnabled(len(sel) == 1 and bool(self.rel))
        if len(sel) != 1 or not self.rel:
            self.clubs.blockSignals(False)
            self.count()
            return
        L = sel[0]
        c = self.custom.get(key(L), {"off": set(), "extra": []})
        rows = [(cid, False) for cid in L["clubs"] + L["in_game"]] + [(cid, True) for cid in c["extra"]]
        for cid, extra in sorted(rows, key=lambda r: (r[0] in L["in_game"] or self.rel.clubs[r[0]].get("in_game") == "1",
                                                      self.rel.clubs[r[0]]["name"].lower())):
            club = self.rel.clubs[cid]
            note = _("in the game") if club.get("in_game") == "1" else str(len(self.rel.squads.get(cid, [])))
            if extra:
                note += "  " + _("from %s") % club.get("league", "")
            it = QTreeWidgetItem([club["name"], note])
            it.setData(0, Qt.UserRole, (cid, extra))
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(0, Qt.Unchecked if cid in c["off"] else Qt.Checked)
            if club.get("in_game") == "1":
                for k in range(2):
                    it.setForeground(k, Qt.gray)
            self.clubs.addTopLevelItem(it)
        self.clubs.blockSignals(False)
        self.count()

    def custom_of(self, L):
        return self.custom.setdefault(key(L), {"off": set(), "extra": []})

    def tidy(self, L):
        c = self.custom.get(key(L))
        if c is not None and not c["off"] and not c["extra"]:
            del self.custom[key(L)]

    def club_ticked(self, it, col):
        sel = self.picked()
        if len(sel) != 1 or col != 0:
            return
        L = sel[0]
        cid, extra = it.data(0, Qt.UserRole)
        c = self.custom_of(L)
        if it.checkState(0) == Qt.Checked:
            c["off"].discard(cid)
        elif extra:
            c["extra"].remove(cid)
        else:
            c["off"].add(cid)
        self.tidy(L)
        self.refresh_row(L)

    def refresh_row(self, L):
        cur = self.tree.currentItem()
        i = cur.data(0, Qt.UserRole) if cur else None
        self.fill()
        for n in range(self.tree.topLevelItemCount()):
            if self.tree.topLevelItem(n).data(0, Qt.UserRole) == i:
                self.tree.setCurrentItem(self.tree.topLevelItem(n))
                break

    def add_extra(self):
        sel = self.picked()
        if len(sel) != 1 or not self.rel:
            return
        L = sel[0]
        c = self.custom_of(L)
        d = ClubPickDialog(self, self.rel, set(L["clubs"]) | set(L["in_game"]) | set(c["extra"]))
        if d.finish() and d.picked:
            c["extra"] += d.picked
        self.tidy(L)
        self.refresh_row(L)

    def count(self):
        info = self.info()
        used = sum(B.new_club_count(L) for L in self.project.recipe["leagues"])
        sel = sum(len(E["clubs"]) for E in map(self.effective, self.picked()) if N.fits(E, info)) if self.rows else 0
        room = self.room if self.room is not None else 0
        text = _("New clubs in the recipe: %d of the %d the game takes.") % (used, room)
        if sel:
            text += "  " + _("Selected: %d more.") % sel
        old = N.outdated(self.project.recipe, self.rel) if self.rel else []
        if old:
            text += "\n" + _("%d of your leagues are from another NewLife version (%s): Update my leagues to this "
                             "version brings them to %s.") % (len(old), ", ".join(x["name"] for x in old),
                                                               self.rel.version)
        self.foot.setText(text)
        self.b_add.setEnabled(bool(sel) and used + sel <= room)
        self.b_update.setEnabled(bool(old))

    def update(self):
        old = N.outdated(self.project.recipe, self.rel) if self.rel else []
        if not old:
            return
        d = UpdateDialog(self, self.rel, old, self.rows)
        if not d.finish():
            return
        info = self.info()
        done, notes, failed = [], [], []
        for x in old:
            try:
                name, _st, _el, nt = N.update_league(self.project.recipe, self.rel, x, self.rows, info=info,
                                                     keep=d.keep.get(id(x)))
            except N.Error as e:
                failed.append(str(e))
                continue
            done.append(name)
            notes += nt
        if done:
            self.project.touch()
        text = _("Updated to %s: %s. Build again and start a new career.") % (self.rel.version, ", ".join(done)) \
            if done else ""
        for t in notes + failed:
            text += ("\n" if text else "") + tr(t)
        self.say(text, "ok" if done and not failed else "")
        self.count()

    def add(self):
        info = self.info()
        sel = [E for E in map(self.effective, self.picked()) if N.fits(E, info)]
        if not sel or not self.rel:
            return
        used = {str(i) for x in self.project.recipe["leagues"] for i in (x.get("newlife") or {}).get("clubs") or []}
        seen = {}
        for E in sel:
            for i in E["clubs"]:
                where = "the recipe" if i in used else seen.get(i)
                if where:
                    error(self, "NewLife Database", _("%s would play in two leagues (%s and %s).")
                          % (self.rel.clubs[i]["name"], where, E["name"]))
                    return
                seen[i] = E["name"]
        names, swap = [], []
        stayed = elsewhere = 0
        for L in sel:
            if not L["country"]:
                error(self, "NewLife Database", _("%s has no country the game knows.") % L["name"])
                continue
            name, st, el = N.add_league(self.project.recipe, self.rel, L, info=info, custom=key(L) in self.custom)
            names.append(name)
            stayed += st
            elsewhere += el
            if info:
                swap += [info["clubs"][e["id"]][0] for e in self.project.recipe["leagues"][-1].get("game_clubs") or []
                         if B.game_club_where(info, e["id"])]
        if names:
            self.project.touch()
            text = _("Added: %s. Change them on Leagues, New clubs and Players, then Build.") % ", ".join(names)
            if swap:
                text += "\n" + _("%s also play in a competition of the game: on New clubs pick each one and use "
                                 "Club of the game to choose the club that takes its place there.") % ", ".join(swap)
            if stayed:
                text += "\n" + _("%d players stay at their game club (their club would have too few players).") % stayed
            if elsewhere:
                text += "\n" + _("%d players are not added: another league already has them.") % elsewhere
            self.say(text, "ok")
