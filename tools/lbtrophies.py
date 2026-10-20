r"""Trophies of the competitions (0.2.5, mato 21.10.): a modder pairs a trophy folder of their own
with a competition and the game shows that trophy. Nothing else: a competition with no folder
paired keeps what it had, and no competition borrows a trophy someone can see is another's.

It goes through FL26's own Entrance.lua (FuNZoTiK / VirtuaRed), no module of ours: Entrance.lua
picks a folder of content\Entrance by the match's tournament id (the regulation id, as sider.log
prints it) and trophy_rewrite hands the game entry 16, the AFC Champions League ceremony, whose
files the folder replaces (cup_afc_cl_hi ...). The folder is laid out as FL26's: the files at its
top or in a phase folder (Group_Knockout, Eliminatorias ...), the final's in Final.

  recipe["trophies"] = {"<competition id>": "<folder>"}   (Leagues > More > Trophies)
  Build: each folder into <world>\trophies\<competition id>, and trophies\trophies.json with the
         competition's regulation ids (all of them: a group row is a tournament id too, 1026 is
         the Champions League's) and the two folders Entrance.lua is to use
  Switch on: one marked block in Entrance.lua for the world switched on, replaced every time;
         the rest of the file is not touched. The block looks for the world's trophies.json once,
         so a world deleted or renamed since leaves every competition as it was.
"""
import json, os, re, shutil

FOLDER = "trophies"
INDEX = "trophies.json"
TAG = "FL26 Mod Studio trophies"
BEGIN = "-- ---- %s:" % TAG
END = "-- ---- end of %s ----" % TAG
HOOK = "-- %s (hook)" % TAG
FINAL = "final"
PHASES = ("group_knockout", "knockout", "eliminatorias", "regular_fase", "regular_phase", "group stage",
          "generic", "championship")
GAME_PARTS = ("common", "asset")           # what a trophy folder holds at its top
MODULES = ("Entrance.lua",)


def files_in(folder):
    return sum(len(fs) for _d, _s, fs in os.walk(folder))


def problems(recipe):
    """what is wrong with the recipe's trophies: a folder gone or empty"""
    out = []
    for cid, folder in sorted((recipe.get("trophies") or {}).items(), key=lambda kv: str(kv[0])):
        if not str(cid).isdigit():
            out.append("%s is not a competition id" % (cid,))
        elif not folder or not os.path.isdir(folder):
            out.append("competition %s: no trophy folder %s" % (cid, folder))
        elif not files_in(folder):
            out.append("competition %s: the trophy folder %s has no files" % (cid, folder))
    return out


def phases(folder):
    """(the folder Entrance.lua uses for a match, the one for a final), relative to the trophy's
    folder ("" = its top): FL26's own layout, Final for the final and the files at the top or in
    a phase folder for the rest"""
    subs = {d.lower(): d for d in os.listdir(folder) if os.path.isdir(os.path.join(folder, d))}
    top = any(d in subs for d in GAME_PARTS) or any(os.path.isfile(os.path.join(folder, f)) for f in os.listdir(folder))
    final = subs.get(FINAL)
    if top:
        match = ""
    else:
        match = next((subs[p] for p in PHASES if p in subs), None)
        if match is None:
            match = next((subs[d] for d in sorted(subs) if d != FINAL), final or "")
    return match, (final if final is not None else match)


def regulations(db):
    """{competition id: [every regulation id of it, the group and phase rows too]} of the tables at <db>"""
    import mkleague as M
    regs = M.load(db, "CompetitionRegulation.bin")
    out = {}
    for i in range(len(regs) // M.REG):
        g = regs[i * M.REG:(i + 1) * M.REG]
        out.setdefault(g[M.R_CID], []).append(g[M.R_ID] | g[M.R_ID + 1] << 8)
    return {c: sorted(set(r)) for c, r in out.items()}


def build(pl, tmp, db, log=print):
    """the plan's trophies into the world being built (<tmp>): the folders, and trophies.json"""
    want = pl.get("trophies") or {}
    if not want:
        return 0
    regs = regulations(db)
    index = {}
    for cid, folder in sorted(want.items(), key=lambda kv: int(kv[0])):
        rids = regs.get(int(cid))
        if not rids:
            log("  warning: trophy of competition %s -- the world has no such competition, left out" % cid)
            continue
        dst = os.path.join(tmp, FOLDER, str(cid))
        shutil.copytree(folder, dst)
        match, final = phases(dst)
        index[str(cid)] = {"rids": rids, "match": match, "final": final, "from": folder}
    os.makedirs(os.path.join(tmp, FOLDER), exist_ok=True)
    with open(os.path.join(tmp, FOLDER, INDEX), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=1)
    log("  trophies: %d competition(s) with a trophy of their own (Entrance.lua shows them once the world "
        "is switched on)" % len(index))
    return len(index)


def signature(pl):
    """what input_key reads of the trophy folders: a file put in one or changed is a new Build"""
    out = []
    for cid, folder in sorted((pl.get("trophies") or {}).items(), key=lambda kv: str(kv[0])):
        for d, _s, fs in sorted(os.walk(folder)) if folder and os.path.isdir(folder) else []:
            for f in sorted(fs):
                try:
                    st = os.stat(os.path.join(d, f))
                except OSError:
                    continue
                out.append((str(cid), os.path.relpath(os.path.join(d, f), folder), st.st_size, int(st.st_mtime)))
    return out


def module_path(sider):
    """FL26's Entrance.lua in <sider>\\modules, when it is the one this file knows how to extend"""
    mods = os.path.join(sider, "modules")
    for f in sorted(os.listdir(mods)) if os.path.isdir(mods) else []:
        if f.lower() in [m.lower() for m in MODULES]:
            p = os.path.join(mods, f)
            text = open(p, encoding="utf-8", errors="replace").read()
            if re.search(r"^function make_key\(ctx, filename\)", text, re.M) and "trophy_rewrite" in text \
                    and "content\\\\Entrance" in text:
                return p
    return None


def lua_str(s):
    return '"%s"' % s.replace("\\", "\\\\").replace('"', '\\"')


def block(world, index):
    """the lines of ours for <world>'s trophies; [] when it has none"""
    if not index:
        return []
    base = "..\\..\\livecpk\\%s\\%s" % (world, FOLDER)
    rows = []
    for cid, e in sorted(index.items(), key=lambda kv: int(kv[0])):
        here = base + "\\" + cid
        match = here + ("\\" + e["match"] if e["match"] else "")
        final = here + ("\\" + e["final"] if e["final"] else "")
        for rid in e["rids"]:
            rows.append("\t\t[%d] = {%s, %s},   -- competition %s" % (rid, lua_str(match), lua_str(final), cid))
    out = ["%s %s (Mod Studio writes this on Switch on; the rest of the file is not ours) ----" % (BEGIN, world),
           "local fl26ms_trophies",
           "local function fl26ms_trophy(ctx, filename)",
           "\tif fl26ms_trophies == nil then",
           "\t\tfl26ms_trophies = {}",
           "\t\tlocal f = io.open(fileroot .. %s, \"r\")" % lua_str("\\" + base + "\\" + INDEX),
           "\t\tif f == nil then return nil end",
           "\t\tf:close()",
           "\t\tfl26ms_trophies = {"] + rows + [
           "\t\t}",
           "\tend",
           "\tlocal t = fl26ms_trophies[tid]",
           "\tif t == nil then return nil end",
           "\tentry = 16",
           "\tif ctx.match_info == 53 then Entrance = t[2] else Entrance = t[1] end",
           "\treturn string.format(\"%s:%s\", Entrance, filename)",
           "end",
           END]
    return out


def strip(lines):
    """Entrance.lua's lines without ours"""
    out, skip = [], False
    for l in lines:
        s = l.strip()
        if s.startswith(BEGIN):
            skip = True
            continue
        if skip:
            if s == END:
                skip = False
            continue
        if HOOK in l:
            continue
        out.append(l)
    return out


def rename_lines(lines, old, new):
    """Entrance.lua's lines with our block of world <old> renamed <new> (worlds.rename)"""
    out, inside = [], False
    was, now = lua_str("\\livecpk\\%s\\" % old)[1:-1], lua_str("\\livecpk\\%s\\" % new)[1:-1]
    for l in lines:
        s = l.strip()
        if s.startswith("%s %s " % (BEGIN, old)):
            inside = True
            l = l.replace("%s %s " % (BEGIN, old), "%s %s " % (BEGIN, new), 1)
        elif inside and s == END:
            inside = False
        elif inside:
            l = l.replace(was, now)
        out.append(l)
    return out


def apply(text, world, index):
    """Entrance.lua's text with <world>'s block (and the one line in make_key that asks it), or
    with none when the world pairs no trophy"""
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = strip(text.split(nl))
    ours = block(world, index)
    if not ours:
        return nl.join(lines)
    at = next(i for i, l in enumerate(lines) if re.match(r"function make_key\(ctx, filename\)", l))
    hook = "\tlocal fl26ms_key = fl26ms_trophy(ctx, filename) if fl26ms_key then return fl26ms_key end   " + HOOK
    return nl.join(lines[:at] + ours + [lines[at], hook] + lines[at + 1:])


def switch_on(sider, world, root, log=print, keep_before=None):
    """the block of <world> (its folder <root>) into Entrance.lua; another world's goes"""
    try:
        with open(os.path.join(root, FOLDER, INDEX), encoding="utf-8") as f:
            index = json.load(f)
    except (OSError, ValueError):
        index = {}
    path = module_path(sider)
    if path is None:
        if index:
            log("NOTE: %d trophy(ies) of %s -- the game has no FL26 Entrance.lua in modules, so they are "
                "not shown" % (len(index), world))
        return False
    # latin-1 both ways: every byte of FL26's file comes back as it was; ours are ASCII
    text = open(path, encoding="latin-1", newline="").read()
    new = apply(text, world, index)
    if new != text:
        if keep_before:
            keep_before(path, "Switch on %s: its trophies in Entrance.lua" % world, sider)
        open(path, "w", encoding="latin-1", newline="").write(new)
    if index:
        log("Entrance.lua: %d trophy(ies) of %s" % (len(index), world))
    elif new != text:
        log("Entrance.lua: the trophies of another world taken out")
    return bool(index)
