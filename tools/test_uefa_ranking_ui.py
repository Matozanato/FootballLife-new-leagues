"""Dedicated UEFA presentation and shared change legend; controlled metadata only.

Reuses the actual uefakey algorithm and existing CUPS persistence. No Build or
country-specific native mapping investigation is performed.
"""
import copy
import os
from unittest.mock import patch
import test_qualification as T
import test_conmebol_auto_allocation as Auto
from test_qualification_ux import text_items
from test_cups_layout import rect, settle
from modstudio.pages import qualification_presentation as P
from modstudio import i18n
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QPushButton, QAbstractItemView

Q, UI, qa = T.Q, T.UI, T.qa
LABEL = "Enable Libertadores new format, Sudamericana and Recopa Sudamericana"
N = 0


def ok(label, condition):
    global N
    assert condition, label
    N += 1
    print("ok %d - %s" % (N, label))


def dedicated():
    app, page, e, q = T.page_for()
    original = copy.deepcopy(app.project.recipe)
    dialog = UI.UefaRankingDialog(q, e.preview(), q.sources)
    ok("UEFA Ranking is a dedicated interface, not a generic PresetDialog", not isinstance(dialog, UI.PresetDialog) and dialog.conf == 2)
    ok("UEFA title and confirmation identify the ranking action", dialog.windowTitle() == "UEFA Ranking" and dialog.buttons.button(QDialogButtonBox.Ok).text() == "Apply UEFA ranking to draft")
    primary = "\n".join((dialog.instructions.text(), dialog.preview.summary.text(), dialog.preview.show_unchanged.text()))
    ok("UEFA primary instructions and summary contain no generic preset terminology", "preset" not in primary.casefold() and "Ready for draft" not in primary and "included sources" not in primary)
    ok("ranking instructions explain allocations, seeding and the unsaved CUPS draft", all(s in primary for s in ("qualification", "seeding", "unsaved CUPS draft")))
    ok("drag-and-drop and multi-selection are preserved", dialog.list.dragDropMode() == QAbstractItemView.InternalMove and dialog.list.selectionMode() == QAbstractItemView.ExtendedSelection)
    order = [s.draft_key for s in dialog.ranking()[0]]
    dialog.list.setCurrentRow(1)
    dialog.list.item(1).setSelected(True)
    dialog.move(-1)
    ok("Up/Down still changes ranking order and refreshes the comparison", [s.draft_key for s in dialog.ranking()[0]] != order and dialog.preview._data[-1] == dialog.proposal)
    reset = next(b for b in dialog.findChildren(QPushButton) if b.text() == "UEFA's order")
    reset.click()
    ok("UEFA's order resets using the existing default ordering", [s.draft_key for s in dialog.ranking()[0]] == order)
    on, off = dialog.ranking()
    expected = copy.deepcopy(original)
    def candidate(s):
        return dict(id="g%d" % int(s.key) if s.kind == "game" else s.key, name=s.name,
                    country=s.country, clubs=s.clubs, cup=s.cup, game=s.kind == "game")
    T.uefakey.apply(expected, list(map(candidate, on)), list(map(candidate, off)))
    proposed = Q.preview(original, dialog.proposal)
    ok("dedicated dialog produces the exact existing UEFA ranking, access and seeding", all(proposed[k] == expected[k] for k in ("uefa_rank", "uefa_off", "uefa_seed", "game_europe")) and [L.get("europe") for L in proposed["leagues"]] == [L.get("europe") for L in expected["leagues"]])
    ok("CURRENT/PROPOSED comparison and seeding details remain available", dialog.preview.tree.headerItem().text(1) == "Current" and dialog.preview.tree.headerItem().text(2) == "Proposed" and "UEFA seeding" in dialog.preview.technical.toPlainText())
    items = [it for it in text_items(dialog.preview.tree) if isinstance(it.data(0, Qt.UserRole), bool)]
    ok("changed and unchanged places retain their distinct colors", any(it.data(0, Qt.UserRole) for it in items) and any(not it.data(0, Qt.UserRole) for it in items) and all((it.foreground(1).color() == QColor(P.CHANGE_COLOR)) == it.data(0, Qt.UserRole) for it in items))
    ok("legend explains orange and uses exactly the change highlight color", dialog.preview.legend.text() == "Highlighted in orange: changed qualification places" and P.CHANGE_COLOR in dialog.preview.legend.styleSheet())
    generic = UI.PresetDialog(q, e.preview(), q.sources, 3)
    ok("generic comparison previews share the same legend", generic.preview.legend.text() == dialog.preview.legend.text() and generic.windowTitle() == "Generate qualification preset")
    generic.deleteLater()
    dialog.resize(940, 560)
    dialog.show()
    settle()
    ok("legend and ranking confirmation fit the rendered dialog", not dialog.preview.legend.isHidden() and rect(dialog.preview.legend, dialog).right() < dialog.width() and rect(dialog.buttons, dialog).bottom() < dialog.height())
    if os.environ.get("UEFA_UI_CAPTURE"):
        dialog.grab().save(os.environ["UEFA_UI_CAPTURE"] + "-ranking.png")
    dialog.reject()
    with patch.object(UI.UefaRankingDialog, "exec", return_value=QDialog.Rejected) as opened, \
            patch.object(UI, "PresetDialog", side_effect=AssertionError("generic UEFA dialog")):
        q.rank_button.click()
    ok("UEFA toolbar calls the dedicated ranking interface and Cancel leaves everything unchanged", opened.called and app.project.recipe == original and not e.dirty_keys())
    def accept_ranking(d):
        d.confirm()
        return d.result()
    with patch.object(UI.UefaRankingDialog, "exec", accept_ranking), \
            patch.object(UI, "PresetDialog", side_effect=AssertionError("generic UEFA dialog")):
        q.rank_button.click()
    ok("confirmation changes only the shared unsaved CUPS draft", app.project.recipe == original and bool(e.dirty_keys()))
    T.discard(page)
    ok("Discard restores the prior UEFA configuration", app.project.recipe == original and not T.editor(page).dirty_keys())
    e, q = T.editor(page), T.editor(page).qualification
    with patch.object(UI.UefaRankingDialog, "exec", accept_ranking):
        q.rank_button.click()
    T.apply(page)
    saved = copy.deepcopy(app.project.recipe)
    ok("Apply persists the unchanged UEFA algorithm's result", all(saved[k] == expected[k] for k in ("uefa_rank", "uefa_off", "uefa_seed", "game_europe")))
    ok("one Undo restores the original configuration", app.project.undo() and app.project.recipe == original)
    settle()
    ok("Redo restores the complete UEFA ranking result", app.project.redo() and app.project.recipe == saved)
    settle()
    page.close()


def conmebol_label():
    app, page, e, q = T.page_for(Auto.world(), 4)
    checkbox = e.settings["conmebol"]
    before = copy.deepcopy(app.project.recipe)
    ok("CONMEBOL checkbox has the exact requested English label", checkbox.text() == LABEL)
    ok("label changes neither checkbox state nor recipe serialization", checkbox.isChecked() and app.project.recipe == before)
    for width, height in ((1366, 768), (1080, 640)):
        page.resize(width, height)
        page.show()
        settle()
        ok("long CONMEBOL label fits without clipping at %dx%d" % (width, height), checkbox.width() >= checkbox.minimumSizeHint().width() and rect(checkbox, page).right() < page.width())
    if os.environ.get("UEFA_UI_CAPTURE"):
        page.grab().save(os.environ["UEFA_UI_CAPTURE"] + "-conmebol.png")
    changes = UI.A.generate(before, "fake-tables")
    with patch.object(UI, "PresetDialog", side_effect=AssertionError("CONMEBOL ranking")):
        q.generate_button.click()
    ok("CONMEBOL Auto Set still produces exactly the same allocation", {k: v for k, v in e.changes().items() if k[0] == "qualification"} == changes and app.project.recipe == before)
    T.discard(page)
    e, q = T.editor(page), T.editor(page).qualification
    e.settings["conmebol"].setChecked(False)
    T.apply(page)
    ok("renamed checkbox still saves the existing classic-mode field", not Q.modern(app.project.recipe) and not any("Enable Libertadores" in k for k in app.project.recipe))
    e = T.editor(page)
    e.settings["conmebol"].setChecked(True)
    T.apply(page)
    ok("renamed checkbox still saves modern mode under the same key", app.project.recipe["conmebol"] == Q.B.CONMEBOL_MODERN)
    i18n.set_language("es")
    app2, page2, e2, q2 = T.page_for(Auto.world(), 4)
    page2.resize(1080, 640)
    page2.show()
    settle()
    check2 = e2.settings["conmebol"]
    ok("localized CONMEBOL label remains readable at the smaller window", check2.text() == i18n._(LABEL) and check2.width() >= check2.minimumSizeHint().width() and rect(check2, page2).right() < page2.width())
    page2.close()
    i18n.set_language("en")
    page.close()


if __name__ == "__main__":
    with patch.object(Q, "metadata", return_value=(T.NATIVES, T.ASSOCIATIONS, T.CONF)), \
            patch.object(UI.A, "playable_native_rids", return_value={str(s.key) for s in T.NATIVES}), \
            patch.object(T.C.B, "game_competitions", side_effect=lambda base: T.NATIVE if base else []), \
            patch.object(T.C.B, "game_tops", return_value=[(1, "Original cup league", False)]), \
            patch.object(UI, "run_job", side_effect=T.inline):
        dedicated()
        conmebol_label()
    print("test_uefa_ranking_ui: ok (%d)" % N)
