r"""league packages (.fl26pack): a modder makes leagues once, anybody adds them to their own game.

    python lbpackage.py export <recipe.json> <out.fl26pack> --name "..." [--author ..] [--version ..]
                            [--league "League A" --league "League B"] [--edits] [--sider <SiderAddons>]
    python lbpackage.py show   <pack.fl26pack>
    python lbpackage.py add    <pack.fl26pack> <recipe.json> [--store <dir>]
    python lbpackage.py remove <tag> <recipe.json>

A package carries a piece of a recipe, never a built world: the ids a league gets depend on
what else a person's game already has, so they are given out when that person builds.  That is
also why faces travel as they were made and are moved to their players' ids at build
(lbfaces.py).  Inside the zip:

    manifest.json    format, name, author, version, description, the leagues
    recipe.json      the leagues (as a recipe has them), their clubs' player changes, and with
                     --edits the changes to the game's own leagues, clubs and players
    assets\...       logos and crests the leagues and clubs use
    kitserver\<n>\   a club's Kit Server kit folder (p1, p2, g1 ...), lbservers.py writes its line
    scoreboards\<n>\ a league's Scoreboard Server folder, the same
    faces\<n>\...    the faces players were given (#Win, sourceimages, portrait.dds)

Paths in recipe.json are relative to the package.  add() unpacks a package into a store
folder, makes its paths full again and puts its leagues into a recipe, remembering under
"packs" what came from which package so remove() can take exactly that out again.
"""
import argparse, json, os, re, shutil, sys, zipfile

import lbfaces

FORMAT = "fl26pack"
FORMAT_VERSION = 1
EXT = ".fl26pack"


class Error(Exception):
    pass


# a league's own pictures, one path each: its logo, the country's flag, its cups' logos
LEAGUE_PICTURES = ("logo", "flag", "cup_logo", "supercup_logo", "league_cup_logo")
# the league fields each part of a package (PARTS) carries
LEAGUE_PARTS = {"squads": ("formation", "club_formations"),
                "crests": LEAGUE_PICTURES + ("club_crests",),
                "managers": ("club_coaches",),
                "kits": ("club_kits", "club_away_kits"),
                "kitfiles": ("kit_folders",),
                "scoreboards": ("scoreboard",)}


def tag_of(manifest):
    t = re.sub(r"[^A-Za-z0-9._-]+", "-", "%s-%s" % (manifest.get("name", "pack"), manifest.get("author", ""))).strip("-.")
    return t[:60] or "pack"


# ---- export ----

# what a package can carry besides the leagues themselves; Make a package ticks them all
PARTS = ("squads", "faces", "crests", "managers", "kits", "kitfiles", "scoreboards", "stadiums")


def export(recipe, out, meta, leagues=None, edits=False, log=print, players=True, parts=None, sider=None):
    """write the package out from recipe; leagues are names (all when None), meta has name,
    author, version, description.  parts (all of PARTS when None) is what goes in:
      squads    the player changes of the clubs (and their formations)
      faces     the faces and portraits those players were given
      crests    club crests, league logos and flags
      managers  managers' names and portraits
      kits      the clubs' shirt colours
      kitfiles  the clubs' Kit Server kits (their folders, p1 p2 g1 ...)
      scoreboards  the leagues' Scoreboard Server scoreboards
      stadiums  the clubs' home stadiums (the Stadium Server line, not the stadium itself)
    sider (the SiderAddons folder): kits and scoreboards a league has no folder for in the recipe
    are taken from the world as it is in the game (lbservers.collect).
    A package without squads can go on top of a squad database that is updated on its own
    (NewLife) without putting old squads back (see overlay()).  players=False is parts without
    squads.  Returns the manifest."""
    parts = set(PARTS if parts is None else parts)
    if not players:
        parts.discard("squads")
    bad = parts - set(PARTS)
    if bad:
        raise Error("no such part of a package: %s" % ", ".join(sorted(bad)))
    if "squads" not in parts:
        parts.discard("faces")
    squads = "squads" in parts
    if not str(meta.get("name", "")).strip():
        raise Error("the package needs a name")
    if sider and ({"kitfiles", "scoreboards"} & parts):
        import lbservers
        try:
            with open(os.path.join(sider, "livecpk", recipe.get("world") or "", "leaguebuilder-plan.json"),
                      encoding="utf-8") as f:
                built = json.load(f)
        except (OSError, ValueError):
            built = None
        if built:
            recipe = json.loads(json.dumps(recipe))
            nk, nb = lbservers.collect(recipe, built, sider, leagues)
            log("from the game: %d club kits, %d scoreboards" % (nk, nb))
    have = {L["name"]: L for L in recipe.get("leagues", [])}
    names = list(have) if leagues is None else list(leagues)
    missing = [n for n in names if n not in have]
    if missing:
        raise Error("no league called %s in the recipe" % ", ".join(missing))
    if not names and not edits:
        raise Error("the package would be empty: pick at least one league")
    for n in names:
        up = have[n].get("above")
        if isinstance(up, str) and up and not up.isdigit() and up not in names:
            raise Error("%s sits below %s, which is not in the package" % (n, up))

    tmp = out + ".making"
    if os.path.exists(tmp):
        shutil.rmtree(tmp)
    os.makedirs(tmp)
    used = {}

    def asset(path):
        if not path:
            return path
        if not os.path.isfile(path):
            raise Error("picture %s is missing" % path)
        base = re.sub(r"[^A-Za-z0-9._-]+", "_", os.path.basename(path))
        stem, ext = os.path.splitext(base)
        name, k = base, 1
        while name.lower() in used and used[name.lower()] != os.path.abspath(path):
            k += 1
            name = "%s_%d%s" % (stem, k, ext)
        if name.lower() not in used:
            used[name.lower()] = os.path.abspath(path)
            os.makedirs(os.path.join(tmp, "assets"), exist_ok=True)
            shutil.copyfile(path, os.path.join(tmp, "assets", name))
        return "assets/" + name

    nface = [0]
    nfold = {"kitserver": 0, "scoreboards": 0}

    def folder(path, kind):
        if not path:
            return path
        if not os.path.isdir(path):
            raise Error("folder %s is missing" % path)
        rel = "%s/%d" % (kind, nfold[kind])
        nfold[kind] += 1
        shutil.copytree(path, os.path.join(tmp, kind, str(nfold[kind] - 1)))
        return rel

    def face(path):
        d = os.path.join(tmp, "faces", str(nface[0]))
        lbfaces.pack(path, d)
        nface[0] += 1
        return "faces/%d" % (nface[0] - 1)

    def players_of(c):
        c = json.loads(json.dumps(c))
        for ch in list((c.get("edits") or {}).values()) + list(c.get("add") or []):
            if "faces" not in parts:
                ch.pop("face", None)
                ch.pop("portrait", None)
            if str(ch.get("face", "")).strip():
                ch["face"] = face(ch["face"])
            if str(ch.get("portrait", "")).strip():
                ch["portrait"] = asset(ch["portrait"])
        if c.get("coach_portrait"):
            c["coach_portrait"] = asset(c["coach_portrait"])
        if c.get("join"):                              # a game player, or one of the package's clubs
            c["join"] = [r for r in c["join"] if str(r).isdigit() or str(r).rsplit("/", 2)[0] in names]
            if not c["join"]:
                c.pop("join")
        return c

    out_r = {"leagues": [], "players": {}, "edits": {}}
    for n in names:
        L = json.loads(json.dumps(have[n]))
        L.pop("pack", None)
        for part, keys in LEAGUE_PARTS.items():
            if part not in parts:
                for k in keys:
                    L.pop(k, None)
        for k in LEAGUE_PICTURES:
            if L.get(k):
                L[k] = asset(L[k])
        if L.get("club_crests"):
            L["club_crests"] = [asset(p) if p else p for p in L["club_crests"]]
        if L.get("kit_folders"):
            L["kit_folders"] = [folder(p, "kitserver") if p else "" for p in L["kit_folders"]]
        if L.get("scoreboard"):
            L["scoreboard"] = folder(L["scoreboard"], "scoreboards")
        out_r["leagues"].append(L)
    for key, c in (recipe.get("players") or {}).items():
        lg = key.rpartition("/")[0]
        if (lg in names) or (edits and key.isdigit()):
            if not squads:
                c = {k: c[k] for k in ("coach_portrait", "stadium") if c.get(k)}
            if "managers" not in parts:
                c.pop("coach_portrait", None)
            if "stadiums" not in parts:
                c.pop("stadium", None)
            if (c.get("edits") or c.get("add") or c.get("remove") or c.get("join") or c.get("coach_portrait")
                    or c.get("stadium")):
                out_r["players"][key] = players_of(c)
    if edits:
        e = json.loads(json.dumps(recipe.get("edits") or {}))
        if "crests" not in parts:
            for kind, key in (("leagues", "logo"), ("competitions", "logo"), ("clubs", "crest")):
                for k, v in list((e.get(kind) or {}).items()):
                    v.pop(key, None)
                    if not v:
                        e[kind].pop(k)
        for v in (e.get("leagues") or {}).values():
            if v.get("logo"):
                v["logo"] = asset(v["logo"])
        for v in (e.get("clubs") or {}).values():
            if v.get("crest"):
                v["crest"] = asset(v["crest"])
        out_r["edits"] = {k: v for k, v in e.items() if v}

    man = {"format": FORMAT, "format_version": FORMAT_VERSION,
           "name": meta["name"].strip(), "author": str(meta.get("author", "")).strip(),
           "version": str(meta.get("version", "1.0")).strip() or "1.0",
           "description": str(meta.get("description", "")).strip(),
           "made_with": str(meta.get("made_with", "")),
           "leagues": [{"name": L["name"], "country": L.get("country", ""), "clubs": L.get("clubs", 0),
                        "above": L.get("above")} for L in out_r["leagues"]],
           "clubs": sum(int(L.get("clubs", 0) or 0) for L in out_r["leagues"]),
           "faces": nface[0],
           "kits": nfold["kitserver"], "scoreboards": nfold["scoreboards"],
           "players": squads,
           "parts": [x for x in PARTS if x in parts],
           "edits": {k: len(v) for k, v in out_r["edits"].items()},
           "player_changes": sum(len(c.get("edits") or {}) + len(c.get("add") or []) for c in out_r["players"].values())}
    json.dump(man, open(os.path.join(tmp, "manifest.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    json.dump(out_r, open(os.path.join(tmp, "recipe.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    part = out + ".part"
    with zipfile.ZipFile(part, "w", zipfile.ZIP_DEFLATED) as z:
        for d, _subs, files in os.walk(tmp):
            for f in files:
                p = os.path.join(d, f)
                z.write(p, os.path.relpath(p, tmp).replace(os.sep, "/"))
    shutil.rmtree(tmp)
    os.replace(part, out)
    log("wrote %s: %d leagues, %d clubs, %d faces, %d kits, %d scoreboards"
        % (out, len(man["leagues"]), man["clubs"], man["faces"], man["kits"], man["scoreboards"]))
    return man


# ---- reading ----

def manifest(path):
    try:
        with zipfile.ZipFile(path) as z:
            man = json.loads(z.read("manifest.json").decode("utf-8"))
    except (zipfile.BadZipFile, KeyError, ValueError) as e:
        raise Error("%s is not a league package (%s)" % (path, e))
    if man.get("format") != FORMAT:
        raise Error("%s is not a league package" % path)
    if int(man.get("format_version", 0)) > FORMAT_VERSION:
        raise Error("%s was made by a newer program (package format %s); update FL26 Mod Studio"
                    % (os.path.basename(path), man.get("format_version")))
    return man


def unpack(path, store):
    r"""unpack into store\<tag>; returns (manifest, recipe piece with full paths, folder)"""
    man = manifest(path)
    dst = os.path.join(store, tag_of(man))
    if os.path.exists(dst):
        shutil.rmtree(dst)
    os.makedirs(dst)
    root = os.path.realpath(dst)
    with zipfile.ZipFile(path) as z:
        for n in z.namelist():
            t = os.path.realpath(os.path.join(dst, n))
            if not (t == root or t.startswith(root + os.sep)):
                raise Error("%s: a file points outside the package (%s)" % (path, n))
        z.extractall(dst)
    r = json.load(open(os.path.join(dst, "recipe.json"), encoding="utf-8"))

    def full(p):
        if not p:
            return p
        q = os.path.realpath(os.path.join(dst, p))
        if not q.startswith(root + os.sep):
            raise Error("%s: a path points outside the package (%s)" % (path, p))
        return q

    for L in r.get("leagues", []):
        for k in LEAGUE_PICTURES:
            if L.get(k):
                L[k] = full(L[k])
        if L.get("club_crests"):
            L["club_crests"] = [full(p) if p else p for p in L["club_crests"]]
        if L.get("kit_folders"):
            L["kit_folders"] = [full(p) if p else p for p in L["kit_folders"]]
        if L.get("scoreboard"):
            L["scoreboard"] = full(L["scoreboard"])
    for c in (r.get("players") or {}).values():
        for ch in list((c.get("edits") or {}).values()) + list(c.get("add") or []):
            if ch.get("face"):
                ch["face"] = full(ch["face"])
            if ch.get("portrait"):
                ch["portrait"] = full(ch["portrait"])
        if c.get("coach_portrait"):
            c["coach_portrait"] = full(c["coach_portrait"])
    e = r.get("edits") or {}
    for v in (e.get("leagues") or {}).values():
        if v.get("logo"):
            v["logo"] = full(v["logo"])
    for v in (e.get("clubs") or {}).values():
        if v.get("crest"):
            v["crest"] = full(v["crest"])
    return man, r, dst


# ---- into a recipe and out again ----

def clashes(recipe, piece, tag):
    """league names of piece that the recipe already has from elsewhere"""
    mine = {L["name"] for L in recipe.get("leagues", []) if L.get("pack") != tag}
    return [L["name"] for L in piece.get("leagues", []) if L["name"] in mine]


OVERLAY = ("club_crests", "club_coaches", "club_kits", "club_away_kits", "kit_folders", "scoreboard")


def overlay(recipe, piece, got, names):
    """a package made without players, on leagues the recipe already has (a squad database
    such as NewLife, updated on its own): its crests, managers, league pictures and stadiums go
    onto those leagues' clubs, matched by club name, and the squads stay as they are.  What
    was there before is kept in got so remove() puts it back."""
    have = {L["name"]: L for L in recipe.get("leagues", [])}
    pl = recipe.setdefault("players", {})
    for P in piece.get("leagues", []):
        if P["name"] not in names:
            continue
        L = have[P["name"]]
        was = {k: json.loads(json.dumps(L.get(k))) for k in OVERLAY + LEAGUE_PICTURES if k in L}
        got.setdefault("overlay", {})[L["name"]] = was
        at = {str(n).strip().lower(): i for i, n in enumerate(L.get("club_names") or [])}
        moved, hit = {}, 0
        for j, n in enumerate(P.get("club_names") or []):
            i = at.get(str(n).strip().lower())
            if i is None:
                continue
            moved[j], hit = i, hit + 1
            for k in OVERLAY:
                v = (P.get(k) or [])[j] if j < len(P.get(k) or []) else ""
                if v:
                    col = L.setdefault(k, [])
                    col.extend([""] * (i + 1 - len(col)))
                    col[i] = v
        for k in LEAGUE_PICTURES:
            if P.get(k):
                L[k] = P[k]
        for key, c in (piece.get("players") or {}).items():
            lg, _s, j = key.rpartition("/")
            if lg != P["name"] or not j.isdigit() or int(j) not in moved:
                continue
            dst = "%s/%d" % (lg, moved[int(j)])
            got.setdefault("before", {})[dst] = json.loads(json.dumps(pl.get(dst)))
            pl.setdefault(dst, {}).update({k: c[k] for k in ("coach_portrait", "stadium") if c.get(k)})
            got["players"].append(dst)
        got.setdefault("matched", {})[L["name"]] = [hit, len(P.get("club_names") or [])]


def add(recipe, man, piece, folder, rename=None):
    """put a package's piece into recipe (changed in place).  rename maps a clashing league
    name to the one it gets here.  A package added again (same tag) replaces itself.  A
    package made without players goes onto a league of the same name (see overlay())."""
    tag = tag_of(man)
    if tag in (recipe.get("packs") or {}):
        remove(recipe, tag)
    rename = dict(rename or {})
    onto = [] if man.get("players", True) else [n for n in clashes(recipe, piece, tag) if n not in rename]
    bad = [n for n in clashes(recipe, piece, tag) if n not in rename and n not in onto]
    if bad:
        raise Error("the recipe already has a league called %s" % ", ".join(bad))
    nm = lambda n: rename.get(n, n)
    got = {"name": man.get("name"), "author": man.get("author"), "version": man.get("version"),
           "folder": folder, "leagues": [], "players": [], "edits": {}}
    overlay(recipe, piece, got, onto)
    for L in piece.get("leagues", []):
        if L["name"] in onto:
            continue
        L = dict(L)
        L["name"] = nm(L["name"])
        if isinstance(L.get("above"), str) and not L["above"].isdigit():
            L["above"] = nm(L["above"])
        L["pack"] = tag
        recipe.setdefault("leagues", []).append(L)
        got["leagues"].append(L["name"])
    pl = recipe.setdefault("players", {})
    for key, c in (piece.get("players") or {}).items():
        lg, s, k = key.rpartition("/")
        if s and lg in onto:
            continue
        if s:
            key = "%s/%s" % (nm(lg), k)
        elif key in pl:
            # a club of the game the recipe already changes: the package's changes go on top
            old = pl[key]
            got.setdefault("before", {})[key] = json.loads(json.dumps(old))
            old.setdefault("edits", {}).update(c.get("edits") or {})
            old["add"] = (old.get("add") or []) + list(c.get("add") or [])
            old["remove"] = sorted(set(old.get("remove") or []) | set(c.get("remove") or []))
            got["players"].append(key)
            continue
        pl[key] = c
        got["players"].append(key)
    for kind, vals in (piece.get("edits") or {}).items():
        dst = recipe.setdefault("edits", {}).setdefault(kind, {})
        for k, v in vals.items():
            dst.setdefault(k, {}).update(v)
        got["edits"][kind] = list(vals)
    recipe.setdefault("packs", {})[tag] = got
    return tag


def remove(recipe, tag):
    """take out what a package brought: its leagues, their clubs' players, its edits"""
    got = (recipe.get("packs") or {}).pop(tag, None)
    if got is None:
        raise Error("no package %s in the recipe" % tag)
    names = set(got.get("leagues") or [])
    recipe["leagues"] = [L for L in recipe.get("leagues", []) if L.get("pack") != tag]
    for L in recipe.get("leagues", []):
        was = (got.get("overlay") or {}).get(L["name"])
        if was is not None:
            for k in OVERLAY + LEAGUE_PICTURES:
                if k in was:
                    L[k] = was[k]
                else:
                    L.pop(k, None)
    pl = recipe.get("players") or {}
    # a club of the game that the recipe changed before the package came gets those back
    before = got.get("before") or {}
    for key in got.get("players") or []:
        if before.get(key) is not None:
            pl[key] = before[key]
        else:
            pl.pop(key, None)
    for kind, keys in (got.get("edits") or {}).items():
        for k in keys:
            (recipe.get("edits") or {}).get(kind, {}).pop(k, None)
    return names


def packs(recipe):
    return dict(recipe.get("packs") or {})


def main():
    ap = argparse.ArgumentParser(prog="lbpackage.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("recipe")
    e.add_argument("out")
    e.add_argument("--name", required=True)
    e.add_argument("--author", default="")
    e.add_argument("--version", default="1.0")
    e.add_argument("--description", default="")
    e.add_argument("--league", action="append")
    e.add_argument("--edits", action="store_true")
    e.add_argument("--no-players", action="store_true",
                   help="leave the player changes out: crests, managers and stadiums only")
    e.add_argument("--without", action="append", default=[], choices=PARTS,
                   help="leave a part out (again for more): " + ", ".join(PARTS))
    e.add_argument("--sider", default=None,
                   help="the SiderAddons folder: kits and scoreboards the recipe has no folder for come from the game")
    s = sub.add_parser("show")
    s.add_argument("pack")
    a = sub.add_parser("add")
    a.add_argument("pack")
    a.add_argument("recipe")
    a.add_argument("--store", default=None)
    r = sub.add_parser("remove")
    r.add_argument("tag")
    r.add_argument("recipe")
    o = ap.parse_args()
    try:
        if o.cmd == "export":
            rec = json.load(open(o.recipe, encoding="utf-8"))
            export(rec, o.out, {"name": o.name, "author": o.author, "version": o.version,
                                "description": o.description}, o.league, o.edits, players=not o.no_players,
                     parts=[x for x in PARTS if x not in o.without], sider=o.sider)
        elif o.cmd == "show":
            print(json.dumps(manifest(o.pack), indent=1, ensure_ascii=False))
        elif o.cmd == "add":
            rec = json.load(open(o.recipe, encoding="utf-8"))
            store = o.store or os.path.join(os.path.dirname(os.path.abspath(o.recipe)), "packs")
            man, piece, folder = unpack(o.pack, store)
            tag = add(rec, man, piece, folder)
            json.dump(rec, open(o.recipe, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
            print("added %s: %s" % (tag, ", ".join(L["name"] for L in piece.get("leagues", []))))
        elif o.cmd == "remove":
            rec = json.load(open(o.recipe, encoding="utf-8"))
            print("removed:", ", ".join(sorted(remove(rec, o.tag))))
            json.dump(rec, open(o.recipe, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    except (Error, lbfaces.Error) as err:
        sys.exit("lbpackage: %s" % err)


if __name__ == "__main__":
    main()
