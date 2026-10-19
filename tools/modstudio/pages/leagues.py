"""Leagues: every league in one list -- the game's and the ones the recipe adds -- by continent,
in the order they are dragged into.  The one picked is edited on the right: a league of the game
in the game's leagues panel, a league of ours with the league window."""
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QHBoxLayout, QLabel, QLineEdit, QMenu,
                               QPushButton, QSplitter, QStackedWidget, QToolButton, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget, QFormLayout, QGridLayout, QScrollArea,
                               QTableWidget, QTableWidgetItem)
import fl26world

from ..i18n import _
from ..ui import hint, row
from .. import theme
from .builder import (BuilderPage, GameLeagues, fmt_text, europe_text, tier_of, pixmap, others_labels,
                      built_plan, built_league, select_team_text)

CONTINENTS = ((2, "Europe"), (3, "Asia"), (4, "South America"), (5, "Africa"),
              (6, "North and Central America"), (7, "Oceania"), (0, "Other"))
ROLE = Qt.UserRole


def keep_continent_places(leagues, keys, confeds):
    """the recipe's leagues reordered by the list on screen, each continent only among the places
    its leagues already hold: the list groups by continent, the recipe's order is the Build's
    (who gets a Select Team place), so a drag inside Oceania must not move Oceania behind Europe"""
    pos = {k: n for n, k in enumerate(keys)}
    cont = [confeds.get(L.get("country", ""), 0) for L in leagues]
    out = list(leagues)
    for c in set(cont):
        at = [i for i, x in enumerate(cont) if x == c]
        mine = sorted((leagues[i] for i in at), key=lambda L: pos.get("o" + L["name"], len(pos)))
        for i, L in zip(at, mine):
            out[i] = L
    return out


def updown_text(r, L):
    """how many clubs go up and down: with the league above, and with the league below"""
    out = []
    if L.get("above") not in (None, ""):
        out.append(_("%d with %s above") % (int(L.get("exchange", 3)), L["above"]))
    for M in r["leagues"]:
        if M.get("above") == L["name"]:
            out.append(_("%d with %s below") % (int(M.get("exchange", 3)), M["name"]))
    return ", ".join(out) or "—"


class LeagueTree(QTreeWidget):
    """the list: a league can be dragged up or down among the leagues of its continent, never
    into another continent or onto a league"""
    moved = Signal()

    def __init__(self):
        super().__init__()
        self.setHeaderHidden(True)
        self.setColumnCount(2)
        self.setRootIsDecorated(False)
        self.setIndentation(0)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setDropIndicatorShown(True)

    def _ok(self, event):
        src = self.currentItem()
        dst = self.itemAt(event.position().toPoint())
        if not src or not src.parent() or not dst:
            return False
        if dst.parent() is None:             # a continent's own row: only the first place under it
            return dst is src.parent() and self.dropIndicatorPosition() == QAbstractItemView.BelowItem
        return dst.parent() is src.parent() and self.dropIndicatorPosition() != QAbstractItemView.OnItem

    def dragMoveEvent(self, event):
        super().dragMoveEvent(event)
        if not self._ok(event):
            event.ignore()

    def dropEvent(self, event):
        if not self._ok(event):
            event.ignore()
            return
        src = self.currentItem()
        dst = self.itemAt(event.position().toPoint())
        parent = src.parent()
        parent.removeChild(src)
        if dst is parent:
            at = 0
        else:
            at = parent.indexOfChild(dst) + (1 if self.dropIndicatorPosition() == QAbstractItemView.BelowItem else 0)
        parent.insertChild(at, src)
        self.setCurrentItem(src)
        # the move is done here; a MoveAction handed back would have the drag remove the source
        # row once more, and the league vanished from the list until it was filled again
        # (Discord, capital030: it showed after Ours and back to All)
        event.setDropAction(Qt.CopyAction)
        event.accept()
        self.moved.emit()


class Leagues(BuilderPage):
    title = "Leagues"
    hint = ("Every league: the game's own and the ones you add. Drag a league to put it in order; pick one "
            "to change it on the right.")
    help = ("The list on the left has all the leagues by continent.\n"
            "- game: a league the game has; you can rename it, give it a logo and change its clubs.\n"
            "- ours: a league your world adds; Edit league changes its clubs, format and division.\n"
            "- changed: a league of the game you changed.\n\n"
            "Drag a league up or down to put the leagues of a continent in order.\n"
            "The More menu has the cups, European places, UEFA ranking and competition names.\n"
            "Nothing reaches the game until Build and install.")

    def __init__(self, app):
        super().__init__(app)
        self.action("Add league", self.add, "primary")
        more = QToolButton()
        more.setText(_("More") + "  ▾")
        more.setPopupMode(QToolButton.InstantPopup)
        m = QMenu(more)
        for label, name in (("Pre-season cups", "preseason"), ("Cups of our countries", "our_cups"), ("Cups of the game's countries", "game_cups"),
                            ("European places of the game's leagues", "game_europe"),
                            ("First-season European clubs", "europe_first"),
                            ("UEFA ranking", "uefa_rank"), ("South American places", "samerica"),
                            ("Competition names", "competition_names"), ("Competition IDs", "competition_ids"),
                            # the order of the countries in Select Team; the 0.1.8 look left it and the
                            # two below out of this menu (Discord, laracroft7826 15.10.: "it was in the old one")
                            ("League order", "league_order"),
                            ("Seasons of the game's leagues", "game_seasons")):
            m.addAction(_(label)).triggered.connect(lambda _c=False, n=name: getattr(self.nl(), n)())
        m.addSeparator()
        m.addAction(_("World name and file...")).triggered.connect(lambda: self.app.open_page("NewLeagues"))
        more.setMenu(m)
        self.actions.addWidget(more)

        split = QSplitter(Qt.Horizontal)
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 10, 0)
        lv.setSpacing(8)
        self.search = QLineEdit()
        self.search.setPlaceholderText(_("Find a league..."))
        self.search.textChanged.connect(self.fill)
        lv.addWidget(self.search)
        chips = QHBoxLayout()
        chips.setSpacing(6)
        self.filter = QButtonGroup(self)
        self.chips = []
        for i, text in enumerate(("All", "Ours", "Changed")):
            b = QPushButton(_(text))
            self.chips.append((b, _(text)))
            b.setObjectName("tab")
            b.setCheckable(True)
            b.setChecked(i == 0)
            self.filter.addButton(b, i)
            chips.addWidget(b)
        chips.addStretch(1)
        self.filter.idClicked.connect(lambda *_a: self.fill())
        lv.addLayout(chips)
        self.tree = LeagueTree()
        self.tree.currentItemChanged.connect(lambda *_a: self.show_current())
        self.tree.moved.connect(self.save_order)
        # save_order sorts the recipe's leagues, so the rows' indexes into it are refilled after
        self.tree.moved.connect(lambda: QTimer.singleShot(0, self.fill))
        lv.addWidget(self.tree, 1)
        self.count = hint("")
        # B93 (vmican, 16.10.): the 0.2.3 table of places is back -- the order and where the last
        # Build put each league in Select Team -- behind a button next to the counter
        self.b_places = QPushButton(_("Places in Select Team"))
        self.b_places.setCheckable(True)
        self.b_places.setToolTip(_("The order of your leagues and where the last Build put each one in "
                                   "Select Team. * = the order changed since: Build again to see where it goes."))
        self.b_places.toggled.connect(lambda *_a: self.show_current())
        lv.addWidget(row(self.count, "stretch", self.b_places))
        split.addWidget(left)

        self.right = QStackedWidget()
        # a league of ours
        ours = QWidget()
        ov = QVBoxLayout(ours)
        ov.setContentsMargins(10, 0, 0, 0)
        ov.setSpacing(10)
        self.o_tag = QLabel(_("OURS"))
        self.o_tag.setObjectName("eyebrow")
        ov.addWidget(self.o_tag)
        self.o_name = QLabel("")
        self.o_name.setObjectName("bigtitle")
        self.o_logo = QLabel()
        self.o_logo.setFixedSize(64, 64)
        self.o_logo.setAlignment(Qt.AlignCenter)
        ov.addWidget(row(self.o_logo, self.o_name, "stretch"))
        f = QFormLayout()
        f.setHorizontalSpacing(18)
        f.setVerticalSpacing(8)
        self.o_form = f
        self.o_rows = {}
        for key in ("Country", "Clubs", "Format", "Division", "Up / down", "Europe", "League ID"):
            lab = QLabel("")
            lab.setWordWrap(True)
            self.o_rows[key] = lab
            f.addRow(_(key), lab)
        ov.addLayout(f)
        self.o_crests = QGridLayout()
        self.o_crests.setSpacing(10)
        self.o_crests.setColumnStretch(5, 1)
        ov.addLayout(self.o_crests)
        b_edit = QPushButton(_("Edit league..."))
        b_edit.setObjectName("primary")
        b_edit.clicked.connect(lambda: self.on_ours("edit"))
        b_low = QPushButton(_("Add lower tier"))
        self.o_low = b_low
        b_low.clicked.connect(lambda: self.on_ours("add_lower"))
        b_clubs = QPushButton(_("Clubs and names"))
        b_clubs.clicked.connect(lambda: self.app.open_page("NewClubs"))
        b_pl = QPushButton(_("Players"))
        b_pl.clicked.connect(lambda: self.app.open_page("Players"))
        b_rm = QPushButton(_("Remove"))
        b_rm.setObjectName("danger")
        b_rm.clicked.connect(lambda: self.on_ours("remove"))
        ov.addWidget(row(b_edit, b_low, b_clubs, b_pl, "stretch", b_rm))
        ov.addStretch(1)
        # 0.2.4: in a scroll area of its own: at 1280x720 the rows (wrapped labels) were squeezed
        # into each other; now they keep their height and the panel scrolls
        o_sa = QScrollArea()
        o_sa.setWidgetResizable(True)
        o_sa.setFrameShape(QScrollArea.NoFrame)
        o_sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        o_sa.setStyleSheet("QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; }")
        o_sa.setWidget(ours)
        self.right.addWidget(o_sa)
        # a league of the game: the game's leagues panel, without its own list
        self.game = GameLeagues(app)
        self.game.list.parentWidget().hide()
        self.game.outer.setContentsMargins(10, 0, 0, 0)
        for i in range(self.game.actions.count()):
            w = self.game.actions.itemAt(i).widget()
            if w:
                w.hide()
        for lab in self.game.findChildren(QLabel, "hint"):
            if lab.parentWidget() is self.game and lab is not self.game.banner:
                lab.hide()
                break
        self.right.addWidget(self.game)
        self.empty = hint(_("Pick a league on the left."))
        self.empty.setAlignment(Qt.AlignCenter)
        self.right.addWidget(self.empty)
        # the places table (B93)
        self.places = QTableWidget(0, 6)
        self.places.setHorizontalHeaderLabels(["#", _("League"), _("Country"), _("Division"), _("Select Team"),
                                               _("League ID")])
        self.places.horizontalHeaderItem(0).setToolTip(_("The league's place in the order: the first ones get a "
                                                         "place in Select Team"))
        self.places.horizontalHeaderItem(4).setToolTip(_("Where the last Build put the league in Select Team"))
        self.places.verticalHeader().hide()
        self.places.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.places.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.places.setAlternatingRowColors(True)
        self.places.horizontalHeader().setStretchLastSection(True)
        self.right.addWidget(self.places)
        split.addWidget(self.right)
        split.setSizes([340, 900])
        split.setStretchFactor(1, 1)
        self.outer.addWidget(split, 1)
        self.project.changed.connect(self.fill)
        self._countries = (None, {})        # (tables, {game league's regulation id: country}) for natural

    def nl(self):
        """the New leagues page, whose tools the More menu and the buttons use"""
        return self.app.page("NewLeagues")

    def shown(self):
        self.need_tables()
        self.game.need_tables() or self.game.fill()
        self.fill()

    def refresh(self):
        self.fill()

    # ---- the list ----
    def entries(self):
        """[(key, continent, name, kind, payload)] in the order to show: kind "game" / "ours";
        key "g<competition id>" / "o<name>"; payload the game's row or the recipe's index"""
        P = self.project
        changed = P.edits("leagues")
        out = []
        import leaguebuilder as B
        friendly = B.game_info(P.base).get("friendly_cids", set()) if P.base else set()
        for rid, cid, name, teams in sorted(P.game_lgs, key=lambda x: x[0]):
            if cid in friendly:              # the pre-season tournaments: cups, not leagues
                continue
            e = changed.get(str(rid), {})
            out.append(("g%d" % cid, P.game_confeds.get(cid, 0), e.get("name", name),
                        "changed" if e else "game", (rid, cid, name, teams)))
        for i, L in enumerate(P.recipe["leagues"]):
            out.append(("o" + L["name"], P.confeds.get(L.get("country", ""), 0), L["name"], "ours", i))
        order = {k: n for n, k in enumerate(P.recipe.get("league_order") or [])}
        if not order:
            # 0.2.4: nothing dragged yet -- by country, each country's divisions from the top down,
            # the game's and yours together (exe test 14.10.: the Modpack listed the game's leagues
            # first and its own in the order they were added, the Bundesliga far from the 2.
            # Bundesliga and the 3. Liga)
            return sorted(out, key=self.natural)
        late = len(order)
        return sorted(out, key=lambda x: order.get(x[0], late))     # stable: unknown keep theirs

    def natural(self, e):
        """(country, division, name) of an entry: the list's order before any drag"""
        import unicodedata
        P = self.project
        if self._countries[0] is not P.base:
            import leaguebuilder as B
            try:
                self._countries = (P.base, B.game_league_countries(P.base, P.game_lgs) if P.base else {})
            except Exception:           # tables that do not read: the game's leagues by name only
                self._countries = (P.base, {})
        _k, _c, name, kind, payload = e
        if kind == "ours":
            L = P.recipe["leagues"][payload]
            country, tier = L.get("country", ""), tier_of(P, L.get("above"))
        else:
            country, tier = self._countries[1].get(payload[0], ""), P.parent_tiers.get(payload[0])
        fold = lambda t: unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().casefold()
        return (fold(country) or "~", tier or 99, fold(name))

    def fill(self):
        q = self.search.text().strip().lower()
        want = self.filter.checkedId()
        cur = self.tree.currentItem()
        key = cur.data(0, ROLE)[0] if cur and cur.data(0, ROLE) else None
        self.tree.blockSignals(True)
        self.tree.clear()
        heads = {}
        for code, cname in CONTINENTS:
            h = QTreeWidgetItem([_(cname).upper(), ""])
            h.setFlags(Qt.ItemIsEnabled | Qt.ItemIsDropEnabled)
            h.setForeground(0, QBrush(QColor(theme.SUBTLE)))
            fnt = h.font(0)
            fnt.setBold(True)
            fnt.setPointSizeF(fnt.pointSizeF() * 0.85)
            h.setFont(0, fnt)
            heads[code] = h
        tags = {"game": (_("game"), theme.SUBTLE), "ours": (_("ours"), theme.ACCENT),
                "changed": (_("changed"), theme.WARN)}
        pick, shown, total = None, 0, 0
        kinds = {}
        for e in self.entries():
            k, conf, name, kind, payload = e
            total += 1
            kinds[kind] = kinds.get(kind, 0) + 1
            if q and q not in name.lower():
                continue
            if want == 1 and kind != "ours" or want == 2 and kind != "changed":
                continue
            it = QTreeWidgetItem(["⠿  " + name, tags[kind][0]])
            it.setForeground(1, QBrush(QColor(tags[kind][1])))
            it.setTextAlignment(1, Qt.AlignRight | Qt.AlignVCenter)
            it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)
            it.setData(0, ROLE, e)
            if kind == "ours":
                pm = pixmap(self.project.recipe["leagues"][payload].get("logo"), 20)
                if pm:
                    it.setIcon(0, pm)
            heads.get(conf, heads[0]).addChild(it)
            shown += 1
            if k == key:
                pick = it
        for code, _n in CONTINENTS:
            h = heads[code]
            if h.childCount():
                self.tree.addTopLevelItem(h)
                h.setExpanded(True)
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, self.tree.header().ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(1, self.tree.header().ResizeMode.ResizeToContents)
        if pick is None and self.tree.topLevelItemCount():
            pick = self.tree.topLevelItem(0).child(0)
        self.tree.blockSignals(False)
        if pick:
            self.tree.setCurrentItem(pick)
        self.show_current()
        # B93 (vmican, 16.10.): a group of clubs in no league ("Other Europe") is not a league --
        # it is counted apart, and the leagues with a place in Select Team are counted too
        r = self.project.recipe
        groups = sum(1 for L in r["leagues"] if L.get("others"))
        ours = len(r["leagues"]) - groups
        total -= groups
        for (b, text), n in zip(self.chips, (total, ours, kinds.get("changed", 0))):
            b.setText("%s  %d" % (text, n))
        text = (_("%d leagues: %d of the game, %d of yours.") % (total, total - ours, ours)
                if shown == total + groups else _("%d of %d leagues shown.") % (shown, total + groups))
        if groups:
            text += "  " + (_("%d group of clubs in no league.") if groups == 1 else
                            _("%d groups of clubs in no league.")) % groups
        plan = built_plan(self.app.game, r.get("world"))
        if plan:
            placed = sum(1 for p in plan.get("leagues") or [] if not p.get("others")
                         and p.get("slot") not in (None, fl26world.NO_SLOT))
            text += "  " + _("%d of yours with a place in Select Team.") % placed
        self.count.setText(text)
        self.fill_places(plan)

    def fill_places(self, plan):
        """the places table: the order and where the last Build put each league in Select Team
        (the 0.2.3 New leagues columns # and Select Team, asked back by vmican, B93)"""
        r = self.project.recipe
        names = dict(self.project.parents)
        order = [L["name"] for L in r["leagues"] if not L.get("others")]
        was = [p.get("name") for p in (plan or {}).get("leagues") or []]
        rows = sorted(r["leagues"], key=lambda L: (bool(L.get("others")), order.index(L["name"]) if L["name"] in order else 0))
        self.places.setRowCount(len(rows))
        for n, L in enumerate(rows):
            up = L.get("above")
            div = _("top") if up in (None, "") else _("below %s") % (names.get(up, up) if isinstance(up, int) else up)
            t = tier_of(self.project, up)
            if t:
                div = "%d  (%s)" % (t, div)
            b = built_league(self.app.game, r.get("world"), L, plan or {})
            cid = str(b["cid"]) if b.get("cid") is not None else (_("not built yet") if plan else "")
            if L.get("others"):
                num, seen, div, cid = "", _("no league (%s)") % others_labels().get(L["others"], L["others"]), "", ""
            else:
                num, seen = str(order.index(L["name"]) + 1), select_team_text(L, b, plan)
                if seen and b and L["name"] in was and was.index(L["name"]) != order.index(L["name"]):
                    seen += "  *"
            for c, v in enumerate((num, L["name"], L.get("country", ""), div, seen, cid)):
                it = QTableWidgetItem(v)
                if c == 0:
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.places.setItem(n, c, it)
            pm = pixmap(L.get("logo"), 20)
            if pm:
                self.places.item(n, 1).setIcon(pm)
        self.places.resizeColumnsToContents()

    def save_order(self):
        """the order on screen into the recipe: league_order for the list, and the recipe's
        leagues in the same order (the order New leagues and Build use)"""
        keys = []
        for i in range(self.tree.topLevelItemCount()):
            h = self.tree.topLevelItem(i)
            keys += [h.child(j).data(0, ROLE)[0] for j in range(h.childCount())]
        if self.search.text().strip() or self.filter.checkedId():
            # some leagues are hidden: keep them where they were, between the ones moved
            full = [e[0] for e in self.entries()]
            shown = set(keys)
            it = iter(keys)
            keys = [next(it) if k in shown else k for k in full]
        r = self.project.recipe
        r["league_order"] = keys
        r["leagues"] = keep_continent_places(r["leagues"], keys, self.project.confeds)
        self.project.touch()

    # ---- the right side ----
    def current(self):
        it = self.tree.currentItem()
        return it.data(0, ROLE) if it else None

    def show_current(self):
        if self.b_places.isChecked():
            self.right.setCurrentWidget(self.places)
            return
        e = self.current()
        if not e:
            self.right.setCurrentWidget(self.empty)
            return
        k, conf, name, kind, payload = e
        if kind == "ours":
            self.show_ours(payload)
            self.right.setCurrentWidget(self.right.widget(0))
        else:
            g = self.game
            if g.search.text():
                g.search.setText("")
            for n, rowx in enumerate(g.shown_rows):
                if rowx[0] == payload[0]:
                    g.list.setCurrentRow(n)
                    break
            self.right.setCurrentWidget(g)

    def show_ours(self, i):
        from .builder import built_plan, built_league, world_dir, world_crest, world_logo
        P = self.project
        r = P.recipe
        L = r["leagues"][i]
        names = dict(P.parents)
        up = L.get("above")
        div = _("top") if up in (None, "") else _("below %s") % (names.get(up, up) if isinstance(up, int) else up)
        t = tier_of(P, up)
        plan = built_plan(self.app.game, r.get("world"))
        b = built_league(self.app.game, r.get("world"), L, plan or {})
        self.o_name.setText(L["name"])
        vals = {"Country": L.get("country", ""), "Clubs": str(L.get("clubs", "")), "Format": fmt_text(L),
                "Division": ("%d  (%s)" % (t, div)) if t else div,
                "Up / down": updown_text(r, L),
                "Europe": europe_text(L) or "—",
                "League ID": str(b["cid"]) if b.get("cid") is not None else
                (_("not built yet") if plan else "—")}
        # B54: a group of clubs in no league (plan["others"], e.g. Other Africa teams) never gets a
        # competition, so no league id, format or division: say what it is instead of "not built yet"
        others = L.get("others")
        if others:
            vals["League ID"] = _("no league (%s)") % others_labels().get(others, others)
        for k, v in vals.items():
            self.o_rows[k].setText(v)
        for k in ("Format", "Division", "Up / down", "Europe"):
            self.o_form.setRowVisible(self.o_rows[k], not others)
        self.o_low.setEnabled(not others)
        # B89: a world installed from a zip carries no source pictures (the recipe's paths are the
        # author's); the built world folder has every crest and logo, so fall back to those
        wdir = world_dir(self.app.game, r.get("world"))
        pm = pixmap(L.get("logo"), 60) or pixmap(world_logo(wdir, b.get("cid")), 60)
        self.o_logo.setPixmap(pm if pm else QPixmap())
        self.o_logo.setVisible(bool(pm))
        self.show_crests(L, b, wdir)

    def show_crests(self, L, b=None, wdir=""):
        """the league's clubs, crest over short name, five to a row; `b` the built league (its team
        ids) and `wdir` the world folder, for the crests the build wrote (B89: zip worlds)"""
        from .builder import world_crest      # B103: was imported in show_ours only -> NameError here
        teams = list((b or {}).get("teams") or [])
        while self.o_crests.count():
            w = self.o_crests.takeAt(0).widget()
            if w:
                w.deleteLater()
        P = self.project
        crests = list(L.get("club_crests") or [])
        abbrs = list(L.get("club_abbrs") or [])
        names = list(L.get("club_names") or [])
        kits = L.get("club_kits") or []
        game = {int(e.get("at", -1)): e for e in L.get("game_clubs") or []}
        for k in range(int(L.get("clubs") or 0)):
            path, kit = (crests[k] if k < len(crests) else None), (kits[k] if k < len(kits) else None)
            name = names[k] if k < len(names) and names[k] else ""
            abbr = abbrs[k] if k < len(abbrs) and abbrs[k] else ""
            if k in game:
                tid = int(game[k]["id"])
                ed = P.edits("clubs").get(str(tid), {})
                gname, gshort = P.game_cl.get(tid, (str(tid), ""))
                path, kit = ed.get("crest"), ed.get("kit") or None
                name, abbr = ed.get("name") or gname, ed.get("abbr") or gshort
            cell = QLabel()
            cell.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
            cell.setFixedWidth(64)
            pm = pixmap(path, 44, kit)
            if not pm:
                tid = int(game[k]["id"]) if k in game else (teams[k] if k < len(teams) else None)
                pm = pixmap(world_crest(wdir, tid), 44)
            if pm:
                cell.setPixmap(pm)
            else:
                cell.setText("—")
                cell.setFixedHeight(44)
            cap = QLabel(abbr or name[:3])
            cap.setObjectName("subtle")
            cap.setAlignment(Qt.AlignHCenter)
            box = QWidget()
            bv = QVBoxLayout(box)
            bv.setContentsMargins(0, 0, 0, 0)
            bv.setSpacing(2)
            bv.addWidget(cell, 0, Qt.AlignHCenter)
            bv.addWidget(cap)
            box.setToolTip(name)
            self.o_crests.addWidget(box, k // 5, k % 5)

    def on_ours(self, what):
        """run a New leagues button on the league picked here"""
        e = self.current()
        if not e or e[3] != "ours":
            return
        nl = self.nl()
        nl.refresh()
        nl.tree.setCurrentItem(nl.tree.topLevelItem(e[4]))
        getattr(nl, what)()

    def add(self):
        self.nl().add()
