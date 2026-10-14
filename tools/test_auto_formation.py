"""python test_auto_formation.py <folder with the game's tables> -- a new club with no formation
of its own plays the one its squad fits (0.2.4, lbplayers.pick_formation), not the engine's fixed
4-2-3-1: every club of the Modpack (1212 new clubs, no formation in the recipe) played 4-2-3-1.
The picker on made-up squads (two strikers, wingers, three centre backs), then one world built in a
temporary game folder: clubs with different squads get different formations and their best
eleven for them, a formation the recipe names (a club's own, a league's) stands."""
import collections, os, random, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B
import lbplayers as P
import mktactics
import playeredit as E

N = 0
WORLD = "_FL26AutoForm"


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def player(pos, v, also=()):
    """a made-up player: registered at pos, rated 1 at `also`, every ability v (overall v)"""
    d = {"Registered Position": pos}
    for r in E.POSITIONS:
        d[r] = "2" if r == pos else ("1" if r in also else "0")
    for n, _b in E.ABILITIES:
        d[n] = str(v)
    return d


def squad(first, bench):
    """a keeper, then the starters at 92-96, the bench at 88 (above any placeholder at Build)"""
    rows = [player("GK", 80)]
    rows += [player(p, 92 + n % 5, also) for n, (p, also) in enumerate(first)]
    rows += [player(p, 88, also) for p, also in bench]
    return rows


TWO_UP = squad([("CB", ()), ("CB", ()), ("LB", ()), ("RB", ()), ("DMF", ("CMF",)), ("CMF", ("DMF",)),
                ("CMF", ("AMF",)), ("AMF", ("CMF",)), ("CF", ("SS",)), ("CF", ("SS",))],
               [("CB", ()), ("CMF", ()), ("CF", ()), ("LB", ())])
WINGERS = squad([("CB", ()), ("CB", ()), ("LB", ()), ("RB", ()), ("DMF", ()), ("CMF", ()), ("CMF", ()),
                 ("LWF", ("LMF",)), ("RWF", ("RMF",)), ("CF", ())],
                [("CB", ()), ("CMF", ()), ("LWF", ()), ("RB", ())])
BACK3 = squad([("CB", ()), ("CB", ()), ("CB", ()), ("LMF", ("LB",)), ("RMF", ("RB",)), ("DMF", ()),
               ("CMF", ()), ("CMF", ()), ("CF", ()), ("CF", ())],
              [("CB", ()), ("CMF", ()), ("CF", ()), ("DMF", ())])
BACK5 = squad([("CB", ()), ("CB", ()), ("CB", ()), ("LB", ()), ("RB", ()), ("DMF", ()),
               ("CMF", ()), ("CMF", ()), ("CF", ()), ("CF", ())],
              [("CB", ()), ("CMF", ()), ("CF", ()), ("DMF", ())])


def roles_of(e):
    return mktactics.roles(e["places"])


def forwards(roles):
    return sum(roles.count(r) for r in ("CF", "LWF", "RWF", "SS"))


def unit(forms):
    two = roles_of(P.pick_formation(TWO_UP, forms))
    ok("two strong strikers and no wingers: two up front (%s)" % " ".join(two),
       two.count("CF") + two.count("SS") == 2 and not {"LWF", "RWF"} & set(two))
    wing = roles_of(P.pick_formation(WINGERS, forms))
    ok("strong wingers: three forwards (%s)" % " ".join(wing),
       forwards(wing) == 3 and {"LWF", "RWF"} <= set(wing))
    b3 = roles_of(P.pick_formation(BACK3, forms))
    ok("three centre backs and wide midfielders: three at the back (%s)" % " ".join(b3),
       b3.count("CB") == 3 and not {"LB", "RB"} & set(b3))
    b5 = roles_of(P.pick_formation(BACK5, forms))
    ok("three centre backs and full backs: five at the back (%s)" % " ".join(b5),
       b5.count("CB") == 3 and {"LB", "RB"} <= set(b5))
    ok("the four squads get four formations", len({tuple(sorted(x)) for x in (two, wing, b3, b5)}) == 4)
    rows = list(WINGERS)
    random.Random(7).shuffle(rows)
    ok("the squad's order does not change the pick",
       P.pick_formation(rows, forms)["label"] == P.pick_formation(WINGERS, forms)["label"])
    rare = [e for e in forms if e["clubs"] < P.PICK_USED]
    ok("a shape fewer than %d clubs of the game play is never picked" % P.PICK_USED,
       all(P.pick_formation(s, forms)["clubs"] >= P.PICK_USED for s in (TWO_UP, WINGERS, BACK3, BACK5))
       and (not rare or P.pick_formation(TWO_UP, rare) is None))
    ok("no formations or no outfield players: nothing picked",
       P.pick_formation(WINGERS, []) is None and P.pick_formation([player("GK", 80)], forms) is None)
    # of the formations the winger squad fits as well, the one most clubs of the game play wins
    same = [e for e in forms if sorted(roles_of(e)) == sorted(wing)]
    ok("ties go to the formation more clubs of the game play", P.pick_formation(WINGERS, forms) is same[0])


def edits(rows):
    return {str(n): dict(r) for n, r in enumerate(rows)}


def build(base, game, forms):
    label = lambda name: next(e["label"] for e in forms if e["name"] == name)
    own, league = label("3-1-4-2"), label("4-4-2")
    recipe = {"world": WORLD,
              "players": {"Auto Albania/0": {"edits": edits(TWO_UP)},
                          "Auto Albania/1": {"edits": edits(WINGERS)},
                          "Auto Albania/2": {"edits": edits(BACK3)},
                          "Auto Albania/4": {"edits": edits(BACK5)}},
              "leagues": [{"name": "Auto Albania", "country": "Albania", "clubs": 10, "legs": 2,
                           "club_formations": ["", "", "", own]},
                          {"name": "Auto Andorra", "country": "Andorra", "clubs": 10, "legs": 2,
                           "formation": league}]}
    said = []
    pl = B.plan(recipe, base)
    B.build(pl, base, game, False, log=said.append)
    db = os.path.join(game, "SiderAddons", "livecpk", WORLD, "common", "etc", "pesdb")
    said = "\n".join(str(s) for s in said)
    rows, tforms, _h = mktactics.read(db)
    first = {}
    for k, club, _s in rows:
        if club not in first and k in tforms:
            first[club] = mktactics.roles(tforms[k][0])
    a, b = (L["teams"] for L in pl["leagues"])
    shape = {e["label"]: roles_of(e) for e in forms}

    ok("every new club has tactics in the built tables", all(t in first for t in a + b))
    ok("the two-striker squad plays two up front (%s)" % " ".join(first[a[0]]),
       first[a[0]].count("CF") + first[a[0]].count("SS") == 2)
    ok("the winger squad plays three forwards (%s)" % " ".join(first[a[1]]), forwards(first[a[1]]) == 3)
    ok("the three centre backs play three at the back (%s)" % " ".join(first[a[2]]),
       first[a[2]].count("CB") == 3 and not {"LB", "RB"} & set(first[a[2]]))
    ok("the club's own formation in the recipe stands (%s)" % own, first[a[3]] == shape[own])
    ok("the league's formation stands for all its clubs (%s)" % league, all(first[t] == shape[league] for t in b))
    picked = collections.Counter(tuple(first[t]) for t in a if t != a[3])
    ok("the clubs of one league play more than one formation (%d)" % len(picked), len(picked) >= 3)
    ok("Build says how many it picked and which",
       "formations picked for 9 clubs from their squads (" in said and "formations for 11 clubs" in said)
    sq = P.Squads(db)
    for k in (0, 1, 2, 4):
        eleven = sq.squad(a[k])
        ok("club %d: its best eleven stands in the picked formation" % k,
           P.lineup_problems(eleven, first[a[k]]) == []
           and all(int(r["Speed"]) >= 88 or r["Registered Position"] == "GK" for r in eleven[:11]))


def main(base):
    forms = B.formations(base)
    assert forms, "no Tactics.bin in %s" % base
    unit(forms)
    game = tempfile.mkdtemp(prefix="fl26-autoform-")
    try:
        for d in ("livecpk", "modules", "content"):
            os.makedirs(os.path.join(game, "SiderAddons", d))
        with open(os.path.join(game, "SiderAddons", "sider.ini"), "w") as f:
            f.write("[sider]\n")
        build(base, game, forms)
    finally:
        shutil.rmtree(game, ignore_errors=True)
    print("1..%d" % N)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1])
