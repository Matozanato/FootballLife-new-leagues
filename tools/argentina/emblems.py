"""Argentina's competition emblems: the six files the game reads, emb_<cid>_{,b_,w_}{l,ll}.png (256 / 512, RGBA), into
the world's common/render/symbol/emblemLc, from data/logos (the leagues', the Regional's entry, the new cups'). A plain
background (white or black, flooded from the corners) becomes transparent; the picture is cropped and centred on a
square. A white-only emblem (the Supercopa Internacional's, the Recopa's) is drawn dark on the light lists (l, w_) and
white on the dark ones (b_). The Recopa de Campeones has no emblem of its own yet: recopa_de_campeones.png is made on
the Supercopa Internacional's trophy."""
import os
from collections import deque
from PIL import Image

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "logos")
LEAGUES = {"Primera Nacional": "primera_nacional.png", "Primera B Metropolitana": "primera_b.png",
           "Primera C": "primera_c.png", "Torneo Federal A": "federal_a.jpg",
           "Torneo Promocional Amateur": "promocional.png", "Torneo Argentino del Interior": "interior.jpg"}
REGIONAL = "torneo_regional_amateur.jpg"
DARK = (28, 36, 64)


def clear(im):
    px = im.load(); w, h = im.size
    c = px[2, 2]
    if c[3] < 128:
        return im
    white = min(c[:3]) > 235
    black = max(c[:3]) < 30
    if not (white or black):
        return im
    seen = set(); q = deque([(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)])
    while q:
        x, y = q.popleft()
        if (x, y) in seen or not (0 <= x < w and 0 <= y < h):
            continue
        r, g, b, a = px[x, y]
        if (white and min(r, g, b) < 225) or (black and max(r, g, b) > 40):
            continue
        seen.add((x, y)); px[x, y] = (r, g, b, 0)
        q.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    return im


def disc(im, cx, cy, r):
    """a black emblem in a circle open at the top (the Federal A's): the disc kept whole, outside it only the bright
    marks (the AFA crest)"""
    px = im.load(); w, h = im.size
    for y in range(h):
        for x in range(w):
            r_, g, b, a = px[x, y]
            if (x - cx) ** 2 + (y - cy) ** 2 > r * r:
                px[x, y] = (r_, g, b, min(a, max(r_, g, b)))
    return im


SHAPE = {"federal_a.jpg": (401, 426, 354)}   # centre and radius of its circle (measured on the picture)


def square(im):
    im = im.crop(im.getbbox())
    side = int(max(im.size) * 1.04)
    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    sq.paste(im, ((side - im.size[0]) // 2, (side - im.size[1]) // 2))
    return sq


def tint(im, rgb):
    a = im.split()[3]
    out = Image.new("RGBA", im.size, rgb + (255,)); out.putalpha(a)
    return out


def write(root, emb, log=print):
    """emb: {competition id: picture file in data/logos}"""
    out = os.path.join(root, "common", "render", "symbol", "emblemLc")
    os.makedirs(out, exist_ok=True)
    for cid, f in sorted(emb.items()):
        im = Image.open(os.path.join(HERE, f)).convert("RGBA")
        im = square(disc(im, *SHAPE[f]) if f in SHAPE else clear(im))
        ext = [im.getpixel((x, y)) for x in range(0, im.size[0], 7) for y in range(0, im.size[1], 7)]
        white_only = all(p[3] < 40 or min(p[:3]) > 230 for p in ext)
        for pre in ("", "b_", "w_"):
            v = tint(im, DARK) if white_only and pre != "b_" else im
            for suf, n in (("l", 256), ("ll", 512)):
                v.resize((n, n), Image.LANCZOS).save(os.path.join(out, "emb_%04d_%s%s.png" % (cid, pre, suf)))
    log("argentina: %d competition emblem(s)" % len(emb))
