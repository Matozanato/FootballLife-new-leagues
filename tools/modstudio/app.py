r"""python -m modstudio.app   -> the FL26 Mod Studio window

    top bar      the name, File / Game / Profiles / Language / Help menus, ready or not, Start the game
    state boxes  the game folder, Sider, the world in the game, the modules, its leagues, the pack
    sections     numbered across the top (pages/*.py); Game content and Tools open a menu
    centre       the open section
    status bar   ready or the problem, what the program is doing, whether the world is saved

Settings (game folder, language, window size) live in %APPDATA%\FL26ModStudio\settings.json.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))

from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtGui import QAction, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QButtonGroup, QDialog, QFrame, QHBoxLayout, QLabel, QMainWindow,
                               QMenu, QPushButton, QScrollArea, QSizePolicy, QStackedWidget, QStatusBar,
                               QTextBrowser, QToolButton, QVBoxLayout, QWidget, QMessageBox)

from modstudio import VERSION, theme, i18n
from modstudio.i18n import _
from modstudio.game import Game, guess_folders
from modstudio.siderini import SiderIni
from modstudio.ui import Stat
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
    # 0.2.4, variant A of the mockups (mato 15.10.): one section, My world, for Build and edit your
    # world, Import your world and NewLife Database -- the worlds on disk as cards, Build and
    # install above them, the pages that change the open world as tabs (pages/myworld.py)
    # 0.2.4 beta (B82, mato 16.10.): Build is the first tab, the section's home -- testers lost the
    # Build page when it sat under More
    ("MY WORLD", False, [("World", "My world", ["Build", "Leagues", "NewClubs", "Players", "Kits", "Stadiums"])]),
    ("GAME CONTENT", True, [(n, None, [n]) for n in ("Balls", "Commentary", "Music", "Servers")]),
    ("TOOLS", True, [(n, None, [n]) for n in ("Modules", "Roots", "Profiles", "Restore", "Diagnostics")]),
    ("SETTINGS", False, [("Settings", None, ["Settings"])]),
]
TAB_TITLE = {"Build": "Build", "Packages": "League packages",
             "NewClubs": "Clubs"}
# a page not in the bar: the section that stays lit. My world shows its own under the cards with
# no tab lit (More: League packages, Import a world zip, NewLife Database)
OPEN_FOR = {"NewLeagues": "World", "Packages": "World", "Install": "World",
            "NewLife": "World"}


def file_version(path):
    """the version a Windows exe carries ("7.3.3"), "" when it has none or this is not Windows"""
    try:
        import ctypes
        from ctypes import wintypes
        v = ctypes.windll.version
        size = v.GetFileVersionInfoSizeW(path, None)
        if not size:
            return ""
        buf = ctypes.create_string_buffer(size)
        if not v.GetFileVersionInfoW(path, 0, size, buf):
            return ""
        p, n = ctypes.c_void_p(), wintypes.UINT()
        if not v.VerQueryValueW(buf, "\\", ctypes.byref(p), ctypes.byref(n)) or n.value < 52:
            return ""
        ms, ls = ctypes.cast(p, ctypes.POINTER(wintypes.DWORD * 13)).contents[2:4]
        parts = [ms >> 16, ms & 0xFFFF, ls >> 16, ls & 0xFFFF]
        while len(parts) > 2 and parts[-1] == 0:
            parts.pop()
        return ".".join(str(x) for x in parts)
    except Exception:
        return ""


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
        self._start_note = self.open_live_world()
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
        self.stack = QStackedWidget()
        v.addWidget(self._nav())
        v.addWidget(self.stack, 1)
        self.setCentralWidget(root)

        sb = QStatusBar()
        sb.setSizeGripEnabled(False)
        # left: ready, or the problem by name (the same as the box at the top)
        self.status_state = QLabel("")
        self.status_state.setObjectName("sbstate")
        sb.addWidget(self.status_state)
        self.status_left = QLabel(_("Ready"))
        sb.addWidget(self.status_left, 1)
        self.status_busy = QLabel("")
        sb.addPermanentWidget(self.status_busy)
        # edits of clubs, players and leagues go into the recipe at once; this says whether the
        # recipe file has them yet (poll, 11.10.: people looked for an Apply button)
        # 0.2.5: Undo / Redo of the last change to your world (mato 16.10.), Ctrl+Z / Ctrl+Y when
        # no text box has the keys
        self.status_undo, self.status_redo = QPushButton("\u21b6 " + _("Undo")), QPushButton("\u21b7 " + _("Redo"))
        for b, tip, go, key in ((self.status_undo, _("Take back the last change to your world (Ctrl+Z)"), self.undo, "Ctrl+Z"),
                                (self.status_redo, _("Do the taken-back change again (Ctrl+Y)"), self.redo, "Ctrl+Y")):
            b.setObjectName("statusbtn")
            b.setFlat(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setToolTip(tip)
            b.setAccessibleName(tip)
            b.setEnabled(False)
            b.clicked.connect(go)
            QShortcut(QKeySequence(key), self, go)
            sb.addPermanentWidget(b)
        self.status_saved = QPushButton("")
        self.status_saved.setObjectName("statusbtn")
        self.status_saved.setFlat(True)
        self.status_saved.setCursor(Qt.PointingHandCursor)
        self.status_saved.clicked.connect(lambda: self.project.autosave())
        sb.addPermanentWidget(self.status_saved)
        self.status_points = QLabel("")
        sb.addPermanentWidget(self.status_points)
        sb.addPermanentWidget(QLabel("MOD STUDIO " + VERSION))
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
        self.bus.content_changed.connect(self.update_header)
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

    def live_recipe(self):
        """the file part of open_live_world, with no window work so it can run off the window's
        thread: (the world in the game, its recipe copy, the recipe read or None), or None when
        there is nothing to open. On the Modpack it is most of the 9 s the window stood still after
        a switch (coldstart, 17.10.): reading its 132 MB recipe back from the plan, writing the copy,
        reading it, and making the 86 league logos small"""
        live = self.project.live_worlds()
        if not live or self.project.recipe.get("world") in live:
            return None
        kept = os.path.join(self.project.copies_dir(), live[0] + ".json")
        if not os.path.exists(kept) and self.project.base:
            # no copy of its recipe (built before Build kept one, or elsewhere): read the
            # recipe back from the plan the world carries (leaguebuilder.recipe_from_plan)
            try:
                import leaguebuilder
                plan = os.path.join(self.game.livecpk_dir, live[0], "leaguebuilder-plan.json")
                with open(plan, encoding="utf-8") as f:
                    rec = leaguebuilder.recipe_from_plan(json.load(f), self.project.base)
                os.makedirs(self.project.copies_dir(), exist_ok=True)
                text = json.dumps(rec, indent=1, ensure_ascii=False)   # not dump(): see Project._write
                with open(kept, "w", encoding="utf-8") as f:
                    f.write(text)
            except Exception:
                pass
        rec = None
        if os.path.exists(kept):
            try:
                with open(kept, encoding="utf-8") as f:
                    rec = json.load(f)
                from modstudio.pages import builder as _PB
                _PB.warm([L.get("logo") for L in rec.get("leagues") or []], (20, 28))
            except Exception:
                pass
        return live[0], kept, rec

    def open_live_world(self, found=False):
        """open the recipe of the world in the game when another one is open (at a start, and after
        My world's Put in the game); what to tell, or "". found: what live_recipe() gave, when it
        ran in the background already"""
        if found is False:
            found = self.live_recipe()
        if not found:
            return ""
        world, kept, rec = found
        live = self.project.live_worlds()
        if not live or live[0] != world or self.project.recipe.get("world") in live:
            return ""
        note = ""
        was = self.project.recipe.get("world")
        if rec is not None:
            try:
                self.project.autosave()            # the world open now keeps its changes
                self.project.adopt(rec, kept, copy=True)
                self.settings["last_recipe"] = kept
                note = _("Opened %s, the world in the game "
                         "(the last one open was %s).") % (world, was)
            except Exception:
                pass
        from modstudio import installer as _I
        if not note and not _I.ready_world(self.game, world):
            # a ready world has no recipe to open, and Build is off for it: nothing to tell
            note = _("The world in the game is %s, but Mod Studio has %s open. "
                     "Open %s (File > Open a world...) before you Build.") % (world, was, world)
        return note

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
                # triggered(checked) would land in a slot's first default argument (the Language
                # items' code, which became False and left the program in English)
                a.triggered.connect(lambda _c=False, f=slot: f())
        b.setMenu(m)
        return b

    def _topbar(self):
        w = QWidget()
        w.setObjectName("menubar")
        w.setAttribute(Qt.WA_StyledBackground, True)
        h = QHBoxLayout(w)
        h.setContentsMargins(14, 6, 12, 2)
        h.setSpacing(2)
        mark = QLabel(">_")
        mark.setObjectName("brandmark")
        h.addWidget(mark)
        h.addSpacing(8)
        self.h_title = QLabel("FL26 // MOD STUDIO")
        self.h_title.setObjectName("brand")
        h.addWidget(self.h_title)
        h.addSpacing(10)
        ver = QLabel(VERSION)
        ver.setObjectName("version")
        h.addWidget(ver, 0, Qt.AlignVCenter)
        h.addSpacing(18)
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
        self.lang_btn = self._menu_button("Language", [(name, (lambda c=code: self.set_language(c)), True)
                                                       for code, name in i18n.LANGUAGES])
        h.addWidget(self.lang_btn)
        hb = self._menu_button("Help", [
            ("User guide", self.guide),
            ("Quick tour", self.start_tour),
            ("Install a Modpack, step by step", self.start_modpack_guide),
            ("Edit a Modpack, step by step", self.start_edit_guide),
            ("Check for updates...", self.check_updates),
            ("About FL26 Mod Studio", self.about)])
        self.help_btn = hb
        auto = QAction(_("Check for updates at start"), hb.menu())
        auto.setCheckable(True)
        auto.setChecked(self.settings.get("check_updates", True))
        auto.toggled.connect(self.set_auto_updates)
        # just above Check for updates... (found by its text: the items above it are not always the same)
        upd = [a for a in hb.menu().actions() if a.text() == _("Check for updates...")]
        hb.menu().insertAction(upd[0], auto) if upd else hb.menu().addAction(auto)
        h.addWidget(hb)
        cb = QToolButton()
        cb.setObjectName("menu")
        cb.setText(_("Credits"))
        cb.setToolTip(_("Everyone who helped make Mod Studio"))
        cb.clicked.connect(self.credits)
        h.addWidget(cb)
        # mato 19.10.: the Ko-fi link always in sight, next to Credits (the name is Ko-fi's own, not translated)
        kb = QToolButton()
        kb.setObjectName("menu")
        kb.setText("♥ Ko-fi")
        kb.setToolTip(_("Support FL26 Mod Studio"))
        kb.clicked.connect(self.open_kofi)
        self.kofi_btn = kb
        h.addWidget(kb)
        h.addStretch(1)
        self.run_label = QLabel("")
        self.run_label.setObjectName("running")
        h.addWidget(self.run_label)
        h.addSpacing(10)
        # ready or not, in so many words, next to the button that starts the game (the design of 15.10.)
        self.h_ready = QLabel("")
        self.h_ready.setObjectName("pill")
        h.addWidget(self.h_ready)
        h.addSpacing(8)
        self.play_btn = QPushButton(_("Start the game"))
        self.play_btn.setObjectName("play")
        self.play_btn.setToolTip(_("Start the game with the current setup (as the desktop shortcut does)"))
        self.play_btn.clicked.connect(self.play)
        h.addWidget(self.play_btn)
        return w

    def _header(self):
        """the state boxes under the name: what is in the game now, each with its number, red with
        the problem's name when something is wrong (B37: say WHAT is missing, not only "2 missing")"""
        w = QWidget()
        w.setObjectName("topbar")
        w.setAttribute(Qt.WA_StyledBackground, True)
        h = QHBoxLayout(w)
        h.setContentsMargins(14, 2, 14, 6)
        h.setSpacing(8)
        self.stats = {}
        for key, cap, stretch, page in (("game", "GAME FOLDER", 3, "Settings"), ("sider", "SIDER", 2, "Settings"),
                                        ("world", "ACTIVE WORLD", 2, "Roots"), ("modules", "MODULES", 2, "Modules"),
                                        ("leagues", "LEAGUES", 1, "Leagues"), ("pack", "PACK", 3, "Install")):
            s = Stat(_(cap), lambda p=page: self.open_page(p))
            self.stats[key] = s
            h.addWidget(s, stretch)
        # kept for the code that wrote here before
        self.h_game = self.stats["game"].val
        self.h_profile = QLabel("")
        return w

    def _nav(self):
        """the sections from NAV, numbered across the top; a group that folded in the old left bar
        (Game content, Tools) is one button with its pages in a menu"""
        w = QWidget()
        w.setObjectName("nav")
        w.setAttribute(Qt.WA_StyledBackground, True)
        h = QHBoxLayout(w)
        h.setContentsMargins(10, 0, 10, 0)
        h.setSpacing(2)
        self.nav_group = QButtonGroup(self)
        self.nav_history, self.nav_at = [], -1
        self.nav_buttons, self.nav_group_of, self.nav_folds, self.nav_heads = {}, {}, {}, {}
        self.nav_titles = {}
        # 0.2.5: back and forward through the pages you had open, as in a browser (Vicentico 16.10.:
        # could not find his way back to Build details). Alt+Left/Right and the mouse's side
        # buttons do the same; only whole pages are remembered, not what was picked on them.
        self.nav_back, self.nav_fwd = QToolButton(), QToolButton()
        for b, text, tip, go, keys in ((self.nav_back, "◀", _("Back"), self.go_back, (QKeySequence.Back, "Alt+Left")),
                                       (self.nav_fwd, "▶", _("Forward"), self.go_forward, (QKeySequence.Forward, "Alt+Right"))):
            b.setObjectName("navitem")
            b.setText(text)
            b.setToolTip(tip)
            b.setAccessibleName(tip)
            b.setCursor(Qt.PointingHandCursor)
            b.setEnabled(False)
            b.clicked.connect(go)
            for k in keys:
                QShortcut(QKeySequence(k), self, go)
            h.addWidget(b)
        h.addSpacing(8)
        titles = {cls.__name__: cls.title for _c, group in page_groups() for cls in group}
        n = 0
        for caption, folds, sections in NAV:
            if caption and folds:
                n += 1
                b = QToolButton()
                b.setObjectName("navitem")
                b.setCheckable(True)
                b.setPopupMode(QToolButton.InstantPopup)
                b.setCursor(Qt.PointingHandCursor)
                theme.caps(b)
                m = QMenu(b)
                for key, title, names in sections:
                    t = _(title or titles[names[0]])
                    m.addAction(t).triggered.connect(lambda _c=False, p=names[0]: self.open_page(p))
                    self.nav_buttons[key] = b
                    self.nav_group_of[key] = caption
                    self.nav_titles[key] = t
                b.setMenu(m)
                b.number, b.caption = n, _(caption.capitalize())
                b.setText("%d. %s  ▾" % (n, b.caption))
                b.setAccessibleName(b.caption)
                self.nav_heads[caption] = b
                self.nav_group.addButton(b)
                h.addWidget(b)
                continue
            for key, title, names in sections:
                n += 1
                t = _(title or titles[names[0]])
                b = QPushButton("%d. %s" % (n, t))
                b.setObjectName("navitem")
                # what Windows reads out (and a test clicks) is the name without its number
                b.setAccessibleName(t)
                b.setCheckable(True)
                b.setCursor(Qt.PointingHandCursor)
                theme.caps(b)
                b.clicked.connect(lambda _c=False, p=names[0]: self.open_page(p))
                self.nav_group.addButton(b)
                self.nav_buttons[key] = b
                self.nav_titles[key] = t
                h.addWidget(b)
        h.addStretch(1)
        return w

    def nav_open(self, group):
        return group in (self.settings.get("nav_open") or [])

    def fold(self, group, on, save=True):
        """the old left bar opened and folded its groups; the sections across the top have a menu
        for them instead, so there is nothing to fold (kept for callers)"""
        return

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
        self.section_holder = {}
        for _caption, _folds, sections in NAV:
            for key, _title, names in sections:
                for n in names:
                    self.section_of[n] = key
                if key == "World":
                    # My world: header, world cards, its pages as tabs (pages/myworld.py)
                    from modstudio.pages.myworld import MyWorld
                    inside = [n for n, k in OPEN_FOR.items() if k == key and n in self.pages]
                    self.my_world = MyWorld(self, [(n, held(n)) for n in names], [(n, held(n)) for n in inside])
                    for n in names + inside:
                        self.section_of[n] = key
                        placed.add(n)
                    self.section_tabs[key] = self.my_world.tabs
                    self.section_holder[key] = self.my_world
                    self.stack.addWidget(self.my_world)
                    continue
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
                hv.addWidget(tabs)
                self.section_tabs[key] = tabs
                self.section_holder[key] = holder
                self.stack.addWidget(holder)
        for n, p in self.pages.items():
            if n not in placed:
                self.stack.addWidget(held(n))

    def _world_build(self):
        """My world's Build and install: the Build page's own (its log is Build details)"""
        self.open_page("Build")
        self.page("Build").build_all()

    def update_world_bar(self, progress=None):
        """My world's header now: progress is the build's time and step ("" when it is over)"""
        if hasattr(self, "my_world"):
            self.my_world.update_bar(progress)

    def open_my_world(self):
        """My world on the tab that was open last (Leagues the first time)"""
        tabs = self.my_world.tabs
        name = next((n for n, h in self.holder_of.items() if h is tabs.currentWidget() and h in tabs.buttons),
                    "Leagues")
        self.open_page(name)

    # ---- pages ----
    def page(self, name):
        return self.pages[name]

    def open_page(self, name):
        if not getattr(self, "_nav_jump", False) and name in self.pages:
            hist = self.nav_history
            if not hist or hist[self.nav_at] != name:
                del hist[self.nav_at + 1:]
                hist.append(name)
                del hist[:-50]
                self.nav_at = len(hist) - 1
            self._nav_arrows()
        p = self.pages[name]
        key = self.section_of.get(name) or OPEN_FOR.get(name)
        tabs = self.section_tabs.get(key) if name in self.section_of else None
        if tabs is not None:
            self.stack.setCurrentWidget(self.section_holder[key])
            if tabs.currentWidget() is not self.holder_of[name]:
                tabs.blockSignals(True)
                tabs.setCurrentWidget(self.holder_of[name])
                tabs.blockSignals(False)
        else:
            self.stack.setCurrentWidget(self.holder_of[name])
        b = self.nav_buttons.get(key)
        if b:
            b.setChecked(True)
        # a group's button says which of its pages is open ("6. Tools: Lua modules")
        for head in self.nav_heads.values():
            head.sub = self.nav_titles.get(key) if b is head else None
            self._head_text(head)
        self.settings["page"] = name
        if key == "World":
            self.my_world.shown()
        try:
            p.shown()
        except Exception as e:
            p.say(_("This section could not be shown: %s") % e, "err")

    def _nav_arrows(self):
        self.nav_back.setEnabled(self.nav_at > 0)
        self.nav_fwd.setEnabled(self.nav_at < len(self.nav_history) - 1)

    def _nav_go(self, step):
        """open the page `step` places away in the history without adding to it"""
        at = self.nav_at + step
        if not 0 <= at < len(self.nav_history):
            return
        self.nav_at = at
        self._nav_jump = True
        try:
            self.open_page(self.nav_history[at])
        finally:
            self._nav_jump = False
        self._nav_arrows()

    def go_back(self):
        self._nav_go(-1)

    def go_forward(self):
        self._nav_go(1)

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

    def _text_box_took(self, redo):
        """a text box with the focus keeps Ctrl+Z / Ctrl+Y for its own text"""
        from PySide6.QtWidgets import QLineEdit, QPlainTextEdit, QTextEdit
        w = QApplication.focusWidget()
        if isinstance(w, QLineEdit):
            if w.isRedoAvailable() if redo else w.isUndoAvailable():
                (w.redo if redo else w.undo)()
                return True
        elif isinstance(w, (QTextEdit, QPlainTextEdit)):
            (w.redo if redo else w.undo)()
            return True
        return False

    def undo(self):
        if self._text_box_took(False):
            return
        if self.project.undo():
            self.status(_("Change taken back"))
            self.show_saved()

    def redo(self):
        if self._text_box_took(True):
            return
        if self.project.redo():
            self.status(_("Change done again"))
            self.show_saved()

    def show_saved(self):
        p = self.project
        self.status_undo.setEnabled(p.can_undo())
        self.status_redo.setEnabled(p.can_redo())
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

    def update_header(self, problems=None):
        """the state boxes, ready or not and the status bar's first words, from what is on disk now.
        problems: the red lines of Home's ready check, by name (Home passes them each time it looks;
        they count until something changes while Home is not open)"""
        from modstudio import checks, installer, backups
        home = self.pages.get("Overview") if hasattr(self, "pages") else None
        if problems is not None:
            self._home_problems = list(problems)
        elif home is None or not home.isVisible():
            self._home_problems = []
        g, st = self.game, self.stats
        prof = self.settings.get("profile")
        bad = []
        if g.folder:
            st["game"].set(g.folder, "" if g.ok() else "err",
                           "\n".join(x for x in (g.folder, g.version(), (_("Profile: %s") % prof) if prof else "") if x))
        else:
            st["game"].set(_("not chosen"), "err", _("Game > Choose the game folder"))
        if not g.ok():
            bad.append(_("no game folder") if not g.folder else "; ".join(_(p) for p in g.problems()))
        # Sider: its folder and version (sider.exe's own number)
        exe = os.path.join(g.sider_dir, "sider.exe") if g.folder else ""
        if g.ok() and os.path.isfile(exe) and os.path.isfile(g.ini_path):
            ver = file_version(exe)
            st["sider"].set((_("%s OK") % ver) if ver else _("OK"), "ok",
                            "%s\n%s" % (g.sider_dir, _("Sider %s") % ver if ver else ""))
        elif g.ok():
            st["sider"].set(_("not found"), "err", _("No Sider folder with sider.exe and sider.ini in the game folder"))
            bad.append(_("Sider is not in the game folder"))
        else:
            st["sider"].set("—", "", "")
        live = self.project.live_worlds() if g.ok() else []
        if len(live) > 1:
            st["world"].set(", ".join(live), "err", _("%d worlds are in the game; only one should be") % len(live))
            bad.append(_("%d worlds are switched on; only one should be") % len(live))
        elif live:
            st["world"].set(live[0], "info", _("The world switched on in the game"))
        else:
            st["world"].set(_("none"), "", _("No world of yours is switched on in the game"))
        # Mod Studio's modules: the count, or the files that are not right, by name
        state = checks.modules_state(g) if g.ok() else None
        if state and checks.modules_ok(state):
            n = state["total"]
            st["modules"].set(_("%d / %d ON") % (n - len(state["left_off"]), n), "ok",
                              _("Mod Studio's modules: installed, up to date and switched on"))
        elif state:
            names = state["missing"] + state["changed"] + state["off"]
            if state["missing"]:
                v = _("%d missing") % len(state["missing"])
            elif state["changed"]:
                v = _("%d older") % len(state["changed"])
            else:
                v = _("%d off") % len(state["off"])
            what = []
            if state["missing"]:
                what.append(_("missing: %s") % ", ".join(state["missing"]))
            if state["changed"]:
                what.append(_("older or damaged: %s") % ", ".join(state["changed"]))
            if state["off"]:
                what.append(_("switched off: %s") % ", ".join(state["off"]))
            st["modules"].set(v, "err", "\n".join(what))
            bad.append(_("Mod Studio's modules: %s") % "; ".join(what) if names else v)
        else:
            st["modules"].set("—", "", "")
        r = self.project.recipe
        if live and r.get("world") in live:
            st["leagues"].set(str(len(r.get("leagues") or [])), "", _("Leagues in %s") % r.get("world"))
        else:
            st["leagues"].set("—", "", _("Open the world in the game to see its leagues"))
        recs = installer.records(g.sider_dir) if g.ok() else []
        if recs:
            last = max(recs, key=lambda x: x.get("time", ""))
            st["pack"].set(last.get("name", "?"), "", _("%d packs installed here; the last one: %s")
                           % (len(recs), last.get("name", "?")))
        else:
            st["pack"].set("—", "", _("No pack installed with Import your world"))
        try:
            pts = len(backups.history(g.sider_dir)) if g.ok() else 0
        except Exception:
            pts = 0
        self.status_points.setText(_("RESTORE POINTS: %d") % pts if pts else "")
        problems = bad + [p for p in self._home_problems if p not in bad]
        if problems:
            self.h_ready.setText("■ " + _("NOT READY"))
            state_ = "err"
            first = problems[0]
            self.status_state.setText("● " + (first if len(first) <= 60 else first[:57] + "..."))
        elif not live:
            self.h_ready.setText("■ " + _("NO WORLD YET"))
            state_ = "warn"
            self.status_state.setText("● " + _("No world switched on yet"))
        else:
            self.h_ready.setText("■ " + _("READY TO PLAY"))
            state_ = "ok"
            self.status_state.setText("● " + _("SYSTEM READY"))
        tip = "\n".join("• " + p for p in problems) if problems else ""
        for w in (self.h_ready, self.status_state):
            w.setProperty("state", state_)
            w.setToolTip(tip)
            theme.repolish(w)
        self.h_profile.setText(_("Profile: %s") % prof if prof else "")

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
                self, _("Start the game"), _("There are problems with the module order:") + "\n\n" +
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
                                "La langue change au prochain démarrage du programme.\n"
                                "O idioma muda quando o programa for aberto de novo.")

    def start_tour(self):
        """the quick tour of where things are (modstudio/tour.py); one at a time"""
        from modstudio import tour
        if getattr(self, "_tour", None) is not None:
            return
        self._tour = tour.Tour(self, done=lambda: setattr(self, "_tour", None),
                               follow=(_("Show me how to install a Modpack"), self.start_modpack_guide)).start()

    KOFI = "https://ko-fi.com/mata28"

    def open_kofi(self):
        """the Ko-fi button next to Credits: the page in the browser"""
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl(self.KOFI))

    def ask_support(self):
        """mato 19.10.: the first start of a version reminds, in two lines, that Ko-fi is there.
        Once per version (settings "support"); after the quick tour, never over it"""
        if self.settings.get("support") == VERSION:
            return
        if getattr(self, "_tour", None) is not None:
            QTimer.singleShot(2000, self.ask_support)
            return
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        self.settings["support"] = VERSION
        self.save_settings()
        box = QMessageBox(self)
        box.setWindowTitle(_("Support FL26 Mod Studio"))
        # the link itself in the box too, not only behind the button (mato 19.10.)
        import html
        box.setTextFormat(Qt.RichText)
        box.setTextInteractionFlags(Qt.TextBrowserInteraction)
        box.setText(html.escape(_("FL26 Mod Studio is free and donating is never required, but a small donation "
                                  "on Ko-fi makes it easier for us to keep the project maintained and updated. "
                                  "Thank you!"))
                    + '<br><br><a href="%s">%s</a>' % (self.KOFI, self.KOFI.split("//", 1)[1]))
        kofi = box.addButton(_("Support on Ko-fi"), QMessageBox.AcceptRole)
        box.addButton(_("Not now"), QMessageBox.RejectRole)
        box.setDefaultButton(kofi)
        box.finished.connect(lambda _r: box.clickedButton() is kofi
                             and QDesktopServices.openUrl(QUrl(self.KOFI)))
        box.open()
        self._support = box

    def start_modpack_guide(self):
        """Help > Install a Modpack, step by step: the tour's card, every click in order (tour.modpack_steps)"""
        from modstudio import tour
        if getattr(self, "_tour", None) is not None:
            return
        self._tour = tour.Tour(self, done=lambda: setattr(self, "_tour", None), guide="modpack",
                               follow=(_("Show me how to edit a Modpack"), self.start_edit_guide)).start()

    def start_edit_guide(self):
        """Help > Edit a Modpack, step by step: Make it editable..., the tabs, Build and install (tour.edit_steps)"""
        from modstudio import tour
        if getattr(self, "_tour", None) is not None:
            return
        self._tour = tour.Tour(self, done=lambda: setattr(self, "_tour", None), guide="edit").start()

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

    def _head_text(self, head):
        sub = getattr(head, "sub", None) if not getattr(self, "_compact", False) else None
        head.setText("%d. %s%s  ▾" % (head.number, head.caption, (": " + sub) if sub else ""))

    def resizeEvent(self, e):
        """0.2.4: a narrow window (under 1260 px, down to the 1080 the window keeps) gets a tighter
        bar: no name next to >_, tighter sections, a group's button without its page's name"""
        super().resizeEvent(e)
        compact = self.width() < 1260
        if compact == getattr(self, "_compact", False) or not hasattr(self, "nav_heads"):
            return
        self._compact = compact
        self.h_title.setVisible(not compact)
        pad = "padding: 8px 6px 6px 6px;" if compact else ""
        for b in set(self.nav_buttons.values()) | set(self.nav_heads.values()):
            b.setStyleSheet(pad)
        for head in self.nav_heads.values():
            self._head_text(head)

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
        keep_error(kind, err, tb)
        previous(kind, err, tb)
    return hook


def keep_error(kind, err, tb):
    """an error in a click goes to errors.log next to settings.json: the exe has no console, so a
    button that failed did nothing and said nothing (B161, vmican 19.10.: Remove and Edit league,
    no box, no crash.log). The newest last; the file is cut back when it passes 1 MB"""
    try:
        import traceback, time
        os.makedirs(APPDIR, exist_ok=True)
        p = os.path.join(APPDIR, "errors.log")
        if os.path.exists(p) and os.path.getsize(p) > 1 << 20:
            with open(p, "rb") as f:
                f.seek(-(256 << 10), 2)
                tail = f.read()
            with open(p, "wb") as f:
                f.write(tail)
        with open(p, "a", encoding="utf-8") as f:
            f.write("---- %s  Mod Studio %s\n%s" % (time.strftime("%Y-%m-%d %H:%M:%S"), VERSION,
                                                     "".join(traceback.format_exception(kind, err, tb))))
    except Exception:
        pass


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
    if os.environ.get("FL26_SHOT_SIZE"):          # --shot at a given window size ("1280x720")
        w.resize(*(int(x) for x in os.environ["FL26_SHOT_SIZE"].split("x")))
    w.show()
    if "--shot" in sys.argv:                     # a picture of each page, for the guide
        out = sys.argv[sys.argv.index("--shot") + 1]
        os.makedirs(out, exist_ok=True)

        def shoot():
            for name in w.pages:
                w.open_page(name)
                for _i in range(6):              # layouts settle one level per pass
                    app.processEvents()
                w.grab().save(os.path.join(out, name + ".png"))
            # My world's + Add... over the window, as it opens
            from modstudio.pages.myworld import AddDialog
            w.open_page("Leagues")
            d = AddDialog(w.my_world, w.my_world.card_title())
            if os.environ.get("FL26_SHOT_ADD"):          # a file to pick in it
                d.pick(os.environ["FL26_SHOT_ADD"])
            d.show()
            for _i in range(8):
                app.processEvents()
            shot = w.grab()
            from PySide6.QtGui import QPainter, QColor
            p = QPainter(shot)
            p.fillRect(shot.rect(), QColor(0, 0, 0, 176))
            pic = d.grab()
            p.drawPixmap((shot.width() - pic.width()) // 2, 170, pic)
            p.end()
            shot.save(os.path.join(out, "MyWorld-Add.png"))
            d.close()
            app.quit()
        QTimer.singleShot(1500, shoot)
    else:
        # 0.2.4: the first start of a version with a new look shows where things are now
        # (FL26_NO_TOUR=1: the exe tests that click through the window)
        from modstudio import tour
        if tour.due(w.settings) and not os.environ.get("FL26_NO_TOUR"):
            QTimer.singleShot(1500, w.start_tour)
        if not os.environ.get("FL26_NO_TOUR"):
            QTimer.singleShot(2500, w.ask_support)
        if w.settings.get("check_updates", True):
            QTimer.singleShot(3000, lambda: w.check_updates(quiet=True))
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
