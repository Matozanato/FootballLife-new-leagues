r"""python rigcheck.py <game folder> <pack folder> -- is this test game what a player gets?

B408 (morpheus 10.11.2026, GigaPack beta 1): our FL 2027 test game loaded fl26match.lua, put in
by hand during the limits work, and Mod Studio's pack did not have it. Every GigaPack test passed
on that game; a player's new career died while it was made. A test in the game proves the pack
only when the game runs the pack's modules and nothing of ours besides, so before a test:

  - every lua.module line of ours (fl26*.lua, switched on) is a module of the pack, in the pack's
    order (modules.txt), and every module of the pack has its line;
  - each of those files in SiderAddons\modules is the pack's own (its FL 2027 copy, <m>.fl27.lua,
    in an FL_2027.exe folder), and so is each DLL of the pack;
  - with --log: sider.log loaded exactly those (Loading module: ...), so the game started with them.

Modules of others (common\kits.lua, ML_FastForward ...) are listed, not judged. fl26regions and
fl26regnames belong to the world (switch-on writes them). Exit 1 on any difference."""
import hashlib
import os
import re
import sys

PER_WORLD = {"fl26regions", "fl26regnames"}


def md5(p):
    with open(p, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def ini_modules(sider):
    """the switched-on lua.module names, in order"""
    out = []
    for line in open(os.path.join(sider, "sider.ini"), encoding="utf-8", errors="replace"):
        m = re.match(r'^\s*lua\.module\s*=\s*"?([^";\r\n]+?)"?\s*$', line)
        if m:
            out.append(m.group(1).strip())
    return out


def log_modules(sider):
    """the modules sider.log says it loaded, in order"""
    out = []
    for line in open(os.path.join(sider, "sider.log"), encoding="utf-8", errors="replace"):
        m = re.match(r"^Loading module: (.+?) \.\.\.", line)
        if m:
            out.append(m.group(1).strip())
    return out


def check(game, pack, with_log=False, log=print):
    """the differences between this game's modules and the pack's (an empty list: it is the pack)"""
    sider = os.path.join(game, "SiderAddons")
    fl27 = os.path.exists(os.path.join(game, "FL_2027.exe"))
    order = open(os.path.join(pack, "modules.txt"), encoding="utf-8").read().split()
    pmods = os.path.join(pack, "modules")
    lines = ini_modules(sider)
    # ours by the file's name, wherever its line points (review 11.11.: "experimental\fl26x.lua" went
    # to the others and was never judged, the very case rule 10 is there to catch)
    def name_of(l):
        return re.split(r"[\\/]", l)[-1]
    mine = [l for l in lines if re.match(r"^fl26[\w.-]*\.lua$", name_of(l), re.I)]
    ours = [l[:-4] for l in mine if name_of(l) == l]
    others = [l for l in lines if l not in mine]
    bad = ["%s is loaded from a subfolder: a player never gets it" % l for l in mine if name_of(l) != l]
    for m in ours:
        if m not in order and m not in PER_WORLD:
            bad.append("%s.lua is loaded but is not in the pack: a player never gets it" % m)
    for m in order:
        if m not in ours and m not in PER_WORLD:
            bad.append("%s.lua of the pack has no lua.module line (Install now not done?)" % m)
    shared = [m for m in ours if m in order]
    if shared != [m for m in order if m in ours]:
        bad.append("our modules load in another order than the pack's: %s" % " ".join(shared))
    for m in shared:
        src = os.path.join(pmods, m + ".fl27.lua") if fl27 else ""
        if not os.path.isfile(src):
            src = os.path.join(pmods, m + ".lua")
        dst = os.path.join(sider, "modules", m + ".lua")
        if not os.path.isfile(src):
            continue                        # a per-world module the pack leaves to the world
        if not os.path.isfile(dst):
            bad.append("%s.lua is missing in SiderAddons\\modules" % m)
        elif md5(src) != md5(dst):
            bad.append("%s.lua is not the pack's (%s, the pack's %s)" % (m, md5(dst)[:8], md5(src)[:8]))
    for f in sorted(os.listdir(pmods)):
        if f.lower().endswith(".dll"):
            dst = os.path.join(sider, "modules", f)
            if not os.path.isfile(dst):
                bad.append("%s of the pack is missing in SiderAddons\\modules" % f)
            elif md5(dst) != md5(os.path.join(pmods, f)):
                bad.append("%s is not the pack's (%s, the pack's %s)" % (f, md5(dst)[:8], md5(os.path.join(pmods, f))[:8]))
    if with_log:
        loaded = log_modules(sider)
        if loaded != lines:
            bad.append("sider.log loaded other modules than sider.ini names (start the game once after Install now)")
    log("rigcheck: %s, %s; %d of our modules, %d of others (%s)" % (
        game, "FL 2027" if fl27 else "FL26", len(ours), len(others), ", ".join(others) or "none"))
    for b in bad:
        log("  BAD " + b)
    log("rigcheck: " + ("the game runs the pack's modules" if not bad else "%d difference(s) -- not a test of the pack" % len(bad)))
    return bad


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(1 if check(args[0], args[1], "--log" in sys.argv) else 0)
