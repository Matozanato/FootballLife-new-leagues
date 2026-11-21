r"""python tools/test_face_pool.py -- the face pool (mato 06.11.: "15-20 tisuca lica ... da ne
posudujemo od drugih igraca"): regens and the world's new players get faces of our own, made from
numbers (tools/facepool.py), instead of 90 faces copied from real players.

The pool: 32,760 faces (mato 07.11.: "jos bar 10k faca"; 17.11.: the new group sea), the groups'
sizes as ALLOC, in two blocks: the first the 06.11. pool byte for byte and in the same order for
every group but the two made again on 17.11. (REDRAWN: sas, sea), then 11,600 more where the new
players are, none of them nearer a real face than the draws SKIP leaves out; the
same bytes for the same seed and others for another seed, no two faces alike, every field inside the values the game's own faces use (and
a hair style the game's players wear, no glasses, the editor's unused bits), skin colour that
fits the region (Nordic and Eastern Europe light, Africa dark, Latin America and Brazil mixed, East
Asia skin 2) and blue/grey/green eyes more often in the north than in Africa or East Asia.

The pack: version 2 ("FL26RF02", no portraits) reads back as written; version 1 still reads.

The DLL (fl26regen.c, built here when zig is found; else that half is skipped): it loads a
version 2 pool and a version 1 pack and picks the same face for a player as facepool.face_of --
which for a version 1 pack is the walk the DLL did before the group index, so a career's regens
keep their faces with the old pack -- and refuses a pack that is too big or cut short.
"""
import ctypes, glob, hashlib, os, random, shutil, struct, subprocess, sys, tempfile, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import facepool as F

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def find_zig():
    z = os.environ.get("ZIG")
    if z and os.path.exists(z):
        return z
    z = shutil.which("zig")
    if z:
        return z
    found = sorted(glob.glob("D:/dev/tools/zig-*/zig.exe"))
    return found[-1] if found else None


def old_face_of(natmap, faces, pid, nat):
    """fl26regen.c face_of as it was before the group index (30.09.-06.11.)"""
    g = natmap[nat] if nat < 512 else 0xFF
    n = sum(1 for f in faces if f[0] == g)
    if not n:
        g, n = -1, len(faces)
    k = F.mix(pid ^ 0x5eedface) % n
    for i, f in enumerate(faces):
        if (g < 0 or f[0] == g):
            if k == 0:
                return i
            k -= 1
    return -1


def share(fs, test):
    return sum(1 for f in fs if test(f)) / len(fs)


OWNER_RVA, STRIDE, R_ID, R_NAT = 0x3705E10, 0x17C, 0x30, 0x144   # fl26regen.c


def new_players(D, natmap, old, load):
    """the world's new players past 65,536 (06.11.2026, the FL27 Megapack: 86,400 listed, the
    DLL took the first 65,536 by id and a whole league -- Aalborg's "FL P55381".."FL P55410",
    ids 241,915-241,944 -- kept the game's one default head). new_scan runs on a database block
    of the test's own (the DLL built with -DFL26REGEN_TEST)."""
    D.fl26_regen_test_block.argtypes = [ctypes.c_uint64, ctypes.c_uint32]
    D.fl26_regen_new.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_int]
    load(F.pack(natmap, old, F.MAGIC1))        # portraits 0..89: fl26_regen_face shows the pick
    held = []

    def block(ids):
        blk = ctypes.create_string_buffer(len(ids) * STRIDE + 8)
        for i, pid in enumerate(ids):
            struct.pack_into("<I", blk, i * STRIDE + R_ID, pid)
            struct.pack_into("<H", blk, i * STRIDE + R_NAT, (237, 80, 13, 146, 200)[pid % 5])
        struct.pack_into("<I", blk, len(ids) * STRIDE, len(ids))
        owner = ctypes.create_string_buffer(0x68)
        struct.pack_into("<Q", owner, 0x48, ctypes.addressof(blk))
        cell = ctypes.c_uint64(ctypes.addressof(owner))
        held.extend((blk, owner, cell))            # the DLL reads them until the next block
        D.fl26_regen_test_block((ctypes.addressof(cell) - OWNER_RVA) % (1 << 64), len(ids) * STRIDE)

    # the Megapack's shape: the game's 26,395 ids, then 86,400 new players in ranges of 30 up to
    # the id bound; one range of 30 listed twice (lists may overlap) and ids listed that the
    # database does not hold
    game = list(range(1, 26396))
    new = list(range(262144 - 86400, 262144))
    for k in range(0, len(new), 330):
        D.fl26_regen_new(new[k], new[min(k + 329, len(new) - 1)], 0)
    D.fl26_regen_new(new[0], new[29], 0)
    D.fl26_regen_new(300000, 300100, 0)

    block(game + new[:20000])                     # a smaller block first: the lists grow later
    ok("a block with 20,000 new players: all 20,000 found", D.fl26_regen_test_scan() == 20000)
    block(game + new)
    got = D.fl26_regen_test_scan()
    ok("86,400 new players listed: all %d get a face (65,536 before)" % got, got == 86400)
    probe = [new[0], new[65535], new[65536], 241915, 241944, new[-1]]
    ok("the ids past the 65,536th (241,280 on, Aalborg's 241,915-241,944, 262,143) get their face",
       all(D.fl26_regen_face(p) == old_face_of(natmap, old, p, (237, 80, 13, 146, 200)[p % 5]) for p in probe))
    ok("a game player is not one of them", D.fl26_regen_face(26395) == -1 and D.fl26_regen_face(1) == -1)
    block(game + new[:100])
    ok("a smaller block again (another save): 100, the lists kept", D.fl26_regen_test_scan() == 100
       and D.fl26_regen_face(new[50]) >= 0 and D.fl26_regen_face(new[150]) == -1)
    block(game + new)
    ok("and the whole world once more: 86,400", D.fl26_regen_test_scan() == 86400)


# md5 of each group's faces (its block byte, then the 56 bytes of each, in the pack's order) of the
# 06.11. pool of 20,000 (make_pool(blocks=BLOCKS[:1]) before 17.11.; the pack of 06.11., md5
# 644a96cf, holds them) and of the 07.11. pool of 32,000 (md5 59181dc5): every group but REDRAWN
# must stay them, so a player of a nation that kept its group keeps his face
KEPT20_MD5 = {"nweu": "323041fb0279a8371391018a6bede1e8", "seu": "d5cbb5c02fb622bee93934b3b6beb278",
              "eeu": "5c1790c70d85267d4241830b1199b349", "afr": "acd0e92917b4b9737a4a254b117ffcac",
              "mena": "aa8d11fdc4524d8b927140dd595ef129", "lat": "08ed4f6fe8b7d4047435df503ff73edc",
              "bra": "7fd1346d1381f1a06a514dc5ae41a897", "eas": "60eaf05a75c810dfc28a6c95af6a443e",
              "nord": "0f7d602e52f1d3539955948e2bf07896"}
KEPT32_MD5 = {"nweu": "50422725d64f8a69c8b9925738d364b6", "seu": "0da9fe0559aca39d7f6b51626a5cbf26",
              "eeu": "3e2a4df077177000aece6a305a825399", "afr": "128f3016fc8aadb6983b4c9263420121",
              "mena": "53b3d245928960bfe14cc21c01f458e5", "lat": "0ff7b00eb6ed79bbf7a705fc20b5b9fa",
              "bra": "7fd1346d1381f1a06a514dc5ae41a897", "eas": "60eaf05a75c810dfc28a6c95af6a443e",
              "nord": "c986ab3a5826577836df8d37f18ecfb3"}


def group_md5(pool, blocks=None):
    h = collections.defaultdict(hashlib.md5)
    for i, (g, b) in enumerate(pool):
        h[F.GROUPS[g]].update(bytes([blocks[i] if blocks else 0]) + b)
    return {g: x.hexdigest() for g, x in h.items()}


def main():
    st = F.load_stats()
    draws = []
    pool = F.make_pool(st, draws=draws)
    total = sum(F.ALLOC.values())
    ok("the pool holds %d faces (at least 30,000 asked, the DLL takes 32,767)" % len(pool),
       len(pool) == total and 30000 <= total <= F.MAX_FACES)
    n1 = sum(F.BLOCKS[0].values())
    kept = [g for g in F.GROUPS if g not in F.REDRAWN]
    ok("the groups made again on 17.11. are sas and sea, the other %d keep theirs" % len(kept),
       tuple(F.REDRAWN) == ("sas", "sea") and set(kept) == set(KEPT20_MD5))
    pool20 = F.make_pool(st, blocks=F.BLOCKS[:1])            # block 1 alone: no REPLACE, no SKIP
    m20, m32 = group_md5(pool20), group_md5(pool, F.block_of_pool())
    ok("block 1: every kept group's faces are the 06.11. pool's, the same bytes in the same order",
       all(m20[g] == KEPT20_MD5[g] for g in kept))
    ok("the whole pool: every kept group's faces and blocks are the 07.11. pool's (REPLACE and SKIP "
       "included), byte for byte", all(m32[g] == KEPT32_MD5[g] for g in kept))
    keptg = {F.GROUPS.index(g) for g in kept}
    same = [i for i in range(n1) if pool[i][0] in keptg and pool[i] == pool20[i]]
    ok("in block 1 a kept group's face differs from the plain draw only at the %d REPLACE faces %s"
       % (len(F.REPLACE), F.REPLACE),
       set(i for i in range(n1) if pool[i][0] in keptg) - set(same) == set(F.REPLACE))
    ok("a REPLACE face keeps its place: the same group, block 1",
       all(pool[i][0] == pool20[i][0] for i in F.REPLACE) and all(F.block_of_pool()[i] == 0 for i in F.REPLACE))
    ok("block 2: the %d new faces only where the new players are (%s)" % (sum(F.BLOCKS[1].values()), ", ".join(
       "%s +%d" % (g, n) for g, n in F.BLOCKS[1].items())), sum(F.BLOCKS[1].values()) == 11600
       and all(F.BLOCKS[1].get(g, 0) == 0 for g in ("seu", "bra", "eas", "sas", "sea")))
    skipped = {(g, n) for g, v in F.SKIP.items() for n in v}
    ok("the %d draws too near a real face are not in the pool; a kept group's are all past block 1"
       % len(skipped), skipped and not skipped & set(draws) and len(draws) == len(pool)
       and all(n >= max(nn for i, (gg, nn) in enumerate(draws[:n1]) if gg == g and i not in F.REPLACE)
               for g, n in skipped if g not in F.REDRAWN))
    by = collections.defaultdict(list)
    for g, b in pool:
        by[F.GROUPS[g]].append(F.decode(b))
    ok("each group has its share (%s)" % ", ".join("%s %d" % (g, len(by[g])) for g in F.GROUPS),
       all(len(by[g]) == F.ALLOC[g] for g in F.GROUPS) and min(F.ALLOC[g] for g in kept) >= 1000
       and F.ALLOC["sas"] >= 500 and F.ALLOC["sea"] >= 1500)
    ok("each block is in group order", all([g for g, _b in blk] == sorted(g for g, _b in blk)
                                              for blk in (pool[:n1], pool[n1:])))
    ok("the same seed: the same pool", F.make_pool(st) == pool)
    other = F.make_pool(st, seed=F.SEED + 1)
    ok("another seed: another pool", sum(1 for a, b in zip(pool, other) if a == b) < 10)
    keys = [F.face_key(F.decode(b)) for _g, b in pool]
    ok("no two faces alike", len(set(keys)) == len(keys) and len({b for _g, b in pool}) == len(pool))
    bad = collections.Counter(x for _g, b in pool for x in F.check_face(st, b))
    ok("every field inside the game's own values, a game hair style, no glasses (%s)" % (dict(bad) or "none off"),
       not bad)
    ok("every face round-trips through decode/encode", all(F.encode(F.decode(b)) == b for _g, b in pool[:2000]))
    ok("the editor's unused bits and the PES 15 eye white as the game writes them",
       all(all(f[k] == v for k, v in F.FIXED.items()) for fs in by.values() for f in fs))
    ok("skin 1..6 only", all(1 <= f["skin"] <= 6 for fs in by.values() for f in fs))
    out = share([b for _g, b in pool], lambda b: b[9] & 0x40)
    ok("shirt out (byte 9 bit 6) as often as the game's players wear it, 97%% (%.1f%%)" % (100 * out),
       0.95 <= out <= 1.0)

    light = lambda f: f["skin"] <= 2
    dark = lambda f: f["skin"] >= 5
    sh = {g: (share(by[g], light), share(by[g], dark)) for g in F.GROUPS}
    print("   light/dark: " + ", ".join("%s %d/%d%%" % (g, 100 * a, 100 * b) for g, (a, b) in sh.items()))
    ok("Nordic faces light (skin 1-2 at least 70%, dark at most 10%)", sh["nord"][0] >= 0.70 and sh["nord"][1] <= 0.10)
    ok("Eastern Europe light (80%), almost none dark", sh["eeu"][0] >= 0.80 and sh["eeu"][1] <= 0.03)
    ok("Africa dark (skin 5-6 at least 75%), almost none light", sh["afr"][1] >= 0.75 and sh["afr"][0] <= 0.03)
    ok("East Asia mostly skin 2", share(by["eas"], lambda f: f["skin"] == 2) >= 0.6)
    ok("South Asia mostly brown (skin 3-4 at least 65%%: %.0f%%), few light" % (
       100 * share(by["sas"], lambda f: F.band(f["skin"]) == 1)),
       share(by["sas"], lambda f: F.band(f["skin"]) == 1) >= 0.65 and sh["sas"][0] <= 0.25)
    ok("South-East Asia skin 2-4 (at least 85%%: %.0f%%), almost none dark" % (
       100 * share(by["sea"], lambda f: 2 <= f["skin"] <= 4)),
       share(by["sea"], lambda f: 2 <= f["skin"] <= 4) >= 0.85 and sh["sea"][1] <= 0.05)
    ok("Latin America and Brazil mixed (each band at least 10%)",
       all(share(by[g], lambda f, b=b: F.band(f["skin"]) == b) >= 0.10 for g in ("lat", "bra") for b in range(3)))
    eyes = {g: share(by[g], lambda f: f["iris"] in (4, 6, 7, 9)) for g in F.GROUPS}
    ok("blue/grey/green eyes: north %.0f%% > Africa %.0f%%, East Asia %.0f%%" % (
       100 * eyes["nord"], 100 * eyes["afr"], 100 * eyes["eas"]),
       eyes["nord"] > 3 * eyes["afr"] and eyes["nord"] > 3 * eyes["eas"])
    blond = {g: share(by[g], lambda f: f["hpreset"] in (7, 8)) for g in F.GROUPS}
    ok("light hair more often in the north (%.0f%%) than in Africa (%.0f%%)" % (100 * blond["nord"], 100 * blond["afr"]),
       blond["nord"] > 3 * blond["afr"])
    hairs = len({tuple(f[k] for k in F.HAIR) for fs in by.values() for f in fs})
    colors = len({tuple(f[k] for k in F.HCOL) for fs in by.values() for f in fs})
    beards = len({f["fhair_t"] for fs in by.values() for f in fs})
    ok("many hair styles (%d), hair colours (%d), facial hair types (%d)" % (hairs, colors, beards),
       hairs >= 500 and colors >= 8 and beards >= 15)
    afro = {g: share(by[g], lambda f: f["hstyle"] in (4, 5, 6)) for g in F.GROUPS}
    ok("afro / dreadlocks / braids more often in Africa (%.0f%%) than in East Asia (%.0f%%)" % (
       100 * afro["afr"], 100 * afro["eas"]), afro["afr"] > 3 * afro["eas"])

    # ---- the pack ----
    natmap = bytearray(st["natmap"])
    faces = [(g, F.NO_PORTRAIT, b) for g, b in pool]
    blocks = F.block_of_pool()
    data = F.pack(natmap, faces, blocks=blocks)
    ok("version 2 pack: magic, size %d" % len(data), data[:8] == b"FL26RF02" and len(data) == 524 + 60 * len(faces))
    ver, nm, back = F.read_pack(data)
    ok("version 2 pack reads back as written, no portraits, the block in each face's second byte",
       ver == 2 and nm == natmap and back == faces and F.read_blocks(data) == blocks
       and blocks.count(0) == n1 and blocks.count(1) == len(pool) - n1)
    ok("Sweden on nord, Nigeria on afr, Japan on eas, Brazil on bra, Croatia on eeu",
       [F.GROUPS[natmap[n]] for n in (237, 80, 13, 146, 200)] == ["nord", "afr", "eas", "bra", "eeu"])
    ok("17.11.: India and Pakistan on sas, Indonesia, Thailand and Samoa on sea, Kazakhstan on eas, "
       "Uzbekistan on mena, Fiji on afr, Belize on lat",
       [F.GROUPS[natmap[n]] for n in (9, 27, 10, 36, 168, 216, 240, 164, 108)]
       == ["sas", "sas", "sea", "sea", "sea", "eas", "mena", "afr", "lat"])
    v1 = F.pack(natmap, faces[:300], F.MAGIC1)
    ok("a version 1 pack still reads", F.read_pack(v1)[0] == 1)
    try:
        F.read_pack(data[:-1])
        cut = False
    except ValueError:
        cut = True
    ok("a pack cut short is refused", cut)

    # ---- the DLL ----
    zig = find_zig()
    if not zig:
        print("test_face_pool: no zig -- the DLL half skipped")
        print("test_face_pool: ok (%d)" % N)
        return
    T = tempfile.mkdtemp(prefix="facepool-")
    dll = os.path.join(T, "fl26regen.dll")

    def cc(src, out):
        subprocess.run([zig, "cc", "-shared", "-target", "x86_64-windows-gnu", "-O2", "-s", "-DFL26REGEN_TEST", "-o",
                        out, src, "-lkernel32"], check=True, capture_output=True)
    cc(os.path.join(HERE, "native", "fl26regen.c"), dll)
    D = ctypes.CDLL(dll)
    D.fl26_regen_faces_load.argtypes = [ctypes.c_char_p]
    D.fl26_regen_face_pick.argtypes = [ctypes.c_uint32, ctypes.c_uint]
    D.fl26_regen_face.argtypes = [ctypes.c_uint32]

    def load(blob):
        p = os.path.join(T, "pack.bin")
        open(p, "wb").write(blob)
        D.fl26_regen_faces_load(p.encode("mbcs"))

    rng = random.Random(7)
    probe = [(rng.randrange(1, 1 << 20), rng.randrange(512)) for _ in range(3000)]
    probe += [(pid, n) for pid in (100000, 400001, 999999) for n in (237, 80, 13, 146, 200, 260, 511)]
    load(data)
    got = [D.fl26_regen_face_pick(p, n) for p, n in probe]
    ok("the DLL loads the %d-face pool and picks what facepool.face_of picks" % len(faces),
       got == [F.face_of(natmap, faces, p, n, blocks) for p, n in probe])
    ok("a Swede gets a nord face, a Nigerian an afr face (the DLL's pick)",
       all(faces[D.fl26_regen_face_pick(p, 237)][0] == F.GROUPS.index("nord") and
           faces[D.fl26_regen_face_pick(p, 80)][0] == F.GROUPS.index("afr") for p in range(500000, 500300)))
    spread = collections.Counter(D.fl26_regen_face_pick(p, 208) for p in range(400000, 420000))
    ok("20,000 French players spread over the seu faces (%d used, most %d times)" % (
       len(spread), max(spread.values())), len(spread) >= 0.9 * F.ALLOC["seu"] and max(spread.values()) <= 20)
    ok("a player neither regen nor new: no portrait asked (-1)", D.fl26_regen_face(123456) == -1)
    # an old career: the 20,000-face pack, then the 32,000 one. A face of block 0 stays for n0 of
    # n players of a group (the 20,000 pack's count of it of the 32,000 pack's), the others get
    # one of block 2; a group that did not grow keeps every face
    nat_of = {"nweu": None, "seu": 208, "eeu": 200, "afr": 80, "mena": None, "lat": None, "bra": 146,
              "eas": 13, "sas": 9, "nord": 237, "sea": 10}
    for g in F.GROUPS:
        if nat_of[g] is None:
            nat_of[g] = next(n for n in range(512) if natmap[n] == F.GROUPS.index(g))
    ok("one nationality of each group", all(natmap[nat_of[g]] == F.GROUPS.index(g) for g in F.GROUPS))
    ids = list(range(700000, 720000))
    load(F.pack(natmap, faces[:n1]))
    was = {g: [D.fl26_regen_face_pick(p, nat_of[g]) for p in ids] for g in F.GROUPS}
    load(data)
    now = {g: [D.fl26_regen_face_pick(p, nat_of[g]) for p in ids] for g in F.GROUPS}
    kept = {g: share(list(zip(was[g], now[g])), lambda t: t[0] == t[1]) for g in F.GROUPS}
    want = {g: F.BLOCKS[0][g] / F.ALLOC[g] for g in F.GROUPS}
    print("   the same face as with the 20,000 pack (want): " + ", ".join(
        "%s %.1f%% (%.0f%%)" % (g, 100 * kept[g], 100 * want[g]) for g in F.GROUPS))
    ok("each group: the share n0/n of its players keeps his face (within 1.5 points), all of seu, bra, eas",
       all(abs(kept[g] - want[g]) <= 0.015 for g in F.GROUPS) and all(kept[g] == 1 for g in ("seu", "bra", "eas")))
    ok("a player who does not keep his face gets one of block 2",
       all(blocks[b] == 1 for g in F.GROUPS for a, b in zip(was[g], now[g]) if a != b))
    use = collections.Counter(f for g in ("afr", "eeu") for f in now[g])
    ok("afr and eeu: the old faces and the new ones worn alike (a face %.1f vs %.1f players)" % (
       sum(use[f] for f in use if blocks[f] == 0) / max(1, sum(1 for f in use if blocks[f] == 0)),
       sum(use[f] for f in use if blocks[f] == 1) / max(1, sum(1 for f in use if blocks[f] == 1))),
       0.8 < (sum(1 for g in ("afr", "eeu") for f in now[g] if blocks[f] == 0) /
              sum(F.BLOCKS[0][g] for g in ("afr", "eeu"))) /
             (sum(1 for g in ("afr", "eeu") for f in now[g] if blocks[f] == 1) /
              sum(F.BLOCKS[1][g] for g in ("afr", "eeu"))) < 1.25)
    full = faces + faces[:F.MAX_FACES - len(faces)]
    fblk = blocks + blocks[:F.MAX_FACES - len(faces)]
    load(F.pack(natmap, full, blocks=fblk))
    ok("a version 2 pack of exactly 32,767 faces loads",
       D.fl26_regen_face_pick(5, 237) == F.face_of(natmap, full, 5, 237, fblk) >= 0)

    # a pack of block 0 alone picks as the DLL before the blocks (fl26regen.c of 11b138c)
    try:
        src = subprocess.run(["git", "-C", HERE, "show", "11b138c:tools/native/fl26regen.c"], check=True,
                             capture_output=True).stdout
    except (OSError, subprocess.CalledProcessError):
        src = None
    if src:
        open(os.path.join(T, "old.c"), "wb").write(src)
        cc(os.path.join(T, "old.c"), os.path.join(T, "old.dll"))
        O = ctypes.CDLL(os.path.join(T, "old.dll"))
        O.fl26_regen_faces_load.argtypes = [ctypes.c_char_p]
        O.fl26_regen_face_pick.argtypes = [ctypes.c_uint32, ctypes.c_uint]
        old90 = [(i // 9, i, pool[i * 37][1]) for i in range(90)]
        for name, blob in (("block 1 of the pool alone (%d)" % n1, F.pack(natmap, [(g, F.NO_PORTRAIT, b) for g, b in pool20])),
                           ("the %d faces all in block 0" % len(faces), F.pack(natmap, faces)),
                           ("a version 1 pack of 90", F.pack(natmap, old90, F.MAGIC1))):
            p = os.path.join(T, "same.bin")
            open(p, "wb").write(blob)
            D.fl26_regen_faces_load(p.encode("mbcs"))
            O.fl26_regen_faces_load(p.encode("mbcs"))
            ok("%s: the same face for each of %d players as the DLL before the blocks" % (name, len(probe) + len(ids)),
               all(D.fl26_regen_face_pick(i, n) == O.fl26_regen_face_pick(i, n)
                   for i, n in probe + [(i, 80) for i in ids]))
        del O
    else:
        print("test_face_pool: no git -- the old DLL's picks not compared")

    # a version 1 pack of the old shape: 10 groups of 9 faces with portraits 0..89
    old = [(i // 9, i, pool[i * 37][1]) for i in range(90)]
    load(F.pack(natmap, old, F.MAGIC1))
    got = [D.fl26_regen_face_pick(p, n) for p, n in probe]
    ok("a version 1 pack: the same face for each player as before the group index",
       got == [old_face_of(natmap, old, p, n) for p, n in probe])
    load(F.pack(natmap, [(0, 0, pool[0][1])] * 4096, F.MAGIC1))
    ok("a version 1 pack of 4,096 faces is refused, as before", D.fl26_regen_face_pick(5, 237) == -1)
    big = F.MAGIC2 + bytes(natmap) + struct.pack("<I", 32768) + bytes(60) * 32768
    load(big)
    ok("a version 2 pack past 32,767 faces is refused", D.fl26_regen_face_pick(5, 237) == -1)
    load(data[:-60])
    ok("a version 2 pack cut short is refused", D.fl26_regen_face_pick(5, 237) == -1)
    load(data)
    ok("loaded again after a refusal: the pool is back",
       D.fl26_regen_face_pick(5, 237) == F.face_of(natmap, faces, 5, 237, blocks))

    new_players(D, natmap, old, load)
    del D
    shutil.rmtree(T, ignore_errors=True)
    print("test_face_pool: ok (%d)" % N)


if __name__ == "__main__":
    main()
