"""Leagues: every league in one list -- the game's and the ones the recipe adds -- by continent,
in the order they are dragged into.  The one picked is edited on the right: a league of the game
in the game's leagues panel, a league of ours with the league window."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QHBoxLayout, QLabel, QLineEdit, QMenu,
                               QPushButton, QSplitter, QStackedWidget, QToolButton, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget, QFormLayout)

from ..i18n import _
from ..ui import hint, row
from .. import theme
from .builder import BuilderPage, GameLeagues, fmt_text, europe_text, tier_of, pixmap

CONTINENTS = ((2, "Europe"), (3, "Asia"), (4, "South America"), (5, "Africa"),
              (6, "North and Central America"), (7, "Oceania"), (0, "Other"))
ROLE = Qt.UserRole


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
        event.accept()
        self.moved.emit()


class Leagues(BuilderPage):
    title = "Leagues"
    hint = ("Every league: the game's own and the ones you add. Drag a league to put it in order; pick one "
            "to change it on the right.")
    help = ("The list on the left has all the leagues by continent.\n"
            "- game: a league the game has; you can rename it, give it a logo and change its clubs.\n"
            "- ours: a league your recipe adds; Edit league changes its clubs, format and division.\n"
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
        for label, name in (("Pre-season cups", "preseason"), ("Cups of the game's countries", "game_cups"),
                            ("European places of the game's leagues", "game_europe"),
                            ("UEFA ranking", "uefa_rank"), ("South American places", "samerica"),
                            ("Competition names", "competition_names")):
            m.addAction(_(label)).triggered.connect(lambda _c=False, n=name: getattr(self.nl(), n)())
        m.addSeparator()
        m.addAction(_("World name and recipe...")).triggered.connect(lambda: self.app.open_page("NewLeagues"))
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
        for i, text in enumerate(("All", "Ours", "Changed")):
            b = QPushButton(_(text))
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
        lv.addWidget(self.tree, 1)
        self.count = hint("")
        lv.addWidget(self.count)
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
        ov.addWidget(self.o_name)
        f = QFormLayout()
        f.setHorizontalSpacing(18)
        f.setVerticalSpacing(8)
        self.o_rows = {}
        for key in ("Country", "Clubs", "Format", "Division", "Up / down", "Europe", "League ID"):
            lab = QLabel("")
            lab.setWordWrap(True)
            self.o_rows[key] = lab
            f.addRow(_(key), lab)
        ov.addLayout(f)
        b_edit = QPushButton(_("Edit league..."))
        b_edit.setObjectName("primary")
        b_edit.clicked.connect(lambda: self.on_ours("edit"))
        b_low = QPushButton(_("Add lower tier"))
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
        self.right.addWidget(ours)
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
        split.addWidget(self.right)
        split.setSizes([340, 900])
        split.setStretchFactor(1, 1)
        self.outer.addWidget(split, 1)
        self.project.changed.connect(self.fill)

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
        late = len(order)
        return sorted(out, key=lambda x: order.get(x[0], late))     # stable: unknown keep theirs

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
            h.setForeground(0, QBrush(QColor("#6F7986")))
            fnt = h.font(0)
            fnt.setBold(True)
            fnt.setPointSizeF(fnt.pointSizeF() * 0.85)
            h.setFont(0, fnt)
            heads[code] = h
        tags = {"game": (_("game"), theme.SUBTLE), "ours": (_("ours"), theme.ACCENT),
                "changed": (_("changed"), theme.WARN)}
        pick, shown, total = None, 0, 0
        for e in self.entries():
            k, conf, name, kind, payload = e
            total += 1
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
        ours = len(self.project.recipe["leagues"])
        self.count.setText(_("%d leagues: %d of the game, %d of yours.") % (total, total - ours, ours)
                           if shown == total else _("%d of %d leagues shown.") % (shown, total))

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
        pos = {k: n for n, k in enumerate(keys)}
        r["leagues"].sort(key=lambda L: pos.get("o" + L["name"], len(pos)))
        self.project.touch()

    # ---- the right side ----
    def current(self):
        it = self.tree.currentItem()
        return it.data(0, ROLE) if it else None

    def show_current(self):
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
        from .builder import built_plan, built_league
        P = self.project
        r = P.recipe
        L = r["leagues"][i]
        names = dict(P.parents)
        up = L.get("above")
        div = _("top") if up in (None, "") else _("below %s") % (names.get(up, up) if isinstance(up, int) else up)
        t = tier_of(P, up)
        plan = built_plan(self.app.game, r.get("world"))
        b = built_league(self.app.game, r.get("world"), L["name"], plan or {})
        self.o_name.setText(L["name"])
        vals = {"Country": L.get("country", ""), "Clubs": str(L.get("clubs", "")), "Format": fmt_text(L),
                "Division": ("%d  (%s)" % (t, div)) if t else div,
                "Up / down": str(L.get("exchange", 3)) if up not in (None, "") else "—",
                "Europe": europe_text(L) or "—",
                "League ID": str(b["cid"]) if b.get("cid") is not None else
                (_("not built yet") if plan else "—")}
        for k, v in vals.items():
            self.o_rows[k].setText(v)

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
