"""Profiles: save the current setup under a name, switch between setups, safe mode"""
import json, os, shutil

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QFileDialog, QInputDialog, QLabel, QPlainTextEdit, QSplitter,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from .. import profiles as PR
from ..i18n import _
from ..ui import Page, section, hint, ask, error, info


def when(stamp):
    s = stamp or ""
    return "%s.%s.%s %s:%s" % (s[6:8], s[4:6], s[0:4], s[9:11], s[11:13]) if len(s) >= 13 else s


class Profiles(Page):
    title = "Profiles"
    hint = ("A profile remembers which content folders and modules are switched on, and in what order. "
            "Save one for each way you play (a full patch, a league test, no extras) and switch in one "
            "click. \"As found\" is the setup the program found the first time; safe mode goes back to it.")

    def __init__(self, app):
        super().__init__(app)
        self.action("Save current setup...", self.save_new, "primary")
        self.action("Switch to it", self.switch)
        self.action("Update with current setup", self.update)
        self.action("Delete", self.delete, "danger")
        split = QSplitter(Qt.Horizontal)
        self.tree = QTreeWidget()
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setHeaderLabels([_("Profile"), _("Saved"), _("Folders on"), _("Modules on"),
                                   _("If you switch")])
        for c, w in enumerate((220, 130, 90, 90)):
            self.tree.setColumnWidth(c, w)
        self.tree.itemDoubleClicked.connect(lambda *a: self.switch())
        self.tree.currentItemChanged.connect(lambda *a: self.inspect())
        split.addWidget(self.tree)
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(10, 0, 0, 0)
        rv.addWidget(section("What it switches on"))
        self.detail = QPlainTextEdit()
        self.detail.setObjectName("log")
        self.detail.setReadOnly(True)
        rv.addWidget(self.detail, 1)
        from ..ui import row
        from PySide6.QtWidgets import QPushButton
        b1 = QPushButton(_("Export..."))
        b1.clicked.connect(self.export)
        b2 = QPushButton(_("Import..."))
        b2.clicked.connect(self.import_)
        rv.addWidget(row(b1, b2))
        rv.addWidget(hint(_("Export a profile to share your setup with someone who has the same mods.")))
        split.addWidget(right)
        split.setSizes([760, 420])
        self.outer.addWidget(split, 1)
        app.bus.ini_changed.connect(self.refresh)
        app.bus.game_changed.connect(self.refresh)

    def sd(self):
        return self.app.game.sider_dir

    def refresh(self):
        ini = self.app.ini()
        if ini is None:
            self.tree.clear()
            self.say(_("No sider.ini: choose the game folder first."), "warn")
            return
        self.say("")
        PR.ensure_first(self.sd(), ini)
        cur = self.tree.currentItem()
        cur = cur.text(0) if cur else None
        self.tree.clear()
        active = self.app.settings.get("profile")
        for p in PR.listing(self.sd()):
            on_r = sum(1 for v, en in p.get("cpk.root", []) if en)
            on_m = sum(1 for v, en in p.get("lua.module", []) if en)
            a, b, c = PR.differences(ini, p)
            diff = _("nothing changes") if not (a or b or c) else \
                _("%d on, %d off, %d back") % (a, b, c)
            it = QTreeWidgetItem([p["name"] + ("   ●" if p["name"] == active else ""), when(p.get("saved")),
                                  str(on_r), str(on_m), diff])
            it.setData(0, Qt.UserRole, p)
            it.setToolTip(0, p.get("note", ""))
            self.tree.addTopLevelItem(it)
            if p["name"] == cur:
                self.tree.setCurrentItem(it)

    def current(self):
        it = self.tree.currentItem()
        return it.data(0, Qt.UserRole) if it else None

    def inspect(self):
        p = self.current()
        if not p:
            self.detail.clear()
            return
        lines = [p.get("note", "")] if p.get("note") else []
        for k, head in (("cpk.root", _("Content folders")), ("lua.module", _("Lua modules"))):
            lines.append("")
            lines.append(head.upper())
            for v, en in p.get(k, []):
                lines.append(("  ✓ " if en else "    ") + v)
        self.detail.setPlainText("\n".join(lines).strip())

    def save_new(self):
        ini = self.app.ini()
        if ini is None:
            return
        name, ok = QInputDialog.getText(self, _("Save current setup..."), _("Name of the profile:"))
        if not ok or not name.strip():
            return
        name = name.strip()
        if any(p["name"].lower() == name.lower() for p in PR.listing(self.sd())) and \
                not ask(self, "Profiles", _("There is a profile called %s. Replace it?") % name):
            return
        PR.save(self.sd(), PR.capture(ini, name))
        self.app.settings["profile"] = name
        self.app.update_header()
        self.refresh()

    def update(self):
        p, ini = self.current(), self.app.ini()
        if p and ini and ask(self, "Profiles", _("Replace %s with the setup as it is now?") % p["name"]):
            q = PR.capture(ini, p["name"], p.get("note", ""))
            PR.save(self.sd(), q)
            self.refresh()

    def switch(self, prof=None):
        p = prof or self.current()
        ini = self.app.ini()
        if not p or ini is None:
            return
        g, s = self.app.game.running()
        if g and not ask(self, "Profiles", _("The game is running. The change takes effect at the next start. "
                                             "Switch anyway?")):
            return
        notes = PR.apply(ini, p, self.sd(), self.app.game.modules_dir)
        self.app.save_ini(ini, "profile %s" % p["name"])
        self.app.settings["profile"] = p["name"]
        self.app.update_header()
        self.refresh()
        if notes:
            info(self, "Profiles", _("Switched to %s, but:") % p["name"] + "\n\n" + "\n".join(notes[:20]))
        else:
            self.say(_("Switched to %s.") % p["name"], "ok")

    def safe_mode(self):
        first = next((p for p in PR.listing(self.sd()) if p["name"] == PR.FIRST), None)
        if not first:
            error(self, "Profiles", _("There is no \"As found\" profile for this game."))
            return
        if ask(self, "Safe mode", _("Go back to the setup the program found the first time (\"As found\")? "
                                    "Save the current setup as a profile first if you want to come back to it.")):
            self.switch(first)

    def delete(self):
        p = self.current()
        if not p:
            return
        if p["name"] == PR.FIRST:
            error(self, "Profiles", _("\"As found\" is kept: it is the way back to the game as it was."))
            return
        if ask(self, "Delete", _("Delete the profile %s? The mods themselves stay.") % p["name"]):
            PR.delete(p)
            self.refresh()

    def export(self):
        p = self.current()
        if not p:
            return
        dst, _f = QFileDialog.getSaveFileName(self, _("Export..."), PR.safe_name(p["name"]) + ".fl26profile.json",
                                              "JSON (*.json)")
        if dst:
            q = {k: v for k, v in p.items() if not k.startswith("_")}
            with open(dst, "w", encoding="utf-8") as f:
                json.dump(q, f, indent=1, ensure_ascii=False)

    def import_(self):
        src, _f = QFileDialog.getOpenFileName(self, _("Import..."), "", "JSON (*.json)")
        if not src:
            return
        try:
            with open(src, encoding="utf-8") as f:
                p = json.load(f)
            assert isinstance(p.get("name"), str) and any(k in p for k in PR.KEYS)
        except (OSError, ValueError, AssertionError):
            error(self, "Import...", _("That is not a profile file."))
            return
        if p["name"] == PR.FIRST:
            p["name"] = PR.FIRST + " (imported)"
        PR.save(self.sd(), p)
        self.refresh()
