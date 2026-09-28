"""Music: goal songs (goalsong-server) and the menu soundtrack (soundtrack-server).

The soundtrack is folders of Track_1.mp3 .. Track_N.mp3, and SoundtrackServer.lua holds how
many tracks each folder has (Main_Soundtrack_MaxCount = 49 ...).  A track added without
raising that number is never played, so the page keeps the files and the numbers together.
"""
import os, shutil, time

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (QFileDialog, QLabel, QPushButton, QSplitter, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget)

from .. import servers as S, theme
from ..backups import home
from ..i18n import _
from ..ui import hint, row, ask, error
from .content import ServerPage

ROW = Qt.UserRole


def id3(path):
    """(artist, title) from an ID3v2 tag, or ("", "")"""
    try:
        with open(path, "rb") as f:
            head = f.read(10)
            if head[:3] != b"ID3":
                return "", ""
            ver = head[3]
            size = (head[6] << 21) | (head[7] << 14) | (head[8] << 7) | head[9]
            data = f.read(min(size, 262144))
    except OSError:
        return "", ""
    out, i = {}, 0
    while i + 10 <= len(data):
        fid = data[i:i + 4]
        if fid[:1] == b"\0":
            break
        n = int.from_bytes(data[i + 4:i + 8], "big")
        if ver == 4:
            n = (data[i + 4] << 21) | (data[i + 5] << 14) | (data[i + 6] << 7) | data[i + 7]
        body = data[i + 10:i + 10 + n]
        if fid in (b"TIT2", b"TPE1") and body:
            enc, txt = body[0], body[1:]
            try:
                s = txt.decode("utf-16") if enc in (1, 2) else txt.decode("utf-8" if enc == 3 else "latin-1")
            except UnicodeDecodeError:
                s = txt.decode("latin-1", "replace")
            out[fid] = s.strip("\0").strip()
        i += 10 + n
    return out.get(b"TPE1", ""), out.get(b"TIT2", "")


class Soundtrack(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 8, 0, 0)
        v.addWidget(hint(_("Menu music. Each folder holds Track_1.mp3, Track_2.mp3 ...; SoundtrackServer.lua "
                           "says how many there are, so the program changes that number whenever you add "
                           "or remove a track. Removed tracks are moved to SiderAddons\\ModStudio\\removed.")))
        split = QSplitter(Qt.Horizontal)
        self.cats = QTreeWidget()
        self.cats.setRootIsDecorated(False)
        self.cats.setHeaderLabels([_("Folder"), _("Tracks"), _("Module plays")])
        self.cats.setColumnWidth(0, 200)
        self.cats.currentItemChanged.connect(lambda *_a: self.fill_tracks())
        split.addWidget(self.cats)
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(10, 0, 0, 0)
        self.tracks = QTreeWidget()
        self.tracks.setRootIsDecorated(False)
        self.tracks.setAlternatingRowColors(True)
        self.tracks.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.tracks.setHeaderLabels([_("No."), _("File"), _("Artist"), _("Title")])
        for c, w in enumerate((50, 130, 200)):
            self.tracks.setColumnWidth(c, w)
        self.tracks.itemDoubleClicked.connect(lambda *_a: self.play())
        rv.addWidget(self.tracks, 1)
        btn = []
        for text, slot, kind in ((_("Add tracks..."), self.add, "primary"), (_("Up"), lambda: self.move(-1), None),
                                 (_("Down"), lambda: self.move(1), None), (_("Listen"), self.play, None),
                                 (_("Remove"), self.remove, "danger")):
            b = QPushButton(text)
            if kind:
                b.setObjectName(kind)
            b.clicked.connect(slot)
            btn.append(b)
        rv.addWidget(row(*btn))
        self.fix_btn = QPushButton(_("Make the module play every track"))
        self.fix_btn.clicked.connect(self.fix_counts)
        self.note = QLabel("")
        self.note.setWordWrap(True)
        rv.addWidget(row(self.note, "stretch", self.fix_btn, stretch=False))
        split.addWidget(right)
        split.setSizes([380, 800])
        v.addWidget(split, 1)

    def root(self):
        return os.path.join(self.app.game.content_dir, "soundtrack-server")

    def lua(self):
        return os.path.join(self.app.game.modules_dir, "SoundtrackServer.lua")

    def refresh(self):
        cur = self.cats.currentItem()
        cur = cur.data(0, ROW)[0] if cur else None
        self.cats.clear()
        counts = S.counts(self.lua())
        if not os.path.isdir(self.root()):
            self.note.setText(_("There is no soundtrack-server folder in SiderAddons\\content."))
            return
        bad = 0
        for folder, key, title in S.SOUNDTRACK:
            n = len(S.tracks(os.path.join(self.root(), folder)))
            c = counts.get(key)
            it = QTreeWidgetItem([_(title), str(n), "-" if c is None else str(c)])
            it.setData(0, ROW, (folder, key))
            if c is not None and c != n:
                bad += 1
                for k in range(3):
                    it.setForeground(k, QBrush(QColor(theme.WARN)))
                it.setToolTip(0, _("the module plays %d of %d tracks") % (min(c, n), n) if c < n else
                              _("the module expects %d tracks but there are %d") % (c, n))
            self.cats.addTopLevelItem(it)
            if folder == cur or (cur is None and self.cats.topLevelItemCount() == 1):
                self.cats.setCurrentItem(it)
        if not os.path.exists(self.lua()):
            self.note.setText(_("SoundtrackServer.lua is not in the modules folder."))
            self.fix_btn.setEnabled(False)
        elif bad:
            self.note.setText(_("%d folder(s) do not match the numbers in SoundtrackServer.lua.") % bad)
            self.note.setStyleSheet("color: %s;" % theme.WARN)
            self.fix_btn.setEnabled(True)
        else:
            self.note.setText(_("Every track is played."))
            self.note.setStyleSheet("color: %s;" % theme.GOOD)
            self.fix_btn.setEnabled(False)

    def current(self):
        it = self.cats.currentItem()
        return it.data(0, ROW) if it else (None, None)

    def folder(self):
        f, _k = self.current()
        return os.path.join(self.root(), f) if f else None

    def fill_tracks(self):
        self.tracks.clear()
        d = self.folder()
        if not d:
            return
        for n, name in S.tracks(d):
            a, t = id3(os.path.join(d, name))
            it = QTreeWidgetItem([str(n), name, a, t])
            it.setData(0, ROW, name)
            self.tracks.addTopLevelItem(it)

    def names(self):
        return [self.tracks.topLevelItem(i).data(0, ROW) for i in range(self.tracks.topLevelItemCount())]

    def selected(self):
        return [it.data(0, ROW) for it in self.tracks.selectedItems()]

    def running(self):
        g, s = self.app.game.running()
        if g:
            error(self, "Music", _("Close the game first: it keeps the music files open."))
        return g

    def sync(self, folder_key):
        """the module's number for this folder = the files in it"""
        f, key = folder_key
        n = len(S.tracks(os.path.join(self.root(), f)))
        if os.path.exists(self.lua()):
            S.set_counts(self.lua(), {key: n}, self.app.game.sider_dir)

    def add(self):
        d = self.folder()
        if not d or self.running():
            return
        files, _f = QFileDialog.getOpenFileNames(self, _("Add tracks..."), "", "MP3 (*.mp3)")
        if not files:
            return
        n = len(S.tracks(d))
        S.renumber(d, self.names())                       # close any gaps first
        for i, src in enumerate(files):
            shutil.copy2(src, os.path.join(d, "Track_%d.mp3" % (n + i + 1)))
        self.sync(self.current())
        self.refresh()
        self.fill_tracks()

    def remove(self):
        d = self.folder()
        sel = self.selected()
        if not d or not sel or self.running():
            return
        if not ask(self, "Remove", _("Take %d track(s) out? They are moved to SiderAddons\\ModStudio\\removed.") % len(sel)):
            return
        bin_ = os.path.join(home(self.app.game.sider_dir), "removed", time.strftime("%Y%m%d-%H%M%S"),
                            self.current()[0])
        os.makedirs(bin_, exist_ok=True)
        for n in sel:
            shutil.move(os.path.join(d, n), os.path.join(bin_, n))
        S.renumber(d, [n for n in self.names() if n not in sel])
        self.sync(self.current())
        self.refresh()
        self.fill_tracks()

    def move(self, step):
        d = self.folder()
        sel = self.selected()
        if not d or len(sel) != 1 or self.running():
            return
        order = self.names()
        i = order.index(sel[0])
        j = i + step
        if not 0 <= j < len(order):
            return
        order[i], order[j] = order[j], order[i]
        S.renumber(d, order)
        self.fill_tracks()
        it = self.tracks.topLevelItem(j)
        self.tracks.setCurrentItem(it)

    def play(self):
        d, sel = self.folder(), self.selected()
        if d and sel:
            os.startfile(os.path.join(d, sel[0]))

    def fix_counts(self):
        want = {key: len(S.tracks(os.path.join(self.root(), f))) for f, key, _t in S.SOUNDTRACK}
        have = S.counts(self.lua())
        want = {k: v for k, v in want.items() if k in have}
        changed = S.set_counts(self.lua(), want, self.app.game.sider_dir)
        self.app.status(_("SoundtrackServer.lua: %d number(s) changed") % len(changed))
        self.refresh()


class Music(ServerPage):
    title = "Music"
    server = "goalsongs"

    def extra_tabs(self):
        self.soundtrack = Soundtrack(self.app)
        return [("Menu soundtrack", self.soundtrack)]

    def refresh(self):
        super().refresh()
        self.soundtrack.refresh()
