"""Stadiums: stadium-server's home stadiums, competition stadiums and finals"""
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QCheckBox, QLabel, QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

import lbstadiums as L
from .. import theme
from ..i18n import _
from ..ui import hint, row, ask, error, run_job
from .content import ServerPage

TID = Qt.UserRole + 1


class WorldClubs(QWidget):
    """the home stadiums of a ready world's clubs (one from Import your world): it is not built on
    this PC, so they are picked here, by hand or with Find automatically, and kept in
    livecpk\\<world>\\fl26stadiums.json (lbstadiums.load_edits); Save writes map_teams.txt as
    Switch on does"""

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.world = self.pl = self.lib = None
        self.edits, self.auto = {}, set()          # edits: as saved + changes; auto: proposed, not saved yet
        self.saved = {}
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 8, 0, 0)
        v.addWidget(hint(_("The home stadiums of the clubs of a world you imported (a modpack). It names the "
                           "stadiums of its maker's stadium pack: the ones your pack does not have can be "
                           "picked here from yours, by hand or with Find automatically. Your picks stay with "
                           "a new version of the world.")))
        self.search = QLineEdit()
        self.search.setPlaceholderText(_("Find a club, a league or a stadium..."))
        self.search.textChanged.connect(self.fill)
        self.missing = QCheckBox(_("Only clubs without their stadium"))
        self.missing.toggled.connect(self.fill)
        v.addWidget(row(self.search, self.missing))
        self.tree = QTreeWidget()
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.tree.setHeaderLabels([_("Club"), _("League"), _("Home stadium"), _("In your stadium pack")])
        for c, w in enumerate((220, 220, 280)):
            self.tree.setColumnWidth(c, w)
        self.tree.itemDoubleClicked.connect(lambda *_a: self.pick())
        v.addWidget(self.tree, 1)
        self.b_pick = QPushButton(_("Choose a stadium..."))
        self.b_pick.clicked.connect(self.pick)
        self.b_game = QPushButton(_("The game's stadium"))
        self.b_game.clicked.connect(lambda: self.set_selected(None))
        self.b_back = QPushButton(_("The world's stadium"))
        self.b_back.clicked.connect(self.back)
        self.b_auto = QPushButton(_("Find automatically"))
        self.b_auto.clicked.connect(self.find_auto)
        self.b_save = QPushButton(_("Save"))
        self.b_save.setObjectName("primary")
        self.b_save.clicked.connect(self.save)
        self.b_undo = QPushButton(_("Discard"))
        self.b_undo.clicked.connect(self.discard)
        v.addWidget(row(self.b_pick, self.b_game, self.b_back, self.b_auto, "stretch", self.b_undo, self.b_save,
                        stretch=False))
        self.note = QLabel("")
        self.note.setWordWrap(True)
        v.addWidget(self.note)
        self.buttons = (self.b_pick, self.b_game, self.b_back, self.b_auto, self.b_save, self.b_undo)

    # ---- the world ----

    def ready(self):
        """the ready world in the game, None for none"""
        from .. import installer as I
        g = self.app.game
        try:
            if not g.ok():
                return None
            return next((w for w in self.app.project.live_worlds() if I.ready_world(g, w)), None)
        except Exception:
            return None

    def root(self):
        return os.path.join(self.app.game.livecpk_dir, self.world)

    def refresh(self):
        if self.changed():
            return                                 # changes not saved yet stay on screen
        w = self.ready()
        self.lib = L.library(self.app.game.sider_dir) if w else None
        if w is None:
            self.world = self.pl = None
            self.tree.clear()
            self.say(_("No imported world is in the game. A world you build has its stadiums in Build: Edit "
                       "club > Home stadium."))
            self.enable(False)
            return
        if not self.lib:
            self.say(_("Stadium Server is not installed: there is no stadium pack to pick from."), theme.WARN)
        self.world = w
        self.enable(False)
        self.say(_("Reading %s ...") % w)
        plan = os.path.join(self.root(), "leaguebuilder-plan.json")

        def job(progress):
            from .. import filecache
            return filecache.json_file(plan)

        def done(pl):
            self.pl = pl
            self.saved = L.load_edits(self.root())
            self.edits, self.auto = dict(self.saved), set()
            self.fill()
            self.enable(True)

        def failed(tb):
            self.say(_("The world's plan could not be read: %s") % tb.strip().splitlines()[-1], theme.WARN)
        run_job(job, done, failed)

    def enable(self, on):
        for b in self.buttons:
            b.setEnabled(on and bool(self.lib) or b in (self.b_game, self.b_back, self.b_save, self.b_undo) and on)

    def say(self, text, color=None):
        self.note.setText(text)
        self.note.setStyleSheet("color: %s;" % color if color else "")

    def changed(self):
        return self.world is not None and (self.edits != self.saved or bool(self.auto))

    # ---- the table ----

    def entry(self, tid, want=None):
        """(stadium entry or None, where it comes from: "world" / "yours" / "auto" / "game")"""
        if tid in self.edits:
            return self.edits[tid], ("auto" if tid in self.auto else "yours") if self.edits[tid] else "game"
        st = (L.wanted(self.pl) if want is None else want).get(tid, (None, None))[1]
        return st, "world" if st else "game"

    def fill(self):
        if self.pl is None:
            return
        q = self.search.text().strip().lower()
        sel = {it.data(0, TID) for it in self.tree.selectedItems()}
        self.tree.clear()
        want = L.wanted(self.pl)
        own = self.own_lines()
        n = have = 0
        for tid, _key, name, league in L.clubs(self.pl):
            st, src = self.entry(tid, want)
            folder = str((st or {}).get("folder") or "")
            found = L.find(self.lib, folder) if st and self.lib and not L.problem(st) else None
            if st:
                n += 1
                have += 1 if found else 0
            if self.missing.isChecked() and (found or not st):
                continue
            if st:
                label = st.get("name") or os.path.basename(folder)
            else:
                label = own.get(tid) or _("the game's stadium")
            if src == "game":
                status = _("a line of your stadium pack") if tid in own else _("the game's stadium")
            elif found:
                status = {"world": _("yes"), "yours": _("yes, picked by you"),
                          "auto": _("found automatically (not saved yet)")}[src]
            else:
                status = _("no: the club plays at the game's stadium")
            if q and q not in ("%s %s %s" % (name, league, label)).lower():
                continue
            it = QTreeWidgetItem([name, league, label, status])
            it.setData(0, TID, tid)
            it.setToolTip(2, folder)
            if st and not found and src != "game":
                for k in range(4):
                    it.setForeground(k, QBrush(QColor(theme.WARN)))
            elif src in ("yours", "auto"):
                it.setForeground(3, QBrush(QColor(theme.GOOD)))
            self.tree.addTopLevelItem(it)
            if tid in sel:
                it.setSelected(True)
        msg = _("%s: %d of %d clubs have their home stadium in your pack.") % (self.world, have, n)
        if self.changed():
            msg += " " + _("Changes not saved yet.")
        self.say(msg, theme.GOOD if have == n and not self.changed() else theme.WARN)

    def own_lines(self):
        """{team id: stadium name} of the lines of the stadium pack itself (not ours) in map_teams.txt"""
        out = {}
        if not self.lib:
            return out
        for line in L.read(os.path.join(self.lib, L.FILE))[0]:
            m = L.LINE.match(line)
            if m and not m.group(1) and L.TAG not in line:
                parts = [x.strip() for x in line.split("#")[0].split(",")]
                if len(parts) >= 3:
                    out[int(m.group(2))] = parts[2]
        return out

    def selected(self):
        return [it.data(0, TID) for it in self.tree.selectedItems()]

    # ---- changes ----

    def set_selected(self, st):
        tids = self.selected()
        if not tids:
            return
        for tid in tids:
            self.edits[tid] = dict(st) if st else None
            self.auto.discard(tid)
        self.fill()

    def pick(self):
        tids = self.selected()
        if not tids or not self.lib:
            return
        from .builder import StadiumPicker
        cur = self.entry(tids[0])[0] or {}
        d = StadiumPicker(self, self.lib, str(cur.get("folder") or ""))
        if d.exec() and d.choice:
            self.set_selected({"folder": d.choice, "slot": L.stadium_slot(os.path.join(self.lib, d.choice)),
                               "name": os.path.basename(d.choice)})

    def back(self):
        for tid in self.selected():
            self.edits.pop(tid, None)
            self.auto.discard(tid)
        self.fill()

    def find_auto(self):
        if self.pl is None or not self.lib:
            return
        got = L.suggest(self.pl, self.lib, self.edits)
        for tid, (st, _how) in got.items():
            self.edits[tid] = st
            self.auto.add(tid)
        self.fill()
        self.say(self.note.text() + " " + (_("Found %d stadium(s) automatically: check them and press Save.") % len(got)
                                           if got else _("Nothing more found automatically.")), theme.WARN)

    def discard(self):
        if self.changed() and not ask(self, "Discard changes", _("Forget the changes you have not saved?")):
            return
        self.edits, self.auto = dict(self.saved), set()
        self.fill()

    def save(self):
        if self.world is None or self.pl is None:
            return
        g, _s = self.app.game.running()
        if g and not ask(self, "Stadiums", _("The game is running. It reads the home stadiums when it starts: "
                                             "restart it after saving. Save now?")):
            return
        from ..backups import snapshot
        path = os.path.join(self.lib or os.path.join(self.app.game.sider_dir, L.FOLDER), L.FILE)
        log = []
        try:
            if os.path.exists(path):
                snapshot(path, "Stadiums: " + self.world, self.app.game.sider_dir)
            L.save_edits(self.root(), self.edits)
            L.write(self.pl, self.app.game.sider_dir, log.append, self.edits)
        except OSError as e:
            error(self, "Stadiums", _("Could not save: %s") % e)
            return
        self.saved, self.auto = dict(self.edits), set()
        self.app.bus.content_changed.emit()
        self.fill()


class Stadiums(ServerPage):
    title = "Stadiums"
    hint = "Where each club plays at home, and where the cups and finals are played."
    server = "stadiums"

    def extra_tabs(self):
        self.clubs = WorldClubs(self.app)
        return [("Your world's clubs", self.clubs)]

    def refresh(self):
        super().refresh()
        self.clubs.refresh()
