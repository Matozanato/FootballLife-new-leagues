"""League Builder: new leagues, their clubs, the game's own leagues and clubs, and the build.

Every page edits app.project.recipe (modstudio/project.py); leaguebuilder.py does the work.
"""
import csv, io, json, os

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QImage, QColor, QBrush
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
                               QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QPlainTextEdit, QPushButton, QRadioButton, QSpinBox, QSplitter,
                               QTableWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
                               QFileDialog, QButtonGroup, QHeaderView, QAbstractItemView,
                               QMessageBox, QScrollArea, QApplication)

import leaguebuilder as B
import fl26world
from .. import theme
from ..i18n import _, tr
from ..backups import snapshot
from ..ui import Page, section, hint, row, ask, error, run_job

EURO_WORLD = "_FL26Euro"


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
         8: "AFC CL2", 9: "SUD"}
TOP_FLIGHT = [[1, 0], [2, 1], [3, 2]]      # the preset: 1st UCL, 2nd UEL, 3rd UECL
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
UEFA_PRESET = ("Top flight: 1st UCL, 2nd UEL, 3rd UECL",
               "1st to the Champions League, 2nd to the Europa League, 3rd to the Conference League", TOP_FLIGHT)


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


def europe_text(L):
    return ", ".join("%d %s" % (pos, SHORT.get(comp, comp)) for pos, comp in sorted(L.get("europe") or []))


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


class EuropeTable(QWidget):
    """a league's European places: league position -> competition, one row each"""

    def __init__(self, places, clubs):
        super().__init__()
        self.clubs = clubs
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels([_("League position"), _("Competition")])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setMinimumHeight(120)
        self.table.setMaximumHeight(170)
        v.addWidget(self.table)
        self.preset = QPushButton()
        self.preset_places = TOP_FLIGHT
        self.set_confed(None)
        self.preset.clicked.connect(lambda: self.set_places(self.preset_places))
        add = QPushButton(_("Add place"))
        add.clicked.connect(self.add)
        rem = QPushButton(_("Remove place"))
        rem.clicked.connect(self.remove)
        clr = QPushButton(_("Clear"))
        clr.clicked.connect(lambda: self.set_places([]))
        v.addWidget(row(self.preset, add, rem, clr))
        self.set_places(places or [])

    def _row(self, pos, comp):
        r = self.table.rowCount()
        self.table.insertRow(r)
        sp = QSpinBox()
        sp.setRange(1, max(self.clubs, 1))
        sp.setValue(min(max(int(pos), 1), max(self.clubs, 1)))
        cb = QComboBox()
        for c, name in fl26world.COMPETITIONS:
            cb.addItem(_(name), c)
        cb.setCurrentIndex(max(0, cb.findData(int(comp))))
        self.table.setCellWidget(r, 0, sp)
        self.table.setCellWidget(r, 1, cb)

    def set_places(self, places):
        self.table.setRowCount(0)
        for pos, comp in places:
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
    def __init__(self, parent, title):
        super().__init__(parent)
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
        self.v.addWidget(bb)
        self.fit()
        try:
            theme.dark_title_bar(self)
        except Exception:
            pass
        return self.exec() == QDialog.Accepted

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
        self.form.addRow("", self.exhibition)
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
        self.form.addRow(_("Cup"), row(self.cup, self.cup_name))
        self.supercup = QCheckBox(_("Super cup (champion v cup winner)"))
        self.supercup.setChecked(bool(L.get("supercup")))
        self.form.addRow("", self.supercup)
        self.cup.toggled.connect(lambda on: self.supercup.setEnabled(on and self.cup.isEnabled()))
        self.form.addRow("", hint(_("a top division of a new country: a national cup for it and the division "
                                    "below, any number of clubs (byes when the field is not 16, 32 ...)")))
        self.lcup = QCheckBox(_("League cup"))
        self.lcup.setChecked(bool(L.get("league_cup")))
        self.lcup_name = QLineEdit(L.get("league_cup_name", ""))
        self.lcup_name.setPlaceholderText(_("(the league's name + League Cup)"))
        self.form.addRow("", row(self.lcup, self.lcup_name))
        self.form.addRow("", hint(_("a knockout of 16, 8 or 4 clubs of this division and the one below, "
                                    "September to December")))
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
        self.above.currentIndexChanged.connect(
            lambda _i: self.season.setEnabled(self.above.currentData() is None and not self.exhibition.isChecked()))
        self.europe.set_confed(project.confeds.get(self.country_name()))
        self.country.currentTextChanged.connect(
            lambda t: self.europe.set_confed(project.confeds.get(B.country_of(t, project.countries))))
        self.exhibition.toggled.connect(lambda _on: self.exhibition_state())
        self.exhibition_state()

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
        self.season.setEnabled(top and not on)

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
        if self.logo.path:
            L["logo"] = self.logo.path
        else:
            L.pop("logo", None)
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


class ClubDialog(Dialog):
    """one club: name, short name, crest -- a new club, or one of the game's"""

    def __init__(self, parent, name, short, crest, was=None, coach=None, formation=None, formations=(),
                 league_formation=""):
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
        self.coach = None
        if coach is not None:              # a new club: its manager's name
            self.coach = QLineEdit(coach)
            self.coach.setMaxLength(45)
            self.coach.setPlaceholderText("FL M0001")
            self.form.addRow(_("Manager"), self.coach)
            self.form.addRow("", hint(_("the manager's name in the game; empty = a numbered one")))
        self.coach_name = coach
        self.formation, self.formation_value = None, formation
        if formation is not None:          # a new club: its formation, or the league's
            from ..pitch import FormationPick, places_of
            first = (_("As the league (%s)") % league_formation if league_formation
                     else _("As the league (the game's default 4-2-3-1)"))
            self.formation = FormationPick(formations, formation, first, places_of(formations, league_formation))
            self.form.addRow(_("Formation"), self.formation)
        if was:
            self.form.addRow("", hint(_("In the game: %s (%s)") % was))
        self.result = None

    def ok(self):
        short = self.short.text().strip()
        if short and (not all(c.isalnum() for c in short) or not B.short_name(short)):
            error(self, "Club", _("The short name takes letters and digits only."))
            return
        self.result = (self.name.text().strip(), B.short_name(short), self.crest.path)
        if self.coach is not None:
            self.coach_name = self.coach.text().strip()
        if self.formation is not None:
            self.formation_value = self.formation.value()
        self.accept()


class GameClubDialog(Dialog):
    """a club the game already has for one place of a new league (the league's "game_clubs",
    leaguebuilder.game_club_checks): the club and, when it plays somewhere in the game, the club
    that takes its place there -- one of the game's that plays in nothing, or a new one"""

    def __init__(self, parent, project, taken, cur=None):
        super().__init__(parent, "Club of the game")
        self.info = B.game_info(project.base)
        cur = cur or {}
        self.clubs = sorted(((t, n, s) for t, (n, s) in self.info["clubs"].items()
                             if t not in taken and B.game_club_problem(self.info, t) is None),
                            key=lambda c: (c[1] or "").lower())
        self.form.addRow(hint(_("The club keeps its name, crest, kits, manager and players. It leaves every "
                                "competition it plays in the game and plays in this league instead.")))
        self.search = QLineEdit()
        self.search.setPlaceholderText(_("Name, short name or team ID"))
        self.search.textChanged.connect(lambda *_a: self.fill())
        self.form.addRow(_("Search"), self.search)
        self.no_league = QCheckBox(_("Only clubs in no league"))
        self.no_league.toggled.connect(lambda *_a: self.fill())
        self.form.addRow("", self.no_league)
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
        self.rb_game = QRadioButton(_("Its place goes to a club of the game that plays in nothing:"))
        self.swap_club = QComboBox()
        self.swap_club.setMinimumWidth(320)
        for t, n, s in self.clubs:
            if not self.info["entries"].get(t):
                self.swap_club.addItem("%s (%s, %d)" % (n, s, t), t)
        self.rb_new = QRadioButton(_("Its place goes to a new club, named:"))
        self.swap_name = QLineEdit()
        self.swap_name.setMaxLength(45)
        grp = QButtonGroup(self)
        grp.addButton(self.rb_game)
        grp.addButton(self.rb_new)
        self.form.addRow(self.rb_game)
        self.form.addRow("", self.swap_club)
        self.form.addRow(self.rb_new)
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
        if pick:
            self.tree.setCurrentItem(pick)
        self.tree.blockSignals(False)
        self.show_swap()

    def chosen(self):
        it = self.tree.currentItem()
        return it.data(0, Qt.UserRole) if it else None

    def show_swap(self):
        t = self.chosen()
        where = B.game_club_where(self.info, t) if t is not None else []
        if t is None:
            self.where.setText(_("Pick a club above."))
        elif where:
            self.where.setText(_("%s plays in %s. Every one of those competitions keeps its number of clubs: "
                                 "pick who takes its place there.") % (self.info["clubs"][t][0], ", ".join(where)))
        else:
            self.where.setText(_("%s plays in nothing: it just moves.") % self.info["clubs"][t][0])
        for w in (self.rb_game, self.swap_club, self.rb_new, self.swap_name):
            w.setEnabled(bool(where))

    def ok(self):
        t = self.chosen()
        if t is None:
            error(self, "Club of the game", _("Pick a club."))
            return
        swap = None
        if B.game_club_where(self.info, t):
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
        self.result = {"id": t, "swap": swap}
        self.accept()


class PreseasonDialog(Dialog):
    """the recipe's pre-season cups (preseason_cups): a name and 4 or 8 invited clubs each, a club
    of a new league ("<league>/<k>") or a club id of the game typed in"""
    SLOTS = 8

    def __init__(self, parent, project):
        super().__init__(parent, "Pre-season cups")
        self.project = project
        self.cups = [{"name": c.get("name", ""), "clubs": list(c.get("clubs") or [])}
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
        self.action("Add lower tier", self.add_lower, tip="A new league one division below the selected one: "
                    "same country, clubs and format, with promotion and relegation between the two")
        self.action("Edit", self.edit)
        self.action("Remove", self.remove, "danger")
        self.action("Pre-season cups", self.preseason, tip="Friendly knockouts of 4 or 8 invited clubs in "
                    "July, before the season")
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
    hint = ("The clubs of one new league. An empty name becomes \"<league> 01\", \"<league> 02\" ...; an "
            "empty short name is made from the name; a club with no crest gets a numbered badge. A place can "
            "also hold a club the game already has: Club of the game.")

    def __init__(self, app):
        super().__init__(app)
        self.action("Edit club", self.edit, "primary")
        self.action("Players", self.players, tip="Change this club's squad")
        self.action("Club of the game...", self.game_club,
                    tip="Put a club the game already has in this place, instead of a new club")
        self.action("New club here", self.new_here, tip="Give this place back to a new club")
        self.action("Insert club", lambda: self.shift(1), tip="A new club before the selected one")
        self.action("Remove club", lambda: self.shift(-1), "danger", tip="Take the selected club out of the league")
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

    def built_ids(self, L):
        """the team ids a build gave this league's clubs, or []: ids are handed out at Build,
        after the game's own clubs"""
        return list(built_league(self.app.game, self.project.recipe.get("world"), L["name"]).get("teams") or [])

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
            pm = pixmap(crests[k], 28)
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
        n = len((pl.get(str(tid)) or {}).get("edits") or {})
        it = QTreeWidgetItem([str(k + 1), name, short, str(tid), _("(the game's)"), str(n) if n else ""])
        sw = e.get("swap")
        if isinstance(sw, dict):
            tip = _("A club of the game. A new club, %s, takes its place in the game.") % sw.get("name", "")
        elif sw is not None:
            tip = _("A club of the game. %s takes its place in the game.") \
                % self.project.game_cl.get(int(sw), (str(sw), ""))[0]
        else:
            tip = _("A club of the game that played in no competition.")
        for c in range(6):
            it.setToolTip(c, tip)
        it.setForeground(4, QBrush(QColor(theme.SUBTLE)))
        it.setData(0, Qt.UserRole, k)
        return it

    def current(self):
        it = self.tree.currentItem()
        return it.data(0, Qt.UserRole) if it else None

    def taken(self, skip):
        """the clubs of the game the recipe already uses, in a place or taking one, but the one
        at place `skip` of the league shown"""
        out = set()
        cur = self.league()
        for L in self.project.recipe["leagues"]:
            for e in L.get("game_clubs") or []:
                if L is cur and int(e.get("at", -1)) == skip:
                    continue
                out.add(int(e["id"]))
                if e.get("swap") is not None and not isinstance(e["swap"], dict):
                    out.add(int(e["swap"]))
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
            gc = [x for x in L.get("game_clubs") or [] if int(x.get("at", -1)) != k]
            L["game_clubs"] = sorted(gc + [e], key=lambda x: int(x["at"]))
            self.project.touch()

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
        self.say(_("%s now has %d clubs: check its European places on the New leagues page, then Build again "
                   "and start a new career.") % (L["name"], L["clubs"]), "ok")

    def edit(self):
        L, k = self.league(), self.current()
        if not L or k is None:
            return
        if k in self.game_places(L):
            QMessageBox.information(self, _("New clubs"), _("This is a club of the game: rename it or change its "
                                                             "crest on Game's leagues and clubs, or pick another one "
                                                             "with Club of the game."))
            return
        names, abbrs, crests = self.lists(L)
        coaches = list(L.get("club_coaches") or [])[:L["clubs"]]
        coaches += [""] * (L["clubs"] - len(coaches))
        forms = list(L.get("club_formations") or [])[:L["clubs"]]
        forms += [""] * (L["clubs"] - len(forms))
        d = ClubDialog(self, names[k], abbrs[k], crests[k], coach=coaches[k], formation=forms[k],
                       formations=self.project.formations(), league_formation=L.get("formation", ""))
        if d.finish() and d.result:
            names[k], abbrs[k], crests[k] = d.result
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
        self.uecl = QCheckBox(_("Include the Conference League"))
        self.uecl.setToolTip(_("A league phase of 36 clubs and a February play-off, like the Champions League "
                               "and the Europa League"))
        self.uecl.toggled.connect(self.set_uecl)
        self.outer.addWidget(row(self.uecl, hint(_("off = no Conference League; the Champions League and Europa "
                                                   "League keep their 36-club league phase and play-off either way"))))
        self.b_euro = QPushButton(_("Only the new European cups..."))
        self.b_euro.setToolTip(_("A world with nothing but the new Champions League and Europa League (league "
                                 "phase of 36 and play-off) and, when ticked above, the Conference League: "
                                 "no new leagues, the game's clubs and leagues as they are. Your recipe is "
                                 "not changed."))
        self.b_euro.clicked.connect(self.do_europe_only)
        self.outer.addWidget(row(self.b_euro, hint(_("for the new European format alone, without building "
                                                     "any league"))))
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

    def refresh(self):
        g = self.app.game
        w = self.project.recipe.get("world", "")
        self.uecl.blockSignals(True)
        self.uecl.setChecked(bool(self.project.recipe.get("uecl", True)))
        self.uecl.blockSignals(False)
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
            pl = B.plan({"world": name, "leagues": [], "edits": {}, "players": {}, "uecl": uecl}, self.project.base)
        except B.BuildError as e:
            self.out.clear()
            self.say(_("error: %s") % tr(str(e)))
            return
        game, base = self.app.game.folder, self.project.base

        def go(log):
            log(B.describe(pl))
            log(_("building ..."))
            B.build(pl, base, game, replace, log=log)
            log("\n" + _("Next: switch %s on (it takes the place of any other world), then start the game "
                          "and start a new Master League career.") % name)

        def switch():
            if ask(self, title, _("Make %s the live world in sider.ini?") % name):
                def on(log):
                    snapshot(self.app.game.ini_path, "League Builder: switch on " + name, self.app.game.sider_dir)
                    B.switch_on(name, self.app.game.folder, log=log)
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
            log("\n" + _("Next: 3. Switch it on, then start the game."))
            note = exhibition_note(pl)
            if note:
                log("\n" + note)
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
