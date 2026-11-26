r"""python mszip.py [--no-exe] [--untested] [--no-faces]   -> out\mszip\ and out\FL26ModStudio-<version>.zip

FL Mod Studio in one folder:

  FL26ModStudio.exe     the window (tools/modstudio_main.py), frozen with PyInstaller as a
  _internal\            folder, not one file: a one-file .exe unpacks some 150 MB to a temporary
                        folder on every start, and an antivirus reads all of it each time --
                        that was the slow start people reported. modstudio/lang,
                        modstudio/assets (the icon) and lang are in _internal
  pack\                 the modules the League Builder's "Install the modules" puts in place
                        (tools/lbpack.py)
  README.html           the guide (guides/en/mod-studio-guide.md)
  README.<hr|es|fr|pt>.html  the same in Croatian, Spanish, French, Portuguese (guides/<code>/mod-studio-guide.md)
  LICENSE.txt           the FL Mod Studio License; LICENSE-MIT.txt for 0.3.0 and older and the MIT parts

Frozen from a staged copy of tools/ without the lines that point at
this machine's folders, and every staged source inside the .exe, the pack and the guides is
checked for drive paths and user names. No game file, no table, no club data goes in.
"""
import os, re, shutil, subprocess, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(REPO, "out", "mszip")
WORK = os.path.join(REPO, "out", "msexe")
STAGE = os.path.join(WORK, "src")
NAME = "FL26ModStudio"
PRIVATE = re.compile(r"[A-Za-z]:\\\\?(de[v]|User[s]|instalacij[a])|stuc[e]|fl26-dump[s]", re.I)
LOCAL_PATH_LINE = re.compile(r'^\s*sys\.path\.insert\(0, r"[A-Za-z]:\\[^"]*"\)\s*$')
HIDDEN = ["leaguebuilder", "bigjson", "lbplayers", "lbrating", "playeredit", "lbfaces", "lbpackage", "lbassets", "lbpack", "lbstadiums", "lbtrophies", "mktrophyvariants",
          "mkplayers", "mksplit", "mkreshape", "mkphases", "mkuecl", "mkeuropo", "mkkits", "mkemblems",
          "mkcrests", "mkregioncats", "mkregnames", "mkcup", "mkccup", "mkcoaches", "mkcatflags", "mkmpcol", "mkteamcrest", "afp",
          "siderdir", "mktactics", "shieldcrest", "crestmatch", "kitpics", "kitnumbers", "kitnumbers_data", "lbservers", "kitmaker", "kitpatterns",
          "siderroot", "cpkread", "countries", "flpaths", "caltab", "boundscan", "capstone", "py7zr", "regions", "rowkeep",
          "PIL.Image", "PIL.DdsImagePlugin"]

CSS = """
:root{--ink:#1d2328;--muted:#5b6670;--line:#dfe3e6;--bg:#fbfbfa;--accent:#0f6b4f;--code:#eef1f0}
@media (prefers-color-scheme:dark){:root{--ink:#e4e8ea;--muted:#9aa5ad;--line:#343c42;--bg:#16191b;--accent:#4fc59b;--code:#23292d}}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 "Segoe UI",system-ui,sans-serif}
main{max-width:52rem;margin:0 auto;padding:2rem 1.25rem 4rem}
h1{font-size:2rem;line-height:1.2;margin:0 0 1rem;letter-spacing:-.01em}
h2{font-size:1.3rem;margin:2.4rem 0 .6rem;padding-top:.4rem;border-top:1px solid var(--line)}
a{color:var(--accent)} hr{border:0;border-top:1px solid var(--line);margin:1.5rem 0}
code{background:var(--code);padding:.1em .35em;border-radius:4px;font:.9em Consolas,monospace}
pre{background:var(--code);padding:.8rem 1rem;border-radius:6px;overflow-x:auto} pre code{padding:0}
table{border-collapse:collapse;width:100%;margin:.8rem 0;font-size:.95rem}
th,td{border-bottom:1px solid var(--line);padding:.45rem .6rem;text-align:left;vertical-align:top}
th{color:var(--muted);font-weight:600}
blockquote{margin:1rem 0;padding:.6rem 1rem;border-left:3px solid var(--accent);background:var(--code);border-radius:0 6px 6px 0}
blockquote p{margin:.2rem 0} li{margin:.25rem 0}
"""


# sites a shipped patch set must never touch again: each crashed a release once
KNOWN_BAD = {"1412f9046": "MenuUtilityDemoPlayer+0x2b0 -> +0x6b0, the Master League / Be a Legend "
                          "creation crash of the 0.2.0 package (GitHub #122, #125)"}


def same_text(a, b):
    """two text files, line endings aside"""
    rd = lambda p: open(p, "rb").read().replace(b"\r\n", b"\n")
    return rd(a) == rd(b)


def check_pack(pack):
    """what went wrong once must not go out again (0.2.0 shipped an old fl26caps.lua):
    a known crash site in a module stops the zip; so does a fl26caps.lua that is not the
    patch set last generated (sider/fl26caps.<set>.lua, made by patchset.py and never copied
    over) or not the one installed in the game we test with (FL26_DIR). Modules that differ
    from the game's copy are listed: they were not played in the game in that form."""
    bad, untested = [], []
    mods = os.path.join(pack, "modules")
    for f in sorted(os.listdir(mods)):
        text = open(os.path.join(mods, f), "rb").read().decode("utf-8", "replace").lower()
        bad += ["%s: %s" % (f, why) for site, why in KNOWN_BAD.items() if site in text]
    sider = os.path.join(REPO, "sider")
    for g in sorted(os.listdir(sider)):
        if (g.startswith("fl26caps.") and g.endswith(".lua")
                and g not in ("fl26caps.lua", "fl26caps.fl27.lua", "fl26caps.template.lua")):
            # an FL 2027 set (patchset.py --fl27) is the pack's fl26caps.fl27.lua, the others its fl26caps.lua
            want = "fl26caps.fl27.lua" if ".fl27." in g else "fl26caps.lua"
            if not same_text(os.path.join(mods, want), os.path.join(sider, g)):
                bad.append("%s is not the generated sider/%s -- copy it over sider/%s" % (want, g, want))
    # the FL 2027 copies (<name>.fl27.lua) go into an FL_2027.exe folder under the plain name, so
    # they are compared with FL27_DIR's modules, the rest with FL26_DIR's
    for env, mine in (("FL26_DIR", lambda f: ".fl27." not in f), ("FL27_DIR", lambda f: ".fl27." in f)):
        if env == "FL27_DIR" and not any(".fl27." in f for f in os.listdir(mods)):
            continue
        game = os.environ.get(env)
        gmods = os.path.join(game, "SiderAddons", "modules") if game else None
        if gmods and os.path.isdir(gmods):
            for f in sorted(os.listdir(mods)):
                if not (f.endswith(".lua") and mine(f)):
                    continue
                plain = f.replace(".fl27.", ".")
                g = os.path.join(gmods, plain)
                if not os.path.exists(g) or not same_text(os.path.join(mods, f), g):
                    (bad if plain == "fl26caps.lua" else untested).append(
                        f + (": not the one installed in the game (%s) -- test the shipped file" % env
                             if plain == "fl26caps.lua" else ""))
        elif "--untested" in sys.argv:
            print("pack check: %s not set, the modules are not compared with the game's (--untested)" % env)
        else:
            bad.append("%s is not set, so nothing says these modules were played in the game -- "
                       "set it to the game folder you test with (or pass --untested for a fork's own build)" % env)
    # 0.2.0 went out once without the regen faces (lbpack only logs a missing face pack), and every
    # candidate up to 17.11. with the 30.09. pack of 103 game faces instead of the face pool
    faces = os.path.join(mods, "fl26regen_faces.bin")
    if "--no-faces" not in sys.argv:
        if not (os.path.exists(faces) and os.path.isdir(os.path.join(pack, "livecpk", "FL26 Regen Faces"))):
            bad.append("no regen face pack in the package -- lbpack.py builds the face pool "
                       "(or pass --no-faces for a fork without it)")
        else:
            import facepool
            data = open(faces, "rb").read()
            bad += ["fl26regen_faces.bin: %s" % b for b in facepool.pool_problems(data)]
            if data[:8] == facepool.MAGIC2:
                bad += ["fl26regen_faces.bin: %s" % b for b in
                        facepool.portrait_problems(data, os.path.join(pack, "livecpk", "FL26 Regen Faces"))]
    for f in untested:
        print("pack check: NOT PLAYED in the game in this form: %s" % f)
    return bad


def guide(md, html, lang):
    import markdown
    body = markdown.markdown(open(md, encoding="utf-8").read(), extensions=["tables", "fenced_code"])
    title = re.search(r"<h1>(.*?)</h1>", body).group(1)
    open(html, "w", encoding="utf-8").write(
        '<!doctype html>\n<html lang="%s"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>%s</title><style>%s</style></head><body><main>\n%s\n</main></body></html>\n"
        % (lang, title, CSS, body))


def version():
    return re.search(r'VERSION = "([^"]+)"', open(os.path.join(HERE, "modstudio", "__init__.py"),
                                                  encoding="utf-8").read()).group(1)


def stage():
    if os.path.exists(STAGE):
        shutil.rmtree(STAGE)
    os.makedirs(STAGE)

    def put(src, dst):
        lines = open(src, encoding="utf-8").read().split("\n")
        lines = [l for l in lines if not LOCAL_PATH_LINE.match(l)]
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, "w", encoding="utf-8", newline="\n").write("\n".join(lines))

    for f in os.listdir(HERE):
        if f.endswith(".py"):
            put(os.path.join(HERE, f), os.path.join(STAGE, f))
    for d, subs, files in os.walk(os.path.join(HERE, "modstudio")):
        subs[:] = [s for s in subs if s != "__pycache__"]
        for f in files:
            src = os.path.join(d, f)
            dst = os.path.join(STAGE, os.path.relpath(src, HERE))
            if f.endswith(".py"):
                put(src, dst)
            # _fl27mm*.pyd: the optional native tools (mod-manager-rust), only when someone built
            # them; without it the release builds as before and Game file tools says it is missing
            elif f.endswith((".json", ".ico", ".png", ".pyd")):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
    shutil.copytree(os.path.join(HERE, "lang"), os.path.join(STAGE, "lang"))


def modstudio_modules():
    out = []
    for d, subs, files in os.walk(os.path.join(STAGE, "modstudio")):
        subs[:] = [s for s in subs if s != "__pycache__"]
        for f in files:
            if f.endswith(".py"):
                rel = os.path.relpath(os.path.join(d, f), STAGE)[:-3].replace(os.sep, ".")
                out.append(rel[:-9] if rel.endswith(".__init__") else rel)
    return out


def freeze():
    stage()
    sep = ";"
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--onedir", "--windowed",
           "--contents-directory", "_internal",
           "--name", NAME, "--distpath", os.path.join(WORK, "dist"),
           "--workpath", os.path.join(WORK, "build"), "--specpath", WORK, "--paths", STAGE,
           "--icon", os.path.join(STAGE, "modstudio", "assets", "app.ico"),
           "--add-data", os.path.join(STAGE, "lang") + sep + "lang",
           "--add-data", os.path.join(STAGE, "modstudio", "assets") + sep + os.path.join("modstudio", "assets"),
           "--add-data", os.path.join(STAGE, "modstudio", "lang") + sep + os.path.join("modstudio", "lang")]
    for h in HIDDEN + modstudio_modules():
        cmd += ["--hidden-import", h]
    cmd.append(os.path.join(STAGE, "modstudio_main.py"))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("PyInstaller failed:\n" + r.stderr[-3000:])
    toc = open(os.path.join(WORK, "build", NAME, "PYZ-00.toc"), encoding="utf-8").read()
    used = sorted(set(re.findall(re.escape(STAGE).replace("\\\\", "[\\\\/]+") + r"[\\/]+([\w\\/]+\.py)", toc)))
    bad = []
    for f in used + ["modstudio_main.py"]:
        for i, l in enumerate(open(os.path.join(STAGE, f), encoding="utf-8"), 1):
            if PRIVATE.search(l):
                bad.append("%s:%d: %s" % (f, i, l.strip()[:110]))
    print("exe: %d of our modules inside" % len(used))
    return bad


def main():
    import lbpack
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    bad = []
    if "--no-exe" not in sys.argv:
        bad += freeze()
    shutil.copytree(os.path.join(WORK, "dist", NAME), OUT, dirs_exist_ok=True)
    lbpack.build(os.path.join(OUT, "pack"))
    bad += check_pack(os.path.join(OUT, "pack"))
    guide(os.path.join(REPO, "guides", "en", "mod-studio-guide.md"), os.path.join(OUT, "README.html"), "en")
    langs = ("hr", "es", "fr", "pt")
    for code in langs:
        guide(os.path.join(REPO, "guides", code, "mod-studio-guide.md"),
              os.path.join(OUT, "README.%s.html" % code), code)
    # the licence goes with every copy (LICENSE, rule 3); the MIT one for 0.3.0 and older and the contributors' parts
    # the optional native module's bc7 decoder follows iOrange/bcdec (MIT): its notice goes too
    for src, dst in (("LICENSE", "LICENSE.txt"), ("LICENSE-MIT", "LICENSE-MIT.txt"),
                     (os.path.join("mod-manager-rust", "LICENSE-BCDEC.txt"), "LICENSE-BCDEC.txt")):
        with open(os.path.join(REPO, src), encoding="utf-8") as f:
            text = f.read()
        with open(os.path.join(OUT, dst), "w", encoding="utf-8", newline="\r\n") as f:
            f.write(text)
    for f in ["README.html"] + ["README.%s.html" % c for c in langs] + [os.path.join("pack", "modules.txt")]:
        for i, l in enumerate(open(os.path.join(OUT, f), encoding="utf-8"), 1):
            if PRIVATE.search(l):
                bad.append("%s:%d: %s" % (f, i, l.strip()[:110]))
    if bad:
        raise SystemExit("the package cannot go out (private text, or a check above):\n  " + "\n  ".join(bad))
    z = os.path.join(REPO, "out", "%s-%s.zip" % (NAME, version()))
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(OUT):
            for f in files:
                p = os.path.join(root, f)
                zf.write(p, os.path.join("FL26 Mod Studio", os.path.relpath(p, OUT)))
    print("zip: %s (%.1f MB)" % (z, os.path.getsize(z) / 1e6))
    return 0


if __name__ == "__main__":
    sys.exit(main())
