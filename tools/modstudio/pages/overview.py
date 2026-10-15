"""Home: the world that is live in the game, what changed since it was built and one button to
build and install it, the ready check as a table (a red bar above it names the problem and has
the button that puts it right), quick actions and the last changes"""
import json, os, time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
                               QSizePolicy, QVBoxLayout, QWidget)

from .. import backups, checks, installer, modfix, theme
from ..i18n import _
from ..ui import Page, Stat

STATE_WORD = {"ok": "OK", "warn": "LOOK", "err": "FIX"}


def _card(name="card"):
    f = QFrame()
    f.setObjectName(name)
    v = QVBoxLayout(f)
    v.setContentsMargins(20, 16, 20, 16)
    v.setSpacing(6)
    return f, v


def _label(text="", name=None, wrap=True):
    l = QLabel(text)
    if name:
        l.setObjectName(name)
    l.setWordWrap(wrap)
    return l


def _head(text, name="section"):
    """a card's name in capitals: orange for what to do, blue for what is"""
    return theme.caps(_label(text, name, False))


class _ListLine(QLabel):
    """names on one line, as many as the width takes, then "… +N" (all of them in the tip)"""

    def __init__(self):
        super().__init__()
        self.setObjectName("subtle")
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.names = []

    def set(self, names):
        self.names = list(names)
        self.setToolTip("\n".join(self.names) if len(self.names) > 1 else "")
        self._fit()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._fit()

    def _fit(self):
        fm, n = self.fontMetrics(), len(self.names)
        width = max(60, self.width())
        text = ("… +%d" % n) if n else ""
        for k in range(n, 0, -1):
            t = ", ".join(self.names[:k]) + ("" if k == n else ", … +%d" % (n - k))
            if fm.horizontalAdvance(t) <= width:
                text = t
                break
        QLabel.setText(self, text)


class _Elided(QLabel):
    """a line of text cut with "…" to the width it has, the whole text in the tip"""

    def __init__(self, text):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.full = text
        self.setToolTip(text)
        self.setAccessibleName(text)           # what Windows reads out and a driver finds: all of it
        self._fit()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._fit()

    def _fit(self):
        QLabel.setText(self, self.fontMetrics().elidedText(self.full, Qt.ElideRight, max(40, self.width())))


class Overview(Page):
    title = "Home"
    hint = ""

    def __init__(self, app):
        super().__init__(app)
        body = QWidget()
        cols = QHBoxLayout(body)
        cols.setContentsMargins(0, 2, 0, 0)
        cols.setSpacing(16)
        left = QVBoxLayout()
        left.setSpacing(14)
        right = QVBoxLayout()
        right.setSpacing(14)
        cols.addLayout(left, 1)
        side = QWidget()
        side.setLayout(right)
        side.setFixedWidth(330)
        cols.addWidget(side, 0, Qt.AlignTop)

        # the problem, by name, with the button that puts it right (B37: "2 missing" was not enough)
        self.problem = QFrame()
        self.problem.setObjectName("problembar")
        ph = QHBoxLayout(self.problem)
        ph.setContentsMargins(18, 12, 12, 12)
        ph.setSpacing(14)
        self.p_cap = _head("", "problemcap")
        self.p_text = _label("", "problemtext")
        self.p_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.p_btn = QPushButton("")
        self.p_btn.setObjectName("primary")
        self.p_btn.clicked.connect(lambda: self._p_do and self._p_do())
        self._p_do = None
        ph.addWidget(self.p_cap, 0, Qt.AlignVCenter)
        ph.addWidget(self.p_text, 1)
        ph.addWidget(self.p_btn, 0, Qt.AlignVCenter)
        self.problem.hide()
        left.addWidget(self.problem)

        # the live world: its name (the pack's, for a world from a zip) with where it came from,
        # its numbers in boxes as the bar's, its leagues on one line (15.10.: a title made of
        # league names said too little)
        live, lv = _card()
        lv.setSpacing(10)
        top = QHBoxLayout()
        top.setSpacing(16)
        txt = QVBoxLayout()
        txt.setSpacing(4)
        self.l_eyebrow = theme.caps(_label("● " + _("IN THE GAME NOW"), "eyebrow"))
        trow = QHBoxLayout()
        trow.setSpacing(10)
        self.l_world = _label("", "bigtitle", False)
        self.l_world.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.l_source = theme.caps(_label("", "srctag", False))
        trow.addWidget(self.l_world)
        trow.addWidget(self.l_source, 0, Qt.AlignVCenter)
        trow.addStretch(1)
        txt.addWidget(self.l_eyebrow)
        txt.addLayout(trow)
        top.addLayout(txt, 1)
        self.b_open = b1 = QPushButton(_("Open its leagues"))
        b1.clicked.connect(self.open_live)
        b2 = QPushButton(_("Switch world..."))
        b2.clicked.connect(self.switch_world)
        top.addWidget(b1, 0, Qt.AlignVCenter)
        top.addWidget(b2, 0, Qt.AlignVCenter)
        lv.addLayout(top)
        boxes = QHBoxLayout()
        boxes.setSpacing(8)
        self.w_stats = {}
        for key, cap, stretch in (("world", "World", 3), ("leagues", "Leagues", 2), ("clubs", "New clubs", 2),
                                  ("built", "Built", 3), ("source", "Source", 2)):
            self.w_stats[key] = Stat(_(cap))
            boxes.addWidget(self.w_stats[key], stretch)
        lv.addLayout(boxes)
        self.l_leagues = _ListLine()
        lv.addWidget(self.l_leagues)
        self.l_detail = _label("", "subtle")
        lv.addWidget(self.l_detail)
        left.addWidget(live)

        # build and install, or "Ready to play"
        self.buildcard, buv = _card("bluecard")
        h = QHBoxLayout()
        h.setSpacing(16)
        t2 = QVBoxLayout()
        t2.setSpacing(4)
        self.l_changes = _label("", "cardtitle")
        self.l_changes_detail = _label("", "subtle")
        t2.addWidget(self.l_changes)
        t2.addWidget(self.l_changes_detail)
        h.addLayout(t2, 1)
        self.b_build = QPushButton(_("Build and install"))
        self.b_build.setObjectName("primary")
        self.b_build.setStyleSheet("padding: 9px 22px;")
        self.b_build.clicked.connect(self.build)
        self.b_eu = b_eu = QPushButton(_("Only the European cups..."))
        b_eu.setToolTip(_("A world with just the new Champions League, Europa League and Conference League "
                          "and the game's own leagues: no new leagues"))
        b_eu.clicked.connect(self.europe_only)
        h.addWidget(b_eu, 0, Qt.AlignVCenter)
        h.addWidget(self.b_build, 0, Qt.AlignVCenter)
        buv.addLayout(h)
        left.addWidget(self.buildcard)

        # the ready check: one row per check, its state, its number and what to do
        health = QFrame()
        health.setObjectName("card")
        hv = QVBoxLayout(health)
        hv.setContentsMargins(0, 0, 0, 0)
        hv.setSpacing(0)
        hh = QHBoxLayout()
        hh.setContentsMargins(20, 14, 20, 10)
        hh.addWidget(_head(_("Ready check"), "section_o"))
        hh.addStretch(1)
        self.l_count = _label("", "cardnote", False)
        hh.addWidget(self.l_count)
        hv.addLayout(hh)
        heads = QWidget()
        heads.setObjectName("checkrow")
        heads.setAttribute(Qt.WA_StyledBackground, True)
        heads.setProperty("level", "head")
        hl = [_head(x, "colhead") for x in (_("State"), _("Check"), _("Value"), _("Action"))]
        hl[3].setAlignment(Qt.AlignRight)
        self._cols(QHBoxLayout(heads), *hl)
        hv.addWidget(heads)
        self.health_rows = QVBoxLayout()
        self.health_rows.setSpacing(0)
        hv.addLayout(self.health_rows)
        left.addWidget(health)
        left.addStretch(1)

        # quick actions
        qa, qv = _card()
        qv.setSpacing(8)
        qv.addWidget(_head(_("Quick actions"), "section_o"))
        self.q_modules = QPushButton(_("Install the modules"))
        self.q_modules.clicked.connect(lambda: modfix.install_now(self) and self.refresh())
        self.q_build = QPushButton(_("Build the world again"))
        self.q_build.clicked.connect(self.build)
        q_import = QPushButton(_("Import a world zip"))
        q_import.clicked.connect(self.import_zip)
        q_pack = QPushButton(_("Add a league package"))
        q_pack.clicked.connect(lambda: (self.app.open_page("Packages"), self.app.page("Packages").add_pack()))
        for b in (self.q_modules, self.q_build, q_import, q_pack):
            b.setObjectName("quick")
            qv.addWidget(b)
        right.addWidget(qa)

        # last changes
        recent, self.rv = _card()
        rh = QHBoxLayout()
        rh.addWidget(_head(_("Last changes")))
        rh.addStretch(1)
        rh.addWidget(_label(_("restore points"), "cardnote", False))
        self.rv.addLayout(rh)
        self.recent_rows = QVBoxLayout()
        self.recent_rows.setSpacing(0)
        self.rv.addLayout(self.recent_rows)
        more = QPushButton(_("All restore points"))
        more.clicked.connect(lambda: self.app.open_page("Restore"))
        self.rv.addSpacing(6)
        self.rv.addWidget(more, 0, Qt.AlignLeft)
        right.addWidget(recent)
        right.addStretch(1)

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

    @staticmethod
    def _cols(h, state, text, value, action):
        """the columns of the ready check, the same widths in the head and in every row"""
        h.setContentsMargins(20, 8, 16, 8)
        h.setSpacing(14)
        state.setFixedWidth(46)
        value.setFixedWidth(150)
        value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        action.setFixedWidth(150)
        h.addWidget(state, 0, Qt.AlignVCenter)
        h.addWidget(text, 1)
        h.addWidget(value, 0, Qt.AlignVCenter)
        h.addWidget(action, 0, Qt.AlignVCenter)

    # ---- rows ----
    @staticmethod
    def _clear(layout):
        while layout.count():
            it = layout.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
            elif it.layout():
                Overview._clear(it.layout())

    def _check(self, level, text, value="", page=None, action=None):
        """one row of the ready check"""
        w = QWidget()
        w.setObjectName("checkrow")
        w.setAttribute(Qt.WA_StyledBackground, True)
        w.setProperty("level", level)
        s = _label(STATE_WORD.get(level, level), "state", False)
        s.setProperty("level", level)
        # one line, cut with "…" when the window is narrow (all of it in the tip): wrapped lines
        # were squeezed into each other at 1080x640
        t = _Elided(text)
        w.setMinimumHeight(36)
        v = _label(value, "value", False)
        v.setProperty("level", level)
        a = QWidget()
        ah = QHBoxLayout(a)
        ah.setContentsMargins(0, 0, 0, 0)
        ah.addStretch(1)
        if action:
            b = QPushButton(action[0])
            b.setObjectName("primary")
            b.setStyleSheet("padding: 3px 10px; min-height: 14px;")
            b.clicked.connect(action[1])
            ah.addWidget(b)
        elif page and page in self.app.pages:
            b = QPushButton(_("Open"))
            b.setObjectName("action" if level != "ok" else "rowbtn")
            b.clicked.connect(lambda _c=False, p=page: self.app.open_page(p))
            ah.addWidget(b)
        self._cols(QHBoxLayout(w), s, t, v, a)
        w.setProperty("alt", self.health_rows.count() % 2 == 1)
        self.health_rows.addWidget(w)

    def _change(self, when, text):
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 6, 0, 6)
        h.setSpacing(12)
        a = _label(when, "when", False)
        a.setFixedWidth(92)
        h.addWidget(a, 0, Qt.AlignTop)
        b = _label(text)
        b.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        h.addWidget(b, 1)
        self.recent_rows.addWidget(w)
        line = QFrame()
        line.setObjectName("rowline")
        self.recent_rows.addWidget(line)

    # ---- refresh ----
    def refresh(self):
        g = self.app.game
        P = self.app.project
        ini = self.app.ini() if g.ok() else None
        live = P.live_worlds() if g.ok() else []
        r = P.recipe
        st = self.w_stats
        if live:
            w = live[0]
            mine = r.get("world") == w
            names = [L["name"] for L in r["leagues"]] if mine else []
            zipped = installer.ready_world(g, w)
            recs = installer.installed_as(g.sider_dir, w) if zipped else []
            pack = recs[-1].get("name", "") if recs else ""
            self.l_eyebrow.setText("● " + _("IN THE GAME NOW"))
            self.l_world.setText(pack or w)
            self.l_source.setText(_("From zip") if zipped else _("Built here"))
            self.l_source.setProperty("state", "zip" if zipped else "built")
            self.l_source.show()
            built = os.path.join(g.livecpk_dir, w)
            when = time.strftime("%d.%m. %H:%M", time.localtime(os.path.getmtime(built))) if os.path.isdir(built) else "?"
            st["world"].set(w, "info", _("The world switched on in the game"))
            st["world"].setVisible(bool(pack) and pack != w)
            if mine:
                from leaguebuilder import new_club_count
                st["leagues"].set(str(len(names)))
                st["clubs"].set(str(sum(new_club_count(L) for L in r["leagues"])))
            else:
                st["leagues"].set("—", "", _("Mod Studio has %s open") % r.get("world"))
                st["clubs"].set("—", "", _("Mod Studio has %s open") % r.get("world"))
            st["built"].set(when)
            st["source"].set(_("zip") if zipped else _("Build"), "info" if zipped else "ok")
            self.l_leagues.set(names)
            notes = [] if mine else [_("Mod Studio has %s open") % r.get("world")]
            if len(live) > 1:
                notes.append(_("%d worlds are in the game; only one should be") % len(live))
            self.l_detail.setText(" · ".join(notes))
            self.l_detail.setVisible(bool(notes))
            self.b_open.setText(_("Open its leagues") if mine else _("Open that world..."))
        else:
            self.b_open.setText(_("Open its leagues"))
            self.l_eyebrow.setText(_("NO WORLD OF YOURS IN THE GAME"))
            self.l_world.setText(r.get("world", ""))
            self.l_source.hide()
            from leaguebuilder import new_club_count
            st["world"].hide()
            st["leagues"].set(str(len(r["leagues"])))
            st["clubs"].set(str(sum(new_club_count(L) for L in r["leagues"])))
            st["built"].set(_("not yet"))
            st["source"].set("—")
            self.l_leagues.set([L["name"] for L in r["leagues"]])
            self.l_detail.setText(_("Build and install puts this world in the game."))
            self.l_detail.show()
        theme.repolish(self.l_source)

        kept = os.path.join(P.copies_dir(), r.get("world", "") + ".json")
        changed = True
        if os.path.exists(kept):
            try:
                from .. import filecache
                old = filecache.json_file(kept)
                changed = json.dumps(old.get("leagues"), sort_keys=True) != json.dumps(r.get("leagues"), sort_keys=True) \
                    or json.dumps(old.get("edits"), sort_keys=True) != json.dumps(r.get("edits"), sort_keys=True)
            except (OSError, ValueError):
                pass
        ready = [w for w in live if installer.ready_world(g, w)]
        self.b_build.setVisible(not ready)
        self.b_eu.setVisible(not ready)
        self.q_build.setVisible(not ready)
        self.buildcard.setObjectName("okcard" if ready else "bluecard")
        theme.repolish(self.buildcard)
        if ready:
            # 0.2.4: a world installed from a zip is built already; Build would switch it off
            self.l_changes.setText(_("Ready to play"))
            self.l_changes_detail.setText(_("%s is a ready world, installed from a zip: nothing to build. "
                                            "Press Play and start a new Master League.") % ready[0])
        elif not r["leagues"] and not r.get("edits"):
            self.l_changes.setText(_("Nothing to build yet"))
            self.l_changes_detail.setText(_("Add a league or change one of the game's on the Leagues page."))
        elif changed or r.get("world") not in live:
            self.l_changes.setText(_("Changes not in the game yet"))
            self.l_changes_detail.setText(_("Build and install puts your world in the game: Mod Studio's modules, "
                                            "the world, switched on."))
        else:
            self.l_changes.setText(_("The game has the latest build"))
            self.l_changes_detail.setText(_("Build again after you change a league, a club or a player."))
        self.b_build.setEnabled(bool(r["leagues"] or r.get("edits")))
        self.q_build.setEnabled(self.b_build.isEnabled())

        self._clear(self.health_rows)
        rows = []
        state = mod_text = None
        if ini is not None:
            roots = ini.entries("cpk.root")
            mods = ini.entries("lua.module")
            rows.append(("ok", _("Content folders on"), "%d / %d" % (sum(e.enabled for e in roots), len(roots)), None))
            rows.append(("ok", _("Lua modules on"), "%d / %d" % (sum(e.enabled for e in mods), len(mods)), None))
            # 0.2.4: whether Mod Studio's own modules are there, current and on, with the button
            # that puts them right (they were behind League Builder > Build > 0. Install the modules)
            state = checks.modules_state(g)
            line = modfix.summary(state)
            mod_text = line[1] if line else None
            if line:
                rows.insert(0, line + (None, None if line[0] == "ok" else
                                       (_("Install now"), lambda: modfix.install_now(self) and self.refresh())))
        if g.ok() and os.path.isdir(g.sider_dir):
            rows.append(("ok", _("Packs installed here"), str(len(installer.records(g.sider_dir))), None))
            hist = backups.history(g.sider_dir)
        else:
            hist = []
        mods_bad = bool(rows) and rows[0][0] == "err" and len(rows[0]) > 4
        for level, area, text, page in checks.quick(g, ini, r):
            if mods_bad and area == "Lua modules" and page == "Build":
                continue            # a DLL missing or changed: the modules line above says it, with its button
            rows.append((level, "%s: %s" % (_(area), _(text)), "", page))
        # the red ones first, then what to look at, then what is fine
        order = {"err": 0, "warn": 1}
        rows.sort(key=lambda row: order.get(row[0], 2))
        for row in rows:
            level, text, right, page = row[:4]
            self._check(level, text, right, page, row[4] if len(row) > 4 else None)
        n_ok = sum(1 for row in rows if row[0] == "ok")
        n_look = sum(1 for row in rows if row[0] == "warn")
        n_bad = sum(1 for row in rows if row[0] == "err")
        bits = [_("%d checks") % len(rows), _("%d ok") % n_ok]
        if n_look:
            bits.append(_("%d to look at") % n_look)
        if n_bad:
            bits.append(_("%d to fix") % n_bad)
        self.l_count.setText(" · ".join(bits))
        self.q_modules.setObjectName("quick" if not state or checks.modules_ok(state) else "quickmain")
        theme.repolish(self.q_modules)

        # the red bar: the first problem, said by name, and its button
        bad = [row for row in rows if row[0] == "err"]
        if state and not checks.modules_ok(state):
            if state["missing"]:
                cap = _("%d missing") % len(state["missing"])
                what = _("%s not in %s. An antivirus may have taken them: Windows Security > Protection "
                         "history.") % (_(" and ").join([", ".join(state["missing"][:-1]), state["missing"][-1]])
                                        if len(state["missing"]) > 1 else state["missing"][0],
                                        os.path.join(os.path.basename(g.sider_dir), "modules"))
            elif state["changed"]:
                cap = _("%d older") % len(state["changed"])
                what = _("%s: an older version or damaged.") % ", ".join(state["changed"])
            else:
                cap = _("%d switched off") % len(state["off"])
                what = _("%s: not switched on in sider.ini.") % ", ".join(state["off"])
            self._problem(cap, what, _("Install the modules"), lambda: modfix.install_now(self) and self.refresh())
        elif bad:
            level, text, right, page = bad[0][:4]
            act = bad[0][4] if len(bad[0]) > 4 else None
            cap = _("%d problem") % len(bad) if len(bad) == 1 else _("%d problems") % len(bad)
            if act:
                self._problem(cap, text, act[0], act[1])
            elif page and page in self.app.pages:
                self._problem(cap, text, _("Open"), lambda p=page: self.app.open_page(p))
            else:
                self._problem(cap, text, None, None)
        else:
            self.problem.hide()
        # the top bar says the same (the modules line it works out itself)
        self.app.update_header(problems=[row[1] for row in bad if row[1] != mod_text])

        self._clear(self.recent_rows)
        for h in hist[:6]:
            t = h["time"]
            when = "%s.%s. %s:%s" % (t[6:8], t[4:6], t[9:11], t[11:13])
            self._change(when, h.get("reason") or h["file"])
        if not hist:
            self.recent_rows.addWidget(_label(_("Nothing changed yet."), "subtle"))

    def _problem(self, cap, text, button, do):
        self.p_cap.setText(cap)
        self.p_text.setText(text)
        self._p_do = do
        self.p_btn.setVisible(bool(button))
        if button:
            self.p_btn.setText(button)
        self.problem.show()

    def switch_world(self):
        """Content folders with the League Builder worlds shown: they are what a world switch picks
        from, and the page hides them by default"""
        self.app.open_page("Roots")
        r = self.app.pages.get("Roots")
        if r is not None and hasattr(r, "show_worlds"):
            r.show_worlds.setChecked(True)

    def open_live(self):
        live = self.app.project.live_worlds()
        if live and self.app.project.recipe.get("world") != live[0]:
            self.app.page("NewLeagues").open_recipe()
        else:
            self.app.open_page("Leagues")

    def import_zip(self):
        self.app.open_page("Install")
        self.app.page("Install").pick_file()

    def europe_only(self):
        self.app.open_page("Build")
        self.app.page("Build").do_europe_only()

    def build(self):
        self.app.open_page("Build")
        self.app.page("Build").build_all()
