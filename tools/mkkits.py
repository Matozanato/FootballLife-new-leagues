r"""mkkits.py -- give OUR added clubs a kit, by lending them a shipped one.

Our clubs (the Build passes their ids with --clubs; without it, team id >= 71578) have crests
but no kit definition at all, so on the pitch they
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

  # --colours <json> {team id: [home shirt, away shirt]} in NewLife's words ("stripes #ffffff
  # #0052d5 #ffffff"): such a club gets the shipped kit nearest its own colours instead of the
  # one its place in the roster gives

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
import json, os, re, struct, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pesdb

REC, ID_OFF, NAME_OFF, NAME_LEN = 1532, 0x08, 0x170, 0x46
T_NATIONAL = 0x53          # top bit set on the 144 national teams (leaguebuilder.T_NATIONAL)
FIRST_OURS = 71578
KINDS = ("1st_realUni", "2nd_realUni", "GK1st_realUni")
# a third kit, lent when there is one: 511 of the 932 shipped clubs have a 3rd_realUni (6 a 4th).
# A donor without one lends the next donor's, so every club of ours gets three (0.1.8, asked for
# on Discord).
THIRD = "3rd_realUni"
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


def roster(team_bin, only=None):
    """[(team id, name)] of our clubs: the ids in only, or every id from FIRST_OURS. The first
    free id depends on the database under the world (a custom one may leave 71213 free, #54),
    so the Build names its clubs."""
    raw = pesdb.wesys_unpack(open(team_bin, "rb").read())
    out = []
    for i in range(len(raw) // REC):
        r = raw[i * REC:(i + 1) * REC]
        tid = struct.unpack_from("<I", r, ID_OFF)[0]
        if (tid in only) if only is not None else tid >= FIRST_OURS:
            name = r[NAME_OFF:NAME_OFF + NAME_LEN].split(b"\0")[0].decode("utf-8", "replace")
            out.append((tid, name))
    out.sort()
    return out


def national_teams(team_bin):
    """the ids of the game's national teams: never a kit donor, or a new club turns out in
    Belgium's or Wales's shirt (GitHub #57)"""
    raw = pesdb.wesys_unpack(open(team_bin, "rb").read())
    return {struct.unpack_from("<I", raw, i * REC + ID_OFF)[0] for i in range(len(raw) // REC)
            if raw[i * REC + T_NATIONAL] & 0x80}


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


def donors(raw, es, textures=None, skip=()):
    """Shipped clubs with a complete set of the three kinds we hand out -- and, when the list of
    shipped textures is given, whose three kits actually have their texture in the game. `skip`:
    ids that lend nothing (the national teams)."""
    blobs = {}
    for name, off, size in es:
        m = re.match(r"(\d+)_DEF_(.+)\.bin$", name)
        if m and size == 120 and int(m.group(1)) not in skip:
            blobs.setdefault(int(m.group(1)), {})[m.group(2)] = raw[off:off + size]
    full = [(tid, b) for tid, b in sorted(blobs.items()) if all(k in b for k in KINDS)]
    if textures is not None:
        full = [(tid, b) for tid, b in full
                if all(texture_names(b[k]) in textures for k in KINDS)]
        for _tid, b in full:
            if THIRD in b and texture_names(b[THIRD]) not in textures:
                del b[THIRD]
    return full


def kinds_of(blobs):
    """the kinds a club of ours is given: the three, and the third kit when it has one"""
    return KINDS + ((THIRD,) if THIRD in blobs else ())


def with_third(pairs, pool):
    """pairs with a third kit for every club whose donor has none: the next donor's in pool order
    that has one, so a club keeps it across re-runs"""
    thirds = [(i, b[THIRD]) for i, (_tid, b) in enumerate(pool) if THIRD in b]
    if not thirds:
        return pairs
    at = {tid: i for i, (tid, _b) in enumerate(pool)}
    out = []
    for c, (dtid, blobs) in pairs:
        if THIRD not in blobs:
            i = at.get(dtid, 0)
            blobs = dict(blobs)
            blobs[THIRD] = next((b for j, b in thirds if j > i), thirds[0][1])
        out.append((c, (dtid, blobs)))
    return out


def colours_of(blob):
    """the five RGB triples of a kit definition; [0] is the shirt, [1] its second colour
    (Arsenal a71a2f/d7d7d7, Celtic d7d7d7/189163, Hajduk d7d7d7/103e7f)"""
    return [tuple(blob[4 + 3 * k:7 + 3 * k]) for k in range(5)]


def shirt(words):
    """(body, second) RGB of a shirt described the NewLife way: pattern #body #second #trim"""
    try:
        cols = words.split()[1:3]
        return tuple(tuple(int(c[k:k + 2], 16) for k in (1, 3, 5)) for c in cols) if len(cols) == 2 else None
    except (AttributeError, ValueError):
        return None


def cdist(a, b):
    """colour distance weighted the way the eye sees it ("redmean")"""
    r = (a[0] + b[0]) / 2.0
    dr, dg, db = a[0] - b[0], a[1] - b[1], a[2] - b[2]
    return ((2 + r / 256) * dr * dr + 4 * dg * dg + (2 + (255 - r) / 256) * db * db) ** 0.5


def closest(cands, want, used):
    """the (donor id, blob) of cands whose shirt is nearest `want` (body, second); a donor lent
    often costs a little more, so clubs of one colour still get different kits"""
    def cost(c):
        col = colours_of(c[1])
        return 2 * cdist(want[0], col[0]) + cdist(want[1], col[1]) + 25 * used.get(c[0], 0)
    return min(cands, key=cost)


def painted(blob, want):
    """blob with its first two colours (shirt, second) set to want (body, second): the menus
    and scoreboards take a club's colours from its kit definition, the textures stay the
    donor's (JamesNotLike: colours picked in Mod Studio)"""
    if not want:
        return blob
    b = bytearray(blob)
    for k, rgb in enumerate(want[:2]):
        b[4 + 3 * k:7 + 3 * k] = bytes(rgb)
    return bytes(b)


def matched(clubs, pool, colours):
    """[(club, (home donor id, {kind: blob}))]: the home kit and goalkeeper kit of the donor whose
    first kit is nearest the club's home shirt, the second kit from whichever shipped first or
    second kit is nearest its away shirt; a club with no colours keeps the donor its place gives"""
    firsts = [(tid, b["1st_realUni"]) for tid, b in pool]
    both = firsts + [(tid, b["2nd_realUni"]) for tid, b in pool]
    by_id = dict(pool)
    used, out = {}, []
    for i, c in enumerate(clubs):
        home, away = [shirt(w) for w in (list(colours.get(c[0]) or []) + [None, None])[:2]]
        if not home:
            dtid, blobs = pool[i % len(pool)]
            out.append((c, (dtid, blobs)))
            continue
        dtid = closest(firsts, home, used)[0]
        used[dtid] = used.get(dtid, 0) + 1
        blobs = dict(by_id[dtid])
        blobs["1st_realUni"] = painted(blobs["1st_realUni"], home)
        if away:
            atid, ablob = closest([x for x in both if x[0] != dtid], away, used)
            used[atid] = used.get(atid, 0) + 1
            blobs["2nd_realUni"] = painted(ablob, away)
        out.append((c, (dtid, blobs)))
    return out


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

    ids = opt("--clubs")
    clubs = roster(team_bin, {int(x) for x in ids.split(",") if x.strip()} if ids is not None else None)
    raw, es, hdr = archive(unipar)
    tex = opt("--textures")
    textures = read_textures(tex) if tex else None
    if textures is not None:
        print("%d kit textures listed in %s" % (len(textures), tex))
    else:
        print("warning: no --textures list; a donor whose textures are missing lends a blank kit")
    pool = donors(raw, es, textures, national_teams(team_bin))
    if not pool:
        print("no shipped club has all of %s -- is that the right archive?" % (KINDS,))
        return 1
    print("%d clubs of ours, %d shipped clubs able to lend a kit" % (len(clubs), len(pool)))

    col = opt("--colours")
    colours = {int(k): v for k, v in json.load(open(col, encoding="utf-8")).items()} if col else {}
    pairs = with_third(matched(clubs, pool, colours), pool)
    if colours:
        print("%d clubs dressed by their own colours" % sum(1 for (tid, _), _p in pairs if shirt((colours.get(tid) or [""])[0])))
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
        for kind in kinds_of(dblobs):
            open(os.path.join(d, "%s%s.bin" % (stem, kind)), "wb").write(dblobs[kind])
            written += 1
    print("wrote %d kit definitions under %s" % (written, os.path.join(root, TEAM_DIR)))

    if "--archive" in argv:
        out = repack(raw, es, pairs)
        if hdr is not None:                       # keep the file's own wesys prefix
            out = pesdb.wesys_pack(out, hdr)
        p = os.path.join(root, TEAM_DIR.replace("/", os.sep), "UniformParameter.bin")
        os.makedirs(os.path.dirname(p), exist_ok=True)     # no club written: no folder yet (#54)
        open(p, "wb").write(out)
        print("wrote %s (%d bytes, shipped entries plus ours)" % (p, len(out)))
    return 0


def repack(raw, es, pairs):
    """Shipped entries byte for byte, then ours -- same header/index/names/blobs shape."""
    items = [(name, raw[off:off + size]) for name, off, size in es]
    for (tid, _), (_, dblobs) in pairs:
        for kind in kinds_of(dblobs):
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
