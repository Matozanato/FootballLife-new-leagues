"""Offline CUPS editors: drafts, field patches, legacy recipes, navigation and Project undo.

Uses fake domestic league metadata and temp autosave files; never reads or writes a game.
Run: python tools/test_cups_page.py
"""
import copy
import json
import os
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication, QDialog
from modstudio.project import Project
from modstudio.pages import builder as B
from modstudio.pages.cups import Cups
from modstudio.pages.cup_editors import GameCupsEditor, OurCupsEditor, CupConflict
from modstudio import theme

qa = QApplication.instance() or QApplication([])
# Windows' offscreen platform may expose no system fonts. Load the normal UI fonts
# explicitly for meaningful size checks and optional visual captures in that environment.
if not QFontDatabase.families() and os.name == "nt":
    for name in ("segoeui.ttf", "seguisb.ttf"):
        QFontDatabase.addApplicationFont(os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts", name))
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

    def __init__(self):
        self.bus = Bus()
        self.project = Project(self)
        self.project.base = "fake-tables"
        self.project.countries = ["Test"]
        self.project.confeds = {"Test": 2}
        self.opened = []

    def page(self, name):
        return self.cups if name == "Cups" else SimpleNamespace(
            competition_names=lambda: self.opened.append("names"),
            competition_ids=lambda: self.opened.append("ids"),
            trophies=lambda: self.opened.append("trophies"))

    def open_page(self, name):
        self.opened.append(name)


def recipe():
    return {"world": "_FL26CupsTest", "players": {"untouched": {"large": [1, 2, 3]}},
            "future_setting": {"preserve": True}, "game_cups": [
                {"league": 1, "name": "Legacy Cup", "future": "keep"},
                {"league": 999, "name": "Unknown league", "future": "keep too"}],
            "leagues": [
                {"name": "Alpha", "country": "Test", "clubs": 12, "legs": 2,
                 "cup": True, "cup_name": "Old cup", "supercup": True, "future": 17},
                {"name": "Beta", "country": "Test", "clubs": 12, "season": "calendar"},
                {"name": "Existing calendar", "country": "Test", "clubs": 12,
                 "season": "calendar", "league_cup": True},
                {"name": "Lower", "above": "Alpha", "clubs": 12},
                {"name": "Exhibition", "exhibition": True, "clubs": 12},
                {"name": "Other", "others": "europe", "clubs": 1}]}


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
    game, ours = page.sections
    ge, oe = game["editor"], ours["editor"]
    ok("real page with three sections", page.tabs.count() == 3)
    ok("Game keeps seven columns", ge.table.columnCount() == 7)
    ok("Our keeps ten columns and only eligible leagues", oe.table.columnCount() == 10
       and oe.keys() == ["Alpha", "Beta", "Existing calendar"])
    ok("existing supercup restriction", not ge.rows[1][4].isEnabled()
       and not ge.rows[1][5].isEnabled() and not ge.rows[1][6].isEnabled())
    ok("calendar league cup restrictions preserved", not oe.rows[1][1][6].isEnabled()
       and oe.rows[2][1][6].isEnabled())
    ok("opening does not create undo or change recipe", not project.can_undo()
       and project.recipe == recipe())
    original_players = project.recipe["players"]
    ge.rows[0][2].setText("Draft game cup")
    ge.rows[0][3].path = "custom-logo.png"
    ge.rows[0][3].changed()
    ge.search.setText("Beta")
    ok("filter hides a row without losing its draft", ge.table.isRowHidden(0)
       and ge.rows[0][2].text() == "Draft game cup")
    page.tabs.setCurrentIndex(1)
    oe.rows[0][1][1].setText("Draft own cup")
    page.tabs.setCurrentIndex(2)
    page.shown()
    ok("section and page navigation retain both drafts", game["editor"] is ge
       and ours["editor"] is oe and bool(ge.dirty_keys()) and bool(oe.dirty_keys()))
    page.apply_section(game)
    ok("game Apply preserves legacy unknown rows and fields", project.recipe["game_cups"][0]
       == {"league": 1, "name": "Draft game cup", "logo": "custom-logo.png", "future": "keep"}
       and project.recipe["game_cups"][1]["league"] == 999)
    ok("Apply preserves other section draft and unrelated player identity", ours["editor"] is oe
       and project.recipe["players"] is original_players and project.recipe["future_setting"]["preserve"])
    ok("Undo restores original game_cups representation", project.undo()
       and project.recipe["game_cups"] == recipe()["game_cups"])
    qa.processEvents()
    ok("Redo restores game_cups edits", project.redo()
       and project.recipe["game_cups"][0]["name"] == "Draft game cup")
    qa.processEvents()
    project._snap_at = 0  # explicitly separate the two user actions for the undo assertions
    page.apply_section(ours)
    ok("Our Apply writes the existing league fields only", project.recipe["leagues"][0]["cup_name"]
       == "Draft own cup" and project.recipe["leagues"][0]["future"] == 17)
    ok("Undo restores own cups", project.undo() and project.recipe["leagues"][0]["cup_name"] == "Old cup")
    qa.processEvents()
    ok("page refresh after Undo", ours["editor"].rows[0][1][1].text() == "Old cup")
    ok("Redo restores own cups", project.redo() and project.recipe["leagues"][0]["cup_name"] == "Draft own cup")
    qa.processEvents()
    # Simulate the replacement of a league dictionary performed by Edit League.
    oe = ours["editor"]
    oe.rows[0][1][1].setText("Pending name")
    changed_league = dict(project.recipe["leagues"][0], cup_name="Edit League name", clubs=16)
    project.recipe["leagues"][0] = changed_league
    project.touch()
    qa.processEvents()
    page.apply_section(ours)
    ok("Edit League conflict keeps draft and current project", oe.rows[0][1][1].text() == "Pending name"
       and changed_league["cup_name"] == "Edit League name" and "changed elsewhere" in ours["message"].text())
    page.discard_section(ours)
    ok("Discard reloads Edit League replacement", ours["editor"].rows[0][1][1].text() == "Edit League name")
    oe = ours["editor"]
    oe.rows[0][1][1].setText("Merge name")
    changed_league["clubs"] = 18
    changed_league["league_cup_name"] = "Elsewhere league cup"
    project.touch()
    qa.processEvents()
    page.apply_section(ours)
    ok("disjoint edits merge without overwriting unrelated fields", changed_league["cup_name"] == "Merge name"
       and changed_league["clubs"] == 18 and changed_league["league_cup_name"] == "Elsewhere league cup")
    oe = ours["editor"]
    oe.rows[0][1][0].setChecked(False)
    ok("national cup controls supercup enablement", not oe.rows[0][1][3].isEnabled())
    page.apply_section(ours)
    ok("disabling national cup removes supercup", "cup" not in changed_league and "supercup" not in changed_league)
    # Actual Edit League uses the same fields, not a duplicate cup configuration.
    changed_league["cup"] = True
    dialog = B.LeagueDialog(None, project, changed_league)
    ok("Edit League reads Cups fields", dialog.cup_name.text() == "Merge name"
       and dialog.cup.isChecked() and dialog.lcup_name.text() == "Elsewhere league cup")
    dialog.cup_name.setText("  Edit League writes back  ")
    dialog.cup_logo.path = "edit-league-logo.png"
    dialog.ok()
    ok("Edit League uses the same cup serialization", dialog.result() == QDialog.Accepted
       and dialog.league["cup_name"] == "Edit League writes back"
       and dialog.league["cup_logo"] == "edit-league-logo.png")
    project.recipe["leagues"][0] = dialog.league
    project.touch()
    qa.processEvents()
    ok("Cups refreshes fields written by Edit League", ours["editor"].rows[0][1][1].text() == "Edit League writes back"
       and ours["editor"].rows[0][1][2].path == "edit-league-logo.png")
    # A draft is not silently applied to a different project; returning restores it.
    ge = game["editor"]
    ge.rows[0][2].setText("Suspended draft")
    before = copy.deepcopy(project.recipe)
    project.adopt({"world": "_FL26OtherProject", "leagues": []}, None)
    qa.processEvents()
    ok("switching projects isolates drafts", not project.recipe.get("game_cups")
       and "_FL26CupsTest" in page.banner.text() and page.has_drafts())
    project.adopt(before, None)
    qa.processEvents()
    ok("returning to project restores its draft", game["editor"].rows[0][2].text() == "Suspended draft")
    page.discard_section(game)
    ok("discard clears suspended draft", not page.has_drafts())
    page.hide()
    old_editor = ours["editor"]
    project.recipe["leagues"][0]["cup_name"] = "Changed while hidden"
    project.touch()
    qa.processEvents()
    ok("hidden page avoids rebuilding editors for unrelated signals", ours["editor"] is old_editor)
    page.show()
    page.shown()
    ok("opening the page reloads changes made while hidden", ours["editor"].rows[0][1][1].text() == "Changed while hidden")
    # Missing original tables still permits custom-country editing.
    project.base = None
    project.tables_changed.emit()
    qa.processEvents()
    ok("missing tables handled safely", game["editor"] is None and ours["editor"] is not None)
    project.base = "fake-tables"
    project.tables_changed.emit()
    qa.processEvents()
    # No-op Apply must not normalize an old recipe or create an Undo step.
    project.adopt(recipe(), None)
    qa.processEvents()
    saved = copy.deepcopy(project.recipe)
    page.apply_section(game)
    page.apply_section(ours)
    ok("no-op Apply preserves old recipe byte-equivalent data", project.recipe == saved and not project.can_undo())
    ge = game["editor"]
    ge.rows[0][2].setText("Autosaved cup")
    with tempfile.TemporaryDirectory(prefix="cups-page-") as folder:
        project.path = os.path.join(folder, "world.json")
        page.apply_section(game)
        project.autosave()
        with open(project.path, encoding="utf-8") as stream:
            persisted = json.load(stream)
        ok("Project autosave persists cup keys", persisted["game_cups"][0]["name"] == "Autosaved cup"
           and persisted["game_cups"][1]["future"] == "keep too" and not project.dirty)
    project.path = None
    # An unchanged row with explicit false flags must keep its exact legacy representation.
    project.adopt(recipe(), None)
    qa.processEvents()
    project.recipe["leagues"][0]["league_cup"] = False
    project.touch()
    qa.processEvents()
    oe = ours["editor"]
    oe.search.setText("Beta")
    oe.rows[0][1][1].setText("Filtered draft")
    ok("Our filtering keeps hidden row changes", oe.table.isRowHidden(0) and bool(oe.dirty_keys()))
    page.apply_section(ours)
    ok("editing a name preserves explicit false legacy flags", project.recipe["leagues"][0]["league_cup"] is False)
    # Enabling a super cup must not override a national cup disabled through Edit League.
    project.adopt(recipe(), None)
    project.recipe["leagues"][0].pop("supercup")
    project._forget()
    qa.processEvents()
    oe = ours["editor"]
    oe.rows[0][1][3].setChecked(True)
    project.recipe["leagues"][0].pop("cup")
    project.touch()
    qa.processEvents()
    page.apply_section(ours)
    ok("concurrent national cup removal blocks super cup", "supercup" not in project.recipe["leagues"][0]
       and "national cup changed" in ours["message"].text())
    page.discard_section(ours)
    project.adopt(recipe(), None)
    qa.processEvents()
    oe = ours["editor"]
    oe.rows[0][1][1].setText("Removed league draft")
    project.recipe["leagues"].pop(0)
    project.touch()
    qa.processEvents()
    page.apply_section(ours)
    ok("removed league draft stays visible and cannot be misapplied", oe.rows[0][1][1].text() == "Removed league draft"
       and "removed, renamed" in ours["message"].text())
    page.discard_section(ours)
    ok("Discard refreshes removed leagues", "Alpha" not in ours["editor"].keys())
    project.adopt(recipe(), None)
    qa.processEvents()
    ge = game["editor"]
    ge.rows[0][2].setText("Conflicting game draft")
    project.recipe["game_cups"][0]["name"] = "External game name"
    project.touch()
    qa.processEvents()
    page.apply_section(game)
    ok("Game conflicts are atomic", project.recipe["game_cups"][0]["name"] == "External game name"
       and ge.rows[0][2].text() == "Conflicting game draft")
    page.discard_section(game)
    ge = game["editor"]
    ge.rows[0][2].setText("Deleted game row draft")
    project.recipe["game_cups"].pop(0)
    project.touch()
    qa.processEvents()
    page.apply_section(game)
    ok("deleted game settings are not resurrected silently", len(project.recipe["game_cups"]) == 1
       and "changed elsewhere" in game["message"].text())
    page.discard_section(game)
    ge = game["editor"]
    ge.rows[0][1].setChecked(True)
    project.base = "other-tables"
    project.tables_changed.emit()
    qa.processEvents()
    page.apply_section(game)
    ok("table changes preserve draft but block stale Apply", ge.rows[0][1].isChecked()
       and "tables changed" in game["message"].text())
    page.discard_section(game)
    project.base = "fake-tables"
    project.adopt(recipe(), None)
    qa.processEvents()
    # Legacy wrappers use the extracted widgets and Cancel does not mutate a league.
    legacy = B.OurCupsDialog(None, project)
    legacy.editor.rows[0][1][1].setText("Cancelled")
    legacy.reject()
    ok("legacy dialog Cancel has no effects", project.recipe["leagues"][0]["cup_name"] == "Old cup")
    ok("table does not force page-wide minimum width", game["editor"].table.minimumWidth() == 0
       and ours["editor"].table.minimumWidth() == 0)
    page.tabs.setCurrentIndex(1)
    page.resize(720, 650)
    qa.processEvents()
    ok("narrow page contains the table and Apply controls", page.width() == 720
       and ours["editor"].table.width() < page.width()
       and ours["apply"].geometry().right() <= ours["apply"].parentWidget().width())
    ok("narrow tables keep readable name fields", all(ours["editor"].table.columnWidth(c) >= 160 for c in (2, 5, 8)))
    page.resize(1400, 650)
    qa.processEvents()
    ok("table expands with available page width", ours["editor"].table.width() > 1000)
    page.resize(1000, 650)
    if os.environ.get("CUPS_SNAPSHOT"):
        page.tabs.setCurrentIndex(1)
        qa.processEvents()
        page.grab().save(os.environ["CUPS_SNAPSHOT"])
    page.close()
    print("test_cups_page: ok (%d)" % N)


if __name__ == "__main__":
    with patch.object(B.B, "game_tops", return_value=[(1, "Alpha Game", False), (2, "Beta Game", True)]):
        run()
