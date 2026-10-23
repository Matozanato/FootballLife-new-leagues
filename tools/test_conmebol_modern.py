r"""python tools/test_conmebol_modern.py <folder with the game's tables> [--keep]

The modern CONMEBOL competitions (PR #146, vmardonesdev: Libertadores qualifying in three phases,
a Copa Sudamericana with a first stage and a play-off, the Recopa Sudamericana) are there only
when the user picks them, and keep their ids. The three blockers of our review of #146:

 1. a world with Libertadores, Libertadores qualifying or Copa Sudamericana places (3, 4, 9) and
    nothing else of the modern competitions became a modern world, and Build refused it ("modern
    CONMEBOL setup is incomplete": the FL26 Modpack r7 went from building to exit code 2). Such a
    recipe now plans and builds the classic competitions as before: no phases, no first stage, no
    Recopa, no helper competition, the Sudamericana dated as before;
 2. the League dialog's competition list left out Libertadores qualifying, and OK made such a
    place a Champions League place without a word: the place keeps its competition (with Qt);
 3. the helper competitions (the Sudamericana's first stage and play-off, the Libertadores'
    phases 1 and 2) took the first free competition and regulation ids every Build, so a league
    added later moved them, and a career holds them. They are kept like every cup's (pinned_ids):
    a modern world built, then built again with a new league (and its national and super cup) in
    front, keeps every CONMEBOL id.

Plan level, the switch (recipe "conmebol": "modern"), what turning it off takes out, the plan read
back into a recipe (recipe_from_plan) keeping it. The worlds are built offline into a temporary
game folder (nothing of the real game is touched). --keep leaves the temporary folder.
"""
import copy, json, os, re, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import leaguebuilder as B
import fl26world

N = 0
BRA, ARG, CHI, COL = 29, 30, 67, 168          # the game's South American top divisions (fl26world.SAM_GAME)
HELPERS = ("conmebol:" + B.SAM_FIRST_CODE, "conmebol:" + B.SPO_CODE, "conmebol:" + B.LIBQ_CODE)


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def classic():
    """a world as every one before 0.2.5: new South American leagues and a league of the game with
    Libertadores, qualifying and Copa Sudamericana places"""
    return {"world": "_TestConmebolClassic",
            "leagues": [{"name": "CL Bolivia", "country": "Bolivia", "clubs": 12, "legs": 2, "cup": True,
                         "europe": [[1, 3], [2, 3], [3, 4], [4, 9], [5, 9], [0, 9]]},
                        {"name": "CL Peru", "country": "Peru", "clubs": 12, "legs": 2,
                         "europe": [[1, 3], [2, 4], [3, 9], [4, 9]]}],
            "game_europe": {str(CHI): [[1, 3], [2, 4], [3, 9]]}}


def modern():
    """a complete modern field: 26 Libertadores group places, 13 in phase 2, 6 in phase 1, 12
    Copa Sudamericana group places and 32 in its first stage, dealt in turn over six new leagues
    and the game's four South American top divisions"""
    new = [("MO Bolivia", "Bolivia", 16), ("MO Ecuador", "Ecuador", 16), ("MO Paraguay", "Paraguay", 12),
           ("MO Peru", "Peru", 18), ("MO Uruguay", "Uruguay", 16), ("MO Venezuela", "Venezuela", 14)]
    game = [(BRA, 20), (ARG, 28), (CHI, 16), (COL, 20)]
    sources = [(n, c) for n, _k, c in new] + game
    nxt = {s: 1 for s, _c in sources}
    places = {s: [] for s, _c in sources}
    k = 0
    for comp in [3] * 26 + [fl26world.LIB_F2] * 13 + [fl26world.LIB_F1] * 6 + [9] * 12 + [fl26world.SUD_FIRST] * 32:
        for _ in range(len(sources)):
            s, clubs = sources[k % len(sources)]
            k += 1
            if nxt[s] <= clubs:
                places[s].append([nxt[s], comp])
                nxt[s] += 1
                break
    return {"world": "_TestConmebolModern", "conmebol": "modern",
            "leagues": [{"name": n, "country": cty, "clubs": c, "legs": 2, "europe": places[n]} for n, cty, c in new],
            "game_europe": {str(rid): places[rid] for rid, _c in game}}


def world_dir(game, world):
    return os.path.join(game, "SiderAddons", "livecpk", world)


def build(base, game, recipe):
    """recipe built over the plan its world folder already has (the builder page's way)"""
    path = os.path.join(world_dir(game, recipe["world"]), "leaguebuilder-plan.json")
    prev = None
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            prev = json.load(f)
    log = []
    try:
        B.build(B.plan(recipe, base, prev), base, game, prev is not None, log=log.append)
    except Exception:
        print("\n".join("# " + l for l in log[-30:]))
        raise
    with open(path, encoding="utf-8") as f:
        pl = json.load(f)
    with open(os.path.join(world_dir(game, recipe["world"]), "fl26world.txt"), encoding="utf-8") as f:
        return pl, f.read()


def switch(base):
    """the recipe's "conmebol" and the places only the modern competitions have"""
    r = classic()
    ok("Libertadores, qualifying and Sudamericana places alone: the classic competitions",
       not B.recipe_has_modern_conmebol(r))
    ok('"conmebol": "modern" picks the modern ones', B.recipe_has_modern_conmebol(dict(r, conmebol="modern")))
    for comp in sorted(fl26world.CONMEBOL_STAGE_IDS):
        x = copy.deepcopy(r)
        x["leagues"][1]["europe"].append([6, comp])
        ok("a place in %s means them too" % fl26world.CONMEBOL_STAGE_TARGETS[comp][0], B.recipe_has_modern_conmebol(x))
    ok("a place of a game league in phase 1 means them too",
       B.recipe_has_modern_conmebol(dict(r, game_europe={str(BRA): [[1, fl26world.LIB_F1]]})))
    ok("a CONMEBOL country without a league means them too",
       B.recipe_has_modern_conmebol(dict(r, conmebol_associations={"Bolivia": [[1, 3]]})))
    try:
        B.recipe_has_modern_conmebol(dict(r, conmebol="new"))
        bad = False
    except B.BuildError:
        bad = True
    ok("a conmebol value other than modern is refused", bad)

    x = modern()
    x["conmebol_associations"] = {"Bolivia": [[1, 9]]}
    gone = B.drop_modern_conmebol(x)
    left = [e for L in x["leagues"] for e in L["europe"]] + [e for v in x["game_europe"].values() for e in v]
    ok("switched off: the %d places only they have go (phases, first stage, the association)" % gone,
       gone == 13 + 6 + 32 + 1 and not any(e[1] in fl26world.CONMEBOL_STAGE_IDS for e in left)
       and "conmebol" not in x and "conmebol_associations" not in x)
    ok("and the Libertadores and Sudamericana places stay",
       sum(e[1] == 3 for e in left) == 26 and sum(e[1] == 9 for e in left) == 12)
    ok("the world is then a classic one", not B.recipe_has_modern_conmebol(x))
    ok("a recipe with conmebol is an edit of the game (has_edits)", B.has_edits({"conmebol": "modern"}))

    pl = B.plan(modern(), base)
    ok("the modern field plans: phases 1 and 2, the first stage",
       pl["modern_libertadores_access"] == "custom" and pl["libq"] and pl["suda_first"])
    back = B.recipe_from_plan(pl, base)
    ok("read back from the plan (a ready world made editable) it is still modern",
       back.get("conmebol") == "modern" and B.recipe_has_modern_conmebol(back))


def classic_world(base, game):
    """blocker 1: the classic recipe plans and builds, without anything of the modern competitions"""
    r = classic()
    pl = B.plan(r, base)
    ok("classic: planned as vanilla, no phases, no first stage, no stages",
       pl["modern_libertadores_access"] == "vanilla" and not pl["libq"] and not pl["suda_first"]
       and not pl["conmebol_stages"])
    codes = [c.get("code") for c in pl["ccups"]]
    ok("classic: no Recopa Sudamericana (it is a modern competition)", "FL_SAMRC" not in codes)
    sud = next(c for c in pl["ccups"] if c["number"] == B.SUDAM)
    ok("classic: the Copa Sudamericana is the classic cup (8 groups of 4, no February-December dates)",
       sud["groups"] == 8 and not (sud.get("opts") or {}).get("cal"))
    # the World Modpack (mato 23.10.): sudamericana_calendar puts the classic cup on February-December
    pc = B.plan(dict(classic(), sudamericana_calendar=True), base)
    sc = next(c for c in pc["ccups"] if c["number"] == B.SUDAM)
    ok("classic with sudamericana_calendar: the same cup, filled in February on the Libertadores' days",
       sc["groups"] == 8 and sc["entry"] == sud["entry"]
       and sc.get("opts") == {"fill": B.SAM_GROUP_FILL, "national": 0, "days": [], "cal": 1}
       and not pc["suda_first"] and "FL_SAMRC" not in [c.get("code") for c in pc["ccups"]])
    ok("and read back from the plan it keeps the setting",
       B.recipe_from_plan(pc, base).get("sudamericana_calendar") is True)
    built, text = build(base, game, r)
    ok("classic: Build makes the world (the Modpack r7 was refused)", True)
    ok("classic: no helper competition ids", not any(k.startswith("conmebol:") for k in built["cup_ids"]))
    ok("classic: the world file has no first stage, play-off or phase lines, no cal=1",
       not re.search(r"^lpre .*(single=1|poko=1|feed=)", text, re.M) and " cal=1" not in text)
    ok("classic: and no Recopa", "Recopa" not in text)


def modern_world(base, game):
    """blocker 3: the helper competitions keep their ids from Build to Build"""
    r = modern()
    one, text1 = build(base, game, r)
    ids1 = {k: v for k, v in one["cup_ids"].items() if k.startswith(("conmebol:", "ccup:"))}
    ok("modern: Build makes the world with the three helper competitions", all(k in ids1 for k in HELPERS))
    ok("modern: and the Copa Sudamericana and the Recopa", "ccup:FL_SUDAM" in ids1 and "ccup:FL_SAMRC" in ids1)
    lpre1 = sorted(l for l in text1.splitlines() if l.startswith("lpre "))
    ok("modern: four pre-round lines (first stage, play-off, phases 1 and 2)", len(lpre1) == 4)
    cids = [w["cid"] for w in ids1.values()]
    regs = [v for w in ids1.values() for f, v in w.items() if f != "cid" and not (f == "ko" and v == w.get("reg"))]
    ok("modern: no two of them share a competition or regulation id",
       len(set(cids)) == len(cids) and len(set(regs)) == len(regs))

    # a league with its national and super cup in front: it takes ids, the CONMEBOL ones stay
    more = copy.deepcopy(r)
    more["leagues"].insert(0, {"name": "MO Albania", "country": "Albania", "clubs": 10, "legs": 2,
                               "cup": True, "supercup": True})
    two, text2 = build(base, game, more)
    ids2 = {k: v for k, v in two["cup_ids"].items() if k.startswith(("conmebol:", "ccup:"))}
    ok("modern, a league added in front: every CONMEBOL competition keeps its ids (%s)"
       % "; ".join("%s %s -> %s" % (k, ids1[k], ids2.get(k)) for k in ids1 if ids1[k] != ids2.get(k)),
       ids1 == ids2)
    lpre2 = sorted(l for l in text2.splitlines() if l.startswith("lpre "))
    ok("modern: the pre-round lines name the same regulations",
       [l.split()[1] for l in lpre1] == [l.split()[1] for l in lpre2])
    new = two["cup_ids"]["cup:MO Albania"]
    ok("modern: the new league's cup took ids nobody had",
       new["cid"] not in cids and new["reg"] not in regs)

    back, _t = build(base, game, r)
    ok("modern, the league taken out again: still the same ids",
       {k: v for k, v in back["cup_ids"].items() if k.startswith(("conmebol:", "ccup:"))} == ids1)


def ui():
    """blocker 2: a place the list does not offer keeps its competition"""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("# NOTE: no PySide6, the League dialog's list not checked")
        return
    app = QApplication.instance() or QApplication([])
    from modstudio.pages import builder as P
    places = [[1, 3], [2, 4], [3, 9], [0, 9]]
    t = P.EuropeTable(copy.deepcopy(places), 16, modern=True)
    ok("modern list: Libertadores qualifying is not offered", 4 not in [c for c, _n in t.competitions])
    ok("a qualifying place opened in it comes back unchanged (it became a Champions League place)",
       sorted(t.places()) == sorted(places))
    t = P.EuropeTable(copy.deepcopy(places), 16)
    ok("classic list: every competition of before, none of the modern ones",
       [c for c, _n in t.competitions] == [c for c, _n in fl26world.COMPETITIONS
                                           if c not in fl26world.CONMEBOL_STAGE_IDS]
       and sorted(t.places()) == sorted(places))
    t.set_confed(4)
    ok("classic list: a South American league keeps its preset", not t.preset.isHidden())
    t = P.EuropeTable([[1, fl26world.LIB_F1]], 16)
    ok("classic list: a phase-1 place (a recipe of #146) also comes back unchanged",
       t.places() == [[1, fl26world.LIB_F1]])
    app.processEvents()


def main(base, keep=False):
    switch(base)
    ui()
    game = tempfile.mkdtemp(prefix="fl26-conmebol-")
    try:
        classic_world(base, game)
        modern_world(base, game)
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
