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

`--unipar` is the shipped archive, extracted from dt34_g4.cpk with

    python cpkx.py <cpk> <dir> uniform/team/UniformParameter.bin

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


def donors(raw, es):
    """Shipped clubs with a complete set of the three kinds we hand out."""
    blobs = {}
    for name, off, size in es:
        m = re.match(r"(\d+)_DEF_(.+)\.bin$", name)
        if m and size == 120:
            blobs.setdefault(int(m.group(1)), {})[m.group(2)] = raw[off:off + size]
    full = [(tid, b) for tid, b in sorted(blobs.items()) if all(k in b for k in KINDS)]
    return full


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
    pool = donors(raw, es)
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
