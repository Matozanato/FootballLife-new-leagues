"""content folders (cpk.root): what each holds, and which one wins for a file.

Sider looks a file up in the cpk.root folders in the order sider.ini lists them and stops at
the first folder that has it, so of two folders with the same file the higher one wins.  Only
the switched-on folders take part.

    idx = scan(sider_dir, ini)          # {root value: RootInfo}
    for c in conflicts(idx, ini):       # every file more than one live folder has
        print(c.path, "wins:", c.winner, "hidden:", c.losers)
"""
import os, time
from .siderini import norm, root_path


class RootInfo:
    __slots__ = ("value", "path", "exists", "files", "size", "kinds", "scanned")

    def __init__(self, value, path):
        self.value, self.path = value, path
        self.exists = os.path.isdir(path)
        self.files, self.size, self.kinds, self.scanned = {}, 0, {}, 0.0


# what a file is, by where it sits in common\... (for the "what does this folder change" column)
KINDS = [
    ("common\\character0\\model\\character\\face", "faces"),
    ("common\\character0\\model\\character\\boots", "boots"),
    ("common\\character0\\model\\character\\glove", "gloves"),
    ("common\\character0\\model\\character\\uniform", "kits"),
    ("common\\character0\\model\\character", "player models"),
    ("common\\character1", "player models"),
    ("common\\render\\symbol\\flag", "logos and flags"),
    ("common\\render\\symbol\\team", "crests"),
    ("common\\render\\symbol", "logos and flags"),
    ("common\\render\\thumbnail", "thumbnails"),
    ("common\\etc\\pesdb", "database"),
    ("common\\etc", "game data"),
    ("common\\sound", "sound"),
    ("common\\bg\\model\\ball", "balls"),
    ("common\\bg", "stadiums and pitch"),
    ("common\\demo", "cut scenes"),
    ("common\\script", "scripts"),
    ("common\\menu", "menus"),
    ("common\\ui", "menus"),
    ("common\\font", "fonts"),
    ("asset\\model\\bg", "stadiums and pitch"),
    ("asset\\model\\character", "player models"),
    ("asset", "models"),
    ("dt", "game data"),
]


def kind_of(rel):
    r = rel.lower()
    for pre, k in KINDS:
        if r.startswith(pre):
            return k
    return "other"


def walk(path):
    """{relative path (lower case, backslashes): size} -- scandir, whose sizes come free on
    Windows with the directory listing (a 32,000-file folder in a fraction of a second)"""
    out, stack = {}, [(path, "")]
    while stack:
        d, rel = stack.pop()
        try:
            items = list(os.scandir(d))
        except OSError:
            continue
        for e in items:
            r = e.name if not rel else rel + "\\" + e.name
            try:
                if e.is_dir(follow_symlinks=False):
                    stack.append((e.path, r))
                else:
                    out[r.lower()] = e.stat().st_size
            except OSError:
                pass
    return out


def scan_root(path, value=None):
    info = RootInfo(value or path, path)
    if not info.exists:
        return info
    t = time.time()
    info.files = walk(path)
    for key, sz in info.files.items():
        info.size += sz
        k = kind_of(key)
        info.kinds[k] = info.kinds.get(k, 0) + 1
    info.scanned = time.time() - t
    return info


def scan(sider_dir, ini, only_enabled=False, progress=None):
    """{normalised root value: RootInfo} for every cpk.root line (on and off)"""
    out = {}
    roots = ini.entries("cpk.root")
    for n, e in enumerate(roots):
        if only_enabled and not e.enabled:
            continue
        k = norm(e.value)
        if k in out:
            continue
        out[k] = scan_root(root_path(sider_dir, e.value), e.value)
        if progress:
            progress(n + 1, len(roots), e.value)
    return out


class Conflict:
    __slots__ = ("path", "winner", "losers")

    def __init__(self, path, winner, losers):
        self.path, self.winner, self.losers = path, winner, losers


def conflicts(idx, ini):
    """files that more than one switched-on folder has, in Sider's order"""
    order = [norm(e.value) for e in ini.entries("cpk.root") if e.enabled]
    seen, owner = set(), {}
    live = []
    for k in order:
        if k in seen or k not in idx:
            continue
        seen.add(k)
        live.append(k)
    for k in live:
        for f in idx[k].files:
            owner.setdefault(f, []).append(k)
    return [Conflict(f, ks[0], ks[1:]) for f, ks in sorted(owner.items()) if len(ks) > 1]


def summary(conf):
    """{(winner, loser): count} -- the folder-to-folder view of the conflicts"""
    out = {}
    for c in conf:
        for l in c.losers:
            out[(c.winner, l)] = out.get((c.winner, l), 0) + 1
    return out


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return ("%d %s" % (n, unit)) if unit == "B" else ("%.1f %s" % (n, unit))
        n /= 1024.0
