"""Offline Continental > Competitions UI, storage, settings and draft regression tests.

No game files are changed. Native metadata is mocked; real plan integration can be
checked separately against locally unpacked tables.
"""
import copy
import json
import os
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_cups_page import App, qa
from PySide6.QtCore import Qt
from modstudio import competition_catalog as C
from modstudio.pages import continental as UI, builder
from modstudio.pages.cups import Cups
from modstudio.pages.cup_editors import CupConflict

N = 0
NATIVE = [(c.number, c.name, [c.number + 10]) for c in C.ORIGINALS] + [(98, "National teams cup", [98])]


def ok(label, condition):
    global N
    assert condition, label
    N += 1
    print("ok %d - %s" % (N, label))


def recipe():
    return {"world": "_FL26ContinentalTest", "players": {"keep": {"data": [1, 2, 3]}},
            "edits": {"competitions": {"2": {"name": "Old Champions", "future": 23},
                                         "98": {"name": "National cup override"}},
                      "leagues": {"12": {"name": "Unrelated"}}},
            "ccup_names": {"6": "Old African cup", "unknown": "Preserve"},
            "ccup_logos": {"0": "canonical-caf.png", "unknown": "future.png"},
            "caf_super_cup_logo": "different-legacy-caf.png",
            "samerica_super_cup_logo": "legacy-recopa.png",
            "leagues": [{"name": "Test League", "country": "Test", "clubs": 12, "cup": True,
                          "europe": [[1, 3], [2, 4], [3, 9]], "future": "keep"}],
            "game_europe": {"29": [[1, 3], [2, 4], [3, 9]]},
            "uefa_rank": ["g1"], "uefa_seed": [["g1", 1, 0]],
            "preseason_cups": [{"name": "Untouched"}], "trophies": {"2": "unchanged"}}


def make_page(data=None):
    app = App()
    app.project.adopt(copy.deepcopy(data if data is not None else recipe()), None)
    page = app.cups = Cups(app)
    page.resize(1100, 780)
    page.show()
    page.shown()
    page.tabs.setCurrentIndex(2)
    for _ in range(3):
        qa.processEvents()
    return app, page


def editor(page):
    return page.continental_section["editor"]


def select(page, key):
    e = editor(page)
    c = e.competitions[key]
    e.confederation.setCurrentIndex(e.confederation.findData(c.confederation))
    for i in range(e.list.count()):
        if e.list.item(i).data(Qt.UserRole) == key:
            e.list.setCurrentRow(i)
            break
    assert e._selected == key
    return e


def apply(page):
    page.apply_section(page.continental_section)
    for _ in range(3):
        qa.processEvents()


def discard(page):
    page.discard_section(page.continental_section)
    for _ in range(3):
        qa.processEvents()


def run():
    app, page = make_page(dict(recipe(), conmebol="modern"))
    p, e = app.project, editor(page)
    initial = copy.deepcopy(p.recipe)
    players = p.recipe["players"]
    ok("six confederations in approved order", [e.confederation.itemText(i) for i in range(6)]
       == ["UEFA", "CONMEBOL", "CONCACAF", "AFC", "CAF", "OFC"])
    ok("Competitions and Qualification sections", [e.tabs.tabText(i) for i in range(2)]
       == ["Competitions", "Qualification"])
    expected = {2: 4, 4: 3, 6: 1, 3: 3, 5: 3, 7: 1}
    for conf, count in expected.items():
        e.confederation.setCurrentIndex(e.confederation.findData(conf))
        ok("confederation %d lists its competitions" % conf, e.list.count() == count)
        ok("only supported confederation controls are exposed for %d" % conf,
           all(box.isHidden() == (next(s for s in C.SETTINGS if s.key == key).confederation != conf)
               for key, box in e.settings.items()))
    ok("national-team competitions stay outside this catalog", not any(c.number == 98 for c in e.rows))
    ok("every engine-generated continental cup is represented", {c.number for c in e.rows if c.storage == "generated"}
       == {c[0] for c in C.W.CCUPS} | {C.B.caf_super_cup({})["number"], C.B.samerica_super_cup({})["number"]})
    e = select(page, "game:afc")
    ok("AFC Elite maps to the existing native slot without renaming game data", e.original_name.text()
       == "AFC Champions League Elite" and e.name.placeholderText() == "AFC Champions League"
       and e.competitions["game:afc"].number == 8 and e.competitions["game:afc"].targets == (5,)
       and "separate modern Elite format is not implemented" in e.details["Format and stages"].text())
    with patch.object(C, "native_metadata", return_value=({6: 4}, {6: [(11, 3, 16)]})), \
            patch.object(C.B, "game_competitions", return_value=NATIVE + [(6, "Additional native slot", [11])]):
        discovered = {c.key: c for c in C.catalog("fake-tables")}
    ok("additional engine-recognized native table entries are discovered", discovered["game:6"].confederation == 4
       and discovered["game:6"].native_stages == ((11, 3, 16),))
    ok("native format details use actual stage limits", "table limit 16 clubs" in
       dict(C.information(discovered["game:6"], p.recipe))["Format and stages"])
    ok("navigation creates no changes or Undo steps", p.recipe == initial and not p.can_undo())
    e = select(page, "game:ucl")
    ok("selection loads original identity inline", e.name.text() == "Old Champions" and e.identity_body.isEnabled())
    e.name.setText("New Champions")
    e.logo.path = "ucl-custom.png"
    e.logo_changed()
    e = select(page, "game:afc")
    e.name.setText("Custom Elite slot")
    e.logo.path = "elite-slot.png"
    e.logo_changed()
    e = select(page, "generated:8")
    e.name.setText("New AFC Two")
    e.logo.path = "afc-two.png"
    e.logo_changed()
    e = select(page, "uecl")
    e.name.setText("My Conference")
    e.logo.path = "conference.png"
    e.logo_changed()
    e.settings["uecl"].setChecked(False)
    ok("UECL switch is a draft, not an immediate write", "uecl" not in p.recipe
       and e._selected != "uecl"
       and "uecl" not in [e.list.item(i).data(Qt.UserRole) for i in range(e.list.count())])
    e.tabs.setCurrentIndex(1)
    page.tabs.setCurrentIndex(0)
    page.shown()
    page.tabs.setCurrentIndex(2)
    e = select(page, "game:ucl")
    ok("selection and page navigation preserve pending name/logo", e.name.text() == "New Champions"
       and e.logo.path == "ucl-custom.png" and p.recipe == initial)
    apply(page)
    ok("original identity patches edits.competitions only", p.recipe["edits"]["competitions"]["2"]
       == {"name": "New Champions", "logo": "ucl-custom.png", "future": 23})
    ok("generated identity uses logical cup-number storage", p.recipe["ccup_names"]["8"] == "New AFC Two"
       and p.recipe["ccup_logos"]["8"] == "afc-two.png")
    ok("native AFC ID 8 and generated AFC Two number 8 remain distinct", p.recipe["edits"]["competitions"]["8"]
       == {"name": "Custom Elite slot", "logo": "elite-slot.png"})
    ok("UECL retains dedicated storage and checkbox behavior", p.recipe["uecl"] is False
       and p.recipe["uecl_name"] == "My Conference" and p.recipe["uecl_logo"] == "conference.png")
    ok("Apply preserves unknown metadata, other tools and player identity", p.recipe["players"] is players
       and p.recipe["edits"]["competitions"]["98"] == initial["edits"]["competitions"]["98"]
       and all(p.recipe[k] == initial[k] for k in ("preseason_cups", "trophies", "uefa_rank", "uefa_seed", "leagues", "game_europe")))
    ok("unrelated identity edits do not normalize legacy logo aliases", p.recipe["caf_super_cup_logo"]
       == "different-legacy-caf.png" and p.recipe["samerica_super_cup_logo"] == "legacy-recopa.png")
    after = copy.deepcopy(p.recipe)
    ok("Undo restores the exact old continental recipe", p.undo() and p.recipe == initial)
    qa.processEvents()
    ok("Redo restores all continental edits", p.redo() and p.recipe == after)
    qa.processEvents()
    e = select(page, "generated:0")
    ok("CAF logo uses canonical override ahead of legacy alias", e.logo.path == "canonical-caf.png")
    e.logo.clear()
    e.settings["caf_super_cup"].setChecked(False)
    apply(page)
    ok("clearing CAF logo clears both canonical and legacy fallback", "0" not in p.recipe["ccup_logos"]
       and "caf_super_cup_logo" not in p.recipe and p.recipe["caf_super_cup"] is False)
    e = select(page, "generated:-1")
    ok("Recopa reads a legacy-only logo without normalizing storage", e.logo.path == "legacy-recopa.png"
       and "-1" not in p.recipe["ccup_logos"])
    e.logo.path = "recopa-new.png"
    e.logo_changed()
    apply(page)
    ok("Recopa logo edit updates existing fallback consistently", p.recipe["ccup_logos"]["-1"]
       == p.recipe["samerica_super_cup_logo"] == "recopa-new.png")
    select(page, "generated:-1").logo.clear()
    apply(page)
    ok("Recopa clear cannot resurrect a legacy logo", "-1" not in p.recipe["ccup_logos"]
       and "samerica_super_cup_logo" not in p.recipe)
    e = select(page, "game:ucl")
    e.name.setText("Pending conflict")
    p.recipe["edits"]["competitions"]["2"]["name"] = "Changed through old tool"
    p.touch()
    qa.processEvents()
    apply(page)
    ok("old Competition Names conflicts keep draft and live value", editor(page).name.text() == "Pending conflict"
       and p.recipe["edits"]["competitions"]["2"]["name"] == "Changed through old tool"
       and "changed elsewhere" in page.continental_section["message"].text())
    discard(page)
    ok("Discard reloads the current project", editor(page).name.text() == "Changed through old tool")
    e = select(page, "game:ucl")
    e.name.setText("Merge name")
    p.recipe["edits"]["competitions"]["2"]["logo"] = "external-logo.png"
    p.touch()
    qa.processEvents()
    ok("unedited identity fields refresh while another field has a draft", editor(page).logo.path == "external-logo.png")
    apply(page)
    ok("disjoint identity edits merge", p.recipe["edits"]["competitions"]["2"]["name"] == "Merge name"
       and p.recipe["edits"]["competitions"]["2"]["logo"] == "external-logo.png")
    e = select(page, "game:afc")
    e.name.setText("AFC pending while tables refresh")
    with patch.object(C, "native_metadata", return_value=({8: 3}, {8: [(15, 2, 16), (16, 3, 16)]})):
        p.tables_changed.emit()
        qa.processEvents()
    ok("table refresh updates stage metadata while preserving drafts", editor(page).name.text()
       == "AFC pending while tables refresh" and "table limit 16 clubs" in editor(page).details["Format and stages"].text())
    with patch.object(C.B, "game_competitions", return_value=[c for c in NATIVE if c[0] != 8]):
        p.tables_changed.emit()
        qa.processEvents()
        apply(page)
    ok("removed native competition cannot receive a stale draft", p.recipe["edits"]["competitions"]["8"]["name"]
       == "Custom Elite slot" and "not in the selected" in page.continental_section["message"].text())
    discard(page)
    select(page, "generated:14").name.setText("OFC suspended")
    saved = copy.deepcopy(p.recipe)
    p.adopt({"world": "_FL26Another", "leagues": []}, None)
    qa.processEvents()
    ok("project switch isolates continental drafts", not p.recipe.get("ccup_names") and page.has_drafts())
    p.adopt(saved, None)
    qa.processEvents()
    ok("reopening project restores confederation and draft", editor(page).confederation.currentData() == 7
       and editor(page).name.text() == "OFC suspended")
    discard(page)
    ok("Discard removes the archived continental draft", not page.has_drafts())
    p.adopt(initial, None)
    qa.processEvents()
    clean = copy.deepcopy(p.recipe)
    apply(page)
    ok("no-op Apply preserves legacy recipe exactly", p.recipe == clean and not p.can_undo())
    select(page, "game:ucl").name.setText("Autosaved continental")
    with tempfile.TemporaryDirectory(prefix="continental-ui-") as folder:
        p.path = os.path.join(folder, "recipe.json")
        apply(page)
        p.autosave()
        with open(p.path, encoding="utf-8") as stream:
            stored = json.load(stream)
        ok("Project autosave persists continental edits", stored["edits"]["competitions"]["2"]["name"]
           == "Autosaved continental" and not p.dirty)
    p.path = None
    legacy = recipe()
    legacy.update(edits=None, ccup_names=None, ccup_logos=None)
    p.adopt(legacy, None)
    qa.processEvents()
    untouched = copy.deepcopy(p.recipe)
    apply(page)
    ok("legacy null optional maps are not normalized on open or no-op Apply", p.recipe == untouched)
    select(page, "game:ucl").name.setText("Native from null map")
    select(page, "generated:6").name.setText("Generated from null map")
    e = select(page, "generated:6")
    e.logo.path = "new-null-map-logo.png"
    e.logo_changed()
    apply(page)
    ok("explicit identity edits support legacy null maps", p.recipe["edits"]["competitions"]["2"]["name"]
       == "Native from null map" and p.recipe["ccup_names"]["6"] == "Generated from null map"
       and p.recipe["ccup_logos"]["6"] == "new-null-map-logo.png")
    page.close()


def modern_tests():
    data = recipe()
    data["leagues"][0]["europe"] += [[4, C.W.LIB_F1], [5, C.W.SUD_FIRST]]
    data["game_europe"]["29"] += [[4, C.W.LIB_F2]]
    data["conmebol_associations"] = {"Bolivia": [[1, 3]]}
    app, page = make_page(data)
    p = app.project
    e = select(page, "game:libertadores")
    baseline = copy.deepcopy(p.recipe)
    ok("modern mode detected from places and associations without explicit flag", e.settings["conmebol"].isChecked()
       and "conmebol" not in p.recipe and "Phase 1" in e.system_guide.text())
    e.settings["conmebol"].setChecked(False)
    e.name.setText("Pending Libertadores")
    ok("classic preview is accurate and non-destructive", "Classic mode" in e.details["Format and stages"].text()
       and p.recipe == baseline)
    with patch.object(UI, "ask", return_value=False) as confirm:
        apply(page)
    ok("declining modern-mode warning preserves all edits and source data", p.recipe == baseline
       and not p.can_undo() and editor(page).name.text() == "Pending Libertadores")
    ok("existing warning reports the actual removed-place count", confirm.call_count == 1
       and "4 places" in confirm.call_args.args[2])
    with patch.object(UI, "ask", return_value=True):
        apply(page)
    ok("accepted warning uses existing cleanup for every source", not C.modern(p.recipe)
       and "conmebol_associations" not in p.recipe
       and p.recipe["leagues"][0]["europe"] == [[1, 3], [2, 4], [3, 9]]
       and p.recipe["game_europe"]["29"] == [[1, 3], [2, 4], [3, 9]])
    ok("mode and identities are one Undo operation", p.undo() and p.recipe == baseline)
    qa.processEvents()
    # The old dialog uses the very same cleanup/warning operation.
    old = builder.SouthAmericaDialog(None, p)
    old.modern.setChecked(False)
    with patch.object(builder, "ask", return_value=False):
        old.ok()
    ok("legacy South American dialog retains cancellation behavior", p.recipe == baseline)
    old.reject()
    discard(page)
    # Explicit activation stays a boolean draft until Apply.
    p.adopt(recipe(), None)
    qa.processEvents()
    e = select(page, "game:libertadores")
    ok("classic Sudamericana remains documented without being offered", "Existing classic Sudamericana projects" in e.system_guide.text()
       and e.list.count() == 1)
    e.settings["conmebol"].setChecked(True)
    e = select(page, "generated:9")
    ok("modern Sudamericana preview includes supported stage counts", "32 assigned clubs" in e.system_guide.text()
       and "12 direct group places" in e.system_guide.text() and "conmebol" not in p.recipe
       and "two-leg play-off" in e.system_guide.text())
    apply(page)
    ok("modern activation uses the existing recipe value", p.recipe["conmebol"] == "modern")
    discard(page)
    page.close()


def plan_tests():
    app, page = make_page()
    e = select(page, "generated:6")
    baseline = copy.deepcopy(app.project.recipe)
    fake_plan = {"leagues": [], "uecl": True,
                 "ccups": [{"number": 6, "groups": 2, "entry": list(range(8))}]}
    with patch.object(C.B, "plan", return_value=fake_plan) as backend, \
            patch.object(UI, "run_job", side_effect=lambda fn, done, failed: done(fn(lambda _x: None))):
        e.request_plan()
    ok("exact information uses the existing plan backend", backend.call_count == 1
       and "8 participants; 2 groups" in e.details["Current plan"].text()
       and app.project.recipe == baseline and not app.project.can_undo())
    jobs = []
    with patch.object(UI, "run_job", side_effect=lambda fn, done, failed: jobs.append(done)):
        e.request_plan()
    e.name.setText("Changed during plan")
    jobs[0]({"cups": {6: {"participants": 32, "groups": 8}}})
    ok("stale asynchronous plan results are ignored", "32 participants" not in e.details["Current plan"].text()
       and "Values changed" in e.plan_note.text())
    preview = C.preview_recipe(app.project.recipe, e.changes(), e.competitions)
    ok("preview does not copy or mutate large player data", preview["players"] is app.project.recipe["players"]
       and app.project.recipe == baseline)
    with patch.object(UI, "run_job", side_effect=lambda fn, done, failed: jobs.append(done)):
        e.request_plan()
    discard(page)
    jobs[-1]({"cups": {6: {"participants": 32, "groups": 8}}})
    ok("late plan callback cannot populate a replacement editor", editor(page)._plan is None)
    app.project.base = None
    app.project.tables_changed.emit()
    qa.processEvents()
    e = select(page, "game:ucl")
    ok("missing tables disable original competition identity editing", not e.identity_body.isEnabled())
    e = select(page, "generated:6")
    e.name.setText("Portable CAF")
    ok("generated editing remains available without game tables", e.identity_body.isEnabled()
       and not e.check_plan.isEnabled() and page.continental_section["apply"].isEnabled())
    apply(page)
    ok("generated name persists without native tables", app.project.recipe["ccup_names"]["6"] == "Portable CAF")
    if os.environ.get("CONTINENTAL_SNAPSHOT"):
        for _ in range(4):
            qa.processEvents()
        page.grab().save(os.environ["CONTINENTAL_SNAPSHOT"])
    page.close()


if __name__ == "__main__":
    with patch.object(C.B, "game_competitions", side_effect=lambda base: NATIVE if base else []), \
            patch.object(C.B, "game_tops", return_value=[(1, "Original league", False)]):
        run()
        modern_tests()
        plan_tests()
    print("test_continental_competitions: ok (%d)" % N)
