"""python test_kickoff_wide.py [<world folder>] -- a Kick Off between two clubs of a league whose
competition id is past 255 is that league's, not the one its low byte names (B427, 11.11.2026).

pop1806, GigaPack beta 1: "u srpskoj ligi stoji bedz od J-lige". SmokePatch's lib\\CommonLib.lua
reads CompetitionEntry.bin's competition id as one byte, so Srpska liga Istok (553) was read as 41,
the J.League, and a Kick Off between two of its clubs wore the J.League's sleeve badge and
scoreboard. fl26slotnames.lua sets CommonLib's lists right after every read of the file.

Here the module runs whole in Lua (lupa) beside a stand-in for CommonLib that reads the file the
way CommonLib does (one byte, its playable list, lists never cleared), in the order of the game:
our livecpk_read, then CommonLib's, then the next event. With a world folder (livecpk\\<world>) the
same on its CompetitionEntry.bin and fl26world.txt. What the game shows is the season test's and
the feature table's row."""
import os
import re
import struct
import sys
import tempfile
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MOD = os.path.join(ROOT, "sider", "experimental", "fl26slotnames.lua")
N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def runtime():
    try:
        from lupa import luajit21 as lj
    except ImportError:
        try:
            from lupa import lua54 as lj
        except ImportError:
            return None
    return lj.LuaRuntime(encoding=None)


# CommonLib.lua's own reading (lines 109-145 of FL 2027 1.1's file), kept to what matters here
COMMONLIB = b"""
local m = { teams_in_playable_leagues_map = {}, compID_to_tournamentID_map = {}, tournamentID_to_compID_map = {} }
local playable = {}
function m.playable(list) playable = list end
function m.has_value(tab, val) for _, v in ipairs(tab) do if v == val then return true end end return false end
function m.try_unzlib(data) return data, "ERR_NOT_ZLIBBED" end
function m.read_entries(bytes)
  local i, o = 0, 1
  while o <= #bytes do
    local b0, b1, b2, b3 = bytes:byte(o, o + 3)
    local teamID = b0 + b1 * 256 + b2 * 65536 + b3 * 16777216
    local compID = bytes:byte(o + 8)
    if m.has_value(playable, compID) then
      if m.teams_in_playable_leagues_map[compID] ~= nil then
        if m.has_value(m.teams_in_playable_leagues_map[compID], teamID) == false then
          table.insert(m.teams_in_playable_leagues_map[compID], teamID)
        end
      else
        m.teams_in_playable_leagues_map[compID] = { teamID }
      end
    end
    i = i + 1
    o = i * 12 + 1
  end
end
function m.tid_same_league(home_id, away_id)
  for index, value in pairs(m.teams_in_playable_leagues_map) do
    if m.has_value(value, home_id) and m.has_value(value, away_id) then
      return m.compID_to_tournamentID_map[index]
    end
  end
end
return m
"""

SETUP = b"""
LOG = {}
function log(s) LOG[#LOG + 1] = s end
CHUNK = {}
HANDLERS = {}
memory = { read = function(addr, len) return CHUNK[addr] or string.rep(string.char(0), len) end }
"""


def entry(team, cid):
    b = bytearray(12)
    struct.pack_into("<I", b, 0, team)
    b[8] = cid & 0xff
    b[9] = 1
    b[11] = cid >> 8
    return bytes(b)


class Game:
    """the module in Lua with a ctx, a memory and CommonLib's stand-in"""

    def __init__(self, world_text, playable, tournaments):
        self.lua = runtime()
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, "modules"))
        with open(os.path.join(d, "modules", "fl26world.txt"), "w", encoding="utf-8") as f:
            f.write(world_text)
        L = self.lua
        L.execute(SETUP)
        # sider gives a module no pcall, xpcall or require (11.11.: the first fix called pcall, passed
        # here and raised in the game on every file the game opened)
        L.execute(b"pcall, xpcall, require = nil, nil, nil")
        self.cl = L.execute(COMMONLIB)
        self.cl.playable(L.table_from(playable))
        for cid, tid in tournaments.items():
            self.cl.compID_to_tournamentID_map[cid] = tid
        self.mod = L.execute(open(MOD, encoding="utf-8").read().encode("utf-8"))
        self.ctx = L.eval(b"{ register = function(name, f) HANDLERS[name] = f end }")
        self.ctx.sider_dir = d.encode("utf-8")
        self.mod.init(self.ctx)

    def handlers(self):
        h = self.lua.globals().HANDLERS
        return sorted(k.decode() for k in h.keys())

    def log(self):
        g = self.lua.globals().LOG
        return [g[i].decode("utf-8", "replace") for i in range(1, len(g) + 1)]

    def read(self, data, pieces=2, commonlib=True):
        """the game reads the file: our handler gets every piece first, CommonLib after it"""
        h = self.lua.globals().HANDLERS
        name = b"common\\etc\\pesdb\\CompetitionEntry.bin"
        step = max(12, (len(data) // pieces) // 12 * 12)
        off = 0
        while off < len(data):
            part = data[off:off + step] if off + 2 * step <= len(data) else data[off:]
            self.lua.globals().CHUNK[1] = part
            h[b"livecpk_read"](self.ctx, name, 1, len(part), len(data), off)
            off += len(part)
        if commonlib:
            self.ctx.common_lib = self.cl
            self.cl.read_entries(data)

    def event(self, name="livecpk_make_key"):
        self.lua.globals().HANDLERS[name.encode()](self.ctx, b"x", 0)

    def teams(self, cid):
        t = self.cl.teams_in_playable_leagues_map[cid]
        return None if t is None else sorted(t[i] for i in range(1, len(t) + 1))


def sandbox_calls():
    """every module we ship, its comments and strings left out: the calls sider's env does not have"""
    import glob
    bad = []
    for f in sorted(glob.glob(os.path.join(os.path.dirname(MOD), "*.lua"))):
        src = open(f, encoding="utf-8", errors="replace").read()
        src = re.sub(r"--\[(=*)\[.*?\]\1\]", "", src, flags=re.S)
        for line in src.splitlines():
            line = re.sub(r'"(?:[^"\\]|\\.)*"', '""', line)
            line = re.sub(r"'(?:[^'\\]|\\.)*'", "''", line)
            line = line.split("--", 1)[0]
            if re.search(r"(?<![\w.:])(pcall|xpcall|require)\s*[(\"'{]", line):
                bad.append("%s: %s" % (os.path.basename(f), line.strip()[:90]))
    return bad


def main():
    bad = sandbox_calls()
    ok("no module we ship calls pcall, xpcall or require (sider's module env has none)%s"
       % ("" if not bad else ": " + "; ".join(bad[:5])), not bad)
    if runtime() is None:
        src = open(MOD, encoding="utf-8").read()
        ok("no lupa: the module's text holds the three events and the whole id",
           all(w in src for w in ('ctx.register("livecpk_read", ko_read)', 'ctx.register("livecpk_make_key", ko_make_key)',
                                  'ctx.register("set_teams", ko_set_teams)', "bytes:byte(o + 11)")))
        print("skip - no lupa: the module not run")
        print("all %d passed" % N)
        return

    world = ("league 52 cid=41 slot=18 tier=1 clubs=3 name=J1 League\n"
             "league 438 cid=553 slot=300 tier=3 clubs=3 name=Srpska liga Istok\n"
             "league 394 cid=297 slot=255 tier=1 clubs=2 name=Virsliga\n"
             "league 700 cid=600 slot=310 tier=1 clubs=2 name=A league on no game league's byte\n"
             "league 245 cid=242 slot=133 tier=1 clubs=2 name=SuperLiga Srbije\n")
    data = b"".join([entry(t, 41) for t in (101, 102, 103)] + [entry(t, 553) for t in (9001, 9002, 9003)]
                    + [entry(t, 297) for t in (9101, 9102)] + [entry(t, 600) for t in (9201, 9202)]
                    + [entry(t, 242) for t in (9301, 9302)]
                    + [entry(t, 604) for t in (9001, 9301)]          # a cup of the world, 604 = 92 as a byte
                    + [entry(9003, 41)])                              # a club really in 41 too stays there
    # Mod Studio's line in CommonLib's playable list names the world's ids: 553 is there, a byte never is
    g = Game(world, [41, 92, 242, 553, 297, 600], {41: 52, 242: 245, 92: 777})
    ok("three events are taken: the file's read, the next file, the teams of a match",
       g.handlers() == ["livecpk_make_key", "livecpk_read", "set_teams"])
    ok("the log says how many leagues are past 255",
       any("3 league(s) of the world have a competition id past 255" in s for s in g.log()))
    g.read(data)
    ok("before: CommonLib has the Serbian and the Latvian clubs in the J.League's list (the bug)",
       g.teams(41) == [101, 102, 103, 9001, 9002, 9003, 9101, 9102] and g.teams(553) is None)
    ok("... and a Kick Off between two of them is the J.League's", g.cl.tid_same_league(9001, 9002) == 52)
    g.event()
    ok("after the next event: the J.League's list is its own clubs (and the one really in both)",
       g.teams(41) == [101, 102, 103, 9003])
    ok("each league past 255 has its list under its own id", g.teams(553) == [9001, 9002, 9003]
       and g.teams(297) == [9101, 9102] and g.teams(600) == [9201, 9202])
    ok("a Kick Off between two clubs of Srpska liga Istok is tournament 438, Virsliga's 394, the plain one's 700",
       g.cl.tid_same_league(9001, 9002) == 438 and g.cl.tid_same_league(9101, 9102) == 394
       and g.cl.tid_same_league(9201, 9202) == 700)
    ok("the J.League's own Kick Off and a league of the world under 256 are as before",
       g.cl.tid_same_league(101, 102) == 52 and g.cl.tid_same_league(9301, 9302) == 245 and g.teams(242) == [9301, 9302])
    ok("a cup of the world past 255 (604, byte 92) no longer puts its clubs into league 92's list",
       g.teams(92) == [] and g.cl.tid_same_league(9001, 9301) is None)
    ok("clubs of two different leagues stay an exhibition",
       g.cl.tid_same_league(9001, 9101) is None and g.cl.tid_same_league(101, 9001) is None)
    ok("the tournament's competition id is the whole one", g.cl.tournamentID_to_compID_map[438] == 553)
    ok("the log names the count and an example",
       any("3 league(s) of the world past competition id 255 given to CommonLib" in s and "club(s) taken out" in s
           and "had been read as" in s for s in g.log()))
    # the game reads the file again (live update on / off): CommonLib puts the clubs back, we take them out again
    g.read(data, pieces=3)
    ok("a second read: CommonLib has them in the J.League's list again", 9001 in g.teams(41))
    g.event("set_teams")
    ok("... and the teams of the next match set it right again",
       g.teams(41) == [101, 102, 103, 9003] and g.teams(553) == [9001, 9002, 9003])
    n = len(g.log())
    g.event()
    g.event("set_teams")
    ok("nothing is done when the file was not read again", len(g.log()) == n)

    # no CommonLib in the game: nothing breaks, one line
    g = Game(world, [41], {41: 52})
    g.read(data, commonlib=False)
    g.event()
    g.read(data, commonlib=False)
    g.event()
    ok("no CommonLib: one line in the log, no error", sum("no CommonLib" in s for s in g.log()) == 1)

    # a world with no id past 255 (FL 2026): nothing is registered
    g = Game("league 245 cid=242 slot=133 tier=1 clubs=2 name=SuperLiga Srbije\n", [242], {242: 245})
    ok("a world with no competition id past 255: no event taken", g.handlers() == [])

    if len(sys.argv) >= 2:
        w = sys.argv[1]
        raw = open(os.path.join(w, "common", "etc", "pesdb", "CompetitionEntry.bin"), "rb").read()
        if raw[3:8].lower() == b"wesys":
            raw = zlib.decompress(raw[16:])
        text = open(os.path.join(w, "fl26world.txt"), encoding="utf-8", errors="replace").read()
        leagues = [(int(a), int(b)) for a, b in re.findall(r"^league (\d+) cid=(\d+)", text, re.M)]
        wide = [(i, c) for i, c in leagues if c > 255]
        true = {}
        for o in range(0, len(raw), 12):
            true.setdefault(raw[o + 8] | raw[o + 11] << 8, set()).add(struct.unpack_from("<I", raw, o)[0])
        playable = sorted({c for _i, c in leagues if c <= 255}
                          | {9, 10, 11, 12, 13, 14, 21, 22, 23, 39, 40, 41, 66, 67, 68, 69, 90, 111})
        g = Game(text, playable, {c: i for i, c in leagues if c <= 255})
        g.read(raw, pieces=4)
        mixed = [c for c in playable if g.teams(c) is not None and set(g.teams(c)) - true.get(c, set())]
        print("world: %d leagues, %d past 255; before, %d list(s) of CommonLib hold clubs of another competition"
              % (len(leagues), len(wide), len(mixed)))
        g.event()
        ok("world: no list of CommonLib holds a club that is not in that competition",
           all(set(g.teams(c)) <= true.get(c, set()) for c in playable if g.teams(c) is not None))
        ok("world: every league past 255 has its own clubs under its own id, and its tournament id",
           all(set(g.teams(c) or []) == true.get(c, set()) and g.cl.compID_to_tournamentID_map[c] == i for i, c in wide))
        for i, c in wide[:1] + wide[-1:]:
            t = sorted(true[c])
            ok("world: a Kick Off between two clubs of league %d (competition %d) is tournament %d" % (i, c, i),
               g.cl.tid_same_league(t[0], t[-1]) == i)
        print([s for s in g.log() if "Kick Off" in s][-1])
    else:
        print("skip - no world folder: the built world's file not read")
    print("all %d passed" % N)


if __name__ == "__main__":
    main()
