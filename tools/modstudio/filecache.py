"""Files read again only when they change (0.2.4: the Modpack's leaguebuilder-plan.json is ~1 s of
json.load, and Home, Leagues and Clubs read it on every visit -- 4 s to open Home). What is kept is
shared: callers read it and never change it."""
import json
import os

_KEPT = {}


def stamp(path):
    try:
        st = os.stat(path)
    except OSError:
        return None
    return st.st_mtime_ns, st.st_size


def json_file(path):
    """json.load of path, the same object while the file stays the same; OSError/ValueError as
    json.load gives them"""
    key = stamp(path)
    got = _KEPT.get(("json", path))
    if key is not None and got is not None and got[0] == key:
        return got[1]
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    _KEPT[("json", path)] = (key, data)
    return data


def by_files(name, paths, make):
    """make(), worked out again only when one of paths changed (or appeared, or went)"""
    key = tuple(stamp(p) for p in paths)
    got = _KEPT.get((name, tuple(paths)))
    if got is not None and got[0] == key:
        return got[1]
    value = make()
    _KEPT[(name, tuple(paths))] = (key, value)
    return value
