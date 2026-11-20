r"""python tools/test_facemini.py -- the face pool's small pictures (mato 06.11.: "male slike moramo
popraviti"): fl26regen's capture mode draws one player with pool face k on Edit's player screen,
and tools/facemini.py makes the game's portrait of that face from a screenshot.

The picture, on a screenshot made here (the red menu's colours as the game draws them: black with
no green or blue, red grid lines, the red glow, the grey panel's red edge; a head with black hair
and a darker patch inside it, a green shirt): 128 x 128 with the header of the game's own
portraits, DXT5, 16,512 bytes; transparent around the player and over the grid; the face and
the black hair opaque; no red at the edge; the shirt grey (or green with --shirt keep); a shot
without a player and the same picture twice in a row are told.

The pack step: the pool with portrait number k for every face that has a picture, 0xffff for the
others, everything else as it was; a picture of a face the pool does not have is refused.

The capture file (fl26regen.c, built here with -DFL26REGEN_TEST when zig is found): what each
line means, what is refused, the last line wins; the appearance lookups answer for that player
(and only him) with pool face k, count the lookups, and stop at "off" or a face the pack lacks.
"""
import ctypes, os, random, shutil, struct, subprocess, sys, tempfile

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import facemini as M
import facepool as F
from test_face_pool import find_zig

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


SKIN = (190, 140, 115)
HAIR = (24, 19, 17)
SHIRT = (30, 140, 60)


def menu():
    """Edit's red menu as the game draws it, 1924 x 1084"""
    im = Image.new("RGB", (1924, 1084), (6, 1, 1))
    d = ImageDraw.Draw(im)
    for x in range(0, 1924, 37):
        d.line([(x, 0), (x, 1084)], fill=(150, 8, 9), width=2)
    for y in range(0, 1084, 41):
        d.line([(0, y), (1924, y)], fill=(120, 5, 6), width=1)
    d.rectangle([0, 470, 1924, 520], fill=(185, 26, 24))          # the glow
    d.rectangle([0, 0, 1457, 1084], fill=(52, 0, 0))               # the panel's edge
    return im


def player(im, dark_patch=True):
    d = ImageDraw.Draw(im)
    d.polygon([(1490, 1084), (1520, 520), (1610, 480), (1720, 480), (1810, 520), (1850, 1084)], fill=SHIRT)
    d.rectangle([1620, 400, 1710, 500], fill=SKIN)                 # neck
    d.ellipse([1560, 180, 1770, 460], fill=SKIN)                   # head, chin at 460
    d.chord([1555, 150, 1775, 330], 180, 360, fill=HAIR)           # black hair on top
    if dark_patch:
        d.ellipse([1640, 175, 1690, 215], fill=(5, 3, 3))          # hair as dark as the menu, inside
    d.ellipse([1610, 300, 1640, 315], fill=(40, 25, 22))           # eyes
    d.ellipse([1690, 300, 1720, 315], fill=(40, 25, 22))
    return im


def at(box, x, y):
    """screenshot pixel -> picture pixel"""
    bx, by, side = box
    return int((x - bx) * M.SIZE / side), int((y - by) * M.SIZE / side)


def picture_tests():
    shot = player(menu())
    im, notes = M.portrait(shot)
    a = np.asarray(im).astype(int)
    ok("the picture is 128 x 128 RGBA", im.size == (128, 128) and im.mode == "RGBA")
    ok("nothing to look at again on a good shot (%s)" % notes, "bad" not in notes)
    ok("transparent in the corners and over the grid above the head",
       a[0, 0, 3] == 0 and a[0, 127, 3] == 0 and a[at(M.BOX, 1480, 130)[::-1]][3] == 0 and
       a[at(M.BOX, 1850, 200)[::-1]][3] == 0)
    fx, fy = at(M.BOX, 1665, 360)
    ok("the face opaque, in its own colour", a[fy, fx, 3] == 255 and np.abs(a[fy, fx, :3] - SKIN).max() <= 12)
    hx, hy = at(M.BOX, 1665, 195)
    ok("the black hair opaque, the patch as dark as the menu too", a[hy, hx, 3] == 255 and
       a[at(M.BOX, 1600, 200)[::-1]][3] == 255)
    edge = a[(a[..., 3] > 20) & (a[..., 3] < 235)]
    ok("no red at the edge (%d edge pixels)" % len(edge), len(edge) > 50 and
       not ((edge[:, 0] > 40) & (edge[:, 1] < 0.45 * edge[:, 0])).any())
    sx, sy = at(M.BOX, 1765, 508)                                  # the shirt beside the neck
    sh = a[sy, sx]
    ok("the shirt below the chin is grey and opaque to the edge (%s)" % sh, sh[3] >= 250 and abs(sh[0] - sh[1]) <= 6 and abs(sh[1] - sh[2]) <= 6)
    keep = np.asarray(M.portrait(shot, shirt="keep")[0]).astype(int)[sy, sx]
    ok("--shirt keep: the shirt stays green", keep[1] > keep[0] + 60)
    ok("the neck stays skin with a grey shirt", np.abs(a[at(M.BOX, 1665, 470)[::-1]][:3] - SKIN).max() <= 15)

    data = M.dds_bytes(im)
    ok("the .dds: 16,512 bytes, the game's header, 128 x 128 DXT5 one mip",
       len(data) == 16512 and data[:128] == M.game_header() and M.check_dds(data) == (128, 128, b"DXT5", 1))
    import io
    back = np.asarray(Image.open(io.BytesIO(data)).convert("RGBA")).astype(int)
    ok("the .dds reads back: corners clear, face opaque", back[0, 0, 3] == 0 and back[fy, fx, 3] > 240)

    _im, n2 = M.portrait(menu())
    ok("a shot without a player is told (%s)" % n2.get("bad"), "bad" in n2)
    return shot


def convert_and_pack(shot):
    T = tempfile.mkdtemp(prefix="facemini-")
    src, out = os.path.join(T, "shots"), os.path.join(T, "out")
    os.makedirs(src)
    shot.save(os.path.join(src, "mini_3.png"))
    shot.save(os.path.join(src, "mini_4.png"))                     # the head not drawn again
    player(menu(), dark_patch=False).save(os.path.join(src, "mini_12.png"))
    menu().save(os.path.join(src, "mini_7.png"))
    Image.new("RGB", (10, 10)).save(os.path.join(src, "other.png"))
    done, bad = M.convert(src, out, log=lambda *_: None)
    ok("convert: one picture for each mini_<k>.png, in face order", [k for k, _ in done] == [3, 4, 7, 12])
    d = os.path.join(out, M.REGEN_DIR)
    ok("convert: <k>.dds under FL26 Regen Faces\\common\\render\\symbol\\player\\regen",
       sorted(os.listdir(d)) == ["12.dds", "3.dds", "4.dds", "7.dds"])
    ok("convert: the same picture twice and the empty shot are told, the good ones not",
       sorted(k for k, _ in bad) == [4, 7] and not any(l.startswith(("face 3:", "face 12:")) for l in open(os.path.join(out, "report.txt"))))
    os.remove(os.path.join(d, "7.dds"))

    rng = random.Random(3)
    natmap = bytearray([0xFF] * 512)
    natmap[237] = 9
    faces = [(rng.randrange(10), F.NO_PORTRAIT, bytes(rng.randrange(256) for _ in range(56))) for _ in range(20)]
    pool = os.path.join(T, "pool.bin")
    blocks = [0] * 14 + [1] * 6
    open(pool, "wb").write(F.pack(natmap, faces, blocks=blocks))
    path, n = M.pack(pool, out, log=lambda *_: None)
    ver, nm, got = F.read_pack(open(path, "rb").read())
    ok("pack: each face keeps its block (the second byte)", F.read_blocks(open(path, "rb").read()) == blocks)
    ok("pack: faces 3, 4, 12 get their portrait number, the others none (%d)" % n,
       n == 3 and [k for _g, k, _b in got] == [k if k in (3, 4, 12) else 0xFFFF for k in range(20)])
    ok("pack: groups, faces and the nationality map as they were, version 2",
       ver == 2 and nm == natmap and [(g, b) for g, _k, b in got] == [(g, b) for g, _k, b in faces])
    shutil.copy(os.path.join(d, "3.dds"), os.path.join(d, "20.dds"))
    try:
        M.pack(pool, out, log=lambda *_: None)
        refused = False
    except SystemExit:
        refused = True
    ok("pack: a picture of face 20 of a 20-face pool is refused", refused)
    os.remove(os.path.join(d, "20.dds"))
    share_tests(pool, out, d)
    shutil.rmtree(T, ignore_errors=True)
    return natmap, faces


def share_tests(pool, out, d):
    """mato 18.11.: ~100 pictures for now, every face shows the nearest captured one"""
    raw = open(pool, "rb").read()
    path, n, total = M.share(out, pool, log=lambda *_: None)
    data = open(path, "rb").read()
    _v, nm, got = F.read_pack(data)
    _v, _nm, faces = F.read_pack(raw)
    ks = [k for _g, k, _b in got]
    mine = lambda k: any(faces[c][0] == faces[k][0] for c in (3, 4, 12))      # its group has a picture
    ok("share: every face of a group with a picture gets one of the pictures 3, 4, 12 (%d pictures, %d faces)" % (n, total),
       n == 3 and total == 20 and set(ks) <= {3, 4, 12, F.NO_PORTRAIT} and all(ks[k] != F.NO_PORTRAIT for k in range(20) if mine(k)))
    L = M.looks(faces)
    cross = [k for k in range(20) if not mine(k)]
    ok("share: a face of a group with no picture gets another group's only if it looks close (%d such faces)" % len(cross),
       all((ks[k] == F.NO_PORTRAIT) == (min(float(M.distance(L, k, np.array([c]))[0]) for c in (3, 4, 12))
                                         > M.OTHER_GROUP + M.CROSS_MAX) for k in cross))
    ok("share: a captured face keeps its own picture", all(ks[k] == k for k in (3, 4, 12)))
    ok("share: groups, blocks, faces and the map as they were",
       [(g, b) for g, _k, b in got] == [(g, b) for g, _k, b in faces] and F.read_blocks(data) == F.read_blocks(raw))
    ok("share: every portrait number has its 128 x 128 DXT5 .dds", M.check_shared(data, os.path.join(out, M.FACE_ROOT)) == [])
    rows = open(os.path.join(out, "share.tsv"), encoding="utf-8").read().split("\n")
    ok("share: share.tsv one line a face", rows[0].startswith("face\t") and len([r for r in rows[1:] if r]) == 20)
    for k in range(20):
        if k in (3, 4, 12) or ks[k] == F.NO_PORTRAIT:
            continue
        best = min((float(M.distance(L, k, np.array([c]))[0]), c) for c in (3, 4, 12))
        if ks[k] != best[1]:
            ok("share: face %d shows the nearest picture (%d, not %d)" % (k, best[1], ks[k]), False)
            break
    else:
        ok("share: every other face shows the nearest captured face", True)
    same = [k for k in range(20) if faces[k][0] == faces[3][0]]
    ok("share: a face of a group with a picture never shows another group's",
       all(faces[ks[k]][0] == faces[k][0] for k in range(20) if mine(k)) and same)
    os.remove(os.path.join(d, "12.dds"))
    k12 = M.share(out, pool, log=lambda *_: None)[1]
    ok("share: rerun after the pictures changed maps on what is there", k12 == 2 and
       set(k for _g, k, _b in F.read_pack(open(path, "rb").read())[2]) <= {3, 4, F.NO_PORTRAIT})


def share_pool_tests():
    """the real pool: rank's order and share over 32,760 faces"""
    raw = F.pool_pack()
    _v, natmap, faces = F.read_pack(raw)
    order = M.rank(faces, 60, log=lambda *_: None)
    ks = [k for k, _g in order]
    groups = set(faces[k][0] for k in ks[:len(F.GROUPS)])
    ok("rank: the first %d picks are one of every group" % len(F.GROUPS), groups == set(range(len(F.GROUPS))))
    ok("rank: 60 different faces, gain falling within each group", len(set(ks)) == 60 and all(
        a[1] >= b[1] - 1e-3 for g in range(len(F.GROUPS))
        for a, b in zip([o for o in order if faces[o[0]][0] == g], [o for o in order if faces[o[0]][0] == g][1:])))
    T = tempfile.mkdtemp(prefix="facemini-share-")
    d = os.path.join(T, M.REGEN_DIR)
    os.makedirs(d)
    dds = M.dds_bytes(Image.new("RGBA", (M.SIZE, M.SIZE), (120, 90, 70, 255)))
    for k in ks:
        open(os.path.join(d, "%d.dds" % k), "wb").write(dds)
    path, n, total = M.share(T, log=lambda *_: None)
    data = open(path, "rb").read()
    got = F.read_pack(data)[2]
    nums = [k for _g, k, _b in got]
    ok("share on the pool: all %d faces get a picture of the %d" % (total, n),
       total == len(faces) == 32760 and set(nums) <= set(ks) and F.NO_PORTRAIT not in nums)
    ok("share on the pool: the captured faces keep their own", all(nums[k] == k for k in ks))
    ok("share on the pool: every face shows a face of its own group",
       all(faces[nums[k]][0] == faces[k][0] for k in range(len(faces))))
    ok("share on the pool: the pack is the pool (facepool.pool_problems) and every number has its .dds",
       F.pool_problems(data) == [] and M.check_shared(data, os.path.join(T, M.FACE_ROOT)) == [])
    shutil.rmtree(T, ignore_errors=True)


def capture_tests(natmap, faces):
    zig = find_zig()
    if not zig:
        print("test_facemini: no zig -- the DLL half skipped")
        return
    T = tempfile.mkdtemp(prefix="facemini-dll-")
    dll = os.path.join(T, "fl26regen.dll")
    subprocess.run([zig, "cc", "-shared", "-target", "x86_64-windows-gnu", "-O2", "-s", "-DFL26REGEN_TEST", "-o", dll,
                    os.path.join(HERE, "native", "fl26regen.c"), "-lkernel32"], check=True, capture_output=True)
    D = ctypes.CDLL(dll)
    D.fl26_regen_test_cap_parse.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_uint32)]
    D.fl26_regen_test_cap_apply.argtypes = [ctypes.c_char_p]
    D.fl26_regen_test_cap_find.argtypes = [ctypes.c_uint64]
    D.fl26_regen_test_cap_find.restype = ctypes.c_void_p
    D.fl26_regen_test_cap_served.restype = ctypes.c_long
    D.fl26_regen_faces_load.argtypes = [ctypes.c_char_p]

    def parse(text):
        o = (ctypes.c_uint32 * 4)()
        got = D.fl26_regen_test_cap_parse(text.encode(), o)
        return got, tuple(o[i] if i != 1 else ctypes.c_int32(o[1]).value for i in range(4))

    ok("capture: 'player 241915 face 17'", parse("player 241915 face 17\n") == (1, (241915, 17, 0, 0)))
    ok("capture: capitals, tabs, CRLF and a comment", parse("  PLAYER\t5  Face 0  # the pilot\r\n") == (1, (5, 0, 0, 0)))
    for bad in ("player 0 face 3", "player 1048576 face 1", "player 12 face 32768", "player -1 face 2",
                "player 12 face 2 extra", "player 12a face 2", "player 12 face", "face 3", "player 12 faces 2",
                "faces 9-3", "faces 1-5000", "faces 0-3", "faces x", ""):
        ok("capture: %r means nothing" % bad, parse(bad)[0] == 0)
    ok("capture: 'faces 241915-241944'", parse("faces 241915-241944") == (2, (0, -1, 241915, 241944)))
    ok("capture: 'faces 7' is 7-7", parse("faces 7") == (2, (0, -1, 7, 7)))
    ok("capture: the last player line wins", parse("player 3 face 4\nplayer 9 face 1\n") == (1, (9, 1, 0, 0)))
    ok("capture: 'off' after a player: nobody", parse("player 3 face 4\noff\n")[0] == 0)
    ok("capture: a player after 'off'", parse("off\nplayer 3 face 4")[0] == 1)
    ok("capture: a player and a range together", parse("faces 10-20\nplayer 3 face 4\n") == (3, (3, 4, 10, 20)))

    p = os.path.join(T, "pack.bin")
    open(p, "wb").write(F.pack(natmap, faces))
    D.fl26_regen_faces_load(p.encode("mbcs"))
    pid = 241915
    key = lambda i, hi=0: ((i | hi) << 32) | 0x1234
    ok("capture: no lookup answered before a player is set", not D.fl26_regen_test_cap_find(key(pid)))
    ok("capture: player %d wears face 7" % pid, D.fl26_regen_test_cap_apply(b"player 241915 face 7\n") == 1)
    r = D.fl26_regen_test_cap_find(key(pid))
    rec = ctypes.string_at(r, 72) if r else b""
    ok("capture: the lookup answers with his id and face 7's 56 bytes in the table's record shape",
       len(rec) == 72 and struct.unpack_from("<I", rec)[0] == pid and rec[4:12] == bytes(8) and
       rec[12:68] == faces[7][2] and rec[68:] == bytes(4))
    ok("capture: the id's high bits in the key (0xf00fffff) are the game's flags, not the id",
       D.fl26_regen_test_cap_find(key(pid, 0x00500000)) and not D.fl26_regen_test_cap_find(key(pid + 1)))
    ok("capture: the lookups are counted (2)", D.fl26_regen_test_cap_served() == 2)
    D.fl26_regen_test_cap_apply(b"player 241915 face 8\n")
    r = D.fl26_regen_test_cap_find(key(pid))
    ok("capture: face 8 after face 7, the count from 0 again",
       r and ctypes.string_at(r + 12, 56) == faces[8][2] and D.fl26_regen_test_cap_served() == 1)
    ok("capture: face 20 of a 20-face pack: refused, nobody",
       D.fl26_regen_test_cap_apply(b"player 241915 face 20") == -1 and not D.fl26_regen_test_cap_find(key(pid)))
    D.fl26_regen_test_cap_apply(b"player 241915 face 1")
    ok("capture: 'off' and an empty file: nobody",
       D.fl26_regen_test_cap_apply(b"off") == 0 and not D.fl26_regen_test_cap_find(key(pid)) and
       D.fl26_regen_test_cap_apply(b"") == 0)

    # the thread that reads the file (no game here: the database is not found, 0 players listed)
    import time
    txt, ack = os.path.join(T, "fl26regen_capture.txt"), os.path.join(T, "fl26regen_capture.ack")
    open(txt, "w").write("player 241915 face 5\nfaces 241915-241944\n")
    D.fl26_regen_capture_watch.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    ok("capture: the thread starts once", D.fl26_regen_capture_watch(txt.encode("mbcs"), ack.encode("mbcs")) == 1 and
       D.fl26_regen_capture_watch(txt.encode("mbcs"), ack.encode("mbcs")) == 1)

    def answer(want, secs=3.0):
        t = time.time()
        while time.time() - t < secs:
            try:
                a = open(ack).read()
            except OSError:
                a = ""
            if want in a:
                return a
            time.sleep(0.05)
        return a

    a = answer("player 241915 face 5 served 0")
    ok("capture: the answer file says who wears which face, and the range (%r)" % a,
       a.startswith("seq 1\n") and "faces 241915-241944: 0 player(s) in the database" in a)
    ok("capture: the DLL says who and which face to the loader",
       D.fl26_regen_capture_id() == 241915 and D.fl26_regen_capture_face() == 5)
    D.fl26_regen_test_cap_find(key(pid)); D.fl26_regen_test_cap_find(key(pid))
    ok("capture: the lookups show in the answer", "served 2" in answer("served 2"))
    open(txt + ".tmp", "w").write("player 241915 face 6\n")
    os.replace(txt + ".tmp", txt)
    a = answer("face 6")
    ok("capture: a new face in the file is in the answer within a second (%r)" % a,
       "seq 2" in a and "player 241915 face 6 served 0" in a and "faces" not in a)
    os.remove(txt)
    a = answer("off")
    ok("capture: the file deleted: nobody", "off" in a and D.fl26_regen_capture_id() == 0 and
       D.fl26_regen_capture_face() == -1)
    del D
    shutil.rmtree(T, ignore_errors=True)


def framing_tests(shot):
    """18.11. (mato: "the minifaces are still cut too high, almost level with the chin"): the
    framing measured as on the game's own portraits, the box found from the shots, the checks a
    capture run makes on every shot"""
    m = np.zeros((128, 128), bool)
    yy, xx = np.mgrid[:128, :128]
    m[((xx - 64) / 33.0) ** 2 + ((yy - 52) / 40.0) ** 2 <= 1] = True        # head rows 12-92, 67 wide
    m[88:110, 50:78] = True                                                 # neck
    m[105:, 8:120] = True                                                   # shoulders, shirt
    fr = M.frame(m)
    ok("frame: top, head width, neck, bottom row of a drawn portrait (%s)" % fr,
       fr["top"] == 12 and 66 <= fr["headw"] <= 68 and 86 <= fr["neck"] <= 96 and fr["bottomw"] == 112)
    box = M.calibrate([shot] * 3, log=lambda *_: None)
    im, notes = M.portrait(shot, box)
    f2 = M.frame(np.asarray(im)[..., 3] > 128)
    ok("calibrate: the box frames the head as the game does (%s -> %s)" % (box, f2),
       abs(f2["headw"] - M.GAME_HEADW) <= 3 and abs(f2["neck"] - M.GAME_NECK) <= 3 and "bad" not in notes)

    import io
    from PIL import PngImagePlugin
    ox, oy = 1300, 40
    info = PngImagePlugin.PngInfo()
    info.add_text(M.CROP_KEY, "%d,%d" % (ox, oy))
    b = io.BytesIO()
    shot.crop((ox, oy, 1924, 800)).save(b, "PNG", pnginfo=info)
    small = Image.open(io.BytesIO(b.getvalue()))
    same = np.abs(np.asarray(M.portrait(small)[0]).astype(int) - np.asarray(M.portrait(shot)[0]).astype(int)).max()
    ok("a shot saved cropped (its corner in %s) makes the same picture (diff %d)" % (M.CROP_KEY, same), same == 0)

    black = Image.new("RGB", (1924, 1084), (2, 2, 2))
    ok("a black screen is told", "black" in M.portrait(black)[1].get("bad", ""))
    grey = Image.new("RGB", (1924, 1084), (120, 120, 120))
    player(grey)
    ok("a head on another screen (no red menu) is told (%s)" % M.portrait(grey)[1].get("bad"),
       "menu" in M.portrait(grey)[1].get("bad", ""))
    red = player(menu())
    ImageDraw.Draw(red).rectangle([1400, 520, 1924, 1084], fill=(200, 10, 12))   # a red kit
    ok("a red kit, cut out with the menu, is told (%s)" % M.portrait(red)[1].get("bad"),
       "see-through" in M.portrait(red)[1].get("bad", ""))


def main():
    shot = picture_tests()
    framing_tests(shot)
    natmap, faces = convert_and_pack(shot)
    share_pool_tests()
    capture_tests(natmap, faces)
    print("test_facemini: ok (%d)" % N)


if __name__ == "__main__":
    main()
