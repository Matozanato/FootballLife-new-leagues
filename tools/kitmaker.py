r"""kitmaker.py -- kit pictures for a club from its colours and crest (0.2.1)

A kit picture is the game's 2048 x 2048 kit texture: the shirt's back (upside down) at the top of
the middle column, its front below it, the sleeves left and right at the top, the shorts left and
right at the bottom.  Where the shorts and the sleeve cuffs are comes from modstudio\assets\
kitmask.png (shorts 1, cuffs 2), read off Xxspedd's kit template; everything else is shirt.

The colours and pattern are a shirt in words, the way NewLife and shieldcrest write it:

    "stripes #ffffff #0031a4 #0031a4"     pattern, body, second, trim [, shorts]

pattern is plain, stripes, hoops, halves, sleeves, centre or band; the shorts take the trim
colour.  The club's crest goes on the chest and, small, on the left leg of the shorts.

    p1 home, p2 away (no away words: the home colours swapped), p3 a third kit and g1 the
    goalkeeper's, plain, in colours the others do not wear

kitpics.make_kit turns the pictures into a kit-server folder.

    python kitmaker.py <out folder> "<home words>" ["<away words>"] [--crest <picture>]
"""
import os, re, sys

from PIL import Image, ImageDraw

N = 2048
MASK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modstudio", "assets", "kitmask.png")
# the middle column (the shirt's front and back) and where they end, in texture pixels
COL = (650, 1330)
BACK_HEM, FRONT_TOP, FRONT_HEM = 0, 1180, 1805
CHEST = (1178, 1180)                     # the crest's centre: the wearer's left chest
CREST = 112                              # 175 looked twice too big on the shirt (in game, 07.10.)
SHORTS_CREST = ((125, 1690), 62)
PATTERNS = ("plain", "stripes", "hoops", "halves", "sleeves", "centre", "band")
# colours a third or a goalkeeper's kit is picked from: the one furthest from the club's other kits
PALETTE = ("#ffffff", "#101010", "#f5d000", "#8a8f96", "#14285a", "#c8102e", "#1d8f3a", "#ff7a00",
           "#6a2c91", "#7fd3f0", "#f28cb1")
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
_masks = None


def rgb(h):
    return tuple(int(h[k:k + 2], 16) for k in (1, 3, 5))


def words(kit):
    """a shirt in words, checked and filled out to pattern + 3 colours (+ shorts), or None"""
    p = (kit or "").split()
    if not p:
        return None
    if HEX.match(p[0]):
        p = ["plain"] + p
    cols = [c for c in p[1:] if HEX.match(c)]
    if p[0] not in PATTERNS or not cols:
        return None
    while len(cols) < 3:
        cols.append(cols[-1])
    return " ".join([p[0]] + cols[:4])


def masks():
    """(shorts, cuffs) as "L" masks of the texture"""
    global _masks
    if _masks is None:
        m = Image.open(MASK)
        idx = Image.frombytes("L", m.size, m.tobytes())       # the palette indices themselves
        _masks = tuple(idx.point(lambda v, n=n: 255 if v == n else 0) for n in (1, 2))
    return _masks


def draw(kit):
    shorts, cuff = masks()
    pat, *cols = kit.split()
    body, second, trim = (rgb(c) for c in cols[:3])
    shorts_c = rgb(cols[3]) if len(cols) > 3 else None       # a fourth colour: the shorts'
    img = Image.new("RGB", (N, N), body)
    d = ImageDraw.Draw(img)
    x0, x1 = COL
    c = (x0 + x1) // 2
    back_end = FRONT_TOP - 540                               # the back is above this, the front below FRONT_TOP

    def box(a, b, top, bottom):                              # pixels a <= x < b, top <= y < bottom
        if b > a and bottom > top:
            d.rectangle((a, top, b - 1, bottom - 1), fill=second)
    if pat == "stripes":
        w = (x1 - x0) / 7
        for i in range(1, 7, 2):
            box(x0 + int(-(-i * w // 1)), x0 + int(-(-(i + 1) * w // 1)), 0, N)
    elif pat == "hoops":
        for y in range(N):
            dy = FRONT_HEM - y if y >= FRONT_TOP - 270 else y - BACK_HEM
            if (dy // 105) % 2 == 1:
                box(0, N, y, y + 1)
    elif pat == "halves":
        box(c, x1, FRONT_TOP, N)
        box(x0, c, 0, back_end)
        box(c, x1, back_end, FRONT_TOP)
    elif pat == "sleeves":
        box(0, x0, 0, N)
        box(x1, N, 0, N)
    elif pat == "centre":
        box(c - 94, c + 95, 0, N)
    elif pat == "band":
        box(x0, x1, 1301, 1420)
        box(x0, x1, 386, 505)
    img.paste(shorts_c or (trim if trim != body or pat != "plain" else second), (0, 0), shorts)
    img.paste(trim if trim != body else second, (0, 0), cuff)
    d.rectangle((0, 0, 490, 122), fill=second)               # the captain's armband
    return img


def paste_crest(img, crest):
    """the crest picture on the chest and the shorts; a crest that cannot be read is left out"""
    try:
        cr = Image.open(crest).convert("RGBA")
    except (OSError, ValueError):
        return
    # cut the empty border and scale to the size both ways, so a small crest is as big as a big one
    c0 = cr.crop(cr.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox() or (0, 0) + cr.size)
    for (x, y), size in ((CHEST, CREST), SHORTS_CREST):
        k = size / max(c0.size)
        c = c0.resize((max(1, round(c0.width * k)), max(1, round(c0.height * k))), Image.LANCZOS)
        img.paste(c, (x - c.width // 2, y - c.height // 2), c)


def dist(a, b):
    a, b = rgb(a), rgb(b)
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def far_colour(avoid):
    return max(PALETTE, key=lambda c: min(dist(c, x) for x in avoid))


def away_of(home):
    """the away shirt of a club with none: the home colours swapped"""
    h = home.split()
    return " ".join([h[0], h[2], h[1], h[1]])


def extra_kits(home, away):
    """(third, goalkeeper) in words: plain, in colours none of the other kits wear"""
    h, a = home.split(), away.split()
    worn = h[1:4] + a[1:4]
    # a colour of the club no shirt is made of yet, else the palette's furthest
    own = [c for c in (h[2], h[3], a[2], a[3]) if min(dist(c, h[1]), dist(c, a[1])) > 90]
    third = own[0] if own else far_colour(worn)
    trim3 = max((h[1], h[2]), key=lambda c: dist(c, third))         # the club's own colour on it
    gk = far_colour(worn + [third, "#00a000"])                       # never the pitch's green
    trimg = max(("#101010", "#ffffff"), key=lambda c: dist(c, gk))
    return "plain %s %s %s" % (third, trim3, trim3), "plain %s %s %s %s" % (gk, trimg, trimg, gk)


def crest_kit(crest):
    """a plain shirt in the crest's two commonest colours (transparent and near-white edges aside)"""
    try:
        im = Image.open(crest).convert("RGBA")
    except (OSError, ValueError):
        return None
    im.thumbnail((128, 128))
    px = [p[:3] for p in im.getdata() if p[3] > 200]
    if not px:
        return None
    q = Image.new("RGB", (len(px), 1))
    q.putdata(px)
    q = q.quantize(colors=6)
    pal = q.getpalette()
    cols = ["#%02x%02x%02x" % tuple(pal[3 * i:3 * i + 3]) for _n, i in sorted(q.getcolors(), reverse=True)]
    body = cols[0]
    second = next((c for c in cols[1:] if dist(c, body) > 90), "#ffffff" if dist(body, "#ffffff") > 90 else "#101010")
    return "plain %s %s %s" % (body, second, second)


def pictures(out, home, away=None, crest=None):
    """p1, p2, p3, g1 .png of a club into out; -> {var: path}, or {} when home is no shirt"""
    home = words(home)
    if not home:
        return {}
    away = words(away) or away_of(home)
    third, gk = extra_kits(home, away)
    os.makedirs(out, exist_ok=True)
    done = {}
    for var, kit in (("p1", home), ("p2", away), ("p3", third), ("g1", gk)):
        img = draw(kit)
        if crest:
            paste_crest(img, crest)
        done[var] = os.path.join(out, var + ".png")
        img.save(done[var])
    return done


def main(argv):
    crest = None
    if "--crest" in argv:
        i = argv.index("--crest")
        crest = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    if len(argv) < 2:
        print(__doc__)
        return 2
    got = pictures(argv[0], argv[1], argv[2] if len(argv) > 2 else None, crest)
    print("\n".join(got.values()) if got else "not a shirt: %s" % argv[1])
    return 0 if got else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
