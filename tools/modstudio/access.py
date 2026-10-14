"""Can Mod Studio write in the game folder? (B14, Konkubent 13.10.)

A game installed under C:\\Program Files (x86) can only be changed by a program run as
administrator: Install mods stopped on livecpk\\_FL26Modpack with a raw PermissionError
[WinError 5] and said nothing about what to do. Mod Studio now tries a small file in the
folders it writes in when the game folder is chosen and before it installs, builds or switches a
world on, and says it plainly: run it as administrator (it offers to restart itself so), or move
the game out of Program Files.

No Qt here: the dialog with "Restart as administrator" is ui.denied_box.
"""
import errno, os, re, sys

from .i18n import _

DENIED_WINERRORS = (5,)          # ERROR_ACCESS_DENIED
IN_USE_WINERRORS = (32, 33)      # a sharing / lock violation: a file in use, which no admin rights fix
DENIED_ERRNOS = (errno.EACCES, errno.EPERM)
_TEXT = re.compile(r"\[WinError 5\]|\[Errno 13\]|Permission denied|Access is denied", re.I)
_PATH = re.compile(r"""['"]([A-Za-z]:[\\/][^'"]*|\\\\[^'"]+)['"]""")
PROBE = ".fl26ms-write-test"


def probe(folder):
    """True when a file can be made (and removed) in `folder`, False when Windows refuses it,
    None when the folder is not there (nothing to say yet)"""
    if not folder or not os.path.isdir(folder):
        return None
    p = os.path.join(folder, "%s-%d.tmp" % (PROBE, os.getpid()))
    try:
        with open(p, "wb") as f:
            f.write(b"x")
    except OSError as e:
        return False if is_denied(e) else None
    try:
        os.remove(p)
    except OSError:
        pass
    return True


def folders(game):
    """the folders Mod Studio writes in, game folder first"""
    sd = game.sider_dir if game.folder else ""
    return [game.folder] + ([sd, os.path.join(sd, "modules"), os.path.join(sd, "livecpk"),
                             os.path.join(sd, "content")] if sd else [])


def blocked(game):
    """the first folder of the game Windows does not let Mod Studio write in, else None"""
    for d in folders(game):
        if probe(d) is False:
            return d
    return None


def is_denied(e):
    """is this exception (or the one it came from) Windows refusing a write?"""
    seen = set()
    while e is not None and id(e) not in seen:
        seen.add(id(e))
        if getattr(e, "winerror", None) in IN_USE_WINERRORS:
            return False                  # the game (or another program) has the file open
        if isinstance(e, PermissionError):
            return True
        if isinstance(e, OSError) and (getattr(e, "winerror", None) in DENIED_WINERRORS
                                       or e.errno in DENIED_ERRNOS):
            return True
        if _TEXT.search(str(e)):          # shutil.Error, a BuildError carrying the OSError's text
            return True
        e = e.__cause__ or e.__context__
    return False


def denied_path(err):
    """the path Windows refused when `err` (an exception or a traceback's text) is a refused
    write: "" when it names no path, None when it is not a refused write"""
    if isinstance(err, BaseException):
        if not is_denied(err):
            return None
        e = err
        while e is not None:
            if isinstance(e, OSError) and e.filename:
                return str(e.filename)
            e = e.__cause__ or e.__context__
        text = str(err)
    else:
        text = str(err or "")
        lines = [l for l in text.strip().splitlines() if l.strip()]
        # a traceback: only its last line says what stopped it
        if not lines or not _TEXT.search(lines[-1]):
            return None
        text = lines[-1]
    m = _PATH.findall(text)
    return m[-1].replace("\\\\", "\\") if m else ""


def in_program_files(path):
    p = os.path.normcase(os.path.abspath(path or ""))
    for v in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
        d = os.environ.get(v)
        if d and (p + os.sep).startswith(os.path.normcase(os.path.abspath(d)) + os.sep):
            return True
    return "\\program files" in p


def message(path, game_folder=None):
    """what to do, in plain words (translated)"""
    where = path or game_folder or ""
    text = _("Windows does not let Mod Studio write in %s.") % where if where else \
        _("Windows does not let Mod Studio write in the game folder.")
    if in_program_files(game_folder or path):
        text += " " + _("The game is installed under Program Files, which only a program run as "
                        "administrator may change.")
    text += "\n\n" + _("Do one of these:\n"
                       "  1. Restart Mod Studio as administrator (right-click FL26ModStudio.exe > Run "
                       "as administrator), or\n"
                       "  2. move the game out of Program Files (for example to C:\\Games\\Football Life "
                       "2026) and choose the new folder in Settings.")
    if is_admin():
        text += "\n\n" + _("Mod Studio already runs as administrator: the folder or a file in it is "
                           "read-only, or another program (an antivirus, the game) holds it.")
    return text


def is_admin():
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_command():
    """(program, its arguments) that start this Mod Studio again"""
    if getattr(sys, "frozen", False):
        args = sys.argv[1:]
    else:
        args = list(getattr(sys, "orig_argv", [sys.executable] + sys.argv))[1:]
    return sys.executable, [a for a in args if a != "--elevated"] + ["--elevated"]


def quote(a):
    return '"%s"' % a.replace('"', '\\"') if (not a or any(c in a for c in ' \t"')) else a


def restart_as_admin():
    """start Mod Studio again as administrator (Windows asks first); True when it started.
    The caller closes this one: the new one waits for it (--elevated, app.main)."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        exe, args = relaunch_command()
        r = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, " ".join(quote(a) for a in args),
                                                os.getcwd(), 1)
        return int(r) > 32
    except Exception:
        return False
