r"""mkkits.py -- give OUR added clubs a kit, by lending them a shipped one.

Our clubs (team id >= 71578) have crests but no kit definition at all, so on the pitch they
wear whatever the engine falls back to. A kit definition is a named 120-byte blob:

    common/character0/model/character/uniform/team/<id>/<id>_DEF_1st_realUni.bin

five colour triples, a parameter block, and five 16-byte texture names (`u<id>p<kit>` and
four variants) -- see docs/kits-by-team-id.md. Nothing here is indexed by team id, so ids in
the 71,xxx range are as addressable as any other.

Making new textures is a separate job. This tool does the cheap half: it copies a shipped
club's blob verbatim, under our club's name. The texture names inside still point at the
donor's textures, which exist, so our club turns out in that club's colours -- a real kit
rather than a fallback, and a different one per club, because 891 shipped clubs have a full
set to lend. Donors are handed out by position in our roster, so a club keeps its kit across
re-runs.

Purely additive: every file written is for an id no shipped file uses, and no shipped file is
read back out or modified.

  # look first: which donor each club would get
  python mkkits.py --team-bin <Team.bin> --unipar <UniformParameter.bin> --list

  # write the kit tree into a cpk root
  python mkkits.py --team-bin <Team.bin> --unipar <UniformParameter.bin> --root <livecpk-root>

`--unipar` is the shipped archive. Take the newest copy: the game reads the download cpks after
Data, and data_s2526c.cpk carries the last one (dt34_g4.cpk has an older one):

    python cpkx.py <game>\download\data_s2526c.cpk <dir> uniform/team/UniformParameter.bin

`--textures` is the list of kit textures the game ships, from the cpk listings:

    for %f in (<game>\Data\*.cpk <game>\download\*.cpk) do python cpk.py %f >> cpklist.txt

Pass it. A definition is only a pointer to a texture (`u0001p1.ftex` ...), and many shipped
definitions point at textures the game does not have: about 900 clubs have a full set of
definitions, about 700 have the textures. A club lent a definition without its texture wears
the engine's plain fallback kit (seen in game 2026-09-27: donor 2655, no u2655p1.ftex).

**Not solved yet (2026-09-27).** With textured donors the game does read these definitions --
the kit server logs the donor's KitFile and colours for our club (team 72163 with donor 174's
definition: KitFile=u0174p1, ShirtColor1=#512889) -- but the pre-match model and the Strip
screen still show the engine's plain default kit, with neither the donor's texture nor its
colours. Same with the per-club files alone and with the repacked archive. The render path
treats our team ids differently; that is the open question, not the definition.

Whether the engine reads these per-club files or only the archive is not established (the exe
builds the paths at runtime). This writes the files; --archive additionally writes a repacked
UniformParameter.bin with our entries appended, for the other case.
"""
import os, re, struct, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pesdb

REC, ID_OFF, NAME_OFF, NAME_LEN = 1532, 0x08, 0x170, 0x46
FIRST_OURS = 71578
KINDS = ("1st_realUni", "2nd_realUni", "GK1st_realUni")
TEAM_DIR = "common/character0/model/character/uniform/team"


def roster(team_bin):
    raw = pesdb.wesys_unpack(open(team_bin, "rb").read())
    out = []
    for i in range(len(raw) // REC):
        r = raw[i * REC:(i + 1) * REC]
        tid = struct.unpack_from("<I", r, ID_OFF)[0]
        if tid >= FIRST_OURS:
            name = r[NAME_OFF:NAME_OFF + NAME_LEN].split(b"\0")[0].decode("utf-8", "replace")
            out.append((tid, name))
    out.sort()
    return out


def archive(path):
    """-> (raw, [(name, offset, size)], the file's own 3-byte wesys prefix or None)"""
    raw, hdr = open(path, "rb").read(), None
    if raw[3:8] == b"WESYS":
        hdr, raw = raw[:3], pesdb.wesys_unpack(raw)
    count = struct.unpack_from("<I", raw, 0)[0]
    es = []
    for i in range(count):
        off, size, noff = struct.unpack_from("<III", raw, 8 + i * 12)
        es.append((raw[noff:raw.index(b"\0", noff)].decode(), off, size))
    return raw, es, hdr


def texture_names(blob):
    """The main texture a kit definition points at, e.g. 'u0001p1' (the other four are variants)."""
    m = re.search(rb"u\d{4,5}[a-z]\d", blob[0x13:])
    return m.group(0).decode() if m else None


def donors(raw, es, textures=None):
    """Shipped clubs with a complete set of the three kinds we hand out -- and, when the list of
    shipped textures is given, whose three kits actually have their texture in the game."""
    blobs = {}
    for name, off, size in es:
        m = re.match(r"(\d+)_DEF_(.+)\.bin$", name)
        if m and size == 120:
            blobs.setdefault(int(m.group(1)), {})[m.group(2)] = raw[off:off + size]
    full = [(tid, b) for tid, b in sorted(blobs.items()) if all(k in b for k in KINDS)]
    if textures is not None:
        full = [(tid, b) for tid, b in full
                if all(texture_names(b[k]) in textures for k in KINDS)]
    return full


def read_textures(path):
    """Texture names out of any text that mentions them -- e.g. `python cpk.py <cpk>` listings."""
    return set(re.findall(r"(u\d{4,5}[a-z]\d)\.ftex", open(path, encoding="utf-8", errors="replace").read()))


def build(argv):
    def opt(flag, default=None):
        return argv[argv.index(flag) + 1] if flag in argv else default

    team_bin, unipar = opt("--team-bin"), opt("--unipar")
    if not team_bin or not unipar:
        print(__doc__)
        return 2
    root, do_list = opt("--root"), "--list" in argv

    clubs = roster(team_bin)
    raw, es, hdr = archive(unipar)
    tex = opt("--textures")
    textures = read_textures(tex) if tex else None
    if textures is not None:
        print("%d kit textures listed in %s" % (len(textures), tex))
    else:
        print("warning: no --textures list; a donor whose textures are missing lends a blank kit")
    pool = donors(raw, es, textures)
    if not pool:
        print("no shipped club has all of %s -- is that the right archive?" % (KINDS,))
        return 1
    print("%d clubs of ours, %d shipped clubs able to lend a kit" % (len(clubs), len(pool)))

    pairs = [(c, pool[i % len(pool)]) for i, c in enumerate(clubs)]
    if do_list:
        for (tid, name), (dtid, _) in pairs:
            print("  %6d  %-30s <- shipped club %d" % (tid, name, dtid))
        return 0
    if not root:
        print("nothing written: pass --root <livecpk-root> or --list")
        return 0

    written = 0
    for (tid, _), (_, dblobs) in pairs:
        d = os.path.join(root, TEAM_DIR.replace("/", os.sep), str(tid))
        os.makedirs(d, exist_ok=True)
        for kind in KINDS:
            open(os.path.join(d, "%d_DEF_%s.bin" % (tid, kind)), "wb").write(dblobs[kind])
            written += 1
    print("wrote %d kit definitions under %s" % (written, os.path.join(root, TEAM_DIR)))

    if "--archive" in argv:
        out = repack(raw, es, pairs)
        if hdr is not None:                       # keep the file's own wesys prefix
            out = pesdb.wesys_pack(out, hdr)
        p = os.path.join(root, TEAM_DIR.replace("/", os.sep), "UniformParameter.bin")
        open(p, "wb").write(out)
        print("wrote %s (%d bytes, shipped entries plus ours)" % (p, len(out)))
    return 0


def repack(raw, es, pairs):
    """Shipped entries byte for byte, then ours -- same header/index/names/blobs shape."""
    items = [(name, raw[off:off + size]) for name, off, size in es]
    for (tid, _), (_, dblobs) in pairs:
        for kind in KINDS:
            items.append(("%d_DEF_%s.bin" % (tid, kind), dblobs[kind]))
    index_end = 8 + len(items) * 12
    names, name_at = bytearray(), {}
    for name, _ in items:
        if name not in name_at:
            name_at[name] = index_end + len(names)
            names += name.encode() + b"\0"
    while len(names) % 16:
        names += b"\0"
    blob_start = index_end + len(names)
    out = bytearray(struct.pack("<II", len(items), 8))
    blobs, at = bytearray(), blob_start
    for name, b in items:
        out += struct.pack("<III", at, len(b), name_at[name])
        blobs += b
        at += len(b)
    return bytes(out + names + blobs)


if __name__ == "__main__":
    sys.exit(build(sys.argv))
