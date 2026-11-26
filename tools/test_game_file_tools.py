r"""python tools/test_game_file_tools.py

The Game file tools page and its optional native module (native.py, mod-manager-rust):

  - a Rust panic reaches Python as pyo3's PanicException, a BaseException: the worker's
    `except Exception` would not see it and the window stayed busy. native.py turns it into a
    RuntimeError; KeyboardInterrupt and SystemExit go through as they are;
  - without the module the page builds, has its three tools, and says the module is missing;
  - an edit that rewrites a game file takes a restore point in SiderAddons\ModStudio\backups
    first (Restore points lists it) and leaves no <file>.fl27mm-backup next to the game's file;
  - native.py offers nothing that writes sider.ini (pack install, pack order, menus, text files).

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
for gone in ("studio_install", "studio_edit", "studio_write", "studio_remove", "menu_link",
             "menu_clone", "sorted_roots", "scan", "verify", "conflicts", "patch_binary"):
    assert gone not in public, gone
ok("native.py has no pack install, pack order, menu or text-file writers (%d functions)" % len(public))

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
    assert page.tabs.count() == 3, page.tabs.count()
    assert [page.tabs.tabText(i) for i in range(3)] == ["CPK archives", "Textures", "Assets"]
    ok("the page builds without the module, with its three tools")
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
finally:
    shutil.rmtree(T, ignore_errors=True)

print("test_game_file_tools: ok (%d)" % N)
