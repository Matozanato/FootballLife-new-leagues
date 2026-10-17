r"""python tools/test_my_world.py

0.2.4 (mato 15.10., variant A): one section, My world, in place of Build and edit your world,
Import your world and NewLife Database.
  - the bar has five numbered items: Home, My world, Game content, Tools, Settings; Build, Import
    your world and NewLife Database still open (inside My world, with no tab lit);
  - My world shows a card for each world on disk: the one in the game green (IN THE GAME NOW)
    with Export / Rename / Delete, Delete refused for it; another world has Put in the game, and
    pressing it switches that world on in sider.ini and turns its card green;
  - Cups does not stay lit after one of its windows (B70);
  - a card says "1 league · 1 new club", not "1 leagues" (B70);
  - + Add... tells a league package (.fl26pack, with its leagues to tick), a world zip and the
    NewLife Database folder apart.

The whole window in this process (QT_QPA_PLATFORM=offscreen), a fake game folder and APPDATA in
a temp folder. No game.
"""
import json, os, shutil, sys, tempfile, time, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.pop("FL26_DIR", None)
T = tempfile.mkdtemp(prefix="myworld-")
os.environ["APPDATA"] = os.path.join(T, "appdata")      # before modstudio.app reads it (APPDIR)
os.environ["FL26_SAVE_ROOT"] = os.path.join(T, "konami")  # Put in the game switches the save folder: a fake one

from test_world_manage import make_game, put

N = 0
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def settle(qa, secs=1.0):
    t0 = time.time()
    while time.time() - t0 < secs:
        qa.processEvents()
        time.sleep(0.02)


def main():
    try:
        run()
    finally:
        shutil.rmtree(T, ignore_errors=True)
    print("test_my_world: ok (%d)" % N)


def run():
    from PySide6.QtWidgets import QApplication, QPushButton
    from PySide6.QtGui import QColor
    qa = QApplication.instance() or QApplication([])
    from modstudio import app as A, theme, worlds as WL
    from modstudio.pages import myworld as M, builder as PB, install as PI
    PI.error = lambda *a, **k: None          # Import your world: "choose the game folder first"
    PB.ask = lambda *a, **k: False           # "unpack the game's tables?" (NewLife, no tables here): no
    from modstudio import saves as SV, ui as U
    SV.game_running = lambda: False          # the fake save folder: whatever runs on this PC
    from modstudio import game as G
    G.Game.running = staticmethod(lambda: (False, False))   # rename/delete: the real game may run on this PC
    from modstudio.pages import roots as RPm
    RPm.error = lambda parent, title, text: (_ for _ in ()).throw(AssertionError("error box: %s: %s" % (title, text)))
    notes = []
    U.info = lambda parent, title, text: notes.append(text)
    put(os.path.join(os.environ["FL26_SAVE_ROOT"], "save", "ML00000000"), b"career of _FL26Live")
    theme.apply(qa)
    game = make_game(T)
    ms = os.path.join(os.environ["APPDATA"], "FL26ModStudio")
    os.makedirs(os.path.join(ms, "tables"))
    for x in ("_FL26Live", "_FL26Old"):         # Build's copies of their recipes (Project.copies_dir)
        put(os.path.join(ms, "recipes", x + ".json"), json.dumps({"world": x, "leagues": []}))
    with open(os.path.join(ms, "settings.json"), "w", encoding="utf-8") as f:
        json.dump({"game": game.folder, "tables": os.path.join(ms, "tables"), "check_updates": False}, f)
    ok("the window's settings are in the temp APPDATA", A.APPDIR == ms)
    w = A.Main()
    w.resize(1400, 860)
    w.show()
    settle(qa, 0.5)

    # ---- the bar
    texts = [b.text() for b in w.nav_group.buttons()]
    ok("the bar: five numbered items, %s" % texts,
       texts == ["1. Home", "2. My world", "3. Game content  ▾", "4. Tools  ▾", "5. Settings"])
    ok("no Build and edit your world / Import your world / NewLife Database in the bar",
       not any(k in w.nav_buttons for k in ("Build", "Import", "NewLife")))
    # B82 (16.10.): Build is the first tab of My world; the others still open inside it with no tab lit
    for name in ("Build", "Install", "NewLife", "Packages", "NewLeagues"):
        w.open_page(name)
        qa.processEvents()
        sec = w.my_world
        lit = [n for n, b in sec.tab_btn.items() if b.isChecked()]
        ok("%s still opens, inside My world, %s" % (name, "as the lit Build tab" if name == "Build" else "with no tab lit"),
           w.stack.currentWidget() is sec and sec.tabs.currentWidget() is w.holder_of[name]
           and lit == (["Build"] if name == "Build" else [])
           and w.nav_buttons["World"].isChecked())
    ok("B82: Build is the first tab", list(sec.tab_btn) [0] == "Build")
    w.open_page("Leagues")
    qa.processEvents()
    ok("Leagues is the lit tab of My world", w.my_world.tab_btn["Leagues"].isChecked())
    ok("the tabs: Build (B82), Leagues, Clubs, Players, Kits, Stadiums and Cups",
       [b.text() for b in w.my_world.tab_btn.values()] + [w.my_world.cups.text()]
       == ["Build", "Leagues", "Clubs", "Players", "Kits", "Stadiums", "Cups"])
    # ---- B70: Cups stayed lit on the page opened after one of its windows (Build details)
    from PySide6.QtCore import Qt, QPoint
    from PySide6.QtGui import QCursor
    cups = w.my_world.cups
    QCursor.setPos(w.mapToGlobal(QPoint(w.width() - 2, w.height() - 2)))   # the mouse is not on Cups
    opened = []
    w.page("NewLeagues").preseason = lambda: opened.append("preseason")
    cups.setAttribute(Qt.WA_UnderMouse, True)          # what the window left behind
    cups.menu().actions()[0].trigger()
    ok("B70: Cups > Pre-season cups opens its window and Cups lets go of its lit look",
       opened == ["preseason"] and not cups.underMouse())
    cups.setAttribute(Qt.WA_UnderMouse, True)
    w.open_page("Build")
    qa.processEvents()
    ok("B70: the Build tab: Cups is not lit", not cups.underMouse()
       and [n for n, b in w.my_world.tab_btn.items() if b.isChecked()] == ["Build"])
    w.open_page("Leagues")
    settle(qa, 1.0)

    # ---- the cards
    sec = w.my_world
    cards = {c.world: c for c in sec.cards}
    ok("a card for each world on disk, the live one first: %s" % list(cards),
       list(cards) == ["_FL26Live", "_FL26Old"])
    ok("the world in the game is the open one", w.project.recipe.get("world") == "_FL26Live")
    live = cards["_FL26Live"]
    ok("the live card: worldlive, IN THE GAME NOW", live.objectName() == "worldlive"
       and "IN THE GAME NOW" in live.eyebrow.text())
    ok("the live card is 420 x 120", (live.width(), live.height()) == (M.CARD_W, M.CARD_H))
    pic = live.grab().toImage()
    ok("its border is the theme's green", QColor(pic.pixel(0, pic.height() // 2)).name().lower()
       == QColor(theme.GOOD).name().lower())
    ok("its background is the live green", QColor(pic.pixel(pic.width() // 2, 4)).name().lower()
       == QColor(theme.LIVE_BG).name().lower())
    btns = [b.text() for b in live.findChildren(QPushButton)]
    ok("the live card has Active (off) / Export / Rename / Delete: %s" % btns,
       all(t in btns for t in ("⇪ Export...", "Rename", "Delete")) and live.go.text().endswith("Active")
       and not live.go.isEnabled())
    ok("Delete is refused for the world in the game", not live.delete.isEnabled()
       and "in the game now" in live.delete.toolTip())
    old = cards["_FL26Old"]
    ok("the other world: worldcard, NOT IN THE GAME, Activate",
       old.objectName() == "worldcard" and old.eyebrow.text() == "NOT IN THE GAME"
       and old.go.text().endswith("Activate") and old.go.isEnabled() and old.delete.isEnabled())
    ok("+ New world after the cards", sec.new_world.text() == "+ New world")
    ok("the counters: competitions and new countries", "/ 255" in sec.c_comps.text()
       and "/ 99" in sec.c_regions.text())
    ok("the Master League note in the header; one Build and install button only, on the Build tab (B82)",
       "Master League" in sec.note.text() and not hasattr(sec, "build") and hasattr(sec, "world_state"))

    # ---- Put in the game: the switch, then the cards again
    PB.ask = lambda *a, **k: True
    old.go.click()
    settle(qa, 0.5)
    ok("Put in the game switched _FL26Old on in sider.ini, _FL26Live off", WL.live(game) == ["_FL26Old"])
    ok("its recipe is the open one now (the tabs change it)", w.project.recipe.get("world") == "_FL26Old")
    kr = os.environ["FL26_SAVE_ROOT"]
    ok("Put in the game switched the save folder: _FL26Live's career in save__FL26Live, save is _FL26Old's",
       open(os.path.join(kr, "save__FL26Live", "ML00000000"), "rb").read() == b"career of _FL26Live"
       and os.path.isdir(os.path.join(kr, "save")) and not os.listdir(os.path.join(kr, "save")))
    ok("the first time the player is told where the careers are", len(notes) == 1 and "save__FL26Live" in notes[0])
    st = w.page("Settings")
    st.refresh()
    ok("Settings: Each world keeps its own careers, on", st.per_world.isChecked())
    st.per_world.setChecked(False)
    ok("Settings: unticked, the setting is off", w.settings.get(SV.SETTING) is False)
    st.per_world.setChecked(True)
    cards = {c.world: c for c in sec.cards}
    ok("the cards follow: _FL26Old green and first", sec.cards[0].world == "_FL26Old"
       and cards["_FL26Old"].objectName() == "worldlive" and cards["_FL26Live"].objectName() == "worldcard"
       and cards["_FL26Live"].go.isEnabled() and not cards["_FL26Old"].go.isEnabled())

    # ---- Rename on a card: in the background, the cards wait meanwhile (B66) and keep their order (B75)
    from modstudio.pages import roots as RP
    from PySide6 import QtWidgets
    RP.ask = lambda *a, **k: True
    QtWidgets.QInputDialog.getText = staticmethod(lambda *a, **k: ("_FL26Live2", True))
    before = [c.world for c in sec.cards]
    sec.rename("_FL26Live")
    ok("Rename on a card: the cards wait (buttons off), the card says Renaming _FL26Live...",
       sec._renaming == "_FL26Live" and all(not c.rename.isEnabled() and not c.export.isEnabled() for c in sec.cards)
       and any(c.world == "_FL26Live" and c.info.text() == "Renaming _FL26Live..." for c in sec.cards))
    t0 = time.time()
    while sec._renaming and time.time() - t0 < 60:
        qa.processEvents()
        time.sleep(0.02)
    settle(qa, 0.5)
    after = [c.world for c in sec.cards]
    ok("Rename on a card: done, the renamed card in the same place: %s -> %s" % (before, after),
       not sec._renaming and after == [x.replace("_FL26Live", "_FL26Live2") for x in before]
       and all(c.rename.isEnabled() for c in sec.cards))

    # ---- + Add...
    pk = os.path.join(T, "SerieCD.fl26pack")
    with zipfile.ZipFile(pk, "w") as z:
        z.writestr("manifest.json", json.dumps({
            "format": "fl26pack", "format_version": 1, "name": "Serie C+D", "version": "1",
            "leagues": [{"name": "Serie C", "country": "Italy", "clubs": 20},
                        {"name": "Serie D", "country": "Italy", "clubs": 18}]}))
    wz = os.path.join(T, "FL26-Modpack.zip")
    with zipfile.ZipFile(wz, "w") as z:
        z.writestr("SiderAddons/livecpk/_FL26Modpack/fl26world.txt", "world _FL26Modpack\n")
    nl = os.path.join(T, "NewLife 1.5")
    for f in ("players.csv", "clubs.csv", "newlife.json"):
        put(os.path.join(nl, "NewLife-1.5", f), "x")
    nz = os.path.join(T, "nl15-whole.zip")
    with zipfile.ZipFile(nz, "w") as z:
        for f in ("players.csv", "clubs.csv", "newlife.json"):
            z.writestr(f, "x")
    other = os.path.join(T, "ball.zip")
    with zipfile.ZipFile(other, "w") as z:
        z.writestr("ball/config.txt", "x")
    ok("kind_of: .fl26pack", M.kind_of(pk) == ("pack", pk))
    ok("kind_of: world zip", M.kind_of(wz) == ("world", wz))
    ok("kind_of: NewLife folder (one level deeper too)", M.kind_of(nl) == ("newlife", nl))
    ok("kind_of: NewLife in one zip", M.kind_of(nz)[0] == "newlife-zip")
    ok("kind_of: any other zip goes to Import your world", M.kind_of(other) == ("mod", other))
    ok("kind_of: not there", M.kind_of(os.path.join(T, "nope.zip"))[0] == "")
    card = {"world": "_FL26X", "title": "_FL26X", "built": True, "when": "", "open": False, "live": False}
    ok("B70: a card says 1 league · 1 new club, not 1 leagues · 1 new clubs: %s"
       % M.info_text(dict(card, leagues=1, clubs=1)), M.info_text(dict(card, leagues=1, clubs=1)) == "1 league · 1 new club")
    ok("and 2 leagues · 0 new clubs", M.info_text(dict(card, leagues=2, clubs=0)) == "2 leagues · 0 new clubs")
    d = M.AddDialog(sec, sec.card_title())
    ok("the window: Add to <world>", d.windowTitle() == "Add to _FL26Old")
    ok("Add is off until something is picked", not d.add.isEnabled())
    d.pick(pk)
    ok("a package: Found: league package, 2 leagues, 38 clubs: %s" % d.found.text(),
       d.kind == "pack" and 'league package "Serie C+D" (2 leagues, 38 clubs)' in d.found.text())
    ok("its leagues to tick, all ticked", d.picked() == ["Serie C", "Serie D"])
    ok("Add on", d.add.isEnabled())
    d.pick(wz)
    ok("a world zip: Found: a world zip", d.kind == "world" and "world zip" in d.found.text()
       and d.ticks.count() == 0 and d.add.isEnabled())
    d.pick(nl)
    ok("the NewLife folder: Found: NewLife Database", d.kind == "newlife" and "NewLife Database" in d.found.text())
    d.pick(nz)
    ok("NewLife in one zip: unpack it first, Add off", d.kind == "" and not d.add.isEnabled()
       and "unpack" in d.found.text())
    d.pick(other)
    ok("anything else: Import your world looks inside", d.kind == "mod" and d.add.isEnabled())
    d.pick(wz)
    d.go()
    qa.processEvents()
    ok("Add with a world zip opens Import your world inside My world",
       w.stack.currentWidget() is sec and sec.tabs.currentWidget() is w.holder_of["Install"])
    d.deleteLater()

    # the row of world cards folds away and stays folded (Xxspedd, 17.10.)
    ok("the world cards show at first", not sec.cards_area.isHidden() and "▾" in sec.fold.text())
    sec.fold.click()
    qa.processEvents()
    ok("Worlds folds them away, and the settings keep it",
       sec.cards_area.isHidden() and "▸" in sec.fold.text() and w.settings.get("cards_folded") is True)
    sec.fold.click()
    qa.processEvents()
    ok("and opens them again", not sec.cards_area.isHidden() and w.settings.get("cards_folded") is False)
    w.close()
    qa.processEvents()


if __name__ == "__main__":
    main()
