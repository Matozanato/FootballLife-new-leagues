"""NewLife Database: pick leagues from a NewLife release and put each in the recipe in one go"""
import copy, os

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QPushButton, QSplitter, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
                               QWidget)

import leaguebuilder as B
import lbplayers as P
from .. import newlife as N
from ..i18n import _, tr
from ..ui import hint, error, pick_dir, run_job
from .builder import BuilderPage, Dialog


def key(L):
    return (L["country"], L["name"])


class ClubPickDialog(Dialog):
    """clubs of the release to add to a league: a search over every club, with its league"""

    def __init__(self, parent, rel, skip, game=()):
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
        # B95 (vmican 17.10.): the release's clubs the game has (Envigado, its twin) are found too,
        # greyed with the way in, not missing as if they did not exist
        self.game = sorted(((rel.clubs[cid]["name"], rel.clubs[cid].get("league", ""), cid) for cid in game
                            if cid in rel.clubs), key=lambda x: (x[0].lower(), x[1]))
        self.list.itemChanged.connect(self.toggled)
        # vmican (16.10., beta): tick a whole search at once -- e.g. search a league, tick all
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        self.b_all = QPushButton(_("Tick all shown"))
        self.b_all.setToolTip(_("Ticks every club the list shows now: search a league first to add its clubs"))
        self.b_all.clicked.connect(lambda: self.tick_shown(True))
        self.b_none = QPushButton(_("Untick all"))
        self.b_none.clicked.connect(lambda: self.tick_shown(False))
        h.addWidget(self.b_all)
        h.addWidget(self.b_none)
        h.addStretch(1)
        self.v.insertWidget(3, row)
        self.n = QLabel("")
        self.v.insertWidget(4, self.n)
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
        for name, league, cid in self.game if q else []:
            if q not in name.lower() and q not in league.lower():
                continue
            it = QListWidgetItem("%s  (%s)  -- %s" % (name, league, _("a club of the game: Club of the game... puts it here")))
            it.setFlags(it.flags() & ~(Qt.ItemIsSelectable | Qt.ItemIsEnabled))
            it.setToolTip(_("The game has this club, with its team ID: in Clubs, Club of the game... puts it in this "
                            "place, and moves it from another league of your world."))
            self.list.addItem(it)
        self.list.blockSignals(False)
        self.b_all.setEnabled(bool(q))          # not 500 clubs of any league at once
        self.count()

    def toggled(self, it):
        cid = it.data(Qt.UserRole)
        if it.checkState() == Qt.Checked:
            self.checked.add(cid)
        else:
            self.checked.discard(cid)
        self.count()

    def tick_shown(self, on):
        """tick (on) every club the list shows now, or untick every club, shown or not"""
        if not on:
            self.checked.clear()
        self.list.blockSignals(True)
        for i in range(self.list.count()):
            it = self.list.item(i)
            if it.data(Qt.UserRole) is None:         # a club of the game, greyed (B95)
                continue
            if on:
                self.checked.add(it.data(Qt.UserRole))
            it.setCheckState(Qt.Checked if on else Qt.Unchecked)
        self.list.blockSignals(False)
        self.count()

    def count(self):
        self.n.setText(_("%d picked") % len(self.checked) if self.checked else "")

    def ok(self):
        sel = [it.data(Qt.UserRole) for it in self.list.selectedItems()]
        self.picked = [cid for _n, _l, cid in self.all if cid in self.checked or cid in sel]
        self.accept()


class PlayerPickDialog(Dialog):
    """the players of a NewLife club that go in its squad: the release's whole squad, the ones
    the club gets now ticked (mato 27.10.2026: pick a club's players on the NewLife page)"""

    def __init__(self, parent, rel, cid, chosen=None):
        super().__init__(parent, "Choose the players")
        self.v.insertWidget(0, QLabel(_("%s: tick the players the club gets, up to %d.")
                                      % (rel.clubs[cid]["name"], P.SQUAD)))
        self.list = QTreeWidget()
        self.list.setRootIsDecorated(False)
        self.list.setAlternatingRowColors(True)
        self.list.setHeaderLabels([_("Player"), _("Position"), _("Age"), _("Rating")])
        self.list.setColumnWidth(0, 240)
        self.v.insertWidget(1, self.list, 1)
        self.scroll.hide()
        rows = sorted(rel.squads.get(cid, []), key=lambda r: -P.overall(r))
        self.order = [str(r.get("newlife_id", "")).strip() for r in rows]
        self.best = {str(r.get("newlife_id", "")).strip() for r in rel.squad(cid)}
        mine = {str(i) for i in chosen or []} & set(self.order)
        self.ticked = mine or set(self.best)
        self.gk = {i for i, r in zip(self.order, rows) if r.get("Registered Position") == "GK"}
        for i, r in zip(self.order, rows):
            it = QTreeWidgetItem([r.get("name", ""), r.get("Registered Position", ""), str(r.get("Age", "")),
                                  str(P.overall(r))])
            it.setData(0, Qt.UserRole, i)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(0, Qt.Checked if i in self.ticked else Qt.Unchecked)
            self.list.addTopLevelItem(it)
        self.list.itemChanged.connect(self.toggled)
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        b = QPushButton(_("The best ones"))
        b.setToolTip(_("Ticks the players the club gets when nobody chooses: its best %d, three goalkeepers at most")
                     % P.SQUAD)
        b.clicked.connect(self.reset)
        h.addWidget(b)
        h.addStretch(1)
        self.v.insertWidget(2, row)
        self.n = QLabel("")
        self.n.setWordWrap(True)
        self.v.insertWidget(3, self.n)
        self.picked = None
        self.count()
        self.setMinimumSize(560, 520)

    def toggled(self, it):
        i = it.data(0, Qt.UserRole)
        if it.checkState(0) == Qt.Checked:
            self.ticked.add(i)
        else:
            self.ticked.discard(i)
        self.count()

    def reset(self):
        self.ticked = set(self.best)
        self.list.blockSignals(True)
        for n in range(self.list.topLevelItemCount()):
            it = self.list.topLevelItem(n)
            it.setCheckState(0, Qt.Checked if it.data(0, Qt.UserRole) in self.ticked else Qt.Unchecked)
        self.list.blockSignals(False)
        self.count()

    def count(self):
        n = len(self.ticked)
        lines = [_("%d of %d players ticked; a club takes up to %d.") % (n, len(self.order), P.SQUAD)]
        if n > P.SQUAD:
            lines.append(_("Untick %d: a club takes up to %d players.") % (n - P.SQUAD, P.SQUAD))
        elif n == 0:
            lines.append(_("Tick at least one player."))
        elif n < P.MIN_SQUAD:
            lines.append(_("The club gets stand-in players up to %d.") % P.MIN_SQUAD)
        if n and not self.ticked & self.gk:
            lines.append(_("No goalkeeper ticked."))
        self.n.setText("\n".join(lines))

    def ok(self):
        if not 1 <= len(self.ticked) <= P.SQUAD:
            return
        self.picked = None if self.ticked == self.best else [i for i in self.order if i in self.ticked]
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


class GameLeaguesDialog(Dialog):
    """the game's own leagues the release has, each with what bringing it to the release's season
    does: clubs that swap leagues, clubs renamed after the one that came up, squads"""
    help = ("Each ticked league of the game gets the clubs and squads it has in this NewLife season. A club "
            "that went up or down between two leagues of the game swaps places with one going the other way; "
            "a club that went down out of the game's leagues becomes the club that came up in its place (its "
            "name, short name, crest and squad; its kit and stadium stay). Clubs you changed by hand stay as "
            "they are.")

    def __init__(self, parent, rel, plan, info, done):
        super().__init__(parent, "Bring the game's leagues to this season")
        self.form.addRow(hint(_("Clubs and players come from %s. The leagues keep their number of clubs, their "
                                "format and their cups.") % rel.version))
        if done:
            self.form.addRow(hint(_("Done before with NewLife %s: doing it again replaces that.") % done))
        name = lambda t: info["clubs"].get(t, (str(t),))[0]
        self.boxes = []
        for p in plan:
            box = QCheckBox("%s  (%s)" % (p["name"], p["release"]))
            box.setChecked(True)
            lines = [_("%d clubs get their squad") % len(p["clubs"])]
            lines += [_("%s goes to %s's league") % (name(a), name(b)) for a, b in p["swaps"]]
            lines += [_("%s becomes %s") % (name(t), rel.clubs[c]["name"]) for t, c in p["replace"]]
            lines += [tr(n) for n in p["notes"]]
            for t in p.get("stay") or []:            # B137
                lines.append(_("%s stays in %s: the game's league has more places than this season's. A NewLife "
                               "league that has it too (Ligue 3 after Ligue 2) cannot take it: there, use Club "
                               "of the game and give it a new club in its place, or leave it out.")
                             % (name(t), p["name"]))
            text = QLabel("\n".join(lines))
            text.setWordWrap(True)
            w = QWidget()
            h = QVBoxLayout(w)
            h.setContentsMargins(0, 0, 0, 6)
            h.addWidget(box)
            h.addWidget(text)
            self.form.addRow(w)
            self.boxes.append((p["cid"], box))
        # Aleperfe87 22.10.: the release names some of the game's players otherwise, and Bring made
        # them twice (a new copy at the club, the game's own one a free agent)
        self.only = QCheckBox(_("Only the game's own players"))
        self.only.setToolTip(_("The clubs that keep their place get only the transfers between the game's "
                               "players and the new ratings: no new players, nobody let go. Clubs that came up "
                               "still get their whole squad."))
        self.form.addRow(self.only)
        self.form.addRow(hint(_("Tick it if Bring gives you the same player twice.")))
        self.cids, self.new_players = [], True

    def ok(self):
        self.cids = [c for c, box in self.boxes if box.isChecked()]
        self.new_players = not self.only.isChecked()
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
        self.picks = {}           # club id -> [newlife_id]: the players chosen for a club not in the world yet
        self.action("Open NewLife Database...", self.open_dir)
        self.b_add = self.action("Add to your world", self.add, "primary",
                                 tip="Each selected league becomes a new league with its clubs and players")
        # 0.2.4: two buttons in sight (the long ones did not fit and were cut), the rest in More
        more = self.more([("Update my leagues to this version", self.update,
                           "Leagues you added from another NewLife version get this version's clubs "
                           "and players; their division, format, European places and cups stay"),
                          ("Bring the game's leagues to this season...", self.game_leagues,
                           "The game's own leagues get the clubs that went up and down and the squads "
                           "they have in this NewLife season"),
                          ("Undo the game's leagues", self.undo_game,
                           "Takes back what Bring the game's leagues to this season did")])
        self.b_update, self.b_game, self.b_undo = more.acts
        for a in more.acts:
            a.setEnabled(False)
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
        # click a column to sort by it, again to turn it round (jibibi, 2026-10-06); the list
        # opens as the file has it, by country
        self.tree.setSortingEnabled(True)
        self.tree.sortByColumn(1, Qt.AscendingOrder)
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
        self.b_players = QPushButton(_("Choose the players..."))
        self.b_players.setToolTip(_("The players of the selected club that go in its squad; without a choice it gets "
                                    "its best ones"))
        self.b_players.clicked.connect(self.choose_players)
        self.b_players.setEnabled(False)
        self.clubs.currentItemChanged.connect(lambda *a: self.club_selected())
        self.clubs.itemDoubleClicked.connect(lambda *a: self.choose_players())
        rv.addWidget(self.b_players)
        split.addWidget(right)
        split.setSizes([820, 340])
        self.outer.addWidget(split, 1)
        self.foot = hint("")
        self.outer.addWidget(self.foot)
        self.project.changed.connect(self.count)

    def shown(self):
        if self.need_tables(True):
            return
        if self.room is None:
            self.room = B.clubs_room(self.project.base)
        folder = self.app.settings.get("newlife")
        if self.rel is None and folder and os.path.isdir(folder):
            self.load(folder)
        elif self.rel is not None and (self.rel.tables != (self.info() or {}).get("base", self.rel.tables)
                                       or self.rel.use_recipe(self.project.recipe)):
            # other tables since (Settings): which clubs the game has; or another world, or one
            # that took a NewLife club the game has (B56) in or out of a league of its own
            self.read_rows()
            self.fill()
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
            self.read_rows()
            self.custom = {}
            self.picks = {}
            self.fill()

        def failed(tb):
            self.app.busy(False)
            self.where.setText(_("No NewLife Database opened."))
            error(self, "NewLife Database", tb.strip().splitlines()[-1])

        run_job(lambda progress: N.Release(folder), done, failed)

    def read_rows(self):
        """the release's leagues, their clubs "in game" by the tables in use (a database mod's
        own, from Settings: Yanis 14.10., UML 2026 v3), not by the plain game"""
        names = dict((i, n) for n, i in B.country_ids(self.project.base)) if self.project.base else {}
        self.rel.use_recipe(self.project.recipe)     # B56: a twin the world has as a new club stays one
        self.rows = self.rel.leagues(lambda c: names.get(int(c), "").split(" (")[0], self.info())

    def fill(self):
        q = self.search.text().strip().lower()
        info = self.info()
        self.gamekeys = self.game_keys(info)
        self.tree.setSortingEnabled(False)
        self.tree.clear()
        for i, L in enumerate(self.rows):
            if q and q not in L["name"].lower() and q not in L["country"].lower():
                continue
            E = self.effective(L)
            game = tuple(L["key"]) in self.gamekeys
            ok = N.fits(E, info) and not game
            it = QTreeWidgetItem([L["name"] + ("  *" if key(L) in self.custom else ""), L["country"],
                                  str(len(E["clubs"])), str(len(E["in_game"]) or ""),
                                  str(L["players"]), str(L["strength"]),
                                  _("the game's own league: Bring the game's leagues to this season") if game
                                  else "" if ok else _("a league takes %d to %d clubs") % (B.CLUBS_MIN, B.CLUBS_MAX)])
            it.setData(0, Qt.UserRole, i)
            for c, v in ((2, len(E["clubs"])), (4, L["players"]), (5, L["strength"])):
                it.setData(c, Qt.DisplayRole, int(v or 0))     # numbers sort as numbers
            it.setToolTip(3, _("Clubs of this league the game already has: they join the new league with "
                               "their own names, crests, kits and players"))
            if not ok:
                for c in range(7):
                    it.setForeground(c, Qt.gray)
            self.tree.addTopLevelItem(it)
        self.tree.setSortingEnabled(True)
        self.count()

    def picked(self):
        return [self.rows[it.data(0, Qt.UserRole)] for it in self.tree.selectedItems()]

    def game_keys(self, info):
        """the release's leagues that are leagues of the game (Premier League, Championship ...).
        Added as new leagues they stood beside the game's own, two Championships (Discord,
        capital030); Bring the game's leagues to this season is their way in"""
        if not self.rel or info is None:
            return set()
        tag = (id(self.rel), info.get("base"))
        if getattr(self, "_gk", (None,))[0] != tag:
            try:
                match, _t = N._game_targets(self.rel, info)
                self._gk = (tag, {tuple(L["key"]) for L in match.values()})
            except Exception:
                self._gk = (tag, set())
        return self._gk[1]

    def addable(self, info):
        return [E for E in map(self.effective, self.picked())
                if N.fits(E, info) and tuple(E["key"]) not in getattr(self, "gamekeys", set())]

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
            chosen = self.chosen(cid) if club.get("in_game") != "1" else None
            if chosen:
                note = _("%d of %d chosen") % (len(chosen), len(self.rel.squads.get(cid, [])))
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
        self.club_selected()
        self.count()

    def chosen(self, cid):
        """the players chosen for club cid (newlife_ids): in the league of the world that has it,
        else on this page for a league still to add; None: its best ones"""
        x, _k = N.placed(self.project.recipe, self.rel, cid)
        return N.picks_of(x, cid) if x is not None else self.picks.get(cid)

    def club_selected(self):
        it = self.clubs.currentItem()
        cid = it.data(0, Qt.UserRole)[0] if it else None
        self.b_players.setEnabled(bool(self.rel and cid in self.rel.clubs
                                       and self.rel.clubs[cid].get("in_game") != "1"
                                       and self.rel.squads.get(cid)))

    def choose_players(self):
        it = self.clubs.currentItem()
        if not it or not self.rel or not self.b_players.isEnabled():
            return
        cid = it.data(0, Qt.UserRole)[0]
        d = PlayerPickDialog(self, self.rel, cid, self.chosen(cid))
        if not d.finish():
            return
        self.use_players(cid, d.picked)

    def use_players(self, cid, picked):
        """picked (newlife_ids, None: the best ones) for club cid: for its league in the world now,
        else when its league is added"""
        name = self.rel.clubs[cid]["name"]
        n = len(picked or self.rel.squad(cid))
        x, k = N.placed(self.project.recipe, self.rel, cid)
        if x is None:
            if picked:
                self.picks[cid] = picked
            else:
                self.picks.pop(cid, None)
            self.say(_("%s: %d players chosen; they go in when you add the league.") % (name, n), "ok")
        else:
            try:
                st, el = N.repick(self.project.recipe, self.rel, x, k, picked, info=self.info())
            except N.Error as e:
                error(self, "NewLife Database", tr(str(e)))
                return
            self.project.touch()
            text = _("%s (%s): %d players chosen. Build again.") % (x["club_names"][k], x["name"], n)
            if st:
                text += "\n" + _("%d players stay at their game club (their club would have too few players).") % st
            if el:
                text += "\n" + _("%d players are not added: another league already has them.") % el
            self.say(text, "ok")
        cur = self.clubs.currentItem()
        sel = cur.data(0, Qt.UserRole) if cur else None
        self.show_league()
        for i in range(self.clubs.topLevelItemCount()):
            if self.clubs.topLevelItem(i).data(0, Qt.UserRole) == sel:
                self.clubs.setCurrentItem(self.clubs.topLevelItem(i))
                break

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
        # later, not inside this signal: refresh_row rebuilds the club list, and deleting the item
        # Qt is still emitting itemChanged for crashed Mod Studio in Qt6Widgets (GitHub #120)
        QTimer.singleShot(0, lambda: self.refresh_row(L))

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
        sel = sum(len(E["clubs"]) for E in self.addable(info)) if self.rows else 0
        room = self.room if self.room is not None else 0
        text = _("New clubs in your world: %d of the %d the game takes.") % (used, room)
        if sel:
            text += "  " + _("Selected: %d more.") % sel
        old = N.outdated(self.project.recipe, self.rel) if self.rel else []
        if old:
            text += "\n" + _("%d of your leagues are from another NewLife version (%s): Update my leagues to this "
                             "version brings them to %s.") % (len(old), ", ".join(x["name"] for x in old),
                                                               self.rel.version)
        size = N.resized(self.project.recipe, self.rel) if self.rel else []
        if size:
            text += "\n" + _("%d of your leagues have squads of another size than Players per new club (%d): "
                             "Update my leagues takes their players again (%s).") % (
                len(size), P.SQUAD, ", ".join(x["name"] for x in size))
        self.foot.setText(text)
        busy = getattr(self, "bringing", False)  # B260: not while Bring the game's leagues works on a copy
        self.b_add.setEnabled(bool(sel) and used + sel <= room and not busy)
        self.b_update.setEnabled(bool(old or size) and not busy)
        self.b_game.setEnabled(bool(self.rel) and info is not None and not busy)
        self.b_undo.setEnabled(bool(self.project.recipe.get("newlife_game")) and not busy)

    def update(self):
        old = N.to_update(self.project.recipe, self.rel) if self.rel else []
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
        sel = self.addable(info)
        if not sel or not self.rel:
            return
        # B62: say where in the world the club is, under the name it has there (a renamed club keeps its
        # NewLife link, so "your world" alone sent people looking for a club they could not find)
        used = {}
        for x in self.project.recipe["leagues"]:
            names = list(x.get("club_names") or [])
            for k, i in enumerate((x.get("newlife") or {}).get("clubs") or []):
                if i:
                    n = names[k] if k < len(names) and names[k] else ""
                    used[str(i)] = "%s, %s" % (_("your world"), x.get("name", "")) + (": %s" % n if n else "")
        seen = {}
        for E in sel:
            for i in E["clubs"]:
                where = used.get(i) or seen.get(i)
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
            name, st, el = N.add_league(self.project.recipe, self.rel, L, info=info, custom=key(L) in self.custom,
                                        picks={i: self.picks[i] for i in L["clubs"] if i in self.picks})
            names.append(name)
            stayed += st
            elsewhere += el
            if info:
                swap += [info["clubs"][e["id"]][0] for e in self.project.recipe["leagues"][-1].get("game_clubs") or []
                         if B.game_club_where(info, e["id"])]
        if names:
            self.project.touch()
            text = _("Added: %s. Change them on Leagues, Clubs and Players, then Build.") % ", ".join(names)
            if swap:
                text += "\n" + _("%s also play in a competition of the game: on Clubs pick each one and use "
                                 "Club of the game to choose the club that takes its place there.") % ", ".join(swap)
            if stayed:
                text += "\n" + _("%d players stay at their game club (their club would have too few players).") % stayed
            if elsewhere:
                text += "\n" + _("%d players are not added: another league already has them.") % elsewhere
            self.say(text, "ok")

    def game_leagues(self):
        info = self.info()
        if not self.rel or info is None:
            return
        rel, recipe = self.rel, self.project.recipe
        plan = N.game_league_plan(recipe, rel, info)
        if not plan:
            self.say(_("%s has none of the game's leagues.") % rel.version)
            return
        d = GameLeaguesDialog(self, rel, plan, info, (recipe.get("newlife_game") or {}).get("version"))
        if not d.finish() or not d.cids:
            return
        work = {k: copy.deepcopy(recipe[k]) for k in ("leagues", "edits", "players", "newlife_game") if k in recipe}
        start = N.bring_start(recipe)
        self.app.busy(True)
        self.bringing = True                     # B260: this page's buttons wait for it
        self.count()

        def done(n):
            self.app.busy(False)
            self.bringing = False
            N.take_bring(recipe, work, start)    # B260: what was added meanwhile stays
            self.project.touch()
            self.say(_("The game's leagues now have the %s season: %d clubs swap leagues, %d take the name of the "
                       "club that came up, %d squads (%d players join from other clubs, %d new, %d leave). Build "
                       "again and start a new career.") % (rel.version, 2 * n["swaps"], n["replaced"], n["clubs"],
                                                          n["join"], n["add"], n["remove"])
                     + ("\n" + _("%d players of this season the game does not have were left out.") % n["skipped"]
                        if n.get("skipped") else ""), "ok")
            self.read_rows()                     # B79: a club whose place went is a new club now
            self.fill()
            self.count()

        def failed(tb):
            self.app.busy(False)
            self.bringing = False
            self.count()
            error(self, "NewLife Database", tb.strip().splitlines()[-1])

        run_job(lambda progress: N.refresh_game_leagues(work, rel, info, d.cids, d.new_players), done, failed)

    def undo_game(self):
        if N.undo_game_leagues(self.project.recipe):
            self.project.touch()
            self.say(_("The game's leagues are back as the game has them."), "ok")
            if self.rel:                         # B79: its clubs are the game's again
                self.read_rows()
                self.fill()
        self.count()
