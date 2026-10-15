r"""Home stadiums of the recipe's clubs, into Stadium Server's map_teams.txt.

Mod Studio's Edit club has a Home stadium: a stadium folder of the stadium-server library, kept in
the recipe as players[club]["stadium"] = {"folder": "Region\\Stadium", "slot": "009", "name": ...},
the club being a game club's team id ("101") or a new club's "League/k".  A new club's team id is
known only once the world is built, so the lines are written when a world is switched on (and
when the live world is built again, which switches it on):

  - every line written before (it ends with "# FL26 Mod Studio: ...") goes, whatever world it
    was for, so only the live world's clubs have lines of ours;
  - a line of your own for a club that now gets one of ours is switched off (a # in front and
    OFF at its end), and switched back on when that club no longer gets ours;
  - the world's lines go at the end of the file.

A ready world (one from Import your world) is not built here, so its stadiums are picked on the
Stadiums page, Your world's clubs, and kept in livecpk\<world>\fl26stadiums.json by team id: an
entry there takes the place of the plan's, null keeps the club at the stadium the game gives it.
Find automatically proposes stadiums of this PC's library by name (suggest) for the clubs whose
stadium the library does not have under the plan's folder (0.2.4).

Without Stadium Server (SiderAddons\content\stadium-server) the lines go to SPFL26's own stadium
module, common\stadiums.lua, which reads the same files from content\stadiums (JamesNotLike,
0.1.8); with neither nothing is written.
"""
import codecs, json, os, re, shutil, unicodedata

FOLDER = os.path.join("content", "stadium-server")
OWN = os.path.join("content", "stadiums")            # SPFL26's common\stadiums.lua: same files, its own folder
FILE = "map_teams.txt"
TAG = "# FL26 Mod Studio:"
OFF = "  # (switched off by FL26 Mod Studio)"
EDITS = "fl26stadiums.json"                  # livecpk\<world>\: the stadiums picked for a ready world
LINE = re.compile(r"^\s*(#\s*)?(\d+)\s*,")


def stadium_slot(folder):
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


def find(lib, folder):
    """the folder of the stadium in this PC's library: as the world names it, else a folder of the
    same name under another region (a stadium pack moves stadiums between its region folders
    from one version to the next); None when the player does not have that stadium -- the club
    then plays where the game puts it, as without Mod Studio (0.2.4: a modpack's 502 home
    stadiums are of the maker's stadium pack, a player may have another one)"""
    folder = folder.strip().strip("\\/")
    if folder and os.path.isdir(os.path.join(lib, folder)):
        return folder
    base = os.path.basename(folder.replace("/", "\\")).lower()
    if not base or not os.path.isdir(lib):
        return None
    for region in sorted(os.listdir(lib)):
        d = os.path.join(lib, region)
        if not os.path.isdir(d):
            continue
        for n in os.listdir(d):
            if n.lower() == base and os.path.isdir(os.path.join(d, n)):
                return region + "\\" + n
    return None


def coverage(pl, sider, edits=None):
    """(clubs with a home stadium, how many of them this PC has the stadium for)"""
    lib = library(sider)
    want = wanted(pl, edits)
    if not lib:
        return len(want), 0
    return len(want), sum(1 for _c, st in want.values()
                          if not problem(st) and find(lib, str(st.get("folder") or "")))


def problem(st):
    """why a club's stadium entry cannot be written, or None"""
    if not str(st.get("folder") or "").strip():
        return "no stadium folder"
    for k in ("name", "folder"):
        if "," in str(st.get(k) or "") or "#" in str(st.get(k) or ""):
            return "the stadium %s cannot hold a comma or #" % k
    slot = str(st.get("slot") or "").strip()
    if slot and not slot.isdigit():
        return "the stadium slot %r is not a number" % slot
    return None


def wanted(pl, edits=None):
    """{team id: (club key, stadium entry)} for the plan's clubs that have a home stadium, with the
    stadiums picked for a ready world (edits, load_edits) in place of the plan's"""
    tids = {}
    for p in (pl.get("leagues") or []) + (pl.get("others") or []):     # clubs in no league too
        for k, tid in enumerate(p.get("teams") or []):
            tids["%s/%d" % (p["name"], k)] = tid
    out = {}
    for club, c in (pl.get("players") or {}).items():
        st = c.get("stadium") if isinstance(c, dict) else None
        if not st:
            continue
        tid = int(club) if club.isdigit() else tids.get(club)
        if tid is not None:
            out[tid] = (club, st)
    if edits:                                          # picked for a ready world: in place of the plan's
        key = {tid: club for club, tid in tids.items()}
        for tid, st in edits.items():
            if st:
                out[tid] = (key.get(tid, str(tid)), st)
            else:
                out.pop(tid, None)
    return out


def _edits_file(root):
    try:
        with open(os.path.join(root, EDITS), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_file(root, section, value):
    """one section of fl26stadiums.json (clubs: stadium pack, game: the game's stadiums), the other
    kept; no file when both are empty"""
    path = os.path.join(root, EDITS)
    data = _edits_file(root)
    data.update({"format": "fl26stadiums", "format_version": 1})
    data[section] = value
    if not data.get("clubs") and not data.get("game") and not data.get("game_auto"):
        if os.path.exists(path):
            os.remove(path)
        return
    with open(path + ".tmp", "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(path + ".tmp", path)


def load_edits(root):
    """{team id: stadium entry, or None for the game's stadium} picked for the world in
    livecpk\\<world> (root); {} when none were"""
    out = {}
    for k, st in (_edits_file(root).get("clubs") or {}).items():
        if str(k).isdigit() and (st is None or isinstance(st, dict)):
            out[int(k)] = dict(st) if st else None
    return out


def save_edits(root, edits):
    """the stadium pack's stadiums picked for a ready world into livecpk\\<world>\\fl26stadiums.json"""
    _save_file(root, "clubs", {str(t): edits[t] for t in sorted(edits)})


def load_game(root):
    """({team id: game stadium id} chosen by hand, Game stadiums automatically pressed) for a ready
    world on the Stadiums page: Team.bin holds the stadiums, this is kept so a new version of the
    world gets them too"""
    data = _edits_file(root)
    hand = {int(k): int(v) for k, v in (data.get("game") or {}).items() if str(k).isdigit() and isinstance(v, int)}
    return hand, bool(data.get("game_auto"))


def save_game(root, hand, auto):
    _save_file(root, "game_auto", bool(auto))
    _save_file(root, "game", {str(t): int(hand[t]) for t in sorted(hand)})


def clubs(pl):
    """[(team id, club key, club name, league)] of every club of the world, league by league"""
    out, seen = [], set()
    for p in (pl.get("leagues") or []) + (pl.get("others") or []):
        names = p.get("club_names") or []
        for k, tid in enumerate(p.get("teams") or []):
            if tid in seen:
                continue
            seen.add(tid)
            out.append((tid, "%s/%d" % (p["name"], k), names[k] if k < len(names) else "", p["name"]))
    return out


# ---- Find automatically: a stadium of this PC's library by its name ----

GENERIC = {"stadium", "stadion", "stadio", "estadio", "estadi", "stade", "stadionul", "stadiumi", "stadiou",
           "stadyumu", "stadyum", "arena", "park", "ground", "municipal", "municipale", "comunale", "national",
           "nacional", "nazionale", "sports", "sport", "complex", "centre", "center", "the", "de", "del", "la",
           "le", "di", "do", "da", "dos", "das", "of", "im", "an", "der", "am", "el", "los", "las"}
CLUB_WORDS = {"fc", "fk", "kf", "sk", "nk", "gnk", "hnk", "ac", "as", "ss", "us", "sc", "cf", "cd", "ud", "sd",
              "rc", "rcd", "afc", "ca", "ec", "se", "club", "football", "futbol", "calcio", "if", "bk", "ff",
              "sv", "pfc", "ofk", "ks", "kv", "cs", "csm", "nt"}


def words(s):
    """the words of a name, lower case, without accents and punctuation"""
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.findall(r"[a-z0-9]+", s)


def stadium_key(s):
    """the words that tell a stadium from another (Stadio San Siro and San Siro: "san siro"); ""
    when too short to be sure"""
    w = [x for x in words(s) if x not in GENERIC]
    k = " ".join(w)
    return k if len(k.replace(" ", "")) >= 4 else ""


def library_names(lib):
    """[(Region\\Stadium, folder name)] of every stadium folder of the library (two levels, as find)"""
    out = []
    try:
        regions = sorted(os.listdir(lib), key=str.lower)
    except OSError:
        return out
    for region in regions:
        d = os.path.join(lib, region)
        if not os.path.isdir(d):
            continue
        for n in sorted(os.listdir(d), key=str.lower):
            try:
                inner = {x.lower() for x in os.listdir(os.path.join(d, n))}
            except OSError:
                continue
            if inner & {"common", "addon", "asset"}:
                out.append((region + "\\" + n, n))
    return out


def club_part(name):
    """the club a stadium folder names, if it names one: Jan Breydelstadion (Club Brugge) -> Club Brugge,
    El Campin - Millonarios -> Millonarios"""
    m = re.search(r"\(([^()]+)\)\s*$", name) or re.search(r"\s[-–]\s(.+)$", name)
    return m.group(1) if m else ""


def club_words(name):
    return {w for w in words(name) if w not in CLUB_WORDS}


def suggest(pl, lib, edits=None):
    """{team id: (stadium entry, how)} for the clubs of the world without a stadium this library has.
    how is "name" (the library has the plan's stadium under another name: Levadia Municipal Stadium
    / Levadia National Stadium) or "club" (a stadium folder that names the club: Jan Breydelstadion
    (Club Brugge)). Only a sure one: a name that fits two different stadiums is not proposed, and a
    club picked by hand (edits) is left alone"""
    names = library_names(lib) if lib else []
    by_key, by_club = {}, []
    for rel, n in names:
        k = stadium_key(n)
        if k:
            by_key.setdefault(k, []).append(rel)
        c = club_words(club_part(n))
        if c and max(len(w) for w in c) >= 4:
            by_club.append((c, rel))

    def one(found):
        # the same stadium in two regions (England\Anfield, Konami\Anfield) is one: the first
        found = sorted(found, key=str.lower)
        return found[0] if found and len({os.path.basename(r).lower() for r in found}) == 1 else None

    want = wanted(pl, edits)
    edits = edits or {}
    out = {}
    for tid, _club, cname, _league in clubs(pl):
        if tid in edits:
            continue
        st = want.get(tid, (None, None))[1]
        if st and not problem(st) and find(lib, str(st.get("folder") or "")):
            continue                                   # this PC has it already
        rel = how = None
        if st:
            for n in (st.get("name"), os.path.basename(str(st.get("folder") or "").replace("/", "\\"))):
                k = stadium_key(n) if n else ""
                rel = one(by_key.get(k, [])) if k else None
                if rel:
                    how = "name"
                    break
        cw = club_words(cname)
        if not rel and cw:
            rel = one([r for c, r in by_club if c == cw])
            how = "club" if rel else None
        if rel:
            out[tid] = ({"folder": rel, "slot": stadium_slot(os.path.join(lib, rel)),
                         "name": (how == "name" and (st or {}).get("name")) or os.path.basename(rel)}, how)
    return out


def read(path):
    if not os.path.exists(path):
        return [], "\r\n", False, "utf-8"
    raw = open(path, "rb").read()
    bom = raw.startswith(codecs.BOM_UTF8)
    if bom:
        raw = raw[3:]
    try:
        text, enc = raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        text, enc = raw.decode("cp1252", "replace"), "cp1252"
    return text.splitlines(), "\r\n" if "\r\n" in text or not text else "\n", bom, enc


def library(sider):
    """the stadium library the game reads: Stadium Server's, else SPFL26's own, None for neither"""
    for f in (FOLDER, OWN):
        d = os.path.join(sider, f)
        if os.path.isdir(d):
            return d
    return None


def write(pl, sider, log=print, edits=None):
    """the plan's home stadiums, with those picked for a ready world (edits), into the stadium
    library's map_teams.txt (library()); the number written"""
    lib = library(sider) or os.path.join(sider, FOLDER)
    want = wanted(pl, edits)
    if not os.path.isdir(lib):
        if want:
            log("NOTE: %d club(s) have a home stadium, but Stadium Server is not installed -- not written"
                % len(want))
        return 0
    path = os.path.join(lib, FILE)
    lines, nl, bom, enc = read(path)
    if not want and not any(TAG in l or l.endswith(OFF) for l in lines):
        return 0
    rows = []
    for l in lines:
        if TAG in l:
            continue                                   # ours, from an earlier switch on
        if l.endswith(OFF):                            # yours, switched off by us: back on
            l = l[:-len(OFF)]
            l = re.sub(r"^(\s*)#\s*", r"\1", l, count=1)
        rows.append(l)
    lines, mine, off = [], [], 0
    for tid, (club, st) in sorted(want.items()):
        bad = problem(st)
        folder = str(st.get("folder") or "").strip().strip("\\/")
        if not bad:
            found = find(lib, folder)
            if found is None:
                bad = "no folder %s in the stadium-server library" % folder
            elif found != folder:
                log("  home stadium of club %d (%s): %s is at %s in this library" % (tid, club, folder, found))
                folder = found
        if bad:
            log("  home stadium of club %d (%s): %s, skipped" % (tid, club, bad))
            continue
        slot = str(st.get("slot") or "").strip() or stadium_slot(os.path.join(lib, folder)) or "009"
        name = str(st.get("name") or "").strip() or os.path.basename(folder)
        mine.append((tid, "%d, %03d, %s, %s   %s %s" % (tid, int(slot), name, folder, TAG, club)))
    taken = {tid for tid, _l in mine}
    for l in rows:
        m = LINE.match(l)
        if m and not m.group(1) and int(m.group(2)) in taken:
            l = "#" + l + OFF
            off += 1
        lines.append(l)
    while lines and not lines[-1].strip():
        lines.pop()
    lines += [l for _t, l in mine]
    if os.path.exists(path):
        if not os.path.exists(path + ".before-builder"):
            shutil.copy2(path, path + ".before-builder")
        shutil.copy2(path, path + ".prev")
    data = (nl.join(lines) + nl).encode(enc, "replace")
    with open(path + ".tmp", "wb") as f:
        f.write((codecs.BOM_UTF8 if bom else b"") + data)
    os.replace(path + ".tmp", path)
    log("home stadiums: %d club(s) -> %s%s" % (len(mine), path,
        ", %d line(s) of your own switched off for them" % off if off else ""))
    return len(mine)
