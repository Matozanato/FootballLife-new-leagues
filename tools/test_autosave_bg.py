r"""python tools/test_autosave_bg.py

B480: with a big world (the GigaPack's recipe is 260 MB) the window stopped for 2.4 s a moment
after every change: the autosave made the recipe's text on the window's thread (the stall
recorder, 15.11.2026: json.dumps under project._write under autosave). A big recipe is now
written by a worker next to its file and the window only moves it into place; a change made
while the worker wrote throws that text away and the next save writes the world as it is.
A small recipe is saved as before. No game, no window on screen (offscreen)."""
import json, os, shutil, sys, tempfile, time, types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def wait(qa, cond, secs=20):
    end = time.time() + secs
    while not cond() and time.time() < end:
        qa.processEvents()
        time.sleep(0.01)
    return cond()


def main():
    qa = QApplication.instance() or QApplication([])
    from modstudio.project import Project
    import modstudio.app as A
    tmp = tempfile.mkdtemp(prefix="fl26_bg_")
    old_appdir = A.APPDIR
    A.APPDIR = os.path.join(tmp, "appdata")
    try:
        app = types.SimpleNamespace(settings={}, save_settings=lambda: None)
        p = Project(app)
        p.path = os.path.join(tmp, "w.json")
        p.save()
        saved = []
        p.saved.connect(lambda: saved.append(1))

        # small: the timer's save is the plain one, done when it returns
        p.players()["7"] = {"join": ["123"]}
        p.mark()
        p._autosave_bg()
        ok("small world: saved at once, on the spot",
           not p.dirty and getattr(p, "_bg", None) is None
           and json.load(open(p.path, encoding="utf-8"))["players"]["7"] == {"join": ["123"]})

        # big: by the worker
        p.BIG = 1
        p.players()["8"] = {"join": ["5"]}
        p.mark()
        p._autosave_bg()
        ok("big world: the save goes to a worker, the window does not wait", p.dirty and p._bg is not None)
        ok("big world: saved when the worker is done", wait(qa, lambda: not p.dirty) and p._bg is None)
        text = open(p.path, encoding="utf-8").read()
        ok("big world: the file holds the change", json.loads(text)["players"]["8"] == {"join": ["5"]})
        ok("big world: the same text as a plain save writes", text == p._text(p.recipe))
        ok("big world: nothing left next to the file", not os.path.exists(p.path + ".bg.tmp"))

        # a change while the worker writes: that text is not used
        import bigjson
        real = bigjson.dumps
        held = []

        def slow(*a, **k):
            held.append(1)
            end = time.time() + 5
            while len(held) < 2 and time.time() < end:
                time.sleep(0.01)
            return real(*a, **k)
        bigjson.dumps = slow
        try:
            p.players()["9"] = {"join": ["1"]}
            p.mark()
            p._autosave_bg()
            wait(qa, lambda: len(held) == 1)
            p.players()["10"] = {"join": ["2"]}
            p.mark()                                   # changed under the worker
            held.append(2)
            ok("changed meanwhile: the worker's save lands and is not taken",
               wait(qa, lambda: p._bg is None) and p.dirty)
            ok("changed meanwhile: its file is gone", not os.path.exists(p.path + ".bg.tmp"))
            ok("changed meanwhile: the file is still the last full save",
               "10" not in json.load(open(p.path, encoding="utf-8"))["players"])
        finally:
            bigjson.dumps = real
        ok("changed meanwhile: the next save is on its way", p._timer.isActive())
        p._timer.stop()
        p._autosave_bg()
        ok("changed meanwhile: and writes both changes", wait(qa, lambda: not p.dirty)
           and set(json.load(open(p.path, encoding="utf-8"))["players"]) >= {"7", "8", "9", "10"})

        # a plain save while the worker writes wins; the worker's file is thrown away
        held[:] = []
        bigjson.dumps = slow
        try:
            p.players()["11"] = {"join": ["3"]}
            p.mark()
            p._autosave_bg()
            wait(qa, lambda: len(held) == 1)
            p.autosave()
            ok("a save by hand meanwhile: saved at once", not p.dirty)
            held.append(2)
            ok("a save by hand meanwhile: the worker's file is dropped",
               wait(qa, lambda: p._bg is None) and not os.path.exists(p.path + ".bg.tmp")
               and "11" in json.load(open(p.path, encoding="utf-8"))["players"])
        finally:
            bigjson.dumps = real

        # a world without a file of its own: the copy the next start opens
        q = Project(app)
        q.recipe["world"] = "_FL26BgTest"
        q.BIG, q._size = 1, 2
        q.touch()
        q._timer.stop()
        q._autosave_bg()
        copy = os.path.join(A.APPDIR, "recipes", "_FL26BgTest.json")
        ok("no file of its own: the worker writes the kept copy", wait(qa, lambda: not q.dirty)
           and json.load(open(copy, encoding="utf-8"))["world"] == "_FL26BgTest"
           and app.settings.get("last_recipe") == copy and not os.path.exists(copy + ".bg.tmp"))
        print("all %d passed" % N)
    finally:
        A.APPDIR = old_appdir
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
