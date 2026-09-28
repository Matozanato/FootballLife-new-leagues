"""League Builder: new leagues, their clubs, the game's own leagues and clubs, and the build.

Every page edits app.project.recipe (modstudio/project.py); leaguebuilder.py does the work.
"""
import csv, io, os

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QImage, QColor, QBrush
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
                               QLabel, QLineEdit, QListWidget, QListWidgetItem, QPlainTextEdit,
                               QPushButton, QRadioButton, QSpinBox, QSplitter, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget, QFileDialog, QButtonGroup,
                               QMessageBox)

import leaguebuilder as B
from .. import theme
from ..i18n import _, tr
from ..backups import snapshot
from ..ui import Page, section, hint, row, ask, error, run_job

PICTURES = "Pictures (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;All files (*.*)"
ALL_CLUBS = -1


def pixmap(path, size):
    if not path:
        return None
    try:
        import lbassets
        im = lbassets.preview(path, size)
        buf = io.BytesIO()
        im.save(buf, "PNG")
        pm = QPixmap()
        pm.loadFromData(buf.getvalue(), "PNG")
        return pm
    except Exception:
        return None


def fmt_text(L):
    if L.get("split"):
        s = L["split"]
        return _("%dx, then %s %dx") % (s.get("legs", 2), "/".join(map(str, s["groups"])), s.get("group_legs", 1))
    return _("everyone %dx") % L.get("legs", 2)


class PictureField(QWidget):
    """a picture file: a preview, Pick and Clear"""

    def __init__(self, value=None, size=72, empty="(made for you)"):
        super().__init__()
        self.path, self.size, self.empty = value or None, size, empty
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        self.view = QLabel()
        self.view.setFixedSize(size + 8, size + 8)
        self.view.setAlignment(Qt.AlignCenter)
        self.view.setStyleSheet("border: 1px solid %s; background: %s;" % (theme.BORDER, theme.PANEL))
        h.addWidget(self.view)
        v = QVBoxLayout()
        b1 = QPushButton(_("Pick picture..."))
        b1.clicked.connect(self.pick)
        b2 = QPushButton(_("Clear"))
        b2.clicked.connect(self.clear)
        v.addWidget(b1)
        v.addWidget(b2)
        v.addStretch(1)
        h.addLayout(v)
        h.addStretch(1)
        self.show_it()

    def pick(self):
        p, _f = QFileDialog.getOpenFileName(self, _("Pick picture..."), os.path.dirname(self.path or ""), _(PICTURES))
        if p:
            self.path = os.path.normpath(p)
            self.show_it()

    def clear(self):
        self.path = None
        self.show_it()

    def show_it(self):
        pm = pixmap(self.path, self.size)
        if pm:
            self.view.setPixmap(pm)
        else:
            self.view.setPixmap(QPixmap())
            self.view.setText(_(self.empty) if not self.path else _("(not readable)"))
            self.view.setWordWrap(True)


class Dialog(QDialog):
    def __init__(self, parent, title):
        super().__init__(parent)
        self.setWindowTitle(_(title))
        self.form = QFormLayout()
        self.form.setLabelAlignment(Qt.AlignRight)
        self.v = QVBoxLayout(self)
        self.v.addLayout(self.form)

    def finish(self):
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText(_("OK"))
        bb.button(QDialogButtonBox.Cancel).setText(_("Cancel"))
        bb.accepted.connect(self.ok)
        bb.rejected.connect(self.reject)
        self.v.addWidget(bb)
        try:
            theme.dark_title_bar(self)
        except Exception:
            pass
        return self.exec() == QDialog.Accepted

    def ok(self):
        self.accept()


class LeagueDialog(Dialog):
    """one new league: name, country, clubs, format, division, logo"""

    def __init__(self, parent, project, league=None):
        super().__init__(parent, "League")
        self.project = project
        L = dict(league or {"clubs": 12, "legs": 2})
        self.league, self.orig = L, league
        self.name = QLineEdit(L.get("name", ""))
        self.form.addRow(_("Name"), self.name)
        self.country = QComboBox()
        self.country.setEditable(True)
        self.country.addItems(project.countries)
        self.country.setCurrentText(L.get("country", ""))
        self.country.setInsertPolicy(QComboBox.NoInsert)
        self.form.addRow(_("Country"), self.country)
        self.clubs = QSpinBox()
        self.clubs.setRange(B.CLUBS_MIN, B.CLUBS_MAX)
        self.clubs.setValue(L.get("clubs", 12))
        self.form.addRow(_("Clubs"), self.clubs)

        sp = L.get("split") or {}
        self.rr = QRadioButton(_("everyone plays everyone, times:"))
        self.split = QRadioButton(_("splits in two (Scottish style)"))
        g = QButtonGroup(self)
        g.addButton(self.rr)
        g.addButton(self.split)
        (self.split if sp else self.rr).setChecked(True)
        self.legs = QSpinBox()
        self.legs.setRange(1, B.LEGS_MAX)
        self.legs.setValue(L.get("legs", 2))
        self.form.addRow(_("Format"), row(self.rr, self.legs))
        self.slegs = QSpinBox()
        self.slegs.setRange(1, B.LEGS_MAX)
        self.slegs.setValue(sp.get("legs", 2))
        self.groups = QLineEdit("/".join(map(str, sp.get("groups", []))) or "6/6")
        self.groups.setFixedWidth(70)
        self.glegs = QSpinBox()
        self.glegs.setRange(1, B.LEGS_MAX)
        self.glegs.setValue(sp.get("group_legs", 2))
        self.form.addRow("", self.split)
        self.form.addRow("", row(QLabel(_("first")), self.slegs, QLabel(_("x, then groups")), self.groups,
                                 self.glegs, QLabel("x")))

        self.above = QComboBox()
        self.above.addItem(_("(top division)"), None)
        for x in project.recipe["leagues"]:
            if x is not league:
                self.above.addItem(x["name"], x["name"])
        for r, n in project.parents:
            self.above.addItem("%s  [%d]" % (n, r), r)
        cur = L.get("above")
        i = self.above.findData(int(cur) if isinstance(cur, str) and cur.isdigit() else cur)
        self.above.setCurrentIndex(max(0, i))
        self.form.addRow(_("Division"), self.above)
        self.exchange = QSpinBox()
        self.exchange.setRange(1, 6)
        self.exchange.setValue(L.get("exchange", 3))
        self.form.addRow(_("Up / down"), row(self.exchange, QLabel(_("clubs, with the league above"))))
        self.logo = PictureField(L.get("logo"))
        self.form.addRow(_("Logo"), self.logo)

    def ok(self):
        L = self.league
        L["name"] = self.name.text().strip()
        L["country"] = self.country.currentText().strip()
        L["clubs"] = self.clubs.value()
        if self.split.isChecked():
            try:
                groups = [int(x) for x in self.groups.text().replace(",", "/").split("/") if x.strip()]
            except ValueError:
                error(self, "League", _("Clubs, times and groups must be numbers."))
                return
            L["split"] = {"legs": self.slegs.value(), "groups": groups, "group_legs": self.glegs.value()}
            L["legs"] = self.slegs.value()
        else:
            L.pop("split", None)
            L["legs"] = self.legs.value()
        L["exchange"] = self.exchange.value()
        a = self.above.currentData()
        if a is None:
            L.pop("above", None)
        else:
            L["above"] = a
        if self.logo.path:
            L["logo"] = self.logo.path
        else:
            L.pop("logo", None)
        if not L["name"] or not L["country"]:
            error(self, "League", _("A league needs a name and a country."))
            return
        if L["country"] not in self.project.countries:
            error(self, "League", _("Pick the country from the list."))
            return
        clash = [x for x in self.project.recipe["leagues"] if x is not self.orig and x["name"].lower() == L["name"].lower()]
        if clash:
            error(self, "League", _("There is already a league called %s.") % L["name"])
            return
        self.accept()


class ClubDialog(Dialog):
    """one club: name, short name, crest -- a new club, or one of the game's"""

    def __init__(self, parent, name, short, crest, was=None):
        super().__init__(parent, "Club")
        self.name = QLineEdit(name or "")
        self.name.setMinimumWidth(280)
        self.form.addRow(_("Name"), self.name)
        self.short = QLineEdit(short or "")
        self.short.setMaxLength(3)
        self.short.setFixedWidth(60)
        self.form.addRow(_("Short name"), self.short)
        self.form.addRow("", hint(_("three letters, A-Z and 0-9; empty = made from the name")))
        self.crest = PictureField(crest)
        self.form.addRow(_("Crest"), self.crest)
        if was:
            self.form.addRow("", hint(_("In the game: %s (%s)") % was))
        self.result = None

    def ok(self):
        short = self.short.text().strip()
        if short and B.short_name(short) != short.upper():
            error(self, "Club", _("The short name takes letters A-Z and digits only."))
            return
        self.result = (self.name.text().strip(), B.short_name(short), self.crest.path)
        self.accept()


class PasteDialog(Dialog):
    def __init__(self, parent, lines):
        super().__init__(parent, "Paste club names")
        self.v.insertWidget(0, QLabel(_("One club per line, in order.")))
        self.text = QPlainTextEdit("\n".join(lines))
        self.text.setMinimumSize(360, 380)
        self.v.insertWidget(1, self.text)
        self.result = None

    def ok(self):
        r = [x.strip() for x in self.text.toPlainText().splitlines()]
        while r and not r[-1]:
            r.pop()
        self.result = r
        self.accept()


class BuilderPage(Page):
    """a League Builder page: a banner and a button when the game's tables are not there"""

    def __init__(self, app):
        super().__init__(app)
        self.project = app.project
        self.project.tables_changed.connect(self._tables)

    def need_tables(self):
        if self.project.base is None:
            self.say(_("The League Builder needs the game's tables: Settings > Unpack the game's tables "
                       "(once, and again after a game update)."), "warn")
            return True
        return False

    def _tables(self):
        if self.project.base is not None:
            self.say("")
        self.refresh()


class NewLeagues(BuilderPage):
    title = "New leagues"
    hint = ("Leagues to add to the game. Each gets its clubs at once, with full squads and a manager; "
            "name them on the New clubs page, change their players on the Players page, then Build.")

    def __init__(self, app):
        super().__init__(app)
        self.action("Add league", self.add, "primary")
        self.action("Edit", self.edit)
        self.action("Remove", self.remove, "danger")
        top = QHBoxLayout()
        top.addWidget(QLabel(_("World name")))
        self.world = QLineEdit()
        self.world.setFixedWidth(240)
        self.world.editingFinished.connect(self.set_world)
        top.addWidget(self.world)
        top.addWidget(hint(_("the folder your leagues are built into; it must start with _FL26")))
        top.addStretch(1)
        for text, d in (("Move up", -1), ("Move down", 1)):
            b = QPushButton(_(text))
            b.clicked.connect(lambda _c=False, d=d: self.move(d))
            top.addWidget(b)
        self.outer.addLayout(top)
        self.tree = QTreeWidget()
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setIconSize(QSize(28, 28))
        self.tree.setHeaderLabels([_("League"), _("Country"), _("Clubs"), _("Format"), _("Division"),
                                   _("Up / down"), _("Players changed")])
        for c, w in enumerate((240, 150, 60, 170, 230, 80)):
            self.tree.setColumnWidth(c, w)
        self.tree.itemDoubleClicked.connect(lambda *a: self.edit())
        self.outer.addWidget(self.tree, 1)
        self.foot = hint("")
        self.outer.addWidget(self.foot)
        self.project.changed.connect(self.refresh)

    def shown(self):
        self.need_tables()
        self.refresh()

    def set_world(self):
        w = self.world.text().strip()
        if w != self.project.recipe.get("world"):
            if not w.startswith("_FL26"):
                self.say(_("The world name must start with _FL26."), "err")
                self.world.setText(self.project.recipe.get("world", ""))
                return
            self.project.recipe["world"] = w
            self.project.touch()

    def refresh(self):
        r = self.project.recipe
        self.world.setText(r.get("world", ""))
        cur = self.selected()
        self.tree.clear()
        names = dict(self.project.parents)
        pl = self.project.players()
        for i, L in enumerate(r["leagues"]):
            up = L.get("above")
            div = _("top") if up in (None, "") else _("below %s") % (names.get(up, up) if isinstance(up, int) else up)
            n = sum(len((pl.get("%s/%d" % (L["name"], k)) or {}).get("edits") or {}) for k in range(L.get("clubs", 0)))
            it = QTreeWidgetItem([L["name"], L.get("country", ""), str(L.get("clubs", "")), fmt_text(L), div,
                                  str(L.get("exchange", 3)) if up not in (None, "") else "", str(n) if n else ""])
            pm = pixmap(L.get("logo"), 28)
            if pm:
                it.setIcon(0, pm)
            it.setData(0, Qt.UserRole, i)
            self.tree.addTopLevelItem(it)
        if cur is not None and cur < self.tree.topLevelItemCount():
            self.tree.setCurrentItem(self.tree.topLevelItem(cur))
        clubs = sum(L.get("clubs", 0) for L in r["leagues"])
        self.foot.setText(_("%d new leagues, %d new clubs.") % (len(r["leagues"]), clubs)
                          + ("   " + _("Recipe: %s") % self.project.path if self.project.path else ""))

    def selected(self):
        it = self.tree.currentItem()
        return it.data(0, Qt.UserRole) if it else None

    def add(self):
        if self.need_tables():
            return
        d = LeagueDialog(self, self.project)
        if d.finish():
            self.project.recipe["leagues"].append(d.league)
            self.project.touch()

    def edit(self):
        i = self.selected()
        if i is None:
            return
        L = self.project.recipe["leagues"][i]
        old, n_old = L["name"], L.get("clubs", 0)
        d = LeagueDialog(self, self.project, L)
        if d.finish():
            self.project.recipe["leagues"][i] = d.league
            self.project.rename_league(old, d.league["name"])
            if d.league["clubs"] < n_old:
                self.project.drop_league(d.league["name"], d.league["clubs"])
            self.project.touch()

    def remove(self):
        i = self.selected()
        if i is None:
            return
        name = self.project.recipe["leagues"][i]["name"]
        if ask(self, "Remove", _("Remove %s, with its clubs and their player changes?") % name):
            del self.project.recipe["leagues"][i]
            for L in self.project.recipe["leagues"]:
                if L.get("above") == name:
                    L.pop("above")
            self.project.drop_league(name)
            self.project.touch()

    def move(self, d):
        i = self.selected()
        L = self.project.recipe["leagues"]
        if i is None or not 0 <= i + d < len(L):
            return
        L[i], L[i + d] = L[i + d], L[i]
        self.project.touch()
        self.tree.setCurrentItem(self.tree.topLevelItem(i + d))

    # ---- recipe files (File menu) ----
    def open_recipe(self):
        if self.project.dirty and not ask(self, "Open recipe...", _("Unsaved changes are lost. Open anyway?")):
            return
        p, _f = QFileDialog.getOpenFileName(self, _("Open recipe..."), self.app.settings.get("recipes", ""),
                                            _("Recipe") + " (*.json)")
        if not p:
            return
        try:
            self.project.open(p)
        except (B.BuildError, ValueError, OSError) as e:
            error(self, "Open recipe...", str(e))
            return
        self.app.settings["recipes"] = os.path.dirname(p)
        self.app.open_page("NewLeagues")

    def save_recipe(self, ask_name=False):
        self.set_world()
        p = self.project.path
        if ask_name or not p:
            p, _f = QFileDialog.getSaveFileName(
                self, _("Save recipe as..."),
                os.path.join(self.app.settings.get("recipes", ""), self.project.recipe["world"] + ".json"),
                _("Recipe") + " (*.json)")
            if not p:
                return
        self.project.save(p)
        self.app.settings["recipes"] = os.path.dirname(p)
        self.app.status(_("Recipe saved: %s") % p)

    def new_recipe(self):
        if self.project.dirty and not ask(self, "New", _("Start a new recipe? Unsaved changes are lost.")):
            return
        self.project.new()


class NewClubs(BuilderPage):
    title = "New clubs"
    hint = ("The clubs of one new league. An empty name becomes \"<league> 01\", \"<league> 02\" ...; an "
            "empty short name is made from the name; a club with no crest gets a numbered badge.")

    def __init__(self, app):
        super().__init__(app)
        self.action("Edit club", self.edit, "primary")
        self.action("Players", self.players, tip="Change this club's squad")
        self.action("Paste names...", self.paste)
        self.action("Load names from file...", self.load_file)
        top = QHBoxLayout()
        top.addWidget(QLabel(_("League")))
        self.combo = QComboBox()
        self.combo.setMinimumWidth(260)
        self.combo.currentIndexChanged.connect(lambda *_a: self.show_clubs())
        top.addWidget(self.combo)
        top.addStretch(1)
        self.outer.addLayout(top)
        self.tree = QTreeWidget()
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setIconSize(QSize(28, 28))
        self.tree.setHeaderLabels(["#", _("Name"), _("Short name"), _("Crest"), _("Players changed")])
        for c, w in enumerate((40, 320, 90, 260)):
            self.tree.setColumnWidth(c, w)
        self.tree.itemDoubleClicked.connect(lambda *a: self.edit())
        self.outer.addWidget(self.tree, 1)
        self.project.changed.connect(self.refresh)

    def shown(self):
        self.need_tables()
        self.refresh()

    def refresh(self):
        names = [L["name"] for L in self.project.recipe["leagues"]]
        cur = self.combo.currentText()
        self.combo.blockSignals(True)
        self.combo.clear()
        self.combo.addItems(names)
        if cur in names:
            self.combo.setCurrentText(cur)
        self.combo.blockSignals(False)
        self.show_clubs()
        if not names:
            self.say(_("No new leagues yet: add one on the New leagues page."), "warn")
        elif self.project.base is not None:
            self.say("")

    def league(self):
        return self.project.league(self.combo.currentText())

    @staticmethod
    def lists(L):
        n = L.get("clubs", 0)
        for k in ("club_names", "club_abbrs", "club_crests"):
            v = list(L.get(k) or [])[:n]
            L[k] = v + [None if k == "club_crests" else ""] * (n - len(v))
        return L["club_names"], L["club_abbrs"], L["club_crests"]

    def show_clubs(self):
        cur = self.tree.currentItem()
        cur = cur.data(0, Qt.UserRole) if cur else None
        self.tree.clear()
        L = self.league()
        if not L:
            return
        names, abbrs, crests = self.lists(L)
        pl = self.project.players()
        for k in range(L["clubs"]):
            n = len((pl.get("%s/%d" % (L["name"], k)) or {}).get("edits") or {})
            it = QTreeWidgetItem([str(k + 1), names[k] or "%s %02d" % (L["name"], k + 1), abbrs[k] or "",
                                  os.path.basename(crests[k]) if crests[k] else "", str(n) if n else ""])
            if not names[k]:
                it.setForeground(1, QBrush(QColor(theme.SUBTLE)))
            pm = pixmap(crests[k], 28)
            if pm:
                it.setIcon(1, pm)
            it.setData(0, Qt.UserRole, k)
            self.tree.addTopLevelItem(it)
            if k == cur:
                self.tree.setCurrentItem(it)

    def current(self):
        it = self.tree.currentItem()
        return it.data(0, Qt.UserRole) if it else None

    def edit(self):
        L, k = self.league(), self.current()
        if not L or k is None:
            return
        names, abbrs, crests = self.lists(L)
        d = ClubDialog(self, names[k], abbrs[k], crests[k])
        if d.finish() and d.result:
            names[k], abbrs[k], crests[k] = d.result
            self.project.touch()

    def players(self):
        L, k = self.league(), self.current()
        if L and k is not None:
            self.app.page("Players").show_club("%s/%d" % (L["name"], k))
            self.app.open_page("Players")

    def set_names(self, rows):
        L = self.league()
        if not L:
            return
        names = self.lists(L)[0]
        given = [r for r in rows if r]
        if len(given) > L["clubs"]:
            QMessageBox.warning(self, _("New clubs"), _("%d names for %d clubs: the rest are left out.")
                                % (len(given), L["clubs"]))
        for k in range(L["clubs"]):
            names[k] = rows[k] if k < len(rows) else ""
        self.project.touch()

    def paste(self):
        L = self.league()
        if L:
            d = PasteDialog(self, list(self.lists(L)[0]))
            if d.finish() and d.result is not None:
                self.set_names(d.result)

    def load_file(self):
        p, _f = QFileDialog.getOpenFileName(self, _("Load names from file..."), "",
                                            _("Club list") + " (*.txt *.csv);;" + _("All files") + " (*.*)")
        if p:
            with open(p, encoding="utf-8-sig", errors="replace") as fh:
                self.set_names([r[0].strip() for r in csv.reader(fh) if r and r[0].strip()])


class GameLeagues(BuilderPage):
    title = "Game's leagues and clubs"
    hint = ("The leagues and clubs the game already has: new names, logos and crests. Changes are written "
            "into your world, so they show while the world is switched on. A saved Edit file (EDIT00000000) "
            "in the game's save folder overrides club names: move it away to see them.")

    def __init__(self, app):
        super().__init__(app)
        split = QSplitter(Qt.Horizontal)
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 8, 0)
        self.search = QLineEdit()
        self.search.setPlaceholderText(_("Find a league or club..."))
        self.search.textChanged.connect(self.fill)
        lv.addWidget(self.search)
        self.list = QListWidget()
        self.list.currentRowChanged.connect(lambda *_a: self.show_league())
        lv.addWidget(self.list, 1)
        split.addWidget(left)

        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(8, 0, 0, 0)
        rv.addWidget(section("League"))
        f = QFormLayout()
        self.lname = QLineEdit()
        f.addRow(_("Name"), self.lname)
        self.lwas = hint("")
        f.addRow("", self.lwas)
        self.logo_box = QHBoxLayout()
        self.logo = None
        f.addRow(_("Logo"), self.logo_box)
        rv.addLayout(f)
        self.b_keep = QPushButton(_("Keep league changes"))
        self.b_keep.setObjectName("primary")
        self.b_keep.clicked.connect(self.keep_league)
        self.b_undo = QPushButton(_("Undo league changes"))
        self.b_undo.clicked.connect(self.undo_league)
        rv.addWidget(row(self.b_keep, self.b_undo))
        rv.addSpacing(6)
        rv.addWidget(section("Clubs"))
        self.tree = QTreeWidget()
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setIconSize(QSize(24, 24))
        self.tree.setHeaderLabels([_("Club id"), _("Name"), _("Short name"), _("Crest"), _("Changed")])
        for c, w in enumerate((70, 260, 80, 180, 80)):
            self.tree.setColumnWidth(c, w)
        self.tree.itemDoubleClicked.connect(lambda *a: self.edit_club())
        rv.addWidget(self.tree, 1)
        b1 = QPushButton(_("Edit club"))
        b1.clicked.connect(self.edit_club)
        b2 = QPushButton(_("Players"))
        b2.clicked.connect(self.players)
        b3 = QPushButton(_("Undo club changes"))
        b3.clicked.connect(self.undo_club)
        rv.addWidget(row(b1, b2, b3))
        split.addWidget(right)
        split.setSizes([300, 900])
        self.outer.addWidget(split, 1)
        self.shown_rows = []
        self.project.changed.connect(self.fill)

    def shown(self):
        self.need_tables()
        self.fill()

    def refresh(self):
        self.fill()

    def fill(self):
        q = self.search.text().strip().lower()
        cur = self.list.currentRow()
        self.list.blockSignals(True)
        self.list.clear()
        P = self.project
        self.shown_rows = [(ALL_CLUBS, None, _("(all clubs)"), sorted(P.game_cl))] + list(P.game_lgs)
        if q:
            self.shown_rows = [x for x in self.shown_rows if x[0] == ALL_CLUBS or q in x[2].lower()]
        changed = P.edits("leagues")
        for rid, cid, name, teams in self.shown_rows:
            e = changed.get(str(rid), {})
            label = name if rid == ALL_CLUBS else "%s  (%d)" % (e.get("name", name), len(teams))
            it = QListWidgetItem(label + ("  *" if e else ""))
            self.list.addItem(it)
        self.list.blockSignals(False)
        self.list.setCurrentRow(cur if 0 <= cur < self.list.count() else 0)
        self.show_league()

    def current_league(self):
        i = self.list.currentRow()
        return self.shown_rows[i] if 0 <= i < len(self.shown_rows) else None

    def show_league(self):
        g = self.current_league()
        self.tree.clear()
        if self.logo:
            self.logo.setParent(None)
            self.logo = None
        if not g:
            return
        rid, cid, name, teams = g
        league = rid != ALL_CLUBS
        e = self.project.edits("leagues").get(str(rid), {})
        self.lname.setText(e.get("name", name) if league else "")
        self.lname.setEnabled(league)
        self.b_keep.setEnabled(league)
        self.b_undo.setEnabled(league)
        self.lwas.setText((_("In the game: %s") % name) if league else "")
        if league:
            self.logo = PictureField(e.get("logo"), 64, "(the game's own)")
            self.logo_box.addWidget(self.logo)
        q = self.search.text().strip().lower()
        cl = self.project.game_cl
        for tid in teams:
            if tid not in cl:
                continue
            if rid == ALL_CLUBS and q and q not in cl[tid][0].lower():
                continue
            it = QTreeWidgetItem()
            it.setData(0, Qt.UserRole, tid)
            self.club_row(it, tid)
            self.tree.addTopLevelItem(it)

    def club_row(self, it, tid):
        n, a = self.project.game_cl[tid]
        e = self.project.edits("clubs").get(str(tid), {})
        np = self.project.players().get(str(tid)) or {}
        k = len(np.get("edits") or {}) + len(np.get("add") or []) + len(np.get("remove") or [])
        marks = ([_("name/crest")] if e else []) + ([_("%d players") % k] if k else [])
        vals = [str(tid), e.get("name") or n, e.get("abbr") or a,
                os.path.basename(e["crest"]) if e.get("crest") else "", ", ".join(marks)]
        for c, v in enumerate(vals):
            it.setText(c, v)
        pm = pixmap(e.get("crest"), 24)
        it.setIcon(1, pm if pm else QPixmap())

    def keep_league(self):
        g = self.current_league()
        if not g or g[0] == ALL_CLUBS:
            return
        rid, cid, name, teams = g
        e = {}
        if self.lname.text().strip() and self.lname.text().strip() != name:
            e["name"] = self.lname.text().strip()
        if self.logo and self.logo.path:
            e["logo"] = self.logo.path
        if e:
            self.project.edits("leagues")[str(rid)] = e
        else:
            self.project.edits("leagues").pop(str(rid), None)
        self.project.touch()

    def undo_league(self):
        g = self.current_league()
        if g and g[0] != ALL_CLUBS:
            self.project.edits("leagues").pop(str(g[0]), None)
            self.project.touch()

    def selected_tid(self):
        it = self.tree.currentItem()
        return (it.data(0, Qt.UserRole), it) if it else (None, None)

    def edit_club(self):
        tid, it = self.selected_tid()
        if tid is None:
            return
        n, a = self.project.game_cl[tid]
        e = self.project.edits("clubs").get(str(tid), {})
        d = ClubDialog(self, e.get("name") or n, e.get("abbr") or a, e.get("crest"), was=(n, a))
        if not (d.finish() and d.result):
            return
        name, short, crest = d.result
        e = {}
        if name and name != n:
            e["name"] = name
        if short and short != a:
            e["abbr"] = short
        if crest:
            e["crest"] = crest
        if e:
            self.project.edits("clubs")[str(tid)] = e
        else:
            self.project.edits("clubs").pop(str(tid), None)
        self.club_row(it, tid)
        self.project.dirty = True

    def undo_club(self):
        for it in self.tree.selectedItems():
            tid = it.data(0, Qt.UserRole)
            self.project.edits("clubs").pop(str(tid), None)
            self.club_row(it, tid)
        self.project.dirty = True

    def players(self):
        tid, it = self.selected_tid()
        if tid is not None:
            self.app.page("Players").show_club(str(tid))
            self.app.open_page("Players")


class Build(BuilderPage):
    title = "Build"
    hint = ("Turn the recipe into a world: 1. check the plan, 2. build it into SiderAddons\\livecpk, "
            "3. switch it on in sider.ini, then start the game and 4. check sider.log. "
            "The builder's modules are installed once (0), and again after a new version of the program.")

    def __init__(self, app):
        super().__init__(app)
        self.steps = []
        bar = QHBoxLayout()
        for text, fn, kind in (("0. Install the modules", self.do_install, None),
                               ("1. Check the plan", self.do_plan, None),
                               ("2. Build the world", self.do_build, "primary"),
                               ("3. Switch it on", self.do_on, None),
                               ("4. After a start: check", self.do_check, None)):
            b = QPushButton(_(text))
            if kind:
                b.setObjectName(kind)
            b.clicked.connect(fn)
            bar.addWidget(b)
            self.steps.append(b)
        bar.addStretch(1)
        self.outer.addLayout(bar)
        self.state = hint("")
        self.outer.addWidget(self.state)
        self.out = QPlainTextEdit()
        self.out.setObjectName("log")
        self.out.setReadOnly(True)
        self.outer.addWidget(self.out, 1)

    def shown(self):
        self.need_tables()
        self.refresh()

    def refresh(self):
        g = self.app.game
        w = self.project.recipe.get("world", "")
        built = os.path.exists(os.path.join(g.livecpk_dir, w)) if g.ok() else False
        missing = B.modules_missing(g.folder) if g.ok() else []
        bits = [_("World %s: %s") % (w, _("built") if built else _("not built yet"))]
        if g.ok():
            bits.append(_("builder modules: %s") % (_("installed") if not missing else
                                                     _("%d missing, press 0") % len(missing)))
        self.state.setText("   ·   ".join(bits))

    def say(self, text, kind=None):
        if kind is not None:
            return super().say(text, kind)
        self.out.appendPlainText(tr(str(text)))

    def plan(self):
        self.app.page("NewLeagues").set_world()
        r = self.project.recipe
        if self.project.base is None:
            raise B.BuildError(_("no game tables -- Settings > Unpack the game's tables"))
        if not self.app.game.ok():
            raise B.BuildError(_("no game folder -- Game > Choose the game folder"))
        if not r["world"].startswith("_FL26"):
            raise B.BuildError(_("the world name must start with _FL26"))
        if not r["leagues"] and not B.has_edits(r):
            raise B.BuildError(_("nothing to build: add a league or change one of the game's"))
        return B.plan(r, self.project.base)

    def run(self, what, background=False, done=None):
        self.out.clear()
        if not background:
            try:
                what(self.say)
            except B.BuildError as e:
                self.say(_("error: %s") % tr(str(e)))
            except Exception:
                import traceback
                self.say(_("unexpected error:") + "\n" + traceback.format_exc())
            self.refresh()
            return
        for b in self.steps:
            b.setEnabled(False)
        self.app.busy(True, _("Building..."))

        def finish(result=None, err=None):
            self.app.busy(False)
            for b in self.steps:
                b.setEnabled(True)
            if err:
                self.say(err)
            self.refresh()
            self.app.bus.content_changed.emit()
            if done and not err:
                done()

        def job(progress):
            try:
                what(lambda t: progress(t))
            except B.BuildError as e:
                return _("error: %s") % tr(str(e))
            return None
        run_job(job, done=lambda r: finish(err=r), failed=lambda tb: finish(err=_("unexpected error:") + "\n" + tb),
                progress=self.say)

    def do_plan(self):
        self.run(lambda log: log(B.describe(self.plan())))

    def do_build(self):
        try:
            pl = self.plan()
        except B.BuildError as e:
            self.out.clear()
            self.say(_("error: %s") % tr(str(e)))
            return
        game = self.app.game.folder
        out = os.path.join(self.app.game.livecpk_dir, pl["world"])
        replace = False
        if os.path.exists(out):
            if not ask(self, "Build", _("%s exists. Build it again?") % pl["world"]):
                return
            replace = True
        base = self.project.base

        def go(log):
            log(B.describe(pl))
            log(_("building ..."))
            B.build(pl, base, game, replace, log=log)
            log("\n" + _("Next: 3. Switch it on, then start the game."))
        self.run(go, background=True)

    def do_on(self):
        w = self.project.recipe.get("world", "").strip()
        if ask(self, "Switch on", _("Make %s the live world in sider.ini?") % w):
            def go(log):
                snapshot(self.app.game.ini_path, "League Builder: switch on " + w, self.app.game.sider_dir)
                B.switch_on(w, self.app.game.folder, log=log)
                log("\n" + _("Start the game, then 4. check."))
            self.run(go)
            self.app.bus.ini_changed.emit()

    def do_install(self):
        if ask(self, "Install the modules",
               _("Copy the league builder's modules into %s and load them from sider.ini? "
                 "Files it replaces are kept in a before-builder folder next to them.") % self.app.game.modules_dir):
            def go(log):
                snapshot(self.app.game.ini_path, "League Builder: install the modules", self.app.game.sider_dir)
                B.install_modules(self.app.game.folder, log=log)
                log("\n" + _("Done. This is needed once, and again after a new version of the program."))
            self.run(go)
            self.app.bus.ini_changed.emit()

    def do_check(self):
        self.run(lambda log: B.check(self.app.game.folder, log=log))
