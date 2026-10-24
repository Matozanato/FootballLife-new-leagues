r"""coldstart.py -- "test as a new player": a world zip installed and switched on through the
Mod Studio exe on a COLD PC, with the window watched every second.

HARD RULE (mato 17.10., B104): before every Mod Studio release and every world zip. Testers
(David, Vicentico) froze for 1-13 minutes on the first switch to Modpack r10: every made kit was
drawn again on their PCs (the kitmaker.txt stamps held the building PC's path), while on our PC
the kits were already drawn with our own stamps (warm), so no test of ours ever saw it.
Fixes: ad66369 (stamp by folder inside the kit library; a world from a zip keeps its kits),
72686bf / d75bf38 (the switch in a worker, the cards held).

What "cold" is -- absent on a new player's PC, present on ours:
  %APPDATA%\FL26ModStudio            settings.json, tables\ (the game's unpacked tables; a first
                                     start unpacks them by itself, 1-2 min), recipes\, packs\,
                                     newlife\ cache, running.lock, crash.log
  SiderAddons\livecpk\<world>        the world itself (+ its .modstudio mark)
  SiderAddons\content\kit-server\<world>\...\kitmaker.txt
                                     the made kits and their stamps (ours: stamps of OUR path)
  SiderAddons\content\scoreboard-server\<world>, our map lines in every content map
  SiderAddons\ModStudio\             installed.json, backups\ + backups.json (restore points)
  SiderAddons\modules\fl26*.lua, fl26world.txt, fl26regen_faces.bin, CommonLib's "-- FL26 world" line
  Documents\KONAMI\...\2026          save_<world> folders, modstudio-saves.json (the first swap
                                     ever copies the whole save folder into backups\saves)
  %TEMP%                             nothing of ours; Install unpacks the zip there (fl26ms_*)

Modes (the default is "all"):
  prepare   builds the cold copy: a minimal game folder OUTSIDE C: on a path with a space
            (default "D:\FL26 cold test\game"), read from --from (default E:\instalacija, only
            READ): FL_2026.exe, download\data_s2526*.cpk + data_extra*.cpk (for the first-start
            table unpack), SiderAddons with a sider.ini from before Mod Studio
            (sider_ini_backups, lines with "fl26" dropped), the modules without ours, every
            content server's map files without our lines, the kits the kit library lends
            numbers from (B214: the first, a light and a dark one); an empty --apdata with
            settings.json = {"game": <copy>} only (without it Mod Studio guesses the game folder from the registry: E:\instalacija here); a
            save folder of its own (FL26_SAVE_ROOT) -- never Documents\KONAMI.
  run       must run in the interactive session (session 1): starts the exe with APPDATA =
            --apdata, FL26_SAVE_ROOT = the copy's, FL26_DIR/EXE/SIDER unset; waits for the
            first-start table unpack; My world > + Add... > Choose a file... > the zip > Add >
            Install the world; [with --other-zip: that one first, then Activate it and Activate
            the Modpack again]; a screenshot before every press (k_cold_<NN>_<step>.png in
            --shots); every 1 s SendMessageTimeout(WM_NULL, 1 s) to the main window.
  all       prepare, then run -- here when this is session 1, else through the FL26Uia
            scheduled task (its "launch" op starts a .bat in session 1); waits for the result.

PASS needs: every install completes (Ready to play / Almost ready), no stretch of the window not
answering longer than 5 s (whole run), the Modpack's first switch <= 60 s (Install's switch-on,
and the Activate when --other-zip gives a second world), no question answered No.

    set PYTHONIOENCODING=utf-8
    python tools/coldstart.py --zip D:\dev\fl26\modpack-build\FL26-Modpack-NL15B6-r10.zip ^
        --exe "D:\dev\fl26\ModStudio-editpack-d75bf38\FL26 Mod Studio\FL26ModStudio.exe" ^
        [--game "D:\FL26 cold test\game"] [--apdata "D:\FL26 cold test\appdata"] [--shots DIR]
        [--other-zip <a second world zip> | --make-other _FL26CroatiaD1D2cup] [--reset]
    python tools/coldstart.py prepare --dry-run ...     what would be copied, nothing written

Nothing is written to --from (E:), C:\Football Life 2026 or Documents\KONAMI; the cold root must
not be on E:. --reset empties the cold root first (only a root this script made: .coldstart in it).
"""
import argparse, ctypes, glob, json, os, re, shutil, subprocess, sys, tempfile, threading, time, unicodedata, zipfile
from ctypes import wintypes

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_DEFAULT = r"E:\instalacija"
GAME_DEFAULT = r"D:\FL26 cold test\game"
MARKER = ".coldstart"
TASK_DEFAULT = "FL26Uia"
MAIN_TITLE = "FL26 Mod Studio"
LIMIT_HANG = 5.0             # s: longest stretch the window may not answer
LIMIT_SWITCH = 60.0          # s: the Modpack's first switch
SKIP_ENV = ("FL26_DIR", "FL26_EXE", "FL26_SIDER", "FL26_SET", "FL26_PESDB", "FL26_OUT", "FL26_SAVE_ROOT",
            "QT_QPA_PLATFORM", "FL26_SHOT_SIZE", "FL26_SHOT_ADD")


def say(*a):
    print(*a, flush=True)


def die(msg, code=2):
    say("ERROR: " + msg)
    raise SystemExit(code)


def gb(n):
    return "%.2f GB" % (n / 1e9)


# =============================================================================== prepare ====
def norm_path(p):
    return os.path.normcase(os.path.abspath(p))


def guard(cfg):
    """the cold copy never goes on E:, never on C: for the game, the game path has a space"""
    for key in ("root", "game", "apdata", "shots", "save_root"):
        p = norm_path(cfg[key])
        if p.startswith("e:"):
            die("%s (%s) is on E: -- the cold copy never goes on E:" % (key, cfg[key]))
        if p.startswith(norm_path(cfg["src"])):
            die("%s (%s) is inside the source game %s" % (key, cfg[key], cfg["src"]))
    if norm_path(cfg["game"]).startswith("c:"):
        die("the game copy must be outside C: (a player's game is often on another drive)")
    if " " not in cfg["game"]:
        die("the game copy's path must have a space in it (%s)" % cfg["game"])
    if not norm_path(cfg["game"]).startswith(norm_path(cfg["root"])):
        die("--game must be inside the cold root %s" % cfg["root"])


def vanilla_ini(src_sider, given=None):
    """sider.ini as it was before Mod Studio: --sider-ini, else the oldest copy in
    SiderAddons\\sider_ini_backups with no _FL26 root and no fl26*.lua switched on"""
    if given:
        return given
    d = os.path.join(src_sider, "sider_ini_backups")
    for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        p = os.path.join(d, f)
        on = [l for l in open(p, encoding="utf-8", errors="replace").read().lower().splitlines()
              if l.strip() and not l.lstrip().startswith(("#", ";"))]
        if not any("_fl26" in l or "fl26" in l for l in on):
            return p
    die("no sider.ini from before Mod Studio under %s: give --sider-ini" % d)


def ours(line):
    """a map / ini line of ours (Build's tag, an install header, a world folder, the Modpack's kits)"""
    l = line.lower()
    return (b"fl26 mod studio" in l or b"_fl26" in l or b"modpack\\" in l or b"modpack/" in l
            or b"fl26" in l and (b".lua" in l or b"livecpk" in l))


def filtered(src):
    data = open(src, "rb").read()
    lines = data.split(b"\n")
    keep = [l for l in lines if not ours(l)]
    return b"\n".join(keep), len(lines) - len(keep)


def numbers_kit_src(lib):
    """the kit the kit library lends numbers from, as lbservers.numbers_kit picks it (sorted
    walk, the first p1 with _back, _leg and _name), on the library WITHOUT our folders -- the one a
    player's PC with the plain library finds, so the kit stamps come out as on a player's PC"""
    p1s = []
    for d, subs, files in os.walk(lib):
        if os.path.normcase(d) == os.path.normcase(lib):
            subs[:] = [s for s in subs if not (s.lower().startswith("_fl26") or s.lower() == "modpack")]
        if os.path.basename(d).lower() == "p1":
            p1s.append((d, files))
    kits = numbers_kits_src(lib, p1s, 1)
    return kits[0] if kits else None


def numbers_kits_src(lib, p1s=None, most=None):
    """B214: the kits the library lends numbers from, as lbservers.numbers_kits picks them (the
    first, a light and a dark one), on the library without our folders"""
    import kitpics, lbservers
    if p1s is None:
        p1s = []
        for d, subs, files in os.walk(lib):
            if os.path.normcase(d) == os.path.normcase(lib):
                subs[:] = [s for s in subs if not (s.lower().startswith("_fl26") or s.lower() == "modpack")]
            if os.path.basename(d).lower() == "p1":
                p1s.append((d, files))
    out, want, seen = [], {"light", "dark"}, 0
    for d, files in sorted(p1s):
        names = [f.lower() for f in files]
        if not all(any(n.endswith(s + ".ftex") for n in names) for s in ("_back", "_leg", "_name")):
            continue
        if not out:
            out.append(os.path.dirname(d))
        if most == 1 or not want or seen >= lbservers.LOOK:
            break
        seen += 1
        c = kitpics.ink(d)
        lum = kitpics._lum(c) if c else None
        kind = None if lum is None else "light" if lum >= lbservers.LIGHT else "dark" if lum <= lbservers.DARK else None
        if kind in want:
            want.discard(kind)
            if os.path.dirname(d) not in out:
                out.append(os.path.dirname(d))
    return out


class Plan:
    """what prepare copies; dry: only count"""

    def __init__(self, dry):
        self.dry, self.n, self.bytes, self.dropped = dry, 0, 0, 0

    def mkdir(self, d):
        if not self.dry:
            os.makedirs(d, exist_ok=True)

    def copy(self, a, b):
        self.n += 1
        self.bytes += os.path.getsize(a)
        if self.dry:
            return
        os.makedirs(os.path.dirname(b), exist_ok=True)
        if os.path.exists(b) and os.path.getsize(a) == os.path.getsize(b) \
                and int(os.path.getmtime(a)) == int(os.path.getmtime(b)):
            return
        shutil.copy2(a, b)

    def write(self, b, data):
        self.n += 1
        self.bytes += len(data)
        if not self.dry:
            os.makedirs(os.path.dirname(b), exist_ok=True)
            open(b, "wb").write(data)

    def copytree(self, a, b, skip=lambda name: False):
        for dp, dn, fn in os.walk(a):
            dn[:] = [x for x in dn if not skip(x)]
            for f in fn:
                if not skip(f):
                    s = os.path.join(dp, f)
                    self.copy(s, os.path.join(b, os.path.relpath(s, a)))


def skip_module(name):
    n = name.lower()
    return (n.startswith("fl26") or n.startswith("before-builder") or ".before-" in n or ".bak" in n
            or ".wrong" in n or n.endswith(".prev"))


def prepare(cfg, dry=False, reset=False):
    guard(cfg)
    src, root, game = cfg["src"], cfg["root"], cfg["game"]
    src_sider = os.path.join(src, "SiderAddons")
    for p in (os.path.join(src, "FL_2026.exe"), os.path.join(src_sider, "sider.ini")):
        if not os.path.isfile(p):
            die("not a game folder: no %s" % p)
    if not os.path.isfile(cfg["zip"]):
        die("no zip %s" % cfg["zip"])
    if os.path.isdir(root) and os.listdir(root):
        if not os.path.exists(os.path.join(root, MARKER)):
            die("%s is not empty and was not made by coldstart.py (no %s): choose another --game" % (root, MARKER))
        if reset and not dry:
            # everything but the game's exe and archives (nothing of them is warm or cold)
            say("reset: emptying %s (the copied FL_2026.exe and download stay)" % root)
            for base, keep in ((root, {MARKER.lower(), os.path.basename(game).lower()}),
                               (game, {"fl_2026.exe", "download"})):
                for n in os.listdir(base) if os.path.isdir(base) else []:
                    if n.lower() not in keep:
                        p = os.path.join(base, n)
                        shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
        elif not reset:
            ms = os.path.join(cfg["apdata"], "FL26ModStudio")
            if os.path.isdir(ms) and set(os.listdir(ms)) - {"settings.json"}:
                die("%s is warm already (a run used it): --reset for a cold one" % ms)
            if os.path.isdir(os.path.join(game, "SiderAddons", "ModStudio")):
                die("the game copy is warm already (SiderAddons\\ModStudio there): --reset for a cold one")
    pl = Plan(dry)
    pl.mkdir(root)
    if not dry:
        open(os.path.join(root, MARKER), "w").write("made by tools/coldstart.py %s\n" % time.strftime("%Y-%m-%d %H:%M"))
    # -- the game: the exe, the archives the first start unpacks the tables from
    pl.copy(os.path.join(src, "FL_2026.exe"), os.path.join(game, "FL_2026.exe"))
    dl = os.path.join(src, "download")
    for c in sorted(glob.glob(os.path.join(dl, "data_s2526*.cpk")) + glob.glob(os.path.join(dl, "data_extra*.cpk"))):
        pl.copy(c, os.path.join(game, "download", os.path.basename(c)))
    # -- Sider: sider.ini from before Mod Studio, its roots as (empty) folders
    sider = os.path.join(game, "SiderAddons")
    ini_src = vanilla_ini(src_sider, cfg.get("sider_ini"))
    ini, n = filtered(ini_src)
    pl.dropped += n
    pl.write(os.path.join(sider, "sider.ini"), ini)
    roots = 0
    for l in ini.decode("utf-8", "replace").splitlines():
        m = re.match(r'\s*cpk\.root\s*=\s*"?\.\\(.+?)"?\s*$', l)
        if m:
            pl.mkdir(os.path.join(sider, m.group(1)))
            roots += 1
    for f in ("sider.exe", "sider.dll"):
        if os.path.isfile(os.path.join(src_sider, f)):
            pl.copy(os.path.join(src_sider, f), os.path.join(sider, f))
    # -- modules: the pack's own without ours (a new player has none of Mod Studio's)
    pl.copytree(os.path.join(src_sider, "modules"), os.path.join(sider, "modules"), skip_module)
    cl = os.path.join(src_sider, "modules", "lib", "CommonLib.lua")
    if os.path.isfile(cl):
        data = open(cl, "rb").read()
        pl.write(os.path.join(sider, "modules", "lib", "CommonLib.lua"),
                 b"\n".join(l for l in data.split(b"\n") if b"-- FL26 world" not in l))
    # -- content: each server folder with its map / config files, our lines out
    content = os.path.join(src_sider, "content")
    for s in sorted(os.listdir(content)):
        sd = os.path.join(content, s)
        if not os.path.isdir(sd):
            continue
        pl.mkdir(os.path.join(sider, "content", s))
        for f in os.listdir(sd):
            p = os.path.join(sd, f)
            if not os.path.isfile(p) or os.path.getsize(p) > 4 << 20:
                continue
            if f.lower().endswith((".txt", ".ini", ".lua", ".csv", ".json")):
                data, n = filtered(p)
                pl.dropped += n
                pl.write(os.path.join(sider, "content", s, f), data)
            elif f.lower() == "dummy.bin":
                pl.copy(p, os.path.join(sider, "content", s, f))
    pl.mkdir(os.path.join(sider, "livecpk"))
    lib = os.path.join(content, "kit-server")
    kits = numbers_kits_src(lib) if os.path.isdir(lib) else []
    for k in kits:
        pl.copytree(k, os.path.join(sider, "content", "kit-server", os.path.relpath(k, lib)))
    # -- the player's own save folder (FL26_SAVE_ROOT), never Documents\KONAMI
    save = os.path.join(cfg["save_root"], "save")
    if cfg.get("saves_from"):
        pl.copytree(cfg["saves_from"], save)
    else:
        pl.write(os.path.join(save, "SYSTEM00000000"), b"options")
        pl.write(os.path.join(save, "ML00000000"), b"a career before")
    # -- Mod Studio's settings: an empty folder but for the game folder
    ms = os.path.join(cfg["apdata"], "FL26ModStudio")
    pl.write(os.path.join(ms, "settings.json"), json.dumps({"game": game}, indent=1).encode("utf-8"))
    pl.mkdir(cfg["shots"])
    pl.mkdir(os.path.join(root, "results"))
    say("%s %d files, %s into %s (%d lines of ours left out; sider.ini from %s; %d Sider roots as empty "
        "folders; numbers kits %s)" % ("would copy" if dry else "copied", pl.n, gb(pl.bytes), root, pl.dropped,
                                       ini_src, roots, ", ".join(os.path.relpath(k, lib) for k in kits) or "none"))
    if cfg.get("make_other"):
        out = os.path.join(root, "other-%s.zip" % cfg["make_other"])
        if dry:
            say("would export %s from %s to %s (read only there)" % (cfg["make_other"], src_sider, out))
        elif not os.path.isfile(out):
            sys.path.insert(0, HERE)
            from modstudio import installer as I
            say("exporting %s (a second world, read only from %s) ..." % (cfg["make_other"], src_sider))
            I.export_world(src_sider, cfg["make_other"], out, log=say)
        cfg["other_zip"] = out
    if not dry:
        json.dump(cfg, open(cfg["config"], "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        say("config %s" % cfg["config"])
    return cfg


def zip_world(path):
    """the world a world zip carries (livecpk\\<_FL26...>\\fl26world.txt)"""
    with zipfile.ZipFile(path) as z:
        for n in z.namelist():
            m = re.search(r"(?:^|/)livecpk/(_FL26[^/]*)/fl26world\.txt$", n, re.I)
            if m:
                return m.group(1)
    die("%s is not a world zip (no livecpk\\_FL26...\\fl26world.txt)" % path)


# ================================================================================ Win32 =====
u32 = ctypes.WinDLL("user32", use_last_error=True)
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
u32.SendMessageTimeoutW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
                                    wintypes.UINT, wintypes.UINT, ctypes.POINTER(ctypes.c_size_t)]
u32.SendMessageTimeoutW.restype = ctypes.c_size_t
u32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
u32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
u32.IsHungAppWindow.argtypes = [wintypes.HWND]
WM_NULL, WM_CLOSE, WM_COMMAND, WM_SETTEXT = 0x0000, 0x0010, 0x0111, 0x000C
SMTO_ABORTIFHUNG, SMTO_ERRORONEXIT = 0x0002, 0x0020


def session_id():
    s = wintypes.DWORD()
    k32.ProcessIdToSessionId(os.getpid(), ctypes.byref(s))
    return s.value


def exe_of(pid):
    h = k32.OpenProcess(0x1000, False, pid)          # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return ""
    try:
        buf, n = ctypes.create_unicode_buffer(1024), wintypes.DWORD(1024)
        return buf.value if k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)) else ""
    finally:
        k32.CloseHandle(h)


def text_of(h):
    n = u32.GetWindowTextLengthW(h)
    b = ctypes.create_unicode_buffer(n + 1)
    u32.GetWindowTextW(h, b, n + 1)
    return b.value


def edit_text(h):
    """an edit box's text in another process: WM_GETTEXT (GetWindowText reads only its caption)"""
    b = ctypes.create_unicode_buffer(1024)
    u32.SendMessageW(h, 0x000D, 1024, ctypes.cast(b, ctypes.c_void_p).value)
    return b.value


def class_of(h):
    b = ctypes.create_unicode_buffer(256)
    u32.GetClassNameW(h, b, 256)
    return b.value


def windows(exe=None):
    """[(hwnd, pid, title, class)] of the visible top-level windows (of the process running exe)"""
    out, cache = [], {}

    def cb(h, _l):
        if u32.IsWindowVisible(h):
            pid = wintypes.DWORD()
            u32.GetWindowThreadProcessId(h, ctypes.byref(pid))
            if exe is not None:
                if pid.value not in cache:
                    cache[pid.value] = os.path.normcase(exe_of(pid.value)) == os.path.normcase(exe)
                if not cache[pid.value]:
                    return True
            out.append((h, pid.value, text_of(h), class_of(h)))
        return True
    u32.EnumWindows(WNDENUMPROC(cb), 0)
    return out


def children(h):
    out = []

    def cb(c, _l):
        out.append(c)
        return True
    u32.EnumChildWindows(h, WNDENUMPROC(cb), 0)
    return out


def answers(h, ms=1000):
    """the window took a WM_NULL within ms"""
    r = ctypes.c_size_t()
    return bool(u32.SendMessageTimeoutW(h, WM_NULL, 0, 0, SMTO_ABORTIFHUNG | SMTO_ERRORONEXIT, ms, ctypes.byref(r)))


def running_names():
    try:
        out = subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True, text=True,
                             creationflags=0x08000000).stdout.lower()
    except OSError:
        return ""
    return out


class Sampler(threading.Thread):
    """every `period` s: did the window answer a WM_NULL within 1 s (and IsHungAppWindow)"""

    def __init__(self, hwnd, period=1.0, pid=None, dumps=None):
        super().__init__(daemon=True)
        self.hwnd, self.period, self.samples, self.stop = hwnd, period, [], threading.Event()
        self.pid, self.dumps, self.bad_run = pid, dumps, 0

    def dump(self):
        """what the not-answering window is doing: py-spy's stacks into results/hang-*.txt"""
        exe = os.path.join(os.path.dirname(sys.executable), "Scripts", "py-spy.exe")
        if not (self.pid and self.dumps and os.path.isfile(exe)):
            return
        path = os.path.join(self.dumps, "hang-%s.txt" % time.strftime("%H%M%S"))

        def go():
            try:
                r = subprocess.run([exe, "dump", "--pid", str(self.pid)], capture_output=True, text=True,
                                   timeout=20, creationflags=0x08000000)
                open(path, "w", encoding="utf-8").write(r.stdout + r.stderr)
            except Exception as e:
                open(path, "w", encoding="utf-8").write("py-spy failed: %s" % e)
        threading.Thread(target=go, daemon=True).start()

    def run(self):
        while not self.stop.is_set():
            t = time.time()
            ok = answers(self.hwnd, 1000)
            lat = time.time() - t
            hung = bool(u32.IsHungAppWindow(self.hwnd))
            good = ok and lat < 1.0 and not hung
            self.samples.append((t, good, round(lat, 3), hung))
            self.bad_run = 0 if good else self.bad_run + 1
            if self.bad_run in (2, 5, 9):
                self.dump()
            self.stop.wait(max(0.0, self.period - lat))

    def stretches(self, t0=0.0, t1=None):
        """[(start, seconds)] the window did not answer, between t0 and t1"""
        t1 = t1 or time.time()
        out, start = [], None
        for t, ok, lat, _h in list(self.samples):
            if t < t0 or t > t1:
                continue
            if not ok and start is None:
                start = t
            elif ok and start is not None:
                out.append((start, t + lat - start))
                start = None
        if start is not None:
            out.append((start, t1 - start))
        return out

    def worst(self, t0=0.0, t1=None):
        s = self.stretches(t0, t1)
        return round(max((d for _s, d in s), default=0.0), 1)


# ================================================================================== run =====
def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^0-9A-Za-z ]+", " ", s).lower().split())


def slug(s):
    return re.sub(r"[^0-9a-z]+", "_", norm(s))[:30].strip("_") or "x"


class Runner:
    def __init__(self, cfg):
        self.cfg = cfg
        self.exe = cfg["exe"]
        self.world = zip_world(cfg["zip"])
        self.other = zip_world(cfg["other_zip"]) if cfg.get("other_zip") else None
        self.sider = os.path.join(cfg["game"], "SiderAddons")
        self.res = {"exe": self.exe, "zip": cfg["zip"], "world": self.world, "other": self.other,
                    "game": cfg["game"], "apdata": cfg["apdata"], "steps": [], "boxes": [], "fails": [],
                    "notes": [], "started": time.strftime("%Y-%m-%d %H:%M:%S")}
        self.n_shot = 0
        self.main = None
        self.sampler = None
        self.seen = set()
        self.log = open(os.path.join(cfg["root"], "results", "coldstart.log"), "a", encoding="utf-8")

    # ---- bookkeeping
    def note(self, text):
        line = "%s  %s" % (time.strftime("%H:%M:%S"), text)
        say(line)
        self.log.write(line + "\n")
        self.log.flush()

    def fail(self, text):
        self.res["fails"].append(text)
        self.note("FAIL: " + text)

    def shot(self, step, hwnd=None):
        """a picture BEFORE a press: the whole screen; the window alone (PrintWindow) when the
        screen cannot be grabbed (locked)"""
        self.n_shot += 1
        base = os.path.join(self.cfg["shots"], "k_cold_%02d_%s" % (self.n_shot, slug(step)))
        path, k = base + ".png", 2
        while os.path.exists(path):
            path, k = "%s_%d.png" % (base, k), k + 1
        try:
            from PIL import ImageGrab
            ImageGrab.grab(all_screens=True).save(path)
        except Exception:
            try:
                self.printwindow(hwnd or self.main, path)
            except Exception as e:
                self.note("no screenshot %s (%s)" % (path, e))
                return None
        return path

    @staticmethod
    def printwindow(h, path):
        from PIL import Image
        g = ctypes.windll.gdi32
        rc = wintypes.RECT()
        u32.GetWindowRect(h, ctypes.byref(rc))
        W, H = rc.right - rc.left, rc.bottom - rc.top
        hdc = u32.GetWindowDC(h)
        mdc = g.CreateCompatibleDC(hdc)
        bmp = g.CreateCompatibleBitmap(hdc, W, H)
        g.SelectObject(mdc, bmp)
        u32.PrintWindow(h, mdc, 2)

        class BMI(ctypes.Structure):
            _fields_ = [("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_int32), ("biHeight", ctypes.c_int32),
                        ("biPlanes", ctypes.c_uint16), ("biBitCount", ctypes.c_uint16),
                        ("biCompression", ctypes.c_uint32), ("biSizeImage", ctypes.c_uint32),
                        ("biXPelsPerMeter", ctypes.c_int32), ("biYPelsPerMeter", ctypes.c_int32),
                        ("biClrUsed", ctypes.c_uint32), ("biClrImportant", ctypes.c_uint32)]
        bi = BMI(ctypes.sizeof(BMI), W, -H, 1, 32, 0, 0, 0, 0, 0, 0)
        buf = ctypes.create_string_buffer(W * H * 4)
        g.GetDIBits(mdc, bmp, 0, H, buf, ctypes.byref(bi), 0)
        Image.frombuffer("RGBA", (W, H), buf.raw, "raw", "BGRA", 0, 1).convert("RGB").save(path)
        g.DeleteObject(bmp)
        g.DeleteDC(mdc)
        u32.ReleaseDC(h, hdc)

    # ---- UI Automation
    def uia(self, hwnd):
        from pywinauto import Desktop
        return Desktop(backend="uia").window(handle=hwnd).wrapper_object()

    def buttons(self, hwnd, text, enabled=None, exact=False):
        out = []
        w = self.uia(hwnd)
        # the bar's sections are checkable: UIA calls them CheckBox ('My world')
        for c in w.descendants(control_type="Button") + w.descendants(control_type="CheckBox"):
            try:
                t = c.window_text()
                # the bar's sections carry their number: "2. MY WORLD" (app._nav)
                if (t.strip() == text) if exact else (re.sub(r"^\d+ ", "", norm(t)) == norm(text)):
                    if enabled is None or c.is_enabled() == enabled:
                        out.append(c)
            except Exception:
                pass
        return out

    def press(self, c, step, hwnd=None):
        """screenshot, then the button's Invoke on a thread of its own: a button that opens a modal
        window does not return until it closes"""
        self.shot(step, hwnd)
        self.note("press %s" % step)

        def go():
            try:
                import comtypes
                comtypes.CoInitializeEx(0)
            except Exception:
                pass
            for m in ("invoke", "click"):
                try:
                    getattr(c, m)()
                    return
                except Exception:
                    pass
        t = time.time()
        threading.Thread(target=go, daemon=True).start()
        time.sleep(1.0)
        return t

    def wait_button(self, text, timeout, hwnd=None, exact=False, stop_kinds=()):
        """an enabled button `text` in the window; boxes that come up meanwhile are answered"""
        t0 = time.time()
        while time.time() - t0 < timeout:
            ev = self.boxes_once()
            if ev and ev["kind"] in stop_kinds:
                return None
            try:
                b = self.buttons(hwnd or self.main, text, enabled=True, exact=exact)
                if b:
                    return b[0]
            except Exception:
                pass
            time.sleep(2.0)
        return None

    # ---- the boxes (QMessageBox and the like): read, picture, answer
    def dialog_list(self):
        return [w for w in windows(self.exe) if w[0] != self.main and w[2] and w[2] != "FL26ModStudio"]

    def read_box(self, h):
        texts, btns = [], []
        try:
            for c in self.uia(h).descendants():
                ct = c.element_info.control_type
                if ct == "Text" and c.window_text().strip():
                    texts.append(c.window_text().strip())
                elif ct == "Button":
                    btns.append(c)
        except Exception as e:
            texts.append("(not read: %s)" % e)
        return texts, btns

    def boxes_once(self):
        """answer every new box once; returns the last event (or None)"""
        last = None
        live = set()
        for h, _pid, title, cls in self.dialog_list():
            live.add(h)
            if h in self.seen or cls == "#32770" or title.startswith("Add to"):
                continue                      # the file dialog and + Add... are driven by the steps
            self.seen.add(h)
            last = self.answer(h, title)
        self.seen &= live
        return last

    def answer(self, h, title):
        t = time.time()
        texts, btns = self.read_box(h)
        body = " ".join(texts)
        low = body.lower()
        names = {norm(b.window_text()): b for b in btns}
        kind, pick = "unexpected", None
        if title == "Update available":
            kind, pick = "update", "later"
        elif "yes" in names and "no" in names:
            if title == "Switch on" and "in the game" in low:
                kind, pick = "switch_ask", "yes"
            elif "replace it" in low:
                kind, pick = "replace_ask", "yes"
                self.res["notes"].append("asked to replace an older world: the copy was not cold")
            else:
                kind, pick = "question_no", "no"
        elif title == "Master League careers":
            kind = "ml_note"
        elif title == "Ready to play":
            kind = "install_ok"
        elif title == "Almost ready":
            kind = "install_fix"
        elif title == "Switch on" and "is in the game now" in low:
            kind = "switch_ok"
        elif title == "Switch on":
            kind = "switch_fail"
        elif title == "Import your world" and ("stopped" in low or "could not" in low):
            kind = "install_fail"
        elif title == "Unsaved changes":
            kind, pick = "unsaved", "discard"
        if pick is None:
            pick = next((k for k in ("ok", "close", "later", "no", "cancel") if k in names), None)
        ev = {"t": round(t, 2), "title": title, "kind": kind, "text": body[:1500], "pressed": pick, "pressed_t": None}
        self.res["boxes"].append(ev)
        self.note("box \"%s\" (%s): %s" % (title, kind, body[:160].replace("\n", " ")))
        if kind in ("question_no", "unexpected"):
            self.fail("a box nobody expects on a new player's PC: \"%s\": %s" % (title, body[:300]))
        if pick and pick in names:
            ev["pressed_t"] = round(self.press(names[pick], "box_%s_%s" % (slug(title), pick), h), 2)
        else:
            self.shot("box_%s_closed" % slug(title), h)
            u32.PostMessageW(h, WM_CLOSE, 0, 0)
        return ev

    def wait_event(self, kinds, timeout):
        t0 = time.time()
        while time.time() - t0 < timeout:
            ev = self.boxes_once()
            if ev and ev["kind"] in kinds:
                return ev
            if self.proc.poll() is not None:
                self.fail("Mod Studio closed (exit code %s)" % self.proc.returncode)
                return None
            time.sleep(0.5)
        return None

    # ---- the steps
    def step(self, name, t0, t1, **kw):
        d = {"step": name, "secs": round(t1 - t0, 1), "worst_not_answering_s": self.sampler.worst(t0, t1)
             if self.sampler else None}
        d.update(kw)
        self.res["steps"].append(d)
        self.note("step %s: %.1f s, longest not answering %.1f s %s" % (
            name, d["secs"], d["worst_not_answering_s"] or 0, json.dumps(kw, ensure_ascii=False) if kw else ""))
        return d

    def launch(self):
        env = {k: v for k, v in os.environ.items() if k.upper() not in SKIP_ENV}
        env.update(APPDATA=self.cfg["apdata"], FL26_SAVE_ROOT=self.cfg["save_root"], PYTHONIOENCODING="utf-8")
        if self.cfg.get("temp"):
            os.makedirs(self.cfg["temp"], exist_ok=True)
            env.update(TEMP=self.cfg["temp"], TMP=self.cfg["temp"])
        t0 = time.time()
        self.proc = subprocess.Popen([self.exe], cwd=os.path.dirname(self.exe), env=env)
        while time.time() - t0 < 180:
            m = [w for w in windows(self.exe) if w[2] == MAIN_TITLE]
            if m:
                self.main = m[0][0]
                break
            if self.proc.poll() is not None:
                die("Mod Studio closed at its start (exit code %s)" % self.proc.returncode, 1)
            time.sleep(0.5)
        else:
            die("no Mod Studio window after 3 minutes", 1)
        self.sampler = Sampler(self.main, pid=self.proc.pid, dumps=os.path.dirname(self.cfg["result"]))
        self.sampler.start()
        self.step("start (to the window)", t0, time.time())
        return t0

    def first_start(self):
        """the first start unpacks the game's tables by itself (auto_tables); done when its
        fl26-unpacked.json is there"""
        t0 = time.time()
        mark = os.path.join(self.cfg["apdata"], "FL26ModStudio", "tables", "fl26-unpacked.json")
        while time.time() - t0 < 900:
            self.boxes_once()
            if os.path.isfile(mark):
                time.sleep(3)                  # done() loads the tables on the GUI thread
                return self.step("first start: the game's tables unpacked", t0, time.time())
            time.sleep(1.0)
        self.fail("the first start did not unpack the game's tables in 15 minutes (%s)" % mark)

    def my_world(self):
        b = self.buttons(self.main, "My world")
        if b:
            self.press(b[0], "nav_my_world")
            time.sleep(1.5)
        else:
            self.note("no My world button (the page may be open already)")
            try:
                seen = sorted({"%s:%r" % (c.element_info.control_type, c.window_text())
                               for c in self.uia(self.main).descendants()
                               if "world" in norm(c.window_text()) or "add" in norm(c.window_text())})
                self.note("  names with world/add: %s" % "; ".join(seen[:40]))
            except Exception as e:
                self.note("  names not read: %s" % e)

    def file_dialog(self, path, timeout=30):
        t0 = time.time()
        while time.time() - t0 < timeout:
            d = [w for w in windows(self.exe) if w[3] == "#32770"]
            if d:
                h = d[0][0]
                time.sleep(1.0)
                edit = None
                for c in children(h):
                    if class_of(c) == "Edit":
                        p = u32.GetParent(c)
                        if class_of(p) == "ComboBox" and class_of(u32.GetParent(p)) == "ComboBoxEx32":
                            edit = c
                            break
                if edit is None:
                    edit = next((c for c in children(h) if class_of(c) == "Edit"), None)
                if edit is None:
                    self.fail("the file dialog has no file name box")
                    return False
                # the name goes in through UI Automation: WM_SETTEXT left the box empty (run 5, 17.10.)
                set_ok = False
                try:
                    from pywinauto import Desktop
                    spec = Desktop(backend="uia").window(handle=h)
                    box = spec.child_window(auto_id="1148", control_type="Edit").wrapper_object()
                    box.set_edit_text(path)
                    set_ok = (box.window_text() or "").strip() == path
                except Exception as e:
                    self.note("file dialog: UIA name box not set (%s), WM_SETTEXT instead" % e)
                if not set_ok:
                    u32.SendMessageW(edit, WM_SETTEXT, 0, ctypes.cast(ctypes.c_wchar_p(path), ctypes.c_void_p).value)
                if edit_text(edit).strip() != path:
                    # neither stuck (runs 5-8, 17.10.): type it, as a player would
                    try:
                        from pywinauto import Desktop, keyboard
                        u32.SetForegroundWindow(h)
                        Desktop(backend="uia").window(handle=h).child_window(
                            auto_id="1148", control_type="Edit").wrapper_object().set_focus()
                        keyboard.send_keys("^a{BACKSPACE}", pause=0.05)
                        keyboard.send_keys(re.sub(r"([+^%~(){}\[\]])", r"{\1}", path), with_spaces=True, pause=0.01)
                        time.sleep(0.5)
                    except Exception as e:
                        self.note("file dialog: typing failed (%s)" % e)
                got = edit_text(edit).strip()
                self.shot("file_dialog_open", h)
                self.note("file dialog: %s (the name box says %r)" % (path, got))
                try:
                    from pywinauto import Desktop
                    Desktop(backend="uia").window(handle=h).child_window(auto_id="1", control_type="Button").wrapper_object().invoke()
                except Exception:
                    u32.PostMessageW(h, WM_COMMAND, 1, 0)        # IDOK: Open
                t1 = time.time()
                while time.time() - t1 < 15 and u32.IsWindow(h) and u32.IsWindowVisible(h):
                    time.sleep(0.3)
                if u32.IsWindow(h) and u32.IsWindowVisible(h):
                    self.shot("file_dialog_stuck", h)
                    u32.PostMessageW(h, WM_COMMAND, 2, 0)        # IDCANCEL, so the window can close
                    self.fail("the file dialog did not take %s (name box %r)" % (path, got))
                    return False
                return True
            time.sleep(0.5)
        self.fail("no file dialog after Choose a file...")
        return False

    def install(self, zp, world, modpack):
        """My world > + Add... > Choose a file... > the zip > Add > Install the world, timed"""
        name = "install %s" % world
        self.my_world()
        add = self.buttons(self.main, "+ Add...", exact=True)
        if not add:
            return self.fail("%s: no + Add... button on My world" % name)
        self.press(add[0], "add_" + world)
        dlg, t0 = None, time.time()
        while time.time() - t0 < 20 and not dlg:
            dlg = next((w[0] for w in windows(self.exe) if w[2].startswith("Add to")), None)
            time.sleep(0.5)
        if not dlg:
            return self.fail("%s: + Add... opened no window" % name)
        ch = self.buttons(dlg, "Choose a file...")
        if not ch:
            return self.fail("%s: no Choose a file... in + Add..." % name)
        self.press(ch[0], "choose_file_" + world, dlg)
        if not self.file_dialog(zp):
            return None
        ok = self.wait_button("Add", 30, hwnd=dlg)
        if not ok:
            return self.fail("%s: Add stayed off for %s" % (name, zp))
        t_look = self.press(ok, "add_ok_" + world, dlg)
        go = self.wait_button("Install the world", 3600, stop_kinds=("install_fail",))
        if not go:
            return self.fail("%s: Install the world never came on (the zip looked into for an hour?)" % name)
        self.step("look inside %s" % os.path.basename(zp), t_look, time.time())
        t0 = self.press(go, "install_the_world_" + world)
        ev = self.wait_event(("install_ok", "install_fix", "install_fail", "switch_fail"), 7200)
        t_end = time.time()
        if ev is None:
            return self.fail("%s: no end after 2 hours" % name)
        boxes = [b for b in self.res["boxes"] if b["t"] >= t0]
        t_sw = self.switch_started("Import your world: switch on " + world)
        first_end = next((b["t"] for b in boxes if b["kind"] in ("ml_note", "install_ok", "install_fix",
                                                                    "install_fail", "switch_fail")), ev["t"])
        sw = round(first_end - t_sw, 1) if t_sw else None
        drawn = self.kits_drawn(world, t_sw or t0)
        d = self.step(name, t0, t_end, end=ev["kind"], switch_on_s=sw, kits_drawn=drawn,
                      worst_in_switch_s=self.sampler.worst(t_sw, first_end) if t_sw else None)
        if ev["kind"] not in ("install_ok", "install_fix"):
            self.fail("%s did not complete: %s" % (name, ev["text"][:300]))
        if ev["kind"] == "install_fix":
            self.res["notes"].append("%s: Almost ready -- %s" % (world, ev["text"][:600]))
        if modpack:
            if sw is None:
                self.fail("%s: the switch-on's start was not found in the restore points" % name)
            elif sw > LIMIT_SWITCH:
                self.fail("%s: the first switch took %.0f s (> %.0f s)" % (name, sw, LIMIT_SWITCH))
        return d

    def switch_started(self, reason):
        """when the switch began: the restore point of sider.ini it takes first (backups.json)"""
        try:
            rows = json.load(open(os.path.join(self.sider, "ModStudio", "backups.json"), encoding="utf-8"))
        except (OSError, ValueError):
            return None
        hit = [r for r in rows if r.get("reason") == reason]
        if not hit:
            return None
        return time.mktime(time.strptime(hit[-1]["time"], "%Y%m%d-%H%M%S"))

    def kits_drawn(self, world, since):
        """made kits whose kitmaker.txt was written since `since` -- drawn on this PC (B104)"""
        n = 0
        for d in (os.path.join(self.sider, "content", "kit-server", world),
                  os.path.join(self.sider, "content", "kits", world)):
            for dp, _dn, fn in os.walk(d):
                if "kitmaker.txt" in fn and os.path.getmtime(os.path.join(dp, "kitmaker.txt")) >= since - 1:
                    n += 1
        return n

    def activate(self, world, modpack):
        name = "activate %s" % world
        self.my_world()
        btns = self.buttons(self.main, "Activate", enabled=True)
        if not btns:
            return self.fail("%s: no Activate button on" % name)
        if len(btns) > 1:                       # the card of `world`: its name label above the button
            labels = [c for c in self.uia(self.main).descendants(control_type="Text")
                      if norm(c.window_text()).startswith(norm(world)[:8])]
            pick = None
            for b in btns:
                r = b.rectangle()
                if any(l.rectangle().left >= r.left - 330 and l.rectangle().right <= r.right + 40 for l in labels):
                    pick = b
            btns = [pick or btns[0]]
        self.press(btns[0], "activate_" + world)
        ask = self.wait_event(("switch_ask", "switch_fail"), 60)
        if not ask or ask["kind"] != "switch_ask":
            return self.fail("%s: no \"Put ... in the game?\" question" % name)
        t0 = ask["pressed_t"] or ask["t"]       # Yes pressed
        ev = self.wait_event(("switch_ok", "switch_fail"), 3600)
        t_end = time.time()
        if ev is None:
            return self.fail("%s: no end after an hour" % name)
        first_end = next((b["t"] for b in self.res["boxes"] if b["t"] > t0 and b["kind"] in
                          ("ml_note", "switch_ok", "switch_fail")), ev["t"])
        t_sw = self.switch_started("Your world: switch on " + world)
        secs = round(first_end - t0, 1)              # from Yes to the first box after the switch
        d = self.step(name, t0, t_end, end=ev["kind"], switch_s=secs, kits_drawn=self.kits_drawn(world, t0),
                      switch_from_restore_point_s=round(first_end - t_sw, 1) if t_sw and t_sw >= t0 - 2 else None)
        if ev["kind"] != "switch_ok":
            self.fail("%s: %s" % (name, ev["text"][:300]))
        ini = open(os.path.join(self.sider, "sider.ini"), encoding="utf-8", errors="replace").read()
        if not re.search(r'(?im)^\s*cpk\.root\s*=\s*"?\.\\livecpk\\%s"?\s*$' % re.escape(world), ini):
            self.fail("%s: sider.ini has no switched-on cpk.root for it" % name)
        if modpack and secs > LIMIT_SWITCH:
            self.fail("%s: the switch took %.0f s (> %.0f s)" % (name, secs, LIMIT_SWITCH))
        return d

    def close(self):
        if self.cfg.get("keep_open") or self.proc.poll() is not None:
            return
        self.shot("close")
        u32.PostMessageW(self.main, WM_CLOSE, 0, 0)
        t0 = time.time()
        while time.time() - t0 < 30 and self.proc.poll() is None:
            self.boxes_once()
            time.sleep(0.5)
        if self.proc.poll() is None:
            # a modal window (a file dialog left open by a failed step) eats WM_CLOSE; the cold copy
            # is the test's own, and a live one holds appdata so the next --reset fails (run 6, 17.10.)
            self.res["notes"].append("Mod Studio did not close in 30 s: killed (pid %d)" % self.proc.pid)
            self.proc.kill()

    def cold_check(self):
        """what makes this run cold, as found before the start"""
        ms = os.path.join(self.cfg["apdata"], "FL26ModStudio")
        lib = os.path.join(self.sider, "content", "kit-server")
        c = {"appdata_only_settings": sorted(os.listdir(ms)) == ["settings.json"] if os.path.isdir(ms) else False,
             "no_world_in_livecpk": not any(n.lower().startswith("_fl26") for n in os.listdir(os.path.join(self.sider, "livecpk"))),
             "no_made_kits": not any(n.lower().startswith("_fl26") for n in os.listdir(lib)) if os.path.isdir(lib) else True,
             "no_modstudio_folder": not os.path.isdir(os.path.join(self.sider, "ModStudio")),
             "no_save_aside": not any(n.startswith("save_") for n in os.listdir(self.cfg["save_root"])),
             "game_outside_c_with_space": " " in self.cfg["game"] and not norm_path(self.cfg["game"]).startswith("c:")}
        self.res["cold"] = c
        bad = [k for k, v in c.items() if not v]
        if bad and not self.cfg.get("allow_warm"):
            die("not cold: %s -- prepare --reset first" % ", ".join(bad), 1)

    def run(self):
        if session_id() == 0:
            die("run needs the interactive session (session 1); this is session 0: use mode all (it goes "
                "through the %s task) or start it from a terminal on the desktop" % self.cfg.get("task", TASK_DEFAULT))
        names = running_names()
        if '"fl_2026.exe"' in names or '"pes2021.exe"' in names:
            die("the game is running: Mod Studio would refuse the save switch -- close it first", 1)
        self.cold_check()
        t_all = self.launch()
        try:
            self.first_start()
            zips = ([(self.cfg["other_zip"], self.other, False)] if self.other else []) + [(self.cfg["zip"], self.world, True)]
            for zp, w, mp in zips:
                if self.install(zp, w, mp) is None and self.res["fails"]:
                    break
            else:
                if self.other:
                    if self.activate(self.other, False) is not None:
                        self.activate(self.world, True)
                else:
                    self.res["notes"].append("no --other-zip: the Modpack's first switch is Install's switch-on only; "
                                             "My world's Activate was not measured (no second world to go back from)")
        finally:
            t_end = time.time()
            try:
                self.close()
            except Exception as e:
                self.res["notes"].append("close: %s" % e)
            if self.sampler:
                self.sampler.stop.set()
                worst = self.sampler.worst(t_all, t_end)
                self.res["worst_not_answering_s"] = worst
                self.res["not_answering"] = [(time.strftime("%H:%M:%S", time.localtime(s)), round(d, 1))
                                             for s, d in self.sampler.stretches(t_all, t_end) if d >= 1.0]
                self.res["samples"] = len(self.sampler.samples)
                if worst > LIMIT_HANG:
                    self.fail("the window did not answer for %.1f s (> %.0f s)" % (worst, LIMIT_HANG))
            self.res["secs"] = round(t_end - t_all, 1)
            self.res["verdict"] = "FAIL" if self.res["fails"] else "PASS"
            json.dump(self.res, open(self.cfg["result"], "w", encoding="utf-8"), indent=1, ensure_ascii=False)
            report(self.res)
        return 0 if self.res["verdict"] == "PASS" else 1


def report(res):
    say("")
    say("== coldstart: %s ==  %s  (%s, %s s)" % (res.get("verdict"), res.get("world"), os.path.basename(res.get("zip", "")),
                                             res.get("secs")))
    for s in res.get("steps", []):
        extra = {k: v for k, v in s.items() if k not in ("step", "secs", "worst_not_answering_s")}
        say("  %-44s %7.1f s   not answering max %5.1f s   %s" % (s["step"][:44], s["secs"],
                                                               s.get("worst_not_answering_s") or 0,
                                                               json.dumps(extra, ensure_ascii=False) if extra else ""))
    say("  longest stretch not answering: %s s (limit %.0f); stretches >= 1 s: %s" % (
        res.get("worst_not_answering_s"), LIMIT_HANG, res.get("not_answering")))
    for n in res.get("notes", []):
        say("  NOTE " + n)
    for f in res.get("fails", []):
        say("  FAIL " + f)
    say("  %s" % res.get("verdict"))


# ================================================================== session 1 by the task ====
def task_info(task):
    """(pythonw, folder of the driver) of the FL26Uia task, which runs its uiadrv.py in session 1"""
    r = subprocess.run(["schtasks", "/query", "/tn", task, "/xml"], capture_output=True)
    raw = r.stdout
    text = raw.decode("utf-16", "replace") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") or b"\x00<" in raw[:8] \
        else raw.decode("utf-8", "replace")
    cmd = re.search(r"<Command>\"?([^<\"]+)\"?</Command>", text)
    arg = re.search(r"<Arguments>\"?([^<\"]+uiadrv\.py)\"?</Arguments>", text)
    if not (cmd and arg):
        return None, None
    return cmd.group(1), os.path.dirname(arg.group(1))


def hop(cfg, timeout_min):
    task = cfg.get("task", TASK_DEFAULT)
    pyw, drv = task_info(task)
    if not drv or not os.path.isfile(os.path.join(drv, "uiadrv.py")):
        die("this is session 0 and there is no %s task with its uiadrv.py: run\n    python %s run --config \"%s\"\n"
            "from a terminal on the desktop" % (task, os.path.abspath(__file__), cfg["config"]))
    if not os.path.basename(pyw).lower().startswith("pythonw"):
        pyw = os.path.join(os.path.dirname(pyw), "pythonw.exe")
    bat = os.path.join(tempfile.gettempdir(), "fl26-coldstart-run.bat")    # no space in its path
    with open(bat, "w", encoding="mbcs" if os.name == "nt" else "utf-8") as f:
        f.write('@echo off\r\nset PYTHONIOENCODING=utf-8\r\nstart "" /min "%s" "%s" run --config "%s"\r\n'
                % (pyw, os.path.abspath(__file__), cfg["config"]))
    if os.path.exists(cfg["result"]):
        os.remove(cfg["result"])
    t = time.time()
    while time.time() - t < 60:                      # one step at a time: wait for one before
        q = subprocess.run(["schtasks", "/query", "/tn", task, "/fo", "LIST"], capture_output=True, text=True).stdout
        if "Running" not in q:
            break
        time.sleep(1)
    out = os.path.join(drv, "out.json")
    if os.path.exists(out):
        os.remove(out)
    json.dump({"op": "launch", "exe": bat}, open(os.path.join(drv, "cmd.json"), "w", encoding="utf-8"))
    subprocess.run(["schtasks", "/run", "/tn", task], check=True, capture_output=True)
    say("started in session 1 through %s (%s); log %s" % (task, bat, os.path.join(cfg["root"], "results", "coldstart.log")))
    t = time.time()
    while time.time() - t < timeout_min * 60:
        if os.path.exists(cfg["result"]):
            time.sleep(1)
            res = json.load(open(cfg["result"], encoding="utf-8"))
            report(res)
            return 0 if res.get("verdict") == "PASS" else 1
        time.sleep(5)
    die("no result after %d minutes (%s)" % (timeout_min, cfg["result"]), 1)


# ================================================================================= main =====
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("mode", nargs="?", default="all", choices=("all", "prepare", "run"))
    ap.add_argument("--zip", help="the world zip (the Modpack)")
    ap.add_argument("--exe", help="FL26ModStudio.exe of the release zip, unpacked")
    ap.add_argument("--game", default=GAME_DEFAULT, help="the cold game copy (a path with a space, not C:, not E:)")
    ap.add_argument("--apdata", help="the empty APPDATA (default: <root>\\appdata)")
    ap.add_argument("--shots", help="screenshots k_cold_*.png (default: <root>\\shots)")
    ap.add_argument("--from", dest="src", default=SRC_DEFAULT, help="the game read from (only read)")
    ap.add_argument("--other-zip", help="a second world zip: installed first, Activated, then the Modpack Activated again")
    ap.add_argument("--make-other", metavar="WORLD", help="export WORLD from --from as the second world zip")
    ap.add_argument("--sider-ini", help="sider.ini as before Mod Studio (default: the oldest clean sider_ini_backups copy)")
    ap.add_argument("--saves-from", help="a save folder to copy as the player's (default: two small files)")
    ap.add_argument("--temp-in-root", action="store_true", help="TEMP/TMP of Mod Studio inside the cold root (default: the real %%TEMP%%)")
    ap.add_argument("--reset", action="store_true", help="empty the cold root first (only one this script made)")
    ap.add_argument("--dry-run", action="store_true", help="prepare: only say what would be copied")
    ap.add_argument("--config", help="run: the config prepare wrote")
    ap.add_argument("--task", default=TASK_DEFAULT, help="the scheduled task that runs in session 1")
    ap.add_argument("--timeout-min", type=int, default=240)
    ap.add_argument("--keep-open", action="store_true")
    ap.add_argument("--allow-warm", action="store_true", help="run even when the copy is not cold (a second look)")
    a = ap.parse_args()
    if a.mode == "run":
        a.config = a.config or os.path.join(os.path.dirname(os.path.abspath(a.game)), "results", "coldstart-config.json")
        if not os.path.isfile(a.config):
            die("no %s: prepare first" % a.config)
        cfg = json.load(open(a.config, encoding="utf-8"))
        cfg.update({k: v for k, v in (("keep_open", a.keep_open), ("allow_warm", a.allow_warm)) if v})
        if sys.stdout is None:
            # pythonw (the FL26Uia hop): no console, so a crash would vanish without a trace
            sys.stdout = sys.stderr = open(os.path.join(os.path.dirname(a.config), "coldstart-run.out"), "a",
                                           encoding="utf-8", errors="replace", buffering=1)
        else:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        return Runner(cfg).run()
    if not a.zip or not a.exe:
        ap.error("--zip and --exe are needed (or run --config <config.json>)")
    if not os.path.isfile(a.exe):
        die("no exe %s" % a.exe)
    if not os.path.isdir(os.path.join(os.path.dirname(a.exe), "pack")):
        die("%s has no pack folder next to it: the unpacked release zip, please" % a.exe)
    game = os.path.abspath(a.game)
    root = os.path.dirname(game)
    cfg = {"src": os.path.abspath(a.src), "root": root, "game": game, "zip": os.path.abspath(a.zip),
           "exe": os.path.abspath(a.exe),
           "apdata": os.path.abspath(a.apdata or os.path.join(root, "appdata")),
           "shots": os.path.abspath(a.shots or os.path.join(root, "shots")),
           "save_root": os.path.join(root, "KONAMI", "2026"),
           "config": os.path.join(root, "results", "coldstart-config.json"),
           "result": os.path.join(root, "results", "coldstart-result.json"),
           "other_zip": os.path.abspath(a.other_zip) if a.other_zip else None,
           "make_other": a.make_other, "sider_ini": a.sider_ini, "saves_from": a.saves_from,
           "temp": os.path.join(root, "temp") if a.temp_in_root else None, "task": a.task,
           "keep_open": a.keep_open, "allow_warm": a.allow_warm}
    zip_world(cfg["zip"])
    if cfg["other_zip"] and zip_world(cfg["other_zip"]) == zip_world(cfg["zip"]):
        die("--other-zip carries the same world as --zip")
    prepare(cfg, dry=a.dry_run, reset=a.reset)
    if a.mode == "prepare" or a.dry_run:
        return 0
    if session_id() != 0:
        return Runner(cfg).run()
    return hop(cfg, a.timeout_min)


if __name__ == "__main__":
    sys.coinit_flags = 0              # COM multithreaded: a press runs on a thread of its own
    raise SystemExit(main())
