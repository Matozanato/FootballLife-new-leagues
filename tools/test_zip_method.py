r"""python tools/test_zip_method.py

B386 (acoco75, ticket of 09.11.2026): Import your world on the zip of another pack looked through
every file and then said "That compression method is not supported". The zip was packed with
Deflate64 (Windows does that to a file past 2 GB), which Python's zipfile does not read.

Here: a zip whose one member names method 9 (a Deflate zip with the method field of its local and
central header changed -- Python cannot write Deflate64 either). installer.unpack says so before
it unpacks anything, in words that name the way out (unpack it, Choose a folder...), translated;
lbpackage.manifest / unpack give an Error and leave no half-unpacked folder. A normal zip goes
through as before. No game.
"""
import json, os, shutil, struct, sys, tempfile, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from modstudio import installer as I
from modstudio import i18n
import lbpackage as K

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def deflate64(path, member):
    """change the compression method of `member` from 8 (Deflate) to 9 (Deflate64) in both headers"""
    b = bytearray(open(path, "rb").read())
    name = member.encode("utf-8")
    n = 0
    i = b.find(b"PK\x03\x04")
    while i >= 0:                      # local header: method at +8, name at +30
        ln = struct.unpack_from("<H", b, i + 26)[0]
        if bytes(b[i + 30:i + 30 + ln]) == name:
            assert struct.unpack_from("<H", b, i + 8)[0] == 8
            struct.pack_into("<H", b, i + 8, 9)
            n += 1
        i = b.find(b"PK\x03\x04", i + 4)
    i = b.find(b"PK\x01\x02")
    while i >= 0:                      # central header: method at +10, name at +46
        ln = struct.unpack_from("<H", b, i + 28)[0]
        if bytes(b[i + 46:i + 46 + ln]) == name:
            assert struct.unpack_from("<H", b, i + 10)[0] == 8
            struct.pack_into("<H", b, i + 10, 9)
            n += 1
        i = b.find(b"PK\x01\x02", i + 4)
    assert n == 2, n
    open(path, "wb").write(b)


def main():
    d = tempfile.mkdtemp()
    try:
        big = "SiderAddons/livecpk/_FL26X/common/big.bin"
        z1 = os.path.join(d, "world.zip")
        with zipfile.ZipFile(z1, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("SiderAddons/livecpk/_FL26X/fl26world.txt", "world _FL26X\n" * 50)
            z.writestr(big, b"abc" * 5000)
        work = os.path.join(d, "w1")
        os.makedirs(work)
        ok("a normal zip unpacks as before", I.unpack(z1, work) == work
           and os.path.isfile(os.path.join(work, *big.split("/"))))
        with zipfile.ZipFile(z1) as z:
            ok("... and no method of it is called unreadable", I.zip_unreadable(z.infolist()) is None)

        deflate64(z1, big)
        with zipfile.ZipFile(z1) as z:
            ok("the member's method reads as 9", {m.filename: m.compress_type for m in z.infolist()}[big] == 9)
            ok("zip_unreadable names it", I.zip_unreadable(z.infolist()) == "Deflate64")
            try:
                z.read(big)
                ok("Python itself cannot read it (NotImplementedError)", False)
            except NotImplementedError:
                ok("Python itself cannot read it (NotImplementedError)", True)
        work = os.path.join(d, "w2")
        os.makedirs(work)
        try:
            I.unpack(z1, work)
            ok("unpack refuses the zip", False)
        except ValueError as e:
            ok("unpack refuses the zip with the way out in its words",
               "Deflate64" in str(e) and "Choose a folder..." in str(e) and "7-Zip" in str(e))
        ok("... before anything is unpacked", os.listdir(work) == [])

        # the words are in every language of the program, with the method's place kept
        en = I.zip_unreadable_text("%s")
        for code in ("hr", "es", "pt", "fr"):
            t = json.load(open(os.path.join(HERE, "modstudio", "lang", code + ".json"), encoding="utf-8"))["text"]
            ok("%s: translated, one %%s" % code, en in t and t[en] != en and t[en].count("%s") == 1)

        # a league package
        z2 = os.path.join(d, "pack.zip")
        with zipfile.ZipFile(z2, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("manifest.json", json.dumps({"format": K.FORMAT, "format_version": 1, "name": "x" * 400}))
        deflate64(z2, "manifest.json")
        try:
            K.manifest(z2)
            ok("a league package with an unreadable manifest is an Error", False)
        except K.Error as e:
            ok("a league package with an unreadable manifest is an Error that says what to do",
               "cannot read" in str(e) and "Deflate" in str(e) and "pack.zip" in str(e))
    finally:
        shutil.rmtree(d, ignore_errors=True)
    print("all %d passed" % N)


if __name__ == "__main__":
    main()
