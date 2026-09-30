r"""python lbpack.py <out dir>   -> the module pack the league builder installs

The builder's worlds are read by our modules, and only by the versions that read the world
file (docs/mod-studio.md). A person who has the public release, or nothing at all, needs
this exact set, so it ships inside the builder and "Install modules" puts it in place.

What goes in, and from where -- every file from a source that is ours and clean:

  sider/*.lua, sider/experimental/*.lua
                            the world-file readers and the guards. Where the public repository
                            sits beside this one (../fl26-public), its copies are taken first, so
                            the pack is exactly what is published; otherwise this repository's.
  tools/native/*.c          the DLLs, compiled now with zig (tools/native/build-*.sh)
  the regen face pack       fl26regen_faces.bin (into modules) and the livecpk root
                            "FL26 Regen Faces" (into livecpk), from $FL26_REGEN_FACES or
                            ../fl26-modding-research/out/regenfaces. It holds game renders, so it
                            is never in a repository, only in the package; without it the pack
                            is built anyway and regens keep the generic face.

fl26regions.lua and fl26regnames.lua are not in the pack: they name the competitions and
regions of one world, so the builder makes them per world and switch-on puts them in place.

The pack is checked before it is written out: no drive letters, no user folders.
"""
import os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PUBLIC = os.path.join(os.path.dirname(REPO), "fl26-public")
# zig: $ZIG, else the copy in tools\ beside this repo's folder, else the one on PATH
ZIG = os.environ.get("ZIG") or next(
    (z for z in [os.path.join(os.path.dirname(REPO), "tools", "zig-x86_64-windows-0.16.0", "zig.exe")]
     if os.path.exists(z)), "zig")

# the lua.module lines, in load order (the order of the working install)
ORDER = [
    "fl26caps", "fl26nullguard", "fl26nullguard2", "fl26nullguard4", "fl26nullguard5",
    "fl26nullguard7", "fl26nullguard8", "fl26nullguard9", "fl26nullguard10", "fl26joindll",
    "fl26hdr192", "fl26chain", "fl26comptab", "fl26slotnames", "fl26clubs", "fl26regen", "fl26editlist",
    "fl26rank", "fl26deeprank", "fl26regions", "fl26reg64", "fl26regnames", "fl26catlist",
    "fl26swiss", "fl26augseason", "fl26superguard", "fl26resultsguard", "fl26ctlguard",
    "fl26seasonend",
]
PER_WORLD = {"fl26regions", "fl26regnames"}
DLLS = {"fl26join": "build-join.sh", "fl26chain": "build-chain.sh",
        "fl26clubs": "build-clubs.sh", "fl26swiss": "build-swiss.sh", "fl26regen": "build-regen.sh"}
FACES = os.environ.get("FL26_REGEN_FACES") or os.path.join(os.path.dirname(REPO), "fl26-modding-research",
                                                           "out", "regenfaces")
FACE_ROOT = "FL26 Regen Faces"            # the livecpk root of the portraits (install_modules)
# written so that the line does not match itself
PRIVATE = re.compile(r"[A-Za-z]:\\\\?(de[v]|User[s]|instalacij[a])|stuc[e]|fl26-dump[s]", re.I)


def source(m):
    """the module's file: the public repository's copy first, then this one's"""
    roots = [PUBLIC, REPO] if os.path.isdir(os.path.join(PUBLIC, "sider")) else [REPO]
    for root in roots:
        for sub in ("sider", os.path.join("sider", "experimental")):
            p = os.path.join(root, sub, m + ".lua")
            if os.path.exists(p):
                return p
    raise SystemExit("%s.lua is in neither sider/ nor sider/experimental/" % m)


def build(out, log=print):
    mods = os.path.join(out, "modules")
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(mods)
    for m in ORDER:
        if m in PER_WORLD:
            continue
        shutil.copy2(source(m), os.path.join(mods, m + ".lua"))
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
    faces = os.path.join(FACES, "fl26regen_faces.bin")
    if os.path.exists(faces) and os.path.isdir(os.path.join(FACES, FACE_ROOT)):
        shutil.copy2(faces, mods)
        shutil.copytree(os.path.join(FACES, FACE_ROOT), os.path.join(out, "livecpk", FACE_ROOT))
        log("pack: regen face pack from %s" % FACES)
    else:
        log("pack: NO regen face pack (%s) -- regens will keep the generic face" % FACES)
    open(os.path.join(mods, "..", "modules.txt"), "w", encoding="utf-8", newline="\n").write(
        "".join(m + "\n" for m in ORDER))
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
