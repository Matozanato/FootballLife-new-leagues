"""profiles: named setups -- which content folders and modules are switched on, in which order.

A profile is SiderAddons\\ModStudio\\profiles\\<name>.json:

    {"name": "...", "saved": "20260928-013000", "note": "...",
     "cpk.root":   [["value", true], ...],       # in order, on/off
     "lua.module": [["value", false], ...]}

Switching to a profile switches every listed line on or off and puts them in the profile's
order; lines the profile does not know are switched off (they were added after it was saved),
and lines it knows that sider.ini lost are added back when their file or folder is still there.

The first time the program sees a game it saves the setup as it found it ("As found"), so
there is always a way back to the game as it was -- that is what safe mode switches to.
"""
import json, os, re, time

from .siderini import norm, root_path
from .backups import home

KEYS = ("cpk.root", "lua.module")
FIRST = "As found"


def folder(sider_dir):
    d = os.path.join(home(sider_dir), "profiles")
    os.makedirs(d, exist_ok=True)
    return d


def safe_name(name):
    return re.sub(r'[<>:"/\\|?*]+', "_", name).strip() or "profile"


def capture(ini, name, note=""):
    p = {"name": name, "saved": time.strftime("%Y%m%d-%H%M%S"), "note": note}
    for k in KEYS:
        p[k] = [[e.value, e.enabled] for e in ini.entries(k)]
    return p


def save(sider_dir, prof):
    p = os.path.join(folder(sider_dir), safe_name(prof["name"]) + ".json")
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(prof, f, indent=1, ensure_ascii=False)
    os.replace(p + ".tmp", p)
    return p


def listing(sider_dir):
    out = []
    d = folder(sider_dir)
    for f in sorted(os.listdir(d)):
        if f.lower().endswith(".json"):
            try:
                with open(os.path.join(d, f), encoding="utf-8") as fh:
                    p = json.load(fh)
                p["_file"] = os.path.join(d, f)
                out.append(p)
            except (OSError, ValueError):
                pass
    out.sort(key=lambda p: (p["name"] != FIRST, p["name"].lower()))
    return out


def delete(prof):
    os.remove(prof["_file"])


def ensure_first(sider_dir, ini):
    """save the setup as found, once per game"""
    if ini is None:
        return False
    if any(p["name"] == FIRST for p in listing(sider_dir)):
        return False
    save(sider_dir, capture(ini, FIRST, "the setup the first time FL26 Mod Studio opened this game"))
    return True


def differences(ini, prof):
    """(switched on, switched off, moved, added back) counts if the profile were applied"""
    on = off = add = 0
    for k in KEYS:
        want = {norm(v): en for v, en in prof.get(k, [])}
        have = {norm(e.value): e.enabled for e in ini.entries(k)}
        for v, en in have.items():
            w = want.get(v, False)
            if w and not en:
                on += 1
            elif en and not w:
                off += 1
        add += sum(1 for v, en in want.items() if en and v not in have)
    return on, off, add


def apply(ini, prof, sider_dir, modules_dir):
    """change `ini` (not saved) to the profile; returns notes about lines that could not come back"""
    notes = []
    for k in KEYS:
        want = prof.get(k, [])
        wmap = {norm(v): en for v, en in want}
        have = {norm(e.value) for e in ini.entries(k)}
        for v, en in want:
            if norm(v) in have or not en:
                continue
            there = os.path.isdir(root_path(sider_dir, v)) if k == "cpk.root" else \
                os.path.exists(os.path.join(modules_dir, v))
            if there:
                ini.add(k, v)
            else:
                notes.append("%s %s is gone from disk" % ("folder" if k == "cpk.root" else "module", v))
        seen = set()
        for e in ini.entries(k):                 # a line listed twice: only the first is on
            on = wmap.get(norm(e.value), False) and norm(e.value) not in seen
            if on:
                seen.add(norm(e.value))
            if on != e.enabled:
                ini.set_enabled(e, on)
        ini.reorder(k, [v for v, en in want])
    return notes
