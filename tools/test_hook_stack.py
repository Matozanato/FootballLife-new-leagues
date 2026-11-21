"""test_hook_stack.py -- the byte checks of fl26catlist and fl26confgroups against FL 2027's code as
the modules before them in the pack leave it, not as the exe file has it.

Why (beta4p, 17.11.2026): fl26compcache, loaded earlier, puts `jmp rel32; nop` on the entry of
0x1414bb000 (a regulation by id). fl26confgroups' new check of that entry expected the file's bytes,
so the DLL said "off bytes at 0x1414bb000 ... nothing written" and Select Team and Competition Info
lost their confederations; fl26catlist's lower-league stub had stood down for the same reason since
beta4o. test_confgroups_dll.py compared with the file only, so neither showed up offline.

What it does, without the game:
  1. FL_2027.exe (FL27_EXE, else E:/FL/FL27/game/FL_2027.exe) is mapped into this process the way the
     loader would (headers and sections at their RVAs, in a read-write-execute block).
  2. The modules of the pack run over it in lbpack.ORDER (FL 2027's copies, the bundles opened),
     up to fl26confgroups:
       - every `{va=0x..., old="...", new="..."}` patch a module's Lua file declares is applied
         where the bytes are `old` (fl26caps and the other Lua patch sets);
       - the DLLs whose install takes the exe's base alone (fl26walk, fl26compcache, fl26edit,
         fl26squadlist) are built from tools/native with zig, loaded here and installed on the image;
       - the sites fl26catlist itself writes are noted (its stubs are not built here).
     A DLL that needs the world's configuration (fl26join, fl26chain, fl26clubs, fl26regen) is not
     run; it says so.
  3. Then the checks, with the modules' own rules:
       - fl26catlist: every site it patches is the game's bytes exactly; 0x1414bb000, which it only
         calls, is the game's or behind another module's jump (called_ok in fl26catlist.lua);
       - fl26confgroups: the SIGS table of fl26confgroups.c with sig_state's rule (a site of OWN
         exactly, any other one the game's or behind another module's jump), the eight vtable
         entries, and no site fl26catlist writes inside a SIGS range.
     And the case that broke beta4p is asserted to be there: 0x1414bb000 starts with
     fl26compcache's jump.

    python tools/test_hook_stack.py

Needs zig (ZIG, PATH, or D:/dev/tools/zig-*/zig.exe) and the exe; without either it says SKIPPED.
No game is started.
"""
import ctypes, glob, os, re, shutil, struct, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
NATIVE = os.path.join(HERE, "native")
SIDER = os.path.join(ROOT, "sider")
IMAGE_VA = 0x140000000
STOP = "fl26confgroups"
# DLL modules whose install(exe_base) patches code only (no world line, no config)
RUN_DLLS = {"fl26walk": "fl26_walk_install", "fl26compcache": "fl26_compcache_install",
            "fl26edit": "fl26_edit_install", "fl26squadlist": "fl26_squadlist_install"}
NEED_CFG = {"fl26joindll": "fl26join", "fl26chain": "fl26chain", "fl26clubs": "fl26clubs",
            "fl26regen": "fl26regen", "fl26swiss": "fl26swiss", "fl26match": "fl26match"}


def find_zig():
    z = os.environ.get("ZIG")
    if z and os.path.exists(z):
        return z
    z = shutil.which("zig")
    if z:
        return z
    found = sorted(glob.glob("D:/dev/tools/zig-*/zig.exe"))
    return found[-1] if found else None


def pack_order():
    import ast
    tree = ast.parse(open(os.path.join(HERE, "lbpack.py"), encoding="utf-8").read())
    ns = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) \
                and node.targets[0].id in ("ORDER", "BUNDLES", "FL27"):
            ns[node.targets[0].id] = ast.literal_eval(node.value)
    assert set(ns) == {"ORDER", "BUNDLES", "FL27"}, sorted(ns)
    out = []
    for n in ns["ORDER"]:
        for part in ns["BUNDLES"].get(n, [n]):
            out.append((part, ns["FL27"].get(part, part)))
    return out


def lua_file(name, fl27name):
    for n in (fl27name, name):
        for d in (SIDER, os.path.join(SIDER, "experimental")):
            p = os.path.join(d, n + ".lua")
            if os.path.exists(p):
                return p
    return None


k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.VirtualAlloc.restype = ctypes.c_void_p
k32.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32, ctypes.c_uint32]


def map_image(path):
    raw = open(path, "rb").read()
    pe = struct.unpack_from("<I", raw, 0x3c)[0]
    nsec, optsz = struct.unpack_from("<HH", raw, pe + 6)[0], struct.unpack_from("<H", raw, pe + 20)[0]
    size_image, size_hdr = struct.unpack_from("<II", raw, pe + 24 + 56)
    base = None
    # below the block there must be room for the modules' stubs (each wants a page within 2 GB)
    for want in range(0x7ff000000000, 0x7e0000000000, -0x100000000):
        base = k32.VirtualAlloc(ctypes.c_void_p(want), size_image, 0x3000, 0x40)
        if base:
            break
    assert base, "no room to map the exe (%d MB)" % (size_image >> 20)
    ctypes.memmove(base, raw, size_hdr)
    for i in range(nsec):
        o = pe + 24 + optsz + 40 * i
        vsz, rva, rsz, rp = struct.unpack_from("<IIII", raw, o + 8)
        if rsz:
            ctypes.memmove(base + rva, raw[rp:rp + min(rsz, vsz or rsz)], min(rsz, vsz or rsz))
    return base, size_image


def rd(base, va, n):
    return ctypes.string_at(base + va - IMAGE_VA, n)


def wr(base, va, b):
    ctypes.memmove(base + va - IMAGE_VA, b, len(b))


PATCH = re.compile(r'va\s*=\s*0x([0-9a-fA-F]+)\s*,\s*old\s*=\s*"([0-9a-fA-F]+)"\s*,\s*new\s*=\s*"([0-9a-fA-F]+)"')


def called_ok(got, want):
    """fl26catlist.called_ok / fl26confgroups' sig_state for a function only called: the game's bytes,
    or `jmp rel32`, nop / int3 padding and the game's bytes after it"""
    if got == want:
        return 1
    if got[:1] != b"\xe9":
        return 0
    k = 5
    while k < len(want) and got[k] in (0x90, 0xcc):
        k += 1
    return 2 if k < len(want) and got[k:] == want[k:] else 0


def main():
    exe = os.environ.get("FL27_EXE", "E:/FL/FL27/game/FL_2027.exe")
    zig = find_zig()
    if not os.path.exists(exe) or not zig:
        print("SKIPPED: %s" % ("no FL 2027 exe at %s (set FL27_EXE)" % exe if not os.path.exists(exe) else "no zig (set ZIG)"))
        return 0
    base, size = map_image(exe)
    checks = 0

    cat_src = open(os.path.join(SIDER, "experimental", "fl26catlist.lua"), encoding="utf-8").read()
    cg_src = open(os.path.join(NATIVE, "fl26confgroups.c"), encoding="utf-8").read()
    defs = {m.group(1): int(m.group(2), 16) for m in re.finditer(r"^#define (\w+)\s+0x([0-9a-fA-F]+)\b", cg_src, re.M)}
    sigs = [(n, bytes.fromhex(h), w) for n, h, w in re.findall(r'\{ (\w+),\s+"([0-9a-f]+)", "([^"]+)" \}', cg_src)]
    own = re.search(r"static const uint64_t OWN\[\] = \{([^}]*)\}", cg_src).group(1).replace("\n", " ")
    own = {defs[x.strip()] for x in own.split(",") if x.strip()}
    vts = re.findall(r"\{ (\w+) \+ (0x[0-9a-f]+),\s+(\w+),\s+\"([^\"]+)\" \}", cg_src)
    assert len(sigs) >= 30 and len(vts) == 8 and len(own) >= 9, (len(sigs), len(vts), len(own))

    # fl26catlist's checks: {site, bytes, called only?}
    cat = []
    for va, h in re.findall(r'\{ (0x14[0-9a-f]+), "([0-9a-f]+)"', cat_src):
        cat.append((int(va, 16), bytes.fromhex(h), False))
    for va_name, hex_expr in (("COUNTRY_FN", "COUNTRY_ENTRY"), ("ICONS_SITE", "ICONS_OLD"), ("CONF_TABLE", "CONF_TABLE_BYTES")):
        va = int(re.search(r"local %s\s*=\s*(0x[0-9a-f]+)" % va_name, cat_src).group(1), 16)
        hx = "".join(re.findall(r'"([0-9a-f]+)"', re.search(r"local %s\s*=\s*([^\n]*)" % hex_expr, cat_src).group(1)))
        cat.append((va, bytes.fromhex(hx), False))
    m = re.search(r'local LOWER_SITE, LOWER_BYTES, LOWER_BACK = (0x[0-9a-f]+), "([0-9a-f]+)"', cat_src)
    cat.append((int(m.group(1), 16), bytes.fromhex(m.group(2)), False))
    m = re.search(r'local LOOKUP, LOOKUP_BYTES = (0x[0-9a-f]+), "([0-9a-f]+)"', cat_src)
    lookup = int(m.group(1), 16)
    cat.append((lookup, bytes.fromhex(m.group(2)), True))
    assert "called_ok(got, c[2])" in cat_src and "{ LOOKUP, LOOKUP_BYTES, true }" in cat_src
    assert len(cat) >= 10, len(cat)
    # the sites fl26catlist writes (for the overlap with confgroups): the patched ones, 5+ bytes each
    cat_writes = [(va, len(b)) for va, b, called in cat if not called and va != int(
        re.search(r"local CONF_TABLE\s*=\s*(0x[0-9a-f]+)", cat_src).group(1), 16)]

    watched = [(defs[n], len(b)) for n, b, _w in sigs] + [(va, len(b)) for va, b, _c in cat]
    snap = lambda: {va: rd(base, va, n) for va, n in watched}
    who = {}

    def note(before, module):
        after = snap()
        for va in after:
            if after[va] != before[va]:
                who.setdefault(va, []).append(module)

    tmp = tempfile.mkdtemp()
    order = pack_order()
    names = [n for n, _f in order]
    assert STOP in names and "fl26catlist" in names and names.index("fl26compcache") < names.index("fl26catlist") < names.index(STOP)
    keep = []
    for name, fl27 in order:
        if name == STOP:
            break
        before = snap()
        lua = lua_file(name, fl27)
        done = []
        if lua:
            n_ok = n_skip = 0
            for va, old, new in PATCH.findall(open(lua, encoding="utf-8", errors="replace").read()):
                va, old, new = int(va, 16), bytes.fromhex(old), bytes.fromhex(new)
                if not IMAGE_VA <= va < IMAGE_VA + size:
                    continue
                if rd(base, va, len(old)) == old:
                    wr(base, va, new)
                    n_ok += 1
                else:
                    n_skip += 1
            if n_ok or n_skip:
                done.append("%d patches of %s (%d not the bytes expected)" % (n_ok, os.path.basename(lua), n_skip))
        if name in RUN_DLLS:
            dll = os.path.join(tmp, name + ".dll")
            subprocess.run([zig, "cc", "-shared", "-target", "x86_64-windows-gnu", "-O2", "-s", "-w", "-o", dll,
                            os.path.join(NATIVE, name + ".c"), "-lkernel32"], check=True, cwd=NATIVE)
            d = ctypes.CDLL(dll)
            keep.append(d)
            fn = getattr(d, RUN_DLLS[name])
            fn.restype, fn.argtypes = ctypes.c_int, [ctypes.c_uint64]
            done.append("%s.dll installed: %d" % (name, fn(base)))
        elif name in NEED_CFG:
            done.append("%s.dll not run here (it needs the world's configuration)" % NEED_CFG[name])
        note(before, name)
        if done:
            print("  %-16s %s" % (name, "; ".join(done)))

    # the case of beta4p: fl26compcache's jump on 0x1414bb000
    entry = rd(base, lookup, 6)
    assert entry[0] == 0xe9 and entry[5] == 0x90 and "fl26compcache" in who.get(lookup, []), \
        "0x1414bb000 is %s, not behind fl26compcache's jump: the case this test is for is not there" % entry.hex()
    checks += 1

    fails = []
    for va, want, called in cat:
        got = rd(base, va, len(want))
        st = called_ok(got, want) if called else int(got == want)
        if not st:
            fails.append("fl26catlist: 0x%x is %s, expected %s (changed by %s)" % (va, got.hex(), want.hex(), who.get(va, "?")))
        elif st == 2:
            print("  fl26catlist: 0x%x only called, behind %s's jump -- accepted" % (va, "/".join(who.get(va, ["?"]))))
        checks += 1
    for name, want, what in sigs:
        va = defs[name]
        got = rd(base, va, len(want))
        st = int(got == want) if va in own else called_ok(got, want)
        if not st:
            fails.append("fl26confgroups: 0x%x [%s] is %s, expected %s (changed by %s)" % (va, what, got.hex(), want.hex(), who.get(va, "?")))
        elif st == 2:
            print("  fl26confgroups: 0x%x [%s] only called, behind %s's jump -- accepted" % (va, what, "/".join(who.get(va, ["?"]))))
        checks += 1
    for vt, off, fn, what in vts:
        got = struct.unpack("<Q", rd(base, defs[vt] + int(off, 16), 8))[0]
        if got != base - IMAGE_VA + defs[fn] and got != defs[fn]:
            fails.append("fl26confgroups: %s is 0x%x, not %s" % (what, got, fn))
        checks += 1
    for cva, cn in cat_writes:
        for name, want, what in sigs:
            va = defs[name]
            if cva < va + len(want) and va < cva + cn:
                fails.append("fl26catlist writes 0x%x..+%d inside fl26confgroups' check of 0x%x [%s]" % (cva, cn, va, what))
        checks += 1
    for f in fails:
        print("FAIL", f)
    assert not fails, "%d byte checks fail on the image the modules before them leave" % len(fails)
    print("test_hook_stack: %d checks OK (fl26catlist %d sites, fl26confgroups %d sites + %d vtable entries, "
          "after %d modules in the pack's order)" % (checks, len(cat), len(sigs), len(vts), names.index(STOP)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
