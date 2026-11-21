"""Cups > International (feature/cwc32): the Intercontinental is always listed, "Add Club World Cup"
adds the Club World Cup of 32, Apply writes the recipe's club_world_cup (leaguebuilder.cwc_config
reads it), Remove takes it out, a picked cup is unticked, and the old Leagues > More entry opens the
tab. Fake tables and a fake app; never reads or writes a game.
Run: python tools/test_international_tab.py
"""
import os
import sys
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtWidgets import QApplication
from modstudio.project import Project
from modstudio.pages.cups import Cups
from modstudio.pages import international as I
from modstudio.pages.cup_editors import CupConflict
from modstudio import theme
import leaguebuilder as LB

qa = QApplication.instance() or QApplication([])
theme.apply(qa)
N = 0


def ok(name, condition):
    global N
    assert condition, name
    N += 1
    print("ok %d - %s" % (N, name))


class Bus(QObject):
    content_changed = Signal()
    game_changed = Signal()
    ini_changed = Signal()


class App:
    settings = None
    game = SimpleNamespace(livecpk_dir="")

    def __init__(self):
        self.bus = Bus()
        self.project = Project(self)
        self.project.base = None
        self.project.countries = ["Test"]
        self.project.confeds = {"Test": 2}
        self.installs = 0
        self.opened = []
        self.build = SimpleNamespace(do_install=self.install)

    def install(self):
        self.installs += 1

    def page(self, name):
        return self.cups if name == "Cups" else self.build

    def open_page(self, name):
        self.opened.append(name)


def recipe():
    return {"world": "_FLIntlTest",
            "leagues": [{"name": "Alpha", "country": "Test", "clubs": 12, "cup": True, "supercup": True}]}


def items(editor):
    return [editor.list.item(i).data(Qt.UserRole) for i in range(editor.list.count())]


def run():
    app = App()
    project = app.project
    project.recipe = recipe()
    project._forget()
    app.cups = page = Cups(app)
    page.resize(1000, 650)
    page.show()
    page.shown()
    qa.processEvents()
    tabs = [page.tabs.tabText(i) for i in range(page.tabs.count())]
    ok("Cups has the International tab last", tabs[-1] == "International" and len(tabs) == 4)
    page.show_international()
    qa.processEvents()
    sec = page.current_section()
    ok("show_international opens it", sec is page.international_section)
    ed = sec["editor"]
    ok("its editor is the International one", isinstance(ed, I.InternationalEditor))
    ok("the Intercontinental is listed alone at first", items(ed) == [I.IC])
    ok("named Intercontinental Cup", ed.list.item(0).text() == "Intercontinental Cup")
    ok("Add Club World Cup is offered", ed.add_button.isVisibleTo(ed))
    ok("nothing to apply when nothing changed", not ed.dirty_keys() and not page.apply_button.isEnabled())

    ed.add_button.click()
    qa.processEvents()
    ok("Add lists the Club World Cup", items(ed) == [I.IC, I.CWC])
    ok("and hides the button", not ed.add_button.isVisibleTo(ed))
    ok("and selects it", ed.list.currentItem().data(Qt.UserRole) == I.CWC and ed.cwc_body.isVisibleTo(ed))
    ok("the field text names the OFC place", "1 OFC" in I.CWC_FIELD and "4 CAF" in I.CWC_FIELD)
    ok("Apply is on", bool(ed.dirty_keys()) and page.apply_button.isEnabled())
    ed.every.setValue(4)
    ed.first.setValue(2030)
    page.apply_section(sec)
    qa.processEvents()
    c = project.recipe.get("club_world_cup")
    ok("Apply writes club_world_cup", c == {"on": True, "every": 4, "first": 2030, "keep_old": True,
                                            "old_name": "Intercontinental Cup", "replace": None})
    ok("cwc_config takes it", LB.cwc_config(project.recipe)["first"] == 2030)
    ok("turning it on asks for the modules", app.installs == 1)
    ok("the league's cup stays", project.recipe["leagues"][0]["cup"] is True)

    ed = page.current_section()["editor"]
    ok("a new editor shows it as built", items(ed) == [I.IC, I.CWC] and not ed.dirty_keys())
    ed.list.setCurrentRow(0)
    ed.name.setText("Copa Intercontinental FIFA")
    ok("the Intercontinental's name is in the list", ed.list.item(0).text() == "Copa Intercontinental FIFA")
    # a cup to give the Intercontinental its ids: picked in the tree, unticked on Apply
    pick = None
    for i in range(ed.tree.topLevelItemCount()):
        g = ed.tree.topLevelItem(i)
        for k in range(g.childCount()):
            if g.child(k).data(0, Qt.UserRole) == "super:Alpha":
                pick = g.child(k)
    ok("the world's super cup can be picked", pick is not None)
    pick.setSelected(True)
    import modstudio.pages.international as mod
    asked = []
    mod.ask = lambda *a: asked.append(a) or False
    page.apply_section(page.current_section())
    ok("a refused question keeps the draft", asked and project.recipe["leagues"][0]["supercup"] is True
       and page.current_section()["editor"] is ed and ed.dirty_keys())
    mod.ask = lambda *a: True
    page.apply_section(page.current_section())
    c = project.recipe["club_world_cup"]
    ok("Apply with a pick unticks that cup", project.recipe["leagues"][0]["supercup"] is False
       and project.recipe["leagues"][0]["cup"] is True and c["replace"] == "super:Alpha")
    ok("and keeps the name", c["old_name"] == "Copa Intercontinental FIFA")
    ok("the modules are asked for once only", app.installs == 1)

    project._snap_at = 0  # Remove is a user action of its own for Undo
    ed = page.current_section()["editor"]
    ed.list.setCurrentRow(1)
    ed.remove_button.click()
    ok("Remove lists the Intercontinental alone", items(ed) == [I.IC] and ed.add_button.isVisibleTo(ed))
    page.apply_section(page.current_section())
    ok("Apply after Remove takes club_world_cup out", "club_world_cup" not in project.recipe)
    ok("Undo brings it back", project.undo() and project.recipe.get("club_world_cup", {}).get("on") is True)
    qa.processEvents()

    # the old entry (Leagues > More > Club World Cup) opens the tab
    from modstudio.pages.builder import NewLeagues
    fake = SimpleNamespace(app=app)
    NewLeagues.club_world_cup(fake)
    ok("the old entry opens Cups > International", app.opened[-1] == "Cups"
       and page.current_section() is page.international_section)
    print("test_international_tab: ok (%d)" % N)


if __name__ == "__main__":
    run()
