"""Navigation must reuse unchanged editors without retaining stale project data.

Deterministic work-count assertions, not machine-dependent timing thresholds.
For actual Main.open_page timings use profile_cups_navigation.py.
"""
import copy
import os
import tempfile
import time
from unittest.mock import patch

from test_cups_page import qa, recipe
from test_continental_competitions import make_page, select, editor, NATIVE
from modstudio import competition_catalog as C
from modstudio.pages import continental as UI
from modstudio.pages.builder import PictureField

N = 0


def ok(label, condition):
    global N
    assert condition, label
    N += 1
    print("ok %d - %s" % (N, label))


def reopen(page):
    page.hide()
    qa.processEvents()
    page.show()
    page.shown()
    qa.processEvents()


def identities(page):
    return tuple(s["editor"] for s in page.all_sections)


def run():
    app, page = make_page(recipe())
    p = app.project
    game, ours = page.sections
    original = identities(page)
    with patch.object(page, "replace_editor", wraps=page.replace_editor) as rebuild, \
            patch.object(C, "catalog", wraps=C.catalog) as catalog, \
            patch.object(C.B, "game_tops", wraps=C.B.game_tops) as tops, \
            patch.object(PictureField, "show_it", autospec=True) as images, \
            patch.object(UI, "run_job") as jobs:
        for _ in range(5):
            reopen(page)
            for index in (0, 1, 2):
                page.tabs.setCurrentIndex(index)
                qa.processEvents()
        ok("repeated navigation retains all three editors", identities(page) == original)
        ok("no table reconstruction or catalog/league parsing during unchanged navigation",
           rebuild.call_count == catalog.call_count == tops.call_count == 0)
        ok("navigation neither reloads logo images nor starts plan workers", images.call_count == jobs.call_count == 0)

    ge = game["editor"]
    ge.search.setText("Alpha")
    ge.rows[0][2].setText("Pending game cup")
    oe = ours["editor"]
    oe.search.setText("Beta")
    oe.rows[0][1][1].setText("Pending own cup")
    ce = select(page, "generated:6")
    ce.name.setText("Pending continental cup")
    ce.tabs.setCurrentIndex(1)
    # Qualification now loads source metadata lazily in a worker. Compare the
    # settled view, not the transient splitter geometry before its first layout.
    until = time.monotonic() + 3
    while ce.qualification._loading and time.monotonic() < until:
        qa.processEvents()
    for _i in range(4):
        qa.processEvents()
    view = ce.view_state()
    reopen(page)
    ok("navigation keeps draft widgets, searches and continental selection",
       identities(page) == original and ge.search.text() == "Alpha" and oe.search.text() == "Beta"
       and ce.view_state() == view and ce.name.text() == "Pending continental cup")
    for section in page.all_sections:
        page.discard_section(section)
    qa.processEvents()

    original = identities(page)
    # UI change notifications are intentionally emitted without creating undo
    # steps here, so the only work counted is the page refresh itself.
    p.recipe.setdefault("players", {})["new"] = {"rating": 70}
    with patch.object(page, "replace_editor", wraps=page.replace_editor) as rebuild:
        p.changed.emit()
        qa.processEvents()
        reopen(page)
        ok("unrelated player changes emit refresh without rebuilding cup widgets", rebuild.call_count == 0)

    class NoCopy(dict):
        def __deepcopy__(self, memo):
            raise AssertionError("unrelated player/club data copied")

    p.recipe["players"] = NoCopy(p.recipe["players"])
    p.recipe["leagues"][0]["roster"] = NoCopy({"large": list(range(1000))})
    p.recipe["leagues"][0]["cup_name"] = "Changed in Edit League"
    p.changed.emit()
    qa.processEvents()
    current = identities(page)
    ok("Edit League cup change rebuilds only Our Countries",
       current[0] is original[0] and current[1] is not original[1] and current[2] is original[2]
       and current[1].rows[0][1][1].text() == "Changed in Edit League")
    ok("section refresh does not copy unrelated players or league rosters", isinstance(p.recipe["players"], NoCopy))
    p.recipe["players"] = dict(p.recipe["players"])
    p.recipe["leagues"][0].pop("roster")
    p._forget()

    page.hide()
    before = identities(page)
    p.recipe["game_cups"][0]["name"] = "Changed outside Cups"
    p.changed.emit()
    qa.processEvents()
    ok("hidden page defers cup reconstruction", identities(page) == before)
    reopen(page)
    current = identities(page)
    ok("returning reloads changed game cups only", current[0] is not before[0]
       and current[1:] == before[1:] and current[0].rows[0][2].text() == "Changed outside Cups")

    before = identities(page)
    select(page, "game:ucl")
    p.recipe["leagues"][0]["europe"] = [[1, 0]]
    p.changed.emit()
    qa.processEvents()
    current = identities(page)
    ok("qualification changes refresh Continental without rebuilding domestic tables",
       current[:2] == before[:2] and current[2] is not before[2]
       and "competition: 1." in current[2].details["Qualification overview"].text())
    ce = select(page, "generated:6")
    ce.name.setText("Kept while qualification changes")
    p.recipe["leagues"][0]["europe"].append([2, 6])
    p.changed.emit()
    qa.processEvents()
    ok("nested qualification mutations reconcile a continental draft without replacing it",
       editor(page) is ce and ce.name.text() == "Kept while qualification changes"
       and "competition: 1." in ce.details["Qualification overview"].text())
    page.discard_section(page.continental_section)
    qa.processEvents()

    ce = select(page, "generated:6")
    callbacks = []
    with patch.object(UI, "run_job", side_effect=lambda fn, done, failed: callbacks.append(done)):
        ce.request_plan()
    reopen(page)
    callbacks.pop()({"cups": {6: {"participants": 8, "groups": 2}}})
    ok("unchanged navigation preserves a valid in-flight plan and its result",
       editor(page) is ce and "8 participants" in ce.details["Current plan"].text())
    page.hide()
    with patch.object(UI, "run_job", side_effect=lambda fn, done, failed: callbacks.append(done)):
        ce.request_plan()
    p.recipe["players"]["new"]["rating"] = 71
    p.changed.emit()
    callbacks.pop()({"cups": {6: {"participants": 32, "groups": 8}}})
    reopen(page)
    ok("any project signal invalidates cached/in-flight plans even while hidden",
       editor(page) is ce and ce._plan is None and "32 participants" not in ce.details["Current plan"].text())

    p._forget()
    ge = game["editor"]
    ge.rows[0][2].setText("Applied cached editor")
    page.apply_section(game)
    qa.processEvents()
    reopen(page)
    ok("Apply from a reused editor persists through navigation", p.recipe["game_cups"][0]["name"] == "Applied cached editor")
    p.undo()
    qa.processEvents()
    reopen(page)
    ok("Undo refreshes cached game settings", game["editor"].rows[0][2].text() == "Changed outside Cups")
    p.redo()
    qa.processEvents()
    ok("Redo refreshes cached game settings", game["editor"].rows[0][2].text() == "Applied cached editor")

    page.hide()
    before = identities(page)
    p.recipe["world"] += "Renamed"
    p.path = os.path.join(tempfile.gettempdir(), "cups-performance-rename.json")
    p.changed.emit()
    reopen(page)
    ok("world rename/Save As changes draft ownership without rebuilding widgets", identities(page) == before)
    p.path = None
    reopen(page)

    ge = game["editor"]
    ge.rows[0][2].setText("Project A suspended")
    initial = copy.deepcopy(p.recipe)
    p.adopt({"world": "_FL26DifferentProject", "leagues": []}, None)
    qa.processEvents()
    ok("switching projects does not reuse another project's editors", identities(page) != before
       and not p.recipe.get("game_cups"))
    p.adopt(initial, None)
    qa.processEvents()
    ok("returning to a project restores its isolated draft", game["editor"].rows[0][2].text() == "Project A suspended")
    page.discard_section(game)
    qa.processEvents()
    ok("Discard reloads the current project value", game["editor"].rows[0][2].text() == "Applied cached editor")

    before = identities(page)
    p.tables_changed.emit()
    qa.processEvents()
    ok("same-path table reload explicitly invalidates cached editors", all(a is not b for a, b in zip(before, identities(page))))
    # File stamps additionally catch table replacement without a project signal.
    with patch("modstudio.pages.cups.filecache.stamp", return_value=(123, 456)):
        before = identities(page)
        reopen(page)
        after = identities(page)
        ok("table file changes reload native metadata while preserving unrelated domestic widgets",
           after[0] is not before[0] and after[1] is before[1] and after[2] is not before[2])

    # Pixel refresh is incremental even when a logo is overwritten at the same path.
    with tempfile.TemporaryDirectory(prefix="cups-logo-refresh-") as root:
        path = os.path.join(root, "logo.png")
        from PySide6.QtGui import QImage, QColor
        image = QImage(16, 16, QImage.Format_ARGB32)
        image.fill(QColor("red"))
        image.save(path)
        p.recipe["game_cups"][0]["logo"] = path
        p.changed.emit()
        qa.processEvents()
        before = identities(page)
        preview = game["editor"].rows[0][3]
        image.fill(QColor("blue"))
        image.save(path)
        # Guarantee a distinct mtime even on file systems with coarse resolution.
        stat = os.stat(path)
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))
        with patch.object(preview, "show_it", wraps=preview.show_it) as reload:
            reopen(page)
            ok("changed logo file reloads only its preview without rebuilding any editor",
               identities(page) == before and reload.call_count == 1)
            reopen(page)
            ok("unchanged logo is not decoded again", reload.call_count == 1)
    page.close()


if __name__ == "__main__":
    with patch.object(C.B, "game_competitions", side_effect=lambda base: NATIVE if base else []), \
            patch.object(C.B, "game_tops", return_value=[(1, "Alpha Game", False), (2, "Beta Game", True)]):
        run()
    print("test_cups_performance: ok (%d)" % N)
