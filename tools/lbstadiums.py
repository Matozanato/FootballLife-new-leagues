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

Without Stadium Server (SiderAddons\content\stadium-server) the lines go to SPFL26's own stadium
module, common\stadiums.lua, which reads the same files from content\stadiums (JamesNotLike,
0.1.8); with neither nothing is written.
"""
import codecs, os, re, shutil

FOLDER = os.path.join("content", "stadium-server")
OWN = os.path.join("content", "stadiums")            # SPFL26's common\stadiums.lua: same files, its own folder
FILE = "map_teams.txt"
TAG = "# FL26 Mod Studio:"
OFF = "  # (switched off by FL26 Mod Studio)"
LINE = re.compile(r"^\s*(#\s*)?(\d+)\s*,")


def _ids(d, pat):
    try:
        return sorted({m.group(1) for n in os.listdir(d) for m in [re.fullmatch(pat, n, re.I)] if m})
    except OSError:
        return []


def stadium_slot(folder):
    r"""the stadium slot a stadium folder was made for: the slot of its picture
    (common\render\thumbnail\stadium\stNNN.dds -- Stadium Server shows that one, and a pack's own
    map uses that slot), else its AddOn folders, else its one model folder (Asset\model\bg\stNNN).
    A stadium of the game ("Konami" or "common" in the pack) has no model in its folder, only
    lighting and nets for the game's own stadium NNN: served under another slot it is dark
    (Discord, Erax, 0.2.4: Estadio del Tauro st055 written as 009)"""
    pic = _ids(os.path.join(folder, "common", "render", "thumbnail", "stadium"), r"st(\d{3})\.dds")
    if len(pic) == 1:
        return pic[0]
    seen = {}
    for sub in ("fog", "Light", "Cutscene", "Large_hexagonal_net"):
        for n in _ids(os.path.join(folder, "AddOn", sub), r"(\d{3})"):
            seen[n] = seen.get(n, 0) + 1
    if seen:
        return max(seen, key=seen.get)
    model = _ids(os.path.join(folder, "Asset", "model", "bg"), r"st(\d{3})")
    return model[0] if len(model) == 1 else ""


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


def coverage(pl, sider):
    """(clubs with a home stadium, how many of them this PC has the stadium for)"""
    lib = library(sider)
    want = wanted(pl)
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


def wanted(pl):
    """{team id: (club key, stadium entry)} for the plan's clubs that have a home stadium"""
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


def keep_before(path, reason, sider=None):
    """a map about to be written, kept as a restore point in SiderAddons\\ModStudio\\backups (Restore
    points shows it; the first copy is what Put Sider back as before Mod Studio puts back). Until
    0.2.4 it was <map>.before-builder and <map>.prev next to the map (mato 15.10.: "from now on"
    not next to the files)"""
    if not os.path.isfile(path):
        return None
    try:
        from modstudio import backups
    except ImportError:                    # the CLI without the modstudio package beside it
        return None
    return backups.before_change(path, reason, sider)


def library(sider):
    """the stadium library the game reads: Stadium Server's, else SPFL26's own, None for neither"""
    for f in (FOLDER, OWN):
        d = os.path.join(sider, f)
        if os.path.isdir(d):
            return d
    return None


def write(pl, sider, log=print):
    """the plan's home stadiums into the stadium library's map_teams.txt (library()); the number written"""
    lib = library(sider) or os.path.join(sider, FOLDER)
    want = wanted(pl)
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
        # the slot of the folder on this PC first: the recipe's was read from the maker's folder
        # (or not at all), and a wrong one makes the stadium dark
        own = stadium_slot(os.path.join(lib, folder))
        slot = own or str(st.get("slot") or "").strip()
        if not slot:
            # nothing in the folder names its stadium: Stadium Server's usual slot, said in the log
            slot = "009"
            log("  home stadium of club %d (%s): %s names no stadium slot (no stNNN picture, AddOn or "
                "model folder), served as 009" % (tid, club, folder))
        if own and str(st.get("slot") or "").strip() and int(own) != int(st["slot"]):
            log("  home stadium of club %d (%s): %s is stadium %s, not %s" % (tid, club, folder, own, st["slot"]))
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
    keep_before(path, "Switch on: home stadiums map", sider)
    data = (nl.join(lines) + nl).encode(enc, "replace")
    with open(path + ".tmp", "wb") as f:
        f.write((codecs.BOM_UTF8 if bom else b"") + data)
    os.replace(path + ".tmp", path)
    log("home stadiums: %d club(s) -> %s%s" % (len(mine), path,
        ", %d line(s) of your own switched off for them" % off if off else ""))
    return len(mine)
