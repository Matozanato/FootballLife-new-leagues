"""health checks of a game's mod setup, as (level, area, text, page) rows.

    level  "err" (the game will miss something), "warn" (probably not what you want), "ok"
    page   the section that fixes it (a page class name), or None

quick() is cheap enough for the overview; full() also reads every content-server map and the
end of sider.log.
"""
import os, re

from . import modules as MOD, servers as S
from .i18n import _
from .siderini import root_path

PAGE_OF = {"stadiums": "Stadiums", "balls": "Balls", "kits": "Kits", "commentary": "Commentary",
           "goalsongs": "Music"}
ERR_WORDS = re.compile(r"(error|failed|attempt to|not found|cannot|can't|unable|stack traceback)", re.I)


def quick(game, ini):
    out = []
    for p in game.problems():
        out.append(("err", "Game", p, "Settings"))
    if ini is None:
        return out
    roots = ini.entries("cpk.root")
    for e in roots:
        if e.enabled and not os.path.isdir(root_path(game.sider_dir, e.value)):
            out.append(("err", "Content folders", _("%s is switched on but the folder is missing") % e.value, "Roots"))
    seen = set()
    for e in roots:
        k = e.value.lower().replace("/", "\\")
        if e.enabled and k in seen:
            out.append(("warn", "Content folders", _("%s is switched on twice") % e.value, "Roots"))
        seen.add(k)
    for p in MOD.check_order(ini, game.modules_dir):
        en = p if isinstance(p, str) else p[0]
        text = _(p) if isinstance(p, str) else _(p[0]) % p[1:]
        out.append(("warn" if "twice" in en or "before" in en or "above" in en else "err",
                    "Lua modules", text, "Modules"))
    mods = {os.path.basename(e.value.replace("\\", "/")).lower(): e.enabled for e in ini.entries("lua.module")}
    for s in S.SERVERS:
        on = mods.get(s.module.lower())
        if on and not s.installed(game.content_dir):
            out.append(("err", s.title, _("%s is on but there is no content\\%s folder") % (s.module, s.folder), None))
    return out


def map_problems(game):
    """content-server map lines that point at a folder or file that is not in the library"""
    out = []
    for s in S.SERVERS:
        if not s.library or not s.installed(game.content_dir):
            continue
        lib = {S.norm_item(p) for p in S.library(s.path(game.content_dir), s.library)}
        for m in s.maps:
            mf = m.open(s.path(game.content_dir))
            items = [i for i, c in enumerate(m.cols) if c.kind == "item"]
            bad = 0
            first = None
            for r in mf.rows():
                if not r.enabled:
                    continue
                for i in items:
                    v = r.fields[i] if i < len(r.fields) else ""
                    if v and S.norm_item(v) not in lib:
                        bad += 1
                        first = first or v
            if bad:
                out.append(("warn", s.title, _("%s: %d line(s) point at items that are not in the library (e.g. %s)")
                            % (m.file, bad, first), PAGE_OF.get(s.key, "Servers")))
    return out


def log_problems(game, tail=4000):
    """error-looking lines at the end of sider.log: [(line number, text)]"""
    try:
        lines = open(game.log_path, encoding="utf-8", errors="replace").read().splitlines()
    except OSError:
        return []
    start = max(0, len(lines) - tail)
    return [(i + 1, l) for i, l in enumerate(lines[start:], start) if ERR_WORDS.search(l)]


def full(game, ini):
    out = quick(game, ini)
    out += map_problems(game)
    return out
