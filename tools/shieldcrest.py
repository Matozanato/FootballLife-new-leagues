"""A club crest drawn from the club's shirt: a shield in the shirt's colours and pattern with
the club's short name across it.

The shirt is described in words, the way NewLife's clubs.csv carries it (home_kit):

    "<pattern> <body> <second> <trim>"     e.g. "stripes #ffffff #0052d5 #ffffff"

pattern: plain, stripes, hoops, halves, sleeves, band, centre. Everything is drawn here (no
picture of anyone else's), so a new club gets a crest that looks like its colours until the
modder gives it a real one.

    python shieldcrest.py "hoops #ffffff #39ac52 #207b31" CEL out.png
"""
import sys

from PIL import Image, ImageDraw, ImageFont

FONT = r"C:\Windows\Fonts\arialbd.ttf"
PATTERNS = ("plain", "stripes", "hoops", "halves", "sleeves", "band", "centre")


def parse(kit):
    """(pattern, body, second, trim) as RGB tuples, or None for a description it cannot read"""
    try:
        pat, *cols = kit.split()
        rgb = [tuple(int(c[k:k + 2], 16) for k in (1, 3, 5)) for c in cols[:3]]
    except (AttributeError, ValueError):
        return None
    if len(rgb) != 3 or pat not in PATTERNS:
        return None
    return (pat,) + tuple(rgb)


def luma(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def far(a, b):
    return abs(luma(a) - luma(b)) > 60 or sum(abs(x - y) for x, y in zip(a, b)) > 180


def ink(c):
    """black or white, whichever reads on c"""
    return (20, 20, 20) if luma(c) > 150 else (250, 250, 250)


def outline(S, inset):
    """the shield's points on an S x S canvas, `inset` px inside the outer edge"""
    l, r, t = S * 0.12 + inset, S * 0.88 - inset, S * 0.07 + inset
    side = S * 0.46                          # where the straight sides turn to the point
    tip = S * 0.96 - inset * 2.2
    pts = [(l, t), (S / 2, t - S * 0.025), (r, t), (r, side)]
    n = 32
    for k in range(1, n + 1):                # right side bending in to the point
        u = k / float(n)
        pts.append((r - (r - S / 2) * u ** 2, side + (tip - side) * u))
    for k in range(n - 1, -1, -1):           # and back up the left side
        u = k / float(n)
        pts.append((l + (S / 2 - l) * u ** 2, side + (tip - side) * u))
    return pts


def field(S, pat, body, second):
    """the shirt's pattern over the whole canvas"""
    im = Image.new("RGB", (S, S), body)
    d = ImageDraw.Draw(im)
    if pat == "stripes":
        w = S / 9.0
        for k in range(1, 9, 2):
            d.rectangle([k * w, 0, (k + 1) * w, S], fill=second)
    elif pat == "hoops":
        h = S / 8.0
        for k in range(1, 8, 2):
            d.rectangle([0, k * h, S, (k + 1) * h], fill=second)
    elif pat == "halves":
        d.rectangle([S / 2, 0, S, S], fill=second)
    elif pat == "sleeves":
        d.rectangle([0, 0, S * 0.3, S], fill=second)
        d.rectangle([S * 0.7, 0, S, S], fill=second)
    elif pat == "band":
        d.rectangle([0, S * 0.24, S, S * 0.36], fill=second)
    elif pat == "centre":
        d.rectangle([S * 0.4, 0, S * 0.6, S], fill=second)
    return im


def shield(kit, label, size=512):
    """an RGBA size x size crest, or None when `kit` is no shirt description"""
    k = parse(kit) if isinstance(kit, str) else None
    if not k:
        return None
    pat, body, second, trim = k
    ss = 4
    S = size * ss
    edge = trim if far(trim, body) else (second if far(second, body) else ink(body))
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.polygon(outline(S, 0), fill=edge + (255,))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).polygon(outline(S, S * 0.035), fill=255)
    img.paste(field(S, pat, body, second), (0, 0), mask)
    # the short name on a scroll across the shield
    bar = edge
    y0, y1 = S * 0.47, S * 0.66
    d.rectangle([S * 0.05, y0, S * 0.95, y1], fill=bar + (255,))
    d.rectangle([S * 0.08, y0 + S * 0.018, S * 0.92, y1 - S * 0.018], fill=body + (255,)
                if far(body, bar) else ink(bar) + (255,))
    inside = body if far(body, bar) else ink(bar)
    text = ink(inside)
    try:
        font = ImageFont.truetype(FONT, int(S * 0.15))
    except OSError:
        font = ImageFont.load_default()
    tb = d.textbbox((0, 0), label, font=font)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    d.text(((S - tw) / 2 - tb[0], (y0 + y1) / 2 - th / 2 - tb[1]), label, font=font, fill=text + (255,))
    return img.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    im = shield(sys.argv[1], sys.argv[2])
    if im is None:
        sys.exit("not a shirt: %r" % sys.argv[1])
    im.save(sys.argv[3])
