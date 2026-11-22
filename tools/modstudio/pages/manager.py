"""Rust-backed Football Life tools, organized into the original manager sections."""
import json
import os

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QImage, QPixmap
from PySide6.QtWidgets import (QComboBox, QFileDialog, QInputDialog, QLabel, QLineEdit,
                               QPlainTextEdit, QPushButton, QSpinBox, QSplitter, QTabWidget,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from .. import native
from ..i18n import _
from ..siderini import norm, root_path
from ..ui import Page, ask, hint, pick_dir, run_job, row


def _report(value):
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


class ModManager(Page):
    title = "Mod Manager"
    hint = ("Rust-backed Football Life tools, separated by task. Reports are read-only; operations "
            "that change files or Sider settings ask before applying.")

    def __init__(self, app):
        super().__init__(app)
        self.action("Refresh", self.refresh_current, tip="Reload the current tab's data")
        self._studio_text_path = ""
        self._studio_dirty = False
        self._studio_selection = ""
        self._studio_nodes = []
        self._asset_entries = []
        self._animation_path = ""
        self.tabs = QTabWidget()
        self.outer.addWidget(self.tabs, 1)
        self.outputs = {}
        self._make_map_tab()
        self._make_order_tab()
        self._make_conflicts_tab()
        self._make_cpk_tab()
        self._make_texture_tab()
        self._make_tables_tab()
        self._make_assets_tab()
        self._make_menu_tab()
        self._make_studio_tab()
        self.tabs.currentChanged.connect(lambda _index: self.refresh())

    def _tab(self, title):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        self.tabs.addTab(page, _(title))
        return layout

    def _output(self, key, parent, readonly=True):
        box = QPlainTextEdit()
        box.setObjectName("log")
        box.setReadOnly(readonly)
        box.setLineWrapMode(QPlainTextEdit.NoWrap)
        parent.addWidget(box, 1)
        self.outputs[key] = box
        return box

    def _show(self, key, value):
        target = self.outputs.get(key)
        if target is not None:
            target.setPlainText(value if isinstance(value, str) else _report(value))

    def _run(self, label, work, done):
        if not native.available():
            self.say(_("The Rust manager extension is not installed. Rebuild the app with its PyO3 module."), "err")
            return
        self.app.busy(True, _(label))

        def finish(result):
            self.app.busy(False)
            self.say("")
            done(result)

        def fail(traceback_text):
            self.app.busy(False)
            message = traceback_text.strip().splitlines()
            self.say(_("Mod Manager operation failed:") + "\n" + (message[-1] if message else traceback_text), "err")

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

    def _make_map_tab(self):
        layout = self._tab("Game map")
        self.map_root = QLineEdit(self._game_folder())
        self.map_root.setPlaceholderText(_("Game folder"))
        browse = QPushButton(_("Choose folder..."))
        browse.clicked.connect(lambda: self._choose_into(self.map_root, _("Choose the game folder")))
        load = QPushButton(_("Build game map"))
        load.clicked.connect(self.load_game_map)
        self.map_path = QLineEdit()
        self.map_path.setPlaceholderText(_("Explain a game or content path"))
        explain = QPushButton(_("Explain path"))
        explain.clicked.connect(self.explain_game_path)
        layout.addWidget(row(self.map_root, browse, load, stretch=False))
        layout.addWidget(row(self.map_path, explain, stretch=False))
        split = QSplitter(Qt.Horizontal)
        self.map_tree = QTreeWidget()
        self.map_tree.setHeaderLabels([_("Component"), _("Kind"), _("Files"), _("Size")])
        self.map_tree.itemSelectionChanged.connect(self.show_map_node)
        self.map_tree.itemDoubleClicked.connect(self.open_map_node)
        split.addWidget(self.map_tree)
        detail = QWidget()
        dv = QVBoxLayout(detail)
        dv.setContentsMargins(0, 0, 0, 0)
        dv.addWidget(hint(_("Select a component to inspect its mapped paths and files.")))
        self._output("map", dv)
        split.addWidget(detail)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 1)
        layout.addWidget(split, 1)

    @staticmethod
    def _map_size(size):
        size = int(size or 0)
        for unit in (_("B"), _("KiB"), _("MiB"), _("GiB"), _("TiB")):
            if size < 1024 or unit == _("TiB"):
                return _("%(size).1f %(unit)s") % {"size": size, "unit": unit}
            size /= 1024

    def _add_map_nodes(self, parent, nodes):
        for node in nodes:
            info = node.get("info") or {}
            item = QTreeWidgetItem([
                str(node.get("name", node.get("rel", ""))),
                str(info.get("format") or node.get("group", "")),
                str(node.get("files", "")),
                self._map_size(node.get("bytes", 0)),
            ])
            item.setData(0, Qt.UserRole, node)
            parent.addChild(item) if isinstance(parent, QTreeWidgetItem) else parent.addTopLevelItem(item)
            self._add_map_nodes(item, node.get("children") or [])

    def load_game_map(self):
        root = self.map_root.text().strip()
        if not root:
            self.say(_("Choose the game folder first."), "warn")
            return
        if not os.path.isdir(root):
            self.say(_("The selected game folder does not exist or is not a directory."), "err")
            return

        def done(data):
            self.map_tree.clear()
            nodes = data.get("nodes", [])
            if not nodes:
                self.say(_("No game files were found here. Choose the folder containing Data or SiderAddons."),
                         "err")
                self._show("map", data)
                return
            self._add_map_nodes(self.map_tree, nodes)
            self.map_tree.expandToDepth(1)
            self.say("")
            self._show("map", {
                "game": data.get("game", root),
                "archives": data.get("archives", 0),
                "archive_bytes": self._map_size(data.get("archive_bytes", 0)),
                "findings": data.get("findings", []),
            })

        self._run(_("Building the game map..."), lambda: native.game_map(root), done)

    def show_map_node(self):
        items = self.map_tree.selectedItems()
        if items:
            node = items[0].data(0, Qt.UserRole) or {}
            self._show("map", {
                "name": node.get("name"),
                "path": node.get("path"),
                "group": node.get("group"),
                "info": node.get("info", {}),
                "files": node.get("files", 0),
                "bytes": self._map_size(node.get("bytes", 0)),
                "children": len(node.get("children") or []),
                "open_as": node.get("open_as"),
            })

    def open_map_node(self, item, _column=0):
        node = item.data(0, Qt.UserRole) or {}
        action = node.get("open_as")
        if action == "cpk":
            path = node.get("path", "")
            if path:
                self.cpk_path.setText(path)
                self.tabs.setCurrentIndex(next(
                    (i for i in range(self.tabs.count())
                     if self.tabs.tabText(i) == _("CPK archives")), 0
                ))
                self.inspect_cpk()
        elif action == "packs":
            self.tabs.setCurrentIndex(next(
                (i for i in range(self.tabs.count())
                 if self.tabs.tabText(i) == _("Pack order")), 0
            ))
            self.scan_packs()

    def explain_game_path(self):
        path = self.map_path.text().strip()
        if not path:
            return
        self._run(_("Explaining path..."), lambda: native.explain_path(path),
                  lambda data: self._show("map", data))

    def _make_order_tab(self):
        layout = self._tab("Pack order")
        self.order_tree = QTreeWidget()
        self.order_tree.setRootIsDecorated(False)
        self.order_tree.setAlternatingRowColors(True)
        self.order_tree.setHeaderLabels([_("#"), _("Pack path"), _("State")])
        self.order_tree.setColumnWidth(0, 50)
        self.order_tree.setColumnWidth(2, 100)
        self.order_summary = QLabel()
        self.order_summary.setWordWrap(True)
        scan = QPushButton(_("Scan and verify"))
        scan.clicked.connect(self.scan_packs)
        sort = QPushButton(_("Suggest order"))
        sort.clicked.connect(self.suggest_order)
        up = QPushButton(_("Move up"))
        up.clicked.connect(lambda: self.move_order(-1))
        down = QPushButton(_("Move down"))
        down.clicked.connect(lambda: self.move_order(1))
        apply_button = QPushButton(_("Apply order"))
        apply_button.setObjectName("primary")
        apply_button.clicked.connect(self.apply_order)
        layout.addWidget(row(scan, sort, up, down, apply_button, stretch=False))
        layout.addWidget(self.order_summary)
        layout.addWidget(self.order_tree, 1)
        self._output("order", layout)

    def _current_order(self):
        return [self.order_tree.topLevelItem(i).text(1)
                for i in range(self.order_tree.topLevelItemCount())]

    def _fill_order(self, values, active=None):
        self.order_tree.clear()
        for index, value in enumerate(values):
            state = "Active" if active is None or value in active else "Disabled"
            self.order_tree.addTopLevelItem(QTreeWidgetItem([str(index + 1), value, _(state)]))

    def scan_packs(self):
        ini = self.app.ini()
        if ini is None:
            self.say(_("No sider.ini is available for this game."), "err")
            return
        addons = self._addons()

        def work():
            return native.scan(ini.path, addons), native.verify(ini.path, addons)

        def done(result):
            scan, verify = result
            self._fill_order([entry.value for entry in ini.entries("cpk.root")],
                             {entry.value for entry in ini.entries("cpk.root") if entry.enabled})
            self.order_summary.setText(
                _("Active packs: %(packs)d; modules: %(modules)d; missing: %(missing)d; duplicates: %(duplicates)d. "
                  "Order analysis: %(effective)d effective, %(partial)d partial, %(dead)d fully shadowed.")
                % {"packs": len(scan["active_packs"]), "modules": len(scan["active_modules"]),
                   "missing": len(scan["missing"]), "duplicates": len(scan["duplicates"]),
                   "effective": verify["effective"], "partial": verify["partial"], "dead": verify["dead"]})
            self._show("order", {"scan": scan, "order_analysis": verify})

        self._run(_("Scanning Sider packs..."), work, done)

    def suggest_order(self):
        game = getattr(self.app, "game", None)
        ini = self.app.ini()
        if ini is None or not getattr(game, "ini_path", ""):
            self.say(_("No sider.ini is available for this game."), "err")
            return

        def done(values):
            self._fill_order(values, {entry.value for entry in ini.entries("cpk.root") if entry.enabled})
            self._show("order", {"suggested_order": values,
                                 "note": _("Suggestion only. Review it, then choose Apply order.")})

        self._run(_("Calculating suggested pack order..."),
                  lambda: native.sorted_roots(game.ini_path, self._addons()), done)

    def move_order(self, delta):
        current = self.order_tree.currentIndex().row()
        target = current + delta
        if current < 0 or target < 0 or target >= self.order_tree.topLevelItemCount():
            return
        item = self.order_tree.takeTopLevelItem(current)
        self.order_tree.insertTopLevelItem(target, item)
        self.order_tree.setCurrentItem(item)
        for i in range(self.order_tree.topLevelItemCount()):
            self.order_tree.topLevelItem(i).setText(0, str(i + 1))

    def apply_order(self):
        values = self._current_order()
        if not values:
            self.say(_("Scan the Sider packs before applying an order."), "warn")
            return
        if not ask(self, "Apply pack order",
                   _("This reorders cpk.root lines in sider.ini. A backup will be made first. Continue?")):
            return
        ini = self.app.ini()
        if ini is None:
            self.say(_("No sider.ini is available for this game."), "err")
            return
        current = [entry.value for entry in ini.entries("cpk.root")]
        if sorted(map(norm, current)) != sorted(map(norm, values)):
            self.say(_("The pack list changed since the scan. Scan again before applying."), "err")
            return
        addons = self._addons()
        base = os.path.normcase(os.path.abspath(os.path.join(addons, "livecpk", "root")))
        base_values = [entry.value for entry in ini.entries("cpk.root")
                       if os.path.normcase(os.path.abspath(root_path(addons, entry.value))) == base]
        if base_values and values[-len(base_values):] != base_values:
            self.say(_("The base livecpk root must stay last in the pack order."), "err")
            return
        ini.reorder("cpk.root", values)
        self.app.save_ini(ini, "Rust Mod Manager pack order")
        self.say(_("Pack order saved. Restart the game to use it."), "ok")

    def _make_conflicts_tab(self):
        layout = self._tab("Conflicts")
        self.conflict_root = QLineEdit(os.path.join(self._addons(), "livecpk", "root"))
        self.conflict_root.setPlaceholderText(_("Folder containing packs"))
        browse = QPushButton(_("Choose folder..."))
        browse.clicked.connect(lambda: self._choose_into(self.conflict_root, _("Choose the pack folder")))
        run = QPushButton(_("Find conflicts"))
        run.clicked.connect(self.find_conflicts)
        layout.addWidget(row(self.conflict_root, browse, run, stretch=False))
        self._output("conflicts", layout)

    def find_conflicts(self):
        root = self.conflict_root.text().strip()
        if not root:
            self.say(_("Choose a folder containing packs."), "warn")
            return
        self._run(_("Finding file conflicts..."), lambda: native.conflicts(root),
                  lambda report: self._show("conflicts", report))

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
        self.cpk_filter = QLineEdit()
        self.cpk_filter.setPlaceholderText(_("Filter archive paths"))
        self.cpk_filter.textChanged.connect(self.filter_cpk_entries)
        layout.addWidget(self.cpk_filter)
        self.cpk_entries = QTreeWidget()
        self.cpk_entries.setHeaderLabels([_("Path"), _("Stored bytes"), _("Unpacked bytes"), _("Compressed")])
        layout.addWidget(self.cpk_entries, 1)
        self._output("cpk", layout)

    def filter_cpk_entries(self):
        query = self.cpk_filter.text().strip().casefold()
        for index in range(self.cpk_entries.topLevelItemCount()):
            item = self.cpk_entries.topLevelItem(index)
            item.setHidden(bool(query and query not in item.text(0).casefold()))

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
        for path, stored, unpacked, compressed in data.get("files", []):
            item = QTreeWidgetItem([str(path), str(stored), str(unpacked), str(compressed)])
            self.cpk_entries.addTopLevelItem(item)
        self.filter_cpk_entries()
        self._show("cpk", {key: value for key, value in data.items() if key != "files"})

    def map_cpk(self):
        path = self.cpk_path.text().strip()
        if not path:
            path = self._file(filters="CPK archives (*.cpk);;All files (*)")
        if not path:
            return
        self.cpk_path.setText(path)
        self._run(_("Mapping CPK archive..."), lambda: native.archive_map(path),
                  lambda data: self._show("cpk", data))

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

    def _make_tables_tab(self):
        layout = self._tab("Tables")
        self.pesdb_dir = QLineEdit()
        self.pesdb_dir.setPlaceholderText(_("Folder containing PESDB tables"))
        browse_dir = QPushButton(_("Choose folder..."))
        browse_dir.clicked.connect(lambda: self._choose_into(self.pesdb_dir, _("Choose the tables folder")))
        pesdb = QPushButton(_("Inspect PESDB"))
        pesdb.clicked.connect(self.inspect_pesdb)
        layout.addWidget(row(self.pesdb_dir, browse_dir, pesdb, stretch=False))

        self.container_path = QLineEdit()
        self.container_path.setPlaceholderText(_("WESYS container"))
        browse_container = QPushButton(_("Choose container..."))
        browse_container.clicked.connect(lambda: self._choose_file_into(self.container_path))
        report_container = QPushButton(_("Inspect container"))
        report_container.clicked.connect(self.inspect_container)
        unwrap = QPushButton(_("Unwrap..."))
        unwrap.clicked.connect(self.unwrap_container)
        rewrap = QPushButton(_("Rewrap..."))
        rewrap.clicked.connect(self.rewrap_container)
        layout.addWidget(row(self.container_path, browse_container, report_container, unwrap, rewrap,
                             stretch=False))

        self.binary_path = QLineEdit()
        self.binary_path.setPlaceholderText(_("Binary file"))
        browse_binary = QPushButton(_("Choose binary..."))
        browse_binary.clicked.connect(lambda: self._choose_file_into(self.binary_path))
        inspect_binary = QPushButton(_("Inspect binary"))
        inspect_binary.clicked.connect(self.inspect_binary)
        self.patch_offset = QLineEdit()
        self.patch_offset.setPlaceholderText(_("Offset (decimal)"))
        self.patch_hex = QLineEdit()
        self.patch_hex.setPlaceholderText(_("Bytes (hex)"))
        patch = QPushButton(_("Patch bytes..."))
        patch.clicked.connect(self.patch_binary)
        layout.addWidget(row(self.binary_path, browse_binary, inspect_binary, stretch=False))
        layout.addWidget(row(self.patch_offset, self.patch_hex, patch, stretch=False))
        self.binary_sections = QTreeWidget()
        self.binary_sections.setHeaderLabels([_("Section"), _("Offset"), _("Bytes")])
        self.binary_sections.itemSelectionChanged.connect(self.inspect_binary_section)
        layout.addWidget(self.binary_sections, 1)
        self._output("tables", layout)

    def inspect_pesdb(self):
        directory = self.pesdb_dir.text().strip()
        if not directory:
            directory = pick_dir(self, "Choose the PESDB table folder")
        if directory:
            self.pesdb_dir.setText(directory)
            self._run(_("Inspecting PESDB tables..."), lambda: native.pesdb_report(directory),
                      lambda data: self._show("tables", data))

    def inspect_container(self):
        path = self.container_path.text().strip()
        if not path:
            path = self._file()
        if path:
            self.container_path.setText(path)
            self._run(_("Inspecting container..."), lambda: native.container_report(path),
                      lambda data: self._show("tables", data))

    def unwrap_container(self):
        source = self.container_path.text().strip()
        if not source or not os.path.isfile(source):
            self.say(_("Choose an existing container first."), "warn")
            return
        destination = self._save_file(source + ".body", "Unwrap container", "All files (*)")
        if not destination:
            return
        if os.path.exists(destination):
            self.say(_("The output file already exists; choose a different name."), "err")
            return
        if not ask(self, "Unwrap container", _("Write the container body to %s?") % destination):
            return
        self._run(_("Unwrapping container..."), lambda: native.container_unwrap(source, destination),
                  lambda result: self._show("tables", result))

    def rewrap_container(self):
        body = self._file(title="Choose container body")
        if not body:
            return
        original = self.container_path.text().strip() or self._file(title="Choose original container")
        if not original:
            return
        destination = self._save_file(original + ".rewrapped", "Save rewrapped container")
        if not destination:
            return
        if os.path.exists(destination):
            self.say(_("The output file already exists; choose a different name."), "err")
            return
        if not ask(self, "Rewrap container", _("Create %s using the original container header?") % destination):
            return
        self._run(_("Rewrapping container..."),
                  lambda: native.container_rewrap(body, original, destination),
                  lambda result: self._show("tables", result))

    def inspect_binary(self):
        path = self.binary_path.text().strip()
        if not path:
            path = self._file()
        if path:
            self.binary_path.setText(path)

            def work():
                return native.inspect_binary(path), native.binary_hex(path)

            def done(result):
                report, hex_dump = result
                self.binary_sections.clear()
                table = (report.get("sections") or {}).get("sections", [])
                for index, section in enumerate(table):
                    item = QTreeWidgetItem([
                        str(section.get("name", index)), str(section.get("offset", "")),
                        str(section.get("length", section.get("size", ""))),
                    ])
                    item.setData(0, Qt.UserRole, index)
                    self.binary_sections.addTopLevelItem(item)
                self._show("tables", {"report": report, "body_hex": hex_dump})

            self._run(_("Inspecting binary..."), work, done)

    def inspect_binary_section(self):
        items = self.binary_sections.selectedItems()
        path = self.binary_path.text().strip()
        if not items or not path:
            return
        index = items[0].data(0, Qt.UserRole)

        def work():
            return native.binary_section(path, index), native.binary_section_table(path, index)

        def done(result):
            hex_dump, table = result
            self._show("tables", {"section": items[0].text(0), "table": table, "hex": hex_dump})

        self._run(_("Inspecting binary section..."), work, done)

    def patch_binary(self):
        path = self.binary_path.text().strip()
        try:
            raw_offset = self.patch_offset.text().strip()
            offset = int(raw_offset, 16 if raw_offset.lower().startswith("0x") else 10)
        except ValueError:
            self.say(_("Enter a valid decimal or 0x-prefixed byte offset."), "warn")
            return
        hex_bytes = "".join(self.patch_hex.text().split())
        if not path or not hex_bytes:
            self.say(_("Choose a binary and enter the bytes to write."), "warn")
            return
        if not ask(self, "Patch binary", _("Patch %s at offset %s? A backup will be made.")
                   % (path, self.patch_offset.text().strip())):
            return
        def done(result):
            self._show("tables", {"patch": result, "updated_file": path})
            self.inspect_binary()

        self._run(_("Patching binary..."), lambda: native.patch_binary(path, offset, hex_bytes), done)

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
                   _("Update unit %(unit)d, segment %(segment)d, key %(key)d? The Rust manager backs up the file.")
                   % {"unit": unit, "segment": segment, "key": key}):
            return
        path = self._animation_path

        def done(result):
            self._show("assets", result)
            self._run(_("Refreshing animation tracks..."),
                      lambda: native.animation_report(path),
                      lambda report: self._show_animation_report(path, report))

        self._run(_("Updating animation key..."),
                  lambda: native.animation_set_key(path, unit, segment, key, parts, signs), done)

    def set_animation_rate(self):
        path = self._animation_path
        if not path or os.path.splitext(path)[1].lower() != ".gani":
            self.say(_("Select a .gani animation first."), "warn")
            return
        rate = self.animation_rate.value()
        if not ask(self, "Set animation rate",
                   _("Change the frame rate of %s to %d?") % (path, rate)):
            return
        self._run(_("Updating animation rate..."),
                  lambda: native.animation_set_rate(path, rate),
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
        if not ask(self, "Replace texture",
                   _("Replace %s with this image? The Rust manager makes a backup and checks dimensions.")
                   % path):
            return
        self._run(_("Replacing texture..."),
                  lambda: native.asset_replace(path, width, height, rgba),
                  lambda result: self._show("assets", result))

    def _selected_asset_path(self):
        items = self.asset_tree.selectedItems()
        entry = items[0].data(0, Qt.UserRole) if items else {}
        return entry.get("path", "") if isinstance(entry, dict) else ""

    def _selected_asset_entry(self):
        items = self.asset_tree.selectedItems()
        entry = items[0].data(0, Qt.UserRole) if items else {}
        return entry if isinstance(entry, dict) else {}

    def _make_menu_tab(self):
        layout = self._tab("Menu maker")
        self.menu_root = QLineEdit()
        self.menu_root.setPlaceholderText(_("Folder containing menu screen files"))
        browse = QPushButton(_("Choose menu folder..."))
        browse.clicked.connect(lambda: self._choose_into(self.menu_root, _("Choose menu folder")))
        self.menu_bases = QLineEdit()
        self.menu_bases.setPlaceholderText(_("Base menu folders, separated by semicolons"))
        add_base = QPushButton(_("Add base folder..."))
        add_base.clicked.connect(self.add_menu_base)
        clear_bases = QPushButton(_("Clear"))
        clear_bases.clicked.connect(self.menu_bases.clear)
        check = QPushButton(_("Check menu links"))
        check.clicked.connect(self.check_menu)
        layout.addWidget(row(self.menu_root, browse, check, stretch=False))
        layout.addWidget(row(self.menu_bases, add_base, clear_bases, stretch=False))
        self.menu_screen = QLineEdit()
        self.menu_screen.setPlaceholderText(_("Screen ID"))
        self.menu_event = QLineEdit()
        self.menu_event.setPlaceholderText(_("Event"))
        self.menu_target = QLineEdit()
        self.menu_target.setPlaceholderText(_("Target screen ID"))
        link = QPushButton(_("Set link..."))
        link.clicked.connect(self.set_menu_link)
        layout.addWidget(row(self.menu_screen, self.menu_event, self.menu_target, link, stretch=False))
        self.menu_tree = QTreeWidget()
        self.menu_tree.setHeaderLabels([_("Screen / event"), _("Target")])
        self.menu_tree.itemSelectionChanged.connect(self.select_menu_entry)
        layout.addWidget(self.menu_tree, 1)
        self._output("menu", layout)

    def _menu_base_paths(self):
        return [value.strip() for value in self.menu_bases.text().split(";") if value.strip()]

    def add_menu_base(self):
        directory = pick_dir(self, _("Choose a base menu folder"))
        if not directory:
            return
        values = self._menu_base_paths()
        if directory not in values:
            values.append(directory)
            self.menu_bases.setText("; ".join(values))

    def check_menu(self):
        root = self.menu_root.text().strip()
        if not root:
            self.say(_("Choose the menu folder first."), "warn")
            return
        bases = self._menu_base_paths()

        def done(result):
            self.menu_tree.clear()
            for entry in result.get("entries", []):
                screen = str(entry.get("id", ""))
                screen_item = QTreeWidgetItem([screen, ""])
                screen_item.setData(0, Qt.UserRole, {"screen": screen})
                self.menu_tree.addTopLevelItem(screen_item)
                for event in entry.get("events", []):
                    name = str(event.get("name", ""))
                    target = str(event.get("to", ""))
                    item = QTreeWidgetItem([name, target])
                    item.setData(0, Qt.UserRole, {"screen": screen, "event": name, "target": target})
                    screen_item.addChild(item)
            self.menu_tree.expandToDepth(0)
            self._show("menu", result.get("report", result))

        self._run(_("Checking menu links..."), lambda: native.menu_check(root, bases), done)

    def select_menu_entry(self):
        items = self.menu_tree.selectedItems()
        if not items:
            return
        data = items[0].data(0, Qt.UserRole) or {}
        self.menu_screen.setText(data.get("screen", ""))
        self.menu_event.setText(data.get("event", ""))
        self.menu_target.setText(data.get("target", ""))

    def set_menu_link(self):
        root = self.menu_root.text().strip()
        screen, event, target = (self.menu_screen.text().strip(), self.menu_event.text().strip(),
                                 self.menu_target.text().strip())
        if not all((root, screen, event, target)):
            self.say(_("Choose a menu folder and enter the screen, event, and target."), "warn")
            return
        bases = self._menu_base_paths()
        if not ask(self, "Set menu link",
                   _("Change %(screen)s / %(event)s to point to %(target)s? A backup is made.")
                   % {"screen": screen, "event": event, "target": target}):
            return
        self._run(_("Updating menu link..."),
                  lambda: native.menu_link(root, bases, screen, event, target),
                  lambda result: (self._show("menu", result), self.check_menu()))

    def _make_studio_tab(self):
        layout = self._tab("Mod Studio")
        self.studio_root = QLineEdit(self._addons())
        self.studio_root.setPlaceholderText(_("Mod workspace or pack folder"))
        self.studio_root.textEdited.connect(lambda _text: setattr(self, "_studio_selection", ""))
        browse = QPushButton(_("Choose folder..."))
        browse.clicked.connect(lambda: self._choose_into(self.studio_root, _("Choose workspace")))
        refresh = QPushButton(_("Browse"))
        refresh.clicked.connect(self.load_studio_tree)
        layout.addWidget(row(self.studio_root, browse, refresh, stretch=False))
        self.studio_entries = QComboBox()
        self.studio_entries.setMinimumWidth(220)
        entries = QPushButton(_("Refresh registered packs"))
        entries.clicked.connect(self.load_studio_entries)
        self.studio_mode = QComboBox()
        self.studio_mode.addItems(["up", "down", "enable", "disable", "remove"])
        edit_entry = QPushButton(_("Apply pack-list change..."))
        edit_entry.clicked.connect(self.edit_studio_entry)
        layout.addWidget(row(self.studio_entries, entries, self.studio_mode, edit_entry, stretch=False))
        split = QSplitter(Qt.Horizontal)
        self.studio_tree = QTreeWidget()
        self.studio_tree.setHeaderLabels([_("Name"), _("Kind"), _("Size")])
        self.studio_tree.itemDoubleClicked.connect(self.open_studio_item)
        self.studio_tree.itemSelectionChanged.connect(self.select_studio_item)
        split.addWidget(self.studio_tree)
        editor = QWidget()
        ev = QVBoxLayout(editor)
        ev.setContentsMargins(0, 0, 0, 0)
        self.studio_file = QLabel(_("No file selected"))
        ev.addWidget(self.studio_file)
        self.studio_editor = QPlainTextEdit()
        self.studio_editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.studio_editor.textChanged.connect(self._studio_editor_changed)
        ev.addWidget(self.studio_editor, 1)
        save = QPushButton(_("Save text file..."))
        save.clicked.connect(self.save_studio_file)
        ev.addWidget(save)
        split.addWidget(editor)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 2)
        layout.addWidget(split, 1)
        create_file = QPushButton(_("New file..."))
        create_file.clicked.connect(self.create_studio_file)
        rename = QPushButton(_("Rename..."))
        rename.clicked.connect(self.rename_studio_item)
        remove = QPushButton(_("Delete..."))
        remove.clicked.connect(self.remove_studio_item)
        reveal = QPushButton(_("Open location"))
        reveal.clicked.connect(self.reveal_studio_item)
        layout.addWidget(row(create_file, rename, remove, reveal, stretch=False))
        self.studio_name = QLineEdit()
        self.studio_name.setPlaceholderText(_("New pack name"))
        self.studio_kind = QComboBox()
        self.studio_kind_hint = QLabel()
        self.studio_kind_hint.setWordWrap(True)
        self.studio_kind.currentTextChanged.connect(self.update_studio_kind_hint)
        scaffold = QPushButton(_("Create pack scaffold..."))
        scaffold.clicked.connect(self.create_studio_pack)
        check = QPushButton(_("Validate pack"))
        check.clicked.connect(self.check_studio_pack)
        install = QPushButton(_("Install pack..."))
        install.clicked.connect(self.install_studio_pack)
        layout.addWidget(row(self.studio_name, self.studio_kind, scaffold, check, install, stretch=False))
        layout.addWidget(self.studio_kind_hint)
        self._output("studio", layout)
        if native.available():
            self._run(_("Loading pack types..."), native.studio_kinds, self.set_studio_kinds)

    def set_studio_kinds(self, kinds):
        self.studio_kind.clear()
        self._studio_kinds = {entry.get("kind", ""): entry for entry in kinds}
        self.studio_kind.addItems(self._studio_kinds)
        self.update_studio_kind_hint(self.studio_kind.currentText())

    def update_studio_kind_hint(self, kind):
        entry = getattr(self, "_studio_kinds", {}).get(kind, {})
        self.studio_kind_hint.setText(
            _("Hook: %(hook)s\n%(hint)s\nLayout: %(layout)s")
            % {"hook": entry.get("hook", ""), "hint": entry.get("hint", ""),
               "layout": ", ".join(entry.get("layout", []))}
        )

    def load_studio_tree(self):
        root = self.studio_root.text().strip()
        if not root:
            self.say(_("Choose a workspace folder first."), "warn")
            return

        def done(nodes):
            self._studio_nodes = nodes
            self.studio_tree.clear()
            for node in nodes:
                item = QTreeWidgetItem([node.get("name", ""), _("Folder" if node.get("dir") else "File"),
                                        "" if node.get("dir") else str(node.get("size", ""))])
                item.setData(0, Qt.UserRole, node)
                if node.get("dir"):
                    item.addChild(QTreeWidgetItem(["", "", ""]))
                self.studio_tree.addTopLevelItem(item)
            self._show("studio", {"entries": len(nodes), "root": root})

        self._run(_("Reading workspace..."), lambda: native.studio_tree(root), done)

    def open_studio_item(self, item, _column=0):
        node = item.data(0, Qt.UserRole) or {}
        path = node.get("path", "")
        if node.get("dir"):
            self._studio_selection = path
            self.studio_root.setText(path)
            self.load_studio_tree()
            return
        self._studio_selection = path
        if self._studio_dirty and not ask(self, "Unsaved changes",
                                          _("Discard unsaved changes in the current text file?")):
            return

        def done(file_info):
            self._studio_text_path = file_info.get("path", path)
            self._studio_dirty = False
            self.studio_file.setText(self._studio_text_path)
            self.studio_editor.blockSignals(True)
            if file_info.get("binary"):
                self.studio_editor.setPlainText("")
                self._show("studio", file_info)
                self.say(_("This is a binary file and cannot be edited as text."), "warn")
            else:
                self.studio_editor.setPlainText(file_info.get("text", ""))
                self.say("")
            self.studio_editor.blockSignals(False)

        self._run(_("Opening text file..."), lambda: native.studio_read(path), done)

    def select_studio_item(self):
        items = self.studio_tree.selectedItems()
        if not items:
            return
        node = items[0].data(0, Qt.UserRole) or {}
        if node:
            self._studio_selection = node.get("path", "")
            self.studio_file.setText(self._studio_selection)

    def _studio_target(self):
        return self._studio_selection or self.studio_root.text().strip()

    def create_studio_file(self):
        root = self.studio_root.text().strip()
        parent = self._studio_target()
        if os.path.isfile(parent):
            parent = os.path.dirname(parent)
        if not root or not parent:
            self.say(_("Choose a workspace folder first."), "warn")
            return
        name, accepted = QInputDialog.getText(self, _("New file"), _("File name:"))
        if not accepted:
            return
        name = name.strip()
        if not name or os.path.basename(name) != name or name in {".", ".."}:
            self.say(_("Enter a file name, not a path."), "warn")
            return
        path = os.path.join(parent, name)
        if not ask(self, "Create file", _("Create the empty file %s?") % path):
            return
        self._run(_("Creating file..."), lambda: native.studio_create_file(path),
                  lambda size: (self._show("studio", {"created": path, "bytes": size}),
                                self.load_studio_tree()))

    def rename_studio_item(self):
        source = self._studio_target()
        root = self.studio_root.text().strip()
        if not source or os.path.normcase(os.path.abspath(source)) == os.path.normcase(os.path.abspath(root)):
            self.say(_("Select an item inside the workspace to rename."), "warn")
            return
        old_name = os.path.basename(source)
        name, accepted = QInputDialog.getText(self, _("Rename item"), _("New name:"), text=old_name)
        if not accepted:
            return
        name = name.strip()
        if not name or os.path.basename(name) != name or name in {".", ".."}:
            self.say(_("Enter a name, not a path."), "warn")
            return
        destination = os.path.join(os.path.dirname(source), name)
        if not ask(self, "Rename item", _("Rename %s to %s?") % (source, destination)):
            return
        self._run(_("Renaming item..."),
                  lambda: native.studio_rename(source, destination, root),
                  lambda result: (self._show("studio", result), self.load_studio_tree()))

    def remove_studio_item(self):
        path = self._studio_target()
        root = self.studio_root.text().strip()
        if not path or not root:
            self.say(_("Select a file or folder inside the workspace first."), "warn")
            return
        if not ask(self, "Delete workspace item",
                   _("Permanently delete %s and its contents?") % path):
            return
        self._run(_("Deleting item..."), lambda: native.studio_remove(path, root),
                  lambda result: (self._show("studio", result), self.load_studio_tree()))

    def reveal_studio_item(self):
        path = self._studio_target() or self.studio_root.text().strip()
        if not path or not os.path.exists(path):
            self.say(_("Select an existing file or folder first."), "warn")
            return
        folder = path if os.path.isdir(path) else os.path.dirname(path)
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(folder)):
            self.say(_("Could not open the selected location."), "err")

    def _studio_editor_changed(self):
        self._studio_dirty = bool(self._studio_text_path)

    def save_studio_file(self):
        path = self._studio_text_path
        if not path:
            self.say(_("Open a text file in the workspace first."), "warn")
            return
        if not ask(self, "Save file",
                   _("Write changes to %s? The save is atomic, but the Rust manager does not create a backup.")
                   % path):
            return
        text = self.studio_editor.toPlainText()

        def done(size):
            self._studio_dirty = False
            self._show("studio", {"saved": path, "bytes": size})

        self._run(_("Saving text file..."), lambda: native.studio_write(path, text), done)

    def create_studio_pack(self):
        addons = self._addons()
        name = self.studio_name.text().strip()
        kind = self.studio_kind.currentText()
        if not name or not addons:
            self.say(_("Select a game folder and enter a pack name."), "warn")
            return
        if not ask(self, "Create pack scaffold",
                   _("Create a new %(kind)s pack named %(name)s under %(root)s?")
                   % {"kind": kind, "name": name, "root": addons}):
            return
        def done(result):
            self.studio_root.setText(result.get("dir", self.studio_root.text()))
            self._studio_selection = self.studio_root.text()
            self._show("studio", result)
            self.load_studio_tree()
            self.load_studio_entries()

        self._run(_("Creating pack scaffold..."), lambda: native.studio_new_pack(addons, name, kind), done)

    def check_studio_pack(self):
        directory = self._studio_target()
        addons = self._addons()
        if not directory or not os.path.isdir(directory) or not addons:
            self.say(_("Select a pack folder in the workspace first."), "warn")
            return
        self._run(_("Validating pack..."),
                  lambda: native.studio_check_pack(directory, addons),
                  lambda result: self._show("studio", result))

    def install_studio_pack(self):
        source = self._studio_target()
        addons = self._addons()
        if not source or not os.path.isdir(source) or not addons:
            self.say(_("Choose the pack folder and select a game folder first."), "warn")
            return
        if not ask(self, "Install pack",
                   _("Install the validated pack from %s into SiderAddons? Existing destinations are refused.")
                   % source):
            return
        self._run(_("Installing pack..."), lambda: native.studio_install(source, addons),
                  lambda result: (self._show("studio", result), self.load_studio_entries()))

    def load_studio_entries(self):
        addons = self._addons()
        if not addons:
            self.say(_("Select a game folder first."), "warn")
            return

        def done(entries):
            self.studio_entries.clear()
            for entry in entries:
                label = entry.get("value", "") if isinstance(entry, dict) else str(entry)
                key = entry.get("key", "") if isinstance(entry, dict) else ""
                self.studio_entries.addItem(label, key)
            self._show("studio", entries)

        self._run(_("Reading registered Sider packs..."), lambda: native.studio_entries(addons), done)

    def edit_studio_entry(self):
        addons = self._addons()
        index = self.studio_entries.currentIndex()
        value = self.studio_entries.currentText()
        key = self.studio_entries.currentData() or value
        mode = self.studio_mode.currentText()
        if not addons or index < 0:
            self.say(_("Refresh the registered pack list and select a pack first."), "warn")
            return

        def preview_done(report):
            if not ask(self, "Change registered pack",
                       _("Review the preview, then apply %(mode)s to %(pack)s? A sider.ini backup is created.")
                       % {"mode": mode, "pack": value}):
                self._show("studio", report)
                return
            self._run(_("Applying pack-list change..."),
                      lambda: native.studio_edit(addons, key, value, mode, True),
                      lambda result: (self._show("studio", result), self.load_studio_entries()))

        self._run(_("Previewing pack-list change..."),
                  lambda: native.studio_edit(addons, key, value, mode, False), preview_done)

    def _choose_into(self, field, title):
        directory = pick_dir(self, title, field.text().strip())
        if directory:
            field.setText(directory)
            if field is self.studio_root:
                self._studio_selection = ""

    def _choose_file_into(self, field, filters="All files (*)"):
        path = self._file(start=field.text().strip(), filters=filters)
        if path:
            field.setText(path)

    def refresh(self):
        if not hasattr(self, "tabs") or self.tabs.count() == 0:
            return
        current = self.tabs.tabText(self.tabs.currentIndex())
        if current == _("Pack order") and self.order_tree.topLevelItemCount() == 0:
            self.scan_packs()
        elif current == _("Game map") and self.map_tree.topLevelItemCount() == 0:
            if self.map_root.text().strip() and native.available():
                self.load_game_map()
        elif current == _("Mod Studio") and self.studio_tree.topLevelItemCount() == 0:
            if self.studio_root.text().strip() and native.available():
                self.load_studio_tree()

    def refresh_current(self):
        index = self.tabs.currentIndex()
        handlers = (self.load_game_map, self.scan_packs, self.find_conflicts, self.inspect_cpk,
                    self.inspect_texture, self._refresh_tables, self.list_assets, self.check_menu,
                    self.load_studio_tree)
        if 0 <= index < len(handlers):
            handlers[index]()

    def _refresh_tables(self):
        if self.pesdb_dir.text().strip():
            self.inspect_pesdb()
        elif self.container_path.text().strip():
            self.inspect_container()
        elif self.binary_path.text().strip():
            self.inspect_binary()
        else:
            self.say(_("Choose a PESDB folder, container, or binary to inspect."), "warn")
