r"""kitpatterns.py -- the kit patterns Mod Studio draws for new clubs, and the three kits (and the
goalkeeper's) it picks for a club

A kit picture is the game's 2048 x 2048 kit texture (see kitmaker.py). The shirt's body is the
middle column, x 640..1408 around x = 1024: its back at the top, upside down (the hem at y = 0),
its front below, the hem at y = 1805. The sleeves are left and right of it, the shorts and the
cuffs come from kitmask.png, the collar is the strip at the bottom of the middle column.

A pattern is drawn on a "panel": the shirt's body as seen from the front, 768 pixels wide, its
rows counted from the hem up (v = 0 at the hem, the shoulders at v = 900). The front of the
texture is the panel as it is, the back the panel turned half round -- so a sash or a half goes
round the body the way it does on a real shirt. A pattern paints two masks on the panel, where
the second colour goes and where the trim colour goes; the rest is the body colour. It also says
which colour the sleeves, shorts, collar and cuffs wear.

A kit is described in words, the way NewLife and shieldcrest write it:

    "<pattern> <body> <second> <trim> [<shorts>]"      e.g. "sash-wide #ffffff #c8102e #101010"

The seven names of before (plain, stripes, hoops, halves, sleeves, centre, band) are patterns of
the library too, so the words of a NewLife club still read.

plan(home, away, seed) gives a club its kits -- p1 home, p2 away, p3 third, g1 goalkeeper --
the same every time for the same club (seed: its name):

  - home: the club's own words; a plain shirt gets a quiet pattern of the library in the same
    colours (piping, side panels, a yoke ...), so new clubs do not all look alike;
  - away: the club's own away words when they differ clearly from the home kit, else a kit in a
    light colour for a dark home shirt (or a dark one for a light shirt), in the club's colours
    where it can, any pattern of the library;
  - third: a third colour, clearly apart from both;
  - goalkeeper: a colour apart from all three and from the pitch.

"Clearly apart" is a CIEDE2000 difference of at least DISTINCT, both between the kits' main
colours and between their colours as seen from afar (all colours of the kit mixed by area).

    python kitpatterns.py <out folder> [<size>]     a front view of every pattern, p001.png ...
"""
import hashlib, math, os, sys

from PIL import Image, ImageChops, ImageDraw, ImageStat

N = 2048
TX0, TX1, CX = 640, 1408, 1024           # the body's column in the texture
PW = TX1 - TX0                           # the panel's width
VMAX, VMIN = 1200, -80                   # panel rows: v from VMAX (row 0) down to VMIN
PH = VMAX - VMIN + 1
FRONT_HEM, BACK_HEM = 1805, 0
SPLIT = 910                              # texture rows above this are the back, below the front
V_TOP = 900                              # the shoulders, in v
COLLAR = (671, 1888, 1376, 1960)         # the collar's strip in the texture
ARMBAND = (0, 0, 490, 122)
SLEEVES = ((0, 124, TX0, 1240), (TX1, 124, N, 1240))
VIEW_ROWS = (VMAX - V_TOP, VMAX)         # the panel rows seen from the front: shoulders to hem
DISTINCT = 22.0                          # CIEDE2000: kits of a club at least this far apart
INNER = 16.0                             # a kit's second colour at least this far from its body
PITCH = (47, 110, 50)

# colours a kit is picked from, besides the club's own
PALETTE = ("#ffffff", "#f2efe4", "#101010", "#3a3d42", "#8a8f96", "#c4c8cc", "#14285a", "#1f4fbf",
           "#7fc4ec", "#0f7c80", "#1fb5ac", "#0f5a32", "#1d8f3a", "#a8d63a", "#f5d000", "#c9a227",
           "#ff7a00", "#c8102e", "#6d1a2a", "#7a1f3d", "#f28cb1", "#c2185b", "#6a2c91", "#b39ddb",
           "#6b4226", "#d8c39a", "#9fe2bf", "#ff6f61")
GK_PALETTE = ("#a8d63a", "#ff7a00", "#f5d000", "#f28cb1", "#6a2c91", "#1fb5ac", "#101010",
              "#8a8f96", "#7fc4ec", "#ff6f61", "#c2185b", "#3a3d42", "#14285a", "#c4c8cc")


# ---------------------------------------------------------------------------------- colours

def rgb(h):
    return tuple(int(h[k:k + 2], 16) for k in (1, 3, 5))


def hexc(c):
    return "#%02x%02x%02x" % tuple(int(round(v)) for v in c)


def _lin(v):
    v /= 255.0
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def _unlin(v):
    v = v * 12.92 if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055
    return max(0.0, min(255.0, v * 255.0))


def lab(c):
    """CIE L*a*b* (D65) of an (r, g, b) or #rrggbb colour"""
    if isinstance(c, str):
        c = rgb(c)
    r, g, b = (_lin(v) for v in c)
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883

    def f(t):
        return t ** (1 / 3.0) if t > 0.008856 else 7.787 * t + 16 / 116.0
    fx, fy, fz = f(x), f(y), f(z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


_DE = {}


def de2000(c1, c2):
    """the CIEDE2000 colour difference of two colours ((r, g, b), #rrggbb or Lab triples); each
    pair worked out once (mato 09.11.: a Build's kit check of _FL26Megapack's 4345 kits asked 1.4
    million times, most of it the same few colours)"""
    try:
        return _DE[c1, c2]
    except KeyError:
        if len(_DE) > 1 << 18:
            _DE.clear()
        d = _DE[c1, c2] = _de2000(c1, c2)
        return d
    except TypeError:                     # a list: not kept
        return _de2000(c1, c2)


def _de2000(c1, c2):
    L1, a1, b1 = c1 if isinstance(c1, tuple) and len(c1) == 3 and isinstance(c1[0], float) else lab(c1)
    L2, a2, b2 = c2 if isinstance(c2, tuple) and len(c2) == 3 and isinstance(c2[0], float) else lab(c2)
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2)
    Cm = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cm ** 7 / (Cm ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360
    h2p = math.degrees(math.atan2(b2, a2p)) % 360
    dLp, dCp = L2 - L1, C2p - C1p
    if C1p * C2p == 0:
        dhp = 0
    elif abs(h2p - h1p) <= 180:
        dhp = h2p - h1p
    elif h2p - h1p > 180:
        dhp = h2p - h1p - 360
    else:
        dhp = h2p - h1p + 360
    dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp / 2))
    Lm, Cmp = (L1 + L2) / 2, (C1p + C2p) / 2
    if C1p * C2p == 0:
        hm = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hm = (h1p + h2p) / 2
    elif h1p + h2p < 360:
        hm = (h1p + h2p + 360) / 2
    else:
        hm = (h1p + h2p - 360) / 2
    T = (1 - 0.17 * math.cos(math.radians(hm - 30)) + 0.24 * math.cos(math.radians(2 * hm))
         + 0.32 * math.cos(math.radians(3 * hm + 6)) - 0.20 * math.cos(math.radians(4 * hm - 63)))
    dth = 30 * math.exp(-((hm - 275) / 25) ** 2)
    Rc = 2 * math.sqrt(Cmp ** 7 / (Cmp ** 7 + 25 ** 7))
    Sl = 1 + 0.015 * (Lm - 50) ** 2 / math.sqrt(20 + (Lm - 50) ** 2)
    Sc, Sh = 1 + 0.045 * Cmp, 1 + 0.015 * Cmp * T
    Rt = -math.sin(math.radians(2 * dth)) * Rc
    return math.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh))


def lightness(c):
    return lab(c)[0]


def mix(cols_weights):
    """the colour of colours mixed by area, as the eye sees a kit from afar (linear light)"""
    tot = sum(w for _c, w in cols_weights) or 1.0
    out = []
    for k in range(3):
        out.append(_unlin(sum(_lin(rgb(c)[k] if isinstance(c, str) else c[k]) * w for c, w in cols_weights) / tot))
    return tuple(out)


def toward(c, other, t):
    """c moved a fraction t of the way to other"""
    a, b = rgb(c), rgb(other)
    return hexc(tuple(x + (y - x) * t for x, y in zip(a, b)))


# ---------------------------------------------------------------------------------- the library

class Pattern:
    def __init__(self, name, desc, paint, family, sleeves="b", shorts="t", collar="t", cuffs="t", quiet=False):
        self.name, self.desc, self.paint, self.family = name, desc, paint, family
        self.sleeves, self.shorts, self.collar, self.cuffs, self.quiet = sleeves, shorts, collar, cuffs, quiet


LIBRARY = []                    # in the order the ids are given: only ever add at the end
BY_NAME = {}
ALIASES = {"stripes": "stripes-7", "hoops": "hoops-105", "halves": "halves", "sleeves": "contrast-sleeves",
           "centre": "centre-stripe", "band": "chest-band", "plain": "plain"}


def add(name, desc, paint, family, **kw):
    p = Pattern(name, desc, paint, family, **kw)
    LIBRARY.append(p)
    BY_NAME[name] = p
    return p


def get(name):
    return BY_NAME.get(ALIASES.get(name, name))


def known(name):
    return get(name) is not None


def names():
    return [p.name for p in LIBRARY]


def R(v):
    """the panel row of height v above the hem"""
    return VMAX - v


class Ctx:
    """the two masks a pattern paints: s (second colour) and t (trim colour), both "L"""

    def __init__(self, w=PW, h=PH):
        self.w, self.h = w, h
        self.ms = Image.new("L", (w, h), 0)
        self.mt = Image.new("L", (w, h), 0)
        self.S = ImageDraw.Draw(self.ms)
        self.T = ImageDraw.Draw(self.mt)

    def draw(self, which):
        return self.T if which == "t" else self.S

    def mask(self, which):
        return self.mt if which == "t" else self.ms

    def rect(self, x0, v0, x1, v1, which="s", fill=255):
        """x0 <= x < x1, v0 <= v < v1 (heights above the hem)"""
        if x1 > x0 and v1 > v0:
            self.draw(which).rectangle((x0, R(v1) + 1, x1 - 1, R(v0)), fill=fill)

    def poly(self, pts, which="s", fill=255):
        """a polygon of (x, v) points"""
        self.draw(which).polygon([(x, R(v)) for x, v in pts], fill=fill)

    def ellipse(self, cx, cv, rx, rv, which="s", fill=255):
        self.draw(which).ellipse((cx - rx, R(cv) - rv, cx + rx, R(cv) + rv), fill=fill)

    def multiply(self, which, m):
        if which == "t":
            self.mt = ImageChops.multiply(self.mt, m)
            self.T = ImageDraw.Draw(self.mt)
        else:
            self.ms = ImageChops.multiply(self.ms, m)
            self.S = ImageDraw.Draw(self.ms)

    def put(self, which, m):
        """m (a full panel "L" mask) laid over the mask: the larger value wins"""
        if which == "t":
            self.mt = ImageChops.lighter(self.mt, m)
            self.T = ImageDraw.Draw(self.mt)
        else:
            self.ms = ImageChops.lighter(self.ms, m)
            self.S = ImageDraw.Draw(self.ms)


def vgrad(v_from, v_to, a=0, b=255):
    """a panel mask going from a at height v_from to b at height v_to, flat beyond"""
    lo, hi = sorted((v_from, v_to))
    rows = max(2, R(lo) - R(hi))
    g = Image.linear_gradient("L").resize((PW, rows))       # 0 at its top, 255 at its bottom
    if v_from < v_to:                                        # a at the bottom (v_from), b at the top
        g = g.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    g = g.point(lambda x: int(a + (b - a) * x / 255.0))
    m = Image.new("L", (PW, PH), a if v_from < v_to else b)
    top_val = b if v_from < v_to else a
    bot_val = a if v_from < v_to else b
    m.paste(top_val, (0, 0, PW, R(hi)))
    m.paste(bot_val, (0, R(lo), PW, PH))
    m.paste(g, (0, R(hi)))
    return m


def hgrad(a=0, b=255):
    g = Image.linear_gradient("L").rotate(90, expand=True).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    g = g.resize((PW, PH)).point(lambda x: int(a + (b - a) * x / 255.0))
    return g


def radial(cx, cv, radius):
    """a panel mask 0 at (cx, v) growing to 255 at radius"""
    g = Image.radial_gradient("L")                          # 0 in the middle, 255 at 128 px out
    size = int(radius * 2 * 256 / 256.0)
    g = g.resize((size, size))
    m = Image.new("L", (PW, PH), 255)
    m.paste(g, (int(cx - size / 2), int(R(cv) - size / 2)))
    return m


# --- the painters ------------------------------------------------------------------------

def p_none(c):
    pass


def vstripes(n, wide=1.0, which="s", sym=True):
    """n bands across the body (odd n: the outer ones body), the second colour on the odd ones;
    wide: the second colour's band this many times the body's"""
    def paint(c):
        k_b, k_s = (n + 1) // 2, n // 2
        unit = PW / (k_b + k_s * wide)
        x = 0.0
        for i in range(n):
            w = unit * (wide if i % 2 else 1.0)
            if i % 2:
                c.rect(int(round(x)), VMIN, int(round(x + w)), VMAX + 1, which)
            x += w
    return paint


def pins(spacing, width=6, which="s", offset=None):
    def paint(c):
        x = CXP + (offset if offset is not None else 0) - spacing * (PW // spacing)
        while x < PW + spacing:
            c.rect(int(x - width / 2), VMIN, int(x + width / 2), VMAX + 1, which)
            x += spacing
    return paint


CXP = PW // 2


def double_pins(spacing, gap=14, width=5):
    def paint(c):
        x = CXP - spacing * (PW // spacing)
        while x < PW + spacing:
            for dx in (-gap / 2, gap / 2):
                c.rect(int(x + dx - width / 2), VMIN, int(x + dx + width / 2), VMAX + 1)
            x += spacing
    return paint


def tricolour_stripes(n):
    def paint(c):
        w = PW / n
        for i in range(n):
            which = (None, "s", "t")[i % 3]
            if which:
                c.rect(int(i * w), VMIN, int((i + 1) * w), VMAX + 1, which)
    return paint


def edged_stripes(n, edge=10):
    def paint(c):
        w = PW / n
        for i in range(1, n, 2):
            x0, x1 = int(i * w), int((i + 1) * w)
            c.rect(x0, VMIN, x1, VMAX + 1)
            c.rect(x0 - edge, VMIN, x0 + edge // 2, VMAX + 1, "t")
            c.rect(x1 - edge // 2, VMIN, x1 + edge, VMAX + 1, "t")
    return paint


def tapered_stripes(n):
    """stripes wide at the shoulders, narrowing to nothing at the hem"""
    def paint(c):
        w = PW / n
        for i in range(1, n, 2):
            mid = (i + 0.5) * w
            c.poly([(mid - w / 2, V_TOP + 40), (mid + w / 2, V_TOP + 40), (mid + 2, VMIN), (mid - 2, VMIN)])
    return paint


def centre(width, which="s", dx=0, edge=0):
    def paint(c):
        x0 = CXP + dx - width // 2
        c.rect(x0, VMIN, x0 + width, VMAX + 1, which)
        if edge:
            c.rect(x0 - edge, VMIN, x0, VMAX + 1, "t")
            c.rect(x0 + width, VMIN, x0 + width + edge, VMAX + 1, "t")
    return paint


def multi_centre(count, width, gap):
    def paint(c):
        total = count * width + (count - 1) * gap
        x = CXP - total // 2
        for _i in range(count):
            c.rect(x, VMIN, x + width, VMAX + 1)
            x += width + gap
    return paint


def thirds_v(order):
    """three upright thirds, order: the colour of each ("b", "s", "t")"""
    def paint(c):
        w = PW / 3.0
        for i, which in enumerate(order):
            if which != "b":
                c.rect(int(i * w), VMIN, int((i + 1) * w), VMAX + 1, which)
    return paint


def hoops(h, which="s", start=None, top=VMAX + 1, bottom=VMIN):
    """bands of height h counted from the hem, the second colour on the odd ones"""
    def paint(c):
        k = 0
        v = 0 if start is None else start
        while v - h > VMIN:
            v -= h
            k -= 1
        while v < VMAX + 1:
            if k % 2:
                c.rect(0, max(v, bottom), PW, min(v + h, top), which)
            v += h
            k += 1
    return paint


def thin_hoops(spacing, width=8, which="s"):
    def paint(c):
        v = spacing
        while v < VMAX:
            c.rect(0, v, PW, v + width, which)
            v += spacing
    return paint


def tricolour_hoops(h):
    def paint(c):
        v, k = 0, 0
        while v < VMAX + 1:
            which = (None, "s", "t")[k % 3]
            if which:
                c.rect(0, v, PW, v + h, which)
            v += h
            k += 1
    return paint


def band(v0, height, which="s", edge=0):
    def paint(c):
        c.rect(0, v0, PW, v0 + height, which)
        if edge:
            c.rect(0, v0 - edge, PW, v0, "t")
            c.rect(0, v0 + height, PW, v0 + height + edge, "t")
    return paint


def bands(*spec):
    def paint(c):
        for v0, height, which in spec:
            c.rect(0, v0, PW, v0 + height, which)
    return paint


def thirds_h(order):
    """three level thirds from the shoulders down, order top to bottom"""
    def paint(c):
        h = V_TOP / 3.0
        for i, which in enumerate(order):
            if which != "b":
                top = VMAX + 1 if i == 0 else int(V_TOP - i * h)
                bot = VMIN if i == 2 else int(V_TOP - (i + 1) * h)
                c.rect(0, bot, PW, top, which)
    return paint


def halves(side="left", divider=0):
    """the second colour on the wearer's left (the panel's right) or right"""
    def paint(c):
        if side == "left":
            c.rect(CXP, VMIN, PW, VMAX + 1)
        else:
            c.rect(0, VMIN, CXP, VMAX + 1)
        if divider:
            c.rect(CXP - divider // 2, VMIN, CXP + divider // 2, VMAX + 1, "t")
    return paint


def halves_h(top=True):
    def paint(c):
        mid = V_TOP // 2
        if top:
            c.rect(0, mid, PW, VMAX + 1)
        else:
            c.rect(0, VMIN, PW, mid)
    return paint


def quarters(diag=True, third=False):
    def paint(c):
        mid = V_TOP // 2
        a, b = ((CXP, mid, PW, VMAX + 1), (0, VMIN, CXP, mid)) if diag else \
            ((0, mid, CXP, VMAX + 1), (CXP, VMIN, PW, mid))
        c.rect(*a)
        c.rect(*b, which="t" if third else "s")
    return paint


def sash(width, rising=False, which="s", edge=0, offset=0):
    """a band from the wearer's right shoulder to the left hip (rising: the other way round)"""
    def paint(c):
        def line(off, w):
            # its middle runs from (x_top, V_TOP+60) to (x_bot, VMIN)
            xt, xb = (-120 + off, PW + 120 + off) if not rising else (PW + 120 + off, -120 + off)
            return [(xt - w / 2, V_TOP + 60), (xt + w / 2, V_TOP + 60), (xb + w / 2, VMIN), (xb - w / 2, VMIN)]
        if edge:
            c.poly(line(offset, width + 2 * edge), "t")
        c.poly(line(offset, width), which)
    return paint


def double_sash(width, gap):
    def paint(c):
        sash(width, offset=-(width + gap) // 2)(c)
        sash(width, offset=(width + gap) // 2)(c)
    return paint


def cross_sash(width):
    def paint(c):
        sash(width)(c)
        sash(width, rising=True)(c)
    return paint


def diagonal_split(rising=False):
    def paint(c):
        if rising:
            c.poly([(PW, V_TOP + 60), (0, VMIN), (PW, VMIN)])
        else:
            c.poly([(0, V_TOP + 60), (PW, VMIN), (0, VMIN)])
    return paint


def diag_stripes(pitch, width, rising=False, which="s"):
    def paint(c):
        span = V_TOP - VMIN + 200
        x = -span
        while x < PW + span:
            if rising:
                pts = [(x, VMIN), (x + width, VMIN), (x + width + span, VMIN + span), (x + span, VMIN + span)]
            else:
                pts = [(x, VMIN + span), (x + width, VMIN + span), (x + width + span, VMIN), (x + span, VMIN)]
            c.poly(pts, which)
            x += pitch
    return paint


def chevron(apex, rise, thick, which="s", up=False, edge=0):
    """a V across the chest: its point at height apex in the middle, its arms rise to the sides
    (up: the point at the top)"""
    def paint(c):
        def v(th):
            if not up:
                return [(0, apex + rise), (CXP, apex), (PW, apex + rise),
                        (PW, apex + rise - th), (CXP, apex - th), (0, apex + rise - th)]
            return [(0, apex - rise), (CXP, apex), (PW, apex - rise),
                    (PW, apex - rise - th), (CXP, apex - th), (0, apex - rise - th)]
        if edge:
            pts = v(thick + 2 * edge)
            c.poly([(x, y + edge) for x, y in pts], "t")
        c.poly(v(thick), which)
    return paint


def chevrons(apexes, rise, thick, which="s"):
    def paint(c):
        for a in apexes:
            chevron(a, rise, thick, which)(c)
    return paint


def zigzag_all(pitch, amp, thick):
    """chevron stripes all over the body"""
    def paint(c):
        v = VMIN
        while v < VMAX + amp:
            chevron(v, amp, thick)(c)
            v += pitch
    return paint


def yoke_v(depth):
    """a V of the second colour from the shoulders down to a point on the chest"""
    def paint(c):
        c.poly([(0, VMAX + 1), (PW, VMAX + 1), (PW, V_TOP - 40), (CXP, V_TOP - depth), (0, V_TOP - 40)])
    return paint


def checks(size, which="s"):
    def paint(c):
        rows = int((VMAX - VMIN) / size) + 2
        cols = int(PW / size) + 2
        x0 = CXP - size * (cols // 2)
        for j in range(rows):
            for i in range(cols):
                if (i + j) % 2:
                    c.rect(x0 + i * size, j * size, x0 + (i + 1) * size, (j + 1) * size, which)
                    if j == 0:
                        c.rect(x0 + i * size, VMIN, x0 + (i + 1) * size, 0, which)
    return paint


def gingham(size):
    def paint(c):
        a, b = Image.new("L", (PW, PH), 0), Image.new("L", (PW, PH), 0)
        da, db = ImageDraw.Draw(a), ImageDraw.Draw(b)
        x = CXP - size * (PW // size)
        while x < PW + size:
            da.rectangle((x, 0, x + size // 2 - 1, PH), fill=120)
            x += size
        v = 0
        while v < VMAX + size:
            db.rectangle((0, R(v + size // 2), PW, R(v)), fill=120)
            v += size
        both = ImageChops.add(a, b)
        c.put("s", both.point(lambda x: 255 if x == 120 else 0))
        c.put("t", both.point(lambda x: 255 if x > 200 else 0))
    return paint


def tartan(size):
    def paint(c):
        checks(size)(c)
        x = CXP - size * (PW // size) + size // 2
        while x < PW + size:
            c.rect(x - 4, VMIN, x + 4, VMAX + 1, "t")
            x += size
        v = size // 2
        while v < VMAX:
            c.rect(0, v - 4, PW, v + 4, "t")
            v += size
    return paint


def _diamond(c, x, v, w, h, which="s"):
    c.poly([(x, v - h / 2), (x + w / 2, v), (x, v + h / 2), (x - w / 2, v)], which)


def diamonds(w, h, scale=0.62, which="s"):
    """diamonds apart from each other, every other row moved half a step"""
    def paint(c):
        j, v = 0, VMIN
        while v < VMAX + h:
            x = CXP - w * (PW // w) + (w / 2 if j % 2 else 0)
            while x < PW + w:
                _diamond(c, x, v, w * scale, h * scale, which)
                x += w
            v += h / 2
            j += 1
    return paint


def harlequin(w, h, lines=False):
    """diamonds touching at their points: half the body in each colour (argyle with lines)"""
    def paint(c):
        v = VMIN
        while v < VMAX + h:
            x = CXP - w * (PW // w)
            while x < PW + w:
                _diamond(c, x, v, w, h)
                x += w
            v += h
        if lines:
            v = VMIN - PW
            while v < VMAX + h:
                for rising in (False, True):
                    x0, x1 = (0, PW)
                    v0, v1 = (v, v + PW * h / w) if rising else (v + PW * h / w, v)
                    c.poly([(x0, v0 - 4), (x1, v1 - 4), (x1, v1 + 4), (x0, v0 + 4)], "t")
                v += h
    return paint


def dots(spacing, r, which="s", stagger=True):
    def paint(c):
        j, v = 0, spacing // 2
        while v < VMAX + spacing:
            off = spacing / 2 if (stagger and j % 2) else 0
            x = CXP - spacing * (PW // spacing) + off
            while x < PW + spacing:
                c.ellipse(x, v, r, r, which)
                x += spacing
            v += spacing
            j += 1
    return paint


def big_circle(r, cv=520, which="s", ring=0):
    def paint(c):
        c.ellipse(CXP, cv, r, r, which)
        if ring:
            c.ellipse(CXP, cv, r - ring, r - ring, which, fill=0)
    return paint


def rings(step, width):
    def paint(c):
        rr = step * 12
        while rr > 0:
            c.ellipse(CXP, 450, rr, rr, "s", fill=255)
            c.ellipse(CXP, 450, rr - width, rr - width, "s", fill=0)
            rr -= step
    return paint


def star_points(cx, cv, r_out, r_in, n=5):
    pts = []
    for k in range(2 * n):
        a = math.pi / 2 + k * math.pi / n
        r = r_out if k % 2 == 0 else r_in
        pts.append((cx + r * math.cos(a), cv + r * math.sin(a)))
    return pts


def stars(spacing, size):
    def paint(c):
        j, v = 0, spacing // 2
        while v < VMAX + spacing:
            off = spacing / 2 if j % 2 else 0
            x = CXP - spacing * (PW // spacing) + off
            while x < PW + spacing:
                c.poly(star_points(x, v, size, size * 0.42))
                x += spacing
            v += spacing
            j += 1
    return paint


def chest_star(size):
    def paint(c):
        c.poly(star_points(CXP, 470, size, size * 0.42))
    return paint


def sawtooth(teeth, height, which="s"):
    """teeth along the hem"""
    def paint(c):
        w = PW / teeth
        pts = [(0, VMIN)]
        for i in range(teeth):
            pts += [(i * w, height), ((i + 0.5) * w, 0), ((i + 1) * w, height)]
        pts += [(PW, VMIN)]
        c.rect(0, VMIN, PW, 0, which)
        c.poly(pts, which)
    return paint


def zigzag_band(v0, amp, pitch, thick):
    def paint(c):
        top, bot = [], []
        x, k = 0, 0
        while x <= PW + pitch:
            y = v0 + (amp if k % 2 else 0)
            top.append((x, y + thick))
            bot.append((x, y))
            x += pitch / 2
            k += 1
        c.poly(top + bot[::-1])
    return paint


def waves(v0, amp, length, thick, count=1, gap=0, which="s"):
    def paint(c):
        for k in range(count):
            base = v0 + k * (thick + gap)
            top, bot = [], []
            for x in range(0, PW + 9, 8):
                y = base + amp * math.sin(2 * math.pi * x / length)
                top.append((x, y + thick))
                bot.append((x, y))
            c.poly(top + bot[::-1], which)
    return paint


def vwaves(count, amp, length, thick):
    def paint(c):
        for k in range(count):
            base = (k + 0.5) * PW / count
            left, right = [], []
            for v in range(VMIN, VMAX + 9, 8):
                x = base + amp * math.sin(2 * math.pi * v / length)
                left.append((x - thick / 2, v))
                right.append((x + thick / 2, v))
            c.poly(left + right[::-1])
    return paint


def grid(spacing, width):
    def paint(c):
        pins(spacing, width)(c)
        thin_hoops(spacing, width)(c)
    return paint


def bricks(w, h, mortar):
    def paint(c):
        c.rect(0, VMIN, PW, VMAX + 1)
        v, j = VMIN, 0
        while v < VMAX + h:
            c.rect(0, v, PW, v + mortar, "t")
            x = CXP - w * (PW // w) + (w / 2 if j % 2 else 0)
            while x < PW + w:
                c.rect(int(x), v, int(x) + mortar, v + h, "t")
                x += w
            v += h
            j += 1
    return paint


def nordic(width):
    def paint(c):
        x = int(PW * 0.62)
        c.rect(x - width // 2, VMIN, x + width // 2, VMAX + 1)
        c.rect(0, 470 - width // 2, PW, 470 + width // 2)
    return paint


def plus_cross(width):
    def paint(c):
        c.rect(CXP - width // 2, VMIN, CXP + width // 2, VMAX + 1)
        c.rect(0, 450 - width // 2, PW, 450 + width // 2)
    return paint


def triangles(size):
    """a field of triangles: squares cut on the diagonal"""
    def paint(c):
        v, j = VMIN, 0
        while v < VMAX + size:
            x = CXP - size * (PW // size)
            while x < PW + size:
                c.poly([(x, v), (x + size, v), (x, v + size)])
                x += size
            v += size
            j += 1
    return paint


def side_panels(width, which="s", piping=0):
    def paint(c):
        c.rect(0, VMIN, width, VMAX + 1, which)
        c.rect(PW - width, VMIN, PW, VMAX + 1, which)
        if piping:
            c.rect(width, VMIN, width + piping, VMAX + 1, "t")
            c.rect(PW - width - piping, VMIN, PW - width, VMAX + 1, "t")
    return paint


def side_lines(count, width, gap, which="s", inset=24):
    def paint(c):
        for k in range(count):
            x = inset + k * (width + gap)
            c.rect(x, VMIN, x + width, VMAX + 1, which)
            c.rect(PW - x - width, VMIN, PW - x, VMAX + 1, which)
    return paint


def raglan(drop=200):
    """the shoulders in the second colour, cut on a slant from the neck to under the arms"""
    def paint(c):
        c.poly([(0, VMAX + 1), (CXP - 150, VMAX + 1), (CXP - 150, V_TOP), (0, V_TOP - drop)])
        c.poly([(PW, VMAX + 1), (CXP + 150, VMAX + 1), (CXP + 150, V_TOP), (PW, V_TOP - drop)])
    return paint


def shoulder_stripes(count=3, width=14, gap=14, length=330):
    """stripes down from the top of each shoulder"""
    def paint(c):
        for side in (0, 1):
            for k in range(count):
                x = 90 + k * (width + gap)
                x = x if side == 0 else PW - x - width
                c.rect(x, V_TOP - length, x + width, VMAX + 1, "s")
    return paint


def compose(*painters):
    def paint(c):
        for p in painters:
            p(c)
    return paint


def gradient_v(top_second=False):
    def paint(c):
        c.put("s", vgrad(60, V_TOP - 60, 255 if not top_second else 0, 0 if not top_second else 255))
    return paint


def gradient_h():
    def paint(c):
        c.put("s", hgrad())
    return paint


def gradient_radial(r):
    def paint(c):
        c.put("s", radial(CXP, 450, r))
    return paint


def gradient_diag():
    def paint(c):
        g = Image.linear_gradient("L").rotate(45, expand=True, fillcolor=0)
        g = g.crop((g.width // 4, g.height // 4, 3 * g.width // 4, 3 * g.height // 4)).resize((PW, PH))
        c.put("s", g)
    return paint


def faded(painter, v_from=40, v_to=V_TOP - 40, which="s"):
    """painter's second colour full at v_from, gone at v_to"""
    def paint(c):
        painter(c)
        c.multiply(which, vgrad(v_from, v_to, 255, 0))
    return paint


def hem_fade(height):
    def paint(c):
        c.put("t", vgrad(0, height, 255, 0))
    return paint


def _build():
    # ---- quiet: one colour shirts with something to tell them apart
    add("plain", "One colour, the collar and cuffs in the trim colour", p_none, "plain", quiet=True)
    add("contrast-sleeves", "Body in one colour, sleeves in the second", p_none, "sleeves", sleeves="s", quiet=True)
    add("trim-sleeves", "Body in one colour, sleeves in the trim colour", p_none, "sleeves", sleeves="t", quiet=True)
    add("plain-second-shorts", "One colour shirt over shorts in the second colour", p_none, "plain",
        shorts="s", collar="s", cuffs="s", quiet=True)
    add("raglan", "Shoulders cut on a slant in the second colour", raglan(), "shoulders", sleeves="s", quiet=True)
    add("yoke", "A band of the second colour over the shoulders", band(V_TOP - 170, 400), "shoulders", quiet=True)
    add("yoke-piped", "A yoke over the shoulders with a trim line under it",
        compose(band(V_TOP - 170, 400), band(V_TOP - 186, 16, "t")), "shoulders", quiet=True)
    add("shoulder-stripes", "Three thin stripes down each shoulder", shoulder_stripes(), "shoulders", quiet=True)
    add("side-panels-narrow", "Narrow side panels in the second colour", side_panels(46), "panels", quiet=True)
    add("side-panels", "Side panels in the second colour", side_panels(90), "panels", quiet=True)
    add("side-panels-wide", "Wide side panels in the second colour", side_panels(140), "panels", sleeves="s")
    add("side-panels-piped", "Side panels with trim piping", side_panels(80, piping=12), "panels", quiet=True)
    add("side-piping", "Thin trim piping down the sides", side_lines(1, 14, 0, "t", 36), "panels", quiet=True)
    add("side-lines-triple", "Three thin lines down each side", side_lines(3, 10, 12), "panels", quiet=True)
    add("hem-band", "A band of the second colour along the hem", band(VMIN, 150), "bands", quiet=True)
    add("hem-line", "A thin trim line just above the hem", band(60, 16, "t"), "bands", quiet=True)

    # ---- upright stripes
    for n in (5, 7, 9, 11, 13):
        add("stripes-%d" % n, "%d upright stripes, the second colour on every other one" % n, vstripes(n), "stripes")
    add("stripes-broad", "Five stripes, the second colour's twice as broad", vstripes(5, 2.0), "stripes")
    add("stripes-narrow-second", "Nine stripes, the second colour's half as broad", vstripes(9, 0.5), "stripes")
    for sp in (40, 64, 96):
        add("pinstripes-%d" % sp, "Thin pinstripes %d pixels apart" % sp, pins(sp), "pinstripes", quiet=sp >= 64)
    add("pinstripes-trim", "Pinstripes in the trim colour", pins(64, 6, "t"), "pinstripes", quiet=True)
    add("pinstripes-double", "Pairs of thin pinstripes", double_pins(110), "pinstripes", quiet=True)
    add("stripes-tricolour", "Stripes of all three colours in turn", tricolour_stripes(9), "stripes")
    add("stripes-edged", "Stripes of the second colour with trim edges", edged_stripes(7), "stripes")
    add("stripes-tapered", "Stripes broad at the shoulders narrowing to the hem", tapered_stripes(7), "stripes")
    add("centre-stripe-narrow", "One narrow stripe down the middle", centre(90), "centre", quiet=True)
    add("centre-stripe", "One stripe down the middle", centre(190), "centre")
    add("centre-stripe-wide", "One wide stripe down the middle", centre(300), "centre")
    add("centre-stripe-edged", "A stripe down the middle with trim edges", centre(170, edge=14), "centre")
    add("centre-twin", "Two stripes down the middle", multi_centre(2, 70, 40), "centre")
    add("centre-triple", "Three thin stripes down the middle", multi_centre(3, 34, 26), "centre")
    add("offset-stripe-left", "A stripe through the crest, on the wearer's left", centre(150, dx=154), "centre")
    add("offset-stripe-right", "A stripe down the wearer's right side", centre(150, dx=-154), "centre")
    add("tricolour-upright", "Three upright thirds: second, body, trim", thirds_v("sbt"), "thirds")
    add("bars", "The second colour on both outer thirds, the body in the middle", thirds_v("sbs"), "thirds",
        sleeves="s")

    # ---- level stripes and bands
    for h in (50, 80, 105, 150):
        add("hoops-%d" % h, "Hoops %d pixels deep" % h, hoops(h), "hoops", sleeves="s" if h >= 150 else "b")
    add("pin-hoops-50", "Thin level lines close together", thin_hoops(50), "hoops", quiet=True)
    add("pin-hoops-90", "Thin level lines far apart", thin_hoops(90, 10), "hoops", quiet=True)
    add("hoops-tricolour", "Hoops of all three colours in turn", tricolour_hoops(90), "hoops")
    add("hoops-chest", "Hoops over the chest, the lower half plain", hoops(70, bottom=V_TOP // 2), "hoops")
    add("hoops-lower", "Hoops on the lower half, the chest plain", hoops(70, top=V_TOP // 2), "hoops")
    add("hooped-sleeves", "Plain body, hooped sleeves of the second colour", p_none, "sleeves",
        sleeves="h", cuffs="t")
    add("chest-band-thin", "A thin band across the chest", band(430, 40), "bands", quiet=True)
    add("chest-band", "A band across the chest", band(385, 120), "bands")
    add("chest-band-wide", "A wide band across the chest", band(340, 220), "bands")
    add("waist-band", "A band across the waist", band(170, 110), "bands")
    add("double-band", "Two bands across the chest", bands((470, 60, "s"), (370, 60, "s")), "bands")
    add("triple-band", "Three thin bands across the chest", bands((500, 28, "s"), (440, 28, "s"), (380, 28, "s")),
        "bands")
    add("band-edged", "A chest band with trim edges", band(390, 110, edge=14), "bands")
    add("band-two-tone", "Two touching bands, second over trim", bands((450, 70, "s"), (380, 70, "t")), "bands")
    add("top-half", "The upper half in the second colour", halves_h(True), "halves-level", sleeves="s")
    add("bottom-half", "The lower half in the second colour", halves_h(False), "halves-level")
    add("tricolour-level", "Three level thirds: second, body, trim", thirds_h("sbt"), "thirds", sleeves="s")
    add("bottom-block", "The lowest third in the second colour", thirds_h("bbs"), "halves-level")

    # ---- halves and quarters
    add("halves", "The wearer's left half in the second colour", halves("left"), "halves", sleeves="b")
    add("halves-right", "The wearer's right half in the second colour", halves("right"), "halves")
    add("halves-divided", "Halves with a trim line between them", halves("left", 18), "halves")
    add("quarters", "Quartered: second colour top left and bottom right", quarters(True), "quarters")
    add("quarters-crossed", "Quartered the other way round", quarters(False), "quarters")
    add("quarters-three", "Quartered in all three colours", quarters(True, True), "quarters")

    # ---- sashes and diagonals
    for w, nm in ((90, "sash-narrow"), (160, "sash"), (250, "sash-wide")):
        add(nm, "A sash from the right shoulder to the left hip (%s)" % nm.split("-")[-1].replace("sash", "medium"),
            sash(w), "sash")
    add("sash-rising-narrow", "A narrow sash from the left shoulder to the right hip", sash(90, True), "sash")
    add("sash-rising", "A sash from the left shoulder to the right hip", sash(160, True), "sash")
    add("sash-edged", "A sash with trim edges", sash(150, edge=14), "sash")
    add("sash-double", "Two parallel sashes", double_sash(80, 50), "sash")
    add("sash-trim", "A narrow sash in the trim colour", sash(80, which="t"), "sash", quiet=True)
    add("cross-sash", "Two sashes crossing in an X", cross_sash(110), "sash")
    add("diagonal-split", "Split on the slant, the lower part in the second colour", diagonal_split(), "diagonal")
    add("diagonal-split-rising", "Split on the other slant", diagonal_split(True), "diagonal")
    add("diagonal-stripes", "Slanting stripes all over", diag_stripes(130, 60), "diagonal")
    add("diagonal-stripes-rising", "Slanting stripes the other way", diag_stripes(130, 60, True), "diagonal")
    add("diagonal-pins", "Thin slanting lines all over", diag_stripes(70, 10), "diagonal", quiet=True)
    add("diagonal-pins-rising", "Thin slanting lines the other way", diag_stripes(70, 10, True), "diagonal")

    # ---- chevrons
    add("chevron", "A V across the chest", chevron(420, 260, 90), "chevron")
    add("chevron-thin", "A thin V across the chest", chevron(440, 260, 36), "chevron", quiet=True)
    add("chevron-wide", "A broad V across the chest", chevron(380, 260, 170), "chevron")
    add("chevron-up", "An upturned V across the chest", chevron(560, 240, 90, up=True), "chevron")
    add("chevron-double", "Two Vs across the chest", chevrons((470, 340), 230, 60), "chevron")
    add("chevron-triple", "Three thin Vs across the chest", chevrons((500, 420, 340), 220, 32), "chevron")
    add("chevron-edged", "A V across the chest with trim edges", chevron(420, 260, 80, edge=14), "chevron")
    add("chevron-low", "A V across the waist", chevron(150, 220, 80), "chevron")
    add("chevrons-all", "Chevron stripes all over", zigzag_all(150, 140, 55), "chevron")
    add("yoke-v", "The shoulders in the second colour coming to a point on the chest", yoke_v(360), "shoulders",
        sleeves="s")

    # ---- geometric
    for s in (64, 100, 160):
        add("checks-%d" % s, "Checkerboard of %d-pixel squares" % s, checks(s), "checks")
    add("gingham", "Gingham: crossing bands, the trim where they meet", gingham(110), "checks")
    add("tartan", "Checks with trim lines through them", tartan(120), "checks")
    add("diamonds", "Diamonds all over", diamonds(150, 190), "diamonds")
    add("diamonds-small", "Small diamonds all over", diamonds(80, 100, 0.55), "diamonds", quiet=True)
    add("harlequin", "Harlequin diamonds in two colours", harlequin(150, 200), "diamonds")
    add("argyle", "Argyle: diamonds with trim lines across", harlequin(170, 230, lines=True), "diamonds")
    add("dots", "Polka dots", dots(90, 16), "dots", quiet=True)
    add("dots-large", "Large polka dots", dots(150, 42), "dots")
    add("chest-circle", "A big circle on the chest", big_circle(190), "dots")
    add("chest-ring", "A ring on the chest", big_circle(210, ring=40), "dots")
    add("rings", "Rings spreading out from the chest", rings(70, 30), "dots")
    add("stars", "Little stars all over", stars(120, 26), "stars", quiet=True)
    add("chest-star", "One big star on the chest", chest_star(170), "stars")
    add("sawtooth-hem", "Teeth along the hem", sawtooth(8, 120), "bands")
    add("zigzag-band", "A zigzag band across the chest", zigzag_band(390, 70, 128, 60), "chevron")
    add("waves", "Waving bands across the body", waves(160, 30, 384, 60, 4, 80), "waves")
    add("wave-band", "One waving band across the chest", waves(390, 40, 512, 110), "waves")
    add("waves-upright", "Waving upright stripes", vwaves(4, 26, 420, 60), "waves")
    add("grid", "Window-pane grid of thin lines", grid(110, 8), "checks", quiet=True)
    add("grid-trim", "A grid of thin trim lines", compose(pins(140, 8, "t"), thin_hoops(140, 8, "t")), "checks",
        quiet=True)
    add("bricks", "Bricks: the second colour with trim mortar lines", bricks(160, 80, 10), "checks", sleeves="s")
    add("nordic-cross", "A Nordic cross, its upright through the crest side", nordic(110), "cross")
    add("plus-cross", "A cross through the middle of the chest", plus_cross(120), "cross")
    add("triangles", "Squares cut into triangles", triangles(120), "diamonds")

    # ---- fades
    add("fade-up", "The second colour at the hem fading out to the chest", gradient_v(False), "fade")
    add("fade-down", "The second colour at the shoulders fading out to the hem", gradient_v(True), "fade",
        sleeves="s")
    add("fade-across", "Fading from one side to the other", gradient_h(), "fade")
    add("fade-round", "The body colour in the middle of the chest, the second colour round it",
        gradient_radial(520), "fade")
    add("fade-slant", "Fading on the slant", gradient_diag(), "fade")
    add("fade-hoops", "Hoops fading out towards the chest", faded(hoops(80)), "fade")
    add("fade-stripes", "Stripes fading out towards the chest", faded(vstripes(9)), "fade")
    add("fade-hem", "The trim colour fading up from the hem", hem_fade(380), "fade", quiet=True)
    add("fade-pinstripes", "Pinstripes fading out towards the chest", faded(pins(48, 8)), "fade", quiet=True)

    # ---- combinations
    add("stripes-7-sleeves", "Seven stripes with sleeves in the second colour", vstripes(7), "stripes", sleeves="s")
    add("hoops-80-sleeves", "Hoops with sleeves in the trim colour", hoops(80), "hoops", sleeves="t")
    add("halves-sleeves", "Halves with sleeves in the trim colour", halves("left"), "halves", sleeves="t")
    add("sash-sleeves", "A sash with sleeves in the second colour", sash(140), "sash", sleeves="s")
    add("chevron-sleeves", "A V across the chest with sleeves in the second colour", chevron(420, 260, 90),
        "chevron", sleeves="s")
    add("panels-sleeves", "Side panels running into sleeves of the second colour", side_panels(110), "panels",
        sleeves="s")
    add("centre-sleeves", "A stripe down the middle with sleeves in the second colour", centre(170), "centre",
        sleeves="s")


_build()


# ---------------------------------------------------------------------------------- drawing

def parse(kit):
    """(Pattern, body, second, trim, shorts or None) of a kit in words, or None"""
    p = (kit or "").split()
    if len(p) < 2:
        return None
    pat = get(p[0])
    try:
        cols = [rgb(c) for c in p[1:5]]
    except ValueError:
        return None
    if not pat or not cols:
        return None
    while len(cols) < 3:
        cols.append(cols[-1])
    return (pat, cols[0], cols[1], cols[2], cols[3] if len(cols) > 3 else None)


_PANELS = {}


def panel_masks(pat):
    """(second mask, trim mask) of pattern pat on the panel, drawn once"""
    if pat.name not in _PANELS:
        c = Ctx()
        pat.paint(c)
        _PANELS[pat.name] = (c.ms, c.mt)
    return _PANELS[pat.name]


def panel(pat, body, second, trim):
    ms, mt = panel_masks(pat)
    im = Image.new("RGB", (PW, PH), body)
    im.paste(second, (0, 0), ms)
    im.paste(trim, (0, 0), mt)
    return im


def role(r, body, second, trim):
    """the colour a part wears: "b" body, "s" second, "t" trim; "h" (hooped sleeves) the second"""
    return {"b": body, "s": second, "t": trim, "h": second}[r]


SLEEVE_HOOP = 64            # hooped sleeves: bands this wide round the arm


def _sleeve_hoops(d, body):
    """bands of the body colour across sleeves already in the second colour: the arm runs across
    the texture (the cuff at its outer edge), so the bands stand upright"""
    for x0, y0, x1, y1 in SLEEVES:
        x = x0 + SLEEVE_HOOP if x0 == 0 else x0
        while x < x1:
            d.rectangle((x, y0, min(x + SLEEVE_HOOP, x1) - 1, y1 - 1), fill=body)
            x += 2 * SLEEVE_HOOP


def render(kit):
    """the 2048 x 2048 kit picture (RGB) of a kit in words"""
    import kitmaker
    pat, body, second, trim, shorts_c = parse(kit)
    shorts, cuff = kitmaker.masks()
    img = Image.new("RGB", (N, N), body)
    d = ImageDraw.Draw(img)
    sl = role(pat.sleeves, body, second, trim)
    if sl != body:
        for box in SLEEVES:
            d.rectangle((box[0], box[1], box[2] - 1, box[3] - 1), fill=sl)
        if pat.sleeves == "h":
            _sleeve_hoops(d, body)
    pn = panel(pat, body, second, trim)
    # the front: v from FRONT_HEM - SPLIT down to VMIN, rows SPLIT.. of the texture
    top_row = R(FRONT_HEM - SPLIT)
    img.paste(pn.crop((0, top_row, PW, PH)), (TX0, SPLIT))
    # the back: the panel turned half round, v 0 .. SPLIT from the top of the texture
    back = pn.crop((0, R(SPLIT) + 1, PW, R(0) + 1)).rotate(180)
    img.paste(back, (TX0, 0))
    sh = shorts_c or role(pat.shorts, body, second, trim)
    if sh == body and pat.name == "plain":
        sh = second if second != body else trim
    img.paste(sh, (0, 0), shorts)
    cf = role(pat.cuffs, body, second, trim)
    if cf == body:
        cf = second
    img.paste(cf, (0, 0), cuff)
    col = role(pat.collar, body, second, trim)
    if col == body:
        col = second
    d.rectangle((COLLAR[0], COLLAR[1], COLLAR[2] - 1, COLLAR[3] - 1), fill=col)
    d.rectangle(ARMBAND, fill=second)
    return img


def preview(kit, size=160):
    """a flat front view of the kit -- shirt and shorts -- size x size, RGBA, for pages and lists"""
    pat, body, second, trim, shorts_c = parse(kit)
    S = 4 * size                                          # drawn big, made small: smooth edges
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    k = S / 640.0
    front = panel(pat, body, second, trim).crop((0, VIEW_ROWS[0], PW, VIEW_ROWS[1]))
    tw, th = int(300 * k), int(330 * k)
    tx, ty = (S - tw) // 2, int(70 * k)
    torso = front.resize((tw, th), Image.LANCZOS)
    sl = role(pat.sleeves, body, second, trim)
    cf = role(pat.cuffs, body, second, trim)
    cf = second if cf == body else cf
    d = ImageDraw.Draw(out)
    for side in (-1, 1):                                  # the sleeves, out and down from the shoulders
        sx = tx if side < 0 else tx + tw
        pts = [(sx, ty + 8 * k), (sx + side * 130 * k, ty + 95 * k), (sx + side * 82 * k, ty + 170 * k),
               (sx, ty + 105 * k)]
        d.polygon(pts, fill=sl)
        if pat.sleeves == "h":
            for f in (0.3, 0.62):                         # two bands of the body round the arm
                p0 = (pts[0][0] + (pts[1][0] - pts[0][0]) * f, pts[0][1] + (pts[1][1] - pts[0][1]) * f)
                p1 = (pts[3][0] + (pts[2][0] - pts[3][0]) * f, pts[3][1] + (pts[2][1] - pts[3][1]) * f)
                d.line([p0, p1], fill=body, width=max(2, int(18 * k)))
        a, b = pts[1], pts[2]
        d.line([a, b], fill=cf, width=max(2, int(16 * k)))
    out.paste(torso, (tx, ty))
    col = role(pat.collar, body, second, trim)
    col = second if col == body else col
    d.pieslice((S // 2 - 52 * k, ty - 46 * k, S // 2 + 52 * k, ty + 46 * k), 0, 180, fill=col)
    d.pieslice((S // 2 - 36 * k, ty - 32 * k, S // 2 + 36 * k, ty + 32 * k), 0, 180, fill=(0, 0, 0, 0))
    sh = shorts_c or role(pat.shorts, body, second, trim)
    if sh == body and pat.name == "plain":
        sh = second if second != body else trim
    sy = ty + th + int(6 * k)
    d.polygon([(tx + 6 * k, sy), (tx + tw - 6 * k, sy), (tx + tw + 8 * k, sy + 150 * k),
               (S // 2 + 12 * k, sy + 150 * k), (S // 2, sy + 70 * k), (S // 2 - 12 * k, sy + 150 * k),
               (tx - 8 * k, sy + 150 * k)], fill=sh)
    line = (90, 90, 90, 255) if lightness(body) > 80 else (0, 0, 0, 0)
    if line[3]:
        d.rectangle((tx, ty, tx + tw - 1, ty + th - 1), outline=line, width=max(1, int(2 * k)))
    return out.resize((size, size), Image.LANCZOS)


# ---------------------------------------------------------------------------------- the look

_COVER = {}


def coverage(pat):
    """(body, second, trim) shares of the shirt as seen from the front: the body panel's masks,
    the sleeves counted as a quarter of the shirt"""
    if pat.name not in _COVER:
        ms, mt = panel_masks(pat)
        box = (0, VIEW_ROWS[0], PW, VIEW_ROWS[1])
        t = ImageStat.Stat(mt.crop(box)).mean[0] / 255.0
        s_only = ImageChops.multiply(ms.crop(box), ImageChops.invert(mt.crop(box)))
        s = ImageStat.Stat(s_only).mean[0] / 255.0
        b = max(0.0, 1.0 - s - t)
        share = {"b": b * 0.75, "s": s * 0.75, "t": t * 0.75}
        if pat.sleeves == "h":
            share["s"] += 0.125
            share["b"] += 0.125
        else:
            share[pat.sleeves] += 0.25
        _COVER[pat.name] = (share["b"], share["s"], share["t"])
    return _COVER[pat.name]


_LOOK, _PARTS = {}, {}


def look(kit):
    """(main colour, the colour from afar) of a kit in words: Lab triples"""
    if kit not in _LOOK:
        if len(_LOOK) > 1 << 18:
            _LOOK.clear()
        pat, body, second, trim, _sh = parse(kit)
        cov = coverage(pat)
        cols = list(zip((body, second, trim), cov))
        main = max(cols, key=lambda x: x[1])[0]
        _LOOK[kit] = lab(main), lab(mix(cols))
    return _LOOK[kit]


def apart(k1, k2):
    """how far two kits are apart: the smaller of the difference of their main colours and of
    their colours from afar (CIEDE2000)"""
    m1, a1 = look(k1)
    m2, a2 = look(k2)
    return min(de2000(m1, m2), de2000(a1, a2))


def shared(k1, k2):
    """the share of two kits' area (0..1) in colours alike: a colour pair under SAME apart counts
    in full, fading out to none at twice that"""
    def parts(k):
        if k not in _PARTS:
            if len(_PARTS) > 1 << 18:
                _PARTS.clear()
            pat, body, second, trim, _sh = parse(k)
            _PARTS[k] = tuple((lab(c), w) for c, w in zip((body, second, trim), coverage(pat)) if w > 0)
        return _PARTS[k]
    out = 0.0
    for c1, w1 in parts(k1):
        for c2, w2 in parts(k2):
            d = de2000(c1, c2)
            out += min(w1, w2) * max(0.0, min(1.0, (2 * SAME - d) / SAME))
    return min(1.0, out)


SAME = 12.0


def distinct(k1, k2):
    """True when two kits are clearly apart: their main colours and their colours from afar at
    least DISTINCT apart, and less than half of them in alike colours"""
    return apart(k1, k2) >= DISTINCT and shared(k1, k2) < 0.5


def clash(k1, k2):
    """True when two kits would be mistaken for each other: most of their area in alike colours,
    or alike from afar. A club's own away kit is kept unless it clashes (it is the real one)"""
    return shared(k1, k2) >= 0.6 or de2000(look(k1)[1], look(k2)[1]) < SAME


# ---------------------------------------------------------------------------------- picking

def _h(seed, tag):
    return int(hashlib.md5(("%s|%s" % (seed, tag)).encode("utf-8")).hexdigest()[:12], 16)


def _order(items, seed, tag):
    """items in an order of their own for this seed: the same every run, on every PC"""
    return sorted(items, key=lambda x: _h(seed, "%s|%s" % (tag, x if isinstance(x, str) else getattr(x, "name", x))))


def _words(name, body, second, trim, shorts=None):
    w = "%s %s %s %s" % (name, body, second, trim)
    return w + (" " + shorts if shorts else "")


def _contrast_second(body, candidates, seed, tag):
    """of candidates, the first (in this seed's order of the club's own, then black and white)
    that stands out from body"""
    for c in candidates:
        if c and de2000(c, body) >= INNER + 8:
            return c
    return max(("#ffffff", "#101010", "#f5d000", "#14285a"), key=lambda c: de2000(c, body))


def _norm(words):
    """the club's words filled out: (pattern name, body, second, trim, shorts or None) or None"""
    p = parse(words)
    if not p:
        return None
    pat, b, s, t, sh = p
    return pat.name, hexc(b), hexc(s), hexc(t), hexc(sh) if sh else None


QUIET_HOME = True        # a plain home shirt gets a quiet pattern of the library in its colours


def home_kit(home, seed):
    n = _norm(home)
    if not n:
        return None
    name, b, s, t, sh = n
    if name == "plain" and QUIET_HOME:
        quiet = _order([p.name for p in LIBRARY if p.quiet], seed, "home")
        name = quiet[0]
        if de2000(s, b) < INNER:                 # a one colour shirt: a second colour that shows
            s = _contrast_second(b, [t, sh], seed, "home2")
            t = t if de2000(t, b) >= INNER else s
    return _words(name, b, s, t, sh)


def _club_colours(*kits):
    out = []
    for k in kits:
        n = _norm(k) if k else None
        if n:
            for c in n[1:]:
                if c and c not in out:
                    out.append(c)
    return out


def _make(seed, tag, bodies, seconds, pool, against, tries=None):
    """the first kit (in this seed's order) with a body of `bodies` (tried in order), a second
    colour of `seconds` that stands out from it, a pattern of pool, that is DISTINCT from every
    kit of against"""
    pats = _order(pool, seed, tag + "-pattern")
    best, best_d = None, -1.0
    for bi, body in enumerate(bodies):
        sec = _contrast_second(body, seconds, seed, tag)
        trims = [c for c in seconds + ["#ffffff", "#101010"] if c != sec and de2000(c, body) >= INNER]
        trim = trims[0] if trims else sec
        for pi, pat in enumerate(pats[:12]):
            w = _words(pat, body, sec, trim)
            if all(distinct(w, a) for a in against):
                return w
            d = min([apart(w, a) * (1.0 if shared(w, a) < 0.5 else 0.5) for a in against] or [100.0])
            if d > best_d:
                best, best_d = w, d
    return best


def plan(home, away=None, seed=None, third=None):
    """{"p1": home, "p2": away, "p3": third, "g1": goalkeeper} in words for a club with home words
    `home` (its own) and away words `away` (its own, or None); seed tells clubs of the same
    colours apart (the club's name). third: a third kit in words the recipe sets (club_third_kits,
    a club whose three kits all looked like a league opponent's home kit), worn as it is; None
    picks one. {} when home is no kit in words."""
    seed = seed if seed is not None else "%s|%s" % (home, away or "")
    p1 = home_kit(home, seed)
    if not p1:
        return {}
    pool = [p.name for p in LIBRARY]
    own = _club_colours(home, away)
    h_body = _norm(p1)[1]
    p2 = None
    if away and _norm(away):
        cand = home_kit(away, seed + "|away")
        if not clash(cand, p1):
            p2 = cand
    if not p2:
        light = lightness(h_body) < 55
        club = [c for c in own[1:] if (lightness(c) >= 62) == light]
        stock = [c for c in PALETTE if (lightness(c) >= 70 if light else lightness(c) <= 40)]
        bodies = club + _order(stock, seed, "away-body")
        p2 = _make(seed, "away", bodies, [h_body] + own, pool, [p1])
    a_body = _norm(p2)[1]
    fam = {get(_norm(k)[0]).family for k in (p1, p2)}
    pool3 = [p.name for p in LIBRARY if p.family not in fam]
    # B360 (mato 09.11.: "nacrtan iz boja kluba"): the third kit in the club's colours, those of
    # its home kit -- an away kit's own colour is not one (Penya Encarnada, blue and red, had a red
    # third with lime shorts from its lime away kit). A home colour apart from both kits, else
    # black or white, else a darker or lighter shade of the home colours, else a grey; the
    # palette last
    home_cols = _club_colours(home)
    shades = [toward(c, k, t) for c in home_cols for k, t in (("#101010", 0.55), ("#ffffff", 0.6))]
    first = [c for c in home_cols + ["#101010", "#ffffff"] + shades + ["#3a3d42", "#f2efe4", "#8a8f96", "#c4c8cc"]
             if de2000(c, h_body) >= DISTINCT and de2000(c, a_body) >= DISTINCT]
    bodies = list(dict.fromkeys(first)) + _order([c for c in PALETTE if c not in first], seed, "third-body")
    p3 = _make(seed, "third", bodies, home_cols + [h_body], pool3, [p1, p2])
    if third and _norm(third):
        p3 = _words(*_norm(third))
    t_body = _norm(p3)[1]
    gk_bodies = [c for c in _order(GK_PALETTE, seed, "gk-body") if de2000(c, PITCH) >= DISTINCT]
    gk_pool = [p.name for p in LIBRARY if p.quiet]
    g = _make(seed, "gk", gk_bodies, _order(["#101010", "#ffffff"], seed, "gk-second") + [h_body], gk_pool,
              [p1, p2, p3])
    gn = _norm(g)
    g1 = _words(gn[0], gn[1], gn[2], gn[3], gn[1])              # goalkeeper's shorts: the shirt's colour
    return {"p1": p1, "p2": p2, "p3": p3, "g1": g1}


def generated_home(seed):
    """home words for a club with no colours at all (a numbered badge): two colours of the
    palette, picked by its name, that stand out from each other"""
    body = _order(PALETTE, seed, "body")[0]
    sec = next(c for c in _order(PALETTE, seed, "second") if de2000(c, body) >= DISTINCT + 8)
    return "plain %s %s %s" % (body, sec, sec)


# ---------------------------------------------------------------------------------- previews

SAMPLE = ("#1f4fbf", "#ffffff", "#c8102e")


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    out = argv[0]
    size = int(argv[1]) if len(argv) > 1 else 160
    os.makedirs(out, exist_ok=True)
    for i, p in enumerate(LIBRARY, 1):
        preview(_words(p.name, *SAMPLE), size).save(os.path.join(out, "p%03d.png" % i), optimize=True)
    print("%d patterns into %s" % (len(LIBRARY), out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
