"""Compact BUILD settings and relocated European-only action; no real game writes."""
import copy
import json
import os
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from test_cups_page import App, qa
from modstudio.pages import builder as UI
from modstudio.i18n import _
from PySide6.QtCore import Qt, QPoint, QRect
from PySide6.QtWidgets import QLabel, QPushButton, QComboBox, QFrame, QInputDialog, QScrollArea

N = 0


def ok(label, condition):
    global N
    assert condition, label
    N += 1
    print("ok %d - %s" % (N, label))


def settle():
    for _ in range(4):
        qa.processEvents()


def run():
    owner = App()
    p = owner.project
    p.adopt({"world": "_FL26BuildLayout", "leagues": [], "players": {"keep": {"edits": {"1": {"name": "Unchanged"}}}},
             "uecl_name": "My Conference", "uecl_logo": "keep-logo.png"}, None)
    game = SimpleNamespace(ok=lambda: False, folder="", livecpk_dir="unused-build-layout")
    app = SimpleNamespace(project=p, settings={}, game=game, update_world_bar=lambda: None)
    build = UI.Build(app)
    outer = QScrollArea()
    outer.setWidgetResizable(True)
    outer.setWidget(build)
    outer.resize(1000, 700)
    outer.show()
    build.opts.set_open(True, save=False)
    build.stepfold.set_open(True, save=False)

    def refresh():
        with patch.object(build, "ready_live", return_value=[]), \
                patch.object(build, "file_text", return_value="File: test fixture"):
            build.refresh()
        settle()

    refresh()
    ok("no redundant Continental navigation button or handler",
       not hasattr(build, "b_cups") and not hasattr(build, "open_continental")
       and not any(b.text() == _("Manage continental competitions...") for b in build.findChildren(QPushButton)))
    ok("Country cups framed panel and heading are removed",
       not any(l.text() == _("Country cups") for l in build.findChildren(QLabel)))
    ok("draw is a direct compact row in existing World options",
       build.cupdraw_row.parentWidget() is build.opts.inner
       and build.opts.body.itemAt(0).widget() is build.cupdraw_row
       and build.cupdraw_row.minimumHeight() == 0
       and not any(f.objectName() == "card" and f.isAncestorOf(build.cupdraw)
                   for f in build.findChildren(QFrame)))
    ok("Country cup draw is not duplicated",
       len([c for c in build.findChildren(QComboBox) if c.accessibleName() == _("Country cup draw")]) == 1)
    ok("draw keeps all three existing options and explanatory text",
       [build.cupdraw.itemData(i) for i in range(build.cupdraw.count())] == ["seeded", "random", "off"]
       and any("bracket" in l.text() for l in build.cupdraw_row.findChildren(QLabel)))
    ok("European-only action is inside existing Step by step operations",
       build.stepfold.inner.isAncestorOf(build.b_euro)
       and not build.opts.inner.isAncestorOf(build.b_euro))
    ok("European-only action is not duplicated and retains its tooltip",
       len([b for b in build.findChildren(QPushButton) if b.text() == _("Build only the European cups...")]) == 1
       and "no new leagues" in build.b_euro.toolTip())
    ok("keyboard focus and label buddy remain available",
       build.b_euro.focusPolicy() & Qt.TabFocus and build.cupdraw.focusPolicy() & Qt.TabFocus
       and any(l.buddy() is build.cupdraw for l in build.cupdraw_row.findChildren(QLabel)))
    ok("new-club options and all normal build steps remain present",
       all(hasattr(build, field) for field in ("mkits", "rkits", "ekits", "pfaces", "squad", "b_all"))
       and len(build.steps) == 10)
    before = copy.deepcopy(p.recipe)
    for mode in ("random", "off", "seeded"):
        p._snap_at = 0
        build.cupdraw.setCurrentIndex(build.cupdraw.findData(mode))
        ok("draw mode %s uses existing recipe and backend rule" % mode,
           UI.B.cup_draw(p.recipe) == mode and (mode != "seeded" or "cup_draw" not in p.recipe))
    ok("draw changes preserve unrelated recipe data",
       all(p.recipe[k] == value for k, value in before.items()))
    ok("Undo of draw setting succeeds", p.undo())
    refresh()
    ok("refresh shows the undone draw setting", build.cupdraw.currentData() == "off")
    ok("Redo of draw setting succeeds", p.redo())
    refresh()
    ok("refresh shows the redone draw setting", build.cupdraw.currentData() == "seeded")
    with tempfile.TemporaryDirectory(prefix="build-cups-ui-") as root:
        p.path = os.path.join(root, "recipe.json")
        p._snap_at = 0
        build.cupdraw.setCurrentIndex(build.cupdraw.findData("random"))
        p.autosave()
        with open(p.path, encoding="utf-8") as stream:
            saved = json.load(stream)
        ok("draw still autosaves through Project", saved["cup_draw"] == "random" and not p.dirty)
        game.ok = lambda: True
        game.folder = root
        game.livecpk_dir = root
        for enabled in (False, True):
            p.recipe["uecl"] = enabled
            current = copy.deepcopy(p.recipe)
            with patch.object(build, "ready_blocks", return_value=False), \
                    patch.object(QInputDialog, "getText", return_value=("_FL26EuroLayout", True)) as prompt, \
                    patch.object(UI, "can_write", return_value=True), \
                    patch.object(UI.B, "plan", return_value={"world": "_FL26EuroLayout"}) as planner, \
                    patch.object(build, "run") as run_build:
                build.b_euro.click()
            ok("European-only click reaches the same backend with Conference %s" % enabled,
               planner.call_count == run_build.call_count == 1
               and planner.call_args.args[0]["uecl"] is enabled
               and planner.call_args.args[0]["uecl_name"] == "My Conference"
               and planner.call_args.args[0]["uecl_logo"] == "keep-logo.png"
               and planner.call_args.args[0]["leagues"] == []
               and run_build.call_args.kwargs["background"] is True
               and ("and the Conference League" in prompt.call_args.args[2]) == enabled
               and p.recipe == current)
        game.ok = lambda: False
        p.path = None
    for width, height in ((720, 600), (1080, 640), (1400, 900)):
        outer.resize(width, height)
        settle()
        ok("draw row stays natural-height and separate from club options at %d px" % width,
           build.cupdraw_row.height() < 100
           and build.cupdraw_row.geometry().bottom() < build.cards_area.geometry().top())
        for control in (build.cupdraw, build.b_euro):
            outer.ensureWidgetVisible(control)
            settle()
            visible = QRect(control.mapTo(outer.viewport(), QPoint()), control.size())
            ok("%s remains reachable at %dx%d" % (control.accessibleName() or control.text(), width, height),
               outer.viewport().rect().contains(visible) and control.isVisible() and control.isEnabled())
    if os.environ.get("BUILD_LAYOUT_SNAPSHOT"):
        outer.resize(1200, 950)
        outer.ensureWidgetVisible(build.cupdraw)
        settle()
        outer.grab().save(os.environ["BUILD_LAYOUT_SNAPSHOT"])
    outer.close()
    settle()


if __name__ == "__main__":
    run()
    print("test_build_cups_layout: ok (%d)" % N)
