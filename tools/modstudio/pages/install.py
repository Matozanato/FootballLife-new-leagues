"""Install: drop a mod (zip, 7z, folder, .lua, .cpk), see what is in it, install it; and the
list of mods installed with the program, each one removable"""
import bigjson
import html, os, re, shutil, tempfile, threading

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (QComboBox, QFileDialog, QFrame, QLabel, QLineEdit, QPushButton,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout)

from .. import installer as I, saves, theme
from ..i18n import _
from ..roots import human
from ..ui import (Page, Fold, section, hint, row, ask, error, info, run_job, can_write, denied, save_switch, save_note,
                  next_turn)

ROW = Qt.UserRole
KIND = {"root": "Content folder (livecpk)", "content": "Content server files", "module": "Lua module",
        "cpk": "Packed .cpk (unpacked on install)", "pack": "League package", "dll": "DLL (not installed)",
        "world": "Ready world (goes in the game)"}
NO_FACES = ("Mod Studio's modules with the face pack are not installed: the new players of this world "
            "will all look the same until you install them (Home > Install now).")


def warm_modules_state(game):
    """from a worker, at the end of its job: the header's comparison of every module with the pack
    (checks.modules_state) is done here, so the window's thread finds it kept (B479, 15.11.)"""
    try:
        from .. import checks
        checks.warm_modules(game)          # (and the modules' links Home's checks read, B480)
    except Exception:
        pass


def update_words(up):
    """"GigaPack beta 3 -> GigaPack beta 4" of an Update (installer.update_check)"""
    if up.get("from") and up.get("to"):
        return _("%s → %s") % (up["from"], up["to"])
    return _("the version you have → %s") % (up.get("to") or "?")


def _retired_n(up, kind):
    r = up.get("retired") or {}
    return r.get(kind, 0) if isinstance(r, dict) else (r if kind == "players" else 0)


def retired_text(up):
    """the players of the version installed the new one retires, and why (the author's reasons, the
    recipe's id_retire): only players -- a club, league or cup retired is no Update (no_update_text)"""
    n = _retired_n(up, "players")
    if not n:
        return ""
    why = "; ".join(str(x) for x in (up.get("reasons") or [])[:3])
    return (_("%d players of the version you have are not in this one (its author took them out: %s). In a "
              "career their place may show a stand-in player.") % (n, why) if why else
            _("%d players of the version you have are not in this one (its author took them out). In a career "
              "their place may show a stand-in player.") % n)


def changed_text(up):
    """the leagues whose shape the new version changed (idledger.structure_changes)"""
    ch = up.get("changed") or []
    if not ch:
        return ""
    return (_("These leagues are played another way in this version (clubs, rounds, promotion or relegation): "
              "%s. A career's season running now was laid out the old way and may not go right; this is not "
              "checked in the game.") % ", ".join(ch[:8]) + (" ..." if len(ch) > 8 else ""))


def renamed_text(up):
    """the clubs of the version installed that have another name under the same id (idledger.renamed):
    a career sees each as the club it was -- right for a rename, not for another club in its place"""
    ren = up.get("renamed") or []
    if not ren:
        return ""
    return (_("%d clubs have another name under the same id (%s): a career sees each as the same club.")
            % (len(ren), ", ".join("%s → %s" % (a, b) for _t, a, b in ren[:5]) + (" ..." if len(ren) > 5 else "")))


def new_comps_text(up):
    """the leagues and cups the Update brings that the installed version does not have (18.11.2026
    evening, rowkeep.py: their rows go after the old ones, so careers go on without them)"""
    n = int(up.get("new_leagues") or 0) + int(up.get("new_cups") or 0)
    if not n:
        return ""
    return _("%d new league(s) and cup(s) appear only in a new Master League; your careers go on without "
             "them.") % n


def update_text(up):
    """what an Update does, in the summary of the zip"""
    text = (_("Update (%s): the version you have is replaced by this one. Your careers stay: every club, league, "
              "cup and player id they hold is still there. What a running career shows of this version's changes is "
              "not checked in the game; for all that is new, start a new Master League.") % update_words(up))
    for extra in (new_comps_text(up), retired_text(up), changed_text(up), renamed_text(up)):
        if extra:
            text += " " + extra
    return text


def no_update_text(up):
    """why a zip of a world installed already is not an Update of it"""
    why = up.get("why")
    if why == "other":
        # review 18.11.2026: "another world" was not true of a world its author started again (another
        # lineage) or changed past the names rule: said as what Mod Studio knows
        return _("Warning: Mod Studio cannot tell that this is a later version of the one you have: it is another "
                 "world with the same name, or one its author made again without the ids of yours. A career of the "
                 "one you have does not continue in it.")
    if why == "diverged":
        return (_("Warning: this version (%s) and the one you have (%s) both come after an earlier version, but the "
                  "one you have is not one this version was made from (a test zip, or a version made on another "
                  "PC). Its ids may stand for other clubs and players, so it replaces the one you have and a career "
                  "of the one you have does not continue in it.") % (up.get("to") or "?", up.get("from") or "?"))
    if why == "older":
        return _("Warning: this is an older version (%s) than the one you have (%s). A career of the one you have "
                 "does not continue in it.") % (up.get("to") or "?", up.get("from") or "?")
    if why == "same":
        return _("This is the version you have: it goes in again.")
    if why == "rows":
        # 18.11.2026 evening (installer.rows_verdict, rowkeep.report_of): the ids are kept, but a
        # league or cup of the version installed lost a place, has another club in one, or a new club
        return _("Warning: this version changes leagues or cups a career of the one you have is playing (a place "
                 "in them is gone, holds another club or has a club new to the world, or their rows in the game's "
                 "tables moved). It replaces the one you have and a career of the one you have does not continue "
                 "in it.")
    if why == "retired":
        r = up.get("retired") or {}
        names = up.get("retired_names") or {}
        words = {"clubs": _("clubs"), "leagues": _("leagues"), "cups": _("cups")}
        listed = "; ".join("%s: %s" % (words[k], ", ".join(names.get(k) or []) or r[k])
                           for k in ("leagues", "cups", "clubs") if r.get(k))
        why_ = "; ".join(str(x) for x in (up.get("reasons") or [])[:3])
        return (_("Warning: this version takes out clubs, leagues or cups of the one you have (%s). A career "
                  "that has them does not continue in it, so it replaces the one you have.") % listed
                + (" " + _("Its author says why: %s.") % why_ if why_ else ""))
    words = {"clubs": _("clubs"), "players": _("players"), "leagues": _("leagues"), "cups": _("cups"),
             "reused": _("ids given to someone else")}
    gone = ", ".join("%d %s" % (n, words.get(k, k)) for k, n in sorted((up.get("gone") or {}).items()) if k != "plan")
    if not gone:
        return _("Warning: Mod Studio cannot tell the ids of the version you have, so a career of it may not "
                 "continue in this one.")
    return (_("Warning: this version does not keep all ids of the one you have (gone or changed: %s). A career "
              "of the version you have may break in it.") % gone
            + (" " + _("Its author's first version that keeps track of ids cannot promise that.")
               if up.get("first") else ""))


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
        # (behind another page the list waits for shown(): it reads the installed packs' record,
        # megabytes with a big world, 0.2 s of every Put in the game, 11.11.)
        app.bus.content_changed.connect(lambda: self.refresh() if self.isVisible() else None)

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
            # off the window's thread: the Modpack's unpacked zip took 9 s to delete and the window
            # stopped answering (coldstart, 17.10.); each look has a mkdtemp of its own
            import threading
            threading.Thread(target=shutil.rmtree, args=(I.long_path(self.work),), kwargs={"ignore_errors": True},
                             daemon=True).start()
        self.work = None

    def look(self, path, auto=False):
        """auto: a world zip from + Add..., installed with the defaults as soon as it is read"""
        self.auto = auto
        if not self.app.game.ok():
            error(self, "Import your world", _("Choose the game folder first (Game ▾)."))
            return
        if path.lower().endswith(".fl26pack"):
            self.add_league_pack(path)
            return
        self.cleanup()
        # B480: where to unpack it is worked out by a worker. work_dir reads the zip's list of files
        # (its size unpacked): the GigaPack's 160,000 files, 0.8 s of a stopped window (the exe test
        # of beta4o, zipfile._RealGetContents on the window's thread)
        self._look_n = n = getattr(self, "_look_n", 0) + 1
        sider = self.app.game.sider_dir

        def where(_progress):
            try:
                return True, I.work_dir(path, sider)
            except (OSError, ValueError) as e:
                return False, str(e)

        def placed(r):
            got, work = r
            if n != self._look_n:                 # another look() since: this one is not wanted
                if got:
                    threading.Thread(target=shutil.rmtree, args=(I.long_path(work),),
                                     kwargs={"ignore_errors": True}, daemon=True).start()
                return
            if not got:
                error(self, "Import your world", _("Could not read the mod:") + "\n\n" + work)
                return
            self._look_in(path, work)

        def lost(tb):
            if n == self._look_n:
                error(self, "Import your world", _("Could not read the mod:") + "\n\n" +
                      tb.strip().splitlines()[-1].split(":", 1)[-1].strip())
        run_job(where, placed, lost)

    def _look_in(self, path, work):
        """look(), the rest: `work` is the empty folder to unpack `path` in"""
        self.src = path
        self.work = work
        label = os.path.splitext(os.path.basename(path.rstrip("\\/")))[0]
        self.name.setText(label)
        self.what.setText(_("Looking inside %s ...") % os.path.basename(path))
        self.tree.clear()
        self.go.setEnabled(False)
        # Jeyspeed, beta 18.11.2026: the Update choice of a GigaPack comes only when the whole zip
        # is read, and he thought Update did not work. Say it while it reads.
        self.summary.setText(_("Reading the whole file first. When it is done, what is inside shows up here, "
                               "with Install, or Update for a new version of a world you have. "
                               "A big world takes a few minutes."))
        self.result.show()
        self.app.busy(True, _("Looking inside the mod"))

        sider_dir, game = self.app.game.sider_dir, self.app.game

        def job(progress):
            top = I.unpack(path, self.work, progress=lambda d, n, b: progress((d, n, b)))
            parts = I.detect(top, label)
            notice = I.read_notice(top)
            for p in parts:
                if p.kind == "world":
                    p.notice = notice             # the author's words (the recipe's "notice"), first in the summary
                    p.made = I.world_made(path)       # newer or older than the one installed (headline)
                    # 17.11.2026: an Update when its id ledger keeps every id of the version installed
                    # (the careers of it go on); None: a zip without a ledger, or nothing installed
                    p.update = None
                    if I.installed_as(sider_dir, p.name) or I.ready_world(game, p.name):
                        try:
                            p.update = I.update_check(game, p.name, os.path.dirname(p.world_file))
                        except (OSError, ValueError):
                            p.update = None
                if p.kind == "world" and I.face_players(p.world_file) and I.face_pack_missing(sider_dir):
                    p.warnings.append(NO_FACES)
                # B74: a world of the same name built on this PC: Install would stop on it, so say
                # it now and leave that part out (translated and filled in already)
                p.blocked = p.kind == "world" and I.world_in_the_way(game, p.name)
                if p.blocked:
                    p.warnings.insert(0, I.world_there(p.name))
                # mato 07.11.: a world for the other game (an FL 2027 world in FL26 breaks it) stays out
                bad = I.wrong_game(game.folder, p.src, p.world_file, p.name) if p.kind in ("world", "root") else None
                if bad:
                    p.blocked = p.wrong_game = True
                    p.install = False
                    p.warnings.insert(0, bad)
                # B400: a file the game could not open with the game in this folder (MAX_PATH)
                p.too_long = None if p.blocked else I.too_long(game, p)
                if p.too_long:
                    p.warnings.insert(0, I.too_long_text(game, *p.too_long[:2]))
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
            self.summary.setText("")
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
        # B379 (09.11.): a world of the other game stays out, and the rest of its zip (scoreboards,
        # map lines for its competitions) is no use without it: "installed" with none of it working
        wrong = any(getattr(p, "wrong_game", False) for p in parts)
        self.go.setEnabled(not wrong and any(p.kind != "pack" and not getattr(p, "blocked", False) for p in parts))
        if getattr(self, "auto", False) and world and self.go.isEnabled():
            self.auto = False
            self.install()
            return
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
                up = getattr(worlds[0], "update", None)
                if up and up.get("ok"):
                    return _("%s: an update of the world %s you have (%s)") % (base, w, update_words(up))
                if up and up.get("why") == "other":
                    return _("%s: a world with the name %s you have, not a later version of it") % (base, w)
                if up and up.get("why") == "diverged":
                    return _("%s: a version of the world %s that does not follow the one you have") % (base, w)
                if up and up.get("why") == "rows":
                    return _("%s: a later version of the world %s you have, in which its careers do not go on") % (base, w)
                # 16.11.: an older zip was "a newer version" too. The ledgers' numbers tell which is
                # which (review 17.11.: an older zip was offered as an Update), else the zips' times
                v = (up or {}).get("why") if (up or {}).get("why") in ("older", "same") else \
                    I.world_version(self.app.game.sider_dir, w, getattr(worlds[0], "made", None))
                if v == "newer":
                    return _("%s: a newer version of the world %s you have") % (base, w)
                if v == "older":
                    return _("%s: an older version of the world %s than the one you have") % (base, w)
                if v == "same":
                    return _("%s: the same version of the world %s you have") % (base, w)
                return _("%s: another version of the world %s you have") % (base, w)
            return _("%s: a ready world to play (%s)") % (base, w)
        if all(p.kind == "pack" for p in parts):
            return _("%s: a league package") % base
        return _("%s: a mod") % base

    def plain(self, parts):
        """what is inside and what happens on Install, in plain words"""
        out = []
        worlds = [p for p in parts if p.kind == "world"]
        for p in worlds:
            if getattr(p, "notice", ""):
                out.append(_("From the author of %s:") % p.name + "\n" + p.notice + "\n")
        for p in worlds:
            try:
                import fl26world
                n = len(fl26world.read_world(p.world_file)[1])
                out.append(_("%d leagues with their clubs, players and faces") % n)
            except Exception:
                pass
            if I.installed_as(self.app.game.sider_dir, p.name) or I.ready_world(self.app.game, p.name):
                up = getattr(p, "update", None)
                if up and up.get("ok"):
                    out.append(update_text(up))
                    continue
                out.append(_("The version you have is taken out first, nothing of it stays behind. Your saves "
                             "are not touched; start a new Master League with this one."))
                if up:
                    out.append("! " + no_update_text(up))
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
        long = [p for p in chosen if getattr(p, "too_long", None)]
        if long and not ask(self, "Import your world", I.too_long_text(self.app.game, sum(p.too_long[0] for p in long),
                                                                        max(p.too_long[1] for p in long))
                            + "\n\n" + _("Install anyway?")):
            return
        name = self.name.text().strip() or "mod"
        sd = self.app.game.sider_dir
        older = [p.name for p in chosen if p.kind == "world"
                 and (I.installed_as(sd, p.name) or I.ready_world(self.app.game, p.name))]
        ups = [getattr(p, "update", None) for p in chosen if p.kind == "world" and p.name in older]
        self.updating = bool(older) and all(u and u.get("ok") for u in ups)
        yours = _("Files you added to the world's folder or changed in it are not in the new "
                  "version: Mod Studio keeps a copy of them and tells you where.")
        if self.updating:
            # 17.11.2026: the careers of the version installed go on in this one (its id ledger
            # keeps every id they hold): Update, and no "start a new Master League"
            if not self.ask_update(older[0], ups[0], yours):
                return
        elif older and not ask(self, "Import your world", _("%s is installed already. It is taken out first, then this "
                                                       "one goes in. Your saves are not touched; start a new Master "
                                                       "League with this one.\n\nReplace it?") % ", ".join(older)
                               + "".join("\n\n" + no_update_text(u) for u in ups if u)
                               + "\n\n" + yours):
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
        import time
        self.t_install = time.time()               # an Edit save older than this is the old world's (B197)
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

        kept = []                                 # (world, folder, added, changed): I.keep_yours
        self.kept_note = ""                       # where they went, said again by final_check

        def job(progress):
            import lbstadiums
            picked = {}                           # Stadiums > Your world's clubs: the picks stay with a new version
            for w in older:                       # the older version out first, not copied over
                old = os.path.join(self.app.game.livecpk_dir, w)
                picked[w] = (lbstadiums.load_edits(old), lbstadiums.load_game(old))
                progress(_("Taking out the %s you had") % w)
                I.replace_world(self.app.game, ini, w, log=log.append, kept=kept)
            inst = I.Installer(self.app.game, ini, name, log=log.append, replace_lines=repl, comps=comps,
                               progress=lambda d, n, b: progress("%d / %d %s · %s" % (d, n, _("files"), gb(b))))
            rec = inst.run(self.parts, where)
            for w, (edits, game) in picked.items():
                root = os.path.join(self.app.game.livecpk_dir, w)
                if not os.path.isdir(root) or os.path.exists(os.path.join(root, lbstadiums.EDITS)):
                    continue
                if edits:
                    lbstadiums.save_edits(root, edits)
                    log.append("%s: the %d home stadium(s) you picked are kept" % (w, len(edits)))
                hand, auto_on = game
                if hand or auto_on:
                    import json, lbgamestadiums
                    lbstadiums.save_game(root, hand, auto_on)
                    db = os.path.join(root, "common", "etc", "pesdb")
                    try:
                        with open(os.path.join(root, "leaguebuilder-plan.json"), encoding="utf-8") as f:
                            picks = lbgamestadiums.world_picks(
                                bigjson.load(f), lbgamestadiums.confed_of(db, getattr(self.app.project, "base", None)),
                                hand, auto_on)
                        n = lbgamestadiums.write_team_bin(os.path.join(db, "Team.bin"), picks)
                        log.append("%s: the game stadiums you gave the clubs are kept (%d changed)" % (w, n))
                    except (OSError, ValueError) as e:
                        log.append("%s: the game stadiums you gave the clubs could not be put back: %s" % (w, e))
            ini.save(reason="installed %s" % name)     # (here, not in done(): B480 round 2)
            from ..game import Game
            rec["_running"] = Game.running()
            warm_modules_state(self.app.game)
            return rec

        def done(rec):
            clock.stop()
            # a world: world_on follows, and until it is done the world's own modules are not in
            # the game yet. The program stays busy over the lines below, so the header waits
            # instead of saying NOT READY, 2 modules missing, in red for a minute (11.11.)
            switching = bool(rec.get("world"))
            if not switching:
                self.app.busy(False)
            self.app.save_ini(ini, "installed %s" % name, saved=True, running=rec.pop("_running", None))
            self.app.bus.content_changed.emit()
            self.cleanup()
            self.tree.clear()
            self.more.hide()
            self.what.setText(_("%s is installed.") % name)
            self.summary.setText("")
            self.say(_("%s is installed: %d file(s) added, %d replaced (the old ones are kept).")
                     % (name, len(rec["created"]), len(rec["replaced"])), "ok")
            self.kept_note = self.kept_text(kept)
            if self.kept_note:
                self.say(self.kept_note, "warn")
            if rec.get("unmatched"):
                self.say(_("%s is installed, but this world has no competition called %s: pick the "
                           "competition yourself on Game content > Servers (Library > Use it for...).")
                         % (name, ", ".join(rec["unmatched"])), "warn")
            if switching:
                self.app.busy(False)
                self.world_on(rec)

        def failed(tb):
            clock.stop()
            self.app.busy(False)
            self.go.setEnabled(True)
            if denied(self, tb):
                return
            # the error's own words, without "ValueError:" and the like in front (B74)
            why = re.sub(r"^(?:\w+\.)*\w*(?:Error|Exception|WorldThere|WrongGame): ", "", tb.strip().splitlines()[-1])
            error(self, "Import your world", _("The install stopped:") + "\n\n" + why +
                  "\n\n" + _("What was done so far is in Restore points."))
        run_job(job, done, failed, progress=clock.step)

    def ask_update(self, world, up, yours):
        """the box of an Update (update_check ok): True on Update"""
        from PySide6.QtWidgets import QMessageBox
        text = (_("Update %s: %s.") % (world, update_words(up)) + "\n\n" +
                _("Your careers stay: your saves and the world's save folder are not touched, and the version "
                  "you have is replaced by this one, which keeps every club, league, cup and player id a career "
                  "of it holds. What a running career shows of this version's changes is not checked in the "
                  "game; for all that is new, start a new Master League."))
        for extra in (new_comps_text(up), retired_text(up), changed_text(up), renamed_text(up)):
            if extra:
                text += "\n\n" + extra
        text += "\n\n" + yours
        box = QMessageBox(QMessageBox.Question, _("Import your world"), text, QMessageBox.NoButton, self)
        yes = box.addButton(_("Update"), QMessageBox.AcceptRole)
        box.addButton(QMessageBox.Cancel)
        box.setDefaultButton(yes)
        box.exec()
        return box.clickedButton() is yes

    @staticmethod
    def kept_text(kept):
        """where keep_yours put what the person had added to the world or changed in it, one line a
        world ("" when nothing was kept). 16.11.: said only in a banner that final_check's "ready to
        play" replaced 40 s later, and the Ready to play box did not say it -- final_check says it too"""
        return "\n".join(_("%s: %d file(s) you had added or changed are not in the version installed now. "
                           "Nothing was deleted: they are kept in %s") % (w, n_add + n_chg, folder)
                         for w, folder, n_add, n_chg in kept)

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
            warm_modules_state(game)

        def over(_r=None):
            clock.stop()
            # B440 (12.11.): the modules came with this install, so what this game can hold is
            # read again -- the competition counter said "726 / 726" until Mod Studio was
            # started again (the ids past 255 were not counted). B441: and the club lists,
            # Import kits matched 0 clubs of the world just installed
            try:
                B.use_game(game.folder)
                self.app.project.drop_names()
            except Exception:
                pass
            self.app.bus.ini_changed.emit()
            save_note(self, sw)
            # B123 (Vicentico, 17.10.): the installed world's recipe opens as after Put in the game --
            # the tabs (Leagues and the rest) kept showing the world in the game before the zip until
            # Mod Studio was started again. Read in the background: the Modpack's is 132 MB
            run_job(read, done=opened, failed=lambda _tb: opened(None))

        def read(_progress):
            found = self.app.live_recipe(fresh=True)        # B468: the zip's world, not an old copy
            # B419 (12.11.): what final_check reads is read here too. It ran on the GUI thread after
            # the busy bar was gone, and the plan of a big world (the GigaPack's is 130 MB) took 3 s
            # of it: the window stood still at the very end of "Install the world"
            from .. import checks
            try:
                self.ready_rows = (w, checks.ready_check(game, w))
            except Exception:
                self.ready_rows = None
            return found

        def opened(found):
            self.app.busy(False)
            if found and self.app.open_live_world(found, fresh=True):
                # B480 (17.11.2026): the rest on turns of their own -- in the turn of adopt() (the
                # page on screen filled in it) the pages and the box of the end check were 0.55 s
                # of a stopped window with 220,000 players
                next_turn(pages)
            else:
                self.final_check(w)

        def pages():
            self.app.bus.content_changed.emit()
            try:
                self.app.page("Build").refresh()
            except Exception:
                pass
            next_turn(lambda: self.final_check(w))

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
        ready, self.ready_rows = getattr(self, "ready_rows", None), None
        rows = ready[1] if ready and ready[0] == w else checks.ready_check(self.app.game, w)
        bad = [t for lv, t in rows if lv == "err"]
        warn = [t for lv, t in rows if lv == "warn"]
        good = [t for lv, t in rows if lv == "ok"]
        text = "\n".join(["\u2713  " + t for t in good] + ["!  " + t for t in warn] + ["\u2717  " + t for t in bad])
        # what this install kept of the person's files, and where: the banner that said it is
        # replaced below, so the last banner and the box say it again (once: a later check does not)
        kept, self.kept_note = getattr(self, "kept_note", ""), ""
        if bad:
            # the banner stays after the box is closed: its link shows the list again (Novarama,
            # beta 15.10.: "see what to fix -- where?")
            self.fix_text = text + ("\n\n" + kept if kept else "")
            self.say(_('%s is installed, but not ready to play yet: <a href="fix">see what to fix</a>.') % w
                     + ("<br>" + html.escape(kept).replace("\n", "<br>") if kept else ""), "err")
            self.show_fix()
        elif getattr(self, "updating", False):
            # 17.11.2026: an Update -- the careers go on; the old Edit save is the career's, left as it is
            self.say(_("%s is updated and ready to play. Press Start the game and load your career, or start "
                       "a new Master League.") % w + ("\n" + kept if kept else ""), "ok")
            self.what.setText(_("\u2713 Updated: press Start the game and load your career"))
            info(self, _("Ready to play"), text + "\n\n" +
                 _("Press Start the game and load your career: it goes on with this version. For all that is "
                   "new in it, start a new Master League. No Build needed.")
                 + ("\n\n" + kept if kept else ""))
        else:
            self.say(_("%s is ready to play. Press Start the game and start a new Master League.") % w
                     + ("\n" + kept if kept else ""), "ok")
            self.what.setText(_("\u2713 Ready to play: press Start the game and start a new Master League"))
            info(self, _("Ready to play"), text + "\n\n" +
                 _("Press Start the game and start a NEW Master League (an old career does not get the new leagues). "
                   "No Build needed.") + ("\n\n" + kept if kept else ""))
        updated, self.updating = getattr(self, "updating", False), False
        self.edit_check(w, updated)

    def ask_edit(self, update):
        """B197's box: True to move the Edit save aside. An Update keeps it by default (review
        17.11.2026: the box was not asked on an Update at all)"""
        if not update:
            return ask(self, "Move the Edit save aside",
                       _("An Edit save from before this install is in the game's save folder. Made for an older "
                         "version of the world, it can stop a new Master League in the season or leave a club "
                         "without its players, and it hides the new squads in Exhibition and Edit mode.") + "\n\n" +
                       _("Move the Edit save aside") + "?")
        from PySide6.QtWidgets import QMessageBox
        box = QMessageBox(QMessageBox.Question, _("Move the Edit save aside"),
                          _("An Edit save from before this update is in the game's save folder.") + "\n\n" +
                          _("To continue your career: keep it -- your career uses it.") + "\n" +
                          _("For a new Master League with this version: move it aside -- made for the version "
                            "before, it can stop a new Master League in the season or leave a club without its "
                            "players."), QMessageBox.NoButton, self)
        keep = box.addButton(_("Keep it"), QMessageBox.RejectRole)
        move = box.addButton(_("Move it aside"), QMessageBox.AcceptRole)
        box.setDefaultButton(keep)
        box.exec()
        return box.clickedButton() is move

    def edit_check(self, w, update=False):
        """B197 (22.10.): the world's save folder still has the Edit save of its older version. Its
        squads list players this version no longer has: a new Master League on it crashed in the
        season (0x141321d00) or played with a team that lost every match. Build's box says so after
        a Build; a world zip said nothing. update: an Update -- the career goes on with that save"""
        from .. import game as G
        since = getattr(self, "t_install", None)
        if not since or not G.old_edit(since - 5):
            return
        if not self.ask_edit(update):
            return
        try:
            name = G.edit_aside(w)
        except OSError as e:
            if not denied(self, e):                   # a game under Program Files (B43)
                error(self, "Move the Edit save aside", str(e))
            return
        info(self, "Move the Edit save aside",
             _("The Edit save is now %s, in the same folder. The game makes a new one; to get the old one "
               "back, rename it to EDIT00000000.") % name)

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
        # B480: the record of what was installed is read by a worker. A big world's is megabytes
        # (each of its files), and read here it stopped the window after Install and after Make it
        # editable (the exe test of beta4o: refresh -> I.records on the window's thread)
        self._refresh_n = n = getattr(self, "_refresh_n", 0) + 1
        if not self.app.game.ok() or not os.path.isdir(self.app.game.sider_dir):
            self.done.clear()
            return
        sider = self.app.game.sider_dir

        def read(_progress):
            try:
                return bigjson.load_path(I.db_path(sider))
            except (OSError, ValueError):
                return []

        def got(rows):
            if n == self._refresh_n:              # the last refresh asked for: the list as it is now
                self.fill_done(rows)
        run_job(read, got, lambda _tb: got([]))

    def fill_done(self, rows):
        # the rows stay here and each line holds its index (B480, 17.11.2026): a row in the line's
        # data went into Qt as a copy -- a world's row lists every file it put in, 160,000 paths for
        # the GigaPack, each one turned into Qt's own string and back -- 0.86 s of a stopped window
        # at the end of Make it editable in the exe test of beta4p (15 ms a row here, no load at all)
        self.done.clear()
        was, self._done_rows = getattr(self, "_done_rows", None), list(rows)
        if was:
            from .. import letgo
            letgo.drop(was)
            del was
        for i in range(len(rows) - 1, -1, -1):
            r = rows[i]
            t = r.get("time", "")
            when = "%s.%s.%s %s:%s" % (t[6:8], t[4:6], t[0:4], t[9:11], t[11:13]) if len(t) >= 13 else t
            what = ", ".join("%s %s" % (_(KIND.get(k, k)).split(" (")[0].lower(), n) for k, n in r.get("parts", []))
            it = QTreeWidgetItem([r["name"], when])
            it.setData(0, ROW, i)
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
        rows, i = getattr(self, "_done_rows", None) or [], it.data(0, ROW)
        if not isinstance(i, int) or not 0 <= i < len(rows):
            return
        rec = rows[i]
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
