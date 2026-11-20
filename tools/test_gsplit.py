"""python test_gsplit.py [<world folder> <folder with the game's tables>] -- a play-off place of a
split season of the game's own is the final table's (B425, 11.11.2026).

The Scottish Championship's relegation play-off (GigaPack, cup 724) names the Premiership's 11th
as `entry=134:11`, on the regular phase (33 rounds) of the game's own split season (total 133,
groups 135 and 136). fl26swiss filled the cup from the regular phase's table the day the
Championship ended, the groups still playing, and fl26chain read the entrants off the same table:
in the second season of the Build 5 test the 11th of 33 rounds finished 10th, won the play-off, and
the real 11th went down without a match while the Championship's runner-up went up having lost.

Here: the world file's `gsplit` line (fl26world), the Lua side of both modules (in Lua, with lupa),
and that fl26swiss.c holds the pieces: the export, the gate on the regular phase's progression, the
place from the groups' final tables and the daily look. With a world folder and the game's tables,
from_tables is run on them. What the game does with it is the season test's (two seasons)."""
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fl26world

ROOT = os.path.dirname(HERE)
CHAIN_LUA = os.path.join(ROOT, "sider", "experimental", "fl26chain.lua")
SWISS_LUA = os.path.join(ROOT, "sider", "experimental", "fl26swiss.lua")
SWISS_C = os.path.join(HERE, "native", "fl26swiss.c")
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
    return lj.LuaRuntime()


def chain_poffs(text):
    """fl26chain.lua's read_world on this world file, in Lua: the play-offs' entries and the log"""
    lua = runtime()
    if lua is None:
        return None, None
    src = open(CHAIN_LUA, encoding="utf-8").read()
    head = src[src.index("local APCLAU = {}"):]
    body = head[:re.search(r"^local function read_world\(ctx\).*?^end$", head, re.S | re.M).end()]
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "modules"))
    with open(os.path.join(d, "modules", "fl26world.txt"), "w", encoding="utf-8") as fh:
        fh.write(text)
    f = lua.execute("local LOG = {}\nlocal function log(s) LOG[#LOG + 1] = s end\n" + body
                    + "\nreturn function(dir) read_world({ sider_dir = dir }) return POFFS, LOG end")
    poffs, log = f(d)
    out = []
    for i in range(1, len(poffs) + 1):
        p = poffs[i]
        out.append((p[1], p[2], p[3], [(p[6][k][1], p[6][k][2]) for k in range(1, len(p[6]) + 1)]))
    return out, [log[i] for i in range(1, len(log) + 1)]


def swiss_gsplits(lines):
    """the gsplit block of fl26swiss.lua's read_world, in Lua, on these lines"""
    lua = runtime()
    if lua is None:
        return None
    src = open(SWISS_LUA, encoding="utf-8").read()
    blk = re.search(r"    local gt, grest = line:match.*?\n    end\n", src, re.S).group(0)
    f = lua.execute("return function(lines)\n  local gsplits = {}\n  for _, line in ipairs(lines) do\n" + blk
                    + "  end\n  return gsplits\nend")
    g = f(lua.table_from(lines))
    return [tuple(g[i][k] for k in (1, 2, 3, 4)) for i in range(1, len(g) + 1)]


def main():
    # ---- the world file
    d = tempfile.mkdtemp()
    p = os.path.join(d, "fl26world.txt")
    scot = {"id": 413, "tier": 2, "clubs": 10, "above": 134, "splittotal": 133, "promote": 2, "demote": 2,
            "gsplit": (133, 134, [135, 136]), "name": "Scottish Championship"}
    third = {"id": 414, "tier": 3, "clubs": 10, "above": 413, "promote": 1, "name": "League One"}
    fl26world.write_world(p, "_T", [scot, dict(scot, id=415, name="a second league under it"), third],
                          groups=["poff 724 up=134 low=413 entry=134:11,413:2"])
    text = open(p, encoding="utf-8").read()
    ok("write_world: one gsplit line for a split season of the game's own, whatever the leagues under it",
       re.findall(r"^gsplit .*$", text, re.M) == ["gsplit 133 regular=134 groups=135,136"])
    ok("the league line keeps above= and splittotal=, and carries no gsplit word",
       re.search(r"^league 413 .*above=134 splittotal=133 ", text, re.M) is not None
       and "gsplit" not in re.search(r"^league 413 .*$", text, re.M).group(0))
    fl26world.write_world(p, "_T", [third])
    ok("no league under a shipped split: no gsplit line", "gsplit" not in open(p, encoding="utf-8").read())
    ok("the line is in the module's own description of the file", re.search(r"^  gsplit\s", fl26world.__doc__, re.M) is not None)

    # ---- fl26chain.lua: the play-off's place is the total's
    poffs, log = chain_poffs(open(p, encoding="utf-8").read())
    if poffs is None:
        print("skip - no lupa: the Lua side by its text only")
    else:
        fl26world.write_world(p, "_T", [scot, third], groups=["poff 724 up=134 low=413 entry=134:11,413:2"])
        poffs, log = chain_poffs(open(p, encoding="utf-8").read())
        ok("fl26chain.lua: 134:11 under a shipped split is 133:11, the other entrant and up/low as written",
           poffs == [(724, 134, 413, [(133, 11), (413, 2)])])
        ok("... and the log says so", any("play-off 724" in s and "final table" in s for s in log))
        # a split of ours: the play-off names the group itself and nothing is rewritten
        own = [{"id": 249, "tier": 1, "clubs": 12, "demote": 2, "name": "Super League"},
               {"id": 421, "tier": 2, "clubs": 10, "above": 249, "promote": 2, "name": "Challenge League"}]
        fl26world.write_world(p, "_T", own, splits=[(249, 916, [917, 918])],
                              groups=["poff 778 up=249 low=421 entry=918:5,421:2"])
        poffs, log = chain_poffs(open(p, encoding="utf-8").read())
        ok("a split of the world's own: its play-off is left as written",
           poffs == [(778, 249, 421, [(918, 5), (421, 2)])] and not any("final table" in s for s in log))
        # a plain pair: nothing either
        fl26world.write_world(p, "_T", [{"id": 60, "tier": 1, "clubs": 18, "demote": 2},
                                        {"id": 61, "tier": 2, "clubs": 18, "above": 60, "promote": 2}],
                              groups=["poff 700 up=60 low=61 entry=60:16,61:3"])
        poffs, log = chain_poffs(open(p, encoding="utf-8").read())
        ok("a plain pair: left as written", poffs == [(700, 60, 61, [(60, 16), (61, 3)])])
        g = swiss_gsplits(["gsplit 133 regular=134 groups=135,136", "split 249 regular=916 groups=917,918",
                           "gsplit 141 regular=147 groups=148,175", "gsplit 9 regular=0 groups=1,2", "gsplit 9 regular=5 groups=1"])
        ok("fl26swiss.lua: the gsplit lines read as {total, regular, top, bottom}; a line short of one is left out",
           g == [(133, 134, 135, 136), (141, 147, 148, 175)])

    # ---- the text of both sides
    lua = open(SWISS_LUA, encoding="utf-8").read()
    c = open(SWISS_C, encoding="utf-8").read()
    ok("fl26swiss.lua hands the lines to fl26_swiss_gsplits, four numbers each, and says so of an old DLL",
       'GetProcAddress(h, "fl26_swiss_gsplits")' in lua and "#gsplits * 4" in lua and "no fl26_swiss_gsplits" in lua)
    ok("fl26swiss.c exports fl26_swiss_gsplits and knows the Scottish season without the line",
       re.search(r"__declspec\(dllexport\) int fl26_swiss_gsplits\(const uint16_t\* v, int n\)", c) is not None
       and "g_gsplit[MAX_GSPLIT] = { { 133, 134, { 135, 136 } } }" in c)
    gate = c[c.index("static void ccup_fill_leagues_over("):]
    gate = gate[:gate.index("\n}\n")]
    ok("the regular phase's progression does not end the league while its groups are not played out",
       re.search(r"gsplit_regular\(r\);\s+if \(g && !gsplit_keep\(g\)\) \{.*?return;", gate, re.S) is not None
       and gate.index("gsplit_regular(r)") < gate.index("g_lg_over[r] = year + 1"))
    ok("a progression outside a cup's 60 days before its fill day (the July turn, day 182) does not end the league",
       re.search(r"int f = season_ord\(c->fill\);\s+if \(f <= s \|\| f - s > 60\) continue;\s+for \(unsigned i = 0; i < c->n; i\+\+\) if \(c->ereg\[i\] == r\) mine = 1;", gate) is not None
       and gate.index("mine = 1") < gate.index("g_lg_over[r] = year + 1"))
    club = c[c.index("static uint32_t ccup_club("):]
    club = club[:club.index("\n}\n")]
    ok("a national cup's place of the regular phase comes from the groups' final tables first",
       "gsplit_regular(reg)" in club and club.index("gsplit_club(") < club.index("cwc_club(reg, rank, how)"))
    keep = c[c.index("static int gsplit_keep("):]
    keep = keep[:keep.index("\n}\n")]
    ok("the groups' tables are kept only when every match of the group is played, April to July",
       "d < 100 || d > 200 || !season_played(r)" in keep and "keep_group_final(r, ad)" in keep)
    ok("a world's own split on those ids is not touched", re.search(
        r"static const gsplit_t\* gsplit_live\(const gsplit_t\* g\)\s*\{\s*const split_t\* s;\s*if \(split_part\(g->total", c) is not None)
    ok("the game's own groups are looked at every day (the game may not ask for their progression) and on their progression",
       re.search(r"done_day\[after\] = ad;\s+gsplit_day\(\);", c) is not None
       and re.search(r"gsplit_group\(r\);\s+if \(g && gsplit_keep\(g\)\) ccup_fill_leagues_over\(g->regular, started\);", c) is not None)
    ok("a group's table can be counted from the matches for the game's own groups too",
       re.search(r"if \(split_part\(reg, &sp\) != 3\) \{\s+const gsplit_t\* g = gsplit_group\(reg\);", c) is not None)
    ok("the short path's log names the group's first and last club (splitcheck.py reads them)",
       c.count("split group's final table kept for the season end (day %d, %d clubs): %08x first, %08x last") == 2)

    # ---- the tables
    if len(sys.argv) >= 3:
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            leagues, _splits = fl26world.from_tables(sys.argv[1], sys.argv[2])
        gs = {L["id"]: L.get("gsplit") for L in leagues if L.get("splittotal")}
        print("leagues under a shipped split:", gs)
        ok("every league under a shipped split season names its groups", gs and all(v for v in gs.values()))
        for lid, v in gs.items():
            L = next(x for x in leagues if x["id"] == lid)
            ok("league %d: gsplit (%d, %d, %s) is its splittotal and above" % (lid, v[0], v[1], v[2]),
               v[0] == L["splittotal"] and v[1] == L["above"] and len(v[2]) == 2 and len(set(v[2])) == 2)
        if 413 in gs:
            ok("the Scottish Championship stands under 133 / 134 / 135, 136", gs[413] == (133, 134, [135, 136]))
    else:
        print("skip - no world folder and tables: from_tables not run")
    print("all %d passed" % N)


if __name__ == "__main__":
    main()
