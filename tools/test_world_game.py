r"""python tools/test_world_game.py [<folder with FL26's tables>]

mato 07.11.2026: "people must not put this pack into FL26 by mistake, it could break their game".
An FL 2027 world (the Megapack: 204 leagues, ~103,000 players, 4800 clubs) does not fit FL26's
2400 clubs and 61905 players; an FL26 world in FL 2027 replaces FL 2027's own tables (B307).

  - Build writes `game fl26|fl27 teams=<n> players=<n>` after the world file's `world` line
    (worldgame.stamp), and "game" into leaguebuilder-plan.json -- with the tables given, a small
    Build checks it;
  - Install mods refuses a world (or a database folder) of the other game, before a file is
    copied: by its game line, or -- a world without one -- by its size; a valid FL26 world without
    the line goes anywhere;
  - Switch on (leaguebuilder.switch_on) refuses it with sider.ini untouched;
  - a recipe for FL 2027 ("game": "fl27") and one too big for FL26 are not built in FL26;
  - an export stamps a world built before the line, and the zip's json and read-me say the game;
  - fl26gameguard.lua (first in the pack's load order) stops the game, with a message box, when a
    switched-on world or modules\fl26world.txt is the other game's; otherwise one log line.

No game: fake game folders (an empty FL_2026.exe / FL_2027.exe) in a temp folder, and the Lua
module run in lupa's LuaJIT with a stand-in ffi (the exe's name, the box, TerminateProcess).
"""
import json, os, shutil, struct, sys, tempfile, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import worldgame as WG
import leaguebuilder as B
import fl26world
from modstudio import installer as I, i18n
from modstudio.siderini import SiderIni

N = 0
GUARD = os.path.join(os.path.dirname(HERE), "sider", "fl26gameguard.lua")


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %2d - %s" % (N, name))


def put(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(data.encode("utf-8") if isinstance(data, str) else data)


def table(n, rec):
    """a packed pesdb table that says it holds n records (its header; the rest is not read)"""
    return b"\x00\x01\x01WESYS" + struct.pack("<II", 4, n * rec) + b"\x00" * 4


def game(root, exe):
    """a game folder with `exe` (or none), Sider and an empty sider.ini"""
    if exe:
        put(os.path.join(root, exe), b"")
    sd = os.path.join(root, "SiderAddons")
    put(os.path.join(sd, "sider.ini"), '[sider]\nlua.module = "kserv.lua"\n')
    for d in ("modules", "livecpk", "content"):
        os.makedirs(os.path.join(sd, d), exist_ok=True)
    return root


class Game:
    def __init__(self, folder):
        self.folder = folder
        self.sider_dir = os.path.join(folder, "SiderAddons")
        self.livecpk_dir = os.path.join(self.sider_dir, "livecpk")
        self.modules_dir = os.path.join(self.sider_dir, "modules")
        self.content_dir = os.path.join(self.sider_dir, "content")


WORLD_TEXT = "# fl26world 1\r\nworld %s\r\nleague 900 cid=130 region=40 clubs=4 name=Test League\r\nnewfaces 500000-500003\r\n"


def world(root, name, game_line=None, teams=40, players=1200):
    """a built world folder at <root>\\<name>: its world file (with `game_line`) and tables"""
    d = os.path.join(root, name)
    text = WORLD_TEXT % name
    if game_line:
        text = WG.stamped(text, game_line)
    put(os.path.join(d, "fl26world.txt"), text)
    put(os.path.join(d, "common", "etc", "pesdb", "Team.bin"), table(teams, WG.TEAM_REC))
    put(os.path.join(d, "common", "etc", "pesdb", "Player.bin"), table(players, WG.PLAYER_REC))
    return d


def pack(tmp, name, **kw):
    """a world zip as unpacked: SiderAddons\\livecpk\\<world>"""
    src = os.path.join(tmp, "pack-" + name + "-" + str(N))
    world(os.path.join(src, "SiderAddons", "livecpk"), name, **kw)
    return src


def install(g, src):
    """Install mods of the unpacked zip at src into game folder g: (refused text or None, parts)"""
    sd = os.path.join(g, "SiderAddons")
    work = tempfile.mkdtemp(prefix="wg_work_")
    try:
        parts = I.detect(I.unpack(src, work), "pack")
        said = [I.wrong_game(g, p.src, p.world_file, p.name) for p in parts if p.kind in ("world", "root")]
        ini = SiderIni.load(os.path.join(sd, "sider.ini"))
        try:
            I.Installer(Game(g), ini, "pack.zip").run(parts)
            ini.save()
            return None, said
        except I.WrongGame as e:
            return str(e), said
    finally:
        shutil.rmtree(work, ignore_errors=True)


def ini_text(g):
    return open(os.path.join(g, "SiderAddons", "sider.ini"), encoding="utf-8").read()


# ---- the Lua module -------------------------------------------------------------------------
FAKE_FFI = r"""
local exe = ...
FAKE = { box = nil, title = nil, killed = false, logs = {} }
function log(s) FAKE.logs[#FAKE.logs + 1] = s end
ffi = {
  cdef = function() end,
  new = function(t, n) return { n = n } end,
  string = function(b, n) return b.s end,
  C = {
    fl26gameguard_GetModuleFileNameA = function(_, buf, n) buf.s = exe; return #exe end,
    fl26gameguard_MultiByteToWideChar = function() return 0 end,
    fl26gameguard_WideCharToMultiByte = function() return 0 end,
    fl26gameguard_MessageBoxA = function(_, text, title, flags) FAKE.box = text; FAKE.title = title; return 1 end,
    fl26gameguard_GetCurrentProcess = function() return 1 end,
    fl26gameguard_TerminateProcess = function() FAKE.killed = true; return 1 end,
  },
}
"""


def run_guard(g, exe):
    """fl26gameguard.lua's init in game folder g as `exe` would run it: (killed, box text, log lines)"""
    from lupa import luajit21 as lj
    lua = lj.LuaRuntime()
    lua.execute(FAKE_FFI, "C:\\Games\\Football Life\\" + exe)
    m = lua.execute(open(GUARD, encoding="utf-8").read())
    m.init(lua.table_from({"sider_dir": os.path.join(g, "SiderAddons") + "\\"}))
    fake = lua.globals().FAKE
    return bool(fake.killed), fake.box, [fake.logs[i] for i in range(1, len(fake.logs) + 1)]


def main(base=None):
    tmp = tempfile.mkdtemp(prefix="fl26 world game ")      # a space in the path, as a player's
    try:
        # ---- worldgame: the line and its reading ----
        ok("FL26's caps here are leaguebuilder's", WG.FL26_CAPS == B.GAME_CAPS["fl26"])
        line = WG.stamp_line("fl27", 4512, 103210)
        ok("the game line: %s" % line, line == "game fl27 teams=4512 players=103210")
        text = WG.stamped(WORLD_TEXT % "_FL26Mega", line)
        rows = text.split("\r\n")
        ok("it goes right after the world line, the file keeps its CRLF", rows[1] == "world _FL26Mega" and rows[2] == line)
        ok("stamped twice: one game line", WG.stamped(text, WG.stamp_line("fl26")).count("game ") == 1)
        d = world(tmp, "_FL26Read", line)
        ok("read back", WG.read_stamp(os.path.join(d, "fl26world.txt")) == {"game": "fl27", "teams": 4512, "players": 103210})
        name, leagues = fl26world.read_world(os.path.join(d, "fl26world.txt"))
        ok("the world file readers do not mind it (read_world, world_name, face_players)",
           name == "_FL26Read" and [L["id"] for L in leagues] == [900]
           and I.world_name(os.path.join(d, "fl26world.txt")) == "_FL26Read"
           and I.face_players(os.path.join(d, "fl26world.txt")) == 4)
        ok("a packed table's records from its header", WG.counts(d) == (40, 1200))
        put(os.path.join(d, "common", "etc", "pesdb", "Team.bin"), b"\x00" * (WG.TEAM_REC * 7))
        ok("... and an unpacked one's from its size", WG.counts(d)[0] == 7)
        WG.stamp(d, "fl26")
        ok("stamp() writes the world's own counts", WG.read_stamp(os.path.join(d, "fl26world.txt")) ==
           {"game": "fl26", "teams": 7, "players": 1200})
        ok("no world file, no tables: (None, None, None, False)",
           WG.world_game(os.path.join(tmp, "nothing")) == (None, None, None, False))

        g26, g27 = game(os.path.join(tmp, "FL26"), "FL_2026.exe"), game(os.path.join(tmp, "FL27"), "FL_2027.exe")
        ok("game_of by the exe", (WG.game_of(g26), WG.game_of(g27), WG.game_of(tmp)) == ("fl26", "fl27", None))
        both = game(os.path.join(tmp, "both"), "FL_2027.exe")
        put(os.path.join(both, "FL_2026.exe"), b"")
        ok("both exes: FL26, as flpaths.game_exe and leaguebuilder.is_fl27 read it",
           WG.game_of(both) == "fl26" and not B.is_fl27(both))

        # ---- Install mods ----
        msg, said = install(g26, pack(tmp, "_FL26Mega", game_line=WG.stamp_line("fl27", 4512, 103210)))
        ok("an FL 2027 world into FL26: refused -- %s" % msg, msg and "FL 2027" in msg and "4512" in msg
           and "2400" in msg and said and said[0] == msg)
        ok("  ... before a file is copied: no livecpk\\_FL26Mega, no world file in modules, sider.ini as it was",
           not os.path.exists(os.path.join(g26, "SiderAddons", "livecpk", "_FL26Mega"))
           and not os.path.exists(os.path.join(g26, "SiderAddons", "modules", "fl26world.txt"))
           and "_FL26Mega" not in ini_text(g26))
        msg, _s = install(g27, pack(tmp, "_FL26Mega", game_line=WG.stamp_line("fl27", 4512, 103210)))
        ok("the same zip into FL 2027 goes in", msg is None
           and os.path.isfile(os.path.join(g27, "SiderAddons", "livecpk", "_FL26Mega", "fl26world.txt"))
           and "_FL26Mega" in ini_text(g27))

        msg, _s = install(g26, pack(tmp, "_FL26OldBig", teams=4100, players=99000))
        ok("a world without the line and 4100 clubs into FL26: refused by its size", msg and "4100" in msg)
        msg, _s = install(g26, pack(tmp, "_FL26OldPlayers", teams=2300, players=70000))
        ok("... 2300 clubs but 70000 players: refused", msg and "70000" in msg)
        msg, _s = install(g26, pack(tmp, "_FL26Old", teams=2400, players=61905))
        ok("a world without the line at FL26's caps exactly (2400 / 61905): goes into FL26", msg is None
           and os.path.isdir(os.path.join(g26, "SiderAddons", "livecpk", "_FL26Old")))
        g27b = game(os.path.join(tmp, "FL27b"), "FL_2027.exe")
        msg, _s = install(g27b, pack(tmp, "_FL26Old", teams=2400, players=61905))
        ok("  ... and into FL 2027 too (nothing says it is FL26's)", msg is None)

        msg, _s = install(g27, pack(tmp, "_FL26Nl", game_line=WG.stamp_line("fl26", 2390, 60000)))
        ok("an FL26 world into FL 2027: refused -- %s" % msg, msg and "FL26" in msg
           and not os.path.exists(os.path.join(g27, "SiderAddons", "livecpk", "_FL26Nl")))
        msg, _s = install(g26, pack(tmp, "_FL26Nl", game_line=WG.stamp_line("fl26", 2390, 60000)))
        ok("  ... into FL26: in", msg is None)

        src = os.path.join(tmp, "dbpack")                     # a world's tables without its world file
        put(os.path.join(src, "SiderAddons", "livecpk", "Big DB", "common", "etc", "pesdb", "Player.bin"),
            table(90000, WG.PLAYER_REC))
        msg, said = install(g26, src)
        ok("a database folder (no world file) with 90000 players into FL26: refused",
           msg and "90000" in msg and not os.path.exists(os.path.join(g26, "SiderAddons", "livecpk", "Big DB")))
        ok("a game folder Mod Studio cannot tell (no exe): nothing refused",
           I.wrong_game(tmp, world(tmp, "_FL26NoExe", WG.stamp_line("fl27"))) is None)

        i18n.set_language("hr")
        try:
            hr = I.wrong_game(g26, os.path.join(g27, "SiderAddons", "livecpk", "_FL26Mega"), world="_FL26Mega")
        finally:
            i18n.set_language("en")
        ok("in the user's language: %s" % hr, hr and hr.startswith("_FL26Mega je svijet za FL 2027"))

        # ---- Switch on ----
        world(os.path.join(g26, "SiderAddons", "livecpk"), "_FL26Copied", WG.stamp_line("fl27", 4512, 103210))
        before = ini_text(g26)
        try:
            B.switch_on("_FL26Copied", g26, log=lambda *a: None)
            refused = None
        except B.BuildError as e:
            refused = str(e)
        ok("Switch on of an FL 2027 world in FL26: refused -- %s" % refused,
           refused and refused.startswith("_FL26Copied is a world for FL 2027 (4512 clubs, 103210 players"))
        ok("  ... sider.ini and modules untouched", ini_text(g26) == before
           and I.world_name(os.path.join(g26, "SiderAddons", "modules", "fl26world.txt")) != "_FL26Copied")
        i18n.set_language("hr")
        try:
            ok("  ... and Build's log says it in the user's language", i18n.tr(refused).startswith(
                "_FL26Copied je svijet za FL 2027 (klubova 4512, igrača 103210; FL26 prima 2400"))
        finally:
            i18n.set_language("en")

        # ---- Build ----
        B.FL27 = False
        try:
            B.plan({"world": "_FL26Megapack", "game": "fl27", "leagues": []}, None)
            refused = None
        except B.BuildError as e:
            refused = str(e)
        ok("a recipe for FL 2027 is not built in FL26 -- %s" % refused,
           refused == "_FL26Megapack is a recipe for FL 2027 -- choose FL 2027's game folder (Game) and Build there")
        B.FL27 = True
        try:
            B.plan({"world": "_FL26X", "game": "fl26", "leagues": []}, None)
            refused = None
        except B.BuildError as e:
            refused = str(e)
        ok("  ... nor one for FL26 in FL 2027", refused and "recipe for FL26" in refused)
        B.FL27 = False
        if base:
            room = B.clubs_room
            L = {"name": "Test National", "country": "France", "clubs": 18, "legs": 2, "exchange": 3, "above": 81}
            try:
                B.clubs_room = lambda b: 10
                for fl27, want in ((False, "18 new clubs, but FL26 has room for 10 more (a full squad each) -- a world "
                                           "this big is for FL 2027: choose FL 2027's game folder (Game) and Build there"),
                                   (True, "18 new clubs, but the game has room for 10 more (a full squad each)")):
                    B.FL27 = fl27
                    try:
                        B.plan({"world": "_FL26Big", "leagues": [dict(L)]}, base)
                        said = None
                    except B.BuildError as e:
                        said = str(e)
                    ok("too many clubs in %s: %s" % ("FL 2027" if fl27 else "FL26", said), said == want)
            finally:
                B.clubs_room, B.FL27 = room, False
            gb = game(os.path.join(tmp, "build"), None)
            pl = B.plan({"world": "_FL26Stamp", "leagues": [dict(L)]}, base)
            B.build(pl, base, gb, False, log=lambda *a: None)
            out = os.path.join(gb, "SiderAddons", "livecpk", "_FL26Stamp")
            rows = open(os.path.join(out, "fl26world.txt"), encoding="utf-8").read().splitlines()
            s = WG.read_stamp(os.path.join(out, "fl26world.txt"))
            ok("Build stamps the world file after its world line: %s" % rows[2], rows[1] == "world _FL26Stamp"
               and rows[2].startswith("game fl26 teams=") and s["teams"] == WG.counts(out)[0] > 0
               and s["players"] == WG.counts(out)[1] > 0)
            ok("  ... and the plan says the game",
               json.load(open(os.path.join(out, "leaguebuilder-plan.json"), encoding="utf-8")).get("game") == "fl26")
        else:
            print("# no tables given: the Build's own stamp is not checked")

        # ---- export ----
        sd26 = os.path.join(g26, "SiderAddons")
        world(os.path.join(sd26, "livecpk"), "_FL26Export")             # built before the line
        zp = os.path.join(tmp, "export.zip")
        info = I.export_world(sd26, "_FL26Export", zp)
        with zipfile.ZipFile(zp) as z:
            wf = z.read("SiderAddons/livecpk/_FL26Export/fl26world.txt").decode("utf-8")
            readme = z.read(I.WORLD_README).decode("utf-8")
            js = json.loads(z.read(I.WORLD_INFO).decode("utf-8"))
        ok("an export of a world built before the line stamps it by the game it is in (FL26)",
           wf.splitlines()[2] == "game fl26 teams=40 players=1200" and info["game"] == js["game"] == "fl26")
        ok("  ... the world on disk is left as it was",
           WG.read_stamp(os.path.join(sd26, "livecpk", "_FL26Export", "fl26world.txt")) is None)
        ok("  ... the read-me and the json say it", "FOR FL26 ONLY" in readme and js["needs"][0].startswith("FL26"))
        nog = os.path.join(tmp, "noexe")
        world(os.path.join(nog, "SiderAddons", "livecpk"), "_FL26ExportBig", teams=4000, players=100000)
        info = I.export_world(os.path.join(nog, "SiderAddons"), "_FL26ExportBig", zp)
        ok("  ... a big one, the game unknown: FL 2027 by its size", info["game"] == "fl27")

        # ---- fl26gameguard.lua ----
        try:
            import lupa  # noqa: F401
        except ImportError:
            print("# no lupa: fl26gameguard.lua not run")
            lupa = None
        import lbpack
        ok("fl26gameguard is first in the pack's load order", lbpack.ORDER[0] == "fl26gameguard")
        if lupa:
            gg = game(os.path.join(tmp, "guard"), "FL_2026.exe")
            lc = os.path.join(gg, "SiderAddons", "livecpk")
            world(lc, "_FL26Mine", WG.stamp_line("fl26", 2300, 60000))
            world(lc, "_FL26Mega", WG.stamp_line("fl27", 4512, 103210))
            world(lc, "_FL26Older")
            ini = os.path.join(gg, "SiderAddons", "sider.ini")
            put(ini, '[sider]\ncpk.root = ".\\livecpk\\_FL26Mine"\ncpk.root = ".\\livecpk\\_FL26Older"\n'
                     ';cpk.root = ".\\livecpk\\_FL26Mega"\nlua.module = "fl26gameguard.lua"\n')
            killed, box, logs = run_guard(gg, "FL_2026.exe")
            ok("FL26 with its own world on (and the FL 2027 one switched off): runs on -- %s" % logs[-1],
               not killed and box is None and "1 world file(s)" in logs[-1])
            put(ini, '[sider]\ncpk.root = ".\\livecpk\\_FL26Mega"\ncpk.root = "%s"\n'
                % os.path.join(lc, "_FL26Mine"))
            killed, box, logs = run_guard(gg, "FL_2026.exe")
            ok("an FL 2027 world copied in by hand and switched on in FL26: the game closes", killed)
            ok("  ... with a message box saying what to do -- %r" % box[:120], box and box.startswith(
                "_FL26Mega cannot be played here: it is a world for FL 2027 (4512 clubs, 103210 players")
               and "My world" in box and "sider.ini" in box)
            ok("  ... and a sider.log line", any(l.startswith("fl26gameguard: REFUSED _FL26Mega") for l in logs))
            killed, box, logs = run_guard(gg, "FL_2027.exe")
            ok("the same sider.ini in FL 2027: the FL26 world (absolute cpk.root path) is refused there",
               killed and "_FL26Mine" in box and "a world for FL26" in box)
            put(ini, '[sider]\ncpk.root = ".\\livecpk\\_FL26Mega"\n')
            killed, box, logs = run_guard(gg, "FL_2027.exe")
            ok("FL 2027 with its own world: runs on", not killed and box is None)
            put(ini, '[sider]\ncpk.root = ".\\livecpk\\_FL26Older"\n')
            shutil.copy(os.path.join(lc, "_FL26Mega", "fl26world.txt"), os.path.join(gg, "SiderAddons", "modules"))
            killed, box, logs = run_guard(gg, "FL_2026.exe")
            ok("an FL 2027 world file in FL26's modules (what the modules read): the game closes", killed)
            os.remove(os.path.join(gg, "SiderAddons", "modules", "fl26world.txt"))
            killed, box, logs = run_guard(gg, "FL_2026.exe")
            ok("a world without the line (built before): runs on, in FL26 and in FL 2027",
               not killed and not run_guard(gg, "FL_2027.exe")[0])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("test_world_game: all %d passed" % N)


if __name__ == "__main__":
    os.environ["FL26_LEDGER_STORE"] = tempfile.mkdtemp(prefix="fl26ledgers-")   # review 3, 18.11.2026: never the real history
    main(sys.argv[1] if len(sys.argv) > 1 else None)
