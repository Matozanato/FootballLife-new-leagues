r"""Trophy variants (FL 2027, mato 08.11.): "several dozen generated trophies so that every
competition has its own" -- a trophy folder (a base) made again for each competition, in its
textures only: the cup's metal another colour, its coloured parts (ribbons, the plinth) in the
competition's colours, the competition's logo on the panels of the base, and the flags, banners
and stand of the ceremony in its colours with its logo and name. The models, the ceremony itself
(fdc frames, gani) and every other file stay the base's, so a variant is as safe in the game as
its base is.

A base is a trophy folder lbtrophies can pair (FL26's layout, entry 16: common\demo\prop\
cup_afc_cl_hi, common\demo\fixdemoobj ...). The models' fmdl (in #Win\*.fpk) name the colour
textures (Base_Tex_SRGB): the cup's (common\demo\prop\cup_*) are recoloured, the ceremony's
(fixdemoobj, the circle flags) are rebranded where they are a flat colour with decals on it --
a texture with people, kits or a photo on it is left as it is.

  spec = {"base": <folder>, "metal": "gold" | "silver" | ..., "colours": ["#rrggbb", "#rrggbb"],
          "logo": <png or None>, "name": <competition name or "">}
  write(spec, out)          the variant's own files (the textures it changed) under <out>, in the
                            base's layout; lbtrophies serves every other file from the base
  auto(comps, bases, logos) a variant for each competition, the same one every Build: the base
                            and the metal from a hash of the competition's name, the colours from
                            its logo, no two competitions of a world alike

The textures are .ftex 2.03/2.04 read at their first mip and written with one (as the community's
trophies for FL26/FL 2027 are): format 0 (RGBA8), 2 (DXT1) and 4 (DXT5), Pillow doing the DXT;
another format is written as DXT5 (4). A side over 2048 is halved: the base's 4096 textures are
16 MB each and a variant is one competition of hundreds.

  python mktrophyvariants.py <base folder> <out folder> <metal> [#colour1 #colour2] [logo.png] [--name NAME]
  python mktrophyvariants.py --preview <base folder> <out.png> <metal> [...]
"""
import colorsys, hashlib, io, json, os, struct, sys, zlib

CHUNK = 16384
ALBEDO = "Base_Tex_SRGB"
METALNESS = "MetalnessMap_Tex_LIN"
MODEL_DIRS = (("common", "demo", "prop"), ("common", "demo", "fixdemoobj"))
FORMATS = {0: None, 2: "DXT1", 4: "DXT5"}      # ftex pixel format -> Pillow's DDS pixel_format
FOURCC = {2: b"DXT1", 4: b"DXT5"}
MAX_SIDE = 2048                 # the cup's textures, seen close in the ceremony
MAX_SCENE = 1024                # the flags and the stand's, seen from afar
VERSION = 1                     # a change of what a variant looks like: Build makes them again
SKIP_DIRS = ("cut_data", "anime", "sourceimages")
LUMA = (0.2126, 0.7152, 0.0722)
# the colour a trophy's metal takes (sRGB of the polished metal at its usual brightness)
METALS = {
    "gold": (212, 170, 64),
    "silver": (196, 199, 204),
    "bronze": (176, 116, 64),
    "pale gold": (226, 204, 132),
    "rose gold": (206, 142, 118),
    "platinum": (226, 228, 222),
    "dark steel": (110, 116, 126),
    "copper": (184, 100, 58),
}
METAL_ORDER = tuple(METALS)
# the panels of a cup's colour texture where the competition's logo goes, by the md5 of that
# .ftex, as fractions of the texture (x0, y0, x1, y1). The base competition's decals are there,
# so a panel is always painted over, logo or not. A base folder may name its own in variant.json:
# {"panels": {"<texture file name>": [[x0, y0, x1, y1], ...]}}
PANELS = {
    # joaako1602's state-championship trophies (Carioca, Paulista: one texture, two models): the
    # six plates of the plinth and the one below them
    "23c43b0db1d7d9172743caf1287be0c5": [
        (0.152, 0.239, 0.359, 0.446), (0.423, 0.240, 0.629, 0.446), (0.693, 0.239, 0.900, 0.446),
        (0.155, 0.538, 0.361, 0.745), (0.417, 0.534, 0.623, 0.741), (0.687, 0.534, 0.894, 0.741),
        (0.378, 0.786, 0.680, 1.000),
    ],
}
FONT = r"C:\Windows\Fonts\arialbd.ttf"
FLAT = 0.5          # the share of a ceremony texture its background colour must cover to be rebranded
SKIN = 0.02         # the share of skin colour that says a texture has people on it (staff, crowd): left alone


class Error(Exception):
    pass


# ---- ftex ---------------------------------------------------------------------------------------

def ftex_head(b):
    """(format, width, height, mip levels) of an .ftex's bytes"""
    if b[:4] != b"FTEX":
        raise Error("not an .ftex")
    fmt, w, h, _depth = struct.unpack_from("<HHHH", b, 8)
    return fmt, w, h, b[16]


def ftex_data(b, level=0):
    """the pixel data of mip <level> of an .ftex, its chunks put back together"""
    off, size, _c, _i, _f, n = struct.unpack_from("<IIIBBH", b, 0x40 + 16 * level)
    out = bytearray()
    for k in range(n):
        cs, us, o = struct.unpack_from("<HHI", b, off + 8 * k)
        part = b[off + o:off + o + cs]
        out += zlib.decompress(part) if cs != us else part
    return bytes(out[:size])


def dds_header(fmt, w, h, n):
    pf = struct.pack("<II4s5I", 32, 4, FOURCC[fmt], 0, 0, 0, 0, 0)
    return (struct.pack("<4s7I", b"DDS ", 124, 0x81007, h, w, n, 0, 1) + b"\0" * 44 + pf
            + struct.pack("<5I", 0x1000, 0, 0, 0, 0))


def read_ftex(path):
    """the first mip of an .ftex as an RGBA Pillow image"""
    from PIL import Image
    b = open(path, "rb").read()
    fmt, w, h, _m = ftex_head(b)
    data = ftex_data(b)
    if fmt == 0:
        return Image.frombytes("RGBA", (w, h), data[:w * h * 4])
    if fmt not in FOURCC:
        raise Error("%s: ftex format %d" % (path, fmt))
    return Image.open(io.BytesIO(dds_header(fmt, w, h, len(data)) + data)).convert("RGBA")


def ftex_bytes(im, fmt, like=None):
    """an .ftex of <im> with one mip level in format <fmt> (0, 2 or 4; another is 4); the rest of
    the header (version, flags) the .ftex bytes <like>'s, the base's"""
    if fmt not in FORMATS:
        fmt = 4
    im = im.convert("RGBA")
    w, h = im.size
    if fmt == 0:
        data = im.tobytes()
    else:
        b = io.BytesIO()
        (im.convert("RGB") if fmt == 2 else im).save(b, "DDS", pixel_format=FORMATS[fmt])
        data = b.getvalue()[128:]
    head = bytearray(like[:0x40]) if like and like[:4] == b"FTEX" else bytearray(0x40)
    if head[:4] != b"FTEX":
        head[0:4] = b"FTEX"
        head[4:8] = bytes.fromhex("85EB0140")          # 2.03
        head[16:20] = bytes.fromhex("01021100")
        head[28:32] = (3).to_bytes(4, "little")
    struct.pack_into("<HHHH", head, 8, fmt, w, h, 1)
    head[16] = 1                                       # one mip level
    head[0x24] = head[0x25] = 0                        # all of it in this file (no .ftexs)
    packed = []
    for i in range(0, max(len(data), 1), CHUNK):
        c = data[i:i + CHUNK]
        z = zlib.compress(c, 9)
        packed.append(z if len(z) < len(c) else c)
    sizes = [len(data[i:i + CHUNK]) for i in range(0, max(len(data), 1), CHUNK)]
    table, at = bytearray(), 8 * len(packed)
    for z, us in zip(packed, sizes):
        table += struct.pack("<HHI", len(z), us if us < 0x10000 else 0, at)
        at += len(z)
    entry = struct.pack("<IIIBBH", 0x50, len(data), at, 0, 0, len(packed))
    return bytes(head) + entry + bytes(table) + b"".join(packed)


# ---- fpk / fmdl: which textures colour which model -----------------------------------------------

def fpk_files(b):
    """{path in the fpk: bytes} of a Fox Engine .fpk"""
    if b[:6] != b"foxfpk":
        raise Error("not an .fpk")
    n = struct.unpack_from("<I", b, 0x20)[0]
    out = {}
    for i in range(n):
        do, ds, no, nl = struct.unpack_from("<QQQQ", b, 0x30 + 0x30 * i)
        out[b[no:no + nl].decode("ascii", "replace")] = b[do:do + ds]
    return out


def fmdl_materials(m):
    """[(material, [(parameter, texture name, texture folder)])] of an .fmdl (2.03)"""
    if m[:4] != b"FMDL":
        raise Error("not an .fmdl")
    info, _f0, _f1, c0, c1, o0, _l0, o1, _l1 = struct.unpack_from("<QQQIIIIII", m, 8)
    s0, s1 = {}, {}
    for i in range(c0):
        t, n, o = struct.unpack_from("<HHI", m, info + 8 * i)
        s0[t] = (n, o0 + o)
    for i in range(c1):
        t, o, ln = struct.unpack_from("<III", m, info + 8 * c0 + 12 * i)
        s1[t] = (o1 + o, ln)
    if not all(k in s0 for k in (4, 6, 7, 12)) or 3 not in s1:
        return []

    def string(i):
        _blk, ln, off = struct.unpack_from("<HHI", m, s0[12][1] + 8 * i)
        return m[s1[3][0] + off:s1[3][0] + off + ln].decode("ascii", "replace")
    n6, a6 = s0[6]
    tex = [tuple(string(x) for x in struct.unpack_from("<HH", m, a6 + 4 * i)) for i in range(n6)]
    n7, a7 = s0[7]
    par = [struct.unpack_from("<HH", m, a7 + 4 * i) for i in range(n7)]
    n4, a4 = s0[4]
    out = []
    for i in range(n4):
        name, _p, _mat, ntex, _nvec, first, _fv = struct.unpack_from("<HHHBBHH", m, a4 + 16 * i)
        binds = []
        for k in range(ntex):
            if first + k < len(par):
                pn, ref = par[first + k]
                if ref < len(tex):
                    binds.append((string(pn), tex[ref][0], tex[ref][1]))
        out.append((string(name), binds))
    return out


def phase_roots(base):
    """the folders of a trophy folder that hold a "common": its top, or its phase folders"""
    if os.path.isdir(os.path.join(base, "common")):
        return [""]
    return sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d, "common")))


def _on_disk(root, rel):
    """<rel> (with /) as it is spelt under <root> (the case of the files), or None"""
    here = root
    for part in rel.split("/"):
        try:
            names = {n.lower(): n for n in os.listdir(here)}
        except OSError:
            return None
        n = names.get(part.lower())
        if n is None:
            return None
        here = os.path.join(here, n)
    return os.path.relpath(here, root).replace(os.sep, "/")


def textures(base):
    """{"cup": [(colour texture, its metalness texture or None)], "scene": [colour textures]} of
    the models in <base> (paths under a phase folder, with /, as the files are spelt), each once:
    the cup's (common/demo/prop/cup_*) and the ceremony's (the rest). A texture the game has, not
    the folder, is not one a variant can change; one a model uses as anything but its colour is
    never taken for one."""
    cup, scene, other = [], [], set()
    for ph in phase_roots(base):
        root = os.path.join(base, ph)
        for parts in MODEL_DIRS:
            top = os.path.join(root, *parts)
            for d in sorted(os.listdir(top)) if os.path.isdir(top) else []:
                win = os.path.join(top, d, "#Win")
                for f in sorted(os.listdir(win)) if os.path.isdir(win) else []:
                    if not f.lower().endswith(".fpk"):
                        continue
                    try:
                        files = fpk_files(open(os.path.join(win, f), "rb").read())
                    except (Error, OSError, struct.error):
                        continue
                    for n, m in sorted(files.items()):
                        if not n.lower().endswith(".fmdl"):
                            continue
                        try:
                            mats = fmdl_materials(m)
                        except (Error, struct.error, IndexError):
                            continue
                        is_cup = parts[-1] == "prop" and d.lower().startswith("cup_")
                        for _mat, binds in mats:
                            got = {}
                            for p, name, folder in binds:
                                if not folder.startswith("/Assets/pes16/"):
                                    continue
                                rel = _on_disk(root, "common/" + folder[len("/Assets/pes16/"):].strip("/")
                                               + "/#windx11/" + os.path.splitext(name)[0] + ".ftex")
                                if rel:
                                    got.setdefault(p, rel)
                                    if p != ALBEDO:
                                        other.add(rel.lower())
                            if ALBEDO not in got:
                                continue
                            if is_cup:
                                pair = (got[ALBEDO], got.get(METALNESS))
                                if pair[0] not in [c for c, _m in cup]:
                                    cup.append(pair)
                            elif got[ALBEDO] not in scene:
                                scene.append(got[ALBEDO])
    # a colour texture in the folder for a model the game has (no fpk of it here): the
    # game's model finds it by its path all the same -- the Fox name of a colour texture ends _bsm
    for ph in phase_roots(base):
        root = os.path.join(base, ph)
        for parts in MODEL_DIRS:
            top = os.path.join(root, *parts)
            for d, subs, fs in sorted(os.walk(top)) if os.path.isdir(top) else []:
                subs[:] = sorted(x for x in subs if x.lower() not in SKIP_DIRS)
                for f in sorted(fs):
                    stem = os.path.splitext(f)[0].lower()
                    if f.lower().endswith(".ftex") and (stem.endswith("_bsm") or stem.endswith("_nomip_bsm")):
                        rel = os.path.relpath(os.path.join(d, f), root).replace(os.sep, "/")
                        if rel.lower() not in other and rel not in scene and rel not in [c for c, _m in cup]:
                            scene.append(rel)
    cups = {c.lower() for c, _m in cup}
    return {"cup": [(c, m) for c, m in cup if c.lower() not in other],
            "scene": [s for s in scene if s.lower() not in other and s.lower() not in cups]}


# ---- the pictures --------------------------------------------------------------------------------

def hexrgb(c):
    if isinstance(c, (tuple, list)):
        return tuple(int(x) for x in c[:3])
    c = str(c).strip().lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def lum(c):
    return sum(k * v for k, v in zip(LUMA, c)) / 255.0


def panels_of(base, path, rel):
    """the logo panels of the cup texture <rel> of <base> (variant.json, else PANELS by md5)"""
    try:
        own = json.load(open(os.path.join(base, "variant.json"), encoding="utf-8")).get("panels") or {}
        if os.path.basename(rel) in own:
            return [tuple(p) for p in own[os.path.basename(rel)]]
    except (OSError, ValueError, AttributeError):
        pass
    return PANELS.get(hashlib.md5(open(path, "rb").read()).hexdigest(), [])


def fit(pic, w, h, fill=0.8):
    """<pic> cut to what is drawn of it and scaled into w x h (fill of the smaller side)"""
    from PIL import Image
    pic = pic.convert("RGBA")
    bb = pic.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    if bb:
        pic = pic.crop(bb)
    k = fill * min(w / pic.width, h / pic.height)
    return pic.resize((max(1, int(pic.width * k)), max(1, int(pic.height * k))), Image.LANCZOS)


def text_picture(text, w, h, colour):
    """<text> in bold capitals, as large as fits w x h, on transparency"""
    from PIL import Image, ImageDraw, ImageFont
    text = " ".join(str(text or "").upper().split())
    if not text or w < 8 or h < 8:
        return None
    size = max(8, int(h * 0.7))
    while True:
        try:
            font = ImageFont.truetype(FONT, size)
        except OSError:
            font = ImageFont.load_default()
        box = ImageDraw.Draw(Image.new("L", (1, 1))).textbbox((0, 0), text, font=font)
        if box[2] - box[0] <= w * 0.94 or size <= 8:
            break
        size = max(8, int(size * 0.9))
    out = Image.new("RGBA", (box[2] - box[0] + 4, box[3] - box[1] + 4), (0, 0, 0, 0))
    ImageDraw.Draw(out).text((2 - box[0], 2 - box[1]), text, font=font, fill=tuple(colour) + (255,))
    return out


def ink_on(c):
    """white or near black, whichever reads on colour c"""
    return (250, 250, 250) if lum(c) < 0.45 else (20, 20, 24)


def split(y, bins=64):
    """the brightness that best splits <y> (numbers 0..1) in two (Otsu): a ribbon from a plinth,
    the light part of a cloth from its dark"""
    import numpy as np
    hist, edges = np.histogram(y, bins=bins, range=(0.0, 1.0))
    p = hist.astype(np.float64) / max(hist.sum(), 1)
    mids = (edges[:-1] + edges[1:]) / 2
    w0 = np.cumsum(p)
    m0 = np.cumsum(p * mids)
    mt = m0[-1]
    w1 = 1.0 - w0
    with np.errstate(divide="ignore", invalid="ignore"):
        between = np.where((w0 > 0) & (w1 > 0), (mt * w0 - m0) ** 2 / (w0 * w1), 0.0)
    if not between.any():
        return float(np.median(y))
    return float(edges[int(between.argmax()) + 1])


def recolour(im, metal, colours, panels=(), logo=None):
    """the cup's colour texture <im> as the variant's: the metal (unsaturated parts and the yellows
    of gold, most of a trophy) toned to <metal>, every other coloured part (ribbons, a plinth) to
    the first or the second of <colours> with its shading kept, the panels painted over in the
    metal with <logo> in the middle. (picture, the panel boxes in pixels)"""
    import numpy as np
    from PIL import Image
    a = np.asarray(im.convert("RGBA"), dtype=np.float32) / 255.0
    rgb, alpha = a[..., :3], a[..., 3:]
    mx, mn = rgb.max(-1), rgb.min(-1)
    y = rgb @ np.array(LUMA, dtype=np.float32)
    sat = np.where(mx > 1e-4, (mx - mn) / np.maximum(mx, 1e-4), 0.0)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    d = np.maximum(mx - mn, 1e-6)
    hue = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60.0
    goldish = (hue >= 22) & (hue <= 65) & (y > 0.12)
    is_metal = ((sat < 0.22) | goldish) & (y > 0.03)
    m = np.array(METALS.get(metal, METALS["gold"]), dtype=np.float32) / 255.0
    ref = float(np.percentile(y[is_metal], 75)) if is_metal.any() else 0.6
    tone = np.clip(y / max(ref, 0.05), 0.0, 1.6)[..., None]
    metal_px = np.clip(m * tone + np.clip(tone - 1.0, 0, None) * 0.35, 0, 1)
    cols = [np.array(hexrgb(c), dtype=np.float32) / 255.0 for c in (colours or [])] or [m]
    out = rgb.copy()
    out[is_metal] = metal_px[is_metal]
    is_col = (~is_metal) & (sat >= 0.22) & (y > 0.015)
    if is_col.any():
        cut = split(y[is_col])
        pick = np.where(y >= cut, 0, min(1, len(cols) - 1))
        for k, c in enumerate(cols[:2]):
            sel = is_col & (pick == k)
            if sel.any():
                cy = max(float(c @ np.array(LUMA, dtype=np.float32)), 0.02)
                shade = np.clip(y / cy, 0.3, 1.8)[..., None]
                out[sel] = np.clip(c * shade, 0, 1)[sel]
    res = Image.fromarray((np.concatenate([out, alpha], -1) * 255 + 0.5).astype(np.uint8), "RGBA")
    w, h = res.size
    boxes = []
    for x0, y0, x1, y1 in panels:
        box = (int(x0 * w), int(y0 * h), min(w, int(x1 * w)), min(h, int(y1 * h)))
        bw, bh = box[2] - box[0], box[3] - box[1]
        if bw < 4 or bh < 4:
            continue
        plate = tuple(int(v * 230) for v in m) + (255,)
        panel = Image.new("RGBA", (bw, bh), plate)
        if logo is not None:
            lg = fit(logo, bw, bh)
            panel.alpha_composite(lg, ((bw - lg.width) // 2, (bh - lg.height) // 2))
        res.paste(panel, box[:2])
        boxes.append(box)
    return res, boxes


def panel_metalness(im, boxes, logo=None):
    """the cup's metalness texture with the panels metal again (the base's decals were not) and
    <logo>, where it is drawn, not metal: the logo reads as paint on the plate"""
    from PIL import Image
    res = im.convert("RGBA").copy()
    sw, sh = res.size
    for box in boxes:
        bw, bh = box[2] - box[0], box[3] - box[1]
        panel = Image.new("RGBA", (bw, bh), (255, 255, 255, 255))
        if logo is not None:
            lg = fit(logo, bw, bh)
            dark = Image.new("RGBA", lg.size, (0, 0, 0, 255))
            panel.paste(dark, ((bw - lg.width) // 2, (bh - lg.height) // 2), lg.getchannel("A"))
        res.paste(panel, box[:2])
    return res


def decal_boxes(mask, grow=3, least=4):
    """the boxes (x0, y0, x1, y1) of the groups of True in a small 2-D mask, each grown a little"""
    import numpy as np
    m = mask.copy()
    for _ in range(grow):
        g = m.copy()
        g[1:] |= m[:-1]
        g[:-1] |= m[1:]
        g[:, 1:] |= m[:, :-1]
        g[:, :-1] |= m[:, 1:]
        m = g
    h, w = m.shape
    seen = np.zeros_like(m)
    out = []
    for sy in range(h):
        for sx in range(w):
            if not m[sy, sx] or seen[sy, sx]:
                continue
            stack, x0, y0, x1, y1, n = [(sy, sx)], sx, sy, sx, sy, 0
            seen[sy, sx] = True
            while stack:
                cy, cx = stack.pop()
                n += 1
                x0, y0, x1, y1 = min(x0, cx), min(y0, cy), max(x1, cx), max(y1, cy)
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if 0 <= ny < h and 0 <= nx < w and m[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
            if n >= least:
                out.append((x0, y0, x1 + 1, y1 + 1))
    return out


def skin(im):
    """the share of a picture in the colours of skin (a face, an arm): a texture of people"""
    import numpy as np
    from PIL import Image
    a = np.asarray(im.convert("RGB").resize((256, 256), Image.BOX), dtype=np.float32) / 255.0
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a.max(-1), a.min(-1)
    sat = (mx - mn) / np.maximum(mx, 1e-4)
    return float(((r > g) & (g > b) & (r - b > 0.12) & (r - g > 0.04) & (sat > 0.18) & (sat < 0.65)
                  & (mx > 0.35)).mean())


def rebrand(im, colours, logo=None, name=""):
    """a ceremony texture (a flag, a banner, the stand) as the variant's, or None when it is not
    one to rebrand: a flat background colour (FLAT of it, not grey) with decals on it. The
    background becomes the first of <colours> with the cloth's shading kept, each decal its logo
    (a squarish one) or its name (a wide one)."""
    import numpy as np
    from PIL import Image
    src = im.convert("RGBA")
    small = np.asarray(src.resize((128, 128), Image.BOX), dtype=np.float32)
    q = (small[..., :3] // 16).astype(np.int32)
    codes = q[..., 0] * 256 + q[..., 1] * 16 + q[..., 2]
    vals, counts = np.unique(codes, return_counts=True)
    top = vals[counts.argmax()]
    bg = small[..., :3][codes == top].mean(0)
    near = np.abs(small[..., :3] - bg).max(-1) <= 40
    h_, s_, v_ = colorsys.rgb_to_hsv(*(bg / 255.0))
    if near.mean() < FLAT or s_ < 0.25 or small[..., 3].mean() < 200 or skin(src) > SKIN:
        return None
    new = np.array(hexrgb(colours[0]) if colours else (30, 60, 140), dtype=np.float32)
    a = np.asarray(src, dtype=np.float32)
    w, h = src.size
    by = max(lum(bg), 0.02)
    y = (a[..., :3] @ np.array(LUMA, dtype=np.float32)) / 255.0
    full_near = np.abs(a[..., :3] - bg).max(-1) <= 48
    shade = np.clip(y / by, 0.5, 1.5)[..., None]
    out = a.copy()
    out[..., :3] = np.where(full_near[..., None], np.clip(new * shade, 0, 255), a[..., :3])
    res = Image.fromarray(out.astype(np.uint8), "RGBA")
    fill = tuple(int(v) for v in new) + (255,)
    ink = ink_on(new)
    for x0, y0, x1, y1 in decal_boxes(~near):
        box = (x0 * w // 128, y0 * h // 128, min(w, x1 * w // 128), min(h, y1 * h // 128))
        bw, bh = box[2] - box[0], box[3] - box[1]
        if bw < 6 or bh < 6 or bw * bh > 0.6 * w * h:
            continue
        panel = Image.new("RGBA", (bw, bh), fill)
        pic = None
        if bw <= 2.2 * bh and logo is not None:
            pic = fit(logo, bw, bh, 0.9)
        elif name:
            pic = text_picture(name, bw, bh, ink)
        elif logo is not None:
            pic = fit(logo, bw, bh, 0.9)
        if pic is not None:
            panel.alpha_composite(pic, ((bw - pic.width) // 2, (bh - pic.height) // 2))
        res.paste(panel, box[:2])
    return res


# ---- the variant -------------------------------------------------------------------------------

def _src(base, rel):
    return next((os.path.join(base, ph, *rel.split("/")) for ph in phase_roots(base)
                 if os.path.isfile(os.path.join(base, ph, *rel.split("/")))), None)


_LOADED = {}


def _load(path, side=MAX_SIDE):
    """(picture no larger than side, ftex format, the file's bytes) of an .ftex; read once a run
    (every variant of a base starts from the same textures)"""
    from PIL import Image
    k = (os.path.normcase(os.path.abspath(path)), side)
    if k in _LOADED:
        return _LOADED[k]
    b = open(path, "rb").read()
    fmt = ftex_head(b)[0]
    im = read_ftex(path)
    if max(im.size) > side:
        f = side / max(im.size)
        im = im.resize((max(4, int(im.width * f) // 4 * 4), max(4, int(im.height * f) // 4 * 4)), Image.LANCZOS)
    if len(_LOADED) > 64:
        _LOADED.clear()
    _LOADED[k] = (im, fmt, b)
    return _LOADED[k]


def variant_textures(spec):
    """{path under the phase folder (with /): (picture, ftex format, the base's bytes)} of the
    variant <spec>: each texture of its base it changes, once"""
    from PIL import Image
    base = spec["base"]
    logo = Image.open(spec["logo"]).convert("RGBA") if spec.get("logo") else None
    cols = list(spec.get("colours") or []) or (logo_colours(spec["logo"]) if logo else [])
    tex = textures(base)
    if not tex["cup"]:
        raise Error("%s: no trophy model with its colour texture in the folder (common\\demo\\prop\\cup_*\\#Win"
                    "\\*.fpk naming one in #windx11)" % base)
    out = {}
    for rel, mrel in tex["cup"]:
        path = _src(base, rel)
        im, fmt, b = _load(path)
        pic, boxes = recolour(im, spec.get("metal") or "gold", cols, panels_of(base, path, rel), logo)
        out[rel] = (pic, fmt, b)
        if boxes and mrel and mrel not in out:
            mim, mfmt, mb = _load(_src(base, mrel))
            k = (mim.width / pic.width, mim.height / pic.height)
            mboxes = [(int(x0 * k[0]), int(y0 * k[1]), int(x1 * k[0]), int(y1 * k[1])) for x0, y0, x1, y1 in boxes]
            out[mrel] = (panel_metalness(mim, mboxes, logo), mfmt, mb)
    for rel in tex["scene"]:
        try:
            im, fmt, b = _load(_src(base, rel), MAX_SCENE)
        except (Error, OSError, ValueError, struct.error, zlib.error):
            continue                    # a format this cannot write back (BC7 ...): the base's stays
        if fmt not in FORMATS:
            continue
        pic = rebrand(im, cols, logo, spec.get("name") or "")
        if pic is not None:
            out[rel] = (pic, fmt, b)
    return out


def write(spec, out):
    """the variant's own files under <out>: each texture it changes, in every phase folder of the
    base that has it. [the paths written, with /, under the phase folder]"""
    tex = variant_textures(spec)
    done = []
    for ph in phase_roots(spec["base"]):
        for rel, (im, fmt, like) in tex.items():
            if not os.path.isfile(os.path.join(spec["base"], ph, *rel.split("/"))):
                continue
            dst = os.path.join(out, ph, *rel.split("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as f:
                f.write(ftex_bytes(im, fmt, like))
            if rel not in done:
                done.append(rel)
    return done


def preview(spec, png, size=384):
    """a sheet of the textures the variant changes, the base's above and the variant's below"""
    from PIL import Image, ImageDraw
    tex = variant_textures(spec)
    cells = []
    for rel, (pic, _f, _b) in tex.items():
        a = read_ftex(_src(spec["base"], rel))
        a.thumbnail((size, size))
        cells.append((os.path.basename(rel), a, pic.resize(a.size, Image.LANCZOS)))
    sheet = Image.new("RGBA", (len(cells) * (size + 8), 2 * size + 40), (40, 40, 40, 255))
    dr = ImageDraw.Draw(sheet)
    for i, (n, a, b) in enumerate(cells):
        x = i * (size + 8)
        for k, p in enumerate((a, b)):
            bg = Image.new("RGBA", p.size, (90, 90, 90, 255))
            bg.alpha_composite(p)
            sheet.alpha_composite(bg, (x, 16 + k * (size + 12)))
        dr.text((x + 2, 2), n, fill=(255, 255, 0, 255))
    sheet.convert("RGB").save(png)
    return png


# ---- every competition its own -----------------------------------------------------------------

def logo_colours(path, n=2):
    """the n commonest strong colours of a logo picture, #rrggbb, most used first"""
    from PIL import Image
    try:
        im = Image.open(path).convert("RGBA")
    except (OSError, ValueError):
        return []
    im.thumbnail((128, 128))
    seen = {}
    for r, g, b, a in im.getdata():
        if a < 128:
            continue
        h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        if v < 0.12 or s < 0.3:
            continue
        e = seen.setdefault((int(h * 12) % 12, int(v * 3)), [0, 0, 0, 0])
        e[0] += 1
        e[1] += r
        e[2] += g
        e[3] += b
    out = []
    for cnt, r, g, b in sorted(seen.values(), reverse=True):
        c = "#%02x%02x%02x" % (r // cnt, g // cnt, b // cnt)
        if c not in out:
            out.append(c)
        if len(out) == n:
            break
    return out


# the colours of a competition whose logo gives none (no logo, or one of greys), by its hash
PALETTE = ("#1f4e9c", "#c8102e", "#0b7a3e", "#5b2c83", "#e87722", "#00838f", "#7a1f2b", "#2e3a87",
           "#b38f00", "#00594f", "#8a1538", "#3c6e71")


def key(name, cid):
    """a competition's number for the hash: of its name (ids move when a recipe changes), of its
    id when it has none"""
    s = str(name or "").strip().casefold() or "#%s" % cid
    return int(hashlib.sha1(s.encode("utf-8")).hexdigest()[:12], 16)


def auto(comps, bases, logos=None):
    """{competition id: spec} for <comps> [(competition id, name)]: the base and the metal from a
    hash of the name, so a competition has the same trophy every Build; the colours from its logo
    (<logos>: {id: png}), else from the hash. Two the hash makes alike: the later (by hash, then
    name, then id) takes the next base and metal, so no two in a world are the same."""
    bases = [b for b in bases if b and os.path.isdir(b)]
    if not bases:
        return {}
    logos = logos or {}
    combos = [(b, m) for m in METAL_ORDER for b in bases]
    taken, out = set(), {}
    for cid, name in sorted(comps, key=lambda c: (key(c[1], c[0]), str(c[1]), int(c[0]))):
        k = key(name, cid)
        logo = logos.get(cid) or logos.get(str(cid)) or None
        cols = logo_colours(logo) if logo else []
        j = 0
        while len(cols) < 2:
            c = PALETTE[(k >> (5 * j)) % len(PALETTE)]
            if c not in cols:
                cols.append(c)
            j += 1
        start = k % len(combos)
        for step in range(len(combos)):
            b, m = combos[(start + step) % len(combos)]
            if (b, m, tuple(cols), logo) not in taken:
                break
        taken.add((b, m, tuple(cols), logo))
        out[int(cid)] = {"base": b, "metal": m, "colours": cols, "logo": logo, "name": name or ""}
    return out


def main(argv):
    pre = argv[:1] == ["--preview"]
    if pre:
        argv = argv[1:]
    name = ""
    if "--name" in argv:
        i = argv.index("--name")
        name = argv[i + 1] if i + 1 < len(argv) else ""
        argv = argv[:i] + argv[i + 2:]
    if len(argv) < 3:
        print(__doc__)
        return 2
    base, out, metal = argv[:3]
    cols = [c for c in argv[3:] if c.startswith("#")]
    logo = next((c for c in argv[3:] if not c.startswith("#")), None)
    spec = {"base": base, "metal": metal, "colours": cols, "logo": logo, "name": name}
    if pre:
        print(preview(spec, out))
    else:
        for rel in write(spec, out):
            print(rel)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
