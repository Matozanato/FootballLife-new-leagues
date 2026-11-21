"""Numbers and name letters of our own for a kit Mod Studio draws (Reddit, u/InquisitiveSapienLad,
13.11.2026: the drawn kits of a world had no numbers and no names on the back -- he put fonts on
them by hand, kit by kit).

A drawn kit took its numbers from a kit of the player's kit library (lbservers.numbers_kits). A
game with no such kit -- a fresh install, or one whose library holds drawn kits alone -- gave
none, and the kit's config named no number file. Now such a kit gets these: plain block digits
and letters, white or dark, whichever stands out from the shirt.

The masks are in kitnumbers_data.py (mkkitnumbers.py makes them; Bebas Neue, SIL Open Font
License 1.1).
"""
import base64, io

NAME = "fl-numbers-1"           # in the kit's stamp (lbservers._drawing): another set, another name
LIGHT, DARK = (255, 255, 255), (24, 24, 28)
# where the name and the number stand on the back of a drawn shirt (kitpics.DEFAULT_CONFIG's
# places are those of a kit with none): the name above, the number under it
# these are the values of nine real kits in ten (600 kits of a library looked at, 13.11.2026)
CONFIG = {"Name": "0", "NameShape": "0", "NameY": "12", "NameSize": "9", "NameStretch": "1",
          "BackNumberY": "19", "BackNumberSize": "25", "BackNumberSpacing": "8", "BackNumberType": "0",
          "ShortsNumberSide": "0", "ShortsNumberX": "16", "ShortsNumberY": "7", "ShortsNumberSize": "16"}
_MASKS = {}


def ink(shirt):
    """white or dark, by the contrast with the shirt's colour (#rrggbb or (r, g, b))"""
    import kitpics
    if isinstance(shirt, str):
        shirt = tuple(int(shirt.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    return LIGHT if kitpics.contrast(LIGHT, shirt) >= kitpics.contrast(DARK, shirt) else DARK


def mask(which):
    """the L picture of "numbers" (2048 x 256) or "names" (2048 x 512)"""
    if which not in _MASKS:
        from PIL import Image
        import kitnumbers_data as D
        raw = "".join(D.NUMBERS if which == "numbers" else D.NAMES)
        _MASKS[which] = Image.open(io.BytesIO(base64.b64decode(raw))).convert("L")
    return _MASKS[which]


def picture(which, colour):
    """the RGBA picture: the colour everywhere (so the edges do not darken), the mask its alpha"""
    from PIL import Image
    m = mask(which)
    im = Image.new("RGBA", m.size, tuple(colour) + (0,))
    im.putalpha(m)
    return im


def ftex(which, colour):
    """the .ftex bytes of the picture (DXT5)"""
    import kitpics
    im = picture(which, colour)
    b = io.BytesIO()
    im.save(b, "DDS", pixel_format="DXT5")
    return kitpics.dds_to_ftex(b.getvalue(), im.size[0], im.size[1])


def write(vdir, name, shirt):
    """<name>_back.ftex, _leg.ftex and _name.ftex in the kit variant's folder vdir, in the ink
    that stands out from the shirt; -> the suffixes written"""
    import os
    c = ink(shirt)
    num = ftex("numbers", c)
    for suf, data in (("_back", num), ("_leg", num), ("_name", ftex("names", c))):
        open(os.path.join(vdir, name + suf + ".ftex"), "wb").write(data)
    return ["_back", "_leg", "_name"]
