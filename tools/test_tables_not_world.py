r"""python test_tables_not_world.py -- Settings > Use another tables folder refuses a world Mod Studio
builds (B277, jibibi 29.10.: he picked livecpk\_FL26-France\common\etc\pesdb and got "Country.bin
not found"; every Build rewrites that folder). worlds.world_of names the world a folder is in; a
database of your own in livecpk (not _FL26...) and folders outside livecpk stay allowed."""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modstudio import worlds as WL

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


G = r"E:\Program Files (x86)\SP Football Life 2026\Sider\Patch_Final_Whistle\livecpk"
ok("the world's pesdb is in the world", WL.world_of(G + r"\_FL26-France\common\etc\pesdb") == "_FL26-France")
ok("the world folder itself", WL.world_of(G + r"\_FL26M2400E") == "_FL26M2400E")
ok("case of livecpk does not matter", WL.world_of(G.replace("livecpk", "LiveCPK") + r"\_FL26X\common") == "_FL26X")
ok("a database mod in livecpk is not a world", WL.world_of(G + r"\UML\common\etc\pesdb") is None)
ok("a Build's work folder is not a world", WL.world_of(G + r"\_FL26X.building\common") is None)
ok("a folder outside livecpk", WL.world_of(r"C:\Users\jb\Documents\FL26-France\pesdb") is None)
ok("an _FL26 folder not under livecpk", WL.world_of(r"D:\backup\_FL26-France\common\etc\pesdb") is None)

# the page asks world_of before it takes the folder
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "modstudio", "pages", "settings.py"),
          encoding="utf-8") as f:
    src = f.read()
pick = src[src.index("def pick_tables"):]
ok("pick_tables refuses a world before it stores the folder",
   pick.index("world_of(d)") < pick.index('self.app.settings["tables"] = d'))

# the page itself, offscreen: the folder dialog answers a world, the box says so, nothing is taken
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import types
from PySide6.QtWidgets import QApplication
qa = QApplication.instance() or QApplication([])
from modstudio.pages import settings as SP
said, loads = [], []
SP.error = lambda parent, title, text: said.append(text)
SP.info = lambda parent, title, text: said.append(text)
pick = {"d": G + r"\_FL26-France\common\etc\pesdb"}
SP.QFileDialog.getExistingDirectory = staticmethod(lambda *a, **k: pick["d"])
page = types.SimpleNamespace(app=types.SimpleNamespace(
    settings={}, project=types.SimpleNamespace(load_tables=lambda d=None: loads.append(d) or None,
                                               tables_error="no tables in that folder", overlay=0)),
    refresh=lambda: None)
SP.Settings.pick_tables(page)
ok("a world: one box naming the world", len(said) == 1 and "_FL26-France" in said[0] and "Build" in said[0])
ok("a world: the tables setting is not touched", "tables" not in page.app.settings)
ok("a world: no tables are loaded from it", loads == [])
said.clear()
pick["d"] = r"C:\Users\jb\Documents\FL26-France\pesdb"
SP.Settings.pick_tables(page)
ok("another folder still goes to load_tables", loads[:1] == [pick["d"]])
print("all %d passed" % N)
