r"""python tools/test_dialogs_fit.py [--screen 1920x1032]

HARD rule (mato, 17.10.): every window of Mod Studio fits a 1920x1080 screen -- 1920 x 1032 with the
Windows taskbar -- with the biggest content we have (the Modpack: 86 leagues, well over 1000 clubs),
its OK / Add / Cancel / Close buttons on the screen without scrolling the window. David found + Add...
1958 px tall with the Modpack's package (fixed in ecca268; test_my_world.py "86 leagues").

The whole window in this process (QT_QPA_PLATFORM=offscreen with a 1920 x 1032 screen from a config
file), a fake game folder and APPDATA in a temp folder, the game's tables copied from
D:/dev/fl26-modding-research/out/base-pesdb (FL26_PESDB overrides). No game, nothing on E:.

Every dialog is opened the way the program opens it (its page method, or its class with the same
arguments), and exec() is caught: the window is shown non-modally, measured and closed with Cancel,
so nothing in the world changes. A message box (QMessageBox.question/information/warning/critical/
about) and an input box (QInputDialog.getText/getItem/getInt) are built with the same text and
measured the same way. Measured: the window with its title bar (TITLE_H) fits the screen, it sits on
the screen, and its buttons (a QDialogButtonBox's, else the bottom row of push buttons outside any
scroll area) are shown and inside the window.

The windows of Mod Studio (grep QDialog / class .*Dialog / .exec() in tools/modstudio, 17.10.):
  app.py         Credits (QDialog), Update available (QDialog, offer_update), Unsaved changes
                 (QMessageBox in closeEvent), Play: module order problems (question), About,
                 Help, language changed, update checks (information/warning)
  changes.py     WorldChangesDialog (Changes in this world)
  ui.py          denied_box (Windows refused the write), ask/info/error (QMessageBox statics)
  myworld.py     AddDialog (+ Add...)
  builder.py     Dialog (base: a form that scrolls, fit()), LeagueDialog (Add league, Add lower tier,
                 Edit league), StadiumPicker, ClubDialog (new club, club of the game), GameClubDialog,
                 PreseasonDialog, CompetitionIdsDialog, CompetitionNamesDialog, GameEuropeDialog,
                 EuropeFirstDialog, UefaRankDialog, LeagueOrderDialog, GameSeasonsDialog,
                 SouthAmericaDialog, GameCupsDialog, OurCupsDialog, PasteDialog, "Move to another
                 league" (a plain Dialog), SwapDialog, CrestImportDialog, AfterBuild (Build finished);
                 QInputDialog (Only the new European cups...), Remove leagues (question)
  newlife.py     ClubPickDialog, UpdateDialog, GameLeaguesDialog
  packages.py    MakeDialog (Make a league package), AddDialog (Add a league package)
  playerpick.py  PickPlayers (Sign / Call up players), PickClub (Transfer to...)
  tableimport.py ImportDialog (Import a squad from a table)
  content.py     RowDialog (Add a line / Change the line of a server's map), QInputDialog.getItem
  players.py / profiles.py / roots.py / install.py: QInputDialog (Squad level, Save current setup,
                 Rename world, Folder name in livecpk)
  QFileDialog (every Choose a file / folder / Save as): the Windows file chooser, sized by Windows.
Whatever this test cannot open is printed as NOT COVERED: <name> (reason), for the UI test through
the exe; nothing is skipped without a word.
"""
import json, os, shutil, sys, tempfile, time, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SCR_W, SCR_H = 1920, 1032          # a 1920 x 1080 screen less the Windows taskbar (48 px)
if "--screen" in sys.argv:
    SCR_W, SCR_H = (int(x) for x in sys.argv[sys.argv.index("--screen") + 1].lower().split("x"))
TITLE_H, EDGE = 31, 1              # Windows 11 title bar and border at 100 %: offscreen draws none
T = tempfile.mkdtemp(prefix="dialogsfit-")
with open(os.path.join(T, "screen.json"), "w") as f:
    json.dump({"screens": [{"name": "fit", "x": 0, "y": 0, "width": SCR_W, "height": SCR_H,
                            "logicalDpi": 96, "logicalBaseDpi": 96, "dpr": 1}]}, f)
# the platform's options are split at ":" -- a path with C: in it breaks them: a relative one,
# read while the QApplication is made with T as the working folder
os.environ["QT_QPA_PLATFORM"] = "offscreen:configfile=screen.json"
os.environ.pop("FL26_DIR", None)
os.environ["APPDATA"] = os.path.join(T, "appdata")
os.environ["FL26_SAVE_ROOT"] = os.path.join(T, "konami")
PESDB = os.environ.get("FL26_PESDB") or "D:/dev/fl26-modding-research/out/base-pesdb"

from test_world_manage import make_game, put

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
N = 0
SEEN = []            # every window measured: dict(label, kind, title, w, h, problems, buttons)
COVER = []           # (opener, [records])
NOT_COVERED = []     # (name, reason)
NATIVE = []          # QFileDialog calls met on the way
CUR = {"label": ""}


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


def in_scroll(w, top):
    from PySide6.QtWidgets import QAbstractScrollArea
    p = w.parentWidget()
    while p is not None and p is not top:
        if isinstance(p, QAbstractScrollArea):
            return True
        p = p.parentWidget()
    return False


def action_buttons(d):
    """the window's own buttons: a button box's, else the bottom row of push buttons outside any
    scroll area (+ Add...'s Cancel / Add, Build finished's Done, Changes' Close ...)"""
    from PySide6.QtWidgets import QDialogButtonBox, QPushButton
    out = []
    for bb in d.findChildren(QDialogButtonBox):
        if not in_scroll(bb, d) and bb.isVisibleTo(d):
            out += [b for b in bb.buttons() if b.isVisibleTo(d)]
    if out:
        return out
    pbs = [b for b in d.findChildren(QPushButton) if b.isVisibleTo(d) and not in_scroll(b, d)]
    if not pbs:
        return []
    low = max(b.mapTo(d, b.rect().topLeft()).y() for b in pbs)
    return [b for b in pbs if abs(b.mapTo(d, b.rect().topLeft()).y() - low) <= 6]


def measure(d, kind="dialog", note=""):
    from PySide6.QtCore import QRect
    from PySide6.QtWidgets import QApplication
    qa = QApplication.instance()
    d.show()
    settle(qa, 0.25)
    g = d.geometry()
    fw, fh = g.width() + 2 * EDGE, g.height() + TITLE_H + EDGE
    probs = []
    if fh > SCR_H:
        probs.append("too tall: %d px with its title bar, the screen has %d" % (fh, SCR_H))
    if fw > SCR_W:
        probs.append("too wide: %d px, the screen has %d" % (fw, SCR_W))
    top, bottom = g.y() - TITLE_H, g.y() + g.height() + EDGE
    # Qt places the inside of the window offscreen, Windows its frame: 2 px of the border may differ
    if not probs and (top < -2 or bottom > SCR_H + 2 or g.x() < -2 or g.x() + g.width() > SCR_W + 2):
        probs.append("placed off the screen: x %d..%d, y %d..%d (title bar included)"
                     % (g.x(), g.x() + g.width(), top, bottom))
    btns = action_buttons(d)
    if not btns:
        probs.append("no OK / Cancel / Close button found")
    for b in btns:
        r = QRect(b.mapTo(d, b.rect().topLeft()), b.size())
        if not b.isVisible():
            probs.append("button %r not shown" % b.text())
        elif not d.rect().contains(r):
            probs.append("button %r outside the window (%d,%d %dx%d in %dx%d)"
                         % (b.text(), r.x(), r.y(), r.width(), r.height(), d.width(), d.height()))
        elif g.y() + r.bottom() > SCR_H:
            probs.append("button %r below the screen (y %d)" % (b.text(), g.y() + r.bottom()))
    rec = {"label": CUR["label"], "kind": kind, "cls": type(d).__name__, "title": d.windowTitle(),
           "w": fw, "h": fh, "y": top, "problems": probs, "buttons": [b.text() for b in btns], "note": note}
    SEEN.append(rec)
    d.hide()
    return rec


def patch_qt():
    from PySide6.QtWidgets import QDialog, QMessageBox, QInputDialog, QFileDialog

    def dlg_exec(self):
        measure(self)
        return 0                                      # Rejected: nothing changes

    def box_exec(self):
        measure(self, "message box", self.text()[:80])
        return QMessageBox.Cancel

    QDialog.exec = dlg_exec
    QMessageBox.exec = box_exec

    def static_box(icon, buttons, answer):
        def f(parent, title, text, *a, **k):
            b = QMessageBox(icon, title, text, buttons, parent)
            measure(b, "message box", text.replace("\n", " ")[:80])
            b.deleteLater()
            return answer
        return staticmethod(f)
    QMessageBox.question = static_box(QMessageBox.Question, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    QMessageBox.information = static_box(QMessageBox.Information, QMessageBox.Ok, QMessageBox.Ok)
    QMessageBox.warning = static_box(QMessageBox.Warning, QMessageBox.Ok, QMessageBox.Ok)
    QMessageBox.critical = static_box(QMessageBox.Critical, QMessageBox.Ok, QMessageBox.Ok)
    QMessageBox.about = static_box(QMessageBox.NoIcon, QMessageBox.Ok, None)

    def input_box(answer, items=False):
        def f(parent, title, label, *a, **k):
            d = QInputDialog(parent)
            d.setWindowTitle(title)
            d.setLabelText(label)
            if items and a:
                d.setComboBoxItems(list(a[0]))
            measure(d, "input box", label.replace("\n", " ")[:80])
            d.deleteLater()
            return answer
        return staticmethod(f)
    QInputDialog.getText = input_box(("", False))
    QInputDialog.getItem = input_box(("", False), items=True)
    QInputDialog.getInt = input_box((0, False))

    def native(answer):
        def f(parent=None, caption="", *a, **k):
            NATIVE.append((CUR["label"], caption))
            return answer
        return staticmethod(f)
    QFileDialog.getOpenFileName = native(("", ""))
    QFileDialog.getOpenFileNames = native(([], ""))
    QFileDialog.getSaveFileName = native(("", ""))
    QFileDialog.getExistingDirectory = native("")


def opened(label, fn):
    """run an opener: every window it shows is measured; none, or an exception: NOT COVERED"""
    CUR["label"] = label
    n0 = len(SEEN)
    try:
        fn()
    except Exception as e:
        import traceback
        NOT_COVERED.append((label, "could not open headless: %s: %s" % (type(e).__name__, e)))
        traceback.print_exc()
        return []
    got = SEEN[n0:]
    if not got:
        NOT_COVERED.append((label, "no window opened headless"))
    COVER.append((label, got))
    return got


# ---- the big world: the Modpack's size
COUNTRIES = ["England", "Spain", "Italy", "Germany", "France", "Portugal", "Netherlands", "Belgium", "Scotland",
             "Turkey", "Greece", "Croatia", "Serbia", "Bosnia and Herzegovina", "Slovenia", "Austria",
             "Switzerland", "Denmark", "Sweden", "Norway", "Poland", "Czech Republic", "Romania", "Hungary",
             "Ukraine", "Russia", "Argentina", "Brazil", "Uruguay", "Chile", "Colombia", "Mexico", "United States",
             "Japan", "Korea Republic", "China PR", "Australia", "Saudi Arabia", "Egypt", "Morocco"]
TIERS = ["Premier Division", "First League", "Second League", "Third Division North"]
WORDS = ["Real Club Deportivo", "Athletic", "Sporting", "Dinamo", "Union", "Olympique", "Racing", "Atletico",
         "Football Club", "Rovers", "Wanderers", "Calcio", "Borussia", "Spartak", "Hajduk", "Universidad"]


def big_recipe(countries):
    have = [c for c in COUNTRIES if c in countries] or countries[:40]
    leagues, i = [], 0
    while len(leagues) < 86:
        c = have[i % len(have)]
        tier = sum(1 for L in leagues if L["country"] == c)
        if tier >= len(TIERS):
            i += 1
            continue
        n = 16 + (len(leagues) * 5) % 9                       # 16 .. 24
        name = "%s %s" % (c, TIERS[tier])
        L = {"name": name, "country": c, "clubs": n, "legs": 2,
             "club_names": ["%s %s %02d" % (WORDS[(k + len(leagues)) % len(WORDS)], c, k + 1) for k in range(n)],
             "club_abbrs": ["%s%02d" % (c[:1].upper(), k + 1) for k in range(n)],
             "club_crests": [None] * n}
        if tier == 0:
            L["europe"] = [[1, 0], [2, 0], [3, 1], [4, 2], [0, 2]]
            L["cup"] = True
            L["super_cup"] = True
        else:
            L["above"] = "%s %s" % (c, TIERS[tier - 1])
            L["exchange"] = 3
        leagues.append(L)
        i += 1
    return {"world": "_FL26Live", "leagues": leagues, "edits": {}, "players": {},
            "preseason_cups": [{"name": "Summer Cup %d" % j, "clubs": ["%s/%d" % (leagues[j]["name"], k)
                                                                          for k in range(4)]} for j in range(6)]}


def big_pack(path, recipe):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("manifest.json", json.dumps({
            "format": "fl26pack", "format_version": 1, "name": "FL26 Modpack leagues", "version": "0.2.4",
            "author": "mato", "player_changes": 1300, "faces": 900,
            "edits": {"leagues": ["1"], "clubs": ["2", "3"]},
            "description": "Every league of the FL26 Modpack: 86 leagues, their clubs, crests, kits, "
                           "scoreboards and squads.",
            "leagues": [{"name": L["name"], "country": L["country"], "clubs": L["clubs"]}
                        for L in recipe["leagues"]]}))


def main():
    try:
        run()
    finally:
        shutil.rmtree(T, ignore_errors=True)


def run():
    from PySide6.QtWidgets import QApplication
    here = os.getcwd()
    os.chdir(T)
    try:
        qa = QApplication.instance() or QApplication([])
    finally:
        os.chdir(here)
    # offscreen has no fonts of its own on Windows: text came out 2.35x wider and lines 13 px instead of
    # 17 (17.10.). The Windows fonts the theme asks for, so sizes are the ones the exe shows.
    from PySide6.QtGui import QFontDatabase
    fdir = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    for n in ("SegUIVar.ttf", "segoeui.ttf", "segoeuib.ttf", "segoeuii.ttf", "seguisb.ttf", "consola.ttf"):
        if os.path.exists(os.path.join(fdir, n)):
            QFontDatabase.addApplicationFont(os.path.join(fdir, n))
    ok("the Windows font is there (Segoe UI)", "Segoe UI" in QFontDatabase.families())
    sg = qa.primaryScreen().availableGeometry()
    ok("the screen is %dx%d (%dx%d asked)" % (sg.width(), sg.height(), SCR_W, SCR_H),
       (sg.width(), sg.height()) == (SCR_W, SCR_H))
    from modstudio import app as A, theme, saves as SV, ui as U, game as G
    from modstudio.pages import builder as PB, install as PI, myworld as M
    import leaguebuilder as B
    SV.game_running = lambda: False
    G.Game.running = staticmethod(lambda: (False, False))
    G.Game.start = lambda self, *a, **k: "not in a test"         # never the game
    theme.apply(qa)
    patch_qt()

    game = make_game(T)
    ms = os.path.join(os.environ["APPDATA"], "FL26ModStudio")
    tables = os.path.join(ms, "tables")
    os.makedirs(tables)
    for n in os.listdir(PESDB):
        if n.endswith(".bin"):
            shutil.copy2(os.path.join(PESDB, n), tables)
    base = B.base_dir(tables)
    for wn in ("_FL26Live", "_FL26Old"):       # make_game's worlds have a dummy Team.bin: the game's tables
        wdb = os.path.join(game.folder, "SiderAddons", "livecpk", wn, "common", "etc", "pesdb")
        for n in os.listdir(tables):
            shutil.copy2(os.path.join(tables, n), wdb)
    recipe = big_recipe(B.country_names(base))
    clubs = sum(L["clubs"] for L in recipe["leagues"])
    ok("the big world: %d leagues, %d clubs" % (len(recipe["leagues"]), clubs),
       len(recipe["leagues"]) == 86 and clubs >= 1300)
    # some changes to the game's own clubs (Changes in this world, Import crests)
    gcl = sorted(B.game_clubs(base))
    recipe["edits"]["clubs"] = {str(t): {"name": "Renamed club %d" % t} for t in gcl[:300]}
    put(os.path.join(ms, "recipes", "_FL26Live.json"), json.dumps(recipe))
    put(os.path.join(ms, "recipes", "_FL26Old.json"), json.dumps({"world": "_FL26Old", "leagues": []}))
    # a stadium library: 86 countries x 5 stadiums
    lib = os.path.join(game.folder, "SiderAddons", "content", "stadium-server")
    for j, L in enumerate(recipe["leagues"]):
        for s in range(5):
            put(os.path.join(lib, "Country %02d %s" % (j, L["country"]), "Stadium %s %d" % (L["name"], s),
                             "config.txt"), "x")
    with open(os.path.join(ms, "settings.json"), "w", encoding="utf-8") as f:
        json.dump({"game": game.folder, "tables": tables, "check_updates": False}, f)

    w = A.Main()
    w.resize(1400, 860)
    w.move(260, 80)
    w.show()
    settle(qa, 0.8)
    pr = w.project
    if len(pr.recipe.get("leagues") or []) != 86:
        p = os.path.join(T, "big.json")
        put(p, json.dumps(recipe))
        pr.open(p)
        settle(qa, 0.3)
    ok("the window has the big world open (%d leagues) and the game's tables" % len(pr.recipe["leagues"]),
       len(pr.recipe["leagues"]) == 86 and pr.base is not None)

    # ---- the main window itself
    w.open_page("Leagues")
    settle(qa, 0.3)
    mh = w.minimumSizeHint()
    CUR["label"] = "Main window (smallest size)"
    rec = {"label": CUR["label"], "kind": "window", "cls": "Main", "title": w.windowTitle(),
           "w": max(mh.width(), w.minimumWidth()) + 2 * EDGE, "h": max(mh.height(), w.minimumHeight()) + TITLE_H + EDGE,
           "y": 0, "problems": [], "buttons": [], "note": ""}
    if rec["h"] > SCR_H or rec["w"] > SCR_W:
        rec["problems"].append("its smallest size %dx%d is bigger than the screen" % (rec["w"], rec["h"]))
    SEEN.append(rec)
    COVER.append((CUR["label"], [rec]))

    # ---- app.py
    opened("Credits", w.credits)
    opened("Update available (80 lines of notes)", lambda: w.offer_update({
        "version": "9.9.9", "page": "https://example.invalid/",
        "notes": "\n".join(["## New"] + ["- a new thing number %d that takes a long line to say what it does" % i
                                         for i in range(40)] + ["## Fixed"] + ["- bug B%d fixed" % i for i in range(40)])}))
    opened("Changes in this world (300 club changes)", w.show_changes)
    opened("About", w.about)
    opened("Help (no README next to it)", w.guide)
    mods = w.pages.get("Modules")
    if mods is not None:
        mods.order_problems = lambda: ["module_%02d.lua must be loaded after module_%02d.lua, it uses its "
                                       "tables at start" % (i, i + 1) for i in range(12)]
    opened("Play: problems with the module order", w.play)
    opened("Windows refused the write (denied_box)",
           lambda: U.denied_box(w, os.path.join(game.folder, "SiderAddons", "sider.ini")))

    # ---- My world: + Add... with the Modpack's 86-league package
    pk = os.path.join(T, "Modpack86.fl26pack")
    big_pack(pk, recipe)
    sec = w.my_world

    def add_dialog():
        d = M.AddDialog(sec, sec.card_title())
        measure(d, note="empty")
        d.pick(pk)
        measure(d, note="86-league package picked")
        d.deleteLater()
    opened("My world > + Add... (86-league package)", add_dialog)
    opened("My world > Rename world (input box)", lambda: w.page("Roots").rename_world("_FL26Old", done=lambda n: None))

    # ---- Leagues (NewLeagues page)
    nl = w.page("NewLeagues")
    nl.refresh()
    settle(qa, 0.2)

    def select(i):
        nl.tree.setCurrentItem(nl.tree.topLevelItem(i))
    opened("New league (LeagueDialog)", nl.add)
    select(0)
    opened("Add lower tier (LeagueDialog)", nl.add_lower)
    big = max(range(86), key=lambda i: recipe["leagues"][i]["clubs"] * (recipe["leagues"][i].get("above") is None))
    select(big)
    opened("Edit league (LeagueDialog, %d clubs, European places)" % recipe["leagues"][big]["clubs"], nl.edit)

    def remove_all():
        for i in range(nl.tree.topLevelItemCount()):
            nl.tree.topLevelItem(i).setSelected(True)
        nl.remove()
    opened("Remove 86 leagues (question box listing them)", remove_all)
    ok("Remove asked and was told no: the 86 leagues are still there", len(pr.recipe["leagues"]) == 86)
    for label, fn in (("Pre-season cups (PreseasonDialog)", nl.preseason),
                      ("Competition IDs (CompetitionIdsDialog)", nl.competition_ids),
                      ("Competition names (CompetitionNamesDialog)", nl.competition_names),
                      ("European places of the game's leagues (GameEuropeDialog)", nl.game_europe),
                      ("First-season European clubs (EuropeFirstDialog)", nl.europe_first),
                      ("UEFA ranking (UefaRankDialog)", nl.uefa_rank),
                      ("South American places (SouthAmericaDialog)", nl.samerica),
                      ("League order (LeagueOrderDialog)", nl.league_order),
                      ("Seasons of the game's leagues (GameSeasonsDialog)", nl.game_seasons),
                      ("Cups of the game's countries (GameCupsDialog)", nl.game_cups),
                      ("Cups of our countries (OurCupsDialog, %d top divisions)"
                       % sum(1 for L in recipe["leagues"] if not L.get("above")), nl.our_cups)):
        opened(label, fn)

    # ---- Clubs (NewClubs page)
    nc = w.page("NewClubs")
    w.open_page("NewClubs")
    settle(qa, 0.2)
    nc.combo.setCurrentIndex(big)
    settle(qa, 0.2)
    nc.tree.setCurrentItem(nc.tree.topLevelItem(2))
    ok("Clubs: a club of %s is selected" % nc.league()["name"], nc.current() is not None)
    opened("Edit club (ClubDialog, stadium library of 430)", nc.edit)
    opened("Club of the game... (GameClubDialog)", nc.game_club)

    class Rel:                                 # a NewLife Database: 162 leagues, 3000 clubs
        version = "NewLife 1.5"
        clubs = {str(100000 + j): {"name": "%s %d" % (WORDS[j % len(WORDS)], j), "league": "League %d" % (j // 18),
                                   "in_game": "0"} for j in range(3000)}

        def use_tables(self, g):
            pass

        def use_recipe(self, r):
            pass
    nc.nl_rel = Rel()
    opened("NewLife club... (ClubPickDialog, 3000 clubs)", nc.newlife_club)
    opened("Move to another league... (85 leagues)", nc.move_club)
    opened("Paste names... (PasteDialog)", nc.paste)
    opened("Remove club (question box)", lambda: nc.shift(-1))
    opened("Import crests... (CrestImportDialog)", lambda: PB.import_crests(nc))
    opened("Choose a home stadium (StadiumPicker, 430 stadiums)",
           lambda: PB.StadiumPicker(nc, PB.stadium_lib(w), "").exec())

    # ---- the game's leagues and clubs
    gl = w.page("Leagues").game
    info = B.game_info(pr.base)
    tid = next(t for t in sorted(info["league_of"]) if t in pr.game_cl)
    opened("Edit club of the game (ClubDialog)", lambda: PB.edit_game_club(gl, tid))
    opened("Swap leagues with a club... (SwapDialog)", lambda: PB.SwapDialog(gl, pr, tid, set()).finish())

    # ---- Build finished
    bp = w.page("Build")
    opened("Build finished (AfterBuild)", lambda: PB.AfterBuild(bp, {
        "world": "_FL26Live", "secs": 412, "leagues": 86, "clubs": clubs,
        "notes": [PB.database_note(pr) or "Your world uses the NewLife Database 1.5: its clubs and squads.",
                  "Exhibition: the new leagues show in Exhibition under Other European and Other Asian, "
                  "86 leagues in groups of 24, the clubs in no league under Others.",
                  "Each world keeps its own careers: the careers of _FL26Old are in save__FL26Old."]}).exec())
    if hasattr(bp, "do_europe_only"):
        opened("Only the new European cups... (input box)", bp.do_europe_only)

    # ---- NewLife
    from modstudio.pages import newlife as NLP
    from modstudio import newlife as NLM
    NLM.lineup = lambda rel, x, rows, keep=False: ({}, {"clubs": [str(100000 + k) for k in range(int(x["clubs"]))],
                                                         "in_game": []})
    opened("Update my leagues to this version (UpdateDialog, 86 leagues)",
           lambda: NLP.UpdateDialog(w.page("NewLife"), Rel(), recipe["leagues"], []).finish())
    gcl_names = {t: n for t, (n, s) in pr.game_cl.items()}
    plan = [{"name": name, "release": "NewLife %s" % name, "cid": rid,
             "clubs": list(teams), "swaps": [(teams[0], teams[1]), (teams[2], teams[3])] if len(teams) > 3 else [],
             "replace": [(teams[-1], "100001")] if teams else [], "notes": ["Two clubs keep their own squads."]}
            for rid, cid, name, teams in [(r, c, n, list(ts)) for r, c, n, ts in pr.game_lgs]]
    opened("Bring the game's leagues to this season (GameLeaguesDialog, %d leagues)" % len(plan),
           lambda: NLP.GameLeaguesDialog(w.page("NewLife"), Rel(), plan, {"clubs": info["clubs"]}, "1.4").finish())

    # ---- League packages
    kp = w.page("Packages")
    opened("Add a league package (packages.AddDialog, 86 leagues)", lambda: kp.add_pack(pk))
    opened("Make a league package (MakeDialog, 86 leagues)", kp.make_pack)

    # ---- Players
    from modstudio.pages import playerpick as PP, tableimport as TI
    pp = w.page("Players")
    opened("Sign players... (PickPlayers)", lambda: PP.PickPlayers(pp, pr, "Sign players...").exec())
    every = [("%s  —  %s" % (n, L["name"]), "%s/%d" % (L["name"], k))
             for L in recipe["leagues"] for k, n in enumerate(L["club_names"])]
    every += [("%s  —  #%d" % (n, t), str(t)) for t, (n, s) in sorted(pr.game_cl.items())]
    opened("Transfer to... (PickClub, %d clubs)" % len(every),
           lambda: PP.PickClub(pp, "Transfer to...", "Somebody moves to:", every).exec())
    head = ["Name", "Position", "Age", "Nationality", "Club", "Height", "Weight", "Preferred Foot"] + \
           ["Attribute %d" % i for i in range(52)]
    rows = [["Player %d" % i] + ["%d" % (i + j) for j in range(len(head) - 1)] for i in range(30)]
    opened("Import a squad from a table (ImportDialog, %d columns)" % len(head),
           lambda: TI.ImportDialog(pp, "fm-export.csv", head, rows, "A new club has 30 places ...").exec())

    # ---- content servers: a line of each map
    from modstudio.pages.content import ServerView, RowDialog
    views = w.findChildren(ServerView)
    for v in views:
        for t in v.map_tabs:
            opened("%s > %s > Add a line (RowDialog)" % (v.server.key, t.m.title),
                   lambda v=v, t=t: RowDialog(v, t.m).exec())
    if not views:
        NOT_COVERED.append(("content servers: Add a line (RowDialog)", "no ServerView in the window"))

    # ---- Profiles
    prof = w.pages.get("Profiles")
    if prof is not None and hasattr(prof, "save_new"):
        opened("Profiles > Save current setup... (input box)", prof.save_new)

    # ---- unsaved changes on closing
    pr.dirty = True
    opened("Unsaved changes (closing the window)", w.close)
    pr.dirty = False

    # ---- what this test does not open
    for name, why in (
            ("Players > Squad level... (QInputDialog.getInt)", "needs a club's squad loaded on the Players page; a "
             "standard Qt input box like Rename world's, which is measured"),
            ("Game content > a server's Library > Use it for... (QInputDialog.getItem)", "needs a library item "
             "picked; a standard Qt input box"),
            ("Import your world > Folder name in livecpk (QInputDialog.getText)", "only for a mod zip without a "
             "folder; a standard Qt input box"),
            ("every Choose a file / folder / Save as... (QFileDialog)", "the Windows file chooser: Windows sizes "
             "it, not Mod Studio"),
            ("Import your world / Install: the boxes after a real install", "they need a real mod zip and write "
             "to the game folder"),
            ("Updates: up to date / could not reach GitHub (information / warning)", "need the network; one-line "
             "message boxes")):
        NOT_COVERED.append((name, why))

    # ---- the report
    print()
    print("Screen %dx%d (title bar %d px counted). Every window measured:" % (SCR_W, SCR_H, TITLE_H))
    bad = []
    for r in SEEN:
        tag = "FAIL" if r["problems"] else "ok  "
        print("  %s %-62s %-24s %4d x %4d  %s%s" % (tag, r["label"][:62], r["cls"][:24], r["w"], r["h"],
                                                    ", ".join(r["buttons"]) or "-",
                                                    ("  [" + r["note"] + "]") if r["note"] else ""))
        for p in r["problems"]:
            print("         ! " + p)
        if r["problems"]:
            bad.append(r)
    for label, caption in NATIVE:
        print("  file chooser met under %s: %s (Windows' own, NOT COVERED)" % (label, caption))
    print()
    for name, why in NOT_COVERED:
        print("NOT COVERED: %s (%s)" % (name, why))
    print()
    print("%d windows measured, %d too big / off the screen, %d not covered"
          % (len(SEEN), len(bad), len(NOT_COVERED)))
    w.project.dirty = False
    for x in qa.topLevelWidgets():
        x.hide()
    qa.processEvents()
    ok("every window measured fits the %dx%d screen with its buttons on it: %s"
       % (SCR_W, SCR_H, "; ".join("%s %dx%d" % (r["label"], r["w"], r["h"]) for r in bad) or "all"), not bad)
    print("test_dialogs_fit: ok (%d)" % N)


if __name__ == "__main__":
    main()
