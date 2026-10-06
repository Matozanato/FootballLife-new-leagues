"""a NewLife Database release as leagues to pick: every league of the release, its clubs and
players, and the recipe entries that put a whole league in the game in one go -- a new League
Builder league with the release's clubs, each club's squad its best players from the release.

A release comes whole (newlife-<version>/: players.csv, clubs.csv, newlife.json) or in parts
(NewLife-<version>-<part>.zip, one per continent or piece of one; split.py): the person
downloads the parts they want into one folder and Mod Studio reads all of them from there, as
they are. The release is downloaded separately (it is not on GitHub); nothing of it is copied
anywhere but the recipe the person builds -- and the crests and league logos a release may
carry (crests/<club id>.png, logos/*.png named in newlife.json's league_logos, 1.2 on), which
are unpacked to %APPDATA%\\FL26ModStudio\\newlife\\<version> for the recipe to point at.
"""
import collections, csv, glob, io, json, os, zipfile

import leaguebuilder as B
import lbplayers as P

FILES = ("players.csv", "clubs.csv", "newlife.json")
PART = "NewLife-*.zip"
CACHE = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "FL26ModStudio", "newlife")


class Error(Exception):
    pass


def parts_in(folder):
    return sorted(glob.glob(os.path.join(folder, PART)))


def find(folder):
    """the folder in or under `folder` (a download is often unpacked one level deeper) with a
    whole release or with parts"""
    ok = lambda d: all(os.path.exists(os.path.join(d, f)) for f in FILES) or parts_in(d)
    if ok(folder):
        return folder
    for d in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        sub = os.path.join(folder, d)
        if os.path.isdir(sub) and ok(sub):
            return sub
    return None


def _sources(where):
    """[(label, open(name) -> text file, [picture names], read(name) -> bytes)] -- the whole
    release, or every part"""
    if all(os.path.exists(os.path.join(where, f)) for f in FILES):
        pics = ["%s/%s" % (d, f) for d in ("crests", "logos") if os.path.isdir(os.path.join(where, d))
                for f in sorted(os.listdir(os.path.join(where, d))) if f.lower().endswith(".png")]
        return [("", lambda n: open(os.path.join(where, n), encoding="utf-8", newline=""), pics,
                 lambda n: open(os.path.join(where, n), "rb").read())]
    out = []
    for zp in parts_in(where):
        try:
            z = zipfile.ZipFile(zp)
            missing = [f for f in FILES if f not in z.namelist()]
        except (zipfile.BadZipFile, OSError) as e:
            raise Error("%s is not a NewLife part (%s) -- download it again" % (os.path.basename(zp), e))
        if missing:
            raise Error("%s is not a NewLife part: no %s" % (os.path.basename(zp), ", ".join(missing)))
        pics = [n for n in z.namelist() if n.split("/")[0] in ("crests", "logos") and n.lower().endswith(".png")]
        out.append((os.path.basename(zp), lambda n, z=z: io.TextIOWrapper(z.open(n), encoding="utf-8", newline=""),
                    pics, lambda n, z=z: z.read(n)))
    return out


class Release:
    def __init__(self, folder):
        where = find(folder)
        if not where:
            raise Error("no NewLife Database here: put the NewLife-....zip parts you downloaded in one folder "
                        "(no need to unpack them) and open that folder")
        self.folder = where
        self.meta, self.parts = None, []
        self.clubs, self.squads = {}, {}
        self.crests, self.logos = {}, {}          # club id / (country, league) -> read() of the png
        versions = set()
        for label, opener, pics, read in _sources(where):
            with opener("newlife.json") as f:
                m = json.load(f)
            versions.add(m.get("version", "?"))
            self.meta = self.meta or m
            if m.get("part"):
                self.parts.append(m["part"].get("name", label))
            for n in pics:
                cid = os.path.splitext(n.split("/")[-1])[0]
                if n.startswith("crests/") and cid.isdigit():
                    self.crests[cid] = lambda n=n, read=read: read(n)
            for e in m.get("league_logos") or []:
                if isinstance(e, dict) and e.get("file") in pics:
                    self.logos[(str(e.get("country", "")), e.get("league", ""))] = \
                        lambda n=e["file"], read=read: read(n)
            with opener("clubs.csv") as f:
                for r in csv.DictReader(f):
                    self.clubs[r["newlife_id"]] = r
            with opener("players.csv") as f:
                for r in csv.DictReader(f):
                    if r.get("club_id"):
                        self.squads.setdefault(r["club_id"], []).append(r)
        if len(versions) > 1:
            raise Error("the parts in this folder are of different versions (%s): keep one version's parts "
                        "only" % ", ".join(sorted(versions)))

    def _unpack(self, sub, name, read):
        d = os.path.join(CACHE, "".join(ch if ch.isalnum() or ch in "._-" else "_"
                                        for ch in str(self.meta.get("version", "0"))), sub)
        path = os.path.join(d, name)
        if not os.path.exists(path):
            os.makedirs(d, exist_ok=True)
            with open(path + ".part", "wb") as f:
                f.write(read())
            os.replace(path + ".part", path)
        return path

    def crest(self, cid):
        """the path of club cid's crest from the release, unpacked, or None"""
        read = self.crests.get(str(cid))
        return self._unpack("crests", "%s.png" % cid, read) if read else None

    def league_logo(self, L):
        """the path of league L's logo (from leagues()) from the release, unpacked, or None"""
        read = self.logos.get(tuple(L.get("key") or ()))
        if not read:
            return None
        k = "%s_%s" % L["key"]
        return self._unpack("logos", "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in k) + ".png", read)

    @property
    def version(self):
        return "%s %s" % (self.meta.get("name", "NewLife Database"), self.meta.get("version", "?"))

    def leagues(self, country_of):
        """[{name, country, clubs: [club id], in_game: [club id], players, strength}] --
        country_of(Country.bin id) gives the country's name; strongest first within a country.
        clubs are the ones a new league makes; in_game the league's clubs the game already has
        (they stay where the game has them)"""
        by, have = {}, {}
        for cid, c in self.clubs.items():
            if c.get("league"):
                key = (c.get("country", ""), c["league"])
                by.setdefault(key, [])
                (have.setdefault(key, []) if c["in_game"] == "1" else by[key]).append(cid)
        out = []
        for (cty, name), ids in by.items():
            best = sorted((P.overall(r) for i in ids for r in self.squads.get(i, [])), reverse=True)
            top = best[:11 * len(ids)]
            out.append({"name": name, "key": (cty, name),
                        "country": country_of(cty) if cty.isdigit() else "", "clubs": sorted(ids),
                        "in_game": sorted(have.get((cty, name), [])),
                        "players": sum(min(len(self.squads.get(i, [])), P.SQUAD) for i in ids),
                        "strength": round(sum(top) / float(len(top))) if top else 0})
        return sorted(out, key=lambda L: (L["country"], -L["strength"], L["name"]))

    def squad(self, cid):
        """the club's best P.SQUAD players, best first: goalkeepers kept to three"""
        rows = sorted(self.squads.get(cid, []), key=lambda r: -P.overall(r))
        gk = [r for r in rows if r.get("Registered Position") == "GK"][:3]
        out = gk + [r for r in rows if r.get("Registered Position") != "GK"]
        return sorted(out[:P.SQUAD], key=lambda r: -P.overall(r))


def game_clubs(L, info=None):
    """the team ids of league L's clubs the game already has (a NewLife club the game has keeps
    the game's id) that can play in a league of ours: all of them without the game's tables
    (info = leaguebuilder.game_info)"""
    return [int(c) for c in L.get("in_game") or [] if info is None or B.game_club_problem(info, int(c)) is None]


def fits(L, info=None):
    """the league's new clubs and the game's own together make a league (GitHub #61: the Swiss
    Super League, 9 new clubs and Basel, Young Boys and Lugano, was refused for 9)"""
    return B.CLUBS_MIN <= len(L["clubs"]) + len(game_clubs(L, info)) <= B.CLUBS_MAX


def unique_name(recipe, name):
    have = {x["name"] for x in recipe["leagues"]}
    if name not in have:
        return name
    n = 2
    while "%s (%d)" % (name, n) in have:
        n += 1
    return "%s (%d)" % (name, n)


PREFIX = {"FC", "FK", "NK", "SK", "HNK", "GNK", "AC", "AS", "SC", "SV", "CD", "CF", "CA", "SD", "UD", "RC",
          "KF", "KS", "MFK", "FCM", "AFC", "CFC", "SSC", "TSV", "VFB", "VFL", "US", "RCD", "IF", "BK", "IK", "OFK", "FSV"}


def abbr(name, taken):
    """a three-letter short name the game takes (A-Z and 0-9), not one taken already: the
    initials when there are three words, else the start of the club's own word (Banik Ostrava
    -> BAN; FC Dukla Prague -> DUK)"""
    words = [B.ascii_letters(w) for w in name.split()]
    words = [w for w in words if w and not w.isdigit()]
    own = [w for w in words if w not in PREFIX] or words or ["CLB"]
    tries = []
    if len(own) >= 3:
        tries.append("".join(w[0] for w in own[:3]))
    tries.append(own[0][:3])
    if len(own) >= 2:
        tries += [own[0][:2] + own[1][0], own[0][0] + own[1][:2]]
    w = own[0]
    tries += [w[0] + w[k] + w[j] for k in range(1, len(w)) for j in range(k + 1, len(w))]
    for t in tries:
        if len(t) == 3 and t not in taken:
            return t
    for n in range(10):
        t = (w + "XX")[:2] + str(n)
        if t not in taken:
            return t
    return (w + "XX")[:2] + "0"


def add_league(recipe, rel, L, legs=2, info=None, custom=False, name=None, more=0):
    """put league L (from rel.leagues) in the recipe: a new league with its clubs, every club's
    squad from the release. The whole squad is set: places the release has no player for leave
    the club, down to P.MIN_SQUAD. The league's clubs the game already has take the last places
    as clubs of the game ("game_clubs"): one that plays somewhere in the game still needs the
    club that takes its place there (New clubs, Club of the game). A player the game already
    has (the release's game_id, under the same name in these tables) moves to the club with a
    "join" -- a copy would leave him at his old club as well -- unless his club would drop
    below P.MIN_SQUAD or an earlier league already has him; he keeps his name, face and id and
    takes the release's other fields. A player whose move is refused is left out of the club
    rather than copied, and the prototype player of his place stays instead.
    A prototype player who stays (the release has fewer than P.MIN_SQUAD players for the club)
    is brought to the club's level, a little under its own players (lbplayers.fill_level): the prototype
    is a top club's squad, and a fourth-tier side with eleven of its own had seven of them
    (Risto 04.10.).
    name: the league's name (update_league keeps the one it has), else the release's; more: the
    clubs update_league puts in after (the person's own), counted for the league's size.
    custom: the person changed the league's line-up (clubs left out or brought from other
    leagues); update_league then keeps that line-up instead of the release's.
    Returns (the new league's name, players left at their game club for lack of players,
    players left out because another league has them)."""
    game = game_clubs(L, info)
    if not B.CLUBS_MIN <= len(L["clubs"]) + len(game) + more <= B.CLUBS_MAX:
        raise Error("%s has %d clubs; a league takes %d to %d" % (L["name"], len(L["clubs"]) + len(game) + more,
                                                                  B.CLUBS_MIN, B.CLUBS_MAX))
    name = name or unique_name(recipe, L["name"])
    clubs = sorted(L["clubs"], key=lambda i: rel.clubs[i]["name"].lower())
    taken = set()
    abbrs = []
    for i in clubs:
        a = abbr(rel.clubs[i]["name"], taken)
        taken.add(a)
        abbrs.append(a)
    recipe["leagues"].append({"name": name, "country": L["country"], "clubs": len(clubs) + len(game), "legs": legs,
                              "club_names": [rel.clubs[i]["name"] for i in clubs], "club_abbrs": abbrs,
                              "club_kits": [rel.clubs[i].get("home_kit", "") for i in clubs],
                              "club_away_kits": [rel.clubs[i].get("away_kit", "") for i in clubs],
                              "newlife": {"version": rel.meta.get("version", ""), "clubs": [int(i) for i in clubs]}})
    if L.get("key"):
        recipe["leagues"][-1]["newlife"]["key"] = list(L["key"])
    if custom:
        recipe["leagues"][-1]["newlife"]["custom"] = True
    crests = [rel.crest(i) for i in clubs]
    if any(crests):
        recipe["leagues"][-1]["club_crests"] = crests
    logo = rel.league_logo(L)
    if logo:
        recipe["leagues"][-1]["logo"] = logo
    if game:
        recipe["leagues"][-1]["game_clubs"] = [_game_entry(info, len(clubs) + j, t) for j, t in enumerate(game)]
    pl = recipe.setdefault("players", {})
    mover, db = _movers(recipe, info)
    proto = db.proto() if db is not None else []
    league_ovr = [P.overall(r) for i in clubs for r in rel.squad(i)]
    stayed = elsewhere = 0
    for k, i in enumerate(clubs):
        c, s, e = _club_players(rel, i, mover, proto, league_ovr)
        stayed, elsewhere = stayed + s, elsewhere + e
        pl[P.new_key(name, k)] = c
    return name, stayed, elsewhere


def _movers(recipe, info):
    """(mover, the game's squads or None) for the players of NewLife clubs put in the recipe:
    mover(row) says what happens to the player of a release row (see add_league)"""
    pl = recipe.setdefault("players", {})
    db = P.Squads(info["base"]) if info and info.get("base") else None
    national = (info or {}).get("national") or set()
    taken = {str(r) for c in pl.values() for r in c.get("join") or []}   # moved by an earlier league
    leaving = collections.Counter()

    def mover(r):
        """("move", the game's id of the player in release row r) when he can come to his NewLife
        club; ("keep", that id) when he is a player of these tables but must stay where he is --
        his game club would drop below P.MIN_SQUAD, or an earlier league already took him; and
        ("copy", None) when he is not a player of these tables and becomes a new player. A row
        that is kept is left out of the NewLife club: copying him would put the same man at two
        clubs, which is the thing the move exists to prevent. The third value says whether a
        kept player is somebody another league already has."""
        g = str(r.get("game_id", "")).strip()
        if db is None or not g.isdigit() or int(g) not in db.index:
            return "copy", None, False
        if not P.same_name(r["name"], db.name(int(g))):
            return "copy", None, False        # another database: that id is somebody else
        if g in taken:
            return "keep", g, True            # an earlier league already has him
        old = [t for t in db.clubs_of.get(int(g), []) if t not in national]
        if old and len(db.by_club[old[0]]) - leaving[old[0]] - 1 < P.MIN_SQUAD:
            return "keep", g, False           # his club would have too few players left
        if old:
            leaving[old[0]] += 1
        taken.add(g)
        return "move", g, False

    return mover, db


_NAMES = {}


def stand_in_name(rel, i, n):
    """a name for prototype player n who stays at NewLife club i (the release has too few
    players for it): a first name and a surname of two other players of its league, always the
    same two for the same place, so no "FL P00151" plays in a real club's squad"""
    league = (rel.clubs.get(i) or {}).get("league") or ""
    key = (id(rel), league)
    if key not in _NAMES:
        names = [r.get("name", "").split() for j in sorted(rel.clubs, key=str)
                 if (rel.clubs[j].get("league") or "") == league for r in rel.squad(j)]
        _NAMES[key] = ([x[0] for x in names if len(x) >= 2], [x[-1] for x in names if len(x) >= 2],
                       {" ".join(x) for x in names})
    firsts, lasts, real = _NAMES[key]
    if not firsts:
        return None
    h = int(str(i)) * 131 + n * 7919 if str(i).isdigit() else n * 7919
    for t in range(8):                    # not the name of a real player of the league
        name = "%s %s" % (firsts[(h + t) % len(firsts)], lasts[(h // 7 + 3 + 5 * t) % len(lasts)])
        if name not in real:
            break
    return name


def _club_players(rel, i, mover, proto, league_ovr):
    """(the recipe's players entry for NewLife club i, players kept at their game club, players
    left out because another league has them): its squad from the release, see add_league"""
    sq = rel.squad(i)
    ed, join = {}, []
    stayed = elsewhere = 0
    for r in sq:
        ch = {"name": r["name"]}              # no order: Build picks the best eleven
        for f in P.FIELDS:
            if r.get(f, "") != "":
                ch[f] = r[f]
        how, g, other = mover(r)
        if how == "move":
            del ch["name"]                    # the game's spelling stays
            join.append(g)
            ed[g] = ch
        elif how == "keep":
            # left out: he is somebody the game already has, at a club that cannot spare
            # him or at a NewLife club of an earlier league. The place stays with the
            # prototype player mkplayers made (keep below keeps enough of them: the club
            # never drops under P.MIN_SQUAD), so the club has one real player fewer and no
            # copy of him anywhere.
            if other:
                elsewhere += 1
            else:
                stayed += 1
        else:
            ed[str(len(ed) - len(join))] = ch
    keep = max(len(sq) - len(join), P.MIN_SQUAD - len(join))
    want = P.fill_level([P.overall(r) for r in sq], league_ovr)
    for n in range(len(ed) - len(join), keep):              # prototype players who stay
        if n < len(proto) and want is not None and str(n) not in ed:
            ed[str(n)] = P.at_level(proto[n], want)
            name = stand_in_name(rel, i, n)
            if name:
                ed[str(n)]["name"] = name
    c = {"edits": ed}
    if join:
        c["join"] = join
    if keep < P.SQUAD:
        c["remove"] = [str(n) for n in range(keep, P.SQUAD)]
    return c, stayed, elsewhere


def put_club(recipe, rel, x, k, cid, info=None):
    """put NewLife club cid (one the game does not have) in place k of league x, a league of
    the recipe: its name, short name, kits, crest and squad, as add_league gives them, and its
    NewLife id, so Build gives it the world id it keeps (newlife_tids). Whatever was in that
    place goes: a club of the game there (game_clubs) and its player changes (victormican, #83:
    NewLife clubs into the empty places of a league made by hand). Returns (players kept at
    their game club, players left out because another league has them)."""
    c = rel.clubs[cid]
    n = int(x.get("clubs") or 0)
    if not 0 <= k < n:
        raise Error("%s has no club %d" % (x["name"], k + 1))
    if c.get("in_game") == "1":
        raise Error("%s is a club of the game: use Club of the game for it" % c["name"])

    def at(key, v, blank=""):
        lst = list(x.get(key) or [])[:n]
        lst += [blank] * (n - len(lst))
        lst[k] = v
        x[key] = lst

    taken = {a for j, a in enumerate(x.get("club_abbrs") or []) if j != k and a}
    at("club_names", c["name"])
    at("club_abbrs", abbr(c["name"], taken))
    at("club_kits", c.get("home_kit", ""))
    at("club_away_kits", c.get("away_kit", ""))
    crest = rel.crest(cid)
    if crest or x.get("club_crests"):
        at("club_crests", crest, None)
    nl = x.setdefault("newlife", {})
    at_nl = list(nl.get("clubs") or [])[:n]
    nl["clubs"] = at_nl + [0] * (n - len(at_nl))     # 0 = not a NewLife club, as project.py pads
    nl["clubs"][k] = int(cid)
    gc = [e for e in x.get("game_clubs") or [] if int(e.get("at", -1)) != k]
    if gc:
        x["game_clubs"] = gc
    else:
        x.pop("game_clubs", None)
    pl = recipe.setdefault("players", {})
    mover, db = _movers(recipe, info)
    proto = db.proto() if db is not None else []
    mates = [j for j, y in rel.clubs.items() if y.get("league") and y.get("league") == c.get("league")]
    league_ovr = [P.overall(r) for j in mates for r in rel.squad(j)]
    entry, stayed, elsewhere = _club_players(rel, cid, mover, proto, league_ovr)
    pl[P.new_key(x["name"], k)] = entry
    return stayed, elsewhere


def outdated(recipe, rel):
    """the recipe's leagues added from another version of the NewLife Database than rel's"""
    v = str(rel.meta.get("version", ""))
    return [x for x in recipe["leagues"] if (x.get("newlife") or {}).get("version") and str(x["newlife"]["version"]) != v]


def _from_cache(path):
    """a crest or logo the release gave (unpacked to CACHE), not one the person picked"""
    try:
        return os.path.normcase(os.path.abspath(path)).startswith(os.path.normcase(os.path.abspath(CACHE)))
    except (TypeError, ValueError):
        return False


# every list a league keeps per place (modstudio.project.Project.PLACE_LISTS)
PLACE_LISTS = (("club_names", ""), ("club_abbrs", ""), ("club_crests", None), ("club_coaches", ""),
               ("club_formations", ""), ("club_ids", ""), ("club_kits", ""), ("club_away_kits", ""))
# per place of a league: what the person set, which an update keeps for the same club
KEEP_LISTS = (("club_coaches", ""), ("club_formations", ""), ("club_ids", ""))
# what an update takes from the release (and KEEP_LISTS put back club by club)
FRESH = ("club_names", "club_abbrs", "club_crests", "club_kits", "club_away_kits", "game_clubs", "newlife",
         "clubs") + tuple(k for k, _e in KEEP_LISTS)


def keeps_lineup(x):
    """what an update does with league x's clubs unless told: keep the line-up the person made
    (custom), take the release's (a league added whole in 0.1.8 on), and keep it for a league
    added before 0.1.8 -- nothing says whether its clubs were picked by hand"""
    nl = x.get("newlife") or {}
    return bool(nl.get("custom")) or not nl.get("key")


def lineup(rel, x, rows, keep=None):
    """(the league of rel league x of the recipe is, the clubs it gets: E with "clubs" and
    "in_game") -- the release's line-up for it, or x's own clubs still in rel when keep
    (keeps_lineup(x) when None). Error when rel has no such league."""
    nl = x["newlife"]
    old_nl = [str(i) for i in nl.get("clubs") or []]
    gc_old = [str(e["id"]) for e in x.get("game_clubs") or []]
    by_key = {tuple(L["key"]): L for L in rows}
    k = tuple(nl.get("key") or ())
    if k not in by_key:              # added before 0.1.8: the league most of its clubs are in now
        votes = collections.Counter((rel.clubs[i].get("country", ""), rel.clubs[i].get("league", ""))
                                    for i in old_nl + gc_old if i in rel.clubs)
        k = next((v for v, _c in votes.most_common() if v in by_key), None)
    if k is None:
        raise Error("%s: NewLife %s has no league with its clubs" % (x["name"], rel.meta.get("version", "")))
    E = dict(by_key[k])
    if keeps_lineup(x) if keep is None else keep:
        E["clubs"] = sorted(i for i in old_nl if i in rel.clubs and rel.clubs[i].get("in_game") != "1")
        E["in_game"] = sorted(gc_old)
    return by_key[k], E


def update_league(recipe, rel, x, rows, info=None, keep=None):
    """bring league x of the recipe (added from another NewLife version) to release rel, in its
    place: the release's clubs and squads for it -- the clubs the league has in rel, or x's own
    line-up when keep (see lineup) -- and everything else of the league as it was: its name,
    division, format, European places, cups and the rest. A club that stays keeps its manager,
    formation, id, a crest picked by hand, its manager's portrait and its stadium; a club of the
    game keeps what was set for it. rows = rel.leagues(...).
    Returns (the league's name, players left at their game club, players another league has,
    [notes])."""
    nl = x["newlife"]
    name, idx = x["name"], recipe["leagues"].index(x)
    old_n = int(x.get("clubs") or 0)
    old_nl = [str(i) for i in nl.get("clubs") or []]
    gc_old = {str(e["id"]): e for e in x.get("game_clubs") or []}
    notes = []
    _L, E = lineup(rel, x, rows, keep)
    keep = keeps_lineup(x) if keep is None else keep
    others = {str(i) for y in recipe["leagues"] if y is not x for i in (y.get("newlife") or {}).get("clubs") or []}
    others |= {str(e["id"]) for y in recipe["leagues"] if y is not x for e in y.get("game_clubs") or []}
    clash = [i for i in E["clubs"] + E["in_game"] if i in others]
    if clash:
        notes.append("%s: %s stay in the league they are in already" % (
            name, ", ".join(rel.clubs[i]["name"] if i in rel.clubs else i for i in clash)))
        E["clubs"] = [i for i in E["clubs"] if i not in clash]
        E["in_game"] = [i for i in E["in_game"] if i not in clash]

    # by club: ("n", NewLife id), ("g", the game's id) or ("o", place) for a club of the
    # builder's own the person put in the league, which stays as it is
    who = {}
    for j in range(old_n):
        g = next((i for i, e in gc_old.items() if int(e.get("at", -1)) == j), None)
        i = old_nl[j] if j < len(old_nl) else ""
        is_nl = i in rel.clubs or (i.isdigit() and B.NEWLIFE_TEAMS[0] <= int(i) <= B.NEWLIFE_TEAMS[1])
        who[j] = ("g", g) if g else ("n", i) if is_nl else ("o", j)
    own = [j for j in range(old_n) if who[j][0] == "o"]
    total = len(E["clubs"]) + len(game_clubs(E, info)) + len(own)
    if not B.CLUBS_MIN <= total <= B.CLUBS_MAX:
        raise Error("%s would have %d clubs with NewLife %s; a league takes %d to %d" % (
            name, total, rel.meta.get("version", ""), B.CLUBS_MIN, B.CLUBS_MAX))
    pl = recipe.setdefault("players", {})
    own_vals = {j: {key: (list(x.get(key) or []) + [e] * old_n)[j] for key, e in PLACE_LISTS} for j in own}
    own_pl = {j: pl.get(P.new_key(name, j)) for j in own}
    kept = {}
    for j, w in who.items():
        if w[0] == "o":
            continue
        d = {key: (list(x.get(key) or []) + [e] * old_n)[j] for key, e in KEEP_LISTS}
        crest = (list(x.get("club_crests") or []) + [None] * old_n)[j]
        if crest and not _from_cache(crest):
            d["club_crests"] = crest
        c = pl.get(P.new_key(name, j)) or {}
        d.update({f: c[f] for f in ("coach_portrait", "stadium") if c.get(f)})
        kept[w] = d

    def club_ref(r):                 # "league/place" of this league -> who, else r as it is
        lg, _s, j = r.rpartition("/") if isinstance(r, str) else ("", "", "")
        return who.get(int(j)) if lg == name and j.isdigit() else r
    cups = [(c, [club_ref(r) for r in c.get("clubs") or []]) for c in recipe.get("preseason_cups") or []]
    for key in [key for key in pl if key.rpartition("/")[0] == name]:
        del pl[key]
    for c in pl.values():            # players other clubs took from this league's old squads
        if c.get("join"):
            c["join"] = [r for r in c["join"] if str(r).rpartition("/")[0].rpartition("/")[0] != name]

    recipe["leagues"].pop(idx)
    try:
        got, stayed, elsewhere = add_league(recipe, rel, E, legs=x.get("legs", 2), info=info,
                                            custom=bool(keep), name=name, more=len(own))
    except Exception:
        recipe["leagues"].insert(idx, x)
        raise
    y = recipe["leagues"].pop()
    place = {}
    z = {f: v for f, v in x.items() if f not in FRESH}
    z.update({f: v for f, v in y.items() if f not in ("name", "legs", "logo", "country")})
    if y.get("logo") and not (x.get("logo") and not _from_cache(x["logo"])):
        z["logo"] = y["logo"]
    for e in z.get("game_clubs") or []:
        e.update({f: v for f, v in gc_old.get(str(e["id"]), {}).items() if f not in ("at", "id")})
    n = int(z["clubs"])
    pos = len(z["newlife"]["clubs"])     # the person's own clubs: after the NewLife ones, before the game's
    for j in own:
        for key, e in PLACE_LISTS:
            lst = list(z.get(key) or [])
            lst = lst[:n] + [e] * (n - len(lst))
            lst.insert(pos, own_vals[j][key])
            if any(v not in ("", None) for v in lst):
                z[key] = lst
            else:
                z.pop(key, None)
        for e in z.get("game_clubs") or []:
            if int(e["at"]) >= pos:
                e["at"] = int(e["at"]) + 1
        for m in range(n - 1, pos - 1, -1):
            if P.new_key(got, m) in pl:
                pl[P.new_key(got, m + 1)] = pl.pop(P.new_key(got, m))
        if own_pl[j]:
            pl[P.new_key(got, pos)] = own_pl[j]
        n += 1
        z["clubs"] = n
        place[("o", j)] = pos
        pos += 1
    place = dict(place)
    place.update({("n", str(i)): j for j, i in enumerate(z["newlife"]["clubs"])})
    place.update({("g", str(e["id"])): int(e["at"]) for e in z.get("game_clubs") or []})
    for w, d in kept.items():
        j = place.get(w)
        if j is None:
            continue
        for key, v in d.items():
            if key in ("coach_portrait", "stadium"):
                pl.setdefault(P.new_key(got, j), {})[key] = v
            elif v not in ("", None):
                lst = list(z.get(key) or [])
                z[key] = lst + [None if key == "club_crests" else ""] * (n - len(lst))
                z[key][j] = v
    for c, refs in cups:
        c["clubs"] = [r if not isinstance(r, tuple) else "%s/%d" % (got, place[r])
                      for r in refs if r is not None and (not isinstance(r, tuple) or r in place)]
    if n != old_n:
        sp = z.get("split")
        if sp and z.get("apertura"):
            sp["groups"] = [n]
        elif sp and sp.get("groups"):
            sp["groups"] = list(sp["groups"])
            sp["groups"][-1] = int(sp["groups"][-1]) + n - old_n
        notes.append("%s now has %d clubs (it had %d): check its European places and promotion" % (got, n, old_n))
    recipe["leagues"].insert(idx, z)
    return got, stayed, elsewhere, notes


# ---- the game's own leagues, brought to the release's season (0.1.8) ----
#
# The release lists the clubs of the game's leagues as they line up in its season: who went up,
# who went down, and every squad with the game's player ids. Bringing a game league to it takes
# three things, none of which changes how many clubs any competition of the game has:
#   - a club that went up or down between two leagues of the game swaps places with one going
#     the other way (edits.swaps, as Game's leagues and clubs > Swap does: every entry, the cup
#     and a continental place too);
#   - a club that went down out of the game's world (to League One, say) hands its place to a
#     club the release brings up that the game has not got: the game's club takes that club's
#     name, short name, crest and squad (edits.clubs and its players entry);
#   - every club of the league gets the release's squad: players of the game join it from their
#     old club ("join"), players the game has not got are added ("add"), the rest leave
#     ("remove"), and everyone's abilities come from the release ("edits").
# What it did is kept in recipe["newlife_game"], so doing it again (a newer release) or undoing
# it takes back exactly that and nothing a person set by hand.

MATCH = 0.5          # a release league is a game league when it holds this share of its clubs


def _game_entry(info, at, tid):
    """a club of the game in a NewLife league; one whose only places are continental keeps them,
    so nobody has to take its place (GitHub #82: Ludogorets in the Europa League stopped the Build)"""
    e = {"at": at, "id": tid}
    if info is not None and B.game_club_where(info, int(tid)) and not B.game_club_where(info, int(tid), True):
        e["keep"] = True
    return e


def _game_targets(rel, info):
    """({game league cid: release league}, {team id: cid of the game league the release puts it
    in}) for the game's leagues the release has"""
    rows = rel.leagues(str)
    match, target = {}, {}
    for _r, cid, _n, ts in B.game_leagues(info["base"]):
        if cid in info["friendly_cids"]:
            continue
        ts = set(ts)
        best = max(rows, key=lambda L: len(ts & {int(x) for x in L["in_game"]}), default=None)
        if best is not None and len(ts & {int(x) for x in best["in_game"]}) >= MATCH * len(ts):
            match[cid] = best
    for cid, L in match.items():
        for t in L["in_game"]:
            target[int(t)] = cid
    return match, target


def _refresh_record(recipe):
    r = recipe.get("newlife_game") or {}
    return {"version": r.get("version", ""), "swaps": [[int(a) for a in p] for p in r.get("swaps") or []],
            "replaced": {int(k): v for k, v in (r.get("replaced") or {}).items()},
            "clubs": [int(t) for t in r.get("clubs") or []]}


def _hand_clubs(recipe):
    """team ids the recipe already changes by hand: clubs of a new league, swaps and renames of
    its own, and clubs whose players it changes"""
    mine = _refresh_record(recipe)
    used = set()
    for x in recipe.get("leagues") or []:
        for e in x.get("game_clubs") or []:
            used.add(int(e["id"]))
            if e.get("swap") not in (None, "") and not isinstance(e.get("swap"), dict):
                used.add(int(e["swap"]))
    for p in (recipe.get("edits") or {}).get("swaps") or []:
        if [int(a) for a in p] not in mine["swaps"]:
            used |= {int(a) for a in p}
    used |= {int(k) for k in ((recipe.get("edits") or {}).get("clubs") or {}) if int(k) not in mine["replaced"]}
    for k, c in (recipe.get("players") or {}).items():
        if k.isdigit() and not c.get("newlife_game") and any(c.get(f) for f in ("edits", "join", "add", "remove")):
            used.add(int(k))
    return used


def game_league_plan(recipe, rel, info):
    """[{cid, name, release, swaps: [(team id, team id it swaps with)], replace: [(team id,
    release club id)], clubs: [team id], notes: [...]}], one per game league the release has:
    what refresh_game_leagues does to it (clubs: the team ids that get the release's squad)"""
    match, target = _game_targets(rel, info)
    league_of = {}
    for _r, c, _n, ts in B.game_leagues(info["base"]):
        for t in ts:
            league_of.setdefault(t, c)
    used = _hand_clubs(recipe)
    moving = collections.defaultdict(list)          # (from league, to league) -> clubs
    for t, c in sorted(target.items()):
        cur = league_of.get(t)
        if cur in match and cur != c and t not in used:
            moving[(cur, c)].append(t)
    swaps = {}
    for (a, b), ts in sorted(moving.items()):
        for x, y in zip(ts, moving.get((b, a), [])):
            if x not in swaps and y not in swaps:
                swaps[x], swaps[y] = y, x
    out = []
    for cid, L in sorted(match.items(), key=lambda kv: info["comp_names"].get(kv[0], "")):
        ts = next(tt for _r, c, _n, tt in B.game_leagues(info["base"]) if c == cid)
        p = {"cid": cid, "name": info["comp_names"].get(cid, str(cid)), "release": L["name"],
             "swaps": [], "replace": [], "clubs": [], "notes": []}
        p["swaps"] = [(t, swaps[t]) for t in ts if t in swaps]
        down = [t for t in ts if target.get(t) != cid and t not in swaps and t not in used]
        new = [c for c in L["clubs"] if c in rel.clubs]
        p["replace"] = list(zip(down, new))
        if len(down) > len(new):
            p["notes"].append("%d club(s) the release has elsewhere stay: no club comes up in their place"
                              % (len(down) - len(new)))
        if len(new) > len(down):
            p["notes"].append("%d club(s) the release has in this league find no place: the league keeps "
                              "its %d clubs" % (len(new) - len(down), len(ts)))
        hand = [t for t in ts if t in used]
        if hand:
            p["notes"].append("%d club(s) the recipe already changes by hand are left as they are" % len(hand))
        p["clubs"] = [t for t in ts if target.get(t) == cid and t not in used] + [y for _x, y in p["swaps"]]
        out.append(p)
    return out


def undo_game_leagues(recipe):
    """take back what refresh_game_leagues did (recipe["newlife_game"]); True when there was any"""
    if not recipe.get("newlife_game"):
        return False
    r = _refresh_record(recipe)
    ed = recipe.get("edits") or {}
    if r["swaps"] and ed.get("swaps"):
        ed["swaps"] = [p for p in ed["swaps"] if [int(a) for a in p] not in r["swaps"]]
        if not ed["swaps"]:
            ed.pop("swaps")
    clubs = ed.get("clubs") or {}
    for t, was in r["replaced"].items():
        e = clubs.get(str(t))
        if e is None:
            continue
        for k, v in was.items():
            if e.get(k) == v:
                e.pop(k)
        if not e:
            clubs.pop(str(t))
    if "clubs" in ed and not ed["clubs"]:
        ed.pop("clubs")
    if "edits" in recipe and not recipe["edits"]:
        recipe.pop("edits")
    pl = recipe.get("players") or {}
    for t in r["clubs"]:
        c = pl.get(str(t))
        if c and c.pop("newlife_game", None):
            for k in ("edits", "join", "add", "remove"):
                c.pop(k, None)
            if not c:
                pl.pop(str(t))
    recipe.pop("newlife_game")
    return True


def refresh_game_leagues(recipe, rel, info, cids):
    """bring the game's leagues cids (competition ids, from game_league_plan) to the release's
    season (see above); what an earlier refresh did goes first. Returns counts {"swaps",
    "replaced", "clubs", "join", "add", "remove", "stayed"}."""
    undo_game_leagues(recipe)
    plan = [p for p in game_league_plan(recipe, rel, info) if p["cid"] in set(cids)]
    ed = recipe.setdefault("edits", {})
    rec = {"version": str(rel.meta.get("version", "")), "swaps": [], "replaced": {}, "clubs": []}
    for p in plan:
        for a, b in p["swaps"]:
            if [b, a] not in rec["swaps"] and [a, b] not in rec["swaps"]:
                rec["swaps"].append([a, b])
    if rec["swaps"]:
        ed["swaps"] = list(ed.get("swaps") or []) + [list(s) for s in rec["swaps"]]
    clubs = ed.setdefault("clubs", {})
    squads = {}                                    # team id -> release club id whose squad it gets
    for p in plan:
        for t in p["clubs"]:
            squads[t] = str(t)
    for p in plan:
        for t, c in p["replace"]:
            taken = {x.get("abbr") for k, x in clubs.items() if k != str(t)} | \
                    {s for _n, s in info["clubs"].values()}
            was = {"name": rel.clubs[c]["name"], "abbr": abbr(rel.clubs[c]["name"], taken)}
            crest = rel.crest(c)
            if crest:
                was["crest"] = crest
            clubs.setdefault(str(t), {}).update(was)
            rec["replaced"][str(t)] = was
            squads[t] = c
    if not clubs:
        ed.pop("clubs")
    if not ed:
        recipe.pop("edits")
    n = _game_squads(recipe, rel, info, squads)
    rec["clubs"] = sorted(int(k) for k, c in (recipe.get("players") or {}).items() if c.get("newlife_game"))
    recipe["newlife_game"] = rec
    n.update(swaps=len(rec["swaps"]), replaced=len(rec["replaced"]), clubs=len(rec["clubs"]))
    return n


def _game_squads(recipe, rel, info, squads):
    """the release's squad (rel.squad) for each game club, squads: {team id: release club id}"""
    db = P.Squads(info["base"])
    national = info.get("national") or set()
    pl = recipe.setdefault("players", {})
    taken = {str(r) for c in pl.values() for r in c.get("join") or []}
    size = {t: len(v) for t, v in db.by_club.items()}       # squads as joins and removals leave them
    n = collections.Counter()
    plan = {}
    for t, c in sorted(squads.items()):
        have = [pid for _o, pid, _s, _x in db.by_club.get(t, []) if pid in db.index]
        keep, join, add, ed = [], [], [], {}
        for r in rel.squad(c):
            ch = {f: r[f] for f in P.FIELDS if r.get(f, "") != ""}
            g = str(r.get("game_id", "")).strip()
            if not g.isdigit():                   # no id in the release: one of his club's by name
                g = next((str(p) for p in have if p not in keep and P.same_name(r["name"], db.name(p))), "")
            if not g and len(r["name"].split()) == 1:  # "Gabriel": the one player of the club so called
                one = [p for p in have if p not in keep and P._letters(r["name"]) in map(P._letters, P._words(db.name(p)))]
                g = str(one[0]) if len(one) == 1 else ""
                if g:
                    r = dict(r, name=db.name(one[0]))
            if g.isdigit() and int(g) in db.index and P.same_name(r["name"], db.name(int(g))):
                if int(g) in have:
                    keep.append(int(g))
                    ed[g] = ch
                    continue
                old = [x for x in db.clubs_of.get(int(g), []) if x not in national]
                if g in taken or (old and old[0] not in squads and size[old[0]] - 1 < P.MIN_SQUAD):
                    n["stayed"] += 1              # another club has him and cannot spare him
                    continue
                if old:
                    size[old[0]] -= 1
                taken.add(g)
                join.append(g)
                ed[g] = ch
                continue
            ch["name"] = r["name"]
            add.append(ch)
        plan[t] = (have, keep, join, add, ed)
    joining = {g for x in plan.values() for g in x[2]}
    for t, (have, keep, join, add, ed) in plan.items():
        out = sum(1 for p in have if str(p) in joining)          # signed by another club
        gone = [p for p in have if p not in keep and str(p) not in joining]
        gone = gone[:max(len(have) - out + len(join) + len(add) - P.MIN_SQUAD, 0)]   # a short squad keeps some
        stays = len(have) - out - len(gone)
        add = add[:max(P.CLUB_MAX - stays - len(join), 0)]
        like = str(keep[0] if keep else have[0]) if have else ""
        c = pl.setdefault(str(t), {})
        if ed:
            c["edits"] = ed
        if join:
            c["join"] = join
        if add:
            c["add"] = [dict(ch, like=like) if like else ch for ch in add]
        if gone:
            c["remove"] = [str(p) for p in gone]
        if ed or join or add or gone:
            c["newlife_game"] = True
        elif not c:
            pl.pop(str(t))
        n["join"] += len(join)
        n["add"] += len(add)
        n["remove"] += len(gone)
    return n
