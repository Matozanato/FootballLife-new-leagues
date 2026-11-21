r"""python tools/test_face_regions.py -- the face pool reaches the package, with the 17.11. regions.

17.11.2026: every release candidate (beta4n/o/p, the 0.3.0 ones) shipped the 30.09. pack of 103
game faces ("FL26RF01", 6,704 bytes): lbpack.py took fl26regen_faces.bin from
fl26-modding-research/out/regenfaces, and the face pool (facepool.py, "FL26RF02") never got there.
mato: ship the pool before the release, with "obvious region errors + a new region".

  - lbpack.face_pack builds the pool into the package: "FL26RF02", 32,760 faces, md5 POOL_MD5;
    a $FL26_REGEN_FACES with the old pack, a pool of fewer than 20,000 faces, a portrait number
    without its .dds (facemini.py share, 18.11.), a pool with the
    old map or other faces stops the build; the pool with portrait numbers (facemini.py pack) goes
  - mszip.check_pack stops a package with the old pack or a small pool
  - the map: Pakistan with India on sas, South-East Asia and Polynesia on sea, Melanesia on afr,
    Kazakhstan on eas, Uzbekistan on mena, Belize on lat
  - the groups that kept their nations keep their faces byte for byte (the 20,000 and the 32,000
    pool), so an English or a Brazilian player has the face he had with the 32,000 pool
  - a Pakistani and an Indian player get a sas face, an Indonesian, a Thai and a Samoan a sea
    face, a Kazakh an eas face, a Fijian an afr face -- in facepool.face_of and in fl26regen.dll
"""
import ctypes, glob, hashlib, os, shutil, struct, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import facepool as F
import lbpack
import mszip
import test_face_pool as TP

N = 0
# the 07.11. pool of 32,000 (facepool.py of f5ddac9) where a worktree of it is beside this one
OLD32 = [os.path.join(os.path.dirname(os.path.dirname(HERE)), "faces30k", "out", "facepool", "fl26regen_faces.bin")]
OLD32_MD5 = "59181dc508041076eb4cf069da603091"


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def refused(fn):
    try:
        fn()
    except SystemExit as e:
        return str(e)
    return ""


def main():
    st = F.load_stats()
    want = F.pool_pack(st)
    ver, natmap, faces = F.read_pack(want)
    blocks = F.read_blocks(want)
    G = {g: i for i, g in enumerate(F.GROUPS)}

    # ---- the package ----
    T = tempfile.mkdtemp(prefix="faceregions-")
    keep, repo = lbpack.FACES, mszip.REPO
    try:
        out = os.path.join(T, "pack")
        os.makedirs(os.path.join(out, "modules"))
        lbpack.FACES = None
        logs = []
        n = lbpack.face_pack(out, logs.append)
        shipped = open(os.path.join(out, "modules", "fl26regen_faces.bin"), "rb").read()
        ok("the package's face pack is the pool: FL26RF02, %d faces, md5 %s" % (n, hashlib.md5(shipped).hexdigest()[:8]),
           shipped[:8] == b"FL26RF02" and n == 32760 == len(faces) and shipped == want
           and hashlib.md5(shipped).hexdigest() == F.POOL_MD5 and F.pool_problems(shipped) == [])
        ok("with its livecpk root FL26 Regen Faces, and the log says so (%s)" % logs[-1][:60],
           os.path.isdir(os.path.join(out, "livecpk", "FL26 Regen Faces")) and "32760 faces" in logs[-1])

        def src(name, data):
            d = os.path.join(T, name)
            os.makedirs(os.path.join(d, "FL26 Regen Faces"), exist_ok=True)
            open(os.path.join(d, "fl26regen_faces.bin"), "wb").write(data)
            return d

        def pack_from(d):
            shutil.rmtree(out, ignore_errors=True)
            os.makedirs(os.path.join(out, "modules"))
            lbpack.FACES = d
            return refused(lambda: lbpack.face_pack(out, lambda *a: None))

        old90 = F.pack(natmap[:], [(i % 10, i, faces[i * 300][2]) for i in range(103)], F.MAGIC1)
        ok("FL26_REGEN_FACES with the 30.09. pack of 103 game faces stops the build",
           "30.09." in pack_from(src("rf01", old90)))
        small = F.pack(natmap, faces[:20000 - 1], blocks=blocks[:20000 - 1])
        ok("... and so does a pool of fewer than 20,000 faces", "at least 20000" in pack_from(src("small", small)))
        oldmap = bytearray(natmap)
        oldmap[27], oldmap[10] = G["mena"], G["sas"]
        ok("... a pool with the old map (Pakistan on mena, Indonesia on sas)",
           "map is not the pool's" in pack_from(src("oldmap", F.pack(oldmap, faces, blocks=blocks))))
        other = list(faces)
        other[5] = (other[5][0], other[5][1], other[6][2])
        ok("... a pool with another face", "not the pool's" in pack_from(src("other", F.pack(natmap, other, blocks=blocks))))
        # mato 18.11.: ~100 pictures shared by the whole pool (facemini.py share): many faces, one
        # number, and every number needs its regen\<number>.dds
        import facemini
        from PIL import Image
        dds = facemini.dds_bytes(Image.new("RGBA", (128, 128), (120, 90, 70, 255)))
        shared = [(g, (0, 7, 14)[i % 3] if i % 4 else F.NO_PORTRAIT, b) for i, (g, _k, b) in enumerate(faces)]
        d = src("shots", F.pack(natmap, shared, blocks=blocks))
        regen = os.path.join(d, "FL26 Regen Faces", "common", "render", "symbol", "player", "regen")
        os.makedirs(regen)
        for k in (0, 7, 14):
            open(os.path.join(regen, "%d.dds" % k), "wb").write(dds)
        ok("the pool with shared portrait numbers (facemini.py share) and their .dds goes", pack_from(d) == "")
        ok("... and ships the pictures", sorted(os.listdir(os.path.join(out, "livecpk", "FL26 Regen Faces", "common",
                                                                       "render", "symbol", "player", "regen"))) == ["0.dds", "14.dds", "7.dds"])
        os.remove(os.path.join(regen, "14.dds"))
        ok("... a portrait number without its .dds stops the build", "no .dds (14)" in pack_from(d))
        open(os.path.join(regen, "14.dds"), "wb").write(dds[:84] + b"DXT1" + dds[88:])
        ok("... and so does a .dds that is not 128 x 128 DXT5", "not a 128 x 128 DXT5" in pack_from(d))

        # mszip's check of the package (a repository of the test's own: no patch sets to compare)
        mszip.REPO = os.path.join(T, "repo")
        os.makedirs(os.path.join(mszip.REPO, "sider"))
        pk = os.path.join(T, "mspack")
        os.makedirs(os.path.join(pk, "modules"))
        os.makedirs(os.path.join(pk, "livecpk", "FL26 Regen Faces"))
        open(os.path.join(pk, "modules", "fl26regen_faces.bin"), "wb").write(old90)
        bad = [b for b in mszip.check_pack(pk) if "fl26regen_faces" in b]
        ok("mszip.check_pack stops a package with the 30.09. pack (%s)" % (bad[:1] or "-"), bad)
        open(os.path.join(pk, "modules", "fl26regen_faces.bin"), "wb").write(small)
        ok("... and one with a small pool", any("fl26regen_faces" in b for b in mszip.check_pack(pk)))
        open(os.path.join(pk, "modules", "fl26regen_faces.bin"), "wb").write(want)
        ok("... and lets the pool through", not any("fl26regen_faces" in b for b in mszip.check_pack(pk)))
        open(os.path.join(pk, "modules", "fl26regen_faces.bin"), "wb").write(F.pack(natmap, shared, blocks=blocks))
        ok("... stops shared portrait numbers without their .dds",
           any("no .dds" in b for b in mszip.check_pack(pk)))
        mregen = os.path.join(pk, "livecpk", "FL26 Regen Faces", "common", "render", "symbol", "player", "regen")
        os.makedirs(mregen)
        for k in (0, 7, 14):
            open(os.path.join(mregen, "%d.dds" % k), "wb").write(dds)
        ok("... and lets them through with the pictures", not any("fl26regen_faces" in b for b in mszip.check_pack(pk)))
    finally:
        lbpack.FACES, mszip.REPO = keep, repo

    # ---- the map ----
    grp = lambda n: F.GROUPS[natmap[n]]
    ok("Pakistan and India on sas, Indonesia, Thailand, Vietnam, Samoa, Tonga on sea",
       [grp(n) for n in (27, 9, 10, 36, 38, 168, 171)] == ["sas", "sas", "sea", "sea", "sea", "sea", "sea"])
    ok("Kazakhstan and Kyrgyzstan on eas, Uzbekistan, Tajikistan, Turkmenistan on mena",
       [grp(n) for n in (216, 40, 240, 41, 42)] == ["eas", "eas", "mena", "mena", "mena"])
    ok("Fiji, Vanuatu, Solomon Islands, New Caledonia, Papua New Guinea on afr, Belize on lat",
       [grp(n) for n in (164, 172, 169, 165, 167, 108)] == ["afr"] * 5 + ["lat"])
    ok("England nweu, Brazil bra, Australia nweu, Japan eas, Afghanistan mena (unchanged)",
       [grp(n) for n in (204, 146, 162, 13, 1)] == ["nweu", "bra", "nweu", "eas", "mena"])

    # ---- the kept groups ----
    kept = [g for g in F.GROUPS if g not in F.REDRAWN]
    pool = [(g, b) for g, _k, b in faces]
    m32 = TP.group_md5(pool, blocks)
    ok("every kept group's faces are the 32,000 pool's, byte for byte, the same blocks",
       all(m32[g] == TP.KEPT32_MD5[g] for g in kept))
    have = [p for p in OLD32 if os.path.isfile(p) and hashlib.md5(open(p, "rb").read()).hexdigest() == OLD32_MD5]
    probe = [(pid, nat) for pid in range(240000, 262144, 37) for nat in (204, 146, 80, 237, 200, 208, 13, 124, 76)]
    if have:
        od = open(have[0], "rb").read()
        _v, onat, ofaces = F.read_pack(od)
        oblk = F.read_blocks(od)
        ok("with the 07.11. pack beside (%d players of England, Brazil, Nigeria, Sweden, Croatia, France, Japan, "
           "Mexico, Morocco): every one the same face bytes" % len(probe),
           all(ofaces[F.face_of(onat, ofaces, p, n, oblk)][2] == faces[F.face_of(natmap, faces, p, n, blocks)][2]
               for p, n in probe))
    else:
        print("test_face_regions: the 07.11. pack is not beside this worktree -- the per-player comparison skipped")
    old20 = F.make_pool(st, blocks=F.BLOCKS[:1])
    m20 = TP.group_md5(old20)
    ok("and the 20,000 pool's (block 1), byte for byte", all(m20[g] == TP.KEPT20_MD5[g] for g in kept))

    # ---- the picks ----
    ids = range(250000, 251000)
    pick = lambda nat: {F.GROUPS[faces[F.face_of(natmap, faces, p, nat, blocks)][0]] for p in ids}
    ok("1,000 Pakistani and Indian players: all sas faces", pick(27) == {"sas"} and pick(9) == {"sas"})
    ok("Indonesian, Thai, Samoan players: all sea faces", pick(10) == pick(36) == pick(168) == {"sea"})
    ok("Kazakh players eas faces, Fijian afr, Uzbek mena", pick(216) == {"eas"} and pick(164) == {"afr"}
       and pick(240) == {"mena"})
    spread = {F.face_of(natmap, faces, p, 10, blocks) for p in range(300000, 310000)}
    ok("10,000 Indonesian players spread over the sea faces (%d of %d)" % (len(spread), F.ALLOC["sea"]),
       len(spread) >= 0.95 * F.ALLOC["sea"])

    # ---- the DLL ----
    zig = TP.find_zig()
    if not zig:
        print("test_face_regions: no zig -- the DLL half skipped")
    else:
        dll = os.path.join(T, "fl26regen.dll")
        subprocess.run([zig, "cc", "-shared", "-target", "x86_64-windows-gnu", "-O2", "-s", "-DFL26REGEN_TEST", "-o",
                        dll, os.path.join(HERE, "native", "fl26regen.c"), "-lkernel32"], check=True, capture_output=True)
        D = ctypes.CDLL(dll)
        D.fl26_regen_faces_load.argtypes = [ctypes.c_char_p]
        D.fl26_regen_face_pick.argtypes = [ctypes.c_uint32, ctypes.c_uint]
        p = os.path.join(T, "pool.bin")
        open(p, "wb").write(want)
        D.fl26_regen_faces_load(p.encode("mbcs"))
        nats = (27, 9, 10, 36, 168, 216, 164, 240, 204, 146, 108, 260)
        got = [(i, n, D.fl26_regen_face_pick(i, n)) for i in range(260000, 262144, 3) for n in nats]
        ok("fl26regen.dll on the 32,760-face pool (11 groups) picks what face_of picks (%d players)" % len(got),
           all(f == F.face_of(natmap, faces, i, n, blocks) for i, n, f in got))
        ok("... a Pakistani a sas face, an Indonesian a sea face, a Fijian an afr face",
           all(faces[f][0] == G[{27: "sas", 10: "sea", 164: "afr"}[n]] for i, n, f in got if n in (27, 10, 164)))
        del D
    shutil.rmtree(T, ignore_errors=True)
    print("test_face_regions: ok (%d)" % N)


if __name__ == "__main__":
    main()
