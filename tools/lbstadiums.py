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
    for p in pl.get("leagues") or []:
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
        if not bad and not os.path.isdir(os.path.join(lib, folder)):
            bad = "no folder %s in the stadium-server library" % folder
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
