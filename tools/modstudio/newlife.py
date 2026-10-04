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


def add_league(recipe, rel, L, legs=2, info=None):
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
    Returns (the new league's name, players left at their game club for lack of players,
    players left out because another league has them)."""
    game = game_clubs(L, info)
    if not fits(L, info):
        raise Error("%s has %d clubs; a league takes %d to %d" % (L["name"], len(L["clubs"]) + len(game),
                                                                  B.CLUBS_MIN, B.CLUBS_MAX))
    name = unique_name(recipe, L["name"])
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
    crests = [rel.crest(i) for i in clubs]
    if any(crests):
        recipe["leagues"][-1]["club_crests"] = crests
    logo = rel.league_logo(L)
    if logo:
        recipe["leagues"][-1]["logo"] = logo
    if game:
        recipe["leagues"][-1]["game_clubs"] = [{"at": len(clubs) + j, "id": t} for j, t in enumerate(game)]
    pl = recipe.setdefault("players", {})
    db = P.Squads(info["base"]) if info and info.get("base") else None
    national = (info or {}).get("national") or set()
    taken = {str(r) for c in pl.values() for r in c.get("join") or []}   # moved by an earlier league
    leaving = collections.Counter()

    stayed = elsewhere = 0

    def mover(r):
        """("move", the game's id of the player in release row r) when he can come to his NewLife
        club; ("keep", that id) when he is a player of these tables but must stay where he is --
        his game club would drop below P.MIN_SQUAD, or an earlier league already took him; and
        ("copy", None) when he is not a player of these tables and becomes a new player. A row
        that is kept is left out of the NewLife club: copying him would put the same man at two
        clubs, which is the thing the move exists to prevent."""
        g = str(r.get("game_id", "")).strip()
        if db is None or not g.isdigit() or int(g) not in db.index:
            return "copy", None
        if not P.same_name(r["name"], db.name(int(g))):
            return "copy", None               # another database: that id is somebody else
        if g in taken:
            return "keep", g                  # an earlier league already has him
        old = [t for t in db.clubs_of.get(int(g), []) if t not in national]
        if old and len(db.by_club[old[0]]) - leaving[old[0]] - 1 < P.MIN_SQUAD:
            return "keep", g                  # his club would have too few players left
        if old:
            leaving[old[0]] += 1
        taken.add(g)
        return "move", g

    proto = db.proto() if db is not None else []
    league_ovr = [P.overall(r) for i in clubs for r in rel.squad(i)]

    for k, i in enumerate(clubs):
        sq = rel.squad(i)
        ed, join = {}, []
        for r in sq:
            ch = {"name": r["name"]}          # no order: Build picks the best eleven
            for f in P.FIELDS:
                if r.get(f, "") != "":
                    ch[f] = r[f]
            how, g = mover(r)
            if how == "move":
                del ch["name"]                # the game's spelling stays
                join.append(g)
                ed[g] = ch
            elif how == "keep":
                # left out: he is somebody the game already has, at a club that cannot spare
                # him or at a NewLife club of an earlier league. The place stays with the
                # prototype player mkplayers made (keep below keeps enough of them: the club
                # never drops under P.MIN_SQUAD), so the club has one real player fewer and no
                # copy of him anywhere.
                if g in taken:
                    elsewhere += 1
                else:
                    stayed += 1
            else:
                ed[str(len(ed) - len(join))] = ch
        keep = max(len(sq) - len(join), P.MIN_SQUAD - len(join))
        want = P.fill_level([P.overall(r) for r in sq], league_ovr)
        for n in range(len(ed) - len(join), keep):          # prototype players who stay
            if n < len(proto) and want is not None and str(n) not in ed:
                ed[str(n)] = P.at_level(proto[n], want)
        c = {"edits": ed}
        if join:
            c["join"] = join
        if keep < P.SQUAD:
            c["remove"] = [str(n) for n in range(keep, P.SQUAD)]
        pl[P.new_key(name, k)] = c
    return name, stayed, elsewhere
