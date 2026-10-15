"""restore points: a copy of a file taken before the program changes it.

Copies live next to the game in SiderAddons\\ModStudio\\backups, one folder per day, with an
index (backups.json) that says what each copy was, when, and why.  Nothing is ever deleted
automatically except by keep(): the older copies of one file beyond the newest `n`, but
never the oldest one (Put Sider back as before Mod Studio needs it).
"""
import json, os, shutil, time

HOME = "ModStudio"


def home(sider_dir):
    d = os.path.join(sider_dir, HOME)
    os.makedirs(d, exist_ok=True)
    return d


def _dir_of(path):
    """the SiderAddons folder a file belongs to (the one that holds sider.ini)"""
    d = os.path.dirname(os.path.abspath(path))
    probe = d
    while True:
        if os.path.exists(os.path.join(probe, "sider.ini")):
            return probe
        up = os.path.dirname(probe)
        if up == probe:
            return d
        probe = up


def _index(sider_dir):
    return os.path.join(home(sider_dir), "backups.json")


def load(sider_dir):
    try:
        with open(_index(sider_dir), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def _save(sider_dir, rows):
    p = _index(sider_dir)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=1, ensure_ascii=False)
    os.replace(p + ".tmp", p)


def snapshot(path, reason="", sider_dir=None, before=False):
    """copy `path` into the backups folder; returns the copy's path. before: the file was there
    before Mod Studio's Build first changed it (what a <file>.before-builder next to it said)"""
    sd = sider_dir or _dir_of(path)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    day = os.path.join(home(sd), "backups", stamp[:8])
    os.makedirs(day, exist_ok=True)
    rel = os.path.relpath(os.path.abspath(path), sd)
    base = rel.replace("\\", "__").replace("/", "__")
    dst = os.path.join(day, "%s.%s" % (base, stamp[9:]))
    n = 1
    while os.path.exists(dst):
        n += 1
        dst = os.path.join(day, "%s.%s-%d" % (base, stamp[9:], n))
    shutil.copy2(path, dst)
    rows = load(sd)
    row = {"file": rel, "copy": os.path.relpath(dst, sd), "time": stamp,
           "reason": reason, "size": os.path.getsize(dst)}
    if before:
        row["before"] = True
    rows.append(row)
    _save(sd, rows)
    return dst


def before_change(path, reason, sider_dir=None, keep_n=30):
    """a restore point of `path` before Build or Switch on changes it. Until 0.2.4 these were
    copies next to the file -- map.txt.before-builder (the first one) and map.txt.prev (the last
    one), sider.ini.before-builder, modules\\before-builder-<n>\\ -- and players found them all
    over their content folders (mato 15.10.: "from now on" in SiderAddons\\ModStudio\\backups,
    where Restore points shows them). The first copy is marked `before`, as the .before-builder
    one was: Put Sider back as before Mod Studio puts that one back (factory.originals). Of one
    file the newest `keep_n` copies stay, and the first; None when there is no file yet"""
    if not os.path.isfile(path):
        return None
    sd = sider_dir or _dir_of(path)
    rel = os.path.relpath(os.path.abspath(path), sd).lower()
    first = not os.path.exists(path + ".before-builder") and not any(
        r.get("before") and r["file"].lower() == rel for r in load(sd))
    dst = snapshot(path, reason, sd, before=first)
    keep(sd, os.path.relpath(os.path.abspath(path), sd), keep_n)
    return dst


def history(sider_dir, rel=None):
    """newest first; rel limits it to one file (e.g. "sider.ini")"""
    rows = [r for r in load(sider_dir) if rel is None or r["file"].lower() == rel.lower()]
    rows = [r for r in rows if os.path.exists(os.path.join(sider_dir, r["copy"]))]
    return sorted(rows, key=lambda r: r["time"], reverse=True)


def restore(sider_dir, row):
    """put a copy back; the file as it is now is itself kept first"""
    target = os.path.join(sider_dir, row["file"])
    if os.path.exists(target):
        snapshot(target, "before restoring %s" % row["time"], sider_dir)
    shutil.copy2(os.path.join(sider_dir, row["copy"]), target)
    return target


def keep(sider_dir, rel, n=50):
    rows = history(sider_dir, rel)
    gone = rows[n:-1]          # the oldest copy stays: it is the file as it was before Mod Studio
    gone = [r for r in gone if not r.get("before")]     # and so does the one marked as that (before_change)
    for r in gone:
        try:
            os.remove(os.path.join(sider_dir, r["copy"]))
        except OSError:
            pass
    if gone:
        drop = {r["copy"] for r in gone}
        _save(sider_dir, [r for r in load(sider_dir) if r["copy"] not in drop])
    return len(gone)
