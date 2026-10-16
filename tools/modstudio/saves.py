r"""Each world its own Master League careers (0.2.4, mato 15.10., from a tester's .bat).

The game keeps its saves in Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save. A career
holds team and competition ids, so a career of one world is no good in another one. When the world
in the game changes, the save folder changes with it:

    save              the careers of the world in the game now
    save_<world>      the careers of every other world, kept aside (save_no-world: the game
                      without a world of ours)

    swap_saves(old, new)   save -> save_<old>, save_<new> -> save (an empty save when there is none)
    rename_saves(old, new) save_<old> -> save_<new>, for Rename world
    Switch                 one world switch as the pages do it: the setting, the checks, the swap,
                           the undo when the switch itself stops, the first-time note

What travels with the world and what stays: the whole folder moves (what the tester's .bat does),
so everything the game writes for a career goes with its world -- ML* (Master League), BL*
(Become a Legend), CUP* / LEAGUE* (cup and league modes), EDIT00000000 (the Edit data, which hides
a world's own squads and names when it is another world's: game.py) and any file whose name we do
not know. The player's settings are the one thing that is not a world's: files whose name says so
(SHARED: SYSTEM*, OPTION*, SETTING*, CONFIG*, controller / key files) are copied from the folder
going out into the one coming in, so the options set in one world are there in the next.

Nothing is ever deleted. Before the first swap ever the whole save folder is copied into
SiderAddons\ModStudio\backups\saves\<date> (Restore points lists it). A swap is refused, with
nothing renamed, while the game runs, when a name it needs is taken, or when Windows refuses the
second rename (the first one is undone). The world whose careers are in save is written down in
modstudio-saves.json next to save, so a switch made while this was off, or a reset of Sider, does
not put one world's careers under another's name.

No Qt here: the pages ask (pages/builder.py, install.py, roots.py, profiles.py, restore.py).
"""
import json, os, re, shutil, time

from . import backups
from .game import SAVE_DIR, Game
from .i18n import _

ENV = "FL26_SAVE_ROOT"           # the folder that holds save (tests and the build test: a temp folder)
ACTIVE = "save"
PREFIX = "save_"
NO_WORLD = "no-world"
STATE = "modstudio-saves.json"
SETTING = "save_per_world"       # Settings: on unless the player turns it off
SHARED = re.compile(r"(?i)^(sys|option|setting|config|control|keyconf|keyboard|gamepad|pad)")
AUTO = object()


class SaveError(Exception):
    """a swap that cannot be done, in words for the player; nothing was renamed"""


# ---- where -------------------------------------------------------------------------------------
def root():
    """the folder that holds the game's save folder"""
    return os.environ.get(ENV) or os.path.join(SAVE_DIR, "2026")


def name_of(world):
    return PREFIX + (world or NO_WORLD)


def folder_of(world, r=None):
    """where the careers of `world` (None: no world of ours) are kept while it is not in the game"""
    return os.path.join(r or root(), name_of(world))


def label(world):
    return world or _("the game without a world")


def is_shared(name):
    """a settings file: the player's, whichever world is in the game"""
    return bool(SHARED.match(name))


def game_running():
    """the game has its saves open (tests put a stand-in here)"""
    return Game.running()[0]


def enabled(settings):
    """the setting (on unless turned off). Never in a window without a screen (the tests run the
    whole window offscreen) unless FL26_SAVE_ROOT gives a save folder of their own: a test must
    never rename the save folder of the PC it runs on"""
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen" and not os.environ.get(ENV):
        return False
    return bool((settings or {}).get(SETTING, True))


# ---- the note next to save: whose careers are in it, when the first copy was made ----------------
def load_state(r=None):
    try:
        with open(os.path.join(r or root(), STATE), encoding="utf-8") as f:
            st = json.load(f)
        return st if isinstance(st, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_state(st, r=None):
    p = os.path.join(r or root(), STATE)
    try:
        with open(p + ".tmp", "w", encoding="utf-8") as f:
            json.dump(st, f, indent=1, ensure_ascii=False)
        os.replace(p + ".tmp", p)
    except OSError:
        pass                                     # only a note: the folders are what count


def owner(live, r=None):
    """the world whose careers are in save: the one written down at the last swap, else `live`
    (the world in the game now)"""
    st = load_state(r)
    return st["active"] if "active" in st else live


def forget_owner(r=None):
    """the setting was turned on again: from now on save is the world in the game's"""
    st = load_state(r)
    if "active" in st:
        del st["active"]
        _save_state(st, r)


# ---- checks ------------------------------------------------------------------------------------
def check(old, new, r=None, running=None):
    """why the careers cannot be swapped from `old` to `new` now, or "" """
    if old == new:
        return ""
    if (running or game_running)():
        return _("The game is running. Close it first: the world's Master League careers are switched "
                 "with it, and the game has the save folder open.")
    r = r or root()
    active, out, inn = os.path.join(r, ACTIVE), folder_of(old, r), folder_of(new, r)
    if os.path.exists(active) and not os.path.isdir(active):
        return _("%s is a file, not the game's save folder. Move it away first.") % active
    if os.path.isdir(active) and os.path.lexists(out):
        return _("The careers of %s cannot be put aside: there is a %s in %s already (from before?). "
                 "Rename or move it first; nothing was changed.") % (label(old), name_of(old), r)
    if os.path.lexists(inn) and not os.path.isdir(inn):
        return _("%s is a file, not a save folder. Move it away first; nothing was changed.") % inn
    return ""


# ---- the first copy --------------------------------------------------------------------------------
def saves_home(sider_dir):
    return os.path.join(backups.home(sider_dir), "backups", "saves")


def backup(sider_dir, r=None, why="before the first world switch"):
    """a copy of the whole save folder in SiderAddons\\ModStudio\\backups\\saves\\<date>; the copy's
    folder, or None when there is no save folder yet"""
    r = r or root()
    src = os.path.join(r, ACTIVE)
    if not os.path.isdir(src):
        return None
    base = saves_home(sider_dir)
    stamp = time.strftime("%Y-%m-%d %H-%M")
    d, n = os.path.join(base, stamp), 2
    while os.path.exists(d):
        d, n = os.path.join(base, "%s (%d)" % (stamp, n)), n + 1
    shutil.copytree(src, os.path.join(d, ACTIVE))
    with open(os.path.join(d, "saves.json"), "w", encoding="utf-8") as f:
        json.dump({"kind": "saves", "time": time.strftime("%Y%m%d-%H%M%S"), "from": src, "why": why,
                   "world": load_state(r).get("active")}, f, indent=1, ensure_ascii=False)
    return d


def backups_of(sider_dir):
    """the save folder copies, newest first: [(folder, info)] (Restore points lists them)"""
    out = []
    base = os.path.join(sider_dir, backups.HOME, "backups", "saves")
    try:
        names = os.listdir(base)
    except OSError:
        return out
    for n in names:
        d = os.path.join(base, n)
        try:
            with open(os.path.join(d, "saves.json"), encoding="utf-8") as f:
                out.append((d, json.load(f)))
        except (OSError, ValueError):
            continue
    return sorted(out, key=lambda x: x[1].get("time", ""), reverse=True)


# ---- the swap ----------------------------------------------------------------------------------
def swap_saves(old, new, sider_dir=None, r=None, running=None, log=None, first_copy=True):
    """the careers of `old` aside (save -> save_<old>), those of `new` in (save_<new> -> save, or a
    new empty save), then the settings files copied over. Returns what was done, or None when
    there is nothing to do (old == new). SaveError, with nothing renamed, when it cannot be done"""
    log = log or (lambda t: None)
    if old == new:
        return None
    r = r or root()
    why = check(old, new, r, running)
    if why:
        raise SaveError(why)
    active, out, inn = os.path.join(r, ACTIVE), folder_of(old, r), folder_of(new, r)
    st = load_state(r)
    first = first_copy and not st.get("swaps")
    copy = None
    if first and sider_dir and os.path.isdir(active):
        try:
            copy = backup(sider_dir, r)
        except OSError as e:
            raise SaveError(_("The copy of your save folder could not be made, so nothing was switched: %s") % e)
        log(_("save folder copied first into %s") % copy)
    moved, made = [], False
    try:
        if os.path.isdir(active):
            os.rename(active, out)
            moved.append((active, out))
        if os.path.isdir(inn):
            os.rename(inn, active)
            moved.append((inn, active))
        else:
            os.makedirs(active)
            made = True
    except OSError as e:
        for a, b in reversed(moved):              # the first rename back: as it was
            try:
                os.rename(b, a)
            except OSError:
                pass
        raise SaveError(_("Windows did not let Mod Studio rename the save folder (%s). Everything is as "
                          "it was; nothing was switched.") % e)
    shared = []
    if moved and moved[0][1] == out:
        for f in sorted(os.listdir(out)):
            a, b = os.path.join(out, f), os.path.join(active, f)
            if not (is_shared(f) and os.path.isfile(a)):
                continue
            try:
                if os.path.isfile(b) and _same_bytes(a, b):
                    continue
                shutil.copy2(a, b)
                shared.append(f)
            except OSError as e:
                log(_("settings file %s not copied: %s") % (f, e))
    st["active"] = new
    st.setdefault("swaps", []).append({"time": time.strftime("%Y%m%d-%H%M%S"), "old": old, "new": new,
                                       "fresh": made})
    st["swaps"] = st["swaps"][-50:]
    if copy:
        st["backup"] = copy
    _save_state(st, r)
    log(_("Master League saves: %s -> %s, %s -> save%s") % (
        ACTIVE, name_of(old) if moved and moved[0][1] == out else "-",
        name_of(new) if not made else _("a new empty folder"),
        (_("; settings copied: ") + ", ".join(shared)) if shared else ""))
    return {"old": old, "new": new, "out": out if moved and moved[0][1] == out else None,
            "fresh": made, "first": first, "backup": copy, "shared": shared, "root": r}


def _same_bytes(a, b):
    if os.path.getsize(a) != os.path.getsize(b):
        return False
    with open(a, "rb") as fa, open(b, "rb") as fb:
        return fa.read() == fb.read()


def check_rename(old, new, r=None):
    r = r or root()
    if os.path.lexists(folder_of(old, r)) and os.path.lexists(folder_of(new, r)):
        return _("There is a %s in %s already (careers of an earlier world of that name?). Rename or "
                 "move it first; nothing was renamed.") % (name_of(new), r)
    return ""


def rename_saves(old, new, r=None, log=None):
    """Rename world: save_<old> -> save_<new> (and the note of whose careers are in save). The new
    path, or None when the world has no careers kept aside"""
    r = r or root()
    st = load_state(r)
    if st.get("active") == old:
        st["active"] = new
        _save_state(st, r)
    a, b = folder_of(old, r), folder_of(new, r)
    if not os.path.isdir(a):
        return None
    why = check_rename(old, new, r)
    if why:
        raise SaveError(why)
    os.rename(a, b)
    (log or (lambda t: None))("%s -> %s" % (name_of(old), name_of(new)))
    return b


# ---- one world switch, as the pages do it ---------------------------------------------------------
def in_game(game):
    from . import worlds as WL
    live = WL.live(game)
    return live[0] if live else None


def worlds_on(game, ini):
    """the worlds an ini object (not saved yet) switches on, Sider's order"""
    from .siderini import root_path
    from . import worlds as WL
    out = []
    for e in ini.entries("cpk.root"):
        if not e.enabled:
            continue
        p = root_path(game.sider_dir, e.value)
        n = os.path.basename(os.path.normpath(p))
        if WL.is_world(n) and os.path.normcase(os.path.dirname(os.path.normpath(p))) == \
                os.path.normcase(os.path.normpath(game.livecpk_dir)) and n not in out:
            out.append(n)
    return out


class Switch:
    """the save folder half of one world switch. A page makes one before it asks (problem() says why
    it cannot be done; the page refuses with that), go() right before the world goes in, undo()
    when the world switch itself stops, note() for the first time"""

    def __init__(self, settings, game, new, old=AUTO, r=None):
        self.on = enabled(settings)
        self.game, self.new, self._old, self.r = game, new, old, r
        self.result = None

    def live(self):
        """the world in the game before the switch"""
        return in_game(self.game) if self._old is AUTO else self._old

    def old(self):
        """the world whose careers are in save now (saves.owner)"""
        return owner(self.live(), self.r)

    def needed(self):
        """a real switch (another world goes in) and save is not already the new world's (after a
        reset of Sider the game had no world, but save still held the old one's careers)"""
        if not self.on:
            return False
        live = self.live()
        return live != self.new and owner(live, self.r) != self.new

    def problem(self):
        return check(self.old(), self.new, self.r) if self.needed() else ""

    def go(self, log=None):
        if not self.needed():
            return None
        self.result = swap_saves(self.old(), self.new, self.game.sider_dir, self.r, log=log)
        return self.result

    def undo(self, log=None):
        res, self.result = self.result, None
        if res:
            swap_saves(res["new"], res["old"], self.game.sider_dir, res["root"], log=log, first_copy=False)

    def ask_text(self):
        """a line for the question before the switch"""
        if not self.needed():
            return ""
        old, r = self.old(), self.r or root()
        has = os.path.isdir(folder_of(self.new, r))
        return _("Master League careers: those of %s are kept in %s; %s %s.") % (
            label(old), name_of(old), label(self.new),
            _("gets its own back") if has else _("starts with its own (none yet)"))

    def note(self):
        """the first swap ever: what happened, in plain words, once"""
        res = self.result
        if not res or not res.get("first"):
            return ""
        text = _("Each world now keeps its own Master League careers. Your careers of %s are kept in %s "
                 "(in %s); %s starts with its own. Put %s back in the game and its careers come back.") % (
            label(res["old"]), name_of(res["old"]), res["root"], label(res["new"]), label(res["old"]))
        if not res["fresh"]:
            text = _("Each world now keeps its own Master League careers. Your careers of %s are kept in %s "
                     "(in %s); %s gets its own careers back from %s.") % (
                label(res["old"]), name_of(res["old"]), res["root"], label(res["new"]), name_of(res["new"]))
        if res.get("backup"):
            text += "\n\n" + _("A copy of your save folder as it was is in %s.") % res["backup"]
        return text + "\n\n" + _("You can turn this off in Settings.")
