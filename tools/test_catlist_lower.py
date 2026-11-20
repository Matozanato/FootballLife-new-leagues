"""test_catlist_lower.py -- fl26catlist's League Info "lower league" stub (B420), run in an emulator.

The stub's bytes are taken from sider/experimental/fl26catlist.lua as the module puts them together and run
with Unicorn against a made-up competition table: the builder's frame ([rbp-0x19] the league's record), r15
the database, r14d the league's competition id, and the game's lookup 0x1414bb000 played by the test.

    python tools/test_catlist_lower.py
"""
import os, re, struct, sys

try:
    import unicorn
    from unicorn import x86_const as X
except ImportError:
    print("SKIP: unicorn is not installed")
    sys.exit(0)

HERE = os.path.dirname(os.path.abspath(__file__))
LUA = os.path.join(HERE, "..", "sider", "experimental", "fl26catlist.lua")
N = 0


def ok(what, cond):
    global N
    N += 1
    if not cond:
        print("FAIL:", what)
        sys.exit(1)


src = open(LUA, encoding="utf8").read()
blk = src[src.index("local function install_lower"):src.index("local function install_links")]
num = lambda name: int(re.search(r"\b%s\s*=\s*(0x[0-9a-fA-F]+|\d+)" % name, src).group(1), 0)
m = re.search(r"local LOWER_SITE, LOWER_BYTES, LOWER_BACK = (0x[0-9a-f]+), \"([0-9a-f]+)\", (0x[0-9a-f]+)", src)
SITE, SITE_BYTES, BACK = int(m.group(1), 16), m.group(2), int(m.group(3), 16)
LOOKUP = int(re.search(r"local LOOKUP, LOOKUP_BYTES = (0x[0-9a-f]+)", src).group(1), 16)
m = re.search(r"local LINKS_MAX, LINKS_TBL = (\d+), (\d+)", src)
LINKS_MAX, TBL = int(m.group(1)), int(m.group(2))
hx = re.findall(r'hex2bin\("([0-9a-f]+)"\)', blk)
ok("four runs of bytes in install_lower", len(hx) == 4)
code = (bytes.fromhex(hx[0]) + struct.pack("<I", TBL - 34) + bytes.fromhex(hx[1]) + struct.pack("<Q", LOOKUP)
        + bytes.fromhex(hx[2]) + struct.pack("<Q", BACK) + bytes.fromhex(hx[3]))
ok("the stub is 87 bytes, under the table", len(code) == 87 and len(code) <= TBL)
ok("the site is the builder's mov ebx,r14d ; jmp +0x40", SITE == 0x140c6d143 and SITE_BYTES == "418bdeeb40"
   and SITE + 5 + 0x40 == BACK)
ok("the module checks the site and the lookup before it writes", "LOWER_BYTES" in blk and "LOOKUP_BYTES" in blk)
ok("the stubs' block holds three pages", "0x3000, 0x3000, 0x40" in src and "install_lower(stub + 0x2000, down)" in src)

STUB, DB, FRAME, STACK = 0x15eb02000, 0x20000000, 0x30000000, 0x30010000
REC = 0x314
DEFAULT = DB + 0x80000                      # the record the lookup answers with for an id it has not got


def run(recs, me, down, self_comp=0x7777):
    """recs: {regulation id: (link below, competition id)}; me: the league's regulation id; down: the world's
    {id: id below}. -> (ebx at the way out, lookups asked)"""
    mu = unicorn.Uc(unicorn.UC_ARCH_X86, unicorn.UC_MODE_64)
    for base, size in ((STUB, 0x1000), (DB, 0x100000), (FRAME, 0x20000), (LOOKUP & ~0xfff, 0x1000), (BACK & ~0xfff, 0x1000)):
        mu.mem_map(base, size)
    tbl = b"".join(struct.pack("<H", down.get(r, 0xffff)) for r in range(LINKS_MAX + 1))
    mu.mem_write(STUB, code + b"\xcc" * (TBL - len(code)) + tbl)
    at = {}
    for k, (rid, (below, comp)) in enumerate(sorted(recs.items())):
        a = DB + 0x1000 + k * REC
        at[rid] = a
        mu.mem_write(a, struct.pack("<H", rid))
        mu.mem_write(a + 0x7e, struct.pack("<H", below))
        mu.mem_write(a + 0x80, struct.pack("<I", comp))
    mu.mem_write(DEFAULT, struct.pack("<H", 0xffff))
    mu.mem_write(DEFAULT + 0x80, struct.pack("<I", 0xdead))
    mu.mem_write(LOOKUP, b"\xc3")
    rbp, rsp = FRAME + 0x8000, FRAME + 0x7000
    mu.mem_write(rbp - 0x19, struct.pack("<Q", at[me]))
    asked = []

    def hook(u, addr, size, _):
        if addr == LOOKUP:
            ok("the lookup gets the database in rcx", u.reg_read(X.UC_X86_REG_RCX) == DB)
            ok("the stack is 16-aligned at the call", (u.reg_read(X.UC_X86_REG_RSP) + 8) % 16 == 0)
            rid = u.reg_read(X.UC_X86_REG_RDX) & 0xffff
            asked.append(rid)
            u.reg_write(X.UC_X86_REG_RAX, at.get(rid, DEFAULT))
            for r in (X.UC_X86_REG_RCX, X.UC_X86_REG_RDX, X.UC_X86_REG_R8, X.UC_X86_REG_R9, X.UC_X86_REG_R10, X.UC_X86_REG_R11):
                u.reg_write(r, 0x5a5a5a5a5a5a5a5a)      # the volatile registers come back spoiled
    mu.hook_add(unicorn.UC_HOOK_CODE, hook, begin=LOOKUP, end=LOOKUP)
    keep = {X.UC_X86_REG_RBP: rbp, X.UC_X86_REG_RSP: rsp, X.UC_X86_REG_R15: DB, X.UC_X86_REG_R14: self_comp,
            X.UC_X86_REG_RSI: 0x1111, X.UC_X86_REG_RDI: 0x2222, X.UC_X86_REG_R12: 0, X.UC_X86_REG_R13: 0x3333}
    for r, v in keep.items():
        mu.reg_write(r, v)
    mu.reg_write(X.UC_X86_REG_RBX, 0xffffffff)
    mu.emu_start(STUB, BACK, count=200)
    ok("the stub leaves for the builder's 0x%x" % BACK, mu.reg_read(X.UC_X86_REG_RIP) == BACK)
    for r, v in keep.items():
        ok("a register the builder still needs is kept", mu.reg_read(r) == v)
    ok("the frame's record is untouched", struct.unpack("<Q", mu.mem_read(rbp - 0x19, 8))[0] == at[me])
    return mu.reg_read(X.UC_X86_REG_RBX) & 0xffffffff, asked


SELF = 0x7777
# 1. the game's own link below (a league of the game in the middle: the Championship)
ebx, asked = run({10: (11, 100), 11: (0xffff, 111)}, 10, {})
ok("the runtime link below is followed: %x %s" % (ebx, asked), ebx == 111 and asked == [11])
# 2. no runtime link, the world names the league below (the first group of a set)
ebx, asked = run({300: (0xffff, 100), 301: (0xffff, 222)}, 300, {300: 301})
ok("the world's league below: %x %s" % (ebx, asked), ebx == 222 and asked == [301])
# 3. nothing below: the game's answer, the league itself
ebx, asked = run({300: (0xffff, 100)}, 300, {})
ok("a bottom league shows itself, as the game does", ebx == SELF and asked == [])
# 4. the world names a league the game has no record of
ebx, asked = run({300: (0xffff, 100)}, 300, {300: 999})
ok("an id with no record: itself", ebx == SELF and asked == [999])
# 5. a regulation id past the table and no runtime link
ebx, asked = run({0x500: (0xffff, 100)}, 0x500, {})
ok("an id past the table: itself", ebx == SELF and asked == [])
# 6. the runtime link wins over the world's
ebx, asked = run({300: (302, 100), 301: (0xffff, 222), 302: (0xffff, 333)}, 300, {300: 301})
ok("the runtime link first", ebx == 333 and asked == [302])
# 7. the last id of the table
ebx, asked = run({LINKS_MAX: (0xffff, 100), 5: (0xffff, 55)}, LINKS_MAX, {LINKS_MAX: 5})
ok("the table's last entry", ebx == 55 and asked == [5])
# the module still compiles, and its u64le writes the two addresses as the test put them together
try:
    import lupa
except ImportError:
    lupa = None
if lupa:
    NL = chr(10)
    try:
        import lupa.luajit21 as engine          # Sider runs LuaJIT
    except ImportError:
        engine = lupa
    lua = engine.LuaRuntime()
    res = lua.eval("function(src) local f, e = (loadstring or load)(src, 'fl26catlist.lua') return f ~= nil, e end")(src)
    good, err = res if isinstance(res, tuple) else (res, None)
    ok("fl26catlist.lua compiles: %s" % err, good)
    u32 = src[src.index("local function u32le(v)"):]
    u32 = u32[:u32.index(NL + "end") + 4]
    u64 = src[src.index("local function u64le(v)"):]
    u64 = u64[:u64.index(NL + "end") + 4]
    f = lua.execute(u32 + NL + u64 + NL + "return function(v) local s = u64le(v); local t = {} "
                    "for i = 1, #s do t[i] = string.format('%02x', s:byte(i)) end return table.concat(t) end")
    for v in (LOOKUP, BACK):
        ok("u64le(0x%x)" % v, f(v) == struct.pack("<Q", v).hex())
print("all %d checks passed" % N)
