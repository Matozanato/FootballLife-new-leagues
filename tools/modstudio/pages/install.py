"""Install: drop a mod (zip, 7z, folder, .lua, .cpk), see what is in it, install it; and the
list of mods installed with the program, each one removable"""
import os, re, shutil, tempfile

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (QComboBox, QFileDialog, QFrame, QLabel, QLineEdit, QPushButton,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout)

from .. import installer as I, saves, theme
from ..i18n import _
from ..roots import human
from ..ui import Page, Fold, section, hint, row, ask, error, info, run_job, can_write, denied, save_switch, save_note

ROW = Qt.UserRole
KIND = {"root": "Content folder (livecpk)", "content": "Content server files", "module": "Lua module",
        "cpk": "Packed .cpk (unpacked on install)", "pack": "League package", "dll": "DLL (not installed)",
        "world": "Ready world (goes in the game)"}
NO_FACES = ("Mod Studio's modules with the face pack are not installed: the new players of this world "
            "will all look the same until you install them (Home > Install now).")


def gb(n):
    """bytes as "2.1 GB" / "640 MB" """
    return "%.1f GB" % (n / 1e9) if n >= 1e9 else "%d MB" % (n / 1e6)


class Drop(QFrame):
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.setObjectName("card")
        self.setAcceptDrops(True)
        self.setMinimumHeight(110)
        v = QVBoxLayout(self)
        t = QLabel(_("Drop the pack here"))
        t.setObjectName("cardvalue")
        t.setAlignment(Qt.AlignCenter)
        s = QLabel(_("a modpack or world (.zip), a league package (.fl26pack), any other mod (.7z, a folder, "
                     ".lua, .cpk)"))
        s.setObjectName("cardlabel")
        s.setAlignment(Qt.AlignCenter)
        v.addWidget(t)
        v.addWidget(s)
        b1 = QPushButton(_("Choose a file..."))
        b1.clicked.connect(page.pick_file)
        b2 = QPushButton(_("Choose a folder..."))
        b2.clicked.connect(page.pick_folder)
        v.addWidget(row("stretch", b1, b2, "stretch", stretch=False))
        # B39 (quicksite): Windows does not let Explorer drop files on a program that runs as
        # administrator (Restart as administrator, a game under Program Files); dropping did nothing
        from .. import access
        if access.is_admin():
            n = QLabel(_("Mod Studio runs as administrator, so Windows blocks drag and drop here: "
                         "use Choose a file... or Choose a folder..."))
            n.setObjectName("cardlabel")
            n.setStyleSheet("color: %s;" % theme.WARN)
            n.setWordWrap(True)
            n.setAlignment(Qt.AlignCenter)
            v.addWidget(n)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.toLocalFile()]
        if paths:
            self.page.look(paths[0])


class Install(Page):
    title = "Import your world"
    hint = ("Put a pack you downloaded into the game. Mod Studio looks inside, says what it is and installs "
            "it; a newer version of a pack you have replaces the older one. Everything installed here can be "
            "removed again.")

    def __init__(self, app):
        super().__init__(app)
        self.work = None
        self.parts = []
        self.src = None
        self.outer.addWidget(Drop(self))
        # what the pack is, in plain words, and the one button
        self.result = QFrame()
        self.result.setObjectName("card")
        rv = QVBoxLayout(self.result)
        self.what = QLabel("")
        self.what.setObjectName("cardvalue")
        self.what.setWordWrap(True)
        rv.addWidget(self.what)
        self.summary = hint("")
        rv.addWidget(self.summary)
        self.go = QPushButton(_("Install"))
        self.go.setObjectName("primary")
        self.go.setStyleSheet("font-size: 10pt; font-weight: bold; padding: 8px 24px;")
        self.go.clicked.connect(self.install)
        self.go.setEnabled(False)
        rv.addWidget(row("stretch", self.go, stretch=False))
        self.result.hide()
        self.outer.addWidget(self.result)
        # all the choices, folded
        self.more = Fold("More options: which parts, name, order of the content folders, map lines", app, "install_more")
        self.more.body.addWidget(hint(_("Untick a part you do not want, for example the kits. Double-click a "
                                        "content folder's name to rename it.")))
        self.tree = QTreeWidget()
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setHeaderLabels([_("Install"), _("What it is"), _("Name"), _("Files"), _("Size"), _("Note")])
        for c, w in enumerate((60, 230, 240, 60, 80)):
            self.tree.setColumnWidth(c, w)
        self.tree.setMinimumHeight(160)
        self.tree.itemDoubleClicked.connect(self.rename)
        self.more.body.addWidget(self.tree, 1)
        self.name = QLineEdit()
        self.name.setPlaceholderText(_("name of the mod (it is listed under this name)"))
        self.where = QComboBox()
        self.where.addItem(_("New content folders go on top (they win)"), "top")
        self.where.addItem(_("New content folders go at the bottom"), "bottom")
        self.lines = QComboBox()
        self.lines.addItem(_("Map lines for a club already mapped: use the mod's"), True)
        self.lines.addItem(_("Map lines for a club already mapped: keep mine, add the mod's after"), False)
        self.more.body.addWidget(row(QLabel(_("Name")), self.name))
        self.more.body.addWidget(row(self.where, self.lines))
        self.more.hide()
        self.outer.addWidget(self.more)
        # what is in the game
        self.outer.addWidget(section("In the game now"))
        self.done = QTreeWidget()
        self.done.setRootIsDecorated(False)
        self.done.setAlternatingRowColors(True)
        self.done.setHeaderLabels([_("Pack"), _("Installed")])
        self.done.setColumnWidth(0, 420)
        self.outer.addWidget(self.done, 1)
        rm = QPushButton(_("Remove"))
        rm.setObjectName("danger")
        rm.clicked.connect(self.uninstall)
        self.packs_line = hint("")
        self.outer.addWidget(row(rm, self.packs_line))
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
            error(self, "Import your world", _("Choose the game folder first (Game ▾)."))
            return
        if path.lower().endswith(".fl26pack"):
            self.add_league_pack(path)
            return
        self.cleanup()
        self.src = path
        self.work = tempfile.mkdtemp(prefix="fl26ms_")
        label = os.path.splitext(os.path.basename(path.rstrip("\\/")))[0]
        self.name.setText(label)
        self.what.setText(_("Looking inside %s ...") % os.path.basename(path))
        self.tree.clear()
        self.go.setEnabled(False)
        self.summary.setText("")
        self.result.show()
        self.app.busy(True, _("Looking inside the mod"))

        sider_dir, game = self.app.game.sider_dir, self.app.game

        def job(progress):
            top = I.unpack(path, self.work, progress=lambda d, n, b: progress((d, n, b)))
            parts = I.detect(top, label)
            for p in parts:
                if p.kind == "world" and I.face_players(p.world_file) and I.face_pack_missing(sider_dir):
                    p.warnings.append(NO_FACES)
                # B74: a world of the same name built on this PC: Install would stop on it, so say
                # it now and leave that part out (translated and filled in already)
                p.blocked = p.kind == "world" and I.world_in_the_way(game, p.name)
                if p.blocked:
                    p.warnings.insert(0, I.world_there(p.name))
            return parts

        clock = self.ticking(_("Looking inside %s") % os.path.basename(path))

        def unpacked(d, n, b):
            clock.step("%d / %d %s · %s" % (d, n, _("files"), gb(b)))

        def looked(parts):
            clock.stop()
            self.looked(parts)

        def failed(tb):
            clock.stop()
            self.failed(tb)
        run_job(job, looked, failed, progress=lambda t: unpacked(*t))

    def ticking(self, what):
        """B84: a line that counts the seconds, and the step the worker is at, in the status bar and
        on the page, like Build's -- "Installing X 1:23 · 512 / 4 000 files · 2.1 GB". Without it a
        4 GB Modpack looked hung (Vicentico, beta 16.10.)"""
        from PySide6.QtCore import QTimer
        import time as _time
        t0, last = _time.monotonic(), [""]
        clock = QTimer(self)

        def text():
            m, sec = divmod(int(_time.monotonic() - t0), 60)
            return "%s %d:%02d" % (what, m, sec) + ("   ·   " + last[0] if last[0] else "")

        def tick():
            t = text()
            self.app.status_busy.setText("● " + t)
            self.what.setText(t)
        clock.timeout.connect(tick)
        clock.start(1000)
        clock.step = lambda s: (last.__setitem__(0, s), tick())
        tick()
        return clock

    def failed(self, tb):
        self.app.busy(False)
        self.what.setText("")
        self.result.hide()
        msg = tb.strip().splitlines()[-1]
        error(self, "Import your world", _("Could not read the mod:") + "\n\n" + msg.split(":", 1)[-1].strip())

    def looked(self, parts):
        self.app.busy(False)
        self.parts = parts
        self.tree.clear()
        if not parts:
            self.what.setText(_("Nothing this program can install was found in %s.") % os.path.basename(self.src))
            self.more.hide()
            return
        self.more.show()
        roots = [p for p in parts if p.kind == "root"]
        if len(roots) == 1 and roots[0].name.lower() in ("faces", "kits", "boots", "balls", "mod", "livecpk", "files"):
            roots[0].name = I.safe(self.name.text())
        self.what.setText(self.headline(parts))
        self.summary.setText(self.plain(parts))
        for p in parts:
            it = QTreeWidgetItem(["", _(KIND.get(p.kind, p.kind)), p.name, str(p.files), human(p.size),
                                  "  ".join([_(w) for w in p.warnings] + ([_(p.note)] if p.note else []))])
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(0, Qt.Checked if p.install else Qt.Unchecked)
            it.setData(0, ROW, p)
            it.setToolTip(2, p.src)
            if p.warnings:
                it.setForeground(5, QBrush(QColor(theme.WARN)))
            if p.kind in ("pack", "dll") or getattr(p, "blocked", False):
                it.setCheckState(0, Qt.Unchecked)
                it.setFlags(it.flags() & ~Qt.ItemIsUserCheckable)
            self.tree.addTopLevelItem(it)
        packs = [p for p in parts if p.kind == "pack"]
        world = any(p.kind == "world" for p in parts)
        # a ready world takes the defaults: nothing to choose, one button
        self.where.setVisible(not world)
        self.lines.setVisible(not world)
        if world:
            self.where.setCurrentIndex(0)
            self.lines.setCurrentIndex(0)
        self.go.setText(_("Install the world") if world else _("Install"))
        self.go.setEnabled(any(p.kind != "pack" and not getattr(p, "blocked", False) for p in parts))
        if packs and ask(self, "Import your world", _("%s holds %d league package(s). A league package goes into "
                                                 "your world, and into the game when you Build. "
                                                 "Add it to your world now?") % (os.path.basename(self.src), len(packs))):
            for p in packs:
                self.app.page("Packages").add_pack(p.src)
            if len(packs) == len(parts):
                self.app.open_page("Packages")

    def headline(self, parts):
        """what the pack is, in one line"""
        worlds = [p for p in parts if p.kind == "world"]
        base = os.path.basename(self.src.rstrip("\\/"))
        if worlds:
            w = worlds[0].name
            if I.installed_as(self.app.game.sider_dir, w) or I.ready_world(self.app.game, w):
                return _("%s: a newer version of the world %s you have") % (base, w)
            return _("%s: a ready world to play (%s)") % (base, w)
        if all(p.kind == "pack" for p in parts):
            return _("%s: a league package") % base
        return _("%s: a mod") % base

    def plain(self, parts):
        """what is inside and what happens on Install, in plain words"""
        out = []
        worlds = [p for p in parts if p.kind == "world"]
        for p in worlds:
            try:
                import fl26world
                n = len(fl26world.read_world(p.world_file)[1])
                out.append(_("%d leagues with their clubs, players and faces") % n)
            except Exception:
                pass
            if I.installed_as(self.app.game.sider_dir, p.name) or I.ready_world(self.app.game, p.name):
                out.append(_("The older version is taken out first, nothing of it stays behind. Your saves are "
                             "not touched; start a new Master League with this one."))
        counts = {}
        for p in parts:
            if p.kind != "world":
                label = _(KIND.get(p.kind, p.kind)).split(" (")[0]
                counts[label] = counts.get(label, 0) + 1
        if counts:
            out.append(_("Also inside: %s") % ", ".join("%s%s" % ("%d \u00d7 " % n if n > 1 else "", k)
                                                      for k, n in sorted(counts.items())))
        if worlds:
            out.append(_("Install puts it in the game and switches it on, with Mod Studio's modules. No Build needed."))
        warn = sorted({_(w) for p in parts for w in p.warnings})
        if warn:
            out.append("! " + "  ".join(warn))
        return "\n".join(out)

    def add_league_pack(self, path):
        """a .fl26pack: its own window chooses the leagues and the parts; then Build puts it in the game"""
        packs = self.app.page("Packages")
        if packs.add_pack(path):
            self.what.setText(_("%s: a league package") % os.path.basename(path))
            self.summary.setText(_("Its leagues are in your world now. Build and install puts them in the game."))
            self.result.show()
            self.go.setEnabled(False)
            self.more.hide()
            self.refresh()
            build = self.app.page("Build")
            if hasattr(build, "build_all"):
                self.app.open_page("Build")
                build.build_all()

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
        if g and not ask(self, "Import your world", _("The game is running. Files it has open may not be replaced. "
                                                 "Install anyway?")):
            return
        name = self.name.text().strip() or "mod"
        sd = self.app.game.sider_dir
        older = [p.name for p in chosen if p.kind == "world"
                 and (I.installed_as(sd, p.name) or I.ready_world(self.app.game, p.name))]
        if older and not ask(self, "Import your world", _("%s is installed already (an older version). It is taken out "
                                                     "first, then this one goes in. Your saves are not touched; "
                                                     "start a new Master League with the new version.\n\n"
                                                     "Replace it?") % ", ".join(older)):
            return
        replaced = {r["name"].lower() for w in older for r in I.installed_as(sd, w)}
        if name.lower() not in replaced and any(r["name"].lower() == name.lower() for r in I.records(self.app.game.sider_dir)) and \
                not ask(self, "Import your world", _("A mod called %s is installed already. Install this one as well?") % name):
            return
        ini = self.app.ini()
        if ini is None:
            error(self, "Import your world", _("There is no sider.ini in SiderAddons."))
            return
        if not can_write(self, self.app.game):        # a game under Program Files (B14)
            return
        # a world goes in switched on, and its save folder with it (mato 15.10.): the world in the
        # game now, before the install writes the new one's line, and refused here when the save
        # folder cannot be switched (the game running, a save_<world> name taken)
        self.save_sw = None
        new = next((p.name for p in chosen if p.kind == "world"), None)
        if new:
            self.save_sw = save_switch(self, self.app, new, saves.in_game(self.app.game), title="Import your world")
            if self.save_sw is None:
                return
        self.app.busy(True, _("Installing %s") % name)
        self.go.setEnabled(False)
        log = []
        where, repl = self.where.currentData(), self.lines.currentData()
        # a scoreboard / menu pack's lines go to the competitions of the world in the game; a
        # world zip brings its own world, whose lines are already right
        comps = None
        if not any(p.kind == "world" and p.install for p in self.parts):
            try:
                comps = self.app.project.names()[1]
            except Exception:
                comps = None

        clock = self.ticking(_("Installing %s") % name)

        def job(progress):
            for w in older:                       # the older version out first, not copied over
                progress(_("Taking out the older %s") % w)
                I.replace_world(self.app.game, ini, w, log=log.append)
            inst = I.Installer(self.app.game, ini, name, log=log.append, replace_lines=repl, comps=comps,
                               progress=lambda d, n, b: progress("%d / %d %s · %s" % (d, n, _("files"), gb(b))))
            return inst.run(self.parts, where)

        def done(rec):
            clock.stop()
            self.app.busy(False)
            self.app.save_ini(ini, "installed %s" % name)
            self.app.bus.content_changed.emit()
            self.cleanup()
            self.tree.clear()
            self.more.hide()
            self.what.setText(_("%s is installed.") % name)
            self.summary.setText("")
            self.say(_("%s is installed: %d file(s) added, %d replaced (the old ones are kept).")
                     % (name, len(rec["created"]), len(rec["replaced"])), "ok")
            if rec.get("unmatched"):
                self.say(_("%s is installed, but this world has no competition called %s: pick the "
                           "competition yourself on Game content > Servers (Library > Use it for...).")
                         % (name, ", ".join(rec["unmatched"])), "warn")
            if rec.get("world"):
                self.world_on(rec)

        def failed(tb):
            clock.stop()
            self.app.busy(False)
            self.go.setEnabled(True)
            if denied(self, tb):
                return
            # the error's own words, without "ValueError:" and the like in front (B74)
            why = re.sub(r"^(?:\w+\.)*\w*(?:Error|Exception|WorldThere): ", "", tb.strip().splitlines()[-1])
            error(self, "Import your world", _("The install stopped:") + "\n\n" + why +
                  "\n\n" + _("What was done so far is in Restore points."))
        run_job(job, done, failed, progress=clock.step)

    def world_on(self, rec):
        """a League Builder world was installed: install this version's modules (the face pack the
        new players' faces come from is one of them), then switch the world on as Build's Switch
        on does (sider.ini, the world file in modules, the world's own modules). Always: modules
        of an older Mod Studio, face pack and all, left a new world on the old ones without a word.
        B84: in a worker, with the clock -- on the GUI thread the copy of the modules froze the window"""
        import leaguebuilder as B
        from ..backups import snapshot
        w, game = rec["world"], self.app.game
        modules = True
        log = []
        sw = getattr(self, "save_sw", None)
        if sw is None or sw.new != w:
            sw = saves.Switch(self.app.settings, game, w)
        self.app.busy(True, _("Switching %s on") % w)
        clock = self.ticking(_("Switching %s on") % w)

        def job(progress):
            def say(t):
                log.append(t)
                line = str(t).strip().splitlines()
                if line:
                    progress(line[-1][:90])
            snapshot(game.ini_path, "Import your world: switch on " + w, game.sider_dir)
            if modules:
                B.install_modules(game.folder, log=say)
            # the careers of the world going out aside, this one's in; back as they were when the
            # switch stops
            sw.go(say)
            try:
                B.switch_on(w, game.folder, log=say)
            except BaseException:
                try:
                    sw.undo(say)
                except Exception:
                    pass
                raise

        def over(_r=None):
            clock.stop()
            self.app.busy(False)
            self.app.bus.ini_changed.emit()
            save_note(self, sw)
            self.final_check(w)

        def failed(tb):                                   # BuildError, SaveError, a missing module pack
            clock.stop()
            self.app.busy(False)
            self.app.bus.ini_changed.emit()
            if denied(self, tb):
                return
            why = re.sub(r"^(?:\w+\.)*\w*(?:Error|Exception): ", "", tb.strip().splitlines()[-1])
            error(self, "Import your world", _("%s is installed, but switching it on stopped:") % w + "\n\n" + why
                  + "\n\n" + _("On Home press Install now, then in My world press Activate on this world."))
        run_job(job, over, failed, progress=clock.step)

    def final_check(self, w):
        """0.2.4: after a ready world, check all it needs and say Ready to play, or what to fix"""
        from .. import checks
        rows = checks.ready_check(self.app.game, w)
        bad = [t for lv, t in rows if lv == "err"]
        warn = [t for lv, t in rows if lv == "warn"]
        good = [t for lv, t in rows if lv == "ok"]
        text = "\n".join(["\u2713  " + t for t in good] + ["!  " + t for t in warn] + ["\u2717  " + t for t in bad])
        if bad:
            # the banner stays after the box is closed: its link shows the list again (Novarama,
            # beta 15.10.: "see what to fix -- where?")
            self.fix_text = text
            self.say(_('%s is installed, but not ready to play yet: <a href="fix">see what to fix</a>.') % w, "err")
            self.show_fix()
        else:
            self.say(_("%s is ready to play. Press Play and start a new Master League.") % w, "ok")
            self.what.setText(_("\u2713 Ready to play: press Play and start a new Master League"))
            info(self, _("Ready to play"), text + "\n\n" +
                 _("Press Play and start a NEW Master League (an old career does not get the new leagues). "
                   "No Build needed."))

    def show_fix(self):
        error(self, _("Almost ready"), _("Fix these, then the world is ready to play:") + "\n\n" +
              getattr(self, "fix_text", ""))

    def banner_link(self, href):
        if href == "fix" and getattr(self, "fix_text", ""):
            self.show_fix()
        else:
            super().banner_link(href)

    # ---- installed ----
    def refresh(self):
        self.done.clear()
        if not self.app.game.ok() or not os.path.isdir(self.app.game.sider_dir):
            return
        for r in reversed(I.records(self.app.game.sider_dir)):
            t = r.get("time", "")
            when = "%s.%s.%s %s:%s" % (t[6:8], t[4:6], t[0:4], t[9:11], t[11:13]) if len(t) >= 13 else t
            what = ", ".join("%s %s" % (_(KIND.get(k, k)).split(" (")[0].lower(), n) for k, n in r.get("parts", []))
            it = QTreeWidgetItem([r["name"], when])
            it.setData(0, ROW, r)
            it.setToolTip(0, what)
            it.setToolTip(1, what)
            self.done.addTopLevelItem(it)
        self.packs_line.setText(self.packs_text())

    def packs_text(self):
        try:
            import lbpackage as K
            n = len(K.packs(self.app.page("Packages").project.recipe))
        except Exception:
            return ""
        return (_("League packages in your world: %d (My world > More > League packages)") % n) if n else ""

    def uninstall(self):
        it = self.done.currentItem()
        if not it:
            return
        rec = it.data(0, ROW)
        if not ask(self, "Remove the mod", _("Remove %s? The files it added are deleted, the files it replaced "
                                             "come back, and its sider.ini and map lines are taken out.") % rec["name"]):
            return
        ini = self.app.ini()
        if ini is None or not can_write(self, self.app.game):
            return
        notes = I.uninstall(self.app.game, ini, rec)
        self.app.save_ini(ini, "removed %s" % rec["name"])
        self.app.bus.content_changed.emit()
        self.refresh()
        if notes:
            info(self, "Remove the mod", "\n".join(notes[:20]))
        else:
            self.say(_("%s is removed.") % rec["name"], "ok")
