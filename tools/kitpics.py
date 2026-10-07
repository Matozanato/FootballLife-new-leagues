r"""kitpics.py -- a kit-server club folder from plain kit pictures (0.2.0)

The png -> dds -> ftex part is Xxspedd's (kits_all.py, his kit tool for Football Life 2026,
given to Mod Studio to use): Pillow writes the picture as a 2048x2048 DXT5 DDS, and the DDS's
pixel data goes into an .ftex in 16 KiB zlib chunks behind the header the game reads.

A picture folder is one club: p1.png, p2.png ... for the outfield kits and g1.png ... for the
goalkeeper's, the same names kit-server gives its kit folders (.jpg and .dds work too). It
becomes the folder kit-server reads:

    <club>\order.ini, gk_order.ini
    <club>\p1\config.txt, u<id>p1.ftex, u<id>p1_back.ftex, u<id>p1_leg.ftex, u<id>p1_name.ftex

A picture is only the kit. The back numbers, leg numbers and name font are textures of their
own, so they are taken from a kit folder already in the library (the one picked as "Numbers and
names from"), the outfield ones from its p1 and the goalkeeper's from its g1; config.txt comes
from that kit too, with the colours read off the picture. Without such a kit the config names
no number files and the game keeps the club's own.

    python kitpics.py <picture folder> <team id> <out folder> [<numbers kit folder>]
"""
import io, os, re, shutil, struct, sys, zlib

PICTURE = re.compile(r"^([pg][1-9])\.(png|jpe?g|dds)$", re.I)
SIZE = 2048
CHUNK = 16384
NUMBER_FILES = ("_back", "_leg", "_name")
# the config of a kit with nothing to copy one from: the values kit-server's own
# example kits use
DEFAULT_CONFIG = """; shirt parameters
ShortSleevesModel=1
ShirtModel=144
Collar=1
TightKit=0
ShirtPattern=1
WinterCollar=1
LongSleevesType=62

; shirt - back side
Name=0
NameShape=2
NameY=31
NameSize=6
NameStretch=2
BackNumberY=10
BackNumberSize=23
BackNumberSpacing=10
BackNumberType=0

; shirt - front side
ChestNumberX=15
ChestNumberY=15
ChestNumberSize=14

; shorts parameters
ShortsModel=1
ShortsNumberSide=0
ShortsNumberX=16
ShortsNumberY=7
ShortsNumberSize=14

; texture files
KitFile=
BackNumbersFile=
ChestNumbersFile=
LegNumbersFile=
NameFontFile=

; kit colors
ShirtColor1=#ffffff
ShirtColor2=#ffffff
UndershirtColor=#ffffff
ShortsColor=#ffffff
SocksColor=#ffffff

; sleeve badge positions
RightShortX=14
RightShortY=12
RightLongX=14
RightLongY=12
LeftShortX=0
LeftShortY=31
LeftLongX=0
LeftLongY=31

; kit colors from UniColor.bin
UniColor_Color1=#ffffff
UniColor_Color2=#ffffff
"""


def pictures(d):
    """{"p1": path, ...} of the kit pictures in folder d, or {}"""
    try:
        names = os.listdir(d)
    except OSError:
        return {}
    out = {}
    for n in sorted(names):
        m = PICTURE.match(n)
        if m and os.path.isfile(os.path.join(d, n)):
            out.setdefault(m.group(1).lower(), os.path.join(d, n))
    return out


def dds_bytes(path):
    """the picture as a SIZE x SIZE DXT5 DDS, in memory"""
    from PIL import Image
    im = Image.open(path).convert("RGBA")
    if im.size != (SIZE, SIZE):
        im = im.resize((SIZE, SIZE), Image.LANCZOS)
    b = io.BytesIO()
    im.save(b, "DDS", pixel_format="DXT5")
    return b.getvalue()


def dds_to_ftex(dds):
    """an .ftex of a 2048x2048 DXT5 DDS (Xxspedd's dds_to_ftex): a 0x40 header, one mip
    entry, a table of 256 chunk entries and the zlib chunks, offsets counted from the entry"""
    if dds[:4] != b"DDS ":
        raise ValueError("not a DDS file")
    data = dds[128:]
    if len(data) % CHUNK:
        data += b"\0" * (CHUNK - len(data) % CHUNK)
    chunks = [zlib.compress(data[i:i + CHUNK], 9) for i in range(0, len(data), CHUNK)]
    head = bytearray(0x40)
    head[0:4] = b"FTEX"
    head[4:8] = bytes.fromhex("85EB0140")      # version 2.03
    head[8:10] = (4).to_bytes(2, "little")     # DXT5
    head[10:12] = SIZE.to_bytes(2, "little")
    head[12:14] = SIZE.to_bytes(2, "little")
    head[14:16] = (1).to_bytes(2, "little")
    head[16:20] = bytes.fromhex("01021100")
    head[28:32] = (3).to_bytes(4, "little")
    table_size = 8 * len(chunks)
    table, at = bytearray(), table_size
    for c in chunks:
        table += struct.pack("<HHI", len(c), CHUNK, at)
        at += len(c)
    entry = struct.pack("<IIIBBH", 0x50, len(data), at, 0, 0, len(chunks))
    return bytes(head) + entry + bytes(table) + b"".join(chunks)


def colours(path, n=3):
    """the n commonest colours of the picture, as #rrggbb, most used first"""
    from PIL import Image
    im = Image.open(path).convert("RGBA")
    im.thumbnail((256, 256))
    px = Image.new("RGB", im.size, (0, 0, 0))
    px.paste(im, mask=im.split()[3])
    q = px.quantize(colors=8)
    pal = q.getpalette()
    out = []
    for _count, i in sorted(q.getcolors(), reverse=True):
        c = "#%02x%02x%02x" % tuple(pal[3 * i:3 * i + 3])
        if c not in out:
            out.append(c)
    while len(out) < n:
        out.append(out[-1] if out else "#ffffff")
    return out[:n]


def numbers_source(kit, var):
    """the folder of `kit` to take a kit's number files and config from: its own variant if it
    has it, else its p1 (outfield) or g1 (goalkeeper), else any with a config"""
    if not kit:
        return None
    for v in (var, "g1" if var.startswith("g") else "p1"):
        d = os.path.join(kit, v)
        if os.path.isfile(os.path.join(d, "config.txt")):
            return d
    return None


def config_text(src_dir, name, cols, numbers):
    """config.txt for kit `name`: the source kit's config, or the default one, with the texture
    names ours and the colours the picture's"""
    txt = DEFAULT_CONFIG
    if src_dir:
        try:
            txt = open(os.path.join(src_dir, "config.txt"), encoding="utf-8-sig", errors="replace").read()
        except OSError:
            pass
    c1, c2, c3 = cols
    val = {"KitFile": name, "ChestNumbersFile": "",
           "BackNumbersFile": name + "_back" if numbers else "",
           "LegNumbersFile": name + "_leg" if numbers else "",
           "NameFontFile": name + "_name" if numbers else "",
           "ShirtColor1": c1, "ShirtColor2": c2, "UndershirtColor": c1,
           "ShortsColor": c1, "SocksColor": c1, "UniColor_Color1": c1, "UniColor_Color2": c2}
    out, seen = [], set()
    for line in txt.splitlines():
        m = re.match(r"^(\s*)([A-Za-z0-9_]+)(\s*=\s*)([^;]*?)(\s*;.*)?$", line)
        if m and m.group(2) in val:
            seen.add(m.group(2))
            line = "%s%s%s%s%s" % (m.group(1), m.group(2), m.group(3), val[m.group(2)], m.group(5) or "")
        if m and m.group(2) in ("KitFile_srm", "NameFontFile_ex"):
            continue                                   # kserv adds these back from ours
        out.append(line)
    for k in ("KitFile", "BackNumbersFile", "LegNumbersFile", "NameFontFile"):
        if k not in seen:
            out.append("%s=%s" % (k, val[k]))
    return "\n".join(out) + "\n"


def make_kit(pics, team_id, dst, numbers_kit=None):
    """write the kit-server folder dst for the pictures {var: path} of club team_id; -> the
    variants written. numbers_kit: a library kit folder to take number files and config from"""
    os.makedirs(dst, exist_ok=True)
    done = []
    for var in sorted(pics, key=lambda v: (v[0] == "g", v)):
        vdir = os.path.join(dst, var)
        os.makedirs(vdir, exist_ok=True)
        name = "u%d%s" % (team_id, var)
        path = pics[var]
        dds = open(path, "rb").read() if path.lower().endswith(".dds") else dds_bytes(path)
        open(os.path.join(vdir, name + ".ftex"), "wb").write(dds_to_ftex(dds))
        src = numbers_source(numbers_kit, var)
        have = []
        if src:
            ftex = {f.lower(): f for f in os.listdir(src) if f.lower().endswith(".ftex")}
            for suf in NUMBER_FILES:
                f = next((ftex[k] for k in ftex if k.endswith(suf + ".ftex")), None)
                if f:
                    shutil.copy2(os.path.join(src, f), os.path.join(vdir, name + suf + ".ftex"))
                    have.append(suf)
        open(os.path.join(vdir, "config.txt"), "w", encoding="utf-8", newline="\r\n").write(
            config_text(src, name, colours(path), len(have) == len(NUMBER_FILES)))
        done.append(var)
    shirts = [v for v in done if v.startswith("p")]
    gks = [v for v in done if v.startswith("g")]
    if shirts:
        open(os.path.join(dst, "order.ini"), "w", encoding="utf-8").write("\n".join(shirts) + "\n")
    if gks:
        open(os.path.join(dst, "gk_order.ini"), "w", encoding="utf-8").write("\n".join(gks) + "\n")
    return done


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    pics = pictures(argv[0])
    if not pics:
        print("no kit pictures (p1.png, g1.png ...) in %s" % argv[0])
        return 1
    done = make_kit(pics, int(argv[1]), argv[2], argv[3] if len(argv) > 3 else None)
    print("wrote %s in %s" % (", ".join(done), argv[2]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
