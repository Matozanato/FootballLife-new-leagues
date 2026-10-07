"""The pictures and kits of a league builder world: league logos, club crests, club kits.

Each is keyed by an id and served from the world's livecpk root, so nothing shipped is
touched, and a picture for a shipped id replaces the game's own one only while the world is on:

  league logo   common/render/symbol/emblemLc/emb_<competition id, 4 digits><variant>.png
                six variants, 256 and 512 px (tools/mkemblems.py measured them)
  club crest    common/render/symbol/flag/e_<team id, 6 digits>_r[_l|_ll].png, 128/256/512 px
                (tools/mkcrests.py)
  club kit      common/character0/model/character/uniform/team/<n>/<n><TAG><kind>_realUni.bin
                plus the repacked UniformParameter.bin (tools/mkkits.py): a shipped club's kit
                lent to each new club

A picture the user gives is fitted into a transparent square (never stretched); with none, a
club whose shirt is known (NewLife) gets a shield in its colours (tools/shieldcrest.py), any
other the placeholder the tools draw from the id.
"""
import os
from PIL import Image

import mkemblems
import mkcrests
import shieldcrest

EMBLEM_DIR = ("common", "render", "symbol", "emblemLc")
CREST_DIR = ("common", "render", "symbol", "flag")


FILL = 0.96   # the part of the square a picture spans, as the game's own logos and crests do


def square(path, size):
    """the picture at `path`, fitted into a transparent size x size square: its empty border cut
    off and scaled up as well as down. thumbnail() only shrank, so a 139 x 181 league logo stayed
    a speck in the middle of the 512 square, and a crest with a wide transparent margin came out
    small (in game, 07.10.)"""
    im = Image.open(path).convert("RGBA")
    box = im.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    if box:
        im = im.crop(box)
    k = size * FILL / max(im.width, im.height)
    im = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(im, ((size - im.width) // 2, (size - im.height) // 2), im)
    return out


def league_logo(root, cid, name, picture=None):
    """write the six emblem variants of competition `cid`.

    `_b` and `_w` are the versions for a light and a dark background, not silhouettes: the
    shipped Ligue 2 set (emb_0068) is in full colour in both, while Ligue 1's (emb_0012) is a
    black and a white shape.  Select Team takes `_b` whenever there is one, so a picture is
    written in colour to every variant -- as a black shape it showed as a black disc
    (in game, 28.09.)."""
    d = os.path.join(root, *EMBLEM_DIR)
    os.makedirs(d, exist_ok=True)
    if picture:
        master = square(picture, 512)
    for suf, px in mkemblems.VARIANTS:
        mode = "b" if "_b" in suf else ("w" if "_w" in suf else "")
        if picture:
            im = master if px == 512 else master.resize((px, px), Image.LANCZOS)
        else:
            im = mkemblems.emblem(cid, mkemblems.initials(name, "", cid), mkemblems.tier(name), px, mode)
        im.save(os.path.join(d, "emb_%04d%s.png" % (cid, suf)))


def club_crest(root, tid, label, picture=None, kit=None):
    """write the three crest sizes of team `tid`: the picture given, else a shield in the colours
    of the club's shirt (`kit`, shieldcrest's words), else the numbered placeholder"""
    d = os.path.join(root, *CREST_DIR)
    os.makedirs(d, exist_ok=True)
    master = square(picture, 512) if picture else None
    if master is None and kit:
        master = shieldcrest.shield(kit, label or str(tid), 512)
    if master is None:
        master = mkcrests.crest(tid, label or str(tid), 512)
    for suf, px in mkcrests.FLAG_SIZES:
        im = master if px == 512 else master.resize((px, px), Image.LANCZOS)
        im.save(os.path.join(d, "e_%06d%s.png" % (tid, suf)))


FLAG_SIZES = (("", 128), ("_l", 256), ("_ll", 512))
FLAG_BORDER = (222, 222, 222, 255)


def country_flag(root, fid, picture):
    """write the three sizes of flag `fid` (Country.bin's flag id) from a picture, drawn the way the
    shipped flags are: a square transparent canvas, the flag across the middle (126 x 88 of 128)
    inside a grey frame 1/32 of the canvas thick.  The picture is stretched to the flag's shape,
    as a flag is a rectangle whatever its proportions; it replaces the country's flag everywhere
    the game shows it (Select Team, nationality) while the world is on."""
    d = os.path.join(root, *CREST_DIR)
    os.makedirs(d, exist_ok=True)
    src = Image.open(picture).convert("RGBA")
    for suf, px in FLAG_SIZES:
        u, b = px // 128, px // 32
        box = (u, 20 * u, px - u, 108 * u)
        out = Image.new("RGBA", (px, px), (0, 0, 0, 0))
        out.paste(Image.new("RGBA", (box[2] - box[0], box[3] - box[1]), FLAG_BORDER), box[:2])
        inner = (box[0] + b, box[1] + b, box[2] - b, box[3] - b)
        out.paste(src.resize((inner[2] - inner[0], inner[3] - inner[1]), Image.LANCZOS), inner[:2])
        out.save(os.path.join(d, "flag_%d%s.png" % (fid, suf)))


def preview(picture, size=96):
    """a small square of a picture, for the window"""
    return square(picture, size)
