"""B104: a made kit is drawn again only when its colours, crest or numbers kit change -- not
because the kit library sits at another path (another PC, the other slash), and never for a
world that came ready from a zip.  The drawing itself is faked: only the stamp logic is tested.

    python tools/test_kit_stamps.py
"""
import hashlib, os, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kitmaker, kitpics, lbservers

drawn = []


def fake_pictures(out, words, away=None, crest=None):
    return {"home": words}


def fake_make_kit(pics, tid, dst, numbers=None):
    os.makedirs(dst, exist_ok=True)
    drawn.append(tid)


kitmaker.pictures = fake_pictures
kitpics.make_kit = fake_make_kit

ok = 0


def check(what, cond):
    global ok
    if not cond:
        raise SystemExit("FAIL: " + what)
    ok += 1
    print("ok", what)


def legacy(words, away, crest, numbers):
    """the stamp Mod Studio 0.2.1-0.2.4 a00d29c wrote: the numbers kit's whole path"""
    h = hashlib.md5()
    for x in (words, away or "", numbers or "", os.path.getsize(kitmaker.MASK)):
        h.update(str(x).encode("utf-8") + b"\0")
    h.update(open(crest, "rb").read())
    return h.hexdigest()


tmp = tempfile.mkdtemp(prefix="fl26stamps")
try:
    crest = os.path.join(tmp, "e_071578_r_ll.png")
    with open(crest, "wb") as f:
        f.write(b"\x89PNG fake crest")
    words = "red shirt, white shorts"

    def lib_at(name):
        lib = os.path.join(tmp, name, "SiderAddons", "content", "kit-server")
        os.makedirs(os.path.join(lib, "3F Superliga", "Aarhus", "p1"), exist_ok=True)
        return lib, os.path.join(lib, "3F Superliga", "Aarhus")

    libA, numA = lib_at("pcA")
    dstA = os.path.join(libA, "_W", "Liga", "Club")
    check("first time the kit is drawn", lbservers._made(71578, words, "", crest, dstA, numA, print, lib=libA))
    check("same again: not drawn", not lbservers._made(71578, words, "", crest, dstA, numA, print, lib=libA))
    check("the other slash in the numbers path: not drawn",
          not lbservers._made(71578, words, "", crest, dstA, numA.replace(os.sep, "/"), print, lib=libA))

    # the same library on another PC (the world's zip carried the kit folder with its stamp)
    libB, numB = lib_at("pcB")
    dstB = os.path.join(libB, "_W", "Liga", "Club")
    shutil.copytree(dstA, dstB)
    check("another PC, same numbers kit: not drawn",
          not lbservers._made(71578, words, "", crest, dstB, numB, print, lib=libB))

    # an old stamp written on this PC (whole path, either slash) still counts
    for form in (numA, numA.replace(os.sep, "/")):
        with open(os.path.join(dstA, "kitmaker.txt"), "w", encoding="utf-8") as f:
            f.write(legacy(words, "", crest, form) + "\n")
        check("old stamp of this PC (%s): not drawn" % ("backslash" if os.sep in form else "slash"),
              not lbservers._made(71578, words, "", crest, dstA, numA, print, lib=libA))

    # an old stamp from the PC the zip was built on: drawn for a world of your own ...
    other = r"E:\instalacija\SiderAddons\content\kit-server\3F Superliga\Aarhus"
    with open(os.path.join(dstB, "kitmaker.txt"), "w", encoding="utf-8") as f:
        f.write(legacy(words, "", crest, other) + "\n")
    n = len(drawn)
    check("old stamp from another PC, own world: drawn again",
          lbservers._made(71578, words, "", crest, dstB, numB, print, lib=libB) and len(drawn) == n + 1)
    # ... and kept as it came for a world from a zip
    with open(os.path.join(dstB, "kitmaker.txt"), "w", encoding="utf-8") as f:
        f.write(legacy(words, "", crest, other) + "\n")
    check("old stamp from another PC, world from a zip: kept",
          not lbservers._made(71578, words, "", crest, dstB, numB, print, lib=libB, ready=True))

    # a real change is still drawn, also in a world from a zip without a stamp
    check("other colours: drawn", lbservers._made(71578, "blue shirt", "", crest, dstA, numA, print, lib=libA))
    with open(crest, "ab") as f:
        f.write(b"another crest")
    check("other crest: drawn", lbservers._made(71578, "blue shirt", "", crest, dstA, numA, print, lib=libA))
    check("other numbers kit: drawn",
          lbservers._made(71578, "blue shirt", "", crest, dstA, os.path.join(libA, "Other", "Kit"), print, lib=libA))
    dstC = os.path.join(libB, "_W", "Liga", "New club")
    check("world from a zip, kit folder without a stamp: drawn",
          lbservers._made(71579, words, "", crest, dstC, numB, print, lib=libB, ready=True))
    check("no numbers kit at all: drawn once, then kept",
          lbservers._made(71580, words, "", crest, os.path.join(libA, "_W", "L", "N"), None, print, lib=libA)
          and not lbservers._made(71580, words, "", crest, os.path.join(libA, "_W", "L", "N"), None, print, lib=libA))
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print("test_kit_stamps: %d ok" % ok)
