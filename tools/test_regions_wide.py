r"""python tools/test_regions_wide.py [<folder with the game's tables>]  -> regions 0..255

The caps step "regions" (tools/regions.py) and the module side of regions 128..255 (FL 2027).
Nothing is written anywhere but memory and a temporary folder.

Always (needs unicorn, capstone and lupa; a part whose library is missing is skipped):
  * mkleague.enc_region / dec_region round-trip 0..255, and every region 0..127 encodes to the
    byte it always did (bit 2 clear);
  * the step's parser (18 bytes at 0x1414f8390, run in unicorn) reads every one of the 256
    bytes as dec_region does, and every byte with bit 2 clear as fl26reg128's parser reads it;
  * regions.caps_wide on a caps file with and without the step;
  * fl26reg128.lua (run in Lua) writes nothing and says 0..255 when the step's parser and its
    own 43 sites are in, and writes all 44 into a stock exe as before;
  * mkregnames' row count: the bytes it always wrote up to 127 rows, `cmp cl, n` past it;
  * fl26augseason's trampoline (unicorn): type 0 for 29..255, 5 for everything else; the old
    one's answer for every region but 128..255;
  * fl26swiss's split-carry stub (the bytes carry_install writes, here in Python): only the
    slots' keys, 12 and 15 carry, for every key 0..255, and an empty slot matches nothing.

With the exe (FL26_EXE):
  * regions.patches: 44 sites, every old= what the exe has, nothing overlapping;
  * fl26catlist.lua run in Lua over the exe's bytes: a world with no region past 127 gets
    exactly what the module wrote before (git HEAD copy, or the one in $FL26_CATLIST_OLD); a
    world with region 200 lists 255 regions (80 fb ff / 80 f9 ff) and its stubs, run in unicorn,
    name every region 0..255 from their 256-entry tables and send everything else on to the
    game's own code.

With base tables (the argument or $FL26_PESDB): the league builder hands out regions past 127
only with an FL 2027 caps set that has the step (use_regions), and a plan of 110 new countries
then goes 29..138, each its own, the competition row's byte decoding back.
"""
import os, re, shutil, struct, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import mkleague as M
import regions

FAILS = []
N = [0]


def ok(what, cond):
    N[0] += 1
    print("%s  %s" % ("ok  " if cond else "FAIL", what))
    if not cond:
        FAILS.append(what)


def old_enc(r):
    return ((r & 0x1F) << 3) | ((r >> 5) & 3)


def parser128(dword):
    return ((dword >> 27) & 0x1F) | ((dword >> 19) & 0x60)


# ---- unicorn helpers ----

def uc():
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_64
    return Uc(UC_ARCH_X86, UC_MODE_64)


def run_until(mu, start, stops, limit=200):
    """run from start until rip is one of stops; -> the stop reached"""
    from unicorn import UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_RIP
    hit = []

    def hook(m, addr, size, _):
        if addr in stops:
            hit.append(addr)
            m.emu_stop()
    h = mu.hook_add(UC_HOOK_CODE, hook)
    try:
        mu.emu_start(start, 0xFFFFFFFFFFFFFFFF, count=limit)
    finally:
        mu.hook_del(h)
    return hit[0] if hit else mu.reg_read(UC_X86_REG_RIP)


def encoding():
    ok("enc/dec round-trip 0..255", all(M.dec_region(M.enc_region(r)) == r for r in range(256)))
    ok("256 regions, 256 different bytes", len({M.enc_region(r) for r in range(256)}) == 256)
    ok("0..127 encode as before (bit 2 clear)",
       all(M.enc_region(r) == old_enc(r) and not M.enc_region(r) & 4 for r in range(128)))
    ok("128..255 are 0..127's bytes with bit 2 set",
       all(M.enc_region(r) == old_enc(r - 128) | 4 for r in range(128, 256)))
    ok("enc is rol8(region, 3), dec what the parser computes (regions.decode)",
       all(M.enc_region(r) == ((r << 3) | (r >> 5)) & 0xFF and regions.decode(M.enc_region(r)) == r
           for r in range(256)))
    for bad in (256, -1):
        try:
            M.enc_region(bad)
            ok("region %d refused" % bad, False)
        except ValueError:
            ok("region %d refused" % bad, True)


def parser():
    try:
        from unicorn.x86_const import UC_X86_REG_RAX, UC_X86_REG_R14, UC_X86_REG_RCX
    except ImportError:
        print("skip: no unicorn -- the parser is not run")
        return
    wide = bytes.fromhex(regions.PARSER_NEW)
    try:
        ok("the parser assembles (keystone) to PARSER_NEW", regions.parser_code() == wide)
    except ImportError:
        print("skip: no keystone -- PARSER_NEW not reassembled")
    old = [s for s in regions.reg128_sites() if s[0] == regions.PARSER][0]
    reg128 = bytes.fromhex(old[2])

    def run(code, b3):
        mu = uc()
        mu.mem_map(0x1414F8000, 0x1000)
        mu.mem_map(0x100000, 0x1000)
        mu.mem_write(regions.PARSER, code)
        row = bytes([0x11, 0x22, 0x33, b3])
        mu.mem_write(0x100000, row)
        mu.reg_write(UC_X86_REG_RAX, 0x100000)
        mu.reg_write(UC_X86_REG_R14, 0xDEADBEEFCAFE)
        mu.reg_write(UC_X86_REG_RCX, 0xFFFFFFFFFFFFFFFF)
        mu.emu_start(regions.PARSER, regions.PARSER_END)
        return mu.reg_read(UC_X86_REG_R14)
    got = [run(wide, b) for b in range(256)]
    ok("the step's parser: r14 = dec_region(+3) for all 256 bytes (upper bits clear)",
       got == [M.dec_region(b) for b in range(256)])
    got128 = [run(reg128, b) for b in range(256)]
    ok("fl26reg128's parser (unicorn) agrees with its formula",
       got128 == [parser128(b << 24 | 0x332211) for b in range(256)])
    ok("a byte with bit 2 clear reads the same under both parsers",
       all(got[b] == got128[b] for b in range(256) if not b & 4))


def caps_files():
    d = tempfile.mkdtemp(prefix="regwide-")
    try:
        a, b = os.path.join(d, "a.lua"), os.path.join(d, "b.lua")
        open(a, "w").write('local P = {\n  {va=0x%x, old="%s", new="%s", why="regions: parser"},\n}\n'
                           % (regions.PARSER, regions.PARSER_OLD, regions.PARSER_NEW))
        open(b, "w").write('local P = {\n  {va=0x1414c9c10, old="00", new="11", why="x"},\n}\n')
        ok("caps_wide: a set with the step", regions.caps_wide(a))
        ok("caps_wide: a set without it", not regions.caps_wide(b))
        ok("caps_wide: no file", not regions.caps_wide(os.path.join(d, "none.lua")))
        sets = [f for f in os.listdir(os.path.join(TOP, "sider")) if f.startswith("fl26caps.") and "-regions" in f]
        for f in sets:
            ok("caps_wide: %s" % f, regions.caps_wide(os.path.join(TOP, "sider", f)))
        for f in ("fl26caps.lua", "fl26caps.teams-coaches-regs-players-dates-matches-upper-mlcopy-fixtures-calendar.fl27.lua"):
            p = os.path.join(TOP, "sider", f)
            if not os.path.exists(p):        # the old FL27 set: a test fixture now
                p = os.path.join(TOP, "tools", "testdata", "caps", f)
            if os.path.exists(p):
                ok("caps_wide: %s (no step) is not wide" % f, not regions.caps_wide(p))
        # the FL27 install copy is the set the game runs since 6fc38dd, the step in it
        ok("caps_wide: fl26caps.fl27.lua (the FL27 install copy) is wide",
           regions.caps_wide(os.path.join(TOP, "sider", "fl26caps.fl27.lua")))
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---- Lua ----

def lua():
    try:
        from lupa import luajit21 as lj
    except ImportError:
        try:
            from lupa import lua51 as lj
        except ImportError:
            from lupa import LuaRuntime
            return LuaRuntime(encoding=None)
    return lj.LuaRuntime(encoding=None)


class Mem:
    """memory.read/write for a module: writes kept here, reads fall back to `base`"""
    def __init__(self, base):
        self.base, self.over, self.writes, self.allocs = base, {}, [], []

    def read(self, va, n):
        va, n = int(va), int(n)
        try:
            b = bytearray(self.base(va, n))
        except TypeError:           # not in the exe: an allocation of the module's
            b = bytearray(n)
        b = b.ljust(n, bytes(1))
        for i in range(n):
            if va + i in self.over:
                b[i] = self.over[va + i]
        return bytes(b)

    def write(self, va, s, record=True):
        va = int(va)
        s = bytes(s)
        for i, c in enumerate(s):
            self.over[va + i] = c
        if record:
            self.writes.append((va, s))


def run_module(src, mem, sider=None, prelude=""):
    L = lua()
    logs = []
    g = L.globals()
    g.log = lambda s: logs.append(s.decode("latin1") if isinstance(s, bytes) else str(s))
    memtab = L.eval(b"{}")
    memtab[b"read"] = lambda va, n: mem.read(va, n)
    memtab[b"write"] = lambda va, s: mem.write(va, s)
    memtab[b"unpack"] = lambda f, s: struct.unpack("<I" if f in (b"u32", "u32") else "<H", bytes(s))[0]
    g.memory = memtab
    if prelude:
        L.execute(prelude.encode())
    mod = L.execute(src.encode("utf-8") if isinstance(src, str) else src)
    ctx = L.eval(b"{}")
    ctx[b"sider_dir"] = (sider or tempfile.gettempdir()).encode() + b"\\"
    mod[b"init"](ctx)
    return logs


FAKE_FFI = r"""
ffi = { C = {} }
function ffi.cdef() end
function ffi.cast(t, v) return v end
function ffi.C.VirtualAlloc(p, n, a, b) _alloc(p, n); return p end
function ffi.copy(dst, s, n) memory.write(dst, s) end
"""


def reg128_module():
    try:
        lua()
    except ImportError:
        print("skip: no lupa -- fl26reg128.lua is not run")
        return
    src = open(regions.REG128, encoding="utf-8").read()
    sites = regions.reg128_sites()
    stock = {}
    for va, old, new, why in sites:
        for i, c in enumerate(bytes.fromhex(old)):
            stock[va + i] = c
    base = lambda va, n: bytes(stock.get(va + i, 0) for i in range(n))
    m = Mem(base)
    logs = run_module(src, m)
    ok("fl26reg128 on a stock exe: 44 sites written, regions 0..127",
       len(m.writes) == 44 and any("44 of 44 sites rewritten" in s and "regions 0..127" in s for s in logs))
    m2 = Mem(base)
    for va, old, new, why in sites:
        m2.write(va, bytes.fromhex(regions.PARSER_NEW if va == regions.PARSER else new), record=False)
    logs = run_module(src, m2)
    ok("fl26reg128 after the caps step: nothing written, regions 0..255",
       not m2.writes and any("0 of 44 sites rewritten, 44 already were" in s and "regions 0..255" in s
                             for s in logs))
    m3 = Mem(base)
    m3.write(regions.PARSER, bytes.fromhex(regions.PARSER_NEW), record=False)
    logs = run_module(src, m3)
    ok("fl26reg128 with only the step's parser in: writes the other 43", len(m3.writes) == 43)


def regnames():
    import mkregnames as R
    ok("mkregnames: 24 rows -> 83f918 (the shipped bytes)", R.count_bytes(24) == "83f918")
    ok("mkregnames: 127 rows -> 83f97f", R.count_bytes(127) == "83f97f")
    ok("mkregnames: 128 rows -> 80f980 (cmp cl, 0x80)", R.count_bytes(128) == "80f980")
    ok("mkregnames: 251 rows -> 80f9fb", R.count_bytes(251) == "80f9fb")
    try:
        R.count_bytes(256)
        ok("mkregnames: 256 rows refused", False)
    except ValueError:
        ok("mkregnames: 256 rows refused", True)
    try:
        from capstone import Cs, CS_ARCH_X86, CS_MODE_64
        md = Cs(CS_ARCH_X86, CS_MODE_64)
        i = list(md.disasm(bytes.fromhex(R.count_bytes(200)), R.COUNT[0]))
        ok("mkregnames: 200 rows decode as cmp cl, 0xc8", len(i) == 1 and (i[0].mnemonic, i[0].op_str) == ("cmp", "cl, 0xc8"))
    except ImportError:
        pass


def augseason():
    try:
        from unicorn.x86_const import UC_X86_REG_R8, UC_X86_REG_RAX
    except ImportError:
        print("skip: no unicorn -- fl26augseason is not run")
        return
    src = open(os.path.join(TOP, "sider", "experimental", "fl26augseason.lua"), encoding="utf-8").read()
    new = re.search(r'\{va=0x14252ee00, old="0+", new="([0-9a-f]+)"', src).group(1)
    oldb = "418d40e383f863b805000000730231c0e92d7404ff"
    BACK = 0x141576242

    def answer(code, r):
        mu = uc()
        mu.mem_map(0x14252E000, 0x1000)
        mu.mem_map(0x141576000, 0x1000)
        mu.mem_write(0x14252EE00, bytes.fromhex(code))
        mu.reg_write(UC_X86_REG_R8, r)
        mu.reg_write(UC_X86_REG_RAX, 0x77)
        stop = run_until(mu, 0x14252EE00, {BACK})
        return stop, mu.reg_read(UC_X86_REG_RAX)
    ok("fl26augseason: the trampoline is 21 bytes", len(new) == 42)
    probe = list(range(0, 300)) + [0xFFFF, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 0xFFFFFFFF0000001D]
    got = {r: answer(new, r) for r in probe}
    ok("fl26augseason: every answer jumps back to 0x141576242", all(s == BACK for s, _ in got.values()))
    ok("fl26augseason: type 0 for 29..255, 5 for every other region",
       all(got[r][1] == (0 if 29 <= (r & 0xFFFFFFFF) <= 255 else 5) for r in probe))
    was = {r: answer(oldb, r)[1] for r in probe}
    ok("fl26augseason: the old trampoline's answer for every region but 128..255",
       all(got[r][1] == was[r] for r in probe if not 128 <= r <= 255))


def carry_stub(keys):
    """the stub fl26swiss.c's carry_install writes (slots filled the way split_keys fills them):
    32 slots since 08.11.2026, every jump to "full" a rel32 je"""
    SLOTS, HEAD = 32, 18
    t = bytearray()
    full = HEAD + 10 * SLOTS + 14

    def je():
        t.extend(b"\x0f\x84")
        t.extend(struct.pack("<i", full - (len(t) + 4)))
    t += b"\x83\xef\x01"
    je()
    t += b"\x83\xff\x03"
    je()
    for i in range(SLOTS):
        t += b"\x40\x80\xff\x00"
        je()
    t += b"\xff\x25\0\0\0\0" + struct.pack("<Q", 0x14134A8AA)
    t += b"\xff\x25\0\0\0\0" + struct.pack("<Q", 0x14134A68E)
    for i, k in enumerate(keys):
        t[HEAD + 10 * i + 3] = (k - 12) & 0xFF
    return bytes(t)


def swiss():
    src = open(os.path.join(HERE, "native", "fl26swiss.c"), encoding="utf-8").read()
    ok("fl26swiss.c: 32 slots, cmp dil, imm8 at 18 + 10*i + 3, empty 0, rel32 je",
       "t[n++] = 0x40; t[n++] = 0x80; t[n++] = 0xff; t[n++] = 0x00;" in src
       and "#define CARRY_SLOTS 32" in src and "#define CARRY_HEAD 18" in src
       and "#define CARRY_IMM(i) (CARRY_HEAD + 10 * (i) + 3)" in src
       and "full = CARRY_HEAD + 10 * CARRY_SLOTS + 14" in src
       and "rr[0x2fe] <= 127" not in src)
    jsrc = open(os.path.join(HERE, "native", "fl26join.c"), encoding="utf-8").read()
    ok("fl26join.c: g_stype by 256 regions, rec_region unbounded",
       "#define NREGIONS 256" in jsrc and "static uint8_t g_stype[NREGIONS];" in jsrc and "rec[0x2fe] <= 127" not in jsrc and "r < 128" not in jsrc)
    try:
        from unicorn.x86_const import UC_X86_REG_RDI
    except ImportError:
        print("skip: no unicorn -- the carry stub is not run")
        return
    STUB, NONE, FULL = 0x150000000, 0x14134A8AA, 0x14134A68E
    for keys in ([], [30, 139, 140, 200, 255], [13, 29, 64, 127, 128, 160, 230, 254], list(range(200, 232))):
        code = carry_stub(keys)
        bad = []
        for key in range(256):
            mu = uc()
            mu.mem_map(STUB, 0x1000)
            mu.mem_map(0x14134A000, 0x1000)
            mu.mem_write(STUB, code)
            mu.reg_write(UC_X86_REG_RDI, (key - 11) & 0xFFFFFFFF)     # the game's sub edi,8 / sub edi,3
            stop = run_until(mu, STUB, {NONE, FULL})
            want = FULL if key in (12, 15) or key in keys else NONE
            if stop != want:
                bad.append(key)
        ok("carry stub with keys %s: only those, 12 and 15 carry (keys 0..255)%s"
           % (keys or "none", " -- wrong: %s" % bad[:10] if bad else ""), not bad)


# ---- with the exe ----

def exe_reader():
    try:
        import calwiden
        exe = calwiden.Exe()
    except BaseException as e:      # flpaths.need_exe exits without an exe
        print("skip: no exe (%s)" % str(e).strip()[:80])
        return None
    return exe.read


def step(read):
    ps = regions.patches(read)
    ok("regions.patches: 44 sites", len(ps) == 44)
    ok("every old= is the exe's", all(read(int(p["va"], 16), len(p["old"]) // 2).hex() == p["old"] for p in ps))
    ok("every why starts with 'regions: '", all(p["why"].startswith(regions.WHY) for p in ps))
    par = [p for p in ps if int(p["va"], 16) == regions.PARSER]
    ok("the parser site is the wide parser", len(par) == 1 and par[0]["new"] == regions.PARSER_NEW)
    spans = sorted((int(p["va"], 16), int(p["va"], 16) + len(p["old"]) // 2) for p in ps)
    ok("no two sites overlap", all(a[1] <= b[0] for a, b in zip(spans, spans[1:])))
    try:
        regions.check_overlap(ps, [{"va": "0x%x" % (regions.PARSER + 4), "old": "00"}])
        ok("check_overlap refuses a patch inside the parser", False)
    except SystemExit:
        ok("check_overlap refuses a patch inside the parser", True)


CATLIST = os.path.join(TOP, "sider", "experimental", "fl26catlist.lua")
COUNTRY_FN, LABEL_RET, ICONS_SITE = 0x1414CDBE0, 0x1415788DC, 0x140C6CD97


def world_file(d, leagues):
    os.makedirs(os.path.join(d, "modules"), exist_ok=True)
    with open(os.path.join(d, "modules", "fl26world.txt"), "w") as f:
        for i, (reg, country, conf) in enumerate(leagues):
            f.write("league %d cid=%d region=%d country=%d conf=%d name=Test %d\n"
                    % (1000 + i, 130 + i, reg, country, conf, i))


def catlist_run(src, read, d):
    m = Mem(read)
    allocs = []
    pre = FAKE_FFI
    L_logs = []
    # _alloc is a global the fake VirtualAlloc calls
    lu = lua()
    g = lu.globals()
    g._alloc = lambda p, n: allocs.append((int(p), int(n)))
    g.log = lambda s: L_logs.append(s.decode("latin1") if isinstance(s, bytes) else str(s))
    memtab = lu.eval(b"{}")
    memtab[b"read"] = lambda va, n: m.read(va, n)
    memtab[b"write"] = lambda va, s: m.write(va, s)
    memtab[b"unpack"] = lambda f, s: struct.unpack("<I", bytes(s))[0]
    g.memory = memtab
    lu.execute(pre.encode())
    mod = lu.execute(src.encode("utf-8"))
    ctx = lu.eval(b"{}")
    ctx[b"sider_dir"] = d.encode() + b"\\"
    mod[b"init"](ctx)
    return m, allocs, L_logs


def old_catlist():
    p = os.environ.get("FL26_CATLIST_OLD")
    if p:
        return open(p, encoding="utf-8").read()
    try:
        return subprocess.run(["git", "-C", TOP, "show", "HEAD:sider/experimental/fl26catlist.lua"],
                              capture_output=True, check=True).stdout.decode("utf-8")
    except Exception:
        return None


def catlist(read):
    try:
        lua()
    except ImportError:
        print("skip: no lupa -- fl26catlist.lua is not run")
        return
    src = open(CATLIST, encoding="utf-8").read()
    old = old_catlist()
    tmp = tempfile.mkdtemp(prefix="regwide-cat-")
    try:
        narrow = [(29, 212, 2), (45, 152, 4), (52, 16, 3), (127, 150, 5), (11, 200, 2)]
        a = os.path.join(tmp, "narrow")
        world_file(a, narrow)
        m, allocs, logs = catlist_run(src, read, a)
        ok("catlist, world up to 127: count sites 83fb7f / 83f97f",
           m.read(0x140EADAB6, 3).hex() == "83fb7f" and m.read(0x140EADBB4, 3).hex() == "83f97f")
        if old:
            m0, allocs0, logs0 = catlist_run(old, read, a)
            ok("catlist, world up to 127: every byte written as the module before it wrote it (%d writes)"
               % len(m.writes), m.writes == m0.writes and allocs == allocs0)
        else:
            print("skip: no old fl26catlist.lua to compare with")
        w = os.path.join(tmp, "wide")
        wide = narrow + [(128, 199, 2), (200, 145, 4), (255, 162, 3), (139, 11, 3)]
        world_file(w, wide)
        m, allocs, logs = catlist_run(src, read, w)
        ok("catlist, world with region 255: says so", any("regions up to 255" in s for s in logs))
        ok("catlist, wide: the parser is the step's or the log warns",
           any("WARNING" in s for s in logs) == (read(regions.PARSER, 11).hex() != regions.PARSER_NEW[:22]))
        ok("catlist, wide: count sites 80fbff / 80f9ff (255 regions)",
           m.read(0x140EADAB6, 3).hex() == "80fbff" and m.read(0x140EADBB4, 3).hex() == "80f9ff")
        ok("catlist, wide: '255 regions' listed", any("255 regions (28 shipped + 227 ours)" in s for s in logs))
        # the list itself
        lea = struct.unpack("<i", m.read(0x140EADA38 + 3, 4))[0] + 0x140EADA38 + 7
        ids = [struct.unpack("<I", m.read(lea + 4 * i, 4))[0] for i in range(255)]
        ok("catlist, wide: the list holds every region 1..255 once", sorted(ids) == list(range(1, 256)))
        try:
            from unicorn.x86_const import UC_X86_REG_RCX, UC_X86_REG_RAX, UC_X86_REG_RSP, UC_X86_REG_RDX
        except ImportError:
            print("skip: no unicorn -- the stubs are not run")
            return
        country = {r: c for r, c, _ in wide if r >= 29 or r in (11, 13, 14, 20)}
        label = {10: 211, 20: 135, 23: 135, 28: 31}
        jmp = m.read(COUNTRY_FN, 5)
        stub = COUNTRY_FN + 5 + struct.unpack("<i", jmp[1:5])[0]
        ok("catlist, wide: the country function jumps to a stub", jmp[0] == 0xE9 and any(a == stub for a, _ in allocs))
        body = m.read(stub, 96 + 1024)
        RET_OTHER = 0x140001000
        bad = []
        for r in list(range(0, 260)) + [0x7FFFFFFF, 0xFFFFFFFF]:
            for ret in (LABEL_RET, RET_OTHER):
                mu = uc()
                mu.mem_map(stub & ~0xFFF, 0x2000)
                mu.mem_map(COUNTRY_FN & ~0xFFF, 0x1000)
                mu.mem_map(0x200000, 0x2000)
                mu.mem_write(stub, body)
                mu.mem_write(0x201000, struct.pack("<Q", ret))
                mu.reg_write(UC_X86_REG_RSP, 0x201000)
                mu.reg_write(UC_X86_REG_RCX, r)
                mu.mem_map(ret & ~0xFFF, 0x1000)
                stop = run_until(mu, stub, {ret, COUNTRY_FN + 7})
                eax = mu.reg_read(UC_X86_REG_RAX) & 0xFFFF
                if r <= 255 and ret == LABEL_RET and r not in country and r in label:
                    want = (ret, label[r])
                elif r <= 255 and r in country:
                    want = (ret, country[r])
                else:
                    want = (COUNTRY_FN + 7, None)
                if stop != want[0] or (want[1] is not None and eax != want[1]):
                    bad.append((r, hex(ret), hex(stop), eax))
        ok("catlist, wide: the country stub names regions 0..255 from its tables, the rest go on to the game's code%s"
           % (" -- wrong: %s" % bad[:5] if bad else ""), not bad)
        call = m.read(ICONS_SITE, 5)
        if call[0] != 0xE8:
            print("skip: the League Info icons stub is not in (%s)" % [s for s in logs if "icons" in s][:1])
            return
        istub = ICONS_SITE + 5 + struct.unpack("<i", call[1:5])[0]
        ibody = m.read(istub, 64 + 256)
        runtime = [struct.unpack("<I", read(0x14297D270 + 4 * f, 4))[0] for f in range(8)]
        conf = {r: c for r, _, c in wide if r >= 29}
        bad = []
        for r in list(range(0, 260)):
            mu = uc()
            mu.mem_map(istub & ~0xFFF, 0x1000)
            mu.mem_map(0x200000, 0x2000)
            mu.mem_map(0x300000, 0x1000)
            mu.mem_write(istub, ibody)
            mu.mem_write(0x300300, struct.pack("<I", 0x0B << 25 | 0x1234))
            mu.mem_write(0x201000, struct.pack("<Q", ICONS_SITE + 5))
            mu.mem_map((ICONS_SITE + 5) & ~0xFFF, 0x1000)
            mu.reg_write(UC_X86_REG_RSP, 0x201000)
            mu.reg_write(UC_X86_REG_RAX, 0x300000)
            mu.reg_write(UC_X86_REG_RDX, r)
            stop = run_until(mu, istub, {ICONS_SITE + 5})
            ecx = mu.reg_read(UC_X86_REG_RCX)
            want = runtime[conf[r]] if r in conf else 0x0B
            if stop != ICONS_SITE + 5 or ecx != want:
                bad.append((r, ecx, want))
        ok("catlist, wide: the icons stub gives regions 29..255 their confederation, the rest their own code%s"
           % (" -- wrong: %s" % bad[:5] if bad else ""), not bad)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---- the league builder ----

def builder(base):
    import leaguebuilder as B
    tmp = tempfile.mkdtemp(prefix="regwide-lb-")
    try:
        fl27 = os.path.join(tmp, "fl27")
        fl26 = os.path.join(tmp, "fl26")
        for d, exe in ((fl27, "FL_2027.exe"), (fl26, "FL_2026.exe")):
            os.makedirs(d)
            open(os.path.join(d, exe), "wb").close()
        wide = os.path.join(tmp, "wide.lua")
        open(wide, "w").write('{va=0x%x, old="%s", new="%s", why="regions: parser"}\n'
                              % (regions.PARSER, regions.PARSER_OLD, regions.PARSER_NEW))
        narrow = os.path.join(tmp, "narrow.lua")
        open(narrow, "w").write("-- no step\n")
        ok("use_regions: FL 2026 stays at 127 even with a wide set", B.use_regions(fl26, wide) == 127)
        ok("use_regions: FL 2027 without the step stays at 127", B.use_regions(fl27, narrow) == 127)
        ok("use_regions: FL 2027 with the step goes to 255", B.use_regions(fl27, wide) == 255 == B.REGION_LAST)
        if not base:
            print("# no base tables given -- the builder's allocation is not checked")
            return
        names = [n for n, _ in B.country_ids(base)]
        taken = {"England", "France", "Italy", "Spain", "Portugal", "Netherlands", "Belgium",
                 "Russia", "Switzerland", "Denmark", "Scotland", "Turkey", "Greece", "Argentina",
                 "Brazil", "Chile", "Colombia", "China", "Japan", "Saudi Arabia", "United States",
                 "USA", "Mexico", "Thailand", "Poland", "Croatia", "Germany", "Usa"}
        countries = [n for n in names if n not in taken][:110]
        recipe = {"world": "_TestRegWide",
                  "leagues": [{"name": "RegWide League %03d" % i, "country": c, "clubs": 10, "legs": 2}
                              for i, c in enumerate(countries)]}
        cap = B.TEAM_CAP, B.PLAYER_CAP
        B.TEAM_CAP, B.PLAYER_CAP = B.GAME_CAPS["fl27"]
        try:
            pl = B.plan(recipe, base)
        except B.BuildError as e:
            ok("plan of %d new countries: %s" % (len(countries), e), False)
            return
        finally:
            B.TEAM_CAP, B.PLAYER_CAP = cap
        regs = [p["region"] for p in pl["leagues"]]
        ours = sorted(r for r in regs if r >= 29)
        ok("%d leagues, %d regions, each its own" % (len(regs), len(set(regs))), len(set(regs)) == len(regs))
        ok("regions past 127 handed out (%s..%s)" % (ours[0], ours[-1]), ours[-1] > 127 and 128 in ours)
        ok("every region within 29..255", all(29 <= r <= 255 or r in (11, 13, 14, 20) for r in regs))
        comp = bytearray(M.COMP)
        r = max(regs)
        comp[M.REGION_OFF] = M.enc_region(r)
        ok("Competition.bin +3 for region %d is 0x%02x, the step's parser reads it back" % (r, comp[M.REGION_OFF]),
           regions.decode(comp[M.REGION_OFF]) == r)
        B.use_regions(fl27, narrow)
        try:
            B.plan(recipe, base)
            ok("without the step the same plan is refused (99 regions)", False)
        except B.BuildError as e:
            ok("without the step the same plan is refused: %s" % str(e)[:70], "no free region" in str(e))
    finally:
        import leaguebuilder as B
        B.REGION_LAST = M.REGION_MAX
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    encoding()
    parser()
    caps_files()
    reg128_module()
    regnames()
    augseason()
    swiss()
    read = exe_reader()
    if read:
        step(read)
        catlist(read)
    base = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("FL26_PESDB")
    builder(base if base and os.path.exists(os.path.join(base, "Competition.bin")) else None)
    print("%d checks, %d failed" % (N[0], len(FAILS)))
    for f in FAILS:
        print("FAIL: %s" % f)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
