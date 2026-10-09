r"""python mszip.py [--no-exe]   -> out\mszip\ and out\FL26ModStudio-<version>.zip

FL26 Mod Studio in one folder:

  FL26ModStudio.exe     the window (tools/modstudio_main.py), frozen with PyInstaller as a
  _internal\            folder, not one file: a one-file .exe unpacks some 150 MB to a temporary
                        folder on every start, and an antivirus reads all of it each time --
                        that was the slow start people reported. modstudio/lang,
                        modstudio/assets (the icon) and lang are in _internal
  pack\                 the modules the League Builder's "Install the modules" puts in place
                        (tools/lbpack.py)
  README.html           the guide (docs/mod-studio-guide.md)
  README.<hr|es|fr>.html  the same in Croatian, Spanish, French (docs/mod-studio-guide.<code>.md)

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
HIDDEN = ["leaguebuilder", "lbplayers", "playeredit", "lbfaces", "lbpackage", "lbassets", "lbpack", "lbstadiums",
          "mkplayers", "mksplit", "mkreshape", "mkphases", "mkuecl", "mkeuropo", "mkkits", "mkemblems",
          "mkcrests", "mkregioncats", "mkregnames", "mkcup", "mkccup", "mkcoaches", "mkcatflags", "afp",
          "siderdir", "mktactics", "shieldcrest", "crestmatch", "kitpics", "lbservers", "kitmaker",
          "siderroot", "cpkread", "countries", "flpaths", "caltab", "boundscan", "capstone", "py7zr",
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
            elif f.endswith((".json", ".ico", ".png")):
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
    guide(os.path.join(REPO, "docs", "mod-studio-guide.md"), os.path.join(OUT, "README.html"), "en")
    langs = ("hr", "es", "fr")
    for code in langs:
        guide(os.path.join(REPO, "docs", "mod-studio-guide.%s.md" % code),
              os.path.join(OUT, "README.%s.html" % code), code)
    for f in ["README.html"] + ["README.%s.html" % c for c in langs] + [os.path.join("pack", "modules.txt")]:
        for i, l in enumerate(open(os.path.join(OUT, f), encoding="utf-8"), 1):
            if PRIVATE.search(l):
                bad.append("%s:%d: %s" % (f, i, l.strip()[:110]))
    if bad:
        raise SystemExit("private text in the package:\n  " + "\n  ".join(bad))
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
