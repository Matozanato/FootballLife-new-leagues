"""python tools/test_twin_names.py <folder with the game's tables>

B421 (11.11.2026, Reddit r/SPFootballLife: "many duplicate players", "top players without clubs").
A NewLife release and the game spell some names apart ("Marc-Andre ter Stegen" and the game's
"M. ter Stegen", both at Ajax): the release's row became a new player with a made face, and the
game's player lost his club. newlife.game_twin's second pass pairs them by more than the name.

The test makes a release of the game's Premier League, each squad the game's own with the game's
ids, takes eight players of the game out of it and puts them back with no game id and a year
younger:
  - at his own club under his surname alone, and under another first name with the same first
    letter: the game's player both times;
  - at another club under his surname alone: a new player (a single word and no club in common);
  - at another club with a name in front of his, a centimetre taller: the game's player -- and
    through Bring the game's leagues and a NewLife league's mover he joins that club, no copy;
  - the same two centimetres taller, of another nationality, or at two clubs: new players;
  - a player of a club the release has not got, with a name in front of his: a new player;
  - with his id in the game and a name in front of his: the game's player (the id was right);
  - a row of somebody else with a player's id: that player is still found by his own row.
"""
import csv, json, os, shutil, sys, tempfile, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import leaguebuilder as B
import lbplayers as P

N = 0
CITY = 173


def ok(cond, what):
    global N
    assert cond, what
    N += 1
    print("ok %d - %s" % (N, what))


def letters(name):
    return [w for w in map(P._letters, P._words(name)) if w]


def pick(db, info, clubs):
    """ten players of the league and one of a club outside it whom nobody of their nationality
    shares a word of the name with: (player, his club)"""
    national = info.get("national") or set()
    by = collections.defaultdict(set)
    nat = {}
    for pid in db.index:
        nat[pid] = db.row(pid)["Nationality"]
        for w in letters(db.name(pid)):
            by[(nat[pid], w)].add(pid)

    def alone(pid):
        w = letters(db.name(pid))
        return (len(w) == 2 and min(map(len, w)) >= 4 and w[0] != w[1]
                and all(by[(nat[pid], x)] == {pid} for x in w)
                and len([t for t in db.clubs_of.get(pid, []) if t not in national]) == 1)

    def best(t):
        """the club's twenty best outfield players: a release keeps a club's best P.SQUAD only"""
        rows = [db.row(pid) for _o, pid, _s, _x in db.by_club.get(t, []) if pid in db.index]
        rows = sorted((r for r in rows if r["Registered Position"] != "GK"), key=lambda r: -P.level(r))
        return [int(r["player"]) for r in rows[:20]]

    inside = [(pid, t) for t in sorted(clubs) for pid in best(t) if alone(pid)]
    seen, out = collections.Counter(), []
    for pid, t in inside:                               # two a club at most: no squad runs short
        if seen[t] < 2 and len(out) < 10:
            seen[t] += 1
            out.append((pid, t))
    far = next((pid, t) for t in sorted(db.by_club) if t not in clubs and t not in national
               and t in info["clubs"] and not B.special_team((info["clubs"][t] or ("",))[0])
               for _o, pid, _s, _x in db.by_club[t] if pid in db.index and alone(pid))
    return out, far


def release(folder, db, clubs, rows, left_out):
    os.makedirs(folder)
    with open(os.path.join(folder, "clubs.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["newlife_id", "in_game", "name", "country", "league", "home_kit", "away_kit"])
        for t in sorted(clubs):
            w.writerow([t, 1, "club %d" % t, "204", "English Premier Division", "plain #ffffff #000000 #000000", ""])
    with open(os.path.join(folder, "players.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["newlife_id", "game_id", "name", "birth_date", "club_id"] + list(P.FIELDS))
        for t in sorted(clubs):
            for _o, pid, _s, _x in db.by_club.get(t, []):
                if pid in db.index and pid not in left_out:
                    r = db.row(pid)
                    w.writerow([pid, pid, r["name"], "", t] + [r[k] for k in P.FIELDS])
        for k, (t, name, pid, change) in enumerate(rows):
            r = db.row(pid)
            r["Age"] = str(int(r["Age"]) - 1)
            r.update(change)
            w.writerow([900000 + k, r.pop("game_id", ""), name, "", t] + [r[f] for f in P.FIELDS])
    json.dump({"name": "NewLife Database", "version": "t421", "format": 1},
              open(os.path.join(folder, "newlife.json"), "w", encoding="utf-8"))


def main(base):
    tmp = tempfile.mkdtemp(prefix="nl-b421-")
    os.environ["APPDATA"] = tmp
    from modstudio import newlife as NL
    try:
        L = NL._loose
        ok(L("Rafael", "Rafael Monteiro") == "one" and L("Leandro González Pírez", "González Pírez") == "part"
           and L("Marc-André ter Stegen", "M. ter Stegen") == "initial" and L("Leonardo Palestina", "Leo Palestina") == "initial"
           and L("Giorgos Athanasiadis", "Georgios Athanasiadis") == "first" and L("Mohammad Reza Akhbari", "Mohammadreza Akhbari") == "same",
           "the kinds of a looser name")
        ok(L("Jung Kang-Min", "Jung Gyu-Min") == "first" and L("Vinícius", "Vini Jr") == "" and L("Lucas Ribeiro", "Luan Silva") == "",
           "a middle word apart is another first name, and no word in common is nobody")

        info = B.game_info(base)
        db = P.Squads(base)
        clubs = next(ts for _r, _c, _n, ts in B.game_leagues(base) if CITY in ts)
        men, (far, far_club) = pick(db, info, clubs)
        ok(len(men) == 10, "ten players of the league with a name of their own")
        other = lambda t: next(c for c in sorted(clubs) if c != t)
        third = lambda t: [c for c in sorted(clubs) if c != t][1]
        first, sur = lambda p: P._words(db.name(p))[0], lambda p: P._words(db.name(p))[-1]
        cm = lambda p, d: {"Height (cm)": str(int(db.row(p)["Height (cm)"]) + d)}
        abroad = next(db.row(q)["Nationality"] for q in db.index if db.row(q)["Nationality"] != db.row(men[5][0])["Nationality"])
        (a, ta), (b, tb), (c, tc), (d, td), (e, te), (f, tf), (g, tg), (h, th), (i, ti), (j, tj) = men
        rows = [(ta, sur(a), a, {}),
                (tb, first(b)[:1] + "xq " + sur(b), b, {}),
                (other(tc), sur(c), c, {}),
                (other(td), "Xavier " + db.name(d), d, cm(d, 1)),
                (other(te), "Xavier " + db.name(e), e, cm(e, 2)),
                (other(tf), "Xavier " + db.name(f), f, {"Nationality": abroad}),
                (other(tg), "Xavier " + db.name(g), g, {}), (third(tg), "Xavier " + db.name(g), g, {}),
                (other(th), "Xavier " + db.name(far), far, {}),
                (other(ti), "Xavier " + db.name(i), i, {"game_id": str(i)}),
                (other(tj), "Zzyzx Qwertyu", h, {"game_id": str(j)}),
                (third(tj), "Xavier " + db.name(j), j, {})]
        release(os.path.join(tmp, "rel"), db, clubs, rows, {p for p, _t in men})
        rel = NL.Release(os.path.join(tmp, "rel"))
        rel.use_tables(info)
        twin = NL.game_twin(rel, db, info.get("national") or set())
        row = lambda k: next(r for r in rel.squads[str(rows[k][0])] if r["name"] == rows[k][1] and int(r["newlife_id"]) >= 900000)
        ok(twin(row(0)) == str(a), "his surname alone, at his own club: the game's player (%s)" % db.name(a))
        ok(twin(row(1)) == str(b), "another first name with his first letter, at his own club: the game's (%s)" % db.name(b))
        ok(twin(row(2)) == "", "his surname alone at another club: a single word is not enough")
        ok(twin(row(3)) == str(d), "a name in front of his, a centimetre taller, at another club: the game's (%s)" % db.name(d))
        ok(not P.same_player(rows[3][1], db.name(d)) and NL._him(row(3), str(d), db, twin),
           "and the pair is trusted where the names alone do not fit")
        ok(twin(row(4)) == "", "two centimetres taller at another club: not him")
        ok(twin(row(5)) == "", "another nationality: not him")
        ok(twin(row(6)) == twin(row(7)) == "", "at two clubs of the release: neither")
        ok(twin(row(8)) == "", "a player of a club the release has not got stays there")
        ok(twin(row(9)) == str(i) and not P.same_player(rows[9][1], db.name(i)),
           "his id in the game and a name in front of his: the id was right (%s)" % db.name(i))
        ok(twin(row(10)) == "" and twin(row(11)) == str(j),
           "somebody else's row with a player's id: the player is found by his own row all the same (%s)" % db.name(j))
        plain = NL.game_twin(rel, db)
        ok(plain(row(0)) == str(a) and plain(row(3)) in ("", str(d)) and plain(row(2)) == "",
           "without the national teams' ids: the same at his own club (an international elsewhere is left)")

        recipe = {"leagues": []}
        NL._game_squads(recipe, rel, info, {t: str(t) for t in clubs})
        pl = recipe["players"]
        adds = [x["name"] for v in pl.values() for x in v.get("add") or []]
        gone = {str(x) for v in pl.values() for x in v.get("remove") or []}
        ok(str(a) not in gone and str(b) not in gone and rows[0][1] not in adds and rows[1][1] not in adds,
           "Bring: the two stay at their clubs, no second player made")
        ok(str(d) in pl[str(other(td))].get("join", []) and rows[3][1] not in adds,
           "Bring: the third joins the club the release has him at")
        ok(rows[2][1] in adds and rows[4][1] in adds and rows[5][1] in adds and rows[8][1] in adds,
           "the others are new players, as before")
        ok(str(i) in pl[str(other(ti))].get("join", []) and rows[9][1] not in adds
           and str(j) in pl[str(third(tj))].get("join", []) and rows[11][1] not in adds,
           "Bring: the two of the ids join their clubs")

        mover, _db = NL._movers({"players": {}}, info, rel)
        ok(mover(row(3))[:2] == ("move", str(d)), "a NewLife league: he moves to his club")
        ok(mover(row(4))[:2] == ("copy", None), "and who is not him is copied")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("all %d checks passed" % N)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1])
