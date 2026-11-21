r"""Trophies of the competitions (0.2.5, mato 21.10.): a modder pairs a trophy folder of their own
with a competition and the game shows that trophy (FL 2027: through SmokePatch's
modules\common\cinematics.lua, the same scheme with content\cinematics). Nothing else: a competition with no folder
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

FL 2027 only (mato 08.11.: every competition a trophy of its own; new features are not FL26's):
  recipe["trophy_variants"] = {"bases": ["<trophy folder>", ...]}
  Build: every competition of the world with no trophy of its own -- none paired above, none the
         game's cinematics.lua has -- gets a variant of one of the bases (mktrophyvariants: a
         metal, its colours, its logo and name), the same one every Build. Each base goes into
         trophies\bases\<n> once and a variant's folder holds only the textures it changed; the
         block serves those from the variant and every other file from its base.
"""
import hashlib, json, os, re, shutil

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
# FL 2027 has no Entrance.lua: its SmokePatch cinematics module (modules\common\cinematics.lua, juce's
# reworked) is the same idea -- COMP[tournament id] -> a folder of content\cinematics, entry 16 -- with
# make_key a local function; the block goes in it the same way (mato 07.11.: FL27 does all FL26 does)
FL27_MODULES = (("common", "cinematics.lua"),)
MAKE_KEY = re.compile(r"^(?:local )?function make_key\(ctx, filename\)", re.M)
VARIANTS = "trophy_variants"
KEPT = "trophies_kept"          # a world from a zip made editable: Build keeps the trophies it came with
BASES = "bases"
SPEC = "variant.json"           # a base's own notes for mktrophyvariants (its panels), no game file
# the tournament ids the module shows a trophy of its own for: FL 2027 cinematics.lua's add({...})
# and FL26 Entrance.lua's tid == n (65535 is their fallback, not a competition)
HANDLED = (re.compile(r"\badd\(\{([\d,\s]+)\}"), re.compile(r"\btid\s*==\s*(\d+)"))


PACKED = ((".fpk", "_fpk"), (".fpkd", "_fpkd"))


def gzs_leftover(folder, name):
    r"""B400 (10.11.): True when <name> in <folder> is the folder GzsTool unpacked a packed file
    into, beside the packed file itself: #Win\x_fpk next to #Win\x.fpk (x_fpkd next to x.fpkd).
    The game reads the .fpk; nothing asks for the files in x_fpk (SmokePatch's own content\cinematics
    holds the .fpk alone for 441 of its 448, and mktrophyvariants reads the models out of the .fpk).
    The copy only made the paths long: #Win\winners_platform_afc_cl_fpk\Assets\pes16\demo\
    fixdemoobj\winners_platform_common\winners_platform_common.fmdl put a GigaPack trophy file at
    217 characters in the zip, and the game and Windows stop at 259. Without the .fpk beside it
    the folder stays: then it is not GzsTool's copy of something that is there."""
    if os.path.basename(os.path.normpath(folder)).lower() != "#win":
        return False
    low = name.lower()
    for packed, unpacked in PACKED:
        if low.endswith(unpacked) and os.path.isdir(os.path.join(folder, name)):
            return os.path.isfile(os.path.join(folder, name[:-len(unpacked)] + packed))
    return False


def copy_ignore(folder, names):
    """shutil.copytree's ignore: a trophy folder without GzsTool's unpacked copies (gzs_leftover)"""
    return {n for n in names if gzs_leftover(folder, n)}


def files_in(folder):
    return sum(len(fs) for _d, _s, fs in os.walk(folder))


def bases_of(recipe):
    """the base folders of the recipe's trophy variants"""
    v = recipe.get(VARIANTS) or {}
    return [b for b in (v.get("bases") or []) if b] if isinstance(v, dict) else []


def problems(recipe):
    """what is wrong with the recipe's trophies: a folder gone or empty, a base with no trophy"""
    out = []
    for b in bases_of(recipe):
        if not os.path.isdir(b):
            out.append("trophy variants: no base folder %s" % b)
        else:
            import mktrophyvariants as V
            if not V.textures(b)["cup"]:
                out.append("trophy variants: %s has no trophy model with a colour texture "
                           "(common\\demo\\prop\\cup_*)" % b)
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
    top = any(d in subs for d in GAME_PARTS) or any(os.path.isfile(os.path.join(folder, f)) and f.lower() != SPEC
                                                    for f in os.listdir(folder))
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
        out.setdefault(M.reg_cid(g), []).append(g[M.R_ID] | g[M.R_ID + 1] << 8)
    return {c: sorted(set(r)) for c, r in out.items()}


def handled_in(text):
    """the tournament ids a module's text (Entrance.lua / cinematics.lua, ours taken out) has a
    trophy of its own for"""
    out = set()
    for rx in HANDLED:
        for m in rx.finditer(text):
            out.update(int(x) for x in re.findall(r"\d+", m.group(1)))
    out.discard(65535)
    return out


def handled(sider):
    """the tournament ids the game's own module has a trophy for; set() when there is none"""
    path = module_path(sider) if sider else None
    if not path:
        return set()
    return handled_in("\n".join(strip(open(path, encoding="latin-1").read().split("\n"))))


def _md5(path):
    try:
        return hashlib.md5(open(path, "rb").read()).hexdigest()
    except (OSError, TypeError):
        return None


def emblem(roots, cid):
    """the largest picture of competition <cid>'s emblem in the first of <roots> (the world
    being built, the last Build's) that has one; None when none has"""
    import mkemblems
    for root in roots:
        if not root:
            continue
        for suf, _px in sorted(mkemblems.VARIANTS, key=lambda v: -v[1]):
            p = os.path.join(root, "common", "render", "symbol", "emblemLc", "emb_%04d%s.png" % (cid, suf))
            if os.path.isfile(p):
                return p
    return None


def build_variants(pl, tmp, db, index, regs, log=print, sider=None, prev=None):
    """FL 2027: a variant of a base for every competition of the world with no trophy (<index>:
    the paired ones) and none of the game's module; one the last Build (<prev>, the world's
    folder) made with the same look is taken from it, not made again. How many."""
    import mktrophyvariants as V
    import leaguebuilder as B
    bases = [os.path.normpath(b) for b in bases_of(pl) if os.path.isdir(b)]
    if not bases:
        return 0
    if not B.FL27:
        log("  trophy variants: FL 2027 only -- on FL26 a competition shows a trophy paired with it")
        return 0
    taken = handled(sider)
    names = {c: n for c, _r, n, _k, _new in B.competition_ids(db)}
    want = [(c, names.get(c) or "") for c, rids in sorted(regs.items())
            if str(c) not in index and not (set(rids) & taken)]
    if not want:
        return 0
    specs = V.auto(want, bases, {c: emblem([tmp, prev], c) for c, _n in want})
    try:
        with open(os.path.join(prev, FOLDER, INDEX), encoding="utf-8") as f:
            old = json.load(f)
    except (OSError, ValueError, TypeError):
        old = {}
    copies = {}
    for i, b in enumerate(bases):
        dst = os.path.join(tmp, FOLDER, BASES, str(i))
        shutil.copytree(b, dst, ignore=copy_ignore)
        copies[b] = ("%s\\%d" % (BASES, i), phases(dst))
    jobs, kept = [], 0
    for cid, spec in sorted(specs.items()):
        look = {"base": spec["base"], "metal": spec["metal"], "colours": list(spec["colours"]),
                "logo": _md5(spec["logo"]), "name": spec["name"], "version": V.VERSION}
        dst = os.path.join(tmp, FOLDER, str(cid))
        was = old.get(str(cid)) or {}
        here = os.path.join(prev, FOLDER, str(cid)) if prev else None
        own = None
        if here and was.get("look") == look and os.path.isdir(here) and was.get("own"):
            shutil.copytree(here, dst, ignore=copy_ignore)
            own = was["own"]
            kept += 1
        else:
            jobs.append((cid, spec, dst))
        rel, (match, final) = copies[spec["base"]]
        index[str(cid)] = {"rids": regs[cid], "match": match, "final": final, "from": spec["base"],
                           "base": rel, "look": look, "own": own, "auto": True}

    def one(job):
        cid, spec, dst = job
        try:
            return cid, V.write(spec, dst)
        except V.Error as e:
            log("  warning: trophy variant of competition %s -- %s, left out" % (cid, e))
            return cid, []
    made = 0
    if jobs:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=max(1, min(4, (os.cpu_count() or 2) // 2))) as ex:
            for cid, done in ex.map(one, jobs):
                if not done:
                    index.pop(str(cid), None)
                    continue
                index[str(cid)]["own"] = sorted(d.replace("/", "\\").lower() for d in done)
                made += 1
    n = sum(1 for e in index.values() if e.get("auto"))
    log("  trophy variants: %d competition(s) a trophy of their own from %d base(s) (%d made, %d as "
        "the last Build's)" % (n, len(bases), made, kept))
    return n


def carry(pl, tmp, index, regs, prev, log=print):
    """B481: a world that came ready in a zip was built from trophy folders on its maker's PC.
    Made editable here, its recipe cannot name them (recipe_from_plan leaves out a folder that is
    not on this PC), and the first Build left the world with no trophies at all (15.11.2026: the
    GigaPack after Make it editable + Build, 10547 trophy files gone). With <KEPT> in the plan,
    the trophies of the world as it is (<prev>) go into the world being built as they are: each
    competition of trophies.json that the new world still has and that got no trophy from this
    Build's own folders (<index>), with its regulation ids as they are now. The variants (FL 2027)
    and the bases they are served from as well, unless this recipe has bases of its own: then
    the Build makes the variants itself. How many were kept."""
    if not pl.get(KEPT) or not prev:
        return 0
    try:
        with open(os.path.join(prev, FOLDER, INDEX), encoding="utf-8") as f:
            old = json.load(f)
    except (OSError, ValueError, TypeError):
        return 0
    own_bases = bool(bases_of(pl))
    n, bases = 0, set()
    for cid, e in sorted(old.items(), key=lambda kv: str(kv[0])):
        if not str(cid).isdigit() or str(cid) in index or not isinstance(e, dict):
            continue
        if e.get("auto") and own_bases:
            continue
        rids = regs.get(int(cid))
        if not rids:
            continue                    # the competition is not in the world any more
        src = os.path.join(prev, FOLDER, str(cid))
        rel = e.get("base")
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(tmp, FOLDER, str(cid)), ignore=copy_ignore)
        elif not rel:
            continue                    # nothing of it is there
        if rel:
            bases.add(rel)
        index[str(cid)] = dict(e, rids=rids)
        n += 1
    for rel in sorted(bases):
        src, dst = os.path.join(prev, FOLDER, rel), os.path.join(tmp, FOLDER, rel)
        if os.path.isdir(src) and not os.path.exists(dst):
            shutil.copytree(src, dst, ignore=copy_ignore)
    if n:
        log("  trophies: %d competition(s) keep the trophy the world came with" % n)
    return n


def build(pl, tmp, db, log=print, sider=None, prev=None):
    """the plan's trophies into the world being built (<tmp>): the folders, and trophies.json; on
    FL 2027 the variants for the rest (build_variants: <sider> the game's sider folder, <prev>
    the world as the last Build left it). A world from a zip made editable: the ones it came with
    stay (carry)"""
    want = pl.get("trophies") or {}
    if not want and not bases_of(pl) and not pl.get(KEPT):
        return 0
    regs = regulations(db)
    index = {}
    for cid, folder in sorted(want.items(), key=lambda kv: int(kv[0])):
        rids = regs.get(int(cid))
        if not rids:
            log("  warning: trophy of competition %s -- the world has no such competition, left out" % cid)
            continue
        dst = os.path.join(tmp, FOLDER, str(cid))
        shutil.copytree(folder, dst, ignore=copy_ignore)    # B400: not GzsTool's unpacked copies
        match, final = phases(dst)
        index[str(cid)] = {"rids": rids, "match": match, "final": final, "from": folder}
    paired = len(index)
    kept = carry(pl, tmp, index, regs, prev, log)
    variants = build_variants(pl, tmp, db, index, regs, log, sider, prev) if bases_of(pl) else 0
    if not index and pl.get(KEPT):
        return 0                        # none to keep: as a world with no trophies
    os.makedirs(os.path.join(tmp, FOLDER), exist_ok=True)
    with open(os.path.join(tmp, FOLDER, INDEX), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=1)
    if kept and not paired:
        return kept + variants
    if paired or not variants:
        log("  trophies: %d competition(s) with a trophy of their own (Entrance.lua, on FL 2027 "
            "common\\cinematics.lua, shows them once the world is switched on)" % paired)
    return paired + kept + variants


def signature(pl):
    """what input_key reads of the trophy folders: a file put in one or changed is a new Build"""
    out = []
    folders = sorted((pl.get("trophies") or {}).items(), key=lambda kv: str(kv[0]))
    if bases_of(pl):
        import mktrophyvariants as V
        out.append(("variants", V.VERSION))
        folders += [("base%d" % i, b) for i, b in enumerate(bases_of(pl))]
    for cid, folder in folders:
        for d, _s, fs in sorted(os.walk(folder)) if folder and os.path.isdir(folder) else []:
            for f in sorted(fs):
                try:
                    st = os.stat(os.path.join(d, f))
                except OSError:
                    continue
                out.append((str(cid), os.path.relpath(os.path.join(d, f), folder), st.st_size, int(st.st_mtime)))
    return out


def module_path(sider):
    """FL26's Entrance.lua in <sider>\\modules, or FL 2027's common\\cinematics.lua, when it is the
    one this file knows how to extend"""
    mods = os.path.join(sider, "modules")
    places = [(mods, MODULES, "Entrance")] + [(os.path.join(mods, d), (f,), "cinematics") for d, f in FL27_MODULES]
    for where, names, root in places:
        for f in sorted(os.listdir(where)) if os.path.isdir(where) else []:
            if f.lower() in [m.lower() for m in names]:
                p = os.path.join(where, f)
                text = open(p, encoding="utf-8", errors="replace").read()
                if MAKE_KEY.search(text) and "trophy_rewrite" in text and ("content\\\\%s" % root) in text:
                    return p
    return None


def lua_str(s):
    return '"%s"' % s.replace("\\", "\\\\").replace('"', '\\"')


def block(world, index, skip=()):
    """the lines of ours for <world>'s trophies; [] when it has none. A variant's tournament id
    the module has a trophy for (<skip>) is left to the module. With no variant the lines are
    the same as before there were any (FL26 gets nothing new)."""
    if not index:
        return []
    base = "..\\..\\livecpk\\%s\\%s" % (world, FOLDER)

    def at(here, e):
        return (here + ("\\" + e["match"] if e["match"] else ""),
                here + ("\\" + e["final"] if e["final"] else ""))
    rows, owns = [], {}
    for cid, e in sorted(index.items(), key=lambda kv: int(kv[0])):
        match, final = at(base + "\\" + cid, e)
        if e.get("base"):
            # a variant: its own textures from its folder (t[1], t[2]), the rest from its base's
            n = owns.setdefault(tuple(sorted(e.get("own") or [])), len(owns) + 1)
            bmatch, bfinal = at(base + "\\" + e["base"], e)
            for rid in e["rids"]:
                if rid not in skip:
                    rows.append("\t\t[%d] = {%s, %s, %s, %s, %d},   -- competition %s, a variant" % (
                        rid, lua_str(match), lua_str(final), lua_str(bmatch), lua_str(bfinal), n, cid))
            continue
        for rid in e["rids"]:
            rows.append("\t\t[%d] = {%s, %s},   -- competition %s" % (rid, lua_str(match), lua_str(final), cid))
    if not rows:
        return []
    head = ["%s %s (Mod Studio writes this on Switch on; the rest of the file is not ours) ----" % (BEGIN, world),
            "local fl26ms_trophies"]
    pick = ["\tif ctx.match_info == 53 then Entrance = t[2] else Entrance = t[1] end"]
    own = []
    if owns:
        head.append("local fl26ms_own")
        own = ["\t\tfl26ms_own = {"]
        for files, n in sorted(owns.items(), key=lambda kv: kv[1]):
            own.append("\t\t[%d] = {%s}," % (n, ", ".join("[%s] = true" % lua_str(f) for f in files)))
        own.append("\t\t}")
        pick = ["\tlocal i = 1",
                "\tif ctx.match_info == 53 then i = 2 end",
                "\tif t[5] ~= nil and not fl26ms_own[t[5]][string.lower((string.gsub(filename, \"/\", \"\\\\\")))] "
                "then i = i + 2 end",
                "\tEntrance = t[i]"]
    return head + [
           "local function fl26ms_trophy(ctx, filename)",
           "\tif fl26ms_trophies == nil then",
           "\t\tfl26ms_trophies = {}",
           "\t\tlocal f = io.open(fileroot .. %s, \"r\")" % lua_str("\\" + base + "\\" + INDEX),
           "\t\tif f == nil then return nil end",
           "\t\tf:close()"] + own + [
           "\t\tfl26ms_trophies = {"] + rows + [
           "\t\t}",
           "\tend",
           "\tlocal t = fl26ms_trophies[tid]",
           "\tif t == nil then return nil end",
           "\tentry = 16"] + pick + [
           "\treturn string.format(\"%s:%s\", Entrance, filename)",
           "end",
           END]


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
    skip = handled_in(nl.join(lines)) if any(e.get("base") for e in index.values()) else ()
    ours = block(world, index, skip)
    if not ours:
        return nl.join(lines)
    at = next(i for i, l in enumerate(lines) if MAKE_KEY.match(l))
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
            log("NOTE: %d trophy(ies) of %s -- the game has no FL26 Entrance.lua (FL 2027: common\\cinematics.lua) "
                "in modules, so they are not shown" % (len(index), world))
        return False
    # latin-1 both ways: every byte of FL26's file comes back as it was; ours are ASCII
    text = open(path, encoding="latin-1", newline="").read()
    new = apply(text, world, index)
    if new != text:
        if keep_before:
            keep_before(path, "Switch on %s: its trophies in %s" % (world, os.path.basename(path)), sider)
        open(path, "w", encoding="latin-1", newline="").write(new)
    if index:
        log("%s: %d trophy(ies) of %s" % (os.path.basename(path), len(index), world))
    elif new != text:
        log("%s: the trophies of another world taken out" % os.path.basename(path))
    return bool(index)
