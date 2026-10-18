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
  - a club with a kit line of your own (switched on, or switched off by us) to a folder that is
    in the library gets no kit of ours, neither a package's nor a made one, and that line is on;
  - any other line of your own for a club or league that now gets one of ours is switched off (a
    # in front and OFF at its end), and back on when it no longer gets ours.

The scoreboard line is keyed by the league's regulation id, as the FL26 Modpack's are.
Without Kit Server or Scoreboard Server nothing is written for it.

Kit Server and Scoreboard Server come in two kinds each: kserv.lua reads content\kit-server and
ScoreboardServer.lua content\scoreboard-server, SPFL26's own ones (common\kits.lua and
common\scoreboards.lua, the ones a clean install loads) read content\kits and content\scoreboards,
the same files.  Ours go where the module sider.ini loads reads them (GitHub #129: the made kits
went to kit-server, which that game never read).
"""
import os, re, shutil

import lbstadiums

KITS = os.path.join("content", "kit-server")
SPFL_KITS = os.path.join("content", "kits")       # SPFL26's own Kit Server, common\kits.lua
BOARDS = os.path.join("content", "scoreboard-server")
SPFL_BOARDS = os.path.join("content", "scoreboards")   # and its common\scoreboards.lua
MENUS = os.path.join("content", "menu-server")       # Menu Server: no Build writes it, world zips bring lines
TAG = lbstadiums.TAG
OFF = lbstadiums.OFF
LINE = re.compile(r"^\s*(#\s*)?(\d+)\s*,\s*\"?([^\"#]*)")


def _live_modules(sider):
    """the modules the live lua.module lines of sider.ini load: names without folder and .lua"""
    mods = set()
    try:
        with open(os.path.join(sider, "sider.ini"), encoding="utf-8-sig", errors="replace") as f:
            for l in f:
                s = l.strip()
                if s.startswith("lua.module") and "=" in s:
                    n = os.path.basename(s.split("=", 1)[1].split(";")[0].strip().strip('"').replace("\\", "/")).lower()
                    mods.add(n[:-4] if n.endswith(".lua") else n)
    except OSError:
        pass
    return mods


def libs(sider):
    r"""(kits folder, scoreboards folder) the game reads: SPFL26's own when sider.ini loads its
    module and not ours, else content\kit-server and content\scoreboard-server"""
    mods = _live_modules(sider)
    return (SPFL_KITS if "kits" in mods and "kserv" not in mods else KITS,
            SPFL_BOARDS if "scoreboards" in mods and "scoreboardserver" not in mods else BOARDS)


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


def _stamps(words, away, crest, numbers, lib=None):
    """the kitmaker.txt stamps that count as "made from these": the first is the one written now,
    with the numbers kit by its folder inside the kit library. B104: the stamp had the numbers
    kit's whole path, so on every other PC (and on this one with the other slash) every made kit
    of a world was drawn again at its first Switch on -- 728 for the Modpack, many minutes with
    the window not answering. The others are the stamps written before, with this PC's path."""
    import hashlib, kitmaker
    rel = numbers or ""
    if numbers and lib:
        try:
            rel = os.path.relpath(numbers, lib).replace(os.sep, "/")
        except ValueError:                    # on another drive: the path as it is
            rel = numbers
    pic = open(crest, "rb").read()
    out = []
    for n in [rel] + ([numbers, numbers.replace("/", os.sep), numbers.replace(os.sep, "/")] if numbers else [""]):
        h = hashlib.md5()
        for x in (words, away or "", n or "", os.path.getsize(kitmaker.MASK)):
            h.update(str(x).encode("utf-8") + b"\0")
        h.update(pic)
        if h.hexdigest() not in out:
            out.append(h.hexdigest())
    return out


def _made(tid, words, away, crest, dst, numbers, log, lib=None, ready=False):
    """the kit folder dst made from words and crest, unless it was made from the same ones.
    ready: the world came ready from a zip (Install mods) with its made kits in it -- a kit
    folder with a stamp is kept as it came, whatever PC drew it (B104)"""
    import kitmaker, kitpics, tempfile
    stamps = _stamps(words, away, crest, numbers, lib)
    stamp = os.path.join(dst, "kitmaker.txt")
    try:
        had = open(stamp, encoding="utf-8").read().strip()
        if had in stamps or (ready and had):
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
        f.write(stamps[0] + "\n")
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


def carried(l, world):
    """a line Install mods put in from the world's own zip: a kit or a scoreboard of another pack
    the world carries under <world>\\_kits or <world>\\_packs (installer.export_world).  It ends
    in our tag like a line Build wrote, but Build did not write it and must not take it out:
    Switch on, run at the end of Install mods, wiped every modpack scoreboard that way (Vran,
    14.10.: "no scoreboards with the modpack")"""
    m = LINE.match(l[:-len(OFF)] if l.endswith(OFF) else l)
    if not m:
        return False
    f = m.group(3).strip().lower().replace("/", "\\")
    w = safe(world).lower() + "\\"
    return f.startswith((w + "_kits\\", w + "_packs\\"))


def carrier(l):
    """the world (lower case) whose zip put this line in (carried), or None: switching another
    world on took such a line out for good, and switching the modpack back on did not bring its
    86 scoreboards back (night test 15.10.) -- now it stays, switched off, until its world is on"""
    if TAG not in l:
        return None
    m = LINE.match(l[:-len(OFF)] if l.endswith(OFF) else l)
    if not m:
        return None
    parts = m.group(3).strip().lower().replace("/", "\\").split("\\")
    return parts[0] if len(parts) > 2 and parts[1] in ("_kits", "_packs") else None


def _key(l):
    """the team or competition id a map line is keyed by, or None"""
    m = LINE.match(l[:-len(OFF)] if l.endswith(OFF) else l)
    return int(m.group(2)) if m else None


def world_ids(pl, root=None):
    """(team ids, competition ids) of the world as built: the clubs of its leagues and its clubs in
    no league (the plan's teams), and every id its world file in root names for a competition --
    a league's own, its cid=, cup= and scup=, a ccup line's and its ko= -- the ids a line the world
    carries from another pack is keyed by (installer.borrowed_kits / world_competitions).  (None,
    None) when there is no built world (root and its world file) to read: then nothing is taken"""
    teams = {int(t) for p in (pl.get("leagues") or []) + (pl.get("others") or [])
             for t in p.get("teams") or [] if str(t).isdigit()}
    comps = None
    if root:
        try:
            with open(os.path.join(root, "fl26world.txt"), encoding="utf-8", errors="replace") as f:
                comps = set()
                for line in f:
                    w = line.split()
                    if w[:1] in (["league"], ["ccup"]) and len(w) > 1 and w[1].isdigit():
                        comps.add(int(w[1]))
                        for t in w[2:]:
                            k, _s, v = t.partition("=")
                            if k in ("cid", "cup", "scup", "ko") and v.isdigit():
                                comps.add(int(v))
        except OSError:
            comps = None
    return (None, None) if comps is None else (teams, comps)


def _map(path, mine, log, what, world="", sider=None, keep=None):
    """our lines (key, text) into a map file: earlier ones of ours out, clashing ones of yours
    off; a line a world zip carries from another pack (carrier) stays: on while its world is on,
    switched off (#) while another one is.  While its own world goes on, such a line stays only
    while its key is still one of the world's (keep: None = every one): a league or club taken
    out of the world takes its carried line with it, else it would give its scoreboard or kit to
    whatever league or club a later Build hands that free id (editing a ready world)"""
    lines, nl, bom, enc = lbstadiums.read(path)
    if not mine and not any(TAG in l or l.endswith(OFF) for l in lines):
        return 0
    rows = []
    for l in lines:
        w0 = carrier(l)
        if w0 is not None:                     # another pack's line a world zip brought: on with its world
            mine_w = bool(world) and w0 == safe(world).lower()
            if mine_w and keep is not None and _key(l) not in keep:
                continue                       # its league or club is no longer in the world
            l = re.sub(r"^(\s*)#\s*", r"\1", l[:-len(OFF)] if l.endswith(OFF) else l, count=1)
            rows.append(l if mine_w else "#" + l)
            continue
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
    # a restore point in SiderAddons\ModStudio\backups, no map.txt.before-builder / .prev next to
    # the map any more (mato 15.10.)
    lbstadiums.keep_before(path, "Switch on: %s map" % what, sider)
    data = (nl.join(out) + nl).encode(enc, "replace")
    with open(path + ".tmp", "wb") as f:
        f.write((b"\xef\xbb\xbf" if bom else b"") + data)
    os.replace(path + ".tmp", path)
    log("%s: %d -> %s%s" % (what, len(mine), path, ", %d line(s) of your own switched off for them" % off if off else ""))
    return len(mine)


def _yours(sider, klib, world=""):
    """team ids that have a kit line of your own in map.txt (one Build did not write), switched on
    or switched off by us, whose folder is in the library: a line to a kit that is not installed
    gives the club nothing, so ours goes in for it (22 clubs of the modpack world, 13.10.).  A
    kit the world carries from another pack (carried) counts as one of yours: no kit is made
    over it"""
    out = set()
    for l in lbstadiums.read(os.path.join(sider, klib, "map.txt"))[0]:
        if TAG in l and not (world and carried(l, world)):
            continue
        m = LINE.match(l[:-len(OFF)] if l.endswith(OFF) else l)
        if m and (not m.group(1) or l.endswith(OFF)) and m.group(3).strip() \
                and os.path.isdir(os.path.join(sider, klib, m.group(3).strip())):
            out.add(int(m.group(2)))
    return out


def made_rel(pl, world, league, k):
    """the kit library folder (world\\league\\club) of the kit made for place k of league"""
    cn = [p for p in (pl.get("leagues") or []) + (pl.get("others") or [])
          if (p.get("name") or "Other clubs") == league][0].get("club_names") or []
    return "%s\\%s\\%s" % (world, safe(league), safe(cn[k] if k < len(cn) and cn[k] else "club %d" % k))


def restamp(pl, sider, root, log=print):
    """a ready world from a zip made editable on this PC (installer.make_editable): its made kits
    were drawn on the PC that built it, and their kitmaker.txt holds that PC's stamp. Each made
    kit folder with a stamp gets the stamp of this PC for the colours and crest of the world as it
    came, so the Switch on after a Build keeps it (as it did while the world was ready, B104) and a
    club whose colours or crest are changed since gets its kit drawn again. Returns how many
    stamps were written."""
    klib, _blib = libs(sider)
    lib = os.path.join(sider, klib)
    if not os.path.isdir(lib):
        return 0
    world = safe(pl.get("world") or "FL26 world")
    numbers = numbers_kit(lib, world)
    n = 0
    for tid, league, k, words, away, crest in to_make(pl, root):
        stamp = os.path.join(lib, made_rel(pl, world, league, k), "kitmaker.txt")
        try:
            had = open(stamp, encoding="utf-8").read().strip()
        except OSError:
            continue
        mine = _stamps(words, away, crest, numbers, lib)[0]
        if had and had != mine:
            with open(stamp, "w", encoding="utf-8") as f:
                f.write(mine + "\n")
            n += 1
    log("kits made from colours and crests: %d stamped as made on this PC" % n)
    return n


def write(pl, sider, log=print, root=None):
    """the plan's kits and scoreboards into Kit Server and Scoreboard Server, and a kit made for
    every other new club with colours or a crest (root: the world's folder, for the crests);
    (kits, scoreboards) written"""
    kits, boards = wanted(pl)
    world = safe(pl.get("world") or "FL26 world")
    teams, comps = world_ids(pl, root)
    klib, blib = libs(sider)
    # B130: kserv.lua, when sider.ini loads it, stops at its start when content\kit-server has no
    # map_comp.txt, and the game then shows no kit of Kit Server at all (laracroft7826, 18.10.: his
    # kit-server folder held map.txt alone) -- an empty one is put there, as Kit Server's own
    # download has it
    comp = os.path.join(sider, KITS, "map_comp.txt")
    if "kserv" in _live_modules(sider) and os.path.isdir(os.path.dirname(comp)) and not os.path.exists(comp):
        try:
            open(comp, "w").close()
            log("kits: content\\kit-server had no map_comp.txt, which kserv.lua needs -- an empty one made")
        except OSError:
            pass
    make = to_make(pl, root) if root and os.path.isdir(os.path.join(sider, klib)) else []
    # B104: a world that came ready from a zip brought its made kits along, drawn on the PC it was
    # built on -- they are kept, not drawn again
    ready = bool(root) and os.path.exists(os.path.join(root, ".modstudio"))
    # a club with a kit line of your own keeps that kit: no kit made for it, and none of a league
    # package either (pepponeee98, 14.10.: his Serie C lines were switched off at every Build for
    # the package's kits, which went into a folder of the world again each time)
    yours = _yours(sider, klib, world) if (make or kits) else set()
    kept = sorted({x[0] for x in kits if x[0] in yours} | {x[0] for x in make if x[0] in yours})
    kits = [x for x in kits if x[0] not in yours]
    make = [x for x in make if x[0] not in yours]
    if kept:
        log("kits: %d club(s) keep a kit line of your own (%s)" % (len(kept), ", ".join(map(str, kept))))
    done = []
    for lib, file, items, what in ((klib, "map.txt", kits, "kits"),
                                   (blib, "map_competitions.txt", boards, "scoreboards")):
        root = os.path.join(sider, lib)
        if not os.path.isdir(root):
            if items:
                log("NOTE: %d %s come with the world, but %s is not installed -- not written" % (len(items), what, lib))
            done.append(0)
            continue
        mine = []
        for key, name, src in items:
            if what == "kits":
                league, _s, k = name.rpartition("/")
                club = [p for p in pl["leagues"] if p["name"] == league][0]
                cname = (club.get("club_names") or [])[int(k)] if int(k) < len(club.get("club_names") or []) else ""
                rel = "%s\\%s\\%s" % (world, safe(league), safe(cname or "club %s" % k))
                text = '%d, "%s"   %s %s' % (key, rel, TAG, name)
            else:
                rel = "%s\\%s" % (world, safe(name))
                text = "%d, %s   %s %s" % (key, rel, TAG, name)
            if os.path.isdir(src):
                _copy(src, os.path.join(root, rel))
            elif not os.path.isdir(os.path.join(root, rel)):
                log("  %s of %s: no folder %s, skipped" % (what, name, src))
                continue
            # else: the source is on the PC the world was built on, and the world's zip brought
            # the copy under <world>: the line stays (Install mods, whose Switch on dropped it)
            mine.append((key, text))
        if what == "kits" and make:
            numbers = numbers_kit(root, world)
            new = 0
            for tid, league, k, words, away, crest in make:
                rel = made_rel(pl, world, league, k)
                try:
                    drawn = _made(tid, words, away, crest, os.path.join(root, rel), numbers, log,
                                  lib=root, ready=ready)
                except Exception as e:               # one bad crest picture must not stop the Build
                    log("  kit of %s: not made (%s)" % (rel, e))
                    continue
                new += drawn
                if drawn and new % 50 == 0:          # B104: a long drawing says how far it is
                    log("kits drawn from colours and crests: %d so far (of at most %d)" % (new, len(make)))
                mine.append((tid, '%d, "%s"   %s %s/%d made' % (tid, rel, TAG, league, k)))
            log("kits made from colours and crests: %d (%d new or changed)%s" % (
                len(make), new, "" if numbers else "; no kit in the library lends back numbers, so the game's own are used"))
        done.append(_map(os.path.join(root, file), mine, log, what, world, sider,
                         teams if what == "kits" else comps))
    # B129: the other folder's map too (content\kits or content\kit-server, the one not picked
    # above): Install mods may have merged a world zip's lines there (servers.Server.pick decides
    # its folder its own way), and those lines of ours stayed on for the next world's clubs
    for lib, other, file, what in ((klib, (KITS, SPFL_KITS), "map.txt", "kits"),
                                   (blib, (BOARDS, SPFL_BOARDS), "map_competitions.txt", "scoreboards")):
        for o in other:
            path = os.path.join(sider, o, file)
            if o != lib and os.path.isfile(path):
                _map(path, [], log, what + " (" + o + ")", world, sider, teams if what == "kits" else comps)
    menus(sider, world, log)
    return tuple(done)


def menus(sider, world, log=print):
    r"""the menu themes world zips brought (content\menu-server\map_competitions.txt, lines
    "<world>\..." with our tag): on while their world is in the game, switched off (#) while
    another one is. Switch on handled kits and scoreboards only, so the Modpack's menus stayed on
    under every other world (B72, our test 16.10.: 88 eu1 and the r7 lines live under
    _FL26MyWorld). Lines of your own are not touched; returns the lines changed"""
    path = os.path.join(sider, MENUS, "map_competitions.txt")
    lines, nl, bom, enc = lbstadiums.read(path)
    live = os.path.join(sider, "livecpk")
    want = safe(world).lower() if world else ""
    out, changed = [], 0
    for l in lines:
        body = l[:-len(OFF)] if l.endswith(OFF) else l
        m = LINE.match(body) if TAG in l else None
        w0 = m.group(3).strip().replace("/", "\\").split("\\")[0] if m else ""
        if not w0 or not w0.lower().startswith("_fl26") or not os.path.isdir(os.path.join(live, w0)):
            out.append(l)
            continue
        body = re.sub(r"^(\s*)#\s*", r"\1", body, count=1)
        new = body if w0.lower() == want else "#" + body
        changed += new != l
        out.append(new)
    if changed:
        lbstadiums.keep_before(path, "Switch on: menus map", sider)
        data = (nl.join(out) + nl).encode(enc, "replace")
        with open(path + ".tmp", "wb") as f:
            f.write((b"\xef\xbb\xbf" if bom else b"") + data)
        os.replace(path + ".tmp", path)
        log("menus: %d line(s) of world zips switched %s" % (changed, "with %s" % world if world else "off"))
    return changed


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
    klib, blib = libs(sider)
    kmap = _read_map(os.path.join(sider, klib, "map.txt"))
    bmap = _read_map(os.path.join(sider, blib, "map_competitions.txt"))
    nk = nb = 0
    for L in recipe.get("leagues") or []:
        p = built.get(L["name"])
        if not p or (names is not None and L["name"] not in names):
            continue
        teams = p.get("teams") or []
        own = list(L.get("kit_folders") or [])
        # B148: a world from a zip has the folders of the PC that built it; one not on this PC
        # counts as none
        if teams and (not any(own) or not all(os.path.isdir(f) for f in own if f)):
            fs = []
            for k, tid in enumerate(teams):
                if k < len(own) and own[k] and os.path.isdir(own[k]):
                    fs.append(own[k])
                    continue
                rel = kmap.get(int(tid)) if tid is not None else None
                d = os.path.join(sider, klib, rel) if rel else ""
                fs.append(d if d and is_kit_folder(d) else "")
                nk += 1 if fs[-1] else 0
            L["kit_folders"] = fs
        if not (L.get("scoreboard") and os.path.isdir(L["scoreboard"])) and p.get("rid") is not None:
            rel = bmap.get(int(p["rid"]))
            d = os.path.join(sider, blib, rel) if rel else ""
            if d and os.path.isdir(d):
                L["scoreboard"] = d
                nb += 1
    return nk, nb
