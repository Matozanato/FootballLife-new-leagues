"""Files read again only when they change (0.2.4: the Modpack's leaguebuilder-plan.json is ~1 s of
json.load, and Home, Leagues and Clubs read it on every visit -- 4 s to open Home). What is kept is
shared: callers read it and never change it."""
import json
import os
import threading
import time

_KEPT = {}
_SEEN = {}          # path: (time.monotonic() of the stat, its stamp), from whichever thread asked last


def stamp(path):
    try:
        st = os.stat(path)
    except OSError:
        got = None
    else:
        got = st.st_mtime_ns, st.st_size
    if isinstance(path, str):
        _SEEN[path] = (time.monotonic(), got)
    return got


def recent_stamp(path, within=10.0):
    """stamp(path) as some thread saw it at most `within` seconds ago, else asked again. B480
    (17.11.2026): the window's thread asked the disk for each of 317 league logos on every fill of
    New leagues (pixmap) -- 0.96 s and 3.3 s of a stopped window in the exe test of beta4p, right
    after Make it editable had copied 7.4 GB (the disk busy, each stat slow). The workers that make
    the small pictures ahead (builder.warm) ask for the same stamps a moment before"""
    got = _SEEN.get(path)
    if got is not None and time.monotonic() - got[0] <= within:
        return got[1]
    return stamp(path)


def listed_stamps(folder):
    """{name: stamp} of the files in folder, from one listing of it (no file opened: the size and
    the time come with the folder's entries), {} when it cannot be read"""
    out = {}
    try:
        with os.scandir(folder) as it:
            for e in it:
                try:
                    if e.is_file():
                        st = e.stat()
                        out[e.name] = (st.st_mtime_ns, st.st_size)
                except OSError:
                    pass
    except OSError:
        pass
    return out


def _let_go(entry):
    """B480 round 3 (17.11.2026): a kept value replaced by a newer one went when the last name for
    it went -- the local `got` of json_file, at its return: the GigaPack's old plan (286 MB of JSON,
    millions of objects) freed in one call of C with Python's lock held, from Build's worker, 3.9 s
    of a stopped window at the end of Build in the exe test of beta4r (faulthandler: the worker "at"
    builder.built_plan, the line that called json_file). Freed in small steps by letgo's thread"""
    if (isinstance(entry, tuple) and len(entry) == 2 and entry[1]
            and isinstance(entry[1], (dict, list, tuple, set))):
        from . import letgo
        letgo.drop(entry)


_READING = {}       # path: the lock of the one thread reading it (json_file)
_READING_LOCK = threading.Lock()


def json_file(path):
    """json.load of path, the same object while the file stays the same; OSError/ValueError as
    json.load gives them. Two threads asking for the same file at once read it once (B480 round 3:
    the GigaPack's plan is 2 GB in memory; Build's worker and a page's reader read it side by side)"""
    with _READING_LOCK:
        lock = _READING.setdefault(path, threading.Lock())
    with lock:
        return _json_file(path)


def _json_file(path):
    key = stamp(path)
    got = _KEPT.get(("json", path))
    if key is not None and got is not None and got[0] == key:
        return got[1]
    if got is not None:
        # the file changed: what was kept of it goes now, before the new one is read (one of
        # them in memory at a time), and in small steps
        if _KEPT.get(("json", path)) is got:
            _KEPT.pop(("json", path), None)
        _let_go(got)
        got = None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    old = _KEPT.get(("json", path))
    _KEPT[("json", path)] = (key, data)
    _let_go(old)
    old = None
    return data


def json_kept(path):
    """(value,) when json_file(path) has it already and the file is as it was, else None"""
    got = _KEPT.get(("json", path))
    if got is None:
        return None
    key = stamp(path)
    return (got[1],) if key is not None and got[0] == key else None


def by_files(name, paths, make):
    """make(), worked out again only when one of paths changed (or appeared, or went)"""
    key = tuple(stamp(p) for p in paths)
    got = _KEPT.get((name, tuple(paths)))
    if got is not None and got[0] == key:
        return got[1]
    got = None
    value = make()
    old = _KEPT.get((name, tuple(paths)))
    _KEPT[(name, tuple(paths))] = (key, value)
    _let_go(old)
    old = None
    return value


def stamps(paths):
    return tuple(stamp(p) for p in paths)


def kept(name, paths, key):
    """(value,) kept by by_files or keep for paths as they are (`key`, stamps(paths)), else None"""
    got = _KEPT.get((name, tuple(paths)))
    return (got[1],) if got is not None and got[0] == key else None


def keep(name, paths, key, value):
    """keep value for paths as they were when it was worked out (`key`, stamps(paths) then)"""
    old = _KEPT.get((name, tuple(paths)))
    _KEPT[(name, tuple(paths))] = (key, value)
    _let_go(old)
    old = None


def forget_under(folder):
    """drop what is kept of the files in `folder` (B66: a world renamed is read again under its new
    name, and its old 128 MB plan stayed in memory next to the new one)"""
    top = os.path.normcase(os.path.join(os.path.abspath(folder), ""))
    gone = []
    for k in list(_KEPT):
        paths = k[1] if isinstance(k[1], tuple) else (k[1],)
        if any(isinstance(p, str) and os.path.normcase(os.path.abspath(p)).startswith(top) for p in paths):
            got = _KEPT.pop(k, None)
            if got is not None:
                gone.append(got)
            got = None
    # B480: a world's plan kept here is millions of objects; popped and freed at once it kept
    # Python's lock 2.7 s (Make it editable, the exe test of beta4o). Freed in small steps now
    from . import letgo
    letgo.drop(gone)
    del gone
