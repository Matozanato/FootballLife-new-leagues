"""python tools/test_kitpics.py

Tests for tools/kitpics.py (a kit-server club folder from kit pictures) and the picture branch
of modstudio/pages/kits.py's place. Builds pictures and a fake library kit under
tempfile.mkdtemp(); needs Pillow. Plain asserts, one "ok" line each.
"""
import os, shutil, struct, sys, tempfile, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kitpics as K
from PIL import Image, ImageDraw

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def picture(path, colour, size=1024):
    im = Image.new("RGB", (size, size), colour)
    ImageDraw.Draw(im).rectangle((size // 8, size // 8, size // 3, size // 3), fill=(0, 0, 90))
    im.save(path)


def unpack(ftex):
    """the pixel data of an .ftex, back out of its chunks"""
    off, unc, _comp, _i, _f, n = struct.unpack_from("<IIIBBH", ftex, 0x40)
    out = b""
    for i in range(n):
        cs, us, o = struct.unpack_from("<HHI", ftex, off + 8 * i)
        out += zlib.decompress(ftex[off + o:off + o + cs])
    return unc, out


def main():
    t = tempfile.mkdtemp()
    try:
        club = os.path.join(t, "pics", "Test Club")
        os.makedirs(club)
        picture(os.path.join(club, "p1.png"), (200, 20, 20))
        picture(os.path.join(club, "P2.PNG"), (250, 250, 250))
        picture(os.path.join(club, "g1.jpg"), (30, 160, 30))
        open(os.path.join(club, "notes.txt"), "w").write("x")
        pics = K.pictures(club)
        ok("pictures: p1, p2 (any case) and g1, nothing else", sorted(pics) == ["g1", "p1", "p2"])
        ok("pictures: a folder without pictures is {}", K.pictures(os.path.join(t, "pics")) == {})

        dds = K.dds_bytes(pics["p1"])
        ok("dds_bytes: a 2048 DXT5 DDS", dds[:4] == b"DDS " and dds[84:88] == b"DXT5"
           and len(dds) == 128 + 2048 * 2048)
        f = K.dds_to_ftex(dds)
        ok("ftex: header the game reads (FTEX 2.03, 2048 x 2048, one mip)",
           f[:4] == b"FTEX" and f[4:8] == bytes.fromhex("85EB0140")
           and struct.unpack_from("<HHHH", f, 8) == (4, 2048, 2048, 1) and f[16] == 1)
        unc, data = unpack(f)
        ok("ftex: the chunks give the DDS pixels back", unc == len(data) and data == dds[128:])
        try:
            K.dds_to_ftex(b"PNG.....")
            ok("ftex: refuses what is not a DDS", False)
        except ValueError:
            ok("ftex: refuses what is not a DDS", True)
        ok("colours: the shirt colour first", K.colours(pics["p1"])[0] == "#c81414")

        # a library kit to lend numbers: p1 and g1 with config and the three number files
        lend = os.path.join(t, "lib", "League", "Donor")
        for v in ("p1", "g1"):
            os.makedirs(os.path.join(lend, v))
            open(os.path.join(lend, v, "config.txt"), "w").write(
                "Collar=7   ; 1 to 130\nKitFile=u0101%s\nKitFile_srm=u0101%s_srm\nBackNumbersFile=u0101%s_back\n"
                "ChestNumbersFile=\nLegNumbersFile=u0101%s_leg\nNameFontFile=u0101%s_name\n"
                "ShirtColor1=#000000\n" % ((v,) * 5))
            for s in K.NUMBER_FILES:
                open(os.path.join(lend, v, "u0101%s%s.ftex" % (v, s)), "wb").write(v.encode() + s.encode())
        open(os.path.join(lend, "order.ini"), "w").write("p1\n")

        out = os.path.join(t, "out", "Test Club")
        done = K.make_kit(pics, 72001, out, lend)
        ok("make_kit: outfield kits first, then the goalkeeper's", done == ["p1", "p2", "g1"])
        ok("make_kit: order.ini and gk_order.ini",
           open(os.path.join(out, "order.ini")).read() == "p1\np2\n"
           and open(os.path.join(out, "gk_order.ini")).read() == "g1\n")
        names = sorted(os.listdir(os.path.join(out, "p2")))
        ok("make_kit: kit, number files and config named for the club",
           names == ["config.txt", "u72001p2.ftex", "u72001p2_back.ftex", "u72001p2_leg.ftex", "u72001p2_name.ftex"])
        ok("make_kit: p2 borrows the donor's p1 numbers, g1 its g1",
           open(os.path.join(out, "p2", "u72001p2_back.ftex"), "rb").read() == b"p1_back"
           and open(os.path.join(out, "g1", "u72001g1_leg.ftex"), "rb").read() == b"g1_leg")
        cfg = open(os.path.join(out, "p1", "config.txt")).read()
        ok("config: the donor's values kept, texture names and colour ours, no _srm line",
           "Collar=7   ; 1 to 130" in cfg and "KitFile=u72001p1\n" in cfg and "_srm" not in cfg
           and "BackNumbersFile=u72001p1_back" in cfg and "ShirtColor1=#c81414" in cfg)

        # B214: numbers that stand out from the shirt. Three library kits with real number
        # textures: dark blue (the first by name, as Aarhus), grey, white
        def numbers_kit(name, colour):
            d = os.path.join(t, "lib14", "League", name, "p1")
            os.makedirs(d)
            open(os.path.join(d, "config.txt"), "w").write("BackNumbersFile=x_back\n")
            im = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
            ImageDraw.Draw(im).rectangle((40, 40, 200, 200), fill=colour + (255,))
            png = os.path.join(t, name + ".png")
            im.save(png)
            f = K.dds_to_ftex(K.dds_bytes(png))
            for s in K.NUMBER_FILES:
                open(os.path.join(d, "u1p1%s.ftex" % s), "wb").write(f + name.encode())
            return os.path.dirname(d)
        dark = numbers_kit("A Dark", (8, 32, 60))
        grey = numbers_kit("B Grey", (90, 90, 90))
        light = numbers_kit("C Light", (250, 250, 250))
        c = K.ink(os.path.join(dark, "p1"))
        ok("ftex_image/ink: the colour of the numbers read back off the .ftex",
           c is not None and all(abs(a - b) <= 8 for a, b in zip(c, (8, 32, 60))))
        ok("ink: a file that is not an .ftex is None", K.ink(os.path.join(lend, "p1")) is None)
        ok("contrast: black on white 21, a colour on itself 1",
           round(K.contrast("#000000", "#ffffff")) == 21 and K.contrast((9, 9, 9), "#090909") == 1)
        ok("pick_numbers: a dark shirt gets the light numbers",
           K.pick_numbers([dark, light], "p1", "#08203c") == light)
        ok("pick_numbers: a light shirt keeps the first ones",
           K.pick_numbers([dark, light], "p1", "#e3e3e3") == dark)
        ok("pick_numbers: one kit, a folder or none",
           K.pick_numbers([dark], "p1", "#08203c") == dark and K.pick_numbers(dark, "p2", "#000000") == dark
           and K.pick_numbers([], "p1", "#000000") is None)
        navy = os.path.join(t, "pics", "Navy")
        os.makedirs(navy)
        picture(os.path.join(navy, "p1.png"), (8, 32, 60))
        out14 = os.path.join(t, "out", "Navy")
        K.make_kit(K.pictures(navy), 72005, out14, [dark, light])
        ok("make_kit: a navy shirt wears the white numbers",
           open(os.path.join(out14, "p1", "u72005p1_back.ftex"), "rb").read().endswith(b"C Light"))
        import lbservers
        lib14 = os.path.join(t, "lib14")
        ok("numbers_kits: the first by name, then a light and a dark one (the first is dark already)",
           lbservers.numbers_kits(lib14, "Ours") == [dark, light])
        ok("numbers_kits: an empty library lends none", lbservers.numbers_kits(os.path.join(t, "pics"), "x") == [])

        bare = os.path.join(t, "out", "Bare")
        K.make_kit({"p1": pics["p1"]}, 72002, bare)
        cfg = open(os.path.join(bare, "p1", "config.txt")).read()
        ok("make_kit without a donor: default config, no number files named",
           "KitFile=u72002p1" in cfg and "BackNumbersFile=\n" in cfg
           and sorted(os.listdir(os.path.join(bare, "p1"))) == ["config.txt", "u72002p1.ftex"])

        # kits.py: place() makes a picture folder into a kit; is_kit_folder() finds it
        try:
            from modstudio.pages import kits as P
        except Exception as e:
            print("skip kits.py cases: %s: %s" % (type(e).__name__, e))
        else:
            ok("kits.is_kit_folder: a picture folder counts", P.is_kit_folder(club))
            lib = os.path.join(t, "lib")
            rel = P.place(club, lib, os.path.join("Imported", "Test Club"), 72003, lend)
            ok("kits.place: pictures become a kit in the library",
               rel == os.path.join("Imported", "Test Club")
               and os.path.isfile(os.path.join(lib, rel, "p1", "u72003p1.ftex")))
            rel2 = P.place(club, lib, os.path.join("Imported", "Test Club"), 72003, lend)
            ok("kits.place: a second time goes next to it", rel2 == os.path.join("Imported", "Test Club (2)"))
            ok("kits.number_kits: the donor kit is offered for numbers",
               lend in P.number_kits(lib))
    finally:
        shutil.rmtree(t, ignore_errors=True)
    print("%d cases passed" % N)


if __name__ == "__main__":
    main()
