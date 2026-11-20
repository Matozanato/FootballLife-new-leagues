"""python mkarrows.py -- the small arrows of the combo boxes and the number boxes
(modstudio/assets/arrow-*.png, spin-*.png), each at the size it is shown in and at twice that.

Until beta 3 they were filled triangles of 20 x 16 hard pixels that Qt shrank to 10 x 8 and 8 x 6
on the way to the screen: steps on every edge (mato 11.11.: "rezoluciju popraviti malo"). Now an
angle of two smooth lines, like Back and Forward (modstudio/icons.py), drawn eight times as large
and brought down once, so a 100 % screen gets a picture made for it and a 125-200 % screen the
@2x one (Qt picks it by its name)."""
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "modstudio", "assets")
MUTED, HOT = (135, 146, 162), (74, 163, 255)
K = 8


def angle(w, h, up, colour, line):
    """a w x h picture of an angle that points down (or up), its line `line` pixels thick"""
    W, H = w * K, h * K
    im = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(im)
    t = line * K
    mx = t / 2.0 + K * 0.5                       # the ends stay inside the picture
    top, bottom = H * 0.24, H * 0.76
    if up:
        top, bottom = bottom, top
    pts = [(mx, top), (W / 2.0, bottom), (W - mx, top)]
    d.line(pts, fill=255, width=int(round(t)), joint="curve")
    r = t / 2.0
    for x, y in pts:                             # round ends and a round point
        d.ellipse((x - r, y - r, x + r, y + r), fill=255)
    a = im.resize((w, h), Image.LANCZOS)
    out = Image.new("RGBA", (w, h), colour + (0,))
    out.putalpha(a)
    return out


def main():
    made = []
    for name, w, h, up, colour in (("arrow-down", 10, 8, False, MUTED), ("arrow-down-hot", 10, 8, False, HOT),
                                   ("arrow-up", 10, 8, True, MUTED),
                                   ("spin-down", 8, 6, False, MUTED), ("spin-up", 8, 6, True, MUTED)):
        for k, tail in ((1, ""), (2, "@2x")):
            p = os.path.join(OUT, name + tail + ".png")
            angle(w * k, h * k, up, colour, (1.5 if w >= 10 else 1.3) * k).save(p)
            made.append(os.path.basename(p))
    print("made", ", ".join(made))


if __name__ == "__main__":
    main()
