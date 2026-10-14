"""python test_moved_leagues.py <folder with the game's tables> [<NewLife folder>] -- a database
mod that moves the game's leagues into other leagues' places (Yanis 14.10., UML 2026 v3: Ligue 1
where the Russian Premier Liga was). A game league's country comes from the clubs the tables in
use enter in it, not from its regulation id, and NewLife's "in the game" from the clubs those
tables have, not from the plain game's ids.

1. With the game's own tables every answer is the one 0.2.3 gave (the old code is copied in
   here): the UEFA key's leagues and countries, the July starts, the Kick Off order, the League
   order list; a NewLife release (the folder, when given) has the same clubs in the game.
2. A copy of the tables with the entries of Ligue 1 and the Russian Premier Liga swapped: the
   UEFA key shows regulation 116 as France and 20 as Russia, Russia (now 20) is the one left
   out, the July starts and the Kick Off order follow the clubs.
3. The Russian clubs' ids given to other clubs (half of them French clubs under those ids, half
   gone from Team.bin): a NewLife Russian league is no longer "the game's own league" (it was
   blocked), all its clubs are new clubs and it can be added.
"""
import csv, json, os, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B
import mkleague as M
import mkworld as W
import pesdb
import uefakey
from modstudio import newlife as N

LIGUE1, RUSSIA = 20, 116                  # the regulations as the game ships them
LIGUE1_CID, RUSSIA_CID = 12, 114


# ---- 0.2.3's code (d31a0c1), for the old v new comparison on the game's own tables ----

def old_candidates(base):
    out = []
    for rid, name, clubs, _shipped in B.game_europe_tops(base):
        if rid in uefakey.GAME_LEAGUES:
            out.append(("g%d" % rid, name, uefakey.GAME_LEAGUES[rid], clubs))
    return out


def old_july(base):
    out = []
    for rid, country in sorted(uefakey.GAME_LEAGUES.items()):
        day = B.JULY_START.get(country)
        if day and country != "Scotland":
            out.append("july %d %d" % (rid, day))
    return out


def old_kickorder(pl, base, confed):
    rank = B.country_rank(pl, base, confed)
    out, slots = [], set()
    for reg, slot in sorted(B.SHIPPED_SLOT.items()):
        nm = B.SLOT_COUNTRY.get(slot)
        if nm in rank and slot not in slots:
            slots.add(slot)
            out.append((reg, rank[nm]))
    return ["kickorder " + ",".join("%d:%d" % x for x in out)] if out else []


def new_candidates(base):
    return [(c["id"], c["name"], c["country"], c["clubs"]) for c in uefakey.candidates({"leagues": []}, base)]


def copy_tables(base, to):
    os.makedirs(to)
    for f in os.listdir(base):
        if f.endswith(".bin"):
            shutil.copy(os.path.join(base, f), to)


def write(base, name, raw):
    old = open(os.path.join(base, name), "rb").read()
    open(os.path.join(base, name), "wb").write(pesdb.wesys_pack(bytes(raw), old[:3]))
    B._GAME_INFO.clear()


def swap_entries(base, a, b):
    ents = M.load(base, "CompetitionEntry.bin")
    for i in range(len(ents) // M.ENT):
        o = i * M.ENT + M.E_CID
        if ents[o] in (a, b):
            ents[o] = b if ents[o] == a else a
    write(base, "CompetitionEntry.bin", ents)


def teams_of(base, cid):
    return next(ts for _r, c, _n, ts in B.game_leagues(base) if c == cid)


def check_vanilla(base, folder):
    assert B.moved_countries(base) == {}, B.moved_countries(base)
    assert B.slot_countries(base) == B.SLOT_COUNTRY
    assert {r: B.game_league_countries(base)[r] for r in B.SHIPPED_COUNTRY} == B.SHIPPED_COUNTRY
    assert uefakey.game_countries(base) == uefakey.GAME_LEAGUES, uefakey.game_countries(base)
    assert new_candidates(base) == old_candidates(base)
    print("ok  game tables: UEFA key %d leagues as before" % len(old_candidates(base)))
    assert B.july_lines({"leagues": []}, base) == old_july(base), B.july_lines({"leagues": []}, base)
    print("ok  game tables: %d July starts as before" % len(old_july(base)))
    confed = B.confederations(base)
    for order in ("az", ["Russia", "France", "Greece", "Switzerland", "Japan"], ["Usa", "Colombia"]):
        pl = {"leagues": [], "country_order": order}
        assert B.kickorder_lines(pl, base, confed) == old_kickorder(pl, base, confed), order
    print("ok  game tables: Kick Off order as before")
    if folder:
        rel = N.Release(folder)
        before = json.dumps(rel.leagues(str), sort_keys=True)
        info = B.game_info(base)
        after = json.dumps(rel.leagues(str, info), sort_keys=True)
        assert before == after, "the game's own tables change no NewLife club's in_game"
        assert N._game_targets(rel, info)[0] and all(c["in_game"] == c["release_in_game"] for c in rel.clubs.values())
        print("ok  game tables: NewLife %s, the same %d clubs in the game"
              % (rel.meta.get("version"), sum(c["in_game"] == "1" for c in rel.clubs.values())))


def check_swapped(base):
    swap_entries(base, LIGUE1_CID, RUSSIA_CID)
    by = {c["id"]: c for c in uefakey.candidates({"leagues": []}, base)}
    assert by["g%d" % RUSSIA]["country"] == "France", \
        "UEFA key: regulation %d (French clubs now) shown as %s" % (RUSSIA, by["g%d" % RUSSIA]["country"])
    assert by["g%d" % LIGUE1]["country"] == "Russia", \
        "UEFA key: regulation %d (Russian clubs now) shown as %s" % (LIGUE1, by["g%d" % LIGUE1]["country"])
    on, off = uefakey.ranked({"leagues": []}, base)
    assert [c["id"] for c in off] == ["g%d" % LIGUE1], "the league of Russian clubs is the one left out"
    assert "g%d" % RUSSIA in [c["id"] for c in on]
    print("ok  swapped: UEFA key has regulation %d as France, %d as Russia (left out)" % (RUSSIA, LIGUE1))
    july = B.july_lines({"leagues": []}, base)
    assert "july %d %d" % (RUSSIA, B.JULY_START["France"]) in july, july
    assert "july %d %d" % (LIGUE1, B.JULY_START["Russia"]) in july, july
    print("ok  swapped: July starts follow the clubs")
    confed = B.confederations(base)
    pl = {"leagues": [], "country_order": ["France", "Russia"]}
    line = B.kickorder_lines(pl, base, confed)[0]
    places = dict(tuple(map(int, x.split(":"))) for x in line.split()[1].split(","))
    assert places[RUSSIA] == 0 and places[LIGUE1] == 1, line
    assert {"France", "Russia"} <= {nm for nm, _c in B.order_countries(pl, base, confed)}
    print("ok  swapped: Kick Off order follows the clubs")
    cty = B.game_league_countries(base)
    assert cty[RUSSIA] == "France" and cty[LIGUE1] == "Russia", (cty[RUSSIA], cty[LIGUE1])
    assert B.moved_countries(base) == {RUSSIA: "France", LIGUE1: "Russia"}
    swap_entries(base, LIGUE1_CID, RUSSIA_CID)                      # back as shipped


def fake_release(where, base, russians):
    """a NewLife release with a Russian league: the game's Russian clubs (in_game) and two new"""
    os.makedirs(where)
    cty = dict(B.country_ids(base))
    names = B.game_clubs(base)
    json.dump({"name": "NewLife Database", "version": "t"}, open(os.path.join(where, "newlife.json"), "w"))
    with open(os.path.join(where, "clubs.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["newlife_id", "in_game", "name", "country", "league", "home_kit", "away_kit"])
        for t in russians:
            w.writerow([t, 1, names[t][0], cty["Russia"], "Premier Liga", "", ""])
        for k in range(2):
            w.writerow([B.NEWLIFE_TEAMS[0] + k, 0, "Novy Klub %d" % k, cty["Russia"], "Premier Liga", "", ""])
    with open(os.path.join(where, "players.csv"), "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow(["club_id", "name", "game_id"])


def check_reused(base, tmp):
    russians = teams_of(base, RUSSIA_CID)
    folder = os.path.join(tmp, "release")
    fake_release(folder, base, russians)
    rel = N.Release(folder)
    info = B.game_info(base)
    assert RUSSIA_CID in N._game_targets(rel, info)[0], "game tables: it is the game's own league"
    L = next(x for x in rel.leagues(str) if x["name"] == "Premier Liga")
    assert len(L["in_game"]) == len(russians) and len(L["clubs"]) == 2, "game tables: the Russian clubs are the game's"

    # the Russian clubs' ids given to other clubs: half French clubs, half gone from Team.bin
    france = dict(B.country_ids(base))["France"]
    raw = bytearray(pesdb.wesys_unpack(open(os.path.join(base, "Team.bin"), "rb").read()))
    gone = set(russians[len(russians) // 2:])
    free = max(B.game_clubs(base)) + 1
    for o in range(0, len(raw), W.T_REC):
        t = int.from_bytes(raw[o + W.T_ID:o + W.T_ID + 4], "little")
        if t in gone:
            raw[o + W.T_ID:o + W.T_ID + 4] = free.to_bytes(4, "little")
            free += 1
        elif t in russians:
            nm = ("Club Francais %d" % t).encode()
            raw[o + W.T_NAME:o + W.T_NAME + W.T_NAME_LEN] = nm + bytes(W.T_NAME_LEN - len(nm))
            v = int.from_bytes(raw[o + B.T_COUNTRY:o + B.T_COUNTRY + 2], "little")
            v = (v & ~(0x1ff << 2)) | (france << 2)
            raw[o + B.T_COUNTRY:o + B.T_COUNTRY + 2] = v.to_bytes(2, "little")
    write(base, "Team.bin", raw)
    rel = N.Release(folder)
    info = B.game_info(base)
    assert RUSSIA_CID not in N._game_targets(rel, info)[0], \
        "NewLife's Russian league taken for the game's own (the page blocks it): the clubs under those ids are others"
    # a page that read the release without the tables: add_league still asks them
    L = next(x for x in N.Release(folder).leagues(str) if x["name"] == "Premier Liga")
    r = {"world": "_FL26T", "leagues": []}
    N.add_league(r, N.Release(folder), L, info=info)
    x = r["leagues"][-1]
    assert x["clubs"] == len(russians) + 2 and not x.get("game_clubs"), \
        "%d places, clubs of the game %s" % (x["clubs"], [e["id"] for e in x.get("game_clubs") or []])
    print("ok  reused ids: add_league makes the %d clubs new ones" % x["clubs"])
    L = next(x for x in rel.leagues(str, info) if x["name"] == "Premier Liga")
    assert L["in_game"] == [], "no Russian club is in these tables: %s" % L["in_game"]
    assert len(L["clubs"]) == len(russians) + 2, L["clubs"]
    assert N.fits(L, info), "and it fits"
    print("ok  reused ids: NewLife's Russian league is %d new clubs, addable" % len(L["clubs"]))


def main(base, folder=None, only=None):
    if only != "moved":                   # (only "moved": the moved tables alone, for an older Mod Studio)
        check_vanilla(base, folder)
    scratch = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out", "scratch")
    os.makedirs(scratch, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="moved", dir=scratch)          # next to the repo, as regress018's
    failed = []
    try:
        moved = os.path.join(tmp, "pesdb")
        copy_tables(base, moved)
        for check in (check_swapped, lambda b: check_reused(b, tmp)):
            try:
                check(moved)
            except AssertionError as e:
                failed.append(str(e))
                print("FAIL", e)
    finally:
        B._GAME_INFO.clear()
        shutil.rmtree(tmp, ignore_errors=True)
    print("test_moved_leagues: %s" % ("%d FAILED" % len(failed) if failed else "all passed"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
