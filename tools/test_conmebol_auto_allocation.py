"""Fixed 10-association UI allocation, real validators, no full Build.

Fixtures model four game divisions and six named new divisions. Optional --tables
checks the actual game mappings and the generated B.plan, not a world build.
"""
import copy
import sys
from collections import Counter
from dataclasses import replace
from unittest.mock import patch
import test_qualification as T
from modstudio import conmebol_allocation as A
from test_cups_layout import rect, settle
from PySide6.QtWidgets import QPushButton

Q, UI, qa = T.Q, T.UI, T.qa
N = 0


def ok(label, condition):
    global N
    assert condition, label
    N += 1
    print("ok %d - %s" % (N, label))


def world():
    leagues = [("Division Profesional", "Bolivia", 16), ("LigaPro", "Ecuador", 16),
               ("Primera Division APF", "Paraguay", 12), ("Liga 1", "Peru", 18),
               ("Primera Division AUF", "Uruguay", 16), ("Liga FUTVE", "Venezuela", 16)]
    return {"world": "_FL26FixedConmebol", "conmebol": "modern",
            "leagues": [dict(name=n, country=c, clubs=k, cup=True, legs=2) for n, c, k in leagues]
                       + [dict(name="European custom", country="Germany", clubs=18, europe=[[1, 0]])],
            "game_europe": {"501": [[2, 11]]}, "uefa_rank": ["g501"], "uefa_off": ["g502"],
            "uefa_seed": [["g501", 2, 11]], "europe_first": {"ucl": [101]},
            "players": {"keep": [1, 2, 3]}, "future": {"keep": True}, "caf_super_cup": True}


def attempt(recipe):
    old = copy.deepcopy(recipe)
    try:
        changes = A.generate(recipe, "fake-tables")
        message = ""
    except A.AllocationError as exc:
        changes, message = None, str(exc)
    assert recipe == old, "pure generator must never mutate input, even on failure"
    return changes, message


def pure():
    recipe = world()
    original = copy.deepcopy(recipe)
    changes, message = attempt(recipe)
    ok("four original plus six added divisions produce ten existing-slot patches", not message and len(changes) == 10)
    result = Q.preview(recipe, changes)
    sources = Q.sources(result, "fake-tables")
    totals = Counter()
    for source in sources:
        if source.confederation != 4 or source.kind == "association":
            continue
        rows = Q.effective(source, result)
        actual = Counter(c for p, c in rows)
        expected = dict(zip(A.DESTINATIONS, A.QUOTAS[source.country]))
        ok(source.country + " keeps its fixed country quota", all(actual[c] == n for c, n in expected.items()) and len(rows) == sum(expected.values()))
        ok(source.country + " has one designated cup winner and no repeated positions", len({p for p, c in rows}) == len(rows) and [c for p, c in rows if p == 0] == [A.CUP_TARGETS[source.country]] and not Q.B.europe_problems(source.clubs, rows, source.cup))
        totals.update(actual)
    ok("exact 26/13/6/12/32 totals and 89 entries with no direct F3", dict(totals) == {3: 26, 17: 13, 16: 6, 9: 12, 19: 32} and sum(totals.values()) == 89 and totals[18] == 0)
    ok("repeated generation is idempotent", A.generate(result, "fake-tables") == {})
    reordered = copy.deepcopy(recipe)
    reordered["leagues"].reverse()
    ok("league order cannot change country quotas or source positions", A.generate(reordered, "fake-tables") == changes)
    renamed = copy.deepcopy(recipe)
    for i, league in enumerate(renamed["leagues"]):
        league["name"] = "Renamed %d" % i
    renamed_result = Q.preview(renamed, A.generate(renamed, "fake-tables"))
    ok("display names do not determine allocations", {s.country: Q.effective(s, renamed_result) for s in Q.sources(renamed_result, "fake-tables") if s.confederation == 4} == {s.country: Q.effective(s, result) for s in sources if s.confederation == 4})
    ok("unrelated recipe fields and UEFA access are preserved", all(result[k] == v for k, v in original.items() if k not in ("leagues", "game_europe")) and result["game_europe"]["501"] == original["game_europe"]["501"] and result["leagues"][-1] == original["leagues"][-1])
    # Prove game regulation identifiers are resolved by metadata, not fixed constants.
    moved = tuple(replace(s, key="2001", name="Moved original") if s.country == "Brazil" else s for s in T.NATIVES)
    with patch.object(Q, "metadata", return_value=(moved, T.ASSOCIATIONS, T.CONF)), patch.object(A, "playable_native_rids", return_value={str(s.key) for s in moved}):
        moved_changes = A.generate(recipe, "fake-tables")
        ok("original country mapping is independent of regulation id or league name", ("qualification", "game", "2001") in moved_changes and ("qualification", "game", "29") not in moved_changes)
    no_cups = copy.deepcopy(recipe)
    for league in no_cups["leagues"]:
        league["cup"] = False
    native_no_cups = tuple(replace(s, cup=False) if s.confederation == 4 else s for s in T.NATIVES)
    with patch.object(Q, "metadata", return_value=(native_no_cups, T.ASSOCIATIONS, T.CONF)):
        no_result = Q.preview(no_cups, A.generate(no_cups, "fake-tables"))
        sam = [s for s in Q.sources(no_result, "fake-tables") if s.confederation == 4 and s.kind != "association"]
        ok("no-cup sources transfer the same quota to consecutive league places", all([p for p, c in Q.effective(s, no_result)] == list(range(1, sum(A.QUOTAS[s.country]) + 1)) for s in sam))
        ok("absence of cups never reduces any fixed quota", Counter(c for s in sam for p, c in Q.effective(s, no_result)) == totals)
    # Backend stage rows carry the source fallback when the cup winner has a league place.
    stage = Q.B.own_stage_places({"leagues": [{"rid": 900, "clubs": 16, "europe": [[1, 3], [0, 17]]}]})
    ok("cup overlap retains backend same-source cascading representation", any(r[1] == 0 and r[-1] == 900 for r in stage))


def failures():
    for removed in (("Peru",), ("Peru", "Ecuador", "Bolivia")):
        recipe = world()
        recipe["leagues"] = [L for L in recipe["leagues"] if L["country"] not in removed]
        recipe["conmebol_associations"] = {c: [[1, 16]] for c in removed}
        changes, message = attempt(recipe)
        ok("missing " + ", ".join(removed) + " aborts without synthetic fallback", changes is None and all(c in message for c in removed) and "Available: %d/10" % (10 - len(removed)) in message and "No qualification places were changed" in message)
        ok("manual league-less associations remain available independently", all(any(s.country == c and s.kind == "association" for s in Q.sources(recipe, "fake-tables")) for c in removed))
    for flag in ("above", "exhibition", "others", "clubs"):
        recipe = world()
        peru = next(L for L in recipe["leagues"] if L["country"] == "Peru")
        peru[flag] = {"above": "Parent", "exhibition": True, "others": "latam", "clubs": 0}[flag]
        changes, message = attempt(recipe)
        ok("ineligible " + flag + " source cannot replace a playable first division", changes is None and "Missing: Peru" in message)
    recipe = world()
    recipe["leagues"].append(dict(name="Second Peruvian top", country="Peru", clubs=16))
    changes, message = attempt(recipe)
    ok("duplicate own top divisions are reported, not silently selected", changes is None and "Ambiguous top divisions: Peru" in message)
    recipe = world()
    recipe["leagues"].append(dict(name="New Brazilian top", country="Brazil", clubs=16))
    changes, message = attempt(recipe)
    ok("native-plus-added ambiguity is detected", changes is None and "Ambiguous top divisions: Brazil" in message)
    recipe = dict(world(), conmebol="classic")
    changes, message = attempt(recipe)
    ok("classic mode is not enabled or modified by auto allocation", changes is None and "Enable Modern CONMEBOL" in message and recipe["conmebol"] == "classic")
    recipe = world()
    recipe["conmebol_associations"] = {"Peru": [[1, 16]]}
    changes, message = attempt(recipe)
    ok("existing association allocations are preserved for explicit manual review", changes is None and "manual review" in message)
    recipe = world()
    recipe["game_europe"]["29"] = [[1, 0]]
    changes, message = attempt(recipe)
    ok("overlapping unrelated qualification entries abort atomically", changes is None and "safely combined" in message)
    recipe["game_europe"]["29"] = [[20, 0]]
    changes, message = attempt(recipe)
    ok("nonoverlapping unrelated entries remain unchanged", not message and [20, 0] in changes[("qualification", "game", "29")][1])
    recipe["game_europe"]["29"] = [[20, 18]]
    changes, message = attempt(recipe)
    ok("historical F3 places are not silently rewritten or erased", changes is None and "preserved" in message and "destination 18" not in message)
    recipe["game_europe"]["29"] = [[0, 6]]
    changes, message = attempt(recipe)
    ok("an unrelated cup-winner entry cannot create a second position zero", changes is None and "safely combined" in message)
    changed_confeds = dict(T.CONF, Peru=2)
    with patch.object(Q, "metadata", return_value=(T.NATIVES, T.ASSOCIATIONS, changed_confeds)):
        changes, message = attempt(world())
        ok("country confederation is read from database metadata, not inferred from a league name", changes is None and "Missing: Peru" in message)
    small = tuple(replace(s, clubs=12) if s.country == "Brazil" else s for s in T.NATIVES)
    with patch.object(Q, "metadata", return_value=(small, T.ASSOCIATIONS, T.CONF)):
        changes, message = attempt(world())
        ok("a cup winner cannot be used to exceed the number of distinct available clubs", changes is None and "13 eligible clubs" in message)
    with patch.object(A, "playable_native_rids", return_value={str(s.key) for s in T.NATIVES if s.country != "Chile"}):
        changes, message = attempt(world())
        ok("nonplayable original sources do not satisfy the ten-country gate", changes is None and "Missing: Chile" in message)


def workflow():
    app, page, e, q = T.page_for(world())
    def toolbar():
        return [q.toolbar.layout().itemAt(i).widget().text() for i in range(q.toolbar.layout().count())
                if isinstance(q.toolbar.layout().itemAt(i).widget(), QPushButton) and not q.toolbar.layout().itemAt(i).widget().isHidden()]
    ok("UEFA has exactly ranking, first-season clubs and plan in that order", toolbar() == ["UEFA ranking...", "First-season clubs...", "Check current competition plan"] and q.generate_button.isHidden())
    for conf in (3, 5, 6, 7):
        e.confederation.setCurrentIndex(e.confederation.findData(conf))
        ok("other confederation %d retains the generic preset toolbar" % conf, toolbar() == ["Generate preset...", "Check current competition plan"])
    e.confederation.setCurrentIndex(e.confederation.findData(4))
    ok("CONMEBOL has only auto allocation immediately before plan", toolbar() == ["Auto set continental places", "Check current competition plan"])
    before = copy.deepcopy(app.project.recipe)
    pending = ("qualification", "league", "European custom")
    e.set_qualification(pending, (True, [[2, 1]]))
    with patch.object(UI, "PresetDialog", side_effect=AssertionError("CONMEBOL must not open ranking")), \
            patch.object(Q, "generate", side_effect=AssertionError("no ranking allocation")), \
            patch.object(Q, "ranked_sources", side_effect=AssertionError("no source ranking")), patch.object(UI, "error") as errors:
        q.generate_button.click()
        ok("auto action uses no ranking dialog and changes the shared draft only", not errors.called and app.project.recipe == before and e.dirty_keys())
        ok("auto allocation preserves another confederation's pending draft", e._values[pending] == (True, [[2, 1]]))
        values = copy.deepcopy(e._values)
        q.generate_button.click()
        ok("repeated clicks do not add duplicates or new draft changes", e._values == values)
    settle()
    gap = rect(q.toolbar, page).top() - rect(e.tabs.tabBar(), page).bottom() - 1
    ok("approved eight-pixel toolbar spacing stays unchanged", gap == 8)
    T.discard(page)
    e, q = T.editor(page), T.editor(page).qualification
    ok("Discard restores the original world without saving", app.project.recipe == before and not e.dirty_keys())
    q.generate_button.click()
    T.apply(page)
    applied = copy.deepcopy(app.project.recipe)
    ok("Apply persists only existing qualification fields", applied != before and len(applied["game_europe"]) == 5 and "conmebol_auto" not in applied)
    ok("one Undo reverses the full automatic assignment", app.project.undo() and app.project.recipe == before)
    settle()
    ok("Redo restores the entire automatic assignment", app.project.redo() and app.project.recipe == applied)
    settle()
    page.close()


def deferred():
    app, page, e, q = T.page_for(world(), 4)
    draft = copy.deepcopy(e._values)
    jobs = []
    with patch.object(UI, "run_job", side_effect=lambda fn, done, failed: jobs.append((fn, done, failed))), patch.object(UI, "error") as errors:
        q.generate_button.click()
        ok("automatic allocation runs in a worker with duplicate clicks disabled", q._auto_running and not q.generate_button.isEnabled() and len(jobs) == 1)
        app.project.recipe["leagues"][0]["clubs"] = 18
        fn, done, _failed = jobs.pop()
        done(fn(lambda _value: None))
        ok("concurrent source edits cancel the calculation without overwriting the draft", e._values == draft and errors.called and "world changed" in errors.call_args.args[2])
    page.close()
    app, page, e, q = T.page_for(world(), 4)
    original = copy.deepcopy(app.project.recipe)
    jobs = []
    with patch.object(UI, "run_job", side_effect=lambda fn, done, failed: jobs.append((fn, done, failed))):
        q.generate_button.click()
        fn, done, _failed = jobs.pop()
        app.project.adopt({"world": "_FL26OtherAutoWorld", "leagues": []}, None)
        settle()
        other_before = copy.deepcopy(app.project.recipe)
        done(fn(lambda _value: None))
        ok("a late result cannot write to another world", app.project.recipe == other_before)
        app.project.adopt(original, None)
        settle()
        ok("returning to the original world has no leaked automatic result", app.project.recipe == original and not T.editor(page).dirty_keys())
    page.close()
    missing = world()
    missing["leagues"] = [L for L in missing["leagues"] if L["country"] != "Peru"]
    app, page, e, q = T.page_for(missing, 4)
    e.set_qualification(("qualification", "league", "LigaPro"), (True, [[1, 3]]))
    draft, original = copy.deepcopy(e._values), copy.deepcopy(app.project.recipe)
    with patch.object(UI, "error") as errors:
        q.generate_button.click()
    ok("missing-country failure preserves the entire previous draft and committed recipe", e._values == draft and app.project.recipe == original and "Missing: Peru" in errors.call_args.args[2])
    e.settings["conmebol"].setChecked(False)
    draft = copy.deepcopy(e._values)
    with patch.object(UI, "error") as errors:
        q.generate_button.click()
    ok("disabled modern mode explains the requirement without enabling it", e._values == draft and "Enable Modern CONMEBOL" in errors.call_args.args[2])
    page.close()


def real_plan(base):
    recipe = world()
    # The real database's native rows supply their real identifiers and cups.
    recipe.pop("game_europe")
    recipe.pop("uefa_rank")
    recipe.pop("uefa_off")
    recipe.pop("uefa_seed")
    recipe.pop("europe_first")
    recipe.pop("players")
    recipe.pop("caf_super_cup")
    recipe["leagues"] = recipe["leagues"][:6]
    changes = A.generate(recipe, base)
    result = Q.preview(recipe, changes)
    plan = Q.B.plan(result, base)
    ok("real four-original-plus-six-new allocation validates without a world Build", len(changes) == 10 and plan["modern_libertadores_access"] == "custom")
    ok("real plan retains stage cup-winner fallback sources", any(r[1] == 0 and r[-1] for r in plan["conmebol_stages"]))


if __name__ == "__main__":
    with patch.object(Q, "metadata", return_value=(T.NATIVES, T.ASSOCIATIONS, T.CONF)), \
            patch.object(A, "playable_native_rids", return_value={str(s.key) for s in T.NATIVES}), \
            patch.object(T.C.B, "game_competitions", side_effect=lambda base: T.NATIVE if base else []), \
            patch.object(T.C.B, "game_tops", return_value=[(1, "Original cup league", False)]), \
            patch.object(UI, "run_job", side_effect=T.inline):
        pure()
        failures()
        workflow()
        deferred()
    if "--tables" in sys.argv:
        real_plan(sys.argv[sys.argv.index("--tables") + 1])
    print("test_conmebol_auto_allocation: ok (%d)" % N)
