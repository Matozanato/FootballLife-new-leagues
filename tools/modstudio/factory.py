"""Put Sider back as it was before Mod Studio, in one go (0.2.4, the maintainer, 14.10.: "people
must be able to put Sider back to how it was before Mod Studio with one click").

Every file Mod Studio changed goes back to the oldest copy it kept of it: a restore point
(SiderAddons\\ModStudio\\backups; since 0.2.4 Build keeps its copies there too, the first one
marked "before"), or on an older install a <file>.before-builder next to it, or
modules\\before-builder-<n>.
What Mod Studio brought in (its modules, the face pack, the worlds, the mods installed with
it) is taken out. Nothing is deleted: all of it, and every file as it was just before, is
moved into SiderAddons\\ModStudio\\reset-<time>, with a list (reset.json) that undo() follows
to put it all back. The game's own files and the saves are not touched.
"""
import json, os, shutil, time

from . import backups, installer as I

BB = ".before-builder"
SKIP = ("livecpk", backups.HOME.lower())        # not walked for .before-builder copies


def _stamp_epoch(t):
    try:
        return time.mktime(time.strptime(t[:15], "%Y%m%d-%H%M%S"))
    except (ValueError, TypeError):
        return 0.0


def _ctime(p):
    try:
        return os.path.getctime(p)
    except OSError:
        return 0.0


def _key(rel):
    return os.path.normcase(os.path.normpath(rel))


def _walk(sd):
    """SiderAddons without livecpk and Mod Studio's own folder: (folder, subfolders, files)"""
    for top, dirs, files in os.walk(sd):
        if top == sd:
            dirs[:] = [d for d in dirs if d.lower() not in SKIP]
        yield top, dirs, files


def originals(sd):
    """{key: (rel path, when, copy, before)}: the oldest copy Mod Studio kept of each file it
    changed; before: there is a before-builder copy of it, so it was there before Mod Studio
    (a restore point alone may be of a file Mod Studio brought in itself)"""
    out = {}

    def offer(rel, when, copy, before=False):
        k = _key(rel)
        if k not in out or when < out[k][1]:
            out[k] = (rel, when, copy, before or (k in out and out[k][3]))
        elif before:
            out[k] = out[k][:3] + (True,)

    for r in backups.load(sd):
        if _key(r["file"]).startswith(_key(backups.HOME) + os.sep):
            continue
        c = os.path.join(sd, r["copy"])
        if os.path.isfile(c):
            # a copy Build takes now instead of a .before-builder next to the file (backups.before_change,
            # mato 15.10.) says the same: the file was there before Mod Studio changed it
            offer(r["file"], _stamp_epoch(r.get("time", "")), c, bool(r.get("before")))
    for top, dirs, files in _walk(sd):
        for f in files:
            if f.endswith(BB):
                p = os.path.join(top, f)
                offer(os.path.relpath(p[:-len(BB)], sd), _ctime(p), p, True)
        for d in [d for d in dirs if d.startswith("before-builder-")]:
            dirs.remove(d)
            kept = os.path.join(top, d)
            for f in os.listdir(kept):
                p = os.path.join(kept, f)
                if os.path.isfile(p):
                    offer(os.path.relpath(os.path.join(top, f), sd), _ctime(p), p, True)
    return out


def _ours_created(game):
    """what Mod Studio brought in: rel paths in SiderAddons, and the worlds among them"""
    sd, out = game.sider_dir, []
    import leaguebuilder as B
    try:
        pack = B.pack_dir()
        mods = [f for f in os.listdir(os.path.join(pack, "modules"))
                if os.path.isfile(os.path.join(pack, "modules", f))]
        lc = os.path.join(pack, "livecpk")
        roots = os.listdir(lc) if os.path.isdir(lc) else []
    except Exception:                             # no pack next to the program
        mods, roots = [], []
    mods = set(mods) | {m + ".lua" for m in B.retired_modules()} | {B.MARK, B.MARK + ".prev", B.OFF_FILE}
    out += [os.path.join("modules", f) for f in sorted(mods)]
    out += [os.path.join("livecpk", r) for r in roots]
    worlds = []
    if os.path.isdir(game.livecpk_dir):
        for w in sorted(os.listdir(game.livecpk_dir)):
            d = os.path.join(game.livecpk_dir, w)
            if os.path.isfile(os.path.join(d, B.MARK)) or os.path.exists(os.path.join(d, ".modstudio")):
                worlds.append(w)
                out.append(os.path.join("livecpk", w))
                wm = os.path.join(d, "modules")          # a world's own modules, copied in by Switch on
                out += [os.path.join("modules", f) for f in (os.listdir(wm) if os.path.isdir(wm) else [])
                        if os.path.isfile(os.path.join(wm, f))]
    # a world's own folders in the content servers' libraries (the kits made for its clubs)
    if worlds and os.path.isdir(game.content_dir):
        for lib in os.listdir(game.content_dir):
            for w in worlds:
                if os.path.isdir(os.path.join(game.content_dir, lib, w)):
                    out.append(os.path.relpath(os.path.join(game.content_dir, lib, w), sd))
    for rec in I.records(sd):
        out += rec.get("created", [])
    # the copies Mod Studio left next to the files go too: the reset folder keeps them
    for top, dirs, files in _walk(sd):
        out += [os.path.relpath(os.path.join(top, f), sd) for f in files if f.endswith((BB, ".prev"))]
        for d in [d for d in dirs if d.startswith("before-builder-")]:
            dirs.remove(d)
            out.append(os.path.relpath(os.path.join(top, d), sd))
    seen, uniq = set(), []
    for rel in out:
        if _key(rel) not in seen and os.path.exists(os.path.join(sd, rel)):
            seen.add(_key(rel))
            uniq.append(rel)
    return uniq, worlds


def ours(rel):
    """a module file of Mod Studio's own (modules\\fl26...)"""
    parts = _key(rel).split(os.sep)
    return len(parts) == 2 and parts[0] == "modules" and parts[1].startswith("fl26")


def clean_ini(path, gone_roots, log=lambda t: None):
    """sider.ini after the reset: no line of Mod Studio's left (its module lines and block, a
    content folder of a world or the face pack that went out), even when the oldest copy kept
    already had some (a Mod Studio older than the restore points); every other line as it is"""
    import leaguebuilder as B
    raw = open(path, "rb").read()
    text = raw.decode("utf-8-sig", "replace")
    nl = "\r\n" if "\r\n" in text else "\n"
    gone = {g.lower() for g in gone_roots}
    keep, dropped = [], 0
    for line in text.splitlines():
        s = line.strip().lstrip(";#").strip()
        name = B.module_of(line)[0]
        root = ""
        if s.replace(" ", "").lower().startswith("cpk.root="):
            root = os.path.basename(os.path.normpath(s.split("=", 1)[1].split(";")[0].strip().strip('"'))).lower()
        if (name and name.startswith("fl26")) or root in gone or line.strip() in (B.OURS_HEAD, B.OURS_END) \
                or ("fl26" in s.lower() and line.strip().startswith(";") and "lua.module" not in s and "cpk.root" not in s
                    and "mod studio" in s.lower()):
            dropped += 1
            continue
        keep.append(line)
    if dropped:
        with open(path + ".tmp", "wb") as f:
            f.write((b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b"") + (nl.join(keep) + nl).encode("utf-8"))
        os.replace(path + ".tmp", path)
        log("sider.ini: %d line(s) of Mod Studio taken out" % dropped)
    return dropped


def plan(game):
    """what reset() would do: files that go back ("back"), things taken out ("out"), the worlds
    and the installed mods among them"""
    sd = game.sider_dir
    orig = originals(sd)
    out, worlds = _ours_created(game)
    # a module of ours (fl26...) was never there before Mod Studio: a copy of one is of an older
    # Mod Studio, it goes out. Any other file that was there before (a module of the same name
    # Mod Studio replaced) gets its own back; one Mod Studio brought in is taken out
    have = {_key(r) for r in out}
    for k, v in orig.items():
        if ours(v[0]) and k not in have and os.path.exists(os.path.join(sd, v[0])):
            out.append(v[0])
    out = [r for r in out if ours(r) or not (_key(r) in orig and orig[_key(r)][3])]
    gone = {_key(r) for r in out}
    inside = tuple(k + os.sep for k in gone)      # a file in a folder that goes out goes with it

    def going(k):
        return k in gone or k.startswith(inside)
    back = sorted((v[0] for k, v in orig.items() if not going(k) and not ours(v[0])), key=str.lower)
    return {"back": back, "out": out, "worlds": worlds, "orig": orig,
            "mods": [r.get("name", "") for r in I.records(sd)]}


class _Mover:
    """moves things into the reset folder and writes down how to put them back"""

    def __init__(self, sd):
        self.sd = sd
        self.dir = os.path.join(backups.home(sd), "reset-" + time.strftime("%Y%m%d-%H%M%S"))
        os.makedirs(self.dir)
        self.rows = []

    def aside(self, rel):
        src = os.path.join(self.sd, rel)
        dst = os.path.join(self.dir, "files", rel)
        if not os.path.exists(src) or os.path.exists(dst):
            return
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
        self.rows.append({"path": rel, "kept": os.path.relpath(dst, self.sd)})

    def put(self, copy, rel):
        """the original copy goes to rel; what is there now is kept first"""
        dst = os.path.join(self.sd, rel)
        tmp = os.path.join(self.dir, "orig.tmp")
        shutil.copy2(copy, tmp)                   # the copy itself may be moved aside later
        if os.path.exists(dst):
            self.aside(rel)
        else:
            self.rows.append({"path": rel, "new": True})
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(tmp, dst)

    def save(self, note):
        with open(os.path.join(self.dir, "reset.json"), "w", encoding="utf-8") as f:
            json.dump({"time": time.strftime("%Y%m%d-%H%M%S"), "note": note, "rows": self.rows},
                      f, indent=1, ensure_ascii=False)


def reset(game, log=lambda t: None):
    """put Sider back as it was before Mod Studio; returns the reset folder (undo() takes it)"""
    sd = game.sider_dir
    p = plan(game)
    m = _Mover(sd)
    try:
        for rel in p["back"]:
            m.put(p["orig"][_key(rel)][2], rel)
            log("back as before Mod Studio: %s" % rel)
        for rel in p["out"]:
            m.aside(rel)
            log("taken out: %s" % rel)
        ini = os.path.join(sd, "sider.ini")
        if os.path.exists(ini):
            if not any(r["path"].lower() == "sider.ini" for r in m.rows):
                m.put(ini, "sider.ini")           # kept as it is now, for undo
            clean_ini(ini, [os.path.basename(r) for r in p["out"] if _key(r).startswith("livecpk" + os.sep)], log)
        if os.path.exists(I.db_path(sd)):         # the list of installed mods: they are out now
            m.aside(os.path.relpath(I.db_path(sd), sd))
        for rel in sorted({os.path.dirname(r["path"]) for r in m.rows if r["path"]}, key=len, reverse=True):
            d = os.path.join(sd, rel)             # folders a mod made, empty now
            while rel and _key(d) != _key(sd) and os.path.isdir(d) and not os.listdir(d):
                os.rmdir(d)
                m.rows.append({"path": os.path.relpath(d, sd), "dir": True})
                d = os.path.dirname(d)
    finally:
        m.save("%d file(s) back, %d taken out" % (len(p["back"]), len(p["out"])))
    return m.dir


def resets(sider_dir):
    """the reset folders that can still be undone, newest first"""
    h = os.path.join(sider_dir, backups.HOME)
    if not os.path.isdir(h):
        return []
    return sorted((os.path.join(h, d) for d in os.listdir(h)
                   if d.startswith("reset-") and os.path.isfile(os.path.join(h, d, "reset.json"))), reverse=True)


def undo(sider_dir, folder, log=lambda t: None):
    """put back what reset() moved: Sider is as it was just before the reset"""
    with open(os.path.join(folder, "reset.json"), encoding="utf-8") as f:
        rows = json.load(f)["rows"]
    for r in reversed(rows):
        p = os.path.join(sider_dir, r["path"])
        if r.get("dir"):
            os.makedirs(p, exist_ok=True)
            continue
        if os.path.isdir(p) and not os.path.islink(p):
            shutil.rmtree(p)
        elif os.path.exists(p):
            os.remove(p)
        if not r.get("new"):
            os.makedirs(os.path.dirname(p), exist_ok=True)
            shutil.move(os.path.join(sider_dir, r["kept"]), p)
        log("put back: %s" % r["path"])
    os.replace(folder, os.path.join(os.path.dirname(folder), "undone-" + os.path.basename(folder)))
