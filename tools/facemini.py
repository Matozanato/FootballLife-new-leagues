r"""facemini.py -- the face pool's small pictures (portraits) from the game's own render of each face.

The face pool (tools/facepool.py, fl26regen_faces.bin "FL26RF02") holds 32,000 faces as numbers
and no portraits (portrait number 0xffff), so a regen or a new player with a pool face shows the
grey silhouette in lineups and Game Plan. fl26regen's capture mode (modules\fl26regen_capture.txt,
see sider/fl26regen.lua) draws one chosen player with pool face k on Edit's player screen; a
screenshot of that screen per face is the input here.

  convert <shots dir> <out dir> [--box X,Y,SIDE | --box auto] [--shirt grey|keep] [--glob mini_*.png]
        every <shots dir>\mini_<k>.png -> <out dir>\FL26 Regen Faces\common\render\symbol\player\
        regen\<k>.dds (the game's portrait: 128 x 128 DXT5, one mip, a transparent background),
        <out dir>\preview\<k>.png, a contact sheet and report.txt (the faces to look at again).
        --box auto: the box measured on these shots first (calibrate), for another capture player
  calibrate <shots dir> [--box X,Y,SIDE]
        the box that frames these shots' heads as the game frames its own portraits (GAME_HEADW,
        GAME_NECK): the median of up to 40 shots, so one odd hair style does not move it
  rank <list.txt> [--n 1000] [--pool fl26regen_faces.bin]
        the faces to capture, best first (see NONE): the first ~100 cover every group and the
        common looks, the next ones the rarer looks. tools/facecap.py --faces <list.txt> captures
        them in this order and can stop anywhere
  share <out dir> [--pool fl26regen_faces.bin]
        like pack, for a pool with only some pictures: every face's portrait number points at the
        picture of the captured face that looks most like it (same group, skin, hair, beard, age;
        a captured face keeps its own; another group's picture only if it looks close, else none),
        <out dir>\share.tsv the map. Run it again after every
        capture: FL26_REGEN_FACES=<out dir> then ships the pictures and the pack
  frame <picture.png|.dds> ...
        the framing numbers of portraits (the game's own, ours): top of the hair, head width, the
        narrowest row under the head (jaw and neck) and the width of the bottom row, at 128 pixels
  pack <pool fl26regen_faces.bin> <out dir>
        <out dir>\fl26regen_faces.bin: the pool with portrait number k for every face k that has
        a .dds in <out dir>, 0xffff (none) for the others. With FL26_REGEN_FACES=<out dir>
        tools/lbpack.py puts both in Mod Studio's module pack (modules + livecpk "FL26 Regen Faces")
  show <shot.png> [--box X,Y,SIDE]
        the box drawn on the screenshot and the picture it makes (to set --box)

The picture (600 of the game's own 26,121 portraits in dt14_all.cpk, FL27, all 128 x 128 DXT5,
measured with `frame` 18.11.; median, 10th-90th percentile): alpha 0 around the player; the top of
the hair at row 15 (4-18), the head (hair and ears) 67 pixels wide (62-83, GAME_HEADW), the narrowest
row under it (jaw and neck) at row 93 (87-106, GAME_NECK), the shirt across the bottom row (119 of
128 pixels). Game Plan draws the
whole picture at about 74 screen pixels with the position bar under it, so the neck and the collar
show. On Edit's player screen (the 1924 x 1084 window shot) the capture player's head is at x
1555-1770, chin at y 440: the box 1459,125 with a side of 417 frames it as the game does (calibrate
on the 06.11. pilot's shots: head 218 pixels wide, neck at y 428). The 06.11. box (1432,110,459)
made the head 10% smaller than the game's (60 pixels, not 67) and the neck 5 rows higher (88, not 93). What mato saw cut at the chin (18.11., and 06.11.: "a lineup's small picture
cut the beard off") was the 30.09. pack's 103 pictures (180 x 180, the head 85-105 pixels of 128 wide,
nothing under the chin), shipped in every release up to beta4: not this tool's.
The capture player is always the same player (the same height), so his head is always in the same
place; another capture player: `calibrate` (or convert --box auto). His kit must have no red: the
menu is found by its red, and a red shirt would be cut out with it (the shirt check tells).

The red menu behind the head: every pixel of it has almost no green and blue (the grid lines, the
glow, the black between them, the grey panel's edge are all (r, <12, <12) or r far above g and b),
and no pixel of a head, hair or shirt has. What is left is the player, cleaned up (the one
connected figure, holes filled, the edge pulled in a pixel and its colour taken from inside, so
no red fringe), and scaled down.

--shirt grey (the default) takes the colour out of the shirt below the chin: the capture player's
club kit would otherwise be on every regen's picture of every club.
"""
import glob
import os
import re
import struct
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
SIZE = 128                         # the game's player portraits (lbpack.PORTRAIT)
BOX = (1459, 125, 417)             # x, y, side in the screenshot (see the docstring)
GAME_HEADW = 67                    # the game's portraits: the head's width (hair, ears), of 128
GAME_NECK = 93                     # ... and the narrowest row under the head (jaw, neck)
FACE_ROOT = "FL26 Regen Faces"
REGEN_DIR = os.path.join(FACE_ROOT, "common", "render", "symbol", "player", "regen")
DARK = 12                          # background: green and blue both below this ...
RED = 0.38                         # ... or both below RED * red
CHIN = (GAME_NECK + 4) / 128.0     # the chin's row, of the box's height
CROP_KEY = "fl26crop"              # a shot saved cropped (tools: facecap) keeps "x,y" of its corner here
SHOT = re.compile(r"mini_(\d+)\.png$", re.I)


# ---- the picture -----------------------------------------------------------------------------
def background(rgb):
    """True where a pixel is the red menu behind the player"""
    r, g, b = (rgb[..., i].astype(np.int32) for i in range(3))
    return (np.maximum(g, b) < DARK) | ((g < RED * r) & (b < RED * r))


def figure(rgb):
    """the player's mask (bool) in the box: the connected figure over the head's middle. Worked
    on with the box's edge pixels repeated around it: where the box cuts the player (the shirt at
    the bottom), he stays opaque to the edge"""
    h, w = rgb.shape[:2]
    P = 8
    fg = np.pad(~background(rgb), P, mode="edge")
    fg = ndimage.binary_opening(fg, np.ones((3, 3), bool))
    lab, n = ndimage.label(fg)
    if not n:
        return fg[P:-P, P:-P]
    seed = np.zeros_like(fg)
    seed[P + int(0.30 * h):P + int(0.62 * h), P + int(0.40 * w):P + int(0.60 * w)] = True
    sizes = ndimage.sum(np.ones_like(lab), lab, index=np.arange(1, n + 1))
    keep = set(int(i) for i in np.unique(lab[seed & (lab > 0)]))
    # the shirt is one with the head through the neck; a big piece on the bottom edge is kept too
    for i in np.unique(lab[-1][lab[-1] > 0]):
        if sizes[i - 1] > 0.02 * h * w:
            keep.add(int(i))
    if not keep:
        return np.zeros((h, w), bool)
    m = np.isin(lab, list(keep))
    m = ndimage.binary_closing(m, structure=disk(4), iterations=1)
    m = ndimage.binary_fill_holes(m)
    return m[P:-P, P:-P]


def disk(r):
    y, x = np.mgrid[-r:r + 1, -r:r + 1]
    return x * x + y * y <= r * r


def skin_colour(rgb, m):
    """the face's own colour: the middle of the face (nose and cheeks)"""
    h, w = m.shape
    sl = (slice(int(0.45 * h), int(0.62 * h)), slice(int(0.42 * w), int(0.58 * w)))
    px = rgb[sl][m[sl]]
    return np.median(px, axis=0) if len(px) else np.array([180.0, 140.0, 120.0])


def grey_shirt(rgb, m, chin=CHIN):
    """the colour out of everything below the chin (a fraction of the height) that is not skin
    (the shirt, its badge)"""
    h, w = m.shape
    out = rgb.astype(np.float32).copy()
    s = skin_colour(rgb, m)
    tot = out.sum(axis=2, keepdims=True) + 1e-3
    chroma = out[..., :2] / tot                      # r and g of r+g+b
    sk = s[:2] / (s.sum() + 1e-3)
    d = np.sqrt(((chroma - sk) ** 2).sum(axis=2))
    skin = d < 0.035
    skin = ndimage.binary_opening(skin, np.ones((3, 3), bool))
    y = np.arange(h)[:, None] / float(h)
    below = np.clip((y - (chin - 0.02)) / 0.04, 0, 1)  # a soft start just above the chin
    amount = below * (~skin)
    amount = ndimage.gaussian_filter(amount.astype(np.float32), 2.0)
    lum = (0.299 * out[..., 0] + 0.587 * out[..., 1] + 0.114 * out[..., 2])[..., None]
    out = out * (1 - amount[..., None]) + lum * amount[..., None]
    return np.clip(out, 0, 255).astype(np.uint8)


def frame(mask):
    """the framing of a portrait's mask (bool, square), in pixels of a 128 picture: {top (the hair's
    first row), headw (the widest row of the head's top half: hair and ears), cx (the head's middle),
    neck (the narrowest row under the head: jaw and neck), bottomw (the bottom row's width)}; None
    with nothing in it"""
    n = mask.shape[0]
    s = SIZE / float(n)
    rows = np.where(mask.any(axis=1))[0]
    if not len(rows):
        return None
    left = np.where(mask.any(axis=1), mask.argmax(axis=1), 0)
    right = np.where(mask.any(axis=1), n - 1 - mask[:, ::-1].argmax(axis=1), -1)
    w = right - left + 1
    top = rows[0]
    half = slice(top, min(n, top + int(0.47 * n)))
    hw_row = top + int(w[half].argmax())
    mid = slice(top + int(0.20 * n), min(n, top + int(0.35 * n)))
    cx = float(np.median((left[mid] + right[mid]) / 2.0)) if w[mid].max() > 0 else n / 2.0
    below = w[hw_row + int(0.08 * n):]
    neck = hw_row + int(0.08 * n) + int(below.argmin()) if len(below) else n
    return {"top": round(float(top) * s, 1), "headw": round(float(w[half].max()) * s, 1), "cx": round(cx * s, 1),
            "neck": round(float(neck) * s, 1), "bottomw": round(float(max(w[-1], 0)) * s, 1)}


def origin(shot):
    """(x, y) of a shot's top left corner in the game window: (0, 0), or the corner a cropped shot
    keeps in its CROP_KEY text"""
    v = (getattr(shot, "info", None) or {}).get(CROP_KEY)
    if not v:
        return 0, 0
    x, y = (int(t) for t in str(v).split(","))
    return x, y


def in_box(shot, box):
    """the box's pixels (RGB array) of a screenshot, whole or cropped"""
    x, y, side = box
    ox, oy = origin(shot)
    return np.asarray(shot.convert("RGB").crop((x - ox, y - oy, x - ox + side, y - oy + side)))


def portrait(shot, box=BOX, shirt="grey"):
    """screenshot (PIL image) -> (128 x 128 RGBA image, {notes}); notes["bad"] says why a shot
    must be made again: a black or wrong screen, no player, the head not where the box expects
    it, a see-through shirt"""
    x, y, side = box
    rgb = in_box(shot, box)
    notes = {}
    lum = rgb.astype(np.float32).mean()
    if lum < 8:
        return Image.new("RGBA", (SIZE, SIZE)), dict(notes, bad="a black screen (mean %.1f)" % lum)
    m = figure(rgb)
    inner = ndimage.binary_erosion(m, iterations=1, border_value=1)
    area = inner.mean()
    notes["area"] = round(float(area), 3)
    rows = np.where(inner[:, int(0.4 * side):int(0.6 * side)].any(axis=1))[0]
    notes["top"] = round(float(rows[0]) / side, 3) if len(rows) else 1.0
    # Edit's red menu is behind the head: the top corners of the box are menu, not something else
    c = int(0.18 * side)
    corners = np.concatenate([background(rgb[:c, :c]).ravel(), background(rgb[:c, -c:]).ravel()])
    notes["menu"] = round(float(corners.mean()), 2)
    if not inner.any():
        return Image.new("RGBA", (SIZE, SIZE)), dict(notes, bad="no player found")
    fr = frame(inner)
    notes.update({k: fr[k] for k in ("headw", "neck", "bottomw")})
    # the edge's colour from the nearest pixel inside that is the player's own: no red fringe, and no
    # menu red in a corner the closing filled (beside the neck, over the glow)
    own = inner & ~background(rgb)
    idx = ndimage.distance_transform_edt(~(own if own.any() else inner), return_distances=False, return_indices=True)
    col = rgb[idx[0], idx[1]]
    if shirt == "grey":
        # under this face's own chin: a long face or long hair has it lower, and its stubble stays
        col = grey_shirt(col, inner, min(0.9, max(CHIN, (fr["neck"] + 4) / float(SIZE))))
    alpha = ndimage.gaussian_filter(inner.astype(np.float32), 1.0)
    rgba = np.dstack([col, np.clip(alpha * 255 + 0.5, 0, 255).astype(np.uint8)])
    im = Image.fromarray(rgba, "RGBA").convert("RGBa").resize((SIZE, SIZE), Image.LANCZOS).convert("RGBA")
    a = np.asarray(im)[..., 3]
    if notes["menu"] < 0.6:
        notes["bad"] = "no red menu behind the head (%d%% of the corners): not Edit's player screen" % round(100 * notes["menu"])
    elif area < 0.25 or area > 0.80:
        notes["bad"] = "the figure is %d%% of the box" % round(100 * area)
    elif notes["top"] > 0.25 or notes["top"] < 0.01:
        notes["bad"] = "the top of the head at %d%% of the box" % round(100 * notes["top"])
    elif a[:4].max() > 200 and a[:4, :].mean() > 60:
        notes["bad"] = "something opaque along the top edge"
    elif fr["bottomw"] < 0.5 * SIZE:
        notes["bad"] = "the shirt is see-through at the bottom (%d of %d): a red kit?" % (fr["bottomw"], SIZE)
    elif abs(fr["neck"] - GAME_NECK) > 16:      # long hair over the neck: up to 11 rows lower
        notes["bad"] = "the neck at row %d, not about %d: the head is not where the box expects it" % (fr["neck"], GAME_NECK)
    elif not 48 <= fr["headw"] <= 92:
        notes["bad"] = "the head %d pixels wide, not about %d" % (fr["headw"], GAME_HEADW)
    return im, notes


def calibrate(shots, box=BOX, log=print):
    """the box that frames these shots' heads as the game frames its portraits: their median head
    width to GAME_HEADW, their median neck row to GAME_NECK, the head in the middle. Twice, as the
    figure is found from the box's middle"""
    shots = list(shots)
    if len(shots) > 40:
        shots = shots[::max(1, len(shots) // 40)][:40]
    for _ in range(2):
        x, y, side = box
        f = []
        for p in shots:
            sh = Image.open(p) if isinstance(p, str) else p
            m = figure(in_box(sh, box))
            fr = frame(ndimage.binary_erosion(m, iterations=1, border_value=1))
            if fr and 0.2 < m.mean() < 0.85:
                f.append(fr)
        if not f:
            raise SystemExit("calibrate: no player found in the shots with the box %s" % (box,))
        k = side / float(SIZE)
        hw = float(np.median([v["headw"] for v in f])) * k
        neck = y + float(np.median([v["neck"] for v in f])) * k
        cx = x + float(np.median([v["cx"] for v in f])) * k
        nside = int(round(hw * SIZE / GAME_HEADW))
        box = (int(round(cx - nside / 2.0)), int(round(neck - GAME_NECK * nside / float(SIZE))), nside)
    log("calibrate: %d shots, the head %.0f pixels wide, the neck at y %.0f, the middle at x %.0f -> --box %d,%d,%d"
        % (len(f), hw, neck, cx, box[0], box[1], box[2]))
    return box


def game_header(w=SIZE, h=SIZE):
    """the 128-byte header of the game's own portraits (dt14_all.cpk, unpacked from WESYS): flags
    caps|height|width|pixelformat|mipmapcount|linearsize, linear size w*h, depth 1, one mip, DXT5"""
    hd = bytearray(128)
    hd[0:4] = b"DDS "
    struct.pack_into("<IIIIIII", hd, 4, 124, 0x000A1007, h, w, w * h, 1, 1)
    struct.pack_into("<II4s", hd, 76, 32, 0x4, b"DXT5")
    struct.pack_into("<I", hd, 108, 0x1000)       # caps: texture
    return bytes(hd)


def dds_bytes(im):
    """a 128 x 128 RGBA image -> the game's portrait file (DXT5, one mip: 16,512 bytes), with the
    header exactly as the game's own portraits have it (Pillow writes a pitch and no mip count)"""
    import io
    b = io.BytesIO()
    im.save(b, "DDS", pixel_format="DXT5")
    data = b.getvalue()
    assert data[84:88] == b"DXT5" and len(data) == 128 + im.size[0] * im.size[1], len(data)
    return game_header(*im.size) + data[128:]


def check_dds(data):
    """(width, height, fourcc, mips) of a .dds"""
    assert data[:4] == b"DDS ", "not a dds"
    h, w = struct.unpack_from("<II", data, 12)
    mips = struct.unpack_from("<I", data, 28)[0]
    return w, h, data[84:88], mips


# ---- a few pictures for the whole pool (mato 18.11.) -------------------------------------------
# "we can update minifaces gradually, but for now put about a hundred different minifaces, just so
# it's not empty": a face without a picture of its own shows the picture of the captured face that
# looks most like it in a lineup's small picture -- the same group (part of the world), then the
# skin, the hair colour, the hair's length and shape, the beard, the age. The portrait number in
# the pack is only the name of a .dds (fl26regen.c portrait(): g_faces[f].key, never checked or
# counted; the loader asks for regen\<number>.dds), so any number of faces may share one.
# RANK orders the faces to capture: each next one is the face whose picture takes the most off the
# whole pool's distance to its nearest picture (a face with no picture yet in its group counts
# NONE), so the first ones cover every group and the common looks, the later ones the rarer looks;
# a capture can stop anywhere, and `share` maps the pool on whatever was captured.
NONE = 30.0                        # the distance of a face to "no picture" (the grey silhouette)
OTHER_GROUP = 12.0                 # added for a picture of another group (only when its own has none)
CROSS_MAX = 4.0                    # ... and taken only that close (same skin, near hair): else no picture


def looks(faces):
    """the parts of each pool face (facepool.read_pack's [(group, portrait, 56 bytes)]) a 128-pixel
    picture shows: {name: numpy array over the faces}"""
    sys.path.insert(0, HERE)
    import facepool as F
    D = [F.decode(bytes(b)) for _g, _k, b in faces]
    col = lambda *ks: np.array([[d[k] for k in ks] for d in D], np.float32)
    L = {"group": np.array([g for g, _k, _b in faces], np.int16)}
    L["skin"] = col("skin")[:, 0]
    L["hair"] = np.sqrt(col("hair_r", "hair_g", "hair_b") / 63.0)         # brightness as the eye sees it
    L["hrgb"] = col("hair_r", "hair_g", "hair_b")
    L["hlen"] = col("hlen")[:, 0]
    L["hcat"] = np.where(L["hlen"] <= 2, 0, np.where(L["hlen"] == 3, 1, 2)).astype(np.float32)  # short, medium, long
    w = col("hwave")[:, 0]
    L["wave"] = np.where(w <= 1, 0, np.where(w <= 3, 1, 2)).astype(np.float32)   # straight, wavy, curly
    for k in ("hstyle", "hcrop", "hfront", "fhair_t"):
        L[k] = col(k)[:, 0]
    ft, th = L["fhair_t"], col("fh_thick")[:, 0]
    # the beard as much as it shows: none, the stubble type (1), the others (moustache, goatee, beard)
    L["beard"] = np.where(ft == 0, 0.0, np.where(ft == 1, 0.5 + 0.5 * th, 1.0 + 0.5 * th)).astype(np.float32)
    L["old"] = ((col("forehead_t")[:, 0] >= 3) | (col("laugh_t")[:, 0] >= 2)).astype(np.float32)
    return L


def distance(L, i, idx):
    """how unlike face i looks to each face of idx (an index array) in a small picture: 0 the same;
    one skin step 2.5, brown against blond hair 4.5, long against medium hair 2.5, a full beard
    against none 2.5"""
    d = 2.5 * np.abs(L["skin"][idx] - L["skin"][i])
    d += 7.0 * np.sqrt(((L["hair"][idx] - L["hair"][i]) ** 2).sum(axis=1))
    d += 0.5 * np.abs(L["hlen"][idx] - L["hlen"][i]) + 2.0 * np.abs(L["hcat"][idx] - L["hcat"][i])
    d += 1.0 * np.abs(L["wave"][idx] - L["wave"][i])
    d += 0.5 * (L["hstyle"][idx] != L["hstyle"][i]) + 0.3 * (L["hcrop"][idx] != L["hcrop"][i])
    d += 0.2 * (L["hfront"][idx] != L["hfront"][i])
    d += 1.0 * np.abs(L["beard"][idx] - L["beard"][i])
    d += 0.3 * ((L["fhair_t"][idx] != L["fhair_t"][i]) & (L["beard"][idx] > 0) & (L["beard"][i] > 0))
    d += 0.4 * (L["old"][idx] != L["old"][i])
    d += OTHER_GROUP * (L["group"][idx] != L["group"][i])
    return d.astype(np.float32)


def matrix(L, idx):
    """distance(L, i, idx) for every i of idx: an n x n float32 array"""
    return np.stack([distance(L, i, idx) for i in idx])


def rank(faces, n=1000, log=print):
    """the faces to capture, best first: [(face, gain)]. Lazy greedy facility location per group
    (the gain of a pick only falls as others are picked), the groups' picks merged by gain: the
    same order as one greedy over the pool. The first pick of every group comes first of all."""
    import heapq
    L = looks(faces)
    per = {}
    for g in sorted(set(L["group"].tolist())):
        idx = np.where(L["group"] == g)[0]
        M = matrix(L, idx)
        cur = np.full(len(idx), NONE, np.float32)
        heap = [(-float(np.maximum(cur - M[:, c], 0).sum()), c) for c in range(len(idx))]
        heapq.heapify(heap)
        picks = []
        while heap and len(picks) < min(n, len(idx)):
            _neg, c = heapq.heappop(heap)
            gain = float(np.maximum(cur - M[:, c], 0).sum())
            if heap and gain < -heap[0][0] - 1e-6:
                heapq.heappush(heap, (-gain, c))
                continue
            picks.append((int(idx[c]), gain))
            cur = np.minimum(cur, M[:, c])
        per[g] = picks
        del M
    first = sorted(((p[0][1], g) for g, p in per.items() if p), reverse=True)
    order = [per[g][0] for _gain, g in first]
    pos = {g: 1 for g in per}
    heap = [(-per[g][1][1], g) for g in per if len(per[g]) > 1]
    heapq.heapify(heap)
    while heap and len(order) < n:
        _neg, g = heapq.heappop(heap)
        order.append(per[g][pos[g]])
        pos[g] += 1
        if pos[g] < len(per[g]):
            heapq.heappush(heap, (-per[g][pos[g]][1], g))
    return order[:n]


def nearest(faces, have, L=None):
    """for every face, the captured face (of `have`) whose picture it shows and the distance; a
    captured face shows its own"""
    L = L or looks(faces)
    have = np.array(sorted(have), np.int64)
    out = np.full(len(faces), -1, np.int64)
    dist = np.zeros(len(faces), np.float32)
    if not len(have):
        return out, dist
    for i in range(len(faces)):
        d = distance(L, i, have)
        j = int(d.argmin())                                   # ties: the lowest face number
        out[i], dist[i] = have[j], d[j]
    out[have] = have
    dist[have] = 0
    far = (L["group"][out] != L["group"]) & (dist > OTHER_GROUP + CROSS_MAX)  # another group's, not alike
    out[far] = -1
    return out, dist


def hair_name(rgb):
    r, g, b = (float(v) for v in rgb)
    lum = (r + g + b) / 3.0
    if max(r, g, b) < 10:
        return "black"
    if lum > 30 and max(r, g, b) - min(r, g, b) < 8:
        return "grey"
    if r > 1.4 * g and r > 14:
        return "red"
    if lum > 22:
        return "blond"
    if lum > 12:
        return "light brown"
    return "brown"


def describe(L, k):
    """a face's look in words (for the capture list)"""
    sk = int(L["skin"][k])
    length = {1: "very short", 2: "short", 3: "medium", 4: "long"}.get(int(L["hlen"][k]), "very long")
    hair = "%s, %s, %s" % (hair_name(L["hrgb"][k]), length, ["straight", "wavy", "curly"][int(L["wave"][k])])
    b = float(L["beard"][k])
    beard = "no beard" if b == 0 else "stubble" if L["fhair_t"][k] == 1 and b < 1.5 else "light beard" if b < 1.5 else "beard"
    return "skin %d (%s), hair %s, %s%s" % (sk, "light" if sk <= 2 else "middle" if sk <= 4 else "dark", hair, beard,
                                            ", older" if L["old"][k] else "")


def share(out, pool=None, log=print):
    """<out>\\fl26regen_faces.bin: the pool with every face's portrait number pointing at the
    picture (a .dds in <out>) of the captured face that looks most like it; <out>\\share.tsv the
    map (face, group, picture, distance). Returns (path, pictures, faces)"""
    sys.path.insert(0, HERE)
    import facepool as F
    raw = open(pool, "rb").read() if pool else F.pool_pack()
    _ver, natmap, faces = F.read_pack(raw)
    have = pictures(out)
    past = sorted(k for k in have if k >= len(faces))
    if past:
        raise SystemExit("pictures for faces the pool does not have: %s" % past[:10])
    if not have:
        raise SystemExit("no pictures in %s" % os.path.join(out, REGEN_DIR))
    L = looks(faces)
    near, dist = nearest(faces, have, L)
    new = [(g, int(near[k]) if near[k] >= 0 else F.NO_PORTRAIT, b) for k, (g, _old, b) in enumerate(faces)]
    data = F.pack(natmap, new, F.MAGIC2, blocks=F.read_blocks(raw))
    back = F.read_pack(data)
    bad = [] if back[1] == natmap and [(g, b) for g, _k, b in back[2]] == [(g, b) for g, _k, b in faces]         else ["the faces or the map changed"]
    if pool is None or len(faces) >= 20000:          # a small pool is only a test's
        bad += F.pool_problems(data, raw)
    if bad:
        raise SystemExit("share: the pack is not the pool: %s" % bad)
    path = os.path.join(out, "fl26regen_faces.bin")
    open(path, "wb").write(data)
    with open(os.path.join(out, "share.tsv"), "w", encoding="utf-8", newline="\n") as f:
        f.write("face\tgroup\tpicture\tdistance\n")
        for k in range(len(faces)):
            f.write("%d\t%s\t%s\t%.1f\n" % (k, F.GROUPS[faces[k][0]], near[k] if near[k] >= 0 else "none", dist[k]))
    import hashlib
    used = len(set(near[near >= 0].tolist()))
    got = dist[near >= 0]
    log("%s: %d faces, %d pictures (%d used), median distance %.1f, 90%% under %.1f, %d faces from another "
        "group's picture, %d with none (no near picture yet) (md5 %s)"
        % (path, len(faces), len(have), used, float(np.median(got)), float(np.percentile(got, 90)),
           int(((dist >= OTHER_GROUP) & (near >= 0)).sum()), int((near < 0).sum()), hashlib.md5(data).hexdigest()))
    return path, len(have), len(faces)


def write_rank(faces, n, path, log=print):
    """the capture list: rank's order, one face a line: the face, its group, its rank, how many of
    the pool's faces show its picture when the first 100 are captured, its look"""
    sys.path.insert(0, HERE)
    import facepool as F
    order = rank(faces, n, log)
    L = looks(faces)
    ks = [k for k, _g in order]
    near, _d = nearest(faces, ks[:100], L)
    cover = {k: int((near == k).sum()) for k in ks[:100]}
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("# facemini.py rank: the pool's faces to capture, best first (tools/facecap.py --faces <this file>)\n"
                "# face\tgroup\trank\tfaces showing its picture with the first 100 captured\tlook\n")
        for r, (k, _gain) in enumerate(order, 1):
            f.write("%d\t%s\t%d\t%s\t%s\n" % (k, F.GROUPS[faces[k][0]], r, cover.get(k, ""), describe(L, k)))
    rows = []
    for upto in (100, 300, 500, 1000):
        if upto <= len(ks):
            _n, d = nearest(faces, ks[:upto], L)
            rows.append("first %d: median distance %.1f, 90%% under %.1f" % (upto, float(np.median(d)), float(np.percentile(d, 90))))
    log("%s: %d faces ranked; %s" % (path, len(order), "; ".join(rows)))
    return order


def pictures(out):
    """the face numbers with a .dds in <out>"""
    have = set()
    for p in glob.glob(os.path.join(out, REGEN_DIR, "*.dds")):
        n = os.path.basename(p)[:-4]
        if n.isdigit():
            have.add(int(n))
    return have


def check_shared(data, root):
    """why a pack's portraits are not all there (facepool.portrait_problems)"""
    sys.path.insert(0, HERE)
    import facepool as F
    return F.portrait_problems(data, root)


# ---- the commands ----------------------------------------------------------------------------
def shots_in(d, pattern="mini_*.png"):
    """{k: path} of the screenshots mini_<k>.png in d"""
    out = {}
    for p in glob.glob(os.path.join(d, pattern)):
        m = SHOT.search(os.path.basename(p))
        if m:
            out[int(m.group(1))] = p
    return dict(sorted(out.items()))


def sheet(ims, path, cols=10):
    if not ims:
        return
    rows = (len(ims) + cols - 1) // cols
    W = Image.new("RGBA", (cols * SIZE, rows * (SIZE + 14)), (70, 70, 70, 255))
    from PIL import ImageDraw
    d = ImageDraw.Draw(W)
    for i, (k, im) in enumerate(ims):
        x, y = (i % cols) * SIZE, (i // cols) * (SIZE + 14)
        W.alpha_composite(im, (x, y))
        d.text((x + 3, y + SIZE + 1), str(k), fill=(255, 255, 0, 255))
    W.convert("RGB").save(path)


def convert(src, out, box=BOX, shirt="grey", pattern="mini_*.png", log=print):
    shots = shots_in(src, pattern)
    if not shots:
        raise SystemExit("no mini_<k>.png in %s" % src)
    if box == "auto":
        box = calibrate(shots.values(), log=log)
    ddir = os.path.join(out, REGEN_DIR)
    pdir = os.path.join(out, "preview")
    os.makedirs(ddir, exist_ok=True)
    os.makedirs(pdir, exist_ok=True)
    done, bad, prev = [], [], None
    for k, p in shots.items():
        im, notes = portrait(Image.open(p), box, shirt)
        a = np.asarray(im).astype(np.int16)
        if prev is not None and np.abs(a - prev[1]).mean() < 2.0:   # the same face twice: 0.2-0.8
            notes.setdefault("bad", "the same picture as face %d: the head was not drawn again" % prev[0])
        prev = (k, a)
        if "bad" in notes:
            bad.append((k, notes["bad"]))
        open(os.path.join(ddir, "%d.dds" % k), "wb").write(dds_bytes(im))
        im.save(os.path.join(pdir, "%d.png" % k))
        done.append((k, im))
    first, last = done[0][0], done[-1][0]
    sheet(done, os.path.join(out, "sheet_%d-%d.png" % (first, last)))
    rep = ["%d pictures from %s (faces %d-%d), box %s, shirt %s" % (len(done), src, first, last, box, shirt)]
    rep += ["face %d: %s" % b for b in bad]
    open(os.path.join(out, "report.txt"), "w", encoding="utf-8", newline="\n").write("\n".join(rep) + "\n")
    for line in rep[:40]:
        log(line)
    log("%d to look at again (report.txt); pictures in %s" % (len(bad), ddir))
    return done, bad


def pack(pool, out, log=print):
    sys.path.insert(0, HERE)
    import facepool as F
    raw = open(pool, "rb").read()
    ver, natmap, faces = F.read_pack(raw)
    have = pictures(out)
    past = sorted(k for k in have if k >= len(faces))
    if past:
        raise SystemExit("pictures for faces the pool does not have: %s" % past[:10])
    new = [(g, k if k in have else F.NO_PORTRAIT, b) for k, (g, _old, b) in enumerate(faces)]
    data = F.pack(natmap, new, F.MAGIC2, blocks=F.read_blocks(raw))     # each face keeps its block
    path = os.path.join(out, "fl26regen_faces.bin")
    open(path, "wb").write(data)
    import hashlib
    log("%s: %d faces, %d with a picture (md5 %s)" % (path, len(new), len(have), hashlib.md5(data).hexdigest()))
    return path, len(have)


def parse_box(a):
    if "--box" not in a:
        return BOX
    if a[a.index("--box") + 1] == "auto":
        return "auto"
    x, y, s = (int(v) for v in a[a.index("--box") + 1].split(","))
    return (x, y, s)


def read_picture(p):
    """a portrait (.dds, also the game's own with their header, or .png) -> RGBA image"""
    if p.lower().endswith(".dds"):
        data = open(p, "rb").read()
        w, h, fourcc, _m = check_dds(data)
        import io
        if fourcc == b"DXT5":
            # Pillow wants a pitch it can read: the same pixels under the header it writes itself
            b = io.BytesIO()
            Image.new("RGBA", (w, h)).save(b, "DDS", pixel_format="DXT5")
            data = b.getvalue()[:128] + data[128:128 + w * h]
        return Image.open(io.BytesIO(data)).convert("RGBA")
    return Image.open(p).convert("RGBA")


def main(a):
    if a and a[0] == "rank":
        sys.path.insert(0, HERE)
        import facepool as F
        n = int(a[a.index("--n") + 1]) if "--n" in a else 1000
        raw = open(a[a.index("--pool") + 1], "rb").read() if "--pool" in a else F.pool_pack()
        write_rank(F.read_pack(raw)[2], n, a[1])
        return
    if a and a[0] == "share":
        share(a[1], a[a.index("--pool") + 1] if "--pool" in a else None)
        return
    if not a or a[0] not in ("convert", "pack", "show", "calibrate", "frame"):
        raise SystemExit(__doc__)
    if a[0] == "convert":
        shirt = a[a.index("--shirt") + 1] if "--shirt" in a else "grey"
        pattern = a[a.index("--glob") + 1] if "--glob" in a else "mini_*.png"
        convert(a[1], a[2], parse_box(a), shirt, pattern)
    elif a[0] == "pack":
        pack(a[1], a[2])
    elif a[0] == "calibrate":
        box = parse_box(a)
        calibrate(shots_in(a[1]).values(), BOX if box == "auto" else box)
    elif a[0] == "frame":
        for p in a[1:]:
            im = read_picture(p)
            if im.size != (SIZE, SIZE):
                im = im.resize((SIZE, SIZE), Image.LANCZOS)
            print(os.path.basename(p), frame(np.asarray(im)[..., 3] > 128))
    else:
        from PIL import ImageDraw
        box = parse_box(a)
        shot = Image.open(a[1]).convert("RGB")
        im, notes = portrait(shot, box)
        d = ImageDraw.Draw(shot)
        d.rectangle([box[0], box[1], box[0] + box[2], box[1] + box[2]], outline=(255, 255, 0), width=2)
        base = os.path.splitext(a[1])[0]
        shot.save(base + "_box.png")
        im.save(base + "_mini.png")
        print(notes, "->", base + "_box.png", base + "_mini.png")


if __name__ == "__main__":
    main(sys.argv[1:])
