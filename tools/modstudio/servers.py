"""what the program knows about each Sider content server: its folder, its module, its map
files and their columns, its settings file and what a piece of content in its library looks like.

A content server is a Lua module plus a folder under SiderAddons\\content that holds a library
(stadiums, balls, kits ...) and map files that say which club or competition gets which item.
The pages (pages/content.py) are built from these descriptions, so a server that follows the
same pattern only needs a new entry here.

Column kinds:
    team      a club id (the name is shown next to it)
    comp      a tournament id = regulation id; 65535 is exhibition, id + 1024*k a later stage
    item      a path relative to the server folder, picked from its library
    id3       a number written with three digits (stadium ids)
    int, float, text, flag (0/1), lang (a commentary prefix)
"""
import os, re

from .mapfile import MapFile, IniFile


class Col:
    def __init__(self, title, kind="text", tip="", default=""):
        self.title, self.kind, self.tip, self.default = title, kind, tip, default


class Map:
    def __init__(self, file, title, cols, width=None, sep=",", quote=(), about=""):
        self.file, self.title, self.cols = file, title, cols
        self.width, self.sep, self.quote, self.about = width, sep, quote, about

    @property
    def key(self):
        return self.cols[0].kind           # team or comp

    def open(self, folder):
        return MapFile(os.path.join(folder, self.file), width=self.width, sep=self.sep, quote=self.quote)


class Server:
    def __init__(self, key, title, folder, module, maps, config=None, library=None,
                 about="", settings=None, alias=None):
        self.key, self.title, self.folder, self.module = key, title, folder, module
        self.maps, self.config, self.library, self.about = maps, config, library, about
        self.settings = settings or {}     # key -> (label, kind, tip)
        self.alias = alias                 # (folder, module) a pack ships under its own names

    def pick(self, content_dir):
        """(folder, module) in use: ours, or the alias when only the alias is there"""
        if self.alias and content_dir and not os.path.isdir(os.path.join(content_dir, self.folder)):
            d = os.path.join(content_dir, self.alias[0])
            # SPFL26's own stadium folder ships its map files as "(All packs) map_teams.txt"
            if any(os.path.isfile(os.path.join(d, n)) for n in
                   (self.maps[0].file, "(All packs) " + self.maps[0].file, self.config or "")):
                return self.alias
        return self.folder, self.module

    def folder_in(self, content_dir):
        return self.pick(content_dir)[0]

    def module_in(self, content_dir):
        return self.pick(content_dir)[1]

    def path(self, content_dir):
        return os.path.join(content_dir, self.folder_in(content_dir))

    def installed(self, content_dir):
        return os.path.isdir(self.path(content_dir))

    def ini(self, content_dir):
        return IniFile(os.path.join(self.path(content_dir), self.config)) if self.config else None


# ---- libraries: what one piece of content is ----
MARKERS = {"asset", "common", "addon", "badge", "cap", "armband"}


def is_leaf(path):
    """a folder that is one item (it holds the game's own folder layout, or a kit's config)"""
    try:
        names = {n.lower() for n in os.listdir(path)}
    except OSError:
        return False
    return bool(names & MARKERS) or "config.txt" in names or "order.ini" in names


def library(root, kind="folder", depth=3):
    """relative paths of the items under `root`: folders (kind folder) or .mp3 files (kind mp3)"""
    out = []
    root = os.path.normpath(root)

    def walk(d, level):
        try:
            names = sorted(os.listdir(d), key=str.lower)
        except OSError:
            return
        for n in names:
            p = os.path.join(d, n)
            if kind == "mp3":
                if os.path.isfile(p) and n.lower().endswith(".mp3"):
                    out.append(os.path.relpath(p, root))
                elif os.path.isdir(p) and level < depth:
                    walk(p, level + 1)
            elif os.path.isdir(p):
                if is_leaf(p):
                    out.append(os.path.relpath(p, root))
                elif level < depth:
                    walk(p, level + 1)
    walk(root, 1)
    return out


def norm_item(v):
    """a map's path as the library lists it: one backslash between parts, lower case"""
    return re.sub(r"[\\/]+", r"\\", v.strip()).lower()


_BALL = re.compile(r"^ball(\d+)$", re.I)


def ball_id(folder):
    """the ball id a ball folder was made for: Asset\\model\\ball\\ballNNN"""
    d = os.path.join(folder, "Asset", "model", "ball")
    try:
        for n in os.listdir(d):
            m = _BALL.match(n)
            if m:
                return "%03d" % int(m.group(1))
    except OSError:
        pass
    return ""


def stadium_id(folder):
    """the stadium slot a stadium folder was made for (its AddOn folders are named by it)"""
    seen = {}
    for sub in ("fog", "Light", "Cutscene", "Large_hexagonal_net"):
        try:
            for n in os.listdir(os.path.join(folder, "AddOn", sub)):
                if re.fullmatch(r"\d{3}", n):
                    seen[n] = seen.get(n, 0) + 1
        except OSError:
            pass
    return max(seen, key=seen.get) if seen else ""


def preview(folder):
    """a picture of the item when it has one"""
    for rel in ("Preview.png", "preview.png", "Preview.jpg", "Preview.dds", "preview.dds"):
        p = os.path.join(folder, rel)
        if os.path.exists(p):
            return p
    d = os.path.join(folder, "common", "render", "thumbnail", "ball")
    try:
        for n in os.listdir(d):
            if n.lower().endswith((".dds", ".png")):
                return os.path.join(d, n)
    except OSError:
        pass
    return None


LANGS = [("eng", "English"), ("use", "English (US)"), ("fra", "French"), ("ger", "German"),
         ("ita", "Italian"), ("spa", "Spanish"), ("sam", "Spanish (Latin America)"),
         ("por", "Portuguese"), ("bra", "Portuguese (Brazil)"), ("jpn", "Japanese"),
         ("ara", "Arabic"), ("kor", "Korean"), ("tur", "Turkish"), ("rus", "Russian"),
         ("dut", "Dutch")]

TEAM = Col("Club", "team")
COMP = Col("Competition", "comp")

SERVERS = [
    Server("stadiums", "Stadiums", "stadium-server", "StadiumServer.lua",
           about="Which stadium each club plays at home, and which stadiums a competition or its "
                 "final uses. A stadium is a folder Region\\Stadium in the stadium-server library.",
           maps=[
               Map("map_teams.txt", "Home stadiums", [
                   TEAM, Col("Slot", "id3", "the stadium slot the folder was made for (often 009)", "009"),
                   Col("Stadium name", "text", "the name shown in the game"),
                   Col("Stadium", "item")]),
               Map("map_competitions.txt", "Competitions", [
                   COMP, Col("Slot", "id3", default="009"), Col("Stadium name", "text"),
                   Col("Stadium", "item")], width=7,
                   about="A competition listed here plays at these stadiums instead of the home "
                         "stadium; list one several times for a set of stadiums."),
               Map("map_comp_finals.txt", "Finals", [
                   COMP, Col("Slot", "id3", default="009"), Col("Stadium name", "text"),
                   Col("Stadium", "item")]),
           ],
           config="config.ini", library="folder", alias=("stadiums", "stadiums.lua"),
           settings={"favorite_stadium": ("Favourite stadium id", "int", "used when nothing else matches"),
                     "detailed_logging": ("Detailed log", "flag", "")}),
    Server("balls", "Balls", "ball-server", "BallServer.lua",
           about="Which ball a competition or a home club uses, with its finals ball and its "
                 "winter ball. The ball id is read from the ball folder when you pick one.",
           maps=[
               Map("map_competitions.txt", "Competitions", [
                   COMP, Col("Ball id", "id3"), Col("Ball", "item"),
                   Col("Finals ball id", "id3"), Col("Finals ball", "item"),
                   Col("Winter ball id", "id3"), Col("Winter ball", "item")], width=7,
                   about="Every line needs all seven fields; empty ones stay empty."),
               Map("map_teams.txt", "Home clubs", [TEAM, Col("Ball id", "id3"), Col("Ball", "item")]),
               Map("map_winter_weeks.txt", "Winter weeks", [
                   COMP, Col("From week", "int"), Col("To week", "int"),
                   Col("Always", "flag", "1 = the winter ball in those weeks even without snow")],
                   about="League weeks when the winter ball is used (leagues only)."),
               Map("map_HiVis_winter_balls.txt", "Snow balls", [
                   COMP, Col("Ball id", "id3"), Col("Ball", "item")],
                   about="The high-visibility ball used when it snows."),
           ],
           config="config.ini", library="folder",
           settings={"favorite_ball": ("Favourite ball id", "int", "0 = none")}),
    Server("kits", "Kits", "kit-server", "kserv.lua",
           about="Which kit folder a club uses. A kit folder is League\\Club and holds the kits "
                 "p1, p2, g1 ... with order.ini. map_comp.txt picks the badge set of a competition.",
           maps=[
               Map("map.txt", "Clubs", [TEAM, Col("Kit folder", "item")], quote=(1,)),
               Map("map_comp.txt", "Competitions", [COMP, Col("Badge set", "text")]),
           ],
           config="config.txt", library="folder", alias=("kits", "kits.lua"),
           settings={"auto_select_gk": ("Pick the goalkeeper kit", "flag", ""),
                     "hide_comp_kits_badges": ("Hide competition badges", "flag", ""),
                     "armband_color_match": ("Armband matches the kit", "flag", ""),
                     "armband_light": ("Light armband", "flag", "")}),
    Server("commentary", "Commentary", "commentary-server", "commentary-server.lua",
           about="The commentary language for a club's home matches or a competition "
                 "(the commentary files themselves must be installed).",
           maps=[
               Map("map_teams.txt", "Clubs", [TEAM, Col("Commentary", "lang")]),
               Map("map_competitions.txt", "Competitions", [COMP, Col("Commentary", "lang")]),
           ]),
    Server("goalsongs", "Goal songs", "goalsong-server", "GoalSongServer.lua",
           about="The song played after a goal: per home club, or per competition "
                 "(exclusive = only that song in that competition).",
           maps=[
               Map("map_teams.txt", "Clubs", [
                   TEAM, Col("Song", "item"), Col("Volume +/-", "float", "added to the master volume", "0")]),
               Map("map_competitions.txt", "Competitions", [
                   COMP, Col("Song", "item"), Col("Volume +/-", "float", default="0"),
                   Col("Exclusive", "flag", default="0")]),
           ],
           config="config.ini", library="mp3",
           settings={"master_volume": ("Master volume", "float", "0 .. 1"),
                     "stop_on_replays": ("Stop on replays", "flag", "")}),
    Server("scoreboards", "Scoreboards", "scoreboard-server", "ScoreboardServer.lua",
           about="The scoreboard of a competition; list a competition twice and one is picked "
                 "at random.",
           maps=[Map("map_competitions.txt", "Competitions", [COMP, Col("Scoreboard", "item")])],
           config="config.ini", library="folder", alias=("scoreboards", "scoreboards.lua"),
           settings={"favorite_scoreboard": ("Favourite scoreboard", "int", ""),
                     "detailed_logging": ("Detailed log", "flag", "")}),
    Server("menus", "Menus", "menu-server", "MenuServer.lua",
           about="The menu graphics shown for a competition.",
           maps=[Map("map_competitions.txt", "Competitions", [COMP, Col("Menu", "item")])],
           library="folder"),
    Server("refkits", "Referee kits", "referee_kit-server", "RefKitServer.lua",
           about="The referees' kit in a competition.",
           maps=[Map("map_competitions.txt", "Competitions", [COMP, Col("Referee kit", "item")])],
           config="config.ini", library="folder",
           settings={"favorite_refkit": ("Favourite referee kit", "int", "0 = none")}),
    Server("badges", "Sleeve badges", "badge-server", "SleeveBadge-ArmbandServer.lua",
           about="Sleeve badges and armbands: per competition, and per club.",
           maps=[
               Map("map.txt", "Competitions", [COMP, Col("Badge folder", "item")], quote=(1,)),
               Map("map_teams.txt", "Clubs", [TEAM, Col("Club subfolder", "text",
                   "a folder inside <competition folder>\\badge\\ with this club's own badges")], quote=(1,),
                   about="Clubs with their own badges (champions, holders): the name of a subfolder "
                         "of each competition's badge folder."),
           ],
           library="folder"),
    Server("weather", "Weather", "weather-conditions", "WeatherConditions.lua",
           about="How likely each weather is at a club's home matches, in per cent.",
           maps=[Map("map_teams.csv", "Clubs", [
               TEAM, Col("Summer clear", "int"), Col("Summer cloudy", "int"),
               Col("Summer showers", "int"), Col("Summer rain", "int"),
               Col("Winter clear", "int"), Col("Winter cloudy", "int"),
               Col("Winter showers", "int"), Col("Winter rain", "int"),
               Col("Winter flurries", "int"), Col("Winter snow", "int")], sep=";")]),
]

BY_KEY = {s.key: s for s in SERVERS}

# modules that change the game's look without map files: they can only be switched on or off
# (the second field is the start of the module file name)
FIXED = [
    ("Entrance", "Entrance.lua", "players walking out, per stadium"),
    ("Stadium tunnel", "Stadium_Tunnel.lua", "the tunnel scenes"),
    ("Stadium banners", "Stadium_Banner.lua", "banners in the stands"),
    ("Stadium boards", "Stadium_Board.lua", "advertising boards"),
    ("Corner flags", "Stadium_CornerFlag.lua", "corner flags"),
    ("Fans", "FansServer.lua", "crowd and flags"),
    ("Ball boys", "BallBoysServer.lua", "ball boys' kits"),
    ("Bibs", "BibServer.lua", "training bibs of the substitutes"),
    ("Anthem and tunnel", "tournament_anth_tunnel.lua", "competition anthems and tunnel"),
    ("Whistles", "randomWhistle", "referee whistles"),
    ("Turf", "TurfLoader.lua", "pitch turf and light by season (lists in turf-loader)"),
    ("UI colours", "UIColors.lua", "menu colours (ui-colors folder)"),
    ("Soundtrack", "SoundtrackServer.lua", "menu music (Music section)"),
]


# ---- soundtrack: numbered Track_N.mp3 folders with the counts in the module ----
SOUNDTRACK = [
    ("1_Soundtrack", "Main_Soundtrack_MaxCount", "Menus"),
    ("2_Edit_Mode", "Main_Edit_Mode_MaxCount", "Edit mode"),
    ("3_Competitions_Generic", "Main_Competitions_Generic_MaxCount", "Competitions"),
    ("4_Competitions_Specific", "Main_Competitions_Specific_MaxCount", "Competitions (specific)"),
    ("5_Results_Generic", "Main_Results_Generic_MaxCount", "Results"),
    ("6_Results_Specific", "Main_Results_Specific_MaxCount", "Results (specific)"),
    ("7_Highlights_Generic", "Main_Highlights_Generic_MaxCount", "Highlights"),
    ("8_Highlights_Specific", "Main_Highlights_Specific_MaxCount", "Highlights (specific)"),
]
_TRACK = re.compile(r"^Track_(\d+)\.mp3$", re.I)


def tracks(folder):
    """[(number, file name)] of Track_N.mp3 in a soundtrack folder, by number"""
    out = []
    try:
        for n in os.listdir(folder):
            m = _TRACK.match(n)
            if m:
                out.append((int(m.group(1)), n))
    except OSError:
        pass
    return sorted(out)


def counts(lua_path):
    """{name: number} of the *_MaxCount lines in SoundtrackServer.lua"""
    out = {}
    try:
        for line in open(lua_path, encoding="utf-8", errors="replace"):
            m = re.match(r"\s*local\s+(\w+_MaxCount)\s*=\s*(\d+)", line)
            if m:
                out[m.group(1)] = int(m.group(2))
    except OSError:
        pass
    return out


def set_counts(lua_path, new, sider_dir=None):
    """write the *_MaxCount numbers (a restore point first); returns the names changed"""
    from .backups import snapshot
    raw = open(lua_path, "rb").read()
    text = raw.decode("utf-8", "replace")
    changed = []

    def fix(m):
        name, old = m.group(2), m.group(4)
        if name in new and str(new[name]) != old:
            changed.append(name)
            return m.group(1) + name + m.group(3) + str(new[name])
        return m.group(0)
    text2 = re.sub(r"(?m)^(\s*local\s+)(\w+_MaxCount)(\s*=\s*)(\d+)", fix, text)
    if changed:
        snapshot(lua_path, "soundtrack counts", sider_dir)
        with open(lua_path + ".tmp", "wb") as f:
            f.write(text2.encode("utf-8"))
        os.replace(lua_path + ".tmp", lua_path)
    return changed


def renumber(folder, order, sider_dir=None):
    """rename the tracks of a folder to Track_1..Track_n in the given order of file names
    (files not in `order` keep their place after them); returns the count"""
    have = [n for _i, n in tracks(folder)]
    order = [n for n in order if n in have] + [n for n in have if n not in order]
    tmp = []
    for i, n in enumerate(order):
        t = os.path.join(folder, "__ms_tmp_%d.mp3" % i)
        os.replace(os.path.join(folder, n), t)
        tmp.append(t)
    for i, t in enumerate(tmp):
        os.replace(t, os.path.join(folder, "Track_%d.mp3" % (i + 1)))
    return len(tmp)
