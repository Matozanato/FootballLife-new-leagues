r"""python tools/test_ready_notice.py [tables folder]

B487c (pop1806 16.11.2026): in a ready world (installed from a zip, not made editable yet) a
change to a league (clubs, their names, kits, crest, cups, calendar, format) or to the world's
settings (game cups, Europe, pre-season cups, packages, money, draw, trophies ...) was lost when
My world > Make it editable... read the world's recipe again from its plan; only the players,
the edit tab, a renamed and an added league are carried (pages.myworld carry_added/carry_edits).
Now the pages where such changes are made say so at the top, while the open world is a ready
world (ui.Page.zip_notice): Build, Leagues, Clubs, Cups, New leagues, League packages, NewLife
Database and Trophies. Editing is not blocked. Checked here:
  - the notice on each of those pages for a ready world, none on Players / Kits / Stadiums /
    Import your world (their changes are kept);
  - the page's buttons in sight at 1920x1080 (1920 x 1001 inside the window, the taskbar and the
    title bar off) with the Modpack's size (86 leagues) stay in sight with the notice, in every
    language, and the notice is at most three lines;
  - Trophies (outside My world) has a link that opens My world;
  - Make it editable... (the real one, its job on the fake world) hides every notice, no restart;
    the world a ready one again (Import your world): back;
  - an editable world (built on this PC) has none;
  - the text in es / fr / pt / hr.

The whole window in this process (QT_QPA_PLATFORM=offscreen with a 1920 x 1032 screen), a fake
game folder and APPDATA in a temp folder, the game's tables copied from the folder given, else
FL26_PESDB, else D:/dev/fl26-modding-research/out/base-pesdb. No game, nothing on E: is written.
"""
import json, os, shutil, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SCR_W, SCR_H, TITLE_H = 1920, 1032, 31
T = tempfile.mkdtemp(prefix="readynotice-")
with open(os.path.join(T, "screen.json"), "w") as f:
    json.dump({"screens": [{"name": "fit", "x": 0, "y": 0, "width": SCR_W, "height": SCR_H,
                            "logicalDpi": 96, "logicalBaseDpi": 96, "dpr": 1}]}, f)
os.environ["QT_QPA_PLATFORM"] = "offscreen:configfile=screen.json"      # relative: read with T as cwd
os.environ.pop("FL26_DIR", None)
os.environ["APPDATA"] = os.path.join(T, "appdata")
os.environ["FL26_SAVE_ROOT"] = os.path.join(T, "konami")
PESDB = (sys.argv[1] if len(sys.argv) > 1 else None) or os.environ.get("FL26_PESDB") \
    or "D:/dev/fl26-modding-research/out/base-pesdb"

from test_world_manage import make_game, put

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
N = 0
NOTICE = ("This world came from a zip. To change it, first use My world > Make it editable... Changes to "
          "leagues, clubs, cups and settings made before that are not kept (players' names and edits are).")
WITH = ["Build", "Leagues", "NewClubs", "Cups", "NewLeagues", "Packages", "NewLife", "Trophies"]
WITHOUT = ["Players", "Kits", "Stadiums", "Install"]


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def settle(qa, secs=0.3):
    t0 = time.time()
    while time.time() - t0 < secs:
        qa.processEvents()
        time.sleep(0.01)


def big_recipe(countries):
    """the Modpack's size: 86 leagues, 16-24 clubs each, tiers under each other"""
    leagues, i = [], 0
    have = countries[:40]
    while len(leagues) < 86:
        c = have[i % len(have)]
        tier = sum(1 for L in leagues if L["country"] == c)
        if tier >= 3:
            i += 1
            continue
        n = 16 + (len(leagues) * 5) % 9
        L = {"name": "%s League %d" % (c, tier + 1), "country": c, "clubs": n, "legs": 2,
             "club_names": ["Club %s %02d" % (c, k + 1) for k in range(n)], "club_crests": [None] * n}
        if tier:
            L["above"], L["exchange"] = "%s League %d" % (c, tier), 3
        else:
            L["cup"] = True
        leagues.append(L)
        i += 1
    return {"world": "_FL26Live", "leagues": leagues, "edits": {}, "players": {}}


def in_scroll(b, page):
    """a button inside a list or a form that scrolls on the page: its content, reached by scrolling
    (test_dialogs_fit measures the buttons outside any scroll area the same way)"""
    from PySide6.QtWidgets import QAbstractScrollArea
    p = b.parentWidget()
    while p is not None and p is not page:
        if isinstance(p, QAbstractScrollArea):
            return True
        p = p.parentWidget()
    return False


def in_sight(page, holder):
    """the page's buttons outside its scrolling lists and forms, drawn whole inside the window's
    view of the page"""
    from PySide6.QtWidgets import QAbstractButton
    vp = holder.viewport()
    out = set()
    for b in page.findChildren(QAbstractButton):
        if not b.isVisibleTo(page) or b.width() <= 0 or b.height() <= 0 or in_scroll(b, page):
            continue
        top = b.mapTo(vp, b.rect().topLeft())
        bot = b.mapTo(vp, b.rect().bottomRight())
        if top.y() >= 0 and bot.y() < vp.height() and top.x() >= 0 and bot.x() < vp.width() \
                and b.visibleRegion().boundingRect() == b.rect():
            out.add(b)
    return out


def main():
    try:
        run()
    finally:
        shutil.rmtree(T, ignore_errors=True)
    print("test_ready_notice: ok (%d)" % N)


def run():
    from PySide6.QtWidgets import QApplication
    here = os.getcwd()
    os.chdir(T)
    try:
        qa = QApplication.instance() or QApplication([])
    finally:
        os.chdir(here)
    from PySide6.QtGui import QFontDatabase
    fdir = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    for n in ("SegUIVar.ttf", "segoeui.ttf", "segoeuib.ttf", "segoeuii.ttf", "seguisb.ttf", "consola.ttf"):
        if os.path.exists(os.path.join(fdir, n)):
            QFontDatabase.addApplicationFont(os.path.join(fdir, n))
    from modstudio import app as A, theme, saves as SV, game as G, i18n, ui as U, installer as I
    from modstudio.pages import myworld as M, builder as PB
    import leaguebuilder as B
    SV.game_running = lambda: False
    G.Game.running = staticmethod(lambda: (False, False))
    G.Game.start = lambda self, *a, **k: "not in a test"
    boxes = []
    for mod in (U, M, PB):
        mod.info = lambda parent, title, text, *a, **k: boxes.append(("info", title, text))
        mod.error = lambda parent, title, text, *a, **k: boxes.append(("error", title, text))
    PB.ask = lambda *a, **k: False
    theme.apply(qa)

    if not os.path.isdir(PESDB):
        raise SystemExit("no game tables in %s: give a folder with Team.bin etc. (usage line)" % PESDB)
    game = make_game(T)
    live = os.path.join(game.livecpk_dir, "_FL26Live")
    put(os.path.join(live, ".modstudio"), "a ready world from a zip")            # installer.ready_world
    # the plan Make it editable reads the recipe again from (what leaguebuilder.build writes, short)
    put(os.path.join(live, "leaguebuilder-plan.json"), json.dumps({"world": "_FL26Live", "leagues": [
        {"name": "HNL", "country": 0, "clubs": 2, "legs": 2, "exchange": 3, "rid": 300,
         "club_names": ["Dinamo", "Hajduk"]}]}))
    ms = os.path.join(os.environ["APPDATA"], "FL26ModStudio")
    tables = os.path.join(ms, "tables")
    os.makedirs(tables)
    for n in os.listdir(PESDB):
        if n.endswith(".bin"):
            shutil.copy2(os.path.join(PESDB, n), tables)
    for wn in ("_FL26Live", "_FL26Old"):
        wdb = os.path.join(game.livecpk_dir, wn, "common", "etc", "pesdb")
        for n in os.listdir(tables):
            shutil.copy2(os.path.join(tables, n), wdb)
    recipe = big_recipe(B.country_names(B.base_dir(tables)))
    put(os.path.join(ms, "recipes", "_FL26Live.json"), json.dumps(recipe))
    put(os.path.join(ms, "recipes", "_FL26Old.json"), json.dumps({"world": "_FL26Old", "leagues": []}))
    with open(os.path.join(ms, "settings.json"), "w", encoding="utf-8") as f:
        json.dump({"game": game.folder, "tables": tables, "check_updates": False}, f)

    w = A.Main()
    w.resize(SCR_W, SCR_H - TITLE_H)
    w.move(0, 0)
    w.show()
    settle(qa, 0.8)
    pr = w.project
    if len(pr.recipe.get("leagues") or []) != 86:
        p = os.path.join(T, "big.json")
        put(p, json.dumps(recipe))
        pr.open(p)
        settle(qa, 0.3)
    ok("the ready world is open, the Modpack's size (%d leagues), with the game's tables"
       % len(pr.recipe.get("leagues") or []),
       pr.recipe.get("world") == "_FL26Live" and len(pr.recipe["leagues"]) == 86 and pr.base is not None
       and I.ready_world(w.game, "_FL26Live"))

    ok("the pages with the notice are the ones whose changes Make it editable does not carry: %s"
       % sorted(n for n, p in w.pages.items() if p.zip_notice),
       sorted(n for n, p in w.pages.items() if p.zip_notice) == sorted(WITH))

    def note(n):
        return w.pages[n].zip_note

    # ---- shown on each page, English; the buttons in sight stay in sight; at most three lines
    for code in ("en", "fr", "es", "pt", "hr"):
        i18n.set_language(code)
        for n in WITH:
            w.open_page(n)
            settle(qa, 0.25)
            page, holder = w.pages[n], w.holder_of[n]
            z = note(n)
            z.setVisible(False)
            settle(qa, 0.15)
            before = in_sight(page, holder)
            hbar = holder.horizontalScrollBar().maximum()
            page.zip_note_update()
            settle(qa, 0.15)
            if code == "en":
                ok("%s: the notice is shown for the ready world, at the top, with the text" % n,
                   z.isVisible() and NOTICE.replace(">", "&gt;") in z.text()
                   and z.mapTo(page, z.rect().topLeft()).y() < 200)
            else:
                ok("%s (%s): the notice is shown, in the language" % (n, code),
                   z.isVisible() and "Make it editable" not in z.text())
            after = in_sight(page, holder)
            lost = [b.text() or b.toolTip()[:30] or b.objectName() for b in before - after]
            line = z.fontMetrics().lineSpacing()
            if lost:
                print("   pushed out of sight:", lost, "page", page.height(), "view", holder.viewport().height())
            ok("%s (%s): no button pushed out of sight at 1920x1080 (%d in sight), no sideways scroll, "
               "the notice %d px (%d lines at most 3)" % (n, code, len(before), z.height(), round(z.height() / line)),
               not lost and holder.horizontalScrollBar().maximum() <= hbar and z.height() <= 3 * line + 24)
    i18n.set_language("en")
    for n in WITHOUT:
        w.open_page(n)
        settle(qa, 0.2)
        ok("%s: no notice (its changes are kept)" % n, w.pages[n].zip_note is None)

    # ---- the link on Trophies (outside My world); none on the My world pages (the button is above)
    w.open_page("Trophies")
    settle(qa, 0.2)
    ok("Trophies: a link to My world", 'href="page:Build"' in note("Trophies").text())
    ok("the My world pages: no link (Make it editable... is in sight above the tabs)",
       all('href="page:' not in note(n).text() for n in WITH if n != "Trophies"))
    note("Trophies").linkActivated.emit("page:Build")
    settle(qa, 0.3)
    ok("the link opens My world", w.stack.currentWidget() is w.my_world
       and w.my_world.tabs.currentWidget() is w.holder_of["Build"])
    ok("My world shows Make it editable... for the ready world", w.my_world.b_edit.isVisible())

    # ---- editing is not blocked: the Leagues page's buttons work as before
    ok("editing is not blocked: Add league on Leagues is on", any(
        b.text() == "Add league" and b.isEnabled() for b in w.pages["Leagues"].findChildren(type(w.my_world.b_edit))))

    # ---- Make it editable... (the real button, its job on the fake world): every notice goes
    M.ask = lambda *a, **k: True
    M.can_write = lambda *a, **k: True
    boxes.clear()
    w.my_world.b_edit.click()
    t0 = time.time()
    while I.ready_world(w.game, "_FL26Live") or w._busy:
        if time.time() - t0 > 60:
            break
        settle(qa, 0.1)
    settle(qa, 0.5)
    errs = [b for b in boxes if b[0] == "error"]
    ok("Make it editable... ran: the world is not a ready one any more (%s)" % (errs or "no error box"),
       not I.ready_world(w.game, "_FL26Live") and not errs
       and os.path.exists(os.path.join(live, ".modstudio-edited")))
    for n in WITH:
        w.open_page(n)
        settle(qa, 0.1)
        ok("%s: no notice after Make it editable, no restart" % n, not note(n).isVisible())
    # (the signals alone, with the page hidden: what the pages listen to)
    w.open_page("Players")
    settle(qa, 0.1)
    os.replace(os.path.join(live, ".modstudio-edited"), os.path.join(live, ".modstudio"))
    w.bus.content_changed.emit()                  # Import your world installed it again
    ok("a ready world again (Import your world): the notice is back on every page",
       all(not note(n).isHidden() for n in WITH))
    os.remove(os.path.join(live, ".modstudio"))
    w.bus.ini_changed.emit()
    ok("ini_changed (Make it editable, Put in the game): gone again", all(note(n).isHidden() for n in WITH))
    put(os.path.join(live, ".modstudio"), "a ready world from a zip")
    pr.changed.emit()
    ok("the recipe changed (another world opened): back", all(not note(n).isHidden() for n in WITH))

    # ---- an editable world, built on this PC: none
    p = os.path.join(T, "old.json")
    put(p, json.dumps({"world": "_FL26Old", "leagues": []}))
    pr.open(p)
    settle(qa, 0.3)
    ok("an editable world open: no notice on any page", pr.recipe.get("world") == "_FL26Old"
       and all(note(n).isHidden() for n in WITH))

    # ---- the four languages
    for code in ("es", "fr", "pt", "hr"):
        with open(os.path.join(HERE, "modstudio", "lang", code + ".json"), encoding="utf-8") as f:
            tx = json.load(f)["text"]
        ok("%s.json has the notice and Open My world" % code,
           tx.get(NOTICE, "").strip() and tx.get("Open My world", "").strip() and tx[NOTICE] != NOTICE)
    w.close()


if __name__ == "__main__":
    main()
