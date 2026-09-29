r"""python leaguebuilder.py plan  <recipe.json> [--base <pesdb dir>]
   python leaguebuilder.py build <recipe.json> [--base <pesdb dir>] [--game <dir>] [--replace]
   python leaguebuilder.py on    <world name> [--game <dir>]
   python leaguebuilder.py check [--game <dir>]

The league builder's core: one recipe in, one finished world out. The window (stage C,
docs/mod-studio.md) calls these same functions; this command line is for tests.

A recipe says what a person would say -- which country, how many clubs, how often they meet,
which league sits above -- and nothing about ids:

    { "world": "_FL26BiH",
      "leagues": [
        { "name": "Premijer Liga BiH", "country": "Bosnia and Herzegovina",
          "clubs": 12, "legs": 3,
          "club_names": ["FK Sarajevo", "Zeljeznicar", ...] },
        { "name": "Prva Liga FBiH", "country": "Bosnia and Herzegovina",
          "clubs": 16, "legs": 2, "above": "Premijer Liga BiH", "exchange": 2 },
        { "name": "Split League", "country": "Bosnia and Herzegovina", "clubs": 12,
          "split": { "legs": 2, "groups": [6, 6], "group_legs": 2 } }
      ],
      "uecl": true }

  country     a Country.bin name (flag, Competition Info name, the region's country)
  flag        optional picture of the country's flag; replaces the game's own flag of that
              country (Select Team, nationality) while the world is on
  clubs       10..24, the range seasons have been played with
  legs        how many times each pair meets, 1..4
  above       a league of this recipe (by name) or a shipped regulation id (e.g. 81, Ligue 2);
              the league becomes the division below it, in its region, promotion both ways
  exchange    clubs going up and down between the two (default 3)
  split       Scottish style: a regular phase, then top/bottom groups that keep their points
              (tools/mksplit.py); "groups" are club counts adding up to "clubs"
  apertura    optional, true or {"playoff": 8}: the season is two tournaments, Apertura
              (August to December) and Clausura (January to May), each club meeting every
              other once in each, both starting from zero points; the whole season's table
              stays for promotion and relegation. "playoff" 8 or 4 (default 8, 0 = none): the
              first clubs of each tournament then play a knockout, two legs a round and a
              one-match final (fl26swiss.dll fills it from that tournament's table the day
              after its last round). Built as a split (mksplit, one group of all the clubs, the
              world file's carry=0); 18 clubs at most, 35 dates a season. Not with "split"
  club_names  optional; missing names become "<league> 01", "<league> 02", ...
  europe      optional European places: [[position, competition], ...], competition 0 Champions
              League, 1 Europa League, 2 Conference League, 3 Libertadores, 4 its qualifying
              round, 5 AFC Champions League, or one of the cups the game has not got: 6 CAF
              Champions League, 7 CAF Confederation Cup, 8 AFC Champions League Two, 9 Copa
              Sudamericana (fl26world.COMPETITIONS); each position once, and only the league's
              own (1..clubs). 0..5 are written as uefa lines of the world file, after the shipped
              leagues' places (fl26world.uefa_places); 6..9 build that cup (see ccup_plan)
  cup         optional, a top division of a new country only: true gives the country a national
              cup (a knockout copied from a shipped one, see NATIONAL_CUPS). The game fills a
              domestic cup with the region's first league and the league below it, and a cup's
              round dates come from the cup it was copied from, so the copy is picked by that
              count; when the two divisions make no shape the game dates, the cup keeps the top
              division's clubs only (fl26chain, cup= on the second division's line).
              "cup_name" names it (default "<league> Cup")
  supercup    optional, with cup: true also a super cup, the league's champion v the cup's winner
              in one match before the season (copied from SUPER_CUP_LIKE); "supercup_name"
  exhibition  optional, true: the league is for Kick Off and exhibition matches only -- its clubs
              are in the Select Team list under it, but it never enters a Master League season
              (a historical league, a league of legends ...). It stands alone: no division above
              or below it, no European places, no cups. Its regulation id is one the season
              builder does not take in at creation (CREATION_IDS), and fl26joindll leaves it out
  league_cup  optional, a top division of a new country only: true gives the country a league
              cup, a straight knockout (two legs a round, the final one match) of 16, 8 or 4
              clubs -- the top division's by league position, then the division below's --
              the strongest v the weakest, played September to December (LEAGUE_CUP_DAYS).
              fl26swiss.dll fills and dates it (the ccup line's options); "league_cup_name"
  preseason_cups  (the recipe, not a league) [{"name": ..., "clubs": [...]}]: a knockout of
              4 or 8 invited clubs in July, before the season (PRESEASON_DAYS), paired in the
              order given (first v second ...). A club is "<league>/<k>" (the k-th club of a
              league of the recipe, from 0) or a club id of the game; at least one from a
              league of the recipe (the cup is hosted by its country). A club of the game must
              play in a league that season, or the cup is not filled.
  uecl        (the recipe, not a league) true, the default: the world gets the Conference
              League -- the Champions League and Europa League league phase reshaped to one
              group of 36 (mkreshape.py), the Conference League cloned from it (mkuecl.py:
              competition 174, regulations 186/187, group 1210) and the Europa / Conference
              League play-offs (mkeuropo.py: 188, 189), the ids fl26swiss.dll and the fixture
              dates know. false: the European cups stay as the game ships them

What plan() decides, so that nothing is left to a person to get wrong:

  regulation ids   mkworld's free list, taking ids that have a Select Team slot
                   (fl26world.DEFAULT_SLOT) -- 11, 49, 60, 61, ... -- first, then the three
                   without one (fl26world.NO_SLOT_IDS: those leagues play, but are not in the
                   Select Team list); never one of BAD_REG
  competition ids  from 130 up, the range FL's own added leagues use, never 174 (the
                   Conference League's)
  regions          a league with "above" takes its parent's; a new country gets the next
                   region from 29 up that nothing uses (sider/fl26reg64.lua reads 29..63)
  tier             1, or the parent's plus one
  split phases     mksplit's ids from 191 up (the range split seasons were tested on)

build() writes the world folder: Team/Coach/Competition* tables (mkleague.add_league, as
mkworld does), squads (mkplayers.py), splits (mksplit.py), the Conference League (above), and
fl26world.txt in the folder -- the world file every module reads, with the uefa lines of the
leagues' European places. on() makes it the live world: the one active _FL26
cpk.root in sider.ini (siderroot.py) and the world file copied to modules\. check() reads
sider.log after a start and says, module by module, whether the world file was taken.
"""
import contextlib, glob, io, json, os, shutil, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pesdb
import mkleague as M
import mkworld as W
import mkcoaches
import mkuecl
import fl26world
import siderdir

GAME = os.environ.get("FL26_DIR", r"C:\Football Life 2026")
R_ABOVE = 0x04
LEGS_SHIFT, LEGS_MASK = 12, 7
CLUBS_MIN, CLUBS_MAX, LEGS_MAX = 10, 24, 4
REGION_FIRST, REGION_LAST = 29, 63
CID_FROM = 130
SQUAD, PLAYER_CAP = 30, 51729            # tools/mkplayers.py --per / --cap, as the guide uses
TEAM_CAP = 1536                          # clubs in all, shipped ones included
MAX_SPLITS = 2                           # split seasons tested so far: two at a time (191..196)
# national cups to copy, by the clubs the game puts in them: the top division alone, or the top
# division and the one below. European ones only -- a new country plays the European calendar,
# and a cup's round dates are its prototype's. (code, bracket)
NATIONAL_CUPS = {12: ("SCOTLAND_CUP", 12), 16: ("BELGIUM_CUP", 16), 18: ("NETHERLANDS_D1_CUP", 18),
                 20: ("ENGLAND_D1_CUP", 44)}
NATIONAL_CUPS_TWO = {36: ("FRANCE_D1_CUP", 18), 40: ("ITALY_D1_CUP", 20), 44: ("ENGLAND_D1_CUP", 44)}
SUPER_CUP_LIKE = "BELGIUM_SUPER_CUP"      # two clubs, one match, a European date
CCUP_SIZES = (32, 16, 8, 4)              # the fields a continental cup can have (fl26swiss.dll)
CCUP_REG_FROM = 197                      # its regulation ids: past the split phases' 191..196
CCUP_KEEP = set(range(186, 197))         # the Conference League's 186..189, 190 (moved 145), splits
MAX_CCUP = 8                             # cups fl26swiss.dll takes from the world file (MAX_CCUP)
# the ids the season builder 0x1413156e0 admits at creation, whatever fl26joindll says (its
# include list as fl26join.log printed it on 2026-09-28): an exhibition league must not be one
CREATION_IDS = {2, 3, 4, 5, 6, 7, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 30, 49, 50, 53,
                59, 60, 61, 62, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 95, 115, 116,
                117, 118, 122, 123, 124, 125, 128, 129, 130, 133, 134, 135, 136, 137, 141, 142, 147,
                148, 151, 155, 156, 159, 172, 175}
# The days of the year the domestic knockouts are played on, one per record of the knockout
# fl26swiss borrows (two legs of the last 16, quarter-finals, semi-finals, then the final):
# always seven, a smaller field leaves the first ones unused. A league cup's are the day after
# the Champions League's weekday (CCUP_KO_DAYS, 73 + 7n), September to December; a pre-season
# cup's run from early July, after the season's July turn, filled on PRESEASON_FILL.
LEAGUE_CUP_DAYS = [263, 277, 291, 305, 319, 333, 347]
PRESEASON_FILL = 183
PRESEASON_DAYS = [186, 189, 192, 195, 198, 201, 205]
LEAGUE_CUP_SIZES = (16, 8, 4)
# Apertura/Clausura: fl26swiss dates a split's phases on the Scottish season's 38 dates,
# resampled to its rounds (fl26swiss.c SCOT_DAYS, split_dates); split_days() does the same sums,
# so the playoffs can be put between the league days. Continental cup days (CCUP_GROUP_DAYS,
# CCUP_KO_DAYS there) are kept free when the league has European places.
SPLIT_LINE = [226, 233, 240, 254, 261, 268, 275, 296, 300, 303, 310, 321, 324, 331, 338, 345, 356,
              359, 363, 2, 13, 16, 20, 23, 31, 34, 37, 51, 58, 65, 72, 79, 100, 107, 114, 121, 128, 142]
# fl26swiss starts our splits on the fourth date (SPLIT_SKIP there): the first three are behind
# a league that joins its season through register_all, and a round dated there went a year on.
SPLIT_SKIP = 3
CCUP_DAYS = [326, 333, 25, 32, 39, 46, 73, 80, 94, 101, 115, 122, 136]
PLAYOFF_SIZES = (8, 4)
SEASON_TURN = 182                        # the season's July turn: day-of-year order starts here
# The Kick Off and Edit team lists are ordered by a fixed list of 89 slots in the exe (0x1427d5920,
# read by 0x140ead990): a slot that is not on it sorts last, after Classic Teams -- Peru on slot 49
# did (2026-09-28). fl26comptab rebuilds the list with each league of ours after the slot its
# world line names (kickoff=): the league above it, else the end of its continent's leagues in
# the shipped order (read live 2026-09-28: Europe 0..27 ending on the European cups' slot 25,
# South America 28..40 ending on the Sudamericana's 67, Asia 44..49 ending on 70). Shipped
# leagues' slots from the same reading of the parameter table.
KICKOFF_AFTER = {2: 25, 4: 67, 3: 70}     # UEFA, CONMEBOL, AFC
KICKOFF_OTHER = 70                        # CAF, CONCACAF, OFC: no club list of their own, after Asia
SHIPPED_SLOT = {17: 7, 79: 50, 20: 8, 81: 52, 18: 9, 82: 53, 21: 10, 22: 12, 116: 91, 133: 114,
                19: 11, 80: 51, 117: 94, 118: 96, 50: 16, 30: 14, 29: 13, 163: 122, 67: 15, 119: 99,
                51: 17, 120: 102, 162: 119, 52: 18}
UECL_CID = mkuecl.CID                    # the Conference League's competition id: no league takes it
# the league phase of the Champions League (phase 2) and Europa League (phase 1) as one group of
# 36, the shape fl26swiss.dll draws and the Conference League is cloned from (mkreshape.py)
RESHAPE = ["UEFA_CHAMPIONS_LEAGUE:2:groups:36:1:-", "UEFA_EUROPE_LEAGUE:1:groups:36:1:-"]
UNIPAR = "common/character0/model/character/uniform/team/UniformParameter.bin"
KIT_TEXTURES = "kit-textures.txt"
MARK = "fl26world.txt"                   # a folder holding one was built by this; nothing else is replaced

# the modules that read the world file, and the line each logs when it does (sider.log)
READERS = ["fl26joindll", "fl26chain", "fl26comptab", "fl26editlist", "fl26catlist",
           "fl26clubs", "fl26slotnames", "fl26swiss"]


class BuildError(Exception):
    pass


def call(mod, args):
    """run a tool's main() in this process (so the frozen .exe needs no Python), return its output"""
    old, buf = sys.argv, io.StringIO()
    sys.argv = [mod.__name__ + ".py"] + [str(a) for a in args]
    try:
        with contextlib.redirect_stdout(buf):
            rc = mod.main()
    except SystemExit as e:
        raise BuildError("%s: %s\n%s" % (mod.__name__, e, buf.getvalue()))
    finally:
        sys.argv = old
    if rc:
        raise BuildError("%s returned %s\n%s" % (mod.__name__, rc, buf.getvalue()))
    return buf.getvalue()


def base_dir(opt=None):
    try:
        return fl26world.base_dir(opt)
    except SystemExit as e:
        raise BuildError(str(e))


def unpack_tables(game, out, log=print):
    """unpack the game's tables (download/data_s2526*.cpk, the later ones over the earlier, as
    the game layers them) into <out>; returns the folder with Team.bin -- the --base of the rest"""
    import cpkread
    cpks = sorted(glob.glob(os.path.join(game, "download", "data_s2526*.cpk")))
    if not cpks:
        raise BuildError("no download/data_s2526*.cpk in %s -- is that the game folder?" % game)
    for c in cpks:
        n = cpkread.extract(c, out, ["common/etc/pesdb/", UNIPAR])
        log("  %-20s %d tables" % (os.path.basename(c), n))
    base = os.path.join(out, "common", "etc", "pesdb")
    if not os.path.exists(os.path.join(base, "Team.bin")):
        raise BuildError("the archives held no Team.bin")
    # the kit textures the game has: a kit lent without its texture shows as a blank one
    import re
    tex = set()
    for c in glob.glob(os.path.join(game, "Data", "*.cpk")) + cpks:
        try:
            tex |= {m for n in cpkread.names(c) for m in re.findall(r"(u\d{4,5}[a-z]\d)\.ftex", n)}
        except (OSError, ValueError, KeyError):
            pass
    with open(os.path.join(out, KIT_TEXTURES), "w") as f:
        f.write("".join("%s.ftex\n" % t for t in sorted(tex)))
    log("  %d kit textures" % len(tex))
    return base


def tables_root(base):
    """the unpack folder that holds <base> (…/common/etc/pesdb), or None"""
    parts = os.path.normpath(base).split(os.sep)
    return os.sep.join(parts[:-3]) if parts[-3:] == ["common", "etc", "pesdb"] else None


def load_recipe(path):
    r = json.load(open(path, encoding="utf-8"))
    if not r.get("world", "").startswith("_FL26"):
        raise BuildError("the world name must start with _FL26 (sider.ini roots are found by it)")
    r.setdefault("leagues", [])
    if not r["leagues"] and not has_edits(r):
        raise BuildError("the recipe adds no league and changes nothing")
    return r


def has_edits(r):
    e = r.get("edits") or {}
    import lbplayers
    return bool(e.get("leagues") or e.get("clubs")) or lbplayers.has_players(r)


# ---- what the game already has: its leagues and clubs, for the edit tab ----

def text(b):
    b = bytes(b).split(bytes(1))[0]
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return b.decode("latin-1")


def game_leagues(base):
    """[(reg id, competition id, name, [team ids])] of every league in the tables -- the
    regulations of type 4 that are not a split phase, with the clubs entered in them"""
    comp, regs, ents = (M.load(base, n) for n in
                        ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin"))
    by_cid = {}
    for i in range(len(ents) // M.ENT):
        e = ents[i * M.ENT:(i + 1) * M.ENT]
        by_cid.setdefault(e[M.E_CID], []).append((e[M.E_ORDER], int.from_bytes(e[M.E_TEAM:M.E_TEAM + 4], "little")))
    out, seen = [], set()
    for i in range(len(regs) // M.REG):
        g = regs[i * M.REG:(i + 1) * M.REG]
        if g[M.R_TYPE] not in (4, fl26world.SPLIT_TOTAL) or fl26world.fmt(g) in (fl26world.F_REGULAR,) + fl26world.F_GROUPS:
            continue
        cid = g[M.R_CID]
        if cid in seen:
            continue
        seen.add(cid)
        teams = [t for _, t in sorted(by_cid.get(cid, []))]
        if teams:                            # "League 0" has none: nothing to show or change
            out.append((u16(g, M.R_ID), cid, text(g[M.R_NAME:M.R_NAME + M.NAME_SLOT]), teams))
    return sorted(out, key=lambda x: x[2].lower())


def game_clubs(base):
    """{team id: (name, short name)} of Team.bin"""
    raw = pesdb.wesys_unpack(open(os.path.join(base, "Team.bin"), "rb").read())
    out = {}
    for i in range(len(raw) // W.T_REC):
        r = raw[i * W.T_REC:(i + 1) * W.T_REC]
        out[int.from_bytes(r[W.T_ID:W.T_ID + 4], "little")] = (
            text(r[W.T_NAME:W.T_NAME + W.T_NAME_LEN]), text(r[W.T_ABBR:W.T_ABBR + W.T_ABBR_LEN]))
    return out


T_NATIONAL = 0x53                           # top bit set on the 144 national teams, never on a club


def game_others(base, leagues):
    """(national team ids, other club ids): the teams in no league -- the game's "Others"
    sections, clubs that only play a cup or a continental competition, or nothing at all"""
    raw = pesdb.wesys_unpack(open(os.path.join(base, "Team.bin"), "rb").read())
    inl = {t for *_, ts in leagues for t in ts}
    nat, other = [], []
    for i in range(len(raw) // W.T_REC):
        r = raw[i * W.T_REC:(i + 1) * W.T_REC]
        tid = int.from_bytes(r[W.T_ID:W.T_ID + 4], "little")
        if tid not in inl:
            (nat if r[T_NATIONAL] & 0x80 else other).append(tid)
    return sorted(nat), sorted(other)


# letters a decomposition does not take apart (Đ is not D + a mark)
FOLD = {"Đ": "D", "đ": "D", "Ł": "L", "ł": "L", "Ø": "O", "ø": "O", "ß": "SS", "Æ": "AE", "æ": "AE",
        "Œ": "OE", "œ": "OE", "Þ": "TH", "þ": "TH", "ı": "I"}


def ascii_letters(txt):
    """the letters and digits of a name in capitals, marks taken off: Željezničar -> ZELJEZNICAR.
    A short name is three bytes and the game's own are all A-Z and 0-9; the full name keeps
    its letters (UTF-8, as the game's Bayern München)."""
    import unicodedata
    txt = "".join(FOLD.get(c, c) for c in txt)
    txt = unicodedata.normalize("NFKD", txt)
    return "".join(c for c in txt.upper() if c.isalnum() and c.isascii())


def short_name(txt):
    return ascii_letters(txt)[:W.T_ABBR_LEN]


def apply_edits(edits, raw, regs, log=print):
    """the recipe's changes to the game's own clubs and leagues, in the world's tables"""
    clubs = {int(k): v for k, v in (edits.get("clubs") or {}).items()}
    n = 0
    for i in range(len(raw) // W.T_REC):
        o = i * W.T_REC
        e = clubs.get(int.from_bytes(raw[o + W.T_ID:o + W.T_ID + 4], "little"))
        if not e:
            continue
        if e.get("name"):
            M.put(raw, o + W.T_NAME, e["name"], W.T_NAME_LEN)
        if e.get("abbr"):
            raw[o + W.T_ABBR:o + W.T_ABBR + W.T_ABBR_LEN] = short_name(e["abbr"]).ljust(W.T_ABBR_LEN, bytes(1).decode()).encode("ascii")
        n += 1
    leagues = {int(k): v for k, v in (edits.get("leagues") or {}).items()}
    m = 0
    for i in range(len(regs) // M.REG):
        o = i * M.REG
        e = leagues.get(u16(regs[o:], M.R_ID))
        if e and e.get("name"):
            for k in range(M.NAME_SLOTS):
                M.put(regs, o + M.R_NAME + k * M.NAME_SLOT, e["name"], M.NAME_SLOT)
            m += 1
    if n or m:
        log("  changed %d of the game's clubs and %d of its leagues" % (n, m))


def u16(g, off):
    return int.from_bytes(g[off:off + 2], "little")


# ---- what the window offers to choose from ----

def country_names(base):
    """the country names of Country.bin, title case, sorted, each once"""
    import mkflags
    cty = mkflags.countries(mkflags.table("Country", [base]))
    return sorted({mkflags.title(en) for fid, (en, names) in cty.items()
                   if en and mkflags.by_name(cty, en) == fid})


def country_ids(base):
    """[(name, Country.bin id)] sorted by name: a player's Nationality is this id (measured: 146
    Brazil, 144 Argentina, 236 Spain on the game's own players). A name the table has twice
    carries its id, so each entry says which one it is."""
    import mkflags
    cty = mkflags.countries(mkflags.table("Country", [base]))
    seen = {}
    for fid, (en, names) in cty.items():
        if en:
            seen.setdefault(mkflags.title(en), []).append(fid)
    out = []
    for nm, ids in seen.items():
        for fid in ids:
            out.append((nm if len(ids) == 1 else "%s (%d)" % (nm, fid), fid))
    return sorted(out, key=lambda x: x[0].lower())


def shipped_parents(base):
    """[(regulation id, name)] of the shipped divisions (Competition code *_D<n>_LEAGUE) that
    have no league below them yet -- the ones a new division can go under"""
    import re
    comp, regs = M.load(base, "Competition.bin"), M.load(base, "CompetitionRegulation.bin")
    code = {comp[i * M.COMP + M.CID_OFF]:
            bytes(comp[i * M.COMP + M.CODE_OFF:(i + 1) * M.COMP]).split(b"\0")[0].decode("latin-1")
            for i in range(len(comp) // M.COMP)}
    out = []
    for i in range(len(regs) // M.REG):
        g = regs[i * M.REG:(i + 1) * M.REG]
        if g[M.R_TYPE] != 4 or u16(g, M.R_BELOW) or fl26world.fmt(g) in (12, 13, 14, 15):
            continue
        if not re.search(r"_D\d_LEAGUE$", code.get(g[M.R_CID], "")):
            continue
        raw = bytes(g[M.R_NAME:M.R_NAME + M.NAME_SLOT]).split(b"\0")[0]
        try:
            nm = raw.decode("utf-8")
        except UnicodeDecodeError:
            nm = raw.decode("latin-1")
        out.append((u16(g, M.R_ID), nm))
    return sorted(out, key=lambda x: x[1].lower())


def shipped_tiers(base):
    """{regulation id: division} of the game's leagues (1 = top), for saying which division a
    new league below one of them becomes"""
    regs = M.load(base, "CompetitionRegulation.bin")
    return {u16(regs[i * M.REG:(i + 1) * M.REG], M.R_ID): M.get_tier(regs[i * M.REG:(i + 1) * M.REG])
            for i in range(len(regs) // M.REG)}


def home_cup(regrow, region_of_cid, region):
    """the domestic cup of a region (a knockout, not a two-club super cup), or None.

    GitHub #21. The game fills a domestic cup from the region's first league and the league
    linked below it. A shipped cup built for one division (the DFB-Pokal's 18, the Russian
    Cup's 16) does not survive that: with a new second division under its league it gets 38
    or 36 clubs, or only the new league's clubs when that league has the lower regulation id,
    and its bracket loses rounds. fl26chain puts the top league's clubs back; this names the
    cup it has to watch."""
    cups = sorted(rid for rid, g in regrow.items()
                  if rid < 1024 and g[M.R_TYPE] == 3 and g[M.R_TEAMS] & 0x3f > 2
                  and region_of_cid.get(g[M.R_CID]) == region)
    return cups[0] if cups else None


def home_supercup(regrow, region_of_cid, region):
    """the super cup of a region (a two-club cup), or None. GitHub #29: the new second division
    under a shipped top flight also put one of its clubs into it; fl26chain swaps it out."""
    cups = sorted(rid for rid, g in regrow.items()
                  if rid < 1024 and g[M.R_TYPE] == 3 and g[M.R_TEAMS] & 0x3f == 2
                  and region_of_cid.get(g[M.R_CID]) == region)
    return cups[0] if cups else None


# ---- plan: every id, region and link decided, nothing written ----

def clubs_room(base):
    """how many new clubs fit: the club table stops at TEAM_CAP (the wall a 1536th club met,
    fl26-800-klubova-igra), and every new club takes SQUAD of the PLAYER_CAP player records
    the installed patch set allows -- with the shipped tables both come to 793"""
    n = lambda f, rec: len(pesdb.wesys_unpack(open(os.path.join(base, f), "rb").read())) // rec
    return min(TEAM_CAP - n("Team.bin", W.T_REC), (PLAYER_CAP - n("Player.bin", 312)) // SQUAD)


def plan(recipe, base):
    comp, regs = M.load(base, "Competition.bin"), M.load(base, "CompetitionRegulation.bin")
    import mkflags
    cty = mkflags.countries(mkflags.table("Country", [base]))
    regrow = {u16(regs[i * M.REG:], M.R_ID): regs[i * M.REG:(i + 1) * M.REG]
              for i in range(len(regs) // M.REG)}
    region_of_cid = {comp[i * M.COMP + M.CID_OFF]: M.dec_region(comp[i * M.COMP + M.REGION_OFF])
                     for i in range(len(comp) // M.COMP)}
    used_cid = set(region_of_cid)
    used_region = set(region_of_cid.values())

    leagues = recipe["leagues"]
    names = [L.get("name", "").strip() for L in leagues]
    if not all(names) or len(set(n.lower() for n in names)) != len(names):
        raise BuildError("every league needs a name, and no two the same")

    # mkworld's order (the free list, 145 moved to 190), keeping only ids with a slot
    free = []
    for r in range(1, W.REG_MAX + 1):
        if r in regrow or r in W.BAD_REG or r in W.MOVED_REG.values():
            continue
        r = W.MOVED_REG.get(r, r)
        if (r in fl26world.DEFAULT_SLOT or r in fl26world.NO_SLOT_IDS) and r not in regrow:
            free.append(r)
    free.sort(key=lambda r: r not in fl26world.DEFAULT_SLOT)     # slotted ids first, stable
    if leagues and len(leagues) > len(free):
        raise BuildError("%d leagues, but the game has room for %d (see docs/mod-studio.md)"
                         % (len(leagues), len(free)))
    cids = [c for c in range(CID_FROM, W.CID_MAX + 1) if c not in used_cid and c != UECL_CID][:len(leagues)]
    if len(cids) < len(leagues):
        raise BuildError("no free competition ids left")
    room = clubs_room(base)
    total = sum(int(L.get("clubs", 0) or 0) for L in leagues)
    if total > room:
        raise BuildError("%d new clubs, but the game has room for %d more (a full squad each)"
                         % (total, room))

    out, by_name, country_region = [], {}, {}
    order = order_by_parents(leagues)
    # an exhibition league first takes an id the season builder leaves alone; the others then
    # take what is left, in the usual order
    rid_of, left = {}, list(free)
    for i in order:
        if leagues[i].get("exhibition"):
            r = next((r for r in left if r not in CREATION_IDS), None)
            if r is None:
                raise BuildError("%s: no free regulation id outside Master League for an exhibition "
                                 "league" % names[i])
            rid_of[i] = r
            left.remove(r)
    for i in order:
        if i not in rid_of:
            rid_of[i] = left.pop(0)
    for k, i in enumerate(order):
        L = leagues[i]
        name = names[i]
        n, legs = int(L.get("clubs", 0)), int(L.get("legs", 2))
        if not CLUBS_MIN <= n <= CLUBS_MAX:
            raise BuildError("%s: %d clubs -- a league has %d..%d" % (name, n, CLUBS_MIN, CLUBS_MAX))
        if not 1 <= legs <= LEGS_MAX:
            raise BuildError("%s: clubs meet 1..%d times, not %d" % (name, LEGS_MAX, legs))
        fid = mkflags.by_name(cty, L.get("country", ""))
        if fid is None:
            raise BuildError("%s: no country called %r in Country.bin" % (name, L.get("country")))
        p = {"name": name, "country": fid, "clubs": n, "legs": legs, "rid": rid_of[i], "cid": cids[k],
             "slot": fl26world.DEFAULT_SLOT.get(rid_of[i], fl26world.NO_SLOT), "club_names": list(L.get("club_names") or []),
             "exhibition": bool(L.get("exhibition")),
             "logo": L.get("logo") or None, "flag": L.get("flag") or None,
             "club_crests": list(L.get("club_crests") or []),
             "club_abbrs": list(L.get("club_abbrs") or []),
             "club_coaches": list(L.get("club_coaches") or []),     # managers' names, "" = FL Mnnnn
             "exchange": int(L.get("exchange", 3)), "above": None, "tier": 1,
             "europe": [[int(a), int(b)] for a, b in (L.get("europe") or [])]}
        bad = europe_problems(n, L.get("europe") or [])
        if bad:
            raise BuildError("%s: European places: %s" % (name, "; ".join(bad)))
        if len(p["club_names"]) > n:
            raise BuildError("%s: %d club names for %d clubs" % (name, len(p["club_names"]), n))
        up = L.get("above")
        if up not in (None, ""):
            if isinstance(up, str) and not up.isdigit():
                parent = by_name.get(up.strip().lower())
                if parent is None:
                    raise BuildError("%s: no league called %r above it" % (name, up))
                p["above"], p["tier"], p["region"] = parent["rid"], parent["tier"] + 1, parent["region"]
            else:
                pr = regrow.get(int(up))
                if pr is None or pr[M.R_TYPE] != 4:
                    raise BuildError("%s: regulation %s is not a shipped league" % (name, up))
                if u16(pr, M.R_BELOW):
                    raise BuildError("%s: regulation %s already has a league below it (%d)"
                                     % (name, up, u16(pr, M.R_BELOW)))
                p["above"], p["tier"] = int(up), M.get_tier(pr) + 1
                p["region"] = region_of_cid[pr[M.R_CID]]
                if p["tier"] == 2:
                    p["cup"] = home_cup(regrow, region_of_cid, p["region"])
                    p["scup"] = home_supercup(regrow, region_of_cid, p["region"])
            if p["tier"] > 7:
                raise BuildError("%s: division %d -- the rank field stops at 7" % (name, p["tier"]))
        else:
            key = fid
            if key not in country_region:
                reg = next((r for r in range(REGION_FIRST, REGION_LAST + 1) if r not in used_region), None)
                if reg is None:
                    raise BuildError("no free region left for %s" % L.get("country"))
                used_region.add(reg)
                country_region[key] = reg
            p["region"] = country_region[key]
            if L.get("cup"):
                p["own_cup"] = {"name": (L.get("cup_name") or "").strip() or name + " Cup"}
                if L.get("supercup"):
                    p["own_cup"]["super"] = (L.get("supercup_name") or "").strip() or name + " Super Cup"
            elif L.get("supercup"):
                raise BuildError("%s: a super cup comes with the national cup (cup: true)" % name)
            if L.get("league_cup"):
                p["league_cup"] = {"name": (L.get("league_cup_name") or "").strip() or name + " League Cup"}
        if L.get("league_cup") and p["above"]:
            raise BuildError("%s: a league cup belongs to a country's top division" % name)
        if p["exhibition"]:
            bad = [w for w, on in (("the division above it", p["above"]), ("the European places", p["europe"]),
                                   ("the national cup", L.get("cup")), ("the league cup", L.get("league_cup")),
                                   ("the split", L.get("split")), ("the Apertura/Clausura", L.get("apertura"))) if on]
            if bad:
                raise BuildError("%s: an exhibition league stands alone -- take off %s" % (name, ", ".join(bad)))
        sp = L.get("split")
        if sp:
            groups = [int(x) for x in sp.get("groups", [])]
            if len(groups) < 2 or len(groups) > 3 or sum(groups) != n:
                raise BuildError("%s: split groups %s must be 2 or 3 counts adding up to %d" % (name, groups, n))
            p["split"] = {"legs": int(sp.get("legs", legs)), "groups": groups,
                          "group_legs": int(sp.get("group_legs", 1))}
        ap = L.get("apertura")
        if ap:
            if sp:
                raise BuildError("%s: a league is split or Apertura/Clausura, not both" % name)
            try:
                po = int((ap if isinstance(ap, dict) else {}).get("playoff", PLAYOFF_SIZES[0]))
            except (TypeError, ValueError):
                raise BuildError("%s: the playoff is 8, 4 or 0 clubs" % name)
            if po not in (0,) + PLAYOFF_SIZES:
                raise BuildError("%s: the playoff is 8, 4 or 0 clubs, not %d" % (name, po))
            if 2 * rounds_of(n) > len(SPLIT_LINE) - SPLIT_SKIP:
                raise BuildError("%s: Apertura and Clausura of %d rounds each need %d dates, a season has %d"
                                 " -- 18 clubs at most" % (name, rounds_of(n), 2 * rounds_of(n),
                                                           len(SPLIT_LINE) - SPLIT_SKIP))
            p["split"] = {"legs": 1, "groups": [n], "group_legs": 1, "apertura": True}
            p["apertura"] = {"playoff": po}
        by_name[name.lower()] = p
        out.append(p)
    if sum(1 for p in out if p.get("split")) > MAX_SPLITS:
        raise BuildError("at most %d split leagues for now (the phase ids tested are 191..196)" % MAX_SPLITS)
    for p in out:
        # the points carry goes by the country's competition key, not by league (fl26swiss.c
        # split_keys): a Scottish split there would make the Clausura carry its points too
        q = next((q for q in out if p.get("apertura") and q.get("split") and not q.get("apertura")
                  and q["region"] == p["region"]), None)
        if q:
            raise BuildError("%s and %s: a country has Apertura/Clausura or a split that keeps its"
                             " points, not both" % (p["name"], q["name"]))
    for p in out:
        below = [q for q in out if q["above"] == p["rid"]]
        if below and p["exhibition"]:
            raise BuildError("%s: an exhibition league has no league below it (%s)" % (p["name"], below[0]["name"]))
        if len(below) > 1:
            raise BuildError("%s has %d leagues below it; the game follows one link"
                             % (p["name"], len(below)))
    for p in out:
        if p.get("own_cup"):
            national_cup(p, next((q for q in out if q["above"] == p["rid"]), None))
    import lbplayers
    bad = lbplayers.check(recipe)
    if bad:
        raise BuildError("player changes:\n  " + "\n  ".join(bad[:20]))
    cups, notes = ccup_plan([(p["rid"], pos, comp, 0) for p in out for pos, comp in p["europe"]])
    home = [league_cup(p, out) for p in out if p.get("league_cup")]
    home += [c for p in out if p.get("apertura") for c in playoff_cups(p)]
    home += [preseason_cup(c, k, by_name) for k, c in enumerate(recipe.get("preseason_cups") or [])]
    if len(cups) + len(home) > MAX_CCUP:
        raise BuildError("%d continental, league and pre-season cups -- fl26swiss.dll takes %d"
                         % (len(cups) + len(home), MAX_CCUP))
    return {"world": recipe["world"], "leagues": out, "edits": recipe.get("edits") or {},
            "players": recipe.get("players") or {}, "uecl": bool(recipe.get("uecl", True)),
            "ccups": cups, "ccup_notes": notes, "home_cups": home}


def league_cup(p, out):
    """the league cup of top division p: the biggest of LEAGUE_CUP_SIZES its division and the
    ones below it (the recipe's) have clubs for, by league position, the strongest v the weakest"""
    field, q = [], p
    while q and len(field) < LEAGUE_CUP_SIZES[0]:
        field += [(q["rid"], pos) for pos in range(1, q["clubs"] + 1)]
        q = next((b for b in out if b["above"] == q["rid"]), None)
    size = next(s for s in LEAGUE_CUP_SIZES if s <= len(field))
    field = field[:size]
    field = [field[j] for i in range(size // 2) for j in (i, size - 1 - i)]
    return {"name": p["league_cup"]["name"], "code": "FL_%03d_LCUP" % p["rid"], "kind": "league",
            "country": p["country"], "region": p["region"], "groups": 0, "entry": field,
            "opts": {"fill": 0, "national": 1, "days": LEAGUE_CUP_DAYS}}


def rounds_of(clubs):
    """a single round robin's rounds"""
    return clubs if clubs % 2 else clubs - 1


def season_ord(day):
    """a day of the year as a place in the season, which turns in July (SEASON_TURN)"""
    return day - SEASON_TURN if day >= SEASON_TURN else day + 365 - SEASON_TURN


def season_day(o):
    d = o + SEASON_TURN
    return d - 365 if d > 365 else d


def split_days(n1, n2):
    """the days fl26swiss gives a split's rounds (split_dates, up to 38 rounds): the regular
    phase's n1 and the group's n2"""
    t = n1 + n2
    line = SPLIT_LINE[min(SPLIT_SKIP, len(SPLIT_LINE) - t):]
    last = len(line) - 1
    at = lambda i: line[(i * last * 2 + (t - 1)) // (2 * (t - 1))]
    return [at(i) for i in range(n1)], [at(i) for i in range(n1, t)]


def playoff_days(after, busy, count=7):
    """`count` days after day `after`, in season order: none the day before, of or after a busy
    day, three days apart, the first three days after `after` (the fill window)"""
    b = {season_ord(d) for d in busy}
    out, o = [], season_ord(after) + 3
    while len(out) < count:
        if o > 364:
            raise BuildError("no free days for a playoff after day %d" % after)
        if not any(abs(o - x) <= 1 for x in b) and (not out or o - out[-1] >= 3):
            out.append(o)
        o += 1
    return [season_day(o) for o in out]


def playoff_cups(p):
    """the Apertura and Clausura playoffs of league p: the first `playoff` clubs of each phase,
    the strongest v the weakest, filled the day after the phase's last round and played on
    free days after it. The entries name the league until build() has the phase ids (mksplit)."""
    k = p["apertura"]["playoff"]
    if not k:
        return []
    ap, cl = split_days(rounds_of(p["clubs"]), rounds_of(p["clubs"]))
    busy = ap + cl + (CCUP_DAYS if p.get("europe") else []) + (LEAGUE_CUP_DAYS if p.get("league_cup") else [])
    out = []
    for part, (days_of, tag) in enumerate(((ap, "Apertura"), (cl, "Clausura"))):
        days = playoff_days(days_of[-1], busy)
        busy = busy + days
        order = [pos for i in range(k // 2) for pos in (i + 1, k - i)]
        out.append({"name": "%s %s Playoffs" % (p["name"], tag), "code": "FL_%03d_%sPO" % (p["rid"], tag[0]),
                    "kind": "playoff", "country": p["country"], "region": p["region"], "groups": 0,
                    "league": p["rid"], "phase": part, "entry": [(p["rid"], pos) for pos in order],
                    "opts": {"fill": season_day(season_ord(days_of[-1]) + 1), "national": 1, "days": days}})
    return out


def preseason_cup(c, k, by_name):
    """a pre-season cup of the recipe's preseason_cups: its invited clubs, as references until
    build() knows the new clubs' ids, and its host -- the league of its first new club"""
    name = str(c.get("name") or "").strip() or "Pre-season Cup %d" % (k + 1)
    refs, host = [], None
    for x in c.get("clubs") or []:
        s = str(x).strip()
        if s.isdigit():
            refs.append(int(s))
            continue
        lg, _sl, i = s.rpartition("/")
        p = by_name.get(lg.strip().lower())
        if p is None or not i.isdigit() or int(i) >= p["clubs"]:
            raise BuildError("%s: no club %r (a league of the recipe and its club, from 0, or a "
                             "club id of the game)" % (name, s))
        refs.append((p["rid"], int(i)))
        host = host or p
    if len(refs) not in (4, 8):
        raise BuildError("%s: %d clubs -- a pre-season cup has 4 or 8" % (name, len(refs)))
    if len(set(refs)) != len(refs):
        raise BuildError("%s: a club is invited twice" % name)
    if host is None:
        raise BuildError("%s: at least one club from a league of the recipe (the host)" % name)
    return {"name": name, "code": "FL_PRE%d" % (k + 1), "kind": "preseason",
            "country": host["country"], "region": host["region"], "groups": 0,
            "entry": [(host["rid"], pos) for pos in range(1, len(refs) + 1)], "refs": refs,
            "opts": {"fill": PRESEASON_FILL, "national": 1, "days": PRESEASON_DAYS}}


def national_cup(p, below):
    """pick the shipped cup to copy for league p's national cup (p["own_cup"]), with the league
    below it (or None): the two divisions' clubs when a cup of that size exists, else the top
    division's, the second one kept out of it"""
    c = p["own_cup"]
    two = p["clubs"] + below["clubs"] if below else 0
    if two in NATIONAL_CUPS_TWO:
        c["like"], c["bracket"] = NATIONAL_CUPS_TWO[two]
        c["clubs"], c["keep_top"] = two, False
    elif p["clubs"] in NATIONAL_CUPS:
        c["like"], c["bracket"] = NATIONAL_CUPS[p["clubs"]]
        c["clubs"], c["keep_top"] = p["clubs"], bool(below)
    else:
        raise BuildError("%s: a national cup needs a top division of %s clubs%s" % (
            p["name"], ", ".join(map(str, sorted(NATIONAL_CUPS))),
            " (or %s with the division below)" % " / ".join(map(str, sorted(NATIONAL_CUPS_TWO)))))
    c["below"] = below["rid"] if below else None


def ccup_plan(own):
    """the continental cups the new leagues' places lead to (competitions 6..9, fl26world.CCUPS),
    each only when some place names it. The field is the places of the world's own leagues and,
    where the cup has them, shipped leagues' places after those: the biggest of 32/16/8/4 clubs
    that there are clubs for, the world's own always in. Pots in the order a league's places
    come -- every league's best place in pot 1, then the next ... -- so two clubs of a league do
    not start in the same pot. 8 or more clubs play groups of four, then a knockout of the first
    two; 4 play a knockout. Returns ([{number, name, code, conf, groups, entry}], notes)."""
    cups, notes = [], []
    for c, name, code, conf, fill in fl26world.CCUPS:
        mine = sorted(((r, pos) for r, pos, comp, _a in own if comp == c), key=lambda e: e[1])
        if not mine:
            continue
        size = next((s for s in CCUP_SIZES if s <= len(mine) + len(fill)), 0)
        if not size:
            notes.append("%s: %d place(s), and a cup needs 4 clubs -- not built" % (name, len(mine)))
            continue
        if len(mine) > size:
            notes.append("%s: %d places, the cup takes %d -- the last %d get none"
                         % (name, len(mine), size, len(mine) - size))
            mine = mine[:size]
        field = mine + [e for e in fill if e not in mine][:size - len(mine)]
        seen, ranked = {}, []
        for i, (r, pos) in enumerate(field):
            seen[r] = seen.get(r, -1) + 1
            ranked.append((seen[r], i, (r, pos)))
        field = [e for _k, _i, e in sorted(ranked)]
        if size < 8:            # a knockout pairs entries in order: the strongest v the weakest
            field = [field[j] for i in range(size // 2) for j in (i, size - 1 - i)]
        cups.append({"number": c, "name": name, "code": code, "conf": conf,
                     "groups": size // 4 if size >= 8 else 0, "entry": field})
    return cups, notes


def europe_problems(clubs, europe):
    """what is wrong with a league's European places ([[position, competition], ...]): each a
    position of the league's own, 1..clubs, none twice, and a competition fl26swiss knows"""
    out, seen = [], set()
    comps = {c for c, _n in fl26world.COMPETITIONS}
    for e in europe:
        try:
            pos, comp = int(e[0]), int(e[1])
        except (TypeError, ValueError, IndexError):
            out.append("%r is not a position and a competition" % (e,))
            continue
        if not 1 <= pos <= clubs:
            out.append("position %d -- the league has %d clubs" % (pos, clubs))
        if pos in seen:
            out.append("position %d is listed twice" % pos)
        seen.add(pos)
        if comp not in comps:
            out.append("competition %d is not one of %s" % (comp, ", ".join(str(c) for c in sorted(comps))))
    return out


def own_places(pl):
    """(regulation, position, competition, alt) for the new leagues' European places"""
    return [(p["rid"], pos, comp, 0) for p in pl["leagues"] for pos, comp in p.get("europe") or []]


def order_by_parents(leagues):
    """recipe indices, every league after the league named above it"""
    names = {L.get("name", "").strip().lower(): i for i, L in enumerate(leagues)}
    done, order = set(), []

    def visit(i, path):
        if i in done:
            return
        if i in path:
            raise BuildError("the leagues above each other go round in a circle: %s"
                             % " -> ".join(leagues[j]["name"] for j in path + [i]))
        up = leagues[i].get("above")
        if isinstance(up, str) and up.strip().lower() in names:
            visit(names[up.strip().lower()], path + [i])
        done.add(i)
        order.append(i)
    for i in range(len(leagues)):
        visit(i, [])
    return order


def describe(pl):
    e = pl.get("edits") or {}
    lines = ["world %s: %d new leagues, changes to %d of the game's leagues and %d of its clubs"
             % (pl["world"], len(pl["leagues"]), len(e.get("leagues") or {}), len(e.get("clubs") or {}))]
    lines.append("  Conference League: %s" % ("yes (competition %d, regulations %d/%d)"
                                              % (UECL_CID, mkuecl.REG, mkuecl.KO) if pl.get("uecl") else "no"))
    squads = pl.get("players") or {}
    if squads:
        lines.append("  player changes in %d clubs" % len(squads))
    for p in pl["leagues"]:
        shape = "%d clubs x%d" % (p["clubs"], p["legs"])
        if p.get("apertura"):
            shape = "Apertura + Clausura, %d clubs x1 each" % p["clubs"]
        elif p.get("split"):
            s = p["split"]
            shape += ", then %s x%d" % (" / ".join(map(str, s["groups"])), s["group_legs"])
        lines.append("  %-26s reg %3d  comp %3d  region %2d  slot %3s  division %d%s  %s%s"
                     % (p["name"], p["rid"], p["cid"], p["region"],
                        "-" if p["slot"] == fl26world.NO_SLOT else p["slot"], p["tier"],
                        "  below %d (%d up/down)" % (p["above"], p["exchange"]) if p["above"] else "",
                        shape, "  EXHIBITION ONLY (not in Master League)" if p.get("exhibition") else ""))
        if p.get("europe"):
            names = dict(fl26world.COMPETITIONS)
            lines.append("      European places: %s" % ", ".join(
                "%d. %s" % (pos, names.get(comp, comp)) for pos, comp in sorted(p["europe"])))
    if pl["leagues"] and not own_places(pl):
        lines.append("  no European places: the new leagues send nobody to Europe")
    if any(e[2] == 4 for e in own_places(pl)):
        # issue #33: the qualifying round has no stand-in club for ours to replace
        lines.append("  NOTE: Libertadores qualifying places are not filled yet; those clubs stay at home")
    if not pl.get("uecl") and any(e[2] == 2 for e in own_places(pl)):
        lines.append("  NOTE: Conference League places, but the world gets no Conference League")
    names = dict(fl26world.COMPETITIONS)
    for c, n in sorted(fl26world.uefa_places(own_places(pl))[1].items()):
        lines.append("  NOTE: %s has %d places listed for %d clubs; the last %d get none"
                     % (names[c], n, fl26world.FIELD, n - fl26world.FIELD))
    for p in pl["leagues"]:
        c = p.get("own_cup")
        if c:
            lines.append("  %s: national cup of %d clubs (copied from %s)%s" % (
                c["name"], c["clubs"], c["like"], ", the top division only" if c["keep_top"] else ""))
            if c.get("super"):
                lines.append("  %s: super cup, the champion v the cup winner (copied from %s)"
                             % (c["super"], SUPER_CUP_LIKE))
    for cup in pl.get("ccups") or []:
        lines.append("  %s: %d clubs, %s" % (cup["name"], len(cup["entry"]),
                                             "%d groups of four, then a knockout of %d"
                                             % (cup["groups"], 2 * cup["groups"]) if cup["groups"]
                                             else "a knockout"))
    for note in pl.get("ccup_notes") or []:
        lines.append("  NOTE: " + note)
    for cup in pl.get("home_cups") or []:
        what = {"league": "league cup", "playoff": "playoff, filled on day %d" % cup["opts"]["fill"]}
        lines.append("  %s: %s, a knockout of %d clubs" % (
            cup["name"], what.get(cup["kind"], "pre-season cup in July"), len(cup["entry"])))
    return "\n".join(lines)


# ---- build: tables, squads, splits, world file ----

def club_name(p, k):
    names = p["club_names"]
    if k < len(names) and names[k].strip():
        return names[k].strip()
    return "%s %02d" % (p["name"][:M.NAME_SLOT - 4], k + 1)


def abbr(name, used):
    letters = ascii_letters(name)
    for cand in (letters[:3], letters[:2] + letters[-1:], letters[:1] + letters[-2:]):
        if len(cand) == 3 and cand not in used:
            used.add(cand)
            return cand
    for n in range(1000):
        cand = "%s%02d" % (letters[:1] or "C", n % 100)
        if cand not in used:
            used.add(cand)
            return cand
    return "CLB"


# Country.bin +5 is the country's confederation, in the code Competition.bin +6 uses in its low
# three bits: 2 UEFA, 3 AFC, 4 CONMEBOL, 5 CAF, 6 CONCACAF, 7 OFC (Croatia 2, Japan and the UAE 3,
# Peru 4, Egypt 5, Mexico 6, New Zealand 7). Every league used to be copied from the Premier
# League's row and so came out UEFA wherever it was: a UAE league sat in the Champions League's
# Select Team list and a Peruvian one showed UEFA competitions (Evo-Web, 2026-09-28).
CONFED_OFF, CONFED_MASK = 5, 7


def kickoff_after(p, mine, confed):
    """the slot league p follows in the Kick Off list: the league above it, else the end of its
    continent's leagues (KICKOFF_AFTER)"""
    up = p.get("above")
    if up:
        q = mine.get(up)
        if q and q.get("slot") not in (None, fl26world.NO_SLOT):
            return q["slot"]
        if up in SHIPPED_SLOT:
            return SHIPPED_SLOT[up]
    return KICKOFF_AFTER.get(confed.get(p["country"]), KICKOFF_OTHER)


def confederations(base):
    """{flag id: confederation code} from Country.bin"""
    path = os.path.join(base, "Country.bin")
    if not os.path.exists(path):
        return {}
    raw = pesdb.wesys_unpack(open(path, "rb").read())
    out = {}
    for r in pesdb.rows(raw, 1420):
        fid = (int.from_bytes(r[:4], "little") >> 10) & 0x1ff
        if 2 <= r[CONFED_OFF] <= 7:
            out[fid] = r[CONFED_OFF]
    return out


def country_confederations(base):
    """{country name as country_names() gives it: confederation code} -- 2 UEFA, 3 AFC, 4 CONMEBOL,
    5 CAF, 6 CONCACAF, 7 OFC"""
    import mkflags
    cty = mkflags.countries(mkflags.table("Country", [base]))
    conf = confederations(base)
    return {mkflags.title(en): conf[fid] for fid, (en, names) in cty.items()
            if en and fid in conf and mkflags.by_name(cty, en) == fid}


def build(pl, base, game, replace=False, log=print):
    out = os.path.join(siderdir.find(game), "livecpk", pl["world"])
    if os.path.exists(out):
        if not replace:
            raise BuildError("%s exists -- build with replace to rebuild it" % out)
        if not os.path.exists(os.path.join(out, MARK)):
            raise BuildError("%s was not made by the league builder (no %s) -- left alone" % (out, MARK))
    tmp = out + ".building"
    if os.path.exists(tmp):
        shutil.rmtree(tmp)
    db = os.path.join(tmp, "common", "etc", "pesdb")
    os.makedirs(db)

    comp, regs, ents = (M.load(base, n) for n in
                        ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin"))
    raw = bytearray(pesdb.wesys_unpack(open(os.path.join(base, "Team.bin"), "rb").read()))
    nteam = len(raw) // W.T_REC
    top_id = max(int.from_bytes(raw[i * W.T_REC + W.T_ID:i * W.T_REC + W.T_ID + 4], "little") for i in range(nteam))
    top_alt = max(int.from_bytes(raw[i * W.T_REC + W.T_ALT:i * W.T_REC + W.T_ALT + 4], "little") for i in range(nteam))
    proto = raw[(nteam - 1) * W.T_REC:nteam * W.T_REC]
    made, used_abbr = 0, set()
    confed = confederations(base)

    for p in pl["leagues"]:
        teams, p["abbrs"] = [], []
        for k in range(p["clubs"]):
            r = bytearray(proto)
            tid = top_id + 1 + made
            r[W.T_ID:W.T_ID + 4] = tid.to_bytes(4, "little")
            r[W.T_ALT:W.T_ALT + 4] = (top_alt + 1 + made).to_bytes(4, "little")
            M.put(r, W.T_NAME, club_name(p, k), W.T_NAME_LEN)
            mine = (p.get("club_abbrs") or [])[k:k + 1]
            if mine and mine[0].strip():
                short = short_name(mine[0])
                used_abbr.add(short)
            else:
                short = abbr(club_name(p, k), used_abbr)
            r[W.T_ABBR:W.T_ABBR + W.T_ABBR_LEN] = short.ljust(W.T_ABBR_LEN, bytes(1).decode()).encode("ascii")
            raw += r
            teams.append(tid)
            p["abbrs"].append(r[W.T_ABBR:W.T_ABBR + W.T_ABBR_LEN].split(bytes(1))[0].decode("ascii"))
            made += 1
        p["teams"] = teams
        M.add_league(comp, regs, ents, p["cid"], p["rid"], M.enc_region(p["region"]), p["name"],
                     "FL_%03d_LEAGUE" % p["rid"], teams, quiet=True, tier=p["tier"])
        conf = confed.get(p["country"])
        if conf:
            co = len(comp) - M.COMP + M.FLAG_OFF          # the row add_league just appended
            comp[co] = (comp[co] & ~CONFED_MASK) | conf
        rows = {u16(regs[i * M.REG:], M.R_ID): i for i in range(len(regs) // M.REG)}
        o = rows[p["rid"]] * M.REG
        g = regs[o:o + M.REG]
        if p["above"]:
            po = rows[p["above"]] * M.REG
            # the child takes its parent's calendar shape, as deepen.py does, then its own
            # division and legs; the link is written both ways
            struct.pack_into("<I", g, 0x10, struct.unpack_from("<I", regs, po + 0x10)[0])
            M.set_tier(g, p["tier"])
            g[R_ABOVE:R_ABOVE + 2] = p["above"].to_bytes(2, "little")
            regs[po + M.R_BELOW:po + M.R_BELOW + 2] = p["rid"].to_bytes(2, "little")
        rules = int.from_bytes(g[0x10:0x14], "little")
        rules = (rules & ~(LEGS_MASK << LEGS_SHIFT)) | (p["legs"] << LEGS_SHIFT)
        g[0x10:0x14] = rules.to_bytes(4, "little")
        regs[o:o + M.REG] = g
        log("  %-26s reg %d, %d clubs %d-%d" % (p["name"], p["rid"], len(teams), teams[0], teams[-1]))

    apply_edits(pl.get("edits") or {}, raw, regs, log)
    open(os.path.join(db, "Team.bin"), "wb").write(pesdb.wesys_pack(bytes(raw)))
    cpath = os.path.join(base, "Coach.bin")
    if os.path.exists(cpath):
        craw = open(cpath, "rb").read()
        coaches = pesdb.wesys_unpack(craw)
        named = {t: (p.get("club_coaches") or [])[k].strip() for p in pl["leagues"]
                 for k, t in enumerate(p["teams"])
                 if k < len(p.get("club_coaches") or []) and (p["club_coaches"][k] or "").strip()}
        add, st = mkcoaches.add_coaches(coaches, bytes(raw), top_id + 1, names=named)
        open(os.path.join(db, "Coach.bin"), "wb").write(pesdb.wesys_pack(coaches + add, craw[:3]))
        log("  %d managers" % st["added"])
    with contextlib.redirect_stdout(io.StringIO()):
        M.write_tables(tmp, comp, regs, ents)

    if made:
        import mkplayers
        call(mkplayers, ["--base", base, "--out", tmp, "--per", SQUAD, "--cap", PLAYER_CAP])
        log("  squads of %d for %d clubs" % (SQUAD, made))
    import lbplayers
    faces = []
    lbplayers.apply(pl, base, db, PLAYER_CAP, log, faces)
    if faces:
        import lbfaces
        for n, (pid, folder) in enumerate(faces):
            lbfaces.install(tmp, pid, folder, n, log)

    splits = [p for p in pl["leagues"] if p.get("split")]
    if splits:
        import mksplit
        args = ["--base", db, "--out", tmp]
        for p in splits:
            s = p["split"]
            args += ["--split", "%d:%dx%d:%s%s" % (p["rid"], p["clubs"], s["legs"],
                                                   ":".join("%dx%d" % (c, s["group_legs"]) for c in s["groups"]),
                                                   "@Apertura,Clausura" if s.get("apertura") else "")]
        said = call(mksplit, args)
        log("  %d split season(s)" % len(splits))
        import re
        phases = {int(m.group(1)): [int(x) for x in m.group(2).split(",")] for m in
                  re.finditer(r"^reg (\d+) .*-> split total over \d+ clubs, phases ([\d,]+)", said, re.M)}
        for cup in pl.get("home_cups") or []:
            if cup.get("kind") == "playoff":
                ph = phases.get(cup["league"]) or []
                if len(ph) < 2:
                    raise BuildError("mksplit gave %d no Apertura and Clausura:\n%s" % (cup["league"], said))
                cup["entry"] = [(ph[cup["phase"]], pos) for _r, pos in cup["entry"]]

    uecl = europe(tmp, db, log) if pl.get("uecl") else []
    national_cups(pl, tmp, db, log)
    ccups = continental((pl.get("ccups") or []) + home_cups(pl, confed), tmp, db, log)

    # the world file: the tables' own reading (fl26world.from_tables), with what the recipe
    # knows better -- the country chosen, and how many clubs go up and down
    with contextlib.redirect_stdout(io.StringIO()):
        leagues, split_lines = fl26world.from_tables(tmp, base)
    # Apertura/Clausura: the Clausura starts from zero (fl26swiss leaves its key out of the carry)
    ap_ids = {p["rid"] for p in pl["leagues"] if p.get("apertura")}
    split_lines = [tuple(s) + ("carry=0",) if s[0] in ap_ids else s for s in split_lines]
    mine = {p["rid"]: p for p in pl["leagues"]}
    for L in leagues:
        p = mine.get(L["id"])
        if not p:
            continue
        L["country"] = p["country"]
        L["slot"] = p["slot"]
        if p["slot"] != fl26world.NO_SLOT:
            L["kickoff"] = kickoff_after(p, mine, confed)
        if p.get("exhibition"):
            L["exhibition"] = 1                        # fl26joindll leaves it out of the season
        if p["above"]:
            L["above"], L["promote"] = p["above"], p["exchange"]
        else:
            L.pop("above", None)
            L["promote"] = 0
        below = next((q for q in pl["leagues"] if q["above"] == p["rid"]), None)
        L["demote"] = below["exchange"] if below else 0
        if p.get("cup"):
            L["cup"] = p["cup"]
        if p.get("scup"):
            L["scup"] = p["scup"]
        up = mine.get(p["above"]) if p["above"] else None
        if up and up.get("own_cup", {}).get("keep_top"):
            L["cup"] = up["own_cup"]["reg"]            # fl26chain keeps the cup to the top league
    uefa, over = fl26world.uefa_places(own_places(pl))
    names = dict(fl26world.COMPETITIONS)
    for c, n in sorted(over.items()):
        log("  NOTE: %s has %d places listed for %d clubs; the last %d get none"
            % (names[c], n, fl26world.FIELD, n - fl26world.FIELD))
    if uefa:
        log("  European places: %d of the new leagues, %d in all"
            % (sum(1 for e in own_places(pl) if e[2] in fl26world.UEFA_LINE), len(uefa)))
    fl26world.write_world(os.path.join(tmp, MARK), pl["world"], leagues, split_lines, uefa, uecl,
                          ccups + dates_lines(pl, db) + order_lines(pl, base, confed))
    json.dump(pl, open(os.path.join(tmp, "leaguebuilder-plan.json"), "w", encoding="utf-8"), indent=1)

    pictures(pl, tmp, base, log)
    region_modules(pl, tmp, game, log)

    if os.path.exists(out):
        shutil.rmtree(out)
    os.rename(tmp, out)
    log("built %s: %d leagues, %d clubs" % (out, len(pl["leagues"]), made))
    return out


def europe(root, db, log=print):
    """the Conference League in the world being built (tables in <db>, the world folder <root>):
    the Champions League and Europa League league phase as one group of 36, then mkuecl's clone
    of the Europa League and mkeuropo's play-offs, each in place. Returns the entrants."""
    import mkreshape, mkeuropo
    args = ["--base", db, "--out", root]
    for r in RESHAPE:
        args += ["--reshape", r]
    said = call(mkreshape, args)
    for row in (1027, 1029):
        if "replica %d kept: 36 clubs" % row not in said:
            raise BuildError("the league phase reshape did not give group %d 36 clubs:\n%s" % (row, said))
    log("  Champions League and Europa League: league phase of 36 (groups 1027, 1029)")
    try:
        clubs = mkuecl.build(db, root, log=log)
        mkeuropo.build(db, root, log=log)
    except SystemExit as e:
        raise BuildError("Conference League: %s" % e)
    return clubs


def free_comp_ids(db, reserved=()):
    """competition ids and regulation ids (from CCUP_REG_FROM) nothing in the world's tables in
    <db> uses, nor anything kept for later"""
    comp, regs = M.load(db, "Competition.bin"), M.load(db, "CompetitionRegulation.bin")
    used_cid = {comp[i + M.CID_OFF] for i in range(0, len(comp), M.COMP)}
    used_reg = {u16(regs[i:], M.R_ID) & 0x3ff for i in range(0, len(regs), M.REG)}
    taken = (used_reg | CCUP_KEEP | W.BAD_REG | set(W.MOVED_REG.values()) | set(fl26world.DEFAULT_SLOT)
             | set(fl26world.NO_SLOT_IDS) | set(reserved))
    return ([c for c in range(CID_FROM, W.CID_MAX + 1) if c not in used_cid and c != UECL_CID],
            [r for r in range(CCUP_REG_FROM, 1024) if r not in taken])


def like_reg(db, code):
    """the regulation id of the shipped competition coded `code` (its first row)"""
    comp, regs = M.load(db, "Competition.bin"), M.load(db, "CompetitionRegulation.bin")
    cid = next((comp[i * M.COMP + M.CID_OFF] for i in range(len(comp) // M.COMP)
                if comp[i * M.COMP + M.CODE_OFF:].split(b"\0")[0].decode("latin1") == code), None)
    return next((u16(regs[i * M.REG:], M.R_ID) for i in range(len(regs) // M.REG)
                 if cid is not None and regs[i * M.REG + M.R_CID] == cid), None)


# The Select Team list is ordered by region first, in the order of a list of 28 region ids in
# the exe (0x1427d5760; the comparator 0x140eadae0): the club competitions, then Europe, Latin
# America and Asia, each alphabetical with its "other" group last. fl26catlist.lua copies that
# list and appended our regions 29..63 after it, so a new country came after Thailand whatever
# its name. The `order` line puts each of our countries in its continent, by name.
SHIPPED_REGIONS = [                       # (region, name, confederation); None = a group
    (1, None, 0), (26, None, 0),
    (8, "Belgium", 2), (12, "Denmark", 2), (2, "England", 2), (3, "France", 2), (5, "Italy", 2),
    (7, "Netherlands", 2), (6, "Portugal", 2), (9, "Russia", 2), (15, "Scotland", 2),
    (4, "Spain", 2), (10, "Switzerland", 2), (27, "Turkey", 2), (22, None, 2),
    (17, "Argentina", 4), (16, "Brazil", 4), (18, "Chile", 4), (19, "Colombia", 4), (23, None, 4),
    (21, "China", 3), (28, "Thailand", 3), (24, None, 3),
    (25, None, 9),
]
CONTINENT = {2: 2, 3: 3, 4: 4, 6: 4, 7: 3, 5: 5}   # confederation -> block: CONCACAF with the
                                                    # Americas, OFC with Asia, CAF a block of its own


def order_lines(pl, base, confed):
    """the world file's `order` line: the Select Team list's region order with our countries
    in it (see SHIPPED_REGIONS)"""
    names = dict((fid, nm) for nm, fid in country_ids(base))
    shipped = {r for r, _, _ in SHIPPED_REGIONS}
    ours = {}
    for p in pl["leagues"]:
        r = p["region"]
        if r in shipped or r in ours or p.get("exhibition"):
            continue
        ours[r] = (names.get(p["country"], "~"), CONTINENT.get(confed.get(p["country"]), 5))
    if not ours:
        return []
    out = []
    for block in (2, 4, 3, 5):
        named = [(nm, r) for r, nm, c in SHIPPED_REGIONS if c == block and nm]
        named += [(nm, r) for r, (nm, c) in ours.items() if c == block]
        group = [r for r, nm, c in SHIPPED_REGIONS if c == block and not nm]
        out += [r for nm, r in sorted(named, key=lambda x: x[0].lower())] + group
        if block == 2:
            out = [1, 26] + out
    out.append(25)
    return ["order " + ",".join(map(str, out))]


def dates_lines(pl, db):
    """world file lines `dates <our cup> like=<shipped cup>`: the game dates a cup's rounds by its
    regulation id, in a switch over the shipped ids 2..175, so a national cup or super cup of
    ours (id 176 and up) got its draw but not one date, and was never played (CUPT world,
    2026-09-28: 197 and 198, 20 records, all undated). fl26swiss.dll asks the game for the dates
    of the cup it was copied from instead."""
    out = []
    for p in pl["leagues"]:
        c = p.get("own_cup")
        if not c or not c.get("reg"):
            continue
        for reg, code in ((c["reg"], c["like"]), (c.get("super_reg"), SUPER_CUP_LIKE if c.get("super") else None)):
            like = like_reg(db, code) if reg and code else None
            if like:
                out.append("dates %d like=%d" % (reg, like))
    return out


def national_cups(pl, root, db, log=print):
    """the national cups planned (national_cup) into the world's tables, one mkcup.py each"""
    import mkcup
    for p in pl["leagues"]:
        c = p.get("own_cup")
        if not c:
            continue
        cids, regs = free_comp_ids(db)
        if not cids or not regs:
            raise BuildError("no free competition or regulation ids left for %s" % c["name"])
        teams = list(p["teams"])
        if not c["keep_top"] and c["below"]:
            teams += next(q["teams"] for q in pl["leagues"] if q["rid"] == c["below"])
        c["cid"], c["reg"] = cids[0], regs[0]
        call(mkcup, ["--base", db, "--out", root, "--teams", ",".join(map(str, teams)),
                     "--cid", c["cid"], "--reg", c["reg"], "--region", p["region"], "--name", c["name"],
                     "--code", "FL_%03d_CUP" % p["rid"], "--like", c["like"], "--bracket", c["bracket"]])
        log("  %s: competition %d, regulation %d, %d clubs (copied from %s)"
            % (c["name"], c["cid"], c["reg"], len(teams), c["like"]))
        if c.get("super"):
            cids, regs = free_comp_ids(db)
            c["super_cid"], c["super_reg"] = cids[0], regs[0]
            call(mkcup, ["--base", db, "--out", root, "--teams", ",".join(map(str, p["teams"][:2])),
                         "--cid", cids[0], "--reg", regs[0], "--region", p["region"], "--name", c["super"],
                         "--code", "FL_%03d_SUPER" % p["rid"], "--like", SUPER_CUP_LIKE, "--bracket", 2])
            log("  %s: competition %d, regulation %d (copied from %s)"
                % (c["super"], cids[0], regs[0], SUPER_CUP_LIKE))


def continental(cups, root, db, log=print):
    """build the planned continental cups (ccup_plan) with mkccup.py into the world's tables in
    <db>, with ids nothing in them uses; returns the world file's ccup lines"""
    if not cups:
        return []
    import mkccup
    cids, free = free_comp_ids(db)
    if len(cids) < len(cups) or len(free) < sum(2 if c["groups"] else 1 for c in cups):
        raise BuildError("no free competition or regulation ids left for the continental cups")
    args = ["--base", db, "--out", root]
    for k, cup in enumerate(cups):
        reg = free.pop(0)
        ko = free.pop(0) if cup["groups"] else reg        # a straight knockout is one regulation
        cup.update(cid=cids[k], reg=reg, ko=ko)
        args += ["--cup", "|".join(str(x) for x in (
            cup["name"], cup["code"], cids[k], reg, ko, cup["groups"],
            ",".join("%d:%d" % tuple(e) for e in cup["entry"]),
            "" if cup.get("conf") is None else cup["conf"], cup.get("region", "")))]
    said = call(mkccup, args)
    lines = [l.strip() for l in said.splitlines() if l.startswith("ccup ")]
    if len(lines) != len(cups):
        raise BuildError("mkccup made %d of %d continental cups:\n%s" % (len(lines), len(cups), said))
    lines = [ccup_options(l, cup) for l, cup in zip(lines, cups)]
    for cup in cups:
        log("  %s: competition %d, %d clubs, %s" % (
            cup["name"], cup["cid"], len(cup["entry"]),
            "groups %d, knockout %d" % (cup["reg"], cup["ko"]) if cup["groups"] else "knockout %d" % cup["ko"]))
    return lines


def home_cups(pl, confed):
    """the league and pre-season cups planned, ready for continental(): the country's
    confederation, and the invited clubs' team ids now that build() has given them out"""
    teams = {p["rid"]: p["teams"] for p in pl["leagues"]}
    out = []
    for cup in pl.get("home_cups") or []:
        c = dict(cup, conf=confed.get(cup["country"]), opts=dict(cup["opts"]))
        if cup.get("refs"):
            c["opts"]["clubs"] = [r if isinstance(r, int) else teams[r[0]][r[1]] for r in cup["refs"]]
        out.append(c)
    return out


def ccup_options(line, cup):
    """a world file ccup line with a domestic cup's options (fl26swiss.lua reads them): the day
    it is filled on, national (no continental rule on who may play), its days, invited clubs"""
    o = cup.get("opts")
    if not o:
        return line
    words = ["fill=%d" % o["fill"], "national=%d" % o["national"],
             "days=" + ",".join(map(str, o["days"]))]
    if o.get("clubs"):
        words.append("clubs=" + ",".join(map(str, o["clubs"])))
    head, sep, name = line.partition(" name=")
    return "%s %s%s%s" % (head, " ".join(words), sep, name)


def pictures(pl, root, base, log=print):
    """league logos, club crests and kits for the new leagues (tools/lbassets.py)"""
    import lbassets
    flags = {}
    for p in pl["leagues"]:
        lbassets.league_logo(root, p["cid"], p["name"], p.get("logo"))
        if p.get("flag") and p["country"] not in flags:
            flags[p["country"]] = p["flag"]
            lbassets.country_flag(root, p["country"], p["flag"])
        crests = p.get("club_crests") or []
        for k, tid in enumerate(p["teams"]):
            pic = crests[k] if k < len(crests) else None
            lbassets.club_crest(root, tid, p["abbrs"][k], pic)
    e = pl.get("edits") or {}
    cid_of = {}
    for rid, v in (e.get("leagues") or {}).items():
        if v.get("logo"):
            if not cid_of:
                cid_of = {r: c for r, c, _, _ in game_leagues(base)}
            if int(rid) in cid_of:
                lbassets.league_logo(root, cid_of[int(rid)], v.get("name") or "", v["logo"])
    for tid, v in (e.get("clubs") or {}).items():
        if v.get("crest"):
            lbassets.club_crest(root, int(tid), "", v["crest"])
    log("  %d league logos, %d club crests%s" % (len(pl["leagues"]), sum(len(p["teams"]) for p in pl["leagues"]),
                                               ", %d country flags" % len(flags) if flags else ""))
    if not any(p["teams"] for p in pl["leagues"]):
        return
    t = tables_root(base)
    unipar = os.path.join(t, UNIPAR.replace("/", os.sep)) if t else None
    if not unipar or not os.path.exists(unipar):
        log("  no kits: the game's UniformParameter.bin was not unpacked (Unpack from game)")
        return
    import mkkits
    args = ["mkkits.py", "--team-bin", os.path.join(root, "common", "etc", "pesdb", "Team.bin"),
            "--unipar", unipar, "--root", root, "--archive"]
    if os.path.exists(os.path.join(t, KIT_TEXTURES)):
        args += ["--textures", os.path.join(t, KIT_TEXTURES)]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = mkkits.build(args)
    if rc:
        raise BuildError("kits: %s" % buf.getvalue())
    log("  kits: " + next((l.strip() for l in buf.getvalue().splitlines() if l.startswith("wrote") and "kit" in l), "written"))


def region_modules(pl, root, game, log=print):
    """fl26regions.lua and fl26regnames.lua for this world, into <world>/modules/.

    Both patch the exe with tables that name competitions and regions, so they are made per
    world (tools/mkregioncats.py, tools/mkregnames.py) and switch_on() puts them in place: the
    new leagues get their heading in the competition list, a new country a region heading of
    its own instead of the previous country's -- its own flag, drawn into the world's copy of
    the category menu by tools/mkcatflags.py. Each generator checks every byte it will
    change against the game's own exe first, so a different exe gives no module, not a bad one.
    """
    comps = sorted({p["cid"] for p in pl["leagues"]})
    if not comps:
        return
    exe = os.path.join(game, "FL_2026.exe")
    if not os.path.exists(exe):
        log("  no region headings: no %s" % exe)
        return
    import flpaths
    flpaths.EXE = exe
    d = os.path.join(root, "modules")
    os.makedirs(d, exist_ok=True)
    import mkregioncats, mkregnames, mkcatflags
    try:
        # the flag of each new country as its heading picture; mkregnames then points the
        # region at it (a country with no flag picture gets the plain international flag)
        call(mkcatflags, ["--root", root, "--game", game])
    except BuildError as e:
        log("  no flag headings: %s" % str(e).strip().splitlines()[0])
    try:
        call(mkregioncats, ["--root", root, "--comps", ",".join(map(str, comps)),
                            "--out", os.path.join(d, "fl26regions.lua"), "--write"])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = mkregnames.main(["--root", root, "--out", os.path.join(d, "fl26regnames.lua")])
        if rc:
            raise BuildError("mkregnames returned %s: %s" % (rc, buf.getvalue()))
    except (BuildError, SystemExit) as e:
        log("  no region headings: %s" % str(e).strip().splitlines()[0])
        return
    log("  region headings for %d leagues" % len(comps))


# ---- install: the modules that read a world ----

def pack_dir():
    """the module pack (tools/lbpack.py): next to the program, inside it, or the repo's build"""
    for d in (os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "pack"),
              os.path.join(getattr(sys, "_MEIPASS", HERE), "pack"),
              os.path.join(os.path.dirname(HERE), "out", "lbpack")):
        if os.path.exists(os.path.join(d, "modules.txt")):
            return d
    raise BuildError("the module pack is missing (a folder called pack next to the program)")


def ini_lines(game):
    ini = os.path.join(siderdir.find(game), "sider.ini")
    if not os.path.exists(ini):
        raise BuildError("no %s -- is Sider installed in this game folder?" % ini)
    return ini, open(ini, encoding="utf-8", errors="replace").read().splitlines()


def module_of(line):
    """the module a lua.module line names, commented out or not, and whether it is live"""
    s = line.strip()
    live = not s.startswith((";", "#"))
    s = s.lstrip(";#").strip()
    if not s.startswith("lua.module"):
        return None, False
    name = s.split("=", 1)[1].split(";")[0].strip().strip('"').lower()
    return (name[:-4] if name.endswith(".lua") else name), live


def ensure_modules(game, order, want, log=print):
    """make every module in `want` a live lua.module line of sider.ini, in `order`'s order.

    A commented-out line is switched back on where it is; a missing one goes in after the
    nearest module before it in `order` that the file already loads (or before the first after
    it). Nothing else in the file moves. Returns the modules it touched.

    A line that loads one of these modules out of a before-builder-<n> folder -- the copies
    install_modules keeps of what it replaced -- is pointed back at the module itself: the
    old copy is out of date, and its Lua looks for its DLL in modules, not next to itself
    (evo-web, 2026-09-29: every fl26 line read before-builder-1/..., LoadLibraryA failed
    with error 126 for all four DLLs, and the diagnostics said none of them was loaded)."""
    ini, lines = ini_lines(game)
    fixed, plain = [], {module_of(l)[0] for l in lines}
    for i, l in enumerate(lines):
        m, live = module_of(l)
        if not m or "\\" not in m.replace("/", "\\"):
            continue
        folder, _, base = m.replace("/", "\\").rpartition("\\")
        if base in order and folder.split("\\")[-1].startswith("before-builder"):
            # the module's own line already there: the old copy's line is only switched off
            lines[i] = ('' if live and base not in plain else ';') + 'lua.module = "%s.lua"' % base
            plain.add(base)
            fixed.append(base)
    where = {}
    for i, l in enumerate(lines):
        m, live = module_of(l)
        if m and (m not in where or live):
            where[m] = (i, live)
    done = []
    for m in [x for x in order if x in want]:
        if m in where and where[m][1]:
            continue
        if m in where:
            lines[where[m][0]] = 'lua.module = "%s.lua"' % m
        else:
            k = order.index(m)
            before = [where[x][0] for x in order[:k] if x in where and where[x][1]]
            after = [where[x][0] for x in order[k + 1:] if x in where and where[x][1]]
            if before:
                at = max(before) + 1
            elif after:
                at = min(after)
            else:
                mods = [i for i, l in enumerate(lines) if module_of(l)[0]]
                at = (mods[0] if mods else len(lines))
            lines.insert(at, 'lua.module = "%s.lua"' % m)
            where = {x: ((i + 1 if i >= at else i), lv) for x, (i, lv) in where.items()}
        where[m] = (lines.index('lua.module = "%s.lua"' % m), True)
        done.append(m)
    ext = [i for i, l in enumerate(lines) if l.strip().lstrip(";#").strip().startswith("luajit.ext.enabled")]
    if not ext or lines[ext[0]].replace(" ", "") != "luajit.ext.enabled=1":
        if ext:
            lines[ext[0]] = "luajit.ext.enabled = 1"
        else:
            on = [i for i, l in enumerate(lines) if l.replace(" ", "").startswith("lua.enabled=")]
            lines.insert(on[0] + 1 if on else len(lines), "luajit.ext.enabled = 1")
        done.append("luajit.ext.enabled")
    if fixed:
        log("sider.ini: %d module(s) were loaded from a before-builder folder, now from modules: %s"
            % (len(fixed), ", ".join(fixed)))
        done += [m for m in fixed if m not in done]
    if done:
        shutil.copy2(ini, ini + ".before-builder") if not os.path.exists(ini + ".before-builder") else None
        open(ini, "w", encoding="utf-8", newline="\r\n").write("\n".join(lines) + "\n")
        log("sider.ini: switched on %s" % ", ".join(done))
    return done


def install_modules(game, log=print):
    """put the pack's modules in the Sider folder's modules and load them from sider.ini.

    Every file it would replace is copied first into modules\\before-builder-<n>\\, and
    sider.ini into sider.ini.before-builder, so the install can be undone by hand."""
    pack = pack_dir()
    order = open(os.path.join(pack, "modules.txt"), encoding="utf-8").read().split()
    ini, _ = ini_lines(game)
    dst = os.path.join(siderdir.find(game), "modules")
    if not os.path.isdir(dst):
        raise BuildError("no %s -- is Sider installed in this game folder?" % dst)
    src = os.path.join(pack, "modules")
    changed, same = [], 0
    for f in sorted(os.listdir(src)):
        a, b = os.path.join(src, f), os.path.join(dst, f)
        if os.path.exists(b) and open(a, "rb").read() == open(b, "rb").read():
            same += 1
            continue
        changed.append(f)
    if changed:
        keep = None
        for f in changed:
            b = os.path.join(dst, f)
            if os.path.exists(b):
                if not keep:
                    n = 1
                    while os.path.exists(os.path.join(dst, "before-builder-%d" % n)):
                        n += 1
                    keep = os.path.join(dst, "before-builder-%d" % n)
                    os.makedirs(keep)
                shutil.copy2(b, os.path.join(keep, f))
            shutil.copy2(os.path.join(src, f), b)
        log("modules: %d copied, %d already there%s" % (len(changed), same,
            ("; the old ones are in " + keep) if keep else ""))
    else:
        log("modules: all %d already there" % same)
    have = {f[:-4] for f in os.listdir(dst) if f.endswith(".lua")}
    ensure_modules(game, order, [m for m in order if m in have], log)
    return changed


# ---- on: the live world ----

def switch_on(world, game, log=print):
    root = os.path.join(siderdir.find(game), "livecpk", world)
    wf = os.path.join(root, MARK)
    if not os.path.exists(wf):
        raise BuildError("%s has no %s -- not a league builder world" % (root, MARK))
    import siderroot
    siderroot.INI = os.path.join(siderdir.find(game), "sider.ini")
    if not os.path.exists(siderroot.INI):
        raise BuildError("no %s -- is Sider installed in this game folder?" % siderroot.INI)
    log(call(siderroot, [world]).strip())
    dst = os.path.join(siderdir.find(game), "modules", MARK)
    if os.path.exists(dst):
        shutil.copy2(dst, dst + ".prev")
    shutil.copy2(wf, dst)
    log("world file -> %s" % dst)
    mods = os.path.join(root, "modules")
    for f in sorted(os.listdir(mods)) if os.path.isdir(mods) else []:
        dst = os.path.join(siderdir.find(game), "modules", f)
        if os.path.exists(dst) and not os.path.exists(dst + ".before-builder"):
            shutil.copy2(dst, dst + ".before-builder")
        shutil.copy2(os.path.join(mods, f), dst)
        log("%s -> %s" % (f, dst))
    if os.path.isdir(mods):
        import lbpack
        ensure_modules(game, lbpack.ORDER, [f[:-4] for f in os.listdir(mods) if f.endswith(".lua")], log)
    missing = modules_missing(game)
    if missing:
        log("NOTE: sider.ini does not load %s -- those parts of the world will not work"
            % ", ".join(missing))


def modules_missing(game):
    ini = open(os.path.join(siderdir.find(game), "sider.ini"), encoding="utf-8", errors="replace").read()
    live = {l.split("=", 1)[1].strip().strip('"').lower()
            for l in ini.splitlines() if l.strip().startswith("lua.module")}
    return [m for m in READERS if m + ".lua" not in live]


# ---- check: did the modules take the world file? ----

def check(game, log=print):
    path = os.path.join(siderdir.find(game), "sider.log")
    wf = os.path.join(siderdir.find(game), "modules", MARK)
    want = len(fl26world.read_world(wf)[1]) if os.path.exists(wf) else None
    if not os.path.exists(path):
        raise BuildError("no %s yet -- start the game once with the world switched on" % path)
    text = open(path, encoding="utf-8", errors="replace").read().splitlines()
    ok = True
    for m in READERS:
        mine = [l for l in text if l.startswith("[%s.lua]" % m)]
        took = [l for l in mine if "world file --" in l]
        bad = [l for l in mine if any(w in l for w in ("aborting", "nothing written", "FAILED", "left alone"))]
        if not mine:
            log("  %-14s not loaded" % m)
            ok = False
        elif not took:
            log("  %-14s did NOT read the world file" % m)
            ok = False
        else:
            n = took[0].split("world file --", 1)[1].split()[0]
            same = want is None or n == str(want)
            log("  %-14s %s%s" % (m, took[0].split("world file --", 1)[1].strip(),
                                  "" if same else "   <- the file has %s" % want))
            ok = ok and same
        for l in bad:
            log("      " + l.split("] ", 1)[-1])
    log("the world works as built" if ok else "something is wrong -- see the lines above")
    return ok


def main():
    a = sys.argv[1:]
    get = lambda k: a[a.index(k) + 1] if k in a else None
    if not a or a[0] not in ("plan", "build", "on", "check"):
        print(__doc__)
        return 1
    game = get("--game") or GAME
    try:
        if a[0] == "check":
            return 0 if check(game) else 2
        if a[0] == "on":
            switch_on(a[1], game)
            return 0
        base = base_dir(get("--base"))
        pl = plan(load_recipe(a[1]), base)
        print(describe(pl))
        if a[0] == "build":
            build(pl, base, game, "--replace" in a)
        return 0
    except BuildError as e:
        print("error: %s" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
