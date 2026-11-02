r"""python test_tables_per_game.py -- B307 (02.11.): the game's tables are kept per game. One
%APPDATA%\FL26ModStudio\tables for both made a switch from FL26 to FL27 (Settings > Game folder)
build FL27's world from FL26's tables -- its players, its ids -- and back, until Unpack was pressed
again. FL26's stay in tables (the folder of every Mod Studio before), FL27's go in tables27, and a
tables folder picked by hand is remembered for each game on its own. A game whose tables are not
unpacked yet gets them on the switch (auto_tables: no tables loaded)."""
import os, shutil, sys, tempfile, types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
qa = QApplication.instance() or QApplication([])
from modstudio import project as P
from modstudio.app import APPDIR

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


T = tempfile.mkdtemp(prefix="fl26tables-")
try:
    g26, g27, both = (os.path.join(T, n) for n in ("FL26", "FL27", "both"))
    for d, exes in ((g26, ["FL_2026.exe"]), (g27, ["FL_2027.exe"]), (both, ["FL_2026.exe", "FL_2027.exe"])):
        os.makedirs(d)
        for e in exes:
            open(os.path.join(d, e), "wb").close()
    settings = {}
    app = types.SimpleNamespace(settings=settings, game=types.SimpleNamespace(folder=g26))
    p = P.Project(app)

    ok("FL26: the tables folder of every Mod Studio before", p.tables_dir() == os.path.join(APPDIR, "tables"))
    ok("FL26: its setting is the old one", P.tables_key(app.game) == "tables")
    app.game = types.SimpleNamespace(folder=g27)
    ok("FL27: a tables folder of its own", p.tables_dir() == os.path.join(APPDIR, "tables27"))
    ok("FL27: a setting of its own", P.tables_key(app.game) == "tables_fl27")
    app.game = types.SimpleNamespace(folder=both)
    ok("a folder with both exes is FL26's (game.is_fl27)", p.tables_dir() == os.path.join(APPDIR, "tables"))
    app.game = types.SimpleNamespace(folder="")
    ok("no game folder yet: FL26's", p.tables_dir() == os.path.join(APPDIR, "tables"))
    app.game = None
    ok("no game at all (a test's stand-in app): FL26's", P.tables_key(None) == "tables" and
       p.tables_dir() == os.path.join(APPDIR, "tables"))

    # a tables folder picked by hand stays with its game
    settings["tables"] = r"C:\db\FL26-UML\pesdb"
    app.game = types.SimpleNamespace(folder=g26)
    ok("FL26 reads the folder picked for it", p.own_tables() == r"C:\db\FL26-UML\pesdb")
    app.game = types.SimpleNamespace(folder=g27)
    ok("FL27 does not take FL26's folder", p.own_tables() is None)
    settings["tables_fl27"] = r"C:\db\FL27-UML\pesdb"
    ok("FL27 reads its own", p.own_tables() == r"C:\db\FL27-UML\pesdb")
    app.game = types.SimpleNamespace(folder=g26)
    ok("and FL26 keeps its own", p.own_tables() == r"C:\db\FL26-UML\pesdb")

    # load_tables reads the folder of the game in use: FL27 with nothing unpacked has no tables, so
    # the switch unpacks them (app.auto_tables), never FL26's
    for k in ("tables", "tables_fl27"):
        settings.pop(k, None)
    seen = []
    real = P.Project._default_tables
    P.Project._default_tables = lambda self: seen.append(self.tables_dir()) or real(self)
    app.game = types.SimpleNamespace(folder=g27)
    p.load_tables()
    P.Project._default_tables = real
    ok("FL27: load_tables looks in tables27: %s" % seen, seen[:1] == [os.path.join(APPDIR, "tables27")])
    if not os.path.isdir(os.path.join(APPDIR, "tables27")):
        ok("nothing unpacked for FL27: no tables, so auto_tables unpacks them", p.base is None)

    # Settings, auto_tables and Build's check read the setting of the game in use
    here = os.path.dirname(os.path.abspath(__file__))
    for f, gone in (("modstudio/pages/settings.py", 'settings["tables"]'), ("modstudio/pages/settings.py", 'pop("tables"'),
                    ("modstudio/app.py", 'settings.get("tables")'), ("modstudio/pages/builder.py", 'settings.get("tables")'),
                    ("modstudio/project.py", 'settings.get("tables")')):
        src = open(os.path.join(here, f), encoding="utf-8").read()
        ok("%s no longer reads the one setting for both games (%s)" % (f, gone), gone not in src)
finally:
    shutil.rmtree(T, ignore_errors=True)
print("test_tables_per_game: ok (%d)" % N)
