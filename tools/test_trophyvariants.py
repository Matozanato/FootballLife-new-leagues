r"""python tools/test_trophyvariants.py

Trophy variants (FL 2027, mato 08.11.: every competition a trophy of its own; mktrophyvariants,
lbtrophies). Offline, on a base made here (an fpk with an fmdl naming its textures, as the
community's trophy folders have):
  the two files compile with every warning an error (the escapes of lbtrophies, 08.11.);
  .ftex written and read back (RGBA8 the same, DXT1/DXT5 near, one mip, the base's header);
  the base's colour textures found through its fmdl, the ceremony's by their _bsm name;
  the cup's metal and colours changed, the panels with the logo; a flat flag rebranded, a
  picture that is no flat colour left alone;
  write: only the textures a variant changes, in each phase folder of the base, the base untouched;
  auto: the same variant for a competition every time, whatever order, no two alike;
  Build (build_variants): FL26 makes none; FL 2027 one for each competition with no trophy and
  none of the game's module, the bases once, the last Build's taken again when nothing changed;
  the block in Entrance.lua / cinematics.lua run in Lua (lupa): a variant's own textures from its
  folder, every other file from its base, the final's folder at the final; a tournament id the
  module has a trophy for left to the module; with no variant the block is the one it was before.
With joaako1602's Carioca on the PC (or FL27_TROPHY_BASE): a variant of it as well.
"""
import json, os, shutil, struct, sys, tempfile, time, warnings

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lbtrophies as T
import mktrophyvariants as V
import test_trophies as TT

N = 0
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
# a community trophy folder to make a variant of: joaako1602's Carioca in the private folder next
# to the worktrees, or the one FL27_TROPHY_BASE names
CAR = os.environ.get("FL27_TROPHY_BASE") or next(
    (p for p in (os.path.normpath(os.path.join(HERE, *[".."] * k, "private", "incoming", "trophies_joaako1602", "x",
                                               "Carioca")) for k in (2, 3)) if os.path.isdir(p)), "")
CUP = "common/demo/prop/cup_afc_cl_hi"


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


# ---- a base made here ---------------------------------------------------------------------------

def fmdl(strings, textures, params, mats):
    """an .fmdl 2.03 with just the blocks a material's textures are read from"""
    s0, offs = bytearray(), {}
    offs[4] = len(s0)
    for name, ntex, first in mats:
        s0 += struct.pack("<HHHBBHH", name, 0, 0, ntex, 0, first, 0) + b"\0" * 4
    offs[6] = len(s0)
    for n, p in textures:
        s0 += struct.pack("<HH", n, p)
    offs[7] = len(s0)
    for n, r in params:
        s0 += struct.pack("<HH", n, r)
    data, infos = bytearray(), []
    for s in strings:
        infos.append((0, len(s), len(data)))
        data += s.encode() + b"\0"
    offs[12] = len(s0)
    for i in infos:
        s0 += struct.pack("<HHI", *i)
    counts = {4: len(mats), 6: len(textures), 7: len(params), 12: len(strings)}
    table = b"".join(struct.pack("<HHI", t, counts[t], offs[t]) for t in (4, 6, 7, 12))
    table += struct.pack("<III", 3, 0, len(data))
    info = 56
    o0 = info + len(table)
    o1 = o0 + len(s0)
    head = b"FMDL" + struct.pack("<f", 2.03) + struct.pack("<QQQIIIIII", info, 0, 0, 4, 1, o0, len(s0), o1, len(data))
    return head + table + bytes(s0) + bytes(data)


def fpk(files):
    n = len(files)
    head = bytearray(0x30 + 0x30 * n)
    head[0:6] = b"foxfpk"
    struct.pack_into("<I", head, 0x20, n)
    names, at = bytearray(), len(head)
    place = []
    for name, _b in files.items():
        place.append((at + len(names), len(name)))
        names += name.encode() + b"\0"
    body, at = bytearray(), len(head) + len(names)
    for i, (name, b) in enumerate(files.items()):
        struct.pack_into("<QQQQ", head, 0x30 + 0x30 * i, at + len(body), len(b), place[i][0], place[i][1])
        body += b
    return bytes(head) + bytes(names) + bytes(body)


def cup_picture():
    """the cup's colour texture: gold above, a red ribbon, a blue plinth with a plate on it"""
    from PIL import Image, ImageDraw
    im = Image.new("RGBA", (128, 128), (212, 170, 64, 255))
    d = ImageDraw.Draw(im)
    for y in range(64):
        d.line([(0, y), (127, y)], fill=(150 + y, 120 + y // 2, 40, 255))
    d.rectangle([0, 70, 127, 80], fill=(200, 20, 30, 255))
    d.rectangle([0, 96, 127, 127], fill=(20, 40, 160, 255))
    d.rectangle([16, 104, 48, 120], fill=(240, 240, 240, 255))       # the base competition's decal
    return im


def flag_picture():
    from PIL import Image, ImageDraw
    im = Image.new("RGBA", (128, 128), (20, 140, 60, 255))
    ImageDraw.Draw(im).rectangle([44, 44, 84, 84], fill=(250, 250, 250, 255))
    return im


def noisy_picture():
    import numpy as np
    from PIL import Image
    rng = np.random.default_rng(7)
    return Image.fromarray(rng.integers(0, 255, (128, 128, 3), dtype=np.uint8), "RGB").convert("RGBA")


def logo_png(path):
    from PIL import Image, ImageDraw
    im = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([2, 2, 61, 61], fill=(0, 150, 60, 255))
    d.ellipse([20, 20, 43, 43], fill=(250, 210, 0, 255))
    im.save(path)
    return path


def make_base(root):
    """a trophy folder with Knockout and Final, its cup model naming two textures"""
    model = fmdl(["", "mat0", V.ALBEDO, V.METALNESS, "cup_bsm.tga", "cup_mtl.tga", "/Assets/pes16/demo/prop/cup_afc_cl_hi/"],
                 [(4, 6), (5, 6)], [(2, 0), (3, 1)], [(1, 2, 0)])
    from PIL import Image
    for ph in ("Knockout", "Final"):
        top = os.path.join(root, ph, *CUP.split("/"))
        os.makedirs(os.path.join(top, "#Win"))
        os.makedirs(os.path.join(top, "#windx11"))
        open(os.path.join(top, "#Win", "cup_afc_cl_hi.fpk"), "wb").write(
            fpk({"/Assets/pes16/demo/prop/cup_afc_cl_hi/cup_afc_cl_hi.fmdl": model, "x.skl": b"skl"}))
        open(os.path.join(top, "#windx11", "cup_bsm.ftex"), "wb").write(V.ftex_bytes(cup_picture(), 0))
        open(os.path.join(top, "#windx11", "cup_mtl.ftex"), "wb").write(
            V.ftex_bytes(Image.new("RGBA", (64, 64), (200, 200, 200, 255)), 2))
    stand = os.path.join(root, "Final", "common", "demo", "fixdemoobj", "cupstand_afc_cl", "#windx11")
    os.makedirs(stand)
    open(os.path.join(stand, "stand_bsm.ftex"), "wb").write(V.ftex_bytes(flag_picture(), 4))
    open(os.path.join(stand, "crowd_bsm.ftex"), "wb").write(V.ftex_bytes(noisy_picture(), 0))
    cut = os.path.join(root, "Final", "common", "demo", "fixdemo", "ent", "cut_data")
    os.makedirs(cut)
    open(os.path.join(cut, "x.fdc"), "wb").write(b"fdc")
    json.dump({"panels": {"cup_bsm.ftex": [[0.1, 0.78, 0.42, 0.98]]}}, open(os.path.join(root, "variant.json"), "w"))
    return root


# ---- the old block (before the variants): FL26's must stay the same, byte for byte -------------

def old_block(world, index):
    base = "..\\..\\livecpk\\%s\\%s" % (world, T.FOLDER)
    rows = []
    for cid, e in sorted(index.items(), key=lambda kv: int(kv[0])):
        here = base + "\\" + cid
        match = here + ("\\" + e["match"] if e["match"] else "")
        final = here + ("\\" + e["final"] if e["final"] else "")
        for rid in e["rids"]:
            rows.append("\t\t[%d] = {%s, %s},   -- competition %s" % (rid, T.lua_str(match), T.lua_str(final), cid))
    return ["%s %s (Mod Studio writes this on Switch on; the rest of the file is not ours) ----" % (T.BEGIN, world),
            "local fl26ms_trophies",
            "local function fl26ms_trophy(ctx, filename)",
            "\tif fl26ms_trophies == nil then",
            "\t\tfl26ms_trophies = {}",
            "\t\tlocal f = io.open(fileroot .. %s, \"r\")" % T.lua_str("\\" + base + "\\" + T.INDEX),
            "\t\tif f == nil then return nil end",
            "\t\tf:close()",
            "\t\tfl26ms_trophies = {"] + rows + [
            "\t\t}",
            "\tend",
            "\tlocal t = fl26ms_trophies[tid]",
            "\tif t == nil then return nil end",
            "\tentry = 16",
            "\tif ctx.match_info == 53 then Entrance = t[2] else Entrance = t[1] end",
            "\treturn string.format(\"%s:%s\", Entrance, filename)",
            "end",
            T.END]


def ask(sider, text, tid, mi, filename):
    """(make_key, trophy_rewrite, get_filepath) of the module <text> for one file of a match"""
    L = TT.lua()
    L.globals().log = lambda *a: None
    reg = L.eval("{}")
    ctx = L.eval("{}")
    ctx["sider_dir"] = sider + "\\"
    ctx["register"] = lambda name, fn, reg=reg: reg.__setitem__(name, fn)
    L.execute(text)["init"](ctx)
    c = L.eval("{}")
    c["tournament_id"], c["match_info"], c["home_team"], c["away_team"] = tid, mi, 101, 102
    if reg["set_teams"] is not None:
        reg["set_teams"](c)
    k = reg["livecpk_make_key"](c, filename)
    p = reg["livecpk_get_filepath"](c, filename, k)
    r = reg["trophy_rewrite"](c, tid)
    return k, r, p


# ---- the tests ------------------------------------------------------------------------------------

def compiles():
    for f in ("lbtrophies.py", "mktrophyvariants.py", "test_trophies.py", "test_trophyvariants.py"):
        src = open(os.path.join(HERE, f), encoding="utf-8").read()
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            try:
                compile(src, f, "exec")
                good = True
            except SyntaxError as e:
                print("   %s: %s" % (f, e))
                good = False
        ok("%s compiles with every warning an error (no invalid escape)" % f, good)


def ftex():
    import numpy as np
    im = cup_picture()
    b = V.ftex_bytes(im, 0)
    tmp = tempfile.mkdtemp(prefix="tv-ftex-")
    try:
        p = os.path.join(tmp, "a.ftex")
        open(p, "wb").write(b)
        back = V.read_ftex(p)
        ok("ftex RGBA8: the same pixels", back.tobytes() == im.tobytes())
        fmt, w, h, mips = V.ftex_head(b)
        ok("ftex: format, size, one mip (%d %dx%d %d)" % (fmt, w, h, mips), (fmt, w, h, mips) == (0, 128, 128, 1))
        like = bytearray(V.ftex_bytes(im, 4))
        like[4:8] = bytes.fromhex("5c8f0240")          # 2.04
        for fmt in (2, 4):
            b = V.ftex_bytes(im, fmt, bytes(like))
            open(p, "wb").write(b)
            back = np.asarray(V.read_ftex(p).convert("RGB"), dtype=np.int32)
            err = float(np.abs(back - np.asarray(im.convert("RGB"), dtype=np.int32)).mean())
            ok("ftex %s: read back near (mean error %.1f), the base's version kept" % (V.FORMATS[fmt], err),
               err < 12 and b[4:8] == bytes.fromhex("5c8f0240") and V.ftex_head(b)[0] == fmt)
        ok("ftex: a format it cannot write is written as DXT5", V.ftex_head(V.ftex_bytes(im, 11))[0] == 4)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def generator(tmp):
    import numpy as np
    base = make_base(os.path.join(tmp, "base"))
    logo = logo_png(os.path.join(tmp, "logo.png"))
    t = V.textures(base)
    ok("textures: the cup's colour texture and its metalness through the fmdl (%s)" % t["cup"],
       t["cup"] == [(CUP + "/#windx11/cup_bsm.ftex", CUP + "/#windx11/cup_mtl.ftex")])
    ok("textures: the ceremony's by their _bsm name, the cut data not (%s)" % t["scene"],
       sorted(t["scene"]) == ["common/demo/fixdemoobj/cupstand_afc_cl/#windx11/crowd_bsm.ftex",
                              "common/demo/fixdemoobj/cupstand_afc_cl/#windx11/stand_bsm.ftex"])
    ok("logo colours: the logo's own (%s)" % V.logo_colours(logo), V.logo_colours(logo)[:1] == ["#00963c"])

    pic, boxes = V.recolour(cup_picture(), "silver", ["#00963c", "#fad200"], [(0.1, 0.78, 0.42, 0.98)], None)
    a = np.asarray(pic, dtype=np.int32)
    gold = a[30, 60, :3]
    ok("recolour: the gold is silver now (%s)" % list(gold), abs(int(gold[0]) - int(gold[2])) < 30)
    rib, plinth = a[75, 64, :3], a[110, 100, :3]
    ok("recolour: the ribbon and the plinth in the competition's colours (%s %s)" % (list(rib), list(plinth)),
       rib[1] > rib[0] and rib[1] > rib[2] and plinth[0] > plinth[2] and plinth[1] > plinth[2])
    ok("split: two flat colours apart, the brighter the first", V.split(__import__("numpy").array([0.2] * 30 + [0.6] * 10)) < 0.6)
    ok("recolour: the plate painted over, the base's decal gone (%s)" % (boxes,),
       len(boxes) == 1 and tuple(a[112, 30, :3]) != (240, 240, 240))
    from PIL import Image
    fl = V.rebrand(flag_picture(), ["#c8102e"], Image.open(logo).convert("RGBA"), "Test Cup")
    f = np.asarray(fl, dtype=np.int32)
    ok("rebrand: a flat flag in the competition's colour (%s)" % list(f[5, 5, :3]), f[5, 5, 0] > 150 and f[5, 5, 1] < 60)
    ok("rebrand: its decal the logo now (%s)" % list(f[64, 64, :3]), tuple(f[64, 64, :3]) != (250, 250, 250))
    ok("rebrand: a picture with no flat colour left alone", V.rebrand(noisy_picture(), ["#c8102e"], None, "x") is None)
    grey = Image.new("RGBA", (64, 64), (128, 128, 128, 255))
    ok("rebrand: a grey one left alone", V.rebrand(grey, ["#c8102e"], None, "x") is None)
    staff = flag_picture()
    from PIL import ImageDraw
    ImageDraw.Draw(staff).ellipse([0, 0, 40, 50], fill=(224, 172, 140, 255))      # a face on the cloth
    ok("rebrand: a texture with people on it left alone (skin %.3f)" % V.skin(staff),
       V.rebrand(staff, ["#c8102e"], None, "x") is None and V.skin(flag_picture()) < V.SKIN)

    out = os.path.join(tmp, "v1")
    spec = {"base": base, "metal": "bronze", "colours": [], "logo": logo, "name": "Test Cup"}
    before = {os.path.join(d, f): open(os.path.join(d, f), "rb").read() for d, _s, fs in os.walk(base) for f in fs}
    done = V.write(spec, out)
    files = sorted(os.path.relpath(os.path.join(d, f), out).replace(os.sep, "/") for d, _s, fs in os.walk(out) for f in fs)
    ok("write: the cup's two textures and the stand, in each phase folder that has them (%s)" % files, files == sorted([
        "Final/" + CUP + "/#windx11/cup_bsm.ftex", "Final/" + CUP + "/#windx11/cup_mtl.ftex",
        "Final/common/demo/fixdemoobj/cupstand_afc_cl/#windx11/stand_bsm.ftex",
        "Knockout/" + CUP + "/#windx11/cup_bsm.ftex", "Knockout/" + CUP + "/#windx11/cup_mtl.ftex"]))
    ok("write: the paths it says", sorted(done) == sorted({f.split("/", 1)[1] for f in files}))
    ok("write: the base as it was", before == {os.path.join(d, f): open(os.path.join(d, f), "rb").read()
                                                for d, _s, fs in os.walk(base) for f in fs})
    ok("write: every file it writes an .ftex the game reads (one mip)",
       all(V.ftex_head(open(os.path.join(out, *f.split("/")), "rb").read())[3] == 1 for f in files))
    png = V.preview(spec, os.path.join(tmp, "preview.png"))
    ok("preview: a sheet of the base and the variant", os.path.getsize(png) > 1000)
    os.makedirs(os.path.join(tmp, "nocup"))
    try:
        V.write({"base": os.path.join(tmp, "nocup"), "metal": "gold"}, os.path.join(tmp, "v0"))
        raised = False
    except V.Error:
        raised = True
    ok("write: a folder with no trophy model is an error, nothing made", raised)

    b2 = os.path.join(tmp, "base2")
    shutil.copytree(base, b2)
    comps = [(c, "Cup %d" % c) for c in range(400, 440)] + [(500, ""), (501, "")]
    one = V.auto(comps, [base, b2], {401: logo})
    two = V.auto(list(reversed(comps)), [b2, base][::-1], {401: logo})
    ok("auto: the same variant for each competition, whatever their order", one == two)
    looks = [(s["base"], s["metal"], tuple(s["colours"]), s["logo"]) for s in one.values()]
    ok("auto: no two of the %d alike" % len(one), len(set(looks)) == len(looks) == len(comps))
    ok("auto: a competition with a logo takes its colours (%s)" % one[401]["colours"], one[401]["colours"][0] == "#00963c")
    ok("auto: one with no logo two colours of its own", all(len(s["colours"]) == 2 for s in one.values()))
    ok("auto: both bases used", {s["base"] for s in one.values()} == {base, b2})
    ok("auto: with no base nothing", V.auto(comps, [os.path.join(tmp, "gone")]) == {})
    return base, logo


def lua_block(tmp, base):
    """the block of a world with a paired trophy and a variant, in FL26's Entrance.lua's shape and
    (when on this PC) FL 2027's cinematics.lua"""
    texts = [("FL26 Entrance.lua", "Entrance.lua", "Entrance", TT.SAMPLE)]
    real27 = os.path.join(os.environ.get("FL27_DIR", r"E:\FL\FL27\game"), "SiderAddons", "modules", "common", "cinematics.lua")
    if os.path.isfile(real27):
        texts.append(("FL 2027 cinematics.lua", os.path.join("common", "cinematics.lua"), "cinematics",
                      "".join(T.strip(open(real27, encoding="latin-1", newline="").read().splitlines(True)))))
    else:
        print("skip - FL 2027's own cinematics.lua (not on this PC)")
    for label, rel, content, text in texts:
        sider = os.path.join(tmp, "lua-" + content, "SiderAddons")
        os.makedirs(os.path.join(sider, "modules", "common"))
        os.makedirs(os.path.join(sider, "content", content))
        path = os.path.join(sider, "modules", rel)
        open(path, "w", encoding="latin-1", newline="").write(text)
        taken = T.handled(sider)
        ok("%s: the tournament ids it has a trophy for (%d, 65535 not)" % (label, len(taken)),
           taken and 65535 not in taken and (59 in taken if content == "Entrance" else True))
        busy = min(taken)
        world = os.path.join(sider, "livecpk", "_FL26V")
        tro = os.path.join(world, T.FOLDER)
        os.makedirs(tro)
        TT.trophy(os.path.join(tro, "49"), "Eliminatorias", "Final")
        shutil.copytree(base, os.path.join(tro, "bases", "0"))
        own = sorted(r.replace("/", "\\").lower() for r in V.write(
            {"base": base, "metal": "silver", "colours": ["#123456", "#abcdef"], "logo": None, "name": "V"},
            os.path.join(tro, "500")))
        index = {"49": {"rids": [60, 1084], "match": "Eliminatorias", "final": "Final"},
                 "500": {"rids": [700, 1724], "match": "Knockout", "final": "Final", "base": "bases\\0", "own": own,
                         "auto": True},
                 "501": {"rids": [busy], "match": "Knockout", "final": "Final", "base": "bases\\0", "own": own,
                         "auto": True}}
        json.dump(index, open(os.path.join(tro, T.INDEX), "w"))
        T.switch_on(sider, "_FL26V", world, lambda t: None)
        once = open(path, encoding="latin-1", newline="").read()
        norm = lambda p: os.path.normcase(os.path.normpath(p))
        tex = "common\\demo\\prop\\cup_afc_cl_hi\\#windx11\\cup_bsm.ftex"
        fp = "common\\demo\\prop\\cup_afc_cl_hi\\#Win\\cup_afc_cl_hi.fpk"
        k, r, p = ask(sider, once, 700, 1, tex)
        ok("%s: a variant's own texture from its folder (%s), entry 16" % (label, k),
           r == 16 and norm(p) == norm(os.path.join(tro, "500", "Knockout", tex)))
        k, r, p = ask(sider, once, 700, 1, tex.upper().replace("\\", "/"))
        ok("%s: the same however Sider spells it (case, /)" % label, norm(p) == norm(os.path.join(tro, "500", "Knockout", tex)))
        k, r, p = ask(sider, once, 1724, 1, fp)
        ok("%s: its model (and every file it did not change) from the base (%s)" % (label, k),
           r == 16 and norm(p) == norm(os.path.join(tro, "bases", "0", "Knockout", fp)))
        k, r, p = ask(sider, once, 700, 53, tex)
        ok("%s: at the final its own Final texture" % label, norm(p) == norm(os.path.join(tro, "500", "Final", tex)))
        k, r, p = ask(sider, once, 700, 53, "common\\demo\\fixdemo\\ent\\cut_data\\x.fdc")
        ok("%s: at the final the base's Final for the ceremony's frames" % label,
           norm(p) == norm(os.path.join(tro, "bases", "0", "Final", "common\\demo\\fixdemo\\ent\\cut_data\\x.fdc")))
        k, r, p = ask(sider, once, 60, 1, tex)
        ok("%s: a paired trophy as before, every file from its folder" % label,
           norm(p) == norm(os.path.join(tro, "49", "Eliminatorias", tex)))
        plain = "".join(T.strip(once.splitlines(True)))
        ok("%s: a tournament id the module has a trophy for (%d) left to it" % (label, busy),
           ask(sider, once, busy, 1, tex) == ask(sider, plain, busy, 1, tex) and "-- competition 501" not in once)
        ok("%s: an id of no trophy as before" % label, ask(sider, once, 4321, 1, tex) == ask(sider, plain, 4321, 1, tex))
    paired = {"49": {"rids": [60, 1084], "match": "Eliminatorias", "final": "Final"},
              "222": {"rids": [262], "match": "", "final": ""}}
    ok("no variant: the block line for line the one before the variants (FL26 gets nothing new)",
       T.block("_FL26X", paired) == old_block("_FL26X", paired) and T.block("_FL26X", paired, {60}) == old_block("_FL26X", paired))
    ok("only variants the module has: no block", T.block("_FL26X", {"501": index["501"]}, {busy}) == [])


def build_variants(tmp, base, logo):
    import leaguebuilder as B
    world, prev = os.path.join(tmp, "w.building"), os.path.join(tmp, "w")
    sider = os.path.join(tmp, "bsider")
    os.makedirs(os.path.join(sider, "modules"))
    open(os.path.join(sider, "modules", "Entrance.lua"), "w", encoding="latin-1", newline="").write(TT.SAMPLE)
    emb = os.path.join(world, "common", "render", "symbol", "emblemLc")
    os.makedirs(emb)
    shutil.copy(logo, os.path.join(emb, "emb_0300_l.png"))
    regs = {59: [59, 1083], 300: [300], 301: [301, 1325], 302: [302], 2: [2, 1026]}
    names = {59: "Copa", 300: "Logo Cup", 301: "Liga", 302: "Super Cup", 2: "Champions"}
    was = B.competition_ids, B.FL27
    B.competition_ids = lambda db, base=None: [(c, r, names[c], "cup", False) for c, r in sorted(regs.items())]
    said = []
    try:
        pl = {"trophy_variants": {"bases": [base]}}
        B.FL27 = False
        ok("FL26: no variant made, a note why",
           T.build_variants(pl, world, None, {}, regs, said.append, sider, prev) == 0 and "FL 2027 only" in said[-1])
        B.FL27 = True
        index = {"302": {"rids": [302], "match": "", "final": "", "from": "x"}}
        n = T.build_variants(pl, world, None, index, regs, said.append, sider, prev)
        ok("FL 2027: a variant for each competition with no trophy and none of the module (%d: %s)" % (n, sorted(index)),
           n == 2 and sorted(index) == ["300", "301", "302"])
        e = index["300"]
        ok("its row: every regulation id, the base's phases, its own textures (%s)" % e["own"][:1],
           e["rids"] == [300] and e["base"] == "bases\\0" and (e["match"], e["final"]) == ("Knockout", "Final")
           and e["own"] and all(o == o.lower() and "/" not in o for o in e["own"]))
        ok("the base copied once into trophies\\bases\\0",
           os.path.isfile(os.path.join(world, T.FOLDER, "bases", "0", "Final", "common", "demo", "fixdemo", "ent",
                                       "cut_data", "x.fdc"))
           and not os.path.exists(os.path.join(world, T.FOLDER, "300", "Final", "common", "demo", "fixdemo")))
        ok("the competition's logo is its variant's (%s)" % index["300"]["look"]["colours"],
           index["300"]["look"]["logo"] == T._md5(logo) and index["300"]["look"]["colours"][0] == "#00963c")
        json.dump(index, open(os.path.join(world, T.FOLDER, T.INDEX), "w"))
        os.rename(world, prev)
        os.makedirs(emb)
        shutil.copy(logo, os.path.join(emb, "emb_0300_l.png"))
        again = {"302": index["302"]}
        t0 = time.time()
        T.build_variants(pl, world, None, again, regs, said.append, sider, prev)
        ok("the next Build takes the last one's variants (%s, %.1f s)" % (said[-1].strip(), time.time() - t0),
           "0 made, 2 as the last" in said[-1] and again == index)
        shutil.rmtree(world)
        os.makedirs(world)
        names[301] = "Liga Nova"
        third = {"302": index["302"]}
        T.build_variants(pl, world, None, third, regs, said.append, sider, prev)
        ok("a renamed competition gets its variant made again (%s)" % said[-1].strip(),
           "1 made, 1 as the last" in said[-1] and third["301"]["look"]["name"] == "Liga Nova")
        ok("problems: none for a good base", T.problems(pl) == [])
        p = T.problems({"trophy_variants": {"bases": [os.path.join(tmp, "gone"), os.path.join(tmp, "nocup")]}})
        ok("problems: a base gone, one with no trophy model (%d)" % len(p), len(p) == 2)
        sig = T.signature(pl)
        open(os.path.join(base, "Final", "new.ftex"), "wb").write(b"x")
        ok("a file put in a base makes the next Build a full one", T.signature(pl) != sig)
        ok("no variants: the signature as before", T.signature({"trophies": {}}) == [])
    finally:
        B.competition_ids, B.FL27 = was


def carioca(tmp):
    if not CAR or not os.path.isdir(CAR):
        print("skip - joaako1602's Carioca (not on this PC)")
        return
    t0 = time.time()
    spec = {"base": CAR, "metal": "silver", "colours": ["#0b7a3e", "#f2c200"], "logo": None, "name": "Test Cup"}
    done = V.write(spec, os.path.join(tmp, "car"))
    ok("Carioca: a variant of it (%d textures, %.1f s)" % (len(done), time.time() - t0),
       any("cup_afc_cl_hi" in d.lower() for d in done))
    ok("Carioca: its plates named by the md5 of its texture",
       any(V.panels_of(CAR, V._src(CAR, c), c) for c, _m in V.textures(CAR)["cup"]))


if __name__ == "__main__":
    compiles()
    ftex()
    tmp = tempfile.mkdtemp(prefix="trophyvariants-")
    try:
        base, logo = generator(tmp)
        lua_block(tmp, base)
        build_variants(tmp, base, logo)
        carioca(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("test_trophyvariants: ok (%d)" % N)
