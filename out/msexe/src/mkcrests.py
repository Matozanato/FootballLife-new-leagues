"""mkcrests.py -- generate placeholder club crests for OUR added clubs (id >= 71578).

Our placeholder clubs clone a source club, so in-game they show that source club's crest
(shared) and, in some match scenes, a missing-asset null-deref (0x141fea5ba, mitigated by
nullguard). This makes a distinct, deterministic placeholder crest per club: a two-tone
roundel in a per-id colour with the club's number, so each of our clubs reads as its own
side instead of a clone. Additive and self-made -- no game-derived art.

Roster (id, name, abbr) is read from the deployed Team.bin (record 1532 bytes; id +0x08,
name +0x170, abbr +0x372 -- see mkteams.py). Colour is a deterministic function of the id,
so re-runs are stable and every club keeps the same crest.

  # preview masters, named by team id (for eyeballing):
  python mkcrests.py --team-bin <Team.bin> --out <dir> [--size 128] [--sample 71578,71599]

  # production club-emblem tree the game serves, keyed by team id:
  python mkcrests.py --team-bin <Team.bin> --flags <livecpk-root>

The game serves a club's emblem from  common/render/symbol/flag/e_<teamid6>_r[_l|_ll].png
(128 / 256 / 512 px, PNG), keyed by the club's own TEAM ID. Shipped ids run 1..71577, so our
clubs (71578..) sit just above -- purely additive: no shipped emblem is touched and no Team.bin
edit is needed. --flags writes that tree; activate the root and the crests render.
"""
import colorsys, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pesdb
from PIL import Image, ImageDraw, ImageFont

REC = 1532
ID_OFF, NAME_OFF, NAME_LEN, ABBR_OFF, ABBR_LEN = 0x08, 0x170, 0x46, 0x372, 3
FIRST_OURS = 71578

FONT = r"C:\Windows\Fonts\arialbd.ttf"


def roster(team_bin):
    raw = pesdb.wesys_unpack(open(team_bin, "rb").read())
    n = len(raw) // REC
    out = []
    for i in range(n):
        r = raw[i * REC:(i + 1) * REC]
        cid = int.from_bytes(r[ID_OFF:ID_OFF + 4], "little")
        if cid < FIRST_OURS:
            continue
        name = r[NAME_OFF:NAME_OFF + NAME_LEN].split(b"\0")[0].decode("utf-8", "replace")
        abbr = r[ABBR_OFF:ABBR_OFF + ABBR_LEN].split(b"\0")[0].decode("utf-8", "replace")
        out.append((cid, name, abbr))
    return out


def colours(cid):
    """Deterministic (ring, fill, text) from the club id -- well spread, always legible."""
    h = ((cid - FIRST_OURS) * 0.61803398875) % 1.0          # golden-ratio hue walk
    ring = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(h, 0.62, 0.55))
    fill = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(h, 0.42, 0.93))
    lum = 0.299 * fill[0] + 0.587 * fill[1] + 0.114 * fill[2]
    text = (25, 25, 30) if lum > 140 else (245, 245, 250)
    return ring, fill, text


def crest(cid, label, size):
    ss = 4                                                    # supersample for smooth edges
    S = size * ss
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    ring, fill, text = colours(cid)
    pad = int(S * 0.04)
    d.ellipse([pad, pad, S - pad, S - pad], fill=ring + (255,))
    r2 = int(S * 0.12)
    d.ellipse([r2, r2, S - r2, S - r2], fill=fill + (255,))
    # club number, centred
    try:
        font = ImageFont.truetype(FONT, int(S * (0.42 if len(label) <= 3 else 0.32)))
    except OSError:
        font = ImageFont.load_default()
    tb = d.textbbox((0, 0), label, font=font)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    d.text(((S - tw) / 2 - tb[0], (S - th) / 2 - tb[1]), label, font=font, fill=text + (255,))
    return img.resize((size, size), Image.LANCZOS)


# club-emblem size ladder (measured from shipped flag/e_*_r*.png): _r 128, _r_l 256, _r_ll 512
FLAG_SIZES = [("_r", 128), ("_r_l", 256), ("_r_ll", 512)]


def main():
    a = sys.argv[1:]
    def opt(name, default=None):
        return a[a.index(name) + 1] if name in a else default
    team_bin = opt("--team-bin")
    out = opt("--out")
    flags = opt("--flags")
    size = int(opt("--size", "128"))
    sample = opt("--sample")
    if not team_bin or not (out or flags):
        print(__doc__); return 1

    clubs = roster(team_bin)
    print("roster: %d clubs, id %d..%d" % (len(clubs), clubs[0][0], clubs[-1][0]))

    # rendering the 512 master once and downscaling keeps all three sizes identical in look
    def label_of(cid, abbr):
        return abbr if abbr.strip() else str(cid)

    if flags:
        fd = os.path.join(flags, "common", "render", "symbol", "flag")
        os.makedirs(fd, exist_ok=True)
        for cid, name, abbr in clubs:
            master = crest(cid, label_of(cid, abbr), 512)
            for suf, px in FLAG_SIZES:
                im = master if px == 512 else master.resize((px, px), Image.LANCZOS)
                im.save(os.path.join(fd, "e_%06d%s.png" % (cid, suf)))
        print("wrote %d club emblems (x3 sizes) to %s" % (len(clubs), fd))
        print("keyed by team id (e_%06d.. -- above shipped max 71577, additive)." % clubs[0][0])
        print("NEXT: activate this root in sider.ini (siderroot.py) and play-test.")
        return 0

    # preview masters, named by team id
    os.makedirs(out, exist_ok=True)
    want = set(int(x) for x in sample.split(",")) if sample else None
    made = 0
    for cid, name, abbr in clubs:
        if want and cid not in want:
            continue
        crest(cid, label_of(cid, abbr), size).save(os.path.join(out, "%d.png" % cid))
        made += 1
    print("wrote %d preview crests to %s (%dx%d)" % (made, out, size, size))
    return 0


if __name__ == "__main__":
    sys.exit(main())
