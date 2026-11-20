"""python mkkitnumbers.py <BebasNeue-Regular.ttf>   -> tools/kitnumbers_data.py

The numbers and the name letters Mod Studio gives a kit it draws when no kit of the player's
library lends them (kitnumbers.py), as three masks: the back numbers, the leg numbers (the same
picture) and the name font. A developer's tool, not in the package: the package carries the
masks alone.

The font is Bebas Neue (Dharma Type, SIL Open Font License 1.1 -- the licence lets pictures made
with the font go anywhere). Where each glyph stands is the game's own: measured on 65 real kits
of a kit library (13.11.2026), every one of them has its digits and letters on these centres.
"""
import base64, io, os, sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
# back / leg numbers, 2048 x 256: the centre of each digit, the box a digit may fill
DIGIT_X = (80, 250, 420, 620, 820, 1020, 1220, 1420, 1620, 1820)
DIGIT_W, ONE_W, DIGIT_Y = 112, 62, (14, 240)
# name font, 2048 x 512, two rows: A..N and O..Z with the full stop
NAME_X = ((89, 247, 400, 558, 706, 835, 976, 1126, 1240, 1348, 1484, 1624, 1783, 1951),
          (89, 247, 408, 577, 728, 881, 1032, 1192, 1377, 1552, 1712, 1872, 1986))
NAME_ROWS = ("ABCDEFGHIJKLMN", "OPQRSTUVWXYZ.")
NAME_Y = ((36, 220), (292, 476))
LETTER_W, WIDE = 92, {"M": 118, "W": 140, "I": 30, ".": 30}


def glyph(font, ch, w, h):
    """the glyph ch as an L picture of exactly its ink, at most w wide and h high: scaled to the
    height, pressed narrower when it is wider than w"""
    big = Image.new("L", (1600, 1600), 0)
    ImageDraw.Draw(big).text((200, 200), ch, font=font, fill=255)
    box = big.getbbox()
    im = big.crop(box)
    if ch == ".":
        s = min(w, h // 6)
        return im.resize((s, s), Image.LANCZOS)
    nw = min(w, max(1, round(im.width * h / im.height)))
    return im.resize((nw, h), Image.LANCZOS)


def numbers(font):
    im = Image.new("L", (2048, 256), 0)
    for i, cx in enumerate(DIGIT_X):
        g = glyph(font, str(i), ONE_W if i == 1 else DIGIT_W, DIGIT_Y[1] - DIGIT_Y[0])
        im.paste(g, (cx - g.width // 2, DIGIT_Y[0]))
    return im


def names(font):
    im = Image.new("L", (2048, 512), 0)
    for row, text in enumerate(NAME_ROWS):
        y0, y1 = NAME_Y[row]
        for cx, ch in zip(NAME_X[row], text):
            g = glyph(font, ch, WIDE.get(ch, LETTER_W), y1 - y0)
            im.paste(g, (cx - g.width // 2, y1 - g.height))
    return im


def b64(im):
    b = io.BytesIO()
    im.save(b, "PNG", optimize=True)
    return base64.b64encode(b.getvalue()).decode("ascii")


def main(argv):
    if len(argv) != 1:
        print(__doc__)
        return 1
    font = ImageFont.truetype(argv[0], 1000)
    out = ['"""the masks of kitnumbers.py, written by mkkitnumbers.py -- not edited by hand.',
           "Glyphs: Bebas Neue, (c) 2010 Dharma Type, SIL Open Font License 1.1.\"\"\"", ""]
    for name, im in (("NUMBERS", numbers(font)), ("NAMES", names(font))):
        s = b64(im)
        out.append("%s = (" % name)
        out += ['    "%s"' % s[i:i + 100] for i in range(0, len(s), 100)]
        out.append(")")
    open(os.path.join(HERE, "kitnumbers_data.py"), "w", encoding="ascii", newline="\n").write("\n".join(out) + "\n")
    print("wrote kitnumbers_data.py (%d bytes)" % os.path.getsize(os.path.join(HERE, "kitnumbers_data.py")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
