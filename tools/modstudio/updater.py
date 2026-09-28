"""Updates: is there a newer FL26 Mod Studio on GitHub, and put it in place.

The releases are the public repository's, tagged modstudio-<version>, each with one zip
(FL26ModStudio-<version>.zip, a "FL26 Mod Studio" folder inside). GitHub lists a sha256 for
every asset; the download is checked against it and against its size before anything moves.

A running .exe cannot overwrite itself, so the new files are unpacked to a temporary folder and
a small batch file copies them over the program's folder once this program has closed, then
starts it again. Settings, projects, backups and the unpacked tables live in %APPDATA% and are
not touched; neither is the game.

Run from source (not the frozen .exe) the check still works, but installing only opens the
release page.
"""
import hashlib, json, os, re, subprocess, sys, tempfile, urllib.request, zipfile

from modstudio import VERSION

REPO = "Matozanato/FootballLife-new-leagues"
API = "https://api.github.com/repos/%s/releases?per_page=30" % REPO
TAG = re.compile(r"^modstudio-(\d+(?:\.\d+)*)$")
EXE = "FL26ModStudio.exe"
FOLDER = "FL26 Mod Studio"


def vtuple(v):
    return tuple(int(x) for x in v.split("."))


def frozen():
    return bool(getattr(sys, "frozen", False))


def program_dir():
    return os.path.dirname(os.path.abspath(sys.executable if frozen() else sys.argv[0]))


def _get(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "FL26ModStudio/" + VERSION,
                                               "Accept": "application/vnd.github+json"})
    return urllib.request.urlopen(req, timeout=timeout)


def latest(progress=None):
    """the newest published release: {"version", "url", "size", "sha256", "page", "notes"},
    or None when GitHub has nothing newer than this program"""
    with _get(API) as r:
        rels = json.load(r)
    best = None
    for rel in rels:
        m = TAG.match(rel.get("tag_name") or "")
        if not m or rel.get("draft") or rel.get("prerelease"):
            continue
        zips = [a for a in rel.get("assets", []) if a.get("name", "").lower().endswith(".zip")]
        if not zips:
            continue
        a = zips[0]
        digest = a.get("digest") or ""
        info = {"version": m.group(1), "url": a["browser_download_url"], "size": a.get("size", 0),
                "sha256": digest[7:] if digest.startswith("sha256:") else "",
                "page": rel.get("html_url", ""), "notes": rel.get("body") or ""}
        if best is None or vtuple(info["version"]) > vtuple(best["version"]):
            best = info
    if best and vtuple(best["version"]) > vtuple(VERSION):
        return best
    return None


def download(info, progress=None):
    """the release zip into a temporary folder, checked; returns its path"""
    d = tempfile.mkdtemp(prefix="FL26ModStudio-%s-" % info["version"])
    path = os.path.join(d, "FL26ModStudio-%s.zip" % info["version"])
    h, got = hashlib.sha256(), 0
    with _get(info["url"], timeout=60) as r, open(path, "wb") as f:
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            f.write(b)
            h.update(b)
            got += len(b)
            if progress and info["size"]:
                progress(int(got * 100 / info["size"]))
    if info["size"] and got != info["size"]:
        raise RuntimeError("download incomplete: %d of %d bytes" % (got, info["size"]))
    if info["sha256"] and h.hexdigest() != info["sha256"].lower():
        raise RuntimeError("download damaged: its checksum does not match the release's")
    return path


def can_write(d):
    try:
        t = tempfile.NamedTemporaryFile(dir=d, prefix=".fl26w", delete=True)
        t.close()
        return True
    except OSError:
        return False


def install(zip_path, dst=None, restart=True):
    """unpack next to the zip and start the batch file that swaps the files in once this
    program has exited. The caller quits the application right after."""
    stage = os.path.join(os.path.dirname(zip_path), "new")
    with zipfile.ZipFile(zip_path) as z:
        for n in z.namelist():
            p = os.path.normpath(os.path.join(stage, n))
            if not p.startswith(os.path.normpath(stage) + os.sep):
                raise RuntimeError("unsafe path in the zip: %s" % n)
        z.extractall(stage)
    src = os.path.join(stage, FOLDER)
    if not os.path.isfile(os.path.join(src, EXE)):
        raise RuntimeError("the zip has no %s\\%s" % (FOLDER, EXE))
    dst = dst or program_dir()
    # a one-file .exe runs as two processes (the loader holds the file); wait for both
    pids = sorted({os.getpid(), os.getppid()})
    bat = os.path.join(os.path.dirname(zip_path), "update.cmd")
    log = os.path.join(tempfile.gettempdir(), "FL26ModStudio-update.log")
    sys32 = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")
    tool = lambda n: '"%s"' % os.path.join(sys32, n)
    lines = ["@echo off", "setlocal", ":wait"]
    for p in pids:
        lines.append('%s /fi "PID eq %d" /nh | %s " %d " >nul && (%s -n 2 127.0.0.1 >nul & goto wait)'
                     % (tool("tasklist.exe"), p, tool("find.exe"), p, tool("ping.exe")))
    lines += ['%s "%s" "%s" /E /R:5 /W:1 /NP /NJH > "%s" 2>&1' % (tool("robocopy.exe"), src, dst, log),
              'if errorlevel 8 (echo The update could not be copied into "%s". >> "%s" & exit /b 1)' % (dst, log),
              'start "" "%s"' % os.path.join(dst, EXE) if restart else 'rem no restart',
              'rmdir /s /q "%s"' % os.path.dirname(zip_path)]
    open(bat, "w", encoding="mbcs", newline="\r\n").write("\n".join(lines) + "\n")
    # a hidden console, not a detached process: robocopy and ping need one
    flags = 0x08000000 | 0x00000200                 # CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP
    subprocess.Popen([os.path.join(sys32, "cmd.exe"), "/c", bat], creationflags=flags, close_fds=True,
                     cwd=tempfile.gettempdir())
    return log
