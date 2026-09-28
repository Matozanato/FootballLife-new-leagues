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

A picture the user gives is fitted into a transparent square (never stretched); with none,
the placeholder the tools draw from the id is used.
"""
import os
from PIL import Image

import mkemblems
import mkcrests

EMBLEM_DIR = ("common", "render", "symbol", "emblemLc")
CREST_DIR = ("common", "render", "symbol", "flag")


def square(path, size):
    """the picture at `path`, fitted into a transparent size x size square"""
    im = Image.open(path).convert("RGBA")
    im.thumbnail((size, size), Image.LANCZOS)
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


def club_crest(root, tid, label, picture=None):
    """write the three crest sizes of team `tid`"""
    d = os.path.join(root, *CREST_DIR)
    os.makedirs(d, exist_ok=True)
    master = square(picture, 512) if picture else mkcrests.crest(tid, label or str(tid), 512)
    for suf, px in mkcrests.FLAG_SIZES:
        im = master if px == 512 else master.resize((px, px), Image.LANCZOS)
        im.save(os.path.join(d, "e_%06d%s.png" % (tid, suf)))


def preview(picture, size=96):
    """a small square of a picture, for the window"""
    return square(picture, size)
