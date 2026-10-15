"""Stadiums: stadium-server's home stadiums, competition stadiums and finals"""
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (QCheckBox, QInputDialog, QLabel, QLineEdit, QPushButton, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget)

import lbgamestadiums as G
import lbstadiums as L
from .. import theme
from ..i18n import _
from ..ui import hint, row, ask, error, run_job
from .content import ServerPage

TID = Qt.UserRole + 1


class WorldClubs(QWidget):
    """the home stadiums of a ready world's clubs (one from Import your world, not built on this PC):

      - the game's stadium of each new club (Team.bin +0x3C, lbgamestadiums): Game stadiums
        automatically picks one of the game's for every club, as Build does since 0.2.4, or one
        is chosen by hand; Save writes the world's Team.bin;
      - a stadium of the player's stadium pack over it (map_teams.txt, lbstadiums), picked by hand
        or found by name.

    What the player changed is kept in livecpk\\<world>\\fl26stadiums.json and goes to a new
    version of the world too"""

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.world = self.pl = self.lib = None
        self.edits, self.saved, self.auto = {}, {}, set()      # stadium pack: picks, as saved, proposed
        self.game, self.game_was = {}, {}                     # game stadiums: now, in Team.bin
        self.hand, self.hand_saved = {}, {}                   # chosen by hand
        self.auto_on = self.auto_saved = False                # Game stadiums automatically pressed
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 8, 0, 0)
        v.addWidget(hint(_("The home stadiums of the clubs of a world you imported (a modpack). Every new club "
                           "plays at one of the game's stadiums: give them all one automatically or choose one "
                           "for a club. A stadium of your stadium pack, when the club has one, is played in "
                           "its place. Save, then start a new Master League.")))
        self.search = QLineEdit()
        self.search.setPlaceholderText(_("Find a club, a league or a stadium..."))
        self.search.textChanged.connect(self.fill)
        self.missing = QCheckBox(_("Only clubs whose pack stadium you do not have"))
        self.missing.toggled.connect(self.fill)
        v.addWidget(row(self.search, self.missing))
        self.tree = QTreeWidget()
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.tree.setHeaderLabels([_("Club"), _("League"), _("Game stadium"), _("Stadium pack")])
        for c, w in enumerate((220, 220, 230)):
            self.tree.setColumnWidth(c, w)
        self.tree.itemDoubleClicked.connect(lambda *_a: self.pick_game())
        v.addWidget(self.tree, 1)
        self.b_auto_game = QPushButton(_("Game stadiums automatically"))
        self.b_auto_game.setObjectName("primary")
        self.b_auto_game.clicked.connect(self.auto_game)
        self.b_game = QPushButton(_("Choose a game stadium..."))
        self.b_game.clicked.connect(self.pick_game)
        v.addWidget(row(self.b_auto_game, self.b_game))
        self.b_pick = QPushButton(_("From your stadium pack..."))
        self.b_pick.clicked.connect(self.pick)
        self.b_none = QPushButton(_("No pack stadium"))
        self.b_none.clicked.connect(lambda: self.set_selected(None))
        self.b_back = QPushButton(_("The world's pack stadium"))
        self.b_back.clicked.connect(self.back)
        self.b_auto = QPushButton(_("Find in your pack"))
        self.b_auto.clicked.connect(self.find_auto)
        self.b_save = QPushButton(_("Save"))
        self.b_save.setObjectName("primary")
        self.b_save.clicked.connect(self.save)
        self.b_undo = QPushButton(_("Discard"))
        self.b_undo.clicked.connect(self.discard)
        v.addWidget(row(self.b_pick, self.b_none, self.b_back, self.b_auto, "stretch", self.b_undo, self.b_save,
                        stretch=False))
        self.note = QLabel("")
        self.note.setWordWrap(True)
        v.addWidget(self.note)
        self.pack_buttons = (self.b_pick, self.b_auto)
        self.buttons = (self.b_auto_game, self.b_game, self.b_pick, self.b_none, self.b_back, self.b_auto,
                        self.b_save, self.b_undo)

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

    def tables(self):
        return os.path.join(self.root(), "common", "etc", "pesdb")

    def refresh(self):
        if self.changed():
            return                                 # changes not saved yet stay on screen
        w = self.ready()
        self.lib = L.library(self.app.game.sider_dir) if w else None
        if w is None:
            self.world = self.pl = None
            self.tree.clear()
            self.say(_("No imported world is in the game. A world you build has its stadiums in Build: Edit "
                       "club > Game stadium and Home stadium."))
            self.enable(False)
            return
        self.world = w
        self.enable(False)
        self.say(_("Reading %s ...") % w)
        plan = os.path.join(self.root(), "leaguebuilder-plan.json")
        team = os.path.join(self.tables(), "Team.bin")

        def job(progress):
            from .. import filecache
            return filecache.json_file(plan), G.read_team_bin(team)

        def done(got):
            self.pl, have = got
            self.saved = L.load_edits(self.root())
            self.edits, self.auto = dict(self.saved), set()
            self.new = G.new_clubs(self.pl)
            self.game_was = {t: have.get(t, 0) for t in self.new}
            self.game = dict(self.game_was)
            self.hand_saved, self.auto_saved = L.load_game(self.root())
            self.hand, self.auto_on = dict(self.hand_saved), self.auto_saved
            self.fill()
            self.enable(True)

        def failed(tb):
            self.say(_("The world could not be read: %s") % tb.strip().splitlines()[-1], theme.WARN)
        run_job(job, done, failed)

    def enable(self, on):
        for b in self.buttons:
            b.setEnabled(on and (bool(self.lib) or b not in self.pack_buttons))

    def say(self, text, color=None):
        self.note.setText(text)
        self.note.setStyleSheet("color: %s;" % color if color else "")

    def changed(self):
        return self.world is not None and self.pl is not None and (
            self.edits != self.saved or bool(self.auto) or self.game != self.game_was or self.hand != self.hand_saved or
            self.auto_on != self.auto_saved)

    # ---- the table ----

    def entry(self, tid, want):
        """(stadium pack entry or None, where it comes from: "world" / "yours" / "auto" / "none")"""
        if tid in self.edits:
            return self.edits[tid], ("auto" if tid in self.auto else "yours") if self.edits[tid] else "none"
        st = want.get(tid, (None, None))[1]
        return st, "world" if st else "none"

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
            if tid in self.game:
                gs = G.name(self.game[tid]) if self.game[tid] else _("(none)")
                if self.game[tid] != self.game_was.get(tid):
                    gs += "  *"
            else:
                gs = _("the club's own (a club of the game)")
            if st:
                pack = st.get("name") or os.path.basename(folder)
                if not found:
                    pack = _("%s: not in your pack") % pack
                elif src == "auto":
                    pack += "  " + _("(found, not saved yet)")
            else:
                pack = own.get(tid, "")
            if q and q not in ("%s %s %s %s" % (name, league, gs, pack)).lower():
                continue
            it = QTreeWidgetItem([name, league, gs, pack])
            it.setData(0, TID, tid)
            it.setToolTip(3, folder)
            if st and not found:
                it.setForeground(3, QBrush(QColor(theme.WARN)))
            elif src in ("yours", "auto"):
                it.setForeground(3, QBrush(QColor(theme.GOOD)))
            if tid in self.game and self.game[tid] != self.game_was.get(tid):
                it.setForeground(2, QBrush(QColor(theme.GOOD)))
            self.tree.addTopLevelItem(it)
            if tid in sel:
                it.setSelected(True)
        msg = _("%s: %d new clubs, each at one of the game's stadiums.") % (self.world, len(self.game))
        if n:
            msg += " " + _("%d of the %d stadiums of the stadium pack the world names are in yours.") % (have, n)
        if self.changed():
            msg += " " + _("Changes not saved yet.")
        self.say(msg, theme.WARN if self.changed() else None)

    def selected(self):
        return [it.data(0, TID) for it in self.tree.selectedItems()]

    # ---- the game's stadiums ----

    def auto_game(self):
        if self.pl is None:
            return
        got = G.world_picks(self.pl, G.confed_of(self.tables(), getattr(self.app.project, "base", None)),
                            self.hand, True)
        n = sum(1 for t, s in got.items() if t in self.game and self.game[t] != s)
        self.game.update({t: s for t, s in got.items() if t in self.game})
        self.auto_on = True
        self.fill()
        self.say(self.note.text() + " " + _("%d club(s) get another stadium: check them and press Save.") % n,
                 theme.WARN)

    def pick_game(self):
        tids = [t for t in self.selected() if t in self.game]
        if not tids:
            return
        items = ["%s (%s)" % (G.STADIUMS[i][0], "{:,}".format(G.STADIUMS[i][1]).replace(",", "."))
                 for i in sorted(G.STADIUMS, key=lambda i: (i not in G.FICTIONAL, G.STADIUMS[i][0]))]
        ids = sorted(G.STADIUMS, key=lambda i: (i not in G.FICTIONAL, G.STADIUMS[i][0]))
        cur = self.game.get(tids[0])
        text, ok = QInputDialog.getItem(self, _("Game stadium"), _("The stadium of the game for %d club(s):")
                                        % len(tids), items, ids.index(cur) if cur in ids else 0, False)
        if not ok:
            return
        sid = ids[items.index(text)]
        for t in tids:
            self.game[t] = self.hand[t] = sid
        self.fill()

    # ---- the stadium pack ----

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
        cur = self.entry(tids[0], L.wanted(self.pl))[0] or {}
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
        self.say(self.note.text() + " " + (_("Found %d stadium(s) in your pack: check them and press Save.") % len(got)
                                           if got else _("Nothing more found in your pack.")), theme.WARN)

    # ---- save ----

    def discard(self):
        if self.changed() and not ask(self, "Discard changes", _("Forget the changes you have not saved?")):
            return
        self.edits, self.auto = dict(self.saved), set()
        self.game, self.hand, self.auto_on = dict(self.game_was), dict(self.hand_saved), self.auto_saved
        self.fill()

    def save(self):
        if self.world is None or self.pl is None:
            return
        g, _s = self.app.game.running()
        if g and not ask(self, "Stadiums", _("The game is running. It reads the stadiums when it starts: restart "
                                             "it after saving. Save now?")):
            return
        from ..backups import snapshot
        sd = self.app.game.sider_dir
        maps = os.path.join(self.lib or os.path.join(sd, L.FOLDER), L.FILE)
        team = os.path.join(self.tables(), "Team.bin")
        try:
            for p in (maps, team):
                if os.path.exists(p):
                    snapshot(p, "Stadiums: " + self.world, sd)
            G.write_team_bin(team, {t: s for t, s in self.game.items() if s != self.game_was.get(t)})
            L.save_game(self.root(), self.hand, self.auto_on)
            L.save_edits(self.root(), self.edits)
            L.write(self.pl, sd, lambda m: None, self.edits)
        except OSError as e:
            error(self, "Stadiums", _("Could not save: %s") % e)
            return
        self.saved, self.auto = dict(self.edits), set()
        self.game_was, self.hand_saved, self.auto_saved = dict(self.game), dict(self.hand), self.auto_on
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
