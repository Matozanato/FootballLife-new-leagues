"""Where Sider lives in a game folder.

Sider usually sits next to FL_2026.exe as SiderAddons, but it runs from a folder of any name
("sider", "Sider 7.4" ...), and some players keep several side by side, each set up
differently -- or one level further down, one folder holding a few Sider copies
(sider\\patch 1, sider\\patch 2 ...). What makes a folder Sider's is the sider.ini in it, so that
is what is looked for.

    candidates(game)  the folders in the game folder, or one level below, that hold a sider.ini,
                      as paths relative to the game folder ("SiderAddons", "sider\\patch 1")
    find(game)        the one to use: PREFERRED (set by Mod Studio from its settings) when it
                      holds a sider.ini, else SiderAddons, else the first one found; with none,
                      <game>\\SiderAddons, the usual place, so messages and installs still name it
    name(game, path)  a Sider folder as candidates() names it
"""
import os

DEFAULT = "SiderAddons"
PREFERRED = None                # a folder in the game folder, relative to it, or None


def _dirs(path):
    try:
        return [n for n in os.listdir(path) if os.path.isdir(os.path.join(path, n))]
    except OSError:
        return []


def _has_ini(path):
    return os.path.isfile(os.path.join(path, "sider.ini"))


def candidates(game):
    """the folders in `game` (or one level below) that hold a sider.ini, relative to `game`,
    SiderAddons first. A folder that holds a sider.ini itself is not looked into: its
    subfolders are Sider's own (modules, livecpk ...)."""
    out = []
    for n in _dirs(game):
        top = os.path.join(game, n)
        if _has_ini(top):
            out.append(n)
            continue
        out += [os.path.join(n, m) for m in _dirs(top) if _has_ini(os.path.join(top, m))]
    out.sort(key=lambda n: (n.lower() != DEFAULT.lower(), n.lower()))
    return out


def _same(a, b):
    return os.path.normcase(os.path.normpath(a)) == os.path.normcase(os.path.normpath(b))


def find(game, preferred=None):
    """the Sider folder of `game` (a full path)"""
    pref = preferred or PREFERRED
    found = candidates(game) if game else []
    if pref:
        for n in found:
            if _same(n, pref):
                return os.path.join(game, n)
    return os.path.join(game or "", found[0] if found else DEFAULT)


def name(game, path):
    """`path` (a Sider folder) relative to `game`, the way candidates() names it"""
    try:
        return os.path.relpath(path, game) if game else os.path.basename(path)
    except ValueError:                  # another drive
        return os.path.basename(path)
