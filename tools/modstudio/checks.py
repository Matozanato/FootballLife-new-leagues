"""health checks of a game's mod setup, as (level, area, text, page) rows.

    level  "err" (the game will miss something), "warn" (probably not what you want), "ok"
    page   the section that fixes it (a page class name), or None

quick() is cheap enough for the overview; full() also reads every content-server map and the
end of sider.log. Both check the League Builder world that is switched on (world_problems), with
the recipe being edited when it is that world's.
"""
import json, os, re
import bigjson

from . import modules as MOD, servers as S
from .i18n import _
from .siderini import root_path

PAGE_OF = {"stadiums": "Stadiums", "balls": "Balls", "kits": "Kits", "commentary": "Commentary",
           "goalsongs": "Music"}
ERR_WORDS = re.compile(r"(error|failed|attempt to|not found|cannot|can't|unable|stack traceback)", re.I)
REFUSED = re.compile(r"^\[([\w.-]+\.lua)\] [\w ]+: ABORTED")   # a module that found another exe
_refused = {}


def quick(game, ini, recipe=None):
    out = []
    for p in game.problems():
        out.append(("err", "Game", p, "Settings"))
    out += write_problems(game)
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
        folder, module = s.pick(game.content_dir)
        on = mods.get(module.lower())
        if on and not s.installed(game.content_dir):
            out.append(("err", s.title, _("%s is on but there is no content\\%s folder") % (module, folder), None))
    out += dll_problems(game, ini)
    out += world_problems(game, ini, recipe)
    out += exe_problems(game)
    return out


def write_problems(game):
    """the game folder Windows does not let Mod Studio write in (B14: a game under Program Files)"""
    from . import access
    d = access.blocked(game) if game.folder and os.path.isdir(game.folder) else None
    if d is None:
        return []
    return [("err", "Game", _("Windows does not let Mod Studio write in %s, so it cannot install, build or "
                              "switch anything on there. Restart Mod Studio as administrator (right-click "
                              "FL26ModStudio.exe > Run as administrator), or move the game out of Program "
                              "Files and choose the new folder in Settings.") % d, "Settings")]


def _pack_modules():
    """the modules folder of the pack this Mod Studio installs, None when there is none"""
    try:
        import leaguebuilder
        return os.path.join(leaguebuilder.pack_dir(), "modules")
    except Exception:
        return None


def _same_file(a, b):
    """are the two files the same, byte for byte. Read again only when one of them changed: the
    header asks for every module of the pack each time sider.ini is saved, on the window's thread
    (B479, 15.11.: 0.6 s and more of a stopped window right after Install)"""
    from . import filecache

    def read():
        try:
            if os.path.getsize(a) != os.path.getsize(b):
                return False
            with open(a, "rb") as x, open(b, "rb") as y:
                return x.read() == y.read()
        except OSError:
            return False
    return filecache.by_files("same_file", [a, b], read)


def dll_problems(game, ini):
    """the DLLs our switched-on modules load that are not in SiderAddons\\modules (B15: an
    antivirus quarantined them right after Install modules, and the game silently lacked the
    new leagues' draws and cups). A DLL is compared with the pack's only when its module's .lua
    is the pack's too (the same version installed): then other bytes mean a damaged copy."""
    try:
        import leaguebuilder as B
    except ImportError:
        return []
    mdir = game.modules_dir
    if not os.path.isdir(mdir):
        return []
    pack = None
    gone, changed = [], []
    for e in ini.entries("lua.module"):
        if not e.enabled or MOD.kind_of(e.value) != "core":
            continue
        lua = MOD.path_of(e.value, mdir)
        if not lua or not os.path.isfile(lua):
            continue
        from . import filecache
        names = filecache.by_files("dll-names", [lua], lambda: B.dll_names(lua))
        if not names:
            continue
        src = None
        if pack is None:
            pack = _pack_modules() or ""
        if pack and _same_file(lua, os.path.join(pack, os.path.basename(lua))):
            src = pack
        # (each DLL read whole, and the pack's copy: kept while none of the files changed, B480
        # round 2 -- Home's checks did this on the window's thread on every refresh)
        paths = [os.path.join(mdir, n) for n in names] + ([os.path.join(src, n) for n in names] if src else [])
        got = filecache.by_files("check-dlls", paths, lambda: B.check_dlls(mdir, names, src))
        if any(why == "blocked" for _f, why in got):     # (Windows let it be opened again: asked anew)
            filecache._KEPT.pop(("check-dlls", tuple(paths)), None)
        for f, why in got:
            (changed if why == "changed" else gone).append((f, os.path.basename(lua)))
    out = []
    for f, lua in gone:
        out.append(("err", "Lua modules",
                    _("%s is missing from %s (or Windows will not open it), but %s, which is switched on, needs "
                      "it: an antivirus probably removed it. Add the SiderAddons folder as an exclusion in your "
                      "antivirus, then Home > Install now again.") % (f, mdir, lua),
                    "Build"))
    for f, lua in changed:
        out.append(("warn", "Lua modules",
                    _("%s in %s is not the one Mod Studio installs with %s (empty or different): an "
                      "antivirus may have changed it. Add the SiderAddons folder as an exclusion in your "
                      "antivirus, then Home > Install now again.") % (f, mdir, lua),
                    "Build"))
    return out


def exe_problems(game):
    """our modules that refused the game's exe in the last game (ABORTED at the start of
    sider.log, which log_problems' tail does not reach). With fl26caps refused, new leagues push
    the game's own out of Select Team and the game crashes there (issue #62: a cracked exe)."""
    try:
        st = os.stat(game.log_path)
    except OSError:
        return []
    key = (game.log_path, st.st_mtime, st.st_size)
    if key not in _refused:
        import leaguebuilder as B
        mods, caps, lines = [], False, []
        try:
            with open(game.log_path, encoding="utf-8", errors="replace") as f:
                for l in f:
                    m = REFUSED.match(l)
                    if m and m.group(1) not in mods:
                        mods.append(m.group(1))
                    caps = caps or l.startswith("[fl26caps.lua]")
                    lines.append(l)
        except OSError:
            pass
        in_exe = B.refused_in_exe(lines, mods)
        _refused.clear()
        _refused[key] = (mods, caps and "fl26caps.lua" not in mods, in_exe)
    mods, caps_took, in_exe = _refused[key]
    if not mods:
        return []
    if caps_took:
        out = []
        if in_exe:
            out.append(("warn", "Game", _("%s found the game's FL_2026.exe already changed at its spot by "
                                          "another mod (ABORTED in sider.log), so that one fix of ours is off; "
                                          "the rest of Mod Studio's modules are in. Nothing to do unless the "
                                          "game crashes; then use the Steam FL_2026.exe "
                                          "(docs/developers/by-hand.md, step A6).") % ", ".join(in_exe), "Settings"))
        mods = [mod for mod in mods if mod not in in_exe]
        if not mods:
            return out
        # fl26caps checks thousands of the exe's bytes: when it took them, the exe is the one the
        # modules know, and the others refused bytes another line of ours had patched first -- an
        # old module still on, one twice, or ours out of order (B80, Yanis 16.10.)
        return [("err", "Game", _("%s refused bytes another module had already changed in the last game "
                                  "(ABORTED in sider.log), while fl26caps took the game's FL_2026.exe: "
                                  "sider.ini loads an old module of ours, one twice, or ours out of order. "
                                  "Home > Install now puts the lines right.") % ", ".join(mods), "Build")] + out
    return [("err", "Game", _("%s refused the game's FL_2026.exe in the last game (ABORTED in sider.log): it is "
                              "not the Steam build the modules know, or another mod changed it. New leagues then "
                              "hide the game's leagues in Select Team and the game crashes there. Use the Steam "
                              "FL_2026.exe (docs/developers/by-hand.md, step A6).") % ", ".join(mods), "Settings")]


UECL_REGS = (186, 187, 189, 1210) # the Conference League's league phase, knockout, play-off (mkeuropo) and its group
OLD_GROUPS = (2051, 2053)         # group B of the Champions League / Europa League: only in the
                                  # game's own format, which fl26swiss.dll cannot run (issue #33)
FIRST_OWN_REGION = 29             # regions 0-28 are the game's own, 29 and up the new countries'
UEFA_CODE = 2                     # Competition.bin +6, low three bits: the confederation
# The game counts its regulation records again after every load (0x1414bc0a0), and only the first
# 300: the array is sorted by id, so in a world with more rows the highest ids drop out -- the
# last ties of the two-legged European rounds (their round's id + 7168 and + 8192), of the
# Libertadores and AFC groups. register_all never enters them, so they get no matches: a play-off
# of 16 shows 7 ties and a qualifying round 6 (Discord 13.10., Micarodvzla22, the 0.2.1 Modpack
# world of 334 rows: "14 under its ties", "2 tie(s) without a winner"). fl26regs600 (0.2.2)
# makes the recount cover all 600 rows fl26caps gives the array.
RECOUNT_ROWS = 300
RECOUNT_MODULE = re.compile(r"^fl26regs(\d+)\.lua$")
# The number in the file name is not always the count: in an FL_2027.exe folder Install modules
# puts the FL 2027 copy (fl26regs1200 / fl26regs2000.fl27.lua) in under the plain name
# fl26regs600.lua (leaguebuilder.shipped_source), so the module's own `Set:     regs<N>` line
# (mkregs.py writes it) is what the game counts; the name only when the file cannot be read.
RECOUNT_SET = re.compile(r"^Set:\s+regs(\d+)\b", re.M)


def recount_of(ini, value, fallback):
    """the rows the regs module `value` (a lua.module line of `ini`) recounts: its Set line, read
    from SiderAddons\\modules, else `fallback` (the number in its name)"""
    if getattr(ini, "path", None):
        p = os.path.join(os.path.dirname(ini.path), "modules", value.replace("\\", os.sep).replace("/", os.sep))
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                m = RECOUNT_SET.search(f.read(4096))
            if m:
                return int(m.group(1))
        except OSError:
            pass
    return fallback


def recount_rows(ini):
    """how many regulation rows the game counts with the modules switched on in sider.ini"""
    n = RECOUNT_ROWS
    for e in ini.entries("lua.module"):
        m = RECOUNT_MODULE.match(os.path.basename(e.value.replace("\\", "/")).lower())
        if e.enabled and m:
            n = max(n, recount_of(ini, e.value, int(m.group(1))))
    return n


def old_confed_tops(d, leagues, calendar=()):
    """names of the leagues of a new country outside Europe (a region 29 and up) that plays August
    to May, whose competition row carries their continent's code: a world built by Mod Studio
    0.1.3, or by 0.1.3.1 for a league with no division below it. In July the game keeps such a
    league out of the next season (its season-end filter wants UEFA for our regions), so from the
    second season on it has no clubs and no matches. Builds since 0.1.4 keep that row UEFA
    (leaguebuilder); `calendar` holds the February-December regions, which keep their code"""
    import mkleague as M
    try:
        comp = M.load(os.path.join(d, "common", "etc", "pesdb"), "Competition.bin")
    except (OSError, ValueError):
        return []
    code = {M.comp_cid(comp, i * M.COMP): comp[i * M.COMP + M.FLAG_OFF] & 7
            for i in range(len(comp) // M.COMP)}
    return [L.get("name") or str(L["id"]) for L in leagues
            if (L.get("region") or 0) >= FIRST_OWN_REGION and L.get("region") not in calendar
            and code.get(L.get("cid"), UEFA_CODE) != UEFA_CODE]


DB_TABLES = ("Team.bin", "Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin")


def short_squads(d):
    """{team id: players} of the world's new clubs (the plan it was built from, leaguebuilder-plan.json)
    with fewer than lbplayers.MIN_SQUAD players in its PlayerAssignment.bin; {} when there is no
    plan or no player table. The game crashes when such a club is picked and Become a Legend does
    not start (B28: a Modpack world whose last 80 clubs got no placeholder squad)"""
    try:
        import lbplayers
        from . import filecache
        path = os.path.join(d, "leaguebuilder-plan.json")
        plan = filecache.json_file(path)
        tids = [t for p in plan.get("leagues") or [] for k, t in enumerate(p.get("teams") or [])
                if str(k) not in (p.get("game_clubs") or {})]
        if not tids:
            return {}
        db = os.path.join(d, "common", "etc", "pesdb")
        # 0.2.4: worked out again only when the world changes (Home took 4 s to open on the Modpack)
        return filecache.by_files("short_squads", [path] + [os.path.join(db, f) for f in
                                                            ("PlayerAssignment.bin", "Player.bin", "Team.bin")],
                                  lambda: lbplayers.short_squads(db, tids))
    except (ImportError, OSError, ValueError, TypeError, AttributeError):
        return {}


DRAWN_FNS = ("league_logo", "club_crest")   # the picture jobs whose empty picture Build draws
DRAWN_DIR = re.compile(r"(^|[\\/])drawn[^\\/]*[\\/]", re.I)   # a folder of our drawn pictures: drawn, drawn1111
LOGO_KEYS = ("logo", "cup_logo", "promo_logo")


def recipe_drawn(d):
    """[("recipe_crest" / "recipe_logo", team or competition id, name)] of the pictures the plan of
    the world's last Build (leaguebuilder-plan.json) takes from a folder of drawn ones (DRAWN_DIR):
    a crest or logo we drew ourselves and put in the recipe, which Build uses as any picture.
    [] without a plan"""
    try:
        with open(os.path.join(d, "leaguebuilder-plan.json"), encoding="utf-8") as f:
            plan = bigjson.load(f)
    except (OSError, ValueError):
        return []
    out = []
    for L in (plan.get("leagues") or []) + (plan.get("others") or []):
        if not isinstance(L, dict):
            continue
        teams, names = L.get("teams") or [], L.get("club_names") or []
        for k, p in enumerate(L.get("club_crests") or []):
            if isinstance(p, str) and DRAWN_DIR.search(p):
                out.append(("recipe_crest", teams[k] if k < len(teams) else None,
                            names[k] if k < len(names) else ""))
        for key in LOGO_KEYS:
            p = L.get(key)
            if isinstance(p, str) and DRAWN_DIR.search(p):
                out.append(("recipe_logo", L.get("cid"), "%s (%s)" % (L.get("name") or "", key)))
    return out


def drawn_pictures(d, shields_ok=False):
    """[(job, id, name)] of the logos and crests the world's last Build drew because it had no
    picture for them: the jobs of leaguebuilder-input.json (leaguebuilder.write_input) whose
    picture argument (leaguebuilder.PIC_ARG, "sha1:..." when there was one) is null. A job whose
    files are all in "gone" is not drawn: its picture is on the PC the recipe was made on, and the
    world keeps the one it has (keep_added). shields_ok: a club crest drawn as a shield in the
    colours of its kit counts as a picture (NewLife's new clubs; the GigaPack wants real crests,
    mato 11.11.). 14.11.2026: 62 play-offs of GigaPack beta 2 went out with a drawn emblem and no
    check saw it (logo-lanac-nalaz-1411.md).
    17.11.2026: also the drawn pictures the recipe itself points to (recipe_drawn): Build takes
    them as pictures, so the jobs never show them, and six drawn crests (clubs/crests/drawn1111)
    were still in the GigaPack after the check passed"""
    try:
        with open(os.path.join(d, "leaguebuilder-input.json"), encoding="utf-8") as f:
            last = bigjson.load(f)
    except (OSError, ValueError):
        last = {}                          # no record (a world built before Build wrote one): no jobs to tell
    gone = set(last.get("gone") or [])
    out = recipe_drawn(d)
    for job in last.get("jobs") or []:
        try:
            fn, args, rels = job
        except (TypeError, ValueError):
            continue
        if fn not in DRAWN_FNS or len(args) < 3 or args[2]:
            continue
        if rels and all(r in gone for r in rels):
            continue
        if fn == "club_crest" and shields_ok and len(args) > 3 and args[3]:
            continue
        out.append((fn, args[0], args[1]))
    return out


def club_names(db):
    """{team id: name} of the Team.bin in folder db, {} when there is none"""
    import fl26world
    import mkworld as W
    try:
        raw = fl26world.load(db, "Team.bin")            # packed or plain: a mod may ship either
    except (OSError, ValueError, AssertionError):
        return {}
    out = {}
    for o in range(0, len(raw) - W.T_REC + 1, W.T_REC):
        name = bytes(raw[o + W.T_NAME:o + W.T_NAME + W.T_NAME_LEN]).split(b"\0")[0]
        out[int.from_bytes(raw[o + W.T_ID:o + W.T_ID + 4], "little")] = name
    return out


def database_problems(game, ini, world, name, d):
    """a database mod (UML ...: a root of its own with Team.bin or competition tables) switched on
    with the world (GitHub #36, #54). Above the world in sider.ini its tables hide the world's: an
    empty league table, the new cups gone. Below it, the world's copy of the tables hides the
    mod's, which is right only when the world was built from that mod's tables (Settings > Use
    another tables folder): then every club of the mod is in the world under the same name."""
    out = []
    mine = None
    for e in ini.entries("cpk.root"):
        if not e.enabled or e.index == world.index:
            continue
        r = root_path(game.sider_dir, e.value)
        mod = os.path.basename(os.path.normpath(r))
        db = os.path.join(r, "common", "etc", "pesdb")
        if mod.startswith("_FL26") or not any(os.path.exists(os.path.join(db, f)) for f in DB_TABLES):
            continue
        if e.index < world.index:
            out.append(("err", "Your world in the game",
                        _("%s sits above your world %s in sider.ini and has its own database tables, which hide "
                          "the world's: empty league tables, the new cups missing. Build the world from %s's "
                          "tables (Settings > Use another tables folder...) and keep the world above it")
                        % (mod, name, mod), "Settings"))
            continue
        theirs = club_names(db)
        if not theirs:
            continue
        if mine is None:
            mine = club_names(os.path.join(d, "common", "etc", "pesdb"))
        off = [t for t, n in theirs.items() if mine.get(t) != n]
        if len(off) > max(10, len(theirs) // 50):
            out.append(("err", "Your world in the game",
                        _("%s was built from other tables than %s's (%d of its clubs are missing or named "
                          "differently in the world), so the world hides that database's leagues and clubs. "
                          "Point Settings > Use another tables folder... at %s's common\\etc\\pesdb and build "
                          "the world again") % (name, mod, len(off), mod), "Settings"))
    return out


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
        try:
            calendar = {int(ln.split()[1]) for ln in open(wf, encoding="utf-8")
                        if ln.startswith("season ") and len(ln.split()) > 2 and ln.split()[2] == "1"}
        except (OSError, ValueError):
            calendar = set()
        stuck = old_confed_tops(d, leagues, calendar)
        if stuck:
            out.append(("err", "Your world in the game",
                        _("%s: %s was built before Mod Studio 0.1.4, so from the second season on the "
                          "divisions of that country have no clubs and no matches: build the world "
                          "again and start a new career") % (name, ", ".join(stuck)), "Build"))
        if ids and not any(u[0] in ids for u in uefa):
            out.append(("warn", "Your world in the game",
                        _("%s: your leagues send nobody to Europe (no European places in the world file)") % name,
                        "NewLeagues"))
        try:
            regs = M.load(os.path.join(d, "common", "etc", "pesdb"), "CompetitionRegulation.bin")
            have = {int.from_bytes(regs[i * M.REG + M.R_ID:i * M.REG + M.R_ID + 2], "little")
                    for i in range(len(regs) // M.REG)}
        except (OSError, ValueError):
            have = set()
        counted = recount_rows(ini)
        if len(have) > counted:
            out.append(("err", "Lua modules",
                        _("%s has %d competition regulations, but the game counts only the first %d "
                          "without fl26regs600.lua: the last ties of the European rounds are never played "
                          "(a play-off of 16 shows 7 ties). Install the modules (Mod Studio 0.2.2 or "
                          "later) and start a new career") % (name, len(have), counted), "Modules"))
        if any(r in have for r in OLD_GROUPS):
            out.append(("err", "Your world in the game",
                        _("%s: the Champions League and Europa League are still in groups of four, "
                          "which fl26swiss.dll cannot run (a world built with the Conference League "
                          "off in Mod Studio 0.1.3 or earlier): build the world again") % name, "Build"))
        out += database_problems(game, ini, e, name, d)
        short = short_squads(d)
        if short:
            out.append(("err", "Your world in the game",
                        _("%s: %d club(s) have fewer than 18 players (ids %s): the game crashes when one is "
                          "picked and Become a Legend does not start. Build the world again")
                        % (name, len(short), ", ".join(str(t) for t in sorted(short)[:8])
                           + (" ..." if len(short) > 8 else "")), "Build"))
        if recipe is not None and recipe.get("world") == name:
            on = bool(recipe.get("uecl", True))
        else:
            try:
                from . import filecache
                on = bool(filecache.json_file(os.path.join(d, "leaguebuilder-plan.json")).get("uecl"))
            except (OSError, ValueError):
                on = False
        if not on:
            continue
        missing = [r for r in UECL_REGS if r not in have]
        if missing:
            out.append(("err", "Your world in the game",
                        _("%s: the Conference League is on, but its tables are missing (regulation %s): "
                          "build the world again") % (name, ", ".join(map(str, missing))), "Build"))
    return out


ADDED = re.compile(r"^#\s*-+\s*added by FL26 Mod Studio:\s*(.*?)\s*-*\s*$")   # installer.merge_map's heading
OURS = "FL26 Mod Studio:"                  # the end of a line Build or a world zip wrote (installer.OUR_LINE)


def map_problems(game):
    """content-server map lines that point at a folder or file that is not in the library; the
    lines a zip brought (Install mods' "added by" heading, or a world's own lines) are counted
    apart, per zip or world: an install that stopped half way leaves those (B29)"""
    from . import installer
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
            pack, of_pack, of_world = None, {}, {}
            for r in mf.items:
                if not hasattr(r, "fields"):
                    h = ADDED.match(r.strip())
                    if h:
                        pack = h.group(1)
                    continue
                if not r.enabled:
                    continue
                miss = [v for v in (r.fields[i] if i < len(r.fields) else "" for i in items)
                        if v and S.norm_item(v) not in lib]
                if not miss:
                    continue
                world = miss[0].replace("/", "\\").split("\\")[0] if OURS in r.comment else ""
                if pack:
                    of_pack[pack] = of_pack.get(pack, 0) + 1
                elif world.startswith("_FL26"):
                    of_world[world] = of_world.get(world, 0) + 1
                else:
                    bad += len(miss)
                    first = first or miss[0]
            for name, n in of_pack.items():
                out.append(("err", s.title, _("%s: %d line(s) that %s added point at files that are not there: "
                                              "its install did not finish. Install that zip again.")
                            % (m.file, n, name), "Install"))
            for world, n in of_world.items():
                if installer.ready_world(game, world):
                    out.append(("err", s.title, _("%s: %d line(s) of the world %s point at files that are not "
                                                  "there: its install did not finish. Install the world's zip again.")
                                % (m.file, n, world), "Install"))
                else:
                    out.append(("err", s.title, _("%s: %d line(s) of the world %s point at files that are not "
                                                  "there. Build it again.") % (m.file, n, world), "Build"))
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


_STATE = {}         # game folder: (_modules_sig, modules_state) as last worked out


def _modules_sig(game):
    """what modules_state() depends on, from a few folder listings: the files (name, size, time) of
    the pack's modules and of the game's, sider.ini, the pack's module list, livecpk's folders and
    the modules each world there brings, and which game it is. None when it cannot be told"""
    try:
        import leaguebuilder as B
        pack = B.pack_dir()
    except Exception:
        return None
    from . import filecache as F
    worlds = {}
    try:
        with os.scandir(game.livecpk_dir) as it:
            names = sorted(e.name for e in it if e.is_dir())
    except (OSError, AttributeError, TypeError):
        names = []
    for n in names:
        got = F.listed_stamps(os.path.join(game.livecpk_dir, n, "modules"))
        if got:
            worlds[n] = tuple(sorted(got.items()))
    try:
        return (pack, F.stamp(os.path.join(pack, "modules.txt")),
                tuple(sorted(F.listed_stamps(os.path.join(pack, "modules")).items())),
                tuple(sorted(os.listdir(os.path.join(pack, "livecpk")))) if os.path.isdir(os.path.join(pack, "livecpk")) else (),
                F.stamp(game.ini_path), tuple(sorted(F.listed_stamps(game.modules_dir).items())),
                tuple(names), tuple(sorted(worlds.items())), B.is_fl27(game.folder))
    except Exception:           # (a game object without one of these: not kept, worked out each time)
        return None


def modules_state(game):
    """Mod Studio's own modules on this PC, for the one line Home and Lua modules show (0.2.4:
    people could not tell whether they had them, or the right version):
        {"missing": [...], "changed": [...], "off": [...], "left_off": [...], "total": n}
    missing  a file of the pack not in the modules folder of SiderAddons (or a face pack folder not in livecpk)
    changed  one there that is not the pack's: an older version, or damaged
    off      a module of the pack sider.ini does not load
    left_off an optional one the player switched off on purpose (not a problem)
    None when there is no pack or no Sider folder to compare with.

    Worked out again only when one of the files it looks at changed (_modules_sig: a few folder
    listings). B480 (17.11.2026): the header asks on every sider.ini save and content change, on the
    window's thread, and each time it asked the disk about every file of the pack and of the game
    (and read the changed ones): 1.25 s of a stopped window right after Install the modules and most
    of a 4 s stop after Make it editable in the exe test of beta4p. The workers that change the
    modules (Install the modules, a world's install, Build) work it out before they end"""
    sig = _modules_sig(game)
    got = _STATE.get(game.folder)
    if sig is not None and got is not None and got[0] == sig:
        return got[1]
    out = _modules_state(game)
    if sig is not None:
        _STATE[game.folder] = (sig, out)
    return out


def warm_modules(game):
    """from a worker, at the end of a job that changed the modules or sider.ini: modules_state and
    what checks.quick reads of the modules (modules.links) worked out here, so the window's thread
    finds them kept"""
    try:
        modules_state(game)
        from .siderini import SiderIni
        ini = SiderIni.load(game.ini_path)
        dll_problems(game, ini)             # (the module files and DLLs it compares, read here)
        for e in ini.entries("lua.module"):
            p = MOD.path_of(e.value, game.modules_dir)
            if p and os.path.exists(p):
                MOD.links(p)
    except Exception:
        pass


def _modules_state(game):
    try:
        import leaguebuilder as B
        pack = B.pack_dir()
        order = open(os.path.join(pack, "modules.txt"), encoding="utf-8").read().split()
        _ini, lines = B.ini_lines(game.folder)
    except Exception:
        return None
    mdir, src = game.modules_dir, os.path.join(pack, "modules")
    if not os.path.isdir(mdir) or not os.path.isdir(src):
        return None
    files = B.shipped_files(src)
    # B177 (Vran 20.10.): the modules a world brings (fl26regions, fl26regnames: in the load order,
    # not in the pack) count only when the world in the game has them, against its copies -- Home
    # said "switched off" with no world that needs them, and Install now had nothing to put in
    brought = B.world_modules(game.folder)
    per_world = {m for m in order if m + ".lua" not in files}
    order = [m for m in order if m not in per_world or m in brought]
    out = {"missing": [], "changed": [], "off": [], "left_off": [], "total": len(order)}
    for f in files + [m + ".lua" for m in order if m in per_world]:
        a = brought[f[:-4]] if f[:-4] in per_world else B.shipped_source(src, f, game.folder)
        b = os.path.join(mdir, f)
        if not os.path.isfile(b):
            out["missing"].append(f)
        elif not _same_file(a, b):
            out["changed"].append(f)
    roots = os.path.join(pack, "livecpk")
    for r in sorted(os.listdir(roots)) if os.path.isdir(roots) else []:
        if not os.path.isdir(os.path.join(game.livecpk_dir, r)):
            out["missing"].append(r)
    live = set()
    for l in lines:
        m, on = B.module_of(l)
        if m and on:
            live.add(m.replace("/", "\\").rpartition("\\")[2])
    chosen_off = B.modules_off(mdir)
    for m in order:
        if m not in live:
            out["left_off" if m in chosen_off else "off"].append(m)
    return out


def modules_ok(state):
    return bool(state) and not (state["missing"] or state["changed"] or state["off"])


def ready_check(game, world):
    """the final check after a ready world is installed (0.2.4, a tester: "one complete modpack
    install reliably from start to finish, with an automatic final check"): every thing the game
    needs to play it, as (level, text) -- "ok", "err" (it will not play as it should) or "warn".
    The content servers checked are the ones the world brought map lines or a folder for."""
    out = []
    d = os.path.join(game.livecpk_dir, world)
    if not os.path.isfile(os.path.join(d, "fl26world.txt")):
        return [("err", _("%s is not in SiderAddons\\livecpk: install the zip again") % world)]
    out.append(("ok", _("The world %s is installed") % world))
    try:
        from .siderini import SiderIni
        ini = SiderIni.load(game.ini_path)
    except Exception:
        return out + [("err", _("sider.ini could not be read"))]
    on = [e for e in ini.entries("cpk.root") if e.enabled
          and os.path.basename(os.path.normpath(root_path(game.sider_dir, e.value))) == world]
    try:
        import leaguebuilder as B
        live = B.is_live(world, game.folder)
    except Exception:
        live = False
    if on and live:
        out.append(("ok", _("It is the world in the game")))
    else:
        out.append(("err", _("It is not in the game: My world > Activate on %s") % world))
    state = modules_state(game)
    if state is not None:
        if modules_ok(state):
            out.append(("ok", _("Mod Studio's modules are installed, up to date and switched on")))
        else:
            # which ones: a tester saw "not all in place" and could not tell what (Novarama, 15.10.)
            which = []
            for key, label in (("missing", "missing"), ("changed", "older or damaged"), ("off", "switched off")):
                if state[key]:
                    which.append("%s: %s" % (_(label), ", ".join(state[key])))
            out.append(("err", _("Mod Studio's modules are not all in place (%s): Home > Install now")
                        % "; ".join(which)))
    from . import installer as I
    if I.face_pack_missing(game.sider_dir):
        out.append(("warn", _("The face pack is missing: the new players will all have the same face. "
                              "Home > Install now")))
    try:                                   # home stadiums: of the maker's stadium pack
        import lbstadiums
        from . import filecache
        n, have = lbstadiums.coverage(filecache.json_file(os.path.join(d, "leaguebuilder-plan.json")),
                                      game.sider_dir, lbstadiums.load_edits(d))
    except Exception:
        n = have = 0
    if n and have == n:
        out.append(("ok", _("Home stadiums: all %d clubs have theirs") % n))
    elif n:
        out.append(("warn", _("Home stadiums: %d of %d clubs have theirs. Your stadium pack does not have the "
                              "other %d, so those clubs play at the stadium the game gives them. Stadiums > Your "
                              "world's clubs finds them in your pack or lets you pick others") % (have, n, n - have)))
    live_mods = {os.path.basename(e.value.replace("/", "\\").strip('"')).lower()
                 for e in ini.entries("lua.module") if e.enabled}
    # where sider.ini has a module: SPFL26's own kits.lua and scoreboards.lua sit in modules\common
    # (B44, vmican 15.10.: "kits.lua is not in SiderAddons\modules" while common\kits.lua was on)
    at = {}
    for e in ini.entries("lua.module"):
        v = e.value.replace("/", "\\").strip('"')
        at.setdefault(os.path.basename(v).lower(), []).append(v)
    for srv in S.SERVERS:
        folder, module = srv.pick(game.content_dir)
        base = os.path.join(game.content_dir, folder)
        uses = os.path.isdir(os.path.join(base, world))
        for m in srv.maps:
            try:
                with open(os.path.join(base, m.file), encoding="utf-8-sig", errors="replace") as f:
                    uses = uses or any(world in ln for ln in f)
            except OSError:
                pass
        if not uses:
            continue
        optional = srv.key == "menus"         # the themes are a nice-to-have: the game plays without
        if not any(os.path.isfile(os.path.join(game.modules_dir, v))
                   for v in at.get(module.lower(), []) + [module]):
            out.append(("warn" if optional else "err",
                        _("%s: the world brings them, but %s is not in SiderAddons\\modules. It comes with "
                          "your Sider pack (SPFL26); put it in, then switch it on in Tools > Lua modules")
                        % (_(srv.title), module)))
        elif module.lower() not in live_mods:
            out.append(("warn" if optional else "err",
                        _("%s: the world brings them, but %s is switched off: Tools > Lua modules, tick it, "
                          "Apply") % (_(srv.title), module)))
        else:
            out.append(("ok", _("%s: %s is on and has the world's lines") % (_(srv.title), module)))
    return out
