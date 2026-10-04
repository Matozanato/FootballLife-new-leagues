"""the game install: where things are, is it running, start it.

A Game is the folder that holds FL_2026.exe.  Everything else is found from there:
the Sider folder (sider.exe, sider.ini, modules, content, livecpk; SiderAddons or any folder
that holds a sider.ini, see siderdir) and the save folder.
"""
import os, subprocess

import siderdir

EXE_NAMES = ("FL_2026.exe", "PES2021.exe")
LAUNCHERS = ("FL 2026 start.exe",)
SAVE_DIR = os.path.join(os.path.expanduser("~"), "Documents", "KONAMI",
                        "eFootball PES 2021 SEASON UPDATE")


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
        return siderdir.find(self.folder)

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
            out.append("no FL_2026.exe in the game folder")
        if not os.path.isdir(self.sider_dir):
            out.append("no Sider folder with a sider.ini (Sider is not installed)")
        elif not os.path.exists(self.ini_path):
            out.append("no sider.ini in SiderAddons")
        return out

    def version(self):
        """a short label from the newest data_s*.cpk in download (FL26 updates add them)"""
        try:
            cpks = sorted(f for f in os.listdir(self.download_dir) if f.lower().startswith("data_s"))
            return cpks[-1][:-4] if cpks else ""
        except OSError:
            return ""

    # ---- running ----
    @staticmethod
    def running():
        """(game running, sider running)"""
        try:
            out = subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True, text=True,
                                 creationflags=0x08000000).stdout.lower()
        except OSError:
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
                        if "football life" in name.lower() or "fl26" in name.lower() or "pes 2021" in name.lower():
                            loc = str(winreg.QueryValueEx(sub, "InstallLocation")[0])
                            if loc and Game(loc).exe:
                                found.append(os.path.normpath(loc))
                    except OSError:
                        pass
    except ImportError:
        pass
    for drive in "CDEFG":
        for rel in ("Football Life 2026", "FL26", "Games\\Football Life 2026",
                    "Program Files (x86)\\Football Life 2026"):
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
