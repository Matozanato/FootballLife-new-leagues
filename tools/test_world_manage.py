r"""python tools/test_world_manage.py

0.2.4 (mato 15.10.): the worlds on Content folders.
  - the world in the game is green there (row background, IN THE GAME NOW);
  - Delete world puts all of it in SiderAddons\ModStudio\backups\worlds\<world>\<date> deleted,
    Restore points puts it back byte for byte; the live world is refused; 3 kept per world;
  - Rename world changes every place the name is written, and Switch on (Build's last step)
    finds the world under its new name; Restore points renames it back;
  - from now on Build / Switch on keep their copies in ModStudio\backups (Restore points), none
    next to the maps (map.txt.before-builder / .prev), and Put Sider back as before Mod Studio
    still finds the old copies next to the files as well as the new ones.

Fake game folders in a temp folder, QT_QPA_PLATFORM=offscreen. No game.
"""
import json, os, shutil, sys, tempfile, time, types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.pop("FL26_DIR", None)

from modstudio import backups, factory, installer as I, worlds as WL, theme
from modstudio.game import Game

N = 0
TAG = I.OUR_LINE
OFF = WL.OFF
QUIET = lambda *a, **k: None


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def put(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data if isinstance(data, bytes) else data.encode("utf-8"))


def read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def tree(sd):
    """every file and folder under SiderAddons (ModStudio's own folder left out), with its bytes"""
    out = {}
    for top, dirs, files in os.walk(sd):
        if top == sd:
            dirs[:] = [d for d in dirs if d != backups.HOME]
        for f in files:
            p = os.path.join(top, f)
            with open(p, "rb") as fh:
                out[os.path.relpath(p, sd)] = fh.read()
        for d in dirs:
            out[os.path.relpath(os.path.join(top, d), sd) + os.sep] = b""
    return out


def diff(a, b):
    return sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))


def strays(sd):
    """copies next to files, the way Build and Switch on kept them before 0.2.4"""
    out = []
    for top, dirs, files in os.walk(sd):
        if top == sd:
            dirs[:] = [d for d in dirs if d != backups.HOME]
        out += [os.path.join(top, f) for f in files if f.endswith((".before-builder", ".prev"))]
        out += [os.path.join(top, d) for d in dirs if d.startswith("before-builder-")]
    return out


def make_game(t):
    """a game folder with Sider, two worlds (_FL26Live switched on, _FL26Old off), their kits and
    scoreboards, a ready-world install record, a profile, stadium lines and the CommonLib line"""
    g = os.path.join(t, "game")
    put(os.path.join(g, "FL_2026.exe"), b"MZ")
    sd = os.path.join(g, "SiderAddons")
    put(os.path.join(sd, "sider.ini"),
        'lua.enabled = 1\r\ncpk.root = ".\\livecpk\\UserMod"\r\n#cpk.root = ".\\livecpk\\_FL26Old"\r\n'
        'cpk.root = ".\\livecpk\\_FL26Live"   ; my world\r\nlua.module = "camera.lua"\r\n')
    put(os.path.join(sd, "livecpk", "UserMod", "a.txt"), "their mod")
    for w in ("_FL26Live", "_FL26Old"):
        d = os.path.join(sd, "livecpk", w)
        put(os.path.join(d, "fl26world.txt"), "# a League Builder world\r\nworld %s\r\nleague 17 HNL\r\n" % w)
        put(os.path.join(d, "leaguebuilder-plan.json"), json.dumps({"world": w, "leagues": [
            {"name": "HNL", "teams": [701, 702], "club_names": ["Dinamo", "Hajduk"],
             "kit_folders": [os.path.join(t, "nowhere", "Dinamo"), os.path.join(t, "nowhere", "Hajduk")],
             "rid": 300, "scoreboard": os.path.join(t, "nowhere", "HNL")}]}, indent=1))
        put(os.path.join(d, "fl26playerids.json"), '{\n "world": "%s",\n "ids": [1, 2]\n}' % w)
        put(os.path.join(d, "common", "etc", "pesdb", "Team.bin"), bytes(range(256)) * 4)
        put(os.path.join(d, "modules", "fl26regions.lua"), "-- regions of %s\n" % w)
        for c in ("Dinamo", "Hajduk"):
            put(os.path.join(sd, "content", "kit-server", w, "HNL", c, "p1", "config.txt"), "kit of " + w)
        put(os.path.join(sd, "content", "scoreboard-server", w, "HNL", "bg.dds"), b"\x00DDS " + w.encode())
    put(os.path.join(sd, "content", "kit-server", "_FL26Old", "_kits", "Pack", "X", "p1", "config.txt"), "lent")
    put(os.path.join(sd, "content", "kit-server", "Theirs", "p1", "config.txt"), "their kit")
    # the maps: lines of the live world (Switch on), a line of the old world carried from its zip,
    # one of the player's switched off for the live world's club, and the old world's from long ago
    put(os.path.join(sd, "content", "kit-server", "map.txt"),
        '1, "Theirs"\r\n'
        '#701, "Theirs"' + OFF + '\r\n'
        '701, "_FL26Live\\HNL\\Dinamo"   ' + TAG + ' HNL/0\r\n'
        '702, "_FL26Live\\HNL\\Hajduk"   ' + TAG + ' HNL/1\r\n'
        '#703, "Theirs"' + OFF + '\r\n'
        '703, "_FL26Old\\_kits\\Pack\\X"   ' + TAG + ' kit of Pack\r\n'
        '704, "_FL26Old\\HNL\\Dinamo"\r\n')
    # no newline at the end, a header and a line Import your world added, and a line it took out
    put(os.path.join(sd, "content", "scoreboard-server", "map_competitions.txt"),
        "17, Theirs\n"
        "# ---- added by FL26 Mod Studio: _FL26Old\n"
        "300, _FL26Old\\HNL   " + TAG + " HNL")
    put(os.path.join(sd, "content", "stadium-server", "map_teams.txt"),
        "701, 009, Maksimir, Maksimir   " + TAG + " Dinamo\n#702, 010, Poljud, Poljud" + OFF + "\n"
        "702, 010, Poljud2, Poljud2   " + TAG + " Hajduk\n")
    put(os.path.join(sd, "modules", "fl26world.txt"), read(os.path.join(sd, "livecpk", "_FL26Live", "fl26world.txt")))
    put(os.path.join(sd, "modules", "camera.lua"), "camera")
    put(os.path.join(sd, "modules", "lib", "CommonLib.lua"),
        "local playable_league_comp_ids = {\n  17, -- FL26 world _FL26Live (Mod Studio, Switch on)\n  1,\n}\n")
    I._save(sd, [
        {"name": "nice ball", "time": "20261014-200000", "parts": [], "created": [], "replaced": [], "ini": [],
         "map_added": {}, "map_removed": {}},
        {"name": "_FL26Old", "time": "20261014-210000", "world": "_FL26Old", "parts": [["world", "_FL26Old"]],
         "created": [os.path.join("livecpk", "_FL26Old", "fl26world.txt"),
                     os.path.join("content", "kit-server", "_FL26Old", "_kits", "Pack", "X", "p1", "config.txt")],
         "replaced": [], "ini": [["cpk.root", ".\\livecpk\\_FL26Old"]],
         "map_added": {os.path.join("content", "scoreboard-server", "map_competitions.txt"):
                       ["# ---- added by FL26 Mod Studio: _FL26Old", "300, _FL26Old\\HNL   " + TAG + " HNL"]},
         "map_removed": {os.path.join("content", "kit-server", "map.txt"): ['9, "Gone"']}}])
    put(os.path.join(sd, "ModStudio", "profiles", "mine.json"), json.dumps(
        {"name": "mine", "cpk.root": [[".\\livecpk\\UserMod", True], [".\\livecpk\\_FL26Live", True]]}, indent=1))
    return Game(g)


# ---- the backups of Build / Switch on, and Put Sider back as before Mod Studio -------------------
def from_now_on(t):
    import leaguebuilder as B
    import lbstadiums, lbservers
    game = make_game(os.path.join(t, "fromnow"))
    sd = game.sider_dir
    # an install from before 0.2.4: a copy next to the map and in modules\before-builder-1
    put(os.path.join(sd, "content", "kit-server", "map.txt.before-builder"), '1, "Theirs"\r\n')
    os.makedirs(os.path.join(sd, "modules", "before-builder-1"))
    shutil.copy2(os.path.join(sd, "modules", "camera.lua"), os.path.join(sd, "modules", "before-builder-1", "camera.lua"))
    old_style = sorted(strays(sd))
    time.sleep(1.1)                        # those copies are older than anything 0.2.4 keeps (factory takes the oldest)
    first = {r: read(os.path.join(sd, r)) for r in (os.path.join("content", "scoreboard-server", "map_competitions.txt"),
                                                   os.path.join("content", "stadium-server", "map_teams.txt"),
                                                   os.path.join("modules", "fl26world.txt"))}
    B.switch_on("_FL26Old", game.folder, log=QUIET)
    ok("switch on: the world is the one in the game", WL.live(game) == ["_FL26Old"])
    ok("switch on: no new copy next to a file (only the 2 of the old install)", sorted(strays(sd)) == old_style)
    rows = backups.load(sd)
    for rel in first:
        ok("switch on: a restore point of %s, marked as the first" % rel,
           any(r["file"].lower() == rel.lower() and r.get("before") for r in rows))
    ok("switch on: the map with an old .before-builder copy gets no second 'first' mark",
       not any(r["file"].lower() == os.path.join("content", "kit-server", "map.txt").lower() and r.get("before")
               for r in rows))
    time.sleep(1.1)
    B.switch_on("_FL26Live", game.folder, log=QUIET)
    B.switch_on("_FL26Old", game.folder, log=QUIET)
    rows = backups.load(sd)
    ok("switch on 3x: one first copy of each file stays marked",
       sum(1 for r in rows if r.get("before") and r["file"].lower() == os.path.join("modules", "fl26world.txt").lower()) == 1)
    backups.keep(sd, os.path.join("modules", "fl26world.txt"), 1)
    ok("keep(): the marked first copy is never cleaned up",
       any(r.get("before") for r in backups.history(sd, os.path.join("modules", "fl26world.txt"))))
    ok("switch on: still nothing next to the files", sorted(strays(sd)) == old_style)
    # Put Sider back: the old copies next to the files and the new ones in ModStudio\backups
    plan = factory.plan(game)
    folder = factory.reset(game)
    ok("factory reset: the map with an old-style copy is as before Mod Studio",
       read(os.path.join(sd, "content", "kit-server", "map.txt")) == '1, "Theirs"\r\n')
    ok("factory reset: the module in modules\\before-builder-1 is back", read(os.path.join(sd, "modules", "camera.lua")) == "camera")
    for rel, text in first.items():
        if rel.startswith("modules"):
            ok("factory reset: %s (ours) is taken out" % rel, not os.path.exists(os.path.join(sd, rel)))
        else:
            ok("factory reset: %s is back from its new-style copy" % rel, read(os.path.join(sd, rel)) == text)
    ok("factory reset: no old-style copy left", strays(sd) == [])
    ok("factory reset: the plan named both worlds", sorted(plan["worlds"]) == ["_FL26Live", "_FL26Old"])
    factory.undo(sd, folder)
    ok("undo of the reset: the old-style copies are back", sorted(strays(sd)) == old_style)


# ---- delete and put back --------------------------------------------------------------------------
def delete_restore(t):
    game = make_game(os.path.join(t, "delete"))
    sd = game.sider_dir
    before = tree(sd)
    ok("live(): the world switched on", WL.live(game) == ["_FL26Live"])
    try:
        WL.delete(game, "_FL26Live")
        refused = False
    except WL.WorldError:
        refused = True
    ok("delete: the world in the game is refused", refused)
    ok("delete refused: nothing changed", diff(tree(sd), before) == [])

    folder, info = WL.delete(game, "_FL26Old", QUIET)
    ok("delete: the backup is in ModStudio\\backups\\worlds\\_FL26Old\\<date> deleted",
       os.path.dirname(folder) == os.path.join(sd, "ModStudio", "backups", "worlds", "_FL26Old")
       and folder.endswith(" deleted"))
    for rel in (os.path.join("livecpk", "_FL26Old"), os.path.join("content", "kit-server", "_FL26Old"),
                os.path.join("content", "scoreboard-server", "_FL26Old")):
        ok("delete: %s moved into the backup" % rel,
           not os.path.exists(os.path.join(sd, rel)) and os.path.isdir(os.path.join(folder, "files", rel)))
    ini = read(game.ini_path)
    ok("delete: its cpk.root line is out, the others as they were",
       "_FL26Old" not in ini and ini == before["sider.ini"].decode().replace('#cpk.root = ".\\livecpk\\_FL26Old"\r\n', ""))
    km = read(os.path.join(sd, "content", "kit-server", "map.txt"))
    ok("delete: its kit lines are out (Build's and the carried one)", "_FL26Old" not in km)
    ok("delete: the player's line switched off for it is back on", '\r\n703, "Theirs"\r\n' in km)
    ok("delete: the one switched off for the live world stays off", '#701, "Theirs"' + OFF in km)
    ok("delete: the line Import your world took out comes back", km.endswith('9, "Gone"\r\n'))
    bm = read(os.path.join(sd, "content", "scoreboard-server", "map_competitions.txt"))
    ok("delete: its scoreboard line and header are out", bm == "17, Theirs\n")
    ok("delete: the live world's lines are untouched", '701, "_FL26Live\\HNL\\Dinamo"' in km
       and read(os.path.join(sd, "content", "stadium-server", "map_teams.txt")) == before[
           os.path.join("content", "stadium-server", "map_teams.txt")].decode())
    ok("delete: its install record is out, the other stays", [r["name"] for r in I.records(sd)] == ["nice ball"])
    ok("delete: the world in the game is untouched",
       all(before[k] == v for k, v in tree(sd).items() if "_FL26Live" in k))
    ok("delete: the backup is listed for Restore points", [f for f, _i in WL.backups_of(sd)] == [folder])

    WL.restore(game, folder, QUIET)
    ok("put back: SiderAddons byte for byte as before the delete", diff(tree(sd), before) == [])
    ok("put back: the backup is not listed again", WL.backups_of(sd) == [])

    # the world the modules read (switched off first): its world file, stadium lines and CommonLib line too
    ini = read(game.ini_path).replace('cpk.root = ".\\livecpk\\_FL26Live"', '#cpk.root = ".\\livecpk\\_FL26Live"')
    put(game.ini_path, ini)
    before2 = tree(sd)
    folder2, info2 = WL.delete(game, "_FL26Live", QUIET)
    ok("delete (the modules' world): modules\\fl26world.txt into the backup",
       not os.path.exists(os.path.join(sd, "modules", "fl26world.txt"))
       and os.path.isfile(os.path.join(folder2, "files", "modules", "fl26world.txt")))
    st = read(os.path.join(sd, "content", "stadium-server", "map_teams.txt"))
    ok("delete (the modules' world): its home stadium lines out, the player's back on",
       st == "702, 010, Poljud, Poljud\n")
    ok("delete (the modules' world): its CommonLib line is out",
       "_FL26Live" not in read(os.path.join(sd, "modules", "lib", "CommonLib.lua")))
    WL.restore(game, folder2, QUIET)
    ok("put back (the modules' world): byte for byte", diff(tree(sd), before2) == [])

    # 3 backups of a world are kept
    for k in range(4):
        f, _i = WL.delete(game, "_FL26Old", QUIET)
        if k < 3:
            WL.restore(game, f, QUIET)
    left = os.listdir(os.path.join(sd, "ModStudio", "backups", "worlds", "_FL26Old"))
    ok("prune: the newest %d backups of a world are kept (%d)" % (WL.KEEP, len(left)), len(left) == WL.KEEP)
    ok("prune: the newest (the one not put back yet) is among them", os.path.basename(f) in left)
    WL.restore(game, f, QUIET)
    ok("put back after 5 deletes: still byte for byte", diff(tree(sd), before2) == [])


# ---- rename -------------------------------------------------------------------------------------
def rename(t):
    import leaguebuilder as B
    game = make_game(os.path.join(t, "rename"))
    sd = game.sider_dir
    before = tree(sd)
    ok("check_name: must start with _FL26", WL.check_name(game, "MyWorld") != "")
    ok("check_name: no spaces", WL.check_name(game, "_FL26 My") != "")
    ok("check_name: not the name of another world", WL.check_name(game, "_FL26old", "_FL26Live") != "")
    ok("check_name: a good name", WL.check_name(game, "_FL26New-1", "_FL26Live") == "")
    ini0 = read(game.ini_path).split("\r\n")
    folder, info = WL.rename(game, "_FL26Live", "_FL26New", QUIET)
    ini = read(game.ini_path).split("\r\n")
    ok("rename: the cpk.root line in the same place, on, with its note",
       ini[3] == 'cpk.root = ".\\livecpk\\_FL26New"   ; my world' and len(ini) == len(ini0)
       and [l for i, l in enumerate(ini) if i != 3] == [l for i, l in enumerate(ini0) if i != 3])
    ok("rename: live() says the new name", WL.live(game) == ["_FL26New"])
    for rel in (os.path.join("livecpk", "_FL26New"), os.path.join("content", "kit-server", "_FL26New"),
                os.path.join("content", "scoreboard-server", "_FL26New")):
        ok("rename: %s is there" % rel, os.path.isdir(os.path.join(sd, rel))
           and not os.path.exists(os.path.join(sd, rel.replace("_FL26New", "_FL26Live"))))
    km = read(os.path.join(sd, "content", "kit-server", "map.txt"))
    ok("rename: the kit lines point at the new folder",
       '701, "_FL26New\\HNL\\Dinamo"' in km and "_FL26Live" not in km and "_FL26Old\\_kits" in km)
    w = os.path.join(sd, "livecpk", "_FL26New")
    ok("rename: the world file's world line", "\r\nworld _FL26New\r\n" in read(os.path.join(w, "fl26world.txt")))
    ok("rename: the modules' world file", "\r\nworld _FL26New\r\n" in read(os.path.join(sd, "modules", "fl26world.txt")))
    ok("rename: leaguebuilder-plan.json", json.load(open(os.path.join(w, "leaguebuilder-plan.json")))["world"] == "_FL26New")
    ok("rename: fl26playerids.json", json.load(open(os.path.join(w, "fl26playerids.json")))["world"] == "_FL26New")
    ok("rename: CommonLib line", "-- FL26 world _FL26New (Mod Studio" in read(os.path.join(sd, "modules", "lib", "CommonLib.lua")))
    prof = json.load(open(os.path.join(sd, "ModStudio", "profiles", "mine.json")))
    ok("rename: the profile", prof["cpk.root"][1] == [".\\livecpk\\_FL26New", True])
    ok("rename: the world's tables not touched",
       open(os.path.join(w, "common", "etc", "pesdb", "Team.bin"), "rb").read() == bytes(range(256)) * 4)
    ok("rename: the backup folder keeps the small files",
       os.path.isfile(os.path.join(folder, "before", "sider.ini"))
       and os.path.isfile(os.path.join(folder, "before", "livecpk", "_FL26Live", "fl26world.txt")))
    ok("rename: nothing else in SiderAddons changed", all(
        before[k] == v for k, v in tree(sd).items()
        if "_FL26" not in k and k not in ("sider.ini", os.path.join("content", "kit-server", "map.txt"),
                                          os.path.join("modules", "fl26world.txt"),
                                          os.path.join("modules", "lib", "CommonLib.lua"))))
    # Build's last step on the renamed world
    B.switch_on("_FL26New", game.folder, log=QUIET)
    km = read(os.path.join(sd, "content", "kit-server", "map.txt"))
    # (701 keeps the player's own line, switched back on: lbservers' rule, pepponeee98 14.10.)
    ok("switch on after rename: finds the world, its kit line under the new name",
       '702, "_FL26New\\HNL\\Hajduk"   ' + TAG in km and "_FL26Live" not in km)
    bm = read(os.path.join(sd, "content", "scoreboard-server", "map_competitions.txt"))
    ok("switch on after rename: scoreboard line under the new name", "300, _FL26New\\HNL" in bm)
    ok("switch on after rename: the modules' world file", "world _FL26New" in read(os.path.join(sd, "modules", "fl26world.txt")))
    ok("switch on after rename: no copies next to the maps", strays(sd) == [])
    # Old and New: rename the other one too, then put the first rename back
    WL.restore(game, folder, QUIET)
    ok("rename put back: _FL26Live again, switched on", WL.live(game) == ["_FL26Live"]
       and os.path.isdir(os.path.join(sd, "content", "kit-server", "_FL26Live")))
    ok("rename put back: the world file says _FL26Live",
       "\r\nworld _FL26Live\r\n" in read(os.path.join(sd, "livecpk", "_FL26Live", "fl26world.txt")))
    ok("rename put back: no _FL26New left anywhere",
       not any("_FL26New" in k for k in tree(sd)) and "_FL26New" not in read(game.ini_path))
    # the recipe copy (recipes\<world>.json)
    rd = os.path.join(t, "recipes")
    put(os.path.join(rd, "_FL26Live.json"), json.dumps({"world": "_FL26Live", "leagues": []}))
    got = WL.rename_recipe_copy(rd, "_FL26Live", "_FL26New")
    ok("recipe copy renamed with its world key", got == os.path.join(rd, "_FL26New.json")
       and json.load(open(got))["world"] == "_FL26New" and not os.path.exists(os.path.join(rd, "_FL26Live.json")))


# ---- the pages ------------------------------------------------------------------------------------
def wait_rename(qa, page, secs=120):
    """Rename world runs in the background (B66): the window's events until it is over"""
    t0 = time.time()
    while getattr(page, "renaming", None) and time.time() - t0 < secs:
        qa.processEvents()
        time.sleep(0.01)
    qa.processEvents()
    assert not getattr(page, "renaming", None), "the rename did not end in %d s" % secs


class FakeProject:
    def __init__(self, d, world):
        self.d, self.recipe, self.path, self.dirty = d, {"world": world, "leagues": []}, None, False
        self.changed = types.SimpleNamespace(emit=lambda: None)

    def copies_dir(self):
        return self.d

    def keep_copy(self):
        os.makedirs(self.d, exist_ok=True)
        p = os.path.join(self.d, self.recipe["world"] + ".json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.recipe, f)
        return p

    def drop_names(self):
        pass

    def touch(self):
        self.dirty = True


def pages(t):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QColor
    qa = QApplication.instance() or QApplication([])
    theme.apply(qa)
    from modstudio.app import Bus
    from modstudio.siderini import SiderIni
    from modstudio import roots as R
    from modstudio.pages import roots as RP, restore as RS
    game = make_game(os.path.join(t, "pages"))
    game.running = lambda: (False, False)
    sd = game.sider_dir
    rd = os.path.join(t, "pages-recipes")
    app = types.SimpleNamespace(game=game, bus=Bus(), settings={}, project=FakeProject(rd, "_FL26Live"))
    app.ini = lambda: SiderIni.load(game.ini_path)
    app.busy = QUIET
    app.status = QUIET
    app.save_settings = QUIET
    app.open_page = QUIET

    def save_ini(ini, reason):
        ini.save(reason=reason)
        app.bus.ini_changed.emit()
    app.save_ini = save_ini
    asked, errors = [], []
    RP.ask = lambda parent, title, text: asked.append(text) or True
    RP.error = lambda parent, title, text: errors.append(text)
    RS.ask = RP.ask
    RS.error = RP.error
    page = RP.Roots(app)

    def rescan():
        page.idx = R.scan(sd, app.ini())
        page.load()
    page.rescan = rescan
    page.resize(1400, 600)
    page.show()
    rescan()
    page.show_worlds.setChecked(True)

    def row(world):
        for i in range(page.tree.topLevelItemCount()):
            it = page.tree.topLevelItem(i)
            if it.text(2).endswith("\\" + world):
                return it
        return None

    it = row("_FL26Live")
    ok("Content folders: the live world's row is shown with Show the worlds", it is not None and not it.isHidden())
    ok("Content folders: its background is the theme's green (OK_BG) in every column",
       all(it.background(c).color().name().lower() == QColor(theme.OK_BG).name().lower()
           for c in range(page.tree.columnCount())))
    ok("Content folders: its name in the theme's green, bold", it.foreground(2).color().name().lower()
       == QColor(theme.GOOD).name().lower() and it.font(2).bold())
    ok("Content folders: IN THE GAME NOW in the Note column, with the player's note",
       it.text(7).startswith("● IN THE GAME NOW") and "my world" in it.text(7))
    old = row("_FL26Old")
    ok("Content folders: the world switched off is not green",
       old.background(2).style() == Qt.NoBrush and "IN THE GAME NOW" not in old.text(7))
    ok("Content folders: a mod folder is not green", row("UserMod").background(2).style() == Qt.NoBrush)
    # what is on screen: the live row's pixels are green
    qa.processEvents()
    page.tree.clearSelection()
    page.tree.setCurrentItem(None)
    qa.processEvents()
    img = page.tree.viewport().grab().toImage()
    r = page.tree.visualItemRect(it)
    px = QColor(img.pixel(r.left() + 600, r.center().y()))
    want = QColor(theme.OK_BG)
    ok("Content folders: on screen the live row is green (%s)" % px.name(),
       abs(px.red() - want.red()) < 12 and abs(px.green() - want.green()) < 12 and abs(px.blue() - want.blue()) < 12)

    # Delete world on the live one: refused, explained
    page.tree.setCurrentItem(it)
    ok("Content folders: Rename / Delete world shown for a world row",
       page.b_wdel.isVisibleTo(page) and page.b_wren.isVisibleTo(page))
    before = tree(sd)
    page.delete_world()
    ok("Delete world on the live world: refused with an explanation",
       errors and "world in the game now" in errors[-1] and diff(tree(sd), before) == [])
    page.tree.setCurrentItem(row("UserMod"))
    ok("Content folders: no world buttons for a mod folder", not page.b_wdel.isVisibleTo(page))

    # Delete world on the one switched off: asked in plain words, then all of it in the backup
    page.tree.setCurrentItem(row("_FL26Old"))
    asked.clear()
    page.delete_world()
    ok("Delete world: asks first, names the world, where it is kept and that the recipe stays",
       asked and "_FL26Old" in asked[-1] and "backups" in asked[-1] and "Restore points" in asked[-1]
       and "not deleted" in asked[-1])
    ok("Delete world: the world is out", not os.path.exists(os.path.join(sd, "livecpk", "_FL26Old"))
       and row("_FL26Old") is None)
    # "Delete from disk..." on a world goes the same safe way
    page.tree.setCurrentItem(it := row("_FL26Live"))
    n = len(errors)
    page.delete_folder()
    ok("Delete from disk on a world row: the safe Delete world, refused for the live one",
       len(errors) == n + 1 and os.path.isdir(os.path.join(sd, "livecpk", "_FL26Live")))

    # Restore points lists it and puts it back
    rp = RS.Restore(app)
    rp.refresh()
    rows = [rp.tree.topLevelItem(i) for i in range(rp.tree.topLevelItemCount())]
    wrows = [x for x in rows if "world_backup" in (x.data(0, RS.ROW) or {})]
    ok("Restore points: one row for the deleted world", len(wrows) == 1 and wrows[0].text(1) == "livecpk\\_FL26Old")
    ok("Restore points: the Worlds choice in the list", rp.only.findData(RS.WORLDS) >= 0)
    rp.tree.setCurrentItem(wrows[0])
    ok("Restore points: says what is in the copy", "_FL26Old was deleted" in rp.diff.toPlainText())
    rp.restore()
    ok("Restore points: Put this copy back brings the world back byte for byte", diff(tree(sd), before) == [])

    # Rename world: the name asked, the old one gone everywhere, the recipe follows
    from PySide6 import QtWidgets
    QtWidgets.QInputDialog.getText = staticmethod(lambda *a, **k: ("_FL26Renamed", True))
    rescan()
    page.tree.setCurrentItem(row("_FL26Live"))
    asked.clear()
    page.rename_world()
    wait_rename(qa, page)                     # it runs in the background (B66)
    ok("Rename world: tells the player a career keeps working", asked and "career" in asked[-1])
    ok("Rename world: the world is there under its new name, still green",
       row("_FL26Renamed") is not None and row("_FL26Renamed").data(0, Qt.UserRole + 1) == "live")
    ok("Rename world: the open world's name follows", app.project.recipe["world"] == "_FL26Renamed"
       and json.load(open(os.path.join(rd, "_FL26Renamed.json")))["world"] == "_FL26Renamed")
    QtWidgets.QInputDialog.getText = staticmethod(lambda *a, **k: ("bad name", True))
    page.tree.setCurrentItem(row("_FL26Renamed"))
    page.rename_world()
    ok("Rename world: a name without _FL26 is refused", errors and "_FL26" in errors[-1]
       and row("_FL26Renamed") is not None)
    rp.refresh()
    wrows = [rp.tree.topLevelItem(i) for i in range(rp.tree.topLevelItemCount())]
    wrows = [x for x in wrows if "world_backup" in (x.data(0, RS.ROW) or {})]
    ok("Restore points: the rename is listed", len(wrows) == 1 and "renamed to _FL26Renamed" in wrows[0].text(2))
    rp.tree.setCurrentItem(wrows[0])
    rp.restore()
    ok("Restore points: renamed back, the open world's name too",
       os.path.isdir(os.path.join(sd, "livecpk", "_FL26Live")) and app.project.recipe["world"] == "_FL26Live")
    page.hide()


def main():
    t = tempfile.mkdtemp(prefix="worldmanage-")
    try:
        from_now_on(t)
        delete_restore(t)
        rename(t)
        pages(t)
    finally:
        shutil.rmtree(t, ignore_errors=True)
    print("test_world_manage: ok (%d)" % N)


if __name__ == "__main__":
    main()
