r"""The League Builder worlds in livecpk (_FL26...): which one is in the game, delete one so it can
be put back, rename one (0.2.4, mato 15.10.).

    live(game)              the worlds whose cpk.root line is switched on in sider.ini
    delete(game, world)     everything of the world goes into a backup folder, nothing is deleted
    rename(game, old, new)  every place the name is written changes with it
    backups_of(sider_dir)   the world backups Restore points lists; restore() puts one back
    make_editable(game, w)  a ready world from a zip becomes one Build may change, in place (B85)
    backup(game, w, kind)   a copy of all of a world (before it is made editable, before a Build of it)

A world's backups are kept in SiderAddons\ModStudio\backups\worlds\<world>\<YYYY-MM-DD HH-MM>
deleted (or renamed), one folder each, with world.json saying what was done. Of one world the
newest KEEP folders stay, so deleting the same big world again and again does not fill the disk.

What belongs to a world:
  - its folder, livecpk\<world>, and its cpk.root line in sider.ini;
  - its folders in the content servers' libraries, content\<server>\<world> (the kits made for its
    clubs, its scoreboards, and under _kits / _packs what a world zip carries of other packs);
  - the map lines that point into those folders (Build's, lbservers.py, and the ones a world zip
    brought, installer.export_world), and the lines Import your world took out of a map for them
    (they come back, as Remove the mod does);
  - its records in ModStudio\installed.json (a ready world, from Import your world);
  - when modules\fl26world.txt is its world file: that file, the home stadium lines Switch on
    wrote (lbstadiums.py) and its line in lib\CommonLib.lua.
The person's own recipe (%APPDATA%\FL26ModStudio\recipes, or wherever it was saved) is not
touched by delete: the world can be built again from it.

Nothing here knows Qt; pages/roots.py asks and pages/restore.py puts back.
"""
import codecs, json, os, re, shutil, time

from . import backups, installer as I
from .siderini import parse_entry, root_path

KEEP = 3                                   # world backups kept per world
INFO = "world.json"
TAG = I.OUR_LINE                           # "# FL26 Mod Studio:" -- the end of a map line Mod Studio wrote
OFF = "  # (switched off by FL26 Mod Studio)"   # lbstadiums.OFF: a line of yours we switched off
COMMONLIB_TAG = "-- FL26 world"            # leaguebuilder.COMMONLIB_TAG
STADIUM_MAPS = (os.path.join("stadium-server", "map_teams.txt"), os.path.join("stadiums", "map_teams.txt"))
NAME_OK = re.compile(r"_FL26[A-Za-z0-9_\-]+\Z")
NAME_MAX = 40


class WorldError(Exception):
    """a delete or rename that cannot be done, in words for the player"""


# ---- what is where ----------------------------------------------------------------------------
def _same(a, b):
    return os.path.normcase(os.path.normpath(a)) == os.path.normcase(os.path.normpath(b))


def is_world(name):
    # <world>.building is a Build's work folder, left behind when a Build stops on an error, and
    # <world>.old the world it replaces, for the moment of the swap (B150): no world
    return name.lower().startswith("_fl26") and not name.lower().endswith((".building", ".old"))


def world_of(path):
    """the world (a _FL26 folder in livecpk) path is in or is, None for any other folder: a folder a
    Build rewrites, never the tables it reads (B277)"""
    parts = os.path.normpath(os.path.abspath(path)).split(os.sep)
    return next((parts[i + 1] for i in range(len(parts) - 1)
                 if parts[i].lower() == "livecpk" and is_world(parts[i + 1])), None)


def worlds(game):
    """the _FL26 folders in livecpk"""
    try:
        return sorted(n for n in os.listdir(game.livecpk_dir)
                      if is_world(n) and os.path.isdir(os.path.join(game.livecpk_dir, n)))
    except OSError:
        return []


def _root_lines(game, lines, world):
    """indexes of the cpk.root lines (on or off) that load livecpk\\<world>"""
    want = os.path.join(game.livecpk_dir, world)
    out = []
    for i, l in enumerate(lines):
        e = parse_entry(i, l.rstrip("\r\n"))
        if e and e.key == "cpk.root" and _same(root_path(game.sider_dir, e.value), want):
            out.append(i)
    return out


def live(game):
    """the world folders whose cpk.root line is switched on in sider.ini: the world in the game
    (Home's live world; more than one is a mistake Home points out)"""
    out = []
    try:
        lines = _read(game.ini_path)[0]
    except OSError:
        return out
    for i, l in enumerate(lines):
        e = parse_entry(i, l.rstrip("\r\n"))
        if e and e.key == "cpk.root" and e.enabled:
            p = root_path(game.sider_dir, e.value)
            name = os.path.basename(p)
            if is_world(name) and _same(os.path.dirname(p), game.livecpk_dir) and name not in out:
                out.append(name)
    return out


def in_modules(game):
    """the world modules\\fl26world.txt is the world file of (what the modules read), or None"""
    return I.world_name(os.path.join(game.modules_dir, I.WORLD_FILE))


def name_form(new):
    """why `new` is not written as a world's name, or "": the part of check_name that holds for a
    name the world has already too (Construction's World name field, B295)"""
    from .i18n import _
    new = (new or "").strip()
    if not new.startswith("_FL26"):
        return _("The world name must start with _FL26.")
    if not NAME_OK.match(new):
        return _("After _FL26 use only letters, digits, - and _ (no spaces).")
    if len(new) > NAME_MAX:
        return _("The name is too long (at most %d characters).") % NAME_MAX
    return ""


def check_name(game, new, old=None):
    """why `new` cannot be a world's name, or "" (Build finds a world by "_FL26" at the start,
    the world file's "world" line ends at a space, and a map line cannot hold a quote, a comma or
    a #: letters, digits, - and _ only). In the user's language: a text with a name or number in
    it is translated before it is filled in (the page's _(why) cannot find it afterwards)"""
    from .i18n import _
    new = (new or "").strip()
    why = name_form(new)
    if why:
        return why
    if old is not None and new.lower() == old.lower():
        return _("That is the name it has now.")
    if os.path.exists(os.path.join(game.livecpk_dir, new)) or any(
            n.lower() == new.lower() for n in worlds(game)):
        return _("There is a world called %s already.") % new
    for lib in _libs(game):
        if os.path.exists(os.path.join(game.content_dir, lib, new)):
            return _("content\\%s\\%s is there already: a world of that name was here before.") % (lib, new)
    return ""


def _libs(game):
    try:
        return sorted(n for n in os.listdir(game.content_dir) if os.path.isdir(os.path.join(game.content_dir, n)))
    except OSError:
        return []


def _maps(game, extra=()):
    """the map files of the content servers (content\\<server>\\map*.txt), as paths relative to
    SiderAddons, and any in `extra`"""
    out = []
    for lib in _libs(game):
        d = os.path.join(game.content_dir, lib)
        for f in sorted(os.listdir(d)):
            if f.lower().startswith("map") and f.lower().endswith(".txt") and os.path.isfile(os.path.join(d, f)):
                out.append(os.path.relpath(os.path.join(d, f), game.sider_dir))
    for rel in extra:
        if os.path.isfile(os.path.join(game.sider_dir, rel)) and not any(_same(rel, o) for o in out):
            out.append(rel)
    return out


def _ref(world):
    """a map line's folder under <world>\\: "<world>\\..." after the start, a space, a comma or a quote"""
    return re.compile(r"(?i)(^|[\s,\"'#])" + re.escape(world) + r"(?=[\\/])")


# ---- text files, line by line, bytes kept --------------------------------------------------------
def _read(path):
    """(lines with their endings, encoding, bom): what _write turns back into the same bytes"""
    with open(path, "rb") as f:
        raw = f.read()
    bom = raw.startswith(codecs.BOM_UTF8)
    body = raw[3:] if bom else raw
    try:
        text, enc = body.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        text, enc = body.decode("latin-1"), "latin-1"      # every byte as it is, written back the same
    return text.splitlines(True), enc, bom


def _write(path, lines, enc, bom):
    if isinstance(lines, bytes):                  # the whole file as it is to be (rename's json files)
        with open(path + ".tmp", "wb") as f:
            f.write(lines)
        os.replace(path + ".tmp", path)
        return
    data = "".join(lines).encode(enc)
    with open(path + ".tmp", "wb") as f:
        f.write((codecs.BOM_UTF8 if bom else b"") + data)
    os.replace(path + ".tmp", path)


def _body(l):
    return l.rstrip("\r\n")


def _nl(lines):
    for l in lines:
        if l.endswith("\r\n"):
            return "\r\n"
        if l.endswith("\n"):
            return "\n"
    return "\r\n"


# ---- the backup folder -----------------------------------------------------------------------------
def worlds_home(sider_dir):
    return os.path.join(backups.home(sider_dir), "backups", "worlds")


def _new_backup(sider_dir, world, kind):
    base = os.path.join(worlds_home(sider_dir), world)
    stamp = time.strftime("%Y-%m-%d %H-%M")
    d = os.path.join(base, "%s %s" % (stamp, kind))
    n = 2
    while os.path.exists(d):
        d = os.path.join(base, "%s %s (%d)" % (stamp, kind, n))
        n += 1
    os.makedirs(d)
    return d


def _save_info(folder, info):
    p = os.path.join(folder, INFO)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(info, f, indent=1, ensure_ascii=False)
    os.replace(p + ".tmp", p)


def _load_info(folder):
    with open(os.path.join(folder, INFO), encoding="utf-8") as f:
        return json.load(f)


def _keep_text(sd, folder, rel, reason=None):
    """a copy of a text file into the backup's before\\ (for undoing by hand), and a restore point
    (Restore points) when `reason`"""
    src = os.path.join(sd, rel)
    if not os.path.isfile(src):
        return
    dst = os.path.join(folder, "before", rel)
    if not os.path.exists(dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
    if reason:
        backups.snapshot(src, reason, sd)


def prune(sider_dir, world, keep=KEEP, but=None):
    """only the newest `keep` backups of one world stay. Newest by the time in world.json to the
    fraction of a second: a folder name can come again in the same minute once the older one of
    that name is gone, so the name alone does not say which is newer. `but` (the backup just
    made) always stays"""
    base = os.path.join(worlds_home(sider_dir), world)

    def when(d):
        i = _load_info(os.path.join(base, d))
        return (i.get("time", ""), i.get("t", 0.0), d)
    try:
        dirs = sorted((d for d in os.listdir(base) if os.path.isfile(os.path.join(base, d, INFO))),
                      key=when, reverse=True)
    except (OSError, ValueError):
        return []
    if but is not None:
        dirs = [d for d in dirs if not _same(os.path.join(base, d), but)]
        keep -= 1
    gone = dirs[max(keep, 0):]
    for d in gone:
        shutil.rmtree(long_path(os.path.join(base, d)), ignore_errors=True)
    return gone


def backups_of(sider_dir):
    """the world backups that can be put back, newest first: [(folder, info)]"""
    out = []
    home = worlds_home(sider_dir)
    if not os.path.isdir(home):
        return out
    for w in os.listdir(home):
        base = os.path.join(home, w)
        if not os.path.isdir(base):
            continue
        for d in os.listdir(base):
            f = os.path.join(base, d)
            try:
                info = _load_info(f)
            except (OSError, ValueError):
                continue
            if not info.get("restored"):
                out.append((f, info))
    return sorted(out, key=lambda x: x[1].get("time", ""), reverse=True)


def long_path(p):
    r"""B189 (SladeBR 21.10.): p as a Windows path past MAX_PATH. A world backup goes under
    SiderAddons\ModStudio\backups\worlds\<world>\<time> edited\files\..., and with the game in
    Program Files a scoreboard of a pack there is 275 characters: Windows stops at 260 unless long
    paths are on, and Make it editable said it could not find the path. \\?\ lifts the limit"""
    if os.name != "nt":
        return p
    p = os.path.abspath(p)
    if p.startswith('\\\\?\\'):
        return p
    if p.startswith('\\\\'):
        return '\\\\?\\UNC\\' + p[2:]
    return '\\\\?\\' + p


def size_of(folder):
    n = 0
    for dp, _dn, fn in os.walk(long_path(folder)):
        for f in fn:
            try:
                n += os.path.getsize(os.path.join(dp, f))
            except OSError:
                pass
    return n


def world_size(game, world):
    """the bytes Delete world moves into its backup: livecpk/<world> and its content folders"""
    n = size_of(os.path.join(game.livecpk_dir, world))
    return n + sum(size_of(os.path.join(game.content_dir, lib, world)) for lib in _libs(game)
                   if os.path.isdir(os.path.join(game.content_dir, lib, world)))


def discard(sider_dir, folder):
    """B131 (Vicentico 18.10.: 6 GB of deleted worlds he could not find): a world backup deleted for
    good, to free the disk. Only a folder of worlds_home with its world.json; returns the bytes freed"""
    home = os.path.normcase(os.path.abspath(worlds_home(sider_dir)))
    f = os.path.abspath(folder)
    if (os.path.normcase(os.path.dirname(os.path.dirname(f))) != home
            or not os.path.isfile(os.path.join(f, INFO))):
        raise WorldError("%s is not a world backup of Mod Studio." % folder)
    n = size_of(f)

    def unlock(fn, path, _exc):            # a read-only file stops rmtree
        os.chmod(path, 0o666)
        fn(path)
    shutil.rmtree(long_path(f), onerror=unlock)
    try:
        os.rmdir(os.path.dirname(f))       # the world's folder of backups, when that was its last
    except OSError:
        pass
    return n


# ---- a copy of a world (editing a ready world) ------------------------------------------------------
EDITED = ".modstudio-edited"               # a ready world from a zip, made editable on this PC


def edited_world(game, world):
    """True when livecpk\\<world> came from a zip and was made editable here (make_editable)"""
    return bool(world) and os.path.exists(os.path.join(game.livecpk_dir, world, EDITED))


def backup(game, world, kind="edited", log=lambda t: None):
    """a copy of all of `world` into a world backup, the world staying where it is: its folder, its
    folders in the content servers' libraries, and the map files, sider.ini and modules\\fl26world.txt
    as they are (before\\). kind: "edited" (make_editable), "built" (before a Build of an edited
    world), "updated" (before Remove the mod or a newer zip takes it out). Restore points'
    Put this copy back (restore) makes the world what it was. Returns the
    backup folder; of one world the newest KEEP backups stay (prune)"""
    sd = game.sider_dir
    if not is_world(world) or not os.path.isdir(os.path.join(game.livecpk_dir, world)):
        raise WorldError("There is no world %s in %s." % (world, game.livecpk_dir))
    folder = _new_backup(sd, world, kind)
    info = {"kind": kind, "world": world, "time": time.strftime("%Y%m%d-%H%M%S"), "t": time.time(),
            "copied": [], "texts": []}
    _save_info(folder, info)
    try:
        rels = [os.path.join("livecpk", world)]
        rels += [os.path.join("content", lib, world) for lib in _libs(game)
                 if os.path.isdir(os.path.join(game.content_dir, lib, world))]
        for rel in rels:
            shutil.copytree(long_path(os.path.join(sd, rel)), long_path(os.path.join(folder, "files", rel)))
            info["copied"].append(rel)
            _save_info(folder, info)
            log("copied into the backup: %s" % rel)
        for rel in _maps(game) + ["sider.ini", os.path.join("modules", I.WORLD_FILE)]:
            if os.path.isfile(os.path.join(sd, rel)):
                _keep_text(sd, folder, rel)
                info["texts"].append(rel)
        _save_info(folder, info)
    except BaseException:
        shutil.rmtree(long_path(folder), ignore_errors=True)      # half a copy is no backup
        raise
    prune(sd, world, but=folder)
    return folder


def make_editable(game, world, log=lambda t: None):
    """B85: a ready world from a zip (installer.ready_world) becomes a world of this PC that Build
    may change -- in place, under its own name (mato 15.10.: no copy, which lost the scoreboards the
    zip carries at the next switch). First all of it goes into a backup (Put this copy back makes it
    the ready world again); then the kits made for its clubs on the PC that built it are stamped as
    made here (lbservers.restamp: a Build keeps them, and a club whose colours change gets its kit
    drawn again); then its .modstudio mark becomes .modstudio-edited. Returns the backup folder."""
    root = os.path.join(game.livecpk_dir, world)
    if not I.ready_world(game, world):
        raise WorldError("%s is not a ready world from a zip." % world)
    with open(os.path.join(root, "leaguebuilder-plan.json"), encoding="utf-8") as f:
        plan = json.load(f)
    folder = backup(game, world, "edited", log)
    import lbservers
    lbservers.restamp(plan, game.sider_dir, root, log)
    os.replace(os.path.join(root, ".modstudio"), os.path.join(root, EDITED))
    log("%s: made editable (the backup: %s)" % (world, folder))
    return folder


def _put_copy_back(game, folder, info, log):
    """restore() of a backup taken by backup(): the world's folders as they were (the ones there now
    go into the backup's replaced\\, nothing is deleted), and the map lines the world carries from
    other packs (a zip's _kits / _packs) that a Build since took out come back: on when the world is
    in the game, else switched off (its next Switch on turns them on). The game must be closed
    (Restore points checks that)"""
    from .i18n import _
    sd, world = game.sider_dir, info["world"]
    on = world in live(game)
    for rel in info["copied"]:
        if not os.path.isdir(os.path.join(folder, "files", rel)):
            raise WorldError(_("This copy is not complete (%s is missing): it cannot be put back.") % rel)
    for rel in info["copied"]:
        now, old = os.path.join(sd, rel), os.path.join(folder, "files", rel)
        if os.path.exists(now):
            aside = os.path.join(folder, "replaced", rel)
            if os.path.exists(aside):
                shutil.rmtree(long_path(aside))
            os.makedirs(os.path.dirname(aside), exist_ok=True)
            shutil.move(now, aside)
        os.makedirs(os.path.dirname(now), exist_ok=True)
        shutil.copytree(long_path(old), long_path(now))
        log("put back: %s" % rel)
    import lbservers
    me = lbservers.safe(world).lower()
    for rel in info.get("texts", []):
        before, p = os.path.join(folder, "before", rel), os.path.join(sd, rel)
        if not rel.lower().endswith(".txt") or not os.path.isfile(before) or not os.path.isfile(p):
            continue
        theirs = [l for l in _read(before)[0] if lbservers.carrier(_body(l)) == me]
        if not theirs:
            continue
        lines, enc, bom = _read(p)
        have = {re.sub(r"^\s*#\s*", "", _body(l)) for l in lines}
        back = [l for l in theirs if re.sub(r"^\s*#\s*", "", _body(l)) not in have]
        if back:
            backups.snapshot(p, "world %s put back" % world, sd)
            if lines and not lines[-1].endswith(("\n", "\r")):
                lines[-1] += _nl(lines)
            lines += [("" if on else "#") + re.sub(r"^\s*#\s*", "", _body(l)) + _nl(lines) for l in back]
            _write(p, lines, enc, bom)
            log("%s: %d line(s) of %s back%s" % (rel, len(back), world, "" if on else ", switched off"))
    info["restored"] = time.strftime("%Y%m%d-%H%M%S")
    _save_info(folder, info)
    return world


# ---- delete ----------------------------------------------------------------------------------------
def delete(game, world, log=lambda t: None):
    """take `world` out of the game into a backup folder; returns (folder, info).

    The world switched on in sider.ini is refused (WorldError): taking out the world the game runs
    would leave the modules reading a world file whose tables are gone, and the world's own modules
    patching the game for leagues that are not there -- the player switches another world on (or
    this one off) first, one tick, and then knows the game has no world of this name any more."""
    sd = game.sider_dir
    root = os.path.join(game.livecpk_dir, world)
    if not is_world(world) or not os.path.isdir(root):
        raise WorldError("There is no world %s in %s." % (world, game.livecpk_dir))
    if world in live(game):
        raise WorldError("%s is the world in the game now (green). Switch another world on first, or untick "
                         "this one and press Apply; then it can be deleted." % world)
    named = in_modules(game) == world             # its world file is what the modules read
    folder = _new_backup(sd, world, "deleted")
    info = {"kind": "deleted", "world": world, "time": time.strftime("%Y%m%d-%H%M%S"), "t": time.time(),
            "moved": [], "texts": [], "records": [], "file_named": named}
    _save_info(folder, info)
    recs = I.installed_as(sd, world)
    try:
        # the folders first: a world the game holds open stops here, before any line is touched
        rels = [os.path.join("livecpk", world)]
        rels += [os.path.join("content", lib, world) for lib in _libs(game)
                 if os.path.isdir(os.path.join(game.content_dir, lib, world))]
        if named:
            rels.append(os.path.join("modules", I.WORLD_FILE))
        for rel in rels:
            dst = os.path.join(folder, "files", rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(os.path.join(sd, rel), dst)
            info["moved"].append(rel)
            _save_info(folder, info)
            log("moved into the backup: %s" % rel)
        # sider.ini: its cpk.root line(s), on or off
        if os.path.isfile(game.ini_path):
            lines, enc, bom = _read(game.ini_path)
            at = _root_lines(game, lines, world)
            if at:
                _keep_text(sd, folder, "sider.ini", "world %s deleted" % world)
                op = {"file": "sider.ini", "removed": [[i, lines[i]] for i in at], "on": [], "added": []}
                for i in reversed(at):
                    del lines[i]
                _write(game.ini_path, lines, enc, bom)
                info["texts"].append(op)
                _save_info(folder, info)
                log("sider.ini: %d line(s) of %s taken out" % (len(at), world))
        # the map lines
        added = {}
        for rec in recs:
            for rel, ls in (rec.get("map_added") or {}).items():
                added.setdefault(os.path.normcase(rel), set()).update(l.strip() for l in ls)
        back = {}
        for rec in recs:
            for rel, ls in (rec.get("map_removed") or {}).items():
                back.setdefault(os.path.normcase(rel), []).extend(ls)
        extra = [rel for rec in recs for rel in list((rec.get("map_added") or {})) + list((rec.get("map_removed") or {}))]
        ref = _ref(world)
        for rel in _maps(game, extra):
            stadiums = named and any(_same(os.path.join("content", s), rel) for s in STADIUM_MAPS)
            op = _drop_lines(os.path.join(sd, rel), ref, added.get(os.path.normcase(rel), set()),
                             back.get(os.path.normcase(rel), []), stadiums,
                             lambda r=rel: _keep_text(sd, folder, r, "world %s deleted: its lines taken out" % world))
            if op:
                op["file"] = rel
                op["named"] = stadiums
                info["texts"].append(op)
                _save_info(folder, info)
                log("%s: %d line(s) taken out, %d switched back on, %d put back"
                    % (rel, len(op["removed"]), len(op["on"]), len(op["added"])))
        # its line in the Kick Off league list (leaguebuilder.commonlib_leagues)
        cl = os.path.join("modules", "lib", "CommonLib.lua")
        if named and os.path.isfile(os.path.join(sd, cl)):
            lines, enc, bom = _read(os.path.join(sd, cl))
            at = [i for i, l in enumerate(lines) if (COMMONLIB_TAG + " " + world + " ") in l]
            if at:
                _keep_text(sd, folder, cl, "world %s deleted" % world)
                op = {"file": cl, "removed": [[i, lines[i]] for i in at], "on": [], "added": [], "named": True}
                for i in reversed(at):
                    del lines[i]
                _write(os.path.join(sd, cl), lines, enc, bom)
                info["texts"].append(op)
                _save_info(folder, info)
        # the records of Import your world: the world is out, so are they
        if recs:
            _keep_text(sd, folder, os.path.relpath(I.db_path(sd), sd))
            rows = I.records(sd)
            keys = {(r.get("name"), r.get("time")) for r in recs}
            info["records"] = [[i, r] for i, r in enumerate(rows) if (r.get("name"), r.get("time")) in keys]
            I._save(sd, [r for r in rows if (r.get("name"), r.get("time")) not in keys])
            _save_info(folder, info)
            log("installed.json: %d record(s) of %s taken out" % (len(recs), world))
    finally:
        _save_info(folder, info)
    prune(sd, world, but=folder)
    return folder, info


def _drop_lines(path, ref, added, back, stadiums, keep):
    """a map without the world's lines; what was done, for restore(), or None when nothing was.
    keep() is called before the file is written (a copy and a restore point of it)"""
    try:
        lines, enc, bom = _read(path)
    except OSError:
        return None
    header = {l.strip() for l in added if l.strip().startswith("# ---- added by FL26 Mod Studio:")}

    def gone(l):
        b = _body(l)
        if ref.search(b.split(TAG)[0] if TAG in b else b):
            return True
        if b.strip() in added or b.strip() in header:
            return True
        return stadiums and TAG in b and not b.lstrip().startswith("#")

    at = [i for i, l in enumerate(lines) if gone(l)]
    out = set(at)
    rest = [l for i, l in enumerate(lines) if i not in out]
    # a line of yours we switched off for one the world had goes back on, unless a line of ours
    # still takes its place (what lbstadiums / lbservers do when a line of ours goes)
    key = re.compile(r"^\s*(#\s*)?(\d+)\s*,")
    keys = set()
    for i in at:
        m = key.match(_body(lines[i]))
        if m and not m.group(1):
            keys.add(int(m.group(2)))
    taken = set()
    for l in rest:
        m = key.match(_body(l))
        if m and not m.group(1) and TAG in l:
            taken.add(int(m.group(2)))
    on = []
    for i, l in enumerate(rest):
        b = _body(l)
        if b.endswith(OFF):
            m = key.match(b[:-len(OFF)])
            if m and int(m.group(2)) in keys and int(m.group(2)) not in taken:
                new = re.sub(r"^(\s*)#\s*", r"\1", b[:-len(OFF)], count=1) + l[len(b):]
                on.append([i, l, new])
                rest[i] = new
    have = {_body(l).strip() for l in rest}
    put, fixed = [], False
    nl = _nl(lines)
    for l in back:
        if l.strip() and l.strip() not in have:
            if rest and not rest[-1].endswith(("\n", "\r")) and not fixed:
                rest[-1] += nl
                fixed = True
            put.append(l + nl)
            rest.append(l + nl)
            have.add(l.strip())
    if not at and not on and not put:
        return None
    keep()
    _write(path, rest, enc, bom)
    return {"removed": [[i, lines[i]] for i in at], "on": on, "added": put, "fixed_end": fixed}



# ---- put back --------------------------------------------------------------------------------------
def restore(game, folder, log=lambda t: None):
    """put a world backup back: a deleted world comes back as it was (switched off when it was
    off), a rename is undone by renaming back. Returns the world's name. Its WorldError texts are
    in the user's language, translated before they are filled in (as check_name's)"""
    from .i18n import _
    info = _load_info(folder)
    if info.get("restored"):
        raise WorldError(_("This backup was put back already."))
    if info["kind"] in ("edited", "built", "updated"):
        return _put_copy_back(game, folder, info, log)
    if info["kind"] == "renamed":
        old, new = info["world"], info["new"]
        if not os.path.isdir(os.path.join(game.livecpk_dir, new)):
            raise WorldError(_("%s is not in livecpk any more: nothing to rename back.") % new)
        why = check_name(game, old, new)
        if why:
            raise WorldError(why)
        rename(game, new, old, log)
        info["restored"] = time.strftime("%Y%m%d-%H%M%S")
        _save_info(folder, info)
        return old
    sd, world = game.sider_dir, info["world"]
    if os.path.exists(os.path.join(game.livecpk_dir, world)):
        raise WorldError(_("A world called %s is in livecpk already: rename or delete that one first.") % world)
    taken = os.path.join(game.modules_dir, I.WORLD_FILE)
    # another world was switched on since: its world file stays, and the lines Switch on wrote for
    # it with it; this one comes back switched off (Switch on writes its own again)
    other = info.get("file_named") and os.path.exists(taken)
    for rel in info["moved"]:
        if os.path.exists(os.path.join(sd, rel)) and not (other and _same(rel, os.path.join("modules", I.WORLD_FILE))):
            raise WorldError(_("%s is there again: move it away first.") % rel)
    for rel in info["moved"]:
        src, dst = os.path.join(folder, "files", rel), os.path.join(sd, rel)
        if other and _same(rel, os.path.join("modules", I.WORLD_FILE)):
            log("modules\\fl26world.txt of the world in the game stays")
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
        log("put back: %s" % rel)
    for op in reversed(info["texts"]):
        if other and op.get("named"):
            continue
        p = os.path.join(sd, op["file"])
        if not os.path.exists(p):
            continue
        lines, enc, bom = _read(p)
        backups.snapshot(p, "world %s put back" % world, sd)
        for l in reversed(op["added"]):
            for i in range(len(lines) - 1, -1, -1):
                if lines[i] == l or _body(lines[i]) == _body(l):
                    del lines[i]
                    break
        if op.get("fixed_end") and lines:
            lines[-1] = _body(lines[-1])
        for i, old, new in op["on"]:
            if i < len(lines) and lines[i] == new:
                lines[i] = old
            elif new in lines:
                lines[lines.index(new)] = old
        for i, l in sorted(op["removed"], key=lambda x: x[0]):
            lines.insert(min(i, len(lines)), l)
        _write(p, lines, enc, bom)
        log("%s: as before" % op["file"])
    if info["records"]:
        rows = I.records(sd)
        for i, r in sorted(info["records"], key=lambda x: x[0]):
            rows.insert(min(i, len(rows)), r)
        I._save(sd, rows)
    info["restored"] = time.strftime("%Y%m%d-%H%M%S")
    _save_info(folder, info)
    return world


# ---- rename ----------------------------------------------------------------------------------------
def _swap(rel, old, new):
    """a path with its <old> folder named <new>"""
    if old.lower() not in rel.lower():           # most of a big install record's 50000 paths (B66)
        return rel
    parts = re.split(r"([\\/])", rel)
    return "".join(new if p.lower() == old.lower() else p for p in parts)


def _swap_lines(lines, ref, new):
    return [ref.sub(lambda m: m.group(1) + new, l) for l in lines]


def _only_with(needle, fn, case=True):
    """fn(lines) for the lines that hold `needle`, the others as they are (B66: a big world's
    leaguebuilder-plan.json is 128 MB, 5 million lines, and a regex on every line took seconds;
    only a line with the old name in it can change)"""
    def run(lines):
        if case:
            return [fn([l])[0] if needle in l else l for l in lines]
        low = needle.lower()
        return [fn([l])[0] if low in l.lower() else l for l in lines]
    return run


def rename(game, old, new, log=lambda t: None):
    """rename the world `old` to `new` everywhere its name is written; returns (folder, info).

    The game itself never sees a world's name: Sider gives it the files inside the folder, the
    modules read modules\\fl26world.txt by what is in it, and a save holds team and competition
    ids, not folders. So a career keeps working, as long as everything that points at the folder
    points at the new one: the cpk.root line (same place, on or off as it was), the map lines of
    the kits, scoreboards and menu themes, the content folders, the world file's "world" line,
    leaguebuilder-plan.json and fl26playerids.json (Build reads them back by the name), the
    install records of a ready world, the profiles and lib\\CommonLib.lua's line."""
    sd = game.sider_dir
    src = os.path.join(game.livecpk_dir, old)
    if not os.path.isdir(src):
        raise WorldError("There is no world %s in %s." % (old, game.livecpk_dir))
    why = check_name(game, new, old)
    if why:
        raise WorldError(why)
    ref = _ref(old)
    edits = []                                     # (rel after the rename, rel before, new lines, enc, bom, restore point)

    def text(rel_now, rel_was, fn, point=True):
        p = os.path.join(sd, rel_was)
        if not os.path.isfile(p):
            return
        lines, enc, bom = _read(p)
        out = fn(lines)
        if out != lines:
            edits.append((rel_now, rel_was, out, enc, bom, point))

    def ini_fix(lines):
        out = list(lines)
        for i in _root_lines(game, lines, old):
            e = parse_entry(i, _body(lines[i]))
            v = e.value.rstrip("\\/")
            nv = v[:len(v) - len(old)] + new + e.value[len(v):]
            at = lines[i].find(e.value)
            out[i] = lines[i][:at] + nv + lines[i][at + len(e.value):]
        return out

    text("sider.ini", "sider.ini", ini_fix)
    for rel in _maps(game):
        text(rel, rel, _only_with(old, lambda ls: _swap_lines(ls, ref, new), case=False))
    wl = re.compile(r"^(\s*world\s+)" + re.escape(old) + r"(?=\s|$)")
    world_line = _only_with(old, lambda ls: [wl.sub(lambda m: m.group(1) + new, l) for l in ls])
    for f in (I.WORLD_FILE, ):
        text(os.path.join("livecpk", new, f), os.path.join("livecpk", old, f), world_line, False)
    # the two json files as bytes, not lines (B66: the plan of a world of 1146 clubs is 128 MB, five
    # million lines; split into lines it took seconds and half a GB). json.dump never breaks a line
    # between a key and its value, so this is the same edit, byte for byte, as line by line
    jw = re.compile(rb'("world"[ \t]*:[ \t]*")' + re.escape(old.encode("utf-8")) + rb'"')
    for f in ("leaguebuilder-plan.json", "fl26playerids.json"):
        p = os.path.join(sd, "livecpk", old, f)
        if not os.path.isfile(p):
            continue
        with open(p, "rb") as fh:
            raw = fh.read()
        out, n = jw.subn(lambda m: m.group(1) + new.encode("utf-8") + b'"', raw)
        del raw
        if n:
            edits.append((os.path.join("livecpk", new, f), os.path.join("livecpk", old, f), out, None, None, False))
    if in_modules(game) == old:
        mf = os.path.join("modules", I.WORLD_FILE)
        text(mf, mf, world_line)
    cl = os.path.join("modules", "lib", "CommonLib.lua")
    ct = re.compile(re.escape(COMMONLIB_TAG + " " + old) + r"(?= )")
    text(cl, cl, lambda ls: [ct.sub(COMMONLIB_TAG + " " + new, l) for l in ls])
    import lbtrophies                                 # the world's trophies in FL26's Entrance.lua
    ent = lbtrophies.module_path(sd)
    if ent:
        el = os.path.relpath(ent, sd)
        text(el, el, lambda ls: lbtrophies.rename_lines(ls, old, new))

    # what Mod Studio keeps of its own: the install records and the profiles
    rows = I.records(sd)
    recs_changed = False
    for r in rows:
        mine = r.get("world") == old or ["world", old] in (r.get("parts") or [])
        if not mine:
            continue
        recs_changed = True
        if r.get("world") == old:
            r["world"] = new
        r["parts"] = [[k, new if (k == "world" and n == old) else n] for k, n in (r.get("parts") or [])]
        r["created"] = [_swap(p, old, new) for p in r.get("created") or []]
        r["replaced"] = [[_swap(a, old, new), b] for a, b in r.get("replaced") or []]
        r["ini"] = [[k, _swap(v, old, new)] for k, v in r.get("ini") or []]
        for key in ("map_added", "map_removed"):
            r[key] = {k: _swap_lines(v, ref, new) for k, v in (r.get(key) or {}).items()}
    from . import profiles as PR
    profs = []
    for p in PR.listing(sd):
        vals = p.get("cpk.root") or []
        nv = [[_swap(v, old, new) if _same(root_path(sd, v), src) else v, on] for v, on in vals]
        if nv != vals:
            p["cpk.root"] = nv
            profs.append(p)

    folder = _new_backup(sd, old, "renamed")
    info = {"kind": "renamed", "world": old, "new": new, "time": time.strftime("%Y%m%d-%H%M%S"), "t": time.time(),
            "texts": [e[1] for e in edits], "moved": []}
    for _now, was, _o, _e, _b, point in edits:
        _keep_text(sd, folder, was, ("world %s renamed to %s" % (old, new)) if point else None)
    if recs_changed:
        _keep_text(sd, folder, os.path.relpath(I.db_path(sd), sd))
    for p in profs:
        _keep_text(sd, folder, os.path.relpath(p["_file"], sd))
    _save_info(folder, info)

    # the folders: the world's first (the game holding it open stops everything here), then its
    # content folders; one that will not move puts the others back
    moved = []
    try:
        was = os.stat(src)              # its time stays (B75: My world orders the cards by it, newest first)
    except OSError:
        was = None
    try:
        for lib in [None] + _libs(game):
            a = src if lib is None else os.path.join(game.content_dir, lib, old)
            b = os.path.join(game.livecpk_dir, new) if lib is None else os.path.join(game.content_dir, lib, new)
            if os.path.isdir(a):
                os.rename(a, b)
                moved.append((a, b))
                log("%s -> %s" % (os.path.relpath(a, sd), os.path.relpath(b, sd)))
    except OSError:
        for a, b in reversed(moved):
            try:
                os.rename(b, a)
            except OSError:
                pass
        shutil.rmtree(folder, ignore_errors=True)
        raise
    info["moved"] = [[os.path.relpath(a, sd), os.path.relpath(b, sd)] for a, b in moved]
    for now, _was, out, enc, bom, _point in edits:
        _write(os.path.join(sd, now), out, enc, bom)
        log("%s: %s -> %s" % (now, old, new))
    if recs_changed:
        I._save(sd, rows)
    for p in profs:
        f = p.pop("_file")
        with open(f + ".tmp", "w", encoding="utf-8") as fh:
            json.dump(p, fh, indent=1, ensure_ascii=False)
        os.replace(f + ".tmp", f)
    if was is not None:
        # writing its files changed the folder's time: a renamed world is not a newer one (B75: its
        # card jumped to the front and the next card's Rename opened another world)
        try:
            os.utime(os.path.join(game.livecpk_dir, new), ns=(was.st_atime_ns, was.st_mtime_ns))
        except OSError:
            pass
    _save_info(folder, info)
    prune(sd, old, but=folder)
    return folder, info


def recipe_world(src, dst, old, new):
    """a recipe file (src) written to dst with its "world" key `new` in place of `old`, the rest
    byte for byte; False (nothing written) when it is not a file Project._write wrote.

    B66: a big world's recipe is 126 MB; json.load and json.dump of it for one key took seconds of
    a frozen window and 1.5 GB. Project._write writes it with indent=1, so a line with one space in
    front is a key of the recipe itself (a deeper one has two or more, and a JSON string has no
    line break in it): that one line changes"""
    try:
        with open(src, "rb") as f:
            raw = f.read()
    except OSError:
        return False
    at = b'\n "world": ' + json.dumps(old).encode("utf-8")
    i = raw.find(at)
    if i < 0 or raw.find(at, i + 1) >= 0 or raw[i + len(at):i + len(at) + 1] not in (b",", b"\r", b"\n", b""):
        return False
    with open(dst + ".tmp", "wb") as f:
        f.write(raw[:i])
        f.write(b'\n "world": ' + json.dumps(new).encode("utf-8"))
        f.write(memoryview(raw)[i + len(at):])
    os.replace(dst + ".tmp", dst)
    return True


def rename_recipe_copy(copies_dir, old, new):
    """the copy Build keeps of the world's recipe (recipes\\<world>.json, Project.keep_copy) under
    the new name, its "world" key with it; the new path, or None when there is none"""
    a, b = os.path.join(copies_dir, old + ".json"), os.path.join(copies_dir, new + ".json")
    if not os.path.isfile(a) or os.path.exists(b):
        return None
    if recipe_world(a, b, old, new):
        os.remove(a)
        return b
    with open(a, encoding="utf-8") as f:
        r = json.load(f)
    if r.get("world") == old:
        r["world"] = new
    with open(b + ".tmp", "w", encoding="utf-8") as f:
        json.dump(r, f, indent=1, ensure_ascii=False)
    os.replace(b + ".tmp", b)
    os.remove(a)
    return b
