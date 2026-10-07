"""Kits: kit-server's club kit folders and competition badge sets"""
import os, shutil

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QCheckBox, QComboBox, QFileDialog, QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem

from .. import servers as S, theme
from ..i18n import _
from ..mapfile import Row
from ..ui import hint, row, error
from .content import ServerPage, project


def is_kit_folder(d):
    """a club's kit folder as kit-server reads it: order.ini, or a p1 kit with its config.txt --
    or a folder of kit pictures (p1.png, g1.png ...) to make one from (0.2.0, tools/kitpics.py)"""
    try:
        names = {n.lower() for n in os.listdir(d)}
    except OSError:
        return False
    return ("order.ini" in names or os.path.isfile(os.path.join(d, "p1", "config.txt"))
            or bool(pictures(d)))


def pictures(d):
    """the kit pictures of a picture folder, {"p1": path, ...}, or {} for any other folder"""
    import kitpics
    return kitpics.pictures(d)


def number_kits(lib):
    """the library's kit folders whose p1 has back numbers, leg numbers and a name font to lend a
    kit made from pictures"""
    out = []
    for d in kit_folders(lib):
        try:
            names = [n.lower() for n in os.listdir(os.path.join(d, "p1"))]
        except OSError:
            continue
        if all(any(n.endswith(s + ".ftex") for n in names) for s in ("_back", "_leg", "_name")):
            out.append(d)
    return out


def kit_folders(root, depth=3):
    """the club kit folders at or under `root`, a few levels down"""
    if is_kit_folder(root):
        return [root]
    out = []

    def walk(d, level):
        try:
            names = sorted(os.listdir(d), key=str.lower)
        except OSError:
            return
        for n in names:
            p = os.path.join(d, n)
            if not os.path.isdir(p):
                continue
            if is_kit_folder(p):
                out.append(p)
            elif level < depth:
                walk(p, level + 1)
    walk(root, 1)
    return out


def library_path(root, folder):
    """where a kit folder goes in the library, League\\Club like the rest of it: its path under
    the picked folder, with the picked folder's name in front when that is one part only"""
    root, folder = os.path.normpath(root), os.path.normpath(folder)
    if folder == root:
        return os.path.join(os.path.basename(os.path.dirname(root)) or "Imported", os.path.basename(root))
    rel = os.path.relpath(folder, root)
    return rel if os.sep in rel else os.path.join(os.path.basename(root), rel)


def same_files(a, b):
    """two folders with the same files of the same sizes"""
    def listing(d):
        out = {}
        for dp, _ds, fs in os.walk(d):
            for f in fs:
                p = os.path.join(dp, f)
                out[os.path.relpath(p, d).lower()] = os.path.getsize(p)
        return out
    try:
        return listing(a) == listing(b)
    except OSError:
        return False


def place(src, lib, rel, team_id=None, numbers=None):
    """copy one kit folder into the library at rel; -> the path the map line names. A folder
    already there with other files is kept and this one goes next to it as "<club> (2)". A
    folder of pictures is made into a kit for team_id there instead, with the number files of
    the kit folder `numbers` (tools/kitpics.py)."""
    dst = os.path.join(lib, rel)
    pics = {} if team_id is None or os.path.isfile(os.path.join(src, "order.ini")) else pictures(src)
    if pics:
        import kitpics
        k = 1
        while os.path.exists(dst):
            k += 1
            dst = os.path.join(lib, "%s (%d)" % (rel, k))
        kitpics.make_kit(pics, team_id, dst, numbers)
        return os.path.relpath(dst, lib)
    if os.path.normcase(os.path.abspath(src)) == os.path.normcase(os.path.abspath(dst)):
        return rel
    k = 1
    while os.path.exists(dst) and not same_files(src, dst):
        k += 1
        dst = os.path.join(lib, "%s (%d)" % (rel, k))
    if not os.path.exists(dst):
        shutil.copytree(src, dst)
    return os.path.relpath(dst, lib)


def _dialog_class():
    # Dialog lives in builder.py, which imports the League Builder; load it only when asked
    from .builder import Dialog

    class KitImport(Dialog):
        """kits for many clubs at once (0.1.8): every club kit folder (kit-server format: p1, p2,
        g1 ... with order.ini) under a picked folder is matched to a club by its folder name -- the
        club's name or its team id -- copied into the kit-server library and given a map.txt line.
        Matching by name is tools/crestmatch.py, as for Import crests."""
        help = ("Gives many clubs their kits at once. Pick a folder of ready kit-server kits: one folder per club, "
                "holding p1, p2, g1 ... and order.ini, named after the club (\"Dinamo Zagreb\") or its team ID "
                "(\"2215\").\n\n"
                "A club folder can also hold plain kit pictures instead: p1.png, p2.png ... for the kits and g1.png "
                "for the goalkeeper (2048 x 2048 is best; .jpg and .dds work too). Mod Studio turns them into "
                "kit-server kits; the back numbers, leg numbers and name font come from the kit picked in "
                "\"Numbers and names from\". The picture conversion is Xxspedd's.\n\n"
                "Untick a wrong match before OK. The kits are copied into the kit-server library and get a line "
                "in map.txt; press Save on the Kits page to write it. A club that already has a line keeps it "
                "unless \"Replace kits already set\" is ticked.\n\n"
                "The kits of a new League Builder club go by the team ID Build gave it, so Build the world "
                "first and keep it switched on.")

        def __init__(self, view):
            super().__init__(view, "Import kits")
            import crestmatch
            self.cm, self.view = crestmatch, view
            self.tab = view.map_tabs[0]
            p = project(view.app)
            teams, _c = p.names() if p is not None and p.base is not None else ({}, {})
            worlds = set()
            if p is not None and p.base is not None:
                import leaguebuilder as B
                try:
                    game = set(B.game_clubs(p.base))
                    for db in p.world_tables():
                        worlds |= set(B.game_clubs(db)) - game
                except (OSError, ValueError, B.BuildError):
                    pass
            self.clubs = [(n, tid) for tid, n in sorted(teams.items())]
            self.world_ids = worlds
            self.form.addRow(hint(_("Each kit folder is matched to a club by its folder name: the club's name or "
                                    "its team ID. Untick a wrong match.")))
            self.folder = QLineEdit()
            self.folder.setReadOnly(True)
            pick = QPushButton(_("Pick folder..."))
            pick.clicked.connect(self.pick)
            self.form.addRow(_("Folder"), row(self.folder, pick, stretch=False))
            self.only = QComboBox()
            self.only.addItem(_("All clubs"), None)
            self.only.addItem(_("The new clubs of the live world"), "world")
            self.only.currentIndexChanged.connect(lambda *_a: self.fill())
            self.form.addRow(_("Match to"), self.only)
            self.replace = QCheckBox(_("Replace kits already set"))
            self.form.addRow("", self.replace)
            # kits made from pictures (0.2.0) borrow these textures from a kit of the library
            self.numbers = QComboBox()
            self.numbers.addItem(_("(none: the game keeps the club's own)"), None)
            lib = view.folder()
            for d in number_kits(lib) if lib and os.path.isdir(lib) else []:
                self.numbers.addItem(os.path.relpath(d, lib), d)
            if self.numbers.count() > 1:
                self.numbers.setCurrentIndex(1)
            self.form.addRow(_("Numbers and names from"), self.numbers)
            self.tree = QTreeWidget()
            self.tree.setRootIsDecorated(False)
            self.tree.setAlternatingRowColors(True)
            self.tree.setHeaderLabels([_("Kit folder"), _("Club"), _("Team ID"), _("Match")])
            for c, w in enumerate((280, 260, 80)):
                self.tree.setColumnWidth(c, w)
            self.tree.setMinimumSize(720, 340)
            self.form.addRow(self.tree)
            self.said = hint("")
            self.form.addRow(self.said)
            self.found = []
            self.result = None

        def pick(self):
            d = QFileDialog.getExistingDirectory(self, _("Pick folder..."), self.folder.text())
            if d:
                self.load(d)

        def load(self, d):
            self.folder.setText(os.path.normpath(d))
            self.found = kit_folders(self.folder.text())
            self.fill()

        def matches(self):
            """{kit folder: ((club name, team id), score)} for the clubs the Match to box allows"""
            want = self.only.currentData()
            clubs = [c for c in self.clubs if want is None or c[1] in self.world_ids]
            ids = {tid for _n, tid in clubs}
            names = {f: os.path.basename(f) for f in self.found}
            out, rest = {}, []
            for f in self.found:
                n = names[f].strip()
                if n.isdigit() and int(n) in ids:
                    out[f] = ((dict((t, m) for m, t in clubs)[int(n)], int(n)), 1.0)
                else:
                    rest.append(f)
            taken = {v[0][1] for v in out.values()}
            left = [c for c in clubs if c[1] not in taken]
            # ".kit" so a folder like "St. Pauli" keeps its last word: crestmatch drops a file's extension
            got = self.cm.match([names[f] + ".kit" for f in rest], [(n, i) for i, (n, _t) in enumerate(left)])
            for f, (_x, j, sc) in zip(rest, got):
                if j is not None:
                    out[f] = (left[j], sc)
            return out

        def fill(self):
            m = self.matches()
            root = self.folder.text()
            self.tree.clear()
            for f in self.found:
                it = QTreeWidgetItem([os.path.relpath(f, root) if f != root else os.path.basename(f), "", "", ""])
                it.setData(0, Qt.UserRole, f)
                if f in m:
                    (n, tid), sc = m[f]
                    it.setText(1, n)
                    it.setText(2, str(tid))
                    it.setText(3, "%d %%" % round(sc * 100))
                    it.setData(1, Qt.UserRole, tid)
                    it.setCheckState(0, Qt.Checked if sc >= 0.6 else Qt.Unchecked)
                else:
                    it.setText(1, _("no club found"))
                    it.setForeground(1, QBrush(QColor(theme.SUBTLE)))
                self.tree.addTopLevelItem(it)
            self.said.setText(_("%d kit folders, %d matched to a club.") % (len(self.found), len(m)))

        def ok(self):
            lib = self.view.folder()
            mf = self.tab.mf
            n = kept = 0
            try:
                for i in range(self.tree.topLevelItemCount()):
                    it = self.tree.topLevelItem(i)
                    tid = it.data(1, Qt.UserRole)
                    if tid is None or it.checkState(0) != Qt.Checked:
                        continue
                    have = [r for r in mf.rows() if r.enabled and r.fields and r.fields[0].strip() == str(tid)]
                    if have and not self.replace.isChecked():
                        kept += 1
                        continue
                    src = it.data(0, Qt.UserRole)
                    rel = place(src, lib, library_path(self.folder.text(), src), tid,
                                self.numbers.currentData())
                    if have:
                        have[0].fields[1:2] = [rel]
                        have[0].touch()
                    else:
                        mf.add(Row([str(tid), rel], quoted=[1]), after=self.tab.last_like(Row([str(tid)])))
                    n += 1
            except (OSError, ValueError, ImportError) as e:
                error(self, "Import kits", _("Could not copy the kits: %s") % e)
            if n:
                self.view._lib = None
                self.tab.changed()
            self.result = (n, kept)
            self.accept()

    return KitImport


class Kits(ServerPage):
    title = "Kits"
    server = "kits"

    def __init__(self, app):
        super().__init__(app)
        self.action("Import kits...", self.import_kits, tip="Kits for many clubs at once, from a folder of "
                                                           "kit-server club folders or kit pictures named after the clubs")

    def import_kits(self):
        v = self.view
        if not v.server.installed(v.content_dir()):
            error(self, "Import kits", _("There is no %s folder in SiderAddons\\content: this server is not "
                                         "installed.") % v.server.folder)
            return
        if not v.loaded:
            v.refresh(force=True)
        d = _dialog_class()(v)
        if d.finish() and d.result:
            n, kept = d.result
            self.say(_("%d clubs got kits: press Save to write map.txt.") % n
                     + ("  " + _("%d clubs kept the kits they had.") % kept if kept else ""), "ok" if n else "warn")
