"""Where Sider lives in a game folder.

Sider usually sits next to FL_2026.exe as SiderAddons, but it runs from a folder of any name
("sider", "Sider 7.4" ...), and some players keep several side by side, each set up
differently. What makes a folder Sider's is the sider.ini in it, so that is what is looked for.

    candidates(game)  the folders directly in the game folder that hold a sider.ini
    find(game)        the one to use: PREFERRED (set by Mod Studio from its settings) when it
                      holds a sider.ini, else SiderAddons, else the first one found; with none,
                      <game>\\SiderAddons, the usual place, so messages and installs still name it
"""
import os

DEFAULT = "SiderAddons"
PREFERRED = None                # a folder name in the game folder, or None


def candidates(game):
    """names of the folders in `game` that hold a sider.ini, SiderAddons first"""
    try:
        names = os.listdir(game)
    except OSError:
        return []
    names.sort(key=lambda n: (n.lower() != DEFAULT.lower(), n.lower()))
    return [n for n in names if os.path.isfile(os.path.join(game, n, "sider.ini"))]


def find(game, preferred=None):
    """the Sider folder of `game` (a full path)"""
    pref = preferred or PREFERRED
    found = candidates(game) if game else []
    if pref and pref in found:
        return os.path.join(game, pref)
    return os.path.join(game or "", found[0] if found else DEFAULT)
