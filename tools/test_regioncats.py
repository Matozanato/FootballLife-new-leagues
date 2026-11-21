"""tools/mkregioncats.py: the competition-list headings, run on the game's own reader.

The first reader walked its rows with "cmp eax, imm8; jb": a byte with a sign, so 128 rows or
more read as a negative bound, the unsigned jb as some four billion, and a competition with no
row was looked for past the table (06.11.2026: 209 rows for _FL26Comb150). The rows now sit in
a page of their own behind a stub with an imm32 bound. This runs the exe's reader in unicorn:

  * the old imm8 bound at 209 rows walks past the table (the bug, so the test can see it);
  * the patched reader with 279 rows (the Megapack's 199 leagues) finds every row, gives a
    competition with no row the "none" category and returns;
  * the generated module gets its page, refuses a page that is not empty and writes nothing;
  * Switch on makes an old world's cave module again, with the same leagues.

Needs the FL27 exe (FL26_EXE, default E:/FL/FL27/game/FL_2027.exe), unicorn and lupa.
"""
import os
import struct
import sys

os.environ.setdefault("FL26_EXE", "E:/FL/FL27/game/FL_2027.exe")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import mkregioncats as R              # noqa: E402

FAILS = []
N = [0]
RET_FOUND = 0x141e5b24a
RET_NONE = 0x141e5b244
STUB_RET = R.PAGE_VA + 16
STACK = 0x10000000


def ok(what, cond):
    N[0] += 1
    print("%s  %s" % ("ok  " if cond else "FAIL", what))
    if not cond:
        FAILS.append(what)


def patched(patches, d, off):
    """{va: bytes} of the code page and our page, as the module leaves them"""
    code_va = R.LOOP_VA & ~0xfff
    code = bytearray(d[off(code_va):off(code_va) + 0x2000])
    page = bytearray(R.PAGE_SIZE)
    for p in patches:
        va, new = int(p["va"], 16), bytes.fromhex(p["new"])
        if code_va <= va < code_va + len(code):
            code[va - code_va:va - code_va + len(new)] = new
        elif R.PAGE_VA <= va < R.PAGE_VA + R.PAGE_SIZE:
            page[va - R.PAGE_VA:va - R.PAGE_VA + len(new)] = new
    return code_va, bytes(code), bytes(page)


def reader(code_va, code, page, cid, limit=20000):
    """run 0x141e5b220 with ecx = cid -> (where it stopped, eax)"""
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_EAX, UC_X86_REG_RSP, UC_X86_REG_RIP
    mu = Uc(UC_ARCH_X86, UC_MODE_64)
    mu.mem_map(code_va, len(code))
    mu.mem_write(code_va, code)
    mu.mem_map(R.PAGE_VA, R.PAGE_SIZE)
    mu.mem_write(R.PAGE_VA, page)
    mu.mem_map(STACK, 0x10000)
    mu.reg_write(UC_X86_REG_RSP, STACK + 0x8000)
    # the original table (and what lies past it) for the unpatched reader
    d, off = R.image()
    t = R.ROWS_VA & ~0xfff
    mu.mem_map(t, 0x10000)
    mu.mem_write(t, d[off(t):off(t) + 0x10000])
    mu.reg_write(UC_X86_REG_ECX, cid)
    stops = {RET_FOUND, RET_NONE, STUB_RET}
    hit = []

    def hook(m, addr, size, _):
        if addr in stops:
            hit.append(addr)
            m.emu_stop()
    mu.hook_add(UC_HOOK_CODE, hook)
    try:
        mu.emu_start(0x141e5b220, 0xFFFFFFFFFFFFFFFF, count=limit)
    except Exception:                       # walked off the mapped memory
        return None, mu.reg_read(UC_X86_REG_EAX)
    return (hit[0] if hit else mu.reg_read(UC_X86_REG_RIP)), mu.reg_read(UC_X86_REG_EAX)


def comps(n):
    """n ids no shipped competition has"""
    d, off = R.image()
    shipped = d[off(R.ROWS_VA):off(R.ROWS_VA) + R.ROWS_N * 8]
    have = {struct.unpack_from("<I", shipped, i * 8)[0] for i in range(R.ROWS_N)}
    return [c for c in range(700, 5000) if c not in have][:n], shipped


def old_bug():
    d, off = R.image()
    code_va = R.LOOP_VA & ~0xfff
    code = bytearray(d[off(code_va):off(code_va) + 0x2000])
    code[0x141e5b23a - code_va + 2] = 209        # what 209 rows made of "cmp eax, 0x50"
    stop, eax = reader(code_va, bytes(code), bytes(R.PAGE_SIZE), 0x7fffffff)
    ok("the old imm8 bound at 209 rows: an unlisted competition is looked for past row 209 "
       "(stopped at %s, eax %d)" % (stop and hex(stop), eax), stop != RET_NONE and eax > 209)


def new_reader():
    ids, shipped = comps(199)
    patches, n, added = R.build(None, ids)
    ok("199 leagues of ours: 279 rows, 199 added", (n, added) == (279, 199))
    code_va, code, page = patched(patches, *R.image())
    for cid in (ids[0], ids[127], ids[128], ids[-1]):
        stop, eax = reader(code_va, code, page, cid)
        ok("comp %d (ours) -> category %d" % (cid, R.NEW_CAT), stop == RET_FOUND and eax == R.NEW_CAT)
    for i in (0, R.ROWS_N - 1):
        cid, cat = struct.unpack_from("<II", shipped, i * 8)
        stop, eax = reader(code_va, code, page, cid)
        ok("shipped comp %d keeps category %d" % (cid, cat), stop == RET_FOUND and eax == cat)
    stop, eax = reader(code_va, code, page, 0x7fffffff)
    ok("an unlisted competition gets %d (none) and the reader returns" % (R.KEYS_N + 1),
       stop == STUB_RET and eax == R.KEYS_N + 1)

    room = (R.PAGE_SIZE - (R.ROWS_AT - R.PAGE_VA)) // 8 - R.ROWS_N
    big, _ = comps(room + 1)
    try:
        R.build(None, big[:room])
        ok("%d leagues of ours fit in the page" % room, True)
    except SystemExit:
        ok("%d leagues of ours fit in the page" % room, False)
    try:
        R.build(None, big)
        ok("%d leagues are refused, not written past the page" % (room + 1), False)
    except SystemExit:
        ok("%d leagues are refused, not written past the page" % (room + 1), True)
    return patches


PRELUDE = r"""
ffi = { C = {} }
function ffi.cdef() end
function ffi.cast(t, v) return v end
function ffi.C.fl26regions_VirtualAlloc(p, n, a, b) _alloc(p, n); return p end
"""


def module(added, dirty=False):
    import io
    import tempfile
    import contextlib
    from test_regions_wide import Mem, run_module
    d, off = R.image()
    base = lambda va, k: d[off(va):off(va) + k] if va < R.PAGE_VA else None
    mem = Mem(base)
    if dirty:
        mem.write(R.PAGE_VA + 0x800, b"\x01", record=False)
    out = os.path.join(tempfile.mkdtemp(), "fl26regions.lua")
    ids, _ = comps(added)
    argv, sys.argv = sys.argv, ["mkregioncats.py", "--root", "-", "--comps",
                                ",".join(map(str, ids)), "--out", out, "--write"]
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            R.main()
    finally:
        sys.argv = argv
    src = open(out).read()
    alloc = 'function _alloc(p, n) log(string.format("alloc 0x%x %d", p, n)) end'
    logs = run_module(src, mem, prelude=PRELUDE + alloc)
    return mem, logs


def lua_module():
    ids, _ = comps(199)
    patches, n, added = R.build(None, ids)
    mem, logs = module(added)
    page = bytes.fromhex(patches[0]["new"])
    ok("module: the page holds the bound and the rows", mem.read(R.PAGE_VA, len(page)) == page)
    ok("module: all %d code sites written" % (len(patches) - 1),
       all(mem.read(int(p["va"], 16), len(p["new"]) // 2) == bytes.fromhex(p["new"])
           for p in patches[1:]))
    ok("module: says it applied all", any("applied all" in s for s in logs))
    ok("module: asked for its page, 0x%x bytes at 0x%x" % (R.PAGE_SIZE, R.PAGE_VA),
       "alloc 0x%x %d" % (R.PAGE_VA, R.PAGE_SIZE) in logs)

    mem, logs = module(added, dirty=True)
    ok("module: a page that is not empty -> ABORTED, no code written",
       any("not empty" in s for s in logs) and not mem.writes)


def switch_on_old_world():
    """a world built before the fix brings the cave module: Switch on makes it again"""
    import tempfile
    import leaguebuilder as LB
    ids, shipped = comps(150)
    root = tempfile.mkdtemp()
    os.makedirs(os.path.join(root, "modules"))
    f = os.path.join(root, "modules", "fl26regions.lua")
    rows = shipped + b"".join(struct.pack("<II", c, R.NEW_CAT) for c in ids)
    old = 'local m = {}\nlocal rows = {va=0x143394568, old="%s", new="%s"}\n' % (bytes(len(rows)).hex(), rows.hex())
    open(f, "w").write(old)
    game = os.path.dirname(os.environ["FL26_EXE"])
    logs = []
    LB.regioncats_for_exe(root, game, logs.append)
    new = open(f).read()
    ok("switch on: an old world's module made again in a page of its own (%s)" % "; ".join(logs),
       "fl26regions_VirtualAlloc" in new and "0x163d00040" in new)
    page = bytes.fromhex(R.build(None, ids)[0][0]["new"])
    ok("switch on: the same 150 leagues, the same page as a Build makes", page.hex() in new)
    logs = []
    LB.regioncats_for_exe(root, game, logs.append)
    ok("switch on: a module made with the fix is left alone", open(f).read() == new and not logs)


def main():
    if not os.path.exists(os.environ["FL26_EXE"]):
        print("skip: no %s" % os.environ["FL26_EXE"])
        return 0
    try:
        import unicorn  # noqa: F401
    except ImportError:
        print("skip: no unicorn")
        return 0
    old_bug()
    new_reader()
    lua_module()
    switch_on_old_world()
    print("\n%d checks, %d failed" % (N[0], len(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
