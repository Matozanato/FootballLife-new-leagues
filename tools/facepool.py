r"""facepool.py -- our own pool of 32,760 player faces for regens and new players, made from
numbers alone: no face model, no portrait and no appearance record of any real player in it.

Why. A player who has no face model of his own (a regen, a new club's player) is drawn by the
game from his 56 bytes of appearance data: the head shape, the eyes, nose, mouth, ears, chin, the
skin, hair style and colour, eyebrows, facial hair ... are sliders and types the game builds a 3D
head from (the in-game face editor writes the same bytes). The face pack of 30.09. gave every
regen one of 90 appearance records copied from real players (the "donors"), so many regens
looked like a real player and like each other. The pool here is new faces: every field is drawn
on its own, from how often the game's own players of that part of the world have each value of
that field (tools/facepool_stats.json). So a face is plausible for its region -- skin, hair and
eye colour, nose and lips -- and no face is any real player's.

The 56 bytes (PlayerAppearance.bin after the id; in memory at +0x0c of a 72-byte record):

  bytes 0-6   physique: neck, shoulders, chest/waist, arms, thigh/calf, leg/head length,
              head width/depth -- 4 bits each, stored +7. Drawn per byte from the region.
  bytes 7-9   strip: wrist tape, glasses, sleeves, inners, socks, undershorts, shirt out, ankle
              tape. Drawn per byte from all players, with glasses always off. Shirt out
              (untucked) is byte 9 bit 6 (0x40, the4chancup's Untucked, save bit 2094): 1 =
              out. 97.1% of the game's players have it (93.4% in FL27); the 3% without are the
              classic legends (Beckenbauer, Cruijff, Maradona, Platini ...), so the pool has it
              as often (97.3%).
  bytes 10-55 the in-game face run (46 bytes): the field map of the4chancup's pes_savefile
              (unlimited-tool-works, schema/ingame_face.rs, "measured in the games"), checked here
              against the game's 27,927 records: every field below is inside the values the game's
              own faces use (FIELDS, VALID). Skin is bits 0-2 of byte 33 (SKIN-COLOR-FINDING.md).

  sliders     drawn per region and skin band (light 1-2, middle 3-4, dark 5-6), each on its own
  types       cheek, forehead, facial hair, wrinkles, eyelids, eyebrow, neck line, nose, lips,
              eyebrow style/density/thickness, facial hair thickness, eye colour: the same way
  hair style  the ten hair fields together, one of the hair styles the game's players wear
              (HAIR, at least 3 players each, none with a 0 the editor does not offer), so no
              combination the game never draws (PES 21 crashes on a cropped-style high bit)
  hair colour preset + RGB together, as the game stores them; eyebrow and beard colour drawn
              for that hair colour (most often the same)
  unused bits the values the game's editor writes (7, 7, 7, 1)

Groups and nationality -> group are the face pack's (mkpack.py, facegroups.py B183 and 17.11.):
nweu seu eeu afr mena lat bra eas sas nord sea. The pool is made in two blocks (BLOCKS): the
first 20,000 faces as many per group as the game has players of the region (at least 1,000 each),
then 12,000 more where the new players of the big worlds are. The first block is the 06.11. pool
byte for byte, in the same order -- but for sas, made again on 17.11. (REDRAWN).

17.11. (mato: "obvious region errors + a new region"): sas was South + South-East Asia +
Oceania. It is South Asia now, South-East Asia (and Polynesia) is the new group sea, and the
nations the old map put in the wrong part of the world moved (facegroups.REGIONS_1711). sas and
sea are drawn from their own players' counts (`facepool.py regroup`); every other group keeps
its cell of the 06.11. counts and its faces, byte for byte and in its own order, so a player of
a nation that kept its group keeps his face (32,760 faces in all, ALLOC).

The pack (fl26regen_faces.bin, version 2):
  "FL26RF02", 512 bytes nationality -> group (0xff none), u32 n, n x (u8 group, u8 0,
  u16 portrait number or 0xffff = none, 56 appearance bytes)
The same shape as "FL26RF01"; the DLL (fl26regen.c) reads both, takes up to 32,767 faces and
picks face mix(id) of the player's group, so a player always gets the same face. A pool face has
no portrait (0xffff): the game shows its own picture for a player without one.

  python facepool.py stats <PlayerAppearance.bin> <tables dir> [<old pack>]
        the game's file (WESYS or unpacked) and its Player.bin -> tools/facepool_stats.json
        (nationality -> group from the old pack, else the one already in the stats). It counts
        every group again: with the 17.11. map, eeu, mena, eas, afr and lat would no longer be
        the counts their faces were drawn from, and their faces would change
  python facepool.py regroup <PlayerAppearance.bin> <tables dir>
        the 17.11. map (facegroups.regroup) into the stats, and the cells of REDRAWN (sas, sea)
        counted with it; every other group's cell and the shared tables stay as they are. The
        stats of 17.11. are FL26's data_s2526c.cpk (the file the 06.11. stats came from)
  python facepool.py build [--out DIR] [--seed N] [--real <PlayerAppearance.bin>]...
        DIR\fl26regen_faces.bin and DIR\FL26 Regen Faces\ (the livecpk root lbpack wants; empty
        but for a note). With --real, also checks that no pool face is any real player's face.
  python facepool.py near <PlayerAppearance.bin>...
        how many face fields each block's faces are from the nearest real face (the game's files:
        FL26 2.x and FL27 have several) and from each other (numpy); exits 1 and prints the new
        SKIP when a face of block 2 is nearer than MIN_APART to a real one
  python facepool.py show <pack>
  python facepool.py check <pack>
        is it the pool (pool_problems: the version, at least MIN_POOL faces, the map, the faces;
        portrait numbers aside)? Exits 1 when not
"""
import collections
import json
import os
import random
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STATS = os.path.join(HERE, "facepool_stats.json")
MAGIC1, MAGIC2 = b"FL26RF01", b"FL26RF02"
NO_PORTRAIT = 0xFFFF
MAX_FACES = 32767                      # the DLL keeps face numbers in int16
REC = 60                               # a pack face: group, 0, portrait, 56 bytes
APP_LEN = 56
RUN0 = 10                              # the face run starts at byte 10 of the 56
sys.path.insert(0, HERE)
import facegroups                      # noqa: E402  (the groups and the 17.11. map)
GROUPS = list(facegroups.GROUPS)       # nweu seu eeu afr mena lat bra eas sas nord sea
# The groups made again on 17.11. with the new map (facegroups.REGIONS_1711): sas lost South-East
# Asia and Oceania and got Pakistan, sea is new. Their cells are counted from their own players
# (`regroup`), their faces drawn anew and kept as far from every real face as block 2 (MIN_APART).
# Every other group keeps its 06.11. cell and its faces byte for byte.
REDRAWN = ("sas", "sea")
# The shipped pack is this pool (lbpack.py builds it, mszip.py checks it): never the 30.09. pack of
# 103 game faces ("FL26RF01", 6,704 bytes) again, never a pool smaller than this.
MIN_POOL = 20000
# The pool is made in blocks, each one group by group, every group drawing on with its own
# random stream, so a block added later leaves the faces before it as they were: the same bytes in
# the same place, and a portrait made for face k (facemini.py) still belongs to face k.
# Block 1 (06.11.): 20,000 faces, the groups as many as the game has players of the region, at
# least 1,000 each. Block 2 (07.11., mato "jos bar 10k faca"): 12,000 more where the new players
# are -- the Megapack's 87,930 new players (272 leagues, 193 countries) are eeu 18.9%, afr 19.1%,
# nweu 14.6%, lat 13.7%, mena 8.4%, sas 4.6%, nord 4.4%, eas 3.8%, bra 2.7%, seu 9.9% -- so every
# group ends near the same number of new players per face (2.8 to 2.9; it was 1.6 to 8.3).
# seu, bra and eas already had fewer than that per face (2.4, 1.6, 2.8) and get none.
# 17.11.: sas (1,000 + 400 until now) and sea are all in block 1 -- no career has their new faces,
# so none is an old one to keep -- and share the 2,160 faces the DLL has room for (32,767) by
# their new players in the GigaPack (beta 3): sas 1,763 (India 635, Nepal 346, Pakistan 245,
# Bangladesh 195, Bhutan 179, Maldives 153, Sri Lanka 10), sea 4,744 (South-East Asia 4,109,
# Polynesia 635): about 3 a face each.
BLOCKS = [
    {"seu": 3600, "nweu": 3200, "lat": 2800, "afr": 2200, "eeu": 2000, "bra": 1500,
     "mena": 1500, "eas": 1200, "sas": 590, "nord": 1000, "sea": 1570},
    {"afr": 3650, "eeu": 3800, "nweu": 1300, "lat": 1400, "mena": 1100, "nord": 350},
]
ALLOC = {g: sum(b.get(g, 0) for b in BLOCKS) for g in GROUPS}      # 32,760 in all
# How far a face of block 2 stays from every real player's face: at least MIN_APART of the 77
# face fields (FACE_PART) differ from the nearest face in the game's files (`facepool.py near`
# with the PlayerAppearance.bin of FL26 2.x and FL27: 33,977 different faces). Block 1 was made
# against one file and measures 25 at the least against all of them (26 against its own).
MIN_APART = 28
# The draws of block 2 that came closer than MIN_APART to a real face (`near` lists them): the
# draw is made and thrown away, so the faces after it stay, and the pack is the same without the
# game's files. Numbers only: no player's face is in here.
# The faces of block 1 that came out nearer than 26 fields to a real face of the newer files
# (`near`, 07.11.): mato "zamijeni ih" -- each is made again in its place (same number, same
# group, block 0) from its group's draws after the last block, as far from every real face as
# block 2 (MIN_APART). Every other face of block 1 stays byte for byte.
REPLACE = [3773, 15200]               # seu and lat, 25 fields from a real face
SKIP = {"afr": [4668, 5435], "eeu": [5247], "lat": [2912, 2931, 3103, 3149, 3334, 3394, 3717, 4116],
        "mena": [1663], "nord": [1235], "nweu": [4046],
        "sea": [284, 331, 1147, 1431, 1558]}  # 17.11., against the ten files of FL26 2.x and FL27 1.x
SEED = 2026

# the face run: (name, bit offset from byte 10, width)
FIELDS = [
    ("gloves", 0, 1), ("gloves_col", 1, 3), ("jawline", 4, 4), ("jaw_h", 8, 4), ("p15_jaw_d", 12, 4),
    ("cheekbones", 16, 4), ("cheekbone_h", 20, 4), ("p15_cheekbone_d", 24, 4), ("u28", 28, 4),
    ("u32", 32, 4), ("brow_w", 36, 4), ("in_brow_h", 40, 4), ("brow_d", 44, 4), ("temple_w", 48, 4),
    ("out_brow_h", 52, 4), ("p15_brow_d", 56, 4), ("pupil", 60, 4), ("eye_d", 64, 4),
    ("in_eye_pos", 68, 4), ("in_eye_h", 72, 4), ("out_eye_pos", 76, 4), ("eye_corner_h", 80, 4),
    ("ulid_w_in", 84, 4), ("ulid_h_in", 88, 4), ("ulid_w_out", 92, 4), ("ulid_h_out", 96, 4),
    ("p15_blid_pos", 100, 4), ("blid_h", 104, 4), ("eye_hpos", 108, 4), ("eye_h", 112, 4),
    ("nose_h", 116, 4), ("nose_tip", 120, 4), ("nostril_w", 124, 4), ("p15_nose_bridge", 128, 4),
    ("nose_d", 132, 4), ("nose_w", 136, 4), ("p15_nose_root", 140, 4), ("mouth_h", 144, 4),
    ("mouth_d", 148, 4), ("lip_size", 152, 4), ("u156", 156, 4), ("mouth_corner_h", 160, 4),
    ("lip_w", 164, 4), ("p15_mouth_edge", 168, 4), ("chin_w", 172, 4), ("chin_h", 176, 4),
    ("chin_d", 180, 4), ("skin", 184, 3), ("cheek_t", 187, 5), ("forehead_t", 192, 3),
    ("fhair_t", 195, 5), ("laugh_t", 200, 3), ("ulid_t", 203, 5), ("llid_t", 208, 4),
    ("ear_len", 212, 4), ("ear_w", 216, 4), ("ear_ang", 220, 4), ("brow_t", 224, 5),
    ("neckline_t", 229, 3), ("face_size", 232, 4), ("face_h", 236, 4), ("nose_t", 240, 6),
    ("u246", 246, 2), ("ulip_t", 248, 3), ("llip_t", 251, 3), ("hair_r", 254, 6), ("hair_g", 260, 6),
    ("hair_b", 266, 6), ("hstyle", 272, 4), ("hcrop", 276, 4), ("brow_r", 280, 6),
    ("brow_style", 286, 2), ("brow_g", 288, 6), ("brow_dens", 294, 2), ("brow_b", 296, 6),
    ("brow_thick", 302, 2), ("hlen", 304, 3), ("hwave", 307, 3), ("p15_white", 310, 2),
    ("hacc", 312, 1), ("hacc_col", 313, 3), ("fh_r", 316, 6), ("fh_g", 322, 6), ("fh_b", 328, 6),
    ("fh_thick", 334, 2), ("iris", 336, 4), ("hvar", 340, 8), ("hpreset", 348, 4),
    ("hfront", 352, 3), ("hparted", 355, 3), ("hsideback", 358, 3), ("hairline", 361, 3),
    ("hforehead", 364, 4)]
FIELD = {n: (o, w) for n, o, w in FIELDS}
SLIDERS = ["jawline", "jaw_h", "cheekbones", "cheekbone_h", "brow_w", "in_brow_h", "brow_d",
           "temple_w", "out_brow_h", "pupil", "eye_d", "in_eye_pos", "in_eye_h", "out_eye_pos",
           "eye_corner_h", "ulid_w_in", "ulid_h_in", "ulid_w_out", "ulid_h_out", "blid_h",
           "eye_hpos", "eye_h", "nose_h", "nose_tip", "nostril_w", "nose_d", "nose_w", "mouth_h",
           "mouth_d", "lip_size", "mouth_corner_h", "lip_w", "chin_w", "chin_h", "chin_d",
           "ear_len", "ear_w", "ear_ang", "face_size", "face_h"]
P15 = ["p15_jaw_d", "p15_cheekbone_d", "p15_brow_d", "p15_blid_pos", "p15_nose_bridge",
       "p15_nose_root", "p15_mouth_edge"]          # stored, drawn by PES 15 only
TYPES = ["cheek_t", "forehead_t", "fhair_t", "laugh_t", "ulid_t", "llid_t", "brow_t", "neckline_t",
         "nose_t", "ulip_t", "llip_t", "brow_style", "brow_dens", "brow_thick", "fh_thick", "iris"]
HAIR = ["hstyle", "hcrop", "hlen", "hwave", "hvar", "hfront", "hparted", "hsideback", "hairline",
        "hforehead"]
HAIR_NONZERO = ["hstyle", "hcrop", "hlen", "hwave", "hfront", "hparted", "hsideback", "hairline",
                "hforehead"]                    # 0 is "in some saves" only, what it draws is unknown
HCOL = ["hpreset", "hair_r", "hair_g", "hair_b"]
BROW = ["brow_r", "brow_g", "brow_b"]
FH = ["fh_r", "fh_g", "fh_b"]
FIXED = {"u28": 7, "u32": 7, "u156": 7, "u246": 1, "p15_white": 0}   # the editor's values
FACE_PART = SLIDERS + TYPES + HAIR + HCOL + BROW + FH + ["skin"]      # what makes the face
PHYS_BYTES = range(0, 7)
STRIP_BYTES = range(7, 10)
MIN_CELL = 150                         # fewer players than this in a region's skin band: the region
MIN_HAIR = 3                           # a hair style worn by at least this many players
MIN_COLOR = 10                         # a hair / eyebrow / beard colour of at least this many


def band(skin):
    return 0 if skin <= 2 else 1 if skin <= 4 else 2


# ---- the 56 bytes ----------------------------------------------------------------------------
def decode(blob):
    """56 appearance bytes -> {field: value} (+ "b0".."b9" for the physique and strip bytes)"""
    assert len(blob) == APP_LEN
    d = {"b%d" % i: blob[i] for i in range(RUN0)}
    v = int.from_bytes(blob[RUN0:], "little")
    for n, o, w in FIELDS:
        d[n] = (v >> o) & ((1 << w) - 1)
    return d


def encode(d):
    v = 0
    for n, o, w in FIELDS:
        x = d[n]
        assert 0 <= x < (1 << w), (n, x)
        v |= x << o
    return bytes(d["b%d" % i] for i in range(RUN0)) + v.to_bytes(APP_LEN - RUN0, "little")


# ---- the pack --------------------------------------------------------------------------------
def pack(natmap, faces, magic=MAGIC2, blocks=None):
    """faces: [(group, portrait, 56 bytes)]; blocks: each face's block (version 2 only, the
    second byte of the face; none: all block 0)"""
    assert len(natmap) == 512 and 0 < len(faces) <= MAX_FACES
    blocks = blocks or [0] * len(faces)
    assert len(blocks) == len(faces) and (magic == MAGIC2 or not any(blocks))
    body = b"".join(struct.pack("<BBH", g, bl, k) + bytes(b) for (g, k, b), bl in zip(faces, blocks))
    return magic + bytes(natmap) + struct.pack("<I", len(faces)) + body


def read_blocks(data):
    """each face's block (the second byte of a version 2 face; a version 1 pack is one block)"""
    ver, _nm, faces = read_pack(data)
    return [data[524 + i * REC + 1] if ver == 2 else 0 for i in range(len(faces))]


def read_pack(data):
    """-> (version 1 or 2, natmap, [(group, portrait, 56 bytes)])"""
    if data[:8] not in (MAGIC1, MAGIC2):
        raise ValueError("not a face pack")
    n = struct.unpack_from("<I", data, 520)[0]
    if len(data) != 524 + n * REC:
        raise ValueError("face pack: %d faces but %d bytes" % (n, len(data)))
    faces = []
    for i in range(n):
        o = 524 + i * REC
        g, _z, k = struct.unpack_from("<BBH", data, o)
        faces.append((g, k, bytes(data[o + 4:o + REC])))
    return (1 if data[:8] == MAGIC1 else 2), bytearray(data[8:520]), faces


def mix(x):
    """fl26regen.c mix(): splitmix64"""
    m = (1 << 64) - 1
    x = (x + 0x9e3779b97f4a7c15) & m
    x = ((x ^ (x >> 30)) * 0xbf58476d1ce4e5b9) & m
    x = ((x ^ (x >> 27)) * 0x94d049bb133111eb) & m
    return x ^ (x >> 31)


def pick_of(pid, k, n, n0):
    """fl26regen.c pick_of: the k-th of n faces, of which the first n0 are block 0"""
    if n0 <= 0 or n0 >= n:
        return k % n
    if mix(pid ^ 0xb10c5eed) % n < n0:
        return k % n0
    return n0 + k % (n - n0)


def face_of(natmap, faces, pid, nat, blocks=None):
    """the face index fl26regen.c face_of gives player pid of nationality nat (-1: none); blocks
    as pack's (none: all block 0, a version 1 pack)"""
    if not faces:
        return -1
    g = natmap[nat] if nat < 512 else 0xFF
    key = (id(faces), len(faces), id(blocks))
    if _INDEX.get("key") != key:
        bl = blocks or [0] * len(faces)
        idx, n0 = collections.defaultdict(list), collections.Counter()
        order = [i for i in range(len(faces)) if not bl[i]] + [i for i in range(len(faces)) if bl[i]]
        for i in order:
            idx[faces[i][0]].append(i)
            n0[faces[i][0]] += not bl[i]
        _INDEX.clear()
        _INDEX.update(key=key, idx=idx, n0=n0, all=order, all0=sum(n0.values()))
    idx = _INDEX["idx"].get(g)
    k = mix(pid ^ 0x5eedface)
    if not idx:
        return _INDEX["all"][pick_of(pid, k, len(faces), _INDEX["all0"])]
    return idx[pick_of(pid, k, len(idx), _INDEX["n0"][g])]


_INDEX = {}


# ---- the statistics of the game's faces -------------------------------------------------------
def _hist(values, floor=1):
    """{value: count} of the values at least floor times"""
    c = collections.Counter(values)
    return {str(k): v for k, v in sorted(c.items()) if v >= floor}


def _unwesys(d):
    if d[3:8] == b"WESYS":
        import zlib
        csz, usz = struct.unpack("<II", d[8:16])
        d = zlib.decompress(d[16:16 + csz])
        assert len(d) == usz
    return d


def _records(app_path, tables, natmap):
    """the game's faces with a placed nationality and a skin colour: ({group: [fields]}, all)"""
    raw = _unwesys(open(app_path, "rb").read())
    assert len(raw) % REC == 0
    import pesdb
    P = pesdb.load("Player", tables)
    natof = {}
    for i in range(len(P) // 312):
        r = P[i * 312:(i + 1) * 312]
        natof[struct.unpack_from("<I", r, 8)[0]] = (int.from_bytes(r, "little") >> 233) & 511
    recs = collections.defaultdict(list)
    allr = []
    for i in range(0, len(raw), REC):
        pid = struct.unpack_from("<I", raw, i)[0]
        n = natof.get(pid)
        if n is None or natmap[n] == 0xFF:
            continue
        d = decode(raw[i + 4:i + REC])
        if not 1 <= d["skin"] <= 6:
            continue
        g = GROUPS[natmap[n]]
        recs[g].append(d)
        allr.append(d)
    return recs, allr


def _cell(rs, hairs, cols):
    """one group's counts: skin, physique, and per skin band the sliders, types, hair style and
    colour (numbers into the stats' hairs / hair_colors)"""
    hset, cset = set(hairs), set(cols)
    cell = {"n": len(rs), "skin": _hist(d["skin"] for d in rs), "phys": {}, "bands": {}}
    for b in PHYS_BYTES:
        cell["phys"][str(b)] = _hist((d["b%d" % b] for d in rs), MIN_HAIR)
    for bd in range(3):
        sub = [d for d in rs if band(d["skin"]) == bd]
        use = sub if len(sub) >= MIN_CELL else rs
        c = {"n": len(sub), "own": len(sub) >= MIN_CELL}
        for f in SLIDERS + P15 + TYPES:
            c[f] = _hist(d[f] for d in use)
        c["hair"] = _hist(hairs.index(t) for t in (tuple(d[k] for k in HAIR) for d in use) if t in hset)
        c["hcol"] = _hist(cols.index(t) for t in (tuple(d[k] for k in HCOL) for d in use) if t in cset)
        cell["bands"][str(bd)] = c
    return cell


def regroup_stats(app_path, tables, st=None):
    """the stats with the 17.11. map (facegroups.regroup) and the cells of REDRAWN counted again
    with it. The shared tables (hair styles, colours, strip, the valid values) and every other
    group's cell stay: they are what the faces of those groups were drawn from."""
    st = st or load_stats()
    st["natmap"] = list(facegroups.regroup(st["natmap"]))
    recs, _allr = _records(app_path, tables, st["natmap"])
    hairs = [tuple(t) for t in st["hairs"]]
    cols = [tuple(t) for t in st["hair_colors"]]
    for g in REDRAWN:
        st["cells"][g] = _cell(recs[g], hairs, cols)
    st["groups"] = GROUPS
    st["kept"] = ("17.11.: the cells of %s are the 06.11. counts (with the old map) and stay, so the "
                  "faces of those groups stay the same; %s are counted with the 17.11. map"
                  % (" ".join(g for g in GROUPS if g not in REDRAWN), " ".join(REDRAWN)))
    return st


def make_stats(app_path, tables, old_pack=None):
    """the game's PlayerAppearance.bin and Player.bin -> the counts the pool is drawn from. Only
    counts of single values (or of whole hair styles / colours the game offers) per region: no
    record of a player is kept."""
    if old_pack:
        natmap = list(read_pack(open(old_pack, "rb").read())[1])
    else:
        natmap = load_stats()["natmap"]
    recs, allr = _records(app_path, tables, natmap)
    hair_n = collections.Counter(tuple(d[k] for k in HAIR) for d in allr)
    hairs = sorted(t for t, c in hair_n.items() if c >= MIN_HAIR and all(
        t[HAIR.index(k)] for k in HAIR_NONZERO))
    col_n = collections.Counter(tuple(d[k] for k in HCOL) for d in allr)
    cols = sorted(t for t, c in col_n.items() if c >= MIN_COLOR)
    rgb_n = collections.Counter(tuple(d[k] for k in BROW) for d in allr) + \
        collections.Counter(tuple(d[k] for k in FH) for d in allr)
    rgbs = sorted(t for t, c in rgb_n.items() if c >= MIN_COLOR)
    rset = set(rgbs)
    cells = {g: _cell(recs[g], hairs, cols) for g in GROUPS}
    # eyebrow and beard colour for each hair colour
    brow_of, fh_of = {}, {}
    for ci, t in enumerate(cols):
        sub = [d for d in allr if tuple(d[k] for k in HCOL) == t]
        brow_of[str(ci)] = _hist(rgbs.index(x) for x in (tuple(d[k] for k in BROW) for d in sub) if x in rset)
        fh_of[str(ci)] = _hist(rgbs.index(x) for x in (tuple(d[k] for k in FH) for d in sub) if x in rset)
    strip = {str(b): _hist((d["b%d" % b] & (0xC0 if b == 8 else 0xFF) for d in allr), MIN_COLOR)
             for b in STRIP_BYTES}
    glove = _hist(("%d,%d,%d,%d" % (d["gloves"], d["gloves_col"], d["hacc"], d["hacc_col"]) for d in allr),
                  MIN_COLOR)
    valid = {n: sorted({d[n] for d in allr}) for n, _o, _w in FIELDS}
    return {"about": "counts of the game's own faces per region (facepool.py stats); no player's "
                     "record is in here", "records": len(allr), "natmap": natmap, "groups": GROUPS,
            "hairs": [list(t) for t in hairs], "hair_colors": [list(t) for t in cols],
            "rgbs": [list(t) for t in rgbs], "brow_of": brow_of, "fh_of": fh_of, "strip": strip,
            "glove": glove, "valid": valid, "cells": cells}


def load_stats(path=STATS):
    return json.load(open(path, encoding="utf-8"))


# ---- the pool --------------------------------------------------------------------------------
class _Pick:
    """draws from {value: count} tables; a table is turned into (values, cumulative) once"""
    def __init__(self, rng):
        self.rng, self.cache = rng, {}

    def __call__(self, hist):
        key = id(hist)
        t = self.cache.get(key)
        if t is None:
            vals, cum, s = [], [], 0
            for k, c in hist.items():
                s += c
                vals.append(k)
                cum.append(s)
            t = self.cache[key] = (vals, cum, s, hist)
        vals, cum, s, _h = t
        import bisect
        return vals[bisect.bisect_right(cum, self.rng.randrange(s))]


def make_face(st, g, pick):
    """one new face of group g: a dict of every field"""
    cell = st["cells"][g]
    d = dict(FIXED)
    d["skin"] = int(pick(cell["skin"]))
    c = cell["bands"][str(band(d["skin"]))]
    for b in PHYS_BYTES:
        d["b%d" % b] = int(pick(cell["phys"][str(b)]))
    for b in STRIP_BYTES:
        d["b%d" % b] = int(pick(st["strip"][str(b)]))      # byte 8: sleeves only, no glasses
    d["gloves"], d["gloves_col"], d["hacc"], d["hacc_col"] = map(int, pick(st["glove"]).split(","))
    for f in SLIDERS + P15 + TYPES:
        d[f] = int(pick(c[f]))
    for k, v in zip(HAIR, st["hairs"][int(pick(c["hair"]))]):
        d[k] = v
    ci = pick(c["hcol"])
    for k, v in zip(HCOL, st["hair_colors"][int(ci)]):
        d[k] = v
    for keys, of in ((BROW, st["brow_of"]), (FH, st["fh_of"])):
        h = of.get(ci) or {}
        rgb = st["rgbs"][int(pick(h))] if h else (d["hair_r"], d["hair_g"], d["hair_b"])
        for k, v in zip(keys, rgb):
            d[k] = v
    return d


def face_key(d):
    return tuple(d[k] for k in FACE_PART)


def block_of_pool(blocks=None):
    """the block of each face of make_pool's pool, in its order"""
    return [bi for bi, blk in enumerate(blocks or BLOCKS) for _g in GROUPS for _i in range(blk.get(_g, 0))]


def make_pool(st=None, seed=SEED, alloc=None, avoid=(), blocks=None, skip=None, draws=None, replace=None):
    """[(group, 56 bytes)]: block by block (BLOCKS, or the one block alloc), each group by group in
    GROUPS order; each group draws on from where it stopped in the block before. No two faces
    alike (FACE_PART), none alike any face in avoid (keys of real players' faces), and none of
    the draws skip names ({group: [draw number]}; SKIP for BLOCKS). draws (a list) gets each
    face's (group, draw number). The faces replace names (REPLACE for BLOCKS) are drawn again,
    in place, after the last block."""
    st = st or load_stats()
    if skip is None:
        skip = {} if alloc or blocks else SKIP
    if replace is None:
        replace = [] if alloc or blocks else REPLACE
    skip = {g: set(v) for g, v in skip.items()}
    blocks = [alloc] if alloc else (blocks or BLOCKS)
    seen, out, picks, drawn = set(avoid), [], {}, collections.Counter()
    for blk in blocks:
        for gi, g in enumerate(GROUPS):
            want = blk.get(g, 0)
            if not want:
                continue
            if g not in picks:
                picks[g] = _Pick(random.Random("facepool:%d:%s" % (seed, g)))
            pick = picks[g]
            made = tries = 0
            while made < want:
                tries += 1
                if tries > want * 20:
                    raise RuntimeError("%s: only %d different faces" % (g, made))
                d = make_face(st, g, pick)
                n = drawn[g]
                drawn[g] += 1
                k = face_key(d)
                if k in seen or n in skip.get(g, ()):
                    continue
                seen.add(k)
                out.append((gi, encode(d)))
                if draws is not None:
                    draws.append((g, n))
                made += 1
    for i in sorted(replace):
        gi = out[i][0]
        g = GROUPS[gi]
        pick = picks[g]
        while True:
            d = make_face(st, g, pick)
            n = drawn[g]
            drawn[g] += 1
            k = face_key(d)
            if k not in seen and n not in skip.get(g, ()):
                break
        seen.add(k)
        out[i] = (gi, encode(d))
        if draws is not None:
            draws[i] = (g, n)
    return out


def real_keys(paths):
    """the face keys (FACE_PART) of every record of the game's PlayerAppearance.bin files"""
    keys = set()
    for p in paths:
        raw = _unwesys(open(p, "rb").read())
        keys |= {face_key(decode(raw[i + 4:i + REC])) for i in range(0, len(raw), REC)}
    return keys


def nearest(faces, others, same=False, chunk=24):
    """for each face key of faces, how many of the 77 fields differ from the nearest of others
    (same: faces is others, a face is not its own nearest). numpy; about 80 s for 32,000 x 34,000"""
    import numpy as np
    A = np.array(faces, dtype=np.uint8)
    B = np.array(others, dtype=np.uint8)
    out = np.empty(len(A), dtype=np.int32)
    for i in range(0, len(A), chunk):
        d = (A[i:i + chunk, None, :] != B[None, :, :]).sum(2)
        if same:
            for j in range(d.shape[0]):
                d[j, i + j] = 1 << 20
        out[i:i + chunk] = d.min(1)
    return out.tolist()


def near(real, seed=SEED, log=print):
    """how far the pool's faces are from the real ones and from each other, block by block; the
    faces of block 2 and on nearer than MIN_APART to a real one (their draws go into SKIP).
    Returns [(group, draw, fields apart)] of those."""
    st = load_stats()
    draws = []
    pool = make_pool(st, seed, draws=draws)
    keys = [face_key(decode(b)) for _g, b in pool]
    rk = sorted(real_keys(real))
    log("%d faces in the pool, %d different real faces in %d file(s)" % (len(keys), len(rk), len(real)))
    dr = nearest(keys, rk)
    dp = nearest(keys, keys, same=True)
    lo, bad = 0, []
    for bi, blk in enumerate(BLOCKS):
        hi = lo + sum(blk.values())
        log("  block %d (%d faces): the nearest real face %d fields apart at the least (mean %.1f), "
            "the nearest pool face %d (mean %.1f)" % (bi + 1, hi - lo, min(dr[lo:hi]), sum(dr[lo:hi]) / (hi - lo),
                                                      min(dp[lo:hi]), sum(dp[lo:hi]) / (hi - lo)))
        if bi:
            bad += [draws[i] + (dr[i],) for i in range(lo, hi) if dr[i] < MIN_APART]
        else:
            for i in range(lo, hi):
                if (i in REPLACE or draws[i][0] in REDRAWN) and dr[i] < MIN_APART:
                    bad.append(draws[i] + (dr[i],))
                elif dr[i] < 26:
                    log("  block 1 face %d (%s) only %d fields from a real face: for REPLACE" % (i, draws[i][0], dr[i]))
        lo = hi
    for g, n, d in bad:
        log("  too near a real face: %s draw %d (%d fields apart)" % (g, n, d))
    if bad:
        add = collections.defaultdict(set)
        for g, v in SKIP.items():
            add[g] |= set(v)
        for g, n, _d in bad:
            add[g].add(n)
        log("SKIP = %s" % json.dumps({g: sorted(v) for g, v in sorted(add.items())}))
    return bad


def check_face(st, blob):
    """the fields of a face outside what the game's own faces use: [] when every one is inside"""
    d = decode(blob)
    bad = [n for n, _o, _w in FIELDS if d[n] not in st["valid"][n] and n not in FIXED]
    if not 1 <= d["skin"] <= 6:
        bad.append("skin")
    if d["b8"] & 0x3F:
        bad.append("glasses")
    if tuple(d[k] for k in HAIR) not in {tuple(t) for t in st["hairs"]}:
        bad.append("hair")
    return bad


# md5 of the pack `build` writes (seed SEED, no portraits): lbpack.py ships exactly this, mszip.py
# and test_face_pool.py check it. A change of the pool (BLOCKS, SKIP, the stats) changes it here.
POOL_MD5 = "251cb278935327164e4b6ec86e98b0b6"    # 17.11.: 32,760 faces, 1,966,124 bytes


def pool_pack(st=None, seed=SEED, avoid=()):
    """the pack of the pool, as `build` writes it"""
    st = st or load_stats()
    pool = make_pool(st, seed, avoid=avoid)
    return pack(st["natmap"], [(g, NO_PORTRAIT, b) for g, b in pool], blocks=block_of_pool())


def portrait_problems(data, root):
    """why a face pack's portraits are not all there ([]: each portrait number has its 128 x 128
    DXT5 .dds under <root>/common/render/symbol/player/regen). facemini.py share gives many
    faces one number; the loader asks for regen/<number>.dds, so a number without its file is a
    face with a broken picture."""
    _v, _nm, faces = read_pack(data)
    nums = sorted(set(k for _g, k, _b in faces if k != NO_PORTRAIT))
    d = os.path.join(root, "common", "render", "symbol", "player", "regen")
    missing = [k for k in nums if not os.path.isfile(os.path.join(d, "%d.dds" % k))]
    bad = ["%d portrait number(s) with no .dds (%s)" % (len(missing), ", ".join(map(str, missing[:8])))] if missing else []
    for k in nums:
        if k in missing:
            continue
        with open(os.path.join(d, "%d.dds" % k), "rb") as f:
            hd = f.read(128)
        h, w = struct.unpack_from("<II", hd, 12) if len(hd) == 128 else (0, 0)
        if hd[:4] != b"DDS " or (w, h, hd[84:88]) != (128, 128, b"DXT5"):
            bad.append("regen/%d.dds is not a 128 x 128 DXT5 portrait" % k)
    return bad


def pool_problems(data, want=None):
    """why a face pack is not the face pool ([]: it is). A portrait number may differ (facemini.py
    pack gives a face with a picture its number); the version, the map, the faces, their groups
    and blocks may not. want: the pool's pack (pool_pack() when none)."""
    if data[:8] != MAGIC2:
        return ["not the face pool (%s, %d bytes%s)" % (
            data[:8].decode("latin-1") if data[:8] else "empty", len(data),
            ": the 30.09. pack of game faces" if data[:8] == MAGIC1 else "")]
    try:
        _v, natmap, faces = read_pack(data)
    except ValueError as e:
        return [str(e)]
    if len(faces) < MIN_POOL:
        return ["%d faces, the pool has at least %d" % (len(faces), MIN_POOL)]
    want = want or pool_pack()
    _w, wnat, wfaces = read_pack(want)
    bad = []
    if natmap != wnat:
        bad.append("the nationality map is not the pool's (%d nationalities differ: %s)" % (
            sum(1 for a, b in zip(natmap, wnat) if a != b),
            ", ".join(str(i) for i, (a, b) in enumerate(zip(natmap, wnat)) if a != b)[:80]))
    if len(faces) != len(wfaces):
        bad.append("%d faces, the pool has %d" % (len(faces), len(wfaces)))
    elif read_blocks(data) != read_blocks(want) or any(
            (g, b) != (wg, wb) for (g, _k, b), (wg, _wk, wb) in zip(faces, wfaces)):
        bad.append("its faces are not the pool's (%d differ)" % sum(
            1 for (g, _k, b), (wg, _wk, wb) in zip(faces, wfaces) if (g, b) != (wg, wb)))
    return bad


def build(out, seed=SEED, real=None, log=print):
    st = load_stats()
    avoid = real_keys(real) if real else set()
    data = pool_pack(st, seed, avoid)
    os.makedirs(os.path.join(out, "FL26 Regen Faces"), exist_ok=True)
    open(os.path.join(out, "FL26 Regen Faces", "readme.txt"), "w", encoding="utf-8", newline="\n").write(
        "FL26 face pool (facepool.py): the faces are numbers in fl26regen_faces.bin, no portraits.\n")
    path = os.path.join(out, "fl26regen_faces.bin")
    open(path, "wb").write(data)
    import hashlib
    log("face pool: %d faces, seed %d%s -> %s (md5 %s)" % (
        struct.unpack_from("<I", data, 520)[0], seed,
        ", none a real player's (%d checked)" % len(avoid) if real else "", path, hashlib.md5(data).hexdigest()))
    show(data, log)
    return path


def show(data, log=print):
    ver, natmap, faces = read_pack(data)
    log("version %d, %d faces, %d nationalities placed" % (ver, len(faces), sum(1 for x in natmap if x != 0xFF)))
    for gi, g in enumerate(GROUPS):
        fs = [decode(b) for gg, _k, b in faces if gg == gi]
        if not fs:
            continue
        sk = collections.Counter(f["skin"] for f in fs)
        log("  %-5s %5d faces  skin %s  beard %d%%  blue/grey/green eyes %d%%" % (
            g, len(fs), " ".join("%d:%d%%" % (s, round(100 * sk[s] / len(fs))) for s in range(1, 7)),
            round(100 * sum(1 for f in fs if f["fhair_t"]) / len(fs)),
            round(100 * sum(1 for f in fs if f["iris"] in (4, 6, 7, 9)) / len(fs))))


def main(a):
    if not a or a[0] not in ("stats", "regroup", "build", "show", "near", "check"):
        raise SystemExit(__doc__)
    if a[0] in ("stats", "regroup"):
        st = make_stats(a[1], a[2], a[3] if len(a) > 3 else None) if a[0] == "stats" else regroup_stats(a[1], a[2])
        json.dump(st, open(STATS, "w", encoding="utf-8", newline="\n"), separators=(",", ":"), sort_keys=True)
        print("%s: %d records, %d hair styles, %d hair colours; %s" % (
            STATS, st["records"], len(st["hairs"]), len(st["hair_colors"]),
            ", ".join("%s %d" % (g, st["cells"][g]["n"]) for g in GROUPS if g in st["cells"])))
    elif a[0] == "check":
        bad = pool_problems(open(a[1], "rb").read())
        print("\n".join(bad) or "%s: the face pool" % a[1])
        sys.exit(1 if bad else 0)
    elif a[0] == "build":
        def get(k, d=None):
            return a[a.index(k) + 1] if k in a else d
        real = [a[i + 1] for i, x in enumerate(a) if x == "--real"]
        build(get("--out", os.path.join(HERE, "..", "out", "facepool")), int(get("--seed", SEED)), real)
    elif a[0] == "near":
        sys.exit(1 if near(a[1:]) else 0)
    else:
        show(open(a[1], "rb").read())


if __name__ == "__main__":
    main(sys.argv[1:])
