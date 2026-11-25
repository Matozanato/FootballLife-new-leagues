r"""installing and removing mods: a .zip / .7z / folder / .lua / .cpk is looked at, split into
parts, and each part goes where Sider wants it.

    livecpk root     a folder whose top holds the game's own folders (common, Asset, ...):
                     copied to SiderAddons\livecpk\<name> and listed as a cpk.root
    content          a folder named after a content server (stadium-server, ball-server ...)
                     or holding its map files: the library items are copied into
                     SiderAddons\content\<server>, and the map lines are MERGED into the maps
                     already there -- lines for a club / competition the maps already name
                     replace those lines (they are remembered, and come back on removal)
    module           a .lua file: copied to SiderAddons\modules and listed as a lua.module
    packed cpk       a .cpk: unpacked into a livecpk root (Sider reads loose files)
    league package   a .fl26pack: handed to the League Builder (see lbpackage.py)
    world            a built League Builder world (a livecpk root named _FL26... holding its
                     fl26world.txt, or a SiderAddons copy with that file in modules): the root
                     is copied under the world's own name and its world file goes to
                     modules\fl26world.txt, where the modules read it -- the "newfaces" /
                     "faceapp" lines in it are what gives the world's new players their faces
                     (fl26regen.lua).  The Install page then switches it on.  export_world()
                     makes such a zip.

Everything done is written to SiderAddons\ModStudio\installed.json, one record per mod:
files created, files replaced (with the restore point that holds the old one), sider.ini lines
added and map lines added or taken out.  Removing a mod undoes exactly that.
"""
import bigjson
import filecmp, json, os, re, shutil, sys, tempfile, time, zipfile, zlib

from . import servers as S
from .backups import home, long_path, snapshot
from .mapfile import MapFile
from .siderini import norm

GAME_DIRS = {"common", "asset", "download", "ui", "sound", "movie"}
SERVER_DIRS = {s.folder.lower(): s for s in S.SERVERS}
MAP_LINE = "map line.txt"
EXTRA_SERVERS = {"soundtrack-server", "turf-loader", "ui-colors", "fans-server", "ballboys_server",
                 "bibserver", "entrance", "stadium_tunnel", "stadium_banner", "stadium_board",
                 "stadium_cornerflag", "tournament_anth_tunnel", "whistle_ref", "custom-exhibition-match"}


WORLD_FILE = "fl26world.txt"             # the world file of a League Builder world
FACE_PACK = "fl26regen_faces.bin"        # Mod Studio's face pack; Install the modules puts it in modules
OUR_LINE = "# FL26 Mod Studio:"          # the end of a map line Build wrote (lbstadiums.TAG)
WORLD_SERVERS = ("kits", "scoreboards", "menus")   # content\<server>\<world>: Build writes kits and scoreboards
BORROWED = "_kits"                       # content\kit-server\<world>\_kits: other packs' kits a world zip carries
PACKS = "_packs"                         # content\<server>\<world>\_packs: other packs' scoreboards / menu themes
PACK_OF = {"scoreboards": "scoreboard", "menus": "menu"}   # ... of the world's competitions a world zip carries
WORLD_README = "READ ME - FL26 world.txt"
WORLD_INFO = "fl26worldpack.json"
NOTICE_MAX = 1500                     # Install shows this much of it (the window fits 1920x1080)
WORLD_NOTICE = "NOTICE.txt"           # the recipe's "notice": the author's words, shown by Install before it installs
WORLD_NOTE = "a ready world: it goes in the game, its world file goes to modules\\fl26world.txt"
# B400 (10.11., GigaPack beta 1): Windows without long paths switched on (LongPathsEnabled 0, the
# default) opens a file only while its whole path is under MAX_PATH: 259 characters and the NUL.
# A trophy file of the GigaPack was 217 characters inside the zip, 269 unpacked in a user's
# %TEMP%, and Install mods stopped on [Errno 2]. Mod Studio unpacks, copies and deletes through
# long_path (\\?\), which has no such limit; the game cannot (FL_2026.exe / FL_2027.exe declare no
# longPathAware, Sider adds no \\?\), so a file that goes in the game must stay within GAME_MAX.
MAX_PATH = 260
GAME_MAX = MAX_PATH - 1


def world_name(path):
    """the name on the "world" line of a world file, or None"""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                w = line.split()
                if w[:1] == ["world"] and len(w) > 1:
                    return w[1]
    except OSError:
        pass
    return None


def face_players(path):
    """how many players the world file's "newfaces" / "newfaces3d" / "faceapp" lines name"""
    n = 0
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                w = line.split()
                if w[:1] in (["newfaces"], ["newfaces3d"]):
                    for t in w[1:]:
                        a, _s, b = t.partition("-")
                        if a.isdigit():
                            n += (int(b) - int(a) + 1) if b.isdigit() else 1
                elif w[:1] == ["faceapp"]:
                    n += sum(1 for t in w[1:] if ":" in t)
    except OSError:
        pass
    return n


def world_lines(path, world):
    """the map lines Build wrote for `world` (switched on, ending in our tag, a folder under
    <world>\\), as bytes: the map's own encoding stays as it is"""
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError:
        return []
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    tag, under = OUR_LINE.encode(), (world + "\\").lower().encode()
    out = []
    for l in raw.split(b"\n"):
        l = l.rstrip(b"\r")
        body, _t, _r = l.partition(tag)
        if _t and not l.lstrip().startswith(b"#") and under in body.lower():
            out.append(l)
    return out


def world_competitions(path):
    """the tournament ids a world file names, what the competition maps of the Scoreboard and
    Menu Servers key a competition by: each league's id, its cup and super cup, the
    confederation cups and their knock-out stages.  Not the leagues' cid: the maps do not key
    by it, and a cid is another competition's tournament id (B73, 16.10.: r7's cids 133-169
    carried the SPFL, Jupiler, Liga Betplay ... menus, and id 165 twice)"""
    ids = set()
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                w = line.split()
                if w[:1] in (["league"], ["ccup"]) and len(w) > 1 and w[1].isdigit():
                    ids.add(int(w[1]))
                    for t in w[2:]:
                        k, _s, v = t.partition("=")
                        if k in ("cup", "scup", "ko") and v.isdigit():
                            ids.add(int(v))
    except OSError:
        pass
    return ids


def _line_id(line):
    """the competition id a map line (bytes or str) begins with, or None"""
    if isinstance(line, bytes):
        line = line.decode("utf-8", "replace")
    head = line.split(",", 1)[0].strip()
    return int(head) if head.isdigit() else None


def pack_lines(path, world, comps):
    """the switched-on lines of a competition map (Scoreboard Server, Menu Server) for the
    world's competitions `comps` that point outside <world>\\ -- what another pack (a modpack's
    boards and themes) gives them: [(competition id, folder, quoted, comment)], every line, in
    the map's order (a competition listed twice is picked at random)"""
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError:
        return []
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    out = []
    for l in raw.decode("utf-8", "replace").split("\n"):
        s = l.strip()
        if not s or s.startswith("#") or OUR_LINE in s:
            continue
        m = re.match(r'(\d+)\s*,\s*("?)([^#"]+?)\2\s*(#.*)?$', s)
        if not m or int(m.group(1)) not in comps:
            continue
        folder = m.group(3).strip().strip("\\/")
        if not folder or folder.lower().startswith((world + "\\").lower()):
            continue
        out.append((int(m.group(1)), folder, bool(m.group(2)), (m.group(4) or "").strip()))
    return out


def borrowed_kits(path, world, teams, have):
    """the world's clubs whose kit comes from a line of another pack (SPFL26's own folders, a
    modpack ...): [(team id, kit folder as in the map)], one per club, the line in effect: the
    last one (kserv keeps a club's last line, B203).  `have`: the team ids Build already gave a
    kit of ours."""
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError:
        return []
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    text = raw.decode("utf-8", "replace")
    want, out = set(teams) - set(have), {}
    for l in text.split("\n"):
        s = l.strip()
        if not s or s.startswith("#") or OUR_LINE in s:
            continue
        m = re.match(r'(\d+)\s*,\s*"([^"]+)"', s)
        if m and int(m.group(1)) in want \
                and not m.group(2).lower().startswith((world + "\\").lower()):
            out[int(m.group(1))] = m.group(2).strip()
    return sorted(out.items())


def world_teams(root):
    """the team ids of a built world's leagues and other clubs (leaguebuilder-plan.json)"""
    try:
        with open(os.path.join(root, "leaguebuilder-plan.json"), encoding="utf-8") as f:
            pl = bigjson.load(f)
    except (OSError, ValueError):
        return []
    return [int(t) for p in (pl.get("leagues") or []) + (pl.get("others") or [])
            for t in (p.get("teams") or []) if isinstance(t, int) or str(t).isdigit()]


def face_pack_missing(sider_dir):
    """True when Mod Studio's modules with the face pack are not in this Sider's modules folder"""
    mods = os.path.join(sider_dir, "modules")
    return not all(os.path.exists(os.path.join(mods, f)) for f in (FACE_PACK, "fl26regen.dll", "fl26regen.lua"))


README = """FL26 world: {world}

Install it with FL Mod Studio: Import your world > drop this zip > Install. Mod Studio copies
SiderAddons\\livecpk\\{world}, puts its world file (fl26world.txt) in SiderAddons\\modules
and switches the world on.

REQUIRED: FL Mod Studio's modules with the face pack (SiderAddons\\modules\\{pack}).
Install them once: Home > Install now (or Build and install).
{faces} new players of this world get a generated face from that pack: they are listed on
the newfaces / faceapp lines of fl26world.txt. Without the modules, or without
fl26world.txt in SiderAddons\\modules, every new player looks the same.

Kits ({kits} clubs), scoreboards ({boards} competitions) and menu themes ({menus} competitions),
when the world has them, are in SiderAddons\\content (Kit Server, Scoreboard Server, Menu
Server): Install adds their map lines. Scoreboards and themes of another pack that this
world's competitions use (a modpack's) are under <world>\\_packs. A world zip normally carries
no menu themes: the game's own menus stay. Themes show only with the Menu Server module on in
sider.ini (lua.module = "MenuServer.lua").

By hand: copy SiderAddons into the game folder, copy livecpk\\{world}\\fl26world.txt to
SiderAddons\\modules\\fl26world.txt, and put  cpk.root = ".\\livecpk\\{world}"  in
sider.ini above the other roots (with any other _FL26 world switched off). For the kits and
scoreboards and themes add the lines of the zip's map.txt / map_competitions.txt to your own.
"""


# B199 (JamesNotLike, 22.10.): a scoreboard pack can carry crests of its own, by team id
# (common/render/symbol/flag/e_000204_r_b.png ...). The World Modpack's Community Shield board
# had Leicester's crest for 204, the id whose place the world gives Bolton Wanderers, and in the
# matches with that board Bolton wore Leicester's crest. A crest the world draws itself (its own
# file for the id in livecpk/<world>/common/render/symbol) wins: the pack's is left out.
CREST_FILE = re.compile(r"(?:^|/)common/render/symbol/(?:flag|emblemLc)/(?:e_(\d{6})_|emb_(\d{4,6})_)[^/]*$", re.I)


def own_crests(root):
    """the team ids whose crest the world at root draws itself"""
    ids = set()
    for sub in ("flag", "emblemLc"):
        d = os.path.join(root, "common", "render", "symbol", sub)
        for f in os.listdir(d) if os.path.isdir(d) else []:
            m = CREST_FILE.search("common/render/symbol/%s/%s" % (sub, f))
            if m:
                ids.add(int(m.group(1) or m.group(2)))
    return ids


# B430 (12.11.2026): what Build writes down about a world names the pictures, kit folders and
# trophies it was built from by their full path on the maker's disk -- "C:/Users/<his name>/...",
# the names of his folders. Install, Switch on and Make editable on another PC never find those
# files and take the copies the world carries, so the zip does not need the paths: Export writes
# these files with every such path cut down to "source/d<n>/<its last part>" (the same folder gets
# the same n, so two files of one name from two folders stay two). The world on the maker's own
# disk keeps its files as they are.
LOCAL_PATH_FILES = ("leaguebuilder-plan.json", "leaguebuilder-input.json", "trophies/trophies.json")
_BS = chr(92)
# a JSON string that starts as a path of a disk ("D:/", "D:" and a backslash) or of a share (two backslashes)
_LOCAL_PATH = re.compile('"((?:[A-Za-z]:(?:/|' + _BS * 4 + ')|' + _BS * 8 + ')(?:[^"' + _BS * 2 + ']|' + _BS * 2 + '.)*)"')


def no_local_paths(text):
    """text of a JSON file without the paths of this PC -> (the text, how many were cut)"""
    folders, n = {}, [0]

    def one(m):
        try:
            p = json.loads(m.group(0))
        except ValueError:
            return m.group(0)
        folder, _sep, name = p.replace(_BS, "/").rstrip("/").rpartition("/")
        k = folders.setdefault(folder.lower(), "d%03d" % (len(folders) + 1))
        n[0] += 1
        return json.dumps("source/%s/%s" % (k, name) if folder else "source/%s" % k, ensure_ascii=False)
    return _LOCAL_PATH.sub(one, text), n[0]


def world_ledger(root, world, version=None, prev=None, log=lambda t: None, test=False):
    """(ledger, careers) of the built world in `root` for its zip (idledger.py, 17.11.2026): every
    id a career of this version holds, and what it says of the careers of `prev`, the version
    shared before (its ledger, None for the first): {"continue_from": prev's version when every id
    of it is kept (the next Install of it is an Update), else None, "after": prev's version,
    "breaks": {kind: how many ids of prev are gone}, "first": True for a first version}.
    Its number is one up from every number the lineage gave on this PC (idledger.next_number);
    test: a test zip's ledger ("test": true). (None, None) for a world without a plan.
    18.11.2026 evening (rowkeep.py): the ledger keeps the rows of the world's competition tables
    ("rows"), so the next version's Build lays them out the same; careers["rows"] says whether every
    row of prev is still where it was (rowkeep.summary: prev's rows, else the Build's own verdict,
    the plan's "rows_kept"; None when neither is known) -- when not, careers of prev do not go on"""
    import idledger, rowkeep
    plan, pids = idledger.world_ids(root)
    if not isinstance(plan, dict):
        return None, None
    settings = plan.get("settings") or {}
    version = str(version or "").strip() or idledger.default_version(settings, prev)
    rows = rowkeep.rows_of_world(root)
    led = idledger.make(plan, pids, world, version, number=idledger.next_number(world, prev), prev=prev,
                        retire=settings.get(idledger.RETIRE_KEY), test=test, rows=rows)
    kept = plan.get("rows_kept")
    del plan, pids
    if not prev:
        log("ids: %s is the first version of a new lineage (%s): over a world of before the id ledger, Install "
            "offers an Update only when it keeps every id of it" % (version, led["lineage"]))
        return led, {"continue_from": None, "first": True}
    old = idledger.of_ledger(prev)
    new = idledger.ids_of(led["plan"], led["players"])
    probs = idledger.compare(old, new, idledger.retire_of(led["retire"]))
    # a club, league or cup of prev retired: Install offers Replace, not Update (update_verdict)
    gone = {k: n for k in ("clubs", "leagues", "cups")
            for n in [sum(1 for x in led["retire"].get(k) or {} if idledger._present(old, k, x))] if n}
    rk = None
    if rowkeep.valid(prev.get(idledger.ROWS_KEY)) and rows is not None:
        t = rowkeep.tables_dir(rowkeep.world_db(root), rowkeep.TABLES + (rowkeep.TEAM,))
        # the clubs prev had: the game's (this world's Team.bin but its own new clubs) and prev's own
        known = (rowkeep.team_ids(t[rowkeep.TEAM]) - (set(new["clubs"]) - set(old["clubs"]))) | set(old["clubs"])
        rep = rowkeep.check(prev[idledger.ROWS_KEY], t[rowkeep.TABLES[0]], t[rowkeep.TABLES[1]], t[rowkeep.TABLES[2]],
                            known)
        for line in rowkeep.lines(rep, prev.get("version")):
            log("rows: " + line)
        rk = rowkeep.summary(rep)
    elif isinstance(kept, dict) and rowkeep.same_version(kept.get("of"), prev):
        rk = {k: v for k, v in kept.items() if k != "of"}     # the Build that followed prev said it
    else:
        log("rows: whether the competition rows of %s are where they were is not known (its ledger has none, "
            "and the world was not built after it here)" % prev.get("version"))
    moved = rk is not None and not rk.get("ok")
    careers = {"continue_from": None if probs or gone or moved else prev.get("version"), "after": prev.get("version"),
               "breaks": idledger.counts(probs), "retired": gone,
               "changed": [nm for _r, nm, _d in idledger.structure_changes(old, new)], "rows": rk}
    log("ids: careers of %s %s" % (prev.get("version"), "go on in %s" % version if not probs and not gone and not moved
                                   else "break in %s (%s)" % (version, idledger.summary(probs) if probs else
                                                              ", ".join("%d %s retired" % (n, k) for k, n in sorted(gone.items()))
                                                              if gone else "competition rows of it moved or changed")))
    return led, careers


FIND = object()                           # export_world: look for the version shared before (idledger.find)


def world_notice(recipe, root):
    """the recipe's "notice" (a text, or a list of lines): from `recipe`, else from the built world's
    plan (leaguebuilder.RECIPE_SETTINGS keeps it). "" when there is none"""
    note = recipe.get("notice") if isinstance(recipe, dict) else None
    if note is None:
        try:
            import idledger
            plan, _p = idledger.world_ids(root)
            note = (plan.get("settings") or {}).get("notice") if isinstance(plan, dict) else None
        except Exception:
            note = None
    if isinstance(note, list):
        note = "\n".join(str(x) for x in note)
    return note.strip() if isinstance(note, str) else ""


def read_notice(top):
    """a world zip's NOTICE.txt (export_world), as unpacked in `top`; "" when it has none"""
    p = os.path.join(top, WORLD_NOTICE)
    if not os.path.isfile(long_path(p)):
        return ""
    try:
        with open(long_path(p), "rb") as f:
            text = f.read(NOTICE_MAX + 1).decode("utf-8", "replace").replace("\r\n", "\n").strip()
        return text if len(text) <= NOTICE_MAX else text[:NOTICE_MAX].rstrip() + " ..."
    except OSError:
        return ""


def export_world(sider_dir, world, out, log=lambda t: None, menus=False, version=None, prev_ledger=FIND,
                 test=False, recipe=None, recipe_path=None, keep_broken=False):
    r"""zip the built world SiderAddons\livecpk\<world> for another PC, laid out as
    SiderAddons\livecpk\<world>\... so Install mods (or a copy by hand) puts it in place.

    The world folder holds fl26world.txt, the world file Switch on copies to modules: its
    "newfaces" / "faceapp" lines are the players who get a generated face.  The zip always
    carries it; when the folder's copy has no face lines but the live copy in modules (same
    world) has, the live one goes in.  A read-me and fl26worldpack.json say what the receiver
    needs: Mod Studio's modules with the face pack, or every new player looks the same.

    The world's kits and scoreboards go too: Build puts them in content\<server>\<world> (Kit
    Server, Scoreboard Server) with a map line each.  The zip has them as
    SiderAddons\content\<server>\<world>\... next to a map file of only those lines, which
    Install mods merges into the receiver's map (and takes out again on removal).  What the
    world uses of other packs goes along the same way: the kits its clubs wear (<world>\_kits)
    and the scoreboards and menu themes the switched-on map lines give its competitions, a
    modpack's boards and themes (<world>\_packs, see world_competitions / pack_lines).
    Menu themes go only with menus=True (B88, mato 16.10.2026: the Modpack's themes stayed as the
    background of every menu on the players' PCs and looked broken; the menus stay the game's own).
    17.11.2026 (mato: a newer version of a shared world must not break the careers of the one
    before): the zip carries the world's id ledger (SiderAddons\livecpk\<world>\fl26ids-ledger.json,
    idledger.py), and fl26worldpack.json its version (`version`, else the recipe's pack_version,
    else a number and the date) and whether careers of `prev_ledger`, the version shared before,
    go on in it (world_ledger). Install offers an Update over that version when they do.
    review 18.11.2026 -- the same for Mod Studio, release.py and coldstart.py:
    - prev_ledger FIND (the default): the version shared before is looked up here (idledger.find,
      by `recipe`, else the world's built plan: recipe_of_world); a ledger that cannot be read, or
      a recipe that names its lineage (id_lineage) when no ledger of it is on this PC, stops the
      export (idledger.LedgerError) -- a new lineage would turn every Install into a Replace
    - the ledger goes into this PC's history (idledger.store_save) together with the zip: written
      as out.part, its number noted (idledger.note_issued), the zip put in place, then the ledger
      kept (a failure on the way takes the .part, or the zip, away again). Not for a test zip (test: its ledger
      says "test", no Build or export follows it), and not when careers of the version before do
      not go on in it unless keep_broken (Mod Studio asks; info["stored"] says which)
    - the number is one up from every number the lineage gave on this PC (idledger.next_number:
      test zips and zips not kept count), and the world's plan gets the lineage (stamp_plan)
    Returns the info written to fl26worldpack.json, the ledger under "ledger_data" and where it
    was kept under "stored" (None when it was not)."""
    root = os.path.join(sider_dir, "livecpk", world)
    wf = os.path.join(root, WORLD_FILE)
    if not os.path.isfile(wf):
        raise ValueError("%s has no %s: build the world first" % (root, WORLD_FILE))
    import idledger
    if prev_ledger is FIND:
        notes = []
        like = recipe if recipe is not None else idledger.recipe_of_world(os.path.join(sider_dir, "livecpk"), world)
        _p, prev_ledger = idledger.find(dict(like, world=world), recipe_path, os.path.join(sider_dir, "livecpk"), notes)
        for t in notes:
            log(t)
        log("ids: the version shared before: %s" % (prev_ledger.get("version") if prev_ledger else "none"))
    live = os.path.join(sider_dir, "modules", WORLD_FILE)
    use = wf
    if face_players(wf) == 0 and world_name(live) == world and face_players(live) > 0:
        use = live
    faces = face_players(use)
    # mato 07.11.: the zip says which game the world is for (worldgame.py). A world built before
    # the game line gets it here: by its size (more than FL26 takes is FL 2027's), else the game it is in
    import worldgame as WG
    wtext = None
    game, teams, players, stamped = WG.world_game(root, use)
    if not stamped:
        game = game or WG.game_of(os.path.dirname(os.path.normpath(sider_dir)))
        if game:
            with open(use, "rb") as f:
                wtext = WG.stamped(f.read().decode("utf-8", "replace"),
                                   WG.stamp_line(game, teams, players)).encode("utf-8")
    info = {"format": "fl26world", "format_version": 1, "world": world, "face_players": faces,
            "world_file": "SiderAddons/livecpk/%s/%s" % (world, WORLD_FILE),
            "needs": ["FL Mod Studio modules with the face pack (%s): Home > Install now"
                      % FACE_PACK]}
    if game:
        info["game"] = game
        info["needs"].insert(0, "%s (%s clubs, %s players)" % (WG.TITLE[game], teams, players))
    led, careers = world_ledger(root, world, version, prev_ledger, log, test=test)
    if led is not None:
        info["pack_version"] = led["version"]
        info["ledger"] = {"file": "SiderAddons/livecpk/%s/%s" % (world, idledger.LEDGER),
                          "version": led["version"], "number": led["number"], "made": led["made"]}
        if test:
            info["ledger"]["test"] = True
        info["careers"] = careers
    comps = world_competitions(use)
    content = os.path.join(sider_dir, "content")
    extra = []                            # (server, its folder here, our map lines of this world, lent folders)
    info["menus"] = 0
    for key in WORLD_SERVERS:
        if key == "menus" and not menus:
            continue
        s = S.BY_KEY[key]
        here = os.path.join(content, s.folder_in(content))
        mp = os.path.join(here, s.maps[0].file)
        lines = world_lines(mp, world) if os.path.isdir(os.path.join(here, world)) else []
        if key != "kits":                 # B73: another pack's line an older zip of this world brought in (<world>\_packs)
            packs = ("%s\\%s\\" % (world, PACKS)).lower().encode()   # on an id the world has not: it stays out
            lines = [l for l in lines if packs not in l.lower() or _line_id(l) in comps]
        if key == "menus":                # B73: one menu per competition, the first line (Menu Server picks one of two at random)
            seen = set()
            lines = [l for l in lines if not (_line_id(l) in seen or seen.add(_line_id(l)))]
        lent = []                         # what the world uses of other packs, (folder here, folder in the zip): it goes too
        if key == "kits":                 # kits of other packs the world's clubs wear
            have = [int(l.split(b",", 1)[0]) for l in lines if l.split(b",", 1)[0].strip().isdigit()]
            for tid, folder in borrowed_kits(mp, world, world_teams(root), have):
                if os.path.isdir(os.path.join(here, folder)):
                    lent.append((os.path.join(here, folder), "%s\\%s\\%s" % (world, BORROWED, folder)))
                    lines.append(('%d, "%s\\%s\\%s"   %s kit of %s' % (
                        tid, world, BORROWED, folder, OUR_LINE, folder)).encode("utf-8"))
        else:                             # scoreboards / menu themes other packs give the world's competitions
            one = {_line_id(l) for l in lines} if key == "menus" else set()
            for cid, folder, quoted, note in pack_lines(mp, world, comps):
                if cid in one:                # B73: one menu per competition (Menu Server picks one of two at random)
                    continue
                if os.path.isdir(os.path.join(here, folder)):
                    if key == "menus":
                        one.add(cid)
                    dst = "%s\\%s\\%s" % (world, PACKS, folder)
                    lent.append((os.path.join(here, folder), dst))
                    lines.append(('%d, %s   %s%s %s of %s' % (
                        cid, '"%s"' % dst if quoted else dst, note + " " if note else "", OUR_LINE,
                        PACK_OF[key], folder)).encode("utf-8"))
        if lines:
            extra.append((s, here, lines, lent))
        info[key] = len(lines)
        if lent:
            info[key + "_borrowed"] = len(lent)
    text = README.format(world=world, pack=FACE_PACK, faces=faces, kits=info["kits"],
                         boards=info["scoreboards"], menus=info["menus"])
    if game:
        other = "FL26" if game == "fl27" else "FL 2027"
        text = text.replace("\n\n", "\n\nFOR %s ONLY. Do not put it into %s: Mod Studio refuses it there, and its modules "
                            "stop the game at the start when it is copied in by hand.\n\n" % (WG.TITLE[game], other), 1)
    text = text.replace("\n", "\r\n")
    notice = world_notice(recipe, root)
    if notice:
        info["notice"] = WORLD_NOTICE
    part = out + ".part"
    n = cut = 0
    own, crests = own_crests(root), 0
    with _part_gone_on_error(part), zipfile.ZipFile(part, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(WORLD_README, text)
        z.writestr(WORLD_INFO, json.dumps(info, indent=1, ensure_ascii=False))
        if notice:
            z.writestr(WORLD_NOTICE, notice.replace("\r\n", "\n").replace("\n", "\r\n") + "\r\n")
        if led is not None:
            # review 3, 18.11.2026: the zip's ledger names no folder of this PC either (its ids and names
            # stay; a path a world's files hold, in its players' file, goes as source/...)
            z.writestr(info["ledger"]["file"],
                       no_local_paths(json.dumps(led, ensure_ascii=False, separators=(",", ":")))[0])
        for s, here, lines, lent in extra:
            z.writestr("SiderAddons/content/%s/%s" % (s.folder, s.maps[0].file), b"\r\n".join(lines) + b"\r\n")
            done, written = set(), set()
            fresh = tuple(d.lower().replace("\\", "/") + "/" for _s, d in lent)
            for src, dst in [(os.path.join(here, world), world)] + lent:
                if dst.lower() in done or not os.path.isdir(src):
                    continue
                done.add(dst.lower())
                top = long_path(src)              # B400: os.walk passes over what it cannot open
                for dp, dn, fn in os.walk(top):
                    dn.sort()
                    for f in sorted(fn):
                        p = os.path.join(dp, f)
                        rel = os.path.relpath(p, top).replace(os.sep, "/")
                        if dst == world and (world + "/" + rel).lower().startswith(fresh):
                            continue              # an older copy of a borrowed kit / pack: the fresh one goes
                        # a kit or pack the world carries and nothing lends afresh (a world
                        # installed from a zip, exported again) goes as it is, with its lines
                        name = "SiderAddons/content/%s/%s/%s" % (s.folder, dst.replace("\\", "/"), rel)
                        if name.lower() in written:
                            continue              # a pack folder inside another one already written
                        m = CREST_FILE.search(rel) if dst != world else None
                        if m and int(m.group(1) or m.group(2)) in own:
                            crests += 1           # B199: the world draws this club's crest itself
                            continue
                        written.add(name.lower())
                        z.write(p, name)
                        n += 1
            log("%s: %d map line(s) from %s%s" % (s.title, len(lines), here,
                ", %d of them kits of other packs" % len(lent) if lent else ""))
        if crests:
            log("%d crest file(s) of other packs left out: the world draws those clubs' crests itself" % crests)
        top = long_path(root)
        for dp, dn, fn in os.walk(top):
            # B400: the trophies' GzsTool copies stay out, as Install leaves them out (world_prune)
            here_rel = os.path.relpath(dp, top)
            dn[:] = sorted(d for d in dn if not world_prune("" if here_rel == "." else here_rel, dp, d))
            for f in sorted(fn):
                p = os.path.join(dp, f)
                rel = os.path.relpath(p, top).replace(os.sep, "/")
                if rel in (".modstudio", ".modstudio-edited"):
                    continue
                if rel == idledger.LEDGER:
                    continue                      # the ledger of the zip it came from: this one's went above
                if rel == WORLD_FILE and wtext is not None:
                    z.writestr("SiderAddons/livecpk/%s/%s" % (world, rel), wtext)
                elif rel.lower() in LOCAL_PATH_FILES:
                    try:
                        with open(p, encoding="utf-8") as f:
                            clean, k = no_local_paths(f.read())
                    except (OSError, ValueError):
                        clean, k = None, 0       # not text: it goes as it is
                    if k:
                        z.writestr("SiderAddons/livecpk/%s/%s" % (world, rel), clean.encode("utf-8"))
                        cut += k
                    else:
                        z.write(p, "SiderAddons/livecpk/%s/%s" % (world, rel))
                    del clean
                else:
                    z.write(use if rel == WORLD_FILE else p, "SiderAddons/livecpk/%s/%s" % (world, rel))
                n += 1
                if n % 2000 == 0:
                    log("%d files ..." % n)
    stored = None
    # review 3, 18.11.2026: only the number is noted before the zip is in place (it is spent whatever
    # happens next); the ledger goes into the history, and the plan gets the lineage, only once the zip
    # is there -- a zip that could not be put in place left a version in the history nobody has
    with _part_gone_on_error(part):
        if led is not None:
            try:
                idledger.note_issued(led)     # its number is spent, kept or not
            except OSError as e:
                raise OSError("the export stopped: the number of %s could not be noted (%s)" % (led["version"], e))
        os.replace(part, out)
    if led is not None:
        c = careers or {}
        if test:
            log("ids: a test zip: its ledger is not kept, no Build or export follows it (number %d is spent)"
                % led["number"])
        elif c.get("first") or c.get("continue_from") or keep_broken:
            try:
                stored = idledger.store_save(led)
                log("ids: %s kept as the version shared last (%s)" % (led["version"], stored))
                # an export of this world that is not the recipe open now finds it by its lineage
                if idledger.stamp_plan(root, {idledger.LINEAGE_KEY: led["lineage"]}):
                    log("ids: the world's plan names its lineage %s now" % led["lineage"])
            except OSError as e:          # no zip whose ids this PC does not keep: it goes again
                for f in (out, stored):
                    try:
                        if f:
                            os.remove(f)
                    except OSError:
                        pass
                raise OSError("the export stopped: the id ledger of %s could not be kept (%s)" % (led["version"], e))
        else:
            log("ids: %s is not kept as the version shared last: careers of %s do not go on in it (number %d "
                "is spent)" % (led["version"], c.get("after"), led["number"]))
    if cut:
        log("%d path(s) of this PC left out of the world's plan: the zip names no folder of yours" % cut)
    log("wrote %s: %d files, %d players with generated faces, %d kits, %d scoreboards, %d menu themes"
        % (out, n, faces, info["kits"], info["scoreboards"], info["menus"]))
    return dict(info, ledger_data=led, stored=stored)



class _part_gone_on_error:
    """review 3, 18.11.2026: the zip's .part file (a GigaPack's is about 6 GB) is taken away when
    writing or putting it in place fails, whatever the error"""
    def __init__(self, part):
        self.part = part

    def __enter__(self):
        return self

    def __exit__(self, kind, _e, _tb):
        if kind is not None:
            try:
                os.remove(self.part)
            except OSError:
                pass
        return False


class Part:
    """one thing a mod brings"""

    def __init__(self, kind, src, name, server=None, note=""):
        self.kind, self.src, self.name, self.server, self.note = kind, src, name, server, note
        self.world_file = None            # a world: its fl26world.txt
        self.notice = ""                  # a world from a zip: its author's words (read_notice)
        self.made = None                  # a world from a zip: when the zip was made (world_made)
        self.map_line = None              # content: a loose "map line.txt" for its competition map
        self.install = True
        self.warnings = []
        self.size = 0
        self.files = 0

    def __repr__(self):
        return "<%s %s %s>" % (self.kind, self.name, self.src)


def safe(name):
    return re.sub(r'[<>:"/\\|?*]+', "_", name).strip(" .") or "mod"


ZIP_METHODS = {9: "Deflate64"}      # the methods a zip may name that Python's zipfile does not read


def zip_unreadable(members):
    """B386 (acoco75, 09.11.2026): the name of the compression method of a zip this program cannot
    take apart, or None. Windows packs a file past 2 GB with Deflate64, 7-Zip can be told to;
    Python's zipfile reads Stored, Deflate, BZip2, LZMA (and Zstandard from 3.14)"""
    ok = {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED, zipfile.ZIP_BZIP2, zipfile.ZIP_LZMA,
          getattr(zipfile, "ZIP_ZSTANDARD", zipfile.ZIP_STORED)}
    for m in members:
        if m.compress_type not in ok:
            return ZIP_METHODS.get(m.compress_type, "method %d" % m.compress_type)
    return None


def zip_unreadable_text(name):
    from .i18n import _
    return _("This zip is packed with %s, a method FL Mod Studio cannot read. Unpack it first (7-Zip, or right click > "
             "Extract All in Windows), then Choose a folder... on what came out.") % name


# B487 (16.11.): what a zip says of each file unpack() took out of it -- its size and zlib.crc32,
# which zipfile checked on the way out -- by the unpacked file's path, for the last few zips
# unpacked. An install stamps every file it copies with them (Installer.copy_file): what it put
# there is known later without reading a byte more (a crc32 summed while copying, in Python, made
# the copy of 5000 files 1.3 to 2.8 times as long as CopyFile2's; shutil.copy2 does it, as before)
_UNPACKED = {}


def _sum_key(p):
    return os.path.normcase(long_path(p))


def zip_sum(path):
    """(size, crc32) the zip gave for the file unpack() put at `path`; None when it was not unpacked
    from a zip here (a folder, a .7z)"""
    k = _sum_key(path)
    for sums in reversed(list(_UNPACKED.values())):
        if k in sums:
            return sums[k]
    return None


def stamp_of(src, dst):
    """what an install put at `dst` (copied from `src`): "size mtime_ns crc32", the crc32 the zip
    gave for src ("-" when there is none: a folder, a .7z); "" when dst cannot be looked at"""
    try:
        st = os.stat(dst)
    except OSError:
        return ""
    z = zip_sum(src)
    return "%d %d %s" % (st.st_size, st.st_mtime_ns, "%08x" % z[1] if z and z[0] == st.st_size else "-")


def _stamp(text):
    """(size, mtime_ns, crc32 or None) of a stamp_of; None for none (a record of before 16.11.)"""
    try:
        size, mt, crc = str(text).split()
        return int(size), int(mt), None if crc == "-" else int(crc, 16)
    except (TypeError, ValueError):
        return None


# ModStudio\stamps\<file>: a record's stamps, one per file of its "created", in that order. Not
# in installed.json: the GigaPack's record has 167 000 files, and that file is read again and
# again (Home, Import your world); the stamps only when a newer version replaces the world
STAMPS = "stamps"


def stamps_path(sider_dir, rec):
    n = rec.get("stamps")
    if not isinstance(n, str) or not n or os.path.basename(n) != n:
        return None
    return os.path.join(home(sider_dir), STAMPS, n)


def stamps_of(sider_dir, rec):
    """{file of rec's "created": (size, mtime_ns, crc32 or None)} as the install stamped them; {}
    for a record without (an install before 16.11.) or whose list no longer fits its files"""
    p = stamps_path(sider_dir, rec)
    if not p:
        return {}
    try:
        with open(p, encoding="utf-8") as f:
            got = json.load(f)
    except (OSError, ValueError):
        return {}
    created = rec.get("created") or []
    if not isinstance(got, list) or len(got) != len(created):
        return {}
    return {rel: _stamp(s) for rel, s in zip(created, got) if s}


def unpack(src, work, progress=None):
    """a folder to look at: the folder itself, or `src` unpacked into `work`; progress(done, total,
    bytes) now and then while a zip comes out (B84: a 4 GB Modpack took minutes with no word)"""
    low = src.lower()
    if os.path.isdir(src):
        return src
    if low.endswith(".zip"):
        with zipfile.ZipFile(src) as z:
            members = z.infolist()
            bad = zip_unreadable(members)
            if bad:                           # B386: said before the first file, not after minutes of unpacking
                raise ValueError(zip_unreadable_text(bad))
            for m in members:
                target = os.path.normpath(os.path.join(work, m.filename))
                if not target.startswith(os.path.normpath(work)):
                    raise ValueError("unsafe path in the zip: %s" % m.filename)
            done = size = 0
            last = 0.0
            into = long_path(work)            # B400: %TEMP%\fl26ms_x\ + 217 was past MAX_PATH
            sums = {}
            for m in members:
                try:
                    z.extract(m, into)
                except NotImplementedError:   # a method zip_unreadable does not know of
                    raise ValueError(zip_unreadable_text("method %d" % m.compress_type))
                if not m.is_dir():
                    sums[_sum_key(os.path.join(work, m.filename))] = (m.file_size, m.CRC)
                done += 1
                size += m.file_size
                if progress and (time.monotonic() - last > 0.3 or done == len(members)):
                    last = time.monotonic()
                    progress(done, len(members), size)
            _UNPACKED[_sum_key(work)] = sums
            while len(_UNPACKED) > 3:         # (a zip looked at long ago is not installed now)
                _UNPACKED.pop(next(iter(_UNPACKED)))
        return work
    if low.endswith(".7z"):
        try:
            import py7zr
        except ImportError:
            raise ValueError("7z archives need py7zr; unpack it yourself and install the folder")
        with py7zr.SevenZipFile(src, "r") as z:
            z.extractall(long_path(work))
        return work
    if low.endswith(".rar"):
        raise ValueError("unpack the .rar yourself (7-Zip, WinRAR) and install the folder it gives")
    if low.endswith((".lua", ".cpk", ".fl26pack", ".dll")):
        shutil.copy2(src, os.path.join(work, os.path.basename(src)))
        return work
    raise ValueError("not a mod this program knows: %s" % os.path.basename(src))


GB = 1 << 30
ROOM = GB // 2          # bytes left free on a disk after an unpack


def unpacked_size(src):
    """bytes `src` takes unpacked: a zip's or 7z's files, a single file's own size; 0 for a folder
    or what cannot be read (unpack says why)"""
    low = src.lower()
    try:
        if os.path.isdir(src):
            return 0
        if low.endswith(".zip"):
            with zipfile.ZipFile(src) as z:
                return sum(m.file_size for m in z.infolist())
        if low.endswith(".7z"):
            import py7zr
            with py7zr.SevenZipFile(src, "r") as z:
                return sum(f.uncompressed or 0 for f in z.list())
        return os.path.getsize(src)
    except Exception:
        return 0


def free(d):
    try:
        return shutil.disk_usage(d).free
    except OSError:
        return 0


def work_dir(src, near):
    """B41 (vmican, 15.10.): where to unpack `src`. %TEMP% as always while its disk has room; the
    Modpack is 7 GB unpacked and on a full C: the unpack stopped half-way, the game on D: did not
    help. Then a folder beside the game instead (`near`, the Sider folder: the disk Install copies to
    anyway). Neither with room: ValueError naming what it needs."""
    need = unpacked_size(src)
    tmp = tempfile.gettempdir()
    if not need or free(tmp) >= need + ROOM:
        return tempfile.mkdtemp(prefix="fl26ms_")
    if near and os.path.isdir(near) and free(near) >= need + ROOM:
        here = os.path.join(near, "_fl26ms_unpack")
        os.makedirs(here, exist_ok=True)
        return tempfile.mkdtemp(prefix="fl26ms_", dir=here)
    raise ValueError("not enough free space: %.1f GB unpacked, %.1f GB free on %s, %.1f GB beside the game"
                     % (need / GB, free(tmp) / GB, os.path.splitdrive(tmp)[0] or tmp,
                        free(near) / GB if near else 0))


def lower_names(d):
    try:
        return {n.lower(): n for n in os.listdir(d)}
    except OSError:
        return {}


def is_root(d):
    return bool(set(lower_names(d)) & {"common", "asset"})


def measure(p):
    n = size = 0
    for dp, _dn, fn in os.walk(long_path(p)):   # os.walk passes over a folder it cannot open (B400)
        for f in fn:
            n += 1
            try:
                size += os.path.getsize(os.path.join(dp, f))
            except OSError:
                pass
    return n, size


def world_prune(rel_dir, folder, name):
    """B400: True for a folder of a ready world that is not copied into the game: the copy of a
    trophy's .fpk that GzsTool unpacked beside it (lbtrophies.gzs_leftover), in the world's
    trophies folder. <rel_dir>: the folder holding it, relative to the world; <folder>: its path"""
    import lbtrophies
    top = rel_dir.replace("/", os.sep).split(os.sep)[0].lower()
    return top == lbtrophies.FOLDER and lbtrophies.gzs_leftover(folder, name)


def files_of(src, prune=None):
    """(path, path relative to src) of every file under folder src, through long_path; a folder
    prune(rel dir, its path, name) is True for is left out with all it holds"""
    top = long_path(src)
    for dp, dn, fn in os.walk(top):
        rel_dir = os.path.relpath(dp, top)
        rel_dir = "" if rel_dir == "." else rel_dir
        if prune:
            dn[:] = [d for d in dn if not prune(rel_dir, dp, d)]
        for f in fn:
            yield os.path.join(dp, f), os.path.join(rel_dir, f)


def install_paths(game, p):
    """the paths in the game the files of part p would have (Installer: do_world, do_root,
    do_content, do_module); [] for what is known only once unpacked (a .cpk)"""
    if p.kind == "world":
        out = [os.path.join(game.livecpk_dir, p.name, r) for _s, r in files_of(p.src, world_prune)]
        return out + [os.path.join(game.livecpk_dir, p.name, WORLD_FILE), os.path.join(game.modules_dir, WORLD_FILE)]
    if p.kind == "root":
        return [os.path.join(game.livecpk_dir, p.name, r) for _s, r in files_of(p.src)]
    if p.kind == "content":
        s = S.BY_KEY.get(p.server) if p.server else None
        dst = os.path.join(game.content_dir, s.folder_in(game.content_dir) if s else p.name)
        return [os.path.join(dst, r) for _s, r in files_of(p.src)]
    if p.kind == "module":
        return [os.path.join(game.modules_dir, os.path.basename(p.src))]
    return []


def too_long(game, p, limit=GAME_MAX):
    """B400: (how many, the longest's length, the longest) of the files part p puts in the game
    whose path would be longer than the game can open; None when every one fits"""
    over = [q for q in install_paths(game, p) if len(q) > limit]
    if not over:
        return None
    worst = max(over, key=len)
    return len(over), len(worst), worst


def too_long_text(game, n, length):
    """B400: the warning, translated, for a part with n files too long in the game at `game`"""
    from .i18n import _
    folder = getattr(game, "folder", None) or os.path.dirname(os.path.normpath(game.sider_dir))
    room = max(0, len(os.path.abspath(folder)) - (length - GAME_MAX))
    return _("The game folder's path is too long for %d file(s) of this mod: in the game they would be up to "
             "%d characters long, and the game can open a file only up to %d (a Windows limit). Those files "
             "would be missing in the game. Move the game to a folder with a path of at most %d characters "
             "(for example C:\\Games\\FL), choose it again (Game ▾), and install this again.") % (
        n, length, GAME_MAX, room)


def server_by_maps(d):
    """a content server whose map files are in folder d"""
    names = set(lower_names(d))
    best = None
    for s in S.SERVERS:
        files = {m.file.lower() for m in s.maps}
        if files and files <= names | files and names & files:
            hit = len(names & files)
            # map.txt alone: kit-server (quoted paths) or badge-server; told apart by the lines
            if best is None or hit > best[0]:
                best = (hit, s)
    if best and best[1].key in ("kits", "badges"):
        p = os.path.join(d, "map.txt")
        try:
            text = open(p, encoding="utf-8", errors="replace").read().lower()
            if "badge" in text and "kit" not in text:
                return S.BY_KEY["badges"]
        except OSError:
            pass
    return best[1] if best else None


def detect(top, label="mod"):
    """the parts of the mod unpacked at `top`"""
    parts = []
    loose = []                            # world files found in a modules folder

    def visit(d, depth):
        low = lower_names(d)
        base = os.path.basename(d).lower()
        # a whole SiderAddons-like folder
        if depth <= 2 and ("livecpk" in low or "content" in low or "modules" in low) and not is_root(d):
            for k in ("livecpk", "content", "modules"):
                if k in low:
                    sub = os.path.join(d, low[k])
                    if k == "livecpk":
                        for n in sorted(os.listdir(sub)):
                            if os.path.isdir(os.path.join(sub, n)):
                                visit_root(os.path.join(sub, n), n)
                    elif k == "content":
                        for n in sorted(os.listdir(sub)):
                            if os.path.isdir(os.path.join(sub, n)):
                                visit_content(os.path.join(sub, n))
                    else:
                        for n in sorted(os.listdir(sub)):
                            if n.lower() == WORLD_FILE:
                                loose.append(os.path.join(sub, n))
                            elif n.lower().endswith(".lua"):
                                parts.append(Part("module", os.path.join(sub, n), n))
                            elif n.lower().endswith(".dll"):
                                parts.append(Part("dll", os.path.join(sub, n), n))
            for n, real in sorted(low.items()):
                p = os.path.join(d, real)
                if n.endswith(".lua") and os.path.isfile(p):
                    parts.append(Part("module", p, real))
                elif os.path.isdir(p) and n not in ("livecpk", "content", "modules"):
                    visit(p, depth + 1)
            return
        if base in SERVER_DIRS or base in EXTRA_SERVERS:
            visit_content(d)
            return
        if is_root(d):
            visit_root(d, os.path.basename(d) if d != top else label)
            return
        s = server_by_maps(d)
        if s is not None:
            visit_content(d, s)
            return
        for n, real in sorted(low.items()):
            p = os.path.join(d, real)
            if os.path.isdir(p):
                if depth < 4:
                    visit(p, depth + 1)
            elif n.endswith(".lua"):
                parts.append(Part("module", p, real))
            elif n.endswith(".cpk"):
                parts.append(Part("cpk", p, real[:-4]))
            elif n.endswith(".fl26pack"):
                parts.append(Part("pack", p, real[:-9]))
            elif n.endswith(".dll"):
                parts.append(Part("dll", p, real))

    def visit_root(d, name):
        wf = lower_names(d).get(WORLD_FILE)
        w = world_name(os.path.join(d, wf)) if wf else None
        if w and w.startswith("_FL26") and safe(w) == w:
            p = Part("world", d, w, note=WORLD_NOTE)
            p.world_file = os.path.join(d, wf)
            parts.append(p)
            return
        # B317 (Jh, 04.11.): a folder with no file in it is nothing to put in place -- the copy
        # made no "root (2)" for it and the mark written there stopped the install
        if not any(fn for _dp, _dn, fn in os.walk(d)):
            return
        p = Part("root", d, safe(name))
        if os.path.isdir(os.path.join(d, "common", "etc", "pesdb")) or \
                os.path.isdir(os.path.join(d, "common", "etc")) and \
                any(n.lower().endswith(".bin") for n in os.listdir(os.path.join(d, "common", "etc"))):
            p.warnings.append("it replaces the game's database (common\\etc\\pesdb): leagues, clubs "
                              "and players. It will fight with a League Builder world; keep it below it.")
            p.replaces_db = True
        parts.append(p)

    def visit_content(d, s=None):
        base = os.path.basename(d).lower()
        s = s or SERVER_DIRS.get(base)
        folder = s.folder if s else os.path.basename(d)
        p = Part("content", d, folder, server=s.key if s else None,
                 note="" if s else "copied as it is (no map files to merge)")
        # a loose "map line.txt" beside the server folder (the scoreboard zips posted on Discord)
        for where in (d, os.path.dirname(d)):
            real = lower_names(where).get(MAP_LINE)
            if s and real and not any(m.file.lower() in lower_names(d) for m in s.maps):
                p.map_line = os.path.join(where, real)
                break
        parts.append(p)

    if os.path.isfile(top):
        visit(os.path.dirname(top), 0)
    else:
        visit(top, 0)
    # a SiderAddons copy whose world folder has no world file of its own: the one in modules
    for wf in loose:
        w = world_name(wf)
        for p in parts:
            if p.kind == "root" and w and w.startswith("_FL26") and safe(w) == w \
                    and os.path.basename(p.src).lower() == w.lower():
                p.kind, p.name, p.world_file, p.note = "world", w, wf, WORLD_NOTE
    for p in parts:
        if os.path.isdir(p.src):
            p.files, p.size = measure(p.src)
        elif os.path.exists(p.src):
            p.files, p.size = 1, os.path.getsize(p.src)
        if p.kind == "dll":
            p.install = False
            p.warnings.append("a .dll runs with the game's rights: it is not installed automatically. "
                              "Copy it yourself only if you trust where it comes from.")
    return parts


# ---------------------------------------------------------------------------------------------
def db_path(sider_dir):
    return os.path.join(home(sider_dir), "installed.json")


def records(sider_dir):
    try:
        with open(db_path(sider_dir), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def records_seen(sider_dir):
    """records() for looking only: the same list while the file stays the same (a big world's
    record is megabytes, and Home read it three times a visit). Never change what it gives"""
    from . import filecache
    try:
        return filecache.json_file(db_path(sider_dir))
    except (OSError, ValueError):
        return []


def _save(sider_dir, rows):
    p = db_path(sider_dir)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=1, ensure_ascii=False)
    os.replace(p + ".tmp", p)


class Installer:
    """install the chosen parts of one mod; `rec` is what removal needs"""

    def __init__(self, game, ini, name, log=lambda t: None, replace_lines=True, comps=None, progress=None):
        """comps: {tournament id: name} of the world in the game. With it a competition line of a
        scoreboard / menu pack goes to the competition its comment names: a pack made for another
        world keys the same league by another id (quicksite, League Two on 182 = Guatemala here).
        progress(files done, files in all, bytes done): now and then while the files go in (B84)"""
        self.game, self.ini, self.name, self.log = game, ini, name, log
        self.progress = progress
        self.n_files = self.n_bytes = self.total = 0
        self._told = 0.0
        self.replace_lines = replace_lines
        self.comps = comps
        self.rec = {"name": name, "time": time.strftime("%Y%m%d-%H%M%S"), "created": [], "replaced": [],
                    "ini": [], "map_added": {}, "map_removed": {}, "parts": []}
        # B487: one per file of rec["created"], in its order: stamp_of, "" for a file not copied
        # (a mark); written beside installed.json at the end (STAMPS), for keep_yours
        self.stamps = []
        self.sd = game.sider_dir
        self.merges = []                  # (map, its file in the mod, the game's map file): after the copies

    def rel(self, p):
        return os.path.relpath(p, self.sd)

    def created(self, p, stamp=""):
        self.rec["created"].append(self.rel(p))
        self.stamps.append(stamp)

    def save_stamps(self):
        """the stamps into ModStudio\\stamps\\<time>-<name>.json, its name into the record; without
        them (the disk full) the record is one of before, and keep_yours goes by the files' times"""
        if not any(self.stamps):
            return
        d = os.path.join(home(self.sd), STAMPS)
        base = "%s-%s" % (self.rec["time"], safe(self.name)[:60])
        p, n = os.path.join(d, base + ".json"), 2
        try:
            os.makedirs(d, exist_ok=True)
            while os.path.exists(p):
                p, n = os.path.join(d, "%s-%d.json" % (base, n)), n + 1
            with open(p + ".tmp", "w", encoding="utf-8") as f:
                json.dump(self.stamps, f, separators=(",", ":"))
            os.replace(p + ".tmp", p)
            self.rec["stamps"] = os.path.basename(p)
        except OSError as e:
            self.log("the files' stamps could not be written: %s" % e)

    def _count(self, parts):
        """the files the chosen parts bring, for the counter"""
        n = 0
        for p in parts:
            if not p.install:
                continue
            if os.path.isdir(p.src):
                # a world's files as do_world copies them (B400 leaves GzsTool's folders out: counted
                # in, the bar of a world zip built before it never reached its end)
                n += sum(1 for _f in files_of(p.src, world_prune if p.kind == "world" else None))
            else:
                n += 1
        return n

    def _tick(self, final=False):
        if self.progress and (final or time.monotonic() - self._told > 0.3):
            self._told = time.monotonic()
            self.progress(self.n_files, self.total, self.n_bytes)

    def copy_file(self, src, dst):
        # dst stays as it is for the record (paths relative to SiderAddons); the files themselves
        # are read and written through long_path (B400)
        s, d = long_path(src), long_path(dst)
        self.n_files += 1
        try:
            self.n_bytes += os.path.getsize(s)
        except OSError:
            pass
        self._tick()
        if os.path.exists(d):
            # the same file already there: compared in pieces (whole 1 GB files in memory, twice,
            # stalled the PC -- B84)
            if os.path.getsize(d) == os.path.getsize(s) and filecmp.cmp(s, d, shallow=False):
                return
            b = snapshot(dst, "replaced by %s" % self.name, self.sd)
            self.rec["replaced"].append([self.rel(dst), self.rel(b)])
            new = False
        else:
            self.created(dst)
            new = True
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy2(s, d)
        if new:
            self.stamps[-1] = stamp_of(s, d)

    def copy_tree(self, src, dst, skip=(), prune=None):
        """every file under src to the same place under dst; prune: files_of's"""
        for s, r in files_of(src, prune):
            if r.lower() in skip:
                continue
            self.copy_file(s, os.path.join(dst, r))

    def run(self, parts, root_where="top"):
        self.total = self._count(parts)
        self._tick(final=True)
        for p in parts:
            if not p.install:
                continue
            self.log("%s: %s" % (p.kind, p.name))
            getattr(self, "do_" + p.kind)(p, root_where)
            self.rec["parts"].append([p.kind, p.name])
        self._tick(final=True)
        # B29 (ELBastos): a big zip takes minutes to copy, and an install stopped half way (Mod
        # Studio closed while it "hung") left the map lines of the parts done so far pointing at
        # folders of parts never copied. The lines go in only once every file is there.
        for m, src, dst in self.merges:
            self.merge_map(m, src, dst)
        self.merges = []
        # when the last file went in (keep_yours told the person's changes by it until B487; the
        # stamps tell them now)
        self.rec["done"] = time.strftime("%Y%m%d-%H%M%S")
        self.save_stamps()
        rows = records(self.sd)
        rows.append(self.rec)
        _save(self.sd, rows)
        return self.rec

    def do_root(self, p, where):
        bad = wrong_game(getattr(self.game, "folder", None), p.src, world=p.name)    # a world's tables without its world file
        if bad:
            raise WrongGame(bad)
        dst = os.path.join(self.game.livecpk_dir, p.name)
        n = 2
        while os.path.exists(dst) and not os.path.exists(os.path.join(dst, ".modstudio")):
            dst = os.path.join(self.game.livecpk_dir, "%s (%d)" % (p.name, n))
            n += 1
        self.copy_tree(p.src, dst)
        mark = os.path.join(dst, ".modstudio")
        if not os.path.exists(mark):
            with open(mark, "w", encoding="utf-8") as f:
                f.write(self.name)
            self.created(mark)
        value = ".\\livecpk\\" + os.path.basename(dst)
        if not any(norm(e.value) == norm(value) for e in self.ini.entries("cpk.root")):
            # the first root listed wins; a mod that replaces the database goes last
            # (review 11.11.: any warning sent it last, so a root with a long path, installed after
            # "Install anyway?", lost to every other root without a word)
            self.ini.add("cpk.root", value,
                         where="first" if where == "top" and not getattr(p, "replaces_db", False) else None)
            self.rec["ini"].append(["cpk.root", value])

    def do_world(self, p, where):
        """a League Builder world: the folder under its own name (Switch on and the modules look
        for livecpk\\<world>), and its world file into modules, where the modules read it"""
        dst = os.path.join(self.game.livecpk_dir, p.name)
        if os.path.exists(dst) and not os.path.exists(os.path.join(dst, ".modstudio")):
            raise WorldThere(world_there(p.name))
        bad = wrong_game(getattr(self.game, "folder", None), p.src, p.world_file, p.name)
        if bad:
            raise WrongGame(bad)
        self.copy_tree(p.src, dst, prune=world_prune)   # B400: a world zip built before the fix
        own = os.path.join(dst, WORLD_FILE)
        if p.world_file and not os.path.exists(own):
            self.copy_file(p.world_file, own)
        mark = os.path.join(dst, ".modstudio")
        if not os.path.exists(mark):
            with open(mark, "w", encoding="utf-8") as f:
                f.write(self.name)
            self.created(mark)
        value = ".\\livecpk\\" + p.name
        if not self.ini.find("cpk.root", value):
            self.ini.add("cpk.root", value, where="first")
            self.rec["ini"].append(["cpk.root", value])
        # the copy the modules read; Switch on makes the same one, this one is undone on removal
        self.copy_file(own, os.path.join(self.game.modules_dir, WORLD_FILE))
        self.rec["world"] = p.name
        self.rec["face_players"] = face_players(own)
        if getattr(p, "made", None):          # the next zip of this world is told newer or older by it
            self.rec["made"] = p.made

    def do_module(self, p, where):
        dst = os.path.join(self.game.modules_dir, os.path.basename(p.src))
        self.copy_file(p.src, dst)
        value = os.path.basename(p.src)
        if not any(norm(e.value) == norm(value) for e in self.ini.entries("lua.module")):
            self.ini.add("lua.module", value)
            self.rec["ini"].append(["lua.module", value])

    def do_cpk(self, p, where):
        import cpkread
        tmp = tempfile.mkdtemp(prefix="ms_cpk_")
        try:
            cpkread.extract(p.src, tmp)
            self.do_root(Part("root", tmp, safe(p.name)), where)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def do_pack(self, p, where):
        raise ValueError("a league package is added on the League packages page")

    def do_dll(self, p, where):
        pass

    def do_content(self, p, where):
        s = S.BY_KEY.get(p.server) if p.server else None
        # the folder the loaded module reads: SPFL26's own kits.lua reads content\kits (GitHub #129)
        dst = os.path.join(self.game.content_dir, s.folder_in(self.game.content_dir) if s else p.name)
        maps = {m.file.lower(): m for m in (s.maps if s else [])}
        cfg = s.config.lower() if s and s.config else None
        skip = set(maps) | ({cfg} if cfg and os.path.exists(os.path.join(dst, s.config)) else set())
        self.copy_tree(p.src, dst, skip=skip)
        for low, m in maps.items():
            src = os.path.join(p.src, m.file)
            if not os.path.exists(src):
                real = lower_names(p.src).get(low)
                src = os.path.join(p.src, real) if real else None
            if src and os.path.exists(src):
                self.merges.append((m, src, os.path.join(dst, m.file)))
        if p.map_line and s:
            m = next((m for m in s.maps if m.cols and m.cols[0].kind == "comp"), None)
            if m is not None:
                self.merges.append((m, p.map_line, os.path.join(dst, m.file)))

    def match_comps(self, m, theirs):
        """put each competition line on the competition its comment names, in the world in the game"""
        if not self.comps or not m.cols or m.cols[0].kind != "comp":
            return False
        by_name = {}
        for rid, n in self.comps.items():
            by_name.setdefault(" ".join(str(n).lower().split()), []).append(rid)
        moved = False
        for r in theirs.rows():
            if not (r.enabled and r.fields and r.fields[0].strip().isdigit() and r.comment):
                continue
            name = " ".join(r.comment.split("#")[0].lower().split())
            ids = by_name.get(name)
            rid = int(r.fields[0])
            if not ids:
                self.rec.setdefault("unmatched", []).append(r.comment.split("#")[0].strip())
                self.log("  no competition called \"%s\" in this world: line %d kept as it is; "
                         "pick the competition on Game content > Servers (Library > Use it for...)"
                         % (r.comment.split("#")[0].strip(), rid))
            elif rid not in ids:
                self.log("  %s is %d in this world (the pack said %d)" % (r.comment.split("#")[0].strip(), min(ids), rid))
                r.fields[0] = str(min(ids))
                r.touch()
                moved = True
        return moved

    def merge_map(self, m, src, dst):
        theirs = MapFile(src, width=m.width, sep=m.sep, quote=m.quote)
        moved = self.match_comps(m, theirs)
        if not os.path.exists(dst) and not moved and os.path.basename(src).lower() == m.file.lower():
            self.copy_file(src, dst)
            return
        mine = MapFile(dst, width=m.width, sep=m.sep, quote=m.quote)
        have = {}
        for r in mine.rows():
            if r.enabled and r.fields:
                have.setdefault(r.fields[0], []).append(r)
        same = {mine.render_row(r).strip() for r in mine.rows()}
        new = [r for r in theirs.rows() if r.enabled and mine.render_row(r).strip() not in same]
        if not new:
            return
        added, removed = [], []
        keys = {r.fields[0] for r in new if r.fields}
        if self.replace_lines:
            for k in keys:
                for r in have.get(k, []):
                    removed.append(mine.render_row(r))
                    mine.remove(r)
        mine.items.append("# ---- added by FL26 Mod Studio: %s ----" % self.name)
        for r in new:
            mine.items.append(r)
            added.append(mine.render_row(r))
        mine.save("merge from %s" % self.name, self.sd)
        k = self.rel(dst)
        self.rec["map_added"].setdefault(k, []).extend(added + ["# ---- added by FL26 Mod Studio: %s ----" % self.name])
        self.rec["map_removed"].setdefault(k, []).extend(removed)
        self.log("  %s: %d line(s) added, %d replaced" % (m.file, len(added), len(removed)))


# B74: a world zip whose world has the name of one built on this PC. The message is shown as it
# is (no "ValueError:"), in the user's language; the Import panel says it before Install too
def world_there(world):
    from .i18n import _
    return _("A world called %s is in the game already, built on this PC. Rename that world on its card "
             "in My world (or delete it there), then install this one again.") % world


class WorldThere(ValueError):
    """do_world: livecpk\\<world> is there and not from Install mods (the text is translated)"""


# mato 07.11.2026: an FL 2027 world (the Megapack: 204 leagues, ~103,000 players, 4800 clubs) put
# into FL26 by mistake would break the game, and an FL26 world in FL 2027 replaces its tables with
# FL26's. The world file's game line says which game a world is for (worldgame.py; Build writes it,
# an export too); a world without one is FL 2027's only when its tables hold more than FL26 takes.
def wrong_game(folder, root, world_file=None, world=None):
    """the reason, translated, that the world (or database folder) at <root> cannot go into the
    game at `folder`; None when it may"""
    import worldgame as WG
    m = WG.mismatch(root, folder, world_file)
    if not m:
        return None
    from .i18n import _
    name = world or os.path.basename(os.path.normpath(root))
    want, _have, teams, players = m
    if want == "fl27":
        return _("%s is a world for FL 2027 (%s clubs, %s players). FL26 takes %d clubs and %d players, so it "
                 "would break this game, and it does not go in. Choose FL 2027's folder (Game ▾) and put it "
                 "there, or get the FL26 version of the pack.") % (
            name, "?" if teams is None else teams, "?" if players is None else players,
            WG.FL26_CAPS[0], WG.FL26_CAPS[1])
    return _("%s is a world for FL26. FL 2027 has tables of its own, so it does not go in here. Choose FL26's "
             "folder (Game ▾), get the FL 2027 version of the pack, or open its recipe and Build it with "
             "FL 2027 as the game.") % name


def pack_wrong_game(folder, path, man=None):
    """mato 07.11.: the warning, translated, that the league package at path was made on the other
    game than the one at `folder` (its clubs differ, so some may be missing); None when it fits or
    does not say"""
    import lbpackage as K
    import worldgame as WG
    have = WG.game_of(folder)
    try:
        want = K.game_of(path, man)
    except K.Error:
        return None
    if not have or not want or want == have:
        return None
    from .i18n import _
    name = (man or {}).get("name") or os.path.basename(path)
    if want == "fl27":
        return _("%s is a league package made for FL 2027. FL26 has clubs of its own, so some of its clubs "
                 "may be missing here. Ask its author for the FL26 version.") % name
    return _("%s is a league package made for FL26. FL 2027 has clubs of its own, so some of its clubs "
             "may be missing here. Ask its author for the FL 2027 version.") % name


class WrongGame(WorldThere):
    """do_world: the world is for the other game (wrong_game; the text is translated)"""


def world_in_the_way(game, world):
    """True when installing the ready world `world` would stop at do_world: livecpk\\<world> is
    there, Install mods did not put it there (no .modstudio) and no install record brings it in
    (replace_world would take that one out first)"""
    d = os.path.join(game.livecpk_dir, world)
    return (bool(world) and os.path.isdir(d) and not os.path.exists(os.path.join(d, ".modstudio"))
            and not installed_as(game.sider_dir, world))


def ready_world(game, world):
    """True when livecpk\\<world> came from Install mods (a ready world from a zip, marked
    .modstudio) and not from Build on this PC: Build would only switch it off"""
    return bool(world) and os.path.exists(os.path.join(game.livecpk_dir, world, ".modstudio"))


def installed_as(sider_dir, world):
    """the install records that brought `world` in, oldest first"""
    return sorted((r for r in records_seen(sider_dir)
                   if r.get("world") == world or ["world", world] in (r.get("parts") or [])),
                  key=lambda r: r.get("time", ""))


def world_made(src):
    """when the world zip `src` was made, "YYYYmmdd-HHMMSS": export_world writes fl26worldpack.json
    into it at that moment and the zip keeps that time. None for a folder, a zip without that file
    or one that cannot be read -- then no version can be told newer or older than another
    (16.11.: an older zip of a world was called "a newer version of the world you have")"""
    if not str(src).lower().endswith(".zip") or not os.path.isfile(src):
        return None
    try:
        with zipfile.ZipFile(src) as z:
            m = next((m for m in z.infolist() if m.filename.replace("\\", "/").rsplit("/", 1)[-1].lower() == WORLD_INFO),
                     None)
    except (OSError, zipfile.BadZipFile):
        return None
    if m is None or m.date_time[0] < 1990:
        return None
    return "%04d%02d%02d-%02d%02d%02d" % m.date_time


def world_version(sider_dir, world, made):
    """how a zip of `world` made at `made` (world_made) stands to the one installed: "newer",
    "older", "same", or None when that cannot be told (a folder, no zip time, an install made
    before Mod Studio kept it in the record)"""
    recs = installed_as(sider_dir, world)
    have = recs[-1].get("made") if recs else None
    if not made or not have:
        return None
    return "newer" if made > have else "older" if made < have else "same"


def update_check(game, world, new_root):
    """17.11.2026 (idledger.py): can the world unpacked in `new_root` (a zip's world folder, with the
    id ledger export puts in it) go in over the `world` installed as an Update -- is it a later
    version of the same world (its lineage; a world of a zip without a ledger: its ids are a version
    in the new one's chain, else nearly all its clubs and leagues have the same names under the same
    ids), every id a career of the installed version holds still there, and only players retired?
    None when the new one has no ledger (a zip of before: Install says what it said before) or
    nothing of `world` is installed. Else idledger.update_verdict's {"ok", "why", "from", "to",
    "gone", "retired" {kind: n}, "reasons", "retired_names", "changed", "first", "match", "renamed"}.
    review 18.11.2026: a ledger that is JSON but not whole stopped Install with an AttributeError --
    anything that goes wrong here is a line in the log and None (Install as before the ledger)"""
    import idledger
    try:
        new_led = idledger.load(os.path.join(new_root, idledger.LEDGER), world)
        if new_led is None:
            return None
        root = os.path.join(game.livecpk_dir, world)
        if not os.path.isdir(root):
            return None
        old, old_led = idledger.installed_ids(root)
        v = idledger.update_verdict(old, old_led, new_led)
        if v.get("ok"):
            # 18.11.2026 evening (rowkeep.py): the ids are kept -- and every competition row the careers of
            # the version installed play on is where it was, with the same clubs in its places
            rk = rows_verdict(root, new_root)
            if rk is not None:
                v["rows"] = rk
                if not rk["ok"]:
                    v = dict(v, ok=False, why="rows")
        return v
    except Exception as e:                # noqa: BLE001 -- Install goes on without the Update
        try:
            sys.stderr.write("update_check %s: the zip's id ledger was not checked (%s: %s): Install goes on "
                             "as for a zip without one\n" % (world, type(e).__name__, e))
        except Exception:                 # noqa: BLE001 -- no console (the exe)
            pass
        return None


def rows_verdict(root, new_root):
    """rowkeep.summary of the world unpacked in `new_root` against the one installed in `root`: is every
    row of the installed one's Competition, CompetitionRegulation and CompetitionEntry tables where it
    was, with the same club in each place (ok)? None when either has no tables to read"""
    import rowkeep
    try:
        old = rowkeep.tables_dir(rowkeep.world_db(root), rowkeep.TABLES + (rowkeep.TEAM,))
        new = rowkeep.tables_dir(rowkeep.world_db(new_root))
    except rowkeep.RowsError:
        return None
    rep = rowkeep.check(rowkeep.rows_of_tables(old), new[rowkeep.TABLES[0]], new[rowkeep.TABLES[1]],
                        new[rowkeep.TABLES[2]], rowkeep.team_ids(old[rowkeep.TEAM]))
    return rowkeep.summary(rep)


# files of a world Mod Studio writes itself after the install: never "changed by you".
# kitmaker-index.json: lbservers' cache of the world's kitmaker.txt stamps (lbservers.INDEX, written
# by every Switch on and Build that makes kits; 16.11.: it was kept as "changed by you")
NOT_YOURS = {".modstudio", "fl26world.txt", "fl26playerids.json", "leaguebuilder-files.txt", "map.txt",
             "fl26stadiums.json", "fl26gamestadiums.json", "map_competitions.txt",
             "kitmaker-index.json", "fl26ids-ledger.json"} | {os.path.basename(f) for f in LOCAL_PATH_FILES}
KEPT = "kept"                             # ModStudio\kept\<world>-<time>: keep_yours


def _rec_time(text):
    try:
        return time.mktime(time.strptime(str(text), "%Y%m%d-%H%M%S"))
    except (TypeError, ValueError, OverflowError):
        return None


RUN_GAP = 300      # s: the longest an unpack takes between two files it writes (unpack_run)


def unpack_run(times, start=None):
    """(first, last) modified time of the files one unpack wrote, from the modified times of the
    files an install record of before 16.11. brought in (B487): Install copies a file with the
    time it has (CopyFile2), and a zip's files got theirs as they came out of it, one after the
    other, minutes before `start` (the record's "time": when the copies began). The longest run of
    times with no gap over RUN_GAP, of the times not after start; a file of the player's copied
    over one of them keeps ITS time, and falls outside. None when there are no times"""
    ts = sorted(t for t in times if start is None or t <= start + 5)
    best, first = None, 0
    for i in range(1, len(ts) + 1):
        if i == len(ts) or ts[i] - ts[i - 1] > RUN_GAP:
            if best is None or i - first >= best[0]:        # the later of two as long
                best = (i - first, ts[first], ts[i - 1])
            first = i
    return best and best[1:]


def _crc_of(p):
    crc = 0
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            crc = zlib.crc32(b, crc)
    return crc


def changed_since(path, st, stamp, start, run):
    """True when the file an install put at `path` (os.stat `st`) is not what it put there.
    With the record's stamp (stamp_of, installs of 16.11. on): its size is another, or its time is
    and so are its bytes (the crc32; without one, kept). Without (an older record): its time is
    later than the start of that install, or is not one the unpack gave its files (unpack_run) --
    what cannot be told is kept: a copy too many is harmless, a file of the player's deleted is not"""
    if stamp is not None:
        size, mt, crc = stamp
        if st.st_size != size:
            return True
        if st.st_mtime_ns == mt:
            return False
        if crc is None:
            return True
        try:
            return _crc_of(path) != crc
        except OSError:
            return True
    t = st.st_mtime
    if start is not None and t > start + 5:
        return True
    return run is None or not run[0] <= t <= run[1]


def keep_yours(game, world, olds, log=lambda t: None):
    """before an older install of a ready world is taken out: what the PERSON put into it is not
    deleted with it (pop1806, 14.11.2026: "installing beta 2 over beta 1 deleted what I had set
    up"). Kept, under ModStudio\\kept\\<world>-<time>, in the same folders as they had:
      - every file of livecpk\\<world> that no install record brought in (added by hand): moved;
      - every file the install brought in that is not what it put there (changed_since): copied.
        B487 (pop1806 16.11., "it deleted my faces"): that was told by its time only, later than
        the end of the install; a face copied over one of the world's keeps the time it had, older,
        and went without a copy -- and with a record of beta 3 or older (no "done") every changed
        file did.
    The new version goes in clean, as before -- an old file left in a world is a file the game
    reads. Returns (the folder or None, files added, files changed). Without a record (the world
    is only marked) nothing can be told apart, and nothing is kept."""
    sd = game.sider_dir
    if not olds:
        return None, 0, 0
    dest = os.path.join(home(sd), KEPT, "%s-%s" % (world, time.strftime("%Y%m%d-%H%M%S")))
    key = lambda rel: os.path.normcase(os.path.normpath(rel))
    owned, added, changed = set(), 0, 0

    def keep(rel, move):
        src, dst = long_path(os.path.join(sd, rel)), long_path(os.path.join(dest, rel))
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            (shutil.move if move else shutil.copy2)(src, dst)
            return 1
        except OSError as e:
            log("could not keep %s: %s" % (rel, e))
            return 0
    for rec in olds:
        owned |= {key(r) for r in rec.get("created") or []} | {key(r[0]) for r in rec.get("replaced") or []}
        stamps = stamps_of(sd, rec)
        start = _rec_time(rec.get("time"))
        there = []
        for rel in rec.get("created") or []:
            p = long_path(os.path.join(sd, rel))
            try:
                there.append((rel, p, os.stat(p), stamps.get(rel)))
            except OSError:
                continue
        run = unpack_run([st.st_mtime for _r, _p, st, s in there if s is None], start)
        for rel, p, st, s in there:
            if os.path.basename(rel).lower() not in NOT_YOURS and changed_since(p, st, s, start, run):
                changed += keep(rel, False)
    d = os.path.join(game.livecpk_dir, world)
    for root, _dirs, files in os.walk(long_path(d)) if os.path.isdir(d) else ():
        for f in files:
            full = os.path.join(root, f)
            if full.startswith("\\\\?\\"):
                full = full[4:]
            rel = os.path.relpath(full, sd)
            if key(rel) not in owned and f.lower() not in NOT_YOURS:
                added += keep(rel, True)
    if not (added or changed):
        return None, 0, 0
    log("%s: %d file(s) you added and %d you changed are kept in %s" % (world, added, changed, dest))
    return dest, added, changed


def replace_world(game, ini, world, log=lambda t: None, kept=None):
    """take out an older install of the same ready world before a new one goes in: every record
    that brought it in is removed as Remove the mod does (newest first), and what is left of
    livecpk\\<world> goes too -- copying a new version over the old one kept the old one's
    files (a club the new version no longer has kept its kit folder, a stale id file stayed).
    What the person added to the world or changed in it is kept first (keep_yours; `kept`, a
    list, gets (world, folder, added, changed) when there was any).
    Only a world Install mods put there is touched; returns notes as uninstall does"""
    olds = installed_as(game.sider_dir, world)
    d = os.path.join(game.livecpk_dir, world)
    marked = os.path.exists(os.path.join(d, ".modstudio"))
    notes = []
    keep_edited(game, [world], log)
    where, added, changed = keep_yours(game, world, olds, log)
    if where and kept is not None:
        kept.append((world, where, added, changed))
    for rec in reversed(olds):
        log("removing the older %s (%s)" % (world, rec.get("name")))
        notes += uninstall(game, ini, rec, log=log, kept=True)
    if (olds or marked) and os.path.isdir(d):
        shutil.rmtree(long_path(d))
        log("livecpk\\%s: what was left of the older one deleted" % world)
    return notes


def keep_edited(game, worlds_in, log=lambda t: None):
    """a ready world made editable on this PC (worlds.make_editable) is the user's work now:
    before Remove the mod or a newer zip of it takes it out, all of it goes into a world backup
    (Restore points > Put this copy back)"""
    from . import worlds
    for w in worlds_in:
        if worlds.edited_world(game, w):
            log("a copy of %s (made editable on this PC) before it is taken out: %s"
                % (w, worlds.backup(game, w, "updated")))


def worlds_of(rec):
    """the ready worlds an install record brought in"""
    return [w for w in [rec.get("world")] + [p[1] for p in (rec.get("parts") or [])
                                             if isinstance(p, (list, tuple)) and len(p) > 1 and p[0] == "world"] if w]


def header_pack(recs, live):
    """the install record the header's PACK box names (B168): the newest that brought in the world
    switched on in the game (live: its names), else the newest that brought in no world (a
    scoreboard or kit pack); None when neither is there -- after Activate of r12 the box said
    the eu4 zip installed last, while ACTIVE WORLD was right"""
    by_time = sorted(recs, key=lambda r: r.get("time", ""), reverse=True)
    for want in (lambda w: bool(set(w) & set(live)), lambda w: not w):
        for r in by_time:
            if want(worlds_of(r)):
                return r
    return None


def uninstall(game, ini, rec, log=lambda t: None, kept=False):
    """undo one record; returns notes about what could not be undone. kept: keep_edited ran
    already (replace_world)"""
    sd, notes = game.sider_dir, []
    if not kept:
        keep_edited(game, worlds_of(rec), log)
    # map lines first (the files are still there)
    for rel, lines in rec.get("map_added", {}).items():
        p = os.path.join(sd, rel)
        if not os.path.exists(p):
            continue
        raw = open(p, "rb").read()
        text = raw.decode("utf-8-sig", "replace")
        nl = "\r\n" if "\r\n" in text else "\n"
        drop = {l.strip() for l in lines}
        keep = [l for l in text.splitlines() if l.strip() not in drop]
        back = rec.get("map_removed", {}).get(rel, [])
        snapshot(p, "removing %s" % rec["name"], sd)
        with open(p + ".tmp", "wb") as f:
            f.write((b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b"") +
                    (nl.join(keep + back) + nl).encode("utf-8"))
        os.replace(p + ".tmp", p)
        log("%s: %d line(s) taken out, %d put back" % (rel, len(lines) - 1, len(back)))
    for key, value in rec.get("ini", []):
        for e in ini.entries(key):
            if norm(e.value) == norm(value):
                ini.remove(e)
                log("sider.ini: %s = %s removed" % (key, value))
                break
    for rel in rec.get("created", []):
        p = long_path(os.path.join(sd, rel))          # a deep file of a world (B400)
        try:
            os.remove(p)
        except OSError:
            if os.path.exists(p):
                notes.append("could not delete %s" % rel)
    for rel, copy in rec.get("replaced", []):
        try:
            shutil.copy2(long_path(os.path.join(sd, copy)), long_path(os.path.join(sd, rel)))
        except OSError:
            notes.append("could not put back %s" % rel)
    # empty folders the mod made
    for rel in sorted({os.path.dirname(r) for r in rec.get("created", [])}, key=len, reverse=True):
        d = os.path.join(sd, rel)
        while d.startswith(sd) and len(d) > len(sd):
            try:
                os.rmdir(long_path(d))
            except OSError:
                break
            d = os.path.dirname(d)
    rows = [r for r in records(sd) if not (r["name"] == rec["name"] and r["time"] == rec["time"])]
    _save(sd, rows)
    st = stamps_path(sd, rec)                         # B487: its stamps go with it
    if st and not any(r.get("stamps") == rec.get("stamps") for r in rows):
        try:
            os.remove(st)
        except OSError:
            pass
    return notes


# ----------------------------------------------------------------------------------------
def record_folder_pack(game, ini, name, files, ini_line=None, reason="Mod Studio pack install"):
    """a record for a pack put in place by Mod Studio's Rust tools (install_pack): the files it
    copied, and the sider.ini line it registered, so it shows on Install > In the game now and is
    removable there like any other mod (the line is taken out, the folder is deleted)"""
    sd = game.sider_dir
    root = os.path.join(sd, "livecpk", "root", name)
    created = []
    if os.path.isdir(root):
        for dp, _dn, fn in os.walk(root):
            for f in fn:
                p = os.path.join(dp, f)
                rel = os.path.relpath(p, sd)
                if rel.startswith("livecpk\\root\\") and safe(name) == name:
                    created.append(rel.replace("\\", "/").replace("/", os.sep))
    rec = {"name": name, "time": time.strftime("%Y%m%d-%H%M%S"), "created": created,
           "replaced": [], "ini": ([( "cpk.root", ini_line_value(name))] if ini_line else []),
           "map_added": {}, "map_removed": {}, "parts": []}
    rows = records(sd)
    rows.append(rec)
    _save(sd, rows)
    return rec


def ini_line_value(name):
    """the sider.ini value Rust's register writes for a pack under livecpk/root"""
    return ".\\livecpk\\root\\" + safe(name)


def remove_folder_pack(game, ini, name, ini_line=None):
    """undo one Mod Studio pack without a record: its sider.ini line out, its folder deleted"""
    import shutil as _sh
    sd = game.sider_dir
    notes = []
    value = ini_line or ini_line_value(name)
    for e in ini.entries("cpk.root"):
        if norm(e.value) == norm(value):
            ini.remove(e)
            break
    root = os.path.join(sd, "livecpk", "root", name)
    if os.path.isdir(root):
        snapshot(root, "removing Mod Studio pack %s" % name, sd)
        try:
            _sh.rmtree(long_path(root))
        except OSError as e:
            notes.append(str(e))
    return notes
