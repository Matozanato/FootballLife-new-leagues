r"""python tools/test_club_stadium_kept.py

UI test 15.11.2026 (GigaPack beta 2, beta 4f): a club whose home stadium from the world
("France\Stade Bauer") is not in this PC's stadium pack could not be saved at all -- Edit club
said "No folder France\Stade Bauer in the stadium-server library." on OK, whatever was changed
(name, crest, kits). Build skips such a stadium and the club plays at the game's one
(lbstadiums.find, 0.2.4), so the dialog keeps the world's entry as it was and says so; only a
stadium picked now must be in the library.

StadiumField (builder.py) on a stadium library in a temporary folder; offscreen, no game.
"""
import os, shutil, sys, tempfile
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PySide6.QtWidgets import QApplication

qa = QApplication.instance() or QApplication([])
from modstudio.pages import builder

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def main():
    lib = tempfile.mkdtemp(prefix="fl26-stadlib-")
    try:
        os.makedirs(os.path.join(lib, "France", "Stade de France"))
        os.makedirs(os.path.join(lib, "Europe", "Allianz Arena"))
        world = {"folder": "France\\Stade Bauer", "name": "Stade Bauer", "slot": "12"}

        f = builder.StadiumField(lib, dict(world), None)
        try:
            v = f.value()
        except ValueError as e:
            v = e
        ok("a stadium of the world not in this PC's pack: the club can be saved", isinstance(v, dict))
        ok("and the world keeps the entry as it was", v == {"folder": "France\\Stade Bauer", "name": "Stade Bauer",
                                                            "slot": "012"})
        ok("the field says it is not in the pack", "Not in your stadium pack" in f.shown.text())

        f.name.setText("Bauer")
        ok("its name in the game can still be changed", f.value()["name"] == "Bauer")

        f.folder = "France\\Nowhere"                 # a stadium picked now that is not in the library
        try:
            f.value()
            ok("a stadium picked now must be in the library", False)
        except ValueError as e:
            ok("a stadium picked now must be in the library", "France\\Nowhere" in str(e))

        f.folder = "France\\Stade de France"
        ok("a stadium of the library: saved, no note", f.value()["folder"] == "France\\Stade de France")
        f.update_shown()
        ok("and no 'not in your pack' note", "Not in your stadium pack" not in f.shown.text())

        moved = builder.StadiumField(lib, {"folder": "Germany\\Allianz Arena", "name": "Allianz Arena"}, None)
        moved.update_shown()
        ok("a stadium the pack moved to another region: found, no note",
           "Not in your stadium pack" not in moved.shown.text() and moved.value()["folder"] == "Germany\\Allianz Arena")

        f.clear()
        ok("Game's own: no entry", f.value() == {})

        none = builder.StadiumField(None, dict(world), None)
        ok("without Stadium Server: the entry is kept, no note", none.value()["folder"] == "France\\Stade Bauer"
           and "Not in your stadium pack" not in none.shown.text())
    finally:
        shutil.rmtree(lib, ignore_errors=True)
    print("1..%d" % N)
    print("all passed")


if __name__ == "__main__":
    main()
