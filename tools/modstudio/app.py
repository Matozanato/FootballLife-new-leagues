r"""python -m modstudio.app   -> the FL26 Mod Studio window

    top bar      File / Game / Profiles / Language / Help menus, Play
    header       the game folder, the active profile, whether the game is running
    left         the sections (pages/*.py), grouped
    centre       the open section
    status bar   what the program is doing

Settings (game folder, language, window size) live in %APPDATA%\FL26ModStudio\settings.json.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))

from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtGui import QAction, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QButtonGroup, QDialog, QHBoxLayout, QLabel, QMainWindow,
                               QMenu, QPushButton, QScrollArea, QStackedWidget, QStatusBar, QTextBrowser,
                               QToolButton, QVBoxLayout, QWidget, QMessageBox)

from modstudio import VERSION, theme, i18n
from modstudio.i18n import _
from modstudio.game import Game, guess_folders
from modstudio.siderini import SiderIni
import siderdir

APPDIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "FL26ModStudio")
SETTINGS = os.path.join(APPDIR, "settings.json")


def load_settings():
    try:
        with open(SETTINGS, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_settings(d, seen=None):
    """write the settings. With seen (the settings as this window last read or wrote them) only
    the keys the window changed since go over what the file holds now: a second window, or one
    left open, must not put back an old choice -- a language picked in the other one was lost
    when this one closed and wrote everything it had read at its start."""
    try:
        if seen is not None:
            now = load_settings()
            now.update({k: v for k, v in d.items() if k not in seen or seen[k] != v})
            d.clear()
            d.update(now)
            seen.clear()
            seen.update(json.loads(json.dumps(now)))
        os.makedirs(APPDIR, exist_ok=True)
        with open(SETTINGS + ".tmp", "w", encoding="utf-8") as f:
            json.dump(d, f, indent=1, ensure_ascii=False)
        os.replace(SETTINGS + ".tmp", SETTINGS)
    except OSError:
        pass


class Bus(QObject):
    ini_changed = Signal()          # sider.ini was written
    game_changed = Signal()         # another game folder
    content_changed = Signal()      # files under SiderAddons changed (install, remove, build)


def page_groups():
    """(caption, [page classes]) in the order of the left bar; caption "" is a group without a
    caption, None pages that are built but not in the bar (reached from another page)"""
    from modstudio.pages import overview, roots, modules, install, profiles, restore
    from modstudio.pages import content, stadiums, balls, kits, commentary, music
    from modstudio.pages import builder, players, packages, diagnostics, settings, newlife, leagues
    return [
        ("", [overview.Overview]),
        ("LEAGUE BUILDER", [leagues.Leagues, builder.NewClubs, players.Players, newlife.NewLife,
                            packages.Packages, builder.Build]),
        ("GAME CONTENT", [kits.Kits, stadiums.Stadiums, balls.Balls, commentary.Commentary,
                          music.Music, content.Servers]),
        ("MANAGE", [install.Install, modules.Modules, roots.Roots, profiles.Profiles, restore.Restore,
                    diagnostics.Diagnostics, settings.Settings]),
        (None, [builder.NewLeagues]),
    ]


# 0.2.4: the left bar by what a player wants to do ("it is so crowded, that is not humane", 14.10.).
# (caption, folds, [(key, title, [pages])]): a section of one page shows it as it is, one of more
# shows its pages as tabs, the first one open. GAME CONTENT and TOOLS start folded.
NAV = [
    ("", False, [("Overview", "Home", ["Overview"])]),
    ("YOUR WORLD", False, [
        # 0.2.4: one section, Build a tab next to what it builds (exe test 15.10.: "no sense editing
        # in one tab and building in another"); the bar above the tabs has Build and install
        ("World", "Build and edit your world", ["Build", "Leagues", "NewClubs", "Players", "Kits", "Stadiums",
                                                "Packages"]),
        ("ImportWorld", "Import your world", ["Install"]),
        ("NewLife", "NewLife Database", ["NewLife"]),
    ]),
    ("GAME CONTENT", True, [(n, None, [n]) for n in ("Balls", "Commentary", "Music", "Servers")]),
    ("TOOLS", True, [(n, None, [n]) for n in ("Modules", "Roots", "Profiles", "Restore", "Diagnostics")]),
    ("SETTINGS", False, [("Settings", None, ["Settings"])]),
]
TAB_TITLE = {"Build": "Build", "Packages": "League packages",
             "NewClubs": "Clubs"}
OPEN_FOR = {"NewLeagues": "World"}     # a page not in the bar: the section that stays lit


class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self._seen = json.loads(json.dumps(self.settings))
        i18n.set_language(self.settings.get("lang", "en"))
        self.bus = Bus()
        siderdir.PREFERRED = self.settings.get("sider") or None
        folder = self.settings.get("game") or next(iter(guess_folders()), "")
        self.game = Game(folder)
        self.game_paths()
        from modstudio.project import Project
        self.project = Project(self)
        self.project.load_tables()
        # the recipe of the last session: the one last opened or saved, or the copy the last Build kept
        last = self.settings.get("last_recipe")
        if last and os.path.exists(last):
            try:
                self.project.open(last, copy=os.path.dirname(os.path.abspath(last))
                                  == os.path.abspath(self.project.copies_dir()))
            except Exception:           # a recipe that no longer reads: start with an empty one
                self.project.new()
        # 0.1.8: the live world first. A tester's last recipe was an older world than the one
        # switched on in sider.ini, and the next Build would have replaced the live one with it
        self._start_note = ""
        live = self.project.live_worlds()
        if live and self.project.recipe.get("world") not in live:
            kept = os.path.join(self.project.copies_dir(), live[0] + ".json")
            was = self.project.recipe.get("world")
            if not os.path.exists(kept) and self.project.base:
                # no copy of its recipe (built before Build kept one, or elsewhere): read the
                # recipe back from the plan the world carries (leaguebuilder.recipe_from_plan)
                try:
                    import leaguebuilder
                    plan = os.path.join(self.game.livecpk_dir, live[0], "leaguebuilder-plan.json")
                    with open(plan, encoding="utf-8") as f:
                        rec = leaguebuilder.recipe_from_plan(json.load(f), self.project.base)
                    os.makedirs(self.project.copies_dir(), exist_ok=True)
                    with open(kept, "w", encoding="utf-8") as f:
                        json.dump(rec, f, indent=1, ensure_ascii=False)
                except Exception:
                    pass
            if os.path.exists(kept):
                try:
                    self.project.open(kept, copy=True)
                    self._start_note = _("Opened %s, the world in the game "
                                         "(the last one open was %s).") % (live[0], was)
                except Exception:
                    pass
            from modstudio import installer as _I
            if not self._start_note and not _I.ready_world(self.game, live[0]):
                # a ready world has no recipe to open, and Build is off for it: nothing to tell
                self._start_note = _("The world in the game is %s, but Mod Studio has %s open. "
                                     "Open %s (File > Open a world...) before you Build.") % (live[0], was, live[0])
        self.bus.game_changed.connect(self.project.load_tables)
        self.setWindowTitle("FL26 Mod Studio")
        self.resize(*self.settings.get("size", [1360, 820]))
        self.setMinimumSize(1080, 640)
        ico = os.path.join(HERE, "assets", "app.ico")
        if os.path.exists(ico):
            self.setWindowIcon(QIcon(ico))

        root = QWidget()
        v = QVBoxLayout(root)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        v.addWidget(self._topbar())
        v.addWidget(self._header())
        body = QHBoxLayout()
        body.setSpacing(0)
        self.stack = QStackedWidget()
        body.addWidget(self._nav())
        body.addWidget(self.stack, 1)
        v.addLayout(body, 1)
        self.setCentralWidget(root)

        sb = QStatusBar()
        self.status_left = QLabel(_("Ready"))
        self.status_busy = QLabel("")
        sb.addWidget(self.status_left, 1)
        sb.addPermanentWidget(self.status_busy)
        # edits of clubs, players and leagues go into the recipe at once; this says whether the
        # recipe file has them yet (poll, 11.10.: people looked for an Apply button)
        self.status_saved = QPushButton("")
        self.status_saved.setFlat(True)
        self.status_saved.setCursor(Qt.PointingHandCursor)
        self.status_saved.clicked.connect(lambda: self.project.autosave())
        sb.addPermanentWidget(self.status_saved)
        sb.addPermanentWidget(QLabel("v" + VERSION))
        self.setStatusBar(sb)
        self.project.changed.connect(self.show_saved)
        self.project.saved.connect(self.show_saved)
        QShortcut(QKeySequence.Save, self, lambda: self.project.autosave())
        self.show_saved()
        self._blink = QTimer(self, interval=550, timeout=self._blink_step)
        self._busy = 0

        self.pages = {}
        first = None
        for caption, classes in page_groups():
            for cls in classes:
                p = cls(self)
                self.pages[cls.__name__] = p
                first = first or cls.__name__
        self._sections()
        self.bus.game_changed.connect(self.update_header)
        self.bus.ini_changed.connect(self.update_header)
        self.update_header()
        self._run_timer = QTimer(self, interval=4000, timeout=self.update_running)
        self._run_timer.start()
        QTimer.singleShot(0, self.update_running)       # after the window is up: tasklist takes ~0.3 s
        self.open_page(self.settings.get("page") if self.settings.get("page") in self.pages else first)
        if self._start_note:
            self.status(self._start_note)
        # 0.2.4: the game's tables are unpacked by themselves the first time (and after the game
        # folder changes), no Settings step to know about
        QTimer.singleShot(1200, self.auto_tables)
        self.bus.game_changed.connect(lambda: QTimer.singleShot(500, self.auto_tables))

    def auto_tables(self):
        """unpack the game's tables when there are none yet and no tables folder of your own was
        chosen (Settings has the button for doing it again after a game update)"""
        p = self.project
        if p.base is not None or not self.game.ok() or self.settings.get("tables"):
            return
        s = self.pages.get("Settings")
        if s is None or not s.unpack_btn.isEnabled():
            return
        self.status(_("First start: Mod Studio unpacks the game's tables (its clubs, leagues and players). "
                      "It takes a minute or two."))
        s.unpack()

    # ---- chrome ----
    def _menu_button(self, text, items):
        b = QToolButton()
        b.setObjectName("menu")
        b.setText(_(text) + "  ▾")
        b.setPopupMode(QToolButton.InstantPopup)
        m = QMenu(b)
        for it in items:
            if it is None:
                m.addSeparator()
            else:
                label, slot = it[0], it[1]
                a = m.addAction(label if it[2:3] == [True] else _(label))
                a.triggered.connect(slot)
        b.setMenu(m)
        return b

    def _topbar(self):
        w = QWidget()
        w.setObjectName("topbar")
        h = QHBoxLayout(w)
        h.setContentsMargins(6, 4, 8, 4)
        h.setSpacing(2)
        h.addWidget(self._menu_button("File", [
            ("New world", lambda: self.page("NewLeagues").new_recipe()),
            ("Open a world...", lambda: self.page("NewLeagues").open_recipe()),
            ("Save your world as...", lambda: self.page("NewLeagues").save_recipe(True)),
            ("Changes in this world...", self.show_changes),
            None,
            ("Add a league package...", lambda: (self.open_page("Packages"), self.page("Packages").add_pack())),
            ("Make a league package...", lambda: (self.open_page("Packages"), self.page("Packages").make_pack())),
            None, ("Exit", self.close)]))
        h.addWidget(self._menu_button("Game", [
            ("Choose the game folder...", lambda: self.page("Settings").pick_game()),
            ("Open the game folder", lambda: self._open(self.game.folder)),
            ("Open the Sider folder", lambda: self._open(self.game.sider_dir)),
            ("Open sider.ini", lambda: self._open(self.game.ini_path)),
            ("Open sider.log", lambda: self._open(self.game.log_path)),
            None,
            ("Start the game", self.play),
            ("Start the game without mods (safe mode)...", lambda: self.page("Profiles").safe_mode()),
            None,
            ("Put Sider back as before Mod Studio...",
             lambda: (self.open_page("Restore"), self.page("Restore").reset_sider()))]))
        h.addWidget(self._menu_button("Profiles", [
            ("Manage profiles", lambda: self.open_page("Profiles")),
            ("Save the current setup as a profile...", lambda: self.page("Profiles").save_new())]))
        h.addWidget(self._menu_button("Language", [(name, (lambda c=code: self.set_language(c)), True)
                                                   for code, name in i18n.LANGUAGES]))
        hb = self._menu_button("Help", [
            ("User guide", self.guide),
            ("Check for updates...", self.check_updates),
            ("About FL26 Mod Studio", self.about)])
        auto = QAction(_("Check for updates at start"), hb.menu())
        auto.setCheckable(True)
        auto.setChecked(self.settings.get("check_updates", True))
        auto.toggled.connect(self.set_auto_updates)
        hb.menu().insertAction(hb.menu().actions()[2], auto)
        h.addWidget(hb)
        cb = QToolButton()
        cb.setObjectName("menu")
        cb.setText(_("Credits"))
        cb.setToolTip(_("Everyone who helped make Mod Studio"))
        cb.clicked.connect(self.credits)
        h.addWidget(cb)
        h.addStretch(1)
        self.run_label = QLabel("")
        self.run_label.setObjectName("subtle")
        h.addWidget(self.run_label)
        h.addSpacing(10)
        self.play_btn = QPushButton(_("▶  Play"))
        self.play_btn.setObjectName("play")
        self.play_btn.setToolTip(_("Start the game with the current setup (as the desktop shortcut does)"))
        self.play_btn.clicked.connect(self.play)
        h.addWidget(self.play_btn)
        return w

    def _header(self):
        w = QWidget()
        w.setObjectName("header")
        h = QHBoxLayout(w)
        h.setContentsMargins(12, 5, 12, 5)
        self.h_title = QLabel("FL26 Mod Studio")
        self.h_title.setObjectName("title")
        self.h_game = QLabel("")
        self.h_game.setObjectName("subtle")
        self.h_profile = QLabel("")
        self.h_profile.setObjectName("subtle")
        h.addWidget(self.h_title)
        h.addSpacing(14)
        h.addWidget(self.h_game, 1)
        h.addWidget(self.h_profile)
        return w

    def _nav(self):
        """the left bar from NAV: a button per section, a folding group behind its caption"""
        outer = QScrollArea()
        outer.setWidgetResizable(True)
        outer.setFixedWidth(220)
        outer.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.setFrameShape(QScrollArea.NoFrame)
        w = QWidget()
        w.setObjectName("nav")
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 8)
        v.setSpacing(0)
        self.nav_group = QButtonGroup(self)
        self.nav_buttons, self.nav_group_of, self.nav_folds, self.nav_heads = {}, {}, {}, {}
        titles = {cls.__name__: cls.title for _c, group in page_groups() for cls in group}
        v.addSpacing(10)
        for caption, folds, sections in NAV:
            box = QWidget()
            bv = QVBoxLayout(box)
            bv.setContentsMargins(0, 0, 0, 0)
            bv.setSpacing(0)
            if caption and folds:
                head = QPushButton("")
                head.setObjectName("navgroup")
                head.setCursor(Qt.PointingHandCursor)
                head.clicked.connect(lambda _c=False, g=caption: self.fold(g, not self.nav_open(g)))
                v.addWidget(head)
                self.nav_heads[caption] = head
                self.nav_folds[caption] = box
            elif caption:
                c = QLabel(_(caption))
                c.setObjectName("navcaption")
                v.addWidget(c)
            for key, title, names in sections:
                b = QPushButton(_(title or titles[names[0]]))
                b.setObjectName("navitem")
                b.setCheckable(True)
                b.clicked.connect(lambda _c=False, n=names[0]: self.open_page(n))
                self.nav_group.addButton(b)
                self.nav_buttons[key] = b
                if folds:
                    self.nav_group_of[key] = caption
                bv.addWidget(b)
            v.addWidget(box)
        for g in self.nav_folds:
            self.fold(g, self.nav_open(g), save=False)
        v.addStretch(1)
        outer.setWidget(w)
        return outer

    def nav_open(self, group):
        return group in (self.settings.get("nav_open") or [])

    def fold(self, group, on, save=True):
        """open (on) or fold a group of the left bar; kept for the next start"""
        now = [g for g in (self.settings.get("nav_open") or []) if g != group] + ([group] if on else [])
        self.settings["nav_open"] = now
        self.nav_folds[group].setVisible(bool(on))
        self.nav_heads[group].setText(("\u25be  " if on else "\u25b8  ") + _(group))
        if save:
            self.save_settings()

    def _sections(self):
        """the stack: a section of one page is the page, one of more holds its pages as tabs"""
        from PySide6.QtWidgets import QTabWidget
        self.section_of, self.section_tabs = {}, {}
        # 0.2.4: every page in a scroll area of its own (exe test 15.10., Windows at 125/150 %: a
        # page taller than the window had its buttons squeezed to a line; now it scrolls)
        self.holder_of = {}

        def held(name):
            sa = QScrollArea()
            sa.setWidgetResizable(True)
            sa.setFrameShape(QScrollArea.NoFrame)
            sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            sa.setStyleSheet("QScrollArea { background: transparent; }")
            sa.setWidget(self.pages[name])
            self.holder_of[name] = sa
            return sa
        placed = set()
        for _caption, _folds, sections in NAV:
            for key, _title, names in sections:
                for n in names:
                    self.section_of[n] = key
                if len(names) == 1:
                    self.stack.addWidget(held(names[0]))
                    placed.add(names[0])
                    continue
                holder = QWidget()
                holder.setObjectName("page")
                holder.setAttribute(Qt.WA_StyledBackground, True)
                hv = QVBoxLayout(holder)
                hv.setContentsMargins(12, 10, 12, 0)
                hv.setSpacing(0)
                tabs = QTabWidget()
                tabs.setObjectName("sectiontabs")
                tabs.setDocumentMode(True)
                for n in names:
                    tabs.addTab(held(n), _(TAB_TITLE.get(n) or self.pages[n].title))
                    placed.add(n)
                tabs.currentChanged.connect(lambda _i, t=tabs: self.open_page(
                    next(k for k, h in self.holder_of.items() if h is t.currentWidget())))
                if key == "World":
                    hv.addWidget(self._world_bar(holder))
                hv.addWidget(tabs)
                self.section_tabs[key] = tabs
                self.stack.addWidget(holder)
        for n, p in self.pages.items():
            if n not in placed:
                self.stack.addWidget(held(n))

    def _world_bar(self, holder):
        """above the tabs of Build and edit your world: the open world and Build and install, on
        every tab; while it builds, the time so far and the step it is at"""
        from PySide6.QtWidgets import QFrame
        bar = QFrame()
        bar.setObjectName("card")
        h = QHBoxLayout(bar)
        h.setContentsMargins(14, 8, 10, 8)
        h.setSpacing(12)
        self.wb_name = QLabel()
        self.wb_name.setTextFormat(Qt.RichText)
        h.addWidget(self.wb_name)
        self.wb_state = QLabel()
        self.wb_state.setStyleSheet("color: %s;" % theme.ACCENT)
        h.addWidget(self.wb_state, 1)
        self.wb_build = QPushButton(_("Build and install"))
        self.wb_build.setObjectName("primary")
        self.wb_build.setToolTip(_("Installs the modules, builds the world, switches it on and says what is left"))
        self.wb_build.clicked.connect(self._world_build)
        h.addWidget(self.wb_build)
        self._wb_holder = holder
        t = QTimer(self, interval=1500, timeout=lambda: holder.isVisible() and self.update_world_bar())
        t.start()
        wrap = QWidget()
        v = QVBoxLayout(wrap)
        v.setContentsMargins(0, 0, 0, 8)
        v.addWidget(bar)
        return wrap

    def _world_build(self):
        self.open_page("Build")
        self.page("Build").build_all()

    def update_world_bar(self, progress=None):
        """the world bar now: progress is the build's time and step ("" when it is over)"""
        if not hasattr(self, "wb_name"):
            return
        import html
        r = self.project.recipe
        n = len(r.get("leagues") or [])
        clubs = sum(int(L.get("clubs") or 0) for L in r.get("leagues") or [])
        self.wb_name.setText("<b>%s</b>&nbsp;&nbsp;&nbsp;%s" % (
            html.escape(_("Your world: %s") % (r.get("world") or "")), html.escape(_("%d leagues, %d clubs") % (n, clubs))))
        if progress is not None:
            self.wb_state.setText(progress)
        b = self.pages.get("Build")
        if b is not None and hasattr(b, "b_all"):
            self.wb_build.setEnabled(b.b_all.isEnabled())
            self.wb_build.setToolTip(b.b_all.toolTip() or _("Installs the modules, builds the world, switches it "
                                                            "on and says what is left"))

    # ---- pages ----
    def page(self, name):
        return self.pages[name]

    def open_page(self, name):
        p = self.pages[name]
        key = self.section_of.get(name) or OPEN_FOR.get(name)
        tabs = self.section_tabs.get(key) if name in self.section_of else None
        if tabs is not None:
            self.stack.setCurrentWidget(tabs.parentWidget())
            if tabs.currentWidget() is not self.holder_of[name]:
                tabs.blockSignals(True)
                tabs.setCurrentWidget(self.holder_of[name])
                tabs.blockSignals(False)
        else:
            self.stack.setCurrentWidget(self.holder_of[name])
        b = self.nav_buttons.get(key)
        if b:
            group = self.nav_group_of.get(key)
            if group and not self.nav_open(group):
                self.fold(group, True)
            b.setChecked(True)
        self.settings["page"] = name
        if key == "World":
            self.update_world_bar()
        try:
            p.shown()
        except Exception as e:
            p.say(_("This section could not be shown: %s") % e, "err")

    # ---- shared state ----
    def ini(self):
        """sider.ini as it is on disk now (None when there is none)"""
        try:
            return SiderIni.load(self.game.ini_path)
        except OSError:
            return None

    def save_ini(self, ini, reason):
        """write sider.ini (a restore point is taken first) and tell every page"""
        ini.save(reason=reason)
        self.bus.ini_changed.emit()
        g, s = Game.running()
        self.status(_("sider.ini saved: %s") % reason
                    + ("  — " + _("restart the game to use it") if (g or s) else ""))

    def set_game(self, folder):
        self.game = Game(folder)
        self.game_paths()
        self.settings["game"] = self.game.folder
        self.save_settings()
        self.bus.game_changed.emit()

    def game_paths(self):
        """the builder's tools find the exe through flpaths: give them this game folder, not the
        default C:/Football Life 2026 (0.2.3: "FL_2026.exe not found" on Build)"""
        import flpaths
        if self.game.folder:
            flpaths.use_game(self.game.folder, self.game.sider_dir)

    def set_sider(self, name):
        """use the Sider folder `name` of the game folder (one of siderdir.candidates)"""
        siderdir.PREFERRED = name or None
        self.settings["sider"] = name or ""
        self.save_settings()
        self.game_paths()
        self.bus.game_changed.emit()

    def status(self, text):
        self.status_left.setText(text)

    def show_changes(self):
        from modstudio.pages.changes import WorldChangesDialog
        WorldChangesDialog(self, self.project).exec()

    def show_saved(self):
        p = self.project
        if p.dirty:
            self.status_saved.setText("● " + _("Saving..."))
            self.status_saved.setStyleSheet("color: %s;" % theme.ACCENT)
            self.status_saved.setToolTip(_("Mod Studio saves your world by itself a moment after each change"))
        else:
            self.status_saved.setText("✓ " + _("Your world is saved"))
            self.status_saved.setStyleSheet("")
            self.status_saved.setToolTip(p.path or "")
        self.status_saved.setVisible(bool(self.status_saved.text()))

    def busy(self, on, text=None):
        self._busy = max(0, self._busy + (1 if on else -1))
        if self._busy:
            self.status_busy.setText("● " + (text or _("Working...")))
            self._blink.start()
        else:
            self._blink.stop()
            self.status_busy.setText("")

    def _blink_step(self):
        c = theme.ACCENT if self.status_busy.property("b") else "#FFFFFF"
        self.status_busy.setProperty("b", not self.status_busy.property("b"))
        self.status_busy.setStyleSheet("color: %s;" % c)

    def update_header(self):
        g = self.game
        if g.ok():
            self.h_game.setText("%s   %s" % (g.folder, ("·  " + g.version()) if g.version() else ""))
        else:
            self.h_game.setText(_("No game folder yet: Game ▾ Choose the game folder"))
        prof = self.settings.get("profile")
        live = self.project.live_worlds() if g.ok() else []
        bits = ([_("In the game: %s") % ", ".join(live)] if live else []) + ([_("Profile: %s") % prof] if prof else [])
        self.h_profile.setText("     ".join(bits))

    def update_running(self):
        g, s = Game.running()
        if g:
            self.run_label.setText("● " + _("the game is running"))
            self.run_label.setStyleSheet("color: %s;" % theme.GOOD)
        elif s:
            self.run_label.setText("● " + _("Sider is running"))
            self.run_label.setStyleSheet("color: %s;" % theme.WARN)
        else:
            self.run_label.setText("")
        self.play_btn.setEnabled(self.game.ok() and not g)

    # ---- actions ----
    def play(self):
        if not self.game.ok():
            self.open_page("Settings")
            return
        warn = self.page("Modules").order_problems() if "Modules" in self.pages else []
        if warn and not QMessageBox.question(
                self, _("Play"), _("There are problems with the module order:") + "\n\n" +
                "\n".join("• " + w for w in warn[:6]) + "\n\n" + _("Start anyway?")) == QMessageBox.Yes:
            return
        how = self.game.start()
        self.status(_("Starting the game (%s) ...") % _(how))

    def _open(self, path):
        if path and os.path.exists(path):
            os.startfile(path)

    def set_language(self, code):
        self.settings["lang"] = code
        self.save_settings()
        QMessageBox.information(self, "FL26 Mod Studio",
                                "The language changes when the program is started again.\n"
                                "Jezik se mijenja kad se program ponovno pokrene.\n"
                                "El idioma cambia al volver a abrir el programa.\n"
                                "La langue change au prochain démarrage du programme.")

    def guide(self):
        code = i18n.CODE
        names = (["README.%s.html" % code] if code != "en" else []) + ["README.html"]
        dirs = [os.path.dirname(os.path.abspath(sys.argv[0])), getattr(sys, "_MEIPASS", HERE),
                os.path.join(os.path.dirname(os.path.dirname(HERE)), "out", "modstudio")]
        for n in names:
            for d in dirs:
                p = os.path.join(d, n)
                if os.path.exists(p):
                    os.startfile(p)
                    return
        QMessageBox.information(self, _("Help"), _("The user guide is README.html next to the program."))

    def about(self):
        QMessageBox.about(self, "FL26 Mod Studio",
                          "<b>FL26 Mod Studio</b> v%s<br><br>%s<br><br>%s" % (
                              VERSION,
                              _("A mod manager and league builder for Football Life 2026."),
                              _("It changes sider.ini and the content folders only, and keeps a "
                                "restore point before every change.")))

    def credits(self):
        """the Credits button next to Help: everyone who helped (modstudio/credits.py)"""
        from modstudio import credits
        d = QDialog(self)
        d.setWindowTitle(_("Credits"))
        v = QVBoxLayout(d)
        t = QTextBrowser()
        t.setOpenExternalLinks(True)
        t.setHtml(credits.html(_))
        v.addWidget(t, 1)
        close = QPushButton(_("Close"))
        close.clicked.connect(d.accept)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(close)
        v.addLayout(row)
        d.resize(640, 640)
        d.exec()

    def set_auto_updates(self, on):
        """Help > Check for updates at start: off = only when asked (the menu item above it)"""
        self.settings["check_updates"] = bool(on)
        self.save_settings()

    def check_updates(self, quiet=False):
        """ask GitHub for a newer release; quiet (the check at start) says nothing unless there is one"""
        from modstudio import updater
        from modstudio.ui import run_job

        def done(info):
            if info:
                self.offer_update(info)
            elif not quiet:
                QMessageBox.information(self, _("Updates"), _("FL26 Mod Studio is up to date (v%s).") % VERSION)

        def failed(tb):
            if not quiet:
                QMessageBox.warning(self, _("Updates"), _("Could not reach GitHub to check for updates.")
                                    + "\n\n" + tb.strip().splitlines()[-1])
        run_job(lambda progress: updater.latest(), done, failed)

    def offer_update(self, info):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        from modstudio import updater
        from modstudio.ui import run_job
        page = lambda: QDesktopServices.openUrl(QUrl(info["page"]))
        # What is new and what was fixed is the first thing the dialog shows, not a detail to
        # click open: nobody should install a version without seeing what it changes.
        box = QDialog(self)
        box.setWindowTitle(_("Update available"))
        box.resize(640, 480)
        v = QVBoxLayout(box)
        head = QLabel("<b>%s</b>" % (_("FL26 Mod Studio %s is out (you have %s).") % (info["version"], VERSION)))
        v.addWidget(head)
        v.addWidget(QLabel(_("What is new and what was fixed:")))
        notes = QTextBrowser()
        notes.setOpenExternalLinks(True)
        text = updater.what_changed(info["notes"])
        if text:
            notes.setMarkdown(text)
        else:
            notes.setPlainText(_("This release has no list of changes; the release page may say more."))
        v.addWidget(notes, 1)
        keep = QLabel(_("Download it and restart? Your settings, projects and restore points "
                        "stay as they are, and the game is not touched."))
        keep.setWordWrap(True)
        v.addWidget(keep)
        row = QHBoxLayout()
        row.addStretch(1)
        choice = {}
        for label, key in ((_("Download and install"), "yes"), (_("Open the release page"), "page"),
                           (_("Later"), "later")):
            b = QPushButton(label)
            b.clicked.connect(lambda _c=False, k=key: (choice.update(k=k), box.accept()))
            row.addWidget(b)
            if key == "yes":
                b.setDefault(True)
        v.addLayout(row)
        box.exec()
        if choice.get("k") == "page":
            page()
            return
        if choice.get("k") != "yes":
            return
        if not updater.frozen():
            QMessageBox.information(self, _("Update available"),
                                    _("This copy runs from source; the release page opens instead."))
            page()
            return
        if not updater.can_write(updater.program_dir()):
            QMessageBox.warning(self, _("Update available"),
                                _("The program's folder (%s) cannot be written to. Unpack the new zip "
                                  "yourself, or move FL26 Mod Studio to a folder of your own.")
                                % updater.program_dir())
            page()
            return

        def progress(p):
            self.status_left.setText(_("Downloading the update... %d%%") % p)

        def done(path):
            try:
                updater.install(path)
            except Exception as e:
                QMessageBox.warning(self, _("Update available"), _("The update could not be installed: %s") % e)
                self.status_left.setText(_("Ready"))
                return
            self.status_left.setText(_("Installing the update; FL26 Mod Studio restarts by itself..."))
            QApplication.instance().processEvents()
            QApplication.instance().quit()

        def failed(tb):
            QMessageBox.warning(self, _("Update available"),
                                _("The download failed: %s") % tb.strip().splitlines()[-1])
            self.status_left.setText(_("Ready"))
        progress(0)
        run_job(lambda pr: updater.download(info, pr), done, failed, progress)

    def closeEvent(self, e):
        # changes made since the last Save recipe or Build were lost without a word when Mod
        # Studio closed (the poll, Bon Kirk 11.10.: "an Apply button" -- OK only keeps a change
        # in the open recipe)
        if self.project.dirty:
            box = QMessageBox(QMessageBox.Question, _("Unsaved changes"),
                              _("Your world has changes that are not saved yet. Save them before closing?"),
                              QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, self)
            box.setDefaultButton(QMessageBox.Save)
            r = box.exec()
            if r == QMessageBox.Cancel:
                e.ignore()
                return
            if r == QMessageBox.Save:
                try:
                    if self.project.path:
                        self.project.save()
                        self.settings["last_recipe"] = self.project.path
                    else:                  # never saved: the copy the next start opens again
                        self.settings["last_recipe"] = self.project.keep_copy()
                except OSError as err:
                    QMessageBox.warning(self, _("Unsaved changes"), str(err))
                    e.ignore()
                    return
        self.settings["size"] = [self.width(), self.height()]
        self.save_settings()
        super().closeEvent(e)

    def save_settings(self):
        save_settings(self.settings, self._seen)


def denied_hook(previous):
    """sys.excepthook for the window's own clicks (Switch on, a sider.ini edit, Remove the mod):
    Windows refusing a write in the game folder gets the box that says what to do (B14: a game
    under Program Files, a raw PermissionError traceback before); anything else goes on as before"""
    showing = []

    def hook(kind, err, tb):
        from modstudio import access
        if isinstance(err, Exception) and access.is_denied(err) and not showing:
            showing.append(1)
            try:
                from modstudio.ui import denied_box
                denied_box(QApplication.activeWindow(), access.denied_path(err) or "")
            except Exception:
                previous(kind, err, tb)
            finally:
                showing.clear()
            return
        previous(kind, err, tb)
    return hook


def main():
    # 0.2.4: Build runs in a thread of this process; the window gets its turn every millisecond
    # instead of every five, so it keeps answering while a big world builds (exe test 15.10.)
    sys.setswitchinterval(0.001)
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FL26.ModStudio")
        except Exception:
            pass
    # 0.1.8: follow Windows scaling (125 %, 150 %) exactly, not rounded to 100 % or 200 %
    from PySide6.QtGui import QGuiApplication
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    theme.apply(app)
    # one Mod Studio at a time: the program takes a few seconds to unpack itself, a second
    # click in that time started a second one, and the two wrote over each other's settings
    lock = None
    if "--shot" not in sys.argv:
        from PySide6.QtCore import QLockFile
        os.makedirs(APPDIR, exist_ok=True)
        lock = QLockFile(os.path.join(APPDIR, "running.lock"))
        # --elevated: started by Restart as administrator (access.restart_as_admin) while the
        # one that started it closes
        if not lock.tryLock(30000 if "--elevated" in sys.argv else 200):
            i18n.set_language(load_settings().get("lang", "en"))
            QMessageBox.information(None, "FL26 Mod Studio",
                                    _("FL26 Mod Studio is already open. Look for its window on the taskbar."))
            return
    # 0.2.3: a crash that takes the program down writes where it was to crash.log (people send it)
    try:
        import faulthandler
        os.makedirs(APPDIR, exist_ok=True)
        faulthandler.enable(open(os.path.join(APPDIR, "crash.log"), "w", encoding="utf-8"))
    except Exception:
        pass
    sys.excepthook = denied_hook(sys.excepthook)
    w = Main()
    theme.dark_title_bar(w)
    w.show()
    if "--shot" in sys.argv:                     # a picture of each page, for the guide
        out = sys.argv[sys.argv.index("--shot") + 1]
        os.makedirs(out, exist_ok=True)

        def shoot():
            for name in w.pages:
                w.open_page(name)
                app.processEvents()
                w.grab().save(os.path.join(out, name + ".png"))
            app.quit()
        QTimer.singleShot(1500, shoot)
    elif w.settings.get("check_updates", True):
        QTimer.singleShot(3000, lambda: w.check_updates(quiet=True))
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
