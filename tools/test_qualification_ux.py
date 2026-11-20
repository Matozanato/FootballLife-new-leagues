"""UX and deleted-source recovery. Uses controlled fixtures, never builds a world.

Proposal hashes were captured before the UX changes to protect all six existing
allocation algorithms. No country-specific native mapping is inspected here.
"""
import copy
import hashlib
import json
import os
import sys
from unittest.mock import patch
import test_qualification as T
from test_cups_layout import rect, settle
from modstudio.pages import qualification_presentation as P
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox

Q, UI, qa = T.Q, T.UI, T.qa
N = 0


def ok(label, condition):
    global N
    assert condition, label
    N += 1
    print("ok %d - %s" % (N, label))


def text_items(tree):
    def walk(item):
        yield item
        for i in range(item.childCount()):
            yield from walk(item.child(i))
    return [it for i in range(tree.topLevelItemCount()) for it in walk(tree.topLevelItem(i))]


def removed_sources():
    app, page, e, q = T.page_for(conf=5)
    T.choose(q, "league", "Africa B")
    q.table.set_places([[1, 7]])
    T.choose(q, "league", "Africa A")
    q.table.set_places([[1, 6]])
    orphan = ("qualification", "league", "Africa A")
    valid = ("qualification", "league", "Africa B")
    app.project.recipe["leagues"] = [L for L in app.project.recipe["leagues"] if L["name"] != "Africa A"]
    errors = []
    with patch.object(sys, "excepthook", side_effect=lambda *exc: errors.append(exc)):
        app.project.touch()
        settle()
        page.shown()
        ok("removed league cannot be resurrected or crash a draft preview", not any(L["name"] == "Africa A" for L in e.preview()["leagues"]))
        ok("deleted source disappears and selection safely falls back", all(s.key != "Africa A" for s in q.sources) and q.current_source().key != "Africa A")
        ok("both valid and removed-source drafts remain recoverable", {orphan, valid} <= e.dirty_keys() and q.discard_removed.isVisible())
        for conf in (4, 2, 6, 3, 7, 5, 4):
            e.confederation.setCurrentIndex(e.confederation.findData(conf))
            settle()
            keys = [e.list.item(i).data(Qt.UserRole) for i in range(e.list.count())]
            ok("confederation %d synchronizes competitions and details with a removed-source draft" % conf,
               keys and all(e.competitions[k].confederation == conf for k in keys)
               and e._selected in keys and e.original_name.text() == (e.competitions[e._selected].title or e.competitions[e._selected].name))
            listed = [it.data(0, Qt.UserRole) for it in text_items(q.list) if it.data(0, Qt.UserRole)]
            ok("confederation %d synchronizes qualification and options" % conf,
               q.conf == conf and all(next(s for s in q.sources if s.draft_key == tuple(key)).confederation == conf for key in listed)
               and not e.settings["conmebol"].isHidden() == (conf == 4)
               and not e.settings["caf_super_cup"].isHidden() == (conf == 5))
        ok("switching no longer emits the logged StopIteration through Qt", not errors)
    before = copy.deepcopy(app.project.recipe)
    T.apply(page)
    ok("Apply cannot silently lose a draft for a deleted source", app.project.recipe == before and orphan in e.dirty_keys())
    ok("Undo deletion recovers the source and its pending edit", app.project.undo())
    settle()
    T.choose(q, "league", "Africa A")
    ok("restored source recovers its original draft rows", q.table.places() == [[1, 6]])
    ok("Redo deletion is safe", app.project.redo())
    settle()
    page.say("This section could not be shown:", "err")
    page.shown()
    ok("successful refresh recovers from the error banner without hiding a new failure", page.banner.isHidden() and orphan in e.dirty_keys())
    q.discard_removed.click()
    ok("explicit removed-draft discard keeps valid pending changes", orphan not in e.dirty_keys() and valid in e.dirty_keys())
    app.project._snap_at = 0
    T.apply(page)
    ok("remaining valid changes apply without recreating the deleted league", next(L for L in app.project.recipe["leagues"] if L["name"] == "Africa B")["europe"] == [[1, 7]] and not any(L["name"] == "Africa A" for L in app.project.recipe["leagues"]))
    page.close()

    app, page, e, q = T.page_for(conf=2)
    T.choose(q, "league", "Europe One")
    q.table.set_places([[1, 0]])
    T.choose(q, "league", "Europe Two")
    jobs = []
    with patch.object(UI, "run_job", side_effect=lambda fn, done, fail: jobs.append((fn, done, fail))):
        app.project.recipe["leagues"] = [L for L in app.project.recipe["leagues"] if L["name"] != "Europe Two"]
        app.project.touch()
        settle()
        ok("deleted unedited source disappears before its background refresh completes", jobs and q._loading and not any(s.key == "Europe Two" for s in q.sources))
        fn, done, _failed = jobs[-1]
        done(fn(lambda _value: None))
        ok("background refresh preserves another league's pending edit", e.preview()["leagues"][0]["europe"] == [[1, 0]] and not e.removed_draft_keys())
    page.close()


def readable_preview():
    recipe = T.data()
    recipe["leagues"][0]["europe"] = [[1, 0], [2, 0], [0, 1]]
    sources = Q.sources(recipe, "fake-tables")
    source = next(s for s in sources if s.key == "Europe One")
    other = next(s for s in sources if s.key == "Europe Two")
    changes = {source.draft_key: (True, [[1, 0], [2, 1], [3, 10], [0, 1]])}
    after = Q.preview(recipe, changes)
    preview = P.PresetPreview()
    preview.display([source, other], 2, recipe, after, 2, changes, [], True)
    items = text_items(preview.tree)
    texts = "\n".join(it.text(c) for it in items for c in range(3))
    ok("primary preview contains no raw allocation arrays or internal destination labels", "[[" not in texts and "Competition 0" not in texts)
    ok("preview labels cup winner and ordinal positions", all(x in texts for x in ("Cup winner", "1st place", "2nd place", "3rd place")))
    ok("preview uses supported competition and qualifying-round names", "Champions League" in texts and "Europa League" in texts and "Champions League qualifying" in texts)
    changed = [it for it in items if it.data(0, Qt.UserRole) is True]
    ok("only real differences are marked and additions show No place", len(changed) == 2 and changed[1].text(1) == "No place")
    ok("unchanged sources are hidden by default", not any(it.text(0).startswith("Europe Two") for it in items))
    preview.show_unchanged.setChecked(True)
    ok("unchanged sources can be shown without recalculating assignments", any(it.text(0).startswith("Europe Two") for it in text_items(preview.tree)) and recipe["leagues"][0]["europe"] == [[1, 0], [2, 0], [0, 1]])
    ok("technical details are collapsed and retain raw diagnostics", preview.details.inner.isHidden() and "[[" in preview.technical.toPlainText())
    association = Q.Source("association", "Peru", "Peru", "Peru", 4, 3)
    r = dict(recipe, conmebol_associations={"Peru": [[1, 17]]})
    change = {association.draft_key: (True, [[2, 19]])}
    preview.display([association], 1, r, Q.preview(r, change), 4, change, [], True)
    texts = "\n".join(it.text(c) for it in text_items(preview.tree) for c in range(3))
    ok("association preview uses ranks and phase names, never league positions", "Association rank 1" in texts and "Association rank 2" in texts and "Phase 2" in texts and "First stage" in texts)
    ok("removed assignments show No place", any(it.text(0) == "Association rank 1" and it.text(2) == "No place" for it in text_items(preview.tree)))
    preview.close()
    app, page, e, q = T.page_for(conf=4)
    dialog = UI.PresetDialog(q, e.preview(), q.sources, 4)
    proposal = copy.deepcopy(dialog.proposal)
    if os.environ.get("QUALIFICATION_UX_CAPTURE"):
        dialog.resize(1000, 620)
        dialog.show()
        settle()
        dialog.grab().save(os.environ["QUALIFICATION_UX_CAPTURE"] + "-preset.png")
    dialog.list.setCurrentRow(6)
    dialog.list.item(6).setSelected(True)
    dialog.move(-1)
    ok("ranking changes refresh the structured preview and proposal together", dialog.proposal != proposal and dialog.preview._data[-1] == dialog.proposal)
    dialog.confirm()
    ok("valid proposals still confirm using the existing validation", dialog.result() == QDialog.Accepted)
    responsive = UI.PresetDialog(q, e.preview(), q.sources, 4)
    for width, height in ((1000, 620), (640, 420)):
        responsive.resize(width, height)
        responsive.show()
        settle()
        tree = responsive.preview.tree
        tree.scrollToBottom()
        settle()
        last = tree.topLevelItem(tree.topLevelItemCount() - 1)
        ok("preset %dx%d keeps scrollable assignments and confirmation accessible" % (width, height),
           tree.viewport().height() >= 60 and rect(responsive.buttons, responsive).bottom() < responsive.height()
           and tree.visualItemRect(last.child(last.childCount() - 1)).intersects(tree.viewport().rect()))
    responsive.reject()
    ok("cancelling the structured preview leaves project and draft unchanged", not e.dirty_keys() and app.project.recipe == T.data())
    bad = UI.PresetDialog(q, dict(T.data(), conmebol="classic"), q.sources, 4)
    bad.confirm()
    ok("invalid proposal cannot be confirmed", bad.result() != QDialog.Accepted and not bad.buttons.button(QDialogButtonBox.Ok).isEnabled())
    page.close()


def counters_and_states():
    recipe = T.data()
    sources = Q.sources(recipe, "fake-tables")
    counts, _notes = Q.allocation_counts(sources, recipe, 2)
    comps = [c for c, n in counts.items() for _i in range(n)] + [e[2] for e in T.Q.W.HOLDERS]
    expected = T.Q.W.europe_count(comps, True)
    rows = {r.target: r for r in P.allocation_rows(sources, recipe, 2)}
    ok("UEFA overview uses exact existing dynamic direct capacities", all(rows[c].places == "%d / %d" % pair for c, pair in expected.items()))
    ok("UEFA filler is informational rather than an incomplete error", all(not rows[c].problem and (n >= cap or rows[c].status == "%d automatically filled" % (cap - n)) for c, (n, cap) in expected.items()))
    on, off = Q.ranked_sources(sources, recipe, 4)
    changes, notes, complete = Q.generate(recipe, sources, 4, on, off)
    rows = P.allocation_rows(sources, Q.preview(recipe, changes), 4)
    ok("modern overview shows exactly five manual destinations with backend totals", len(rows) == 5 and {r.target for r in rows} == {3, 17, 16, 9, 19} and all(r.places == "%d / %d" % (Q.MODERN_TOTALS[r.target], Q.MODERN_TOTALS[r.target]) and not r.problem for r in rows))
    ok("modern shortfalls remain explicit requirements", all(r.problem for r in P.allocation_rows(sources, recipe, 4)))
    app, page, e, q = T.page_for()
    T.choose(q, "game", "501")
    ok("native state is plainly labelled and remains read-only", "Use the game's default" in q.description.text() and not q.table.isEnabled() and q.own.text() == "Set custom qualification places")
    q.own.setChecked(True)
    ok("custom state enables the same existing table", q.table.isEnabled() and "Set custom" in q.description.text())
    T.choose(q, "league", "Europe Two")
    ok("own leagues have no redundant native/custom choice and a useful empty state", q.own.isHidden() and q.table.isEnabled() and q.empty_state.isVisible())
    ok("long explanations are available but collapsed", q.explanation.inner.isHidden() and q.explanation_text.text())
    page.resize(1080, 640)
    page.show()
    settle()
    if os.environ.get("QUALIFICATION_UX_CAPTURE"):
        page.grab().save(os.environ["QUALIFICATION_UX_CAPTURE"] + "-editor.png")
        q.scroll.verticalScrollBar().setValue(q.scroll.verticalScrollBar().maximum())
        settle()
        page.grab().save(os.environ["QUALIFICATION_UX_CAPTURE"] + "-overview.png")
    gap = rect(q.toolbar, page).top() - rect(e.tabs.tabBar(), page).bottom() - 1
    print("# Qualification subtab-to-tools external gap: %d logical px" % gap)
    ok("real external subtab-to-tools spacing is exactly eight logical pixels", gap == 8)
    page.close()


def stable_proposals():
    expected = {2: "a5ead6018830d312d75bad9a9b73d97c4ed128587092fe092aa58fd6a2b06bec", 3: "1e6659a03d19d49f639fbcb64da7da76d02d253dd73bbd6dbb91b9e5bcb4b9c4", 4: "87bb8f669cd7420f44a2a4a6c62c47a4102cb8fe87187c43ddf8674aeb75356b", 5: "eeae33db34e56e1e9e0053b61e5ba2e8d461e945818459778f52907a71dd029d", 6: "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945", 7: "c1ec0290d18042a5c6eb80591860c11d2418b075e64865539dd449a28ad60219"}
    for conf, golden in expected.items():
        recipe = T.data()
        sources = Q.sources(recipe, "fake-tables")
        on, off = Q.ranked_sources(sources, recipe, conf)
        sizes = {c: Q.B.CCUP_SIZES[0] for c, _name in Q.destinations(conf, recipe) if c != 5}
        changes, notes, complete = Q.generate(recipe, sources, conf, on, off, sizes)
        digest = hashlib.sha256(json.dumps(sorted([(list(k), v) for k, v in changes.items()], key=repr), sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        ok("confederation %d proposal is byte-for-byte equivalent to the pre-UX fixture" % conf, digest == golden)


if __name__ == "__main__":
    with patch.object(Q, "metadata", return_value=(T.NATIVES, T.ASSOCIATIONS, T.CONF)), \
            patch.object(T.C.B, "game_competitions", side_effect=lambda base: T.NATIVE if base else []), \
            patch.object(T.C.B, "game_tops", return_value=[(1, "Original cup league", False)]), \
            patch.object(UI, "run_job", side_effect=T.inline):
        removed_sources()
        readable_preview()
        counters_and_states()
        stable_proposals()
    print("test_qualification_ux: ok (%d)" % N)
