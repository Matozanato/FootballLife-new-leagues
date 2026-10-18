"""python tools/test_kit_crest.py

B138 (dolokhov 18.10.): the small crest on the shorts of a kit Mod Studio draws stood sideways in
the game.  The shorts lie on their side in the kit texture (the hem at the texture's outer edge,
as in the kit makers' templates, whose shorts logo on the right leg is turned a quarter
anticlockwise); on the left leg the shorts' top points right, so the crest is turned a quarter
clockwise there.  The chest crest stays as it is.

A crest that is an arrow pointing to its own top (a bar on its left) is drawn on a kit; the
test finds where the arrow's tip and the bar land.  Needs Pillow.
"""
import os, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kitmaker
from PIL import Image, ImageDraw

N = 0
ARROW, BAR = (255, 0, 255), (0, 255, 255)        # the arrow and the bar: colours no kit wears


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def arrow(path):
    im = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(100, 0), (190, 90), (130, 90), (130, 200), (70, 200), (70, 90), (10, 90)], fill=ARROW + (255,))
    d.rectangle((0, 120, 40, 200), fill=BAR + (255,))
    im.save(path)


def near(p, c, tol=40):
    return all(abs(a - b) <= tol for a, b in zip(p, c))


def where(img, centre, half, colour):
    """the bounding box of `colour` in the square of side 2*half around centre"""
    x0, y0 = centre[0] - half, centre[1] - half
    box = img.crop((x0, y0, x0 + 2 * half, y0 + 2 * half))
    xs, ys = [], []
    for y in range(box.height):
        for x in range(box.width):
            if near(box.getpixel((x, y)), colour):
                xs.append(x0 + x)
                ys.append(y0 + y)
    return (min(xs), min(ys), max(xs), max(ys)) if xs else None


def tip(img, centre, half):
    """the side the arrow points to: the narrowest end of the arrow, along the longer axis"""
    b = where(img, centre, half, ARROW)
    x0, y0, x1, y1 = b
    def run(line):
        return sum(1 for p in line if near(p, ARROW))
    if x1 - x0 >= y1 - y0:                      # lying: compare its left and right ends
        left = run(img.getpixel((x0 + 2, y)) for y in range(y0, y1 + 1))
        right = run(img.getpixel((x1 - 2, y)) for y in range(y0, y1 + 1))
        return "right" if right < left else "left"
    top = run(img.getpixel((x, y0 + 2)) for x in range(x0, x1 + 1))
    bottom = run(img.getpixel((x, y1 - 2)) for x in range(x0, x1 + 1))
    return "up" if top < bottom else "down"


def main():
    tmp = tempfile.mkdtemp(prefix="fl26crest")
    try:
        crest = os.path.join(tmp, "crest.png")
        arrow(crest)
        got = kitmaker.pictures(os.path.join(tmp, "kit"), "plain #1d8f3a #ffffff #ffffff #101010", None, crest)
        img = Image.open(got["p1"]).convert("RGB")
        (sx, sy), ssize = kitmaker.SHORTS_CREST
        shorts, _cuffs = kitmaker.masks()
        ok("the shorts crest sits on the left leg of the shorts", shorts.getpixel((sx, sy)) == 255
           and sx < kitmaker.N // 2)

        cb = where(img, kitmaker.CHEST, kitmaker.CREST, ARROW)
        ok("the chest crest is drawn", cb is not None)
        ok("the chest crest stands upright (its top up, as the shirt's front)",
           tip(img, kitmaker.CHEST, kitmaker.CREST) == "up")
        rb = where(img, kitmaker.CHEST, kitmaker.CREST, BAR)
        ok("the chest crest is not mirrored (its left side on the left)", rb and rb[0] < (cb[0] + cb[2]) / 2)

        sb = where(img, (sx, sy), ssize, ARROW)
        ok("the shorts crest is drawn, %d pixels at most" % ssize,
           sb is not None and max(sb[2] - sb[0], sb[3] - sb[1]) + 1 <= ssize)
        ok("the shorts crest is turned a quarter clockwise: its top points right, away from the hem",
           tip(img, (sx, sy), ssize) == "right")
        rb = where(img, (sx, sy), ssize, BAR)
        ok("... and is not mirrored: its left side is at the top", rb and rb[3] < (sb[1] + sb[3]) / 2)

        # every kit of the club gets the same: the away, third and goalkeeper's
        for var in ("p2", "p3", "g1"):
            im = Image.open(got[var]).convert("RGB")
            ok("%s: shorts crest top right, chest crest up" % var,
               tip(im, (sx, sy), ssize) == "right" and tip(im, kitmaker.CHEST, kitmaker.CREST) == "up")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("test_kit_crest: %d ok" % N)


if __name__ == "__main__":
    main()
