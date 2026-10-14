"""python test_filecache.py -- a file Mod Studio reads on every visit of a page (the built world's
leaguebuilder-plan.json, ~1 s on the Modpack) is read again only when it changes (0.2.4: Home took
4 s to open, Leagues 4.5 s); a changed or removed file is never served from before."""
import json, os, shutil, sys, tempfile, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modstudio import filecache

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def main():
    d = tempfile.mkdtemp(prefix="fl26-filecache-")
    try:
        p = os.path.join(d, "leaguebuilder-plan.json")
        json.dump({"leagues": [1, 2]}, open(p, "w"))
        a = filecache.json_file(p)
        ok("read", a == {"leagues": [1, 2]})
        ok("the same file again: not read again", filecache.json_file(p) is a)
        time.sleep(0.02)
        json.dump({"leagues": [1, 2, 3]}, open(p, "w"))
        ok("a changed file is read again", filecache.json_file(p) == {"leagues": [1, 2, 3]})
        calls = []
        f = lambda: calls.append(1) or len(calls)
        ok("by_files works it out", filecache.by_files("t", [p], f) == 1)
        ok("and keeps it while the files stay", filecache.by_files("t", [p], f) == 1 and len(calls) == 1)
        time.sleep(0.02)
        json.dump({"leagues": []}, open(p, "w"))
        ok("again when one changes", filecache.by_files("t", [p], f) == 2)
        os.remove(p)
        try:
            filecache.json_file(p)
            ok("a removed file is not served from before", False)
        except OSError:
            ok("a removed file is not served from before", True)
        ok("by_files again when a file goes", filecache.by_files("t", [p], f) == 3)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    print("1..%d" % N)


if __name__ == "__main__":
    main()
