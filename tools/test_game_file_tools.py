r"""python tools/test_game_file_tools.py

The Game file tools page and its optional native module (native.py, mod-manager-rust):

  - a Rust panic reaches Python as pyo3's PanicException, a BaseException: the worker's
    `except Exception` would not see it and the window stayed busy. native.py turns it into a
    RuntimeError; KeyboardInterrupt and SystemExit go through as they are;
  - without the module the page builds, has its six tools, and says the module is missing;
  - an edit that rewrites a game file takes a restore point in SiderAddons\ModStudio\backups
    first (Restore points lists it) and leaves no <file>.fl27mm-backup next to the game's file;
  - Patch bytes and Set link take the same restore point before they write;
  - native.py offers nothing that writes sider.ini (pack install, pack order).

No game, no native module needed: a fake one stands in for it.
"""
import json, os, shutil, sys, tempfile
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
N = 0


def ok(msg):
    global N
    N += 1
    print("ok %d - %s" % (N, msg))


from modstudio import native, backups

# 1. the panic guard, on a stand-in module
class PanicException(BaseException):
    pass


class Fake:
    def cpk_inspect(self, path):
        raise PanicException("index out of bounds: the len is 4 but the index is 9")

    def texture_info(self, path):
        raise KeyboardInterrupt

    def assets_list(self, root, limit, family):
        return json.dumps([{"path": root}])


guarded = native._Guarded(Fake())
try:
    guarded.cpk_inspect("x.cpk")
    raise AssertionError("the panic went through")
except Exception as e:          # what the worker catches
    assert isinstance(e, RuntimeError) and "index out of bounds" in str(e), e
    caught = str(e)
ok("a panic in the native module arrives as a RuntimeError the worker catches: %s" % caught)
try:
    guarded.texture_info("x.ftex")
    raise AssertionError("KeyboardInterrupt was swallowed")
except KeyboardInterrupt:
    pass
ok("KeyboardInterrupt is not turned into an error")
assert json.loads(guarded.assets_list("r", 1, None)) == [{"path": "r"}]
ok("a call that works returns its value unchanged")

# 2. nothing in the bridge writes sider.ini or edits packs
public = {n for n in dir(native) if not n.startswith("_") and callable(getattr(native, n))}
for gone in ("studio_install", "studio_edit", "studio_write", "studio_remove",
             "sorted_roots", "scan", "verify", "conflicts"):
    assert gone not in public, gone
ok("native.py has no pack install, pack order or sider.ini writers (%d functions)" % len(public))

# 3. the page without the module
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
from modstudio.pages.manager import ModManager, _ReportView

said = []
saved_raw = native._fl27mm
native._fl27mm = None
try:
    page = ModManager(SimpleNamespace(game=SimpleNamespace(folder="", sider_dir="", running=lambda: []),
                                      settings={}, section_of={}, busy=lambda *a: None))
    page.say = lambda text, kind="": said.append((text, kind))
    tools = ["Game map", "CPK archives", "Textures", "Tables", "Assets", "Menu maker"]
    assert [page.tabs.tabText(i) for i in range(page.tabs.count())] == tools
    ok("the page builds without the module, with its %d tools" % len(tools))
    opened = []
    page.app.open_page = opened.append
    page.tabs.roots_link.click()
    assert opened == ["Roots"], opened
    ok("Content folders (pack order) on the tool list opens the Roots page")
    page._run("x", lambda: 1, lambda r: None)
    assert said and said[-1][1] == "err" and "optional native module" in said[-1][0], said
    ok("and says the module is missing when a tool is used")
finally:
    native._fl27mm = saved_raw

report = _ReportView()
report.set_data({"rows": [{"name": "Kit atlas", "status": "Ready"}]})
assert report.tree.objectName() == "jsonReportTree"
assert report.tree.topLevelItem(0).text(0) == "rows"
ok("the report view shows a JSON report as a tree")

# 4. an edit in place: restore point first, no sidecar left
T = tempfile.mkdtemp(prefix="gft-")
try:
    sd = os.path.join(T, "SiderAddons")
    target = os.path.join(sd, "livecpk", "pack", "Asset", "anim.gani")
    os.makedirs(os.path.dirname(target))
    open(os.path.join(sd, "sider.ini"), "w").write("[cpk.root]\n")
    open(target, "wb").write(b"before")

    def edit():                     # what gani::set_frame_rate does: its own copy, then the write
        shutil.copy(target, target + ".fl27mm-backup")
        open(target, "wb").write(b"after")
        return {"backup": target + ".fl27mm-backup"}

    result = ModManager._in_place(target, "animation frame rate", edit)()
    assert open(target, "rb").read() == b"after"
    assert not os.path.exists(target + ".fl27mm-backup")
    rows = backups.history(sd)
    assert len(rows) == 1 and rows[0]["reason"] == "animation frame rate", rows
    copy = os.path.join(sd, rows[0]["copy"])
    assert open(copy, "rb").read() == b"before"
    assert os.path.normcase(result["backup"]) == os.path.normcase(copy), result
    ok("an edit in place leaves a restore point (%s) and no .fl27mm-backup beside the file"
       % rows[0]["file"])

    # a sidecar the user already had is theirs: it stays
    open(target + ".fl27mm-backup", "wb").write(b"theirs")
    ModManager._in_place(target, "texture replaced", lambda: None)()
    assert open(target + ".fl27mm-backup", "rb").read() == b"theirs"
    ok("a .fl27mm-backup that was there before is left alone")

    # a failing edit still leaves the restore point, and no new sidecar
    os.remove(target + ".fl27mm-backup")

    def broken():
        shutil.copy(target, target + ".fl27mm-backup")
        raise native.NativeError("bad file")
    try:
        ModManager._in_place(target, "animation key", broken)()
        raise AssertionError("the error was swallowed")
    except native.NativeError:
        pass
    assert not os.path.exists(target + ".fl27mm-backup")
    assert len(backups.history(sd)) == 3
    ok("a failed edit raises, keeps its restore point and leaves no sidecar")

    # Patch bytes and Set link through the page, with a stand-in module that writes like the real one
    import modstudio.pages.manager as MP
    menu_file = os.path.join(sd, "livecpk", "menu", "common", "script", "flow", "BL", "first.json")
    os.makedirs(os.path.dirname(menu_file))
    open(menu_file, "w").write('{"events": {"back": {"to": "BL/first"}}}')

    class Writer:
        def patch_binary(self, path, offset, hex_bytes):
            open(path, "wb").write(b"patched")
            return json.dumps({"changed": 1, "size": 7})

        def menu_screen_path(self, root, screen):
            return menu_file

        def menu_link(self, root, bases, screen, event, target):
            open(menu_file, "w").write('{"events": {"back": {"to": "%s"}}}' % target)
            return "%s · %s -> %s" % (screen, event, target)

        def menu_check(self, root, bases):
            return json.dumps({"entries": [], "report": {}})

        def inspect_binary(self, path):
            return json.dumps({})

        def binary_hex(self, path, offset, length):
            return ""

    saved = native._fl27mm, MP.ask, MP.run_job
    native._fl27mm = native._Guarded(Writer())
    MP.ask = lambda *a, **k: True
    MP.run_job = lambda fn, done, fail: done(fn(None))
    try:
        page = ModManager(SimpleNamespace(game=SimpleNamespace(folder=T, sider_dir=sd, running=lambda: []),
                                          settings={}, section_of={}, busy=lambda *a: None))
        page.say = lambda *a, **k: None
        page.binary_path.setText(target)
        page.patch_offset.setText("0")
        page.patch_hex.setText("00")
        page.patch_binary()
        page.menu_root.setText(os.path.join(sd, "livecpk", "menu"))
        page.menu_screen.setText("BL/first")
        page.menu_event.setText("back")
        page.menu_target.setText("BL/second")
        page.set_menu_link()
    finally:
        native._fl27mm, MP.ask, MP.run_job = saved
    reasons = [r["reason"] for r in backups.history(sd)]
    assert "binary patched" in reasons and "menu link" in reasons, reasons
    assert "BL/second" in open(menu_file).read()
    menu_copy = [r for r in backups.history(sd) if r["reason"] == "menu link"][0]
    assert "BL/first" in open(os.path.join(sd, menu_copy["copy"])).read()
    ok("Patch bytes and Set link each take a restore point of the file before writing it")
finally:
    shutil.rmtree(T, ignore_errors=True)

print("test_game_file_tools: ok (%d)" % N)
