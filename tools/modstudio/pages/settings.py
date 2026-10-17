"""Settings: the game folder, the language, the game's tables for the League Builder"""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFormLayout, QLabel, QLineEdit, QPlainTextEdit,
                               QPushButton, QWidget)

from .. import i18n
import siderdir

from ..game import Game, guess_folders
from ..i18n import _
from ..ui import Page, section, hint, row, ask, error, info, run_job, can_write, denied


class Settings(Page):
    title = "Settings"
    hint = "Where the game is, which language the program speaks, and the game's tables Mod Studio reads."

    def __init__(self, app):
        super().__init__(app)
        w = QWidget()
        form = QFormLayout(w)
        form.setLabelAlignment(Qt.AlignRight)
        self.folder = QComboBox()
        self.folder.setEditable(True)
        self.folder.setMinimumWidth(520)
        b = QPushButton(_("Browse..."))
        b.clicked.connect(self.pick_game)
        use = QPushButton(_("Use this folder"))
        use.setObjectName("primary")
        use.clicked.connect(lambda: self.set_game(self.folder.currentText()))
        form.addRow(_("Game folder"), row(self.folder, b, use, stretch=False))
        self.game_state = QLabel("")
        self.game_state.setWordWrap(True)
        form.addRow("", self.game_state)
        self.sider = QComboBox()
        self.sider.setMinimumWidth(260)
        self.sider.activated.connect(self.set_sider)
        self.sider_note = hint(_("More than one folder here holds a sider.ini. Mod Studio installs mods, "
                                 "builds worlds and reads sider.log in the one chosen here."))
        form.addRow(_("Sider folder"), row(self.sider))
        form.addRow("", self.sider_note)
        self.lang = QComboBox()
        for code, name in i18n.LANGUAGES:
            self.lang.addItem(name, code)
        self.lang.currentIndexChanged.connect(self.set_lang)
        form.addRow(_("Language"), row(self.lang))
        # 0.2.4 (mato 15.10.): the save folder goes with the world in the game (saves.py)
        form.addRow(section("Master League careers"), QLabel(""))
        self.per_world = QCheckBox(_("Each world keeps its own careers (the save folder is switched with the world)"))
        self.per_world.toggled.connect(self.set_per_world)
        form.addRow("", self.per_world)
        from .. import saves
        form.addRow("", hint(_("A career is made for one world: in another world its leagues and clubs are not "
                               "there. When this is on and you switch the world in the game, Mod Studio renames "
                               "the game's save folder: the careers of the world going out are kept in "
                               "save_<world>, and those of the world coming in come back. Your game settings go "
                               "with you. Nothing is deleted. Folder: %s") % saves.root()))
        form.addRow(section("The game's tables"), QLabel(""))
        form.addRow("", hint(_("Mod Studio needs the game's tables (its list of clubs, leagues and players) once "
                               "on every PC: it unpacks them by itself the first time. After a game update click Unpack the game's "
                               "tables again. To build "
                               "on a database of your own (a pesdb folder in livecpk), unpack the game's tables "
                               "first, then pick that folder with Use another tables folder: its files go over the "
                               "game's, which give whatever it does not have.")))
        self.tables = QLabel("")
        self.tables.setWordWrap(True)
        self.unpack_btn = QPushButton(_("Unpack the game's tables"))
        self.unpack_btn.setObjectName("primary")
        self.unpack_btn.clicked.connect(self.unpack)
        other = QPushButton(_("Use another tables folder..."))
        other.clicked.connect(self.pick_tables)
        form.addRow(_("Tables"), self.tables)
        form.addRow("", row(self.unpack_btn, other))
        self.log = QPlainTextEdit()
        self.log.setObjectName("log")
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(160)
        self.log.hide()
        form.addRow("", self.log)
        form.addRow(section("Program"), QLabel(""))
        from ..app import APPDIR
        op = QPushButton(_("Open the program's settings folder"))
        op.clicked.connect(lambda: os.startfile(APPDIR) if os.path.isdir(APPDIR) else None)
        form.addRow("", row(op))
        self.outer.addWidget(w)
        self.outer.addStretch(1)

    def refresh(self):
        g = self.app.game
        self.folder.blockSignals(True)
        self.folder.clear()
        seen = []
        for f in ([g.folder] if g.folder else []) + guess_folders():
            if f.lower() not in [s.lower() for s in seen]:
                seen.append(f)
                self.folder.addItem(f)
        self.folder.setCurrentText(g.folder)
        self.folder.blockSignals(False)
        names = siderdir.candidates(g.folder) if g.folder else []
        self.sider.blockSignals(True)
        self.sider.clear()
        for n in names:
            self.sider.addItem(n, n)
        if not names:
            self.sider.addItem(_("(none found)"), "")
        self.sider.setCurrentIndex(max(0, self.sider.findData(siderdir.name(g.folder, g.sider_dir))))
        self.sider.setEnabled(len(names) > 1)
        self.sider.blockSignals(False)
        self.sider_note.setVisible(len(names) > 1)
        probs = g.problems()
        if probs:
            self.game_state.setText("• " + "\n• ".join(_(p) for p in probs))
            self.game_state.setObjectName("banner_warn")
        else:
            self.game_state.setText(_("Found: %s, Sider in %s, sider.ini.")
                                    % (os.path.basename(g.exe), siderdir.name(g.folder, g.sider_dir)))
            self.game_state.setObjectName("banner_ok")
        self.game_state.style().unpolish(self.game_state)
        self.game_state.style().polish(self.game_state)
        self.lang.blockSignals(True)
        self.lang.setCurrentIndex(max(0, self.lang.findData(self.app.settings.get("lang", "en"))))
        self.lang.blockSignals(False)
        from .. import saves
        self.per_world.blockSignals(True)
        self.per_world.setChecked(saves.enabled(self.app.settings))
        self.per_world.blockSignals(False)
        p = getattr(self.app, "project", None)
        if p is not None and p.base:
            n = len(p.game_cl)
            if p.overlay:
                self.tables.setText(_("%s  (%d clubs, %d leagues; %d files from it, the rest from the game's "
                                      "tables)") % (self.app.settings.get("tables", ""), n, len(p.game_lgs), p.overlay))
            else:
                self.tables.setText(_("%s  (%d clubs, %d leagues)") % (p.base, n, len(p.game_lgs)))
        else:
            self.tables.setText(_("Not unpacked yet."))

    def pick_game(self):
        d = QFileDialog.getExistingDirectory(self, _("Choose the game folder (the one with FL_2026.exe)"),
                                             self.app.game.folder)
        if d:
            self.set_game(d)

    def set_game(self, d):
        d = d.strip()
        if not Game(d).ok() and not ask(self, "Game folder", _("There is no FL_2026.exe in %s. Use it anyway?") % d):
            return
        self.app.set_game(d)
        self.refresh()
        if self.app.game.ok():
            can_write(self, self.app.game)      # a game under Program Files: say so now (B14)

    def set_sider(self):
        name = self.sider.currentData()
        if name and name != siderdir.name(self.app.game.folder, self.app.game.sider_dir):
            self.app.set_sider(name)
        self.refresh()

    def set_lang(self):
        code = self.lang.currentData()
        if code and code != self.app.settings.get("lang", "en"):
            self.app.set_language(code)

    def set_per_world(self, on):
        from .. import saves
        self.app.settings[saves.SETTING] = bool(on)
        if on:
            # from now on save holds the careers of the world in the game, whatever it held while
            # this was off
            saves.forget_owner()
        self.app.save_settings()

    def unpack(self):
        p = getattr(self.app, "project", None)
        if p is None or not self.app.game.ok():
            error(self, "Settings", _("Choose the game folder first."))
            return
        self.unpack_btn.setEnabled(False)
        self.log.clear()
        self.log.show()
        self.app.busy(True, _("Unpacking the game's tables"))

        def job(progress):
            return p.unpack(log=lambda t: progress(t))

        def done(r):
            self.app.busy(False)
            self.unpack_btn.setEnabled(True)
            if not p.overlay:          # a database of your own stays on top of the new tables
                self.app.settings.pop("tables", None)
            p.load_tables()
            self.refresh()
            self.log.appendPlainText(_("Done."))

        def failed(tb):
            self.app.busy(False)
            self.unpack_btn.setEnabled(True)
            if denied(self, tb):
                self.log.appendPlainText(tb.strip().splitlines()[-1])
                return
            self.log.appendPlainText(tb)
        run_job(job, done, failed, progress=lambda t: self.log.appendPlainText(i18n.tr(str(t))))

    def pick_tables(self):
        d = QFileDialog.getExistingDirectory(self, _("A pesdb folder: Team.bin, Player.bin ..."))
        if not d:
            return
        p = self.app.project
        self.app.settings["tables"] = d
        if not p.load_tables(d):
            why = p.tables_error
            self.app.settings.pop("tables", None)
            p.load_tables()
            if "unpack" in why:
                error(self, "Settings", _("That folder has only part of the tables, as a database in livecpk "
                                          "usually does. Click Unpack the game's tables first, then pick the "
                                          "folder again: its files go over the game's tables."))
            elif "no tables" in why:
                error(self, "Settings", _("No tables in that folder: pick the pesdb folder with Team.bin, "
                                          "Player.bin ..."))
            elif "not a game table" in why:
                # B117 (jibibi 17.10.): his Team.bin and Player.bin were there, changed by his own tool,
                # and the box said there were no tables at all
                error(self, "Settings", _("The tables in that folder cannot be read: one of the .bin files is "
                                          "not in the game's own format (changed by another tool?). Use the "
                                          "game's tables or a patch's original pesdb folder."))
            else:
                error(self, "Settings", _("The tables in that folder cannot be read: %s") % why)
        elif p.overlay:
            info(self, "Settings", _("Tables loaded: %d clubs, %d leagues. %d files come from your folder, "
                                     "the rest from the game's tables.") % (len(p.game_cl), len(p.game_lgs), p.overlay))
        else:
            info(self, "Settings", _("Tables loaded: %d clubs, %d leagues.") % (len(p.game_cl), len(p.game_lgs)))
        self.refresh()
