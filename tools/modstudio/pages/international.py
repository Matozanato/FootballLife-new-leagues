"""Cups > International: FIFA's club competitions of the world (feature/cwc32).

The Intercontinental Cup is the game's own Club World Cup of today -- four clubs, the continental
champions, a semi-final and a final in mid-December -- and is always listed. "Add Club World Cup"
puts the Club World Cup of 32 into the world (the recipe's club_world_cup, leaguebuilder.cwc_config):
competition 1 becomes the 2025 format, and the four-club cup can stay as the Intercontinental, a
competition of its own. With no free competition id the Intercontinental takes the ids of a cup the
world builds, picked here (that cup is unticked in its league on Apply).
"""
import json
import os
import re
from copy import deepcopy

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidgetItem, QSplitter, QLabel,
                               QFormLayout, QScrollArea, QCheckBox, QPushButton, QSizePolicy, QLayout,
                               QSpinBox, QLineEdit, QTreeWidget, QTreeWidgetItem, QAbstractItemView)

import leaguebuilder as B
from .. import filecache
from ..i18n import _
from ..ui import hint, row, ask, helped
from .builder import PictureField
from .continental import CompetitionList
from .cup_editors import CupConflict

IC, CWC = "intercontinental", "club_world_cup"
DEFAULTS = {"on": False, "every": 4, "first": 2029, "keep_old": True, "old_name": B.CWC_OLD_NAME, "replace": None,
            "logo": None}
# the Intercontinental's logo is the game's Club World Cup's (competition 1): edits.competitions,
# as Competition Names keeps it, whether the cup of 32 is on or not (leaguebuilder.picture_jobs)
IC_LOGO = "ic_logo"
IC_CID = str(B.CLUB_WORLD_CUP_CID)


def ic_logo(recipe):
    return (((recipe.get("edits") or {}).get("competitions") or {}).get(IC_CID) or {}).get("logo") or None


def put_ic_logo(recipe, path):
    """edits.competitions["1"].logo = path (an entry with neither name nor logo goes); True when changed"""
    if ic_logo(recipe) == (path or None):
        return False
    comps = recipe.setdefault("edits", {}).setdefault("competitions", {})
    entry = comps.setdefault(IC_CID, {})
    if path:
        entry["logo"] = path
    else:
        entry.pop("logo", None)
        if not (entry.get("name") or "").strip():
            comps.pop(IC_CID, None)
    return True

CWC_INFO = ("32 clubs, the 2025 format: eight groups of four played once, then a single-match knockout "
            "of sixteen, in June after the Champions League final. The draw is in late November of the "
            "year before.")
CWC_FIELD = ("12 UEFA, 6 CONMEBOL, 5 AFC, 4 CAF, 4 CONCACAF and 1 OFC. Each confederation takes the "
             "champions of its continental cup of the four seasons before the cup (a club with two titles "
             "counts once); the places left go to its best clubs in the confederation ranking (the points of "
             "the four seasons). The OFC place is the best OFC club of the OFC ranking; a world with no OFC "
             "club in the ranking gives it to the AFC. A place a confederation cannot fill (a world without its "
             "continental cup or its clubs) goes to the best club of the whole ranking not yet in, whatever its "
             "confederation. Any number of clubs of one country.")
CWC_NOTE = ("Build and install puts it in the game, with Mod Studio's modules. Start a new career "
            "afterwards: a career saved before keeps the old cup. Master League and League Mode get the "
            "confederation rankings (UEFA, CONMEBOL, CONCACAF, AFC, CAF and OFC) in Data > Ranking CWC.")
IC_INFO = ("The game's own Club World Cup: four clubs -- the continental champions -- a semi-final and a "
           "final in mid-December.")
IC_ALONE = ("In the game it is still the Club World Cup. Add the Club World Cup of 32 below to have both: "
            "this one then becomes a cup of its own under the name above, every December.")
IC_KEEP_HELP = ("The game's own Club World Cup -- four clubs, the continental champions, a semi-final and a "
                "final in mid-December -- stays in the world as a competition of its own, played every season "
                "under its name (the real Intercontinental Cup is that tournament).\n\n"
                "It needs a competition id of its own. When none is free, pick a cup of your world below: that "
                "cup is no longer built (it is unticked in its league), and the Intercontinental takes its "
                "place. A league cannot be given away here: take a league out on the Leagues page instead.\n\n"
                "Off: the old cup is gone, and the Club World Cup of 32 is the only one.")


def last_build(project):
    """(the plan of the world's last Build, its tables' folder or the game's): what is built now"""
    world = project.recipe.get("world") or ""
    game = getattr(getattr(project, "app", None), "game", None)
    livecpk = getattr(game, "livecpk_dir", "") if game is not None else ""
    root = os.path.join(livecpk, world) if world and livecpk else ""
    path = os.path.join(root, "leaguebuilder-plan.json") if root else ""
    try:
        plan = filecache.json_file(path) if path and os.path.exists(path) else None
    except (OSError, ValueError):
        plan = None                                 # a world never built, or a plan being written
    db = os.path.join(root, "common", "etc", "pesdb") if root else ""
    if not db or not os.path.exists(os.path.join(db, "CompetitionRegulation.bin")):
        db = project.base
    return (plan if isinstance(plan, dict) else {}), db


def config(recipe):
    """the editor's values of the recipe's club_world_cup (DEFAULTS when there is none)"""
    c = dict(DEFAULTS, **(recipe.get(CWC) or {}))
    c["on"] = bool(c.get("on"))
    c["keep_old"] = bool(c.get("keep_old", True))
    try:
        c["every"], c["first"] = int(c.get("every") or 4), int(c.get("first") or 2029)
    except (TypeError, ValueError):
        c["every"], c["first"] = 4, 2029
    if not c.get("old_name") or c["old_name"] in B.CWC_OLD_NAMES:
        c["old_name"] = B.CWC_OLD_NAME
    out = {k: c.get(k) for k in DEFAULTS}
    out[IC_LOGO] = ic_logo(recipe)
    return out


class InternationalEditor(QWidget):
    changed = Signal()
    requires_tables = False

    @staticmethod
    def refresh_inputs(project):
        recipe = project.recipe
        return (json.dumps(recipe.get(CWC), sort_keys=True), ic_logo(recipe),
                [((L.get("name") or ""), bool(L.get("cup")), bool(L.get("supercup")))
                 for L in recipe.get("leagues") or []],
                [(g.get("league"), bool(g.get("super_cup")), bool(g.get("league_cup")))
                 for g in recipe.get("game_cups") or []])

    def __init__(self, parent, project, draft=None):
        super().__init__(parent)
        self.project = project
        self.rows = (IC, CWC)
        self._values = config(project.recipe)
        self._initial = dict(self._values)
        self._loading = False
        self.plan, self.db = last_build(project)
        self.last_ids = self.plan.get("cup_ids") or {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(hint(_("FIFA's club competitions of your world. Changes reach the game after Build and install.")))
        self.splitter = QSplitter(Qt.Horizontal)
        pane = QWidget()
        pane.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Ignored)
        left = QVBoxLayout(pane)
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(8)
        self.list = CompetitionList(pane)
        left.addWidget(self.list)
        self.add_button = QPushButton(_("Add Club World Cup"))
        self.add_button.setObjectName("primary")
        self.add_button.clicked.connect(self.add_cwc)
        left.addWidget(self.add_button)
        left.addStretch(1)
        self.splitter.addWidget(pane)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        detail = QWidget()
        self.right = right = QVBoxLayout(detail)
        right.setContentsMargins(12, 0, 4, 4)
        right.setSizeConstraint(QLayout.SetMinimumSize)
        self.title = QLabel()
        self.title.setObjectName("cardtitle")
        self.title.setWordWrap(True)
        right.addWidget(self.title)
        # -- the Intercontinental
        self.ic_body = QWidget()
        icv = QVBoxLayout(self.ic_body)
        icv.setContentsMargins(0, 0, 0, 0)
        self.ic_info = QLabel(_(IC_INFO))
        self.ic_info.setWordWrap(True)
        icv.addWidget(self.ic_info)
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.keep = QCheckBox(_("Keep it, every December, as a cup of its own"))
        self.keep.toggled.connect(lambda on: self.set("keep_old", on))
        form.addRow(helped(self.keep, _(IC_KEEP_HELP), "Intercontinental Cup"))
        self.name = QLineEdit()
        self.name.setMaxLength(60)
        self.name.textChanged.connect(lambda s: self.set("old_name", s.strip() or B.CWC_OLD_NAME))
        form.addRow(_("Name"), self.name)
        self.ic_logo = PictureField(None, 64, empty="(the game's own)")
        self.ic_logo.changed = lambda: self.set(IC_LOGO, self.ic_logo.path)
        form.addRow(_("Logo"), self.ic_logo)
        icv.addLayout(form)
        self.ic_state = QLabel("")
        self.ic_state.setWordWrap(True)
        icv.addWidget(self.ic_state)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([_("Competition"), _("Competition ID")])
        self.tree.setRootIsDecorated(True)
        self.tree.setMinimumHeight(220)
        self.tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tree.itemSelectionChanged.connect(self.tree_picked)
        icv.addWidget(self.tree)
        right.addWidget(self.ic_body)
        # -- the Club World Cup of 32
        self.cwc_body = QWidget()
        cv = QVBoxLayout(self.cwc_body)
        cv.setContentsMargins(0, 0, 0, 0)
        for text in (CWC_INFO, CWC_FIELD):
            label = QLabel(_(text))
            label.setWordWrap(True)
            cv.addWidget(label)
        self.cwc_short = QLabel("")         # the confederations the last Build has no cup for
        self.cwc_short.setWordWrap(True)
        self.cwc_short.setStyleSheet("color: #c0392b;")
        cv.addWidget(self.cwc_short)
        f2 = QFormLayout()
        f2.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.every = QSpinBox()
        self.every.setRange(1, B.CWC_EVERY_MAX)
        self.every.valueChanged.connect(lambda v: self.set("every", v))
        self.first = QSpinBox()
        self.first.setRange(2000, 2200)
        self.first.valueChanged.connect(lambda v: self.set("first", v))
        f2.addRow(_("Every"), row(self.every, QLabel(_("years, first in")), self.first, "stretch"))
        self.cwc_logo = PictureField(None, 64, empty="(the game's own)")
        self.cwc_logo.changed = lambda: self.set("logo", self.cwc_logo.path)
        f2.addRow(_("Logo"), self.cwc_logo)
        cv.addLayout(f2)
        cv.addWidget(hint(_("4 and 2029 as FIFA plays it; 1 plays it every season.")))
        cv.addWidget(hint(_(CWC_NOTE)))
        self.remove_button = QPushButton(_("Remove Club World Cup"))
        self.remove_button.clicked.connect(self.remove_cwc)
        cv.addWidget(row(self.remove_button, "stretch"))
        right.addWidget(self.cwc_body)
        right.addStretch()
        scroll.setWidget(detail)
        self.splitter.addWidget(scroll)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 3)
        self.splitter.setSizes([240, 650])
        layout.addWidget(self.splitter, 1)
        self.list.currentItemChanged.connect(lambda *_a: self.show_selected())
        self.fill_tree()
        self.sync()

    # ---- values ----
    def set(self, key, value):
        if self._loading or self._values.get(key) == value:
            return
        self._values[key] = value
        self.show_state()
        self.changed.emit()

    def dirty_keys(self):
        v, i = self._values, self._initial
        logo = {IC_LOGO} if v.get(IC_LOGO) != i.get(IC_LOGO) else set()   # written on or off
        if not v["on"] and not i["on"]:
            return logo                               # nothing else of it is written while it is off
        return {k for k in DEFAULTS if v.get(k) != i.get(k)} | logo

    def draft(self):
        return {"values": deepcopy(self._values), "initial": deepcopy(self._initial), "view": self.view_state()}

    def restore_draft(self, draft):
        self._values.update(draft.get("values") or {})
        self._initial.update(draft.get("initial") or {})
        self.fill_tree()
        self.sync()
        self.restore_view(draft.get("view") or {})

    def view_state(self):
        it = self.list.currentItem()
        return {"selected": it.data(Qt.UserRole) if it is not None else IC, "sizes": self.splitter.sizes()}

    def restore_view(self, view):
        want = view.get("selected") or IC
        for i in range(self.list.count()):
            if self.list.item(i).data(Qt.UserRole) == want:
                self.list.setCurrentRow(i)
        if view.get("sizes"):
            self.splitter.setSizes(view["sizes"])

    def reconcile(self):
        self.plan, self.db = last_build(self.project)
        self.last_ids = self.plan.get("cup_ids") or {}
        self.fill_tree()
        self.show_state()

    # ---- the list ----
    def sync(self):
        """the widgets from the values"""
        self._loading = True
        v = self._values
        keep_sel = self.view_state()["selected"] if self.list.count() else IC
        self.list.clear()
        ic = QListWidgetItem(v["old_name"] if v["on"] else _(B.CWC_OLD_NAME))
        ic.setData(Qt.UserRole, IC)
        self.list.addItem(ic)
        if v["on"]:
            it = QListWidgetItem(_("Club World Cup"))
            it.setData(Qt.UserRole, CWC)
            self.list.addItem(it)
        self.add_button.setVisible(not v["on"])
        self.keep.setChecked(bool(v["keep_old"]))
        self.name.setText(v["old_name"] if v["old_name"] not in B.CWC_OLD_NAMES else _(B.CWC_OLD_NAME))
        self.every.setValue(int(v["every"]))
        self.first.setValue(int(v["first"]))
        for field, key in ((self.ic_logo, IC_LOGO), (self.cwc_logo, "logo")):
            field.path = v.get(key) or None
            field.show_it()
        self._loading = False
        self.restore_view({"selected": keep_sel if v["on"] or keep_sel == IC else IC})
        if self.list.currentRow() < 0:
            self.list.setCurrentRow(0)
        self.show_selected()

    def show_selected(self):
        it = self.list.currentItem()
        key = it.data(Qt.UserRole) if it is not None else IC
        self.ic_body.setVisible(key == IC)
        self.cwc_body.setVisible(key == CWC)
        self.title.setText(_("Club World Cup") if key == CWC else
                           (self._values["old_name"] if self._values["on"] else _(B.CWC_OLD_NAME)))
        self.show_state()

    def add_cwc(self):
        self._values["on"] = True
        self.sync()
        for i in range(self.list.count()):
            if self.list.item(i).data(Qt.UserRole) == CWC:
                self.list.setCurrentRow(i)
        self.changed.emit()

    def remove_cwc(self):
        self._values["on"] = False
        self.sync()
        self.changed.emit()

    # ---- the Intercontinental's competition id ----
    def free_ids(self):
        if not self.db:
            return None
        try:
            cids, _regs = B.free_comp_ids(self.db, low=self.plan.get("low_cids"))
        except (OSError, ValueError, TypeError, B.BuildError, SystemExit):
            return None
        held = {w.get("cid") for k, w in self.last_ids.items() if isinstance(w, dict) and k != B.CWC_KEY_IC}
        return [c for c in cids if c not in held]

    def fill_tree(self):
        self.tree.blockSignals(True)
        self.tree.clear()
        chosen = self._values.get("replace")
        groups = {}
        for key, label in (("league", "Leagues"), ("cup", "Cups"), ("super", "Super cups")):
            it = QTreeWidgetItem([_(label), ""])
            it.setFlags(Qt.ItemIsEnabled)
            f = it.font(0)
            f.setBold(True)
            it.setFont(0, f)
            self.tree.addTopLevelItem(it)
            groups[key] = it
        mine = B.cwc_replaceable(self.project.recipe, self.last_ids)
        if chosen and not any(k == chosen for _g, k, _n, _c in mine):
            ids = self.last_ids.get(B.CWC_KEY_IC) or self.last_ids.get(B.cwc_last_key(chosen)) or {}
            mine.append(("super" if chosen.startswith(("super:", "gsuper:")) else "cup", chosen,
                         chosen.partition(":")[2], ids.get("cid")))
        made, pick = set(), None
        for g, key, name, cid in sorted(mine, key=lambda e: (e[0], e[2].casefold())):
            it = QTreeWidgetItem([name, "" if cid is None else str(cid)])
            it.setData(0, Qt.UserRole, key)
            it.setToolTip(0, _("A cup your world builds: it is no longer built, and the Intercontinental takes its place"))
            groups[g].addChild(it)
            if isinstance(cid, int):
                made.add(cid)
            if key == chosen:
                pick = it
        try:
            rows = B.competition_ids(self.db, self.project.base) if self.db else []
        except (OSError, ValueError, TypeError, B.BuildError, SystemExit):
            rows = []
        superish = re.compile(r"super|supercopa|supercoppa|shield|troph[eé]e des champions|recopa|community", re.I)
        own = {w.get("cid") for w in self.last_ids.values() if isinstance(w, dict)}
        for cid, _regs, name, kind, _new in rows:
            if cid in made or cid in own or cid == 1:
                continue
            g = "league" if kind == "league" else "super" if superish.search(name or "") else "cup"
            it = QTreeWidgetItem([name or "?", str(cid)])
            it.setFlags(Qt.NoItemFlags)
            it.setToolTip(0, _("A league cannot give its place here: take it out on the Leagues page")
                          if g == "league" else _("A competition of the game or a continental one: it stays"))
            groups[g].addChild(it)
        groups["league"].setExpanded(False)
        groups["cup"].setExpanded(True)
        groups["super"].setExpanded(True)
        for c in range(2):
            self.tree.resizeColumnToContents(c)
        if pick is not None:
            pick.setSelected(True)
            self.tree.scrollToItem(pick)
        self.tree.blockSignals(False)

    def tree_picked(self):
        it = next(iter(self.tree.selectedItems()), None)
        self.set("replace", it.data(0, Qt.UserRole) if it is not None else None)

    def needs_pick(self):
        """True when the Intercontinental has no competition id unless a cup is picked"""
        v = self._values
        if not (v["on"] and v["keep_old"]) or v.get("replace"):
            return False
        own = self.last_ids.get(B.CWC_KEY_IC)
        free = self.free_ids()
        return not (isinstance(own, dict) and own.get("cid")) and free is not None and not free

    def show_state(self):
        v = self._values
        on, keep = v["on"], v["keep_old"]
        for w in (self.keep,):
            w.setEnabled(on)
        for w in (self.name, self.tree):
            w.setEnabled(on and keep)
        self.ic_info.setText(_(IC_INFO))
        short = B.cwc_short_confeds(self.plan) if self.plan else []
        self.cwc_short.setText(_("Last Build: %s") % " ".join(
            _(B.cwc_short_text([s])) for s in short) if short else "")
        self.cwc_short.setVisible(bool(short))
        if not on:
            text = _(IC_ALONE)
        elif not keep:
            text = _("Not kept: the Club World Cup of 32 is the only one, and no competition id is needed.")
        else:
            own = self.last_ids.get(B.CWC_KEY_IC)
            free = self.free_ids()
            if v.get("replace"):
                text = _("It takes the place of the cup picked below; that cup is no longer built.")
            elif isinstance(own, dict) and own.get("cid"):
                text = _("It keeps its competition id of the last Build (%d).") % own["cid"]
            elif free is None:
                text = _("The world's tables could not be read: pick a cup below to be safe.")
            elif free:
                text = _("Free competition ids: %d -- it takes one, nothing to pick.") % len(free)
            else:
                text = _("No free competition id: the world has all the 255 the game takes. Pick a cup below for "
                         "it to take the place of.")
        self.ic_state.setText(text)
        self.tree.setVisible(on and keep)
        it = self.list.item(0)
        if it is not None:
            it.setText(v["old_name"] if on else _(B.CWC_OLD_NAME))

    # ---- Apply ----
    def apply(self, recipe):
        v = self._values
        if self.needs_pick():
            raise CupConflict(_("No free competition id for the Intercontinental Cup. Pick a cup for it to take "
                                "the place of, or untick \"Keep it\"."))
        key = v.get("replace") if v["on"] and v["keep_old"] else None
        before = json.dumps(recipe.get(CWC), sort_keys=True)
        if key and key != (recipe.get(CWC) or {}).get("replace"):
            name = next((n for _g, k, n, _c in B.cwc_replaceable(recipe, self.last_ids) if k == key), key)
            if not ask(self, "Intercontinental Cup", _("%s is no longer built: it is unticked in its league, and the "
                                                       "Intercontinental takes its competition id. Go on?") % name):
                raise CupConflict(_("Not applied: your changes are kept."))
        changed = False
        if key:
            changed = B.cwc_untick(recipe, key) or changed
        if v["on"]:
            recipe[CWC] = {"on": True, "every": int(v["every"]), "first": int(v["first"]),
                           "keep_old": bool(v["keep_old"]), "old_name": v["old_name"] or B.CWC_OLD_NAME,
                           "replace": key, "logo": v.get("logo") or None}
            if not recipe[CWC]["logo"]:
                recipe[CWC].pop("logo")
        else:
            recipe.pop(CWC, None)
        after = json.dumps(recipe.get(CWC), sort_keys=True)
        changed = changed or after != before
        changed = put_ic_logo(recipe, v.get(IC_LOGO)) or changed
        if v["on"] and not self._initial["on"]:
            # the 32-club draw is fl26swiss.dll's and the rankings fl26contrank's / fl26cwc's: Mod
            # Studio's modules of this version must be in the game (Build and install puts them too)
            app = getattr(self.project, "app", None)
            build = app.page("Build") if app is not None and hasattr(app, "page") else None
            if build is not None and hasattr(build, "do_install"):
                QTimer.singleShot(0, build.do_install)
        return changed
