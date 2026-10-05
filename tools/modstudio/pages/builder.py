"""League Builder: new leagues, their clubs, the game's own leagues and clubs, and the build.

Every page edits app.project.recipe (modstudio/project.py); leaguebuilder.py does the work.
"""
import csv, io, json, os

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QImage, QColor, QBrush, QKeySequence, QShortcut
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QFrame,
                               QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QPlainTextEdit, QPushButton, QRadioButton, QSpinBox, QSplitter,
                               QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
                               QFileDialog, QButtonGroup, QHeaderView, QAbstractItemView,
                               QMessageBox, QScrollArea, QApplication, QCompleter, QToolButton, QMenu,
                               QColorDialog)

import leaguebuilder as B
import lbplayers
import lbstadiums
import fl26world
import uefakey
from .. import theme
from .. import servers as S
from .. import newlife as N
from ..i18n import _, tr
from ..backups import snapshot
from ..ui import Page, section, hint, row, ask, error, info, run_job, helpmark, helped

EURO_WORLD = "_FL26Euro"


def database_note(project):
    """a warning for the build log when a database mod's tables are switched on but the world is
    built from the game's plain ones (#36): the world's copy of the tables would hide the mod's"""
    mods = project.other_databases()
    if not mods:
        return ""
    return _("CAREFUL: %s has its own database tables, but this world is built from the game's plain ones "
             "(Settings). The world carries a copy of the tables and sits above it in sider.ini, so the "
             "leagues and clubs of %s would go back to the plain game's. To keep them, point Settings > "
             "game tables to its common\\etc\\pesdb folder and build again.") % (", ".join(mods), ", ".join(mods))


def exhibition_note(pl):
    """a warning for the build log when the world has exhibition leagues: the game's team list
    for a new Master League career is the one Kick Off uses, so their clubs are in it"""
    ex = [p["name"] for p in pl["leagues"] if p.get("exhibition")]
    if not ex:
        return ""
    return _("CAREFUL: %s is for exhibition matches only, but its clubs still show in the team list when you "
             "start a Master League career (the game has one list for both). Do not pick one of them: their "
             "league never plays a season.") % ", ".join(ex)           # the world "Only the new European cups" builds (#36)
PICTURES = "Pictures (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;All files (*.*)"
ALL_CLUBS = -1
# the European competitions a league place can lead to (fl26world.COMPETITIONS), short names for
# the league list
SHORT = {0: "UCL", 1: "UEL", 2: "UECL", 3: "LIB", 4: "LIB-Q", 5: "AFC", 6: "CAF CL", 7: "CAF CC",
         8: "AFC CL2", 9: "SUD", 10: "UCL-Q", 11: "UEL-Q", 12: "UECL-Q"}
TOP_FLIGHT = [[1, 10], [2, 1], [3, 2]]     # the preset: 1st UCL qualifying, 2nd UEL, 3rd UECL
# the preset by the country's confederation (Country.bin): Asia to the AFC Champions League and
# Champions League Two, South America to the Libertadores and the Sudamericana, Africa to the CAF
# Champions League and Confederation Cup; everyone else keeps the European one
PRESETS = {
    3: ("Top flight: 1st and 2nd AFC Champions League, 3rd AFC CL Two",
        "1st and 2nd to the AFC Champions League, 3rd to the AFC Champions League Two",
        [[1, 5], [2, 5], [3, 8]]),
    # the qualifying round has no pool club: a place of ours there takes a shipped club's
    # (fl26swiss cont_standins, issue #33)
    4: ("Top flight: 1st-3rd Libertadores, 4th qualifying, 5th-6th Sudamericana",
        "1st to 3rd to the Copa Libertadores, 4th to its qualifying rounds, 5th and 6th to the Copa Sudamericana",
        [[1, 3], [2, 3], [3, 3], [4, 4], [5, 9], [6, 9]]),
    5: ("Top flight: 1st and 2nd CAF Champions League, 3rd Confederation Cup",
        "1st and 2nd to the CAF Champions League, 3rd to the CAF Confederation Cup",
        [[1, 6], [2, 6], [3, 7]]),
}
UEFA_PRESET = ("Top flight: 1st UCL qualifying, 2nd UEL, 3rd UECL",
               "1st to the Champions League qualifying, its August play-off (the winner plays the Champions "
               "League, the loser the Europa League), 2nd to the Europa League, 3rd to the Conference League",
               TOP_FLIGHT)


def pixmap(path, size, kit=None):
    """a small picture of `path`; with no path, the shield a NewLife club's shirt (`kit`) gives"""
    if not path and not kit:
        return None
    try:
        if path:
            import lbassets
            im = lbassets.preview(path, size)
        else:
            import shieldcrest
            im = shieldcrest.shield(kit, "", size * 2)
            if im is None:
                return None
            im = im.resize((size, size))
        buf = io.BytesIO()
        im.save(buf, "PNG")
        pm = QPixmap()
        pm.loadFromData(buf.getvalue(), "PNG")
        return pm
    except Exception:
        return None


def europe_text(L):
    return ", ".join((_("cup winner") if int(pos) == B.CUP_WINNER else str(pos)) + " " + SHORT.get(comp, comp)
                     for pos, comp in sorted(L.get("europe") or [], key=lambda e: (int(e[0]) == B.CUP_WINNER, e[0])))


def built_plan(g, world):
    """the world folder's leaguebuilder-plan.json, what the last Build made; None before the first"""
    if not world or not g.ok():
        return None
    try:
        with open(os.path.join(g.livecpk_dir, world, "leaguebuilder-plan.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def built_league(g, world, name, built=None):
    """what the last Build gave a league: its ids (cid, rid) and its clubs' team ids (teams);
    {} before the first Build, and for a league added or renamed since"""
    built = built if built is not None else built_plan(g, world)
    for p in (built or {}).get("leagues") or []:
        if p.get("name") == name:
            return p
    return {}


def fmt_text(L):
    if L.get("apertura"):
        return _("Apertura + Clausura")
    if L.get("split"):
        s = L["split"]
        return _("%dx, then %s %dx") % (s.get("legs", 2), "/".join(map(str, s["groups"])), s.get("group_legs", 1))
    return _("everyone %dx") % L.get("legs", 2)


class PictureField(QWidget):
    """a picture file: a preview, Pick and Clear"""

    def __init__(self, value=None, size=72, empty="(made for you)"):
        super().__init__()
        self.path, self.size, self.empty = value or None, size, empty
        self.changed = None                   # called after Pick or Clear
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
            if self.changed:
                self.changed()

    def clear(self):
        self.path = None
        self.show_it()
        if self.changed:
            self.changed()

    def show_it(self):
        pm = pixmap(self.path, self.size)
        if pm:
            self.view.setPixmap(pm)
        else:
            self.view.setPixmap(QPixmap())
            self.view.setText(_(self.empty) if not self.path else
                              _("(not readable)") if os.path.exists(self.path) else _("(file moved or deleted)"))
            self.view.setToolTip(self.path or "")
            self.view.setWordWrap(True)


class EuropeTable(QWidget):
    """a league's European places: league position -> competition, one row each, with a button
    that removes the row. tall: the table takes the height it is given (a dialog of its own)"""

    def __init__(self, places, clubs, tall=False):
        super().__init__()
        self.clubs = clubs
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels([_("League position"), _("Competition"), ""])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Fixed)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 170)
        self.table.setColumnWidth(2, 44)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setShowGrid(False)
        if tall:
            self.table.setMinimumHeight(240)
        else:
            self.table.setMinimumHeight(170)
            self.table.setMaximumHeight(250)
        v.addWidget(self.table, 1)
        self.preset = QPushButton()
        self.preset_places = TOP_FLIGHT
        self.set_confed(None)
        self.preset.clicked.connect(lambda: self.set_places(self.preset_places))
        add = QPushButton(_("Add place"))
        add.clicked.connect(self.add)
        clr = QPushButton(_("Clear"))
        clr.clicked.connect(lambda: self.set_places([]))
        v.addWidget(row(add, self.preset, "stretch", clr, stretch=False))
        self.set_places(places or [])

    def _row(self, pos, comp):
        r = self.table.rowCount()
        self.table.insertRow(r)
        sp = QSpinBox()
        sp.setRange(B.CUP_WINNER, max(self.clubs, 1))
        sp.setSpecialValueText(_("Cup winner"))
        sp.setToolTip(_("The league position, or Cup winner (below 1): the winner of the country's cup. "
                        "When the winner already has a European place through the league, the place "
                        "goes to the league's next club."))
        sp.setValue(min(max(int(pos), B.CUP_WINNER), max(self.clubs, 1)))
        cb = QComboBox()
        for c, name in fl26world.COMPETITIONS:
            cb.addItem(_(name), c)
        cb.setCurrentIndex(max(0, cb.findData(int(comp))))
        x = QPushButton("✕")
        x.setToolTip(_("Remove this place"))
        x.setFixedWidth(34)
        x.clicked.connect(lambda _c=False, b=x: self.remove_row(b))
        self.table.setCellWidget(r, 0, sp)
        self.table.setCellWidget(r, 1, cb)
        self.table.setCellWidget(r, 2, x)

    def remove_row(self, button):
        for r in range(self.table.rowCount()):
            if self.table.cellWidget(r, 2) is button:
                self.table.removeRow(r)
                return

    def set_places(self, places):
        self.table.setRowCount(0)
        # by position, the cup winner's place last
        for pos, comp in sorted(places, key=lambda e: (int(e[0]) == B.CUP_WINNER, int(e[0]))):
            self._row(pos, comp)

    def add(self):
        taken = {p for p, _c in self.places()}
        pos = next((k for k in range(1, self.clubs + 1) if k not in taken), 1)
        self._row(pos, 1 if pos > 1 else 0)

    def remove(self):
        rows = sorted({i.row() for i in self.table.selectionModel().selectedRows()}, reverse=True)
        if not rows and self.table.rowCount():
            rows = [self.table.currentRow() if self.table.currentRow() >= 0 else self.table.rowCount() - 1]
        for r in rows:
            self.table.removeRow(r)

    def set_clubs(self, n):
        """the league's club count changed: positions go up to it"""
        self.clubs = n
        for r in range(self.table.rowCount()):
            self.table.cellWidget(r, 0).setMaximum(max(n, 1))

    def set_confed(self, conf):
        """the country changed: the preset follows its confederation"""
        label, tip, self.preset_places = PRESETS.get(conf, UEFA_PRESET)
        self.preset.setText(_(label))
        self.preset.setToolTip(_(tip))

    def set_top(self, top):
        self.preset.setEnabled(top)

    def places(self):
        return [[self.table.cellWidget(r, 0).value(), self.table.cellWidget(r, 1).currentData()]
                for r in range(self.table.rowCount())]


class Dialog(QDialog):
    help = ""          # English; a "?" left of the OK button says what the dialog is for

    def __init__(self, parent, title):
        super().__init__(parent)
        self.title_en = title
        self.setWindowTitle(_(title))
        # The form scrolls: the League dialog is taller than a 768-line screen, or a 1080 one at
        # 125 % scaling, and a dialog Qt cannot fit is placed with its top above the screen --
        # Name and Country out of reach, no scroll wheel (Alikhaled_727, 0.1.3).
        self.body = QWidget()
        self.form = QFormLayout(self.body)
        self.form.setLabelAlignment(Qt.AlignRight)
        self.form.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.scroll.setWidget(self.body)
        self.v = QVBoxLayout(self)
        self.v.addWidget(self.scroll, 1)

    def fit(self):
        """size the dialog to its form, but never taller or wider than the screen it opens on"""
        if self.form.rowCount() == 0:
            self.scroll.hide()
            return
        screen = self.screen() or QApplication.primaryScreen()
        room = screen.availableGeometry()
        want = self.body.sizeHint()
        bar = self.scroll.verticalScrollBar().sizeHint().width()
        other = self.sizeHint().height() - self.scroll.sizeHint().height()
        h = min(want.height() + other + 4, int(room.height() * 0.9))
        w = min(max(self.sizeHint().width(), want.width() + bar + 24), int(room.width() * 0.95))
        self.resize(w, h)
        if self.parentWidget():
            c = self.parentWidget().window().frameGeometry().center()
        else:
            c = room.center()
        x = max(room.left(), min(c.x() - w // 2, room.right() - w))
        y = max(room.top() + 30, min(c.y() - h // 2, room.bottom() - h))
        self.move(x, y)

    def finish(self):
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText(_("OK"))
        bb.button(QDialogButtonBox.Cancel).setText(_("Cancel"))
        bb.accepted.connect(self.ok)
        bb.rejected.connect(self.reject)
        self.add_buttons(bb)
        self.fit()
        try:
            theme.dark_title_bar(self)
        except Exception:
            pass
        return self.exec() == QDialog.Accepted

    def add_buttons(self, bb):
        if self.help:
            self.v.addWidget(row(helpmark(self.help, self.title_en), "stretch", bb, stretch=False))
        else:
            self.v.addWidget(bb)

    def ok(self):
        self.accept()


def tier_of(project, up, seen=()):
    """the division a league below `up` becomes: 1 at the top, the game's own leagues by
    their rank field, new ones by following their chain up"""
    if up in (None, ""):
        return 1
    if isinstance(up, int):
        t = project.parent_tiers.get(up)
        return t + 1 if t else None
    if up in seen:
        return None
    for x in project.recipe["leagues"]:
        if x["name"] == up:
            t = tier_of(project, x.get("above"), seen + (up,))
            return t + 1 if t else None
    return None


class LeagueDialog(Dialog):
    """one new league: name, country, clubs, format, division, logo"""
    help = ("Everything about one new league:\n"
            "- Clubs: how many. They are made for you, with full squads and a manager.\n"
            "- Format: everyone plays everyone 1 or more times; or a Scottish split (after the first rounds "
            "the table splits into a top and a bottom group); or Apertura and Clausura (two short tournaments "
            "a season, then playoffs).\n"
            "- Division: the league one level up. (top division) = the best league of its country. Up / down "
            "is how many clubs go up and down between the two.\n"
            "- Season: August to May, or February to December like Brazil or Japan.\n"
            "- Cup, Super cup, League cup: the country's cups, for a top division only.\n"
            "- Formation: how the league's clubs line up.\n"
            "- Europe: which table positions go to which continental competition (top division only).")

    def __init__(self, parent, project, league=None, title="League", new=None):
        super().__init__(parent, title)
        self.project = project
        L = dict(league or new or {"clubs": 12, "legs": 2})
        self.league, self.orig = L, league
        self.name = QLineEdit(L.get("name", ""))
        self.form.addRow(_("Name"), self.name)
        self.country = QComboBox()
        self.country.setEditable(True)
        for label, _n in B.country_choices(project.countries):
            self.country.addItem(label)
        self.country.setCurrentText(L.get("country", ""))
        self.country.setInsertPolicy(QComboBox.NoInsert)
        self.country.completer().setFilterMode(Qt.MatchContains)      # "korea" finds both
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
        self.ap = QRadioButton(_("Apertura and Clausura, then playoffs of:"))
        g.addButton(self.ap)
        (self.ap if L.get("apertura") else self.split if sp else self.rr).setChecked(True)
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
        self.po = QComboBox()
        for n, t in ((8, _("8 clubs")), (4, _("4 clubs")), (0, _("no playoffs"))):
            self.po.addItem(t, n)
        ap = L.get("apertura")
        self.po.setCurrentIndex(max(0, self.po.findData(int(ap.get("playoff", 8)) if isinstance(ap, dict) else 8)))
        self.form.addRow("", row(self.ap, self.po))
        self.form.addRow("", hint(_("two tournaments a season, September to early January and January to May, "
                                    "everyone meeting once in each and starting from zero points; the whole "
                                    "season's table decides promotion and relegation. 18 clubs at most")))

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
        self.tier_lab = QLabel("")
        self.form.addRow(_("Division"), row(self.above, self.tier_lab))
        self.form.addRow("", hint(_("the league one division up: one of the game's, or one of your new leagues "
                                    "(they are at the top of the list -- add the higher one first)")))
        self.above.currentIndexChanged.connect(lambda _i: self.show_tier())
        self.show_tier()
        self.exhibition = QCheckBox(_("Exhibition only -- not in Master League"))
        self.exhibition.setChecked(bool(L.get("exhibition")))
        self.form.addRow("", helped(self.exhibition, "On: the league is only for Kick Off and exhibition matches "
                                    "(legends, a historic season ...). Its clubs never play a Master League "
                                    "season, so it has no division above or below, no cups and no European "
                                    "places."))
        self.form.addRow("", hint(_("for Kick Off and exhibition matches: a historical league, legends ... Its "
                                    "clubs never play a Master League season. It stands alone: no division "
                                    "above or below, no European places, no cups")))
        self.season = QComboBox()
        for k, t in (("august", _("August to May")), ("calendar", _("February to December"))):
            self.season.addItem(t, k)
        self.season.setCurrentIndex(max(0, self.season.findData(str(L.get("season") or "august"))))
        self.form.addRow(_("Season"), self.season)
        self.form.addRow("", hint(_("a top division of a new country: February to December plays like Brazil, Japan or "
                                    "Saudi Arabia, clubs going up and down at New Year; the divisions "
                                    "below it follow it. Not with a split, Apertura/Clausura or the "
                                    "country's cups yet")))
        self.form.addRow("", hint(_("Careful: the game has one team list for Kick Off and Master League, so its "
                                    "clubs still show when you pick your club for a new career. Do not start a "
                                    "career with one: its league never plays.")))
        self.exchange = QSpinBox()
        self.exchange.setRange(1, 6)
        self.exchange.setValue(L.get("exchange", 3))
        self.form.addRow(_("Up / down"), row(self.exchange, QLabel(_("clubs, with the league above"))))
        self.logo = PictureField(L.get("logo"))
        self.form.addRow(_("Logo"), self.logo)
        self.flag = PictureField(L.get("flag"), 72, "(the game's own)")
        self.flag.setToolTip(_("Your own picture of the country's flag. It replaces the game's flag of that "
                               "country everywhere (Select Team, players' nationality) while the world is on; "
                               "leave it empty to keep the game's own."))
        self.form.addRow(_("Country flag"), self.flag)
        self.cup = QCheckBox(_("National cup"))
        self.cup.setChecked(bool(L.get("cup")))
        self.cup_name = QLineEdit(L.get("cup_name", ""))
        self.cup_name.setPlaceholderText(_("(the league's name + Cup)"))
        self.form.addRow(_("Cup"), row(self.cup, self.cup_name, helpmark(
            "A knockout cup like the FA Cup for the clubs of this league and the division below it, from "
            "September to May. Any number of clubs works: when the field is not 16, 32 ..., some clubs get a "
            "bye into the next round. Top division only. Empty name = the league's name + Cup.")))
        self.supercup = QCheckBox(_("Super cup (champion v cup winner)"))
        self.supercup.setChecked(bool(L.get("supercup")))
        self.form.addRow("", helped(self.supercup, "One match in late July: the league champion against the "
                                    "cup winner. It needs the national cup."))
        self.cup.toggled.connect(lambda on: self.supercup.setEnabled(on and self.cup.isEnabled()))
        self.form.addRow("", hint(_("a top division of a new country: a national cup for it and the division "
                                    "below, any number of clubs (byes when the field is not 16, 32 ...)")))
        self.lcup = QCheckBox(_("League cup"))
        self.lcup.setChecked(bool(L.get("league_cup")))
        self.lcup_name = QLineEdit(L.get("league_cup_name", ""))
        self.lcup_name.setPlaceholderText(_("(the league's name + League Cup)"))
        self.form.addRow("", row(self.lcup, self.lcup_name, helpmark(
            "A second knockout cup, like England's Carabao Cup: 16, 8 or 4 clubs of this league and the one "
            "below, one match a round from September to December. When there are more clubs than that, the "
            "extra ones play a pre-round in early September. Top division only.")))
        self.form.addRow("", hint(_("a knockout of 16, 8 or 4 clubs of this division and the one below, "
                                    "September to December; the clubs past it play a pre-round in early September")))
        self.cup_logo = PictureField(L.get("cup_logo"), 48)
        self.supercup_logo = PictureField(L.get("supercup_logo"), 48)
        self.lcup_logo = PictureField(L.get("league_cup_logo"), 48)
        self.po_logo = PictureField(L.get("playoff_logo"), 48)
        self.form.addRow(_("Cup logos"), row(QLabel(_("Cup")), self.cup_logo, QLabel(_("Super cup")),
                                             self.supercup_logo, QLabel(_("League cup")), self.lcup_logo,
                                             QLabel(_("Playoffs")), self.po_logo))
        from ..pitch import FormationPick
        self.formation = FormationPick(project.formations(), L.get("formation", ""))
        self.formation.pitch.setFixedHeight(190)
        self.form.addRow(_("Formation"), self.formation)
        self.form.addRow("", hint(_("how the league's clubs line up: a copy of the tactics of a club of the "
                                    "game with that formation; a club can have its own (Edit club)")))
        self.europe = EuropeTable(L.get("europe"), self.clubs.value())
        self.form.addRow(_("Europe"), self.europe)
        self.form.addRow("", hint(_("league position -> European competition, for a top division; "
                                    "leave it empty for lower tiers")))
        self.clubs.valueChanged.connect(self.europe.set_clubs)
        self.above.currentIndexChanged.connect(lambda _i: self.europe.set_top(self.above.currentData() is None))
        self.europe.set_top(self.above.currentData() is None)
        self.above.currentIndexChanged.connect(lambda _i: self.cup.setEnabled(self.above.currentData() is None))
        self.cup.setEnabled(self.above.currentData() is None)
        self.above.currentIndexChanged.connect(lambda _i: self.lcup.setEnabled(self.above.currentData() is None))
        self.lcup.setEnabled(self.above.currentData() is None)
        self.above.currentIndexChanged.connect(
            lambda _i: self.supercup.setEnabled(self.cup.isEnabled() and self.cup.isChecked()))
        self.supercup.setEnabled(self.cup.isEnabled() and self.cup.isChecked())
        self.above.currentIndexChanged.connect(lambda _i: self.season_follows())
        self.europe.set_confed(project.confeds.get(self.country_name()))
        self.country.currentTextChanged.connect(
            lambda t: self.europe.set_confed(project.confeds.get(B.country_of(t, project.countries))))
        self.exhibition.toggled.connect(lambda _on: self.exhibition_state())
        self.exhibition_state()

    def season_follows(self):
        """the season box of a division below another shows the season it really gets, the one of
        the league above: a division under the Saudi Pro League or the J1 League plays February
        to December with it (GitHub #86), whatever the box said before"""
        top = self.above.currentData() is None
        self.season.setEnabled(top and not self.exhibition.isChecked())
        if top:
            own = str(self.league.get("season") or "august")
        else:
            own = "calendar" if self.follows_calendar(self.above.currentData(), set()) else "august"
        self.season.setCurrentIndex(max(0, self.season.findData(own)))

    def follows_calendar(self, up, seen):
        if isinstance(up, int):
            return up in getattr(self.project, "calendar_parents", set())
        x = next((x for x in self.project.recipe["leagues"] if x["name"] == up), None)
        if x is None or up in seen:
            return False
        seen.add(up)
        if x.get("above") in (None, ""):
            return str(x.get("season") or "") == "calendar"
        a = x["above"]
        return self.follows_calendar(int(a) if isinstance(a, str) and a.isdigit() else a, seen)

    def country_name(self):
        """the game's name of the country picked or typed ("South Korea" -> "Republic of Korea")"""
        return B.country_of(self.country.currentText(), self.project.countries)

    def exhibition_state(self):
        """an exhibition league stands alone: the division, the cups, Europe and a split go grey"""
        on = self.exhibition.isChecked()
        if on:
            self.above.setCurrentIndex(0)
            self.rr.setChecked(True)
        top = self.above.currentData() is None
        self.above.setEnabled(not on)
        self.split.setEnabled(not on)
        self.ap.setEnabled(not on)
        self.po.setEnabled(not on)
        self.europe.setEnabled(not on)
        self.cup.setEnabled(top and not on)
        self.lcup.setEnabled(top and not on)
        self.supercup.setEnabled(top and not on and self.cup.isChecked())
        self.season_follows()

    def ok(self):
        L = self.league
        L["name"] = self.name.text().strip()
        L["country"] = self.country_name()
        L["clubs"] = self.clubs.value()
        L.pop("apertura", None)
        if self.ap.isChecked():
            L.pop("split", None)
            L["apertura"] = {"playoff": self.po.currentData()}
            L["legs"] = self.legs.value()
        elif self.split.isChecked():
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
        if self.cup.isChecked() and self.above.currentData() is None:
            L["cup"] = True
        else:
            L.pop("cup", None)
        if L.get("cup") and self.supercup.isChecked():
            L["supercup"] = True
        else:
            L.pop("supercup", None)
        if self.cup_name.text().strip():
            L["cup_name"] = self.cup_name.text().strip()
        else:
            L.pop("cup_name", None)
        if self.lcup.isChecked() and self.above.currentData() is None:
            L["league_cup"] = True
        else:
            L.pop("league_cup", None)
        if self.lcup_name.text().strip():
            L["league_cup_name"] = self.lcup_name.text().strip()
        else:
            L.pop("league_cup_name", None)
        if self.season.currentData() == "calendar" and self.above.currentData() is None \
                and not self.exhibition.isChecked():
            if L.get("split") or L.get("apertura") or L.get("cup") or L.get("league_cup"):
                error(self, "League", _("A league playing February to December has no split, Apertura/Clausura, "
                                                "national cup or league cup yet."))
                return
            L["season"] = "calendar"
        else:
            L.pop("season", None)
        if self.formation.value():
            L["formation"] = self.formation.value()
        else:
            L.pop("formation", None)
        a = self.above.currentData()
        if a is None:
            L.pop("above", None)
        else:
            L["above"] = a
        for key, f in (("logo", self.logo), ("cup_logo", self.cup_logo), ("supercup_logo", self.supercup_logo),
                       ("league_cup_logo", self.lcup_logo), ("playoff_logo", self.po_logo)):
            if f.path:
                L[key] = f.path
            else:
                L.pop(key, None)
        if self.flag.path:
            L["flag"] = self.flag.path
        else:
            L.pop("flag", None)
        if L.get("game_clubs"):
            L["game_clubs"] = [e for e in L["game_clubs"] if int(e.get("at", 0)) < L["clubs"]]
            if not L["game_clubs"]:
                L.pop("game_clubs")
        places = self.europe.places()
        bad = B.europe_problems(L["clubs"], places)
        if bad:
            error(self, "League", _("European places: %s") % "; ".join(tr(b) for b in bad))
            return
        if places:
            L["europe"] = sorted(places)
        else:
            L.pop("europe", None)
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
        if self.exhibition.isChecked():
            below = [x["name"] for x in self.project.recipe["leagues"]
                     if x is not self.orig and self.orig is not None and x.get("above") == self.orig.get("name")]
            if below:
                error(self, "League", _("%s is below this league; an exhibition league has none.") % below[0])
                return
            for k in ("above", "cup", "supercup", "league_cup", "split", "apertura", "europe", "season"):
                L.pop(k, None)
            L["exhibition"] = True
        else:
            L.pop("exhibition", None)
        self.accept()


    def show_tier(self):
        t = tier_of(self.project, self.above.currentData())
        self.tier_lab.setText(_("= division %d") % t if t else "")


def stadium_lib(app):
    """Stadium Server's folder (its library of stadiums), else SPFL26's own content\\stadiums
    (common\\stadiums.lua reads the same files), None for neither"""
    try:
        return lbstadiums.library(os.path.dirname(app.game.content_dir))
    except Exception:
        return None


def coach_portrait(project, key):
    """the picture of a club's manager (the recipe's players[key]["coach_portrait"]), '' for none"""
    return (project.players().get(key) or {}).get("coach_portrait") or ""


def set_coach_portrait(project, key, path):
    pl = project.players()
    if path:
        pl.setdefault(key, {})["coach_portrait"] = path
    elif key in pl:
        pl[key].pop("coach_portrait", None)
        if not pl[key]:
            pl.pop(key)


def club_stadium(project, key):
    """a club's home stadium (the recipe's players[key]["stadium"]), {} for none"""
    return dict((project.players().get(key) or {}).get("stadium") or {})


def set_club_stadium(project, key, st):
    pl = project.players()
    if st:
        pl.setdefault(key, {})["stadium"] = st
    elif key in pl:
        pl[key].pop("stadium", None)
        if not pl[key]:
            pl.pop(key)


def pack_stadium_of(lib, tid):
    """(name, folder) the stadium pack's map_teams.txt gives team tid now, None when none"""
    if not lib or tid is None:
        return None
    lines, *_r = lbstadiums.read(os.path.join(lib, lbstadiums.FILE))
    for line in lines:
        m = lbstadiums.LINE.match(line)
        if m and not m.group(1) and int(m.group(2)) == int(tid):
            parts = [x.strip() for x in line.split("#")[0].split(",")]
            if len(parts) >= 4:
                return parts[2], parts[3]
    return None


class StadiumPicker(QDialog):
    """every stadium of the stadium pack, by country, with a search: pick one"""

    def __init__(self, parent, lib, current=""):
        super().__init__(parent)
        self.setWindowTitle(_("Choose a home stadium"))
        self.resize(560, 640)
        self.choice = None
        v = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText(_("Find a stadium or a country..."))
        self.search.textChanged.connect(self.fill)
        v.addWidget(self.search)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemDoubleClicked.connect(lambda it, c: self.take())
        v.addWidget(self.tree, 1)
        self.count = hint("")
        v.addWidget(self.count)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.take)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self.items = sorted(S.library(lib, "folder"), key=str.lower)
        self.current = current.replace("/", "\\")
        self.fill()
        self.search.setFocus()

    def fill(self):
        q = self.search.text().strip().lower()
        self.tree.clear()
        groups, n, pick = {}, 0, None
        for rel in self.items:
            country, _s, name = rel.rpartition("\\")
            if q and q not in rel.lower():
                continue
            g = groups.get(country)
            if g is None:
                g = groups[country] = QTreeWidgetItem([country or _("(no country)")])
                g.setFlags(Qt.ItemIsEnabled)
                f = g.font(0)
                f.setBold(True)
                g.setFont(0, f)
                self.tree.addTopLevelItem(g)
            it = QTreeWidgetItem([name])
            it.setData(0, Qt.UserRole, rel)
            g.addChild(it)
            n += 1
            if rel.lower() == self.current.lower():
                pick = it
        if q or len(groups) == 1:
            self.tree.expandAll()
        if pick:
            pick.parent().setExpanded(True)
            self.tree.setCurrentItem(pick)
            self.tree.scrollToItem(pick)
        self.count.setText(_("%d stadiums") % n)

    def take(self):
        it = self.tree.currentItem()
        rel = it.data(0, Qt.UserRole) if it else None
        if not rel:
            return
        self.choice = rel
        self.accept()


class StadiumField(QWidget):
    """Home stadium: picked from the stadium pack's list (Stadium Server); the name the game shows
    can be changed, the slot is read from the stadium's folder"""

    def __init__(self, lib, st, tid=None):
        super().__init__()
        self.lib = lib                     # the stadium-server folder, None when not installed
        self.folder = st.get("folder") or ""
        self.slot_v = st.get("slot") or ""
        self.now = pack_stadium_of(lib, tid)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        h = QHBoxLayout()
        self.shown = QLabel("")
        self.shown.setWordWrap(True)
        self.shown.setMinimumWidth(260)
        h.addWidget(self.shown, 1)
        self.b_pick = QPushButton(_("Choose stadium..."))
        self.b_pick.setObjectName("primary")
        self.b_pick.clicked.connect(self.pick)
        self.b_clear = QPushButton(_("Game's own"))
        self.b_clear.setToolTip(_("No stadium of ours: the club keeps the stadium it has now"))
        self.b_clear.clicked.connect(self.clear)
        h.addWidget(self.b_pick)
        h.addWidget(self.b_clear)
        v.addLayout(h)
        h2 = QHBoxLayout()
        self.name_lab = QLabel(_("Name in the game"))
        h2.addWidget(self.name_lab)
        self.name = QLineEdit(st.get("name") or "")
        self.name.setPlaceholderText(_("the folder's name"))
        self.name.setMaxLength(60)
        h2.addWidget(self.name, 1)
        v.addLayout(h2)
        if not lib:
            self.b_pick.setEnabled(False)
            self.name.setEnabled(False)
        self.update_shown()

    def update_shown(self):
        if self.folder:
            country, _s, n = self.folder.replace("/", "\\").rpartition("\\")
            self.shown.setText("<b>%s</b>  <span style='color:%s'>%s</span>" % (n, theme.SUBTLE, country))
        elif self.now:
            self.shown.setText(_("now: %s (from the stadium pack)") % self.now[0])
        else:
            self.shown.setText("<span style='color:%s'>%s</span>" % (theme.SUBTLE, _("the game's own stadium")))
        self.name.setVisible(bool(self.folder))
        self.name_lab.setVisible(bool(self.folder))
        self.b_clear.setEnabled(bool(self.folder))

    def pick(self):
        d = StadiumPicker(self, self.lib, self.folder or (self.now[1] if self.now else ""))
        if d.exec() and d.choice:
            self.folder = d.choice
            self.slot_v = S.stadium_id(os.path.join(self.lib, d.choice)) or ""
            self.name.setText(d.choice.rpartition("\\")[2])
            self.update_shown()

    def clear(self):
        self.folder, self.slot_v = "", ""
        self.name.setText("")
        self.update_shown()

    def value(self):
        """the recipe's entry, {} for none; raises ValueError with what is wrong"""
        folder = self.folder.strip().strip("\\/")
        if not folder:
            return {}
        st = {"folder": folder, "name": self.name.text().strip() or folder.rpartition("\\")[2],
              "slot": str(self.slot_v).strip()}
        bad = lbstadiums.problem(st)
        if bad:
            raise ValueError(bad)
        if self.lib and not os.path.isdir(os.path.join(self.lib, folder)):
            raise ValueError(_("No folder %s in the stadium-server library.") % folder)
        if st["slot"]:
            st["slot"] = "%03d" % int(st["slot"])
        return {k: v for k, v in st.items() if v}


class ShirtColours(QWidget):
    """a shirt's two colours, as the recipe writes them ("plain #body #second #trim", the NewLife
    way): Build lends the shipped kit nearest them and gives the kit these colours, which the
    menus and scoreboards show (JamesNotLike); empty = the kit Build picks by itself"""

    def __init__(self, words):
        super().__init__()
        parts = (words or "").split()
        self.pattern = parts[0] if parts else "plain"
        self.cols = [c for c in parts[1:3] if QColor(c).isValid()]
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        self.btn = []
        for i, tip in enumerate((_("shirt"), _("second colour"))):
            b = QPushButton()
            b.setFixedSize(54, 24)
            b.setToolTip(tip)
            b.clicked.connect(lambda _c=False, i=i: self.pick(i))
            h.addWidget(b)
            self.btn.append(b)
        self.clear = QPushButton(_("None"))
        self.clear.clicked.connect(lambda: self.set([]))
        h.addWidget(self.clear)
        h.addStretch(1)
        self.set(self.cols)

    def set(self, cols):
        self.cols = list(cols)
        for i, b in enumerate(self.btn):
            c = self.cols[i] if i < len(self.cols) else None
            b.setStyleSheet("background:%s; border:1px solid #888;" % c if c else "")
            b.setText("" if c else "?")
        self.clear.setEnabled(bool(self.cols))

    def pick(self, i):
        start = QColor(self.cols[i] if i < len(self.cols) else (self.cols[0] if self.cols else "#ffffff"))
        c = QColorDialog.getColor(start, self, _("Kit colour"))
        if not c.isValid():
            return
        cols = (self.cols + [c.name()] * 2)[:2] if self.cols else [c.name(), c.name()]
        cols[i] = c.name()
        self.set(cols)

    def value(self):
        if len(self.cols) < 2:
            return ""
        return "%s %s %s %s" % (self.pattern, self.cols[0], self.cols[1], self.cols[1])


class ClubDialog(Dialog):
    """one club: name, short name, crest -- a new club, or one of the game's"""
    help = ("The name, short name and crest of one club, and its home stadium when Stadium Server is "
            "installed. A new club also gets its manager, the manager's picture and its formation; a club of "
            "the game keeps its own.\n\n"
            "Changes reach the game after Build, while the world is switched on.")

    def __init__(self, parent, name, short, crest, was=None, coach=None, formation=None, formations=(),
                 league_formation="", portrait=None, stadium=None, stadium_lib=None, tid=None, kits=None):
        super().__init__(parent, "Club")
        self.name = QLineEdit(name or "")
        self.name.setMinimumWidth(280)
        self.form.addRow(_("Name"), self.name)
        self.short = QLineEdit(short or "")
        self.short.setMaxLength(3)
        self.short.setFixedWidth(60)
        self.form.addRow(_("Short name"), self.short)
        self.form.addRow("", hint(_("three letters or digits; Č, Ž, Đ ... become C, Z, D (the game's short "
                                    "names have no marks); empty = made from the name")))
        self.crest = PictureField(crest)
        self.form.addRow(_("Crest"), self.crest)
        self.stadium, self.stadium_value = None, stadium
        if stadium is not None:            # its home stadium (Stadium Server)
            self.stadium = StadiumField(stadium_lib, stadium, tid)
            self.form.addRow(_("Home stadium"), self.stadium)
            self.form.addRow("", hint(_("%d stadiums in your stadium pack; the choice is written to its "
                                        "map_teams.txt at Build") % len(S.library(stadium_lib, "folder")) if stadium_lib else
                                      _("install Stadium Server (Stadiums page) to give the club a home stadium")))
        self.coach = None
        if coach is not None:              # a new club: its manager's name
            self.coach = QLineEdit(coach)
            self.coach.setMaxLength(45)
            self.coach.setPlaceholderText("FL M0001")
            self.form.addRow(_("Manager"), self.coach)
            self.form.addRow("", hint(_("the manager's name in the game; empty = a numbered one")))
        self.coach_name = coach
        self.portrait = None
        if portrait is not None:           # the manager's portrait (the recipe's "coach_portrait")
            self.portrait = PictureField(portrait, 64, "(the game's own)" if coach is None else "(none)")
            self.form.addRow(_("Manager picture"), self.portrait)
            self.form.addRow("", hint(_("PNG or JPG, made 256 x 256 at Build; the game shows it in Edit mode "
                                        "and the Master League")))
        self.portrait_path = portrait
        self.formation, self.formation_value = None, formation
        if formation is not None:          # a new club: its formation, or the league's
            from ..pitch import FormationPick, places_of
            first = (_("As the league (%s)") % league_formation if league_formation
                     else _("As the league (the game's default 4-2-3-1)"))
            self.formation = FormationPick(formations, formation, first, places_of(formations, league_formation))
            self.form.addRow(_("Formation"), self.formation)
        self.kits, self.kits_value = None, kits
        if kits is not None:               # a new club: its shirt colours (club_kits, club_away_kits)
            self.kits = (ShirtColours(kits[0]), ShirtColours(kits[1]))
            self.form.addRow(_("Home kit colours"), self.kits[0])
            self.form.addRow(_("Away kit colours"), self.kits[1])
            self.form.addRow("", hint(_("Build gives the club the game's kit nearest these colours, and the "
                                        "colours themselves to the menus and scoreboards; None = Build picks a "
                                        "kit by itself")))
        if was:
            self.form.addRow("", hint(_("In the game: %s (%s)") % was))
        self.result = None

    def ok(self):
        short = self.short.text().strip()
        if short and (not all(c.isalnum() for c in short) or not B.short_name(short)):
            error(self, "Club", _("The short name takes letters and digits only."))
            return
        if self.stadium is not None:
            try:
                self.stadium_value = self.stadium.value()
            except ValueError as e:
                error(self, "Club", str(e))
                return
        self.result = (self.name.text().strip(), B.short_name(short), self.crest.path)
        if self.coach is not None:
            self.coach_name = self.coach.text().strip()
        if self.portrait is not None:
            if self.portrait.path and lbplayers.portrait_problem(self.portrait.path):
                error(self, "Club", lbplayers.portrait_problem(self.portrait.path))
                return
            self.portrait_path = self.portrait.path or ""
        if self.formation is not None:
            self.formation_value = self.formation.value()
        if self.kits is not None:
            self.kits_value = (self.kits[0].value(), self.kits[1].value())
        self.accept()


class GameClubDialog(Dialog):
    """a club the game already has for one place of a new league (the league's "game_clubs",
    leaguebuilder.game_club_checks): the club and, when it plays somewhere in the game, the club
    that takes its place there -- one of the game's that plays in nothing, or a new one"""
    help = ("Use a club the game already has (Al Kuwait, say) in this place of your new league, instead of a "
            "new club. It keeps its name, crest, kits, manager and players.\n\n"
            "A club plays in one league only. When it already plays somewhere in the game (a league, a cup, a "
            "continental competition), it leaves all of that, and its old place must not stay empty, or that "
            "league would be one club short. So under the list you pick who takes its old place:\n"
            "- a club of the game that plays in nothing, or\n"
            "- a new club with a name you type; Build makes it for you.\n\n"
            "A club that plays in nothing just moves: there is no old place to fill.")

    def __init__(self, parent, project, taken, cur=None):
        super().__init__(parent, "Club of the game")
        self.info = B.game_info(project.base)
        cur = cur or {}
        # a club the recipe already uses is listed greyed with where (astyleUZ 04.10.: Sparta
        # Prague, already in his league, just did not turn up and looked impossible to pick)
        self.taken = dict(taken) if isinstance(taken, dict) else {t: "" for t in taken}
        self.clubs = sorted(((t, n, s) for t, (n, s) in self.info["clubs"].items()
                             if t not in self.taken and B.game_club_problem(self.info, t) is None),
                            key=lambda c: (c[1] or "").lower())
        self.used = sorted(((t, n, s) for t, (n, s) in self.info["clubs"].items() if t in self.taken),
                           key=lambda c: (c[1] or "").lower())
        self.form.addRow(hint(_("The club keeps its name, crest, kits, manager and players. It leaves every "
                                "competition it plays in the game and plays in this league instead.")))
        self.search = QLineEdit()
        self.search.setPlaceholderText(_("Name, short name or team ID"))
        self.search.textChanged.connect(lambda *_a: self.fill())
        self.form.addRow(_("Search"), self.search)
        self.no_league = QCheckBox(_("Only clubs in no league"))
        self.no_league.toggled.connect(lambda *_a: self.fill())
        self.form.addRow("", helped(self.no_league, "Shows only the clubs that play in no league of the game. "
                                    "They just move into your league and leave no empty place behind, so "
                                    "there is no one to pick for their old place."))
        self.tree = QTreeWidget()
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setHeaderLabels([_("Name"), _("Short name"), _("Team ID"), _("Plays in")])
        for c, w in enumerate((260, 80, 70)):
            self.tree.setColumnWidth(c, w)
        self.tree.setMinimumSize(680, 300)
        self.tree.currentItemChanged.connect(lambda *_a: self.show_swap())
        self.form.addRow(self.tree)
        self.where = hint("")
        self.form.addRow(self.where)
        self.keep = QCheckBox(_("It keeps its places in continental competitions"))
        self.keep.setChecked(bool(cur.get("keep")))
        self.keep.toggled.connect(lambda *_a: self.show_swap())
        self.form.addRow(helped(self.keep, "The club plays in your league and still plays the Champions League, "
                                "Libertadores or other continental competition it is in, so nobody has to take "
                                "its place there. From the second season on, your league's places decide who "
                                "goes."))
        self.rb_game = QRadioButton(_("Its place goes to a club of the game that plays in nothing:"))
        self.swap_club = QComboBox()
        self.swap_club.setMinimumWidth(320)
        for t, n, s in self.clubs:
            if not self.info["entries"].get(t):
                self.swap_club.addItem("%s (%s, %d)" % (n, s, t), t)
        self.rb_new = QRadioButton(_("Its place goes to a new club, named:"))
        self.rb_new.setToolTip(_("Build makes a club of that name for the competitions the club leaves, with a "
                                 "placeholder squad and a numbered badge"))
        self.swap_name = QLineEdit()
        self.swap_name.setMaxLength(45)
        grp = QButtonGroup(self)
        grp.addButton(self.rb_game)
        grp.addButton(self.rb_new)
        self.m_game = helpmark("The club you pick here takes the moved club's old place: its league, its cups "
                               "and its continental competitions. Only clubs of the game that play in nothing "
                               "are in the list, so no other place is left empty.")
        self.m_new = helpmark("Build makes a brand new club with this name for the moved club's old place (its "
                              "league, cups and continental competitions), with a placeholder squad and a "
                              "numbered badge.")
        self.form.addRow(row(self.rb_game, self.m_game))
        self.form.addRow("", self.swap_club)
        self.form.addRow(row(self.rb_new, self.m_new))
        self.form.addRow("", self.swap_name)
        sw = cur.get("swap")
        if isinstance(sw, dict):
            self.rb_new.setChecked(True)
            self.swap_name.setText(sw.get("name") or "")
        else:
            self.rb_game.setChecked(True)
            i = self.swap_club.findData(sw) if sw is not None else -1
            if i >= 0:
                self.swap_club.setCurrentIndex(i)
        self.cur_id = cur.get("id")
        self.result = None
        self.fill()

    def fill(self):
        want = self.search.text().strip().lower()
        free = self.no_league.isChecked()
        keep = self.chosen() if self.tree.topLevelItemCount() else self.cur_id
        self.tree.blockSignals(True)
        self.tree.clear()
        pick = None
        for t, n, s in self.clubs:
            if free and t in self.info["league_of"]:
                continue
            if want and want not in (n or "").lower() and want not in (s or "").lower() and want != str(t):
                continue
            where = B.game_club_where(self.info, t)
            it = QTreeWidgetItem([n, s, str(t), ", ".join(where) or _("nothing")])
            it.setData(0, Qt.UserRole, t)
            self.tree.addTopLevelItem(it)
            if t == keep:
                pick = it
        for t, n, s in self.used if want else []:
            if want not in (n or "").lower() and want not in (s or "").lower() and want != str(t):
                continue
            it = QTreeWidgetItem([n, s, str(t), _("already in this recipe: %s") % self.taken[t]])
            it.setFlags(it.flags() & ~(Qt.ItemIsSelectable | Qt.ItemIsEnabled))
            it.setToolTip(3, _("Take it out of that place first (New clubs: New club here), then pick it here."))
            self.tree.addTopLevelItem(it)
        if pick:
            self.tree.setCurrentItem(pick)
        self.tree.blockSignals(False)
        self.show_swap()

    def chosen(self):
        it = self.tree.currentItem()
        return it.data(0, Qt.UserRole) if it else None

    def show_swap(self):
        t = self.chosen()
        cont = t is not None and bool(set(self.info["entries"].get(t) or []) & B.CONTINENTAL_CIDS)
        self.keep.setVisible(cont)
        where = B.game_club_where(self.info, t, cont and self.keep.isChecked()) if t is not None else []
        if t is None:
            self.where.setText(_("Pick a club above."))
        elif where:
            self.where.setText(_("%s plays in %s. Every one of those competitions keeps its number of clubs: "
                                 "pick who takes its place there.") % (self.info["clubs"][t][0], ", ".join(where)))
        elif cont and self.keep.isChecked():
            self.where.setText(_("%s keeps its continental places and leaves nothing else: it just moves.")
                               % self.info["clubs"][t][0])
        else:
            self.where.setText(_("%s plays in nothing: it just moves.") % self.info["clubs"][t][0])
        for w in (self.rb_game, self.m_game, self.swap_club, self.rb_new, self.m_new, self.swap_name):
            w.setVisible(bool(where))          # a club that plays in nothing leaves no place to fill

    def ok(self):
        t = self.chosen()
        if t is None:
            error(self, "Club of the game", _("Pick a club."))
            return
        swap = None
        keep = self.keep.isVisible() and self.keep.isChecked()
        if B.game_club_where(self.info, t, keep):
            if self.rb_new.isChecked():
                if not self.swap_name.text().strip():
                    error(self, "Club of the game", _("Give the new club a name."))
                    return
                swap = {"name": self.swap_name.text().strip()}
            else:
                swap = self.swap_club.currentData()
                if swap is None:
                    error(self, "Club of the game", _("Pick the club that takes its place."))
                    return
                if swap == t:
                    error(self, "Club of the game", _("A club cannot take its own place."))
                    return
        self.result = {"id": t, "swap": swap, "keep": keep}
        self.accept()


class PreseasonDialog(Dialog):
    """the recipe's pre-season cups (preseason_cups): a name and 4 or 8 invited clubs each, a club
    of a new league ("<league>/<k>") or a club id of the game typed in"""
    SLOTS = 8

    def __init__(self, parent, project):
        super().__init__(parent, "Pre-season cups")
        self.project = project
        self.cups = [{"name": c.get("name", ""), "clubs": list(c.get("clubs") or []), "logo": c.get("logo")}
                     for c in project.recipe.get("preseason_cups") or []]
        self.new_clubs = [("%s/%d" % (L["name"], k), B.club_name(
            {"name": L["name"], "club_names": list(L.get("club_names") or [])}, k))
            for L in project.recipe["leagues"] for k in range(int(L.get("clubs", 0)))]
        self.v.addWidget(hint(_("A knockout of 4 or 8 clubs in July, before the season: first v second, "
                                "third v fourth ... At least one club of a new league, whose country hosts "
                                "it. A club of the game (type its id) must play in a league that season.")))
        body = QHBoxLayout()
        left = QVBoxLayout()
        self.list = QListWidget()
        self.list.setFixedWidth(220)
        left.addWidget(self.list, 1)
        add, rem = QPushButton(_("Add cup")), QPushButton(_("Remove"))
        add.clicked.connect(self.add)
        rem.clicked.connect(self.remove)
        left.addWidget(row(add, rem, stretch=False))
        body.addLayout(left)
        right = QFormLayout()
        self.name = QLineEdit()
        self.name.textEdited.connect(self.store)
        right.addRow(_("Name"), self.name)
        self.logo = PictureField(None, 48)
        self.logo.changed = self.store
        right.addRow(_("Logo"), self.logo)
        self.slots = []
        for i in range(self.SLOTS):
            c = QComboBox()
            c.setEditable(True)
            c.setMinimumWidth(280)
            c.addItem("", None)
            for ref, label in self.new_clubs:
                c.addItem(label, ref)
            c.currentTextChanged.connect(lambda _t: self.store())
            self.slots.append(c)
            right.addRow(_("Club %d") % (i + 1), c)
        body.addLayout(right, 1)
        self.v.insertLayout(0, body)
        self.list.currentRowChanged.connect(self.show_cup)
        self._loading = False
        self.fill_list()

    def fill_list(self, at=0):
        self.list.clear()
        for c in self.cups:
            self.list.addItem(c["name"] or _("(no name)"))
        on = bool(self.cups)
        self.name.setEnabled(on)
        self.logo.setEnabled(on)
        for s in self.slots:
            s.setEnabled(on)
        if on:
            self.list.setCurrentRow(min(at, len(self.cups) - 1))
        else:
            self.show_cup(-1)

    def show_cup(self, i):
        self._loading = True
        c = self.cups[i] if 0 <= i < len(self.cups) else {"name": "", "clubs": []}
        self.name.setText(c["name"])
        self.logo.path = c.get("logo") or None
        self.logo.show_it()
        for k, s in enumerate(self.slots):
            ref = c["clubs"][k] if k < len(c["clubs"]) else None
            j = s.findData(ref) if isinstance(ref, str) else -1
            if j >= 0:
                s.setCurrentIndex(j)
            else:
                s.setCurrentIndex(0)
                s.setEditText("" if ref is None else str(ref))
        self._loading = False

    def slot_value(self, s):
        t = s.currentText().strip()
        if not t:
            return None
        j = s.findText(t)
        if j > 0:
            return s.itemData(j)
        return int(t) if t.isdigit() else t

    def store(self):
        i = self.list.currentRow()
        if self._loading or not 0 <= i < len(self.cups):
            return
        self.cups[i] = {"name": self.name.text().strip(),
                        "clubs": [v for v in (self.slot_value(s) for s in self.slots) if v is not None]}
        if self.logo.path:
            self.cups[i]["logo"] = self.logo.path
        self.list.item(i).setText(self.cups[i]["name"] or _("(no name)"))

    def add(self):
        self.cups.append({"name": _("Pre-season Cup %d") % (len(self.cups) + 1), "clubs": []})
        self.fill_list(len(self.cups) - 1)

    def remove(self):
        i = self.list.currentRow()
        if 0 <= i < len(self.cups):
            del self.cups[i]
            self.fill_list(i)

    def ok(self):
        self.store()
        refs = {ref for ref, _l in self.new_clubs}
        for c in self.cups:
            name = c["name"] or _("(no name)")
            bad = [x for x in c["clubs"] if not isinstance(x, int) and x not in refs]
            if bad:
                error(self, "Pre-season cups", _("%s: %s is neither a club of a new league nor a club id "
                                                  "of the game.") % (name, bad[0]))
                return
            if len(c["clubs"]) not in (4, 8):
                error(self, "Pre-season cups", _("%s: %d clubs -- a pre-season cup has 4 or 8.")
                      % (name, len(c["clubs"])))
                return
            if len(set(map(str, c["clubs"]))) != len(c["clubs"]):
                error(self, "Pre-season cups", _("%s: a club is invited twice.") % name)
                return
            if not any(isinstance(x, str) for x in c["clubs"]):
                error(self, "Pre-season cups", _("%s: at least one club of a new league (its country "
                                                  "hosts the cup).") % name)
                return
        self.accept()


class CompetitionNamesDialog(Dialog):
    """new names and logos for the game's competitions that are not leagues (edits.competitions)
    and for the continental cups the world builds (ccup_names, ccup_logos)"""

    OURS = [("6", "CAF Champions League"), ("7", "CAF Confederation Cup"), ("8", "AFC Champions League Two"),
            ("9", "Copa Sudamericana"), ("0", "CAF Super Cup")]

    def __init__(self, parent, project):
        super().__init__(parent, "Competition names")
        r = project.recipe
        self.rows = [("game", str(c), n) for c, n, _r in B.game_competitions(project.base)] \
            + [("ours", k, n) for k, n in self.OURS]
        self.game = {k: dict(v) for k, v in ((r.get("edits") or {}).get("competitions") or {}).items()}
        self.names = dict(r.get("ccup_names") or {})
        self.logos = dict(r.get("ccup_logos") or {})
        if r.get("caf_super_cup_logo") and "0" not in self.logos:
            self.logos["0"] = r["caf_super_cup_logo"]
        self.v.insertWidget(0, hint(_("Cups, super cups and the continental competitions of the game, and the "
                                      "continental cups the League Builder makes. Leagues are renamed on Game's "
                                      "leagues and clubs. Empty name: the game's own.")))
        body = QHBoxLayout()
        self.list = QListWidget()
        self.list.setFixedWidth(300)
        body.addWidget(self.list)
        right = QVBoxLayout()
        self.was = QLabel()
        right.addWidget(self.was)
        self.name = QLineEdit()
        self.name.setMaxLength(60)
        right.addWidget(QLabel(_("Name")))
        right.addWidget(self.name)
        right.addWidget(QLabel(_("Logo")))
        self.logo_box = QVBoxLayout()
        right.addLayout(self.logo_box)
        self.logo = None
        right.addStretch(1)
        body.addLayout(right, 1)
        self.v.insertLayout(1, body, 1)
        self.scroll.hide()
        self.cur = -1
        self.fill()
        self.list.currentRowChanged.connect(self.show_row)
        self.list.setCurrentRow(0)
        self.setMinimumSize(680, 420)

    def value(self, i):
        kind, k, n = self.rows[i]
        if kind == "game":
            e = self.game.get(k, {})
            return e.get("name", ""), e.get("logo")
        return self.names.get(k, ""), self.logos.get(k)

    def fill(self):
        self.list.blockSignals(True)
        cur = self.list.currentRow()
        self.list.clear()
        for i, (kind, k, n) in enumerate(self.rows):
            name, logo = self.value(i)
            self.list.addItem((name or n) + ("  *" if name or logo else ""))
        self.list.setCurrentRow(cur)
        self.list.blockSignals(False)

    def keep(self):
        if not 0 <= self.cur < len(self.rows):
            return
        kind, k, n = self.rows[self.cur]
        name = self.name.text().strip()
        name = "" if name == n else name
        logo = self.logo.path if self.logo else None
        if kind == "game":
            e = {}
            if name:
                e["name"] = name
            if logo:
                e["logo"] = logo
            if e:
                self.game[k] = e
            else:
                self.game.pop(k, None)
        else:
            for d, v in ((self.names, name), (self.logos, logo)):
                if v:
                    d[k] = v
                else:
                    d.pop(k, None)

    def show_row(self, i):
        self.keep()
        self.fill()
        self.cur = i
        if not 0 <= i < len(self.rows):
            return
        kind, k, n = self.rows[i]
        name, logo = self.value(i)
        self.was.setText(_("In the game: %s") % n if kind == "game" else _("Built with the world: %s") % n)
        self.name.setPlaceholderText(n)
        self.name.setText(name)
        if self.logo:
            self.logo.setParent(None)
        self.logo = PictureField(logo, 64, "(the game's own)" if kind == "game" else "(made for you)")
        self.logo_box.addWidget(self.logo)

    def ok(self):
        self.keep()
        self.accept()


class GameEuropeDialog(Dialog):
    """the recipe's game_europe: the European places of the game's own top divisions, in place of
    the shipped ones"""

    def __init__(self, parent, project):
        super().__init__(parent, "European places of the game's leagues")
        self.tops = B.game_europe_tops(project.base)
        self.places = {}
        for k, v in (project.recipe.get("game_europe") or {}).items():
            if str(k).isdigit():
                self.places[int(k)] = [list(e) for e in v]
        self.v.insertWidget(0, hint(_("Tick a league to give it its own places; the others keep the game's. "
                                      "Places past a competition's room go to nobody (the Plan step says so).")))
        body = QHBoxLayout()
        self.list = QListWidget()
        self.list.setFixedWidth(280)
        for rid, name, _n, _s in self.tops:
            self.list.addItem(name)
        body.addWidget(self.list)
        right = QVBoxLayout()
        right.setSpacing(8)
        self.l_name = QLabel("")
        self.l_name.setObjectName("cardtitle")
        right.addWidget(self.l_name)
        self.own = QCheckBox(_("Own places for this league"))
        self.own.toggled.connect(self.toggle)
        right.addWidget(self.own)
        self.l_whose = hint("")
        right.addWidget(self.l_whose)
        self.table = EuropeTable([], 20, tall=True)
        self.table.preset.hide()
        right.addWidget(self.table, 1)
        body.addLayout(right, 1)
        self.v.insertLayout(1, body, 1)
        self.scroll.hide()
        self.cur = -1
        self.list.currentRowChanged.connect(self.show_league)
        self.list.setCurrentRow(0)
        self.marks()
        self.setMinimumSize(980, 640)

    def marks(self):
        """a league with places of its own carries a dot in the list"""
        for n, (rid, name, _c, _s) in enumerate(self.tops):
            it = self.list.item(n)
            it.setText(("●  " if rid in self.places else "    ") + name)
            it.setForeground(QBrush(QColor(theme.ACCENT if rid in self.places else theme.TEXT)))

    def whose(self, mine):
        self.l_whose.setText(_("Your places: they replace the game's for this league.") if mine else
                             _("The game's own places, shown for reference. Tick the box above to change them."))

    def keep(self):
        if 0 <= self.cur < len(self.tops) and self.own.isChecked():
            self.places[self.tops[self.cur][0]] = self.table.places()

    def show_league(self, i):
        self.keep()
        self.cur = i
        if not 0 <= i < len(self.tops):
            return
        rid, name, clubs, shipped = self.tops[i]
        self.l_name.setText(name)
        self.whose(rid in self.places)
        self.table.set_clubs(clubs)
        mine = rid in self.places
        self.own.blockSignals(True)
        self.own.setChecked(mine)
        self.own.blockSignals(False)
        self.table.set_places(self.places[rid] if mine else shipped)
        self.table.setEnabled(mine)

    def toggle(self, on):
        if not 0 <= self.cur < len(self.tops):
            return
        rid, _name, _clubs, shipped = self.tops[self.cur]
        if on:
            self.places[rid] = self.table.places()
        else:
            self.places.pop(rid, None)
            self.table.set_places(shipped)
        self.table.setEnabled(on)
        self.whose(on)
        self.marks()

    def ok(self):
        self.keep()
        self.result = {str(r): p for r, p in sorted(self.places.items())}
        self.accept()


class EuropeFirstDialog(Dialog):
    """the recipe's europe_first: clubs picked by hand for the Champions, Europa and Conference
    League phases of a new career's first season (AlexRufolo); a club of a new league
    ("<league>/<k>") or of the game (its team id)"""
    help = ("Pick the clubs that play the league phase of the Champions League, Europa League and Conference "
            "League in the first season of a new career.\n\n"
            "Your clubs go in first; the game fills the rest of the 36 places as it always does. Leave a "
            "competition empty and it is filled the usual way. From the second season on, the European places "
            "of the leagues decide who goes.\n\n"
            "A club of the game must play in a league that season. Only a career started after Build gets "
            "these clubs; a career you already play keeps its own.")

    def __init__(self, parent, project):
        super().__init__(parent, "First-season European clubs")
        info = B.game_info(project.base)
        self.labels = {}
        for L in project.recipe["leagues"]:
            for k in range(int(L.get("clubs", 0))):
                ref = "%s/%d" % (L["name"], k)
                self.labels[ref] = "%s  (%s)" % (B.club_name(
                    {"name": L["name"], "club_names": list(L.get("club_names") or [])}, k), L["name"])
        for t, (n, s) in info["clubs"].items():
            if t not in info["national"]:
                self.labels[t] = "%s  (%s, %d)" % (n, s, t)
        got = project.recipe.get("europe_first") or {}
        self.picked = [[int(x) if str(x).isdigit() else x for x in got.get(key) or []]
                       for key, _t in B.EUROPE_FIRST]
        self.v.insertWidget(0, hint(_("Clubs for the league phases of a new career's first season. Your clubs "
                                      "go in first, the game fills the rest; from the second season the "
                                      "leagues' European places decide.")))
        body = QHBoxLayout()
        left = QVBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(_("Club, league or team ID"))
        self.search.textChanged.connect(lambda *_a: self.fill())
        left.addWidget(self.search)
        self.pool = QListWidget()
        self.pool.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.pool.setMinimumWidth(340)
        left.addWidget(self.pool, 1)
        adds = []
        for c, (_key, title) in enumerate(B.EUROPE_FIRST):
            b = QPushButton(_("Add to the %s") % _(title))
            b.clicked.connect(lambda _c=False, c=c: self.add(c))
            adds.append(b)
        for b in adds:
            left.addWidget(b)
        body.addLayout(left, 1)
        self.lists = []
        for c, (_key, title) in enumerate(B.EUROPE_FIRST):
            col = QVBoxLayout()
            col.addWidget(QLabel(_(title)))
            lw = QListWidget()
            lw.setSelectionMode(QAbstractItemView.ExtendedSelection)
            lw.setMinimumWidth(220)
            col.addWidget(lw, 1)
            rem = QPushButton(_("Remove"))
            rem.clicked.connect(lambda _c=False, c=c: self.remove(c))
            col.addWidget(rem)
            self.lists.append(lw)
            body.addLayout(col, 1)
        self.v.insertLayout(1, body, 1)
        self.scroll.hide()
        self.fill()
        self.show_picked()
        self.setMinimumSize(1100, 600)

    def label(self, ref):
        return self.labels.get(ref, str(ref))

    def fill(self):
        q = self.search.text().strip().lower()
        taken = {x for p in self.picked for x in p}
        self.pool.clear()
        for ref, text in sorted(self.labels.items(), key=lambda x: x[1].lower()):
            if ref in taken or (q and q not in text.lower()):
                continue
            it = QListWidgetItem(text)
            it.setData(Qt.UserRole, ref)
            self.pool.addItem(it)

    def show_picked(self):
        for c, lw in enumerate(self.lists):
            lw.clear()
            for ref in self.picked[c]:
                it = QListWidgetItem(self.label(ref))
                it.setData(Qt.UserRole, ref)
                lw.addItem(it)

    def add(self, c):
        refs = [it.data(Qt.UserRole) for it in self.pool.selectedItems()]
        room = B.FIRST_MAX - len(self.picked[c])
        if len(refs) > room:
            error(self, "First-season European clubs", _("A league phase has %d clubs; %d more fit.")
                  % (B.FIRST_MAX, room))
            refs = refs[:room]
        self.picked[c] += refs
        self.fill()
        self.show_picked()

    def remove(self, c):
        drop = {it.data(Qt.UserRole) for it in self.lists[c].selectedItems()}
        self.picked[c] = [x for x in self.picked[c] if x not in drop]
        self.fill()
        self.show_picked()

    def ok(self):
        self.result = {key: list(p) for (key, _t), p in zip(B.EUROPE_FIRST, self.picked) if p}
        self.accept()


class UefaRankDialog(Dialog):
    """the UEFA key (tools/uefakey.py): the world's European top divisions in order, strongest
    first, and the places the key gives each; OK writes them into the leagues' European places"""

    def __init__(self, parent, project):
        super().__init__(parent, "UEFA ranking")
        self.project = project
        on, off = uefakey.ranked(project.recipe, project.base)
        self.v.insertWidget(0, hint(_("Put the countries in order, strongest first (drag, or Up / Down); untick a "
                                      "league to give it no European place. OK gives every league its places by "
                                      "UEFA's key, like UEFA's access list for 2024-27: the first 30 get places, "
                                      "and the places of missing ranks go to the next clubs of the strongest leagues "
                                      "in turn, so every competition stays full. You can still change any league's "
                                      "places by hand afterwards.")))
        body = QHBoxLayout()
        left = QVBoxLayout()
        self.list = QListWidget()
        self.list.setDragDropMode(QAbstractItemView.InternalMove)
        self.list.setMinimumWidth(300)
        for c, ticked in [(c, True) for c in on] + [(c, False) for c in off]:
            it = QListWidgetItem("%s (%s)" % (c["name"], c["country"]))
            it.setData(Qt.UserRole, c)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if ticked else Qt.Unchecked)
            self.list.addItem(it)
        left.addWidget(self.list, 1)
        up, down, reset = QPushButton(_("Up")), QPushButton(_("Down")), QPushButton(_("UEFA's order"))
        up.clicked.connect(lambda: self.move(-1))
        down.clicked.connect(lambda: self.move(1))
        reset.setToolTip(_("UEFA's association ranking for 2026-27"))
        reset.clicked.connect(self.reset)
        left.addWidget(row(up, down, reset))
        body.addLayout(left)
        self.view = QPlainTextEdit()
        self.view.setReadOnly(True)
        body.addWidget(self.view, 1)
        self.v.insertLayout(1, body, 1)
        self.scroll.hide()
        self.list.model().rowsMoved.connect(self.refresh)
        self.list.itemChanged.connect(self.refresh)
        self.refresh()
        self.setMinimumSize(900, 520)

    def leagues(self):
        items = [self.list.item(i) for i in range(self.list.count())]
        on = [it.data(Qt.UserRole) for it in items if it.checkState() == Qt.Checked]
        off = [it.data(Qt.UserRole) for it in items if it.checkState() != Qt.Checked]
        return on, off

    def move(self, d):
        i = self.list.currentRow()
        j = i + d
        if i < 0 or not 0 <= j < self.list.count():
            return
        it = self.list.takeItem(i)
        self.list.insertItem(j, it)
        self.list.setCurrentRow(j)
        self.refresh()

    def reset(self):
        items = [self.list.takeItem(0) for _i in range(self.list.count())]
        items.sort(key=lambda it: (uefakey.default_rank(it.data(Qt.UserRole)["country"]),
                                   not it.data(Qt.UserRole)["game"], it.data(Qt.UserRole)["name"]))
        for it in items:
            self.list.addItem(it)
        self.refresh()

    def refresh(self, *_a):
        on, off = self.leagues()
        tiers = {}
        _places, _seed, notes = uefakey.assign(on, tiers)
        lines = uefakey.table(on, tiers)
        lines += ["", _("Not ranked, no European place: %s") % ", ".join(c["name"] for c in off)] if off else []
        lines += [""] + notes if notes else []
        self.view.setPlainText("\n".join(lines))

    def ok(self):
        on, off = self.leagues()
        self.notes = uefakey.apply(self.project.recipe, on, off)
        self.accept()


class SouthAmericaDialog(Dialog):
    """read only (GitHub #71): every South American league's Libertadores, qualifying and Copa
    Sudamericana places -- the game's leagues and the world's own -- as Check the plan lists them"""

    def __init__(self, parent, project):
        super().__init__(parent, "South American places")
        own, names, clubs = [], {}, {}
        for L in project.recipe["leagues"]:
            n = L.get("name") or "?"
            names[n], clubs[n] = n, L.get("clubs") or 0
            for pos, comp in L.get("europe") or []:
                own.append(("", 0, comp, n) if pos == B.CUP_WINNER else (n, pos, comp, 0))
        cups, _notes = B.ccup_plan(own, clubs)
        self.v.insertWidget(0, hint(_("Which positions go to the Copa Libertadores, its qualifying round and the "
                                      "Copa Sudamericana, for the game's South American leagues and yours. The "
                                      "game's Libertadores places are its own; the Copa Sudamericana is built by "
                                      "Mod Studio, your leagues' places first, then the game's leagues in turn.")))
        view = QPlainTextEdit()
        view.setReadOnly(True)
        view.setPlainText("\n".join(l[4:] for l in B.samerica_lines(own, names, cups)[1:]))
        self.v.insertWidget(1, view, 1)
        self.scroll.hide()
        self.setMinimumSize(820, 360)

    def finish(self):
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.button(QDialogButtonBox.Close).setText(_("Close"))
        bb.rejected.connect(self.reject)
        self.add_buttons(bb)
        try:
            theme.dark_title_bar(self)
        except Exception:
            pass
        self.exec()
        return False


class GameCupsDialog(Dialog):
    """the recipe's game_cups: a league cup, and a super cup where the game has none, for the
    game's own top divisions (the Carabao Cup for the Premier League)"""

    def __init__(self, parent, project):
        super().__init__(parent, "Cups of the game's countries")
        self.tops = B.game_tops(project.base)
        have = {int(c["league"]): c for c in project.recipe.get("game_cups") or [] if str(c.get("league")).isdigit()}
        self.v.insertWidget(0, hint(_("A league cup is 16 clubs of the league and the one below it, by position, "
                                      "one match a round from late September to December; the clubs past 16 play "
                                      "a pre-round in early September. A super cup -- the "
                                      "champion v the cup winner in late July -- only where the game has none. "
                                      "Empty name = the league's name and League Cup / Super Cup.")))
        self.table = QTableWidget(len(self.tops), 5)
        self.table.setHorizontalHeaderLabels([_("League"), _("League cup"), _("Name"), _("Super cup"), _("Name")])
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
            sc.setEnabled(not has_super)
            sn.setEnabled(not has_super)
            for col, w in ((1, lc), (2, ln), (3, sc), (4, sn)):
                self.table.setCellWidget(i, col, w)
            self.rows.append((rid, lc, ln, sc, sn, c))
        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(2, 220)
        self.table.setColumnWidth(4, 220)
        self.table.setMinimumSize(760, 420)
        self.v.insertWidget(1, self.table, 1)
        self.scroll.hide()
        self.cups = []

    def ok(self):
        self.cups = []
        for rid, lc, ln, sc, sn, old in self.rows:
            if not (lc.isChecked() or sc.isChecked()):
                continue
            c = {"league": rid, "league_cup": lc.isChecked(), "super_cup": sc.isChecked()}
            for key, w in (("name", ln), ("super_name", sn)):
                if w.text().strip():
                    c[key] = w.text().strip()
            for key in ("logo", "super_logo"):
                if old.get(key):
                    c[key] = old[key]
            self.cups.append(c)
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
    help = ("What the buttons do:\n"
            "- Add league: a new league; its clubs are made for you.\n"
            "- Add lower tier: a league one division below the selected one, with promotion and relegation "
            "between the two.\n"
            "- Edit / Remove: change or delete the selected league. Ctrl+click, Shift+click or Ctrl+A picks "
            "several leagues, and Remove (or the Delete key) deletes them together.\n"
            "- Pre-season cups: small friendly tournaments of 4 or 8 clubs in July.\n"
            "- Cups of the game's countries: a league cup (like the Carabao Cup) for the game's own leagues, "
            "and a super cup where the game has none.\n"
            "- European places of the game's leagues: which positions of the Premier League, LaLiga ... go to "
            "which European competition.\n"
            "- First-season European clubs: pick by hand who plays the Champions, Europa and Conference "
            "League in a new career's first season.\n"
            "- UEFA ranking: put the European countries in order and every league gets its European places by "
            "UEFA's rules.\n"
            "- South American places: shows who goes to the Libertadores and the Copa Sudamericana.\n"
            "- Competition names: new names and logos for cups and continental competitions.\n"
            "- World name: the folder the world is built into.")

    def __init__(self, app):
        super().__init__(app)
        self.action("Add league", self.add, "primary")
        self.action("Add lower tier", self.add_lower, tip="A new league one division below the selected one: "
                    "same country, clubs and format, with promotion and relegation between the two")
        self.action("Edit", self.edit)
        self.action("Remove", self.remove, "danger")
        self.action("Pre-season cups", self.preseason, tip="Friendly knockouts of 4 or 8 invited clubs in "
                    "July, before the season")
        self.action("Cups of the game's countries", self.game_cups, tip="A league cup (the Carabao Cup) for "
                    "leagues of the game, and a super cup where the game has none")
        self.action("European places of the game's leagues", self.game_europe, tip="Which positions of the "
                    "Premier League, LaLiga ... go to which European competition, in place of the game's list")
        self.action("First-season European clubs", self.europe_first, tip="Pick by hand the clubs of the "
                    "Champions, Europa and Conference League in a new career's first season")
        self.action("UEFA ranking", self.uefa_rank, tip="Put the European countries in order and every league "
                    "gets its European places by UEFA's key")
        self.action("South American places", self.samerica, tip="Which positions of every South American "
                    "league, the game's and yours, go to the Libertadores, its qualifying and the Sudamericana")
        self.action("Competition names", self.competition_names, tip="New names and logos for the cups and "
                    "continental competitions of the game, and for the continental cups the world builds")
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
        self.tree.setHeaderLabels([_("League"), _("League ID"), _("Country"), _("Clubs"), _("Format"),
                                   _("Division"), _("Up / down"), _("Europe"), _("Players changed")])
        self.tree.headerItem().setToolTip(1, _("The league's competition id in the game (the one its logo "
                                               "file uses), given at Build"))
        for c, w in enumerate((240, 80, 150, 60, 170, 230, 80, 150)):
            self.tree.setColumnWidth(c, w)
        self.tree.itemDoubleClicked.connect(lambda *a: self.edit())
        # several leagues at once: Ctrl+click, Shift+click, Ctrl+A, then Remove or Delete
        # (I know?, 2026-10-04: "can u do ctrl+a so i dont have to delete all of them one by one")
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        QShortcut(QKeySequence.Delete, self.tree, self.remove, context=Qt.WidgetShortcut)
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
        plan = built_plan(self.app.game, r.get("world"))
        for i, L in enumerate(r["leagues"]):
            up = L.get("above")
            div = _("top") if up in (None, "") else _("below %s") % (names.get(up, up) if isinstance(up, int) else up)
            t = tier_of(self.project, up)
            if t:
                div = "%d  (%s)" % (t, div)
            n = sum(len((pl.get("%s/%d" % (L["name"], k)) or {}).get("edits") or {}) for k in range(L.get("clubs", 0)))
            b = built_league(self.app.game, r.get("world"), L["name"], plan or {})
            # A league the last Build did not make has no id yet, and is not in the game either
            # (Amir, 2026-09-28: a second division added after the build, blank id, "the game
            # reads only the first league"). Say so rather than leave the cell empty.
            cid = str(b["cid"]) if b.get("cid") is not None else (_("not built yet") if plan else "")
            it = QTreeWidgetItem([L["name"], cid,
                                  L.get("country", ""), str(L.get("clubs", "")), fmt_text(L), div,
                                  str(L.get("exchange", 3)) if up not in (None, "") else "", europe_text(L),
                                  str(n) if n else ""])
            if b.get("rid") is not None:
                it.setToolTip(1, _("competition %s, regulation %s") % (b.get("cid"), b["rid"]))
            elif plan:
                it.setToolTip(1, _("Added or renamed since the last Build: press Build to put it in the game."))
            pm = pixmap(L.get("logo"), 28)
            if pm:
                it.setIcon(0, pm)
            it.setData(0, Qt.UserRole, i)
            self.tree.addTopLevelItem(it)
        if cur is not None and cur < self.tree.topLevelItemCount():
            self.tree.setCurrentItem(self.tree.topLevelItem(cur))
        clubs = sum(B.new_club_count(L) for L in r["leagues"])
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

    def add_lower(self):
        """a league under the selected one, filled in from it: only the name is left to give"""
        if self.need_tables():
            return
        i = self.selected()
        if i is None:
            self.say(_("Select the league the new one goes under, then Add lower tier. To go under one of "
                       "the game's own leagues, use Add league and pick it at Division."), "warn")
            return
        up = self.project.recipe["leagues"][i]
        new = {"country": up.get("country", ""), "clubs": up.get("clubs", 12), "legs": up.get("legs", 2),
               "above": up["name"], "exchange": up.get("exchange", 3)}
        if up.get("split"):
            new["split"] = dict(up["split"])
        d = LeagueDialog(self, self.project, new=new, title=_("League below %s") % up["name"])
        d.name.setFocus()
        if d.finish():
            leagues = self.project.recipe["leagues"]
            at = i + 1                       # after the league above and the ones already under it
            while at < len(leagues) and self._under(leagues[at], up["name"]):
                at += 1
            leagues.insert(at, d.league)
            self.project.touch()
            self.tree.setCurrentItem(self.tree.topLevelItem(at))

    def _under(self, L, name, seen=()):
        up = L.get("above")
        if up == name:
            return True
        for x in self.project.recipe["leagues"]:
            if x["name"] == up and up not in seen:
                return self._under(x, name, seen + (up,))
        return False

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
        rows = sorted({it.data(0, Qt.UserRole) for it in self.tree.selectedItems()})
        if not rows and self.selected() is not None:
            rows = [self.selected()]
        if not rows:
            return
        leagues = self.project.recipe["leagues"]
        names = [leagues[i]["name"] for i in rows]
        q = (_("Remove %s, with its clubs and their player changes?") % names[0] if len(names) == 1 else
             _("Remove these %d leagues, with their clubs and their player changes?") % len(names)
             + "\n\n" + "\n".join(names))
        if ask(self, "Remove", q):
            for i in reversed(rows):
                del leagues[i]
            for L in leagues:
                if L.get("above") in names:
                    L.pop("above")
            for name in names:
                self.project.drop_league(name)
            self.project.touch()

    def preseason(self):
        if not self.project.recipe["leagues"]:
            self.say(_("Add a league first: a pre-season cup is hosted by a new league's country."), "warn")
            return
        d = PreseasonDialog(self, self.project)
        if d.finish():
            if d.cups:
                self.project.recipe["preseason_cups"] = d.cups
            else:
                self.project.recipe.pop("preseason_cups", None)
            self.project.touch()

    def competition_names(self):
        if self.need_tables():
            return
        d = CompetitionNamesDialog(self, self.project)
        if d.finish():
            r = self.project.recipe
            if d.game:
                self.project.edits("competitions").clear()
                self.project.edits("competitions").update(d.game)
            else:
                (r.get("edits") or {}).pop("competitions", None)
            for key, v in (("ccup_names", d.names), ("ccup_logos", d.logos)):
                if v:
                    r[key] = v
                else:
                    r.pop(key, None)
            r.pop("caf_super_cup_logo", None)
            if d.logos.get("0"):
                r["caf_super_cup_logo"] = d.logos["0"]
            self.project.touch()

    def game_europe(self):
        if self.need_tables():
            return
        d = GameEuropeDialog(self, self.project)
        if d.finish():
            if d.result:
                self.project.recipe["game_europe"] = d.result
            else:
                self.project.recipe.pop("game_europe", None)
            self.project.touch()

    def europe_first(self):
        if self.need_tables():
            return
        d = EuropeFirstDialog(self, self.project)
        if d.finish():
            if d.result:
                self.project.recipe["europe_first"] = d.result
            else:
                self.project.recipe.pop("europe_first", None)
            self.project.touch()

    def uefa_rank(self):
        if self.need_tables():
            return
        d = UefaRankDialog(self, self.project)
        if d.finish():
            self.project.touch()
            self.refresh()
            self.say(_("UEFA ranking applied: every ranked league has its European places. Check the plan shows "
                       "them."), "ok")

    def samerica(self):
        SouthAmericaDialog(self, self.project).finish()

    def game_cups(self):
        if self.need_tables():
            return
        d = GameCupsDialog(self, self.project)
        if d.finish():
            if d.cups:
                self.project.recipe["game_cups"] = d.cups
            else:
                self.project.recipe.pop("game_cups", None)
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
        self.app.settings["last_recipe"] = p
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
        self.app.settings["last_recipe"] = p
        self.app.status(_("Recipe saved: %s") % p)

    def new_recipe(self):
        if self.project.dirty and not ask(self, "New", _("Start a new recipe? Unsaved changes are lost.")):
            return
        self.project.new()


class NewClubs(BuilderPage):
    title = "New clubs"
    hint = ("The clubs of one of your leagues. Double-click a club to give it a name, crest, stadium and "
            "manager; More has the rest.")
    help = ("The clubs of the league picked at the top. Double-click a club (or Edit club) for its name, short "
            "name, crest, manager, stadium and formation.\n"
            "- Players: change the club's squad.\n"
            "- Club of the game...: put a club the game already has (Al Kuwait, say) in this place instead of a "
            "new club. If it plays somewhere in the game, you pick who takes its old place there.\n"
            "- NewLife club...: put clubs of the NewLife Database, with their squads, in this place and the "
            "places after it (open the NewLife Database on the NewLife page first).\n"
            "- New club here: undo that; the place gets a new club again.\n"
            "- Insert club / Remove club: a new club before the selected one, or the selected one out. The "
            "league gets one club more or one less.\n"
            "- Move to another league...: the club goes to another of your new leagues, with its name, crest, "
            "manager and players.\n"
            "- Paste names... / Load names from file...: name every club at once, one name per line, in order.")

    def __init__(self, app):
        super().__init__(app)
        self.action("Edit club", self.edit, "primary")
        self.action("Players", self.players, tip="Change this club's squad")
        self.action("Club of the game...", self.game_club,
                    tip="Put a club the game already has in this place, instead of a new club")
        self.action("NewLife club...", self.newlife_club,
                    tip="Put clubs of the NewLife Database in this place and the ones after it")
        more = QToolButton()
        more.setText(_("More") + "  ▾")
        more.setPopupMode(QToolButton.InstantPopup)
        m = QMenu(more)
        for it in (("New club here", self.new_here), ("Insert club", lambda: self.shift(1)),
                   ("Remove club", lambda: self.shift(-1)), ("Move to another league...", self.move_club), None,
                   ("Paste names...", self.paste), ("Load names from file...", self.load_file),
                   ("Import crests...", lambda: import_crests(self))):
            if it is None:
                m.addSeparator()
            else:
                m.addAction(_(it[0])).triggered.connect(lambda _c=False, f=it[1]: f())
        more.setMenu(m)
        self.actions.addWidget(more)
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
        self.tree.setHeaderLabels(["#", _("Name"), _("Short name"), _("Team ID"), _("Crest"), _("Players changed")])
        self.tree.headerItem().setToolTip(3, _("The club's id in the game, from the last Build"))
        for c, w in enumerate((40, 320, 90, 80, 260)):
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
            self.say(_("No new leagues yet: add one on the Leagues page."), "warn")
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

    def built_ids(self, L):
        """the team ids a build gave this league's clubs, or []: ids are handed out at Build,
        after the game's own clubs"""
        got = list(built_league(self.app.game, self.project.recipe.get("world"), L["name"]).get("teams") or [])
        if got:
            return got
        return self.plan_ids(L)

    def plan_ids(self, L):
        """the ids plan() would give this league's clubs (a NewLife club's world id is fixed
        before a build, so a Kit Server's map.txt can be made for it), or []"""
        if self.project.base is None:
            return []
        try:
            m, _free = B.newlife_tids(self.project.recipe.get("leagues") or [], self.project.base,
                                         self.project.recipe.get("newlife_ids"))
        except Exception:
            return []
        ids = list(L.get("club_ids") or [])
        nl = list((L.get("newlife") or {}).get("clubs") or [])
        out = []
        for k in range(int(L.get("clubs") or 0)):
            tid = ids[k] if k < len(ids) and ids[k] else None
            if tid is None and k < len(nl) and nl[k]:
                tid = m.get(int(nl[k]))
            out.append(tid)
        return out

    def show_clubs(self):
        cur = self.tree.currentItem()
        cur = cur.data(0, Qt.UserRole) if cur else None
        self.tree.clear()
        L = self.league()
        if not L:
            return
        names, abbrs, crests = self.lists(L)
        pl = self.project.players()
        ids = self.built_ids(L)
        game = self.game_places(L)
        for k in range(L["clubs"]):
            if k in game:
                it = self.game_row(k, game[k], pl)
                self.tree.addTopLevelItem(it)
                if k == cur:
                    self.tree.setCurrentItem(it)
                continue
            n = len((pl.get("%s/%d" % (L["name"], k)) or {}).get("edits") or {})
            it = QTreeWidgetItem([str(k + 1), names[k] or "%s %02d" % (L["name"], k + 1), abbrs[k] or "",
                                  str(ids[k]) if k < len(ids) else "",
                                  os.path.basename(crests[k]) if crests[k] else "", str(n) if n else ""])
            if not names[k]:
                it.setForeground(1, QBrush(QColor(theme.SUBTLE)))
            kits = L.get("club_kits") or []
            pm = pixmap(crests[k], 28, kits[k] if k < len(kits) else None)
            if pm:
                it.setIcon(1, pm)
            it.setData(0, Qt.UserRole, k)
            self.tree.addTopLevelItem(it)
            if k == cur:
                self.tree.setCurrentItem(it)

    @staticmethod
    def game_places(L):
        """{place: {"at", "id", "swap"}} of the league's clubs of the game"""
        return {int(e.get("at", -1)): e for e in L.get("game_clubs") or []}

    def game_row(self, k, e, pl):
        tid = int(e["id"])
        name, short = self.project.game_cl.get(tid, (str(tid), ""))
        ed = self.project.edits("clubs").get(str(tid), {})       # Edit club: a new name, crest ...
        n = len((pl.get(str(tid)) or {}).get("edits") or {})
        it = QTreeWidgetItem([str(k + 1), ed.get("name") or name, ed.get("abbr") or short, str(tid),
                              _("(new crest)") if ed.get("crest") else _("(the game's)"), str(n) if n else ""])
        sw = e.get("swap")
        if isinstance(sw, dict):
            tip = _("A club of the game. A new club, %s, takes its place in the game.") % sw.get("name", "")
        elif sw is not None:
            tip = _("A club of the game. %s takes its place in the game.") \
                % self.project.game_cl.get(int(sw), (str(sw), ""))[0]
        else:
            tip = _("A club of the game that played in no competition.")
        tip += "  " + _("Edit club changes its name, crest, manager's portrait and stadium.")
        for c in range(6):
            it.setToolTip(c, tip)
        it.setForeground(4, QBrush(QColor(theme.SUBTLE)))
        pm = pixmap(ed.get("crest"), 28)
        if pm:
            it.setIcon(1, pm)
        it.setData(0, Qt.UserRole, k)
        return it

    def current(self):
        it = self.tree.currentItem()
        return it.data(0, Qt.UserRole) if it else None

    def taken(self, skip):
        """{team id: where the recipe already uses it} for the clubs of the game in a place or
        taking one, but the one at place `skip` of the league shown"""
        out = {}
        cur = self.league()
        names = (self.project.names()[0] or {}) if self.project.base else {}
        for L in self.project.recipe["leagues"]:
            for e in L.get("game_clubs") or []:
                if L is cur and int(e.get("at", -1)) == skip:
                    continue
                out[int(e["id"])] = _("%s, club %d") % (L["name"], int(e.get("at", 0)) + 1)
                if e.get("swap") is not None and not isinstance(e["swap"], dict):
                    out[int(e["swap"])] = _("takes %s's place") % names.get(int(e["id"]), e["id"])
        return out

    def game_club(self):
        L, k = self.league(), self.current()
        if not L or k is None:
            return
        if self.project.base is None:
            self.need_tables()
            return
        d = GameClubDialog(self, self.project, self.taken(k), self.game_places(L).get(k))
        if d.finish() and d.result:
            e = {"at": k, "id": d.result["id"]}
            if d.result["swap"] is not None:
                e["swap"] = d.result["swap"]
            if d.result.get("keep"):
                e["keep"] = True
            gc = [x for x in L.get("game_clubs") or [] if int(x.get("at", -1)) != k]
            L["game_clubs"] = sorted(gc + [e], key=lambda x: int(x["at"]))
            self.project.touch()

    def newlife_club(self):
        """NewLife Database clubs into this place and the ones after it (#83): a league made by
        hand gets real clubs with their squads, one tick per place"""
        from .newlife import ClubPickDialog
        L, k = self.league(), self.current()
        if not L or k is None:
            return
        if self.project.base is None:
            self.need_tables()
            return
        rel = getattr(self.app.pages.get("NewLife"), "rel", None) or getattr(self, "nl_rel", None)
        if rel is None:
            folder = self.app.settings.get("newlife")
            if not folder or not os.path.isdir(folder):
                QMessageBox.information(self, _("New clubs"), _("Open the NewLife Database on the NewLife page first."))
                return
            self.app.busy(True)

            def done(r):
                self.app.busy(False)
                self.nl_rel = r
                self.newlife_club()

            run_job(lambda: N.Release(folder), done=done,
                    failed=lambda tb: (self.app.busy(False), error(self, "NewLife club", tb.strip().splitlines()[-1])))
            return
        used = {int(i) for x in self.project.recipe["leagues"] for i in (x.get("newlife") or {}).get("clubs") or []
                if str(i).isdigit()}
        skip = used | {cid for cid, c in rel.clubs.items() if c.get("in_game") == "1"}
        d = ClubPickDialog(self, rel, skip)
        if not d.finish() or not d.picked:
            return
        room = int(L["clubs"]) - k
        if len(d.picked) > room:
            error(self, "NewLife club", _("%d clubs picked, but %s has only %d places from club %d on. Insert "
                                          "clubs first (More > Insert club).") % (len(d.picked), L["name"], room, k + 1))
            return
        try:
            game = B.game_info(self.project.base)
        except OSError:
            game = None
        put = elsewhere = 0
        try:
            for j, cid in enumerate(d.picked):
                elsewhere += N.put_club(self.project.recipe, rel, L, k + j, cid, game)[1]
                put += 1
        except N.Error as e:
            error(self, "NewLife club", str(e))
        if not put:
            return
        self.project.touch()
        text = _("%d NewLife clubs put in %s.") % (put, L["name"])
        if elsewhere:
            text += " " + _("%d of their players stay out: another of your leagues has them.") % elsewhere
        self.say(text + " " + _("Build again and start a new career."), "ok")

    def new_here(self):
        L, k = self.league(), self.current()
        if not L or k is None or k not in self.game_places(L):
            return
        L["game_clubs"] = [e for e in L["game_clubs"] if int(e.get("at", -1)) != k]
        if not L["game_clubs"]:
            L.pop("game_clubs")
        self.project.touch()

    def shift(self, delta):
        L, k = self.league(), self.current()
        if not L:
            return
        if k is None:
            if delta < 0:
                return
            k = L["clubs"]                  # nothing selected: the new club goes last
        if delta < 0 and not ask(self, "Remove club", _("Take club %d out of %s? Its name, crest, manager and "
                                                           "player changes go with it.") % (k + 1, L["name"])):
            return
        if not self.project.shift_places(L["name"], k, delta):
            QMessageBox.warning(self, _("New clubs"), _("A league has %d to %d clubs.") % (B.CLUBS_MIN, B.CLUBS_MAX))
            return
        self.say(_("%s now has %d clubs: check its European places on the Leagues page, then Build again "
                   "and start a new career.") % (L["name"], L["clubs"]), "ok")

    def move_club(self):
        L, k = self.league(), self.current()
        if not L or k is None:
            return
        others = [x["name"] for x in self.project.recipe["leagues"] if x is not L]
        if not others:
            QMessageBox.information(self, _("New clubs"), _("The recipe has no other new league."))
            return
        d = Dialog(self, "Move to another league")
        to = QComboBox()
        to.addItems(others)
        d.form.addRow(_("League"), to)
        d.form.addRow("", hint(_("%s goes to the end of that league, with its name, crest, manager, formation, kits "
                                 "and player changes. %s keeps one club less.") % (self.lists(L)[0][k] or
                                                                                    "%s %02d" % (L["name"], k + 1), L["name"])))
        if not d.finish():
            return
        dst = to.currentText()
        bad = self.project.move_club(L["name"], k, dst)
        if bad:
            QMessageBox.warning(self, _("New clubs"), _(bad))
            return
        self.say(_("The club is now the last of %s: check both leagues' European places on the Leagues page, "
                   "then Build again and start a new career.") % dst, "ok")

    def edit(self):
        L, k = self.league(), self.current()
        if not L or k is None:
            return
        if k in self.game_places(L):
            tid = self.game_places(L)[k]["id"]
            if tid in self.project.game_cl and edit_game_club(self, tid):
                self.refresh()
            return
        names, abbrs, crests = self.lists(L)
        coaches = list(L.get("club_coaches") or [])[:L["clubs"]]
        coaches += [""] * (L["clubs"] - len(coaches))
        forms = list(L.get("club_formations") or [])[:L["clubs"]]
        forms += [""] * (L["clubs"] - len(forms))
        key = "%s/%d" % (L["name"], k)
        d = ClubDialog(self, names[k], abbrs[k], crests[k], coach=coaches[k], formation=forms[k],
                       formations=self.project.formations(), league_formation=L.get("formation", ""),
                       portrait=coach_portrait(self.project, key), stadium=club_stadium(self.project, key),
                       stadium_lib=stadium_lib(self.app), kits=self.kit_words(L, k))
        if d.finish() and d.result:
            names[k], abbrs[k], crests[k] = d.result
            self.set_kit_words(L, k, d.kits_value)
            set_coach_portrait(self.project, key, d.portrait_path)
            set_club_stadium(self.project, key, d.stadium_value)
            coaches[k] = d.coach_name or ""
            if any(coaches):
                L["club_coaches"] = coaches
            else:
                L.pop("club_coaches", None)
            forms[k] = d.formation_value or ""
            if any(forms):
                L["club_formations"] = forms
            else:
                L.pop("club_formations", None)
            self.project.touch()

    @staticmethod
    def kit_words(L, k):
        return tuple((list(L.get(key) or []) + [""] * (k + 1))[k] or "" for key in ("club_kits", "club_away_kits"))

    @staticmethod
    def set_kit_words(L, k, words):
        n = int(L.get("clubs") or 0)
        for key, w in zip(("club_kits", "club_away_kits"), words or ("", "")):
            lst = (list(L.get(key) or []) + [""] * n)[:n]
            lst[k] = w or ""
            if any(lst):
                L[key] = lst
            else:
                L.pop(key, None)

    def players(self):
        L, k = self.league(), self.current()
        if L and k is not None:
            g = self.game_places(L).get(k)
            self.app.page("Players").show_club(str(int(g["id"])) if g else "%s/%d" % (L["name"], k))
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


class SwapDialog(Dialog):
    """a club of another league of the game, to trade places with club tid"""
    help = ("Two clubs of the game trade places: each takes the other's league, cups and European places. "
            "Use it when a club went up or down in real life and the game still has it in its old league: "
            "swap it with a club of the league it belongs in now.\n\n"
            "Both leagues keep their number of clubs. For your new leagues use Club of the game on the New "
            "clubs page instead.")

    def __init__(self, parent, project, tid, skip):
        super().__init__(parent, "Swap leagues")
        info = B.game_info(project.base)
        mine = info["league_of"].get(tid)
        n = project.game_cl.get(tid, (str(tid),))[0]
        self.v.insertWidget(0, hint(_("%s (%s) takes the other club's places -- its league, cups and European "
                                      "competitions -- and the other club takes its places. Both leagues keep "
                                      "their number of clubs.") % (n, mine)))
        self.search = QLineEdit()
        self.search.setPlaceholderText(_("Find a league or club..."))
        self.search.textChanged.connect(self.fill)
        self.v.insertWidget(1, self.search)
        self.list = QListWidget()
        self.v.insertWidget(2, self.list, 1)
        self.scroll.hide()
        self.all = sorted(((project.game_cl[t][0], lg, t) for t, lg in info["league_of"].items()
                           if lg != mine and t not in skip and t in project.game_cl),
                          key=lambda x: (x[0].lower(), x[1]))
        self.picked = None
        self.fill()
        self.setMinimumSize(520, 480)

    def fill(self):
        q = self.search.text().strip().lower()
        self.list.clear()
        for name, league, t in self.all:
            if q and q not in name.lower() and q not in league.lower():
                continue
            it = QListWidgetItem("%s  (%s)" % (name, league))
            it.setData(Qt.UserRole, t)
            self.list.addItem(it)

    def ok(self):
        it = self.list.currentItem()
        if it is None:
            error(self, "Swap leagues", _("Pick a club."))
            return
        self.picked = it.data(Qt.UserRole)
        self.accept()


def swap_of(project, tid):
    """the club tid trades leagues with, or None"""
    for a, b in (project.recipe.get("edits") or {}).get("swaps") or []:
        if int(a) == tid:
            return int(b)
        if int(b) == tid:
            return int(a)
    return None


def edit_game_club(page, tid):
    """the club dialog for club tid of the game: its new name, short name, crest, manager's
    portrait and stadium go into the recipe's edits.clubs (Game's leagues and clubs, and a club
    of the game on New clubs). True when something was kept."""
    project = page.project
    n, a = project.game_cl[tid]
    e = project.edits("clubs").get(str(tid), {})
    d = ClubDialog(page, e.get("name") or n, e.get("abbr") or a, e.get("crest"), was=(n, a),
                   portrait=coach_portrait(project, str(tid)), stadium=club_stadium(project, str(tid)),
                   stadium_lib=stadium_lib(page.app), tid=tid)
    if not (d.finish() and d.result):
        return False
    set_coach_portrait(project, str(tid), d.portrait_path)
    set_club_stadium(project, str(tid), d.stadium_value)
    name, short, crest = d.result
    e = {}
    if name and name != n:
        e["name"] = name
    if short and short != a:
        e["abbr"] = short
    if crest:
        e["crest"] = crest
    if e:
        project.edits("clubs")[str(tid)] = e
    else:
        project.edits("clubs").pop(str(tid), None)
    project.dirty = True
    return True


PICTURE_EXT = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp")


class CrestImportDialog(Dialog):
    """crests for many clubs at once (0.1.8): every picture of a folder matched to a club by its
    file name -- a club's name ("Alianza Lima.png", "alianza_lima_r_l.png") or its team id
    ("2287.png", the crest packs' "e_2287_r.png"). A match goes where Edit club puts a crest: a
    club of the game's in edits.clubs, a new club's in its league's club_crests. Matching by
    name is tools/crestmatch.py, an idea from Xxspedd's escudos.py."""
    help = ("Gives many clubs a crest at once. Pick a folder of pictures: each picture is matched to a club by "
            "its file name, either the club's name (\"Alianza Lima.png\") or its team ID (\"2287.png\", "
            "\"e_2287_r.png\").\n\n"
            "Untick a wrong match before OK. A club that already has a crest keeps it unless \"Replace crests "
            "already set\" is ticked. The pictures stay where they are: Build reads them from that folder, "
            "so do not move or delete it.")

    def __init__(self, parent, project):
        super().__init__(parent, "Import crests")
        import crestmatch
        self.cm = crestmatch
        self.project = project
        self.clubs = []                 # (name, key): key ("game", tid) or ("new", league, place)
        for tid, (n, _s) in sorted(project.game_cl.items()):
            self.clubs.append((n, ("game", tid)))
        for L in project.recipe["leagues"]:
            gp = {int(e.get("at", -1)) for e in L.get("game_clubs") or []}
            names = {"name": L["name"], "club_names": list(L.get("club_names") or [])}
            for k in range(int(L.get("clubs", 0))):
                if k not in gp:
                    self.clubs.append((B.club_name(names, k), ("new", L["name"], k)))
        self.form.addRow(hint(_("Each picture of the folder is matched to a club by its file name: the club's "
                                "name or its team ID. Untick a wrong match.")))
        self.folder = QLineEdit()
        self.folder.setReadOnly(True)
        pick = QPushButton(_("Pick folder..."))
        pick.clicked.connect(self.pick)
        self.form.addRow(_("Folder"), row(self.folder, pick, stretch=False))
        self.only = QComboBox()
        self.only.addItem(_("All clubs"), None)
        self.only.addItem(_("The new leagues' clubs"), "new")
        self.only.addItem(_("The game's clubs"), "game")
        self.only.currentIndexChanged.connect(lambda *_a: self.fill())
        self.form.addRow(_("Match to"), self.only)
        self.replace = QCheckBox(_("Replace crests already set"))
        self.form.addRow("", self.replace)
        self.tree = QTreeWidget()
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setIconSize(QSize(24, 24))
        self.tree.setHeaderLabels([_("Picture"), _("Club"), _("Team ID"), _("Match")])
        for c, w in enumerate((260, 260, 80)):
            self.tree.setColumnWidth(c, w)
        self.tree.setMinimumSize(720, 340)
        self.form.addRow(self.tree)
        self.said = hint("")
        self.form.addRow(self.said)
        self.files = []
        self.result = None

    def pick(self):
        d = QFileDialog.getExistingDirectory(self, _("Pick folder..."), self.folder.text())
        if not d:
            return
        self.folder.setText(os.path.normpath(d))
        self.files = sorted(f for f in os.listdir(d) if f.lower().endswith(PICTURE_EXT))
        self.fill()

    def has_crest(self, key):
        if key[0] == "game":
            return bool(self.project.edits("clubs").get(str(key[1]), {}).get("crest"))
        L = self.project.league(key[1])
        crests = list((L or {}).get("club_crests") or [])
        return key[2] < len(crests) and bool(crests[key[2]])

    def matches(self):
        """{file: ((club name, key), score)} for the clubs the Match to box allows"""
        want = self.only.currentData()
        clubs = [c for c in self.clubs if want is None or c[1][0] == want]
        by_id = {c[1][1]: c for c in clubs if c[1][0] == "game"}
        found, rest = {}, []
        for f in self.files:
            t = self.cm.file_id(f)
            if t in by_id:
                found[f] = (by_id[t], 1.0)
            else:
                rest.append(f)
        taken = {found[f][0][1] for f in found}
        left = [c for c in clubs if c[1] not in taken]
        for f, j, sc in self.cm.match(rest, [(n, i) for i, (n, _k) in enumerate(left)]):
            if j is not None:
                found[f] = (left[j], sc)
        return found

    def fill(self):
        found = self.matches()
        self.tree.clear()
        for f in self.files:
            it = QTreeWidgetItem([f, "", "", ""])
            pm = pixmap(os.path.join(self.folder.text(), f), 24)
            if pm:
                it.setIcon(0, pm)
            if f in found:
                (n, key), sc = found[f]
                it.setText(1, n if key[0] == "game" else "%s (%s)" % (n, key[1]))
                it.setText(2, str(key[1]) if key[0] == "game" else "")
                it.setText(3, "%d %%" % round(sc * 100))
                it.setData(0, Qt.UserRole, list(key))
                it.setCheckState(0, Qt.Checked if sc >= 0.6 else Qt.Unchecked)
            else:
                it.setText(1, _("no club found"))
                it.setForeground(1, QBrush(QColor(theme.SUBTLE)))
            self.tree.addTopLevelItem(it)
        self.said.setText(_("%d pictures, %d matched to a club.") % (len(self.files), len(found)))

    def ok(self):
        n = kept = 0
        for i in range(self.tree.topLevelItemCount()):
            it = self.tree.topLevelItem(i)
            key = it.data(0, Qt.UserRole)
            if not key or it.checkState(0) != Qt.Checked:
                continue
            if self.has_crest(key) and not self.replace.isChecked():
                kept += 1
                continue
            path = os.path.join(self.folder.text(), it.text(0))
            if key[0] == "game":
                self.project.edits("clubs").setdefault(str(key[1]), {})["crest"] = path
            else:
                L = self.project.league(key[1])
                crests = list(L.get("club_crests") or [])
                crests += [None] * (int(L.get("clubs", 0)) - len(crests))
                crests[key[2]] = path
                L["club_crests"] = crests
            n += 1
        if n:
            self.project.touch()
        self.result = (n, kept)
        self.accept()


def import_crests(page):
    """the Import crests dialog from a page; says what it did"""
    if page.project.base is None:
        page.need_tables()
        return
    d = CrestImportDialog(page, page.project)
    if d.finish() and d.result:
        n, kept = d.result
        page.say(_("%d crests imported.") % n
                 + ("  " + _("%d clubs kept the crest they had.") % kept if kept else ""), "ok")


class GameLeagues(BuilderPage):
    title = "Game's leagues and clubs"
    hint = ("The leagues and clubs the game already has: new names, logos and crests. Changes are written "
            "into your world, so they show while the world is switched on. A saved Edit file (EDIT00000000) "
            "in the game's save folder overrides club names: move it away to see them.")
    help = ("Pick a league of the game on the left. Then:\n"
            "- give the league a new name or logo and press Keep league changes;\n"
            "- Edit club: a new name, short name or crest for the selected club;\n"
            "- Players: change its squad;\n"
            "- Swap leagues with a club...: two clubs of the game trade leagues (a promoted club for a "
            "relegated one);\n"
            "- Undo club changes: back to the game's own.\n\n"
            "Nothing is changed in the game's files: it all goes into your world after Build.")

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
        b4 = QPushButton(_("Swap leagues with a club..."))
        b4.setToolTip(_("Two clubs of the game's leagues trade places: a promoted club for a relegated one, say"))
        b4.clicked.connect(self.swap_club)
        b5 = QPushButton(_("Import crests..."))
        b5.setToolTip(_("Crests for many clubs at once, from a folder of pictures named after the clubs"))
        b5.clicked.connect(lambda: import_crests(self))
        rv.addWidget(row(b1, b2, b4, b3, b5))
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
        self.shown_rows = [(ALL_CLUBS, None, _("(all clubs)"), sorted(P.game_cl))] + list(P.game_lgs) \
            + [(g, None, name, teams) for g, name, teams in P.game_groups()]
        if q:                        # (all clubs) and the groups stay: the search picks their clubs
            self.shown_rows = [x for x in self.shown_rows if x[0] < 0 or q in x[2].lower()]
        changed = P.edits("leagues")
        for rid, cid, name, teams in self.shown_rows:
            e = changed.get(str(rid), {})
            label = name if rid == ALL_CLUBS else "%s  (%d)" % (e.get("name", name), len(teams))
            if 0 > rid != ALL_CLUBS:
                label = "%s  (%d)" % (name, sum(1 for t in teams if not q or q in P.game_cl.get(t, ("",))[0].lower()))
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
        league = rid >= 0                    # (all clubs) and the "Others" groups are no league
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
            if not league and q and q not in cl[tid][0].lower():
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
        sw = swap_of(self.project, tid)
        if sw is not None:
            marks.append(_("swaps with %s") % self.project.game_cl.get(sw, (str(sw),))[0])
        vals = [str(tid), e.get("name") or n, e.get("abbr") or a,
                os.path.basename(e["crest"]) if e.get("crest") else "", ", ".join(marks)]
        for c, v in enumerate(vals):
            it.setText(c, v)
        pm = pixmap(e.get("crest"), 24)
        it.setIcon(1, pm if pm else QPixmap())

    def keep_league(self):
        g = self.current_league()
        if not g or g[0] < 0:
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
        if g and g[0] >= 0:
            self.project.edits("leagues").pop(str(g[0]), None)
            self.project.touch()

    def selected_tid(self):
        it = self.tree.currentItem()
        if not it:
            info(self, "Clubs", _("Pick a club in the list first: click its row, then the button."))
        return (it.data(0, Qt.UserRole), it) if it else (None, None)

    def edit_club(self):
        tid, it = self.selected_tid()
        if tid is None:
            return
        if edit_game_club(self, tid):
            self.club_row(it, tid)

    def undo_club(self):
        for it in self.tree.selectedItems():
            tid = it.data(0, Qt.UserRole)
            self.project.edits("clubs").pop(str(tid), None)
            self.drop_swap(tid)
            self.club_row(it, tid)
        self.project.dirty = True

    def drop_swap(self, tid):
        e = self.project.recipe.setdefault("edits", {})
        left = [p for p in e.get("swaps") or [] if tid not in (int(p[0]), int(p[1]))]
        if left:
            e["swaps"] = left
        else:
            e.pop("swaps", None)

    def swap_club(self):
        tid, it = self.selected_tid()
        if tid is None:
            return
        info = B.game_info(self.project.base)
        if tid not in info["league_of"]:
            error(self, "Swap leagues", _("This club plays in no league of the game."))
            return
        e = self.project.recipe.setdefault("edits", {})
        busy = {int(x) for p in e.get("swaps") or [] for x in p if tid not in (int(p[0]), int(p[1]))}
        for L in self.project.recipe["leagues"]:
            for g in L.get("game_clubs") or []:
                busy.add(int(g["id"]))
                if g.get("swap") not in (None, "") and not isinstance(g["swap"], dict):
                    busy.add(int(g["swap"]))
        if tid in busy:
            error(self, "Swap leagues", _("This club already plays in a new league of the recipe."))
            return
        d = SwapDialog(self, self.project, tid, busy)
        if not (d.finish() and d.picked is not None):
            return
        self.drop_swap(tid)
        e.setdefault("swaps", []).append([tid, d.picked])
        self.project.touch()

    def players(self):
        tid, it = self.selected_tid()
        if tid is not None:
            self.app.page("Players").show_club(str(tid))
            self.app.open_page("Players")


class AfterBuild(QDialog):
    """what Build and install did, step by step, and what is left to do"""

    def __init__(self, parent, info):
        super().__init__(parent)
        from ..game import Game
        from .. import VERSION
        self.setWindowTitle(_("Build finished"))
        self.setMinimumWidth(620)
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 18)
        v.setSpacing(12)
        top = QLabel(_("BUILD FINISHED · %d s") % info.get("secs", 0))
        top.setObjectName("eyebrow")
        v.addWidget(top)
        t = QLabel(_("%s is installed.") % info["world"])
        t.setObjectName("bigtitle")
        t.setWordWrap(True)
        v.addWidget(t)
        running = Game.running()[0]
        steps = [("ok", _("World built"), info["world"]),
                 ("ok", _("Leagues and clubs"), _("%d leagues · %d new clubs") % (info["leagues"], info["clubs"])),
                 ("ok", _("Modules installed and switched on"), _("version %s") % VERSION),
                 ("ok", _("Switched on in sider.ini"), _("the live world"))]
        steps.append(("warn", _("The game is running with the old world: restart it to play the new one"), "")
                     if running else ("ok", _("Start the game to play it"), ""))
        import time
        from .. import game as G
        self.world = info["world"]
        self.edit = G.old_edit(time.time() - info.get("secs", 0) - 5)
        if self.edit:
            steps.append(("warn", _("An Edit save from before this Build is in the game's save folder. It hides "
                                    "the new squads and names in Exhibition and Edit mode: move it aside."), ""))
        box = QFrame()
        box.setObjectName("card")
        bv = QVBoxLayout(box)
        bv.setContentsMargins(18, 6, 18, 6)
        for n, (kind, text, right) in enumerate(steps):
            h = QHBoxLayout()
            h.setContentsMargins(0, 8, 0, 8)
            mark = QLabel("✓" if kind == "ok" else "!")
            mark.setObjectName("tick_" + kind)
            mark.setFixedWidth(22)
            h.addWidget(mark)
            lab = QLabel(text)
            lab.setWordWrap(True)
            h.addWidget(lab, 1)
            r = QLabel(right)
            r.setObjectName("subtle")
            h.addWidget(r)
            bv.addLayout(h)
            if n < len(steps) - 1:
                line = QFrame()
                line.setObjectName("rowline")
                bv.addWidget(line)
        v.addWidget(box)
        note = QFrame()
        note.setObjectName("bluecard")
        nv = QVBoxLayout(note)
        nv.setContentsMargins(18, 12, 18, 12)
        h2 = QLabel(_("Before you play"))
        h2.setObjectName("cardtitle")
        nv.addWidget(h2)
        for text in [_("Start a new Master League career: a career saved before keeps the old world.")]                 + info.get("notes", []):
            l = QLabel(text)
            l.setWordWrap(True)
            nv.addWidget(l)
        v.addWidget(note)
        bb = QHBoxLayout()
        bb.addStretch(1)
        if self.edit:
            self.b_edit = QPushButton(_("Move the Edit save aside"))
            self.b_edit.clicked.connect(self.edit_aside)
            bb.addWidget(self.b_edit)
        if running:
            b = QPushButton(_("Close the game"))
            b.clicked.connect(self.close_game)
            bb.addWidget(b)
        ok = QPushButton(_("Done"))
        ok.setObjectName("primary")
        ok.clicked.connect(self.accept)
        bb.addWidget(ok)
        v.addLayout(bb)

    def edit_aside(self):
        from .. import game as G
        try:
            name = G.edit_aside(self.world)
        except OSError as e:
            error(self, "Move the Edit save aside", str(e))
            return
        self.b_edit.setEnabled(False)
        info(self, "Move the Edit save aside",
             _("The Edit save is now %s, in the same folder. The game makes a new one; to get the old one "
               "back, rename it to EDIT00000000.") % name)

    def close_game(self):
        from ..game import EXE_NAMES
        import subprocess
        if ask(self, "Close the game", _("Close the game now? Anything not saved in it is lost.")):
            for n in EXE_NAMES:
                subprocess.run(["taskkill", "/im", n], capture_output=True, creationflags=0x08000000)
            self.accept()


class Build(BuilderPage):
    title = "Build"
    hint = ("Turn the recipe into a world: 1. check the plan, 2. build it into SiderAddons\\livecpk, "
            "3. switch it on in sider.ini, then start the game and 4. check sider.log. "
            "The builder's modules are installed once (0), and again after a new version of the program.")
    help = ("The steps, in order:\n"
            "0. Install the modules: puts Mod Studio's modules into sider. Once, and again after every new "
            "version of Mod Studio.\n"
            "1. Check the plan: reads your leagues and says what will be built and what is wrong. It changes "
            "nothing.\n"
            "2. Build the world: writes your leagues, clubs, players, cups and pictures into a folder in "
            "SiderAddons\\livecpk.\n"
            "3. Switch it on: adds the world to sider.ini, so the game loads it.\n"
            "4. After a start: start the game, then press this. It reads sider.log and says whether every "
            "module worked.\n\n"
            "After building again, start a new Master League career: a career saved before keeps the old world.")

    def __init__(self, app):
        super().__init__(app)
        self.steps = []
        bar = QHBoxLayout()
        for text, fn, kind in (("0. Install the modules", self.do_install, None),
                               ("1. Check the plan", self.do_plan, None),
                               ("2. Build the world", self.do_build, None),
                               ("3. Switch it on", self.do_on, None),
                               ("4. After a start: check", self.do_check, None)):
            b = QPushButton(_(text))
            if kind:
                b.setObjectName(kind)
            b.clicked.connect(fn)
            bar.addWidget(b)
            self.steps.append(b)
        bar.addStretch(1)
        one = QHBoxLayout()
        self.b_all = QPushButton(_("Build and install"))
        self.b_all.setObjectName("primary")
        self.b_all.setStyleSheet("font-size: 11pt; font-weight: bold; padding: 10px 26px; border-radius: 8px;")
        self.b_all.setToolTip(_("Installs the modules, builds the world, switches it on and says what is left"))
        self.b_all.clicked.connect(self.build_all)
        self.steps.append(self.b_all)
        one.addWidget(self.b_all)
        one.addWidget(hint(_("All in one: the modules, the world, switching it on. Or step by step:")), 1)
        self.outer.addLayout(one)
        self.outer.addLayout(bar)
        cards = QHBoxLayout()
        cards.setSpacing(14)
        euc = QFrame()
        euc.setObjectName("card")
        eu = QVBoxLayout(euc)
        eu.setContentsMargins(18, 14, 18, 14)
        eu.setSpacing(8)
        t = QLabel(_("European cups"))
        t.setObjectName("cardtitle")
        eu.addWidget(t)
        eu.addWidget(hint(_("Every world built here has the new Champions League and Europa League: a league "
                            "phase of 36 clubs, then the play-off and the knockout rounds.")))
        clc = QFrame()
        clc.setObjectName("card")
        cl = QVBoxLayout(clc)
        cl.setContentsMargins(18, 14, 18, 14)
        cl.setSpacing(8)
        t2 = QLabel(_("New clubs"))
        t2.setObjectName("cardtitle")
        cl.addWidget(t2)
        cards.addWidget(euc, 3)
        cards.addWidget(clc, 2)
        self.outer.addLayout(cards)
        self.uecl = QCheckBox(_("Include the Conference League"))
        self.uecl.setToolTip(_("A league phase of 36 clubs and a February play-off, like the Champions League "
                               "and the Europa League"))
        self.uecl.toggled.connect(self.set_uecl)
        eu.addWidget(row(self.uecl, helpmark(
            "A league phase of 36 clubs and a February play-off, like the Champions League "
            "and the Europa League"), hint(_("off = no Conference League; the Champions League and Europa "
                                                   "League keep their 36-club league phase and play-off either way"))))
        self.uecl_logo = PictureField(None, 48)
        self.uecl_logo.changed = self.set_uecl_logo
        eu.addWidget(row(QLabel(_("Conference League logo")), self.uecl_logo,
                                 hint(_("empty = a UECL emblem drawn for you"))))
        self.uecl_name = QLineEdit()
        self.uecl_name.setPlaceholderText(B.mkuecl.NAME)
        self.uecl_name.setMaxLength(60)
        self.uecl_name.editingFinished.connect(self.set_uecl_name)
        eu.addWidget(row(QLabel(_("Conference League name")), self.uecl_name,
                                 hint(_("empty = %s; a new name needs the world built again") % B.mkuecl.NAME)))
        self.cafsc = QCheckBox(_("CAF Super Cup"))
        self.cafsc.setToolTip(_("The winners of the CAF Champions League and the Confederation Cup meet once, "
                                "in late July. First played in a career's second season, when both cups "
                                "have a winner"))
        self.cafsc.toggled.connect(self.set_cafsc)
        eu.addWidget(row(self.cafsc, helpmark(
            "The winners of the CAF Champions League and the Confederation Cup meet once, "
            "in late July. First played in a career's second season, when both cups "
            "have a winner"), hint(_("only in a world with both African cups (the European "
                                                    "places of your African leagues)"))))
        self.ekits = QCheckBox(_("Kits you can edit in the game"))
        self.ekits.setToolTip(_("On: the new clubs get no kit borrowed from a club of the game. A borrowed kit is "
                                "a licensed one, and the game's Edit mode refuses it (\"You cannot edit this "
                                "strip\"). Without one each new club wears a plain kit that Edit > Teams > Strip "
                                "changes like any other, Paste Image included. Build again after changing this."))
        self.ekits.toggled.connect(self.set_ekits)
        cl.addWidget(row(self.ekits, helpmark(
            "On: the new clubs get no kit borrowed from a club of the game. A borrowed kit is "
            "a licensed one, and the game's Edit mode refuses it (\"You cannot edit this "
            "strip\"). Without one each new club wears a plain kit that Edit > Teams > Strip "
            "changes like any other, Paste Image included. Build again after changing this."), hint(_("off = each new club borrows a kit of the game (it looks "
                                                    "real, but Edit mode cannot change it)"))))
        self.b_euro = QPushButton(_("Build only the European cups..."))
        self.b_euro.setToolTip(_("A world with nothing but the new Champions League and Europa League (league "
                                 "phase of 36 and play-off) and, when ticked above, the Conference League: "
                                 "no new leagues, the game's clubs and leagues as they are. Your recipe is "
                                 "not changed."))
        self.b_euro.clicked.connect(self.do_europe_only)
        eu.addWidget(row(self.b_euro, helpmark(
            "A world with nothing but the new Champions League and Europa League (league "
            "phase of 36 and play-off) and, when ticked above, the Conference League: "
            "no new leagues, the game's clubs and leagues as they are. Your recipe is "
            "not changed."), hint(_("a world with just the new European format and the game's own leagues and "
                                         "clubs: no new leagues"))))
        cl.addStretch(1)
        self.state = hint("")
        self.outer.addWidget(self.state)
        self.out = QPlainTextEdit()
        self.out.setObjectName("log")
        self.out.setReadOnly(True)
        self.outer.addWidget(self.out, 1)

    def shown(self):
        self.need_tables()
        self.refresh()

    def set_uecl(self, on):
        if bool(self.project.recipe.get("uecl", True)) != on:
            self.project.recipe["uecl"] = on
            self.project.touch()

    def set_cafsc(self, on):
        if bool(self.project.recipe.get("caf_super_cup", True)) != on:
            self.project.recipe["caf_super_cup"] = on
            self.project.touch()

    def set_ekits(self, on):
        if bool(self.project.recipe.get("editable_kits")) != on:
            if on:
                self.project.recipe["editable_kits"] = True
            else:
                self.project.recipe.pop("editable_kits", None)
            self.project.touch()

    def set_uecl_name(self):
        v = self.uecl_name.text().strip()
        if v != (self.project.recipe.get("uecl_name") or ""):
            if v:
                self.project.recipe["uecl_name"] = v
            else:
                self.project.recipe.pop("uecl_name", None)
            self.project.touch()

    def set_uecl_logo(self):
        if self.uecl_logo.path != self.project.recipe.get("uecl_logo"):
            if self.uecl_logo.path:
                self.project.recipe["uecl_logo"] = self.uecl_logo.path
            else:
                self.project.recipe.pop("uecl_logo", None)
            self.project.touch()

    def refresh(self):
        g = self.app.game
        w = self.project.recipe.get("world", "")
        self.uecl.blockSignals(True)
        self.uecl.setChecked(bool(self.project.recipe.get("uecl", True)))
        self.uecl.blockSignals(False)
        self.cafsc.blockSignals(True)
        self.cafsc.setChecked(bool(self.project.recipe.get("caf_super_cup", True)))
        self.cafsc.blockSignals(False)
        self.ekits.blockSignals(True)
        self.ekits.setChecked(bool(self.project.recipe.get("editable_kits")))
        self.ekits.blockSignals(False)
        self.uecl_logo.path = self.project.recipe.get("uecl_logo")
        self.uecl_logo.show_it()
        self.uecl_name.setText(self.project.recipe.get("uecl_name") or "")
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
            raise B.BuildError(_("nothing to build: add a league or change one of the game's -- or, for "
                                 "the new European cups alone, press \"Only the new European cups...\""))
        return B.plan(r, self.project.base)

    def do_europe_only(self):
        """#36: the new European format with the game's own leagues and clubs, and nothing else.
        An empty recipe builds just that (leaguebuilder.build always reshapes the European cups),
        so this builds one into a world of its own and leaves the recipe being edited alone."""
        from PySide6.QtWidgets import QInputDialog
        title = _("Only the new European cups...")
        if self.project.base is None:
            error(self, title, _("no game tables -- Settings > Unpack the game's tables"))
            return
        if not self.app.game.ok():
            error(self, title, _("no game folder -- Game > Choose the game folder"))
            return
        uecl = self.uecl.isChecked()
        name, ok = QInputDialog.getText(
            self, title, _("A world with the new Champions League and Europa League%s and the game's own "
                           "leagues and clubs. Only one world can be switched on, so this is instead of "
                           "a world with new leagues.\n\nName of the world:")
            % (_(" and the Conference League") if uecl else ""), text=EURO_WORLD)
        name = (name or "").strip()
        if not ok or not name:
            return
        if not name.startswith("_FL26"):
            error(self, title, _("the world name must start with _FL26"))
            return
        if name == self.project.recipe.get("world"):
            error(self, title, _("%s is the world of the recipe you are editing: pick another name.") % name)
            return
        out = os.path.join(self.app.game.livecpk_dir, name)
        replace = os.path.exists(out)
        if replace and not ask(self, title, _("%s exists. Build it again?") % name):
            return
        try:
            pl = B.plan({"world": name, "leagues": [], "edits": {}, "players": {}, "uecl": uecl,
                         "uecl_logo": self.project.recipe.get("uecl_logo"),
                         "uecl_name": self.project.recipe.get("uecl_name"),
                         "game_cups": self.project.recipe.get("game_cups") or [],
                         "game_europe": self.project.recipe.get("game_europe") or {}}, self.project.base)
        except B.BuildError as e:
            self.out.clear()
            self.say(_("error: %s") % tr(str(e)))
            return
        game, base = self.app.game.folder, self.project.base

        def go(log):
            log(B.describe(pl))
            note = database_note(self.project)
            if note:
                log("\n" + note + "\n")
            log(_("building ..."))
            B.build(pl, base, game, replace, log=log)
            self.project.drop_names()
            log("\n" + _("Next: switch %s on (it takes the place of any other world), then start the game "
                          "and start a new Master League career.") % name)

        def switch():
            if ask(self, title, _("Make %s the live world in sider.ini?") % name):
                def on(log):
                    snapshot(self.app.game.ini_path, "League Builder: switch on " + name, self.app.game.sider_dir)
                    B.switch_on(name, self.app.game.folder, log=log)
                    self.project.drop_names()
                    log("\n" + _("Start the game, then 4. check."))
                self.run(on)
                self.app.bus.ini_changed.emit()
        self.run(go, background=True, done=switch)

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
        def go(log):
            pl = self.plan()
            log(B.describe(pl))
            note = exhibition_note(pl)
            if note:
                log("\n" + note)
        self.run(go)

    def do_build(self):
        try:
            pl = self.plan()
            if B.pin_newlife(self.project.recipe, self.project.base):
                self.project.touch()       # NewLife clubs keep these world ids from now on
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
        try:
            # a copy of what is built, opened again at the next start (Project.keep_copy)
            kept = self.project.keep_copy()
            self.app.settings["last_recipe"] = kept
            self.app.status(_("Recipe saved: %s") % kept)
        except OSError:
            pass

        def go(log):
            log(B.describe(pl))
            log(_("building ..."))
            B.build(pl, base, game, replace, log=log)
            self.project.drop_names()
            log("\n" + _("Next: 3. Switch it on, then start the game."))
            note = database_note(self.project)
            if note:
                log("\n" + note)
            note = exhibition_note(pl)
            if note:
                log("\n" + note)
        self.run(go, background=True)

    def build_all(self):
        """0.1.8: one button -- install the modules, build the world, switch it on, then a page
        that says what was done and what is left (restart the game, a new career)"""
        try:
            pl = self.plan()
            if B.pin_newlife(self.project.recipe, self.project.base):
                self.project.touch()
        except B.BuildError as e:
            self.out.clear()
            self.say(_("error: %s") % tr(str(e)))
            return
        game = self.app.game.folder
        w = pl["world"]
        replace = os.path.exists(os.path.join(self.app.game.livecpk_dir, w))
        if not ask(self, "Build and install", _("Build %s and make it the live world? Mod Studio's modules are "
                                                "installed too; sider.ini is backed up first.") % w):
            return
        base = self.project.base
        try:
            self.app.settings["last_recipe"] = self.project.keep_copy()
        except OSError:
            pass
        import time
        info = {"world": w, "t0": time.time(),
                "leagues": len(self.project.recipe["leagues"]),
                "clubs": sum(B.new_club_count(L) for L in self.project.recipe["leagues"])}

        def go(log):
            snapshot(self.app.game.ini_path, "League Builder: build and install " + w, self.app.game.sider_dir)
            log(_("installing the modules ..."))
            B.install_modules(game, log=log)
            log(B.describe(pl))
            log(_("building ..."))
            B.build(pl, base, game, replace, log=log)
            B.switch_on(w, game, log=log)
            self.project.drop_names()
            info["secs"] = int(time.time() - info["t0"])
            info["notes"] = [n for n in (database_note(self.project), exhibition_note(pl)) if n]

        def done():
            self.app.bus.ini_changed.emit()
            AfterBuild(self, info).exec()
        self.run(go, background=True, done=done)

    def do_on(self):
        w = self.project.recipe.get("world", "").strip()
        if ask(self, "Switch on", _("Make %s the live world in sider.ini?") % w):
            def go(log):
                snapshot(self.app.game.ini_path, "League Builder: switch on " + w, self.app.game.sider_dir)
                B.switch_on(w, self.app.game.folder, log=log)
                self.project.drop_names()
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
