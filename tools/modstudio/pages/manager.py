"""Game file tools: CPK archives, textures, models and animations, through the optional native
module (native.py). Pack order, installs and sider.ini stay with Roots, Install and Modules."""
import json
import os

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QImage, QPixmap
from PySide6.QtWidgets import (QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem, QPlainTextEdit, QPushButton,
                               QSpinBox, QSplitter, QStackedWidget, QTreeWidget, QTreeWidgetItem,
                               QVBoxLayout, QWidget)

from .. import backups, native, theme
from ..i18n import _
from ..ui import Page, ask, hint, pick_dir, run_job, row


def _report(value):
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


class _ToolDeck(QWidget):
    currentChanged = Signal(int)
    _DESCRIPTIONS = {
        "CPK archives": "Inspect archive contents and locate game resources.",
        "Textures": "Preview and inspect supported texture files.",
        "Assets": "Preview models and inspect or edit animation files.",
    }

    def __init__(self):
        super().__init__()
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        rail = QFrame()
        rail.setObjectName("card")
        rail.setAttribute(Qt.WA_StyledBackground, True)
        rail.setMinimumWidth(205)
        rail.setMaximumWidth(250)
        rail_layout = QVBoxLayout(rail)
        rail_layout.setContentsMargins(12, 12, 12, 12)
        rail_layout.setSpacing(8)
        rail_title = QLabel(_("TOOLS"))
        rail_title.setObjectName("section_o")
        rail_layout.addWidget(rail_title)
        self.search = QLineEdit()
        self.search.setPlaceholderText(_("Find a tool..."))
        self.search.setClearButtonEnabled(True)
        self.search.setToolTip(_("Filter the tool list by name."))
        self.search.textChanged.connect(self._filter_tools)
        rail_layout.addWidget(self.search)
        self.list = QListWidget()
        self.list.setObjectName("managerNav")
        self.list.setSpacing(3)
        self.list.setUniformItemSizes(True)
        self.list.setTextElideMode(Qt.ElideRight)
        self.list.currentRowChanged.connect(self._select)
        self.list.setStyleSheet(
            "QListWidget#managerNav { background: transparent; border: none; }"
            "QListWidget#managerNav::item { border: 1px solid transparent; padding: 9px 8px; }"
            "QListWidget#managerNav::item:hover { background: %s; border-color: %s; }"
            "QListWidget#managerNav::item:selected { background: %s; border-color: %s;"
            " border-left: 3px solid %s; color: %s; }"
            % (theme.PANEL2, theme.BORDER, theme.SELECTION, theme.LINE2, theme.ORANGE, theme.TEXT)
        )
        rail_layout.addWidget(self.list, 1)
        self.tool_count = QLabel(_("0 tools"))
        self.tool_count.setObjectName("subtle")
        rail_layout.addWidget(self.tool_count)
        root.addWidget(rail)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)
        self.title = QLabel()
        self.title.setObjectName("pagetitle")
        content_layout.addWidget(self.title)
        self.description = QLabel()
        self.description.setObjectName("hint")
        self.description.setWordWrap(True)
        content_layout.addWidget(self.description)
        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack, 1)
        root.addWidget(content, 1)

    def addTab(self, page, title):
        item = QListWidgetItem("%02d   %s" % (self.stack.count() + 1, _(title)))
        item.setData(Qt.UserRole, title)
        item.setToolTip(_(self._DESCRIPTIONS.get(title, "")))
        self.list.addItem(item)
        index = self.stack.addWidget(page)
        self.tool_count.setText(_("%(count)d tools") % {"count": self.stack.count()})
        if index == 0:
            self.list.setCurrentRow(0)
        return index

    def _select(self, index):
        if index < 0:
            return
        self.stack.setCurrentIndex(index)
        title = self.tabText(index)
        raw_title = str(self.list.item(index).data(Qt.UserRole))
        self.title.setText(title)
        self.description.setText(_(self._DESCRIPTIONS.get(raw_title, "")))
        self.currentChanged.emit(index)

    def _filter_tools(self, text):
        query = text.strip().casefold()
        visible = []
        for index in range(self.list.count()):
            item = self.list.item(index)
            matches = not query or query in str(item.data(Qt.UserRole)).casefold()
            item.setHidden(not matches)
            if matches:
                visible.append(index)
        current = self.currentIndex()
        if visible and (current < 0 or self.list.item(current).isHidden()):
            self.list.setCurrentRow(visible[0])

    def count(self):
        return self.stack.count()

    def tabText(self, index):
        item = self.list.item(index)
        return _(str(item.data(Qt.UserRole))) if item is not None else ""

    def currentIndex(self):
        index = self.list.currentRow()
        return index if index >= 0 else self.stack.currentIndex()

    def setCurrentIndex(self, index):
        if not 0 <= index < self.count():
            return
        item = self.list.item(index)
        if item.isHidden():
            self.search.clear()
        self.list.setCurrentRow(index)


class _ReportView(QWidget):
    _MAX_CHILDREN = 1000

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.summary = QLabel(_("Run an operation to see its results."))
        self.summary.setObjectName("subtle")
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

        split = QSplitter(Qt.Horizontal)
        self.tree = QTreeWidget()
        self.tree.setObjectName("jsonReportTree")
        self.tree.setHeaderLabels([_("Report"), _("Value")])
        self.tree.setAlternatingRowColors(True)
        self.tree.itemSelectionChanged.connect(self._show_details)
        split.addWidget(self.tree)
        self.details = QTreeWidget()
        self.details.setObjectName("jsonReportDetails")
        self.details.setHeaderLabels([_("Selected item details"), _("Value")])
        self.details.setAlternatingRowColors(True)
        split.addWidget(self.details)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 1)
        layout.addWidget(split, 1)

        self.raw_toggle = QPushButton(_("Show raw JSON"))
        self.raw_toggle.setCheckable(True)
        layout.addWidget(self.raw_toggle, 0, Qt.AlignLeft)
        self.raw = QPlainTextEdit()
        self.raw.setObjectName("log")
        self.raw.setReadOnly(True)
        self.raw.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.raw.setMaximumHeight(220)
        self.raw.setVisible(False)
        self.raw_toggle.toggled.connect(self.raw.setVisible)
        layout.addWidget(self.raw)
        self._data = None

    @staticmethod
    def _value_label(value):
        if isinstance(value, dict):
            return _("%(count)d fields") % {"count": len(value)}
        if isinstance(value, (list, tuple)):
            return _("%(count)d items") % {"count": len(value)}
        if isinstance(value, str):
            if "\n" in value:
                return _("%(lines)d lines · %(chars)d characters") % {
                    "lines": len(value.splitlines()), "chars": len(value),
                }
            return value if len(value) <= 100 else value[:97] + "..."
        return str(value)

    def _add_value(self, parent, label, value, depth=0):
        item = QTreeWidgetItem([str(label), self._value_label(value)])
        item.setData(0, Qt.UserRole, value)
        if parent is None:
            self.tree.addTopLevelItem(item)
        else:
            parent.addChild(item)
        if depth >= 12:
            return item
        if isinstance(value, dict):
            children = list(value.items())
            for key, child in children[:self._MAX_CHILDREN]:
                self._add_value(item, key, child, depth + 1)
            self._add_omitted(item, len(children))
        elif isinstance(value, (list, tuple)):
            for index, child in enumerate(value[:self._MAX_CHILDREN]):
                self._add_value(item, "[%d]" % index, child, depth + 1)
            self._add_omitted(item, len(value))
        return item

    def _add_omitted(self, parent, total):
        if total > self._MAX_CHILDREN:
            parent.addChild(QTreeWidgetItem([
                _("Additional items"), _("%(count)d not shown") % {"count": total - self._MAX_CHILDREN},
            ]))

    def set_data(self, value):
        self._data = value
        self.tree.clear()
        if isinstance(value, dict):
            self.summary.setText(_("%(count)d report fields · select an item to inspect its details")
                                 % {"count": len(value)})
            for key, child in list(value.items())[:self._MAX_CHILDREN]:
                self._add_value(None, key, child)
            self._add_omitted(self.tree.invisibleRootItem(), len(value))
        elif isinstance(value, (list, tuple)):
            self.summary.setText(_("%(count)d results · select an item to inspect its details")
                                 % {"count": len(value)})
            for index, child in enumerate(value[:self._MAX_CHILDREN]):
                self._add_value(None, "[%d]" % index, child)
            self._add_omitted(self.tree.invisibleRootItem(), len(value))
        else:
            self.summary.setText(_("Operation result"))
            self._add_value(None, _("Result"), value)
        self.raw.setPlainText(_report(value))
        self.tree.expandToDepth(1)
        if self.tree.topLevelItemCount():
            self.tree.setCurrentItem(self.tree.topLevelItem(0))

    def _show_details(self):
        items = self.tree.selectedItems()
        if not items:
            return
        value = items[0].data(0, Qt.UserRole)
        self.details.clear()
        if isinstance(value, dict):
            for key, child in list(value.items())[:self._MAX_CHILDREN]:
                self._add_detail(key, child)
            self._add_omitted(self.details.invisibleRootItem(), len(value))
        elif isinstance(value, (list, tuple)):
            for index, child in enumerate(value[:self._MAX_CHILDREN]):
                self._add_detail("[%d]" % index, child)
            self._add_omitted(self.details.invisibleRootItem(), len(value))
        else:
            self._add_detail(_("Value"), value)

    def _add_detail(self, label, value):
        item = QTreeWidgetItem([str(label), self._value_label(value)])
        item.setData(0, Qt.UserRole, value)
        self.details.addTopLevelItem(item)
        if isinstance(value, dict):
            for key, child in list(value.items())[:self._MAX_CHILDREN]:
                item.addChild(QTreeWidgetItem([str(key), self._value_label(child)]))
            self._add_omitted(item, len(value))
        elif isinstance(value, (list, tuple)):
            for index, child in enumerate(value[:self._MAX_CHILDREN]):
                item.addChild(QTreeWidgetItem(["[%d]" % index, self._value_label(child)]))
            self._add_omitted(item, len(value))


class ModManager(Page):
    title = "Game file tools"
    hint = "Inspect CPK archives, textures, models and animations with the optional native tools."

    def __init__(self, app):
        super().__init__(app)
        self.action("Refresh", self.refresh_current, tip="Reload the current tab's data")
        self._asset_entries = []
        self._animation_path = ""
        self.tabs = _ToolDeck()
        self.outer.addWidget(self.tabs, 1)
        self.outputs = {}
        self._make_cpk_tab()
        self._make_texture_tab()
        self._make_assets_tab()
        self.tabs.currentChanged.connect(lambda _index: self.refresh())

    def _tab(self, title):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(10)
        self.tabs.addTab(page, title)
        return layout

    def _can_edit_game_assets(self):
        game = getattr(self.app, "game", None)
        if game is None:
            return True
        running = game.running()
        if any(running):
            self.say(_("Close the game and Sider before editing game assets."), "err")
            return False
        return True

    @staticmethod
    def _in_place(path, reason, call):
        """the work of an edit that rewrites a game file where it is: a restore point first, in
        SiderAddons\\ModStudio\\backups where Restore points lists it, then the native edit. The
        Rust tools keep a copy of their own next to the file (<file>.fl27mm-backup) for their
        command line; inside Mod Studio the restore point is the backup, so that copy is not left
        in the game's folders"""
        side = path + ".fl27mm-backup"

        def work():
            had = os.path.exists(side)
            point = backups.before_change(path, reason)
            try:
                result = call()
            finally:
                if not had and os.path.exists(side):
                    try:
                        os.remove(side)
                    except OSError:
                        pass
            if isinstance(result, dict) and point:
                result["backup"] = point
            return result
        return work

    def _output(self, key, parent, readonly=True):
        report = _ReportView()
        parent.addWidget(report, 1)
        self.outputs[key] = report
        return report

    def _show(self, key, value):
        target = self.outputs.get(key)
        if target is not None:
            target.set_data(value)

    def _run(self, label, work, done, failed=None):
        if not native.available():
            self.say(_("These tools need the optional native module, which this copy of Mod Studio does not have."), "err")
            return
        self.app.busy(True, _(label))

        def finish(result):
            self.app.busy(False)
            self.say("")
            done(result)

        def fail(traceback_text):
            self.app.busy(False)
            message = traceback_text.strip().splitlines()
            self.say(_("The tool stopped:") + "\n" + (message[-1] if message else traceback_text), "err")
            if failed is not None:
                failed(traceback_text)

        run_job(lambda _progress: work(), finish, fail)

    def _file(self, start="", title="Select a file", filters="All files (*)"):
        return QFileDialog.getOpenFileName(self, _(title), start, filters)[0]

    def _save_file(self, start="", title="Save as", filters="All files (*)"):
        return QFileDialog.getSaveFileName(self, _(title), start, filters)[0]

    def _game_folder(self):
        game = getattr(self.app, "game", None)
        return getattr(game, "folder", "") or ""

    def _addons(self):
        game = getattr(self.app, "game", None)
        return getattr(game, "sider_dir", "") or ""

    def _make_cpk_tab(self):
        layout = self._tab("CPK archives")
        self.cpk_path = QLineEdit()
        self.cpk_path.setPlaceholderText(_("CPK archive"))
        browse = QPushButton(_("Choose CPK..."))
        browse.clicked.connect(lambda: self._choose_file_into(self.cpk_path, "CPK archives (*.cpk);;All files (*)"))
        inspect = QPushButton(_("Inspect"))
        inspect.clicked.connect(self.inspect_cpk)
        map_button = QPushButton(_("Map archive"))
        map_button.clicked.connect(self.map_cpk)
        extract = QPushButton(_("Extract..."))
        extract.clicked.connect(self.extract_cpk)
        pack = QPushButton(_("Build CPK..."))
        pack.clicked.connect(self.pack_cpk)
        layout.addWidget(row(self.cpk_path, browse, inspect, map_button, extract, pack, stretch=False))
        self.cpk_summary = QLabel(_("Choose an archive to browse its contents."))
        self.cpk_summary.setWordWrap(True)
        layout.addWidget(self.cpk_summary)
        self.cpk_filter = QLineEdit()
        self.cpk_filter.setPlaceholderText(_("Filter archive paths"))
        self.cpk_filter.textChanged.connect(self.filter_cpk_entries)
        layout.addWidget(self.cpk_filter)
        self.cpk_entries = QTreeWidget()
        self.cpk_entries.setAlternatingRowColors(True)
        self.cpk_entries.setHeaderLabels([_("Archive path"), _("Files / stored"), _("Unpacked size"), _("Kind")])
        layout.addWidget(self.cpk_entries, 3)
        report = self._output("cpk", layout)

    def filter_cpk_entries(self):
        query = self.cpk_filter.text().strip().casefold()
        for index in range(self.cpk_entries.topLevelItemCount()):
            self._filter_cpk_item(self.cpk_entries.topLevelItem(index), query)

    def _filter_cpk_item(self, item, query):
        path = str(item.data(0, Qt.UserRole) or item.text(0)).casefold()
        own_match = not query or query in path
        child_match = False
        for index in range(item.childCount()):
            child_match = self._filter_cpk_item(item.child(index), query) or child_match
        visible = own_match or child_match
        item.setHidden(not visible)
        if query and child_match:
            item.setExpanded(True)
        return visible

    def inspect_cpk(self):
        path = self.cpk_path.text().strip()
        if not path:
            path = self._file(filters="CPK archives (*.cpk);;All files (*)")
        if not path:
            return
        self.cpk_path.setText(path)
        self._run(_("Inspecting CPK..."), lambda: native.cpk_inspect(path),
                  self._show_cpk)

    def _show_cpk(self, data):
        self.cpk_entries.clear()
        files = data.get("files", [])
        folders = {}
        for path, stored, unpacked, compressed in files:
            parts = [part for part in str(path).replace("\\", "/").split("/") if part]
            if not parts:
                continue
            prefix = []
            for part in parts[:-1]:
                prefix.append(part)
                key = "/".join(prefix)
                folder = folders.setdefault(key, {"files": 0, "unpacked": 0})
                folder["files"] += 1
                folder["unpacked"] += int(unpacked)

        for key in sorted(folders, key=lambda value: (value.count("/"), value.casefold())):
            parts = key.split("/")
            parent_key = "/".join(parts[:-1])
            parent = folders[parent_key].get("item") if parent_key else None
            folder = folders[key]
            item = QTreeWidgetItem([
                parts[-1], _("%(count)d files") % {"count": folder["files"]},
                self._map_size(folder["unpacked"]), _("Folder"),
            ])
            item.setData(0, Qt.UserRole, key)
            if parent is None:
                self.cpk_entries.addTopLevelItem(item)
            else:
                parent.addChild(item)
            folder["item"] = item

        for path, stored, unpacked, compressed in files:
            parts = [part for part in str(path).replace("\\", "/").split("/") if part]
            if not parts:
                continue
            parent_key = "/".join(parts[:-1])
            parent = folders[parent_key]["item"] if parent_key else None
            item = QTreeWidgetItem([
                parts[-1], self._map_size(int(stored)), self._map_size(int(unpacked)),
                _("Compressed") if compressed else _("Stored"),
            ])
            item.setData(0, Qt.UserRole, str(path).replace("\\", "/"))
            if parent is None:
                self.cpk_entries.addTopLevelItem(item)
            else:
                parent.addChild(item)

        self.cpk_summary.setText(
            _("%(files)d files · %(compressed)d compressed · %(size)s unpacked · %(folders)d top-level folders")
            % {"files": data.get("entries", len(files)), "compressed": data.get("compressed", 0),
               "size": self._map_size(data.get("unpacked_bytes", 0)),
               "folders": len(data.get("folders", []))}
        )
        shown = data.get("files_shown", len(files))
        total = data.get("files_total", len(files))
        if shown < total:
            self.cpk_summary.setText(
                self.cpk_summary.text() + _(" · showing the first %(shown)d of %(total)d entries")
                % {"shown": shown, "total": total}
            )
        self.filter_cpk_entries()
        self.cpk_entries.expandToDepth(0)
        self._show("cpk", {key: value for key, value in data.items() if key != "files"})

    def _show_cpk_map(self, data):
        self.cpk_entries.clear()
        self.cpk_summary.setText(
            _("%(entries)d files · %(compressed)d compressed · %(size)s unpacked")
            % {"entries": data.get("entries", 0), "compressed": data.get("compressed", 0),
               "size": self._map_size(data.get("unpacked", 0))}
        )
        for section in data.get("sections", []):
            info = section.get("info") or {}
            item = QTreeWidgetItem([
                str(section.get("path", "")),
                _("%(count)d files") % {"count": section.get("files", 0)},
                self._map_size(section.get("bytes", 0)),
                str(info.get("title", _("Folder"))),
            ])
            item.setData(0, Qt.UserRole, section.get("path", ""))
            item.setToolTip(0, str(info.get("what", "")))
            self.cpk_entries.addTopLevelItem(item)
        self.filter_cpk_entries()
        self._show("cpk", data)

    def map_cpk(self):
        path = self.cpk_path.text().strip()
        if not path:
            path = self._file(filters="CPK archives (*.cpk);;All files (*)")
        if not path:
            return
        self.cpk_path.setText(path)
        self._run(_("Mapping CPK archive..."), lambda: native.archive_map(path),
                  self._show_cpk_map)

    def extract_cpk(self):
        path = self.cpk_path.text().strip()
        if not path or not os.path.isfile(path):
            self.say(_("Choose an existing CPK archive first."), "warn")
            return
        output = pick_dir(self, "Choose an empty parent folder for extraction", os.path.dirname(path))
        if not output:
            return
        destination = os.path.join(output, os.path.splitext(os.path.basename(path))[0])
        if os.path.exists(destination):
            self.say(_("Extraction destination already exists; choose an empty parent folder."), "err")
            return
        if not ask(self, "Extract CPK", _("Extract archive contents to %s?") % destination):
            return
        filter_text = self.cpk_filter.text().strip()
        self._run(_("Extracting CPK..."), lambda: native.cpk_extract(path, output, filter_text),
                  lambda result: self._show("cpk", {"files_written": result[0], "folder": result[1]}))

    def pack_cpk(self):
        source = pick_dir(self, "Choose the folder to pack")
        if not source:
            return
        destination = self._save_file(source + ".cpk", "Build CPK", "CPK archives (*.cpk)")
        if not destination:
            return
        if os.path.exists(destination):
            self.say(_("The output file already exists; choose a different name."), "err")
            return
        if not ask(self, "Build CPK", _("Create %s from %s?") % (destination, source)):
            return
        self._run(_("Building CPK..."), lambda: native.cpk_pack(source, destination),
                  lambda result: self._show("cpk", result))

    def _make_texture_tab(self):
        layout = self._tab("Textures")
        self.texture_path = QLineEdit()
        self.texture_path.setPlaceholderText(_("FTEX or DDS file"))
        browse = QPushButton(_("Choose texture..."))
        browse.clicked.connect(lambda: self._choose_file_into(self.texture_path, "Textures (*.ftex *.dds);;All files (*)"))
        info_button = QPushButton(_("Inspect / preview"))
        info_button.clicked.connect(self.inspect_texture)
        convert_button = QPushButton(_("Convert single..."))
        convert_button.clicked.connect(self.convert_texture)
        self.mip = QSpinBox()
        self.mip.setRange(0, 32)
        self.mip.setPrefix(_("Mip level: "))
        self.texture_image = QLabel()
        self.texture_image.setAlignment(Qt.AlignCenter)
        self.texture_image.setMinimumHeight(160)
        self.texture_image.setObjectName("preview")
        layout.addWidget(row(self.texture_path, browse, self.mip, info_button, convert_button, stretch=False))
        layout.addWidget(self.texture_image)
        batch_kind = QComboBox()
        batch_kind.addItems(["diffuse", "normal", "material", "cube"])
        self.texture_batch_kind = batch_kind
        batch = QPushButton(_("Convert folder..."))
        batch.clicked.connect(self.convert_texture_batch)
        layout.addWidget(row(hint(_("Batch conversion")), batch_kind, batch, stretch=False))
        self._output("texture", layout)

    def inspect_texture(self):
        path = self.texture_path.text().strip()
        if not path or not os.path.isfile(path):
            path = self._file(filters="Textures (*.ftex *.dds);;All files (*)")
        if not path:
            return
        self.texture_path.setText(path)

        mip = self.mip.value()

        def work():
            info = native.texture_info(path)
            preview = native.texture_preview(path, mip)
            return info, preview

        def done(result):
            info, (width, height, rgba) = result
            image = QImage(rgba, width, height, width * 4, QImage.Format_RGBA8888).copy()
            self.texture_image.setPixmap(QPixmap.fromImage(image).scaled(
                512, 360, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self._show("texture", info)

        self._run(_("Reading texture..."), work, done)

    def convert_texture(self):
        source = self.texture_path.text().strip()
        if not source or not os.path.isfile(source):
            source = self._file(filters="Textures (*.ftex *.dds);;All files (*)")
        if not source:
            return
        extension = ".dds" if source.lower().endswith(".ftex") else ".ftex"
        destination = self._save_file(os.path.splitext(source)[0] + extension,
                                      "Convert texture", "Textures (*.ftex *.dds)")
        if not destination:
            return
        if os.path.exists(destination):
            self.say(_("The output file already exists; choose a different name."), "err")
            return
        if not ask(self, "Convert texture", _("Convert %s to %s?") % (source, destination)):
            return
        self._run(_("Converting texture..."), lambda: native.convert_texture(source, destination),
                  lambda result: self._show("texture", result))

    def convert_texture_batch(self):
        source = pick_dir(self, "Choose the source folder")
        if not source:
            return
        destination = pick_dir(self, "Choose an empty destination folder")
        if not destination:
            return
        if os.path.abspath(source).lower() == os.path.abspath(destination).lower():
            self.say(_("Source and destination folders must be different."), "err")
            return
        if not ask(self, "Batch texture conversion",
                   _("Convert supported textures from %s into %s? Existing outputs will not be overwritten.")
                   % (source, destination)):
            return
        kind = self.texture_batch_kind.currentText()
        self._run(_("Converting texture folder..."),
                  lambda: native.convert_textures(source, destination, kind),
                  lambda result: self._show("texture", result))


    def _make_assets_tab(self):
        layout = self._tab("Assets")
        self.assets_root = QLineEdit(os.path.join(self._addons(), "livecpk"))
        self.assets_root.setPlaceholderText(_("Asset folder"))
        browse = QPushButton(_("Choose folder..."))
        browse.clicked.connect(lambda: self._choose_into(self.assets_root, _("Choose asset folder")))
        scan = QPushButton(_("List assets"))
        scan.clicked.connect(self.list_assets)
        self.asset_preview_button = QPushButton(_("Preview selected"))
        self.asset_preview_button.clicked.connect(self.preview_asset)
        inspect = QPushButton(_("Inspect animation / rig"))
        inspect.clicked.connect(self.inspect_animation_rig)
        self.asset_inspect_button = inspect
        replace = QPushButton(_("Replace texture..."))
        replace.clicked.connect(self.replace_asset)
        self.asset_replace_button = replace
        layout.addWidget(row(self.assets_root, browse, scan, self.asset_preview_button, inspect, replace,
                             stretch=False))
        self.asset_family = QComboBox()
        self.asset_family.addItem(_("All families"), "")
        for family in ("faces", "hair", "kits", "emblems", "logos", "symbols", "boots",
                       "balls", "menu art", "animations", "other"):
            self.asset_family.addItem(family.title(), family)
        self.asset_family.currentIndexChanged.connect(self.filter_assets)
        self.asset_search = QLineEdit()
        self.asset_search.setPlaceholderText(_("Filter asset paths"))
        self.asset_search.textChanged.connect(self.filter_assets)
        layout.addWidget(row(self.asset_family, self.asset_search, stretch=False))
        split = QSplitter(Qt.Horizontal)
        self.asset_tree = QTreeWidget()
        self.asset_tree.setHeaderLabels([_("Asset"), _("Type"), _("Size")])
        self.asset_tree.itemSelectionChanged.connect(self.show_asset)
        split.addWidget(self.asset_tree)
        detail = QWidget()
        dv = QVBoxLayout(detail)
        dv.setContentsMargins(0, 0, 0, 0)
        self.asset_image = QLabel()
        self.asset_image.setAlignment(Qt.AlignCenter)
        self.asset_image.setMinimumHeight(200)
        dv.addWidget(self.asset_image)
        self.animation_rate = QSpinBox()
        self.animation_rate.setRange(1, 240)
        self.animation_rate.setValue(30)
        set_rate = QPushButton(_("Set animation rate..."))
        set_rate.clicked.connect(self.set_animation_rate)
        dv.addWidget(row(hint(_("Animation frame rate")), self.animation_rate, set_rate, stretch=False))
        self.animation_tracks = QTreeWidget()
        self.animation_tracks.setHeaderLabels([_("Unit / segment"), _("Kind"), _("Keys"), _("First / last")])
        self.animation_tracks.itemSelectionChanged.connect(self.select_animation_segment)
        dv.addWidget(self.animation_tracks, 1)
        self.key_index = QSpinBox()
        self.key_index.setRange(0, 1000000)
        self.key_parts = QLineEdit()
        self.key_parts.setPlaceholderText(_("Quaternion parts: 0,0,0"))
        self.key_signs = QLineEdit()
        self.key_signs.setPlaceholderText(_("Signs: false,false,false"))
        set_key = QPushButton(_("Set quaternion key..."))
        set_key.clicked.connect(self.set_animation_key)
        dv.addWidget(row(hint(_("Quaternion key index")), self.key_index, self.key_parts,
                         self.key_signs, set_key, stretch=False))
        self._output("assets", dv)
        split.addWidget(detail)
        layout.addWidget(split, 1)


    def list_assets(self):
        root = self.assets_root.text().strip()
        if not root:
            self.say(_("Choose an asset folder first."), "warn")
            return

        def done(result):
            self._asset_entries = result.get("items", [])
            self.filter_assets()
            self._show("assets", result)

        self._run(_("Listing assets..."), lambda: native.assets_list(root), done)

    def filter_assets(self):
        if not hasattr(self, "asset_tree"):
            return
        self.asset_tree.clear()
        family = self.asset_family.currentData()
        query = self.asset_search.text().strip().casefold()
        for entry in self._asset_entries:
            path = entry.get("path", "")
            if family and entry.get("family") != family:
                continue
            if query and query not in path.casefold():
                continue
            dimensions = (f'{entry.get("width", 0)}x{entry.get("height", 0)}'
                         if entry.get("width") and entry.get("height") else "")
            item = QTreeWidgetItem([
                os.path.basename(path), str(entry.get("format", "")),
                f'{entry.get("bytes", 0)} {dimensions}'.strip(),
            ])
            item.setData(0, Qt.UserRole, entry)
            self.asset_tree.addTopLevelItem(item)

    def show_asset(self):
        items = self.asset_tree.selectedItems()
        if items:
            entry = items[0].data(0, Qt.UserRole) or {}
            path = entry.get("path", "")
            extension = os.path.splitext(path)[1].lower()
            self.asset_preview_button.setEnabled(extension in {".ftex", ".fmdl"})
            self.asset_inspect_button.setEnabled(extension in {".gani", ".ask", ".frig"})
            self.asset_replace_button.setEnabled(extension == ".ftex" and entry.get("editable", False))
            self._show("assets", entry)

    def preview_asset(self):
        items = self.asset_tree.selectedItems()
        entry = items[0].data(0, Qt.UserRole) if items else {}
        path = entry.get("path", "") if isinstance(entry, dict) else ""
        if not path:
            self.say(_("Select an asset first."), "warn")
            return

        if os.path.splitext(path)[1].lower() == ".ftex":
            def texture_done(result):
                width, height, rgba = result
                image = QImage(rgba, width, height, width * 4, QImage.Format_RGBA8888).copy()
                self.asset_image.setPixmap(QPixmap.fromImage(image).scaled(
                    512, 420, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self._show("assets", {"path": path, "width": width, "height": height})

            self._run(_("Rendering texture preview..."),
                      lambda: native.texture_preview(path, 0), texture_done)
            return

        if os.path.splitext(path)[1].lower() != ".fmdl":
            self.say(_("Select an .fmdl model or .ftex texture to preview."), "warn")
            return

        def done(result):
            png, files, meshes, vertices, maps = result
            self.asset_image.setPixmap(QPixmap.fromImage(QImage.fromData(png)).scaled(
                512, 420, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self._show("assets", {"files": files, "meshes": meshes, "vertices": vertices, "maps": maps})

        self._run(_("Rendering model preview..."),
                  lambda: native.asset_preview(path, "three-quarter", 512), done)

    def inspect_animation_rig(self):
        items = self.asset_tree.selectedItems()
        entry = items[0].data(0, Qt.UserRole) if items else {}
        path = entry.get("path", "") if isinstance(entry, dict) else ""
        if not path:
            path = self._file(filters="Animation and rig files (*.gani *.ask *.frig);;All files (*)")
        if not path:
            return
        ext = os.path.splitext(path)[1].lower()
        if ext not in {".gani", ".ask", ".frig"}:
            path = self._file(filters="Animation and rig files (*.gani *.ask *.frig);;All files (*)")
            if not path:
                return
            ext = os.path.splitext(path)[1].lower()
        if ext == ".gani":
            def done(data):
                self._show_animation_report(path, data)

            self._run(_("Inspecting animation..."), lambda: native.animation_report(path), done)
        else:
            self._animation_path = ""
            self._run(_("Inspecting rig..."), lambda: native.rig_inspect(path),
                      lambda data: self._show("assets", data))

    def _show_animation_report(self, path, data):
        self._animation_path = path
        self.animation_rate.setValue(max(1, min(240, int(data.get("rate", 30)))))
        self.animation_tracks.clear()
        for track in data.get("tracks", []):
            unit_item = QTreeWidgetItem([
                f'{track.get("name", "")} [{track.get("index", 0)}]',
                _("Static") if track.get("static") else _("Animated"), "", "",
            ])
            unit_item.setData(0, Qt.UserRole, {"unit": track.get("index", 0)})
            self.animation_tracks.addTopLevelItem(unit_item)
            for segment_index, segment in enumerate(track.get("segments", [])):
                item = QTreeWidgetItem([
                    str(segment.get("id", segment_index)), str(segment.get("kind", "")),
                    str(segment.get("keys", "")),
                    f'{segment.get("first", "")} / {segment.get("last", "")}',
                ])
                item.setData(0, Qt.UserRole, {
                    "unit": track.get("index", 0), "segment": segment_index,
                    "segment_data": segment,
                })
                unit_item.addChild(item)
        self.animation_tracks.expandToDepth(0)
        self._show("assets", data)

    def select_animation_segment(self):
        items = self.animation_tracks.selectedItems()
        if not items:
            return
        data = items[0].data(0, Qt.UserRole) or {}
        segment = data.get("segment_data")
        if segment:
            self.key_index.setMaximum(max(0, int(segment.get("keys", 1)) - 1))
            self._show("assets", {"selected_unit": data.get("unit"),
                                  "selected_segment": data.get("segment"), **segment})

    def set_animation_key(self):
        items = self.animation_tracks.selectedItems()
        if not self._animation_path or not items:
            self.say(_("Inspect an animation and select a segment first."), "warn")
            return
        data = items[0].data(0, Qt.UserRole) or {}
        if "segment" not in data:
            self.say(_("Select an animation segment, not a unit."), "warn")
            return
        try:
            parts = [int(value.strip()) for value in self.key_parts.text().split(",")]
            if len(parts) != 3 or any(value < 0 or value > 0xFFFFFFFF for value in parts):
                raise ValueError("enter exactly three unsigned 32-bit values")
            signs = [value.strip().lower() for value in self.key_signs.text().split(",")]
            if len(signs) != 3 or any(value not in {"true", "false", "1", "0"} for value in signs):
                raise ValueError("enter exactly three true/false signs")
        except ValueError as error:
            self.say(_("Invalid quaternion values: %s") % error, "warn")
            return
        signs = [value in {"true", "1"} for value in signs]
        unit, segment, key = data["unit"], data["segment"], self.key_index.value()
        if not ask(self, "Set animation key",
                   _("Update unit %(unit)d, segment %(segment)d, key %(key)d? A restore point is made first.")
                   % {"unit": unit, "segment": segment, "key": key}):
            return
        path = self._animation_path
        if not self._can_edit_game_assets():
            return

        def done(result):
            self._show("assets", result)
            self._run(_("Refreshing animation tracks..."),
                      lambda: native.animation_report(path),
                      lambda report: self._show_animation_report(path, report))

        self._run(_("Updating animation key..."),
                  self._in_place(path, "animation key",
                                 lambda: native.animation_set_key(path, unit, segment, key, parts, signs)),
                  done)

    def set_animation_rate(self):
        path = self._animation_path
        if not path or os.path.splitext(path)[1].lower() != ".gani":
            self.say(_("Select a .gani animation first."), "warn")
            return
        rate = self.animation_rate.value()
        if not self._can_edit_game_assets():
            return
        if not ask(self, "Set animation rate",
                   _("Change the frame rate of %s to %d? A restore point is made first.") % (path, rate)):
            return
        self._run(_("Updating animation rate..."),
                  self._in_place(path, "animation frame rate",
                                 lambda: native.animation_set_rate(path, rate)),
                  lambda result: self._show("assets", {"previous_rate": result[0],
                                                        "new_rate": result[1]}))

    def replace_asset(self):
        path = self._selected_asset_path()
        if not path:
            path = self._file(filters="FTEX textures (*.ftex);;All files (*)")
        if not path:
            return
        entry = self._selected_asset_entry()
        if os.path.splitext(path)[1].lower() != ".ftex" or (entry and not entry.get("editable")):
            self.say(_("Choose an .ftex asset to replace."), "warn")
            return
        source = self._file(title="Choose replacement image", filters="Images (*.png *.dds *.tga *.bmp)")
        if not source:
            return
        image = QImage(source).convertToFormat(QImage.Format_RGBA8888)
        if image.isNull():
            self.say(_("Could not read the selected replacement image."), "err")
            return
        width, height = image.width(), image.height()
        rgba = bytes(image.constBits())[:image.sizeInBytes()]
        if not self._can_edit_game_assets():
            return
        if not ask(self, "Replace texture",
                   _("Replace %s with this image? A restore point is made first, and the size must match.")
                   % path):
            return
        self._run(_("Replacing texture..."),
                  self._in_place(path, "texture replaced",
                                 lambda: native.asset_replace(path, width, height, rgba)),
                  lambda result: self._show("assets", result))

    def _selected_asset_path(self):
        items = self.asset_tree.selectedItems()
        entry = items[0].data(0, Qt.UserRole) if items else {}
        return entry.get("path", "") if isinstance(entry, dict) else ""

    def _selected_asset_entry(self):
        items = self.asset_tree.selectedItems()
        entry = items[0].data(0, Qt.UserRole) if items else {}
        return entry if isinstance(entry, dict) else {}


    def _choose_into(self, field, title):
        directory = pick_dir(self, title, field.text().strip())
        if directory:
            field.setText(directory)

    def _choose_file_into(self, field, filters="All files (*)"):
        path = self._file(start=field.text().strip(), filters=filters)
        if path:
            field.setText(path)

    def refresh(self):
        if not hasattr(self, "tabs") or self.tabs.count() == 0:
            return
        return

    def refresh_current(self):
        index = self.tabs.currentIndex()
        handlers = (self.inspect_cpk, self.inspect_texture, self.list_assets)
        if 0 <= index < len(handlers):
            handlers[index]()

