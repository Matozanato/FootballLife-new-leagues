"""python tools/test_newlife_twins.py <folder with the game's tables>

B56 (15.10., Xxspedd): NewLife 1.0 gave seven of the game's Brazilian clubs NewLife ids (Avaí
Futebol Clube 98493 is the game's Avaí FC 2452, Sport Club do Recife 104676 the game's Sport Recife
1936 ...). Bring the game's leagues to this season took the game's own clubs for clubs gone down
and gave their places to those "new" clubs: names on the wrong crests, and Sport twice.

clubs.csv's game_id (1.5b5 on) says which club of the game such a club is. The test makes a
release of the game's Série A and Série B as the 2026/27 season has them (Sport down, Athletico
Paranaense up), the seven under their NewLife ids with game_id, each club's squad the game's own,
and checks that:
  - the seven are clubs of the game under the game's ids, their squads with them;
  - Bring swaps Sport and Athletico, gives no place away, and refreshes the seven's squads;
  - the same release without the column reads as before (the seven new clubs, seven places given);
  - a world that has a twin as a new club already keeps it (its NewLife id), in Bring and in
    Update my leagues, and does not get its name a second time in a place of the game;
  - tables without the game's club (a database mod) make it a new club again;
  - New clubs cannot put a twin in by hand as a new club.
"""
import csv, json, os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import leaguebuilder as B
import lbplayers as P

N = 0
TWINS = {"98493": (2452, "Avaí Futebol Clube"), "98499": (2468, "Vila Nova Futebol Clube"),
         "98849": (5139, "Botafogo Futebol Clube (SP)"), "101712": (5768, "Grêmio Novorizontino SAF"),
         "104649": (5142, "Cuiabá Esporte Clube SAF"), "104652": (2460, "Criciúma Esporte Clube"),
         "104676": (1936, "Sport Club do Recife")}
BR, SPORT, ATHLETICO = "146", 1936, 1930
A_NAME, B_NAME = "Brazilian National First Division", "Brazilian National Second Division"


def ok(cond, what):
    global N
    assert cond, what
    N += 1
    print("ok %d - %s" % (N, what))


def release(folder, base, with_column=True):
    """the game's Série A and B as the release's season has them, the seven under NewLife ids"""
    db = P.Squads(base)
    gl = {n: ts for _r, _c, n, ts in B.game_leagues(base)}
    sa = next(ts for n, ts in gl.items() if SPORT in ts)
    sb = next(ts for n, ts in gl.items() if 2452 in ts)
    league = {t: A_NAME for t in sa if t != SPORT}
    league.update({t: B_NAME for t in sb if t != ATHLETICO})
    league[ATHLETICO], league[SPORT] = A_NAME, B_NAME
    nl = {g: n for n, (g, _nm) in TWINS.items()}
    os.makedirs(folder)
    cols = ["newlife_id", "in_game", "name", "country", "league", "home_kit", "away_kit"] + \
        (["game_id"] if with_column else [])
    with open(os.path.join(folder, "clubs.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for t, lg in sorted(league.items()):
            row = [nl[t], 0, TWINS[nl[t]][1]] if t in nl else [t, 1, "club %d" % t]
            w.writerow(row + [BR, lg, "plain #ffffff #000000 #000000", ""] +
                       ([t if t in nl else ""] if with_column else []))
    with open(os.path.join(folder, "players.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["newlife_id", "game_id", "name", "birth_date", "club_id"] + list(P.FIELDS))
        for t in sorted(league):
            for _o, pid, _s, _x in db.by_club.get(t, []):
                if pid in db.index:
                    r = db.row(pid)
                    w.writerow([pid, pid, r["name"], "", nl.get(t, t)] + [r[k] for k in P.FIELDS])
    json.dump({"name": "NewLife Database", "version": "t56" if with_column else "t55", "format": 1},
              open(os.path.join(folder, "newlife.json"), "w", encoding="utf-8"))


def main(base):
    tmp = tempfile.mkdtemp(prefix="nl-twins-")
    os.environ["APPDATA"] = tmp                    # the crest cache, if anything is unpacked
    from modstudio import newlife as NL
    try:
        info = B.game_info(base)
        new, old = os.path.join(tmp, "new"), os.path.join(tmp, "old")
        release(new, base)
        release(old, base, with_column=False)
        rel = NL.Release(new)
        ok(rel.twins == {n: str(g) for n, (g, _nm) in TWINS.items()}, "clubs.csv game_id read: the seven twins")
        ok(all(str(g) in rel.clubs and n not in rel.clubs and rel.clubs[str(g)]["in_game"] == "1"
               for n, (g, _nm) in TWINS.items()), "each is a club of the game under the game's id")
        ok(len(rel.squads["2452"]) > 10 and "98493" not in rel.squads, "its squad goes with it")
        rows = {L["name"]: L for L in rel.leagues(str, info)}
        ok(not rows[B_NAME]["clubs"] and {str(g) for g, _n in TWINS.values()} <= set(rows[B_NAME]["in_game"]),
           "Série B of the release: all 20 clubs of the game, none new")

        plan = {p["release"]: p for p in NL.game_league_plan({"leagues": []}, rel, info)}
        pb, pa = plan[B_NAME], plan[A_NAME]
        ok(pb["replace"] == [] and pa["replace"] == [], "Bring gives no place of the game away (%s)" % pb["replace"])
        ok((ATHLETICO, SPORT) in pb["swaps"] and (SPORT, ATHLETICO) in pa["swaps"],
           "Sport (down) and Athletico (up) swap leagues")
        ok({g for g, _n in TWINS.values() if g != SPORT} <= set(pb["clubs"]) and SPORT in pb["clubs"],
           "the seven get the release's squad in their own place")
        r = {"leagues": []}
        n = NL.refresh_game_leagues(r, rel, info, [pb["cid"], pa["cid"]])
        ok(n["replaced"] == 0 and not (r.get("edits") or {}).get("clubs"), "no club renamed: %s" % dict(n))
        ok(all(r["players"].get(str(g), {}).get("newlife_game") for g, _n in TWINS.values()),
           "the seven's squads are the release's")

        # the same release without the column: as before 1.5b5
        orel = NL.Release(old)
        ok(orel.twins == {} and all(n in orel.clubs for n in TWINS), "without game_id: the seven are new clubs")
        oplan = {p["release"]: p for p in NL.game_league_plan({"leagues": []}, orel, info)}
        ok(len(oplan[B_NAME]["replace"]) == 7 and not oplan[B_NAME]["swaps"],
           "without game_id: seven places of Série B given away and no swap, as before (%d)"
           % len(oplan[B_NAME]["replace"]))

        # a world with Avaí as a new club already (added from 1.5b4 into a league of its own)
        world = {"leagues": [{"name": "Mine", "clubs": 12, "newlife": {"version": "1.5b4", "clubs": [98493]}}]}
        hplan = {p["release"]: p for p in NL.game_league_plan(world, rel, info)}
        ok(rel.held == {"98493"} and "98493" in rel.clubs and rel.clubs["98493"]["in_game"] == "0",
           "a world with 98493 as a new club keeps it: id and new club as they were")
        ok(all(c != "98493" for _t, c in hplan[B_NAME]["replace"]), "its name is not given to a place of the game too")
        ok(2452 not in hplan[B_NAME]["clubs"], "the game's Avaí does not get its squad beside it")
        NL.game_league_plan({"leagues": []}, rel, info)
        ok(not rel.held and "2452" in rel.clubs, "another world: the twin is the game's again")

        # a world that added Série B from a release without the column as a new league: Update my
        # leagues to the new release keeps the seven as its new clubs, under their NewLife ids
        w2 = {"leagues": []}
        L = next(x for x in orel.leagues(str, info) if x["name"] == B_NAME)
        NL.add_league(w2, orel, L, info=info)
        x2 = w2["leagues"][0]
        ok(set(TWINS) <= {str(i) for i in x2["newlife"]["clubs"]}, "added from the old release: seven new clubs")
        rel.use_recipe(w2)
        rows2 = rel.leagues(str, info)
        NL.update_league(w2, rel, x2, rows2, info=info, keep=False)
        x2 = w2["leagues"][0]
        ok(set(TWINS) <= {str(i) for i in x2["newlife"]["clubs"]} and
           not {g for g, _n in TWINS.values()} & {int(e["id"]) for e in x2.get("game_clubs") or []},
           "Update my leagues: the seven keep their NewLife ids, the game's clubs are not brought in beside them")
        stale = next(L for L in rows2 if L["name"] == B_NAME)      # picked while the seven were new clubs
        rel.use_recipe({"leagues": []})
        w3 = {"leagues": []}
        NL.add_league(w3, rel, stale, info=info)
        ok({g for g, _n in TWINS.values()} <= {int(e["id"]) for e in w3["leagues"][0].get("game_clubs") or []}
           and not set(TWINS) & {str(i) for i in w3["leagues"][0]["newlife"]["clubs"]},
           "a league picked before the world changed: each twin by the id it goes by now")

        # tables without the game's club (a database mod gave 2452 to nobody)
        mod = dict(info, base=None, clubs={t: v for t, v in info["clubs"].items() if t != 2452})
        rel.use_tables(mod)
        ok("98493" in rel.clubs and "2452" not in rel.clubs, "tables without 2452: Avaí is a new club again")
        rel.use_tables(info)
        ok("2452" in rel.clubs and "98493" not in rel.clubs, "the game's tables again: the game's club")

        # New clubs > NewLife club: a twin is not put in as a new club
        x = {"name": "Hand", "clubs": 12}
        try:
            NL.put_club({"leagues": [x]}, rel, x, 0, "98493", info)
            ok(False, "put_club refused a twin")
        except NL.Error as e:
            ok("club of the game" in str(e), "New clubs refuses a twin: %s" % e)
        print("newlife twins: ok (%d)" % N)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main(sys.argv[1])
