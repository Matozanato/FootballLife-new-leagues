"""The UEFA key: European places from a ranking of the countries, the way UEFA hands them out.

The modder puts the European top divisions of a world in order -- the game's own (Premier League,
LaLiga ...) and the new ones whose country is in UEFA -- and the key gives every one its places:
which positions go to the Champions League, its qualifying, the Europa League, the Conference
League and their qualifying. The result is written where the places always were (a new league's
"europe", the recipe's "game_europe" for the game's own), so any of it can still be changed by
hand afterwards, and "uefa_seed", the order fl26swiss should hand the qualifying places out in.

KEY is UEFA's access list for 2024-27 cut to what the world has: no first qualifying round, so
the second is the lowest (fl26world.QCONFIGS, all nine rounds), and the yearly extra Champions
League place for the two best associations of the season before given for good to rank 1.
    LP    Champions League, league phase          EL    Europa League, league phase
    PO    Champions League play-off               ELQ2  Europa League second qualifying round
    Q3    Champions League third qualifying round KL    Conference League, league phase
    Q2    Champions League second qual. round     KLQ2  Conference League second qual. round
"K" is the national cup's winner (going down the league when the winner already has a place).
LP 26 + the two title holders, EL 19 + one, KL 20: with the play-off winners and the clubs that
drop down from the rounds above, 36 in each league phase.

With fewer ranked leagues than KEY has rows (30), the places of the missing ranks are not lost:
each of them goes, tier by tier, to the next club of the strongest leagues in turn -- the first
league's next club, then the second's ... -- so every competition stays full. Past 30 a league
gets no place; the notes say so. In each league the stronger competitions take the higher
positions (a league with a Champions League third qualifying place and a Europa League place
gives the higher one to the Champions League).
"""
import collections

TIERS = ["LP", "PO", "Q3", "Q2", "EL", "ELQ2", "KL", "KLQ2"]       # strongest first
COMP = {"LP": 0, "PO": 10, "Q3": 10, "Q2": 10, "EL": 1, "ELQ2": 11, "KL": 2, "KLQ2": 12}
CUP = "K"
NAMES = {"LP": "Champions League", "PO": "Champions League play-off",
         "Q3": "Champions League third qualifying round", "Q2": "Champions League second qualifying round",
         "EL": "Europa League", "ELQ2": "Europa League qualifying", "KL": "Conference League",
         "KLQ2": "Conference League qualifying"}

KEY = {}


def _row(ranks, **tiers):
    for r in ranks:
        KEY[r] = {t: list(tiers.get(t, [])) for t in TIERS}


_R = lambda a, b: range(a, b + 1)
_row([1], LP=[1, 2, 3, 4, 5], EL=[CUP, 6], KL=[7])
_row(_R(2, 4), LP=[1, 2, 3, 4], EL=[CUP, 5], KL=[6])
_row([5], LP=[1, 2, 3], PO=[4], EL=[CUP, 5], KL=[6])
_row([6], LP=[1, 2], PO=[3], EL=[CUP, 4], KL=[5])
_row([7], LP=[1], PO=[2], EL=[CUP, 3], KL=[4])
_row(_R(8, 10), LP=[1], PO=[2], EL=[CUP], ELQ2=[3], KL=[4])
_row(_R(11, 12), PO=[1], Q3=[2], EL=[CUP], ELQ2=[3], KL=[4])
_row(_R(13, 15), Q3=[1], Q2=[2], ELQ2=[CUP, 3], KL=[4])
_row([16], Q3=[1], Q2=[2], ELQ2=[CUP], KL=[3])
_row(_R(17, 18), Q3=[1], ELQ2=[CUP], KL=[2])
_row(_R(19, 20), Q2=[1], ELQ2=[CUP], KL=[2])
_row(_R(21, 28), Q2=[1], KLQ2=[CUP, 2])
_row(_R(29, 30), Q2=[1])
RANKS = len(KEY)
TOTAL = collections.Counter({t: sum(len(KEY[r][t]) for r in KEY) for t in TIERS})
assert dict(TOTAL) == {"LP": 26, "PO": 8, "Q3": 8, "Q2": 16, "EL": 19, "ELQ2": 16, "KL": 20, "KLQ2": 16}

# UEFA's association ranking for 2026-27 (the 2025 coefficients), Russia left out as UEFA does;
# Country.bin's names. The modder reorders as they like.
DEFAULT_ORDER = [
    "England", "Italy", "Spain", "Germany", "France", "Netherlands", "Portugal", "Belgium",
    "Czech Republic", "Turkey", "Norway", "Greece", "Austria", "Scotland", "Poland", "Denmark",
    "Switzerland", "Israel", "Cyprus", "Sweden", "Croatia", "Serbia", "Ukraine", "Hungary",
    "Romania", "Slovakia", "Slovenia", "Bulgaria", "Azerbaijan", "Ireland", "Moldova", "Iceland",
    "Bosnia and Herzegovina", "Armenia", "Latvia", "Kosovo", "Finland", "Kazakhstan",
    "Faroe Islands", "Malta", "Northern Ireland", "Lithuania", "Liechtenstein", "Estonia",
    "Albania", "Montenegro", "Luxembourg", "Wales", "Georgia", "North Macedonia", "Belarus",
    "Andorra", "Gibraltar", "San Marino",
]
OUT_BY_DEFAULT = {"Russia"}      # in the game, suspended by UEFA: unticked until the modder ticks it

# the game's own top divisions in UEFA countries (regulation -> country)
GAME_LEAGUES = {17: "England", 18: "Italy", 19: "Spain", 20: "France", 21: "Netherlands",
                22: "Portugal", 50: "Germany", 115: "Belgium", 116: "Russia", 117: "Greece",
                118: "Turkey", 133: "Scotland", 141: "Denmark"}


def candidates(recipe, base):
    """[{"id", "name", "country", "clubs", "cup", "game"}] of the world's European top divisions:
    the game's own (id "g<regulation>") and the recipe's new ones in a UEFA country (id = the
    league's name), not yet ranked"""
    import leaguebuilder as B
    import mkleague as M
    comp, regs = M.load(base, "Competition.bin"), M.load(base, "CompetitionRegulation.bin")
    regrow = {int.from_bytes(regs[i * M.REG + M.R_ID:i * M.REG + M.R_ID + 2], "little"): regs[i * M.REG:(i + 1) * M.REG]
              for i in range(len(regs) // M.REG)}
    region_of_cid = {comp[i * M.COMP + M.CID_OFF]: M.dec_region(comp[i * M.COMP + M.REGION_OFF])
                     for i in range(len(comp) // M.COMP)}
    out = []
    for rid, name, clubs, _shipped in B.game_europe_tops(base):
        if rid in GAME_LEAGUES:
            cup = B.home_cup(regrow, region_of_cid, region_of_cid.get(regrow[rid][M.R_CID]))
            out.append({"id": "g%d" % rid, "name": name, "country": GAME_LEAGUES[rid], "clubs": clubs,
                        "cup": cup is not None, "game": True})
    conf = B.country_confederations(base)
    for L in recipe.get("leagues") or []:
        if L.get("above") or L.get("exhibition") or conf.get(L.get("country", "")) != 2:
            continue
        out.append({"id": L["name"], "name": L["name"], "country": L.get("country", ""),
                    "clubs": int(L.get("clubs") or 0), "cup": bool(L.get("cup")), "game": False})
    return out


def ranked(recipe, base):
    """(the candidates in the recipe's uefa_rank order, the ones left out): a recipe without a
    ranking yet gets DEFAULT_ORDER by country, Russia left out; a league new since the ranking
    was saved goes in by its country's default rank"""
    cands = candidates(recipe, base)
    saved = [str(x) for x in recipe.get("uefa_rank") or []]
    if not saved:
        on = [c for c in cands if c["country"] not in OUT_BY_DEFAULT]
        return sorted(on, key=lambda c: (default_rank(c["country"]), not c["game"], c["name"])),             [c for c in cands if c["country"] in OUT_BY_DEFAULT]
    by = {c["id"]: c for c in cands}
    out = [by[i] for i in saved if i in by]
    off = set(str(x) for x in recipe.get("uefa_off") or [])
    for c in cands:
        if c["id"] not in saved and c["id"] not in off and c["country"] not in OUT_BY_DEFAULT:
            k = next((j for j, o in enumerate(out) if default_rank(o["country"]) > default_rank(c["country"])), len(out))
            out.insert(k, c)
    return out, [c for c in cands if c not in out]


def apply(recipe, leagues, left_out=()):
    """write the key's places for leagues (ranked, strongest first) into the recipe: each new
    league's "europe" (its non-UEFA places, Libertadores ones and the like, are kept), the
    game's leagues' "game_europe" (a game league left out gets an empty list: no places, not
    the game's), "uefa_rank", "uefa_off" and "uefa_seed". Returns the notes."""
    places, seed, notes = assign(leagues)
    uefa = {0, 1, 2, 10, 11, 12}
    ge = dict(recipe.get("game_europe") or {})
    by_name = {L["name"]: L for L in recipe.get("leagues") or []}
    for c in list(leagues) + list(left_out):
        mine = places.get(c["id"], [])
        if c["game"]:
            ge[c["id"][1:]] = mine
        elif c["id"] in by_name:
            L = by_name[c["id"]]
            L["europe"] = [e for e in L.get("europe") or [] if int(e[1]) not in uefa] + mine
    recipe["game_europe"] = ge
    recipe["uefa_rank"] = [c["id"] for c in leagues]
    recipe["uefa_off"] = [c["id"] for c in left_out]
    recipe["uefa_seed"] = [list(s) for s in seed]
    return notes


def default_rank(country):
    return DEFAULT_ORDER.index(country) if country in DEFAULT_ORDER else len(DEFAULT_ORDER)


def assign(leagues, tiers=None):
    """leagues: [{"id", "clubs", "cup"}] in rank order (cup: the country has a national cup).
    Returns ({id: [[position, competition], ...]}, seed, notes): position 0 is the cup winner;
    tiers, a dict, gets {id: [(tier, position), ...]};
    seed is [(id, position, competition)] in the order fl26swiss should take them (tier by tier,
    then by rank), notes are sentences for whatever could not be placed."""
    slots = collections.defaultdict(list)          # id -> [(tier, is_cup)]
    count = collections.Counter()
    notes = []
    n = len(leagues)
    for r, L in enumerate(leagues[:RANKS], 1):
        for t in TIERS:
            for p in KEY[r][t]:
                slots[L["id"]].append((t, p == CUP and bool(L.get("cup"))))
                count[t] += 1
    for L in leagues[RANKS:]:
        notes.append("%s: rank %d -- the key has places for %d leagues, so no European place"
                     % (L.get("name", L["id"]), leagues.index(L) + 1, RANKS))
    # the missing ranks' places: tier by tier, one to each league in rank order, round and round
    room = {L["id"]: L["clubs"] for L in leagues[:RANKS]}
    for t in TIERS:
        need = TOTAL[t] - count[t]
        k = 0
        while need > 0 and n:
            ids = [L["id"] for L in leagues[:RANKS] if len(slots[L["id"]]) - sum(c for _t, c in slots[L["id"]]) < room[L["id"]]]
            if not ids:
                notes.append("%s: %d place(s) left over -- the leagues have no more clubs" % (NAMES[t], need))
                break
            L = ids[k % len(ids)]
            slots[L].append((t, False))
            need -= 1
            k += 1
    # positions: the strongest competition the highest, the cup winner apart
    out, order = {}, []
    for rank, L in enumerate(leagues[:RANKS]):
        pos = 0
        places = []
        for t, is_cup in sorted(slots[L["id"]], key=lambda s: TIERS.index(s[0])):
            if is_cup:
                places.append((t, 0))
            else:
                pos += 1
                if pos > L["clubs"]:
                    notes.append("%s: no club left for a %s place" % (L.get("name", L["id"]), NAMES[t]))
                    continue
                places.append((t, pos))
        out[L["id"]] = [[p, COMP[t]] for t, p in places]
        if tiers is not None:
            tiers[L["id"]] = places
        order += [(TIERS.index(t), rank, p, L["id"], COMP[t]) for t, p in places]
    seed = [(lid, p, c) for _t, _r, p, lid, c in sorted(order, key=lambda o: (o[0], o[1], o[2] == 0, o[2]))]
    return out, seed, notes


SHORT = {"LP": "CL", "PO": "CL play-off", "Q3": "CL 3rd qual. round", "Q2": "CL 2nd qual. round",
         "EL": "EL", "ELQ2": "EL 2nd qual. round", "KL": "ECL", "KLQ2": "ECL 2nd qual. round"}


def table(leagues, tiers):
    """the result as text, a line per league: '1. Premier League: CL 1, 2, 3, 4, 5; EL cup, 6; ECL 7'
    (tiers as assign() fills it)"""
    lines = []
    for r, L in enumerate(leagues, 1):
        by = collections.OrderedDict()
        for t, p in tiers.get(L["id"]) or []:
            by.setdefault(SHORT[t], []).append("cup" if p == 0 else str(p))
        txt = "; ".join("%s %s" % (c, ", ".join(v)) for c, v in by.items()) or "no place"
        lines.append("%d. %s: %s" % (r, L.get("name", L["id"]), txt))
    return lines


if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    Ls = [{"id": i, "name": DEFAULT_ORDER[i], "clubs": 18, "cup": True} for i in range(n)]
    tiers = {}
    pl, seed, notes = assign(Ls, tiers)
    print("\n".join(table(Ls, tiers)))
    print(collections.Counter(c for v in pl.values() for _p, c in v))
    print("\n".join(notes))
