r"""Kits (Kit Server) and scoreboards (Scoreboard Server) of the recipe's new leagues.

A league can carry its clubs' Kit Server folders and its own Scoreboard Server folder:

    league["kit_folders"] = ["...\\Club A", "", ...]   one per club: a folder with p1, p2, g1 ...
    league["scoreboard"]  = "...\\HNL"                  a scoreboard folder

They come with a league package (lbpackage, parts "kitfiles" and "scoreboards") or from the
world as it is in the game (collect()).  A new club's team id and a league's regulation id are
known only once the world is built, so the folders are copied and the map lines written when a
world is switched on, the way lbstadiums does the home stadiums:

    content\kit-server\<world>\<league>\<club>\...      map.txt:  <team id>, "<world>\<league>\<club>"
    content\scoreboard-server\<world>\<league>\...      map_competitions.txt:  <regulation id>, <world>\<league>

  - every line written before (it ends with "# FL26 Mod Studio: ...") goes, whatever world it
    was for, so only the live world has lines of ours;
  - a line of your own for a club or league that now gets one of ours is switched off (a # in
    front and OFF at its end), and back on when it no longer gets ours.

The scoreboard line is keyed by the league's regulation id, as the FL26 Modpack's are.
Without Kit Server or Scoreboard Server nothing is written for it.
"""
import os, re, shutil

import lbstadiums

KITS = os.path.join("content", "kit-server")
BOARDS = os.path.join("content", "scoreboard-server")
TAG = lbstadiums.TAG
OFF = lbstadiums.OFF
LINE = re.compile(r"^\s*(#\s*)?(\d+)\s*,\s*\"?([^\"#]*)")


def safe(name):
    """a folder name Sider can read back from a map line (no quote, comma, # or path signs)"""
    return re.sub(r'[\\/:*?"<>|,#]+', "_", str(name)).strip(" .") or "x"


def is_kit_folder(d):
    return os.path.isdir(d) and any(re.fullmatch(r"[pg]\d", n, re.I) and os.path.isdir(os.path.join(d, n))
                                    for n in os.listdir(d))


def wanted(pl):
    """([(team id, club key, folder)], [(regulation id, league name, folder)]) of the plan"""
    kits, boards = [], []
    for p in pl.get("leagues") or []:
        teams = p.get("teams") or []
        for k, f in enumerate(p.get("kit_folders") or []):
            if f and k < len(teams) and teams[k] is not None:
                kits.append((int(teams[k]), "%s/%d" % (p["name"], k), f))
        if p.get("scoreboard") and p.get("rid") is not None:
            boards.append((int(p["rid"]), p["name"], p["scoreboard"]))
    return kits, boards


def to_make(pl, root):
    """[(team id, league, place, home words, away words, crest picture)] of the new clubs that get a
    kit made (kitmaker): no Kit Server folder of their own, a shirt in words or a crest picture of
    their own.  A club of the game keeps its kits; "make_kits": false makes none."""
    import kitmaker
    if pl.get("make_kits") is False:
        return []
    out = []
    for p in (pl.get("leagues") or []) + (pl.get("others") or []):
        teams, folders = p.get("teams") or [], p.get("kit_folders") or []
        game = {int(k) for k in (p.get("game_clubs") or {})}
        home, away = p.get("club_kits") or [], p.get("club_away_kits") or []
        crests = p.get("club_crests") or []
        for k, tid in enumerate(teams):
            if tid is None or k in game or (k < len(folders) and folders[k]):
                continue
            crest = os.path.join(root, "common", "render", "symbol", "flag", "e_%06d_r_ll.png" % int(tid))
            words = kitmaker.words(home[k] if k < len(home) else "")
            own = k < len(crests) and crests[k]
            if not os.path.isfile(crest) or not (words or own):
                continue                      # a numbered placeholder badge: the lent kit stays
            if not words:
                words = kitmaker.crest_kit(crest)
                if not words:
                    continue
            out.append((int(tid), p.get("name") or "Other clubs", k, words,
                        kitmaker.words(away[k] if k < len(away) else ""), crest))
    return out


def numbers_kit(lib, ours):
    """a kit of the library to lend back numbers, leg numbers and a name font: the first, by name,
    whose p1 has all three, outside the folders we write"""
    for d, subs, files in sorted(os.walk(lib)):
        rel = os.path.relpath(d, lib)
        if rel.split(os.sep)[0] == ours:
            subs[:] = []
            continue
        if os.path.basename(d).lower() == "p1":
            names = [f.lower() for f in files]
            if all(any(n.endswith(s + ".ftex") for n in names) for s in ("_back", "_leg", "_name")):
                return os.path.dirname(d)
    return None


def _made(tid, words, away, crest, dst, numbers, log):
    """the kit folder dst made from words and crest, unless it was made from the same ones"""
    import hashlib, kitmaker, kitpics, tempfile
    h = hashlib.md5()
    for x in (words, away or "", numbers or "", os.path.getsize(kitmaker.MASK)):
        h.update(str(x).encode("utf-8") + b"\0")
    h.update(open(crest, "rb").read())
    stamp = os.path.join(dst, "kitmaker.txt")
    try:
        if open(stamp, encoding="utf-8").read().strip() == h.hexdigest():
            return False
    except OSError:
        pass
    tmp = tempfile.mkdtemp(prefix="fl26kit")
    try:
        pics = kitmaker.pictures(tmp, words, away, crest)
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        kitpics.make_kit(pics, tid, dst, numbers)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    with open(stamp, "w", encoding="utf-8") as f:
        f.write(h.hexdigest() + "\n")
    return True


def _copy(src, dst):
    """src's files into dst (dst made again only when they differ: a size or a time)"""
    same = os.path.isdir(dst)
    if same:
        for d, _s, files in os.walk(src):
            for f in files:
                a = os.path.join(d, f)
                b = os.path.join(dst, os.path.relpath(a, src))
                if not os.path.exists(b) or os.path.getsize(a) != os.path.getsize(b):
                    same = False
                    break
            if not same:
                break
    if not same:
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)


def _map(path, mine, log, what):
    """our lines (key, text) into a map file: earlier ones of ours out, clashing ones of yours off"""
    lines, nl, bom, enc = lbstadiums.read(path)
    if not mine and not any(TAG in l or l.endswith(OFF) for l in lines):
        return 0
    rows = []
    for l in lines:
        if TAG in l:
            continue
        if l.endswith(OFF):
            l = re.sub(r"^(\s*)#\s*", r"\1", l[:-len(OFF)], count=1)
        rows.append(l)
    taken = {key for key, _t in mine}
    out, off = [], 0
    for l in rows:
        m = LINE.match(l)
        if m and not m.group(1) and int(m.group(2)) in taken:
            l = "#" + l + OFF
            off += 1
        out.append(l)
    while out and not out[-1].strip():
        out.pop()
    out += [t for _k, t in mine]
    if os.path.exists(path):
        if not os.path.exists(path + ".before-builder"):
            shutil.copy2(path, path + ".before-builder")
        shutil.copy2(path, path + ".prev")
    data = (nl.join(out) + nl).encode(enc, "replace")
    with open(path + ".tmp", "wb") as f:
        f.write((b"\xef\xbb\xbf" if bom else b"") + data)
    os.replace(path + ".tmp", path)
    log("%s: %d -> %s%s" % (what, len(mine), path, ", %d line(s) of your own switched off for them" % off if off else ""))
    return len(mine)


def write(pl, sider, log=print, root=None):
    """the plan's kits and scoreboards into Kit Server and Scoreboard Server, and a kit made for
    every other new club with colours or a crest (root: the world's folder, for the crests);
    (kits, scoreboards) written"""
    kits, boards = wanted(pl)
    world = safe(pl.get("world") or "FL26 world")
    make = to_make(pl, root) if root and os.path.isdir(os.path.join(sider, KITS)) else []
    if make:                                 # a club with a kit line of your own keeps that kit
        lines = lbstadiums.read(os.path.join(sider, KITS, "map.txt"))[0]
        yours = set()
        for l in lines:
            if TAG in l:
                continue
            m = LINE.match(l[:-len(OFF)] if l.endswith(OFF) else l)
            if m and (not m.group(1) or l.endswith(OFF)):
                yours.add(int(m.group(2)))
        make = [x for x in make if x[0] not in yours]
    done = []
    for lib, file, items, what in ((KITS, "map.txt", kits, "kits"),
                                   (BOARDS, "map_competitions.txt", boards, "scoreboards")):
        root = os.path.join(sider, lib)
        if not os.path.isdir(root):
            if items:
                log("NOTE: %d %s come with the world, but %s is not installed -- not written" % (len(items), what, lib))
            done.append(0)
            continue
        mine = []
        for key, name, src in items:
            if not os.path.isdir(src):
                log("  %s of %s: no folder %s, skipped" % (what, name, src))
                continue
            if what == "kits":
                league, _s, k = name.rpartition("/")
                club = [p for p in pl["leagues"] if p["name"] == league][0]
                cname = (club.get("club_names") or [])[int(k)] if int(k) < len(club.get("club_names") or []) else ""
                rel = "%s\\%s\\%s" % (world, safe(league), safe(cname or "club %s" % k))
                text = '%d, "%s"   %s %s' % (key, rel, TAG, name)
            else:
                rel = "%s\\%s" % (world, safe(name))
                text = "%d, %s   %s %s" % (key, rel, TAG, name)
            _copy(src, os.path.join(root, rel))
            mine.append((key, text))
        if what == "kits" and make:
            numbers = numbers_kit(root, world)
            new = 0
            for tid, league, k, words, away, crest in make:
                cn = [p for p in (pl.get("leagues") or []) + (pl.get("others") or [])
                      if (p.get("name") or "Other clubs") == league][0].get("club_names") or []
                rel = "%s\\%s\\%s" % (world, safe(league), safe(cn[k] if k < len(cn) and cn[k] else "club %d" % k))
                try:
                    new += _made(tid, words, away, crest, os.path.join(root, rel), numbers, log)
                except Exception as e:               # one bad crest picture must not stop the Build
                    log("  kit of %s: not made (%s)" % (rel, e))
                    continue
                mine.append((tid, '%d, "%s"   %s %s/%d made' % (tid, rel, TAG, league, k)))
            log("kits made from colours and crests: %d (%d new or changed)%s" % (
                len(make), new, "" if numbers else "; no kit in the library lends back numbers, so the game's own are used"))
        done.append(_map(os.path.join(root, file), mine, log, what))
    return tuple(done)


def _read_map(path):
    """{key: folder} of the lines in effect in a map file"""
    lines, _nl, _b, _e = lbstadiums.read(path)
    out = {}
    for l in lines:
        m = LINE.match(l)
        if m and not m.group(1) and m.group(3).strip():
            out.setdefault(int(m.group(2)), m.group(3).strip())
    return out


def collect(recipe, pl, sider, names=None):
    """fill recipe leagues' kit_folders / scoreboard from the world in the game: the folders the
    Kit Server and Scoreboard Server maps give the built plan's team and regulation ids.  A
    league that has them already keeps its own.  Returns (kit folders, scoreboards) found."""
    built = {p["name"]: p for p in (pl or {}).get("leagues") or []}
    kmap = _read_map(os.path.join(sider, KITS, "map.txt"))
    bmap = _read_map(os.path.join(sider, BOARDS, "map_competitions.txt"))
    nk = nb = 0
    for L in recipe.get("leagues") or []:
        p = built.get(L["name"])
        if not p or (names is not None and L["name"] not in names):
            continue
        teams = p.get("teams") or []
        if not any(L.get("kit_folders") or []) and teams:
            fs = []
            for tid in teams:
                rel = kmap.get(int(tid)) if tid is not None else None
                d = os.path.join(sider, KITS, rel) if rel else ""
                fs.append(d if d and is_kit_folder(d) else "")
            if any(fs):
                L["kit_folders"] = fs
                nk += sum(1 for f in fs if f)
        if not L.get("scoreboard") and p.get("rid") is not None:
            rel = bmap.get(int(p["rid"]))
            d = os.path.join(sider, BOARDS, rel) if rel else ""
            if d and os.path.isdir(d):
                L["scoreboard"] = d
                nb += 1
    return nk, nb
