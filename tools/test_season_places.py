r"""python tools/test_season_places.py <folder with the game's tables> [--keep]

Colombia's places by the whole season (Vicentico, 04.11.2026: "the continental places of the
DIMAYOR count only the Apertura"). The game plays Colombia's Liga BetPlay DIMAYOR (reg 119) as two
tournaments with a table each, 168 (I) and 169 (II), and the MLS (51) as 166 and 167. A place
given to the first tournament goes by its table alone; the European places dialog now also lists
the whole season (game_europe_tops), and a place given to it goes by both tables added together
(fl26swiss: the world file's seasonsum line, test_season_sum.py).

Here, without the game:
  - game_season_totals finds both seasons in the game's tables, halves in order;
  - game_europe_tops lists the whole season right after its first tournament, with its clubs;
  - a recipe with places on 119 plans: the access list names 119, the Copa Sudamericana's place
    of 119 is the cup's, and its shipped fill of Colombia's comes from 119 too (no club of
    Colombia twice from two tables), Check the plan shows Colombia's share;
  - a recipe with places on 168 plans and builds exactly as before: no seasonsum line;
  - places on 119 and on 168 together are refused, with both names;
  - the world built offline has `seasonsum 119 parts=168,169` and the access line of 119;
  - the MLS: places on 51 (the CONCACAF Champions Cup) give `seasonsum 51 parts=166,167`.
The worlds are built into a temporary game folder; --keep leaves it.
"""
import json, os, re, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import leaguebuilder as B
import fl26world

N = 0
COL, COL_I, COL_II, MLS, MLS_I, MLS_II = 119, 168, 169, 51, 166, 167


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def regrow_of(base):
    regs = B.M.load(base, "CompetitionRegulation.bin")
    return {B.u16(regs[i * B.M.REG:], B.M.R_ID): regs[i * B.M.REG:(i + 1) * B.M.REG]
            for i in range(len(regs) // B.M.REG)}


def recipe(world, ge):
    return {"world": world,
            "leagues": [{"name": "SP Peru", "country": "Peru", "clubs": 12, "legs": 2,
                         "europe": [[1, 3], [2, 9], [3, 9], [4, 9]]}],
            "game_europe": ge}


def world_dir(game, world):
    return os.path.join(game, "SiderAddons", "livecpk", world)


def build(base, game, r):
    log = []
    try:
        B.build(B.plan(r, base), base, game, False, log=log.append)
    except Exception:
        print("\n".join("# " + l for l in log[-30:]))
        raise
    with open(os.path.join(world_dir(game, r["world"]), "fl26world.txt"), encoding="utf-8") as f:
        return f.read()


def main(base, keep=False):
    rows = regrow_of(base)
    tot = B.game_season_totals(rows)
    ok("the game's seasons of two tournaments: Colombia 119 = 168 + 169, the MLS 51 = 166 + 167",
       tot.get(COL) == [COL_I, COL_II] and tot.get(MLS) == [MLS_I, MLS_II])
    tops = B.game_europe_tops(base)
    ids = [t[0] for t in tops]
    ok("the places dialog lists the whole season right after its first tournament",
       COL in ids and ids.index(COL) == ids.index(COL_I) + 1 and ids.index(MLS) == ids.index(MLS_I) + 1)
    by = {t[0]: t for t in tops}
    ok("... under the league's own name, with its clubs",
       by[COL][1] == "Liga BetPlay DIMAYOR" and by[COL][2] == by[COL_I][2] >= 18)

    whole = recipe("_TestSeasonWhole", {str(COL): [[1, 3], [2, 3], [3, 4], [4, 9], [5, 9]]})
    pl = B.plan(whole, base)
    ok("places on 119: the plan's seasonsum entry", pl["season_sums"] == [[COL, COL_I, COL_II]])
    ok("... the access list names 119 itself",
       sorted(tuple(e) for e in pl["game_europe"] if e[0] == COL) == [(COL, 1, 3, 0), (COL, 2, 3, 0), (COL, 3, 4, 0)])
    sud = next(c for c in pl["ccups"] if c["number"] == 9)
    col = [tuple(e) for e in sud["entry"] if e[0] in (COL, COL_I, COL_II)]
    ok("... the Copa Sudamericana's Colombian places all from the whole season, none twice",
       col and all(e[0] == COL for e in col) and len(col) == len(set(col))
       and (COL, 4) in col and (COL, 5) in col)
    lines = B.samerica_lines(B.own_places(pl), {}, pl["ccups"])
    ok("... Check the plan counts them as Colombia's share",
       any("Liga BetPlay (Colombia)" in l and "Copa Sudamericana %d clubs" % len(col) in l for l in lines))

    half = recipe("_TestSeasonHalf", {str(COL_I): [[1, 3], [2, 3], [3, 4], [4, 9], [5, 9]]})
    ph = B.plan(half, base)
    ok("places on 168: no seasonsum, the places of 168 as before",
       ph["season_sums"] == [] and all(e[0] == COL_I for e in ph["game_europe"]))
    sudh = next(c for c in ph["ccups"] if c["number"] == 9)
    ok("... the Sudamericana fills from 168 as before",
       all(e[0] != COL for e in sudh["entry"]) and (COL_I, 4) in [tuple(e) for e in sudh["entry"]])

    both = recipe("_TestSeasonBoth", {str(COL): [[1, 3]], str(COL_I): [[2, 3]]})
    try:
        B.plan(both, base)
        refused = ""
    except B.BuildError as e:
        refused = str(e)
    ok("places on 119 and 168 together: refused, both named",
       "Liga BetPlay DIMAYOR I" in refused and "whole season" in refused)
    empty = recipe("_TestSeasonEmpty", {str(COL): [[1, 3]], str(COL_I): []})
    ok("... an empty list on 168 (the modern competitions' default) is not a place", B.plan(empty, base)["season_sums"])

    game = tempfile.mkdtemp(prefix="fl26-seasonsum-")
    try:
        w = build(base, game, whole)
        ok("the world file: seasonsum 119 parts=168,169", "seasonsum 119 parts=168,169" in w.splitlines())
        ok("... the access list's places of 119", {"uefa 119 1 3 0", "uefa 119 2 3 0", "uefa 119 3 4 0"}
           <= set(w.splitlines()) and not re.search(r"^uefa 16[89] ", w, re.M))
        sud = next(l for l in w.splitlines() if l.startswith("ccup ") and "name=Copa Sudamericana" in l)
        ok("... the Copa Sudamericana's entries of Colombia all 119", "119:4" in sud and not re.search(r"\b16[89]:", sud))
        wh = build(base, game, half)
        ok("a world with places on 168: no seasonsum line", "seasonsum" not in wh)
        mls = recipe("_TestSeasonMls", {str(MLS): [[1, 13], [2, 13], [3, 13], [4, 13]]})
        mls["leagues"][0]["europe"] = [[1, 3], [2, 4]]
        wm = build(base, game, mls)
        ok("the MLS: seasonsum 51 parts=166,167", "seasonsum 51 parts=166,167" in wm.splitlines())
    finally:
        if keep:
            print("# kept %s" % game)
        else:
            shutil.rmtree(game, ignore_errors=True)
    print("1..%d" % N)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0].startswith("-"):
        sys.exit(__doc__)
    main(a[0], "--keep" in a)
