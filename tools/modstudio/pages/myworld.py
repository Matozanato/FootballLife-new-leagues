"""My world (0.2.4, variant A of the mockups, mato 15.10.): one section for your world instead of
Build and edit your world, Import your world and NewLife Database.

    header   MY WORLD; the competitions and new countries of the world in the game against the
             game's limits; Build and install (the Build page's own button)
    cards    every world on disk (livecpk\\_FL26...): the one in the game green, Put in the game on
             the others; Export / Rename / Delete on each; + New world
    tabs     the pages that change the open world (Leagues, Clubs, Players, Kits, Stadiums), Cups
             (the cup windows of Leagues > More); + Add... and More on the right

Nothing here builds, switches, exports, renames, deletes or installs by itself: the buttons call
what the pages already do (Build: build_all, do_on, do_export, new_world; Content folders:
rename_world, delete_world; League packages: add_pack; Import your world: look; NewLife: load).
"""
import fnmatch, json, os, time, zipfile

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (QCheckBox, QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel, QMenu,
                               QPushButton, QScrollArea, QStackedWidget, QToolButton, QVBoxLayout, QWidget)

import leaguebuilder as B
from .. import filecache, installer as I, theme, worlds as WL
from ..i18n import _
from ..ui import ask, can_write, denied, error, info, run_job

PLAN = "leaguebuilder-plan.json"
CID_MAX = B.W.CID_MAX                                  # competitions the game has room for (255)
NEW_COUNTRIES = B.REGION_LAST - B.REGION_FIRST + 1      # regions for new countries (29..127: 99)
CARD_W, CARD_H, NEW_W = 420, 120, 140
KINDS = "world zip (Modpack) · .fl26pack (league package) · NewLife Database (folder or zips)"


# ---- what the cards and the header say -------------------------------------------------------
def world_rows(app):
    """the cards, in order: the world in the game first, then the others on disk newest first, then the open
    world when it is not built yet. Each a dict: world, title (a ready world's pack name), live,
    built, zipped (from Import your world), open (the world the tabs change), when (built),
    exportable, and leagues / clubs when the open recipe says them"""
    g, P = app.game, app.project
    ok = g.ok()
    disk = WL.worlds(g) if ok else []
    live = WL.live(g) if ok else []
    open_w = str(P.recipe.get("world") or "").strip()
    def age(w):
        try:
            return -os.path.getmtime(os.path.join(g.livecpk_dir, w))
        except OSError:
            return 0
    names = sorted(disk, key=lambda w: (w not in live, age(w), w.lower()))
    if open_w and open_w.lower() not in {w.lower() for w in disk}:
        names.append(open_w)
    rows = []
    for w in names:
        built = w in disk
        d = os.path.join(g.livecpk_dir, w) if ok else ""
        zipped = built and I.ready_world(g, w)
        recs = I.installed_as(g.sider_dir, w) if zipped else []
        pack = str(recs[-1].get("name") or "") if recs else ""
        try:
            when = time.strftime("%d.%m. %H:%M", time.localtime(os.path.getmtime(d))) if built else ""
        except OSError:
            when = ""
        r = {"world": w, "title": pack or w, "live": w in live, "built": built, "zipped": zipped,
             "open": w == open_w, "when": when,
             "exportable": built and os.path.isfile(os.path.join(d, I.WORLD_FILE))}
        if r["open"]:                    # Home's numbers of the open world
            r["leagues"] = len(P.recipe.get("leagues") or [])
            r["clubs"] = sum(B.new_club_count(L) for L in P.recipe.get("leagues") or [])
        rows.append(r)
    return rows


def plan_summary(game, world):
    """leagues, new clubs and new countries of a built world, from its leaguebuilder-plan.json
    (worked out again only when the file changes); None without one. A big world's plan takes a
    second to read: called from a worker thread"""
    path = os.path.join(game.livecpk_dir, world, PLAN)

    def make():
        try:
            pl = filecache.json_file(path)      # the one Leagues reads too (B66: not a second 128 MB copy)
        except (OSError, ValueError):
            return None
        leagues = pl.get("leagues") or []
        # the plan keeps a league's clubs of the game by place; new_club_count reads them as a list
        clubs = sum(B.new_club_count(dict(p, game_clubs=list(B.game_places(p).values())))
                    for p in leagues + (pl.get("others") or []))
        regions = {p.get("region") for p in leagues
                   if isinstance(p.get("region"), int) and p["region"] >= B.REGION_FIRST}
        return {"leagues": len(leagues), "clubs": clubs, "regions": len(regions)}
    return filecache.by_files("myworld-plan", [path], make)


def competitions(project):
    """how many competitions the world in the game has (the game's tables without one): the rows
    of Leagues > More > Competition IDs (leaguebuilder.competition_ids); None when unknown"""
    worlds = project.world_tables()
    db = worlds[0] if worlds else project.base
    if not db:
        return None
    try:
        return filecache.by_files("myworld-comps", [os.path.join(db, "CompetitionRegulation.bin")],
                                  lambda: len(B.competition_ids(db)))
    except (OSError, ValueError):
        return None


def info_text(r):
    """the dim line of a card: only what is known"""
    bits = [r["world"]] if r["title"] != r["world"] else []
    if r.get("leagues") is not None:        # B70: "1 leagues"
        bits.append(_("%d league") % 1 if r["leagues"] == 1 else _("%d leagues") % r["leagues"])
    if r.get("clubs") is not None:
        bits.append(_("%d new club") % 1 if r["clubs"] == 1 else _("%d new clubs") % r["clubs"])
    bits.append(_("built %s") % r["when"] if r["built"] and r["when"] else "" if r["built"] else _("not built yet"))
    if r["open"] and not r["live"]:
        bits.append(_("open here"))          # the tabs below change this one
    return " · ".join(b for b in bits if b)


def kind_of(path):
    """what + Add... was given: ("pack", path) a league package, ("newlife", folder) the NewLife
    Database (a release folder, or the folder of its NewLife-....zip parts), ("world", path) a
    world zip or folder, ("newlife-zip", path) a whole release packed in one zip (to unpack first),
    ("mod", path) anything else (Import your world looks inside); ("", path) when it is not there"""
    path = os.path.normpath(path.rstrip("\\/")) if path else ""
    if not path or not os.path.exists(path):
        return "", path
    if os.path.isdir(path):
        from .. import newlife as N
        if N.find(path):
            return "newlife", path
        for top, dirs, files in os.walk(path):
            if I.WORLD_FILE in files or any(WL.is_world(d) for d in dirs):
                return "world", path
            if top.count(os.sep) - path.count(os.sep) >= 3:
                dirs[:] = []
        return "mod", path
    low = path.lower()
    if low.endswith(".fl26pack"):
        return "pack", path
    if fnmatch.fnmatch(os.path.basename(low), "newlife-*.zip"):
        return "newlife", os.path.dirname(path)
    if low.endswith(".zip"):
        try:
            with zipfile.ZipFile(path) as z:
                names = [n.replace("\\", "/") for n in z.namelist()]
        except (zipfile.BadZipFile, OSError):
            return "mod", path
        base = {n.rsplit("/", 1)[-1].lower() for n in names}
        if {"newlife.json", "clubs.csv", "players.csv"} <= base:
            return "newlife-zip", path            # a whole release in one zip: the page reads folders
        if I.WORLD_FILE in base or any(WL.is_world(seg) for n in names for seg in n.split("/")[:-1]):
            return "world", path
    return "mod", path


# ---- the widgets -----------------------------------------------------------------------------
def unstick(b):
    """B70: a menu button (Cups) whose menu item opened a window kept the look of the mouse over
    it -- the window took the mouse, the button never heard it leave -- so Cups stayed lit on the
    page opened next (Build details). Unless the mouse is on it, it is not under the mouse."""
    if b.underMouse() and not b.rect().contains(b.mapFromGlobal(QCursor.pos())):
        b.setAttribute(Qt.WA_UnderMouse, False)
        b.update()


class SubTabs(QStackedWidget):
    """the pages of My world, one at a time, under a row of tab buttons; League packages, Import a
    world zip and NewLife Database have no tab (More, + Add...): none is lit"""

    def __init__(self):
        super().__init__()
        self.buttons = {}                    # page holder -> its tab button

    def setCurrentWidget(self, w):
        super().setCurrentWidget(w)
        self.sync()

    def sync(self):
        for h, b in self.buttons.items():
            b.setChecked(h is self.currentWidget())


class WheelRow(QScrollArea):
    """the row of world cards: the mouse wheel moves it left and right (it has no up and down)"""
    def wheelEvent(self, e):
        d = e.angleDelta()
        step = d.y() or d.x()
        if not step:
            return super().wheelEvent(e)
        bar = self.horizontalScrollBar()
        bar.setValue(bar.value() - step)
        e.accept()


class WorldCard(QFrame):
    """one world: IN THE GAME NOW on green; Active / Activate, Export, Rename, Delete"""

    def __init__(self, sec, r):
        super().__init__()
        self.r, self.world = r, r["world"]
        self.setObjectName("worldlive" if r["live"] else "worldcard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedSize(CARD_W, CARD_H)
        v = QVBoxLayout(self)
        v.setContentsMargins(12, 8, 10, 9)
        v.setSpacing(0)
        top = QHBoxLayout()
        top.setSpacing(8)
        txt = QVBoxLayout()
        txt.setSpacing(1)
        eye = QLabel(("● " + _("IN THE GAME NOW")) if r["live"] else
                     _("NOT IN THE GAME") if r["built"] else _("NOT BUILT YET"))
        eye.setObjectName("worldeyebrow")
        self.eyebrow = eye
        eye.setProperty("state", "live" if r["live"] else "")
        theme.caps(eye)
        txt.addWidget(eye)
        nr = QHBoxLayout()
        nr.setSpacing(8)
        self.name = QLabel()
        self.name.setObjectName("worldname")
        self.name.setToolTip(r["world"])
        nr.addWidget(self.name)
        if r["zipped"]:
            tag = theme.caps(QLabel(_("From zip")))
            tag.setObjectName("srctag")
            tag.setProperty("state", "zip")
            tag.setToolTip(_("A ready world, put in with Import your world (a world zip)"))
            nr.addWidget(tag, 0, Qt.AlignVCenter)
        nr.addStretch(1)
        txt.addLayout(nr)
        self.info = QLabel(info_text(r))
        self.info.setObjectName("cardnote")
        txt.addWidget(self.info)
        top.addLayout(txt, 1)
        v.addLayout(top)
        v.addStretch(1)
        bot = QHBoxLayout()
        bot.setSpacing(6)
        bot.addStretch(1)
        # every card says it: Active (green, the world in the game now) or Activate -- testers of the
        # 0.2.4 beta did not know which world was on (mato 16.10.)
        self.go = QPushButton(("● " + _("Active")) if r["live"] else ("▶  " + _("Activate")))
        self.go.setObjectName("go")
        self.go.setProperty("state", "live" if r["live"] else "")
        if r["live"]:
            self.go.setEnabled(False)
            self.go.setToolTip(_("This is the world in the game now"))
        elif r["built"]:
            self.go.setCursor(Qt.PointingHandCursor)
            self.go.setToolTip(_("Switch this world on in sider.ini (the one in the game now goes out; it stays "
                                 "on disk). Start a new Master League with it."))
            self.go.clicked.connect(lambda: sec.put_in_game(self.world))
        else:
            self.go.setEnabled(False)
            self.go.setToolTip(_("Not built yet: Build and install first"))
        bot.addWidget(self.go)
        self.export = QPushButton("⇪ " + _("Export..."))
        self.export.setObjectName("blue")
        self.export.clicked.connect(lambda: sec.export(self.world))
        if not r["exportable"]:
            self.export.setEnabled(False)
            self.export.setToolTip(_("Not built yet: Build and install first"))
        else:
            self.export.setToolTip(_("One .zip of this world for another PC (Import your world installs it there)"))
        self.rename = QPushButton(_("Rename"))
        self.rename.clicked.connect(lambda: sec.rename(self.world))
        self.delete = QPushButton(_("Delete"))
        self.delete.setObjectName("danger")
        self.delete.clicked.connect(lambda: sec.delete(self.world))
        if r["live"]:
            # Content folders refuses the world in the game too (worlds.delete never takes it out)
            self.delete.setEnabled(False)
            self.delete.setToolTip(_("%s is the world in the game now. Put another world in the game first, "
                                     "then you can delete it.") % self.world)
        elif not r["built"]:
            self.delete.setEnabled(False)
            self.delete.setToolTip(_("Nothing of it is on disk yet"))
        else:
            self.delete.setToolTip(_("Out of the game and off the disk; kept in Restore points"))
        if not r["built"]:
            self.rename.setToolTip(_("The name of a world not built yet: World name and file"))
        for b in (self.export, self.rename, self.delete):
            bot.addWidget(b)
        v.addLayout(bot)
        self.set_title()

    def set_title(self):
        room = CARD_W - 40 - (90 if self.r["zipped"] else 0)
        self.name.setText(self.name.fontMetrics().elidedText(self.r["title"], Qt.ElideRight, max(80, room)))

    def set_info(self, summ):
        """the leagues and new clubs of its plan, once they are read"""
        if summ and self.r.get("leagues") is None:
            self.r.update(leagues=summ["leagues"], clubs=summ["clubs"])
            self.info.setText(info_text(self.r))


class DropZone(QFrame):
    """the dashed box of + Add...: a file or folder dropped on it"""

    def __init__(self, on_path):
        super().__init__()
        self.on_path = on_path
        self.setObjectName("dropzone")
        self.setAcceptDrops(True)

    def _hot(self, on):
        self.setProperty("hot", bool(on))
        theme.repolish(self)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self._hot(True)

    def dragLeaveEvent(self, e):
        self._hot(False)

    def dropEvent(self, e):
        self._hot(False)
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.toLocalFile()]
        if paths:
            self.on_path(paths[0])


class AddDialog(QDialog):
    """+ Add...: one window for a world zip (Modpack), a league package and the NewLife Database;
    it says what it found, and Add hands it to the page that already does it"""

    def __init__(self, sec, name):
        super().__init__(sec)
        self.sec, self.app = sec, sec.app
        self.path, self.kind, self.where, self.man = None, "", "", None
        self.setWindowTitle(_("Add to %s") % name)
        self.setObjectName("adddialog")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setMinimumWidth(640)
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 18, 22, 18)
        v.setSpacing(10)
        head = theme.caps(QLabel(_("Add to %s") % name))
        head.setObjectName("pagetitle")
        v.addWidget(head)
        self.drop = DropZone(self.pick)
        dv = QVBoxLayout(self.drop)
        dv.setContentsMargins(20, 22, 20, 20)
        dv.setSpacing(14)
        r = QHBoxLayout()
        r.addStretch(1)
        r.addWidget(QLabel(_("Drop it here or")))
        b1 = QPushButton(_("Choose a file..."))
        b1.clicked.connect(self.pick_file)
        b2 = QPushButton(_("Choose a folder..."))
        b2.clicked.connect(self.pick_folder)
        r.addWidget(b1)
        r.addWidget(b2)
        r.addStretch(1)
        dv.addLayout(r)
        k = QLabel(_(KINDS))
        k.setObjectName("cardnote")
        k.setAlignment(Qt.AlignCenter)
        dv.addWidget(k)
        v.addWidget(self.drop)
        self.found = QLabel("")
        self.found.setObjectName("found")
        self.found.setWordWrap(True)
        self.found.hide()
        v.addWidget(self.found)
        self.ticks_box = QWidget()
        self.ticks = QVBoxLayout(self.ticks_box)
        self.ticks.setContentsMargins(0, 0, 0, 0)
        self.ticks.setSpacing(6)
        self.ticks_box.hide()
        v.addWidget(self.ticks_box)
        self.after = QLabel("")
        self.after.setObjectName("cardnote")
        self.after.setWordWrap(True)
        self.after.setTextFormat(Qt.RichText)
        self.after.hide()
        v.addWidget(self.after)
        bb = QHBoxLayout()
        bb.addStretch(1)
        cancel = QPushButton(_("Cancel"))
        cancel.clicked.connect(self.reject)
        self.add = QPushButton(_("Add"))
        self.add.setObjectName("blue")
        self.add.setStyleSheet("padding: 6px 22px;")
        self.add.setEnabled(False)
        self.add.clicked.connect(self.go)
        bb.addWidget(cancel)
        bb.addWidget(self.add)
        v.addLayout(bb)

    def pick_file(self):
        p, _f = QFileDialog.getOpenFileName(self, _("Choose a file..."), self.app.settings.get("add_dir", ""),
                                            _("World zip, league package, NewLife") + " (*.zip *.fl26pack *.7z);;"
                                            + _("All files") + " (*)")
        if p:
            self.pick(p)

    def pick_folder(self):
        p = QFileDialog.getExistingDirectory(self, _("Choose a folder..."), self.app.settings.get("add_dir", ""))
        if p:
            self.pick(p)

    def pick(self, path):
        """what it is, in one green line; a league package's leagues to tick"""
        self.path = path
        self.kind, self.where = kind_of(path)
        self.app.settings["add_dir"] = os.path.dirname(os.path.normpath(path))
        while self.ticks.count():
            w = self.ticks.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        self.ticks_box.hide()
        self.after.hide()
        self.man = None
        base = os.path.basename(self.where or path)
        state, text = "", ""
        if self.kind == "pack":
            import lbpackage as K
            try:
                self.man = K.manifest(path)
            except K.Error as e:
                self.kind, state, text = "", "err", _("Not a league package that can be read: %s") % e
            else:
                Ls = self.man.get("leagues") or []
                text = "✓ " + _('Found: league package "%s" (%d leagues, %d clubs)') % (
                    self.man.get("name") or base, len(Ls), sum(int(L.get("clubs") or 0) for L in Ls))
                for L in Ls:
                    c = QCheckBox("%s — %s, %d %s" % (L["name"], L.get("country", ""), int(L.get("clubs") or 0),
                                                           _("clubs")))
                    c.setChecked(True)
                    c.name = L["name"]
                    c.toggled.connect(self.count)
                    self.ticks.addWidget(c)
                self.ticks_box.setVisible(bool(Ls))
                same = (self.man.get("name") or "").strip().casefold()
                old = [p for p in K.packs(self.app.project.recipe).values()
                       if (p.get("name") or "").strip().casefold() == same]
                self.replaces = bool(old)
                self.count()
        elif self.kind == "world":
            text = "✓ " + _("Found: a world zip, %s. Add opens Import your world with it; Install puts it "
                                 "in the game as a world of its own.") % base
        elif self.kind == "newlife":
            from .. import newlife as N
            parts = N.parts_in(N.find(self.where) or self.where)
            text = "✓ " + (_("Found: NewLife Database, %d parts in %s") % (len(parts), self.where) if parts else
                                _("Found: NewLife Database in %s") % self.where) + ". " + \
                _("Add opens it on the NewLife page: pick its leagues there.")
        elif self.kind == "newlife-zip":
            self.kind, state = "", "err"
            text = _("%s is the NewLife Database in one zip: unpack it, then Choose a folder... on what "
                     "came out.") % base
        elif self.kind == "mod":
            text = _("%s is not a world zip, a league package or the NewLife Database. Add opens Import your "
                     "world, which looks inside it.") % base
        else:
            state, text = "err", _("%s is not there.") % path
        self.found.setText(text)
        self.found.setProperty("state", state)
        theme.repolish(self.found)
        self.found.show()
        self.add.setEnabled(bool(self.kind))

    def picked(self):
        return [self.ticks.itemAt(i).widget().name for i in range(self.ticks.count())
                if isinstance(self.ticks.itemAt(i).widget(), QCheckBox) and self.ticks.itemAt(i).widget().isChecked()]

    def count(self):
        """Competitions after adding: the world in the game's, and one more for each league ticked"""
        n = competitions(self.app.project)
        if n is None:
            self.after.hide()
            return
        after = n + len(self.picked())
        colour = theme.DANGER if after > CID_MAX else theme.TEXT
        text = _("Competitions after adding: %s") % ('<b style="color:%s">%d / %d</b>' % (colour, after, CID_MAX))
        text += " · " + _("nothing reaches the game until Build and install")
        if getattr(self, "replaces", False):
            text += "<br>" + _("Your world has this package already: Add puts this version in its place.")
        self.after.setText(text)
        self.after.show()
        self.add.setEnabled(bool(self.picked()))

    def go(self):
        kind, path, where = self.kind, self.path, self.where
        if kind == "pack":
            leagues = self.picked()
            if not leagues:
                error(self, "Add a league package", _("Tick at least one league."))
                return
            self.accept()
            packs = self.app.page("Packages")
            if packs.add_pack(path, leagues=leagues):
                self.app.open_page("Leagues")
                self.app.status(packs.banner.text())
        elif kind == "newlife":
            self.accept()
            nl = self.app.page("NewLife")
            if nl.rel is None:
                self.app.settings["newlife"] = where          # NewLife.shown() reads it from there
                self.app.open_page("NewLife")
            else:
                self.app.open_page("NewLife")
                nl.load(where)
        elif kind in ("world", "mod"):
            self.accept()
            self.app.open_page("Install")
            self.app.page("Install").look(path)


class MyWorld(QWidget):
    """the section: header, world cards, tabs; tabs = [(name, holder)] with a tab, inside = the
    same for the pages reached from More and + Add..."""

    def __init__(self, app, tabs, inside):
        super().__init__()
        self.app = app
        self.setObjectName("page")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.cards = []
        self._progress = ""
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        v.addWidget(self._head())
        v.addWidget(self._cards())
        v.addWidget(self._tabrow(tabs))
        self.tabs = SubTabs()
        for n, h in tabs + inside:
            self.tabs.addWidget(h)
            if n in self.tab_btn:
                self.tabs.buttons[h] = self.tab_btn[n]
        self.tabs.sync()                    # the first page is open without a setCurrentWidget
        v.addWidget(self.tabs, 1)
        self._stale = True
        self._seen = None
        self._soon = QTimer(self, singleShot=True, interval=300, timeout=self.refresh_if_shown)
        for sig in (app.bus.ini_changed, app.bus.content_changed, app.bus.game_changed):
            sig.connect(self.later)
        app.project.changed.connect(self.recipe_changed)
        # the Build button follows the Build page's (off for a ready world, while it builds)
        QTimer(self, interval=1500, timeout=lambda: self.isVisible() and self.update_bar()).start()

    # ---- building it ----
    def _head(self):
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(18, 8, 14, 4)
        h.setSpacing(18)
        t = theme.caps(QLabel(_("My world")))
        t.setObjectName("pagetitle")
        h.addWidget(t)
        # Xxspedd (17.10., beta): the row of world cards takes a lot of room -- it folds away and
        # stays folded across starts; the world in the game is still named in the header above
        self.fold = QToolButton()
        self.fold.setObjectName("fold")
        self.fold.setCursor(Qt.PointingHandCursor)
        self.fold.setAutoRaise(True)
        self.fold.clicked.connect(lambda: self.fold_cards(not self.cards_area.isHidden()))
        h.addWidget(self.fold, 0, Qt.AlignVCenter)
        h.addStretch(1)
        self.c_comps = QLabel()
        self.c_comps.setObjectName("counter")
        self.c_comps.setToolTip(_("Competitions (leagues and cups) of the world in the game; the game has room "
                                  "for %d. Leagues > More > Competition IDs lists them.") % CID_MAX)
        self.c_regions = QLabel()
        self.c_regions.setObjectName("counter")
        self.c_regions.setToolTip(_("Countries the world in the game adds to the game's own; there is room for %d.")
                                  % NEW_COUNTRIES)
        self.note = QLabel()
        self.note.setObjectName("mlnote")
        self.note.setToolTip(_("A career saved before keeps the world it started with: after Build and install "
                               "or Activate, start a new Master League."))
        # one Build and install button only, on the Build tab (mato 16.10.: three of them on one screen
        # and testers pressed the wrong one); here the open world's state in a few words
        self.world_state = QLabel()
        self.world_state.setObjectName("cardnote")
        # B85 (mato 17.10.): a ready world from a zip is changed in place, under its own name
        self.b_edit = QPushButton(_("Make it editable..."))
        self.b_edit.setObjectName("blue")
        self.b_edit.setToolTip(_("Build is off for a world that came ready in a zip. This makes it a world you "
                                 "can change and Build, in place and under its own name; all of it is "
                                 "copied first (Restore points)."))
        self.b_edit.clicked.connect(self.make_editable)
        self.b_edit.hide()
        for x in (self.c_comps, self.c_regions, self.note, self.b_edit, self.world_state):
            h.addWidget(x, 0, Qt.AlignVCenter)
        self.set_counter(self.c_comps, "Competitions", None, CID_MAX)
        self.set_counter(self.c_regions, "New countries", None, NEW_COUNTRIES)
        self.update_note()
        return w

    def _cards(self):
        sa = WheelRow()
        sa.setWidgetResizable(True)
        sa.setFrameShape(QScrollArea.NoFrame)
        sa.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        sa.setStyleSheet("QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; }")
        inner = QWidget()
        self.row = QHBoxLayout(inner)
        self.row.setContentsMargins(18, 4, 18, 0)
        self.row.setSpacing(12)
        self.row.addStretch(1)
        sa.setWidget(inner)
        sa.setFixedHeight(CARD_H + 4 + 12)          # the cards, and a scroll bar when there are many
        self.cards_area = sa
        self.fold_cards(bool(self.app.settings.get("cards_folded")), keep=False)
        return sa

    def fold_cards(self, folded, keep=True):
        """hide (folded) or show the row of world cards; keep: remember it in the settings"""
        self.cards_area.setHidden(folded)
        self.fold.setText(("▸  " if folded else "▾  ") + _("Worlds"))
        self.fold.setToolTip(_("Show the world cards") if folded else _("Hide the world cards to make room"))
        if keep:
            self.app.settings["cards_folded"] = folded
            try:
                self.app.save_settings()
            except Exception:
                pass

    def _tabrow(self, tabs):
        wrap = QWidget()
        wv = QVBoxLayout(wrap)
        wv.setContentsMargins(12, 0, 12, 0)
        w = QWidget()
        w.setObjectName("subtabs")
        w.setAttribute(Qt.WA_StyledBackground, True)
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        self.tab_btn = {}
        from modstudio.app import TAB_TITLE
        for n, _h in tabs:
            b = QPushButton(_(TAB_TITLE.get(n) or self.app.pages[n].title))
            b.setObjectName("subtab")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setAccessibleName(b.text())
            b.clicked.connect(lambda _c=False, p=n: self.app.open_page(p))
            self.tab_btn[n] = b
            h.addWidget(b, 0, Qt.AlignBottom)
        # the cups are windows of Leagues > More, not a page: Cups opens them from here
        cups = QToolButton()
        cups.setObjectName("subtab")
        cups.setText(_("Cups"))
        cups.setAccessibleName(_("Cups"))
        cups.setPopupMode(QToolButton.InstantPopup)
        cups.setCursor(Qt.PointingHandCursor)
        m = QMenu(cups)
        for label, name in (("Pre-season cups", "preseason"), ("Cups of our countries", "our_cups"), ("Cups of the game's countries", "game_cups"),
                            ("Competition names", "competition_names")):
            m.addAction(_(label)).triggered.connect(lambda _c=False, n=name: self.cup_window(n))
        cups.setMenu(m)
        self.cups = cups
        h.addWidget(cups, 0, Qt.AlignBottom)
        h.addStretch(1)
        self.add_btn = QPushButton("+ " + _("Add..."))
        self.add_btn.setObjectName("blue")
        self.add_btn.setStyleSheet("padding: 6px 16px;")
        self.add_btn.setToolTip(_("A world zip (Modpack), a league package (.fl26pack) or the NewLife Database"))
        self.add_btn.clicked.connect(self.add)
        more = QToolButton()
        more.setText(_("More") + "  ▾")
        more.setPopupMode(QToolButton.InstantPopup)
        mm = QMenu(more)
        for label, page in (("League packages", "Packages"),
                            ("Import a world zip", "Install"), ("NewLife Database", "NewLife")):
            mm.addAction(_(label)).triggered.connect(lambda _c=False, p=page: self.app.open_page(p))
        mm.addSeparator()
        mm.addAction(_("Content folders")).triggered.connect(self.content_folders)
        more.setMenu(mm)
        self.more = more
        h.addWidget(self.add_btn, 0, Qt.AlignVCenter)
        h.addSpacing(4)
        h.addWidget(more, 0, Qt.AlignVCenter)
        wv.addWidget(w)
        wrap.setContentsMargins(0, 0, 0, 4)
        return wrap

    # ---- now ----
    def set_counter(self, label, cap, n, limit):
        over = n is not None and n > limit
        label.setText('<span style="color:%s; font-size:7pt;">%s</span>&nbsp;&nbsp;<b style="color:%s">%s / %d</b>'
                      % (theme.SUBTLE, _(cap).upper(), theme.DANGER if over else theme.TEXT,
                         "—" if n is None else n, limit))

    def update_note(self):
        if hasattr(self, "b_edit"):
            self.b_edit.setVisible(bool(getattr(self, "_open_zipped", False)) and not self._progress)
        if self._progress:
            self.note.setText(self._progress)
            self.note.setStyleSheet("color: %s;" % theme.ACCENT)
        elif getattr(self, "_open_zipped", False):
            # the open world came from a zip: the tabs change its recipe, but no Build puts that in
            # the game yet (0.2.5: apply the change in place) -- said here, over every tab
            self.note.setText("⚠ " + _("a world from a zip: changes made here do not reach the game yet"))
            self.note.setStyleSheet("")
        else:
            self.note.setText("⚠ " + _("changes need a new Master League"))
            self.note.setStyleSheet("")

    def update_bar(self, progress=None):
        """the world's state as the Build page says it; progress: the build's time and step, "" when over"""
        if progress is not None:
            self._progress = progress
            self.update_note()
        b = self.app.pages.get("Build")
        if b is not None and hasattr(b, "state"):
            self.world_state.setText(b.state.text().split("   ·   ")[0])
            self.world_state.setToolTip(b.state.text().replace("   ·   ", "\n"))

    def later(self, *_a):
        self._stale = True
        self._soon.start()

    def recipe_changed(self):
        """a change of the open world: the cards again only when it is another world (or its size)"""
        r = self.app.project.recipe
        seen = (id(r), r.get("world"), len(r.get("leagues") or []))
        if seen != self._seen:
            self.later()

    def refresh_if_shown(self):
        if self.isVisible():
            self.refresh()

    def shown(self):
        if self._stale:
            self.refresh()
        self.update_bar()
        for b in (self.cups, self.more):
            unstick(b)

    def cup_window(self, name):
        """a window of Leagues > More from Cups; the button lets go of its lit look after it"""
        try:
            getattr(self.app.page("NewLeagues"), name)()
        finally:
            unstick(self.cups)

    def refresh(self):
        """the cards and the counts, from what is on disk now"""
        self._stale = False
        r = self.app.project.recipe
        self._seen = (id(r), r.get("world"), len(r.get("leagues") or []))
        rows = world_rows(self.app)
        self._open_zipped = any(x["open"] and x["zipped"] for x in rows)
        self.update_note()
        while self.row.count():
            it = self.row.takeAt(0)
            if it.widget() is not None:
                it.widget().deleteLater()
        self.cards = []
        for x in rows:
            c = WorldCard(self, x)
            self.cards.append(c)
            self.row.addWidget(c)
        nw = QPushButton("+ " + _("New world"))
        nw.setObjectName("newworld")
        nw.setFixedSize(NEW_W, CARD_H)
        nw.setCursor(Qt.PointingHandCursor)
        nw.setToolTip(_("An empty world of your own (File > New world), then add its leagues"))
        nw.clicked.connect(lambda: self.app.page("Build").new_world())
        self.new_world = nw
        self.row.addWidget(nw)
        self.row.addStretch(1)
        if getattr(self, "_renaming", None):
            self.hold_cards()                         # a rename still runs (B66)
        self.set_counter(self.c_comps, "Competitions", competitions(self.app.project), CID_MAX)
        live = [x["world"] for x in rows if x["live"]]
        if not live:
            self.set_counter(self.c_regions, "New countries", None, NEW_COUNTRIES)
        self.update_bar()
        # the plans of the built worlds: their leagues and clubs, the live one's countries
        g = self.app.game
        want = [x["world"] for x in rows if x["built"] and (x.get("leagues") is None or x["live"])]
        if not want:
            return

        def done(got):
            for c in self.cards:
                if c.world in got:
                    c.set_info(got[c.world])
            if live and live[0] in got:
                s = got[live[0]]
                self.set_counter(self.c_regions, "New countries", s["regions"] if s else None, NEW_COUNTRIES)
        run_job(lambda progress: {w: plan_summary(g, w) for w in want}, done, lambda tb: None)

    # ---- the buttons ----
    def make_editable(self):
        """B85: the open world, a ready world from a zip, becomes one Build may change -- in place,
        under its own name (worlds.make_editable: all of it into a world backup first). Its recipe
        is read again from the plan it carries; a copy of the recipe open before stays next to it
        (<world>.json.before-edit)"""
        title = _("Make it editable")
        g, project = self.app.game, self.app.project
        w = project.recipe.get("world") or ""
        if not I.ready_world(g, w):
            return
        run_g, run_s = g.running()
        if run_g or run_s:
            error(self, title, _("Close the game first: it has the world's files open."))
            return
        if project.base is None:
            error(self, title, _("no game tables -- Settings > Unpack the game's tables"))
            return
        if not ask(self, title, _(
                "%s came ready in a zip. Make it a world you can change and Build?\n\n"
                "It stays where it is, under its own name. All of it is copied first: Restore points > "
                "Put this copy back makes it the ready world again.\n\n"
                "After a Build of it, start a new Master League.") % w):
            return
        if not can_write(self, g):
            return
        try:
            project.autosave()                    # the recipe open now keeps its changes
        except Exception:
            pass
        copies, base = project.copies_dir(), project.base

        def job(progress):
            folder = WL.make_editable(g, w)
            with open(os.path.join(g.livecpk_dir, w, "leaguebuilder-plan.json"), encoding="utf-8") as f:
                rec = B.recipe_from_plan(json.load(f), base)
            os.makedirs(copies, exist_ok=True)
            kept = os.path.join(copies, w + ".json")
            if os.path.exists(kept):
                os.replace(kept, kept + ".before-edit")
            with open(kept + ".tmp", "w", encoding="utf-8") as f:
                json.dump(rec, f, indent=1, ensure_ascii=False)
            os.replace(kept + ".tmp", kept)
            return folder, kept

        def done(r):
            self.app.busy(False)
            filecache.forget_under(os.path.join(g.livecpk_dir, w))
            folder, kept = r
            try:
                project.open(kept, copy=True)
                self.app.settings["last_recipe"] = kept
            except Exception as e:
                error(self, title, str(e))
            self.app.bus.ini_changed.emit()
            self.app.bus.content_changed.emit()
            self.refresh()
            try:
                self.app.page("Build").refresh()  # its Build buttons were off for the ready world
            except Exception:
                pass
            info(self, title, _("%s can be changed now. When your changes are done, Build it, then start a "
                                "new Master League.\n\nThe copy of it as it came: Restore points.") % w)

        def failed(tb):
            self.app.busy(False)
            if not denied(self, tb):
                error(self, title, _("It stopped, the world was not changed:") + "\n\n" + str(tb).strip().splitlines()[-1])
        self.app.busy(True)
        run_job(job, done, failed)

    def card_title(self):
        """the name + Add... adds to: the open world's card title (a ready world's pack name)"""
        w = self.app.project.recipe.get("world") or ""
        for c in self.cards:
            if c.world == w:
                return c.r["title"]
        return w

    def put_in_game(self, w):
        """Put in the game: the Build page's 3. Switch it on, for this world; then the world's
        recipe opens as at a start (the tabs change the world in the game)"""
        if not self.app.page("Build").do_on(w):
            return
        if WL.live(self.app.game) != [w]:
            self.app.open_page("Build")              # its log says why
            return
        note = self.app.open_live_world()
        self.app.status(note or _("%s is in the game now. Start a new Master League with it.") % w)
        self.refresh()

    def export(self, w):
        self.app.page("Build").do_export(w)

    def rename(self, w):
        if not any(c.world == w and c.r["built"] for c in self.cards):
            self.app.open_page("NewLeagues")         # not built: the name is the open world's own
            return
        # B66: the rename runs in the background; the cards wait (their buttons off) until it is over
        def over(new):
            self._renaming = None
            if new:
                self.app.status(_("%s is now %s.") % (w, new))
            self.refresh()
        self._renaming = w
        self.hold_cards()
        if not self.app.page("Roots").rename_world(w, done=over):
            self._renaming = None
            self.hold_cards()

    def hold_cards(self):
        """while a world is renamed: every card's buttons off, the card being renamed says so"""
        w = getattr(self, "_renaming", None)
        for c in self.cards:
            c.setEnabled(not w)
            if w and c.world == w:
                c.info.setText(_("Renaming %s...") % w)
            elif not w:
                c.info.setText(info_text(c.r))

    def delete(self, w):
        if self.app.page("Roots").delete_world(w):
            self.app.status(_("%s is deleted. Restore points > Put this copy back brings it back.") % w)
        self.refresh()

    def add(self):
        AddDialog(self, self.card_title()).exec()

    def content_folders(self):
        self.app.open_page("Roots")
        r = self.app.pages.get("Roots")
        if r is not None and hasattr(r, "show_worlds"):
            r.show_worlds.setChecked(True)
