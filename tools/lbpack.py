r"""python lbpack.py <out dir>   -> the module pack the league builder installs

The builder's worlds are read by our modules, and only by the versions that read the world
file (docs/developers/mod-studio.md). A person who has the public release, or nothing at all, needs
this exact set, so it ships inside the builder and "Install modules" puts it in place.

What goes in, and from where -- every file from a source that is ours and clean:

  sider/*.lua, sider/experimental/*.lua
                            the world-file readers and the guards. Where the public repository
                            sits beside this one (../fl26-public), its copies are taken first, so
                            the pack is exactly what is published; otherwise this repository's.
  tools/native/*.c          the DLLs, compiled now with zig (tools/native/build-*.sh)
  the regen face pack       fl26regen_faces.bin (into modules) and the livecpk root
                            "FL26 Regen Faces" (into livecpk): the face pool, built here by
                            tools/facepool.py from tools/facepool_stats.json (no game renders,
                            no portraits), or $FL26_REGEN_FACES's copy of it with portraits
                            (tools/facemini.py pack). Anything else -- the 30.09. pack of game
                            faces, a smaller or older pool -- stops the build (face_pack).

fl26regions.lua and fl26regnames.lua are not in the pack: they name the competitions and
regions of one world, so the builder makes them per world and switch-on puts them in place.

The pack is checked before it is written out: no drive letters, no user folders.
"""
import os, re, shutil, struct, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PUBLIC = os.path.join(os.path.dirname(REPO), "fl26-public")
# zig: $ZIG, else the copy in tools\ beside this repo's folder, else the one on PATH
ZIG = os.environ.get("ZIG") or next(
    (z for z in [os.path.join(os.path.dirname(REPO), "tools", "zig-x86_64-windows-0.16.0", "zig.exe")]
     if os.path.exists(z)), "zig")

# the lua.module lines, in load order (the order of the working install)
ORDER = [
    "fl26gameguard",            # first: a world of the other game stops the game before anything loads (07.11.)
    "fl26caps",
    "fl26match",                # FL 2027 only (it stands down in FL26): match ids past 65535, players past
                                # 65535 (B408: GigaPack beta 1 shipped without it, a new career died)
    "fl26appcap", "fl26regs600", "fl26slots250", "fl26slot7", "fl26guards", "fl26regfast", "fl26walk",
    "fl26compcache", "fl26joindll",
    "fl26hdr255", "fl26chain", "fl26comptab", "fl26slotnames", "fl26clubs", "fl26regen", "fl26editlist", "fl26edit",
    "fl26rank", "fl26deeprank", "fl26regions", "fl26reg128", "fl26regnames", "fl26catlist", "fl26squadlist",
    "fl26confgroups",           # FL 2027 only (it stands down in FL26): Select Team / Competition Info by confederation
    "fl26swiss", "fl26augseason", "fl26lateguards",
    "fl26seasonend",
]
# Modules that ship as one file (0.2.0, Gu: "quite a lot of separate Lua/DLL modules now"): the
# small one-fix guards, each still its own file in sider/ to read and change, go out bundled in
# load order. Every part keeps its own log lines, so sider.log still says which fix did what,
# and a part that refuses its bytes logs it and leaves the others be (there is no pcall: a part
# whose init raises stops the parts after it, so the best-tried ones go first). Build
# switches the old single lines off and keeps the old files in before-builder-<n>
# (leaguebuilder.install_modules, retired.txt in the pack).
BUNDLES = {
    "fl26guards": ["fl26nullguard", "fl26nullguard2", "fl26nullguard4", "fl26nullguard5",
                   "fl26nullguard7", "fl26nullguard8", "fl26nullguard9", "fl26nullguard10",
                   "fl26nullguard11", "fl26nullguard12", "fl26nullguard13",
                   "fl26nullguard14",   # B475: cup bracket of a size the game has no bye list for
                   "fl26nullguard15"],  # B491: BAL season end, a player key missing from the map
    "fl26lateguards": ["fl26superguard", "fl26resultsguard", "fl26ctlguard", "fl26kitguard"],
}
# FL 2027's own copy of a module, shipped as <module>.fl27.lua beside it: Install modules puts it in
# under the module's name in an FL_2027.exe folder (leaguebuilder.shipped_source). The limits set
# (patchset.py --fl27; since limits-headroom 07.11.: teams 8000, coaches 10000, regulations 2000,
# players 180017, 4140 match ids a calendar day, 3600 standings tables) and the regulation recount
# that goes with its 2000 records (mkregs.py 2000); FL26 keeps 0.3.0's
# The season header: an FL27 set with the standings step (patchset.py <set>-standings) owns the
# sites fl26hdr255 patches, and the FL27 copy of hdr255 stands down when it finds them done.
# Select Team: FL 2027's slots 79/80 (the all-club lists) hold 8000, the P150 set's team array,
# where FL26's hold 2600; the other slots pay for it (143 each with FL 2027's 465 slots, slots-wide:
# mkslots.py 465 --big 8000). A
# career keeps its own copy of the slot region, so FL26's module stays as it was (its careers).
FL27 = {"fl26caps": "fl26caps.fl27", "fl26match": "fl26match.fl27", "fl26regs600": "fl26regs2000.fl27", "fl26hdr255": "fl26hdr255.fl27",
        "fl26slots250": "fl26slots250.fl27"}
# modules a shipped one replaced, not bundled into it: an old install still has their line, the
# two overlap, the second refuses its bytes, and check() read that as "refused the game's exe"
# (audit 12.10., GitHub #130). Build switches them off like the bundled ones (retired.txt).
SUPERSEDED = {"fl26nullguard3": "fl26guards",      # nullguard9 (in fl26guards) replaced it 22.09.
              "fl26hdr127": "fl26hdr255",          # hdr255 expects what hdr127 leaves unpatched
              "fl26hdr192": "fl26hdr255",          # 0.2.2: the season header for 255 competitions
              "fl26deep4": "fl26deeprank",         # rank + deeprank do the third division properly
              "fl26reg64": "fl26reg128"}           # reg128 does all reg64 did, 64 -> 128 regions
PER_WORLD = {"fl26regions", "fl26regnames"}
DLLS = {"fl26join": "build-join.sh", "fl26chain": "build-chain.sh",
        "fl26clubs": "build-clubs.sh", "fl26swiss": "build-swiss.sh", "fl26regen": "build-regen.sh",
        "fl26edit": "build-edit.sh", "fl26walk": "build-walk.sh",
        "fl26compcache": "build-compcache.sh", "fl26squadlist": "build-squadlist.sh",
        "fl26confgroups": "build-confgroups.sh"}
# DLLs that go out as committed, not built here: the bytes the GigaPack's seasons were played with
# (B408: zig does not build fl26match.dll byte for byte again; the committed file is the tested one.
# 16.11.2026 e7681449: source 9a5a47d + the loading fixes pl_fill, pl_bs and the walk cave, without the B465 work in progress)
PREBUILT = ["fl26match"]
# The face pack: the face pool (tools/facepool.py: 32,760 faces made from numbers, none a real
# player's, no portraits), built here from the repository, or $FL26_REGEN_FACES when it is set (the
# pool with portraits, tools/facemini.py pack or share: every portrait number needs its .dds). Until 17.11. the pack came from
# fl26-modding-research/out/regenfaces, which still held the 30.09. pack of 103 game faces
# ("FL26RF01", 6,704 bytes): every release candidate shipped that one, never the pool. The pack
# is checked against the pool (facepool.pool_problems) and the build stops on anything else.
FACES = os.environ.get("FL26_REGEN_FACES") or None
FACE_ROOT = "FL26 Regen Faces"            # the livecpk root of the portraits (install_modules)


def face_pack(out, log=print):
    """modules\\fl26regen_faces.bin and livecpk\\FL26 Regen Faces of the pack under <out>: the
    pool built now, or $FL26_REGEN_FACES's copy of it. Stops when the pack is not the pool."""
    import facepool, tempfile
    mods = os.path.join(out, "modules")
    root = os.path.join(out, "livecpk", FACE_ROOT)
    want = facepool.pool_pack()
    if FACES:
        src = os.path.join(FACES, "fl26regen_faces.bin")
        if not os.path.isfile(src) or not os.path.isdir(os.path.join(FACES, FACE_ROOT)):
            raise SystemExit("FL26_REGEN_FACES=%s has no fl26regen_faces.bin and %s\\ -- unset it to ship "
                             "the face pool built from tools/facepool.py" % (FACES, FACE_ROOT))
        data = open(src, "rb").read()
        bad = facepool.pool_problems(data, want) + facepool.portrait_problems(data, os.path.join(FACES, FACE_ROOT))
        if bad:
            raise SystemExit("FL26_REGEN_FACES=%s: the face pack is not the face pool:\n  %s\n(unset "
                             "FL26_REGEN_FACES to ship the pool built from tools/facepool.py)" % (FACES, "\n  ".join(bad)))
        shutil.copy2(src, mods)
        shutil.copytree(os.path.join(FACES, FACE_ROOT), root)
        what = "from %s" % FACES
    else:
        with tempfile.TemporaryDirectory() as tmp:
            facepool.build(tmp, log=lambda *a: None)
            data = open(os.path.join(tmp, "fl26regen_faces.bin"), "rb").read()
            if data != want:
                raise SystemExit("the face pool came out other than facepool.pool_pack()")
            shutil.copy2(os.path.join(tmp, "fl26regen_faces.bin"), mods)
            shutil.copytree(os.path.join(tmp, FACE_ROOT), root)
        what = "built from tools/facepool.py"
    import hashlib
    md5 = hashlib.md5(data).hexdigest()
    if md5 != facepool.POOL_MD5 and not FACES:
        raise SystemExit("the face pool's md5 is %s, facepool.POOL_MD5 says %s -- a changed pool "
                         "changes POOL_MD5 in the same commit" % (md5, facepool.POOL_MD5))
    n = struct.unpack_from("<I", data, 520)[0]
    made = game_portraits(root)
    pics = sum(f.lower().endswith(".dds") for _d, _s, fs in os.walk(root) for f in fs)
    log("pack: face pool %s: %d faces, md5 %s, %d portrait(s) (%d made %dx%d)"
        % (what, n, md5, pics, made, PORTRAIT, PORTRAIT))
    return n
# written so that the line does not match itself
PRIVATE = re.compile(r"[A-Za-z]:\\\\?(de[v]|User[s]|instalacij[a])|stuc[e]|fl26-dump[s]", re.I)


def is_public(root):
    """is <root> a checkout of the public repository (its own worktrees included)?"""
    try:
        url = subprocess.run(["git", "-C", root, "remote", "get-url", "origin"],
                             capture_output=True, text=True).stdout
    except OSError:
        return False
    return "FootballLife-new-leagues" in url


def source(m):
    """the module's file: this repository's when it is the public one, else the public
    repository's copy first, then this one's.

    0.1.4 to 0.1.5.5 were packed from a public worktree while an older fl26-public sat beside
    it, and that folder won: four modules (fl26joindll, fl26swiss, fl26chain, fl26clubs) went
    out as 0.1.3.1's Lua next to 0.1.5.5's DLLs, and the world's season lines, split phases and
    built cups never reached the game (GitHub #69)."""
    if is_public(REPO):
        roots = [REPO]
    else:
        roots = [PUBLIC, REPO] if os.path.isdir(os.path.join(PUBLIC, "sider")) else [REPO]
    for root in roots:
        for sub in ("sider", os.path.join("sider", "experimental")):
            p = os.path.join(root, sub, m + ".lua")
            if os.path.exists(p):
                return p
    raise SystemExit("%s.lua is in neither sider/ nor sider/experimental/" % m)


def bundle(name, parts):
    """one module of `parts`' sources: each part's chunk runs in a function of its own (its locals
    stay its own) and the bundle's init calls theirs in order"""
    out = ["-- %s.lua -- built by tools/lbpack.py from %s; edit those files, not this one."
           % (name, ", ".join(p + ".lua" for p in parts)),
           "-- Each part logs as it always did. Sider's Lua has no pcall, so a part whose init raises",
           "-- stops the ones after it -- the order puts the oldest, most tried guards first.", ""]
    for i, p in enumerate(parts):
        src = open(source(p), encoding="utf-8").read().rstrip()
        out += ["-- ==== %s.lua ====" % p, "local part%d = (function()" % i, src, "end)()", ""]
    out += ["local PARTS = { " + ", ".join('{ "%s", part%d }' % (p, i) for i, p in enumerate(parts)) + " }",
            "local m = {}",
            "function m.init(ctx)",
            "  for _, p in ipairs(PARTS) do",
            '    if type(p[2]) == "table" and p[2].init then',
            "      p[2].init(ctx)          -- no pcall in Sider's Lua (run023, 2026-10-07)",
            "    end",
            "  end",
            "end",
            "return m", ""]
    return "\n".join(out)


PORTRAIT = 128   # the game's own player portraits: 128 pixels square, DXT5 (FL26 and FL27 alike)


def game_portraits(root):
    """every portrait .dds under <root> at the game's own size; returns how many it changed.

    The pack's portraits were 180 pixels square. FL26 draws them, but FL27 does not survive
    them: a new Master League with the Europack (31,896 new players, each shown with a pack
    portrait) died on its first day, twice, at the same place -- the same career without the
    portraits, or with them at 128, reached the board meeting (02.11.)."""
    from PIL import Image
    n = 0
    for d, _, files in os.walk(root):
        for f in files:
            p = os.path.join(d, f)
            if not f.lower().endswith(".dds") or "symbol" not in p.split(os.sep):
                continue
            with Image.open(p) as im:
                if im.size == (PORTRAIT, PORTRAIT):
                    continue
                im = im.convert("RGBA").resize((PORTRAIT, PORTRAIT), Image.LANCZOS)
            im.save(p, "DDS", pixel_format="DXT5")
            n += 1
    return n


def build(out, log=print):
    mods = os.path.join(out, "modules")
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(mods)
    for m in ORDER:
        if m in PER_WORLD:
            continue
        if m in BUNDLES:
            open(os.path.join(mods, m + ".lua"), "w", encoding="utf-8", newline="\n").write(bundle(m, BUNDLES[m]))
            continue
        shutil.copy2(source(m), os.path.join(mods, m + ".lua"))
        if m in FL27:
            shutil.copy2(source(FL27[m]), os.path.join(mods, m + ".fl27.lua"))
    env = dict(os.environ, ZIG=ZIG)
    sh = shutil.which("sh") or r"C:\Program Files\Git\bin\sh.exe"
    for name, script in DLLS.items():
        dst = os.path.join(mods, name + ".dll")
        r = subprocess.run([sh, os.path.join(HERE, "native", script), dst.replace("\\", "/")],
                           env=env, capture_output=True, text=True)
        if r.returncode or not os.path.exists(dst):
            raise SystemExit("%s failed:\n%s%s" % (script, r.stdout, r.stderr))
        for junk in (name + ".lib", name + ".pdb"):
            p = os.path.join(mods, junk)
            if os.path.exists(p):
                os.remove(p)
    for name in PREBUILT:
        shutil.copy2(os.path.join(HERE, "native", name + ".dll"), os.path.join(mods, name + ".dll"))
    face_pack(out, log)
    open(os.path.join(mods, "..", "modules.txt"), "w", encoding="utf-8", newline="\n").write(
        "".join(m + "\n" for m in ORDER))
    open(os.path.join(mods, "..", "retired.txt"), "w", encoding="utf-8", newline="\n").write(
        "".join("%s %s\n" % (p, b) for b, parts in BUNDLES.items() for p in parts)
        + "".join("%s %s\n" % (p, b) for p, b in SUPERSEDED.items()))
    bad = []
    for f in sorted(os.listdir(mods)):
        if f.endswith(".lua"):
            for i, line in enumerate(open(os.path.join(mods, f), encoding="utf-8", errors="replace"), 1):
                if PRIVATE.search(line):
                    bad.append("%s:%d: %s" % (f, i, line.strip()[:120]))
    if bad:
        raise SystemExit("private paths in the pack:\n  " + "\n  ".join(bad))
    log("pack: %d files in %s" % (len(os.listdir(mods)), mods))
    return mods


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    build(sys.argv[1])
