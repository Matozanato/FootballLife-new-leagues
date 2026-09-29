r"""python fl26world.py --root <livecpk world> [--base <pesdb dir>] [--countries FILE] [--out FILE]
                      [--uefa sider/fl26swiss.lua]
   python fl26world.py --show <fl26world.txt>

The world file: one plain-text description of the leagues a world adds, read by every module
that used to carry its own hard-coded list (fl26joindll, fl26chain, fl26comptab, fl26editlist,
fl26kickofflist, fl26catlist, fl26clubs, fl26slotnames, fl26swiss). The league builder writes
it when it builds a world; this writes it for a world that already exists, from the world's own
competition tables. See docs/mod-studio.md.

    # fl26world 1
    world _FL26BiH
    league 11 cid=130 region=60 country=198 slot=28 tier=1 promote=0 demote=2 clubs=12 legs=3 name=Premijer Liga BiH
    league 49 cid=131 region=60 country=198 slot=49 tier=2 above=11 promote=2 demote=0 clubs=16 legs=2 name=Prva Liga FBiH
    split 109 regular=191 groups=192,193
    uefa 11 1 0 0

What comes from where:
  cid, region, tier, clubs, legs, name   the world's Competition / CompetitionRegulation rows
  above                                  the league whose relegation link (+0x00) names this one,
                                         shipped or ours (Ligue 2 is above France D3)
  promote / demote                       3 over a link, 0 where there is none -- the counts every
                                         world so far has used
  slot                                   the Select Team slot the regulation id has in the exe
                                         (DEFAULT_SLOT: where fl26comptab puts it, or the exe's
                                         own row); an id not listed gets none
  country                                --countries, else guessed from the league's name against
                                         Country.bin (mkflags.py's rules)
  conf                                   the country's confederation (Country.bin +5: 2 UEFA, 3 AFC,
                                         4 CONMEBOL, 5 CAF, 6 CONCACAF, 7 OFC); the league builder
                                         writes it, this does not (a row built before Mod Studio 0.1.3 says
                                         UEFA whatever the country). fl26catlist gives a region
                                         29..63 that continent's icons on the League Info page
  kickoff                                the slot the league follows in the Kick Off / Edit team
                                         lists (fl26comptab; leaguebuilder kickoff_after)
  split                                  a split season (tools/mksplit.py): the total's row is the
                                         league line, its phases (format 12 regular, 13..15
                                         groups, same competition) the split line; carry=0 =
                                         the groups start from zero points (Apertura/Clausura)
  uefa                                   the UEFA access list: one place per line, regulation,
                                         position, competition (0 UCL, 1 UEL, 2 UECL, 3..5 the
                                         other continents), alt -- fl26swiss's ACCESS format.
                                         --uefa copies the ACCESS table of a module file; with
                                         no uefa line fl26swiss uses the DLL's own list, which
                                         knows the shipped leagues only
  uecl                                   the Conference League's first-season entrants (team ids,
                                         mkuecl.py's pick from this world); written when the
                                         world has the Conference League

"Ours" are the league regulations (type 4) the shipped tables do not have. --base is the folder
with the shipped tables (Competition*.bin, Country.bin); default FL26_PESDB, else out/base-pesdb.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pesdb
import mkleague as M

FORMAT = "# fl26world 1"
KEYS = ("cid", "region", "country", "conf", "slot", "tier", "above", "promote", "demote", "clubs", "legs",
        "cup", "exhibition", "scup", "kickoff")
NO_SLOT = 123

# The Select Team slot each regulation id mkworld hands out ends up on, in the exe's competition
# parameter table: the ones fl26comptab places (appended rows, and 49/74/100 moved, 76 reshaped)
# and the ones the exe's own row already puts somewhere visible (11 -> 28 and so on). Read off
# the comptab and editlist boot lines of sider.log, 2026-09-27. 145 and 190 share 112 on purpose
# (fl26comptab SHARED_OK); a world has one or the other.
DEFAULT_SLOT = {
    11: 28, 49: 49, 60: 40, 61: 41, 62: 42, 74: 74, 76: 80, 93: 61, 94: 62, 96: 64, 98: 66,
    100: 81, 109: 82, 110: 83, 111: 84, 112: 85, 113: 86, 114: 87, 121: 68, 138: 107, 139: 108,
    140: 109, 143: 110, 144: 111, 145: 112, 146: 113, 170: 22, 171: 29, 173: 43, 174: 69,
    176: 71, 178: 72, 179: 73, 180: 75, 181: 76, 182: 77, 190: 112,
}
# Regulation ids a world may still use, but with no Select Team slot: the league plays its season
# and is not in the Select Team / Kick Off list. Until 28 September these took slots 6, 5 and 4 --
# free in the parameter table, but the list keeps the Asia-Oceania national teams and the two
# Classic Teams entries there, so a 37th-39th league hid them (GitHub #26). fl26comptab refuses
# PROTECTED_SLOTS for the same reason, also in world files written before this.
NO_SLOT_IDS = (183, 184, 185)
PROTECTED_SLOTS = (4, 5, 6)


# The competitions of a uefa line (fl26swiss's ACCESS comment): the number is what the line
# carries, the name what a person picks.
COMPETITIONS = [(0, "Champions League"), (1, "Europa League"), (2, "Conference League"),
                (3, "Libertadores"), (4, "Libertadores qualifying"), (5, "AFC Champions League")]
UEFA_LINE = {c for c, _n in COMPETITIONS}        # the ones a uefa line carries

# Continental cups the game does not have, built by tools/mkccup.py and run by fl26swiss.dll from
# the world file's ccup lines: groups of four, then a knockout of the winners and runners-up (or a
# straight knockout of four). A league place can lead to them like to the ones above. Each: number,
# name, competition code, confederation (Competition.bin +6), and the shipped leagues' places --
# (regulation, position), strongest first -- that fill the field when the world's own leagues do
# not. A cup is built only in a world where some league names it.
_J1, _CSL, _SPL = 52, 120, 162
_BRA, _ARG, _CHI, _COL = 29, 30, 67, 168
CCUPS = [
    (6, "CAF Champions League", "FL_CAFCL", 5, []),
    (7, "CAF Confederation Cup", "FL_CAFCC", 5, []),
    (8, "AFC Champions League Two", "FL_AFCCL2", 3,
     [(r, p) for k in range(6) for r, p in ((_J1, 5 + k), (_CSL, 4 + k), (_SPL, 5 + k))]),
    (9, "Copa Sudamericana", "FL_SUDAM", 4,
     [(r, p) for k in range(8) for r, p in ((_BRA, 7 + k), (_ARG, 7 + k), (_CHI, 3 + k), (_COL, 3 + k))]),
]
COMPETITIONS += [(c, n) for c, n, _code, _conf, _fill in CCUPS]
FIELD = 36                        # clubs in each UEFA league phase; places past it get nothing

# The DLL's own access list (tools/native/fl26swiss.c, ACCESS): the shipped leagues' European
# places, which every world has under the same regulation ids. A world file with uefa lines
# replaces the DLL's list outright, so a world that adds places for its own leagues writes these
# first and its own after them (uefa_places) -- otherwise the Netherlands, Portugal, Belgium ...
# would lose their places and the big five would fill the gaps. Keep it in step with the C file.
_ENG, _ITA, _ESP, _FRA, _NED, _POR, _GER = 17, 18, 19, 20, 21, 22, 50
_GRE, _TUR, _SCO, _DEN, _BEL = 117, 118, 134, 147, 155
# The title holders first, as in the C list: the Champions League and Europa League winners
# (knockout regs 4 and 6) to the Champions League, the Conference League winner (187) to the
# Europa League; alt = the big-five league whose next club takes a place no holder is known for.
HOLDERS = [(4, 0, 0, _ENG), (6, 0, 0, _ESP), (187, 0, 1, _ITA)]
SHIPPED_ACCESS = sorted(HOLDERS + [(r, n, c, 0) for r, n, c in (
    # Champions League
    (_ENG, 1, 0), (_ITA, 1, 0), (_ESP, 1, 0), (_GER, 1, 0), (_FRA, 1, 0), (_NED, 1, 0), (_POR, 1, 0),
    (_BEL, 1, 0), (_TUR, 1, 0),
    (_ENG, 2, 0), (_ITA, 2, 0), (_ESP, 2, 0), (_GER, 2, 0), (_FRA, 2, 0), (_NED, 2, 0),
    (_ENG, 3, 0), (_ITA, 3, 0), (_ESP, 3, 0), (_GER, 3, 0), (_FRA, 3, 0),
    (_ENG, 4, 0), (_ITA, 4, 0), (_ESP, 4, 0), (_GER, 4, 0),
    (_ENG, 5, 0), (_ESP, 5, 0), (_POR, 2, 0),
    (_SCO, 1, 0), (_GRE, 1, 0),
    (_FRA, 4, 0), (_NED, 3, 0), (_BEL, 2, 0),
    # Europa League
    (_ENG, 6, 1), (_ITA, 5, 1), (_ESP, 6, 1), (_GER, 5, 1), (_FRA, 5, 1),
    (_ENG, 7, 1), (_ITA, 6, 1), (_ESP, 7, 1), (_GER, 6, 1), (_FRA, 6, 1),
    (_NED, 4, 1), (_NED, 5, 1), (_POR, 3, 1), (_POR, 4, 1), (_BEL, 3, 1), (_BEL, 4, 1),
    (_TUR, 2, 1), (_TUR, 3, 1),
    (_SCO, 2, 1), (_SCO, 3, 1),
    (_GRE, 2, 1), (_DEN, 1, 1), (_DEN, 2, 1),
    # Conference League
    (_ENG, 8, 2), (_ITA, 7, 2), (_ESP, 8, 2), (_GER, 7, 2), (_FRA, 7, 2),
    (_NED, 6, 2), (_POR, 5, 2), (_BEL, 5, 2), (_TUR, 4, 2),
    (_SCO, 4, 2), (_GRE, 3, 2),
    (_DEN, 3, 2),
)], key=lambda e: e[2])   # stable: each section's holders stay first


def uefa_places(own):
    """the uefa lines of a world whose own leagues have places: the shipped list and the world's
    places, competition by competition (Champions League first, as fl26swiss hands them out in
    list order), each competition's shipped places before the world's. own: (regulation,
    position, competition, alt) tuples. Empty when own is: no lines, and the DLL's list stands.
    Second result: {competition: places listed} for those past FIELD (the last get nothing)."""
    own = [tuple(int(x) for x in e) for e in own]
    if not own:
        return [], {}
    out = []
    for c, _n in COMPETITIONS:
        if c in UEFA_LINE:
            out += [e for e in SHIPPED_ACCESS if e[2] == c] + [e for e in own if e[2] == c]
    over = {}
    for c in (0, 1, 2):
        n = sum(1 for e in out if e[2] == c)
        if n > FIELD:
            over[c] = n
    return out, over


def read_uefa(path):
    """the uefa lines of a world file, read as fl26swiss.lua reads them:
    ^%s*uefa%s+(%d+)%s+(%d+)%s+(%d+)%s+(%d+)"""
    import re
    pat = re.compile(r"^\s*uefa\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)")
    out = []
    for line in open(path, encoding="utf-8"):
        m = pat.match(line)
        if m:
            out.append(tuple(int(x) for x in m.groups()))
    return out


# names a league is called by that Country.bin spells differently
ALIASES = {"SOUTH KOREA": "Republic of Korea", "KOREA REPUBLIC": "Republic of Korea"}


def write_world(path, name, leagues, splits=(), uefa=(), uecl=(), ccups=()):
    """leagues: list of dicts with 'id', any of KEYS, and 'name'; splits: (total, regular,
    [groups]) for the split seasons among them; uefa: (regulation, position, competition, alt)
    places; uecl: the Conference League's first-season team ids; ccups: the ccup lines as
    tools/mkccup.py prints them"""
    lines = [FORMAT, "world %s" % name]
    for L in leagues:
        parts = ["league %d" % L["id"]]
        parts += ["%s=%d" % (k, L[k]) for k in KEYS if L.get(k) is not None]
        if L.get("name"):
            parts.append("name=%s" % L["name"].replace("\n", " ").strip())
        lines.append(" ".join(parts))
    for s in splits:                     # (total, regular, [groups], extra words ...)
        total, regular, groups = s[:3]
        lines.append("split %d regular=%d groups=%s%s" % (total, regular, ",".join(map(str, groups)),
                                                          "".join(" " + w for w in s[3:])))
    for e in uefa:
        lines.append("uefa %d %d %d %d" % tuple(e))
    if uecl:
        lines.append("uecl " + " ".join(map(str, uecl)))
    lines += list(ccups)
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write("\n".join(lines) + "\n")


def read_world(path):
    """(world name, [league dicts]) -- the same reading the Lua modules do"""
    name, leagues = None, []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line.startswith("world "):
            name = line[6:].strip()
        if not line.startswith("league "):
            continue
        head, _, nm = line.partition(" name=")
        bits = head.split()
        L = {"id": int(bits[1])}
        for b in bits[2:]:
            k, _, v = b.partition("=")
            if v.lstrip("-").isdigit():
                L[k] = int(v)
        if nm:
            L["name"] = nm.strip()
        leagues.append(L)
    return name, leagues


def access_from_lua(path):
    """the { regulation, position, competition, alt } rows of `local ACCESS = {` in a module"""
    import re
    src = open(path, encoding="utf-8").read()
    m = re.search(r"^local ACCESS = \{\r?\n(.*?)^\}", src, re.S | re.M)
    if not m:
        raise SystemExit("no `local ACCESS = {` table in %s" % path)
    body = re.sub(r"--[^\n]*", "", m.group(1))
    return [tuple(int(x) for x in e) for e in re.findall(r"\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\s*\}", body)]


def base_dir(opt):
    for d in (opt, os.environ.get("FL26_PESDB"), os.path.join(HERE, "..", "out", "base-pesdb")):
        if d and os.path.exists(os.path.join(d, "CompetitionRegulation.bin")):
            return d
    raise SystemExit("no shipped tables: pass --base <folder with CompetitionRegulation.bin>")


def load(d, n):
    raw = open(os.path.join(d, n), "rb").read()
    return bytearray(pesdb.wesys_unpack(raw) if raw[3:8] == b"WESYS" else raw)


SPLIT_TOTAL, F_TOTAL, F_REGULAR, F_GROUPS = 9, 11, 12, (13, 14, 15)


def fmt(g):
    return (int.from_bytes(g[0x0c:0x10], "little") >> 12) & 0x3f


def from_tables(root, base, countries_file=None):
    """([league dicts], [splits]) for the leagues <root> adds, in regulation id order. A split
    season (tools/mksplit.py) is one league line for its total -- the row every module keys on --
    and a split line naming its phases, which are not leagues of their own to the modules."""
    p = os.path.join(root, "common", "etc", "pesdb")
    comp, regs = load(p, "Competition.bin"), load(p, "CompetitionRegulation.bin")
    shipped = {int.from_bytes(load(base, "CompetitionRegulation.bin")[i * M.REG + M.R_ID:i * M.REG + M.R_ID + 2], "little")
               for i in range(len(load(base, "CompetitionRegulation.bin")) // M.REG)}
    region = {comp[i * M.COMP + M.CID_OFF]: M.dec_region(comp[i * M.COMP + M.REGION_OFF])
              for i in range(len(comp) // M.COMP)}
    rows = [regs[i * M.REG:(i + 1) * M.REG] for i in range(len(regs) // M.REG)]
    rid = lambda g: int.from_bytes(g[M.R_ID:M.R_ID + 2], "little")
    below = {rid(g): int.from_bytes(g[M.R_BELOW:M.R_BELOW + 2], "little") for g in rows if g[M.R_TYPE] == 4}
    above = {b: a for a, b in below.items() if b}

    leagues, phases = [], {}
    for g in rows:
        i = rid(g)
        if i in shipped or g[M.R_TYPE] not in (4, SPLIT_TOTAL):
            continue
        if g[M.R_TYPE] == 4 and fmt(g) in (F_REGULAR,) + F_GROUPS:
            phases.setdefault(g[M.R_CID], []).append((fmt(g), i))
            continue
        legs = (int.from_bytes(g[0x10:0x14], "little") >> 12) & 7
        L = {"id": i, "cid": g[M.R_CID], "region": region.get(g[M.R_CID]), "tier": M.get_tier(g),
             "clubs": g[M.R_TEAMS] & 0x3f, "legs": legs or None,
             "name": pesdb.cstr(g[M.R_NAME:M.R_NAME + M.NAME_SLOT]) if hasattr(pesdb, "cstr")
                     else bytes(g[M.R_NAME:M.R_NAME + M.NAME_SLOT]).split(b"\0")[0].decode("utf-8", "replace")}
        # a link counts only downwards: the shipped J1 (52) still names 145, the old J2, as the
        # league below it, and a first division of ours on 145 must not take J1's relegated clubs
        up = above.get(i)
        if up and M.get_tier(g) >= 2:
            L["above"] = up
        L["promote"] = 3 if "above" in L else 0
        L["demote"] = 3 if below.get(i) else 0
        if i in DEFAULT_SLOT:
            L["slot"] = DEFAULT_SLOT[i]
        leagues.append(L)
    leagues.sort(key=lambda L: L["id"])
    splits = []
    for L in leagues:
        ph = sorted(phases.get(L["cid"], []))
        if ph and ph[0][0] == F_REGULAR and len(ph) > 1:
            splits.append((L["id"], ph[0][1], [p[1] for p in ph[1:4]]))

    # countries: the file first, then a guess from the name
    try:
        import mkflags
        cty = mkflags.countries(mkflags.table("Country", [base]))
    except SystemExit as e:
        print("  note: no Country.bin (%s) -- no countries" % e)
        return leagues, splits
    rules = mkflags.read_countries_file(countries_file, cty) if countries_file else []
    for L in leagues:
        fid = None
        for kind, key, f in rules:
            if (kind == "id" and key == L["id"]) or (kind == "region" and key == L.get("region")) \
                    or (kind == "name" and key == (L.get("name") or "").upper()):
                fid = f
        for alias, country in ALIASES.items():
            if fid is None and alias in (L.get("name") or "").upper():
                fid = mkflags.by_name(cty, country)
        if fid is None:
            fid, why = mkflags.guess(cty, L.get("name") or "")
            if fid is None:
                print("  %3d %-24s no country: %s" % (L["id"], L.get("name"), why))
        if fid is not None:
            L["country"] = fid
    return leagues, splits


def main():
    a = sys.argv[1:]
    get = lambda k: a[a.index(k) + 1] if k in a else None
    if get("--show"):
        name, leagues = read_world(get("--show"))
        print("world %s, %d leagues" % (name, len(leagues)))
        for L in leagues:
            print("  " + "  ".join("%s=%s" % (k, L[k]) for k in ("id",) + KEYS + ("name",) if k in L))
        return 0
    root = get("--root")
    if not root:
        print(__doc__)
        return 1
    leagues, splits = from_tables(root, base_dir(get("--base")), get("--countries"))
    out = get("--out") or os.path.join(root, "fl26world.txt")
    uefa = access_from_lua(get("--uefa")) if get("--uefa") else []
    write_world(out, os.path.basename(os.path.normpath(root)), leagues, splits, uefa)
    print("%d leagues -> %s" % (len(leagues), out))
    for L in leagues:
        print("  %3d  region %2s  tier %s  slot %3s  country %4s  %2d clubs x%s  above %-4s %s"
              % (L["id"], L.get("region"), L.get("tier"), L.get("slot", "-"), L.get("country", "-"),
                 L["clubs"], L.get("legs"), L.get("above", "-"), L.get("name")))
    for total, regular, groups in splits:
        print("  split %d: regular phase %d, groups %s" % (total, regular, " ".join(map(str, groups))))
    if uefa:
        print("  %d UEFA places" % len(uefa))
    return 0


if __name__ == "__main__":
    sys.exit(main())
