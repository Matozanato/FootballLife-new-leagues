"""the game install: where things are, is it running, start it.

A Game is the folder that holds FL_2026.exe (FL26) or FL_2027.exe (FL27, the same PES 2021 exe
with SmokePatch's changes; 31.10.).  Everything else is found from there:
the Sider folder (sider.exe, sider.ini, modules, content, livecpk; SiderAddons or any folder
that holds a sider.ini, see siderdir) and the save folder.
"""
import os, subprocess, time

import siderdir

EXE_NAMES = ("FL_2026.exe", "FL_2027.exe", "PES2021.exe")
LAUNCHERS = ("FL 2026 start.exe", "FL 2027 start.exe")
FL27_EXE = "FL_2027.exe"


def documents():
    r"""the player's Documents folder as Windows has it -- the folder the game saves under. Not
    ~\Documents: a Documents folder moved elsewhere (OneDrive, another drive) is not there (B296)"""
    if os.name == "nt":
        try:
            import ctypes
            buf = ctypes.create_unicode_buffer(1024)
            if ctypes.windll.shell32.SHGetFolderPathW(0, 5, 0, 0, buf) == 0 and buf.value:  # CSIDL_PERSONAL
                return buf.value
        except (OSError, AttributeError):
            pass
    return os.path.join(os.path.expanduser("~"), "Documents")


SAVE_DIR = os.path.join(documents(), "KONAMI", "eFootball PES 2021 SEASON UPDATE")
SAVE_ID = "2026"
# FL27 saves under Documents\SPGAME\Football Life\2027\save (its exe's paths say so: KONAMI\
# eFootball PES 2021 SEASON UPDATE became SPGAME\Football Life; sys.ini SteamID=2027)
SAVE_DIR_FL27 = os.path.join(documents(), "SPGAME", "Football Life")
SAVE_ID_FL27 = "2027"


def _game_folder(folder):
    if folder is None:
        import flpaths
        folder = flpaths.GAME_DIR
    return folder


def is_fl27(folder=None):
    """the game folder holds FL27's exe (and not FL26's)"""
    folder = _game_folder(folder)
    return bool(folder) and os.path.exists(os.path.join(folder, FL27_EXE)) \
        and not os.path.exists(os.path.join(folder, "FL_2026.exe"))


def save_dir(folder=None):
    """the folder the game's numbered save folders are in: FL26's KONAMI one, or FL27's SPGAME one"""
    return SAVE_DIR_FL27 if is_fl27(folder) else SAVE_DIR


def save_id(folder=None):
    """the save folder's name the game asks for: SteamID of sys.ini next to FL_2026.exe (the Steam
    stand-in reads it; 2026 in FL26, 2027 in FL27). `folder` the game folder, else the one Mod Studio uses"""
    folder = _game_folder(folder)
    try:
        with open(os.path.join(folder, "sys.ini"), encoding="utf-8", errors="replace") as f:
            sect = ""
            for line in f:
                line = line.strip()
                if line.startswith("["):
                    sect = line.strip("[]").strip().lower()
                elif sect == "settings" and "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip().lower() == "steamid" and v.strip().isdigit():
                        return str(int(v.strip()))
    except OSError:
        pass
    return SAVE_ID_FL27 if is_fl27(folder) else SAVE_ID


def _system_time(d):
    try:
        return os.path.getmtime(os.path.join(d, "save", "SYSTEM00000000"))
    except OSError:
        return 0


def save_root(folder=None):
    r"""the folder that holds the game's save folder: SAVE_DIR\<id>. <id> is sys.ini's when the
    game saves there; else the numbered folder whose SYSTEM00000000 was written last -- the game
    saves under 0 when the Steam stand-in does not read sys.ini (B296). The same rule as the
    modules' (tools/native/fl26savedir.h)"""
    base = save_dir(folder)
    want = os.path.join(base, save_id(folder))
    if _system_time(want):
        return want
    best, newest = want, 0
    try:
        names = os.listdir(base)
    except OSError:
        names = []
    for n in names:
        if n.isdigit():
            t = _system_time(os.path.join(base, n))
            if t > newest:
                best, newest = os.path.join(base, n), t
    return best


# the game's Edit save: written before a Build, it hides the Build's squads and names in Exhibition
# and Edit mode (Risto 04.10.: two signings in a career, not in an exhibition)
def edit_file():
    """the Edit save in the save folder in use: FL26_SAVE_ROOT's when it is set (saves.root()),
    so a test with a save folder of its own never sees the PC's real Edit save (coldstart 26.10.:
    the player's EDIT00000000 showed "Move the Edit save aside" on a new player's PC)"""
    r = os.environ.get("FL26_SAVE_ROOT") or save_root()
    return os.path.join(r, "save", "EDIT00000000")


def old_edit(since):
    """the Edit save's path when there is one older than `since` (a time.time()), else None"""
    f = edit_file()
    try:
        return f if os.path.getmtime(f) < since else None
    except OSError:
        return None


def edit_aside(tag):
    """rename the Edit save to EDIT00000000.before-<tag>-<date>, kept next to it; returns the new
    name. Nothing is deleted: renaming it back brings the old Edit data back"""
    import time
    f = edit_file()
    new = "%s.before-%s-%s" % (f, tag, time.strftime("%Y%m%d-%H%M"))
    os.rename(f, new)
    return os.path.basename(new)


class Game:
    def __init__(self, folder):
        self.folder = os.path.normpath(folder) if folder else ""

    # ---- where things are ----
    @property
    def exe(self):
        for n in EXE_NAMES:
            p = os.path.join(self.folder, n)
            if os.path.exists(p):
                return p
        return None

    @property
    def sider_dir(self):
        # 0.2.4: kept for two seconds -- every look lists the game folder and the one below, and
        # a page asks many times over; while Build ran in its thread each look waited for it,
        # and the window stopped answering (exe test 15.10., Build tab -> League packages -> back)
        key = (self.folder, siderdir.PREFERRED)
        now = time.monotonic()
        got = getattr(self, "_sider", None)
        if got is None or got[0] != key or now - got[1] > 2:
            got = self._sider = (key, now, siderdir.find(self.folder))
        return got[2]

    @property
    def ini_path(self):
        return os.path.join(self.sider_dir, "sider.ini")

    @property
    def modules_dir(self):
        return os.path.join(self.sider_dir, "modules")

    @property
    def content_dir(self):
        return os.path.join(self.sider_dir, "content")

    @property
    def livecpk_dir(self):
        return os.path.join(self.sider_dir, "livecpk")

    @property
    def log_path(self):
        return os.path.join(self.sider_dir, "sider.log")

    @property
    def launcher(self):
        for n in LAUNCHERS:
            p = os.path.join(self.folder, n)
            if os.path.exists(p):
                return p
        return None

    @property
    def download_dir(self):
        return os.path.join(self.folder, "download")

    def ok(self):
        return bool(self.folder) and self.exe is not None

    def problems(self):
        """what is missing, as short sentences (empty = fine)"""
        out = []
        if not self.folder:
            return ["the game folder is not set"]
        if not os.path.isdir(self.folder):
            return ["the game folder is not there any more"]
        if not self.exe:
            out.append("no FL_2026.exe (or FL_2027.exe) in the game folder")
        if not os.path.isdir(self.sider_dir):
            out.append("no Sider folder with a sider.ini (Sider is not installed)")
        elif not os.path.exists(self.ini_path):
            out.append("no sider.ini in SiderAddons")
        return out

    def version(self):
        """a short label from the newest data_s*.cpk in download (FL26 updates add them)"""
        try:
            from leaguebuilder import cpk_key
            cpks = sorted((f for f in os.listdir(self.download_dir) if f.lower().startswith("data_s")), key=cpk_key)
            return cpks[-1][:-4] if cpks else ""
        except OSError:
            return ""

    # ---- running ----
    @staticmethod
    def running():
        """(game running, sider running)"""
        names = _process_names()
        if names is not None:
            return any(n.lower() in names for n in EXE_NAMES), "sider.exe" in names
        try:
            out = subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True, text=True,
                                 creationflags=0x08000000).stdout.lower()
        except (OSError, ValueError):       # B210: tasklist and creationflags are Windows only (Mac, Crossover)
            return False, False
        return any(('"%s"' % n.lower()) in out for n in EXE_NAMES), '"sider.exe"' in out

    def start(self, direct=False):
        """start the game the way its shortcut does (the launcher starts sider and the game);
        direct=True starts sider.exe and the game exe instead"""
        if not direct and self.launcher:
            os.startfile(self.launcher)
            return "launcher"
        sider = os.path.join(self.sider_dir, "sider.exe")
        if os.path.exists(sider):
            os.startfile(sider)
        os.startfile(self.exe)
        return "direct"


def guess_folders():
    """likely game folders: the uninstall entries in the registry, then common places"""
    found = []
    try:
        import winreg
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for root in (r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                         r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"):
                try:
                    k = winreg.OpenKey(hive, root)
                except OSError:
                    continue
                for i in range(winreg.QueryInfoKey(k)[0]):
                    try:
                        sub = winreg.OpenKey(k, winreg.EnumKey(k, i))
                        name = str(winreg.QueryValueEx(sub, "DisplayName")[0])
                        if "football life" in name.lower() or "fl26" in name.lower() or "fl27" in name.lower() \
                                or "pes 2021" in name.lower():
                            loc = str(winreg.QueryValueEx(sub, "InstallLocation")[0])
                            if loc and Game(loc).exe:
                                found.append(os.path.normpath(loc))
                    except OSError:
                        pass
    except ImportError:
        pass
    for drive in "CDEFG":
        for rel in ("Football Life 2026", "FL26", "Games\\Football Life 2026",
                    "Program Files (x86)\\Football Life 2026",
                    "Football Life 2027", "FL27", "FL27\\game", "Games\\Football Life 2027"):
            p = "%s:\\%s" % (drive, rel)
            if Game(p).exe:
                found.append(p)
    for drive in "CDEFGHIJ":                     # any folder right under a drive root
        top = "%s:\\" % drive
        try:
            names = os.listdir(top)
        except OSError:
            continue
        for n in names:
            p = os.path.join(top, n)
            if n.lower() not in ("windows", "$recycle.bin", "system volume information") and Game(p).exe:
                found.append(p)
    out = []
    for f in found:
        if f.lower() not in [x.lower() for x in out]:
            out.append(f)
    return out


def _process_names():
    """the lower-case names of the running programs, from Windows' process list (a few ms) --
    0.2.4: tasklist took 0.3 s, and the window asks every 4 s: the window stopped for it each
    time (exe test 15.10., "not fluid"); None where this does not work"""
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class Entry(ctypes.Structure):
            _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                        ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
                        ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                        ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
                        ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_wchar * 260)]
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        k.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        k.Process32FirstW.argtypes = k.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
        k.CloseHandle.argtypes = [wintypes.HANDLE]
        snap = k.CreateToolhelp32Snapshot(2, 0)                 # TH32CS_SNAPPROCESS
        if not snap or snap == wintypes.HANDLE(-1).value:
            return None
        try:
            e = Entry()
            e.dwSize = ctypes.sizeof(Entry)
            names = set()
            ok = k.Process32FirstW(snap, ctypes.byref(e))
            while ok:
                names.add(e.szExeFile.lower())
                ok = k.Process32NextW(snap, ctypes.byref(e))
            return names
        finally:
            k.CloseHandle(snap)
    except Exception:
        return None
