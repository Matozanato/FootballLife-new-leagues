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
  - New clubs cannot put a twin in by hand as a new club;
  - with game_names (1.6b3) a club of the game whose id the tables give another club of the
    country is a new club, and one under a name another game gives it stays the game's;
  - a new club of the release with such an id as game_id (FL27's Liaoning Tieren at Meizhou
    Hakka's 5181) is the game's club in tables that have it there, and the release's own club of
    that id a new one under SWAP_KEY + id; FL26's tables and a world that has the twin as a new
    club keep both as before.
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


def release(folder, base, with_column=True, renum=None):
    """the game's Série A and B as the release's season has them, the seven under NewLife ids;
    renum {team id: id in another game}: clubs of the game with game_id (a game that numbers them
    differently)"""
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
                       ([t if t in nl else (renum or {}).get(t, "")] if with_column else []))
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

        # FL27 numbers a club of the game differently (Tampines 4115 -> 69651): clubs.csv keeps
        # the club under its id, in_game 1, with game_id the other game's id
        ren = os.path.join(tmp, "ren")
        t0 = sorted(t for t in info["clubs"] if str(t) in rel.clubs and rel.clubs[str(t)]["in_game"] == "1"
                    and not rel.clubs[str(t)].get("twin"))[0]
        t1 = max(info["clubs"]) + 1000
        release(ren, base, renum={t0: t1})
        rr = NL.Release(ren)
        ok(rr.twins.get(str(t0)) == str(t1) and str(t0) in rr.clubs and str(t1) not in rr.clubs
           and rr.clubs[str(t0)]["in_game"] == "1", "renumbered club: under its own id until the tables say")
        rr.use_tables(info)
        ok(str(t0) in rr.clubs and str(t1) not in rr.clubs and rr.clubs[str(t0)]["in_game"] == "1",
           "tables with its own id (FL26): a club of the game under %d" % t0)
        f27 = {t: v for t, v in info["clubs"].items() if t != t0}
        f27[t1] = info["clubs"][t0]
        cc = dict(info.get("club_country") or {})
        if t0 in cc:
            cc[t1] = cc.pop(t0)
        fl27 = dict(info, base=None, clubs=f27, club_country=cc)
        rr.use_tables(fl27)
        ok(str(t1) in rr.clubs and str(t0) not in rr.clubs and rr.clubs[str(t1)]["in_game"] == "1"
           and rr.clubs[str(t1)]["twin"] == str(t0), "tables with the other id (FL27): a club of the game under %d" % t1)
        ok(str(t1) in rr.squads and str(t0) not in rr.squads, "its squad goes with it")
        row = next(L for L in rr.leagues(str, fl27) if str(t1) in L["in_game"])
        ok(str(t0) not in row["clubs"] and str(t0) not in row["in_game"], "its league: the club once, as the game's")
        f2 = dict(f27)
        f2[t0] = info["clubs"][t0]
        both = dict(fl27, base=None, clubs=f2, club_country=info.get("club_country"))
        rr.use_tables(both)
        ok(str(t0) in rr.clubs and str(t1) not in rr.clubs, "tables with both ids: its own id")
        rr.use_tables(info)
        ok(str(t0) in rr.clubs and rr.clubs[str(t0)]["in_game"] == "1", "back to FL26's tables: as before")

        # game_names (1.6b3): FL27 gave FL26's id of a club to another club of the same country
        # (5181 Meizhou Hakka is Liaoning Tieren there); the country alone took it for the release's
        gn = os.path.join(tmp, "gn")
        shutil.copytree(os.path.join(tmp, "new"), gn)
        p = os.path.join(gn, "clubs.csv")
        rows = list(csv.DictReader(open(p, encoding="utf-8")))
        for r in rows:
            t = int(r["game_id"] or r["newlife_id"])
            r["game_names"] = info["clubs"][t][0] if t in info["clubs"] else ""
        t2 = next(int(r["newlife_id"]) for r in rows if r["in_game"] == "1" and info["clubs"][int(r["newlife_id"])][0])
        for r in rows:
            if r["newlife_id"] == str(t2):
                r["game_names"] += "|Old Name of %d" % t2
        with open(p, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        rg, rp = NL.Release(gn), NL.Release(os.path.join(tmp, "new"))
        rg.use_tables(info)
        rp.use_tables(info)
        ok({c for c, r in rg.clubs.items() if r["in_game"] == "1"} == {c for c, r in rp.clubs.items() if r["in_game"] == "1"},
           "game_names: the game's tables, the same clubs of the game as without them")
        other = dict(info["clubs"])
        other[t2] = ("Some Other Club",) + tuple(other[t2][1:])
        oth = dict(info, base=None, clubs=other)
        rg.use_tables(oth)
        rp.use_tables(oth)
        ok(rg.clubs[str(t2)]["in_game"] == "0", "game_names: %d another club of the country in the tables -> a new club" % t2)
        ok(rp.clubs[str(t2)]["in_game"] == "1", "without game_names the country takes it (as before 1.6b3)")
        other[t2] = ("Old Name of %d" % t2,) + tuple(other[t2][1:])
        rg.use_tables(dict(info, base=None, clubs=other))
        ok(rg.clubs[str(t2)]["in_game"] == "1", "game_names: the club under the name another game gives it stays the game's")
        rg.use_tables(info)
        ok(rg.clubs[str(t2)]["in_game"] == "1", "game_names: back to the game's tables")

        # ... and the club FL27 has there is a new club of the release (Liaoning Tieren 103240):
        # its game_id is that id, so the tables that have it under that name make it the game's,
        # and the release's own club of that id goes by SWAP_KEY + id meanwhile, a new club
        sw = os.path.join(tmp, "sw")
        shutil.copytree(gn, sw)
        p = os.path.join(sw, "clubs.csv")
        rows = list(csv.DictReader(open(p, encoding="utf-8")))
        own_name = next(r["name"] for r in rows if r["newlife_id"] == str(t2))
        nid, k = "110000", str(NL.SWAP_KEY + t2)
        rows.append(dict(rows[0], newlife_id=nid, in_game="0", name="Some Other Club FC", league=B_NAME,
                         game_id=str(t2), game_names="Some Other Club"))
        with open(p, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        p = os.path.join(sw, "players.csv")
        prow = list(csv.DictReader(open(p, encoding="utf-8")))
        n2 = sum(1 for r in prow if r["club_id"] == str(t2))
        prow.append(dict(prow[0], newlife_id="9999001", game_id="", club_id=nid))
        with open(p, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, list(prow[0]))
            w.writeheader()
            w.writerows(prow)
        other = dict(info["clubs"])
        other[t2] = ("Some Other Club",) + tuple(other[t2][1:])
        oth = dict(info, base=None, clubs=other)
        rs = NL.Release(sw)
        ok(rs.twins.get(nid) == str(t2) and nid in rs._swap and nid in rs.clubs and rs.clubs[str(t2)]["name"] == own_name,
           "swapped twin: off until the tables say, both clubs under their NewLife ids")
        rs.use_tables(info)
        ok(nid in rs.clubs and rs.clubs[nid]["in_game"] == "0" and not rs.clubs[str(t2)].get("twin")
           and rs.clubs[str(t2)]["in_game"] == "1" and k not in rs.clubs,
           "tables with the release's club at %d (FL26): it is the game's, the other a new club" % t2)
        rs.use_tables(oth)
        ok(rs.clubs[str(t2)].get("twin") == nid and rs.clubs[str(t2)]["in_game"] == "1" and nid not in rs.clubs,
           "tables with the other club at %d (FL27): the twin is the game's club" % t2)
        ok(k in rs.clubs and rs.clubs[k]["name"] == own_name and rs.clubs[k]["in_game"] == "0",
           "the release's own club of %d is a new club under %s" % (t2, k))
        ok(len(rs.squads.get(str(t2), [])) == 1 and len(rs.squads.get(k, [])) == n2, "each squad goes with its club")
        ok(rs.now(nid) == str(t2) and rs.now(str(t2)) == str(t2) and rs.now(k) == k, "now(): each club by the id it goes by")
        seen = [c for L in rs.leagues(str, oth) for c in list(L["clubs"]) + list(L["in_game"])]
        ok(seen.count(str(t2)) == 1 and seen.count(k) == 1 and nid not in seen, "the leagues: each club once")
        rs.use_tables(info)
        ok(nid in rs.clubs and k not in rs.clubs and rs.clubs[str(t2)]["name"] == own_name
           and len(rs.squads.get(str(t2), [])) == n2 and len(rs.squads.get(nid, [])) == 1,
           "back to FL26's tables: as before")
        rs.use_tables(oth)
        rs.use_recipe({"leagues": [{"name": "Mine", "clubs": 12, "newlife": {"version": "1.6b2", "clubs": [int(nid)]}}]})
        ok(nid in rs.clubs and rs.clubs[nid]["in_game"] == "0" and rs.clubs[str(t2)]["name"] == own_name and k not in rs.clubs,
           "a world with the twin as a new club already keeps it, and the release's club its id")
        rs.use_recipe({"leagues": [{"name": "Mine27", "clubs": 12, "newlife": {"version": "1.6b3", "clubs": [int(k)]}}]})
        ok(rs.clubs[str(t2)].get("twin") == nid and rs.clubs[k]["name"] == own_name,
           "a world made in FL27 with the release's club under %s: that club" % k)

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
