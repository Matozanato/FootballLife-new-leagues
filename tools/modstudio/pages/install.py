"""Install: drop a mod (zip, 7z, folder, .lua, .cpk), see what is in it, install it; and the
list of mods installed with the program, each one removable"""
import os, shutil, tempfile

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (QComboBox, QFileDialog, QFrame, QLabel, QLineEdit, QPushButton,
                               QSplitter, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from .. import installer as I, theme
from ..i18n import _
from ..roots import human
from ..ui import Page, section, hint, row, ask, error, info, run_job

ROW = Qt.UserRole
KIND = {"root": "Content folder (livecpk)", "content": "Content server files", "module": "Lua module",
        "cpk": "Packed .cpk (unpacked on install)", "pack": "League package", "dll": "DLL (not installed)",
        "world": "League Builder world (switched on)"}
NO_FACES = ("Mod Studio's modules with the face pack are not installed: the new players of this world "
            "will all look the same until you install them (League Builder > Build > 0. Install the modules).")


class Drop(QFrame):
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.setObjectName("card")
        self.setAcceptDrops(True)
        self.setMinimumHeight(96)
        v = QVBoxLayout(self)
        t = QLabel(_("Drop a mod here"))
        t.setObjectName("cardvalue")
        t.setAlignment(Qt.AlignCenter)
        s = QLabel(_(".zip  ·  .7z  ·  a folder  ·  .lua  ·  .cpk  ·  .fl26pack"))
        s.setObjectName("cardlabel")
        s.setAlignment(Qt.AlignCenter)
        v.addWidget(t)
        v.addWidget(s)
        b1 = QPushButton(_("Choose a file..."))
        b1.clicked.connect(page.pick_file)
        b2 = QPushButton(_("Choose a folder..."))
        b2.clicked.connect(page.pick_folder)
        v.addWidget(row("stretch", b1, b2, "stretch", stretch=False))

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.toLocalFile()]
        if paths:
            self.page.look(paths[0])


class Install(Page):
    title = "Install mods"
    hint = ("Drop a downloaded mod here. The program looks inside, says what each part is and where "
            "it goes, and installs only what you tick. Map files of the content servers are merged "
            "into yours instead of replacing them. Every mod installed here can be removed again.")

    def __init__(self, app):
        super().__init__(app)
        self.work = None
        self.parts = []
        self.src = None
        split = QSplitter(Qt.Vertical)
        top = QWidget()
        tv = QVBoxLayout(top)
        tv.setContentsMargins(0, 0, 0, 0)
        tv.addWidget(Drop(self))
        self.what = QLabel("")
        self.what.setObjectName("title")
        tv.addWidget(self.what)
        self.tree = QTreeWidget()
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setHeaderLabels([_("Install"), _("What it is"), _("Name"), _("Files"), _("Size"), _("Note")])
        for c, w in enumerate((60, 230, 240, 60, 80)):
            self.tree.setColumnWidth(c, w)
        self.tree.itemDoubleClicked.connect(self.rename)
        tv.addWidget(self.tree, 1)
        self.name = QLineEdit()
        self.name.setPlaceholderText(_("name of the mod (it is listed under this name)"))
        self.where = QComboBox()
        self.where.addItem(_("New content folders go on top (they win)"), "top")
        self.where.addItem(_("New content folders go at the bottom"), "bottom")
        self.lines = QComboBox()
        self.lines.addItem(_("Map lines for a club already mapped: use the mod's"), True)
        self.lines.addItem(_("Map lines for a club already mapped: keep mine, add the mod's after"), False)
        self.go = QPushButton(_("Install"))
        self.go.setObjectName("primary")
        self.go.clicked.connect(self.install)
        self.go.setEnabled(False)
        tv.addWidget(row(QLabel(_("Name")), self.name, self.where, self.lines, "stretch", self.go, stretch=False))
        split.addWidget(top)
        bottom = QWidget()
        bv = QVBoxLayout(bottom)
        bv.setContentsMargins(0, 6, 0, 0)
        bv.addWidget(section("Installed with FL26 Mod Studio"))
        self.done = QTreeWidget()
        self.done.setRootIsDecorated(False)
        self.done.setAlternatingRowColors(True)
        self.done.setHeaderLabels([_("Mod"), _("Installed"), _("What it added")])
        self.done.setColumnWidth(0, 260)
        self.done.setColumnWidth(1, 140)
        bv.addWidget(self.done, 1)
        rm = QPushButton(_("Remove the mod"))
        rm.setObjectName("danger")
        rm.clicked.connect(self.uninstall)
        bv.addWidget(row(rm))
        split.addWidget(bottom)
        split.setSizes([520, 240])
        self.outer.addWidget(split, 1)
        app.bus.game_changed.connect(self.refresh)
        app.bus.content_changed.connect(self.refresh)

    # ---- choose ----
    def pick_file(self):
        p, _f = QFileDialog.getOpenFileName(self, _("Choose a file..."), "",
                                            _("Mods") + " (*.zip *.7z *.lua *.cpk *.fl26pack);;" + _("All files") + " (*)")
        if p:
            self.look(p)

    def pick_folder(self):
        p = QFileDialog.getExistingDirectory(self, _("Choose a folder..."))
        if p:
            self.look(p)

    def cleanup(self):
        if self.work and os.path.isdir(self.work):
            shutil.rmtree(self.work, ignore_errors=True)
        self.work = None

    def look(self, path):
        if not self.app.game.ok():
            error(self, "Install mods", _("Choose the game folder first (Game ▾)."))
            return
        self.cleanup()
        self.src = path
        self.work = tempfile.mkdtemp(prefix="fl26ms_")
        label = os.path.splitext(os.path.basename(path.rstrip("\\/")))[0]
        self.name.setText(label)
        self.what.setText(_("Looking inside %s ...") % os.path.basename(path))
        self.tree.clear()
        self.go.setEnabled(False)
        self.app.busy(True, _("Looking inside the mod"))

        sider_dir = self.app.game.sider_dir

        def job(progress):
            top = I.unpack(path, self.work)
            parts = I.detect(top, label)
            for p in parts:
                if p.kind == "world" and I.face_players(p.world_file) and I.face_pack_missing(sider_dir):
                    p.warnings.append(NO_FACES)
            return parts

        run_job(job, self.looked, self.failed)

    def failed(self, tb):
        self.app.busy(False)
        self.what.setText("")
        msg = tb.strip().splitlines()[-1]
        error(self, "Install mods", _("Could not read the mod:") + "\n\n" + msg.split(":", 1)[-1].strip())

    def looked(self, parts):
        self.app.busy(False)
        self.parts = parts
        self.tree.clear()
        if not parts:
            self.what.setText(_("Nothing this program can install was found in %s.") % os.path.basename(self.src))
            return
        roots = [p for p in parts if p.kind == "root"]
        if len(roots) == 1 and roots[0].name.lower() in ("faces", "kits", "boots", "balls", "mod", "livecpk", "files"):
            roots[0].name = I.safe(self.name.text())
        self.what.setText(_("%s holds %d part(s):") % (os.path.basename(self.src), len(parts)))
        for p in parts:
            it = QTreeWidgetItem(["", _(KIND.get(p.kind, p.kind)), p.name, str(p.files), human(p.size),
                                  "  ".join([_(w) for w in p.warnings] + ([_(p.note)] if p.note else []))])
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(0, Qt.Checked if p.install else Qt.Unchecked)
            it.setData(0, ROW, p)
            it.setToolTip(2, p.src)
            if p.warnings:
                it.setForeground(5, QBrush(QColor(theme.WARN)))
            if p.kind in ("pack", "dll"):
                it.setCheckState(0, Qt.Unchecked)
                it.setFlags(it.flags() & ~Qt.ItemIsUserCheckable)
            self.tree.addTopLevelItem(it)
        packs = [p for p in parts if p.kind == "pack"]
        self.go.setEnabled(len(packs) < len(parts))
        if packs and ask(self, "Install mods", _("%s holds %d league package(s). A league package goes into the "
                                                 "League Builder recipe and into the game when you Build. "
                                                 "Add it to the recipe now?") % (os.path.basename(self.src), len(packs))):
            for p in packs:
                self.app.page("Packages").add_pack(p.src)
            if len(packs) == len(parts):
                self.app.open_page("Packages")

    def rename(self, it, col):
        p = it.data(0, ROW)
        if p and p.kind == "root" and col == 2:
            from PySide6.QtWidgets import QInputDialog
            t, ok = QInputDialog.getText(self, _("Name"), _("Folder name in livecpk:"), text=p.name)
            if ok and t.strip():
                p.name = I.safe(t)
                it.setText(2, p.name)

    # ---- install ----
    def install(self):
        chosen = []
        for i in range(self.tree.topLevelItemCount()):
            it = self.tree.topLevelItem(i)
            p = it.data(0, ROW)
            p.install = it.checkState(0) == Qt.Checked and p.kind not in ("pack", "dll")
            if p.install:
                chosen.append(p)
        if not chosen:
            return
        g, s = self.app.game.running()
        if g and not ask(self, "Install mods", _("The game is running. Files it has open may not be replaced. "
                                                 "Install anyway?")):
            return
        name = self.name.text().strip() or "mod"
        if any(r["name"].lower() == name.lower() for r in I.records(self.app.game.sider_dir)) and \
                not ask(self, "Install mods", _("A mod called %s is installed already. Install this one as well?") % name):
            return
        ini = self.app.ini()
        if ini is None:
            error(self, "Install mods", _("There is no sider.ini in SiderAddons."))
            return
        self.app.busy(True, _("Installing %s") % name)
        self.go.setEnabled(False)
        log = []
        where, repl = self.where.currentData(), self.lines.currentData()

        def job(progress):
            inst = I.Installer(self.app.game, ini, name, log=log.append, replace_lines=repl)
            return inst.run(self.parts, where)

        def done(rec):
            self.app.busy(False)
            self.app.save_ini(ini, "installed %s" % name)
            self.app.bus.content_changed.emit()
            self.cleanup()
            self.tree.clear()
            self.what.setText(_("%s is installed.") % name)
            self.say(_("%s is installed: %d file(s) added, %d replaced (the old ones are kept).")
                     % (name, len(rec["created"]), len(rec["replaced"])), "ok")
            if rec.get("world"):
                self.world_on(rec)

        def failed(tb):
            self.app.busy(False)
            self.go.setEnabled(True)
            error(self, "Install mods", _("The install stopped:") + "\n\n" + tb.strip().splitlines()[-1] +
                  "\n\n" + _("What was done so far is in Restore points."))
        run_job(job, done, failed)

    def world_on(self, rec):
        """a League Builder world was installed: install Mod Studio's modules when the face pack
        is missing (its new players' faces come from it), then switch the world on as Build's
        Switch on does (sider.ini, the world file in modules, the world's own modules)"""
        import leaguebuilder as B
        from ..backups import snapshot
        w, game = rec["world"], self.app.game
        modules = rec.get("face_players") and I.face_pack_missing(game.sider_dir) and \
            ask(self, "Install mods", _("%d new players of %s get a generated face from Mod Studio's face pack, "
                                        "which is not installed here. Without it they all look the same. "
                                        "Install Mod Studio's modules now?") % (rec["face_players"], w))
        log = []
        try:
            snapshot(game.ini_path, "Install mods: switch on " + w, game.sider_dir)
            if modules:
                B.install_modules(game.folder, log=log.append)
            B.switch_on(w, game.folder, log=log.append)
        except Exception as e:                            # BuildError, a missing module pack
            error(self, "Install mods", _("%s is installed, but switching it on stopped:") % w + "\n\n" + str(e)
                  + "\n\n" + _("Open League Builder > Build and press 0. Install the modules, then 3. Switch it on."))
            return
        finally:
            self.app.bus.ini_changed.emit()
        if rec.get("face_players") and I.face_pack_missing(game.sider_dir):
            info(self, "Install mods", _(NO_FACES))
        else:
            self.say(_("%s is the live world. Start the game and a new Master League career.") % w, "ok")

    # ---- installed ----
    def refresh(self):
        self.done.clear()
        if not self.app.game.ok() or not os.path.isdir(self.app.game.sider_dir):
            return
        for r in reversed(I.records(self.app.game.sider_dir)):
            t = r.get("time", "")
            when = "%s.%s.%s %s:%s" % (t[6:8], t[4:6], t[0:4], t[9:11], t[11:13]) if len(t) >= 13 else t
            what = ", ".join("%s %s" % (_(KIND.get(k, k)).split(" (")[0].lower(), n) for k, n in r.get("parts", []))
            it = QTreeWidgetItem([r["name"], when, what])
            it.setData(0, ROW, r)
            it.setToolTip(2, "\n".join(r.get("created", [])[:40]))
            self.done.addTopLevelItem(it)

    def uninstall(self):
        it = self.done.currentItem()
        if not it:
            return
        rec = it.data(0, ROW)
        if not ask(self, "Remove the mod", _("Remove %s? The files it added are deleted, the files it replaced "
                                             "come back, and its sider.ini and map lines are taken out.") % rec["name"]):
            return
        ini = self.app.ini()
        if ini is None:
            return
        notes = I.uninstall(self.app.game, ini, rec)
        self.app.save_ini(ini, "removed %s" % rec["name"])
        self.app.bus.content_changed.emit()
        self.refresh()
        if notes:
            info(self, "Remove the mod", "\n".join(notes[:20]))
        else:
            self.say(_("%s is removed.") % rec["name"], "ok")
