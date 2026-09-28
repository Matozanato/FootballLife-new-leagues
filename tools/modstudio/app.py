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
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QButtonGroup, QDialog, QHBoxLayout, QLabel, QMainWindow,
                               QMenu, QPushButton, QScrollArea, QStackedWidget, QStatusBar, QTextBrowser,
                               QToolButton, QVBoxLayout, QWidget, QMessageBox)

from modstudio import VERSION, theme, i18n
from modstudio.i18n import _
from modstudio.game import Game, guess_folders
from modstudio.siderini import SiderIni

APPDIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "FL26ModStudio")
SETTINGS = os.path.join(APPDIR, "settings.json")


def load_settings():
    try:
        with open(SETTINGS, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_settings(d):
    try:
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
    """(caption, [page classes]) in the order of the left bar"""
    from modstudio.pages import overview, roots, modules, install, profiles, restore
    from modstudio.pages import content, stadiums, balls, kits, commentary, music
    from modstudio.pages import builder, players, packages, diagnostics, settings
    return [
        ("MANAGE", [overview.Overview, install.Install, roots.Roots, modules.Modules,
                    profiles.Profiles, restore.Restore]),
        ("GAME CONTENT", [stadiums.Stadiums, kits.Kits, balls.Balls, commentary.Commentary,
                          music.Music, content.Servers]),
        ("LEAGUE BUILDER", [builder.NewLeagues, builder.NewClubs, builder.GameLeagues,
                            players.Players, packages.Packages, builder.Build]),
        ("TOOLS", [diagnostics.Diagnostics, settings.Settings]),
    ]


class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        i18n.set_language(self.settings.get("lang", "en"))
        self.bus = Bus()
        folder = self.settings.get("game") or next(iter(guess_folders()), "")
        self.game = Game(folder)
        from modstudio.project import Project
        self.project = Project(self)
        self.project.load_tables()
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
        sb.addPermanentWidget(QLabel("v" + VERSION))
        self.setStatusBar(sb)
        self._blink = QTimer(self, interval=550, timeout=self._blink_step)
        self._busy = 0

        self.pages = {}
        first = None
        for caption, classes in page_groups():
            for cls in classes:
                p = cls(self)
                self.pages[cls.__name__] = p
                self.stack.addWidget(p)
                first = first or cls.__name__
        self.bus.game_changed.connect(self.update_header)
        self.bus.ini_changed.connect(self.update_header)
        self.update_header()
        self._run_timer = QTimer(self, interval=4000, timeout=self.update_running)
        self._run_timer.start()
        self.update_running()
        self.open_page(self.settings.get("page") if self.settings.get("page") in self.pages else first)

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
            ("New recipe", lambda: self.page("NewLeagues").new_recipe()),
            ("Open recipe...", lambda: self.page("NewLeagues").open_recipe()),
            ("Save recipe", lambda: self.page("NewLeagues").save_recipe()),
            ("Save recipe as...", lambda: self.page("NewLeagues").save_recipe(True)),
            None,
            ("Add a league package...", lambda: (self.open_page("Packages"), self.page("Packages").add_pack())),
            ("Make a league package...", lambda: (self.open_page("Packages"), self.page("Packages").make_pack())),
            None, ("Exit", self.close)]))
        h.addWidget(self._menu_button("Game", [
            ("Choose the game folder...", lambda: self.page("Settings").pick_game()),
            ("Open the game folder", lambda: self._open(self.game.folder)),
            ("Open SiderAddons", lambda: self._open(self.game.sider_dir)),
            ("Open sider.ini", lambda: self._open(self.game.ini_path)),
            ("Open sider.log", lambda: self._open(self.game.log_path)),
            None,
            ("Start the game", self.play),
            ("Start the game without mods (safe mode)...", lambda: self.page("Profiles").safe_mode())]))
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
        outer = QScrollArea()
        outer.setWidgetResizable(True)
        outer.setFixedWidth(232)
        outer.setFrameShape(QScrollArea.NoFrame)
        w = QWidget()
        w.setObjectName("nav")
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 8)
        v.setSpacing(0)
        self.nav_group = QButtonGroup(self)
        self.nav_buttons = {}
        for caption, classes in page_groups():
            c = QLabel(_(caption))
            c.setObjectName("navcaption")
            v.addWidget(c)
            for cls in classes:
                b = QPushButton(_(cls.title))
                b.setObjectName("navitem")
                b.setCheckable(True)
                b.clicked.connect(lambda _c=False, n=cls.__name__: self.open_page(n))
                self.nav_group.addButton(b)
                self.nav_buttons[cls.__name__] = b
                v.addWidget(b)
        v.addStretch(1)
        outer.setWidget(w)
        return outer

    # ---- pages ----
    def page(self, name):
        return self.pages[name]

    def open_page(self, name):
        p = self.pages[name]
        self.stack.setCurrentWidget(p)
        self.nav_buttons[name].setChecked(True)
        self.settings["page"] = name
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
        self.settings["game"] = self.game.folder
        save_settings(self.settings)
        self.bus.game_changed.emit()

    def status(self, text):
        self.status_left.setText(text)

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
        self.h_profile.setText((_("Profile: %s") % prof) if prof else "")

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
        save_settings(self.settings)
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

    def set_auto_updates(self, on):
        """Help > Check for updates at start: off = only when asked (the menu item above it)"""
        self.settings["check_updates"] = bool(on)
        save_settings(self.settings)

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
        self.settings["size"] = [self.width(), self.height()]
        save_settings(self.settings)
        super().closeEvent(e)


def main():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FL26.ModStudio")
        except Exception:
            pass
    app = QApplication(sys.argv)
    theme.apply(app)
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
