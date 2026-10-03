"""Lua modules: what a module is, where its file is, and the order checks.

The order checks come from two places:
  * rules the module authors give in their readmes (RULES below), and
  * what the files themselves say: a module that publishes itself as ctx.<name> = m
    must be loaded before a module that reads ctx.<name>.
"""
import os, re, shutil

KNOWN = {
    "commonlib": "shared library other modules use (load it early)",
    "nesalib": "shared library other modules use (load it early)",
    "stadiumserver": "stadium server: picks the stadium per team or competition",
    "kserv": "kit server: kits per team",
    "kitserver": "kit server: kits per team",
    "ballserver": "ball server: ball per team or competition",
    "commentaryserver": "commentary server: commentary language per team or competition",
    "soundtrackserver": "soundtrack server: menu music",
    "soundserver": "sound server: crowd and stadium sounds",
    "goalsongserver": "goal songs per team",
    "refkitserver": "referee kits",
    "sleevebadge-armbandserver": "sleeve badges and captain armbands",
    "scoreboardserver": "scoreboards per competition",
    "menuserver": "menu backgrounds",
    "ballboysserver": "ball boys' kits",
    "bibserver": "substitutes' bibs",
    "fansserver": "crowd and fans",
    "weatherconditions": "weather and time of day for a match",
    "turfloader": "pitch turf per stadium",
    "entrance": "players' entrance scene",
    "uicolors": "menu colours",
    "customexhibitionmatch": "exhibition match options",
    "matchset": "match settings",
    "randomwhistle_gpt": "random referee whistles",
    "stadium_banner": "stadium banners",
    "stadium_board": "advertising boards",
    "stadium_cornerflag": "corner flags",
    "stadium_tunnel": "stadium tunnel",
    "tournament_anth_tunnel": "tournament anthem in the tunnel",
    "camera": "camera module",
}

# (a, b, why): a must be loaded before b.  Names are lower case, without .lua and folder.
RULES = [
    ("commonlib", "stadiumserver", "CommonLib has to come before StadiumServer"),
    ("commonlib", "ballserver", "CommonLib has to come before BallServer"),
    ("weatherconditions", "turfloader", "WeatherConditions has to come before TurfLoader"),
    ("turfloader", "stadiumserver", "TurfLoader has to come before StadiumServer"),
    ("flags", "stadiumserver", "Flags has to come before StadiumServer"),
] + [("customexhibitionmatch", m, "CustomExhibitionMatch has to come before the content servers")
     for m in ("stadiumserver", "ballserver", "kserv", "kitserver", "commentaryserver", "commentary-server",
               "goalsongserver", "scoreboardserver", "refkitserver", "weatherconditions")] + [
    ("fl26joindll", "fl26swiss", "fl26joindll has to come before fl26swiss"),
    ("fl26chain", "fl26swiss", "fl26chain has to come before fl26swiss"),
]

# (module, its name on the page) that read ctx.common_lib: they only work when
# lib\CommonLib.lua is in sider.ini and loaded before them (#91)
COMMONLIB = [("scoreboardserver", "ScoreboardServer"), ("ballserver", "BallServer"),
             ("refkitserver", "RefKitServer"), ("menuserver", "MenuServer"),
             ("uicolors", "UIColors"), ("scoreboard-hexx", "scoreboard-hexx")]

# (module, sider.ini setting, value it needs, why)
NEEDS = [
    ("goalsongserver", "match-stats.enabled", "1", "GoalSongServer needs match-stats.enabled = 1 in sider.ini"),
    ("tournament_anth_tunnel", "match-stats.enabled", "1",
     "tournament_anth_tunnel needs match-stats.enabled = 1 in sider.ini"),
    ("customexhibitionmatch", "luajit.ext.enabled", "1",
     "CustomExhibitionMatch needs luajit.ext.enabled = 1 in sider.ini"),
]


def base(value):
    v = value.replace("/", "\\").strip().strip('"')
    return os.path.splitext(v.split("\\")[-1])[0].lower()


def path_of(value, modules_dir):
    if not modules_dir:
        return None
    return os.path.join(modules_dir, value.strip().strip('"').replace("/", "\\"))


def exists(value, modules_dir):
    p = path_of(value, modules_dir)
    return bool(p) and os.path.exists(p)


def kind_of(value):
    b = base(value)
    if b.startswith("fl26"):
        return "core"
    if "lib" in value.lower().replace("/", "\\").split("\\")[0] or b.endswith("lib"):
        return "library"
    if b.endswith("server") or b in ("kserv",):
        return "server"
    return "script"


def describe(value, modules_dir=None):
    """(kind, English description) of one module line"""
    b = base(value)
    k = kind_of(value)
    if k == "core":
        return k, "League Builder / FL26 research module (keep the order it was installed in)"
    if b in KNOWN:
        return k, KNOWN[b]
    p = path_of(value, modules_dir)
    if p and os.path.exists(p):
        h = first_comment(p)
        if h:
            return k, h
    return k, "Lua module"


def first_comment(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f.readlines()[:12]:
                s = line.strip()
                if s.startswith("--"):
                    s = s.lstrip("-").strip()
                    if len(s) > 6 and not s.startswith("[") and "author" not in s.lower():
                        return s[:120]
    except OSError:
        pass
    return ""


def header(path, lines=40):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return "".join(f.readlines()[:lines])
    except OSError as e:
        return str(e)


_PUB = re.compile(r"\bctx\.([A-Za-z_]\w*)\s*=\s*m\b")
_USE = re.compile(r"\bctx\.([A-Za-z_]\w*)\b")


_INIT = re.compile(r"^\s*(?:local\s+)?function\s+(?:m\.|M\.)?init\s*\(|^\s*init\s*=\s*function", re.M)


def links(path):
    """(names it publishes on ctx, names its init() reads from ctx).  Only init counts:
    reads inside event handlers run after every module is loaded, so order does not matter."""
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return set(), set()
    pub = set(_PUB.findall(text))
    m = _INIT.search(text)
    body = ""
    if m:
        end = re.search(r"^end\b", text[m.end():], re.M)
        body = text[m.end():m.end() + end.start()] if end else text[m.end():]
    use = set(_USE.findall(body)) - pub
    return pub, use


def check_order(ini, modules_dir):
    """problems with the lua.module list, as English sentences or (format, args...) tuples"""
    out = []
    on = [e for e in ini.entries("lua.module") if e.enabled]
    seen = {}
    for e in on:
        b = base(e.value)
        if b in seen:
            out.append(("%s is switched on twice (lines %d and %d)", e.value, seen[b] + 1, e.index + 1))
        seen.setdefault(b, e.index)
        if not exists(e.value, modules_dir):
            out.append(("%s is switched on but its file is missing", e.value))
    pos = {}
    for n, e in enumerate(on):
        pos.setdefault(base(e.value), n)
    for a, b, why in RULES:
        if a in pos and b in pos and pos[a] > pos[b]:
            out.append(why)
    if "fl26cuphook" in pos and "fl26chain" in pos:
        out.append("fl26cuphook is the old version of fl26chain: switch fl26cuphook off")
    if "commonlib" not in pos:
        need = [name for m, name in COMMONLIB if m in pos]
        if need:
            out.append(("CommonLib has to be in sider.ini for %s (lib\\CommonLib.lua, before them)",
                        ", ".join(need)))
    told = set()
    st = ini.settings()
    for m, key, val, why in NEEDS:
        if m in pos and st.get(key, "0") != val and why not in told:
            told.add(why)
            out.append(why)
    # what the files say
    pubs, uses = {}, {}
    for n, e in enumerate(on):
        p = path_of(e.value, modules_dir)
        if p and os.path.exists(p):
            pu, us = links(p)
            for name in pu:
                pubs.setdefault(name, (n, e.value))
            uses[n] = (e.value, us)
    told = set()
    for n, (value, us) in uses.items():
        for name in us:
            if name in pubs and pubs[name][0] > n and (value, name) not in told:
                told.add((value, name))
                out.append(("%s uses %s, which is loaded after it: move %s above it",
                            value, pubs[name][1], pubs[name][1]))
    return out


def install_file(src, modules_dir):
    """copy a .lua into the modules folder (keeps an existing file of the same name
    when it is identical); returns the value to put in sider.ini"""
    name = os.path.basename(src)
    dst = os.path.join(modules_dir, name)
    if os.path.abspath(src).lower() != os.path.abspath(dst).lower():
        os.makedirs(modules_dir, exist_ok=True)
        if os.path.exists(dst):
            from .backups import snapshot
            snapshot(dst, "replaced by " + name, os.path.dirname(modules_dir))
        shutil.copy2(src, dst)
    return name
