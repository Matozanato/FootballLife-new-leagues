r"""The game's own stadiums for the new clubs (0.2.4).

A club's home stadium is a byte of its Team.bin record (+0x3C, a Stadium.bin id; +0x3D is 0).
Build clones every new club from the game's last club (Selangor FC), so until 0.2.4 all of
them -- the modpack's 1212 -- played at Stadio Nazionale (54). Now each new club gets one of
the game's fictional stadiums, picked by:

  - its size: the league's tier wants a capacity (40 000 at the top, 8 000 in the fourth tier);
  - its look: a Spanish-looking stadium for a club of Spain, Portugal or the Americas, an
    English one for the British Isles, a German one for central and eastern Europe ...;
  - variety: a stadium already given in the same league counts against it, so a league of 18
    clubs plays in many stadiums and not in the same two.

The pick is the same Build after Build (same league, same clubs, same order). A club given a
stadium by hand (Edit club > Game stadium: players[club]["game_stadium"]) keeps it, and a
stadium of Stadium Server (map_teams.txt) still comes first in the game: it is served over this
one. The game's real stadiums (Camp Nou, Old Trafford ...) are only given by hand.

Stadium.bin of FL26 (dt10_x64.cpk): 36 records, 35 usable; the table below is its fictional
stadiums, id: (name, capacity, look).
"""
import math, os

T_STADIUM = 0x3C

FICTIONAL = {
    13: ("Metropole Arena", 89000, "en"),
    15: ("Estádio do Escorpião", 87538, "latin"),
    17: ("Estadio del Nuevo Triunfo", 37279, "latin"),
    18: ("Stade de Sagittaire", 41000, "fr"),
    19: ("Stadio Orione", 32160, "med"),
    20: ("Burg Stadion", 59000, "de"),
    29: ("General Stadium", 78000, "any"),
    40: ("Estadio del Martingal", 32150, "latin"),
    42: ("Rose Park Stadium", 35362, "en"),
    43: ("Estadio Campeones", 52000, "latin"),
    44: ("Coliseo de los Deportes", 20000, "latin"),
    45: ("Sports Park", 6000, "en"),
    46: ("Neu Sonne Arena", 41000, "de"),
    47: ("Village Road", 25240, "en"),
    50: ("Hoofdstad Stadion", 55000, "de"),
    54: ("Stadio Nazionale", 70520, "med"),
    55: ("Estadio del Tauro", 69500, "latin"),
}
REAL = {
    2: ("Spotify Camp Nou", 99354), 5: ("Wembley Stadium", 90000), 6: ("Stadio Olimpico", 82307),
    7: ("Old Trafford", 75811), 10: ("Estádio José Alvalade", 50080), 11: ("Allianz Arena", 66000),
    14: ("Estádio do Morumbi", 73501), 16: ("Estádio Urbano Caldeira", 16798), 22: ("Allianz Stadium", 41000),
    23: ("Saitama Stadium 2002", 63700), 24: ("Estádio do Maracanã", 88992), 27: ("El Monumental", 65645),
    28: ("La Bombonera", 49000), 34: ("Estádio Mineirão", 62547), 35: ("Neo Química Arena", 68000),
    41: ("Stade Louis II", 18523), 52: ("Emirates Stadium", 60432), 70: ("Johan Cruijff ArenA", 54033),
}
STADIUMS = {i: v[:2] for i, v in FICTIONAL.items()}
STADIUMS.update(REAL)

# the look of a country's clubs (Country.bin flag id); the Americas by confederation (latin)
LOOK = {}
for _look, _ids in (("en", (204, 214, 225, 232, 241, 206, 213, 245)),
                    ("latin", (236, 228, 192)),
                    ("med", (215, 231, 222, 211, 201, 190, 189, 191, 200, 198, 303, 304, 221, 235, 311, 199, 229)),
                    ("fr", (208, 250, 197, 220, 238)),
                    ("de", (210, 194, 218, 224, 202, 234, 212, 227, 230, 239, 196, 223, 205, 217, 219, 216, 193,
                            195, 209, 203, 207, 226, 237))):
    for _i in _ids:
        LOOK[_i] = _look
NEAR = {"en": {"de"}, "de": {"en", "fr"}, "fr": {"de", "med"}, "med": {"latin", "fr"}, "latin": {"med"}}
TIER_CAPACITY = {1: 40000, 2: 22000, 3: 12000}


def look_of(country, confed=None):
    """the look a club of this country gets: en / latin / med / fr / de, None for any"""
    if country in LOOK:
        return LOOK[country]
    if (confed or {}).get(country) in (4, 6):          # CONMEBOL, CONCACAF
        return "latin"
    return None


def cost(sid, look, want, used):
    """how badly stadium sid fits: lower is better"""
    _name, cap, slook = FICTIONAL[sid]
    c = 0.6 * abs(math.log(cap / want))
    if look and slook != look:
        c += 0.3 if slook == "any" else 0.35 if slook in NEAR.get(look, ()) else 0.8
    return c + 0.5 * used.get(sid, 0)


def league(n, tier=1, country=None, confed=None, fixed=None):
    """[stadium id] for the n clubs of a league: fixed {k: id} keeps a club's own"""
    try:
        tier = int(tier or 1)
    except (TypeError, ValueError):
        tier = 1
    want = TIER_CAPACITY.get(tier, 8000)
    look = look_of(country, confed)
    fixed = fixed or {}
    used, out = {}, []
    for sid in fixed.values():
        if sid in FICTIONAL:
            used[sid] = used.get(sid, 0) + 1
    for k in range(n):
        if fixed.get(k) in STADIUMS:
            out.append(fixed[k])
            continue
        sid = min(sorted(FICTIONAL), key=lambda s: cost(s, look, want, used))
        used[sid] = used.get(sid, 0) + 1
        out.append(sid)
    return out


def fixed_of(pl, p):
    """{k: stadium id} picked by hand for league (or group) p's clubs (players["<league>/k"])"""
    out = {}
    for k in range(int(p.get("clubs") or len(p.get("teams") or []) or 0)):
        c = (pl.get("players") or {}).get("%s/%d" % (p["name"], k))
        sid = c.get("game_stadium") if isinstance(c, dict) else None
        if isinstance(sid, int) and sid in STADIUMS:
            out[k] = sid
    return out


def name(sid):
    return STADIUMS.get(sid, ("stadium %s" % sid,))[0]


# ---- a ready world (Import your world): its Team.bin is not built here ----

def new_clubs(pl):
    """{team id: (league or group, place)} of the world's new clubs (not the game's own)"""
    out = {}
    for p in (pl.get("leagues") or []) + (pl.get("others") or []):
        game = {int(k) for k in (p.get("game_clubs") or {})}
        for k, tid in enumerate(p.get("teams") or []):
            if k not in game and tid not in out:
                out[tid] = (p, k)
    return out


def auto(pl, confed=None, keep=None):
    """{team id: game stadium} the automatic pick gives the world's new clubs, league by league as
    Build gives them; keep {team id: id} are clubs picked by hand"""
    keep, out = keep or {}, {}
    for p in (pl.get("leagues") or []) + (pl.get("others") or []):
        game = {int(k) for k in (p.get("game_clubs") or {})}
        teams = p.get("teams") or []
        fixed = {k: keep[t] for k, t in enumerate(teams) if t in keep}
        try:
            country = int(p.get("country"))
        except (TypeError, ValueError):
            country = None
        for k, sid in enumerate(league(len(teams), p.get("tier") or 1, country, confed, fixed)):
            if k not in game and teams[k] not in out:
                out[teams[k]] = sid
    return out


def read_team_bin(path):
    """{team id: game stadium} of a Team.bin"""
    import mkworld as W, pesdb
    with open(path, "rb") as f:
        raw = pesdb.wesys_unpack(f.read())
    return {int.from_bytes(raw[o + W.T_ID:o + W.T_ID + 4], "little"): raw[o + T_STADIUM]
            for o in range(0, len(raw) - W.T_REC + 1, W.T_REC)}


def write_team_bin(path, picks):
    """the game stadiums {team id: id} into a Team.bin (a .before-stadiums copy the first time);
    the number of clubs changed"""
    import shutil
    import mkworld as W, pesdb
    with open(path, "rb") as f:
        head = f.read()
    raw = bytearray(pesdb.wesys_unpack(head))
    n = 0
    for o in range(0, len(raw) - W.T_REC + 1, W.T_REC):
        tid = int.from_bytes(raw[o + W.T_ID:o + W.T_ID + 4], "little")
        sid = picks.get(tid)
        if sid in STADIUMS and (raw[o + T_STADIUM] != sid or raw[o + T_STADIUM + 1]):
            raw[o + T_STADIUM], raw[o + T_STADIUM + 1] = sid, 0
            n += 1
    if n:
        if not os.path.exists(path + ".before-stadiums"):
            shutil.copy2(path, path + ".before-stadiums")
        with open(path + ".tmp", "wb") as f:
            f.write(pesdb.wesys_pack(bytes(raw), head[:3]))
        os.replace(path + ".tmp", path)
    return n


def confed_of(*bases):
    """{flag id: confederation} from the first of these pesdb folders with a Country.bin (a world
    has none of its own: the game's tables, Mod Studio's project.base, are the fallback)"""
    from leaguebuilder import confederations
    for base in bases:
        if base and os.path.exists(os.path.join(base, "Country.bin")):
            try:
                return confederations(base)
            except Exception:
                pass
    return {}


def world_picks(pl, confed, hand, auto_on):
    """{team id: game stadium} for a ready world's new clubs: the automatic pick when auto_on, with
    the clubs chosen by hand (hand) on top"""
    out = auto(pl, confed, hand) if auto_on else {}
    new = new_clubs(pl)
    out.update({t: s for t, s in hand.items() if t in new and s in STADIUMS})
    return out
