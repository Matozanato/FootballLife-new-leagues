"""Settings: the game folder, the language, the game's tables for the League Builder"""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QFileDialog, QFormLayout, QLabel, QLineEdit, QPlainTextEdit,
                               QPushButton, QWidget)

from .. import i18n
from ..game import Game, guess_folders
from ..i18n import _
from ..ui import Page, section, hint, row, ask, error, info, run_job


class Settings(Page):
    title = "Settings"
    hint = "Where the game is, which language the program speaks, and the game's tables the League Builder reads."

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
        self.lang = QComboBox()
        for code, name in i18n.LANGUAGES:
            self.lang.addItem(name, code)
        self.lang.currentIndexChanged.connect(self.set_lang)
        form.addRow(_("Language"), row(self.lang))
        form.addRow(section("League Builder"), QLabel(""))
        form.addRow("", hint(_("The League Builder reads the game's own tables (clubs, leagues, players). "
                               "Unpack them once from your game; do it again after a game update.")))
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
        probs = g.problems()
        if probs:
            self.game_state.setText("• " + "\n• ".join(_(p) for p in probs))
            self.game_state.setObjectName("banner_warn")
        else:
            self.game_state.setText(_("Found: %s, Sider, sider.ini.") % os.path.basename(g.exe))
            self.game_state.setObjectName("banner_ok")
        self.game_state.style().unpolish(self.game_state)
        self.game_state.style().polish(self.game_state)
        self.lang.blockSignals(True)
        self.lang.setCurrentIndex(max(0, self.lang.findData(self.app.settings.get("lang", "en"))))
        self.lang.blockSignals(False)
        p = getattr(self.app, "project", None)
        if p is not None and p.base:
            n = len(p.game_cl)
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

    def set_lang(self):
        code = self.lang.currentData()
        if code and code != self.app.settings.get("lang", "en"):
            self.app.set_language(code)

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
            self.app.settings.pop("tables", None)
            p.load_tables()
            self.refresh()
            self.log.appendPlainText(_("Done."))

        def failed(tb):
            self.app.busy(False)
            self.unpack_btn.setEnabled(True)
            self.log.appendPlainText(tb)
        run_job(job, done, failed, progress=lambda t: self.log.appendPlainText(i18n.tr(str(t))))

    def pick_tables(self):
        d = QFileDialog.getExistingDirectory(self, _("A folder with Team.bin, Competition.bin ..."))
        if not d:
            return
        p = self.app.project
        self.app.settings["tables"] = d
        if not p.load_tables(d):
            self.app.settings.pop("tables", None)
            error(self, "Settings", _("No game tables in that folder."))
            p.load_tables()
        self.refresh()
