"""GigaPack beta 4 (18.11.2026): a kit / scoreboard folder a world zip installed was "changed by you, kept"
at every later Build (Install gives its files the unpack time, its modstudio-copy.txt has the building PC's
times), so a newer package (HNL's Thunder105 board) never went in.
  python -I test_b_zip_times.py [<folder with lbservers.py and modstudio\\installer.py>]"""
import os, shutil, sys, tempfile, time, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else HERE
TOOLS = HERE
sys.path[:0] = [MOD, TOOLS]
import lbservers as S          # noqa: E402
fails = []


def ok(what, cond):
    print(("ok   " if cond else "FAIL ") + what)
    if not cond:
        fails.append(what)


def put(p, text):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        f.write(text)


def age(d, s):
    for x, _s, fs in os.walk(d):
        for f in fs:
            p = os.path.join(x, f)
            os.utime(p, (os.path.getmtime(p) - s, os.path.getmtime(p) - s))


def zip_install(dst, tmp):
    """dst as a world zip brings it: zipped with its times, unpacked as zipfile does (times = now)"""
    z = os.path.join(tmp, "w.zip")
    with zipfile.ZipFile(z, "w") as zz:
        for x, _s, fs in os.walk(dst):
            for f in fs:
                zz.write(os.path.join(x, f), os.path.relpath(os.path.join(x, f), dst))
    shutil.rmtree(dst)
    with zipfile.ZipFile(z) as zz:
        zz.extractall(dst)


with tempfile.TemporaryDirectory() as tmp:
    src, dst = os.path.join(tmp, "pkg", "HNL"), os.path.join(tmp, "game", "HNL")
    put(os.path.join(src, "bg.dds"), "old board")
    put(os.path.join(src, "config.ini"), "x=1")
    age(src, 29 * 86400)                                   # built a month ago
    ok("first copy", S._copy(src, dst) == "copied")

    def fresh():
        shutil.rmtree(dst, ignore_errors=True)
        shutil.rmtree(src)
        put(os.path.join(src, "bg.dds"), "old board")
        put(os.path.join(src, "config.ini"), "x=1")
        age(src, 29 * 86400)
        S._copy(src, dst)
        zip_install(dst, tmp)                              # Install mods of the world zip: times = now
        put(os.path.join(src, "bg.dds"), "the NEW board, Thunder105")       # the recipe's newer source
        put(os.path.join(src, "flag_teams", "1", "a.dds"), "new")

    fresh()
    said = []
    got = S._copy(src, dst, said.append)
    ok("zip-installed copy, untouched: the newer package goes in (current code: kept) -> %s" % got,
       got == "copied" and open(os.path.join(dst, "bg.dds")).read() == "the NEW board, Thunder105")
    ok("  and its note is written again", os.path.isfile(os.path.join(dst, S.COPIED)))
    ok("  and a second Build: same", S._copy(src, dst) == "same")

    # B166 still holds
    fresh()
    put(os.path.join(dst, "bg.dds"), "drawn by hand, another size")
    ok("B166: a zip-installed copy changed by hand (other size) stays", S._copy(src, dst) == "kept")
    fresh()
    p = os.path.join(dst, "bg.dds")
    put(p, "OLD BOARD")                                    # same size, edited later
    t = os.path.getmtime(os.path.join(dst, S.COPIED)) + 3600
    os.utime(p, (t, t))
    ok("B166: same size, changed after the install (newer than the note) stays", S._copy(src, dst) == "kept")
    fresh()
    put(os.path.join(dst, "mine.dds"), "added by hand")
    ok("B166: a file added by hand: stays", S._copy(src, dst) == "kept")
    fresh()
    os.remove(os.path.join(dst, "config.ini"))
    ok("B166: a file taken out by hand: stays", S._copy(src, dst) == "kept")


print("%d failed" % len(fails) if fails else "all passed")
sys.exit(1 if fails else 0)
