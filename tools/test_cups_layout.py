"""Qt layout/scroll regression checks for CUPS; no real project or game is changed."""
import os
import math
import tempfile
from pathlib import Path
from unittest.mock import patch

from test_cups_page import qa, recipe
from test_continental_competitions import make_page, editor, select, NATIVE
from modstudio import competition_catalog as C
from modstudio import theme
from modstudio.ui import HelpMark
from PySide6.QtCore import QPoint, Qt, QRect
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QPushButton, QToolButton, QMenu, QLabel, QScrollArea,
                              QStyle, QStyleOptionTab, QMessageBox)

N = 0


def ok(label, condition):
    global N
    assert condition, label
    N += 1
    print("ok %d - %s" % (N, label))


def settle():
    for _ in range(4):
        qa.processEvents()


def rect(widget, parent):
    from PySide6.QtCore import QRect
    return QRect(widget.mapTo(parent, QPoint()), widget.size())


def header(page):
    apply = page.apply_button
    discard = page.discard_button
    more = page.more_button
    title = next(w for w in page.findChildren(QLabel) if w.objectName() == "pagetitle")
    widgets = [title, discard, apply, more]
    boxes = [rect(w, page) for w in widgets]
    return (all(page.rect().contains(b) for b in boxes)
            and max(b.center().y() for b in boxes) - min(b.center().y() for b in boxes) <= 2
            and all(a.right() < b.left() for a, b in zip(boxes, boxes[1:])))


def header_geometry(page):
    """Logical-pixel geometry from the rendered production hierarchy."""
    title = next(w for w in page.findChildren(QLabel) if w.objectName() == "pagetitle")
    help_button = page.findChildren(HelpMark)[0]
    bar = page.tabs.tabBar()
    option = QStyleOptionTab()
    bar.initStyleOption(option, page.tabs.currentIndex())
    tab_text = bar.style().subElementRect(QStyle.SE_TabBarTabText, option, bar)
    tab_text.moveTopLeft(bar.mapTo(page, tab_text.topLeft()))
    header_bounds = page.actions.geometry().translated(page.actions.parentWidget().mapTo(page, QPoint()))
    rendered = page.grab().toImage()
    title_ink = ink_bounds(rendered, rect(title, page))
    tab_ink = ink_bounds(rendered, tab_text)
    box = lambda r: [r.x(), r.y(), r.width(), r.height()]
    return {"title": box(rect(title, page)), "help": box(rect(help_button, page)),
            "header_layout": box(header_bounds),
            "header_parent": box(rect(page.actions.parentWidget(), page)),
            "title_size_hint": [title.sizeHint().width(), title.sizeHint().height()],
            "header_size_hint": [page.actions.sizeHint().width(), page.actions.sizeHint().height()],
            "header_minimum": [page.actions.minimumSize().width(), page.actions.minimumSize().height()],
            "header_spacing": page.actions.spacing(),
            "tabs": box(rect(page.tabs, page)), "tab_text": box(tab_text),
            "header_to_tabs": rect(page.tabs, page).top() - header_bounds.bottom() - 1,
            "title_to_tab_text": tab_text.top() - rect(title, page).bottom() - 1,
            "title_ink": box(title_ink), "tab_ink": box(tab_ink),
            "visible_title_to_tabs": tab_ink.top() - title_ink.bottom() - 1,
            "title_help_gap": rect(help_button, page).left() - rect(title, page).right() - 1,
            "main_tab_bar": box(rect(bar, page)),
            "confederation": box(rect(editor(page).confederation, page)),
            "confederation_row": box(rect(editor(page).confederation.parentWidget(), page)),
            "tabs_to_confederation": rect(editor(page).confederation, page).top() - rect(bar, page).bottom() - 1,
            "tab_text_to_confederation": rect(editor(page).confederation, page).top() - tab_ink.bottom() - 1,
            "confederation_to_inner_tabs": rect(editor(page).tabs.tabBar(), page).top()
                - rect(editor(page).confederation, page).bottom() - 1,
            "header_buttons": {b.text(): box(rect(b, page)) for b in
                               (page.discard_button, page.apply_button, page.more_button)},
            "outer_margins": [page.outer.contentsMargins().left(), page.outer.contentsMargins().top(),
                              page.outer.contentsMargins().right(), page.outer.contentsMargins().bottom()]}


def ink_bounds(image, area):
    """Actual orange text pixels, excluding tab underline and widget whitespace."""
    target = QColor(theme.ORANGE)
    dpr = image.devicePixelRatio()
    pixels = []
    for y in range(math.floor(area.top() * dpr), math.ceil((area.bottom() + 1) * dpr)):
        for x in range(math.floor(area.left() * dpr), math.ceil((area.right() + 1) * dpr)):
            c = image.pixelColor(x, y)
            if all(abs(a - b) < 40 for a, b in zip(c.getRgb()[:3], target.getRgb()[:3])):
                pixels.append((x, y))
    assert pixels, "rendered text must contain visible foreground pixels"
    left = math.floor(min(x for x, _ in pixels) / dpr)
    top = math.floor(min(y for _, y in pixels) / dpr)
    right = math.ceil((max(x for x, _ in pixels) + 1) / dpr)
    bottom = math.ceil((max(y for _, y in pixels) + 1) / dpr)
    return QRect(left, top, right - left, bottom - top)


def controls():
    app, page = make_page(recipe())
    p = app.project
    ok("one shared Apply and Discard button in the whole page",
       len([b for b in page.findChildren(QPushButton) if b.text() == "Apply"]) == 1
       and len([b for b in page.findChildren(QPushButton) if b.text() == "Discard changes"]) == 1)
    ok("More retains Competition Names, Competition IDs and Trophies",
       [a.text() for a in page.more_button.menu().actions()] == ["Competition names", "Competition IDs", "Trophies"])
    with patch.object(QMessageBox, "information", return_value=QMessageBox.Ok) as explain:
        page.help_button.click()
    ok("natural-size help button retains the original help dialog",
       explain.call_count == 1 and explain.call_args.args[-1] == page.help_button.help_text)
    for width in (720, 1080, 1400):
        page.resize(width, 650)
        settle()
        ok("title / Discard / Apply / More share an unclipped header at %d px" % width, header(page))
    ok("empty per-section messages reserve no blank row", all(s["message"].isHidden() for s in page.all_sections))
    for index in range(3):
        page.tabs.setCurrentIndex(index)
        settle()
        ok("section %d starts with disabled header actions" % index,
           not page.apply_button.isEnabled() and not page.discard_button.isEnabled())
        e = page.all_sections[index]["editor"]
        if index == 0:
            field = e.rows[0][2]
        elif index == 1:
            field = e.rows[0][1][1]
        else:
            field = select(page, "generated:6").name
        field.setText("Draft section %d" % index)
        ok("section %d edits enable both shared actions" % index,
           page.apply_button.isEnabled() and page.discard_button.isEnabled())
    page.tabs.setCurrentIndex(0)
    page.discard_button.click()
    settle()
    ok("header Discard affects only the active domestic section",
       not page.apply_button.isEnabled() and page.sections[1]["editor"].dirty_keys()
       and editor(page).dirty_keys())
    page.tabs.setCurrentIndex(1)
    page.apply_button.click()
    settle()
    ok("header Apply writes the active section and keeps another section's draft",
       p.recipe["leagues"][0]["cup_name"] == "Draft section 1"
       and not page.apply_button.isEnabled() and editor(page).dirty_keys())
    p.undo()
    settle()
    ok("Undo restores cup data after header Apply", p.recipe["leagues"][0]["cup_name"] == "Old cup")
    page.tabs.setCurrentIndex(2)
    ok("returning to a dirty section restores shared enabled state", page.apply_button.isEnabled())
    page.discard_button.click()
    settle()
    ok("continental header Discard clears only the continental draft", not editor(page).dirty_keys())
    select(page, "generated:6").name.setText("Applied Continental")
    page.apply_button.click()
    settle()
    ok("continental header Apply uses existing storage", p.recipe["ccup_names"]["6"] == "Applied Continental")
    page.close()


def spacing():
    _app, page = make_page(recipe())
    # Native theme controls are the reference, not invented replacement sizes.
    refs = [QPushButton(page.discard_button.text()), QPushButton(page.apply_button.text()), QToolButton()]
    refs[1].setObjectName("primary")
    refs[2].setText(page.more_button.text())
    refs[2].setPopupMode(QToolButton.InstantPopup)
    refs[2].setMenu(QMenu(refs[2]))
    for button in refs:
        button.ensurePolished()
    buttons = (page.discard_button, page.apply_button, page.more_button)
    continental_layout = page.continental_section["layout"]
    for width in (720, 1080, 1400):
        page.resize(width, 650)
        for index in range(3):
            page.tabs.setCurrentIndex(index)
            settle()
            continental_layout.setContentsMargins(0, 0, 0, 0)
            settle()
            original = header_geometry(page)
            continental_layout.setContentsMargins(0, 9, 0, 0)
            settle()
            g = header_geometry(page)
            ok("section %d natural-height title / 8px help gap at %d px" % (index, width),
               g["title_help_gap"] == 8 and g["title"][3] == g["title_size_hint"][1]
               and abs(rect(page.title_label, page).center().y() - rect(page.help_button, page).center().y()) <= 1)
            ok("section %d header actions exactly match original theme sizes/fonts at %d px" % (index, width),
               all(b.size() == r.sizeHint() and b.font() == r.font() and not b.styleSheet()
                   for b, r in zip(buttons, refs)) and not page.header.styleSheet())
            ok("section %d restores original title/main-tabs spacing at %d px" % (index, width),
               g["header_to_tabs"] == 6 and g["header_parent"][3] == max(r.sizeHint().height() for r in refs)
               and g["tab_ink"][1] == original["tab_ink"][1] and header(page))
            if index == 2:
                e = editor(page)
                checkbox = e.settings["uecl"]
                ok("real external main-tab/Confederation gap increases from 0 to 9px at %d px" % width,
                   original["tabs_to_confederation"] == 0 and g["tabs_to_confederation"] == 9
                   and g["confederation_row"][1] - g["main_tab_bar"][1] - g["main_tab_bar"][3] == 9
                   and g["confederation_to_inner_tabs"] == original["confederation_to_inner_tabs"] == 6
                   and g["header_buttons"] == original["header_buttons"]
                   and not page.tabs.tabBar().styleSheet())
                ok("confederation and checkbox retain vertical alignment at %d px width" % width,
                   abs(rect(e.confederation, page).center().y() - rect(checkbox, page).center().y()) <= 2)
    page.close()
    for button in refs:
        button.deleteLater()


def scrolling():
    data = recipe()
    data["conmebol"] = "modern"
    app, page = make_page(data)
    page.hide()
    outer = QScrollArea()
    outer.setWidgetResizable(True)
    outer.setWidget(page)
    outer.resize(1000, 420)
    outer.show()
    settle()
    e = editor(page)
    for width, height in ((720, 400), (1000, 420), (1400, 650)):
        outer.resize(width, height)
        settle()
        ok("Continental fits outer viewport %dx%d without an outer scrollbar" % (width, height),
           outer.verticalScrollBar().maximum() == 0 and outer.horizontalScrollBar().maximum() == 0)
        ok("header remains visible at viewport %dx%d" % (width, height), header(page))
        for conf, name in C.CONFEDERATIONS:
            e.confederation.setCurrentIndex(e.confederation.findData(conf))
            settle()
            ok("%s list fits its rows at %dx%d" % (name, width, height),
               e.list.height() == e.list.content_height() and e.list.verticalScrollBar().maximum() == 0)
    for feature, key in (("uecl", "uecl"), ("conmebol", "generated:9"), ("caf_super_cup", "generated:0")):
        e = select(page, key)
        settle()
        before = e.list.height()
        count = e.list.count()
        e.settings[feature].setChecked(False)
        settle()
        ok(feature + " shrinks the list immediately with a valid selection",
           e.list.count() < count and e.list.height() < before and e.list.height() == e.list.content_height()
           and e.list.currentItem() is not None and e.list.verticalScrollBar().maximum() == 0)
        e.settings[feature].setChecked(True)
        settle()
        ok(feature + " restores exact content height", e.list.height() == before and e.list.count() == count)
    e = select(page, "game:libertadores")
    outer.resize(1000, 420)
    settle()
    scroll = e.detail_scroll
    fixed = [rect(w, page) for w in (e.confederation, e.settings_body, e.tabs.tabBar(), e.list)]
    ok("long modern guide is scrollable only inside the right detail panel",
       scroll.verticalScrollBar().maximum() > 0 and outer.verticalScrollBar().maximum() == 0)
    scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum())
    settle()
    ok("end of the complete guide remains reachable",
       rect(e.system_guide, scroll.viewport()).bottom() <= scroll.viewport().rect().bottom()
       and rect(e.system_guide, scroll.viewport()).bottom() >= 0)
    ok("confederation, checkboxes, tabs and list stay fixed while scrolling details",
       fixed == [rect(w, page) for w in (e.confederation, e.settings_body, e.tabs.tabBar(), e.list)])
    ok("compact list aligns with detail panel top and leaves the right side full height",
       rect(e.list, e.splitter).top() == rect(scroll, e.splitter).top()
       and scroll.height() > e.list.height())
    e.list.setSpacing(3)
    e.list.setStyleSheet("QListWidget { border: 3px solid #344658; }")
    e.list.fit_height()
    settle()
    ok("compact height includes item spacing and styled frame dimensions",
       e.list.height() == e.list.content_height() and e.list.verticalScrollBar().maximum() == 0
       and e.list.visualItemRect(e.list.item(e.list.count() - 1)).bottom() < e.list.viewport().height())
    e.list.setSpacing(0)
    e.list.setStyleSheet("")
    settle()
    e.list.addItems(["Future competition %02d" % i for i in range(30)])
    settle()
    ok("future expansion caps list height and enables internal scrolling",
       e.list.height() <= e.list.MAX_HEIGHT and e.list.verticalScrollBar().maximum() > 0)
    e.list.scrollToBottom()
    settle()
    ok("last future row remains accessible", e.list.visualItemRect(e.list.item(e.list.count() - 1)).intersects(e.list.viewport().rect()))
    e.show_confederation()
    settle()
    ok("normal competition set becomes compact again", e.list.height() == e.list.content_height()
       and e.list.verticalScrollBar().maximum() == 0)
    for i in (0, 1):
        page.tabs.setCurrentIndex(i)
        settle()
        table = page.sections[i]["editor"].table
        ok("domestic section %d keeps readable table and scroll access" % i,
           table.height() >= table.minimumHeight() and table.horizontalScrollBarPolicy() == Qt.ScrollBarAsNeeded)
    page.tabs.setCurrentIndex(2)
    settle()
    ok("returning from a taller domestic table removes the outer scrollbar again", outer.verticalScrollBar().maximum() == 0)
    outer.close()


def window_layout():
    # Full production hierarchy, including My World's header and open world cards.
    # Override settings location before importing the application module.
    import json
    with tempfile.TemporaryDirectory(prefix="cups-layout-window-") as root:
        with patch.dict(os.environ, {"APPDATA": root, "FL26_DIR": ""}):
            from modstudio import app as A
            with patch.object(A, "APPDIR", os.path.join(root, "FL26ModStudio")), \
                    patch.object(A, "SETTINGS", os.path.join(root, "FL26ModStudio", "settings.json")), \
                    patch.object(A, "guess_folders", return_value=[]):
                settings = Path(A.APPDIR, "settings.json")
                settings.parent.mkdir(parents=True, exist_ok=True)
                settings.write_text(json.dumps({"check_updates": False, "page": "Settings",
                                                "lang": os.environ.get("CUPS_LAYOUT_LANG", "en")}), encoding="utf-8")
                window = A.Main()
                window.project.base = "fake-tables"
                window.project.recipe = dict(recipe(), conmebol="modern")
                window.project.path = None
                window.project._forget()
                window.show()
                window.open_page("Cups")
                page = window.page("Cups")
                page.tabs.setCurrentIndex(2)
                select(page, "game:libertadores")
                for width, height in ((1400, 900), (1366, 768), (1080, 640)):
                    window.resize(width, height)
                    settle()
                    holder = window.holder_of["Cups"]
                    e = editor(page)
                    print("# full window %dx%d: page=%dx%d outer=%d list=%d/%d" % (
                        width, height, page.width(), page.height(), holder.verticalScrollBar().maximum(),
                        e.list.height(), e.list.content_height()))
                    ok("full window %dx%d keeps header accessible" % (width, height), header(page))
                    ok("full window %dx%d uses only detail vertical scrolling" % (width, height),
                       holder.verticalScrollBar().maximum() == 0 and e.detail_scroll.verticalScrollBar().maximum() > 0)
                    ok("full window %dx%d shows all competition rows" % (width, height), e.list.verticalScrollBar().maximum() == 0)
                    select(page, "game:ucl")
                    settle()
                    ok("full window %dx%d also fits all four UEFA rows" % (width, height),
                       e.list.count() == 4 and e.list.verticalScrollBar().maximum() == 0
                       and holder.verticalScrollBar().maximum() == 0)
                    e.name.setText("Pending compact layout")
                    settle()
                    ok("full window %dx%d retains detail-only scrolling with pending changes" % (width, height),
                       holder.verticalScrollBar().maximum() == 0 and page.apply_button.isEnabled())
                    page.discard_button.click()
                    settle()
                    select(page, "game:libertadores")
                if os.environ.get("CUPS_LAYOUT_SNAPSHOT"):
                    window.resize(1366, 768)
                    settle()
                    window.grab().save(os.environ["CUPS_LAYOUT_SNAPSHOT"])
                if os.environ.get("CUPS_HEADER_CAPTURE"):
                    import json
                    window.resize(1366, 768)
                    settle()
                    prefix = os.environ["CUPS_HEADER_CAPTURE"]
                    Path(prefix + ".json").write_text(json.dumps(header_geometry(page), indent=2), encoding="utf-8")
                    page.grab().save(prefix + ".png")
                    # Compare only the external margin; tabs retain the shared
                    # theme's original padding in both rendered captures.
                    page.continental_section["layout"].setContentsMargins(0, 0, 0, 0)
                    settle()
                    Path(prefix + "-original.json").write_text(
                        json.dumps(header_geometry(page), indent=2), encoding="utf-8")
                    page.grab().save(prefix + "-original.png")
                    page.continental_section["layout"].setContentsMargins(0, 9, 0, 0)
                    settle()
                window.close()
                settle()


if __name__ == "__main__":
    with patch.object(C.B, "game_competitions", side_effect=lambda base: NATIVE if base else []), \
            patch.object(C.B, "game_tops", return_value=[(1, "Alpha Game", False), (2, "Beta Game", True)]):
        controls()
        spacing()
        scrolling()
        window_layout()
    print("test_cups_layout: ok (%d)" % N)
