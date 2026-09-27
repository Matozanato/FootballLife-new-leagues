r"""mkkits.py -- give OUR added clubs a kit, by lending them a shipped one.

Our clubs (team id >= 71578) have crests but no kit definition at all, so on the pitch they
wear whatever the engine falls back to. A kit definition is a named 120-byte blob:

    common/character0/model/character/uniform/team/<number>/<number><TAG><kind>_realUni.bin

where <number> and <TAG> come from the team id, not the id itself (see kit_key below): ids up
to 16383 are `<id>/<id>_DEF_...`, and ids 65536..81919 -- ours -- are `<id-65536>/
<id-65536>_ACL_...`, the same form the shipped archive uses for its own AFC clubs. Club 72163
is looked up as `6627/6627_ACL_1st_realUni.bin`. A file named `72163_DEF_...` is never asked
for, which is what "the kit does not show" was until 2026-09-27.

The blob holds five colour triples, a parameter block, and five 16-byte texture names
(`u<id>p<kit>` and four variants) -- see docs/kits-by-team-id.md.

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

Seen in game 2026-09-27: club 72163 with the files named 6627_ACL_* wears its donor's first
and second kit in the pre-match screen and the Strip screen.

This writes the per-club files and, with --archive, a repacked UniformParameter.bin with our
entries appended under the same names. Sider looks the entry up by that name
(`find_kit_info:: name: {6627_ACL_1st_realUni.bin}` in sider.log); pass --archive.
"""
import os, re, struct, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pesdb

REC, ID_OFF, NAME_OFF, NAME_LEN = 1532, 0x08, 0x170, 0x46
FIRST_OURS = 71578
KINDS = ("1st_realUni", "2nd_realUni", "GK1st_realUni")
TEAM_DIR = "common/character0/model/character/uniform/team"


# The engine does not use a team id as it stands in a kit name.  Bits 14-16 of the id are a
# range tag and only the rest is the number: 0x1414bdb20 keeps id & 0x23fff, 0x1414bda30
# returns (id >> 14) & 7, and the path builder 0x141ea2400 writes
#     team/<number>/<number><TAG[tag]><kind>_realUni.bin
# with TAG read from the exe's table at 0x14351e460.  Ids 65536..81919 carry tag 4, "_ACL_"
# -- the same names the shipped archive uses for its own 46 AFC clubs -- so club 72163 is
# looked up as team/6627/6627_ACL_1st_realUni.bin.  A tag of 7 or more falls back to _DEF_.
TAGS = ("_DEF_", "_LB_", "_LBN_", "_JL_", "_ACL_", "_SDA_", "_SDN_", "_DEF_")


def kit_key(tid):
    """(folder number, name prefix) the engine asks for, for team id tid"""
    num = tid & 0x23fff
    return num, "%d%s" % (num, TAGS[(tid >> 14) & 7])


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
        num, stem = kit_key(tid)
        d = os.path.join(root, TEAM_DIR.replace("/", os.sep), str(num))
        os.makedirs(d, exist_ok=True)
        for kind in KINDS:
            open(os.path.join(d, "%s%s.bin" % (stem, kind)), "wb").write(dblobs[kind])
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
            items.append(("%s%s.bin" % (kit_key(tid)[1], kind), dblobs[kind]))
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
