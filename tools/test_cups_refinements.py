"""CUPS refinements: visibility, classic data, system guide, defaults and Build migration.

Offline Qt tests. All recipe persistence stays in memory; no real game is modified.
"""
import copy
import os
import sys
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_cups_page import qa
from test_continental_competitions import make_page, select, editor, apply, discard, recipe, NATIVE
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QToolButton, QInputDialog, QDialog
from modstudio import competition_catalog as C, competition_guides as G
from modstudio.pages import builder, continental
import mkuecl

N = 0


def ok(label, condition):
    global N
    assert condition, label
    N += 1
    print("ok %d - %s" % (N, label))


def keys(e):
    return [e.list.item(i).data(Qt.UserRole) for i in range(e.list.count())]


def visibility():
    data = recipe()
    data.update(conmebol="modern", uecl=True, caf_super_cup=True)
    app, page = make_page(data)
    p = app.project
    for feature, target in (("uecl", "uecl"), ("conmebol", "generated:9"), ("caf_super_cup", "generated:0")):
        e = select(page, target)
        baseline = copy.deepcopy(p.recipe)
        e.name.setText("Draft " + feature)
        e.logo.path = feature + ".png"
        e.logo_changed()
        e.settings[feature].setChecked(False)
        ok(feature + ": hidden immediately and selection falls back", target not in keys(e)
           and e._selected in keys(e) and e._selected != target)
        ok(feature + ": hiding keeps source data and pending identities", p.recipe == baseline
           and e._values[("identity", target, "name")] == "Draft " + feature
           and e._values[("identity", target, "logo")] == feature + ".png")
        if feature == "conmebol":
            ok("modern off lists only Libertadores", keys(e) == ["game:libertadores"])
        e.settings[feature].setChecked(True)
        e = select(page, target)
        ok(feature + ": re-enabling restores name/logo drafts", e.name.text() == "Draft " + feature
           and e.logo.path == feature + ".png")
        p._snap_at = 0
        apply(page)
        e = select(page, target)
        e.settings[feature].setChecked(False)
        p._snap_at = 0
        apply(page)
        c = editor(page).competitions[target]
        ok(feature + ": Apply hides without deleting identity", target not in keys(editor(page))
           and C.identity(p.recipe, c, "name") == "Draft " + feature
           and C.identity(p.recipe, c, "logo") == feature + ".png")
        ok(feature + ": Undo restores enabled state", p.undo())
        qa.processEvents()
        ok(feature + ": Undo refreshes visibility", target in keys(editor(page)))
        ok(feature + ": Redo restores hidden state", p.redo())
        qa.processEvents()
        ok(feature + ": Redo keeps identity", target not in keys(editor(page))
           and C.identity(p.recipe, c, "name") == "Draft " + feature)
        editor(page).settings[feature].setChecked(True)
        discard(page)
        ok(feature + ": Discard reloads applied visibility", target not in keys(editor(page)))
    page.close()


def drafts_and_warning():
    app, page = make_page()
    p = app.project
    e = select(page, "game:libertadores")
    original = copy.deepcopy(p.recipe)
    e.settings["conmebol"].setChecked(True)
    select(page, "generated:-1").name.setText("Recopa draft")
    select(page, "generated:9").name.setText("Sudamericana draft")
    editor(page).settings["conmebol"].setChecked(False)
    ok("both hidden competitions retain their independent drafts", keys(editor(page)) == ["game:libertadores"]
       and len(editor(page).dirty_keys()) == 2 and p.recipe == original)
    p.adopt({"world": "_FL26OtherCups", "leagues": []}, None)
    qa.processEvents()
    ok("project switching archives hidden drafts", page.has_drafts() and not p.recipe.get("ccup_names"))
    p.adopt(original, None)
    qa.processEvents()
    ok("returning restores the correct hidden list", keys(editor(page)) == ["game:libertadores"])
    editor(page).settings["conmebol"].setChecked(True)
    ok("returning restores hidden Sudamericana draft", select(page, "generated:9").name.text() == "Sudamericana draft")
    ok("returning restores hidden Recopa draft", select(page, "generated:-1").name.text() == "Recopa draft")
    discard(page)
    modern = recipe()
    modern["leagues"][0]["europe"] += [[4, C.W.LIB_F1]]
    modern["game_europe"]["29"] += [[4, C.W.SUD_FIRST]]
    modern["conmebol_associations"] = {"Bolivia": [[1, 3]]}
    p.adopt(modern, None)
    qa.processEvents()
    e = select(page, "generated:9")
    baseline = copy.deepcopy(p.recipe)
    e.name.setText("Pending hidden identity")
    e.settings["conmebol"].setChecked(False)
    with patch.object(continental, "ask", return_value=False) as confirm:
        apply(page)
    ok("hiding alone does not remove modern places; declined Apply is atomic", p.recipe == baseline
       and not p.can_undo() and confirm.call_count == 1
       and editor(page)._values[("identity", "generated:9", "name")] == "Pending hidden identity")
    with patch.object(continental, "ask", return_value=True):
        apply(page)
    ok("confirmed cleanup removes only existing modern-only allocations", not C.modern(p.recipe)
       and p.recipe["leagues"][0]["europe"] == [[1, 3], [2, 4], [3, 9]]
       and p.recipe["game_europe"]["29"] == [[1, 3], [2, 4], [3, 9]]
       and "conmebol_associations" not in p.recipe)
    ok("hidden names are preserved when applying mode cleanup", p.recipe["ccup_names"]["9"] == "Pending hidden identity")
    ok("Undo restores all modern data in one step", p.undo() and p.recipe == baseline)
    qa.processEvents()
    ok("Undo restores the modern competition list", "generated:9" in keys(editor(page))
       and "generated:-1" in keys(editor(page)))
    page.close()


def qualification_compatibility():
    old_places = [[1, 3], [2, 9], [0, 9]]
    table = builder.EuropeTable(old_places, 12, modern=False)
    ok("classic selector offers no new Sudamericana destination", 9 not in dict(table.competitions))
    ok("opening classic places preserves the exact destinations", sorted(table.places()) == sorted(old_places))
    existing = [table.table.cellWidget(r, 1) for r in range(table.table.rowCount())
                if table.table.cellWidget(r, 1).currentData() == 9]
    ok("legacy Sudamericana entries remain selected but are not selectable as new targets", len(existing) == 2
       and all(not combo.model().item(combo.findData(9)).isEnabled() for combo in existing))
    table.add()
    cb = table.table.cellWidget(table.table.rowCount() - 1, 1)
    ok("new rows cannot select classic Sudamericana", cb.findData(9) == -1)
    table.set_confed(4)
    ok("classic South American preset cannot bypass the restriction", table.preset.isHidden())
    table.set_confed(3)
    ok("unrelated confederation presets are preserved", not table.preset.isHidden())
    modern = builder.EuropeTable([], 12, modern=True)
    modern.add()
    options = dict(modern.competitions)
    ok("modern selector exposes groups and first stage", 9 in options and C.W.SUD_FIRST in options)
    ok("engine still validates legacy Sudamericana places", not C.B.europe_problems(12, old_places, True))
    cups, _notes = C.B.ccup_plan([("Legacy league", i, 9, 0) for i in range(1, 5)], {"Legacy league": 12})
    ok("engine does not generate classic Sudamericana and explains migration", not any(c["number"] == 9 for c in cups)
       and any("retained but inactive" in n for n in _notes))
    own = [("Legacy league", i, 9, 0) for i in range(1, 5)]
    extra = ("Original league", 3)
    field = next(c for c in C.B.ccup_plan(own + [(extra[0], extra[1], 9, 0)],
                                        modern_conmebol=True)[0] if c["number"] == 9)["entry"]
    ok("reading an archived classic world can still reconstruct its original-league places",
       C.B.ccup_given(9, field, own, [], [extra]) == [extra])
    app, page = make_page()
    p = app.project
    league = p.recipe["leagues"][0]
    league["europe"] = copy.deepcopy(old_places)
    dialog = builder.LeagueDialog(None, p, league)
    dialog.ok()
    ok("Edit League preserves legacy Sudamericana on OK", dialog.result() == QDialog.Accepted
       and sorted(dialog.league["europe"]) == sorted(old_places))
    p.recipe["game_europe"] = {"1": [[2, 9]]}
    with patch.object(C.B, "game_europe_tops", return_value=[(1, "Original league", 12, [])]):
        original = builder.GameEuropeDialog(None, p)
        original.ok()
    ok("original game league editor preserves classic overrides", original.result == {"1": [[2, 9]]})
    page.close()


def menu_and_build():
    app, page = make_page()
    menu = next(b.menu() for b in page.findChildren(QToolButton)
                if b.menu() and any(a.text() == "Competition IDs" for a in b.menu().actions()))
    ok("CUPS More retains all three tools", {a.text() for a in menu.actions()}
       >= {"Competition names", "Competition IDs", "Trophies"})
    ids = next(a for a in menu.actions() if a.text() == "Competition IDs")
    for index in range(3):
        page.tabs.setCurrentIndex(index)
        ids.trigger()
        ok("Competition IDs accessible from CUPS section %d" % index, app.opened[-1] == "ids")
    with patch.object(builder, "CompetitionIdsDialog") as existing:
        builder.NewLeagues.competition_ids(page)
    ok("Competition IDs delegates to the existing dialog and logic", existing.call_args.args == (page, app.project)
       and existing.return_value.finish.call_count == 1)
    # Build's settings owner is separate from the Project's test owner (which disables
    # autosave), so no user APPDATA or installed game can be written by this fixture.
    game = SimpleNamespace(ok=lambda: True, livecpk_dir="unused-test-directory")
    build_app = SimpleNamespace(project=app.project, settings={}, game=game,
                                page=app.page, open_page=app.open_page, bus=app.bus)
    build = builder.Build(build_app)
    ok("Build has no duplicate continental controls", not any(hasattr(build, name)
       for name in ("uecl", "uecl_name", "uecl_logo", "cafsc"))
       and not any(box.text() in ("Include the Conference League", "CAF Super Cup")
                   for box in build.findChildren(QCheckBox)))
    build.cupdraw.setCurrentIndex(build.cupdraw.findData("random"))
    ok("country cup draw remains functional in Build", app.project.recipe["cup_draw"] == "random")
    ok("Build has no redundant Continental navigation button", not hasattr(build, "b_cups"))
    for enabled in (False, True):
        app.project.recipe["uecl"] = enabled
        with patch.object(build, "ready_blocks", return_value=False), \
                patch.object(QInputDialog, "getText", return_value=("", False)) as prompt:
            build.do_europe_only()
        ok("European-only tool reads applied recipe option %s" % enabled,
           ("and the Conference League" in prompt.call_args.args[2]) == enabled)
    build.close()
    page.close()


def guides_and_default():
    groups = G.sections(4, {}, True)
    headings = [h for h, _paragraphs in groups]
    text = " ".join(p for _h, paragraphs in groups for p in paragraphs)
    ok("modern guide is divided into readable sections", len(headings) >= 8
       and all(paragraphs for _heading, paragraphs in groups))
    ok("guide covers each qualifying phase and participant progression", all(s in text
       for s in ("Phase 1: 6", "Phase 2: 13", "Phase 3:", "26 configured", "2 protected", "4 phase-3")))
    ok("guide covers Sudamericana groups, transfers and play-off", all(s in text
       for s in ("32 assigned", "12 configured", "16 first-stage winners", "8 group runners-up", "8 Libertadores group thirds")))
    ok("guide covers titleholder cascade and first-season limitations", all(s in text
       for s in ("cascades", "no retained previous-season champions", "late February", "normally stays unplayed", "fallbacks")))
    classic = " ".join(p for _heading, paragraphs in G.sections(4, {}, False) for p in paragraphs)
    ok("classic guide explains disabled generation and retained data", "no longer generated" in classic
       and "not converted" in classic and "confirmation" in classic)
    ok("UEFA explanation moved into Continental", "36 clubs" in str(G.sections(2, {}, False)))
    ok("Conference League default constant changed, IDs retained", mkuecl.NAME == "UEFA Conference League"
       and mkuecl.CODE == "FL_UECL" and (mkuecl.CID, mkuecl.REG, mkuecl.KO) == (174, 186, 187))
    args = mkuecl.phases_args("unused-base", "unused-out", [1, 2])
    ok("generation receives the new default", args[args.index("--name") + 1] == "UEFA Conference League")
    for custom in ("My own Conference", "FL Conference League"):
        args = mkuecl.phases_args("unused-base", "unused-out", [1, 2], name=custom)
        ok("generation preserves explicit custom name %s" % custom, args[args.index("--name") + 1] == custom)
    app, page = make_page()
    e = select(page, "uecl")
    ok("new UI shows the new default without writing a recipe field", e.name.placeholderText() == "UEFA Conference League"
       and "uecl_name" not in app.project.recipe)
    app.project.recipe["uecl_name"] = "FL Conference League"
    app.project.touch()
    qa.processEvents()
    ok("explicit legacy Conference League name is preserved", select(page, "uecl").name.text() == "FL Conference League")
    select(page, "generated:6").name.setText("Unrelated CAF rename")
    apply(page)
    ok("unrelated Apply does not rewrite the legacy name", app.project.recipe["uecl_name"] == "FL Conference League")
    page.close()


if __name__ == "__main__":
    with patch.object(C.B, "game_competitions", side_effect=lambda base: NATIVE if base else []), \
            patch.object(C.B, "game_tops", return_value=[(1, "Original league", False)]):
        visibility()
        drafts_and_warning()
        qualification_compatibility()
        menu_and_build()
        guides_and_default()
    print("test_cups_refinements: ok (%d)" % N)
