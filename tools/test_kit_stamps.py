"""B104: a made kit is drawn again only when its colours, crest or numbers kit change -- not
because the kit library sits at another path (another PC, the other slash), and never for a
world that came ready from a zip.  The drawing itself is faked: only the stamp logic is tested.

    python tools/test_kit_stamps.py
"""
import hashlib, os, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kitmaker, kitpics, lbservers

drawn = []


def fake_pictures(out, words, away=None, crest=None, seed=None, third=None):
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
    other = r"E:\FL\FL26\game\SiderAddons\content\kit-server\3F Superliga\Aarhus"
    with open(os.path.join(dstB, "kitmaker.txt"), "w", encoding="utf-8") as f:
        f.write(legacy(words, "", crest, other) + "\n")
    n = len(drawn)
    check("old stamp from another PC, own world, a Switch on: kept (B374)",
          not lbservers._made(71578, words, "", crest, dstB, numB, print, lib=libB) and len(drawn) == n)
    check("old stamp from another PC, own world, a Build: drawn again",
          lbservers._made(71578, words, "", crest, dstB, numB, print, lib=libB, redraw=True) and len(drawn) == n + 1)
    # ... and kept as it came for a world from a zip
    with open(os.path.join(dstB, "kitmaker.txt"), "w", encoding="utf-8") as f:
        f.write(legacy(words, "", crest, other) + "\n")
    check("old stamp from another PC, world from a zip: kept",
          not lbservers._made(71578, words, "", crest, dstB, numB, print, lib=libB, ready=True))

    # a real change is still drawn, also in a world from a zip without a stamp
    # (B374: a Switch on too, when the kit's stamp says what it was drawn from -- one drawn today)
    os.remove(os.path.join(dstA, "kitmaker.txt"))
    lbservers._made(71578, words, "", crest, dstA, numA, print, lib=libA)
    check("other colours, a Switch on: drawn", lbservers._made(71578, "blue shirt", "", crest, dstA, numA, print, lib=libA))
    check("other colours: drawn",
          lbservers._made(71578, "green shirt", "", crest, dstA, numA, print, lib=libA, redraw=True))
    with open(crest, "ab") as f:
        f.write(b"another crest")
    check("other crest: drawn", lbservers._made(71578, "green shirt", "", crest, dstA, numA, print, lib=libA, redraw=True))
    check("other numbers kit: drawn",
          lbservers._made(71578, "green shirt", "", crest, dstA, os.path.join(libA, "Other", "Kit"), print, lib=libA,
                          redraw=True))
    check("other numbers kit, a Switch on: kept (06.11.: a world built since changed the lending kits)",
          not lbservers._made(71578, "green shirt", "", crest, dstA, numA, print, lib=libA))
    dstC = os.path.join(libB, "_W", "Liga", "New club")
    check("world from a zip, kit folder without a stamp: drawn",
          lbservers._made(71579, words, "", crest, dstC, numB, print, lib=libB, ready=True))
    check("no numbers kit at all: drawn once, then kept",
          lbservers._made(71580, words, "", crest, os.path.join(libA, "_W", "L", "N"), None, print, lib=libA)
          and not lbservers._made(71580, words, "", crest, os.path.join(libA, "_W", "L", "N"), None, print, lib=libA))
    # club_third_kits (megapack 06.11.): no third keeps the stamp as before, a third of its own is drawn again
    check("no third kit given: the same stamp as before",
          lbservers._stamps(words, "", crest, numA, libA)[0] == lbservers._stamps(words, "", crest, numA, libA, third=None)[0])
    dstD = os.path.join(libA, "_W", "L", "Third")
    lbservers._made(71581, words, "", crest, dstD, numA, print, lib=libA)
    check("a third kit of the recipe's own: drawn again",
          lbservers._made(71581, words, "", crest, dstD, numA, print, lib=libA, third="hoops #14285a #f5d000 #f5d000",
                          redraw=True)
          and not lbservers._made(71581, words, "", crest, dstD, numA, print, lib=libA, third="hoops #14285a #f5d000 #f5d000"))
    # B374 (09.11.): another drawing of the same kit (B360 drew third kits anew) -- a Switch on keeps it
    dstE = os.path.join(libA, "_W", "L", "Drawing")
    lbservers._made(71582, words, "", crest, dstE, numA, print, lib=libA)
    with open(os.path.join(dstE, "kitmaker.txt"), "w", encoding="utf-8") as f:
        f.write("0123456789abcdef0123456789abcdef" + chr(10))  # a stamp no drawing of today writes, from before 09.11.
    n = len(drawn)
    check("another drawing, a Switch on: kept", not lbservers._made(71582, words, "", crest, dstE, numA, print, lib=libA)
          and len(drawn) == n)
    check("another drawing, a Build: drawn again",
          lbservers._made(71582, words, "", crest, dstE, numA, print, lib=libA, redraw=True) and len(drawn) == n + 1)
    with open(os.path.join(dstE, "kitmaker.txt"), "w", encoding="utf-8") as f:
        f.write("0123456789abcdef0123456789abcdef" + chr(10) + lbservers._given(words, "", crest) + chr(10))
    n = len(drawn)
    check("another drawing from the same colours and crest, a Switch on: kept",
          not lbservers._made(71582, words, "", crest, dstE, numA, print, lib=libA) and len(drawn) == n)
    check("... other colours, a Switch on: drawn",
          lbservers._made(71582, "blue shirt", "", crest, dstE, numA, print, lib=libA) and len(drawn) == n + 1)
    check("the stamp says what it was drawn from, the crest file it read and the rest (4 lines)",
          len(open(os.path.join(dstE, "kitmaker.txt"), encoding="utf-8").read().split()) == 4)
    # a Switch on that keeps the kit neither walks the library for the numbers kits nor works out
    # the drawing plan (_FL26Megapack, 09.11.: 4345 kits kept in 75 s, 66 of them the plan)
    asked, plans, real_plan = [], [], kitmaker.plan
    kitmaker.plan = lambda *a, **k: plans.append(1) or real_plan(*a, **k)
    try:
        kept = not lbservers._made(71582, "blue shirt", "", crest, dstE,
                                   lambda: asked.append(1) or numA, print, lib=libA)
        check("kept at a Switch on: no library walk, no drawing plan", kept and not asked and not plans)
        check("numbers as a function, drawn: asked once",
              lbservers._made(71582, words, "", crest, dstE, lambda: asked.append(1) or numA, print, lib=libA)
              and len(asked) == 1)
    finally:
        kitmaker.plan = real_plan
    # B376: the crest is read only when its file is not the one the stamp names (683 MB of
    # _FL26Megapack's crests at every Switch on); a crest put in its place is read and drawn
    reads, real_md5 = [], lbservers._crest_md5
    lbservers._crest_md5 = lambda c, had="": reads.append(real_md5(c, had)[1] != had) or real_md5(c, had)
    try:
        n = len(drawn)
        check("crest file as the stamp names it: kept, not read",
              not lbservers._made(71582, words, "", crest, dstE, numA, print, lib=libA)
              and len(drawn) == n and reads == [False])
        st = os.stat(crest)
        with open(crest, "wb") as f:
            f.write(b"PNG a crest put in its place")
        check("another crest put in its place: drawn at a Switch on",
              lbservers._made(71582, words, "", crest, dstE, numA, print, lib=libA) and len(drawn) == n + 1)
        os.utime(crest, ns=(st.st_atime_ns, st.st_mtime_ns))
        check("... its file times changed, the same picture: read again and kept",
              not lbservers._made(71582, words, "", crest, dstE, numA, print, lib=libA) and len(drawn) == n + 1)
    finally:
        lbservers._crest_md5 = real_md5
    # mato 09.11. (jibibi: 27 minutes for a Build): a Build keeping a kit drawn from the same of
    # everything works out no stamp (each read the crest whole: 4345 just written ones, a minute)
    stamp = os.path.join(dstE, "kitmaker.txt")
    lines = open(stamp, encoding="utf-8").read().split()
    with open(stamp, "w", encoding="utf-8") as f:            # a stamp of 08.11.: three lines
        f.write("\n".join(lines[:3]) + "\n")
    os.utime(stamp, ns=(10 ** 18, 10 ** 18))
    n = len(drawn)
    check("a Build, an old stamp of three lines: kept",
          not lbservers._made(71582, words, "", crest, dstE, numA, print, lib=libA, redraw=True)
          and len(drawn) == n)
    check("... it gets the fourth line, its time as it was (B166, coldstart)",
          open(stamp, encoding="utf-8").read().split()[:2] == lines[:2]
          and len(open(stamp, encoding="utf-8").read().split()) == 4 and os.stat(stamp).st_mtime_ns == 10 ** 18)
    stamps, real_stamps = [], lbservers._stamps
    lbservers._stamps = lambda *a, **k: stamps.append(1) or real_stamps(*a, **k)
    try:
        check("a Build again: kept, no stamp worked out",
              not lbservers._made(71582, words, "", crest, dstE, numA, print, lib=libA, redraw=True)
              and len(drawn) == n and not stamps)
        numO = os.path.join(libA, "Other", "Kit")
        check("... another numbers kit: worked out, drawn",
              lbservers._made(71582, words, "", crest, dstE, numO, print, lib=libA, redraw=True)
              and len(drawn) == n + 1 and stamps)
        with open(crest, "wb") as f:
            f.write(b"PNG a crest the Build wrote again")
        check("... a crest changed: drawn",
              lbservers._made(71582, words, "", crest, dstE, numO, print, lib=libA, redraw=True)
              and len(drawn) == n + 2)
    finally:
        lbservers._stamps = real_stamps
    # the crests a Build just hashed (write_manifest) are not read again for the kits' check
    with open(crest, "wb") as f:
        f.write(b"PNG a crest the Build wrote again")       # the same picture, a new file time
    st = os.stat(crest)
    lbservers.CREST_MD5[os.path.normcase(os.path.abspath(crest))] = \
        (st.st_size, st.st_mtime_ns, hashlib.md5(b"PNG a crest the Build wrote again").hexdigest())
    real_open, opened = open, []

    def spy_open(p, *a, **k):
        if os.path.normcase(os.path.abspath(str(p))) == os.path.normcase(os.path.abspath(crest)):
            opened.append(p)
        return real_open(p, *a, **k)
    lbservers.open = spy_open
    try:
        check("a crest the Build hashed: kept without reading it",
              not lbservers._made(71582, words, "", crest, dstE, numO, print, lib=libA, redraw=True)
              and len(drawn) == n + 2 and not opened)
    finally:
        del lbservers.open
        lbservers.CREST_MD5.clear()
    # kitmaker-index.json (09.11.: 4345 stamps opened, 6 ms each with the virus scan): a stamp
    # whose file is as it was read is not opened again, one changed is
    index = os.path.join(libA, "_W", lbservers.INDEX)
    lbservers._read_stamp(stamp)
    lbservers._save_index(index)
    lbservers._load_index(index)
    lbservers.open, opened = spy_open, []
    crest_was, crest = crest, stamp            # spy_open counts opens of `crest`: the stamp now
    try:
        lines = lbservers._read_stamp(stamp)
        check("a stamp as the index has it: not opened", not opened and lines[0] == open(stamp).read().split()[0])
        with open(stamp, "a", encoding="utf-8") as f:
            f.write("x\n")
        check("a stamp changed since: read again", lbservers._read_stamp(stamp) and len(opened) == 1)
    finally:
        del lbservers.open
        crest = crest_was
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print("test_kit_stamps: %d ok" % ok)
