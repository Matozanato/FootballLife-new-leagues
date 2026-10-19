"""Restore points: every file the program changed, as it was before each change"""
import difflib, os, re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QFrame, QLabel, QPlainTextEdit, QPushButton, QSplitter, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget)

from .. import backups, factory, saves as SV, worlds as WL
from ..i18n import _
from ..roots import human
from ..ui import Page, section, hint, row, ask, error, info, run_job, can_write, denied

ROW = Qt.UserRole
WORLDS = "<worlds>"           # the "only" choice that lists the world backups (Content folders > Delete / Rename world)
TEXT_EXT = (".ini", ".txt", ".csv", ".lua", ".json", ".cfg")


# world backups that keep a world where it is (worlds.backup)
def copy_what(kind):
    """what the row of such a backup says, or None for another kind"""
    if kind == "edited":
        return _("the world from a zip before it was made editable")
    if kind == "built":
        return _("the world before a Build")
    if kind == "updated":
        return _("the world before a newer zip or Remove the mod took it out")
    return None


def _reasons():
    """the reasons a restore point is kept with (backups.snapshot), English as the index keeps them,
    and as this language says them: B134 (UI test in French, 18.10.) found them all in English"""
    return [
        ("Switch on: kits map", _("Switch on: kits map")),
        ("Switch on: scoreboards map", _("Switch on: scoreboards map")),
        ("Switch on: menus map", _("Switch on: menus map")),
        ("Switch on: home stadiums map", _("Switch on: home stadiums map")),
        ("Switch on: %s map", _("Switch on: %s map")),
        ("Switch on %s: the world file", _("Switch on %s: the world file")),
        ("Switch on %s: its own module", _("Switch on %s: its own module")),
        ("Switch on %s: its leagues in the Kick Off list", _("Switch on %s: its leagues in the Kick Off list")),
        ("Your world: switch on %s", _("Your world: switch on %s")),
        ("Import your world: switch on %s", _("Import your world: switch on %s")),
        ("Build and install %s", _("Build and install %s")),
        ("Mod Studio's modules switched on", _("Mod Studio's modules switched on")),
        ("Install the modules", _("Install the modules")),
        ("Install the modules: replaced by Mod Studio's", _("Install the modules: replaced by Mod Studio's")),
        ("Install the modules: %s now ships bundled", _("Install the modules: %s now ships bundled")),
        ("Install the modules: livecpk\\%s loaded", _("Install the modules: livecpk\\%s loaded")),
        ("world %s renamed to %s", _("world %s renamed to %s")),
        ("world %s deleted: its lines taken out", _("world %s deleted: its lines taken out")),
        ("world %s deleted", _("world %s deleted")),
        ("world %s put back", _("world %s put back")),
        ("before restoring %s", _("before restoring %s")),
        ("deleted content folder %s", _("deleted content folder %s")),
        ("content folders changed", _("content folders changed")),
        ("modules changed", _("modules changed")),
        ("settings changed", _("settings changed")),
        ("map edited", _("map edited")),
        ("soundtrack counts", _("soundtrack counts")),
        ("replaced by %s", _("replaced by %s")),
        ("merge from %s", _("merge from %s")),
        ("installed %s", _("installed %s")),
        ("removing %s", _("removing %s")),
        ("removed %s", _("removed %s")),
        ("profile %s", _("profile %s")),
    ]


def reason_text(reason):
    """a restore point's reason in the language of the window (an unknown one as it is)"""
    for en, said in _reasons():
        if "%s" not in en:
            if reason == en:
                return said
            continue
        m = re.fullmatch("(.+?)".join(re.escape(t) for t in en.split("%s")), reason or "", re.S)
        if m:
            try:
                return said % m.groups()
            except (TypeError, ValueError):
                return reason
    return reason or ""


def when(t):
    return "%s.%s.%s %s:%s:%s" % (t[6:8], t[4:6], t[0:4], t[9:11], t[11:13], t[13:15]) if len(t) >= 15 else t


class Restore(Page):
    title = "Restore points"
    hint = ("Before the program changes a file (sider.ini, a map, a module) it keeps a copy here. "
            "Pick one to see what changed since, and put it back if you want the old one.")

    def __init__(self, app):
        super().__init__(app)
        self.only = QComboBox()
        self.only.addItem(_("All files"), None)
        self.only.currentIndexChanged.connect(lambda *_a: self.fill())
        self.actions.insertWidget(1, self.only)
        self.action("Put this copy back", self.restore, "primary")
        self.action("Clean up...", self.clean)
        self.action("Delete this copy for good...", self.discard, "danger")
        # 0.2.4: all of Sider back as it was before Mod Studio, in one go, and that undone again
        card = QFrame()
        card.setObjectName("card")
        cv = QVBoxLayout(card)
        t = QLabel(_("Sider as it was before Mod Studio"))
        t.setObjectName("cardvalue")
        cv.addWidget(t)
        cv.addWidget(hint(_("One click puts back every file Mod Studio changed and takes out what it brought in "
                            "(its modules, the face pack, the worlds, the mods installed here). Nothing is "
                            "deleted: it is all kept, and Undo puts it back. Your saves are not touched.")))
        self.b_reset = QPushButton(_("Put Sider back as before Mod Studio..."))
        self.b_reset.setObjectName("danger")
        self.b_reset.clicked.connect(self.reset_sider)
        self.b_undo = QPushButton(_("Undo the last reset"))
        self.b_undo.clicked.connect(self.undo_reset)
        cv.addWidget(row(self.b_reset, self.b_undo, "stretch", stretch=False))
        self.outer.addWidget(card)
        split = QSplitter(Qt.Horizontal)
        self.tree = QTreeWidget()
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setHeaderLabels([_("When"), _("File"), _("Why"), _("Size")])
        for c, w in enumerate((150, 280, 260)):
            self.tree.setColumnWidth(c, w)
        self.tree.currentItemChanged.connect(lambda *_a: self.inspect())
        split.addWidget(self.tree)
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(10, 0, 0, 0)
        rv.addWidget(section("Changes since this copy"))
        self.diff = QPlainTextEdit()
        self.diff.setObjectName("log")
        self.diff.setReadOnly(True)
        self.diff.setLineWrapMode(QPlainTextEdit.NoWrap)
        rv.addWidget(self.diff, 1)
        rv.addWidget(hint(_("Lines starting with - are in the copy, + are in the file now.")))
        split.addWidget(right)
        split.setSizes([700, 520])
        self.outer.addWidget(split, 1)
        app.bus.ini_changed.connect(self.refresh)
        app.bus.content_changed.connect(self.refresh)
        app.bus.game_changed.connect(self.refresh)

    def sd(self):
        return self.app.game.sider_dir

    def refresh(self):
        ok = bool(self.app.game.ok()) and os.path.isdir(self.sd())
        self.b_reset.setEnabled(ok)
        self.b_undo.setVisible(ok and bool(factory.resets(self.sd())))
        if not os.path.isdir(self.sd()):
            self.tree.clear()
            return
        files = sorted({r["file"] for r in backups.load(self.sd())}, key=str.lower)
        cur = self.only.currentData()
        self.only.blockSignals(True)
        self.only.clear()
        self.only.addItem(_("All files"), None)
        if WL.backups_of(self.sd()):
            self.only.addItem(_("Worlds deleted or renamed"), WORLDS)
        for f in files:
            self.only.addItem(f, f)
        i = self.only.findData(cur)
        self.only.setCurrentIndex(max(0, i))
        self.only.blockSignals(False)
        self.fill()

    def fill(self):
        self.tree.clear()
        only = self.only.currentData()
        rows = [] if only == WORLDS else [(r["time"], r) for r in backups.history(self.sd(), only)]
        # a world deleted or renamed in Content folders is one row: Put this copy back brings all of
        # it back (mato 15.10.)
        if only in (None, WORLDS):
            for folder, inf in WL.backups_of(self.sd()):
                rows.append((inf.get("time", ""), {"world_backup": folder, "info": inf}))
            # the copy of the game's save folder taken before the first world switch (saves.py)
            for folder, inf in SV.backups_of(self.sd()):
                rows.append((inf.get("time", ""), {"saves_backup": folder, "info": inf}))
        for t, r in sorted(rows, key=lambda x: x[0], reverse=True):
            if "saves_backup" in r:
                it = QTreeWidgetItem([when(t), SV.ACTIVE + "  (" + _("Master League saves") + ")",
                                      _("the save folder before the first world switch"),
                                      human(WL.size_of(r["saves_backup"]))])
            elif "world_backup" in r:
                inf = r["info"]
                if inf.get("kind") == "renamed":
                    what = _("world renamed to %s") % inf.get("new", "")
                    size = ""
                elif copy_what(inf.get("kind")):
                    what = copy_what(inf["kind"])
                    size = human(WL.size_of(os.path.join(r["world_backup"], "files")))
                else:
                    what = _("world deleted (all of it is in this copy)")
                    size = human(WL.size_of(os.path.join(r["world_backup"], "files")))
                it = QTreeWidgetItem([when(t), "livecpk\\" + inf.get("world", ""), what, size])
                f = it.font(1)
                f.setBold(True)
                it.setFont(1, f)
            else:
                it = QTreeWidgetItem([when(r["time"]), r["file"], reason_text(r.get("reason", "")),
                                      human(r.get("size", 0))])
            it.setData(0, ROW, r)
            self.tree.addTopLevelItem(it)
        if self.tree.topLevelItemCount():
            self.tree.setCurrentItem(self.tree.topLevelItem(0))

    def current(self):
        it = self.tree.currentItem()
        return it.data(0, ROW) if it else None

    def inspect(self):
        r = self.current()
        if not r:
            self.diff.clear()
            return
        if "world_backup" in r:
            self.diff.setPlainText(self.world_text(r))
            return
        if "saves_backup" in r:
            self.diff.setPlainText(self.saves_text(r))
            return
        now = os.path.join(self.sd(), r["file"])
        old = os.path.join(self.sd(), r["copy"])
        if not r["file"].lower().endswith(TEXT_EXT):
            self.diff.setPlainText(_("(not a text file: %s now, %s in the copy)") % (
                human(os.path.getsize(now)) if os.path.exists(now) else _("gone"), human(os.path.getsize(old))))
            return
        try:
            a = open(old, encoding="utf-8", errors="replace").read().splitlines()
            b = open(now, encoding="utf-8", errors="replace").read().splitlines() if os.path.exists(now) else []
        except OSError as e:
            self.diff.setPlainText(str(e))
            return
        d = list(difflib.unified_diff(a, b, "copy", "now", n=2, lineterm=""))
        self.diff.setPlainText("\n".join(d[2:]) if d else _("The file is the same as this copy."))

    def world_text(self, r):
        inf = r["info"]
        if inf.get("kind") == "renamed":
            lines = [_("%s was renamed to %s.") % (inf["world"], inf.get("new", "")), "",
                     _("Put this copy back renames it back to %s, everywhere the name is written.") % inf["world"],
                     "", _("Files the rename changed:")] + ["  " + t for t in inf.get("texts", [])]
        elif copy_what(inf.get("kind")):
            lines = [_("A copy of all of %s: %s.") % (inf["world"], copy_what(inf["kind"])), ""]
            lines += ["  " + m for m in inf.get("copied", [])]
            lines += ["", _("Put this copy back makes the world what it was then. Its folders now are not "
                            "deleted: they go into this copy's folder (replaced)."), "", r["world_backup"]]
        else:
            lines = [_("%s was deleted. All of it is kept in this copy:") % inf["world"], ""]
            lines += ["  " + m for m in inf.get("moved", [])]
            lines += ["  " + _("%s: %d line(s)") % (t["file"], len(t.get("removed", []))) for t in inf.get("texts", [])]
            if inf.get("records"):
                lines.append("  " + _("its records of Import your world"))
            lines += ["", _("Put this copy back brings it back as it was (switched off if it was off)."), "",
                      r["world_backup"]]
        return "\n".join(lines)

    def saves_text(self, r):
        inf = r["info"]
        return "\n".join([
            _("Your Master League save folder as it was before the first world switch:"), "",
            "  " + os.path.join(r["saves_backup"], SV.ACTIVE), "",
            _("It was copied from %s. Mod Studio does not put it back by itself: close the game, then copy "
              "the files you want from this copy into the save folder.") % inf.get("from", "")])

    def restore_world(self, r):
        inf = r["info"]
        if self.app.game.running()[0] or self.app.game.running()[1]:
            error(self, "Restore points", _("Close the game first."))
            return
        if inf.get("kind") == "renamed":
            q = _("Rename %s back to %s?") % (inf.get("new", ""), inf["world"])
        else:
            q = _("Put the world %s back as it was on %s?") % (inf["world"], when(inf.get("time", "")))
        if not ask(self, "Restore points", q) or not can_write(self, self.app.game):
            return
        try:
            w = WL.restore(self.app.game, r["world_backup"])
        except WL.WorldError as e:
            error(self, "Restore points", str(e))
            return
        except OSError as e:
            if not denied(self, e):
                error(self, "Restore points", str(e))
            return
        if inf.get("kind") == "renamed":
            from .roots import rename_recipe
            rename_recipe(self.app, inf.get("new", ""), w)
            from .. import saves                       # its careers kept aside get the name back too
            if saves.enabled(self.app.settings):
                try:
                    saves.rename_saves(inf.get("new", ""), w)
                except (saves.SaveError, OSError) as e:
                    error(self, "Restore points", _("%s is back, but its Master League careers stay in %s:")
                          % (w, saves.name_of(inf.get("new", ""))) + "\n\n" + str(e))
        self.app.bus.ini_changed.emit()
        self.app.bus.content_changed.emit()
        self.say(_("%s is back.") % w, "ok")
        self.refresh()

    def restore(self):
        r = self.current()
        if not r:
            return
        if "world_backup" in r:
            self.restore_world(r)
            return
        if "saves_backup" in r:
            # careers are the player's: shown, never written over by Mod Studio
            info(self, "Restore points", self.saves_text(r))
            try:
                os.startfile(r["saves_backup"])
            except OSError:
                pass
            return
        g, s = self.app.game.running()
        if not ask(self, "Restore points", _("Put back %s as it was on %s? The file as it is now is kept as a "
                                             "restore point too.") % (r["file"], when(r["time"])) +
                   ("\n\n" + _("The game is running: restart it afterwards.") if g else "")):
            return
        try:
            backups.restore(self.sd(), r)
        except OSError as e:
            if not denied(self, e):                   # a game under Program Files (B43)
                error(self, "Restore points", str(e))
            return
        if r["file"].lower() == "sider.ini":
            self.app.bus.ini_changed.emit()
        else:
            self.app.bus.content_changed.emit()
        self.say(_("%s is back as it was on %s.") % (r["file"], when(r["time"])), "ok")
        self.refresh()

    def discard(self):
        """B131: a deleted (or copied) world's backup out for good, to free the disk"""
        r = self.current()
        if not r or "world_backup" not in r:
            info(self, "Restore points", _("Pick a deleted or copied world in the list: only those copies are "
                                           "deleted here (Clean up... is for the copies of files)."))
            return
        inf = r["info"]
        size = human(WL.size_of(r["world_backup"]))
        if not ask(self, "Restore points", _("Delete this copy of %s for good?\n\nIt frees %s on the disk and can "
                                             "not be put back any more.") % (inf.get("world", ""), size)):
            return
        try:
            WL.discard(self.sd(), r["world_backup"])
        except (WL.WorldError, OSError) as e:
            if not isinstance(e, OSError) or not denied(self, e):
                error(self, "Restore points", str(e))
            self.refresh()
            return
        self.say(_("The copy of %s is deleted: %s freed.") % (inf.get("world", ""), size), "ok")
        self.refresh()

    def clean(self):
        rows = backups.load(self.sd())
        files = {r["file"] for r in rows}
        if not rows or not ask(self, "Clean up...", _("Keep the newest 20 copies of each file and delete the "
                                                      "older ones (%d copies of %d files now)?") % (len(rows), len(files))):
            return
        n = sum(backups.keep(self.sd(), f, 20) for f in files)
        self.say(_("%d old copies deleted.") % n, "ok")
        self.refresh()

    # ---- Sider as before Mod Studio ----
    def reset_sider(self):
        game = self.app.game
        if not game.ok() or not os.path.isdir(self.sd()):
            return
        if game.running()[0]:
            error(self, "Restore points", _("Close the game first."))
            return
        try:
            p = factory.plan(game)
        except Exception as e:
            error(self, "Restore points", str(e))
            return
        if not p["back"] and not p["out"]:
            info(self, "Restore points", _("Sider is as it was before Mod Studio already: nothing to put back."))
            return
        what = [_("%d file(s) Mod Studio changed go back as they were (sider.ini among them)") % len(p["back"])
                if p["back"] else "",
                _("Worlds taken out: %s") % ", ".join(p["worlds"]) if p["worlds"] else "",
                _("Mods installed with Mod Studio taken out: %s") % ", ".join(p["mods"]) if p["mods"] else "",
                _("Mod Studio's modules and the face pack taken out")]
        if not ask(self, "Put Sider back as before Mod Studio",
                   _("Put Sider back as it was before Mod Studio?") + "\n\n" +
                   "\n".join("\u2022 " + w for w in what if w) + "\n\n" +
                   _("Nothing is deleted: all of it is kept in SiderAddons\\ModStudio, and Undo the last reset "
                     "puts it back. Your saves are not touched. A Master League started with the new leagues "
                     "will not load without them.")):
            return
        if not can_write(self, game):
            return
        self.app.busy(True, _("Putting Sider back as before Mod Studio"))

        def done(folder):
            self.app.busy(False)
            self.app.bus.ini_changed.emit()
            self.app.bus.content_changed.emit()
            self.app.bus.game_changed.emit()
            self.say(_("Sider is back as it was before Mod Studio. All of it is kept in %s.") % folder, "ok")
            self.refresh()

        def failed(tb):
            self.app.busy(False)
            if denied(self, tb):
                return
            error(self, "Restore points", _("It stopped:") + "\n\n" + tb.strip().splitlines()[-1] + "\n\n" +
                  _("What was done so far can be put back with Undo the last reset."))
            self.refresh()
        run_job(lambda progress: factory.reset(game), done, failed)

    def undo_reset(self):
        folders = factory.resets(self.sd())
        if not folders:
            return
        if self.app.game.running()[0]:
            error(self, "Restore points", _("Close the game first."))
            return
        if not ask(self, "Undo the last reset", _("Put Sider back as it was just before the last reset?")):
            return
        try:
            factory.undo(self.sd(), folders[0])
        except Exception as e:
            error(self, "Restore points", str(e))
            return
        self.app.bus.ini_changed.emit()
        self.app.bus.content_changed.emit()
        self.app.bus.game_changed.emit()
        self.say(_("Sider is back as it was before the reset."), "ok")
        self.refresh()
