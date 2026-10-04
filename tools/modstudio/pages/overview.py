"""Home: the world that is live in the game, what changed since it was built and one button to
build and install it, whether everything is in place, and the last changes"""
import json, os, time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
                               QVBoxLayout, QWidget)

from .. import backups, checks, installer
from ..i18n import _
from ..ui import Page

MARKS = {"ok": "✓", "warn": "!", "err": "✕"}


def _card(name="card"):
    f = QFrame()
    f.setObjectName(name)
    v = QVBoxLayout(f)
    v.setContentsMargins(22, 18, 22, 18)
    v.setSpacing(6)
    return f, v


def _label(text="", name=None, wrap=True):
    l = QLabel(text)
    if name:
        l.setObjectName(name)
    l.setWordWrap(wrap)
    return l


class Overview(Page):
    title = "Home"
    hint = ""

    def __init__(self, app):
        super().__init__(app)
        body = QWidget()
        bv = QVBoxLayout(body)
        bv.setContentsMargins(0, 4, 0, 0)
        bv.setSpacing(18)

        # the live world
        live, lv = _card()
        top = QHBoxLayout()
        top.setSpacing(18)
        txt = QVBoxLayout()
        txt.setSpacing(6)
        self.l_eyebrow = _label("● " + _("LIVE IN THE GAME NOW"), "eyebrow")
        self.l_world = _label("", "bigtitle")
        self.l_detail = _label("", "subtle")
        for w in (self.l_eyebrow, self.l_world, self.l_detail):
            txt.addWidget(w)
        top.addLayout(txt, 1)
        self.b_open = b1 = QPushButton(_("Open its leagues"))
        b1.clicked.connect(self.open_live)
        b2 = QPushButton(_("Switch world..."))
        b2.clicked.connect(lambda: self.app.open_page("Roots"))
        top.addWidget(b1, 0, Qt.AlignVCenter)
        top.addWidget(b2, 0, Qt.AlignVCenter)
        lv.addLayout(top)
        bv.addWidget(live)

        # build and install
        build, buv = _card("bluecard")
        h = QHBoxLayout()
        h.setSpacing(18)
        t2 = QVBoxLayout()
        self.l_changes = _label("", "cardtitle")
        self.l_changes_detail = _label("", "subtle")
        t2.addWidget(self.l_changes)
        t2.addWidget(self.l_changes_detail)
        h.addLayout(t2, 1)
        self.b_build = QPushButton(_("Build and install"))
        self.b_build.setObjectName("primary")
        self.b_build.setStyleSheet("font-size: 11pt; font-weight: bold; padding: 10px 26px; border-radius: 8px;")
        self.b_build.clicked.connect(self.build)
        b_eu = QPushButton(_("Only the European cups..."))
        b_eu.setToolTip(_("A world with just the new Champions League, Europa League and Conference League "
                          "and the game's own leagues: no new leagues"))
        b_eu.clicked.connect(self.europe_only)
        h.addWidget(b_eu, 0, Qt.AlignVCenter)
        h.addWidget(self.b_build, 0, Qt.AlignVCenter)
        buv.addLayout(h)
        bv.addWidget(build)

        # health and last changes, side by side
        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        health, self.hv = _card()
        self.hv.addWidget(_label(_("Everything in place"), "cardtitle"))
        self.health_rows = QVBoxLayout()
        self.health_rows.setSpacing(0)
        self.hv.addLayout(self.health_rows)
        self.hv.addStretch(1)
        recent, self.rv = _card()
        self.rv.addWidget(_label(_("Last changes"), "cardtitle"))
        self.recent_rows = QVBoxLayout()
        self.recent_rows.setSpacing(0)
        self.rv.addLayout(self.recent_rows)
        self.rv.addStretch(1)
        more = QPushButton(_("All restore points"))
        more.clicked.connect(lambda: self.app.open_page("Restore"))
        self.rv.addWidget(more, 0, Qt.AlignLeft)
        grid.addWidget(health, 0, 0)
        grid.addWidget(recent, 0, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        bv.addLayout(grid)
        bv.addStretch(1)

        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setFrameShape(QScrollArea.NoFrame)
        sc.setWidget(body)
        self.outer.addWidget(sc, 1)
        app.bus.ini_changed.connect(self.refresh_if_shown)
        app.bus.content_changed.connect(self.refresh_if_shown)
        app.bus.game_changed.connect(self.refresh_if_shown)
        app.project.changed.connect(self.refresh_if_shown)

    def refresh_if_shown(self):
        if self.isVisible():
            self.refresh()

    # ---- rows ----
    @staticmethod
    def _clear(layout):
        while layout.count():
            it = layout.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
            elif it.layout():
                Overview._clear(it.layout())

    def _row(self, layout, left, text, right="", page=None, last=False):
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 7, 0, 7)
        h.setSpacing(10)
        if left in MARKS:
            m = _label(MARKS[left], "tick_" + ("bad" if left == "err" else left), False)
            m.setFixedWidth(16)
        else:
            m = _label(left, "subtle", False)
            m.setFixedWidth(84)
        h.addWidget(m, 0, Qt.AlignTop)
        h.addWidget(_label(text), 1)
        if page and page in self.app.pages:
            b = QPushButton(_("Open"))
            b.setStyleSheet("padding: 2px 10px; min-height: 14px;")
            b.clicked.connect(lambda _c=False, p=page: self.app.open_page(p))
            h.addWidget(b, 0, Qt.AlignTop)
        elif right:
            h.addWidget(_label(right, "subtle", False), 0, Qt.AlignTop)
        layout.addWidget(w)
        if not last:
            line = QFrame()
            line.setObjectName("rowline")
            layout.addWidget(line)

    # ---- refresh ----
    def refresh(self):
        g = self.app.game
        P = self.app.project
        ini = self.app.ini() if g.ok() else None
        live = P.live_worlds() if g.ok() else []
        r = P.recipe
        if live:
            w = live[0]
            mine = r.get("world") == w
            names = [L["name"] for L in r["leagues"]] if mine else []
            self.l_eyebrow.setText("● " + _("LIVE IN THE GAME NOW"))
            self.l_world.setText(" · ".join(names[:4]) + (" …" if len(names) > 4 else "") if names else w)
            built = os.path.join(g.livecpk_dir, w)
            when = time.strftime("%d.%m. %H:%M", time.localtime(os.path.getmtime(built))) if os.path.isdir(built) else "?"
            bits = [_("world %s") % w]
            if mine:
                from leaguebuilder import new_club_count
                bits.append(_("%d leagues · %d new clubs") % (len(names), sum(new_club_count(L) for L in r["leagues"])))
            bits.append(_("built %s") % when)
            bits.append(_("matches the open recipe") if mine else _("the open recipe is %s") % r.get("world"))
            if len(live) > 1:
                bits.append(_("%d worlds are switched on; only one should be") % len(live))
            self.l_detail.setText(" · ".join(bits))
            self.b_open.setText(_("Open its leagues") if mine else _("Open its recipe..."))
        else:
            self.b_open.setText(_("Open its leagues"))
            self.l_eyebrow.setText(_("NO LEAGUE BUILDER WORLD IN THE GAME"))
            self.l_world.setText(r.get("world", ""))
            self.l_detail.setText(_("Build and install puts this recipe in the game."))

        kept = os.path.join(P.copies_dir(), r.get("world", "") + ".json")
        changed = True
        if os.path.exists(kept):
            try:
                old = json.load(open(kept, encoding="utf-8"))
                changed = json.dumps(old.get("leagues"), sort_keys=True) != json.dumps(r.get("leagues"), sort_keys=True) \
                    or json.dumps(old.get("edits"), sort_keys=True) != json.dumps(r.get("edits"), sort_keys=True)
            except (OSError, ValueError):
                pass
        if not r["leagues"] and not r.get("edits"):
            self.l_changes.setText(_("Nothing to build yet"))
            self.l_changes_detail.setText(_("Add a league or change one of the game's on the Leagues page."))
        elif changed or r.get("world") not in live:
            self.l_changes.setText(_("Changes not in the game yet"))
            self.l_changes_detail.setText(_("Build and install puts the recipe in the game: modules, world, "
                                            "switched on."))
        else:
            self.l_changes.setText(_("The game has the latest build"))
            self.l_changes_detail.setText(_("Build again after you change a league, a club or a player."))
        self.b_build.setEnabled(bool(r["leagues"] or r.get("edits")))

        self._clear(self.health_rows)
        rows = []
        if ini is not None:
            roots = ini.entries("cpk.root")
            mods = ini.entries("lua.module")
            rows.append(("ok", _("Content folders on"), "%d / %d" % (sum(e.enabled for e in roots), len(roots)), None))
            rows.append(("ok", _("Lua modules on"), "%d / %d" % (sum(e.enabled for e in mods), len(mods)), None))
        if g.ok() and os.path.isdir(g.sider_dir):
            rows.append(("ok", _("Mods installed here"), str(len(installer.records(g.sider_dir))), None))
            hist = backups.history(g.sider_dir)
        else:
            hist = []
        for level, area, text, page in checks.quick(g, ini, r):
            rows.append((level, "%s: %s" % (_(area), _(text)), "", page))
        for n, (level, text, right, page) in enumerate(rows):
            self._row(self.health_rows, level, text, right, page, n == len(rows) - 1)

        self._clear(self.recent_rows)
        for n, h in enumerate(hist[:6]):
            t = h["time"]
            when = "%s.%s. %s:%s" % (t[6:8], t[4:6], t[9:11], t[11:13])
            self._row(self.recent_rows, when, h.get("reason") or h["file"], last=n == min(len(hist), 6) - 1)
        if not hist:
            self.recent_rows.addWidget(_label(_("Nothing changed yet."), "subtle"))

    def open_live(self):
        live = self.app.project.live_worlds()
        if live and self.app.project.recipe.get("world") != live[0]:
            self.app.page("NewLeagues").open_recipe()
        else:
            self.app.open_page("Leagues")

    def europe_only(self):
        self.app.open_page("Build")
        self.app.page("Build").do_europe_only()

    def build(self):
        self.app.open_page("Build")
        self.app.page("Build").build_all()
