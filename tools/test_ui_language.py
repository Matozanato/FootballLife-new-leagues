r"""python tools/test_ui_language.py [es|fr|pt|hr]      (no language: all four, one after the other)

B71 (0.2.4): the new screens were half English in the other languages -- texts the code put on
screen without _( ), a text filled in with % before _( ) looked it up (so no key matched), and the
League Builder's own lines (South American places, the UEFA ranking) that only the command line
spoke. This test opens the whole window in another language (Spanish by default) and reads what
a player sees:

  - every page, every tab of My world and of the pages with tabs of their own, Game content,
    Tools and Settings, opened one after the other;
  - on each: the texts of the visible labels, buttons, group boxes, tabs, table headers and combo
    boxes, and the actions of every menu (File, Game, Help, Game content, Tools ...).

A text fails when it is an English text of the translation catalogue whose translation differs
(it should have been translated), when it is such a text filled in ("%s is installed." shown as
"X is installed."), or when it is a sentence of more than three words in plain English that is
not in the catalogue at all. ALLOW lists what stays as it is (names of the game, brands, file
names). Then the lines the builder makes (South American places, the UEFA key's table and notes)
go through the "log" rules and must come out with no English left, and the messages of
worlds.check_name, Project.move_club and Install's world-in-the-way come out translated.

The whole window in this process (QT_QPA_PLATFORM=offscreen), a fake game folder and APPDATA in a
temp folder. No game.
"""
import html, json, os, re, shutil, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ENV0 = dict(os.environ)          # for the run of each language: its own APPDATA keeps Python's user packages
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.pop("FL26_DIR", None)
T = tempfile.mkdtemp(prefix="uilang-")
os.environ["APPDATA"] = os.path.join(T, "appdata")      # before modstudio.app reads it (APPDIR)
os.environ["FL26_SAVE_ROOT"] = os.path.join(T, "konami")

from test_world_manage import make_game, put

LANG = sys.argv[1] if len(sys.argv) > 1 else "es"
assert LANG in ("es", "fr", "pt", "hr"), "usage: test_ui_language.py [es|fr|pt|hr]"
N = 0
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# what stays as it is in every language: names of the game, brands, the program's own name
ALLOW = {
    "FL26 // MOD STUDIO", ">_", "FL26 Mod Studio", "Sider", "Lua", "OK", "UEFA", "AFC", "CAF", "CONMEBOL",
    "CONCACAF", "OFC", "Libertadores", "Copa Libertadores", "Copa Sudamericana", "Champions League",
    "Europa League", "Conference League", "Master League", "NewLife", "NewLife Database", "Kit Server",
    "Select Team", "Kick Off", "Edit", "English", "Hrvatski", "Español", "Português", "Français",
    "Discord", "GitHub", "Ko-fi", "Football Life 2026", "SP Football Life 2026", "PES", "eFootball",
}
# English words a sentence of another language does not have (no "a", "no", "en", "de" ...)
ENGLISH = set("the and of to is are your this with for not it be that from will has have you its what "
              "which when there here into only can been was were by an or all any must does do than then "
              "they them their these those would should could after before every each other first".split())


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def settle(qa, secs=0.3):
    t0 = time.time()
    while time.time() - t0 < secs:
        qa.processEvents()
        time.sleep(0.02)


def catalogue(code):
    """{English: translation} as i18n reads it: the League Builder's file, then Mod Studio's"""
    out = {}
    for d in (os.path.join(HERE, "lang"), os.path.join(HERE, "modstudio", "lang")):
        p = os.path.join(d, code + ".json")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                out.update(json.load(f).get("text") or {})
    return out


def template(key):
    """a regex for an English text with %s / %d in it, or None when it says too little to tell
    (no word of two letters around the gaps: "%s: %s", "%d / %d")"""
    parts = re.split(r"(%(?:\.\d+)?[sdif]|%%)", key)
    if len(parts) == 1:
        return None
    lit = "".join(p for i, p in enumerate(parts) if i % 2 == 0)
    if not re.search(r"[A-Za-z]{2}", lit):
        return None
    rx = ""
    for i, p in enumerate(parts):
        if i % 2 == 0:
            rx += re.escape(p)
        elif p == "%%":
            rx += "%"
        elif p == "%d":
            rx += r"-?\d+"
        else:
            rx += r".+?"
    return re.compile(rx + r"\Z", re.S)


def clean(t):
    """a widget's text as the catalogue has it: no markup, no &-shortcut, no number of the bar
    ("2. My world"), no menu arrow"""
    t = t or ""
    if "<" in t and ">" in t:
        t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    t = t.replace("&&", "\0").replace("&", "").replace("\0", "&")
    t = re.sub(r"\s+▾$", "", t.strip())
    t = re.sub(r"^\d+\.\s+(?=\D)", "", t)
    return t.strip()


class Judge:
    def __init__(self, code):
        self.cat = catalogue(code)
        self.values = set(self.cat.values())
        self.tpl = [(k, template(k)) for k, v in self.cat.items() if v != k]
        self.tpl = [(k, r) for k, r in self.tpl if r is not None]
        self.bad = {}

    def why(self, t):
        """why the text t is English left over, or None"""
        if not t or t in ALLOW or t in self.values or not re.search(r"[A-Za-z]{2}", t):
            return None
        if t in self.cat:
            return "an English text of the catalogue, not translated" if self.cat[t] != t else None
        for k, rx in self.tpl:
            if rx.match(t):
                return "the English text %r filled in, not translated" % k
        if re.search(r"[\\/]|\.(?:txt|ini|lua|json|zip|bin|cpk|dll|exe|png|dds|log|fl26pack)\b", t) \
                or re.fullmatch(r"_FL26\w*", t) or re.fullmatch(r"[\d.\s/%:,-]+\w{0,3}", t):
            return None
        words = t.split()
        if len(words) > 3 and all(ord(c) < 128 for c in t):
            hits = sum(1 for w in re.findall(r"[A-Za-z']+", t.lower()) if w in ENGLISH)
            if hits >= 2:
                return "a sentence in English that is not in the catalogue"
        return None

    def look(self, where, kind, text):
        raw = clean(text)
        for t in [raw] + ([clean(x) for x in raw.split("\n")] if "\n" in raw else []):
            w = self.why(t)
            if w:
                self.bad.setdefault((kind, t), (where, w))


def texts_of(root):
    """(kind, text) of what is visible in root now"""
    from PySide6.QtWidgets import (QAbstractButton, QComboBox, QGroupBox, QLabel, QTabBar, QTableWidget,
                                   QTreeWidget, QAbstractItemView, QHeaderView)
    from PySide6.QtCore import Qt
    from modstudio.ui import Stat
    out = []
    for w in root.findChildren(QLabel):
        if w.isVisible() and w.objectName() != "statval":
            out.append(("QLabel", w.text()))
    for w in root.findChildren(Stat):          # a state box shows its text cut to fit: the whole text
        if w.isVisible():
            out.append(("state box", w.text()))
    for w in root.findChildren(QAbstractButton):
        if w.isVisible():
            out.append((type(w).__name__, w.text()))
    for w in root.findChildren(QGroupBox):
        if w.isVisible():
            out.append(("QGroupBox", w.title()))
    for w in root.findChildren(QTabBar):
        if w.isVisible():
            out += [("tab", w.tabText(i)) for i in range(w.count())]
    for w in root.findChildren(QComboBox):
        if w.isVisible():
            out += [("QComboBox", w.itemText(i)) for i in range(w.count())]
    for w in root.findChildren(QAbstractItemView):
        if not w.isVisible() or w.model() is None:
            continue
        m = w.model()
        for orient, n, hv in ((Qt.Horizontal, m.columnCount(), getattr(w, "horizontalHeader", None)),
                              (Qt.Vertical, m.rowCount(), getattr(w, "verticalHeader", None))):
            if orient == Qt.Vertical and not isinstance(w, QTableWidget):
                continue
            h = hv() if hv else None
            if isinstance(w, QTreeWidget):
                h = w.header()
            if h is None or not h.isVisible():
                continue
            for i in range(n):
                v = m.headerData(i, orient, Qt.DisplayRole)
                if isinstance(v, str):
                    out.append(("header", v))
    return out


def run():
    from PySide6.QtWidgets import QApplication, QMenu, QTabWidget
    qa = QApplication.instance() or QApplication([])
    # offscreen has no fonts of its own on Windows (text 2.35x wider, test_dialogs_fit): the fonts the
    # theme asks for, so the widths below are the ones the exe shows
    from PySide6.QtGui import QFontDatabase
    fdir = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    for n in ("SegUIVar.ttf", "segoeui.ttf", "segoeuib.ttf", "segoeuii.ttf", "seguisb.ttf", "consola.ttf"):
        if os.path.exists(os.path.join(fdir, n)):
            QFontDatabase.addApplicationFont(os.path.join(fdir, n))
    from modstudio import app as A, theme, i18n
    from modstudio.pages import builder as PB, install as PI
    PI.error = lambda *a, **k: None
    PB.ask = lambda *a, **k: False
    from modstudio import saves as SV, ui as U
    SV.game_running = lambda: False
    U.info = lambda *a, **k: None
    theme.apply(qa)
    game = make_game(T)
    ms = os.path.join(os.environ["APPDATA"], "FL26ModStudio")
    os.makedirs(os.path.join(ms, "tables"))
    for x in ("_FL26Live", "_FL26Old"):
        put(os.path.join(ms, "recipes", x + ".json"), json.dumps({"world": x, "leagues": []}))
    with open(os.path.join(ms, "settings.json"), "w", encoding="utf-8") as f:
        json.dump({"game": game.folder, "tables": os.path.join(ms, "tables"), "check_updates": False,
                   "lang": LANG}, f)
    judge = Judge(LANG)
    w = A.Main()
    ok("the window speaks %s" % LANG, i18n.CODE == LANG)
    w.resize(1360, 820)                    # the window's first size
    w.show()
    settle(qa, 0.5)

    names = list(w.pages)
    for name in names:
        w.open_page(name)
        settle(qa, 0.15)
        tabsets = [t for t in w.stack.currentWidget().findChildren(QTabWidget) if t.isVisible()]
        for t in [None] + tabsets:
            for i in range(t.count() if t is not None else 1):
                if t is not None:
                    t.setCurrentIndex(i)
                    settle(qa, 0.05)
                for kind, text in texts_of(w):
                    judge.look(name if t is None else "%s / tab %d" % (name, i), kind, text)
    # My world's own tabs, one after the other
    for n in list(w.my_world.tab_btn):
        w.open_page(n)
        settle(qa, 0.1)
        for kind, text in texts_of(w):
            judge.look("My world / " + n, kind, text)
    # what the French UI test through the exe (18.10.) found cut short at 1920 x 1080, where the Spanish
    # words fit: "+ NOUVEAU MONDI" on My world, the tables' "ACTI" / "EMPLAC" columns, "DERNIÈRES
    # MODIFICATION" on Home. Each must show its whole text, in every language
    from PySide6.QtWidgets import QHeaderView, QLabel, QStyle, QStyleOptionButton, QTreeWidget
    w.resize(1920, 1032)
    w.open_page("Build")
    settle(qa, 0.2)
    nw = w.my_world.new_world
    opt = QStyleOptionButton()
    nw.initStyleOption(opt)
    room = nw.style().subElementRect(QStyle.SE_PushButtonContents, opt, nw).width()
    need = nw.fontMetrics().horizontalAdvance(nw.text())
    ok("%r shows all of its text (%d of %d px)" % (nw.text(), need, room), need <= room)
    heads = {i18n._("On"), i18n._("Slot")}
    seen = 0
    for name in names + [n for n in w.my_world.tab_btn if n not in names]:
        w.open_page(name)
        settle(qa, 0.1)
        for tr in w.findChildren(QTreeWidget):
            if not tr.isVisible():
                continue
            hh, item = tr.header(), tr.headerItem()
            for c in range(tr.columnCount()):
                # every column of a set width, not only On and Slot (B134 after 0.2.4: "DOSSIERS ACT",
                # "MODULES ACT" on Profiles, "ID DU B" on Balls); the last one fills the rest
                fixed = (hh.sectionResizeMode(c) == QHeaderView.Interactive
                         and not (c == tr.columnCount() - 1 and hh.stretchLastSection()))
                if item.text(c).strip() and (item.text(c) in heads or fixed) and not tr.isColumnHidden(c):
                    seen += item.text(c) in heads
                    need = hh.fontMetrics().horizontalAdvance(item.text(c)) +                         2 * hh.style().pixelMetric(QStyle.PM_HeaderMargin, None, hh)
                    ok("%s: the column %r shows all of its name (%d of %d px)"
                       % (name, item.text(c), need, hh.sectionSize(c)), need <= hh.sectionSize(c))
    # Kits and Stadiums show their table only with a server module, which the fake game has not: Slot is
    # seen in the UI test through the exe
    ok("the column On was seen (%d)" % seen, seen >= 4)
    w.open_page("Overview")
    settle(qa, 0.2)
    last = [l for l in w.stack.currentWidget().findChildren(QLabel) if l.text() == i18n._("Last changes")]
    need = last[0].fontMetrics().horizontalAdvance(last[0].text()) if last else 0
    ok("Home: %r shows all of its text (%d of %d px)" % (last and last[0].text(), need, last and last[0].width()),
       last and need <= last[0].width())
    w.resize(1360, 820)
    settle(qa, 0.2)
    # the state boxes when all is well (the fake game has neither): Sider with its version, the
    # modules all on ("%s OK" and "%d / %d ON" were filled in with no _( ))
    from modstudio import checks
    A.file_version = lambda path: "7.3.3"
    checks.modules_state = lambda g: {"missing": [], "changed": [], "off": [], "left_off": ["fl26x.lua"], "total": 36}
    put(os.path.join(w.game.sider_dir, "sider.exe"), b"MZ")
    w.update_header()
    settle(qa, 0.1)
    sv, mv = w.stats["sider"], w.stats["modules"]
    ok("the state boxes show Sider's version and the modules: %r, %r" % (sv.text(), mv.text()),
       "7.3.3" in sv.text() and re.search(r"35\s*/\s*36", mv.text()))
    for s in (sv, mv):
        need = s.val.fontMetrics().horizontalAdvance(s.text())
        ok("%r fits its box at 1360 x 820 (%d of %d px)" % (s.text(), need, s.val.width()), need <= s.val.width())
    for kind, text in texts_of(w):
        judge.look("state boxes", kind, text)
    # B74: Import your world with a zip of a world whose name one built on this PC has: the warning
    # in the panel before Install (translated), that part unticked, Install off
    from modstudio import installer as I
    put(os.path.join(w.game.livecpk_dir, "_FL26Mine", "fl26world.txt"), "world _FL26Mine\r\n")
    w.open_page("Install")
    page = w.pages["Install"]
    p = I.Part("world", os.path.join(T, "zip", "_FL26Mine"), "_FL26Mine")
    p.blocked = I.world_in_the_way(w.game, p.name)
    if p.blocked:
        p.warnings.insert(0, I.world_there(p.name))
    page.src = os.path.join(T, "_FL26Mine.zip")
    page.result.show()
    page.looked([p])
    settle(qa, 0.1)
    it = page.tree.topLevelItem(0)
    from PySide6.QtCore import Qt
    ok("Import your world: the world in the way is said before Install: %r" % it.text(5)[:70],
       p.blocked and "_FL26Mine" in it.text(5) and not judge.why(it.text(5)))
    ok("that part is unticked and Install is off", it.checkState(0) == Qt.Unchecked and not page.go.isEnabled())
    for kind, text in texts_of(w):
        judge.look("Install (world in the way)", kind, text)
    # every menu's actions: the top bar's, the bar's sections, the pages'
    for m in w.findChildren(QMenu):
        for a in m.actions():
            if a.text():
                judge.look("menu", "QAction", a.text())
    ok("pages opened: %d" % len(names), len(names) > 20)
    for (kind, t), (where, why) in sorted(judge.bad.items(), key=lambda e: e[1][0]):
        print("  ENGLISH  %-26s %-12s %r: %s" % (where, kind, t, why))
    ok("no English text left on the %s screens (%d found)" % (LANG, len(judge.bad)), not judge.bad)
    w._run_timer.stop()
    w.close()
    settle(qa, 0.2)
    lines_checks(judge)


def lines_checks(judge):
    """the builder's lines and the messages filled in before they reach a page"""
    import leaguebuilder as B
    import fl26world, uefakey
    from modstudio import i18n, installer as I, worlds as WL
    from modstudio.i18n import tr
    i18n.set_language(LANG)
    left = re.compile(r"\b(?:a league of the game|qualifying|clubs from|down|none|no Copa|in this world|"
                      r"cup winner|the winners|and the|the world's|gives way|\d+(?:st|nd|rd|th)\b|"
                      r"South American places)\b")
    sud = {"number": 9, "entry": [(r, p) for r in fl26world.FILL_NAMES for p in (6, 7)]}
    own = [("Liga X", 1, 3, 0), ("Liga X", 2, 4, 0), ("", 0, 9, "Liga X"), ("Liga X", 5, 9, 0)]
    for cups in ([sud], []):
        lines = B.samerica_lines(own, {"Liga X": "Liga X"}, cups)
        out = [tr(l) for l in lines]
        rest = [l for l in out if left.search(l.replace("Liga X", ""))]
        for l in rest:
            print("  ENGLISH  South American places: %r" % l)
        ok("South American places (%s Sudamericana): every line in %s" % ("with" if cups else "no", LANG),
           not rest and all(len(a) - len(a.lstrip(" ")) == len(b) - len(b.lstrip(" ")) for a, b in zip(out, lines)))
    Ls = [{"id": i, "name": "League %d" % i, "clubs": 10, "cup": True} for i in range(33)]
    tiers = {}
    _pl, _seed, notes = uefakey.assign(Ls, tiers)
    Ls.append({"id": 99, "name": "League 99", "clubs": 2, "cup": False})
    tiers[99] = []
    out = [tr(l) for l in uefakey.table(Ls, tiers) + notes]
    # the abbreviations each language has its own of (Portuguese says Champions League too, Croatian
    # EL is Europska liga; "play-off" is Spanish and Portuguese as well)
    abbr = {"es": "CL|EL|ECL", "fr": "CL|EL|ECL|play-off", "hr": "CL|ECL|play-off"}.get(LANG)
    eng = re.compile((r"(?:: |; )(?:%s)\b|" % abbr if abbr else "") +
                     r"\bqual\. round\b|\bcup\b|\bno place\b|\brank \d+ --|\bplaces for\b|\bleft over\b|"
                     r"\bno club left\b|\bqualifying\b")
    rest = [l for l in out if eng.search(l)]
    for l in rest:
        print("  ENGLISH  UEFA ranking: %r" % l)
    ok("UEFA ranking: the table and its notes in %s (%d lines)" % (LANG, len(out)), not rest)
    english = {"uefakey": uefakey.table(Ls[:2], tiers), "samerica": B.samerica_lines(own, {}, [sud])}
    i18n.set_language("en")
    ok("in English (the command line) the lines are as before",
       uefakey.table(Ls[:2], tiers) == english["uefakey"] and tr(english["samerica"][1]) == english["samerica"][1])
    i18n.set_language(LANG)

    class G:
        livecpk_dir = os.path.join(T, "game", "SiderAddons", "livecpk")
        content_dir = os.path.join(T, "game", "SiderAddons", "content")
        sider_dir = os.path.join(T, "game", "SiderAddons")
        ini_path = os.path.join(sider_dir, "sider.ini")
    for name, old in (("_FL26" + "x" * 80, None), ("_FL26Live", None), ("_FL26Old", "_FL26Live")):
        why = WL.check_name(G, name, old)
        ok("check_name(%s...): %r translated" % (name[:12], why[:50]), why and not judge.why(why))
    from modstudio.project import Project
    p = Project.__new__(Project)
    p.recipe = {"leagues": [{"name": "A", "clubs": B.CLUBS_MIN}, {"name": "B", "clubs": 10}]}
    why = Project.move_club(p, "A", 0, "B")
    ok("move_club: %r translated" % why, why and not judge.why(why))
    put(os.path.join(G.livecpk_dir, "_FL26Mine", "fl26world.txt"), "world _FL26Mine\r\n")
    ok("a world built on this PC is in the way of a world zip of its name",
       I.world_in_the_way(G, "_FL26Mine") and not I.world_in_the_way(G, "_FL26Nobody"))
    why = I.world_there("_FL26Mine")
    ok("Install's world-in-the-way message: %r translated" % why[:60], "_FL26Mine" in why and not judge.why(why))
    i18n.set_language("en")


def main():
    if len(sys.argv) < 2:                       # no language given: all four, each in a process of its own
        shutil.rmtree(T, ignore_errors=True)
        import subprocess
        bad = [c for c in ("es", "fr", "pt", "hr")
               if subprocess.call([sys.executable, os.path.abspath(__file__), c], env=ENV0) != 0]
        assert not bad, "test_ui_language failed for: %s" % ", ".join(bad)
        print("test_ui_language: ok (es, fr, pt, hr)")
        return
    try:
        run()
    finally:
        shutil.rmtree(T, ignore_errors=True)
    print("test_ui_language: ok (%d)" % N)


if __name__ == "__main__":
    main()
