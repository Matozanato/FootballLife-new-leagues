"""a NewLife Database release as leagues to pick: every league of the release, its clubs and
players, and the recipe entries that put a whole league in the game in one go -- a new League
Builder league with the release's clubs, each club's squad its best players from the release.

A release comes whole (newlife-<version>/: players.csv, clubs.csv, newlife.json) or in parts
(NewLife-<version>-<part>.zip, one per continent or piece of one; split.py): the person
downloads the parts they want into one folder and Mod Studio reads all of them from there, as
they are. The release is downloaded separately (it is not on GitHub); nothing of it is copied
anywhere but the recipe the person builds.
"""
import csv, glob, io, json, os, zipfile

import leaguebuilder as B
import lbplayers as P

FILES = ("players.csv", "clubs.csv", "newlife.json")
PART = "NewLife-*.zip"


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
    """[(label, open(name) -> text file)] -- the whole release, or every part"""
    if all(os.path.exists(os.path.join(where, f)) for f in FILES):
        return [("", lambda n: open(os.path.join(where, n), encoding="utf-8", newline=""))]
    out = []
    for zp in parts_in(where):
        try:
            z = zipfile.ZipFile(zp)
            missing = [f for f in FILES if f not in z.namelist()]
        except (zipfile.BadZipFile, OSError) as e:
            raise Error("%s is not a NewLife part (%s) -- download it again" % (os.path.basename(zp), e))
        if missing:
            raise Error("%s is not a NewLife part: no %s" % (os.path.basename(zp), ", ".join(missing)))
        out.append((os.path.basename(zp), lambda n, z=z: io.TextIOWrapper(z.open(n), encoding="utf-8", newline="")))
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
        versions = set()
        for label, opener in _sources(where):
            with opener("newlife.json") as f:
                m = json.load(f)
            versions.add(m.get("version", "?"))
            self.meta = self.meta or m
            if m.get("part"):
                self.parts.append(m["part"].get("name", label))
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
            out.append({"name": name, "country": country_of(cty) if cty.isdigit() else "", "clubs": sorted(ids),
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


def fits(L):
    return B.CLUBS_MIN <= len(L["clubs"]) <= B.CLUBS_MAX


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


def add_league(recipe, rel, L, legs=2):
    """put league L (from rel.leagues) in the recipe: a new league with its clubs, every club's
    squad from the release. The whole squad is set: places the release has no player for leave
    the club, down to P.MIN_SQUAD. Returns the new league's name."""
    if not fits(L):
        raise Error("%s has %d clubs; a league takes %d to %d" % (L["name"], len(L["clubs"]), B.CLUBS_MIN, B.CLUBS_MAX))
    name = unique_name(recipe, L["name"])
    clubs = sorted(L["clubs"], key=lambda i: rel.clubs[i]["name"].lower())
    taken = set()
    abbrs = []
    for i in clubs:
        a = abbr(rel.clubs[i]["name"], taken)
        taken.add(a)
        abbrs.append(a)
    recipe["leagues"].append({"name": name, "country": L["country"], "clubs": len(clubs), "legs": legs,
                              "club_names": [rel.clubs[i]["name"] for i in clubs], "club_abbrs": abbrs,
                              "club_kits": [rel.clubs[i].get("home_kit", "") for i in clubs],
                              "club_away_kits": [rel.clubs[i].get("away_kit", "") for i in clubs],
                              "newlife": {"version": rel.meta.get("version", ""), "clubs": [int(i) for i in clubs]}})
    pl = recipe.setdefault("players", {})
    for k, i in enumerate(clubs):
        sq = rel.squad(i)
        ed = {}
        for n, r in enumerate(sq):
            ch = {"name": r["name"]}          # no order: Build picks the best eleven
            for f in P.FIELDS:
                if r.get(f, "") != "":
                    ch[f] = r[f]
            ed[str(n)] = ch
        c = {"edits": ed}
        if len(sq) < P.SQUAD:
            c["remove"] = [str(n) for n in range(max(len(sq), P.MIN_SQUAD), P.SQUAD)]
        pl[P.new_key(name, k)] = c
    return name
