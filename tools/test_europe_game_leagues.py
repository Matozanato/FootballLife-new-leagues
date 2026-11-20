"""python test_europe_game_leagues.py [<folder with the game's tables>] -- request #5 (06.11.2026):
the European places of the game's own leagues.

FL 2027 plays Belgium's top division as one league of 18 at regulation 115, with no split: the
access list's 155 (FL26's regular phase, fl26swiss.c R_BEL) is not in its tables, so the DLL found
no table for it and Belgium had no club in Europe. Where the tables in use have no 155 the plan
carries access_alias {"155": 115}: the world file lists the shipped places with 115 in 155's place
(uefa lines, even in a world with no places of its own), the European places dialog shows
Belgium's places, game_europe replaces them, and the association ranking knows 115 as Belgium.
FL26's tables have 155: no alias, no uefa lines for a world without places, all as before.

Without the tables only the plan-free parts run; with them the checks follow the tables given
(FL26's or FL 2027's)."""
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fl26world as W
import leaguebuilder as B
import mkleague as M

N = 0
BEL, BEL27 = 155, 115


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def offline():
    alias = {"155": 115}
    moved = W.shipped_access(alias)
    ok("the shipped list keeps its length and order with an alias",
       len(moved) == len(W.SHIPPED_ACCESS) and [e[1:] for e in moved] == [e[1:] for e in W.SHIPPED_ACCESS])
    ok("Belgium's nine places go to 115, none stays on 155",
       sum(1 for e in moved if e[0] == BEL27) == 9 and not any(e[0] == BEL for e in moved))
    ok("no alias: the list as it is", W.shipped_access(None) is W.SHIPPED_ACCESS and W.shipped_access({}) is W.SHIPPED_ACCESS)
    ok("no places, no alias: no uefa lines (the DLL's own list stands)", W.uefa_places([], ()) == ([], {}))
    out, over = W.uefa_places([], (), True, None, alias)
    ok("no places of its own but an alias: the whole shipped list, Belgium on 115",
       sorted(out) == sorted(moved) and not over)
    ok("the same qualifying rounds as the DLL's own list",
       W.pick_rounds(out) == W.pick_rounds(list(W.SHIPPED_ACCESS)))
    out, _over = W.uefa_places([], [BEL27], True, None, alias)
    ok("game_europe replacing 115 drops the moved places", not any(e[0] in (BEL, BEL27) for e in out))


def regrow_of(base):
    regs = M.load(base, "CompetitionRegulation.bin")
    return {B.u16(regs[i * M.REG:], M.R_ID): regs[i * M.REG:(i + 1) * M.REG] for i in range(len(regs) // M.REG)}


def game_dir():
    game = tempfile.mkdtemp(prefix="fl26-europegame-")
    for d in ("livecpk", "modules", "content"):
        os.makedirs(os.path.join(game, "SiderAddons", d))
    with open(os.path.join(game, "SiderAddons", "sider.ini"), "w") as f:
        f.write("[sider]\n")
    return game


def build(recipe, base):
    """the plan and the world file's uefa lines [(reg, position, competition, alt)]"""
    game, fl27 = game_dir(), B.FL27      # build() takes the game's own (use_game): this folder is none
    try:
        pl = B.plan(recipe, base)
        B.build(pl, base, game, False, log=lambda t: None)
        text = open(os.path.join(game, "SiderAddons", "livecpk", recipe["world"], "fl26world.txt"),
                    encoding="utf-8").read()
        return pl, [tuple(int(x) for x in m.groups())
                    for m in re.finditer(r"^uefa (\d+) (\d+) (\d+) (\d+)\s*$", text, re.M)]
    finally:
        B.FL27 = fl27
        shutil.rmtree(game, ignore_errors=True)


def small(**more):
    r = {"world": "_FL26EuropeGame", "leagues": [
        {"name": "Zel Top", "country": "San Marino", "clubs": 18, "legs": 2, "exchange": 0}]}
    r.update(more)
    return r


def built(base):
    regrow = regrow_of(base)
    fl27 = BEL not in regrow
    print("# tables: %s" % ("FL 2027's (no 155)" if fl27 else "FL26's (155 there)"))
    alias = B.access_alias(regrow)
    ok("access_alias: %s" % alias, alias == ({"155": BEL27} if fl27 else {}))
    tops = {r: s for r, _n, _c, s in B.game_europe_tops(base)}
    ok("the European places dialog shows the Jupiler Pro League's nine places (%s)" % tops.get(BEL27),
       len(tops.get(BEL27) or []) == 9 and [1, 0] in tops[BEL27])

    pl, uefa = build(small(), base)
    ok("the plan keeps the alias", pl.get("access_alias") == alias)
    if fl27:
        ok("an FL 2027 world with no places of its own lists the shipped ones (%d)" % len(uefa),
           sorted(uefa) == sorted(W.shipped_access(alias)))
        ok("Belgium's champion in the Champions League, from 115", (BEL27, 1, 0, 0) in uefa)
        ok("nothing on 155", not any(e[0] == BEL for e in uefa))
        rank = B.place_rank(pl)
        ok("115 ranks as Belgium in the qualifying's order", rank and rank.get(BEL27) == rank.get(BEL) != W.UNRANKED)
    else:
        ok("FL26: a world with no places of its own has no uefa lines, as before", uefa == [])

    pl, uefa = build(small(game_europe={str(BEL27): [[1, 0], [2, 1]]}), base)
    bel = sorted(e[1:3] for e in uefa if e[0] in (BEL, BEL27))
    ok("game_europe gives Belgium places of its own (%s), the shipped ones go" % bel, bel == [(1, 0), (2, 1)])
    ok("on the regulation the tables have", all(e[0] == (BEL27 if fl27 else BEL) for e in uefa if e[0] in (BEL, BEL27)))
    lines = B.describe(pl)
    ok("the summary names them", "European places of" in lines and "Jupiler" in lines)


if __name__ == "__main__":
    offline()
    if len(sys.argv) > 1:
        built(sys.argv[1])
    print("1..%d" % N)
