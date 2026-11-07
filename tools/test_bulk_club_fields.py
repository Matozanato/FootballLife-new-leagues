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

    def paste(self, text, manager=False, cancel=False, include_original=False):
        def finish(dialog):
            if cancel:
                return False
            if dialog.include_original is not None:
                self.assertFalse(dialog.include_original.isChecked())
                dialog.include_original.setChecked(include_original)
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
        self.paste("CCC\nNEW\nBBB", include_original=True)
        self.assertEqual(self.page.project.edits("clubs")["100"],
                         {"name": "Renamed", "crest": "crest.png", "abbr": "NEW"})
        self.assertEqual(self.page.league()["club_abbrs"], before["leagues"][0]["club_abbrs"])
        self.paste("CCC\n\nBBB", include_original=True)
        self.assertEqual(self.page.project.edits("clubs")["100"], before["edits"]["clubs"]["100"])

    def test_mixed_manager_persistence_undo_and_atomicity(self):
        self.page.league()["game_clubs"] = [{"at": 0, "id": 100}]
        self.page.project.edits("clubs")["100"] = {"name": "Renamed", "abbr": "GAM"}
        self.page.project._forget()
        before = copy.deepcopy(self.page.project.recipe)
        with patch.object(UI.B.mkcoaches, "club_names", return_value={100: "Original"}):
            for text in ("C\nA", "C\nA\nB\nExtra", "C\nA\n" + "X" * 46):
                self.paste(text, manager=True, include_original=True)
                self.assertEqual(self.page.project.recipe, before)
                self.assertFalse(self.page.project.dirty)
            self.paste("C\nGame manager\nB", manager=True, include_original=True)
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
            self.paste("C\n\nB", manager=True, include_original=True)
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
            self.paste("Third\nFirst\nSecond", manager=True, include_original=True)
        self.assertEqual(self.page.league(), before)
        self.assertEqual(self.page.project.edits("clubs"),
                         {"100": {"coach": "First"}, "101": {"coach": "Second"}, "102": {"coach": "Third"}})

    def test_skip_original_positions_and_preserve_overrides(self):
        for originals, order in (([4], list(range(8))),
                                 ([0, 4, 7], list(range(8))),
                                 ([1, 4, 6], [6, 7, 4, 3, 0, 1, 5, 2])):
            with self.subTest(originals=originals, order=order):
                league = {"name": "Mixed", "clubs": 8,
                          "club_coaches": ["Old %d" % k for k in range(8)],
                          "game_clubs": [{"at": k, "id": 100 + k} for k in originals]}
                page = Page(league, order)
                self.addCleanup(page.close)
                self.page = page
                for k in originals:
                    page.project.edits("clubs")[str(100 + k)] = {
                        "coach": "Saved manager %d" % k, "name": "Saved club"}
                page.project._forget()
                before = copy.deepcopy(page.project.recipe)
                eligible = [k for k in order if k not in originals]
                names = ["New %d" % k for k in eligible]
                names[1] = ""  # An included blank clears only its eligible club.
                expected = copy.deepcopy(before)
                for k, value in zip(eligible, names):
                    expected["leagues"][0]["club_coaches"][k] = value
                with patch.object(UI.B.mkcoaches, "club_names", return_value={}), \
                        patch.object(page.project, "_autosave_soon") as autosave:
                    for text in ("One", "\n".join(names + ["Extra"]),
                                 "\n".join(["X" * 46] + names[1:]),
                                 "\n".join(["Bad\x00"] + names[1:])):
                        self.paste(text, manager=True)
                        self.assertEqual(page.project.recipe, before)
                        self.assertFalse(page.project.dirty)
                    autosave.assert_not_called()
                    self.paste("\n".join(names), manager=True)
                    autosave.assert_called_once()
                self.assertEqual(page.project.recipe, expected)
                with tempfile.TemporaryDirectory() as folder:
                    path = os.path.join(folder, "recipe.json")
                    page.project.save(path)
                    loaded = Project(type("App", (), {"settings": None})())
                    loaded.open(path)
                    self.assertEqual(loaded.recipe, expected)
                page.project.undo()
                self.assertEqual(page.project.recipe, before)
                page.project.redo()
                self.assertEqual(page.project.recipe, expected)

    def test_original_checkbox_count_and_scope(self):
        for manager, original_count in ((False, 0), (False, 2), (False, 3),
                                        (True, 0), (True, 2), (True, 3)):
            with self.subTest(manager=manager, original_count=original_count):
                dialog = UI.PasteClubFieldDialog(self.page, [""] * 3, manager, original_count)
                self.addCleanup(dialog.close)
                if not original_count:
                    self.assertIsNone(dialog.include_original)
                    self.assertEqual(dialog.count, 3)
                    continue
                self.assertEqual(dialog.include_original.text(), "Include original game clubs")
                self.assertFalse(dialog.include_original.isChecked())
                self.assertEqual(dialog.count, 3 - original_count)
                label = "Expected manager names: %d" if manager else "Expected short names: %d"
                self.assertEqual(dialog.expected.text(), label % (3 - original_count))
                dialog.include_original.setChecked(True)
                self.assertEqual(dialog.count, 3)
                self.assertEqual(dialog.expected.text(), label % 3)
                dialog.include_original.setChecked(False)
                self.assertEqual(dialog.count, 3 - original_count)

    def test_only_original_default_is_noop(self):
        self.page.league()["game_clubs"] = [{"at": i, "id": 100 + i} for i in range(3)]
        self.page.project.edits("clubs")["101"] = {"coach": "Saved", "abbr": "OLD"}
        self.page.project._forget()
        before = copy.deepcopy(self.page.project.recipe)
        with patch.object(UI.B.mkcoaches, "club_names", return_value={}), \
                patch.object(self.page.project, "touch") as touch:
            self.paste("Unexpected", manager=True)
            self.assertIn("1 values for 0 clubs", self.errors.call_args.args[2])
            self.paste("", manager=True)
            touch.assert_not_called()
        self.assertEqual(self.page.project.recipe, before)
        self.assertFalse(self.page.project.dirty)

    def test_short_skip_originals_validation_undo_and_persistence(self):
        for originals, order in (([4], list(range(8))),
                                 ([0, 4, 7], list(range(8))),
                                 ([1, 4, 6], [6, 7, 4, 3, 0, 1, 5, 2])):
            with self.subTest(originals=originals, order=order):
                page = Page({"name": "Mixed", "clubs": 8,
                             "club_abbrs": ["O%d" % k for k in range(8)],
                             "club_coaches": ["Manager %d" % k for k in range(8)],
                             "game_clubs": [{"at": k, "id": 100 + k} for k in originals]}, order)
                self.addCleanup(page.close)
                self.page = page
                page.project.game_cl = {100 + k: ("Original club", "G%d" % k) for k in originals}
                # Keep both clubs with saved overrides and clubs using the game's abbreviation.
                page.project.edits("clubs")[str(100 + originals[0])] = {
                    "abbr": "SAV", "coach": "Saved manager", "name": "Saved club"}
                page.project._forget()
                before = copy.deepcopy(page.project.recipe)
                eligible = [k for k in order if k not in originals]
                names = ["n%d" % k for k in eligible]
                names[0] = "\u017e\u01111"
                names[1] = names[-1] = ""
                expected = copy.deepcopy(before)
                for k, value in zip(eligible, names):
                    expected["leagues"][0]["club_abbrs"][k] = value.upper()
                expected["leagues"][0]["club_abbrs"][eligible[0]] = "ZD1"
                with patch.object(page.project, "_autosave_soon") as autosave:
                    for text in ("ONE", "\n".join(names + ["EXT"]),
                                 "\n".join(["ABCD"] + names[1:]),
                                 "\n".join(["A!"] + names[1:]),
                                 "\n".join(["A\x00"] + names[1:])):
                        self.paste(text)
                        self.assertEqual(page.project.recipe, before)
                        self.assertFalse(page.project.dirty)
                    self.paste("\n".join(names), cancel=True)
                    self.assertEqual(page.project.recipe, before)
                    autosave.assert_not_called()
                    self.paste("\n".join(names))
                    autosave.assert_called_once()
                self.assertEqual(page.project.recipe, expected)
                self.assertTrue(page.project.dirty)
                with tempfile.TemporaryDirectory() as folder:
                    path = os.path.join(folder, "recipe.json")
                    page.project.save(path)
                    loaded = Project(type("App", (), {"settings": None})())
                    loaded.open(path)
                    self.assertEqual(loaded.recipe, expected)
                page.project.undo()
                self.assertEqual(page.project.recipe, before)
                page.project.redo()
                self.assertEqual(page.project.recipe, expected)

    def test_short_include_originals_in_reordered_display(self):
        self.page.league()["game_clubs"] = [{"at": k, "id": 100 + k} for k in (0, 2)]
        self.page.project.game_cl = {100: ("First", "ONE"), 102: ("Third", "THR")}
        self.page.project.edits("clubs")["100"] = {"abbr": "SAV", "coach": "Saved manager"}
        self.page.project._forget()
        before = copy.deepcopy(self.page.project.recipe)
        for text in ("AAA\nBBB", "AAA\nBBB\nCCC\nDDD", "AAA\nB!\nCCC"):
            self.paste(text, include_original=True)
            self.assertEqual(self.page.project.recipe, before)
            self.assertFalse(self.page.project.dirty)
        self.paste("th3\n\nb2", include_original=True)
        expected = copy.deepcopy(before)
        expected["leagues"][0]["club_abbrs"] = ["AAA", "B2", "CCC"]
        expected["edits"]["clubs"] = {"100": {"coach": "Saved manager"}, "102": {"abbr": "TH3"}}
        self.assertEqual(self.page.project.recipe, expected)
        self.page.project.undo()
        self.assertEqual(self.page.project.recipe, before)
        self.page.project.redo()
        self.assertEqual(self.page.project.recipe, expected)

    def test_short_only_original_default_is_noop(self):
        self.page.league()["game_clubs"] = [{"at": i, "id": 100 + i} for i in range(3)]
        self.page.project.game_cl = {100 + i: ("Original", "OLD") for i in range(3)}
        self.page.project.edits("clubs")["101"] = {"abbr": "SAV", "coach": "Saved manager"}
        self.page.project._forget()
        before = copy.deepcopy(self.page.project.recipe)
        with patch.object(self.page.project, "touch") as touch:
            self.paste("AAA")
            self.assertIn("1 values for 0 clubs", self.errors.call_args.args[2])
            self.paste("")
            touch.assert_not_called()
        self.assertEqual(self.page.project.recipe, before)
        self.assertFalse(self.page.project.dirty)
        self.paste("c3\na1\nb2", include_original=True)
        self.assertEqual(self.page.league(), before["leagues"][0])
        self.assertEqual(self.page.project.edits("clubs"),
                         {"100": {"abbr": "A1"}, "101": {"abbr": "B2", "coach": "Saved manager"},
                          "102": {"abbr": "C3"}})

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
