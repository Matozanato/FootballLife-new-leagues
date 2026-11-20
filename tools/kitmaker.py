r"""kitmaker.py -- kit pictures for a club from its colours and crest (0.2.1)

A kit picture is the game's 2048 x 2048 kit texture: the shirt's back (upside down) at the top of
the middle column, its front below it, the sleeves left and right at the top, the shorts left and
right at the bottom.  Where the shorts and the sleeve cuffs are comes from modstudio\assets\
kitmask.png (shorts 1, cuffs 2), read off Xxspedd's kit template; everything else is shirt.

The colours and pattern are a shirt in words, the way NewLife and shieldcrest write it:

    "stripes #ffffff #0031a4 #0031a4"     pattern, body, second, trim [, shorts]

pattern is one of the library's (kitpatterns.py: stripes, hoops, halves, sashes, chevrons, checks,
fades, side panels ... and the seven names of before: plain, stripes, hoops, halves, sleeves,
centre, band); the shorts take the trim colour unless a fourth colour is given.  The club's
crest goes on the chest and, small, on the left leg of the shorts.

    p1 home, p2 away, p3 a third kit and g1 the goalkeeper's, picked by kitpatterns.plan: the
    club's own colours, a kit for every one of them in a pattern of the library, the three
    outfield kits and the goalkeeper's clearly apart in colour, the same for the same club every
    time (seed: its name)

kitpics.make_kit turns the pictures into a kit-server folder.

    python kitmaker.py <out folder> "<home words>" ["<away words>"] [--crest <picture>] [--seed <name>]
"""
import os, re, sys

from PIL import Image

import kitpatterns

N = 2048
MASK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modstudio", "assets", "kitmask.png")
# where the shirt's body, sleeves and collar are: kitpatterns.py
CHEST = (1178, 1180)                     # the crest's centre: the wearer's left chest
CREST = 112                              # 175 looked twice too big on the shirt (in game, 07.10.)
SHORTS_CREST = ((125, 1690), 62)
# the shorts lie on their side in the texture, the hem at the outer edge: on the left leg the
# shorts' top points right, so the crest is turned a quarter clockwise there (B138; kit makers'
# templates turn the logo on the right leg a quarter the other way, its top pointing left)
SHORTS_TURN = Image.Transpose.ROTATE_270
# the patterns a shirt in words may name: the library's, and the seven names of before
PATTERNS = tuple(kitpatterns.names()) + tuple(n for n in kitpatterns.ALIASES if n not in kitpatterns.BY_NAME)
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
    if not kitpatterns.known(p[0]) or not cols:
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
    """the kit picture of a shirt in words (kitpatterns.render)"""
    return kitpatterns.render(kit)


def paste_crest(img, crest):
    """the crest picture on the chest and the shorts; a crest that cannot be read is left out"""
    try:
        cr = Image.open(crest).convert("RGBA")
    except (OSError, ValueError):
        return
    # cut the empty border and scale to the size both ways, so a small crest is as big as a big one
    c0 = cr.crop(cr.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox() or (0, 0) + cr.size)
    for ((x, y), size), turn in (((CHEST, CREST), None), (SHORTS_CREST, SHORTS_TURN)):
        c1 = c0.transpose(turn) if turn is not None else c0
        k = size / max(c1.size)
        c = c1.resize((max(1, round(c1.width * k)), max(1, round(c1.height * k))), Image.LANCZOS)
        img.paste(c, (x - c.width // 2, y - c.height // 2), c)


def dist(a, b):
    a, b = rgb(a), rgb(b)
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


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


def plan(home, away=None, seed=None, third=None):
    """{"p1": home, "p2": away, "p3": third, "g1": goalkeeper} in words (kitpatterns.plan), {}
    when home is no shirt. third: the recipe's third kit in words (club_third_kits), or None"""
    home = words(home)
    if not home:
        return {}
    return kitpatterns.plan(home, words(away), seed, words(third) if third else None)


def pictures(out, home, away=None, crest=None, seed=None, third=None):
    """p1, p2, p3, g1 .png of a club into out; -> {var: path}, or {} when home is no shirt.
    seed: the club's name, so two clubs of the same colours get kits of their own; crest None:
    no crest on the kit"""
    kits = plan(home, away, seed, third)
    if not kits:
        return {}
    os.makedirs(out, exist_ok=True)
    done = {}
    for var in ("p1", "p2", "p3", "g1"):
        img = draw(kits[var])
        if crest:
            paste_crest(img, crest)
        done[var] = os.path.join(out, var + ".png")
        img.save(done[var])
    return done


def main(argv):
    opts = {}
    for flag in ("--crest", "--seed"):
        if flag in argv:
            i = argv.index(flag)
            opts[flag] = argv[i + 1]
            argv = argv[:i] + argv[i + 2:]
    if len(argv) < 2:
        print(__doc__)
        return 2
    got = pictures(argv[0], argv[1], argv[2] if len(argv) > 2 else None, opts.get("--crest"), opts.get("--seed"))
    print("\n".join(got.values()) if got else "not a shirt: %s" % argv[1])
    return 0 if got else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
