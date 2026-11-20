"""python test_b494_colombia_chain.py [<GigaPack world zip or fl26world.txt>] -- B494 (antonimus
17.11.2026): in the GigaPack world Primera C Especial (428) and Primera C (960) never exchanged
clubs at New Year.

Colombia's top league of the game is a season of two tournaments (Liga BetPlay 119 = 168 + 169,
the world file's `seasonsum 119 parts=168,169`), and under it (168) the game exchanges nobody
(B330). The game's every-other-pair therefore starts one tier lower, at 340<->428, and skips
428<->960; fl26chain.lua's from_world went by the tier alone and took 340->428 (0 clubs each way)
as the skipped pair, so nobody moved 428<->960. Now from_world counts the tiers from the top of
our chain when that top is under a half (read_world's seasonsum): 428->960 is a chain of ours,
340->428 is not. Nothing else changes: every other league's pairs are the old rule's, checked
on the released GigaPack beta 3 world when it is there (argument, FL26_B494_WORLD, or
E:/FL/objava_b4/_FL26Megapack-beta3.zip).

fl26join.dll now says why such a pair is not exchanged at the New Year teardown ("new year:
428<->960 -- a league of the game's in the region, left to the game's season end"): cal_left,
built natively with FL26_JOIN_TEST when zig is there.

Needs lupa (pip install lupa) for the Lua parts; without it they are skipped."""
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
NATIVE = os.path.join(HERE, "native")
CHAIN_LUA = os.path.join(ROOT, "sider", "experimental", "fl26chain.lua")
JOIN_C = os.path.join(NATIVE, "fl26join.c")
GP3 = "E:/FL/objava_b4/_FL26Megapack-beta3.zip"
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


def lua_world(text):
    """fl26chain.lua's read_world + from_world on this world file text: (chains, leagues by id),
    the chains as tuples (None without lupa)"""
    rt = runtime()
    if rt is None:
        return None
    src = open(CHAIN_LUA, encoding="utf-8").read()
    chunk = re.search(r"^local APCLAU = \{\}$.*?^local function from_world\(world\).*?^end$", src, re.S | re.M).group(0)
    f = rt.execute("local function log() end\n" + chunk + "\nreturn function(ctx) local w = read_world(ctx) "
                   "local ch = from_world(w) return ch, w end")
    d = tempfile.mkdtemp(prefix="b494-")
    try:
        os.makedirs(os.path.join(d, "modules"))
        with open(os.path.join(d, "modules", "fl26world.txt"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        ch, w = f(rt.table_from({"sider_dir": d.replace("/", "\\") + "\\"}))
    finally:
        shutil.rmtree(d, ignore_errors=True)
    chains = [tuple(ch[i][k] for k in range(1, 6)) for i in range(1, len(ch) + 1)]
    leagues = {}
    for i in range(1, len(w) + 1):
        L = w[i]
        leagues[L["id"]] = {k: L[k] for k in L.keys()}
    return chains, leagues


def old_rule(leagues_in_order):
    """the chains from_world made before B494 (the tier alone), for the no-change check"""
    out = []
    for L in leagues_in_order:
        tier, above = L.get("tier"), L.get("above")
        if L.get("group"):
            continue
        if above and tier and ((tier >= 3 and (tier % 2 == 1 or tier >= 6)) or L.get("splitabove")):
            n = L["promote"] if L.get("promote") is not None else 3
            out.append((above, L["id"], n, n, L.get("splitabove") or 0))
        elif above and L.get("splittotal"):
            n = L["promote"] if L.get("promote") is not None else 3
            out.append((L["splittotal"], L["id"], n, n, above))
    return out


COLOMBIA = """\
league 340 cid=226 region=19 country=148 conf=4 slot=202 tier=2 above=168 promote=2 demote=0 clubs=16 legs=2 cup=126 scup=131 kickoff=99 name=Primera B de Colombia
league 428 cid=543 region=19 country=148 conf=4 slot=290 tier=3 above=340 promote=0 demote=2 clubs=30 legs=1 kickoff=202 name=Primera C Especial
league 960 cid=703 region=19 country=148 conf=4 slot=402 tier=4 above=428 promote=2 demote=0 clubs=19 legs=1 kickoff=290 name=Primera C
"""
# a country with five tiers under a league of the game that is no half (the old rule: 3, 5)
OTHER = """\
league 600 region=30 tier=2 above=50 promote=3 demote=3 clubs=20 name=Two
league 601 region=30 tier=3 above=600 promote=3 demote=3 clubs=20 name=Three
league 602 region=30 tier=4 above=601 promote=2 demote=2 clubs=18 name=Four
league 603 region=30 tier=5 above=602 promote=2 demote=0 clubs=18 name=Five
"""
USL = "league 332 cid=217 region=23 country=135 conf=6 slot=194 tier=2 above=166 promote=0 demote=0 clubs=25 legs=2 cup=54 kickoff=17 name=USL Championship\n"
SUMS = "seasonsum 119 parts=168,169\nseasonsum 51 parts=166,167\n"


def world_text(arg):
    p = arg or os.environ.get("FL26_B494_WORLD") or GP3
    if not os.path.exists(p):
        return None, p
    if p.lower().endswith(".zip"):
        with zipfile.ZipFile(p) as z:
            name = next((n for n in z.namelist() if n.endswith("/fl26world.txt")), None)
            return (z.read(name).decode("utf-8") if name else None), p
    return open(p, encoding="utf-8").read(), p


def lua_part(arg):
    got = lua_world(COLOMBIA + OTHER + USL + SUMS)
    if got is None:
        print("skip - Lua (pip install lupa to run it)")
        return
    chains, L = got
    ok("read_world: 340 is under a half of 119 (halfabove), 428 and 960 are not", L[340].get("halfabove") == 119
       and L[428].get("halfabove") is None and L[960].get("halfabove") is None)
    ok("Colombia: 428 -> 960 is a chain of ours, 2 down and 2 up", (428, 960, 2, 2, 0) in chains)
    ok("Colombia: 340 -> 428 is not (the game's pair, 0/0 anyway)", not any(c[:2] == (340, 428) for c in chains))
    ok("Colombia: no chain 168 -> 340 (B330 is a decision of its own)", not any(c[1] == 340 for c in chains))
    ok("the other country: tiers 3 and 5 as before (600->601, 602->603), not 601->602",
       [c for c in chains if c[1] in (600, 601, 602, 603)] == [(600, 601, 3, 3, 0), (602, 603, 2, 2, 0)])
    ok("the USL under the MLS half 166: no chain (nothing below it)", not any(332 in c[:2] for c in chains))

    # without the seasonsum line nothing is shifted: the old pairs (the line is what says 168 is a half)
    chains2, _ = lua_world(COLOMBIA + OTHER)
    ok("no seasonsum line: Colombia as before (340->428, no 428->960)",
       (340, 428, 0, 0, 0) in chains2 and not any(c[:2] == (428, 960) for c in chains2))

    # a deeper Colombia: tiers counted from 340, so 960 (3rd from 340) and 962 (5th) are ours, 961 not
    deep = COLOMBIA + ("league 961 region=19 tier=5 above=960 promote=2 demote=2 clubs=16 name=C2\n"
                       "league 962 region=19 tier=6 above=961 promote=2 demote=0 clubs=16 name=C3\n") + SUMS
    chains3, _ = lua_world(deep)
    ok("deeper chain under a half: 428->960 and 961->962 ours, 960->961 the game's",
       [c[:2] for c in chains3] == [(428, 960), (961, 962)])

    text, path = world_text(arg)
    if text is None:
        print("skip - the GigaPack beta 3 world (%s not found)" % path)
        return
    chains, L = lua_world(text)
    before = old_rule(list(L.values()))           # the world's order, as read_world keeps it
    gone, new = sorted(set(before) - set(chains)), sorted(set(chains) - set(before))
    print("# %s: %d leagues, %d chains (before %d)" % (os.path.basename(path), len(L), len(chains), len(before)))
    ok("GigaPack beta 3: the only chain gone is 340->428", gone == [(340, 428, 0, 0, 0)])
    ok("GigaPack beta 3: the only chain new is 428->960", new == [(428, 960, 2, 2, 0)])
    ok("GigaPack beta 3: every league with halfabove is Colombia's 340",
       [i for i, x in L.items() if x.get("halfabove")] == [340])
    ok("GigaPack beta 3: the chain count stays under MAX_CHAINS (256)", len(chains) <= 256)


def find_zig():
    z = os.environ.get("ZIG")
    if z and os.path.exists(z):
        return z
    z = shutil.which("zig")
    if z:
        return z
    found = sorted(glob.glob("D:/dev/tools/zig-*/zig.exe"))
    return found[-1] if found else None


NATIVE_TEST = r"""
#define FL26_JOIN_TEST
#include "fl26join.c"
#include <stdio.h>
int main(void)
{
  /* Colombia's two pairs and a pair of a country with no league of the game's (exchanged by
     cal_exchange, not said here), and a pair whose lower league closed in another teardown */
  uint16_t pairs[] = { 340, 428, 0,  428, 960, 2,  11, 49, 2,  600, 601, 3 };
  fl26_join_cal_pairs(pairs, 4);
  g_log_len = 0;
  uint16_t alone[] = { 11, 49 }, game[] = { 340, 428, 960, 600 };
  cal_left(alone, 2, game, 4);
  g_log[g_log_len] = 0;
  printf("%s", g_log);
  g_cpair_done[1] = 1; g_log_len = 0;
  cal_left(alone, 2, game, 4);
  g_log[g_log_len] = 0;
  printf("--\n%s", g_log);
  return 0;
}
"""


def native_part():
    src = open(JOIN_C, encoding="utf-8").read()
    ok("fl26join.c: teardown_pre says the pairs it leaves to the game (cal_left after cal_exchange)",
       re.search(r"if \(nalone && g_ncpair\) cal_exchange\(alone, nalone\);\s+if \(ngame && g_ncpair\) "
                 r"cal_left\(alone, nalone, withgame, ngame\);", src) is not None)
    ok("fl26join.c: cal_left only logs (no list written in it)",
       "SETCLUBS_RVA" not in re.search(r"static void cal_left\(.*?\n\}", src, re.S).group(0))
    zig = find_zig()
    if not zig:
        print("skip - native cal_left (no zig; set ZIG)")
        return
    d = tempfile.mkdtemp(prefix="b494n-")
    try:
        c, exe = os.path.join(d, "t.c"), os.path.join(d, "t.exe")
        open(c, "w").write(NATIVE_TEST)
        subprocess.run([zig, "cc", "-O2", "-fno-sanitize=undefined", "-w", "-I", NATIVE, c, "-o", exe], check=True)
        out = subprocess.run([exe], capture_output=True, text=True, timeout=60).stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)
    first, second = out.split("--\n")
    lines = [l for l in first.splitlines() if l.startswith("new year:")]
    ok("cal_left: 340<->428 and 428<->960 said, left to the game's season end",
       lines == ["new year: 340<->428 -- a league of the game's in the region, left to the game's season end",
                 "new year: 428<->960 -- a league of the game's in the region, left to the game's season end"])
    ok("cal_left: the pair of ours exchanged by cal_exchange (11<->49) and a pair half closed (600<->601) not said",
       "11<->49" not in first and "600<->601" not in first)
    ok("cal_left: a pair done this New Year is not said", "428<->960" not in second and "340<->428" in second)


if __name__ == "__main__":
    lua_part(sys.argv[1] if len(sys.argv) > 1 else None)
    native_part()
    print("all %d checks passed" % N)
