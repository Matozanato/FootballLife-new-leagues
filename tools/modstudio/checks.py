"""health checks of a game's mod setup, as (level, area, text, page) rows.

    level  "err" (the game will miss something), "warn" (probably not what you want), "ok"
    page   the section that fixes it (a page class name), or None

quick() is cheap enough for the overview; full() also reads every content-server map and the
end of sider.log. Both check the League Builder world that is switched on (world_problems), with
the recipe being edited when it is that world's.
"""
import json, os, re

from . import modules as MOD, servers as S
from .i18n import _
from .siderini import root_path

PAGE_OF = {"stadiums": "Stadiums", "balls": "Balls", "kits": "Kits", "commentary": "Commentary",
           "goalsongs": "Music"}
ERR_WORDS = re.compile(r"(error|failed|attempt to|not found|cannot|can't|unable|stack traceback)", re.I)


def quick(game, ini, recipe=None):
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
    out += world_problems(game, ini, recipe)
    return out


UECL_REGS = (186, 187, 1210)      # the Conference League's league phase, knockout and its group
OLD_GROUPS = (2051, 2053)         # group B of the Champions League / Europa League: only in the
                                  # game's own format, which fl26swiss.dll cannot run (issue #33)
FIRST_OWN_REGION = 29             # regions 0-28 are the game's own, 29 and up the new countries'
UEFA_CODE = 2                     # Competition.bin +6, low three bits: the confederation


def old_confed_tops(d, leagues):
    """names of the top divisions of a new country outside Europe (a region 29 and up) with a
    division below them, whose competition row carries their continent's code: a world built by
    Mod Studio 0.1.3. In July the game keeps such a league out of the next season (its season-end
    filter wants UEFA for our regions), so from the second season on the country's divisions have
    no clubs and no matches. Builds since 0.1.3.1 keep that row UEFA (leaguebuilder, #33)"""
    import mkleague as M
    try:
        comp = M.load(os.path.join(d, "common", "etc", "pesdb"), "Competition.bin")
    except (OSError, ValueError):
        return []
    code = {comp[i * M.COMP + M.CID_OFF]: comp[i * M.COMP + M.FLAG_OFF] & 7
            for i in range(len(comp) // M.COMP)}
    above = {L.get("above") for L in leagues}
    return [L.get("name") or str(L["id"]) for L in leagues
            if (L.get("region") or 0) >= FIRST_OWN_REGION and L["id"] in above
            and code.get(L.get("cid"), UEFA_CODE) != UEFA_CODE]


def world_problems(game, ini, recipe=None):
    """the League Builder worlds switched on: leagues that send nobody to Europe (no uefa line of
    the world file names one of them), a Champions League / Europa League still in the game's
    groups of four (a world built with the Conference League off before issue #33), and a
    Conference League that is on -- in the recipe being edited when it is this world's, else in
    the plan the world was built from -- but missing from the world's tables"""
    out = []
    try:
        import fl26world
        import mkleague as M
    except ImportError:
        return out
    for e in ini.entries("cpk.root"):
        d = root_path(game.sider_dir, e.value)
        name = os.path.basename(os.path.normpath(d))
        wf = os.path.join(d, "fl26world.txt")
        if not e.enabled or not name.startswith("_FL26") or not os.path.exists(wf):
            continue
        try:
            leagues = fl26world.read_world(wf)[1]
            ids = {L["id"] for L in leagues}
            uefa = fl26world.read_uefa(wf)
        except (OSError, ValueError):
            continue
        stuck = old_confed_tops(d, leagues)
        if stuck:
            out.append(("err", "League Builder",
                        _("%s: %s was built by Mod Studio 0.1.3, so from the second season on the "
                          "divisions of that country have no clubs and no matches: build the world "
                          "again and start a new career") % (name, ", ".join(stuck)), "Build"))
        if ids and not any(u[0] in ids for u in uefa):
            out.append(("warn", "League Builder",
                        _("%s: your leagues send nobody to Europe (no European places in the world file)") % name,
                        "NewLeagues"))
        try:
            regs = M.load(os.path.join(d, "common", "etc", "pesdb"), "CompetitionRegulation.bin")
            have = {int.from_bytes(regs[i * M.REG + M.R_ID:i * M.REG + M.R_ID + 2], "little")
                    for i in range(len(regs) // M.REG)}
        except (OSError, ValueError):
            have = set()
        if any(r in have for r in OLD_GROUPS):
            out.append(("err", "League Builder",
                        _("%s: the Champions League and Europa League are still in groups of four, "
                          "which fl26swiss.dll cannot run (a world built with the Conference League "
                          "off in Mod Studio 0.1.3 or earlier): build the world again") % name, "Build"))
        if recipe is not None and recipe.get("world") == name:
            on = bool(recipe.get("uecl", True))
        else:
            try:
                with open(os.path.join(d, "leaguebuilder-plan.json"), encoding="utf-8") as f:
                    on = bool(json.load(f).get("uecl"))
            except (OSError, ValueError):
                on = False
        if not on:
            continue
        missing = [r for r in UECL_REGS if r not in have]
        if missing:
            out.append(("err", "League Builder",
                        _("%s: the Conference League is on, but its tables are missing (regulation %s): "
                          "build the world again") % (name, ", ".join(map(str, missing))), "Build"))
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


def full(game, ini, recipe=None):
    out = quick(game, ini, recipe)
    out += map_problems(game)
    return out
