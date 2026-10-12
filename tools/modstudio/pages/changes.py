"""File > Changes in this world: everything the recipe changes in one list, and a way to take
single changes back (novarama, poll 11.10.: "a list of everything I changed, and undo one")"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QAbstractItemView)

from ..i18n import _

# what a club edit can hold, in words
CLUB_FIELDS = {"name": "name", "abbr": "short name", "crest": "crest", "stadium": "stadium",
               "kits": "kits", "coach": "manager", "country": "country"}


class WorldChangesDialog(QDialog):
    def __init__(self, parent, project):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle(_("Changes in this world"))
        self.resize(820, 600)
        v = QVBoxLayout(self)
        note = QLabel(_("Everything this recipe changes in the game. Pick one or more lines and press "
                        "Undo to take them back; the new leagues themselves are removed on the New "
                        "leagues page. Build again afterwards."))
        note.setWordWrap(True)
        v.addWidget(note)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([_("Change"), _("What")])
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tree.setColumnWidth(0, 330)
        self.tree.itemSelectionChanged.connect(self.picked)
        v.addWidget(self.tree, 1)
        h = QHBoxLayout()
        self.count = QLabel("")
        h.addWidget(self.count, 1)
        self.b_undo = QPushButton(_("Undo the picked changes"))
        self.b_undo.clicked.connect(self.undo)
        h.addWidget(self.b_undo)
        b_close = QPushButton(_("Close"))
        b_close.clicked.connect(self.accept)
        h.addWidget(b_close)
        v.addLayout(h)
        self.fill()

    # ---- the list ----
    def team(self, key):
        """a club of the game by its id, or a new club by "<league>/<place>" """
        if str(key).isdigit():
            return self.project.team_name(int(key)) or "#%s" % key
        name, _s, k = str(key).rpartition("/")
        L = self.project.league(name) or {}
        clubs = L.get("club_names") or []
        if k.isdigit() and int(k) < len(clubs) and clubs[int(k)]:
            return "%s (%s)" % (clubs[int(k)], name)
        return _("club %s of %s") % (int(k) + 1 if k.isdigit() else k, name)

    def group(self, text, n):
        g = QTreeWidgetItem(self.tree, ["%s  (%d)" % (text, n), ""])
        g.setFlags(g.flags() & ~Qt.ItemIsSelectable)
        f = g.font(0)
        f.setBold(True)
        g.setFont(0, f)
        return g

    def row(self, parent, text, what, ref):
        it = QTreeWidgetItem(parent, [text, what])
        it.setData(0, Qt.UserRole, ref)
        if ref is None:
            it.setFlags(it.flags() & ~Qt.ItemIsSelectable)
        return it

    def fill(self):
        self.tree.clear()
        r = self.project.recipe
        e = r.get("edits") or {}
        total = 0
        leagues = r.get("leagues") or []
        if leagues:
            g = self.group(_("New leagues"), len(leagues))
            for L in leagues:
                self.row(g, L.get("name", "?"), _("%d clubs") % (L["clubs"] if isinstance(L.get("clubs"), int)
                                                    else len(L.get("club_names") or [])),
                         None)
        clubs = e.get("clubs") or {}
        if clubs:
            g = self.group(_("Clubs of the game edited"), len(clubs))
            for tid, c in sorted(clubs.items(), key=lambda x: self.team(x[0]).lower()):
                what = ", ".join(_(CLUB_FIELDS.get(k, k)) for k in c)
                old, new = self.team(tid), c.get("name")
                self.row(g, "%s  →  %s" % (old, new) if new and new != old else old, what, ("clubs", tid))
            total += len(clubs)
        lgs = e.get("leagues") or {}
        if lgs:
            g = self.group(_("Leagues of the game edited"), len(lgs))
            for rid, c in lgs.items():
                name = self.project.comp_name(int(rid)) if str(rid).lstrip("-").isdigit() else str(rid)
                self.row(g, c.get("name") or name or "#%s" % rid, ", ".join(c), ("leagues", rid))
            total += len(lgs)
        comps = e.get("competitions") or {}
        if comps:
            g = self.group(_("Competitions renamed"), len(comps))
            for cid, c in comps.items():
                old = self.project.comp_name(int(cid)) if str(cid).isdigit() else str(cid)
                new = c.get("name", "") if isinstance(c, dict) else str(c)
                self.row(g, old or "#%s" % cid, new, ("competitions", cid))
            total += len(comps)
        swaps = e.get("swaps") or []
        if swaps:
            g = self.group(_("Clubs swapped between leagues"), len(swaps))
            for k, (a, b) in enumerate(swaps):
                self.row(g, "%s  ⇄  %s" % (self.team(a), self.team(b)), "", ("swaps", k))
            total += len(swaps)
        for key, val in e.items():          # anything newer than this list: shown, and undoable whole
            if key in ("clubs", "leagues", "competitions", "swaps") or not val:
                continue
            g = self.group(key, len(val) if hasattr(val, "__len__") else 1)
            self.row(g, _("all of them"), "", ("edits", key))
            total += 1
        players = r.get("players") or {}
        if players:
            nl = sum(1 for p in players.values() if isinstance(p, dict) and p.get("newlife_game"))
            g = self.group(_("Squads changed"), len(players))
            for key, p in sorted(players.items(), key=lambda x: self.team(x[0]).lower()):
                if not isinstance(p, dict):
                    continue
                bits = []
                for k, t in (("edits", _("%d players edited")), ("add", _("%d signed")),
                             ("remove", _("%d released")), ("join", _("%d joined"))):
                    if p.get(k):
                        bits.append(t % len(p[k]))
                if p.get("newlife_game"):
                    bits.append(_("NewLife"))
                self.row(g, self.team(key), ", ".join(bits), ("players", key))
            total += len(players)
            if nl:
                g.setToolTip(0, _("%d of them come from the NewLife Database; the NewLife page takes "
                                  "all of those back at once") % nl)
        self.tree.expandAll() if total < 80 else None
        self.count.setText(_("%d changes") % total if total else _("This recipe changes nothing in the "
                                                                  "game's own clubs and leagues yet."))
        self.picked()

    def picked(self):
        n = sum(1 for it in self.tree.selectedItems() if it.data(0, Qt.UserRole))
        self.b_undo.setEnabled(n > 0)
        self.b_undo.setText(_("Undo %d picked changes") % n if n > 1 else _("Undo the picked change"))

    # ---- taking changes back ----
    def undo(self):
        refs = [it.data(0, Qt.UserRole) for it in self.tree.selectedItems() if it.data(0, Qt.UserRole)]
        if not refs:
            return
        if QMessageBox.question(self, _("Changes in this world"),
                                _("Take back %d change(s)? Save the recipe and Build again to see it "
                                  "in the game.") % len(refs)) != QMessageBox.Yes:
            return
        r = self.project.recipe
        e = r.setdefault("edits", {})
        gone_swaps = set()
        for kind, key in refs:
            if kind == "players":
                (r.get("players") or {}).pop(key, None)
            elif kind == "swaps":
                gone_swaps.add(key)
            elif kind == "edits":
                e.pop(key, None)
            else:
                (e.get(kind) or {}).pop(key, None)
        if gone_swaps:
            e["swaps"] = [p for k, p in enumerate(e.get("swaps") or []) if k not in gone_swaps]
        for k in [k for k, v in e.items() if not v]:
            del e[k]
        self.project.touch()
        self.fill()
