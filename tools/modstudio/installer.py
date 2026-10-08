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
import json, os, re, shutil, tempfile, time, zipfile

from . import servers as S
from .backups import home, snapshot
from .mapfile import MapFile
from .siderini import norm

GAME_DIRS = {"common", "asset", "download", "ui", "sound", "movie"}
SERVER_DIRS = {s.folder.lower(): s for s in S.SERVERS}
EXTRA_SERVERS = {"soundtrack-server", "turf-loader", "ui-colors", "fans-server", "ballboys_server",
                 "bibserver", "entrance", "stadium_tunnel", "stadium_banner", "stadium_board",
                 "stadium_cornerflag", "tournament_anth_tunnel", "whistle_ref", "custom-exhibition-match"}


WORLD_FILE = "fl26world.txt"             # the world file of a League Builder world
FACE_PACK = "fl26regen_faces.bin"        # Mod Studio's face pack; Install the modules puts it in modules
WORLD_README = "READ ME - FL26 world.txt"
WORLD_INFO = "fl26worldpack.json"
WORLD_NOTE = "a League Builder world: it is switched on, its world file goes to modules\\fl26world.txt"


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


def face_pack_missing(sider_dir):
    """True when Mod Studio's modules with the face pack are not in this Sider's modules folder"""
    mods = os.path.join(sider_dir, "modules")
    return not all(os.path.exists(os.path.join(mods, f)) for f in (FACE_PACK, "fl26regen.dll", "fl26regen.lua"))


README = """FL26 world: {world}

Install it with FL26 Mod Studio: Install mods > drop this zip > Install. Mod Studio copies
SiderAddons\\livecpk\\{world}, puts its world file (fl26world.txt) in SiderAddons\\modules
and switches the world on.

REQUIRED: FL26 Mod Studio's modules with the face pack (SiderAddons\\modules\\{pack}).
Install them once: League Builder > Build > 0. Install the modules (or Build and install).
{faces} new players of this world get a generated face from that pack: they are listed on
the newfaces / faceapp lines of fl26world.txt. Without the modules, or without
fl26world.txt in SiderAddons\\modules, every new player looks the same.

By hand: copy SiderAddons into the game folder, copy livecpk\\{world}\\fl26world.txt to
SiderAddons\\modules\\fl26world.txt, and put  cpk.root = ".\\livecpk\\{world}"  in
sider.ini above the other roots (with any other _FL26 world switched off).
"""


def export_world(sider_dir, world, out, log=lambda t: None):
    r"""zip the built world SiderAddons\livecpk\<world> for another PC, laid out as
    SiderAddons\livecpk\<world>\... so Install mods (or a copy by hand) puts it in place.

    The world folder holds fl26world.txt, the world file Switch on copies to modules: its
    "newfaces" / "faceapp" lines are the players who get a generated face.  The zip always
    carries it; when the folder's copy has no face lines but the live copy in modules (same
    world) has, the live one goes in.  A read-me and fl26worldpack.json say what the receiver
    needs: Mod Studio's modules with the face pack, or every new player looks the same.
    Returns the info written to fl26worldpack.json."""
    root = os.path.join(sider_dir, "livecpk", world)
    wf = os.path.join(root, WORLD_FILE)
    if not os.path.isfile(wf):
        raise ValueError("%s has no %s: build the world first" % (root, WORLD_FILE))
    live = os.path.join(sider_dir, "modules", WORLD_FILE)
    use = wf
    if face_players(wf) == 0 and world_name(live) == world and face_players(live) > 0:
        use = live
    faces = face_players(use)
    info = {"format": "fl26world", "format_version": 1, "world": world, "face_players": faces,
            "world_file": "SiderAddons/livecpk/%s/%s" % (world, WORLD_FILE),
            "needs": ["FL26 Mod Studio modules with the face pack (%s): League Builder > Build > "
                      "0. Install the modules" % FACE_PACK]}
    text = README.format(world=world, pack=FACE_PACK, faces=faces).replace("\n", "\r\n")
    part = out + ".part"
    n = 0
    with zipfile.ZipFile(part, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(WORLD_README, text)
        z.writestr(WORLD_INFO, json.dumps(info, indent=1, ensure_ascii=False))
        for dp, dn, fn in os.walk(root):
            dn.sort()
            for f in sorted(fn):
                p = os.path.join(dp, f)
                rel = os.path.relpath(p, root).replace(os.sep, "/")
                if rel == ".modstudio":
                    continue
                z.write(use if rel == WORLD_FILE else p, "SiderAddons/livecpk/%s/%s" % (world, rel))
                n += 1
                if n % 2000 == 0:
                    log("%d files ..." % n)
    os.replace(part, out)
    log("wrote %s: %d files, %d players with generated faces" % (out, n, faces))
    return info


class Part:
    """one thing a mod brings"""

    def __init__(self, kind, src, name, server=None, note=""):
        self.kind, self.src, self.name, self.server, self.note = kind, src, name, server, note
        self.world_file = None            # a world: its fl26world.txt
        self.install = True
        self.warnings = []
        self.size = 0
        self.files = 0

    def __repr__(self):
        return "<%s %s %s>" % (self.kind, self.name, self.src)


def safe(name):
    return re.sub(r'[<>:"/\\|?*]+', "_", name).strip(" .") or "mod"


def unpack(src, work):
    """a folder to look at: the folder itself, or `src` unpacked into `work`"""
    low = src.lower()
    if os.path.isdir(src):
        return src
    if low.endswith(".zip"):
        with zipfile.ZipFile(src) as z:
            for m in z.infolist():
                target = os.path.normpath(os.path.join(work, m.filename))
                if not target.startswith(os.path.normpath(work)):
                    raise ValueError("unsafe path in the zip: %s" % m.filename)
            z.extractall(work)
        return work
    if low.endswith(".7z"):
        try:
            import py7zr
        except ImportError:
            raise ValueError("7z archives need py7zr; unpack it yourself and install the folder")
        with py7zr.SevenZipFile(src, "r") as z:
            z.extractall(work)
        return work
    if low.endswith(".rar"):
        raise ValueError("unpack the .rar yourself (7-Zip, WinRAR) and install the folder it gives")
    if low.endswith((".lua", ".cpk", ".fl26pack", ".dll")):
        shutil.copy2(src, os.path.join(work, os.path.basename(src)))
        return work
    raise ValueError("not a mod this program knows: %s" % os.path.basename(src))


def lower_names(d):
    try:
        return {n.lower(): n for n in os.listdir(d)}
    except OSError:
        return {}


def is_root(d):
    return bool(set(lower_names(d)) & {"common", "asset"})


def measure(p):
    n = size = 0
    for dp, _dn, fn in os.walk(p):
        for f in fn:
            n += 1
            try:
                size += os.path.getsize(os.path.join(dp, f))
            except OSError:
                pass
    return n, size


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
        p = Part("root", d, safe(name))
        if os.path.isdir(os.path.join(d, "common", "etc", "pesdb")) or \
                os.path.isdir(os.path.join(d, "common", "etc")) and \
                any(n.lower().endswith(".bin") for n in os.listdir(os.path.join(d, "common", "etc"))):
            p.warnings.append("it replaces the game's database (common\\etc\\pesdb): leagues, clubs "
                              "and players. It will fight with a League Builder world; keep it below it.")
        parts.append(p)

    def visit_content(d, s=None):
        base = os.path.basename(d).lower()
        s = s or SERVER_DIRS.get(base)
        folder = s.folder if s else os.path.basename(d)
        parts.append(Part("content", d, folder, server=s.key if s else None,
                          note="" if s else "copied as it is (no map files to merge)"))

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


def _save(sider_dir, rows):
    p = db_path(sider_dir)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=1, ensure_ascii=False)
    os.replace(p + ".tmp", p)


class Installer:
    """install the chosen parts of one mod; `rec` is what removal needs"""

    def __init__(self, game, ini, name, log=lambda t: None, replace_lines=True):
        self.game, self.ini, self.name, self.log = game, ini, name, log
        self.replace_lines = replace_lines
        self.rec = {"name": name, "time": time.strftime("%Y%m%d-%H%M%S"), "created": [], "replaced": [],
                    "ini": [], "map_added": {}, "map_removed": {}, "parts": []}
        self.sd = game.sider_dir

    def rel(self, p):
        return os.path.relpath(p, self.sd)

    def copy_file(self, src, dst):
        if os.path.exists(dst):
            if os.path.getsize(dst) == os.path.getsize(src) and open(dst, "rb").read() == open(src, "rb").read():
                return
            b = snapshot(dst, "replaced by %s" % self.name, self.sd)
            self.rec["replaced"].append([self.rel(dst), self.rel(b)])
        else:
            self.rec["created"].append(self.rel(dst))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)

    def copy_tree(self, src, dst, skip=()):
        for dp, _dn, fn in os.walk(src):
            for f in fn:
                s = os.path.join(dp, f)
                r = os.path.relpath(s, src)
                if r.lower() in skip:
                    continue
                self.copy_file(s, os.path.join(dst, r))

    def run(self, parts, root_where="top"):
        for p in parts:
            if not p.install:
                continue
            self.log("%s: %s" % (p.kind, p.name))
            getattr(self, "do_" + p.kind)(p, root_where)
            self.rec["parts"].append([p.kind, p.name])
        rows = records(self.sd)
        rows.append(self.rec)
        _save(self.sd, rows)
        return self.rec

    def do_root(self, p, where):
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
            self.rec["created"].append(self.rel(mark))
        value = ".\\livecpk\\" + os.path.basename(dst)
        if not any(norm(e.value) == norm(value) for e in self.ini.entries("cpk.root")):
            # the first root listed wins; a mod that replaces the database goes last
            self.ini.add("cpk.root", value, where="first" if where == "top" and not p.warnings else None)
            self.rec["ini"].append(["cpk.root", value])

    def do_world(self, p, where):
        """a League Builder world: the folder under its own name (Switch on and the modules look
        for livecpk\\<world>), and its world file into modules, where the modules read it"""
        dst = os.path.join(self.game.livecpk_dir, p.name)
        if os.path.exists(dst) and not os.path.exists(os.path.join(dst, ".modstudio")):
            raise ValueError("a world called %s is in livecpk already (built on this PC?): remove or "
                             "rename that folder first" % p.name)
        self.copy_tree(p.src, dst)
        own = os.path.join(dst, WORLD_FILE)
        if p.world_file and not os.path.exists(own):
            self.copy_file(p.world_file, own)
        mark = os.path.join(dst, ".modstudio")
        if not os.path.exists(mark):
            with open(mark, "w", encoding="utf-8") as f:
                f.write(self.name)
            self.rec["created"].append(self.rel(mark))
        value = ".\\livecpk\\" + p.name
        if not self.ini.find("cpk.root", value):
            self.ini.add("cpk.root", value, where="first")
            self.rec["ini"].append(["cpk.root", value])
        # the copy the modules read; Switch on makes the same one, this one is undone on removal
        self.copy_file(own, os.path.join(self.game.modules_dir, WORLD_FILE))
        self.rec["world"] = p.name
        self.rec["face_players"] = face_players(own)

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
        dst = os.path.join(self.game.content_dir, p.name)
        s = S.BY_KEY.get(p.server) if p.server else None
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
                self.merge_map(m, src, os.path.join(dst, m.file))

    def merge_map(self, m, src, dst):
        theirs = MapFile(src, width=m.width, sep=m.sep, quote=m.quote)
        if not os.path.exists(dst):
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


def uninstall(game, ini, rec, log=lambda t: None):
    """undo one record; returns notes about what could not be undone"""
    sd, notes = game.sider_dir, []
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
        p = os.path.join(sd, rel)
        try:
            os.remove(p)
        except OSError:
            if os.path.exists(p):
                notes.append("could not delete %s" % rel)
    for rel, copy in rec.get("replaced", []):
        try:
            shutil.copy2(os.path.join(sd, copy), os.path.join(sd, rel))
        except OSError:
            notes.append("could not put back %s" % rel)
    # empty folders the mod made
    for rel in sorted({os.path.dirname(r) for r in rec.get("created", [])}, key=len, reverse=True):
        d = os.path.join(sd, rel)
        while d.startswith(sd) and len(d) > len(sd):
            try:
                os.rmdir(d)
            except OSError:
                break
            d = os.path.dirname(d)
    rows = [r for r in records(sd) if not (r["name"] == rec["name"] and r["time"] == rec["time"])]
    _save(sd, rows)
    return notes
