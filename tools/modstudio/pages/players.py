"""Players: the squad of one club -- a new club of the recipe or one of the game's -- and every
field of each player.  Changes go into the recipe (lbplayers.py) and into the world at Build."""
import os

from PySide6.QtCore import Qt, QStringListModel
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (QCheckBox, QComboBox, QCompleter, QFileDialog, QFormLayout, QGridLayout,
                               QHBoxLayout, QInputDialog, QLabel, QLineEdit, QPushButton, QScrollArea,
                               QSpinBox, QSplitter, QTabWidget, QTreeWidget, QTreeWidgetItem,
                               QVBoxLayout, QWidget)

import lbplayers as P
import leaguebuilder as B
import playeredit as E
from .. import theme
from ..i18n import _
from ..ui import hint, row, ask, error, info, section
from .builder import BuilderPage

RATING = ["-", "B", "A"]          # position ratings 0 1 2, as the game's Edit mode shows them
NEW = "+"                          # key prefix of a player added to a game club: "+0", "+1" ...


class Players(BuilderPage):
    title = "Players"
    hint = ("The squad of a club: names, shirt numbers, the starting eleven (the first eleven by squad "
            "order), positions, abilities and skills. Works for the new clubs of the recipe and for the "
            "game's clubs; the changes are written into your world when you Build.")

    def __init__(self, app):
        super().__init__(app)
        self.club = None               # recipe key: "<tid>" or "<league>/<k>"
        self.rows = []                 # the club's players as they are, before changes
        self.cur = None                # key of the player in the inspector
        self._filling = False
        self.action("Best eleven", self.best_eleven, tip="Put the strongest player for each place of the "
                    "club's formation at the top of the squad order")
        self.action("Squad level...", self.squad_level, tip="Raise or lower every ability of the whole squad")
        self.action("Import a squad from a table...", self.import_table,
                    tip="Any CSV of players -- typed by hand, off a website, from Football Manager or an EA FC "
                        "database -- becomes this club's squad")
        self.action("Import CSV...", self.import_csv)
        self.action("Export CSV...", self.export_csv)

        pick = QHBoxLayout()
        pick.addWidget(QLabel(_("League")))
        self.lg = QComboBox()
        self.lg.setMinimumWidth(240)
        self.lg.currentIndexChanged.connect(self.fill_clubs)
        pick.addWidget(self.lg)
        pick.addWidget(QLabel(_("Club")))
        self.cl = QComboBox()
        self.cl.setMinimumWidth(240)
        self.cl.currentIndexChanged.connect(self.club_picked)
        pick.addWidget(self.cl)
        self.find = QLineEdit()
        self.find.setPlaceholderText(_("Find a club..."))
        self.find.setFixedWidth(220)
        self.completer = QCompleter()
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchContains)
        self.completer.activated.connect(self.found)
        self.find.setCompleter(self.completer)
        pick.addWidget(self.find)
        pick.addStretch(1)
        self.outer.addLayout(pick)

        split = QSplitter(Qt.Horizontal)
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 6, 0)
        self.tree = QTreeWidget()
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setHeaderLabels([_("Order"), _("No."), _("Name"), _("Pos"), _("Age"), _("Rating"),
                                   _("Foot"), _("Changed")])
        for c, w in enumerate((62, 40, 220, 50, 40, 55, 50, 80)):
            self.tree.setColumnWidth(c, w)
        self.tree.currentItemChanged.connect(lambda *_a: self.inspect())
        lv.addWidget(self.tree, 1)
        self.b_add = QPushButton(_("Add player"))
        self.b_add.clicked.connect(self.add_player)
        self.b_add.setToolTip(_("A copy of the selected player joins the end of the squad"))
        self.b_remove = QPushButton(_("Remove from club"))
        self.b_remove.clicked.connect(self.remove_player)
        self.b_up = QPushButton(_("Order up"))
        self.b_up.clicked.connect(lambda: self.shift(-1))
        self.b_down = QPushButton(_("Order down"))
        self.b_down.clicked.connect(lambda: self.shift(1))
        self.b_undo_all = QPushButton(_("Undo all changes of this club"))
        self.b_undo_all.setObjectName("danger")
        self.b_undo_all.clicked.connect(self.undo_club)
        lv.addWidget(row(self.b_up, self.b_down, self.b_add, self.b_remove, "stretch", self.b_undo_all, stretch=False))
        self.foot = hint("")
        lv.addWidget(self.foot)
        from ..pitch import Pitch
        self.pitch = Pitch()
        self.pitch.setFixedHeight(340)
        self.pitch.setToolTip(_("The first eleven in the club's formation. Select a player in the list, "
                                "then click a place to put that player there."))
        self.pitch.picked.connect(self.put_at)
        lv.addWidget(self.pitch)
        split.addWidget(left)
        split.addWidget(self._inspector())
        split.setSizes([640, 520])
        self.outer.addWidget(split, 1)
        self.project.changed.connect(self.recipe_changed)

    # ---- the inspector ----
    def _inspector(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(6, 0, 0, 0)
        self.i_title = QLabel("")
        self.i_title.setObjectName("title")
        v.addWidget(self.i_title)
        self.i_sub = hint("")
        v.addWidget(self.i_sub)
        self.ed = {}                   # field -> widget
        self.lab = {}                  # field -> its label (turns accent when changed)
        tabs = QTabWidget()

        basic = QWidget()
        f = QFormLayout(basic)
        f.setLabelAlignment(Qt.AlignRight)
        self._add(f, "name", QLineEdit(), "Name")
        face = QLineEdit()
        face.setReadOnly(True)
        face.setPlaceholderText(_("the game's face"))
        pick_face = QPushButton(_("Choose..."))
        pick_face.setToolTip(_("A face folder: the one with #Win\\face.fpk in it, or a face mod holding one face"))
        pick_face.clicked.connect(self.choose_face)
        no_face = QPushButton(_("Clear"))
        no_face.clicked.connect(lambda: self.set_face(""))
        lab = QLabel(_("Face"))
        f.addRow(lab, row(face, pick_face, no_face, stretch=False))
        self.ed["face"], self.lab["face"] = face, lab
        self.face_note = hint("")
        f.addRow("", self.face_note)
        self._add(f, "shirt", self._spin(1, 99), "Shirt number")
        self._add(f, "order", self._spin(0, 63), "Squad order")
        pos = QComboBox()
        pos.addItems(E.POSITIONS)
        self._add(f, "Registered Position", pos, "Position")
        self.rating = self._spin(40, 99)          # not a field of its own: it moves the abilities
        self.rating.setToolTip(_("The rating of the list, made of the abilities the position leans on. "
                                 "Changing it moves every ability by the same amount."))
        self.rating.valueChanged.connect(self.set_rating)
        f.addRow(QLabel(_("Rating")), self.rating)
        for n in ("Age", "Height (cm)", "Weight (kg)"):
            lo, hi = E.LIMITS[n]
            self._add(f, n, self._spin(lo, hi), n)
        foot = QComboBox()
        foot.addItems(["Right", "Left"])
        self._add(f, "Stronger Foot", foot, "Stronger foot")
        for n in ("Weak Foot Usage", "Weak Foot Accuracy", "Form", "Injury Resistance", "Playing Style"):
            lo, hi = E.LIMITS[n]
            self._add(f, n, self._spin(lo, hi), n)
        nat = QComboBox()             # filled from the game's Country table (fill_countries)
        nat.setEditable(True)
        nat.setInsertPolicy(QComboBox.NoInsert)
        self._add(f, "Nationality", nat, "Nationality")
        f.addRow("", hint(_("Playing style is the game's number: copy it from a player with that style "
                            "(Export CSV shows it). The CSV keeps the country's number for nationality.")))
        tabs.addTab(self._scroll(basic), _("Basics"))

        pw = QWidget()
        g = QGridLayout(pw)
        for i, p in enumerate(E.POSITIONS):
            c = QComboBox()
            c.addItems(RATING)
            lab = QLabel(p)
            g.addWidget(lab, i // 3, (i % 3) * 2, Qt.AlignRight)
            g.addWidget(c, i // 3, (i % 3) * 2 + 1)
            self.ed[p], self.lab[p] = c, lab
            c.currentIndexChanged.connect(lambda _i, n=p: self.edited(n))
        g.addWidget(hint(_("A = natural position, B = can play there, - = not at all.")), 5, 0, 1, 6)
        g.setRowStretch(6, 1)
        tabs.addTab(pw, _("Positions"))

        aw = QWidget()
        g = QGridLayout(aw)
        for i, (n, _b) in enumerate(E.ABILITIES):
            s = self._spin(40, 99)
            lab = QLabel(_(n))
            g.addWidget(lab, i % 13, (i // 13) * 2, Qt.AlignRight)
            g.addWidget(s, i % 13, (i // 13) * 2 + 1)
            self.ed[n], self.lab[n] = s, lab
            s.valueChanged.connect(lambda _v, n=n: self.edited(n))
        g.setRowStretch(13, 1)
        tabs.addTab(self._scroll(aw), _("Abilities"))

        sw = QWidget()
        g = QGridLayout(sw)
        for i, (n, _b) in enumerate(E.SKILLS):
            c = QCheckBox(_(n))
            g.addWidget(c, i % 24, i // 24)
            self.ed[n], self.lab[n] = c, c
            c.toggled.connect(lambda _v, n=n: self.edited(n))
        tabs.addTab(self._scroll(sw), _("Skills"))
        v.addWidget(tabs, 1)
        self.b_undo = QPushButton(_("Undo changes to this player"))
        self.b_undo.clicked.connect(self.undo_player)
        v.addWidget(row(self.b_undo))
        return w

    def _spin(self, lo, hi):
        s = QSpinBox()
        s.setRange(lo, hi)
        s.setFixedWidth(80)
        return s

    def _scroll(self, w):
        s = QScrollArea()
        s.setWidgetResizable(True)
        s.setFrameShape(QScrollArea.NoFrame)
        s.setWidget(w)
        return s

    def _add(self, form, key, widget, label):
        lab = QLabel(_(label))
        form.addRow(lab, widget)
        self.ed[key], self.lab[key] = widget, lab
        if isinstance(widget, QLineEdit):
            widget.editingFinished.connect(lambda k=key: self.edited(k))
        elif isinstance(widget, QSpinBox):
            widget.valueChanged.connect(lambda _v, k=key: self.edited(k))
        elif isinstance(widget, QComboBox):
            widget.currentIndexChanged.connect(lambda _i, k=key: self.edited(k))

    def _get(self, key):
        w = self.ed[key]
        if isinstance(w, QLineEdit):
            return w.text().strip()
        if isinstance(w, QSpinBox):
            return str(w.value())
        if isinstance(w, QCheckBox):
            return "1" if w.isChecked() else "0"
        if key in E.POSITIONS:
            return str(w.currentIndex())
        if key == "Nationality":
            i = w.findText(w.currentText())     # typed text counts only when it names a country
            return str(w.itemData(i if i >= 0 else w.currentIndex()))
        return w.currentText()

    def _set(self, key, val):
        w = self.ed[key]
        val = "" if val is None else str(val)
        if isinstance(w, QLineEdit):
            w.setText(val)
        elif isinstance(w, QSpinBox):
            w.setValue(int(val) if val.lstrip("-").isdigit() else w.minimum())
        elif isinstance(w, QCheckBox):
            w.setChecked(val == "1")
        elif key in E.POSITIONS:
            w.setCurrentIndex(int(val) if val.isdigit() else 0)
        elif key == "Nationality":
            self.fill_countries()
            i = w.findData(int(val)) if val.isdigit() else -1
            if i < 0 and val.isdigit():           # a number the table does not name: keep it
                w.addItem("%s (%s)" % (_("unknown country"), val), int(val))
                i = w.count() - 1
            w.setCurrentIndex(max(0, i))
        else:
            i = w.findText(val)
            w.setCurrentIndex(max(0, i))

    def fill_countries(self):
        w = self.ed["Nationality"]
        if w.count() or not self.project.base:
            return
        w.blockSignals(True)
        for name, fid in B.country_ids(self.project.base):
            w.addItem(name, fid)
        w.blockSignals(False)

    # ---- which club ----
    def shown(self):
        if self.need_tables():
            return
        self.say("")
        if self.lg.count() == 0:
            self.fill_leagues()

    def refresh(self):
        self.fill_leagues()

    def recipe_changed(self):
        if self.isVisible():
            self.fill_leagues()

    def fill_leagues(self):
        P_ = self.project
        keep = self.lg.currentData()
        self.lg.blockSignals(True)
        self.lg.clear()
        for L in P_.recipe["leagues"]:
            self.lg.addItem("★ " + L["name"], ("new", L["name"]))
        for rid, cid, name, teams in P_.game_lgs:
            e = P_.edits("leagues").get(str(rid), {})
            self.lg.addItem(e.get("name", name), ("game", rid))
        for gid, name, teams in P_.game_groups():   # the game's "Others" sections
            self.lg.addItem("%s  (%d)" % (name, len(teams)), ("game", gid))
        i = next((n for n in range(self.lg.count()) if self.lg.itemData(n) == keep), -1) if keep else -1
        self.lg.setCurrentIndex(max(0, i))
        self.lg.blockSignals(False)
        names = []
        for L in P_.recipe["leagues"]:
            for k, n in enumerate(self.new_names(L)):
                names.append("%s  —  %s" % (n, L["name"]))
        for tid, (n, a) in sorted(P_.game_cl.items(), key=lambda x: x[1][0]):
            names.append("%s  —  #%d" % (self.game_name(tid), tid))
        self.completer.setModel(QStringListModel(names, self))
        self.fill_clubs()

    def new_names(self, L):
        names = list(L.get("club_names") or [])
        return [(names[k] if k < len(names) and names[k] else "%s %02d" % (L["name"], k + 1))
                for k in range(L.get("clubs", 0))]

    def game_name(self, tid):
        e = self.project.edits("clubs").get(str(tid), {})
        return e.get("name") or self.project.game_cl.get(tid, ("?", ""))[0]

    def fill_clubs(self):
        d = self.lg.currentData()
        keep = self.club
        self.cl.blockSignals(True)
        self.cl.clear()
        if d and d[0] == "new":
            L = self.project.league(d[1])
            if L:
                for k, n in enumerate(self.new_names(L)):
                    self.cl.addItem(n, P.new_key(L["name"], k))
        elif d:
            teams = next((t for r, c, n, t in self.project.game_lgs if r == d[1]), None)
            if teams is None:
                teams = next((t for g, n, t in self.project.game_groups() if g == d[1]), [])
            for tid in teams:
                if tid in self.project.game_cl:
                    self.cl.addItem(self.game_name(tid), str(tid))
        i = self.cl.findData(keep) if keep else -1
        self.cl.setCurrentIndex(max(0, i))
        self.cl.blockSignals(False)
        self.club_picked()

    def found(self, text):
        label, _s, where = text.rpartition("  —  ")
        if where.startswith("#") and where[1:].isdigit():
            self.show_club(where[1:])
        else:
            L = self.project.league(where)
            if L:
                names = self.new_names(L)
                if label in names:
                    self.show_club(P.new_key(where, names.index(label)))
        self.find.clear()

    def show_club(self, key):
        """open a club by its recipe key (other pages call this)"""
        if self.project.base is None:
            return
        if not key.isdigit():
            lgname = key.rpartition("/")[0]
            data = ("new", lgname)
        else:
            tid = int(key)
            rid = next((r for r, c, n, t in self.project.game_lgs if tid in t), None)
            if rid is None:
                rid = next((g for g, n, t in self.project.game_groups() if tid in t), None)
            data = ("game", rid)
        if self.lg.count() == 0:
            self.fill_leagues()
        # findData does not match a Python tuple (measured: -1 for ("new", name) that is there)
        i = next((n for n in range(self.lg.count()) if self.lg.itemData(n) == data), -1)
        self.club = key
        if i >= 0:
            self.lg.setCurrentIndex(i)
            self.fill_clubs()
        else:                              # a club in no league
            self.cl.blockSignals(True)
            self.cl.clear()
            self.cl.addItem(self.game_name(int(key)), key)
            self.cl.blockSignals(False)
            self.club_picked()

    def club_picked(self):
        key = self.cl.currentData()
        self.club = key
        sq = self.project.squads()
        if not key or sq is None:
            self.rows = []
        elif key.isdigit():
            self.rows = sq.squad(int(key))
        else:
            self.rows = sq.proto()
        self.cur = None
        self.fill_squad()

    # ---- the squad ----
    def changes(self, create=False):
        pl = self.project.players()
        if create:
            return pl.setdefault(self.club, {})
        return pl.get(self.club) or {}

    def view(self):
        """[(key, row as it will be, what changed)] in squad order, removed players last"""
        c = self.changes()
        ed = c.get("edits") or {}
        gone = set(c.get("remove") or [])
        out = []
        for r in self.rows:
            ch = ed.get(r["player"], {})
            m = dict(r)
            m.update(ch)
            out.append((r["player"], m, ch, r["player"] in gone))
        base = len(self.rows)
        for i, a in enumerate(c.get("add") or []):
            like = next((r for r in self.rows if r["player"] == str(a.get("like"))), self.rows[0] if self.rows else {})
            m = dict(like)
            m.update({"player": NEW + str(i), "order": str(base + i), "shirt": ""})
            m.update({k: v for k, v in a.items() if k != "like"})
            out.append((NEW + str(i), m, a, False))
        if self.club and not self.club.isdigit() and not any("order" in ch for ch in ed.values()):
            auto = P.best_eleven([dict(m, player=k) for k, m, ch, g in out if not g],    # what Build will do
                                 self.lineup())
            for k, m, ch, g in out:
                m["order"] = auto.get(k, m.get("order", ""))
        out.sort(key=lambda x: (x[3], int(x[1].get("order") or 0) if str(x[1].get("order", "")).isdigit() else 99))
        return out

    def fill_squad(self):
        self._filling = True
        keep = self.cur
        self.tree.clear()
        new_club = bool(self.club) and not self.club.isdigit()
        for key, m, ch, gone in self.view():
            name = m.get("name") or (_("(numbered name)") if new_club else "")
            it = QTreeWidgetItem([m.get("order", ""), m.get("shirt", ""), name, m.get("Registered Position", ""),
                                  m.get("Age", ""), str(P.overall(m)), m.get("Stronger Foot", "")[:1],
                                  _("leaves") if gone else (_("new") if key.startswith(NEW) else
                                                            (_("%d fields") % len(ch) if ch else ""))])
            it.setData(0, Qt.UserRole, key)
            if str(m.get("order", "")).isdigit() and int(m["order"]) < 11 and not gone:
                f = it.font(2)
                f.setBold(True)
                it.setFont(2, f)
            if gone:
                for c in range(8):
                    it.setForeground(c, QBrush(QColor(theme.SUBTLE)))
                f = it.font(2)
                f.setStrikeOut(True)
                it.setFont(2, f)
            elif ch:
                it.setForeground(7, QBrush(QColor(theme.ACCENT)))
            if not m.get("name"):
                it.setForeground(2, QBrush(QColor(theme.SUBTLE)))
            self.tree.addTopLevelItem(it)
            if key == keep:
                self.tree.setCurrentItem(it)
        self._filling = False
        game = bool(self.club) and self.club.isdigit()
        self.b_add.setEnabled(game)
        self.b_remove.setEnabled(bool(self.club))     # a new club can lose players, not gain them
        c = self.changes()
        n = len(c.get("edits") or {}) + len(c.get("add") or []) + len(c.get("remove") or [])
        self.foot.setText((_("%d players; the first eleven by squad order (bold) start.") % len(self.rows))
                          + ("   " + _("%d changes in this club.") % n if n else "")
                          + ("   " + _("New clubs start with the same squad, and Build picks its best "
                                       "eleven unless you set the order here.") if new_club else ""))
        if self.tree.currentItem() is None and self.tree.topLevelItemCount():
            self.tree.setCurrentItem(self.tree.topLevelItem(0))
        else:
            self.inspect()
        self.draw_pitch()

    # ---- the formation (new clubs) ----
    def places(self):
        """a new club's formation places (None: the engine's 4-2-3-1)"""
        return self.project.club_places(self.club) if self.club and not self.club.isdigit() else None

    def lineup(self):
        import mktactics
        p = self.places()
        return mktactics.roles(p) if p else None

    def draw_pitch(self):
        new_club = bool(self.club) and not self.club.isdigit()
        self.pitch.setVisible(new_club)
        if not new_club:
            return
        names, mark = {}, None
        for k, m, ch, gone in self.view():
            o = str(m.get("order", ""))
            if gone or not o.isdigit() or int(o) > 10:
                continue
            nm = m.get("name") or (m.get("Registered Position", "") + " " + str(P.overall(m)))
            names[int(o)] = nm if len(nm) <= 18 else nm[:17] + "."
            if k == self.cur:
                mark = int(o)
        self.pitch.show_places(self.places(), names, mark)

    def put_at(self, place):
        """the selected player takes the place (order) clicked; whoever was there takes his"""
        if not self.cur or not self.club or self.club.isdigit():
            return
        live = [x for x in self.view() if not x[3]]
        i = next((n for n, x in enumerate(live) if x[0] == self.cur), None)
        if i is None or place >= len(live) or i == place:
            return
        live[i], live[place] = live[place], live[i]
        self.set_orders({x[0]: str(n) for n, x in enumerate(live)})

    def current_view(self):
        it = self.tree.currentItem()
        if not it:
            return None
        key = it.data(0, Qt.UserRole)
        return next((v for v in self.view() if v[0] == key), None)

    def inspect(self):
        if self._filling:
            return
        v = self.current_view()
        self.cur = v[0] if v else None
        self._filling = True
        if not v:
            self.i_title.setText("")
            self.i_sub.setText("")
            self._filling = False
            return
        key, m, ch, gone = v
        orig = self.original(key)
        if hasattr(self, "pitch") and self.pitch.isVisible():
            o = str(m.get("order", ""))
            self.pitch.mark = int(o) if o.isdigit() and int(o) <= 10 else None
            self.pitch.update()
        self.i_title.setText(m.get("name") or _("(numbered name)"))
        self.i_sub.setText(_("player %s") % key if key.isdigit() and self.club.isdigit() else
                           (_("new player (a copy of %s)") % (orig.get("name") or "?") if key.startswith(NEW)
                            else _("place %d in the squad") % (int(key) + 1)))
        for k in self.ed:
            self._set(k, m.get(k, ""))
            self._mark(k, k in ch and str(ch[k]) != str(orig.get(k, "")))
        # a new club's player has no name until Build numbers him (FL P00001 ...): say so in the box
        self.ed["name"].setPlaceholderText(_("numbered at Build (FL P00001 ...) until you type a name")
                                           if not self.club.isdigit() else "")
        self.rating.setValue(P.overall(m))
        self.b_undo.setEnabled(bool(ch) and not key.startswith(NEW))
        self.show_face_note(m.get("face", ""))
        self._filling = False

    def show_face_note(self, folder):
        if not folder:
            self.face_note.setText(_("A face is moved to this player's id when you Build, so it can come "
                                     "from any face mod."))
            return
        import lbfaces
        bad = lbfaces.check(folder)
        if bad:
            self.face_note.setText(_("Problem: %s") % bad[0])
            return
        face = lbfaces.find(folder)
        self.face_note.setText(_("A face made for player %s%s.") % (
            lbfaces.old_id(face), _(", with a portrait") if lbfaces.portrait(face) else ""))

    def choose_face(self):
        if self.cur is None:
            return
        d = QFileDialog.getExistingDirectory(self, _("Choose the face folder"),
                                             self.app.settings.get("face_dir", ""))
        if d:
            self.app.settings["face_dir"] = os.path.dirname(d)
            self.set_face(d)

    def set_face(self, folder):
        if self.cur is None:
            return
        if folder:
            import lbfaces
            face = lbfaces.find(folder)
            bad = lbfaces.check(folder)
            if bad:
                error(self, "Players", bad[0] if face or os.path.isfile(os.path.join(folder, "#Win", "face.fpk"))
                      else _("There is no single face in %s (a folder with #Win\\face.fpk). "
                             "Pick the folder of one face.") % folder)
                return
            folder = os.path.normpath(face)
        self.ed["face"].setText(folder)
        self.edited("face")
        self.show_face_note(folder)

    def original(self, key):
        if key.startswith(NEW):
            a = (self.changes().get("add") or [])[int(key[1:])]
            return next((r for r in self.rows if r["player"] == str(a.get("like"))), {})
        return next((r for r in self.rows if r["player"] == key), {})

    def _mark(self, key, on):
        lab = self.lab[key]
        lab.setStyleSheet("color: %s; font-weight: bold;" % theme.ACCENT if on else "")

    def edited(self, key):
        if self._filling or self.cur is None or not self.club:
            return
        val = self._get(key)
        orig = self.original(self.cur)
        if key == "name" and not val and not self.club.isdigit():
            val = ""
        if self.cur.startswith(NEW):
            a = self.changes(True).setdefault("add", [])[int(self.cur[1:])]
            a[key] = val
        else:
            ed = self.changes(True).setdefault("edits", {})
            ch = ed.setdefault(self.cur, {})
            if val == str(orig.get(key, "")):
                ch.pop(key, None)
            else:
                ch[key] = val
            if key == "Registered Position" and val != orig.get(key):
                p = E.POSITIONS.index(val) if val in E.POSITIONS else None
                if p is not None and ch.get(val, orig.get(val)) != "2":
                    ch[val] = "2"             # a new position is a natural one, as playeredit does
            if not ch:
                ed.pop(self.cur, None)
        err = P.check_edit({key: val}) if val != "" else []
        if err:
            self.say(err[0], "err")
        else:
            self.say("")
        self.project.dirty = True
        self._mark(key, val != str(orig.get(key, "")))
        if key in ("name", "shirt", "order", "Registered Position", "Age", "Stronger Foot") or key in E.FIELDS:
            self.update_row()

    def update_row(self):
        it = self.tree.currentItem()
        v = self.current_view()
        if not it or not v:
            return
        key, m, ch, gone = v
        vals = [m.get("order", ""), m.get("shirt", ""), m.get("name") or _("(numbered name)"),
                m.get("Registered Position", ""), m.get("Age", ""), str(P.overall(m)),
                m.get("Stronger Foot", "")[:1],
                _("new") if key.startswith(NEW) else (_("%d fields") % len(ch) if ch else "")]
        for c, t in enumerate(vals):
            it.setText(c, t)
        self.i_title.setText(m.get("name") or _("(numbered name)"))
        self.rating.blockSignals(True)
        self.rating.setValue(P.overall(m))
        self.rating.blockSignals(False)

    def set_rating(self, want):
        """the player's rating: every ability moves by the same amount, as Squad level does for a
        whole squad; abilities stuck at 40 or 99 hold it back, so it goes again until it lands"""
        v = self.current_view()
        if self._filling or not v or not self.club:
            return
        m = dict(v[1])
        for _t in range(5):
            d = want - P.overall(m)
            if not d:
                break
            for n, _b in E.ABILITIES:
                m[n] = str(max(40, min(99, int(m.get(n) or 40) + d)))
        self._filling = True
        for n, _b in E.ABILITIES:
            self._set(n, m[n])
        self._filling = False
        for n, _b in E.ABILITIES:
            self.edited(n)

    # ---- actions ----
    def undo_player(self):
        if self.cur and not self.cur.startswith(NEW):
            (self.changes().get("edits") or {}).pop(self.cur, None)
            self.project.dirty = True
            self.fill_squad()

    def undo_club(self):
        if self.club and self.changes() and ask(self, "Players", _("Forget every change to this club's players?")):
            self.project.players().pop(self.club, None)
            self.project.dirty = True
            self.fill_squad()

    def set_orders(self, orders):
        """orders: {key: order text}; keys of added players too"""
        c = self.changes(True)
        ed = c.setdefault("edits", {})
        for key, o in orders.items():
            if key.startswith(NEW):
                c["add"][int(key[1:])]["order"] = o
                continue
            orig = self.original(key)
            ch = ed.setdefault(key, {})
            if o == str(orig.get("order", "")):
                ch.pop("order", None)
            else:
                ch["order"] = o
            if not ch:
                ed.pop(key, None)
        self.project.dirty = True
        self.fill_squad()

    def shift(self, d):
        v = self.view()
        live = [x for x in v if not x[3]]
        i = next((n for n, x in enumerate(live) if x[0] == self.cur), None)
        if i is None or not 0 <= i + d < len(live):
            return
        live[i], live[i + d] = live[i + d], live[i]
        self.set_orders({x[0]: str(n) for n, x in enumerate(live)})

    def best_eleven(self):
        if not self.rows:
            return
        live = [dict(m, player=k) for k, m, ch, gone in self.view() if not gone]
        self.set_orders(P.best_eleven(live, self.lineup()))
        self.say(_("The strongest eleven for the club's formation now head the squad order."), "ok")

    def squad_level(self):
        if not self.rows:
            return
        live = [(k, m) for k, m, ch, gone in self.view() if not gone]
        now = round(sum(P.overall(m) for k, m in live) / len(live))
        want, ok = QInputDialog.getInt(self, _("Squad level..."),
                                       _("The squad's average rating is %d. Make it:") % now, now, 40, 99)
        if not ok or want == now:
            return
        d = want - now
        c = self.changes(True)
        ed = c.setdefault("edits", {})
        for k, m in live:
            orig = self.original(k)
            target = c["add"][int(k[1:])] if k.startswith(NEW) else ed.setdefault(k, {})
            for n, _b in E.ABILITIES:
                v = max(40, min(99, int(m.get(n) or 40) + d))
                if not k.startswith(NEW) and str(v) == str(orig.get(n, "")):
                    target.pop(n, None)
                else:
                    target[n] = str(v)
            if not k.startswith(NEW) and not target:
                ed.pop(k, None)
        self.project.dirty = True
        self.fill_squad()
        self.say(_("Every ability moved by %+d.") % d, "ok")

    def add_player(self):
        if not self.club or not self.club.isdigit() or not self.cur:
            return
        like = self.cur if not self.cur.startswith(NEW) else \
            str((self.changes().get("add") or [])[int(self.cur[1:])].get("like"))
        self.changes(True).setdefault("add", []).append({"like": like, "name": ""})
        self.project.dirty = True
        self.cur = NEW + str(len(self.changes()["add"]) - 1)
        self.fill_squad()
        self.ed["name"].setFocus()

    def remove_player(self):
        if not self.club or not self.cur:
            return
        if not self.club.isdigit():
            gone = self.changes().get("remove") or []
            if self.cur not in gone and len(self.rows) - len(gone) <= P.MIN_SQUAD:
                self.say(_("A new club keeps at least %d players.") % P.MIN_SQUAD, "err")
                return
        c = self.changes(True)
        if self.cur.startswith(NEW):
            del c["add"][int(self.cur[1:])]
            self.cur = None
        else:
            gone = c.setdefault("remove", [])
            if self.cur in gone:
                gone.remove(self.cur)          # a second press takes it back
            else:
                gone.append(self.cur)
        self.project.dirty = True
        self.fill_squad()

    def export_csv(self):
        if not self.rows:
            return
        name = self.cl.currentText() or "squad"
        p, _f = QFileDialog.getSaveFileName(self, _("Export CSV..."), name + ".csv", "CSV (*.csv)")
        if not p:
            return
        P.export_csv(p, [m for k, m, ch, gone in self.view() if not gone])
        self.app.status(_("Squad written to %s") % p)

    def import_csv(self):
        if not self.rows:
            return
        p, _f = QFileDialog.getOpenFileName(self, _("Import CSV..."), "", "CSV (*.csv);;" + _("All files") + " (*.*)")
        if not p:
            return
        try:
            live = [dict(m, player=k) for k, m, ch, gone in self.view() if not gone and not k.startswith(NEW)]
            got, err = P.import_csv(p, live)
        except (P.Error, OSError, ValueError) as e:
            error(self, "Import CSV...", str(e))
            return
        if err:
            error(self, "Import CSV...", _("Nothing imported:") + "\n\n" + "\n".join(err[:15]))
            return
        ed = self.changes(True).setdefault("edits", {})
        for key, ch in got.items():
            orig = self.original(key)
            cur = ed.setdefault(key, {})
            for k, v in ch.items():
                if v == str(orig.get(k, "")):
                    cur.pop(k, None)
                else:
                    cur[k] = v
            if not cur:
                ed.pop(key, None)
        self.project.dirty = True
        self.fill_squad()
        info(self, "Import CSV...", _("%d players changed.") % len(got))

    def import_table(self):
        """a squad from any table of players (squadimport.py): the table's players take the club's
        places in squad order; a game club gains or loses players to match, a new club keeps its
        30 places and can lose players down to 18"""
        import squadimport as Q
        from .tableimport import ImportDialog
        if not self.rows or not self.club:
            return
        title = "Import a squad from a table..."
        p, _f = QFileDialog.getOpenFileName(self, _(title), "", "CSV (*.csv *.txt);;" + _("All files") + " (*.*)")
        if not p:
            return
        try:
            head, rows = Q.read_table(p)
        except (OSError, UnicodeError, ValueError) as e:
            error(self, title, str(e))
            return
        if not head or not rows:
            error(self, title, _("The table has no players in it."))
            return
        new = not self.club.isdigit()
        keys = [r["player"] for r in self.rows]
        room = (_("A new club has %d places: the table's first %d players take them, and places left over "
                  "leave the club (it keeps at least %d).") % (P.SQUAD, P.SQUAD, P.MIN_SQUAD) if new else
                _("The table's players take the places of the club's %d players in squad order; more are "
                  "added, fewer leave the club (it keeps at least %d).") % (len(keys), P.MIN_SQUAD))
        dlg = ImportDialog(self, os.path.basename(p), head, rows, room)
        if not dlg.exec():
            return
        mapping = dlg.mapping()
        if not any(t in ("name", "first", "last") for t in mapping.values()):
            error(self, title, _("Pick the column with the players' names."))
            return
        if self.changes() and not ask(self, "Players", _("This club already has changes to its players. "
                                                         "Replace them with the table?")):
            return
        base = self.project.base
        if getattr(self, "_model_for", None) is not base:
            self._model = Q.Model(self.project.squads().players)
            self._model_for = base
        countries = Q.Countries(B.country_ids(base))
        nation = None
        if new:
            L = self.project.league(self.club.rpartition("/")[0])
            nation = countries.find((L or {}).get("country", ""))
        players, warn = Q.convert(head, rows, mapping, self._model, countries, nation, level=dlg.level())
        if not players:
            error(self, title, _("No player could be read:") + "\n\n" + "\n".join(warn[:15]))
            return
        if new and len(players) > P.SQUAD:
            warn.append(_("The table has %d players; a new club takes the first %d.") % (len(players), P.SQUAD))
            players = players[:P.SQUAD]
        if len(players) < P.MIN_SQUAD:
            warn.append(_("The table has %d players; the club keeps %d, so %d stay as they were.")
                        % (len(players), P.MIN_SQUAD, P.MIN_SQUAD - len(players)))

        self.project.players().pop(self.club, None)
        c = self.changes(True)
        ed = c.setdefault("edits", {})
        for k, pl in zip(keys, players):
            orig = self.original(k)
            ch = {f: v for f, v in pl.items() if v != str(orig.get(f, ""))}
            if ch:
                ed[k] = ch
        for pl in players[len(keys):]:              # a game club only: the rest join it
            like = next((r["player"] for r in self.rows
                         if r.get("Registered Position") == pl["Registered Position"]), keys[0])
            c.setdefault("add", []).append(dict(pl, like=like))
        gone = keys[max(len(players), P.MIN_SQUAD):]
        if gone:
            c["remove"] = gone
        if not ed:
            c.pop("edits", None)
        self.project.dirty = True
        self.cur = None
        if new:
            self.fill_squad()                        # Build picks the best eleven of a new club
        else:
            self.set_orders(P.best_eleven([dict(m, player=k) for k, m, ch, g in self.view() if not g]))
        text = _("%d players imported.") % len(players)
        if warn:
            text += "\n\n" + "\n".join(warn[:12]) + ("\n..." if len(warn) > 12 else "")
        info(self, title, text)
