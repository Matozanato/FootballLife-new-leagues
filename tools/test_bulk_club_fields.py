"""Focused, offscreen checks; no game tables needed. Run: python tools/test_bulk_club_fields.py"""
import copy
import json
import os
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem, QWidget
from modstudio.pages import builder as UI
from modstudio.project import Project

APP = QApplication.instance() or QApplication([])


class Page(QWidget):
    def __init__(self, league, order):
        super().__init__()
        self.project = Project(type("App", (), {"settings": None})())
        self.project.recipe["leagues"] = [league]
        self.project._autosave_soon = lambda: None
        self.project._forget()
        self.tree = QTreeWidget(self)
        for k in order:
            item = QTreeWidgetItem([str(k)])
            item.setData(0, Qt.UserRole, k)
            self.tree.addTopLevelItem(item)

    def league(self):
        return self.project.recipe["leagues"][0]

    game_places = staticmethod(UI.NewClubs.game_places)


class BulkFieldsTest(unittest.TestCase):
    def setUp(self):
        self.errors = patch.object(UI, "error").start()
        self.addCleanup(patch.stopall)
        self.page = Page({"name": "Test", "clubs": 3, "club_names": ["A", "B", "C"],
                          "club_abbrs": ["AAA", "BBB", "CCC"],
                          "club_coaches": ["One", "Two", "Three"], "club_crests": [None] * 3}, [2, 0, 1])
        self.addCleanup(self.page.close)

    def paste(self, text, manager=False, cancel=False):
        def finish(dialog):
            if cancel:
                return False
            dialog.text.setPlainText(text)
            dialog.ok()
            return dialog.result is not None
        with patch.object(UI.PasteClubFieldDialog, "finish", finish):
            UI.NewClubs.paste_field(self.page, manager)

    def test_manager_order_isolation_undo_save(self):
        before = copy.deepcopy(self.page.project.recipe)
        self.paste("Coach C\nCoach A\nCoach B\n", manager=True)
        expected = copy.deepcopy(before)
        expected["leagues"][0]["club_coaches"] = ["Coach A", "Coach B", "Coach C"]
        self.assertEqual(self.page.project.recipe, expected)
        self.assertTrue(self.page.project.dirty)
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "recipe.json")
            self.page.project.save(path)
            with open(path, encoding="utf-8") as saved:
                self.assertEqual(json.load(saved), expected)
        self.page.project.undo()
        self.assertEqual(self.page.project.recipe, before)
        self.page.project.redo()
        self.assertEqual(self.page.project.recipe, expected)

    def test_short_normalization_and_blank_positions(self):
        before = copy.deepcopy(self.page.project.recipe)
        self.paste("žđ1\n\nb2")
        before["leagues"][0]["club_abbrs"] = ["", "B2", "ZD1"]
        self.assertEqual(self.page.project.recipe, before)

    def test_invalid_and_cancel_are_atomic(self):
        before = copy.deepcopy(self.page.project.recipe)
        for text, manager in [("A\nB", False), ("A\nB\nC\nD", False),
                              ("A\nB!\nC", False), ("ABCD\nB\nC", False),
                              ("A" * 46 + "\nB\nC", True),
                              ("é" * 23 + "\nB\nC", True), ("A\x00\nB\nC", True)]:
            self.paste(text, manager)
            self.assertEqual(self.page.project.recipe, before)
            self.assertFalse(self.page.project.dirty)
        self.paste("A\nB\nC", cancel=True)
        self.assertEqual(self.page.project.recipe, before)

    def test_all_blank_managers_restore_default(self):
        self.paste("\n\n", manager=True)
        self.assertNotIn("club_coaches", self.page.league())

    def test_game_club_short_override(self):
        self.page.league()["game_clubs"] = [{"at": 0, "id": 100}]
        self.page.project.game_cl = {100: ("Game club", "GAM")}
        self.page.project.edits("clubs")["100"] = {"name": "Renamed", "crest": "crest.png"}
        before = copy.deepcopy(self.page.project.recipe)
        self.paste("CCC\nNEW\nBBB")
        self.assertEqual(self.page.project.edits("clubs")["100"],
                         {"name": "Renamed", "crest": "crest.png", "abbr": "NEW"})
        self.assertEqual(self.page.league()["club_abbrs"], before["leagues"][0]["club_abbrs"])
        self.paste("CCC\n\nBBB")
        self.assertEqual(self.page.project.edits("clubs")["100"], before["edits"]["clubs"]["100"])

    def test_mixed_manager_persistence_undo_and_atomicity(self):
        self.page.league()["game_clubs"] = [{"at": 0, "id": 100}]
        self.page.project.edits("clubs")["100"] = {"name": "Renamed", "abbr": "GAM"}
        self.page.project._forget()
        before = copy.deepcopy(self.page.project.recipe)
        with patch.object(UI.B.mkcoaches, "club_names", return_value={100: "Original"}):
            for text in ("C\nA", "C\nA\nB\nExtra", "C\nA\n" + "X" * 46):
                self.paste(text, manager=True)
                self.assertEqual(self.page.project.recipe, before)
                self.assertFalse(self.page.project.dirty)
            self.paste("C\nGame manager\nB", manager=True)
        expected = copy.deepcopy(before)
        expected["edits"]["clubs"]["100"]["coach"] = "Game manager"
        expected["leagues"][0]["club_coaches"] = ["One", "B", "C"]
        self.assertEqual(self.page.project.recipe, expected)
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "recipe.json")
            self.page.project.save(path)
            loaded = Project(type("App", (), {"settings": None})())
            loaded.open(path)
            self.assertEqual(loaded.recipe, expected)
        self.page.project.undo()
        self.assertEqual(self.page.project.recipe, before)
        self.page.project.redo()
        self.assertEqual(self.page.project.recipe, expected)
        with patch.object(UI.B.mkcoaches, "club_names", return_value={100: "Original"}):
            self.paste("C\n\nB", manager=True)
        self.assertEqual(self.page.project.edits("clubs")["100"], before["edits"]["clubs"]["100"])

    def test_individual_original_manager(self):
        self.page.app = type("App", (), {})()
        self.page.project.game_cl = {100: ("Game club", "GAM")}
        with patch.object(UI.B.mkcoaches, "club_names", return_value={100: "Original"}), \
                patch.object(UI, "stadium_lib", return_value=None), \
                patch.object(UI, "club_stadium", return_value=None):
            def finish(dialog):
                self.assertEqual(dialog.coach.text(), "Original")
                dialog.coach.setText("Individual manager")
                dialog.ok()
                return dialog.result is not None
            with patch.object(UI.ClubDialog, "finish", finish):
                self.assertTrue(UI.edit_game_club(self.page, 100))
            self.assertEqual(self.page.project.edits("clubs")["100"], {"coach": "Individual manager"})
            def clear(dialog):
                self.assertEqual(dialog.coach.text(), "Individual manager")
                dialog.coach.clear()
                dialog.ok()
                return dialog.result is not None
            with patch.object(UI.ClubDialog, "finish", clear):
                self.assertTrue(UI.edit_game_club(self.page, 100))
            self.assertNotIn("100", self.page.project.edits("clubs"))

    def test_all_original_managers_in_display_order(self):
        self.page.league()["game_clubs"] = [{"at": i, "id": 100 + i} for i in range(3)]
        before = copy.deepcopy(self.page.league())
        with patch.object(UI.B.mkcoaches, "club_names", return_value={100: "A", 101: "B", 102: "C"}):
            self.paste("Third\nFirst\nSecond", manager=True)
        self.assertEqual(self.page.league(), before)
        self.assertEqual(self.page.project.edits("clubs"),
                         {"100": {"coach": "First"}, "101": {"coach": "Second"}, "102": {"coach": "Third"}})

    def test_existing_paste_dialog_unchanged(self):
        dialog = UI.PasteDialog(self.page, [])
        dialog.text.setPlainText(" A \n\n B \n\n")
        dialog.ok()
        self.assertEqual(dialog.result, ["A", "", "B"])

    def test_bulk_editors_open_empty(self):
        for manager in (False, True):
            for lines in ([""] * 16, ["Old"] * 16):
                with self.subTest(manager=manager, lines=lines):
                    dialog = UI.PasteClubFieldDialog(self.page, lines, manager)
                    self.assertEqual(dialog.text.toPlainText(), "")
                    dialog.ok()
                    self.assertIsNone(dialog.result)
                    self.assertIn("0 values for 16 clubs", self.errors.call_args.args[2])

    def test_three_typed_values_count_as_three(self):
        for manager in (False, True):
            with self.subTest(manager=manager):
                dialog = UI.PasteClubFieldDialog(self.page, [""] * 16, manager)
                dialog.text.insertPlainText("AAA\nBBB\nCCC")
                dialog.ok()
                self.assertIsNone(dialog.result)
                self.assertIn("3 values for 16 clubs", self.errors.call_args.args[2])

    def test_exactly_sixteen_pasted_entries(self):
        entries = ["A%02d" % i for i in range(16)]
        for manager in (False, True):
            for ending in ("", "\n", "\r\n"):
                with self.subTest(manager=manager, ending=ending):
                    dialog = UI.PasteClubFieldDialog(self.page, [""] * 16, manager)
                    dialog.text.insertPlainText("\n".join(entries) + ending)
                    dialog.ok()
                    self.assertEqual(dialog.result, entries)

    def test_intentional_blank_entries_keep_their_positions(self):
        entries = ["A%02d" % i for i in range(16)]
        entries[0] = entries[5] = entries[-1] = ""
        for manager in (False, True):
            with self.subTest(manager=manager):
                dialog = UI.PasteClubFieldDialog(self.page, [""] * 16, manager)
                dialog.text.insertPlainText("\n".join(entries))
                dialog.ok()
                self.assertEqual(dialog.result, entries)


if __name__ == "__main__":
    unittest.main()
