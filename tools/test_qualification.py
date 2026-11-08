"""Continental qualification/preset/first-season regression suite.

Qt metadata fixtures intentionally relocate original league IDs. Real validators
europe_problems/europe_first and the real UEFA key are used. No world is built.
Optional: --tables <pesdb> additionally checks real source mappings and B.plan.
"""
import copy
import json
import os
import sys
import tempfile
from collections import Counter
from types import SimpleNamespace, MethodType
from unittest.mock import patch

from test_cups_page import qa
from test_continental_competitions import make_page, editor, NATIVE
from modstudio import qualification_data as Q
from modstudio import competition_catalog as C
from modstudio.pages import qualification as UI, first_season as F, builder
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QAbstractItemView
import uefakey

N = 0
CONF = {"England": 2, "Germany": 2, "Russia": 2, "Brazil": 4, "Argentina": 4,
        "Chile": 4, "Colombia": 4, "Bolivia": 4, "Ecuador": 4, "Paraguay": 4,
        "Peru": 4, "Uruguay": 4, "Venezuela": 4, "Japan": 3, "Nigeria": 5,
        "Ghana": 5, "Canada": 6, "USA": 6, "New Zealand": 7}
NATIVES = (
    Q.Source("game", "501", "Relocated English league", "England", 2, 20, True, ((1, 0), (0, 1), (2, 12)), 1),
    Q.Source("game", "502", "Russian league", "Russia", 2, 18, True, ((1, 0), (2, 10)), 2),
    Q.Source("game", "29", "Brazil original", "Brazil", 4, 20, True, country_id=3),
    Q.Source("game", "30", "Argentina original", "Argentina", 4, 30, True, country_id=4),
    Q.Source("game", "67", "Chile original", "Chile", 4, 16, True, country_id=5),
    Q.Source("game", "168", "Colombia original", "Colombia", 4, 20, True, country_id=6),
    Q.Source("game", "52", "Japan original", "Japan", 3, 20, True, ((1, 5), (2, 5), (3, 5), (4, 5)), 7),
    Q.Source("game", "51", "USA original", "USA", 6, 20, False, country_id=8))
ASSOCIATIONS = tuple(Q.Source("association", country, country, country, 4, cap, country_id=200 + i)
                     for i, (country, cap) in enumerate((("Bolivia", 6), ("Ecuador", 4), ("Paraguay", 3),
                                                       ("Peru", 3), ("Uruguay", 2), ("Venezuela", 1))))


def ok(label, condition):
    global N
    assert condition, label
    N += 1
    print("ok %d - %s" % (N, label))


def data():
    leagues = [dict(name="Europe One", country="England", clubs=20, cup=True,
                    club_names=["Local %d" % i for i in range(20)], game_clubs=[{"at": 0, "id": 101}]),
               dict(name="Europe Two", country="Germany", clubs=18, cup=False)]
    leagues += [dict(name="South %d" % i, country=s.country, clubs=16, cup=i % 2 == 0) for i, s in enumerate(ASSOCIATIONS)]
    leagues += [dict(name="Asia", country="Japan", clubs=18, cup=True),
                dict(name="Africa A", country="Nigeria", clubs=18, cup=True),
                dict(name="Africa B", country="Ghana", clubs=18, cup=False),
                dict(name="North", country="Canada", clubs=16, cup=True),
                dict(name="Oceania", country="New Zealand", clubs=12, cup=True),
                dict(name="Lower", above="South 0", country="Bolivia", clubs=12),
                dict(name="Exhibition", exhibition=True, country="Bolivia", clubs=12),
                dict(name="Unassigned", others="america", country="Bolivia", clubs=1)]
    return {"world": "_FL26QualificationTest", "leagues": leagues, "conmebol": "modern",
            "players": {"keep": {"edits": {"1": {"name": "Preserved"}}}},
            "edits": {"competitions": {"2": {"name": "Keep Champions"}}},
            "ccup_names": {"9": "Keep Sudamericana"}, "future_key": {"keep": True}}


def inline(fn, done, failed):
    result = fn(lambda _x: None)
    done(result)


def labels(recipe, _base):
    result = {i: "Original %d — Native England [%d]" % (i, i) for i in range(101, 151)}
    aliases = {i: ("game", i) for i in result}
    for L in recipe.get("leagues") or []:
        if L.get("others") or L.get("exhibition"):
            continue
        inherited = {int(g["at"]): int(g["id"]) for g in L.get("game_clubs") or []}
        for k in range(L["clubs"]):
            ref = "%s/%d" % (L["name"], k)
            result[ref] = "%s — %s / %s [%s]" % (Q.B.club_name(dict(name=L["name"], club_names=L.get("club_names") or []), k), L["name"], L["country"], ref)
            aliases[ref] = ("game", inherited[k]) if k in inherited else ("new", L["name"], k)
    return result, aliases


def page_for(recipe=None, conf=2):
    app, page = make_page(recipe if recipe is not None else data())
    app.project.confeds = dict(CONF)
    app.project.countries = sorted(CONF)
    e = editor(page)
    e.confederation.setCurrentIndex(e.confederation.findData(conf))
    e.tabs.setCurrentIndex(1)
    qa.processEvents()
    return app, page, e, e.qualification


def choose(q, kind, key):
    q._selected = ("qualification", kind, key)
    assert q.current_source(), (kind, key)
    for i in range(q.list.topLevelItemCount()):
        group = q.list.topLevelItem(i)
        for j in range(group.childCount()):
            item = group.child(j)
            if tuple(item.data(0, Qt.UserRole)) == q._selected:
                q.list.blockSignals(True)
                q.list.setCurrentItem(item)
                q.list.blockSignals(False)
    q.mount_source()
    return q.table


def apply(page):
    page.apply_section(page.continental_section)
    qa.processEvents()


def discard(page):
    page.discard_section(page.continental_section)
    qa.processEvents()


def pure():
    recipe = data()
    sources = Q.sources(recipe, "fake-tables")
    ok("original leagues use metadata country mappings, including relocated IDs", next(s for s in sources if s.key == "501").country == "England")
    ok("all six confederations expose eligible sources", {s.confederation for s in sources} == {2, 3, 4, 5, 6, 7})
    ok("lower/exhibition/unassigned sources are excluded", not {"Lower", "Exhibition", "Unassigned"} & {s.name for s in sources})
    ok("four original plus six added South American leagues rank together",
       len([s for s in sources if s.confederation == 4 and not s.linked_to]) == 10)
    expected = {2: [0, 10, 1, 11, 2, 12], 4: [3, 17, 16, 9, 19], 3: [5, 8, 15], 5: [6, 7], 6: [13], 7: [14]}
    for conf, ids in expected.items():
        ok("confederation %d offers only implemented logical destinations" % conf, list(dict(Q.destinations(conf, recipe))) == ids)
    ok("UECL off hides only new Conference assignments", list(dict(Q.destinations(2, dict(recipe, uecl=False)))) == [0, 10, 1, 11])
    classic = dict(recipe, conmebol=None)
    classic.pop("conmebol")
    ok("classic mode offers no new Sudamericana or F3 place", list(dict(Q.destinations(4, classic))) == [3, 4])
    native = sources[0]
    custom = dict(recipe, game_europe={"501": [[3, 11]]})
    ok("custom native access replaces shipped rows without double counting", Q.effective(native, custom) == [[3, 11]])
    empty = dict(recipe, game_europe={"501": []})
    ok("empty override accurately preserves current backend native semantics",
       Q.effective(native, empty) == [list(p) for p in native.native] and "retains native" in Q.inherited_text(native, empty))
    own = next(s for s in sources if s.key == "Europe Two")
    ok("backend position validator rejects duplicate positions", bool(Q.row_errors(own, [[1, 0], [1, 1]], recipe)))
    ok("backend position validator rejects positions beyond source size", bool(Q.row_errors(own, [[19, 0]], recipe)))
    ok("cup winner unavailable without a domestic cup", bool(Q.row_errors(own, [[0, 1]], recipe)))
    own_cup = next(s for s in sources if s.key == "Europe One")
    ok("cup winner accepted with an actual national cup", not Q.row_errors(own_cup, [[0, 1]], recipe))
    small = {k: v for k, v in recipe.items() if k != "leagues"} | {"leagues": []}
    small["conmebol_associations"] = {"200": [[1, 16]]}
    assocs = Q.sources(small, "fake-tables")
    assoc = next(s for s in assocs if s.key == "200")
    ok("numeric association aliases stay under their existing recipe key", assoc.country == "Bolivia" and assoc.clubs == 6)
    ok("association ranks validate capacity and disallow cup-winner zero",
       Q.row_errors(assoc, [[7, 16]], small) and Q.row_errors(assoc, [[0, 16]], small))
    linked = Q.sources(dict(recipe, conmebol_associations={"Bolivia": [[1, 16]]}), "fake-tables")
    legacy = next(s for s in linked if s.kind == "association")
    ok("association added before its league stays linked, never a new league-less source", legacy.linked_to == ("qualification", "league", "South 0"))
    ok("linked historic allocation still contributes to global totals", any("Phase 1: 1 / 6" in line for line in Q.overview(linked, dict(recipe, conmebol_associations={"Bolivia": [[1, 16]]}), 4)))
    on, off = Q.ranked_sources(sources, recipe, 4)
    before = copy.deepcopy(recipe)
    changes, notes, complete = Q.generate(recipe, sources, 4, on, off)
    after = Q.preview(recipe, changes)
    counts = Counter(c for s in sources for _p, c in Q.effective(s, after) if c in Q.MODERN_TOTALS)
    ok("modern preset exactly fills all five fields with zero direct F3",
       complete and all(counts[c] == n for c, n in Q.MODERN_TOTALS.items()))
    ok("modern preset never duplicates a source position or exceeds its clubs",
       all(not Q.B.europe_problems(s.clubs, Q.editable_rows(s, after), s.cup) for s in on))
    ok("preset is deterministic and never mutates the original recipe",
       changes == Q.generate(recipe, sources, 4, on, off)[0] and recipe == before and after["players"] is recipe["players"])
    reordered = [on[-1]] + on[1:-1] + [on[0]]
    other = Q.generate(recipe, sources, 4, reordered, off)[0]
    ok("ranking affects prestigious destination distribution", changes != other)
    excluded = on[-1]
    proposal, _notes, valid = Q.generate(recipe, sources, 4, on[:-1], [excluded])
    ok("excluded custom source receives no modern allocation", valid and not Q.effective(excluded, Q.preview(recipe, proposal)))
    tiny = Q.Source("league", "Tiny", "Tiny", "Brazil", 4, 2)
    scarce = dict(recipe, leagues=[dict(name="Tiny", country="Brazil", clubs=2)])
    result, warnings, valid = Q.generate(scarce, [tiny], 4, [tiny], [])
    ok("shortage is explicit and cannot be confirmed as a complete modern preset", not valid and len(warnings) == 5)
    ok("shortage never forces duplicate positions", len(Q.effective(tiny, Q.preview(scarce, result))) == 2)
    result, warnings, valid = Q.generate(classic, sources, 4, on, [])
    ok("generating a preset cannot turn modern CONMEBOL on", not valid and not result and "conmebol" not in classic)
    historical = copy.deepcopy(recipe)
    historical["leagues"][2]["europe"] = [[1, 18], [2, 4]]
    result, warnings, valid = Q.generate(historical, sources, 4, on, [])
    ok("legacy F3 and classic qualifying preserved and diagnosed, never silently migrated",
       not valid and all(p in Q.preview(historical, result)["leagues"][2]["europe"] for p in [[1, 18], [2, 4]]))
    for conf, sizes in ((3, {8: 8, 15: 8}), (5, {6: 16, 7: 16}), (6, {13: 16}), (7, {14: 8})):
        ranked, off = Q.ranked_sources(sources, recipe, conf)
        proposal, warnings, complete = Q.generate(recipe, sources, conf, ranked, off, sizes)
        preview = Q.preview(recipe, proposal)
        totals = Counter(c for s in sources for _p, c in Q.effective(s, preview))
        ok("confederation %d preset respects actual supported allocation sizes" % conf,
           complete and all(totals[c] == n for c, n in sizes.items()))
    ok("unsupported CONCACAF field size refused", not Q.generate(recipe, sources, 6, [], [], {13: 32})[2])
    on, off = Q.ranked_sources(sources, recipe, 2)
    expected_recipe = copy.deepcopy(recipe)
    candidate = lambda s: dict(id="g%s" % s.key if s.kind == "game" else s.key, name=s.name, country=s.country, clubs=s.clubs, cup=s.cup, game=s.kind == "game")
    uefakey.apply(expected_recipe, list(map(candidate, on)), list(map(candidate, off)))
    proposal, warnings, complete = Q.generate(recipe, sources, 2, on, off)
    preview = Q.preview(recipe, proposal)
    ok("UEFA preset reuses exact existing rank/off/seed algorithm", complete and all(preview[k] == expected_recipe[k] for k in ("uefa_rank", "uefa_off", "uefa_seed", "game_europe")))
    ok("UEFA default ranking retains Russia exclusion", any(s.country == "Russia" for s in off))
    ok("UEFA exclusion limitation is explicitly reported", any("retains native access" in note for note in warnings))
    ok("unrelated competitions/players/custom metadata preserved by UEFA preview",
       all(preview[k] == recipe[k] for k in ("players", "edits", "ccup_names", "future_key")))
    key = ("qualification", "league", "Europe One")
    bad = {key: (True, [[0, 0], [0, 1]])}
    ok("Apply validation uses the backend duplicate-position rule", bool(Q.validate_changes(recipe, Q.preview(recipe, bad), bad, sources)))


def workflow():
    app, page, e, q = page_for()
    original = copy.deepcopy(app.project.recipe)
    for conf in (2, 4, 6, 3, 5, 7):
        e.confederation.setCurrentIndex(e.confederation.findData(conf))
        ok("confederation %d has integrated sources and detail editor" % conf,
           q.list.topLevelItemCount() > 0 and q.table is not None)
    e.confederation.setCurrentIndex(e.confederation.findData(2))
    choose(q, "game", "501")
    ok("original source opens inherited rows read-only", not q.own.isChecked() and not q.table.isEnabled() and len(q.table.places()) == 3)
    q.own.setChecked(True)
    q.table.set_places([[1, 0], [3, 11]])
    ok("editing original source changes only the CUPS draft", app.project.recipe == original and e.dirty_keys())
    q.search.setText("Germany")
    choose(q, "league", "Europe Two")
    q.table.set_places([[1, 10]])
    e.confederation.setCurrentIndex(e.confederation.findData(4))
    choose(q, "league", "South 0")
    q.table.set_places([[1, 16]])
    e.confederation.setCurrentIndex(e.confederation.findData(2))
    choose(q, "game", "501")
    ok("source/search/confederation navigation retains every draft", q.table.places() == [[1, 0], [3, 11]] and app.project.recipe == original)
    apply(page)
    p = app.project
    ok("Apply writes original game_europe and existing league fields only",
       p.recipe["game_europe"]["501"] == [[1, 0], [3, 11]]
       and next(L for L in p.recipe["leagues"] if L["name"] == "Europe Two")["europe"] == [[1, 10]]
       and "qualification" not in p.recipe)
    ok("qualification changes form one undo step", p.undo() and p.recipe == original)
    qa.processEvents()
    ok("Redo restores all qualification edits", p.redo() and p.recipe["game_europe"]["501"] == [[1, 0], [3, 11]])
    qa.processEvents()
    e, q = editor(page), editor(page).qualification
    choose(q, "league", "Europe Two")
    q.table.set_places([[1, 0], [1, 1]])
    saved = copy.deepcopy(p.recipe)
    apply(page)
    ok("duplicate-position Apply is atomic and retains the invalid draft", p.recipe == saved and q.table.places() == [[1, 0], [1, 1]])
    discard(page)
    e, q = editor(page), editor(page).qualification
    choose(q, "league", "Europe Two")
    q.table.set_places([[19, 0]])
    saved = copy.deepcopy(p.recipe)
    apply(page)
    ok("out-of-range rows are not clamped away or committed", q.table.places() == [[19, 0]] and p.recipe == saved)
    discard(page)
    e, q = editor(page), editor(page).qualification
    choose(q, "league", "Europe One")
    q.table.set_places([[0, 1]])
    ok("cup-winner selector uses the existing zero/cascade semantics", q.table.table.cellWidget(0, 0).value() == 0 and q.table.cup_winner)
    apply(page)
    p._snap_at = 0
    e, q = editor(page), editor(page).qualification
    choose(q, "league", "Europe One")
    q.table.set_places([[1, 0]])
    league = next(L for L in p.recipe["leagues"] if L["name"] == "Europe One")
    league["europe"] = [[2, 1]]
    p.touch()
    qa.processEvents()
    apply(page)
    ok("Edit League concurrent changes are not overwritten", league["europe"] == [[2, 1]] and "changed elsewhere" in page.continental_section["message"].text())
    discard(page)
    e, q = editor(page), editor(page).qualification
    choose(q, "league", "Europe One")
    ok("Discard reloads the league editor's current fields", q.table.places() == [[2, 1]])
    with patch.object(Q.B, "game_europe_tops", return_value=[(int(s.key), s.name, s.clubs, list(s.native)) for s in NATIVES]):
        dialog = builder.GameEuropeDialog(None, p)
        dialog.ok()
        ok("old original-league dialog reads exactly the same overrides", dialog.result["501"] == p.recipe["game_europe"]["501"])
    choose(q, "league", "Europe One")
    q.table.set_places([[1, 0]])
    before_switch = copy.deepcopy(p.recipe)
    p.adopt(dict(world="_FL26DifferentQualification", leagues=[]), None)
    qa.processEvents()
    ok("world switching cannot leak qualification drafts", "game_europe" not in p.recipe and page.has_drafts())
    p.adopt(before_switch, None)
    qa.processEvents()
    e, q = editor(page), editor(page).qualification
    choose(q, "league", "Europe One")
    ok("returning to a world restores its qualification draft", q.table.places() == [[1, 0]])
    with tempfile.TemporaryDirectory(prefix="qualification-save-") as root:
        p.path = os.path.join(root, "recipe.json")
        apply(page)
        p.autosave()
        with open(p.path, encoding="utf-8") as stream:
            got = json.load(stream)
        ok("qualification uses Project autosave", got["leagues"][0]["europe"] == [[1, 0]])
        p.path = None
    page.close()


def presets():
    app, page, e, q = page_for(conf=4)
    original = copy.deepcopy(app.project.recipe)
    dialog = UI.PresetDialog(q, e.preview(), q.sources, 4)
    before = [s.draft_key for s in dialog.ranking()[0]]
    dialog.list.setCurrentRow(9)
    dialog.list.item(9).setSelected(True)
    dialog.move(-1)
    ok("preset Up/Down reorders the preview without touching project",
       [s.draft_key for s in dialog.ranking()[0]] != before and app.project.recipe == original)
    item = dialog.list.item(dialog.list.count() - 1)
    item.setCheckState(Qt.Unchecked)
    ok("preset checkboxes exclude sources in the live preview", item.data(Qt.UserRole) in dialog.ranking()[1] and app.project.recipe == original)
    ok("ranking supports drag-and-drop with multiple selection", dialog.list.dragDropMode() == QAbstractItemView.InternalMove and dialog.list.selectionMode() == QAbstractItemView.ExtendedSelection)
    dialog.reject()
    ok("Cancel leaves project and CUPS draft unchanged", app.project.recipe == original and not e.dirty_keys())
    dialog = UI.PresetDialog(q, e.preview(), q.sources, 4)
    totals = dialog.preview.tree.topLevelItem(0)
    ok("preview has readable current/proposed rows and allocation totals",
       dialog.preview.tree.headerItem().text(1) == "Current" and dialog.preview.tree.headerItem().text(2) == "Proposed"
       and any("26 / 26" in totals.child(i).text(2) for i in range(totals.childCount()))
       and any("32 / 32" in totals.child(i).text(2) for i in range(totals.childCount())))
    dialog.confirm()
    ok("confirm produces a validated proposal", dialog.result() == QDialog.Accepted and dialog.complete)
    class AcceptedPreset(UI.PresetDialog):
        def exec(self):
            self.confirm()
            return self.result()
    with patch.object(UI, "PresetDialog", AcceptedPreset):
        q.generate_preset()
    ok("preset confirmation enters the shared draft only", app.project.recipe == original and e.dirty_keys())
    apply(page)
    ok("Apply persists a whole modern preset coherently", app.project.recipe.get("game_europe") and not editor(page).dirty_keys())
    ok("one Undo reverses the entire generated preset", app.project.undo() and app.project.recipe == original)
    qa.processEvents()
    ok("Redo restores the generated preset", app.project.redo())
    qa.processEvents()
    e = editor(page)
    q = e.qualification
    source = next(s for s in q.sources if s.kind == "league" and s.confederation == 4)
    choose(q, "league", source.key)
    old = app.project.recipe
    q.table.add()
    discard(page)
    ok("Discard restores applied preset values", app.project.recipe is old and not editor(page).dirty_keys())
    page.close()


def first_season():
    recipe = data()
    recipe["europe_first"] = {"ucl": [101, "Gone/2"], "uel": [], "uecl": [102], "future": ["preserve", 104]}
    app, page, e, q = page_for(recipe)
    original = copy.deepcopy(app.project.recipe)
    q.show_first()
    f = q.first
    ok("first-season is an integrated view with three internal tabs", q.stack.currentWidget() is f and f.tabs.count() == 3)
    ok("invalid saved references are visibly retained", "Gone/2" in f.warning.text() and len(f.selected()[0]) == 2)
    f.search.setText("Europe One")
    ok("club search matches leagues and excludes already-selected ID aliases",
       f.pool.count() > 0 and all("Europe One" in f.pool.item(i).text() for i in range(f.pool.count()))
       and not any(f.pool.item(i).data(Qt.UserRole) == "Europe One/0" for i in range(f.pool.count())))
    f.search.setText("103")
    ok("club search matches actual team IDs", any(f.pool.item(i).data(Qt.UserRole) == 103 for i in range(f.pool.count())))
    f.search.setText("")
    for i in range(f.pool.count()):
        if f.pool.item(i).data(Qt.UserRole) in (103, 104):
            f.pool.item(i).setSelected(True)
    f.add_selected()
    ok("multi-add updates only first-season draft and keeps unresolved references",
       f.selected()[0] == [101, "Gone/2", 103, 104] and app.project.recipe == original)
    f.tabs.setCurrentIndex(1)
    ok("competition tabs show their own manual/automatic counters", "0 / 36" in f.counter.text())
    ok("selected clubs cannot be assigned to another competition",
       not any(f.pool.item(i).data(Qt.UserRole) in (101, 102, 103, 104, "Europe One/0") for i in range(f.pool.count())))
    f.tabs.setCurrentIndex(0)
    f.lists[0].item(2).setSelected(True)
    f.remove_selected()
    ok("remove preserves ordering and only removes the selected reference", f.selected()[0] == [101, "Gone/2", 104])
    q.back_to_sources()
    e.confederation.setCurrentIndex(e.confederation.findData(4))
    e.confederation.setCurrentIndex(e.confederation.findData(2))
    q.show_first()
    ok("returning to first-season editor keeps its draft", f.selected()[0] == [101, "Gone/2", 104])
    e.settings["uecl"].setChecked(False)
    ok("UECL off preserves its clubs and reserves them against reassignment",
       not f.tabs.isTabEnabled(2) and f.selected()[2] == [102]
       and not any(f.pool.item(i).data(Qt.UserRole) == 102 for i in range(f.pool.count())))
    e.settings["uecl"].setChecked(True)
    ok("UECL re-enable restores the same participant data", f.tabs.isTabEnabled(2) and f.selected()[2] == [102])
    apply(page)
    ok("Apply saves valid edits while preserving an old unresolved reference and unknown fields",
       app.project.recipe["europe_first"]["ucl"] == [101, "Gone/2", 104]
       and app.project.recipe["europe_first"]["future"] == ["preserve", 104])
    ok("one Undo restores first-season selections", app.project.undo() and app.project.recipe == original)
    qa.processEvents()
    ok("Redo restores first-season selections", app.project.redo())
    qa.processEvents()
    e, q = editor(page), editor(page).qualification
    q.show_first()
    f = q.first
    e.set_qualification(("qualification", "first", "uel"), (True, list(range(110, 146))))
    f.refresh()
    f.tabs.setCurrentIndex(1)
    ok("real backend first-season maximum is used", "36 / 36" in f.counter.text() and not f.add_button.isEnabled())
    f.search.setText("149")
    for i in range(f.pool.count()):
        f.pool.item(i).setSelected(True)
    f.add_selected()
    ok("capacity overflow is refused without partial insertion", len(f.selected()[1]) == Q.B.FIRST_MAX)
    discard(page)
    e, q = editor(page), editor(page).qualification
    q.show_first()
    f = q.first
    f.tabs.setCurrentIndex(0)
    f.lists[0].item(1).setSelected(True)
    f.remove_selected()
    apply(page)
    ok("unresolved references disappear only after explicit user removal", "Gone/2" not in app.project.recipe["europe_first"]["ucl"])
    page.close()


def associations_and_legacy():
    recipe = data()
    recipe["leagues"] = []
    recipe["conmebol_associations"] = {"200": [[1, 16]]}
    app, page, e, q = page_for(recipe, 4)
    table = choose(q, "association", "200")
    ok("association editor uses ranks with no cup winner", not table.cup_winner and table.position_label == "Association rank")
    table.set_places([[2, 19]])
    apply(page)
    ok("association Apply preserves original numeric key and existing schema", app.project.recipe["conmebol_associations"] == {"200": [[2, 19]]})
    page.close()
    recipe = data()
    recipe["conmebol_associations"] = {"Bolivia": [[1, 16]]}
    app, page, e, q = page_for(recipe, 4)
    ok("playable associations are not listed under league-less sources", all(q.list.topLevelItem(i).text(0) != "Associations without playable leagues" for i in range(q.list.topLevelItemCount())))
    choose(q, "league", "South 0")
    q.review_linked_association()
    ok("legacy association slots remain reviewable in the shared editor", q.current_source().kind == "association" and q.table.places() == [[1, 16]])
    q.own.setChecked(False)
    apply(page)
    ok("legacy association record is removed only by explicit action", not app.project.recipe.get("conmebol_associations"))
    page.close()
    recipe = data()
    recipe.pop("conmebol")
    recipe["leagues"][2]["europe"] = [[3, 9], [4, 4]]
    app, page, e, q = page_for(recipe, 4)
    choose(q, "league", "South 0")
    ok("classic Sudamericana row remains selected but unavailable for new assignments",
       q.table.places() == [[3, 9], [4, 4]] and 9 not in dict(q.table.competitions)
       and not q.table.table.cellWidget(0, 1).model().item(q.table.table.cellWidget(0, 1).currentIndex()).isEnabled())
    q.table.table.cellWidget(1, 0).setValue(5)
    apply(page)
    ok("editing classic places retains inactive historical Sudamericana", app.project.recipe["leagues"][2]["europe"] == [[3, 9], [5, 4]])
    legacy = SimpleNamespace(app=app)
    legacy.open_qualification = MethodType(builder.NewLeagues.open_qualification, legacy)
    before = copy.deepcopy(app.project.recipe)
    builder.NewLeagues.game_europe(legacy)
    ok("legacy qualification menu routes into the same draft editor", page.tabs.currentIndex() == 2 and editor(page).tabs.currentIndex() == 1 and app.project.recipe == before)
    builder.NewLeagues.europe_first(legacy)
    ok("legacy first-season entry opens the integrated view without committing", editor(page).qualification.first is not None and app.project.recipe == before)
    with patch.object(UI.UefaRankingDialog, "exec", return_value=QDialog.Rejected):
        builder.NewLeagues.uefa_rank(legacy)
    ok("legacy UEFA Ranking opens preview without bypassing Apply", app.project.recipe == before)
    page.close()


def deferred_refresh():
    jobs = []
    with patch.object(UI, "run_job", side_effect=lambda fn, done, fail: jobs.append((fn, done, fail))):
        app, page, e, q = page_for()
        ok("qualification metadata is loaded lazily in a worker", q._loading and len(jobs) == 1)
        fn, done, failed = jobs.pop()
        replacement = data()
        replacement["world"] = "_OtherDeferredWorld"
        app.project.recipe = replacement
        done(Q.sources(data(), "fake-tables"))
        failed("stale failure")
        ok("stale source success and failure cannot populate a different world", not q.sources and q._loading)
        page.refresh()
        e = editor(page)
        e.tabs.setCurrentIndex(1)
        q = e.qualification
        fn, done, failed = jobs.pop()
        done(fn(lambda _value: None))
        expected = q.sources
        q.activate(4)
        q.activate(2)
        ok("confederation changes reuse loaded source metadata", not jobs and q.sources is expected)
        q.search.setText("Russian")
        q.activate(4)
        q.search.setText("South")
        q.activate(2)
        ok("source searches are retained independently per confederation", q.search.text() == "Russian")
    with patch.object(F, "run_job", side_effect=lambda fn, done, fail: jobs.append((fn, done, fail))):
        q.show_first()
        f = q.first
        fn, done, failed = jobs.pop()
        app.project.recipe = dict(data(), world="_AnotherDeferredWorld")
        done(labels(data(), "fake-tables"))
        failed("stale clubs failure")
        ok("stale club loader cannot publish labels into another world", not f.labels and f._loading)
    page.close()


def first_worlds():
    recipe = data()
    recipe["europe_first"] = {"ucl": [101]}
    app, page, e, q = page_for(recipe)
    committed = copy.deepcopy(app.project.recipe)
    q.show_first()
    f = q.first
    f.search.setText("103")
    for i in range(f.pool.count()):
        if f.pool.item(i).data(Qt.UserRole) == 103:
            f.pool.item(i).setSelected(True)
    f.add_selected()
    app.project.adopt(dict(world="_FL26FirstOtherWorld", leagues=[], europe_first={"uel": [104]}), None)
    qa.processEvents()
    q = editor(page).qualification
    q.show_first()
    ok("first-season draft cannot leak into another world's selections", q.first.selected() == [[], [104], []])
    app.project.adopt(committed, None)
    qa.processEvents()
    q = editor(page).qualification
    q.show_first()
    ok("returning to a world restores first-season draft and search", q.first.selected()[0] == [101, 103] and q.first.search.text() == "103")
    discard(page)
    q = editor(page).qualification
    q.show_first()
    ok("Discard restores first-season committed references", q.first.selected()[0] == [101])
    page.close()
    app, page, e, q = page_for()
    before = copy.deepcopy(app.project.recipe)
    def change_during_preview(dialog):
        app.project.recipe["leagues"][0]["europe"] = [[8, 1]]
        dialog.proposal = {("qualification", "league", "Europe One"): (True, [[1, 0]])}
        return QDialog.Accepted
    with patch.object(UI.UefaRankingDialog, "exec", change_during_preview):
        q.generate_preset()
    ok("concurrent league edits invalidate preset preview rather than overwrite it", app.project.recipe["leagues"][0]["europe"] == [[8, 1]] and not e.dirty_keys() and "changed" in q.state.text())
    page.close()


def layouts():
    from pathlib import Path
    from test_cups_layout import settle, rect, header_geometry
    from modstudio import app as A
    with tempfile.TemporaryDirectory(prefix="qualification-layout-") as root:
        with patch.object(A, "APPDIR", root), patch.object(A, "SETTINGS", os.path.join(root, "settings.json")), patch.object(A, "guess_folders", return_value=[]):
            Path(A.SETTINGS).write_text(json.dumps({"check_updates": False, "page": "Settings", "lang": os.environ.get("QUALIFICATION_LANG", "en")}), encoding="utf-8")
            window = A.Main()
            window.project.base = "fake-tables"
            window.project.recipe = data()
            window.project.confeds = dict(CONF)
            window.project.path = None
            window.project._forget()
            window.show()
            window.open_page("Cups")
            page = window.page("Cups")
            page.tabs.setCurrentIndex(2)
            e = editor(page)
            before = header_geometry(page)["header_buttons"]
            e.tabs.setCurrentIndex(1)
            q = e.qualification
            for width, height in ((1400, 900), (1366, 768), (1080, 640)):
                window.resize(width, height)
                settle()
                holder = window.holder_of["Cups"]
                geo = header_geometry(page)
                tools_gap = rect(q.toolbar, page).top() - rect(e.tabs.tabBar(), page).bottom() - 1
                ok("qualification %dx%d has eight external pixels above tools" % (width, height), tools_gap == 8)
                print("# qualification geometry %dx%d gap=%d outer=%d" % (width, height, geo["tabs_to_confederation"], holder.verticalScrollBar().maximum()))
                ok("qualification %dx%d retains nine-pixel gap and action dimensions" % (width, height), geo["tabs_to_confederation"] == 9 and [b[2:] for b in geo["header_buttons"].values()] == [b[2:] for b in before.values()])
                ok("qualification %dx%d keeps fixed controls and only detail scrolling" % (width, height), holder.verticalScrollBar().maximum() == 0 and q.scroll.height() >= 60 and rect(q.toolbar, page).right() < page.width())
                q.show_first()
                settle()
                print("# first geometry outer=%d pool=%d picked=%d minimum=%s stack=%s" % (holder.verticalScrollBar().maximum(), q.first.pool.height(), q.first.lists[0].height(), q.first.minimumSizeHint(), q.stack.size()))
                ok("first-season %dx%d fits integrated view without outer scrolling" % (width, height), holder.verticalScrollBar().maximum() == 0 and q.first.pool.height() > 30 and q.first.lists[0].height() > 30)
                q.back_to_sources()
                e.tabs.setCurrentIndex(0)
                settle()
                ok("competitions stay compact after visiting both qualification views", holder.verticalScrollBar().maximum() == 0 and e.list.verticalScrollBar().maximum() == 0)
                e.tabs.setCurrentIndex(1)
            if os.environ.get("QUALIFICATION_CAPTURE"):
                window.resize(1366, 768)
                settle()
                window.grab().save(os.environ["QUALIFICATION_CAPTURE"] + ".png")
                q.show_first()
                settle()
                window.grab().save(os.environ["QUALIFICATION_CAPTURE"] + "-first.png")
            window.close()
            settle()


def real_backend(base):
    recipe = {"world": "_FL26QualificationReadOnlyPlan", "leagues": [], "conmebol": "modern"}
    sources = Q.sources(recipe, base)
    ranked, off = Q.ranked_sources(sources, recipe, 4)
    proposal, notes, complete = Q.generate(recipe, sources, 4, ranked, off)
    ok("real metadata offers original South American leagues plus actual eligible associations", len([s for s in ranked if s.kind == "game"]) == 4)
    ok("real metadata modern preset has enough actual eligible clubs", complete)
    preview = Q.preview(recipe, proposal)
    plan = Q.B.plan(preview, base)
    ok("real backend validates generated modern package without building a world", plan["modern_libertadores_access"] == "custom" and plan["suda_first"] and plan["libq"])
    old = {"world": "_FL26ClassicQualificationPlan", "leagues": [], "game_europe": {"29": [[7, 9]]}}
    plan = Q.B.plan(old, base)
    ok("real backend keeps classic Sudamericana disabled with saved rows intact", not any(c["number"] in (9, -1) for c in plan["ccups"]) and old["game_europe"]["29"] == [[7, 9]])
    labels, aliases = Q.club_choices({"leagues": []}, base)
    ok("real first-season pool contains actual playable teams", labels and all(isinstance(k, int) for k in labels))
    uefa = {"world": "_FL26UefaReadOnlyPlan", "leagues": []}
    sources = Q.sources(uefa, base)
    ranked, off = Q.ranked_sources(sources, uefa, 2)
    proposal, notes, complete = Q.generate(uefa, sources, 2, ranked, off)
    plan = Q.B.plan(Q.preview(uefa, proposal), base)
    ok("real UEFA ranking proposal validates through the current plan and retains seeding", complete and bool(plan["uefa_seed"]) and "game_europe" not in uefa)


if __name__ == "__main__":
    with patch.object(Q, "metadata", return_value=(NATIVES, ASSOCIATIONS, CONF)), \
            patch.object(C.B, "game_competitions", side_effect=lambda base: NATIVE if base else []), \
            patch.object(C.B, "game_tops", return_value=[(1, "Original cup league", False)]), \
            patch.object(Q, "club_choices", side_effect=labels), \
            patch.object(UI.A, "playable_native_rids", return_value={str(s.key) for s in NATIVES}), \
            patch.object(UI, "run_job", side_effect=inline), patch.object(F, "run_job", side_effect=inline):
        pure()
        workflow()
        presets()
        first_season()
        associations_and_legacy()
        deferred_refresh()
        first_worlds()
        layouts()
    if "--tables" in sys.argv:
        real_backend(sys.argv[sys.argv.index("--tables") + 1])
    print("test_qualification: ok (%d)" % N)
