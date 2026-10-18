r"""python tools/test_save_swap.py

0.2.4 (mato 15.10., from a tester's .bat): every world switch switches the game's save folder,
Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save, so each world keeps its own Master
League careers (modstudio/saves.py):
  - A -> B -> A: save -> save_A, an empty save for B (only the settings files copied in), and back:
    A's files byte for byte, B's kept in save_B, the newest settings in save;
  - the first swap ever copies the whole save folder into SiderAddons\ModStudio\backups\saves first,
    and Restore points lists that copy;
  - refused, nothing renamed: the game running, save_<old> there already, save_<new> a file;
    a second rename that fails puts the first one back;
  - Rename world: save_<old> -> save_<new> (and a name taken is refused);
  - the setting off (Settings) and a window without a screen without FL26_SAVE_ROOT: no change;
  - after a reset of Sider (no world in the game, save still the old world's) putting that world
    back swaps nothing;
  - Content folders: Apply with another world ticked swaps, says it first, tells the first time,
    and with the game running writes nothing; Delete world says the careers stay.

A fake KONAMI folder (FL26_SAVE_ROOT) and fake game folders in a temp folder, QT_QPA_PLATFORM=
offscreen. No game, and the real save folder is never looked at.
"""
import json, os, shutil, sys, tempfile, types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.pop("FL26_DIR", None)
T = tempfile.mkdtemp(prefix="saveswap-")
KONAMI = os.path.join(T, "KONAMI", "eFootball PES 2021 SEASON UPDATE", "2026")
os.environ["FL26_SAVE_ROOT"] = KONAMI          # before anything asks where the saves are

from modstudio import saves as SV, worlds as WL, backups
from test_world_manage import make_game, put

N = 0
QUIET = lambda *a, **k: None
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def tree(d):
    """every file under d with its bytes, and every folder"""
    out = {}
    if not os.path.isdir(d):
        return out
    for top, dirs, files in os.walk(d):
        for f in files:
            p = os.path.join(top, f)
            with open(p, "rb") as fh:
                out[os.path.relpath(p, d)] = fh.read()
        for x in dirs:
            out[os.path.relpath(os.path.join(top, x), d) + os.sep] = b""
    return out


def careers(t):
    """a tree without the settings files (those travel with the player)"""
    return {k: v for k, v in t.items() if not SV.is_shared(os.path.basename(k.rstrip(os.sep)))}


def fill_save(r, tag):
    s = os.path.join(r, "save")
    put(os.path.join(s, "ML00000000"), b"ML career of " + tag + bytes(range(256)))
    put(os.path.join(s, "ML00000001"), b"second ML of " + tag)
    put(os.path.join(s, "BL00000000"), b"Become a Legend of " + tag)
    put(os.path.join(s, "EDIT00000000"), b"Edit data of " + tag)
    put(os.path.join(s, "SYSTEM00000000"), b"options v1")
    put(os.path.join(s, "replay", "r1.bin"), b"replay of " + tag)


def core():
    r = os.path.join(T, "core")
    sd = os.path.join(T, "core-sider")
    put(os.path.join(sd, "sider.ini"), "lua.enabled = 1\r\n")
    fill_save(r, b"A")
    a0 = tree(os.path.join(r, "save"))
    no = lambda: False

    ok("paths: save_<world>, save_no-world for no world of ours",
       SV.folder_of("_FL26A", r) == os.path.join(r, "save__FL26A") and SV.name_of(None) == "save_no-world")
    ok("settings files are the SYSTEM / OPTION ones, careers and Edit data are not",
       SV.is_shared("SYSTEM00000000") and SV.is_shared("OPTION00000000")
       and not any(SV.is_shared(f) for f in ("ML00000000", "BL00000000", "EDIT00000000", "CUP00000000", "replay")))
    ok("same world: nothing to do", SV.swap_saves("_FL26A", "_FL26A", sd, r, running=no) is None
       and tree(os.path.join(r, "save")) == a0)

    # ---- A -> B
    res = SV.swap_saves("_FL26A", "_FL26B", sd, r, running=no)
    ok("A -> B: A's careers in save__FL26A, byte for byte", tree(os.path.join(r, "save__FL26A")) == a0)
    ok("A -> B: B starts with an empty save, only the settings file copied in",
       tree(os.path.join(r, "save")) == {"SYSTEM00000000": b"options v1"} and res["fresh"])
    ok("A -> B: the first swap ever, marked so (the note)", res["first"] and res["shared"] == ["SYSTEM00000000"])
    copies = SV.backups_of(sd)
    ok("A -> B: the save folder was copied first into ModStudio\\backups\\saves",
       len(copies) == 1 and tree(os.path.join(copies[0][0], "save")) == a0
       and copies[0][0].startswith(os.path.join(sd, "ModStudio", "backups", "saves")))
    ok("A -> B: whose careers are in save is written down", SV.load_state(r)["active"] == "_FL26B")

    # B plays a career and changes an option
    put(os.path.join(r, "save", "ML00000000"), b"B's own career")
    put(os.path.join(r, "save", "EDIT00000000"), b"B's Edit data")
    put(os.path.join(r, "save", "SYSTEM00000000"), b"options v2")
    b0 = tree(os.path.join(r, "save"))

    # ---- B -> A
    res = SV.swap_saves("_FL26B", "_FL26A", sd, r, running=no)
    ok("B -> A: A's careers back in save, byte for byte", careers(tree(os.path.join(r, "save"))) == careers(a0))
    ok("B -> A: the newest options came with the player", tree(os.path.join(r, "save"))["SYSTEM00000000"] == b"options v2")
    ok("B -> A: B's careers kept in save__FL26B", tree(os.path.join(r, "save__FL26B")) == b0)
    ok("B -> A: save__FL26A is gone into save (renamed, not copied)", not os.path.exists(os.path.join(r, "save__FL26A")))
    ok("B -> A: not the first swap, no second copy", not res["first"] and not res["fresh"] and len(SV.backups_of(sd)) == 1)

    # ---- A -> B again
    SV.swap_saves("_FL26A", "_FL26B", sd, r, running=no)
    ok("A -> B again: B's careers back byte for byte", tree(os.path.join(r, "save")) == b0)
    a1 = tree(os.path.join(r, "save__FL26A"))
    ok("A -> B again: A's careers aside, byte for byte (options v2 now)",
       careers(a1) == careers(a0) and a1["SYSTEM00000000"] == b"options v2")

    # ---- refusals: nothing renamed
    before = tree(r)
    try:
        SV.swap_saves("_FL26B", "_FL26A", sd, r, running=lambda: True)
        raised = ""
    except SV.SaveError as e:
        raised = str(e)
    ok("the game running: refused, says to close it, nothing renamed", "Close it first" in raised and tree(r) == before)
    os.makedirs(os.path.join(r, "save__FL26B"))
    try:
        SV.swap_saves("_FL26B", "_FL26A", sd, r, running=no)
        raised = ""
    except SV.SaveError as e:
        raised = str(e)
    ok("save_<old> there already: refused, nothing renamed", "save__FL26B" in raised
       and tree(r) == dict(before, **{"save__FL26B" + os.sep: b""}))
    os.rmdir(os.path.join(r, "save__FL26B"))
    put(os.path.join(r, "save__FL26C"), b"a file")
    before = tree(r)
    try:
        SV.swap_saves("_FL26B", "_FL26C", sd, r, running=no)
        raised = ""
    except SV.SaveError as e:
        raised = str(e)
    ok("save_<new> a file: refused, nothing renamed", "not a save folder" in raised and tree(r) == before)
    os.remove(os.path.join(r, "save__FL26C"))

    # ---- the second rename fails: the first one goes back
    before = tree(r)
    real, calls = os.rename, []

    def flaky(a, b):
        calls.append((a, b))
        if len(calls) == 2:
            raise PermissionError(5, "Access is denied", a)
        return real(a, b)
    SV.os.rename = flaky
    try:
        SV.swap_saves("_FL26B", "_FL26A", sd, r, running=no)
        raised = ""
    except SV.SaveError as e:
        raised = str(e)
    finally:
        SV.os.rename = real
    ok("a rename that fails half way: refused, the first rename undone, all as before",
       "nothing was switched" in raised and len(calls) == 3 and tree(r) == before)
    ok("... and the note of whose careers are in save did not change", SV.load_state(r)["active"] == "_FL26B")

    # ---- Rename world
    SV.rename_saves("_FL26A", "_FL26Z", r)
    ok("rename: save__FL26A -> save__FL26Z, byte for byte", not os.path.exists(os.path.join(r, "save__FL26A"))
       and tree(os.path.join(r, "save__FL26Z")) == a1)
    SV.rename_saves("_FL26B", "_FL26Y", r)
    ok("rename of the world whose careers are in save: the note follows, save stays",
       SV.load_state(r)["active"] == "_FL26Y" and tree(os.path.join(r, "save")) == b0)
    os.makedirs(os.path.join(r, "save__FL26Q"))
    try:
        SV.rename_saves("_FL26Z", "_FL26Q", r)
        raised = ""
    except SV.SaveError as e:
        raised = str(e)
    ok("rename onto a save_<name> there already: refused, nothing renamed",
       "save__FL26Q" in raised and os.path.isdir(os.path.join(r, "save__FL26Z")))
    ok("rename of a world with no careers aside: nothing", SV.rename_saves("_FL26Nope", "_FL26N2", r) is None)


def switch():
    """saves.Switch, the way the pages use it, on a game with a world in it"""
    game = make_game(os.path.join(T, "sw"))
    shutil.rmtree(KONAMI, ignore_errors=True)
    fill_save(KONAMI, b"Live")
    s0 = tree(os.path.join(KONAMI, "save"))
    SV.game_running = lambda: False

    sw = SV.Switch({SV.SETTING: False}, game, "_FL26Old")
    ok("setting off: nothing needed, nothing done", not sw.needed() and sw.go() is None
       and tree(os.path.join(KONAMI, "save")) == s0 and not os.path.exists(os.path.join(KONAMI, "save__FL26Live")))
    env = os.environ.pop("FL26_SAVE_ROOT")
    try:
        ok("a window without a screen and no FL26_SAVE_ROOT: never (a test must not touch this PC's saves)",
           not SV.Switch({}, game, "_FL26Old").needed())
    finally:
        os.environ["FL26_SAVE_ROOT"] = env

    sw = SV.Switch({}, game, "_FL26Live")
    ok("the world in the game again: nothing needed", not sw.needed())
    sw = SV.Switch({}, game, "_FL26Old")
    ok("another world: the old one is the one in sider.ini", sw.needed() and sw.old() == "_FL26Live")
    ok("the question says where the careers go", "_FL26Live" in sw.ask_text() and "save__FL26Live" in sw.ask_text()
       and "starts with its own" in sw.ask_text())
    SV.game_running = lambda: True
    ok("the game running: problem() says so", "Close it first" in sw.problem())
    SV.game_running = lambda: False
    ok("problem() empty when it can be done", sw.problem() == "")
    sw.go()
    ok("go(): save__FL26Live holds the careers, save is _FL26Old's",
       tree(os.path.join(KONAMI, "save__FL26Live")) == s0 and SV.load_state()["active"] == "_FL26Old")
    note = sw.note()
    ok("the first-time note in plain words: kept in save__FL26Live, _FL26Old starts with its own, Settings",
       "Your careers of _FL26Live are kept in save__FL26Live" in note and "_FL26Old starts with its own" in note
       and "Settings" in note and "backups" in note)
    ok("B155: the note says the Edit data goes with the careers",
       "Edit data (EDIT00000000) goes with the careers too: it stays with _FL26Live" in note)
    ok("the copy of the first swap is in this game's ModStudio\\backups\\saves",
       len(SV.backups_of(game.sider_dir)) == 1)
    sw.undo()
    ok("undo(): all back as it was", tree(os.path.join(KONAMI, "save")) == s0
       and not os.path.exists(os.path.join(KONAMI, "save__FL26Live")) and SV.load_state()["active"] == "_FL26Live")
    sw2 = SV.Switch({}, game, "_FL26Old")
    sw2.go()
    ok("a second switch: no first-time note any more", sw2.note() == "")
    sw2.undo()

    # after a reset of Sider: no world in the game, save still holds _FL26Live's careers
    sw = SV.Switch({}, game, "_FL26Live", old=None)
    ok("after a reset: putting the same world back swaps nothing (save is its own)", not sw.needed())
    sw = SV.Switch({}, game, "_FL26Old", old=None)
    ok("after a reset: another world puts the old one's careers under its own name", sw.old() == "_FL26Live")
    SV.forget_owner()
    ok("the setting on again: save is the world in the game's from then on", sw.old() is None
       and "active" not in SV.load_state())


def pages():
    """Content folders: Apply, Rename world, Delete world, with the save folder"""
    from PySide6.QtWidgets import QApplication
    qa = QApplication.instance() or QApplication([])
    from modstudio import theme, ui
    theme.apply(qa)
    from modstudio.app import Bus
    from modstudio.siderini import SiderIni
    from modstudio import roots as R
    from modstudio.pages import roots as RP
    from test_world_manage import FakeProject
    game = make_game(os.path.join(T, "pages"))
    game.running = lambda: (False, False)
    shutil.rmtree(KONAMI, ignore_errors=True)
    fill_save(KONAMI, b"Live")
    s0 = tree(os.path.join(KONAMI, "save"))
    SV.game_running = lambda: False
    app = types.SimpleNamespace(game=game, bus=Bus(), settings={}, project=FakeProject(os.path.join(T, "rec"), "_FL26Live"))
    app.ini = lambda: SiderIni.load(game.ini_path)
    app.busy = app.status = app.save_settings = app.open_page = QUIET

    def save_ini(ini, reason):
        ini.save(reason=reason)
        app.bus.ini_changed.emit()
    app.save_ini = save_ini
    asked, errors, infos = [], [], []
    RP.ask = lambda parent, title, text: asked.append(text) or True
    RP.error = lambda parent, title, text: errors.append(text)
    ui.error = lambda parent, title, text: errors.append(text)
    ui.info = lambda parent, title, text: infos.append(text)
    page = RP.Roots(app)
    page.rescan = lambda: (setattr(page, "idx", R.scan(game.sider_dir, app.ini())), page.load())
    page.rescan()
    page.show_worlds.setChecked(True)

    def tick(world, on):
        from PySide6.QtCore import Qt
        for i in range(page.tree.topLevelItemCount()):
            it = page.tree.topLevelItem(i)
            if it.text(2).endswith("\\" + world):
                it.setCheckState(0, Qt.Checked if on else Qt.Unchecked)
        qa.processEvents()

    def switch_old_on():
        tick("_FL26Old", True)
        tick("_FL26Live", False)
        ok("Content folders: _FL26Old ticked on, _FL26Live off, not written yet",
           page.dirty and WL.live(game) == ["_FL26Live"])

    # the game running: nothing written, nothing renamed
    switch_old_on()
    ini0 = open(game.ini_path, "rb").read()
    SV.game_running = lambda: True
    page.apply()
    ok("Apply with the game running: refused with the reason, sider.ini and saves as they were",
       errors and "Close it first" in errors[-1] and open(game.ini_path, "rb").read() == ini0
       and tree(os.path.join(KONAMI, "save")) == s0 and page.dirty)
    SV.game_running = lambda: False
    asked.clear()
    page.apply()
    ok("Apply: asked first, the question says the careers of _FL26Live go to save__FL26Live",
       asked and "save__FL26Live" in asked[-1])
    ok("Apply: _FL26Old in the game, _FL26Live's careers in save__FL26Live byte for byte",
       WL.live(game) == ["_FL26Old"] and tree(os.path.join(KONAMI, "save__FL26Live")) == s0
       and tree(os.path.join(KONAMI, "save")) == {"SYSTEM00000000": b"options v1"})
    ok("Apply: the first time, the player is told once where the careers are",
       len(infos) == 1 and "save__FL26Live" in infos[-1])

    # a change that does not touch the world: no question, no swap
    asked.clear()
    page.ini.reorder("cpk.root", [e.value for e in reversed(page.entries())])
    page.dirty = True
    page.apply()
    ok("Apply without a world change: no question about careers, saves as they were",
       not any("careers" in a for a in asked) and os.path.isdir(os.path.join(KONAMI, "save__FL26Live")))

    # Delete world says the careers stay
    asked.clear()
    page.delete_world("_FL26Live")
    ok("Delete world: the question says its careers stay in save__FL26Live",
       asked and "save__FL26Live" in asked[-1] and "does not delete" in asked[-1])
    ok("Delete world: save__FL26Live is left alone", tree(os.path.join(KONAMI, "save__FL26Live")) == s0)
    from modstudio.pages import restore as RS
    RS.ask, RS.error = RP.ask, RP.error
    rp = RS.Restore(app)
    rp.refresh()
    rows = [rp.tree.topLevelItem(i).data(0, RS.ROW) for i in range(rp.tree.topLevelItemCount())]
    srows = [x for x in rows if "saves_backup" in (x or {})]
    ok("Restore points: the copy of the save folder before the first switch is listed", len(srows) == 1)
    wrows = [x for x in rows if "world_backup" in (x or {})]
    rp.tree.setCurrentItem(rp.tree.topLevelItem(rows.index(wrows[0])))
    rp.restore()
    ok("Restore points: _FL26Live is back (switched off)", os.path.isdir(os.path.join(game.livecpk_dir, "_FL26Live")))
    page.rescan()

    # Rename world: its careers kept aside are renamed with it
    from PySide6 import QtWidgets
    QtWidgets.QInputDialog.getText = staticmethod(lambda *a, **k: ("_FL26Renamed", True))
    asked.clear()
    page.rename_world("_FL26Live")
    from test_world_manage import wait_rename
    wait_rename(qa, page)                     # it runs in the background (B66)
    ok("Rename world: the question says its careers are renamed",
       asked and "save__FL26Live" in asked[-1] and "save__FL26Renamed" in asked[-1])
    ok("Rename world: save__FL26Live -> save__FL26Renamed byte for byte",
       not os.path.exists(os.path.join(KONAMI, "save__FL26Live"))
       and tree(os.path.join(KONAMI, "save__FL26Renamed")) == s0)

    # the setting off: a world switch leaves the saves alone
    app.settings[SV.SETTING] = False
    page.rescan()
    tick("_FL26Renamed", True)
    tick("_FL26Old", False)
    before = tree(KONAMI)
    page.apply()
    ok("the setting off: the world switches, the save folders do not",
       WL.live(game) == ["_FL26Renamed"] and tree(KONAMI) == before)
    page.hide()


def main():
    try:
        core()
        switch()
        pages()
    finally:
        shutil.rmtree(T, ignore_errors=True)
    print("test_save_swap: ok (%d)" % N)


if __name__ == "__main__":
    main()
