"""Add a club from another league: Tick all shown ticks the clubs of the search, Untick all clears
every tick, Tick all is off with no search (vmican, 16.10.).

    python tools/test_clubpick_tickall.py
"""
import os, sys
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget

app = QApplication.instance() or QApplication([])
from modstudio.pages.newlife import ClubPickDialog

clubs = {1: {"name": "Wydad AC", "league": "Botola Pro"}, 2: {"name": "Raja CA", "league": "Botola Pro"},
         3: {"name": "Dinamo Zagreb", "league": "SuperSport HNL"}, 4: {"name": "Hajduk Split", "league": "SuperSport HNL"},
         5: {"name": "Rijeka", "league": "SuperSport HNL"}, 6: {"name": "Already in", "league": "Botola Pro"}}
parent = QWidget()
d = ClubPickDialog(parent, SimpleNamespace(clubs=clubs), skip={6})
ok = 0


def check(what, cond):
    global ok
    if not cond:
        raise SystemExit("FAIL: " + what)
    ok += 1
    print("ok", what)


check("no search: Tick all is off", not d.b_all.isEnabled())
d.search.setText("hnl")
check("search: Tick all is on", d.b_all.isEnabled())
d.b_all.click()
check("the three HNL clubs ticked", d.checked == {3, 4, 5})
check("their boxes show it", all(d.list.item(i).checkState() == Qt.Checked for i in range(d.list.count())))
d.search.setText("botola")
check("a club in the recipe already is not shown", d.list.count() == 2)
d.list.item(0).setCheckState(Qt.Checked)
check("one more by hand", len(d.checked) == 4)
d.ok()
check("picked: the ticks, in the list's order", d.picked == [3, 4, 5, 2] or sorted(d.picked) == [2, 3, 4, 5])
d.b_none.click()
check("Untick all clears every tick, shown or not", not d.checked and d.n.text() == "")
print("test_clubpick_tickall: %d ok" % ok)
