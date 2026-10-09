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


def write(pl, sider, log=print):
    """the plan's kits and scoreboards into Kit Server and Scoreboard Server; (kits, scoreboards) written"""
    kits, boards = wanted(pl)
    world = safe(pl.get("world") or "FL26 world")
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
