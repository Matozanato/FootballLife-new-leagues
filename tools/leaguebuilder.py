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
  clubs       10..24, the range seasons have been played with
  legs        how many times each pair meets, 1..4
  above       a league of this recipe (by name) or a shipped regulation id (e.g. 81, Ligue 2);
              the league becomes the division below it, in its region, promotion both ways
  exchange    clubs going up and down between the two (default 3)
  split       Scottish style: a regular phase, then top/bottom groups that keep their points
              (tools/mksplit.py); "groups" are club counts adding up to "clubs"
  club_names  optional; missing names become "<league> 01", "<league> 02", ...
  europe      optional European places: [[position, competition], ...], competition 0 Champions
              League, 1 Europa League, 2 Conference League, 3 Libertadores, 4 its qualifying
              round, 5 AFC Champions League (fl26world.COMPETITIONS); each position once, and
              only the league's own (1..clubs). Written as uefa lines of the world file, after
              the shipped leagues' places (fl26world.uefa_places)
  uecl        (the recipe, not a league) true, the default: the world gets the Conference
              League -- the Champions League and Europa League league phase reshaped to one
              group of 36 (mkreshape.py), the Conference League cloned from it (mkuecl.py:
              competition 174, regulations 186/187, group 1210) and the Europa / Conference
              League play-offs (mkeuropo.py: 188, 189), the ids fl26swiss.dll and the fixture
              dates know. false: the European cups stay as the game ships them

What plan() decides, so that nothing is left to a person to get wrong:

  regulation ids   mkworld's free list, taking only ids that have a Select Team slot
                   (fl26world.DEFAULT_SLOT) -- 11, 49, 60, 61, ... -- never one of BAD_REG
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

GAME = os.environ.get("FL26_DIR", r"C:\Football Life 2026")
R_ABOVE = 0x04
LEGS_SHIFT, LEGS_MASK = 12, 7
CLUBS_MIN, CLUBS_MAX, LEGS_MAX = 10, 24, 4
REGION_FIRST, REGION_LAST = 29, 63
CID_FROM = 130
SQUAD, PLAYER_CAP = 30, 51729            # tools/mkplayers.py --per / --cap, as the guide uses
TEAM_CAP = 1536                          # clubs in all, shipped ones included
MAX_SPLITS = 2                           # split seasons tested so far: two at a time (191..196)
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
        if r in fl26world.DEFAULT_SLOT and r not in regrow:
            free.append(r)
    if leagues and len(leagues) > len(free):
        raise BuildError("%d leagues, but only %d have a Select Team place (see docs/mod-studio.md)"
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
        p = {"name": name, "country": fid, "clubs": n, "legs": legs, "rid": free[k], "cid": cids[k],
             "slot": fl26world.DEFAULT_SLOT[free[k]], "club_names": list(L.get("club_names") or []),
             "logo": L.get("logo") or None, "club_crests": list(L.get("club_crests") or []),
             "club_abbrs": list(L.get("club_abbrs") or []),
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
        sp = L.get("split")
        if sp:
            groups = [int(x) for x in sp.get("groups", [])]
            if len(groups) < 2 or len(groups) > 3 or sum(groups) != n:
                raise BuildError("%s: split groups %s must be 2 or 3 counts adding up to %d" % (name, groups, n))
            p["split"] = {"legs": int(sp.get("legs", legs)), "groups": groups,
                          "group_legs": int(sp.get("group_legs", 1))}
        by_name[name.lower()] = p
        out.append(p)
    if sum(1 for p in out if p.get("split")) > MAX_SPLITS:
        raise BuildError("at most %d split leagues for now (the phase ids tested are 191..196)" % MAX_SPLITS)
    for p in out:
        below = [q for q in out if q["above"] == p["rid"]]
        if len(below) > 1:
            raise BuildError("%s has %d leagues below it; the game follows one link"
                             % (p["name"], len(below)))
    import lbplayers
    bad = lbplayers.check(recipe)
    if bad:
        raise BuildError("player changes:\n  " + "\n  ".join(bad[:20]))
    return {"world": recipe["world"], "leagues": out, "edits": recipe.get("edits") or {},
            "players": recipe.get("players") or {}, "uecl": bool(recipe.get("uecl", True))}


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
        if p.get("split"):
            s = p["split"]
            shape += ", then %s x%d" % (" / ".join(map(str, s["groups"])), s["group_legs"])
        lines.append("  %-26s reg %3d  comp %3d  region %2d  slot %3d  division %d%s  %s"
                     % (p["name"], p["rid"], p["cid"], p["region"], p["slot"], p["tier"],
                        "  below %d (%d up/down)" % (p["above"], p["exchange"]) if p["above"] else "",
                        shape))
        if p.get("europe"):
            names = dict(fl26world.COMPETITIONS)
            lines.append("      European places: %s" % ", ".join(
                "%d. %s" % (pos, names.get(comp, comp)) for pos, comp in sorted(p["europe"])))
    if pl["leagues"] and not own_places(pl):
        lines.append("  no European places: the new leagues send nobody to Europe")
    if not pl.get("uecl") and any(e[2] == 2 for e in own_places(pl)):
        lines.append("  NOTE: Conference League places, but the world gets no Conference League")
    names = dict(fl26world.COMPETITIONS)
    for c, n in sorted(fl26world.uefa_places(own_places(pl))[1].items()):
        lines.append("  NOTE: %s has %d places listed for %d clubs; the last %d get none"
                     % (names[c], n, fl26world.FIELD, n - fl26world.FIELD))
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


def build(pl, base, game, replace=False, log=print):
    out = os.path.join(game, "SiderAddons", "livecpk", pl["world"])
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
        add, st = mkcoaches.add_coaches(coaches, bytes(raw), top_id + 1)
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
            args += ["--split", "%d:%dx%d:%s" % (p["rid"], p["clubs"], s["legs"],
                                                 ":".join("%dx%d" % (c, s["group_legs"]) for c in s["groups"]))]
        call(mksplit, args)
        log("  %d split season(s)" % len(splits))

    uecl = europe(tmp, db, log) if pl.get("uecl") else []

    # the world file: the tables' own reading (fl26world.from_tables), with what the recipe
    # knows better -- the country chosen, and how many clubs go up and down
    with contextlib.redirect_stdout(io.StringIO()):
        leagues, split_lines = fl26world.from_tables(tmp, base)
    mine = {p["rid"]: p for p in pl["leagues"]}
    for L in leagues:
        p = mine.get(L["id"])
        if not p:
            continue
        L["country"] = p["country"]
        L["slot"] = p["slot"]
        if p["above"]:
            L["above"], L["promote"] = p["above"], p["exchange"]
        else:
            L.pop("above", None)
            L["promote"] = 0
        below = next((q for q in pl["leagues"] if q["above"] == p["rid"]), None)
        L["demote"] = below["exchange"] if below else 0
    uefa, over = fl26world.uefa_places(own_places(pl))
    names = dict(fl26world.COMPETITIONS)
    for c, n in sorted(over.items()):
        log("  NOTE: %s has %d places listed for %d clubs; the last %d get none"
            % (names[c], n, fl26world.FIELD, n - fl26world.FIELD))
    if uefa:
        log("  European places: %d of the new leagues, %d in all" % (len(own_places(pl)), len(uefa)))
    fl26world.write_world(os.path.join(tmp, MARK), pl["world"], leagues, split_lines, uefa, uecl)
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


def pictures(pl, root, base, log=print):
    """league logos, club crests and kits for the new leagues (tools/lbassets.py)"""
    import lbassets
    for p in pl["leagues"]:
        lbassets.league_logo(root, p["cid"], p["name"], p.get("logo"))
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
    log("  %d league logos, %d club crests" % (len(pl["leagues"]), sum(len(p["teams"]) for p in pl["leagues"])))
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
    its own instead of the previous country's. Each generator checks every byte it will
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
    import mkregioncats, mkregnames
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
    ini = os.path.join(game, "SiderAddons", "sider.ini")
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
    it). Nothing else in the file moves. Returns the modules it touched."""
    ini, lines = ini_lines(game)
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
    if done:
        shutil.copy2(ini, ini + ".before-builder") if not os.path.exists(ini + ".before-builder") else None
        open(ini, "w", encoding="utf-8", newline="\r\n").write("\n".join(lines) + "\n")
        log("sider.ini: switched on %s" % ", ".join(done))
    return done


def install_modules(game, log=print):
    """put the pack's modules in <game>\\SiderAddons\\modules and load them from sider.ini.

    Every file it would replace is copied first into modules\\before-builder-<n>\\, and
    sider.ini into sider.ini.before-builder, so the install can be undone by hand."""
    pack = pack_dir()
    order = open(os.path.join(pack, "modules.txt"), encoding="utf-8").read().split()
    ini, _ = ini_lines(game)
    dst = os.path.join(game, "SiderAddons", "modules")
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
    root = os.path.join(game, "SiderAddons", "livecpk", world)
    wf = os.path.join(root, MARK)
    if not os.path.exists(wf):
        raise BuildError("%s has no %s -- not a league builder world" % (root, MARK))
    import siderroot
    siderroot.INI = os.path.join(game, "SiderAddons", "sider.ini")
    if not os.path.exists(siderroot.INI):
        raise BuildError("no %s -- is Sider installed in this game folder?" % siderroot.INI)
    log(call(siderroot, [world]).strip())
    dst = os.path.join(game, "SiderAddons", "modules", MARK)
    if os.path.exists(dst):
        shutil.copy2(dst, dst + ".prev")
    shutil.copy2(wf, dst)
    log("world file -> %s" % dst)
    mods = os.path.join(root, "modules")
    for f in sorted(os.listdir(mods)) if os.path.isdir(mods) else []:
        dst = os.path.join(game, "SiderAddons", "modules", f)
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
    ini = open(os.path.join(game, "SiderAddons", "sider.ini"), encoding="utf-8", errors="replace").read()
    live = {l.split("=", 1)[1].strip().strip('"').lower()
            for l in ini.splitlines() if l.strip().startswith("lua.module")}
    return [m for m in READERS if m + ".lua" not in live]


# ---- check: did the modules take the world file? ----

def check(game, log=print):
    path = os.path.join(game, "SiderAddons", "sider.log")
    wf = os.path.join(game, "SiderAddons", "modules", MARK)
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
