"""League packages: a modder saves leagues of the recipe as one .fl26pack file; anybody adds that
file to their own recipe and builds.  The package carries no ids -- those are given out at Build,
from what each person's game has -- and faces are moved to their players there (lbpackage.py)."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                               QLineEdit, QListWidget, QListWidgetItem, QPlainTextEdit, QPushButton,
                               QSplitter, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

import lbpackage as K
from ..i18n import _
from ..ui import hint, row, ask, error, info, section, run_job
from .builder import BuilderPage

FILTER = "League packages (*.fl26pack);;All files (*.*)"


def store():
    from modstudio.app import APPDIR
    return os.path.join(APPDIR, "packs")


class MakeDialog(QDialog):
    def __init__(self, parent, recipe, last):
        super().__init__(parent)
        self.setWindowTitle(_("Make a league package"))
        self.setMinimumWidth(560)
        v = QVBoxLayout(self)
        v.addWidget(hint(_("Everything a person needs to add these leagues to their game: the leagues, club "
                           "names, logos and crests, player changes and faces. Ids are given out when they "
                           "build, so it works next to whatever else they have.")))
        f = QFormLayout()
        self.name = QLineEdit(last.get("name", ""))
        self.author = QLineEdit(last.get("author", ""))
        self.version = QLineEdit(last.get("version", "1.0"))
        self.version.setFixedWidth(100)
        self.desc = QPlainTextEdit(last.get("description", ""))
        self.desc.setFixedHeight(80)
        f.addRow(_("Name"), self.name)
        f.addRow(_("Author"), self.author)
        f.addRow(_("Version"), self.version)
        f.addRow(_("Description"), self.desc)
        v.addLayout(f)
        v.addWidget(section("Leagues"))
        every, none = QPushButton(_("Select all")), QPushButton(_("Select none"))
        every.clicked.connect(lambda: self.tick(Qt.Checked))
        none.clicked.connect(lambda: self.tick(Qt.Unchecked))
        v.addWidget(row(every, none))
        self.leagues = QListWidget()
        for L in recipe.get("leagues", []):
            it = QListWidgetItem("%s   (%s, %d %s)" % (L["name"], L.get("country", ""), int(L.get("clubs", 0)),
                                                       _("clubs")))
            it.setData(Qt.UserRole, L["name"])
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if not L.get("pack") else Qt.Unchecked)
            if L.get("pack"):
                it.setToolTip(_("came from the package %s") % L["pack"])
            self.leagues.addItem(it)
        v.addWidget(self.leagues, 1)
        e = recipe.get("edits") or {}
        n = len(e.get("leagues") or {}) + len(e.get("clubs") or {}) + \
            sum(1 for k in (recipe.get("players") or {}) if k.isdigit())
        self.edits = QCheckBox(_("Also my changes to the game's own leagues, clubs and players (%d)") % n)
        self.edits.setEnabled(n > 0)
        v.addWidget(self.edits)
        v.addWidget(section("What goes in"))
        labels = {"squads": _("Squads (every player change on these clubs)"),
                  "faces": _("Player faces and portraits"),
                  "crests": _("Crests and league logos"),
                  "managers": _("Managers"),
                  "kits": _("Kit colours"),
                  "kitfiles": _("Kits (the Kit Server kits of the clubs)"),
                  "scoreboards": _("Scoreboards (the Scoreboard Server scoreboard of each league)"),
                  "stadiums": _("Home stadiums (the Stadium Server line, not the stadium itself)")}
        self.parts = {}
        for k in K.PARTS:
            b = self.parts[k] = QCheckBox(labels[k])
            b.setChecked(True)
            v.addWidget(b)
        self.parts["squads"].setToolTip(_("Untick to share only crests, managers and stadiums -- then the package "
                                          "can go on top of an updated squad database without putting old squads back."))
        self.parts["squads"].toggled.connect(self.parts["faces"].setEnabled)
        v.addWidget(hint(_("A league below another league must go with it. A league placed below one of the "
                           "game's leagues works for everybody with the same game version.")))
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText(_("Save the package..."))
        bb.accepted.connect(self.check)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def tick(self, state):
        for i in range(self.leagues.count()):
            self.leagues.item(i).setCheckState(state)

    def picked(self):
        return [self.leagues.item(i).data(Qt.UserRole) for i in range(self.leagues.count())
                if self.leagues.item(i).checkState() == Qt.Checked]

    def meta(self):
        return {"name": self.name.text().strip(), "author": self.author.text().strip(),
                "version": self.version.text().strip() or "1.0", "description": self.desc.toPlainText().strip()}

    def check(self):
        if not self.name.text().strip():
            error(self, "Make a league package", _("Give the package a name."))
            return
        if not self.picked() and not self.edits.isChecked():
            error(self, "Make a league package", _("Tick at least one league."))
            return
        self.accept()


class Packages(BuilderPage):
    title = "League packages"
    hint = ("Share leagues: make a package of your leagues for other people, or add somebody's package to "
            "your recipe. Added leagues show up on every League Builder page; Build puts them in the game.")

    def __init__(self, app):
        super().__init__(app)
        self.action("Add a package...", self.add_pack, "primary")
        self.action("Make a package...", self.make_pack)
        self.action("Remove from the recipe", self.remove_pack, "danger")
        split = QSplitter(Qt.Horizontal)
        self.tree = QTreeWidget()
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setHeaderLabels([_("Package"), _("Version"), _("Author"), _("Leagues")])
        for c, w in enumerate((240, 70, 140, 300)):
            self.tree.setColumnWidth(c, w)
        self.tree.currentItemChanged.connect(lambda *_a: self.show_one())
        split.addWidget(self.tree)
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(8, 0, 0, 0)
        self.about = QPlainTextEdit()
        self.about.setObjectName("log")
        self.about.setReadOnly(True)
        rv.addWidget(self.about, 1)
        split.addWidget(right)
        split.setSizes([700, 420])
        self.outer.addWidget(split, 1)
        self.foot = hint("")
        self.outer.addWidget(self.foot)
        self.project.changed.connect(self.refresh_if_shown)

    def refresh_if_shown(self):
        if self.isVisible():
            self.refresh()

    def shown(self):
        self.need_tables()
        self.refresh()

    def refresh(self):
        self.tree.clear()
        for tag, p in K.packs(self.project.recipe).items():
            it = QTreeWidgetItem([p.get("name") or tag, p.get("version") or "", p.get("author") or "",
                                  ", ".join(p.get("leagues") or [])])
            it.setData(0, Qt.UserRole, tag)
            self.tree.addTopLevelItem(it)
        n = self.tree.topLevelItemCount()
        self.foot.setText(_("%d package(s) in this recipe.") % n if n else
                          _("No packages in this recipe yet. Add a .fl26pack file, or drop one on Install a mod."))
        if n:
            self.tree.setCurrentItem(self.tree.topLevelItem(0))
        else:
            self.about.setPlainText("")

    def show_one(self):
        it = self.tree.currentItem()
        if not it:
            return
        p = K.packs(self.project.recipe).get(it.data(0, Qt.UserRole)) or {}
        lines = ["%s %s" % (p.get("name", ""), p.get("version", "")), _("by %s") % (p.get("author") or "?"), ""]
        lines += [_("Leagues:")] + ["  " + n for n in p.get("leagues") or []]
        if p.get("players"):
            lines += ["", _("Player changes in %d clubs") % len(p["players"])]
        say = {"leagues": "Changes to %d of the game's leagues", "clubs": "Changes to %d of the game's clubs"}
        for kind, keys in (p.get("edits") or {}).items():
            if keys and kind in say:
                lines.append(_(say[kind]) % len(keys))
        man = os.path.join(p.get("folder") or "", "manifest.json")
        if os.path.exists(man):
            import json
            d = json.load(open(man, encoding="utf-8")).get("description")
            if d:
                lines += ["", d]
        self.about.setPlainText("\n".join(lines))

    # ---- actions ----
    def add_pack(self, path=None):
        if not path:
            path, _f = QFileDialog.getOpenFileName(self, _("Add a league package"),
                                                   self.app.settings.get("pack_dir", ""), _(FILTER))
            if not path:
                return
        self.app.settings["pack_dir"] = os.path.dirname(path)
        try:
            man = K.manifest(path)
        except K.Error as e:
            error(self, "League packages", str(e))
            return
        text = [_("%s %s by %s") % (man.get("name"), man.get("version"), man.get("author") or "?"), ""]
        text += ["  %s  (%s, %d %s)" % (L["name"], L.get("country", ""), int(L.get("clubs") or 0), _("clubs"))
                 for L in man.get("leagues", [])]
        if man.get("player_changes"):
            text.append(_("%d player changes, %d faces") % (man["player_changes"], man.get("faces", 0)))
        if any(man.get("edits", {}).values()):
            text.append(_("It also changes some of the game's own leagues or clubs."))
        if man.get("players") is False:
            text.append(_("No squads: its crests and managers go onto the clubs of the same name in leagues "
                          "you already have, and your players stay as they are."))
        if man.get("description"):
            text += ["", man["description"]]
        # the same package again (its name): a new version takes the old one's place (GitHub #34)
        same = lambda n: (n or "").strip().casefold() == (man.get("name") or "").strip().casefold()
        old = [(t, p) for t, p in K.packs(self.project.recipe).items() if same(p.get("name"))]
        if old:
            text += ["", _("The recipe already has %s. Replace it with this version? Its leagues, clubs and "
                           "player changes go out and the new ones come in.")
                     % ", ".join("%s %s" % (p.get("name") or t, p.get("version") or "") for t, p in old)]
        else:
            text += ["", _("Add it to the recipe?")]
        if not ask(self, "Add a league package", "\n".join(text)):
            return
        try:
            man, piece, folder = K.unpack(path, store())
        except K.Error as e:
            error(self, "League packages", str(e))
            return
        tag = K.tag_of(man)
        rename = {}
        going = {n for _t, p in old for n in p.get("leagues") or []}      # replaced, not clashing
        clash = [n for n in K.clashes(self.project.recipe, piece, tag) if n not in going]
        if man.get("players") is False:
            clash = []                        # it goes onto those leagues (lbpackage.overlay)
        if clash:
            if not ask(self, "Add a league package",
                       _("The recipe already has a league called %s. Add the package's with its name after it, "
                         "e.g. \"%s (%s)\"?") % (", ".join(clash), clash[0], man.get("name"))):
                return
            have = {L["name"] for L in self.project.recipe.get("leagues", [])}
            for n in clash:
                new, k = "%s (%s)" % (n, man.get("name")), 2
                while new in have:
                    new, k = "%s (%s %d)" % (n, man.get("name"), k), k + 1
                rename[n] = new
                have.add(new)
        for t, _p in old:
            if t != tag:                      # K.add replaces a package of the same tag itself
                K.remove(self.project.recipe, t)
        try:
            K.add(self.project.recipe, man, piece, folder, rename)
        except K.Error as e:
            error(self, "League packages", str(e))
            return
        self.project.touch()
        msg = _("Added %s. Save the recipe, then Build to put the leagues in the game.") % man.get("name")
        matched = (self.project.recipe.get("packs") or {}).get(tag, {}).get("matched") or {}
        if matched:
            msg += " " + "; ".join(_("%s: %d of %d clubs found by name") % (n, h, t) for n, (h, t) in matched.items())
        self.say(msg, "ok")

    def make_pack(self):
        r = self.project.recipe
        if not r.get("leagues") and not r.get("edits") and not r.get("players"):
            error(self, "Make a league package", _("The recipe has no leagues yet."))
            return
        d = MakeDialog(self, r, self.app.settings.get("last_pack", {}))
        if d.exec() != QDialog.Accepted:
            return
        meta = d.meta()
        self.app.settings["last_pack"] = meta
        start = os.path.join(self.app.settings.get("pack_dir", ""),
                             "%s-%s%s" % (K.tag_of({"name": meta["name"]}), meta["version"], K.EXT))
        out, _f = QFileDialog.getSaveFileName(self, _("Save the package"), start, _(FILTER))
        if not out:
            return
        if not out.lower().endswith(K.EXT):
            out += K.EXT
        self.app.settings["pack_dir"] = os.path.dirname(out)
        from .. import VERSION
        meta["made_with"] = "FL26 Mod Studio %s" % VERSION
        leagues, edits = d.picked(), d.edits.isChecked()
        parts = [k for k, b in d.parts.items() if b.isChecked() and b.isEnabled()]
        sider = getattr(self.app.game, "sider_dir", None) if self.app.game else None
        self.app.busy(True, _("Making the package"))

        def job(progress):
            return K.export(r, out, meta, leagues, edits, log=progress, parts=parts, sider=sider)

        def done(man):
            self.app.busy(False)
            info(self, "Make a league package",
                 _("Saved %s\n\n%d leagues, %d clubs, %d faces. Share this one file; people add it on this page.")
                 % (out, len(man["leagues"]), man["clubs"], man["faces"]))

        def failed(tb):
            self.app.busy(False)
            error(self, "Make a league package", tb.strip().splitlines()[-1])
        run_job(job, done, failed)

    def remove_pack(self):
        it = self.tree.currentItem()
        if not it:
            return
        tag = it.data(0, Qt.UserRole)
        p = K.packs(self.project.recipe).get(tag) or {}
        if not ask(self, "League packages", _("Take %s out of the recipe: its leagues %s and the changes it "
                                              "brought? Build again afterwards.") %
                   (p.get("name") or tag, ", ".join(p.get("leagues") or []))):
            return
        K.remove(self.project.recipe, tag)
        self.project.touch()
