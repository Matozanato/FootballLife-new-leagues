r"""python test_world_dirty_card.py -- Delete / Rename world from a card of My world while Content
folders has ticks not written yet (B269, Risto 29.10.: "press Apply or Discard first" and no Apply or
Discard in sight). From a card the box names Content folders and that page opens, with its Apply and
Discard; from Content folders itself the old box stays."""
import os, sys, tempfile, types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
qa = QApplication.instance() or QApplication([])
from modstudio.pages import roots as RP

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


said, opened = [], []
RP.error = lambda parent, title, text: said.append(text)
RP.can_write = lambda parent, game: True
live = tempfile.mkdtemp()
os.mkdir(os.path.join(live, "_FL26Mine"))
page = types.SimpleNamespace(
    renaming=None, dirty=True, _current=lambda: 0, world_of=lambda row: "_FL26Mine",
    app=types.SimpleNamespace(open_page=opened.append,
                              game=types.SimpleNamespace(livecpk_dir=live, running=lambda: (False, False))))

ok("from a card: not ready", RP.Roots._world_ready(page, "Delete world", "_FL26Mine") is None)
ok("from a card: Content folders opens", opened == ["Roots"])
ok("from a card: the box names Content folders", len(said) == 1 and "Content folders" in said[0])
said.clear(), opened.clear()
ok("from Content folders: not ready", RP.Roots._world_ready(page, "Delete world") is None)
ok("from Content folders: no page jump", opened == [])
ok("from Content folders: the old box", said == ["You have changes in this list that are not written yet: "
                                                 "press Apply or Discard first."])
said.clear()
page.dirty = False
ok("nothing waiting: the card's world is ready", RP.Roots._world_ready(page, "Delete world", "_FL26Mine")
   == "_FL26Mine" and said == [] and opened == [])
print("all %d passed" % N)
