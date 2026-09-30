r"""python mkemblems.py --base <pesdb dir> --out <livecpk root> [--from 130] [--only 130,131]
                      [--preview <dir>]

Give our competitions an emblem of their own.

Where a competition's emblem lives, measured 2026-09-21 in `Data/dt15_x64.cpk`:

    common/render/symbol/emblemLc/emb_<competition id, four digits><variant>.png

312 files for 91 shipped competitions, and the numbers are the competition ids themselves --
emb_0002 is the Champions League, which is competition 2. Two variant sets are in use and
either is enough on its own: 43 competitions ship only the silhouettes `_b_l` / `_b_ll` (black)
and `_w_l` / `_w_ll` (white), 40 ship only the full-colour `_l` / `_ll`, and a handful ship
both plus `_s1` / `_s2` alternates. `_l` is 256 pixels square, `_ll` is 512, all PNG.

That makes a competition emblem the same kind of job as a club crest: keyed by an id, so a
livecpk root can supply one without touching a shipped file or a table. None of our 39 leagues
has one, which is why they show nothing where every shipped league shows a badge.

This writes a placeholder, not artwork: a shield in a colour derived from the competition id,
the league's initials across it, and the tier number below. Self-made, deterministic, and no
game art is copied. Both variant sets are written, because which one a given menu asks for is
not known yet -- whichever it reaches, it finds something.

    python mkemblems.py --base ...\pesdb --out ...\livecpk\_FL26G39Tri
    python mkemblems.py --base ...\pesdb --preview ...\shots\emblems --only 130,138

By default it draws an emblem for every competition the shipped tables do not have, which is
the right test and not a number range: shipped ids run to 145 with gaps, and 130 to 145 are
Scotland and Saudi Arabia. --from and --only override that.

--preview writes the 512s into a plain folder for eyeballing and nothing into the game tree.
"""
import colorsys, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pesdb
from PIL import Image, ImageDraw, ImageFont

COMP, REG = 36, 2352
C_ID, C_CODE = 0x05, 0x08
R_ID, R_CID, R_GROUP, R_NAME = 0x02, 0x08, 0x0a, 0x14
NO_GROUP = 255
FONT = r"C:\Windows\Fonts\arialbd.ttf"
VARIANTS = [("_l", 256), ("_ll", 512), ("_b_l", 256), ("_b_ll", 512),
            ("_w_l", 256), ("_w_ll", 512)]


def load(base, name):
    return pesdb.wesys_unpack(open(os.path.join(base, name), "rb").read())


def competitions(base):
    """[(competition id, code, name)] -- the name is the master regulation's."""
    comp, reg = load(base, "Competition.bin"), load(base, "CompetitionRegulation.bin")
    names = {}
    for i in range(len(reg) // REG):
        r = reg[i * REG:(i + 1) * REG]
        if r[R_GROUP] == NO_GROUP:
            names.setdefault(r[R_CID],
                             r[R_NAME:R_NAME + 0x73].split(bytes(1))[0].decode("utf-8", "replace"))
    out = []
    for i in range(len(comp) // COMP):
        r = comp[i * COMP:(i + 1) * COMP]
        cid = r[C_ID]
        out.append((cid, r[C_CODE:].split(bytes(1))[0].decode("latin1"), names.get(cid, "")))
    return out


def colours(cid):
    h = (cid * 0.61803398875) % 1.0                  # golden-ratio hue walk, same as mkcrests
    dark = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(h, 0.70, 0.45))
    light = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(h, 0.35, 0.96))
    lum = 0.299 * light[0] + 0.587 * light[1] + 0.114 * light[2]
    ink = (20, 20, 28) if lum > 140 else (245, 245, 250)
    return dark, light, ink


DIV = re.compile(r"^(.*?)\s+D([1-9])$")


def initials(name, code, cid):
    """Up to four letters somebody can read at 32 pixels."""
    m = DIV.match(name.strip())
    if m:
        # "Croatia D1" -> CRO, "Bosnia and Herzegovina D1" -> BIH. The country tag says more
        # than the first letter of every word: "CD" tells nobody anything.
        import countries as C
        return C.short(m.group(1))
    words = [w for w in name.replace("-", " ").split() if w[:1].isalpha()]
    if not words:
        words = [w for w in code.replace("_", " ").split() if w[:1].isalpha()]
    if not words:
        return str(cid)
    if len(words) == 1:
        return words[0][:4].upper()
    return "".join(w[0] for w in words)[:4].upper()


def tier(name):
    """The division digit of "France D4", the trailing number of "FL League 07", or "".""" 
    m = DIV.match(name.strip())
    if m:
        return m.group(2)
    tail = name.strip().split()[-1] if name.strip() else ""
    return tail if tail.isdigit() else ""


def emblem(cid, label, sub, size, mode):
    ss = 4
    S = size * ss
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    dark, light, ink = colours(cid)
    if mode == "b":
        dark, light, ink = (18, 18, 22), (18, 18, 22), (255, 255, 255)
    elif mode == "w":
        dark, light, ink = (250, 250, 252), (250, 250, 252), (20, 20, 24)

    # a shield: square shoulders, a point at the bottom -- reads as a competition badge and
    # not as one of our club roundels
    m = S * 0.10
    w = S - 2 * m
    top, bot = m, S - m
    shoulder = top + w * 0.62
    pts = [(m, top), (S - m, top), (S - m, shoulder), (S / 2, bot), (m, shoulder)]
    d.polygon(pts, fill=dark + (255,))
    k = S * 0.045
    inner = [(m + k, top + k), (S - m - k, top + k), (S - m - k, shoulder - k * 0.5),
             (S / 2, bot - k * 1.6), (m + k, shoulder - k * 0.5)]
    d.polygon(inner, fill=light + (255,))

    def fit(text, px, y):
        # as big as asked, smaller when it is wider than the shield (four letters ran over its edges)
        while True:
            try:
                font = ImageFont.truetype(FONT, int(px))
            except OSError:
                font = ImageFont.load_default()
                break
            tb = d.textbbox((0, 0), text, font=font)
            if tb[2] - tb[0] <= (w - 2 * k) * 0.86 or px < S * 0.08:
                break
            px *= 0.93
        tb = d.textbbox((0, 0), text, font=font)
        d.text(((S - (tb[2] - tb[0])) / 2 - tb[0], y - tb[1]), text, font=font, fill=ink + (255,))

    fit(label, S * (0.30 if len(label) > 3 else 0.38), S * 0.24)
    if sub:
        fit(sub, S * 0.22, S * 0.58)
    return img.resize((size, size), Image.LANCZOS)


def main():
    a = sys.argv[1:]
    get = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    base, out, preview = get("--base"), get("--out"), get("--preview")
    if not base or not (out or preview):
        print(__doc__)
        return 1
    only = {int(x) for x in get("--only", "").split(",") if x.strip()}
    first = get("--from")

    comps = competitions(base)
    if only:
        pick = [c for c in comps if c[0] in only]
    elif first:
        pick = [c for c in comps if c[0] >= int(first)]
    else:
        # "ours" is not a number range. Shipped competition ids run up to 145 with gaps --
        # 130 to 145 are Scotland and Saudi Arabia -- so the leagues that need an emblem are
        # the ones the shipped tables do not have, and that is a comparison, not a threshold.
        import modscan
        shipped = load(modscan.base_dir(), "Competition.bin")
        have = {shipped[i * COMP + C_ID] for i in range(len(shipped) // COMP)}
        pick = [c for c in comps if c[0] not in have]
    if not pick:
        raise SystemExit("this pesdb folder adds no competition to the shipped 91 -- is it "
                         "the base rather than one of our worlds?")
    print("%d competitions in %s, %d of them ours" % (len(comps), base, len(pick)))

    d = preview or os.path.join(out, "common", "render", "symbol", "emblemLc")
    os.makedirs(d, exist_ok=True)
    for cid, code, name in pick:
        lab, sub = initials(name, code, cid), tier(name)
        if preview:
            emblem(cid, lab, sub, 512, "").save(os.path.join(d, "emb_%04d_ll.png" % cid))
            continue
        for suf, px in VARIANTS:
            mode = "b" if "_b" in suf else ("w" if "_w" in suf else "")
            emblem(cid, lab, sub, px, mode).save(os.path.join(d, "emb_%04d%s.png" % (cid, suf)))
    print("wrote %d competition emblems to %s" % (len(pick), d))
    for cid, code, name in pick[:5]:
        print("   emb_%04d  %-22s %s" % (cid, code, name))
    if not preview:
        print("Keyed by competition id, and only ids the shipped tables do not use, so nothing "
              "shipped is touched. Activate the root and look at the competition list.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
