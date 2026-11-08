"""Embedded trophy UI: real folder validators/Project undo, controlled competition rows.

No game Build. Production-window tests isolate settings in a temporary directory.
"""
import copy
import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from test_cups_page import qa, App
from test_cups_layout import settle, rect
from modstudio.pages import trophies as UI
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QFileDialog, QToolButton, QMessageBox

N = 0
ROWS = [(2, [2, 1026], "Champions League", "cup", False),
        (59, [59], "National Cup", "cup", False)]


def ok(label, condition):
    global N
    assert condition, label
    N += 1
    print("ok %d - %s" % (N, label))


def inline(fn, done, failed):
    done(fn(lambda _value: None))


def trophy(root, name):
    path = Path(root, name)
    path.mkdir()
    (path / "asset.bin").write_bytes(b"existing trophy assets")
    return str(path)


def page_for(recipe):
    app = App()
    app.project.recipe = recipe
    app.project._forget()
    page = UI.Trophies(app)
    page.resize(1080, 640)
    page.show()
    page.shown()
    settle()
    return app, page


def choose(page, cid):
    item = next(page.editor.table.topLevelItem(i) for i in range(page.editor.table.topLevelItemCount())
                if page.editor.table.topLevelItem(i).data(0, Qt.UserRole) == str(cid))
    page.editor.table.setCurrentItem(item)


def pick(page, cid, folder):
    choose(page, cid)
    with patch.object(QFileDialog, "getExistingDirectory", return_value=folder):
        page.editor.pick()


def editing():
    with tempfile.TemporaryDirectory(prefix="trophies-page-") as root:
        first, second = trophy(root, "first"), trophy(root, "second")
        recipe = {"world": "_FL26TrophiesPage", "leagues": [], "future": {"keep": True},
                  "trophies": {"2": first, "999": str(Path(root, "missing")), "invalid-id": None}}
        original = copy.deepcopy(recipe)
        app, page = page_for(recipe)
        ok("Trophies is an embedded QWidget page rather than a dialog", not isinstance(page, QDialog) and page.editor.table.topLevelItemCount() == 4)
        ok("existing and unknown/invalid trophy references are retained", page.editor.trophies == original["trophies"] and page.editor.warning.isVisible())
        ok("competition ids and all existing regulation references remain visible", any(page.editor.table.topLevelItem(i).text(3) == "2, 1026" for i in range(page.editor.table.topLevelItemCount())))
        pick(page, 2, second)
        ok("Pick edits a temporary mapping without saving the project", app.project.recipe == original and page.apply_button.isEnabled() and page.editor.trophies["2"] == os.path.normpath(second))
        page.editor.find.setText("National")
        page.hide()
        page.show()
        page.shown()
        ok("navigation and search preserve unapplied assignments", page.editor.trophies["2"] == second and page.editor.find.text() == "National" and app.project.recipe == original)
        page.apply()
        expected = dict(original["trophies"], **{"2": second})
        ok("Apply patches only the changed assignment and retains legacy invalid entries", app.project.recipe["trophies"] == expected and app.project.recipe["future"] == original["future"] and not page.dirty_keys())
        ok("one Undo restores the previous trophy mapping", app.project.undo() and app.project.recipe == original)
        settle()
        ok("Undo refreshes the embedded editor", page.editor.trophies["2"] == first)
        ok("Redo restores the complete trophy change", app.project.redo() and app.project.recipe["trophies"] == expected)
        settle()
        page.editor.find.clear()
        pick(page, 59, first)
        page.discard()
        ok("Discard reloads the current project, not the initial dialog state", page.editor.trophies == expected and not page.dirty_keys())
        empty = Path(root, "empty")
        empty.mkdir()
        with patch.object(UI, "error") as errors:
            pick(page, 59, str(empty))
        ok("the existing backend rejects an empty trophy folder without changing data", errors.called and page.editor.trophies == expected)
        pick(page, 59, first)
        # A folder disappearing after Pick must fail atomically on Apply.
        Path(first, "asset.bin").unlink()
        before = copy.deepcopy(app.project.recipe)
        page.apply()
        ok("Apply revalidates changed assets and keeps the failed draft", app.project.recipe == before and page.dirty_keys() == {"59"})
        Path(first, "asset.bin").write_bytes(b"restored")
        page.discard()
        choose(page, "invalid-id")
        page.editor.clear()
        page.apply()
        ok("invalid legacy ids can be explicitly cleared without normalizing other entries", "invalid-id" not in app.project.recipe["trophies"] and "999" in app.project.recipe["trophies"])
        page.editor.find.clear()
        pick(page, 2, first)
        app.project.recipe["trophies"]["2"] = str(Path(root, "external"))
        app.project.touch()
        settle()
        page.apply()
        ok("concurrent trophy changes are never silently overwritten", app.project.recipe["trophies"]["2"].endswith("external") and page.dirty_keys() == {"2"} and "changed elsewhere" in page.banner.text())
        page.discard()
        ok("Discard resolves a conflict using the current project value", page.editor.trophies["2"].endswith("external"))
        pick(page, 2, first)
        app.project.recipe["trophies"]["59"] = second
        app.project.touch()
        settle()
        page.apply()
        ok("Apply preserves concurrent changes to unrelated trophy assignments", app.project.recipe["trophies"]["59"] == second and app.project.recipe["trophies"]["2"] == first)
        app.project.path = str(Path(root, "recipe.json"))
        app.project.autosave()
        saved = json.loads(Path(app.project.path).read_text(encoding="utf-8"))
        ok("Project autosave retains the existing trophies schema", saved["trophies"] == app.project.recipe["trophies"] and "trophy_drafts" not in saved)
        app.project.path = None
        pick(page, 2, second)
        before_world = copy.deepcopy(app.project.recipe)
        app.project.adopt({"world": "_FL26OtherTrophies", "leagues": [], "trophies": {"59": second}}, None)
        settle()
        ok("world switching displays only the newly selected world's mappings", page.editor.trophies == {"59": second} and page.has_drafts())
        app.project.adopt(before_world, None)
        settle()
        ok("returning to a world restores its unapplied trophy draft", page.editor.trophies["2"] == second and app.project.recipe["trophies"]["2"] == first)
        page.discard()
        ok("world-specific drafts can be discarded without transferring assignments", not page.has_drafts())
        page.close()
        app, page = page_for({"world": "_FL26ClearTrophy", "leagues": [], "trophies": {"2": first}})
        choose(page, 2)
        page.editor.clear()
        page.apply()
        ok("clearing the final assignment restores the existing no-trophies default", "trophies" not in app.project.recipe)
        ok("Undo restores a cleared assignment", app.project.undo() and app.project.recipe["trophies"] == {"2": first})
        settle()
        app.project.base = None
        app.project.tables_changed.emit()
        settle()
        ok("missing tables preserve stored mappings and remain safely inspectable", page.editor.trophies == {"2": first} and page.editor.table.topLevelItemCount() == 1 and "not unpacked" in page.editor.note.text())
        page.close()
        malformed = {"world": "_FL26MalformedTrophy", "leagues": [], "trophies": ["preserve historical invalid value"]}
        app, page = page_for(copy.deepcopy(malformed))
        ok("malformed legacy mapping data is reported without normalization or loss", app.project.recipe == malformed and page.banner.isVisible() and not page.apply_button.isEnabled())
        page.close()


def metadata_and_workers():
    with tempfile.TemporaryDirectory(prefix="trophies-metadata-") as root:
        app = App()
        app.game = SimpleNamespace(sider_dir=root)
        app.project.recipe = {"world": "_FL26Selected", "leagues": [], "trophies": {"200": "/old/reference"}}
        app.project._forget()
        db = Path(root, "livecpk", "_FL26Selected", "common", "etc", "pesdb")
        db.mkdir(parents=True)
        (db / "CompetitionRegulation.bin").write_bytes(b"first")
        rows = ROWS + [(200, [900, 901], "Selected world's cup", "cup", True)]
        jobs = []
        page = UI.Trophies(app)
        page.show()
        with patch.object(UI, "run_job", side_effect=lambda fn, done, fail: jobs.append((fn, done, fail))):
            page.shown()
            fn, done, failed = jobs.pop()
            ok("metadata is loaded lazily for the recipe's world rather than the active Sider world", page.database() == str(db) and "Loading" in page.editor.note.text())
            done(rows)
            ok("built competitions and their trophy references are displayed", any(page.editor.table.topLevelItem(i).text(0) == "Selected world's cup" for i in range(page.editor.table.topLevelItemCount())))
            page.shown()
            ok("unchanged navigation does not reload metadata", not jobs)
            stat = (db / "CompetitionRegulation.bin").stat()
            os.utime(db / "CompetitionRegulation.bin", ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))
            page.refresh()
            fn, old_done, old_failed = jobs.pop()
            app.project.adopt({"world": "_FL26OtherMetadata", "leagues": []}, None)
            settle()
            old_done(rows)
            old_failed("stale metadata error")
            ok("late metadata callbacks cannot restore another world's competitions", not any(page.editor.table.topLevelItem(i).text(0) == "Selected world's cup" for i in range(page.editor.table.topLevelItemCount())))
        page.close()


def backend_compatibility():
    with tempfile.TemporaryDirectory(prefix="trophy-copy-only-") as root:
        folder = trophy(root, "source")
        app, page = page_for({"world": "_FL26TrophyCopy", "leagues": []})
        pick(page, 2, folder)
        page.apply()
        ok("applied mapping passes the unchanged trophy backend validator", not UI.lbtrophies.problems(app.project.recipe))
        destination = Path(root, "output")
        destination.mkdir()
        with patch.object(UI.lbtrophies, "regulations", return_value={2: [2, 1026]}):
            copied = UI.lbtrophies.build(app.project.recipe, str(destination), "unused", log=lambda _line: None)
        index = json.loads(Path(destination, "trophies", "trophies.json").read_text(encoding="utf-8"))
        ok("existing trophy copy/index output accepts the page's unchanged recipe schema", copied == 1 and index["2"]["rids"] == [2, 1026] and index["2"]["from"] == folder
           and Path(destination, "trophies", "2", "asset.bin").read_bytes() == Path(folder, "asset.bin").read_bytes())
        page.close()


def production_window():
    with tempfile.TemporaryDirectory(prefix="trophies-window-") as root:
        with patch.dict(os.environ, {"APPDATA": root, "FL26_DIR": ""}):
            from modstudio import app as A
            from modstudio import competition_catalog as C, qualification_data as Q
            from test_continental_competitions import NATIVE
            import test_qualification as Qual
            with patch.object(A, "APPDIR", root), patch.object(A, "SETTINGS", str(Path(root, "settings.json"))), \
                    patch.object(A, "guess_folders", return_value=[]), \
                    patch.object(C.B, "game_competitions", return_value=NATIVE), \
                    patch.object(C.B, "game_tops", return_value=[]), \
                    patch.object(Q, "metadata", return_value=(Qual.NATIVES, Qual.ASSOCIATIONS, Qual.CONF)):
                Path(A.SETTINGS).write_text(json.dumps({"check_updates": False, "page": "Settings", "lang": "en"}), encoding="utf-8")
                window = A.Main()
                first = trophy(root, "selected-trophy")
                window.project.base = "fake-tables"
                window.project.recipe = {"world": "_FL26EmbeddedTrophies", "leagues": [], "trophies": {"2": first}}
                window.project._forget()
                window.show()
                from modstudio.pages import builder
                with patch.object(builder, "TrophiesDialog", side_effect=AssertionError("navigation must not open a trophy dialog")):
                    head = window.nav_heads["GAME CONTENT"]
                    next(a for a in head.menu().actions() if a.text() == "Trophies").trigger()
                    settle()
                    page = window.page("Trophies")
                    ok("GAME CONTENT exposes an embedded TROPHIES page through standard routing", window.stack.currentWidget() is window.holder_of["Trophies"] and page.editor.trophies == {"2": first})
                    window.open_page("Settings")
                    window.page("NewLeagues").trophies()
                    settle()
                    ok("legacy trophy callers route to that same embedded page", window.stack.currentWidget() is window.holder_of["Trophies"])
                    window.open_page("Cups")
                    cups = window.page("Cups")
                    next(a for a in cups.more_button.menu().actions() if a.text() == "Trophies").trigger()
                    settle()
                    ok("CUPS trophy shortcut shares the new page rather than a second editor", window.page("Trophies") is page and window.stack.currentWidget() is window.holder_of["Trophies"])
                leagues = window.page("Leagues")
                more = next(b for b in leagues.findChildren(QToolButton) if b.menu() and any(a.text() == "Pre-season cups" for a in b.menu().actions()))
                actual = [a.text() for a in more.menu().actions() if not a.isSeparator()]
                expected = ["Pre-season cups", "Competition names", "Competition IDs", "League order", "Seasons of the game's leagues", "World name and file..."]
                removed = {"UEFA ranking", "Trophies", "Cups of the game's countries", "Cups of our countries", "European places of the game's leagues", "First-season European clubs", "South American places"}
                ok("obsolete LEAGUES menu entries are absent", not removed.intersection(actual) and actual == expected)
                callbacks = {"Pre-season cups": "preseason", "Competition names": "competition_names", "Competition IDs": "competition_ids", "League order": "league_order", "Seasons of the game's leagues": "game_seasons"}
                for title, method in callbacks.items():
                    with patch.object(window.page("NewLeagues"), method) as called:
                        next(a for a in more.menu().actions() if a.text() == title).trigger()
                        ok(title + " keeps its original callback", called.call_count == 1)
                with patch.object(window, "open_page") as opened:
                    next(a for a in more.menu().actions() if a.text() == "World name and file...").trigger()
                    ok("World name and file keeps its original page", opened.call_args.args == ("NewLeagues",))
                window.open_page("Cups")
                cups.tabs.setCurrentIndex(2)
                e = cups.continental_section["editor"]
                e.confederation.setCurrentIndex(e.confederation.findData(2))
                e.tabs.setCurrentIndex(1)
                settle()

                ok("migrated UEFA ranking, first-season and domestic editors remain accessible", not e.qualification.rank_button.isHidden() and not e.qualification.first_button.isHidden() and all(s["editor"] is not None for s in cups.sections))
                window.open_page("Trophies")
                for width, height in ((1400, 900), (1366, 768), (1080, 640)):
                    window.resize(width, height)
                    settle()
                    holder = window.holder_of["Trophies"]
                    ok("embedded trophy layout fits %dx%d without an outer scrollbar" % (width, height), holder.verticalScrollBar().maximum() == 0 and rect(page.apply_button, page).right() < page.width() and page.editor.table.viewport().height() > 100)
                if os.environ.get("TROPHIES_CAPTURE"):
                    window.resize(1366, 768)
                    settle()
                    window.grab().save(os.environ["TROPHIES_CAPTURE"])
                pick(page, 59, first)
                with patch.object(QMessageBox, "exec", return_value=QMessageBox.Cancel):
                    window.close()
                    ok("closing with unapplied trophy changes can be cancelled safely", window.isVisible() and page.has_drafts())
                page.discard()
                window.project.dirty = False
                window.close()
                settle()


def localized_layout():
    from modstudio import i18n
    i18n.set_language("es")
    try:
        with tempfile.TemporaryDirectory(prefix="trofeos-layout-") as root:
            folder = trophy(root, "trofeo")
            app, page = page_for({"world": "_FL26Trofeos", "leagues": [], "trophies": {"2": folder}})
            settle()
            ok("Spanish labels and controls remain readable at the smaller size", page.status.text() == i18n._("No unapplied trophy changes.")
               and rect(page.discard_button, page).right() < page.width() and page.editor.table.viewport().height() > 100)
            page.close()
    finally:
        i18n.set_language("en")


if __name__ == "__main__":
    with patch.object(UI, "competition_rows", return_value=ROWS), patch.object(UI, "run_job", side_effect=inline):
        editing()
        metadata_and_workers()
        backend_compatibility()
        production_window()
        localized_layout()
    print("test_trophies_page: ok (%d)" % N)
