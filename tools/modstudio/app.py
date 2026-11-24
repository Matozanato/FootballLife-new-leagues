r"""python -m modstudio.app   -> the FL Mod Studio window

    top bar      the name, File / Game / Profiles / Language / Help menus, ready or not, Start the game
    state boxes  the game folder, Sider, the world in the game, the modules, its leagues, the pack
    sections     numbered across the top (pages/*.py); Game content and Tools open a menu
    centre       the open section
    status bar   ready or the problem, what the program is doing, whether the world is saved

Settings (game folder, language, window size) live in %APPDATA%\FL26ModStudio\settings.json.
"""
import json, os, sys
import bigjson

HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))

from PySide6.QtCore import Qt, QSize, QTimer, Signal, QObject
from PySide6.QtGui import QAction, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QButtonGroup, QDialog, QFrame, QHBoxLayout, QLabel, QMainWindow,
                               QMenu, QPushButton, QScrollArea, QSizePolicy, QStackedWidget, QStatusBar,
                               QTextBrowser, QToolButton, QVBoxLayout, QWidget, QMessageBox)

from modstudio import VERSION, anim, icons, theme, i18n
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
    from modstudio.pages import manager, overview, roots, modules, install, profiles, restore
    from modstudio.pages import content, stadiums, balls, kits, commentary, music, trophies
    from modstudio.pages import builder, players, packages, diagnostics, settings, newlife, leagues, cups
    return [
        ("", [overview.Overview]),
        ("LEAGUE BUILDER", [leagues.Leagues, builder.NewClubs, players.Players, newlife.NewLife,
                            packages.Packages, builder.Build, cups.Cups]),
        ("GAME CONTENT", [kits.Kits, stadiums.Stadiums, balls.Balls, commentary.Commentary,
                          music.Music, content.Servers, trophies.Trophies]),
        ("MANAGE", [manager.ModManager, install.Install, modules.Modules, roots.Roots, profiles.Profiles, restore.Restore,
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
    ("MY WORLD", False, [("World", "My world", ["Build", "Leagues", "NewClubs", "Players", "Kits", "Stadiums", "Cups"])]),
    ("GAME CONTENT", True, [(n, None, [n]) for n in ("Balls", "Commentary", "Music", "Trophies", "Servers")]),
    ("TOOLS", True, [(n, None, [n]) for n in
                     ("ModManager", "Modules", "Roots", "Profiles", "Restore", "Diagnostics")]),
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


def warm_game_info(base):
    """leaguebuilder.game_info read ahead, from a worker (it is read once per tables). B480
    (17.11.2026): the NewLife page counts with it at project.changed, and the first time was at the
    end of a world zip install or of Make it editable -- 0.25 s of the 0.55 s the window stood still
    in the stall test with 220,000 players"""
    if not base:
        return
    try:
        import leaguebuilder
        leaguebuilder.game_info(base)
    except Exception:
        pass                              # the page reads it itself then, and says what is wrong


class Main(QMainWindow):
    _running_got = Signal(bool, bool)       # (game running, Sider running), asked by a worker

    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        anim.set_on(self.settings.get("animations", True))
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
        self.project.tables_changed.connect(self._live_after_tables)
        self.setWindowTitle("FL Mod Studio")
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
        self._warming, self._warmed = None, None
        self.project.changed.connect(self.warm_pictures)
        QTimer.singleShot(0, self.warm_pictures)
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

    def _live_open(self, live):
        """the world open in Mod Studio is one of the worlds in the game. The empty world of a start
        never is, whatever its name: it got a free name for the game found at the start, and another
        game folder picked in Settings since can have a world of that name (B399, U4 10.11.: the
        empty _FL26MyWorld was taken for the _FL26MyWorld in the game, whose leagues never opened)"""
        return self.project.recipe.get("world") in live and not self.project.untouched()

    def live_recipe(self, fresh=False):
        """the file part of open_live_world, with no window work so it can run off the window's
        thread: (the world in the game, its recipe copy, the recipe read or None), or None when
        there is nothing to open. On the Modpack it is most of the 9 s the window stood still after
        a switch (coldstart, 17.10.): reading its 132 MB recipe back from the plan, writing the copy,
        reading it, and making the 86 league logos small.

        fresh (B468, 14.11.): the world was installed from a zip just now, so a copy of a recipe of
        that name is an older world's (GigaPack beta 1 and beta 2 are both _FL26Megapack: the
        Leagues page showed beta 1's Argentina, "not built yet" and no crests, over beta 2's plan).
        The copy goes aside to <world>.json.before-install and the recipe is read from the plan
        again, also when a world of that name is the one open"""
        live = self.project.live_worlds()
        if not live or (not fresh and self._live_open(live)):
            return None
        kept = os.path.join(self.project.copies_dir(), live[0] + ".json")
        if fresh and os.path.exists(kept) and self.project.base:
            try:
                os.replace(kept, kept + ".before-install")
            except OSError:
                pass
        if not os.path.exists(kept) and self.project.base:
            # no copy of its recipe (built before Build kept one, or elsewhere): read the
            # recipe back from the plan the world carries (leaguebuilder.recipe_from_plan)
            try:
                import leaguebuilder
                plan = os.path.join(self.game.livecpk_dir, live[0], "leaguebuilder-plan.json")
                with open(plan, encoding="utf-8") as f:
                    read = bigjson.load(f)
                rec = leaguebuilder.recipe_from_plan(read, self.project.base)
                # B480 round 3 (17.11.2026): the plan and this recipe (millions of objects) went
                # where their last name went, each in one call of C with Python's lock held, from
                # this worker: freed by letgo's thread instead, in small steps
                from modstudio import letgo
                letgo.drop(read)
                del read
                os.makedirs(self.project.copies_dir(), exist_ok=True)
                # not dump(): see Project._write. In steps: one json.dumps of the GigaPack's recipe
                # stopped the window for 1.4 s from this worker (B479, 15.11.)
                text = bigjson.dumps(rec, 1, False)
                with open(kept, "w", encoding="utf-8") as f:
                    # in 4 MB pieces too: one write of the whole text (encoding it, \n to \r\n)
                    # held the interpreter from this worker for 0.95 s at the end of a GigaPack
                    # zip install (B480, the stall probe 16.11.); the same bytes
                    for i in range(0, len(text), 1 << 22):
                        f.write(text[i:i + (1 << 22)])
            except Exception:
                pass
            else:
                from modstudio import letgo
                letgo.drop(rec)
        rec = None
        if os.path.exists(kept):
            try:
                with open(kept, encoding="utf-8") as f:
                    rec = bigjson.load(f)
                from modstudio.pages import builder as _PB
                _PB.warm([L.get("logo") for L in rec.get("leagues") or []], (20, 28))
                # the Cups page's pictures and the copy Undo compares with, here too (11.11.: on
                # the window's thread they were 2 s of Put in the game and most of the 5 s the
                # Cups page took to open with 317 leagues)
                _PB.warm([L.get(k + "_logo") for L in rec.get("leagues") or []
                          for k in ("cup", "supercup", "league_cup")], (32,))
                for k, v in (("leagues", []), ("edits", {}), ("players", {})):
                    rec.setdefault(k, v)
                self._live_snap = (rec, self.project._split(rec))
            except Exception:
                pass
        warm_game_info(self.project.base)
        return live[0], kept, rec

    def warm_pictures(self):
        """the small pictures of the open world's league and cup logos, made in the background once
        per world opened. Until 11.11. only Put in the game made them ahead (live_recipe): a start
        with the big world open already, or File > Open, left them to the pages, and the first
        visit of Leagues, New leagues and Cups stood the window still for 2 to 5 s with 317
        leagues (300 logos read and made small on the window's thread; the UI tour in es/fr/pt/hr)"""
        rec = self.project.recipe
        if rec is self._warmed:
            return
        self._warmed = rec
        leagues = [L for L in rec.get("leagues") or [] if isinstance(L, dict)]
        logos = [L.get("logo") for L in leagues if L.get("logo")]
        cups = [L.get(k + "_logo") for L in leagues for k in ("cup", "supercup", "league_cup") if L.get(k + "_logo")]
        if not logos and not cups and not rec.get("players"):
            return
        import threading
        from modstudio.pages import builder as _PB

        def work():
            try:
                _PB.warm(logos, (20, 28))
                _PB.warm(cups, (32,))
                # the squads of the game's tables too: the Leagues page counts the players of the
                # clubs the world changes, and reading them was another 0.5 s of its first opening
                if any((rec.get("players") or {}).values()):
                    self.project.squads()
            except Exception:
                pass

        # (_warming: true while one works -- the UI tour waits for it, as it waits for a job)
        self._warming = t = threading.Thread(target=work, daemon=True, name="warm-pictures")
        t.start()

    def open_live_world(self, found=False, fresh=False):
        """open the recipe of the world in the game when another one is open (at a start, and after
        My world's Put in the game); what to tell, or "". found: what live_recipe() gave, when it
        ran in the background already"""
        if found is False:
            found = self.live_recipe(fresh)
        if not found:
            return ""
        world, kept, rec = found
        live = self.project.live_worlds()
        if not live or live[0] != world or (not fresh and self._live_open(live)):
            return ""
        note = ""
        was = self.project.recipe.get("world")
        if rec is not None:
            try:
                stale = fresh and self.project.path and os.path.normcase(os.path.abspath(
                    self.project.path)) == os.path.normcase(os.path.abspath(kept))
                if not stale:                      # B468: never the old world's recipe over the new copy
                    self.project.autosave()        # the world open now keeps its changes
                snap = getattr(self, "_live_snap", None)
                self._live_snap = None
                self.project.adopt(rec, kept, copy=True, snap=snap[1] if snap and snap[0] is rec else None)
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

    def _live_after_tables(self):
        """B399: the first start with a new APPDATA and a world in the game opens that world once the
        tables are unpacked (its recipe is read back from its plan, which needs them), in place of
        the empty world of the start. The empty one used to be called like the world in the game
        (_FL26MyWorld), so it was taken for it: the world's leagues never opened, and Build (after
        its question) replaced the world with the empty one"""
        if self.project.base is None or not self.project.untouched() or getattr(self, "_live_reading", False):
            return
        # its recipe is read in the background (review 11.11.: on the window's thread a big world's
        # plan, 128 MB, stood the window still at the first start and at every change of game folder)
        self._live_reading = True

        def opened(found):
            self._live_reading = False
            if not found or self.project.base is None or not self.project.untouched():
                return
            try:
                note = self.open_live_world(found)
            except Exception:
                return
            if note and getattr(self, "status_left", None) is not None:
                self.status(note)

        from modstudio.ui import run_job
        run_job(lambda _progress: self.live_recipe(), done=opened, failed=lambda _tb: opened(None))

    def auto_tables(self):
        """unpack the game's tables when there are none yet and no tables folder of your own was
        chosen (Settings has the button for doing it again after a game update)"""
        p = self.project
        if p.base is not None or not self.game.ok() or p.own_tables():
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
                a = m.addAction(label if it[2:3] == (True,) else _(label))
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
        self.h_title = QLabel("FL // MOD STUDIO")
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
            ("About FL Mod Studio", self.about)])
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
        kb.setToolTip(_("Support FL Mod Studio"))
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
        for b, way, tip, go, keys in ((self.nav_back, -1, _("Back"), self.go_back, (QKeySequence.Back, "Alt+Left")),
                                      (self.nav_fwd, 1, _("Forward"), self.go_forward, (QKeySequence.Forward, "Alt+Right"))):
            # (drawn, not the characters of some font: icons.py)
            b.setObjectName("navarrow")
            b.setIcon(icons.chevron(way))
            b.setIconSize(QSize(16, 16))
            b.setAutoRaise(True)
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
                # (the click comes before the tab changes: the page that goes fades out over the next)
                tabs.tabBarClicked.connect(lambda i, t=tabs: self._tab_fade(t, i))
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

    def _tab_fade(self, tabs, i):
        at = tabs.currentIndex()
        if 0 <= i != at and tabs.isTabEnabled(i) and tabs.currentWidget() is not None:
            anim.cover(tabs.currentWidget().parentWidget(), 1 if i > at else -1)

    @staticmethod
    def _side(box, old, new):
        """1 / -1: `new` stands after / before `old` in `box` (the sections, a section's tabs): the
        side the page slides in from. 0: one of them is not there, it just fades"""
        a, b = box.indexOf(old), box.indexOf(new)
        return 0 if a < 0 or b < 0 or a == b else (1 if b > a else -1)

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
            if self.stack.currentWidget() is not self.section_holder[key]:
                anim.cover(self.stack, self._side(self.stack, self.stack.currentWidget(), self.section_holder[key]))
            elif tabs.currentWidget() is not self.holder_of[name]:
                # another tab of the open section: only what is under the tabs moves
                area = tabs if isinstance(tabs, QStackedWidget) else tabs.currentWidget().parentWidget()
                anim.cover(area, self._side(tabs, tabs.currentWidget(), self.holder_of[name]))
            self.stack.setCurrentWidget(self.section_holder[key])
            if tabs.currentWidget() is not self.holder_of[name]:
                tabs.blockSignals(True)
                tabs.setCurrentWidget(self.holder_of[name])
                tabs.blockSignals(False)
        else:
            if self.stack.currentWidget() is not self.holder_of[name]:
                anim.cover(self.stack, self._side(self.stack, self.stack.currentWidget(), self.holder_of[name]))
            self.stack.setCurrentWidget(self.holder_of[name])
        b = self.nav_buttons.get(key)
        if b:
            # (not nav_group.checkedButton(): a click has checked the button before it gets here,
            # so the group always answered "the same one" and the line never travelled)
            was = getattr(self, "_nav_on", None)
            b.setChecked(True)
            self._nav_on = b
            if was is not None and was is not b:
                anim.line(b.parentWidget(), was, b, theme.ORANGE, theme.BAR)
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

    def save_ini(self, ini, reason, saved=False, running=None):
        """write sider.ini (a restore point is taken first) and tell every page. saved: a worker
        wrote it already (ini.save), running: Game.running() as that worker asked -- B480 round 2
        (17.11.2026): at the end of a world zip's install the restore point's copy and the look at
        the running programs took 1.2 s of a stopped window while the disk was still busy"""
        if not saved:
            ini.save(reason=reason)
        self.bus.ini_changed.emit()
        g, s = running if running is not None else Game.running()
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
            import leaguebuilder                   # the clubs and players a world may have in this game
            leaguebuilder.use_game(self.game.folder)

    def set_sider(self, name):
        """use the Sider folder `name` of the game folder (one of siderdir.candidates)"""
        siderdir.PREFERRED = name or None
        self.settings["sider"] = name or ""
        self.save_settings()
        self.game_paths()
        self.bus.game_changed.emit()

    def status(self, text):
        new = bool(text) and text != self.status_left.text()
        self.status_left.setText(text)
        if new:
            anim.notice(self.status_left)

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
            if getattr(self, "_header_held", False):          # the header waited for this job
                QTimer.singleShot(0, lambda: self.update_header(getattr(self, "_home_problems", None)))

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
        # modules not right while a job runs: the job may be the one that puts them there (a world
        # zip is installed first and switched on after, with its own modules). The header waits
        # for the job's end instead of turning red in between; busy() looks again then
        held = self._header_held = bool(state) and not checks.modules_ok(state) and self._busy > 0
        if held:
            st["modules"].set("…", "", _("Working..."))
        elif state and checks.modules_ok(state):
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
        recs = installer.records_seen(g.sider_dir) if g.ok() else []
        shown = installer.header_pack(recs, live)       # the active world's pack (B168)
        last = max(recs, key=lambda x: x.get("time", "")).get("name", "?") if recs else ""
        if shown:
            st["pack"].set(shown.get("name", "?"), "", _("%d packs installed here; the last one: %s")
                           % (len(recs), last))
        elif recs:
            st["pack"].set("—", "", _("The world in the game is not from a pack. %d packs installed here; "
                                      "the last one: %s") % (len(recs), last))
        else:
            st["pack"].set("—", "", _("No pack installed with Import your world"))
        try:
            pts = len(backups.history(g.sider_dir)) if g.ok() else 0
        except Exception:
            pts = 0
        self.status_points.setText(_("RESTORE POINTS: %d") % pts if pts else "")
        problems = bad + [p for p in self._home_problems if p not in bad]
        if held and not problems:
            self.h_ready.setText("■ " + _("Working...").upper())
            state_ = "warn"
            self.status_state.setText("● " + _("Working..."))
        elif problems:
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
        """asked off the window's thread: the process list is ~500 short calls into Windows, and
        while a worker is busy (a world read, a Build) the window's thread waits for Python's lock
        after each one -- 5.7 s of a stopped window on "back to the GigaPack", 1.2 s after Install
        (the stall recorder 15.11.2026, game._process_names under update_running)"""
        if getattr(self, "_running_asked", False):
            return
        if not getattr(self, "_running_wired", False):
            self._running_wired = True
            self._running_got.connect(self._show_running)
        self._running_asked = True
        import threading

        def work():
            try:
                g, s = Game.running()
            except Exception:
                g, s = False, False
            try:
                self._running_got.emit(bool(g), bool(s))
            except RuntimeError:        # the window is gone
                pass
        threading.Thread(target=work, name="running", daemon=True).start()

    def _show_running(self, g, s):
        self._running_asked = False
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
        QMessageBox.information(self, "FL Mod Studio",
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
        box.setWindowTitle(_("Support FL Mod Studio"))
        # the link itself in the box too, not only behind the button (mato 19.10.)
        import html
        box.setTextFormat(Qt.RichText)
        box.setTextInteractionFlags(Qt.TextBrowserInteraction)
        box.setText(html.escape(_("FL Mod Studio is free and donating is never required, but a small donation "
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
        QMessageBox.about(self, "FL Mod Studio",
                          "<b>FL Mod Studio</b> v%s<br><br>%s<br><br>%s" % (
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
                QMessageBox.information(self, _("Updates"), _("FL Mod Studio is up to date (v%s).") % VERSION)

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
        head = QLabel("<b>%s</b>" % (_("FL Mod Studio %s is out (you have %s).") % (info["version"], VERSION)))
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
                                  "yourself, or move FL Mod Studio to a folder of your own.")
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
            self.status_left.setText(_("Installing the update; FL Mod Studio restarts by itself..."))
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
        cups = self.pages.get("Cups")
        if cups is not None and cups.has_drafts():
            box = QMessageBox(QMessageBox.Question, _("Unapplied cup changes"),
                              _("Cup drafts have not been applied to their projects. Close and discard these drafts? To keep editing, cancel and return to Cups."),
                              QMessageBox.Discard | QMessageBox.Cancel, self)
            box.setDefaultButton(QMessageBox.Cancel)
            if box.exec() != QMessageBox.Discard:
                e.ignore()
                return
        trophies = self.pages.get("Trophies")
        if trophies is not None and trophies.has_drafts():
            box = QMessageBox(QMessageBox.Question, _("Unapplied trophy changes"),
                              _("Trophy changes have not been applied to their worlds. Close and discard these drafts? Cancel to keep editing in Game content > Trophies."),
                              QMessageBox.Discard | QMessageBox.Cancel, self)
            box.setDefaultButton(QMessageBox.Cancel)
            if box.exec() != QMessageBox.Discard:
                e.ignore()
                return
        # changes made since the last Save recipe or Build were lost without a word when Mod
        # Studio closed (the poll, Bon Kirk 11.10.: "an Apply button" -- OK only keeps a change
        # in the open recipe). 0.2.5: a change of the last moment is saved like any other, the
        # autosave just did not come round yet; only a write that fails still asks
        if self.project.dirty:
            self.project.autosave()
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
        tell_error(err)
        previous(kind, err, tb)
    return hook


def main_window():
    return next((w for w in QApplication.topLevelWidgets() if isinstance(w, Main)), None)


def tell_error(err):
    """the status line says that a click failed and which file holds why. Until beta 3 the error
    only went to errors.log: the button "did nothing", and whoever reported it had nothing to send
    (Xxspedd 12.11.2026: "Edit league opens no window")"""
    try:
        w = main_window() if isinstance(err, Exception) else None
        if w is not None:
            w.status(_("That did not work (an unexpected error). Send this file with your report: %s")
                     % os.path.join(APPDIR, "errors.log"))
    except Exception:
        pass


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


def record_stalls(w, path, short=0.3):
    """FL26_STALLS=<file>: where every thread is whenever the window has not answered for 0.6 s
    (B479, 15.11.: a stop of 1.4 s after Install and after Switch on, and no way to see in what).
    The watcher is faulthandler's own C thread: it writes while Python's lock is held.

    16.11.: and a sampler. Every 50 ms of a stop of `short` seconds or more it notes the line the
    window's thread is at, and at the end of the stop writes the lines it saw most, so a stop is
    put down to a function and a line without reading the dumps. Each stop is also kept in
    w._stall_gaps as (when, seconds, [(where, count), ...]) for the tests. The lines come from
    faulthandler.dump_traceback, written in C in one go: walking sys._current_frames() from the
    sampler while the other threads ran closed the process (access violation in the sampler,
    3 times in 5 runs of the stall probe, 16.11.)"""
    import faulthandler
    import time as _time
    import threading as _th
    from collections import Counter
    from modstudio import ui as _ui
    w._stalls = open(path, "a", encoding="utf-8")
    w._stall_gaps = []
    w._stalls_timer = QTimer(w, interval=100)
    seen = [_time.perf_counter(), _ui.PROGRESS_SENT[0]]
    from modstudio import procstat as _ps
    try:
        _hb = _ps.beat()            # for tools/hangstacks.py --beat (B480 round 3)
    except Exception:
        _hb = None

    def _beat():
        now, sent = _time.perf_counter(), _ui.PROGRESS_SENT[0]
        if _hb is not None:
            _hb.tick()
        if now - seen[0] > 0.6:
            # after the stacks: how long it was, and how many progress lines of the
            # workers came in it (a window busy drawing them shows no Python frame)
            w._stalls.write("%s gap %.2f s, %d progress line(s) sent in it\n\n"
                            % (_time.strftime("%H:%M:%S"), now - seen[0], sent - seen[1]))
            w._stalls.flush()
        seen[0], seen[1] = now, sent
        # arming again replaces the last; repeat: a long stop is written every 0.6 s of it
        faulthandler.dump_traceback_later(0.6, repeat=True, file=w._stalls)
    w._stalls_timer.timeout.connect(_beat)
    w._stalls_timer.start()

    # a second watcher, a Python thread: in a stop it says every half second how long it
    # waited for its own turns and how much processor time the window's thread took. Its
    # own waits long: Python's lock is held by a worker. Its waits short and the window's
    # thread idle: the window waits for something outside Python. Its waits short and the
    # window's thread busy: Qt itself is working (drawing, laying out)
    import ctypes as _ct
    _k = _ct.WinDLL("kernel32")
    _k.OpenThread.restype = _ct.c_void_p
    _k.GetThreadTimes.argtypes = [_ct.c_void_p] + [_ct.c_void_p] * 4
    _h = _k.OpenThread(0x0040 | 0x0800, False, _k.GetCurrentThreadId())   # QUERY_(LIMITED_)INFORMATION
    main_id = _th.main_thread().ident

    def _cpu():
        t = (_ct.c_ulonglong * 4)()
        if not _h or not _k.GetThreadTimes(_h, _ct.byref(t, 0), _ct.byref(t, 8),
                                           _ct.byref(t, 16), _ct.byref(t, 24)):
            return 0.0, 0.0
        return t[3] / 1e7, t[2] / 1e7           # user, kernel

    import re as _re
    import tempfile as _tf
    _dump = _tf.TemporaryFile()
    _head = _re.compile(rb"(?:Current thread|Thread) 0x([0-9a-fA-F]+)")
    _line = _re.compile(rb'\s+File "(.*)", line (\d+) in (.*)')

    def _stacks():
        """{thread id: ["file:line function", ...] most recent first}, from faulthandler"""
        _dump.seek(0)
        _dump.truncate()
        faulthandler.dump_traceback(_dump, all_threads=True)
        _dump.seek(0)
        out, cur = {}, None
        for ln in _dump.read().splitlines():
            m = _head.match(ln)
            if m:
                cur = out.setdefault(int(m.group(1), 16), [])
                continue
            m = _line.match(ln)
            if m and cur is not None:
                cur.append("%s:%s %s" % (os.path.basename(m.group(1).decode("utf-8", "replace")),
                                         m.group(2).decode(), m.group(3).decode("utf-8", "replace")))
        return out

    def _where(lines, n=3):
        return " <- ".join((lines or [])[:n]) or "(no Python frame: in Qt or waiting)"

    try:
        from PySide6.QtGui import QAccessible as _qacc
    except Exception:
        _qacc = None

    # B480 round 3 (17.11.2026): in the stops of beta4r's exe test (3.9 s at the end of Build) this
    # sampler got its own turn only after the stop, when the worker that had kept Python's lock was
    # done: it wrote "1x letgo" and nothing of the holder, which faulthandler's C dumps showed the
    # whole time (builder.built_plan). The summary now counts the threads of those dumps too, and
    # says from Windows which threads took the processor in the stop and how many page faults the
    # process had (a stop with every thread idle and the faults in the hundreds of thousands is the
    # memory coming back from the disk, not Python)
    _fh_thread = _re.compile(r"^(?:Current thread|Thread) 0x([0-9a-fA-F]+)")
    _fh_line = _re.compile(r'^\s+File "(.*)", line (\d+) in (.*)')
    mine = [None]

    def _dumped(since):
        """{where: count} of the threads other than the window's and the watcher's in the C
        watchdog's dumps written to the file since offset `since`"""
        got = Counter()
        try:
            with open(path, "rb") as f:
                f.seek(since)
                text = f.read(4 << 20).decode("utf-8", "replace")
        except OSError:
            return got
        cur, lines = None, []

        def flush():
            if cur is not None and cur not in (main_id, mine[0]):
                got[_where(lines, 2) if lines else "(no Python frame: in C or waiting)"] += 1
        for ln in text.splitlines():
            m = _fh_thread.match(ln)
            if m or ln.startswith("Timeout ("):
                flush()
                cur, lines = (int(m.group(1), 16) if m else None), []
                continue
            m = _fh_line.match(ln)
            if m and cur is not None:
                lines.append("%s:%s %s" % (os.path.basename(m.group(1)), m.group(2), m.group(3)))
        flush()
        return got

    def _watch():
        mine[0] = _th.get_ident()
        last, worst, told, at = _time.perf_counter(), 0.0, 0.0, _cpu()
        where, others, opened = Counter(), Counter(), None
        took_me = 0.0
        calm_at, calm = 0.0, None           # (threads, memory, file offset) a moment before a stop
        while True:
            _time.sleep(0.05)
            now = _time.perf_counter()
            worst, last = max(worst, now - last - 0.05), now
            gap = now - seen[0]
            if gap < short and opened is None and now - calm_at >= 0.5:
                try:
                    w._stalls.flush()
                    calm = (_ps.threads(tids=list(_stacks())), _ps.memory(), os.path.getsize(path))
                except Exception:
                    calm = None
                calm_at = _time.perf_counter()
                last = calm_at              # (its own time is not a wait for a turn)
            if gap >= short:
                if opened is None:
                    opened = seen[0]
                try:
                    frames = _stacks()
                except Exception:
                    frames = {}
                # B480 (17.11.2026): the wait for a turn is the sleep's alone now; the sampling
                # (faulthandler writes the stacks with Python's lock held) is told apart below
                last = _time.perf_counter()
                took_me = max(took_me, last - now)
                where[_where(frames.get(main_id))] += 1
                for tid, f in frames.items():
                    if tid not in (main_id, _th.get_ident()):
                        others[_where(f, 2) if f else "(no Python frame: in C or waiting)"] += 1
            elif opened is not None:
                took = seen[0] - opened if seen[0] > opened else gap
                top = where.most_common(4)
                w._stall_gaps.append((opened, took, top))
                if took >= short:
                    try:
                        extra = ""
                        if calm is not None:
                            w._stalls.flush()
                            dumps = _dumped(calm[2])
                            if dumps:
                                extra += ("  other threads in faulthandler's dumps (written while the lock was held):\n%s\n"
                                          % "\n".join("    %3dx %s" % (n, s) for s, n in dumps.most_common(4)))
                            extra += "  " + _ps.told(calm[0], _ps.threads(tids=list(calm[0]) + list(_stacks())), calm[1], _ps.memory()) + "\n"
                        w._stalls.write("%s stop %.2f s; the window's thread was at:\n%s\n  other threads:\n%s\n%s\n" % (
                            _time.strftime("%H:%M:%S"), took,
                            "\n".join("    %3dx %s" % (n, s) for s, n in top),
                            "\n".join("    %3dx %s" % (n, s) for s, n in others.most_common(4)), extra))
                        w._stalls.flush()
                    except Exception:
                        return
                where, others, opened = Counter(), Counter(), None
            if gap < 0.6:
                worst, told, at, took_me = 0.0, now, _cpu(), 0.0
            elif now - told >= 0.5:
                u, kk = _cpu()
                try:
                    # (and whether a program reads the window through Windows' accessibility -- a UI
                    # test driver, a screen reader: Qt then answers it from the window's thread)
                    w._stalls.write("  watcher: stopped %.1f s so far; my longest wait for a turn "
                                    "%.2f s (my sampling up to %.2f s); the window's thread took %.2f s user "
                                    "+ %.2f s kernel; accessibility %s\n"
                                    % (gap, worst, took_me, u - at[0], kk - at[1],
                                       "?" if _qacc is None else ("on" if _qacc.isActive() else "off")))
                    w._stalls.flush()
                except Exception:
                    return
                told = now
    _th.Thread(target=_watch, name="stallwatch", daemon=True).start()

    # and the garbage collector: one pass of it keeps Python's lock from start to end and
    # shows in the stacks only as the line that happened to allocate (16.11.: 10-15 s
    # stops with a worker "in" a list comprehension and nothing in C under it)
    import gc as _gc
    _gcat = {}

    def _gcsaid(phase, info):
        g = info.get("generation")
        if phase == "start":
            _gcat[g] = _time.perf_counter()
            return
        took = _time.perf_counter() - _gcat.pop(g, _time.perf_counter())
        if took >= 0.2:
            try:
                # (no count of what is tracked: gc.get_objects() of a paged-out process was
                # itself 6.5 s of a stopped window, 16.11.)
                w._stalls.write("  gc: generation %s took %.2f s (%s collected, %s frozen) in thread %s\n"
                                % (g, took, info.get("collected"), _gc.get_freeze_count(),
                                   _th.current_thread().name))
                w._stalls.flush()
            except Exception:
                pass
    _gc.callbacks.append(_gcsaid)


def main():
    # 0.2.4: Build runs in a thread of this process; the window gets its turn every millisecond
    # instead of every five, so it keeps answering while a big world builds (exe test 15.10.)
    sys.setswitchinterval(0.001)
    # 0.3.1: and a big world's files are read in pieces off the window's thread (gentlejson: json.loads
    # keeps Python's lock for the whole text, 2-3 s of a window standing still with 255 MB)
    from modstudio import gentlejson
    gentlejson.install()
    # B480: ... and bigjson's readers in worker threads rest between their steps, so the window's
    # calls into Qt do not wait a switch interval each behind them
    bigjson.GENTLE = True
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
    theme.apply(app, load_settings())
    # one Mod Studio at a time: the program takes a few seconds to unpack itself, a second
    # click in that time started a second one, and the two wrote over each other's settings
    lock = None
    if "--shot" not in sys.argv and "--selfcheck" not in sys.argv:
        from PySide6.QtCore import QLockFile
        os.makedirs(APPDIR, exist_ok=True)
        lock = QLockFile(os.path.join(APPDIR, "running.lock"))
        # --elevated: started by Restart as administrator (access.restart_as_admin) while the
        # one that started it closes
        if not lock.tryLock(30000 if "--elevated" in sys.argv else 200):
            i18n.set_language(load_settings().get("lang", "en"))
            QMessageBox.information(None, "FL Mod Studio",
                                    _("FL Mod Studio is already open. Look for its window on the taskbar."))
            return
    # 0.2.3: a crash that takes the program down writes where it was to crash.log (people send it)
    try:
        import faulthandler
        os.makedirs(APPDIR, exist_ok=True)
        faulthandler.enable(open(os.path.join(APPDIR, "crash.log"), "w", encoding="utf-8"))
    except Exception:
        pass
    sys.excepthook = denied_hook(sys.excepthook)
    # 0.3.1: the name and "by Matozanato" while the window builds itself (mato 06.11.), drawn by a
    # process of its own so the building does not stop it, then grown into the window (10.11.)
    from modstudio import splash
    sp = splash.Start(app) if splash.wanted() else None
    w = Main()
    theme.dark_title_bar(w)
    # B480 round 3: what Windows put out of Mod Studio's memory while the PC was short of it comes
    # back in a thread of its own, not page by page under Python's lock on the window's thread
    try:
        from modstudio import procstat
        procstat.keep_in()
    except Exception:
        pass
    if os.environ.get("FL26_STALLS"):
        try:
            record_stalls(w, os.environ["FL26_STALLS"])
        except Exception:
            pass
    if os.environ.get("FL26_SHOT_SIZE"):          # --shot at a given window size ("1280x720")
        w.resize(*(int(x) for x in os.environ["FL26_SHOT_SIZE"].split("x")))
    late = 0
    if sp:
        late = splash.RUN_MS + splash.GROW_MS     # the tour and the questions wait for the window
        sp.finish(w)
    else:
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
    elif "--selfcheck" in sys.argv:              # the window walks itself and writes what it saw
        from modstudio import selfcheck
        w._selfcheck = selfcheck.begin(app, w, sys.argv[sys.argv.index("--selfcheck") + 1])
    else:
        # 0.2.4: the first start of a version with a new look shows where things are now
        # (FL26_NO_TOUR=1: the exe tests that click through the window)
        from modstudio import tour
        if tour.due(w.settings) and not os.environ.get("FL26_NO_TOUR"):
            QTimer.singleShot(late + 1500, w.start_tour)
        if not os.environ.get("FL26_NO_TOUR"):
            QTimer.singleShot(late + 2500, w.ask_support)
        if w.settings.get("check_updates", True):
            QTimer.singleShot(late + 3000, lambda: w.check_updates(quiet=True))
    code = app.exec()
    # B480: with a big world open Python took 30 s and more to end after the window closed, the
    # window "not responding" all that time (15.11.2026, the GigaPack: 2 GB given back piece by
    # piece). Everything is saved by now (closeEvent), so the process ends at once
    if os.environ.get("FL26_SLOW_EXIT"):
        sys.exit(code)
    try:
        w.hide()
        if getattr(w, "_stalls", None):
            w._stalls.close()
        sys.stdout.flush()
        sys.stderr.flush()
    except Exception:
        pass
    os._exit(int(code or 0))


if __name__ == "__main__":
    main()
