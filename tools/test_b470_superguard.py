"""python tools/test_b470_superguard.py

B470 (FL Testovi, GigaPack beta 3, season 2, 17.11.): the UEFA Super Cup was never played after
the first summer, and fl26superguard's exit from its setup (0x1413604a0) was silent. The exit now
goes through a stub that counts which entry was missing (Champions League 4 / Europa League 6)
before the function's epilogue, and the module logs every skip. This checks, offline:

  - the bytes: the trampoline's exit jumps to the stub, the stub counts into 0x14252eef4 /
    0x14252eef8 and ends in the same jmp to the epilogue (0x141360b0a) the old exit had; stub and
    counters fit between fl26seasonend's guard (its end read from fl26seasonend.lua), its flag
    byte 0x14252eef0 and fl26ctlguard (0x14252ef00);
  - the module (run in Lua through lupa, when installed, with Sider's memory/log/ctx mocked):
    with no ffi it writes the old plain exit and counts nothing; with ffi it makes the cave page
    RWX, writes the counting exit and the stub, registers livecpk_make_key, and logs a skip of
    the UCL entry, of the UEL entry and of both (an empty vector) as the counters move.
"""
import os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "sider", "experimental", "fl26superguard.lua")
SEASONEND = os.path.join(HERE, "..", "sider", "experimental", "fl26seasonend.lua")
EPILOGUE = 0x141360b0a
N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def const(s, name):
    m = re.search(r'local %s\s*=\s*(0x[0-9a-f]+|"[0-9a-f]+")' % name, s)
    v = m.group(1)
    return int(v, 16) if v.startswith("0x") else v.strip('"')


def check_bytes(s):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_64
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    plain, count = const(s, "TRAMP_PLAIN"), const(s, "TRAMP_COUNT")
    stub_va, stub, cnt = const(s, "STUB_VA"), const(s, "STUB"), const(s, "CNT_VA")
    ok("the counting trampoline differs from the plain one only in its exit jmp",
       plain[:-10] == count[:-10] and len(plain) == len(count))
    ins = list(md.disasm(bytes.fromhex(count), 0x14252ee20))
    ok("capstone decodes the whole trampoline", sum(len(i.bytes) for i in ins) == len(count) // 2)
    ok("its exit jumps to the stub", ins[-1].mnemonic == "jmp" and int(ins[-1].op_str, 16) == stub_va)
    pins = list(md.disasm(bytes.fromhex(plain), 0x14252ee20))
    ok("the plain exit still jumps to the epilogue", int(pins[-1].op_str, 16) == EPILOGUE)
    ok("both je of the trampoline go to the exit", all(int(i.op_str, 16) == ins[-1].address
                                                     for i in ins if i.mnemonic == "je"))
    sins = list(md.disasm(bytes.fromhex(stub), stub_va))
    ok("capstone decodes the whole stub", sum(len(i.bytes) for i in sins) == len(stub) // 2)
    text = [(i.mnemonic, i.op_str) for i in sins]
    ok("the stub tests r8d (UCL entry) first, ebx (UEL entry) second",
       text[0] == ("cmp", "r8d, -1") and text[3] == ("cmp", "ebx, -1"))
    incs = [i for i in sins if i.mnemonic == "inc"]
    tg = [i.address + i.size + struct.unpack_from("<i", i.bytes, 2)[0] for i in incs]
    ok("it counts the UCL miss at CNT_VA and the UEL miss at CNT_VA+4", tg == [cnt, cnt + 4])
    ok("each jne skips exactly its inc", all(int(sins[k].op_str, 16) == sins[k + 2].address for k in (1, 4)))
    ok("it ends in the jmp to the epilogue", sins[-1].mnemonic == "jmp" and int(sins[-1].op_str, 16) == EPILOGUE)
    se = open(SEASONEND, encoding="utf-8").read()
    ends = [int(va, 16) + len(new) // 2 for va, new in re.findall(r'va=0x(14252e[0-9a-f]+), old="[0-9a-f]*", new="([0-9a-f]*)"', se)]
    ok("the stub starts after fl26seasonend's guard (ends 0x%x)" % max(ends), stub_va >= max(ends))
    ok("the stub ends before fl26seasonend's flag byte 0x14252eef0", stub_va + len(stub) // 2 <= 0x14252eef0)
    ok("the counters sit after the flag and before fl26ctlguard", cnt > 0x14252eef0 and cnt + 8 <= 0x14252ef00)


def run_lua(with_ffi, taken=None):
    try:
        from lupa import luajit21 as lupa   # Sider's Lua is LuaJIT
    except ImportError:
        import lupa
    L = lupa.LuaRuntime(unpack_returned_tuples=True, encoding=None)
    mem, logs, reg, prot = {}, [], {}, []

    def read(va, n):
        return bytes(mem.get(va + i, 0) for i in range(int(n)))

    def write(va, b):
        b = b if isinstance(b, bytes) else str(b).encode("latin-1")
        for i, c in enumerate(b):
            mem[va + i] = c

    # the shipped bytes at the patched site in the exe
    write(0x14136059a, bytes.fromhex("4b8d044048c1e004"))
    if taken:
        write(taken, bytes([0xcc]))
    g = L.globals()
    g.py_read = read
    g.py_write = write
    g.py_log = lambda s: logs.append(s.decode("utf-8") if isinstance(s, bytes) else str(s))
    g.py_reg = lambda ev, fn: reg.__setitem__(ev.decode() if isinstance(ev, bytes) else str(ev), fn)
    g.py_prot = lambda va, n, p: (prot.append((int(va), int(n), int(p))), 1)[1]
    L.execute("""
      memory = { read = function(va, n) return py_read(va, n) end,
                 write = function(va, s) py_write(va, s) end,
                 unpack = function(fmt, s) local a, b, c, d = s:byte(1, 4) return a + b * 256 + c * 65536 + d * 16777216 end }
      log = function(s) py_log(s) end
    """)
    if with_ffi:
        L.execute("""
          ffi = { cdef = function(s) end, new = function(t) return {0} end, cast = function(t, v) return v end,
                  C = { fl26superguard_VirtualProtect = function(va, n, p, old) return py_prot(va, n, p) end } }
        """)
    else:
        L.execute("ffi = nil")
    src = open(SRC, encoding="utf-8").read()
    m = L.execute(src.encode("utf-8"))
    ctx = L.eval("function(f) return { register = function(ev, fn) f(ev, fn) end } end")(g.py_reg)
    m.init(ctx)
    return mem, logs, reg, prot, read, write, ctx


def check_lua(s):
    try:
        import lupa  # noqa: F401
    except ImportError:
        print("lupa not installed: the module run is skipped")
        return
    stub_va, stub, cnt = const(s, "STUB_VA"), const(s, "STUB"), const(s, "CNT_VA")
    mem, logs, reg, prot, read, write, ctx = run_lua(False)
    ok("no ffi: all patches applied", any("applied all 2 patches" in l for l in logs))
    ok("no ffi: the plain exit is written", read(0x14252ee20, 29).hex() == const(s, "TRAMP_PLAIN"))
    ok("no ffi: no stub, nothing registered", read(stub_va, 28) == bytes(28) and not reg)
    ok("no ffi: it says the skips are not counted", any("not counted" in l for l in logs))
    mem, logs, reg, prot, read, write, ctx = run_lua(True)
    ok("ffi: the cave page is made PAGE_EXECUTE_READWRITE", prot == [(0x14252e000, 0x1000, 0x40)])
    ok("ffi: all 4 patches applied", any("applied all 4 patches" in l and "each skip is logged" in l for l in logs))
    ok("ffi: the counting exit and the stub are written",
       read(0x14252ee20, 29).hex() == const(s, "TRAMP_COUNT") and read(stub_va, len(stub) // 2).hex() == stub)
    ok("ffi: the site jumps into the trampoline", read(0x14136059a, 8).hex() == "e981e81c01909090")
    ok("ffi: livecpk_make_key registered", "livecpk_make_key" in reg)
    mk = reg["livecpk_make_key"]

    def tick(n=64):
        for _ in range(n):
            mk(ctx, b"x")
    before = len(logs)
    tick()
    ok("no skip, nothing logged", len(logs) == before)
    write(cnt, struct.pack("<I", 1)); tick()
    ok("a UCL skip is logged", "Champions League entry (4) missing" in logs[-1] and "UCL missing 1" in logs[-1])
    write(cnt + 4, struct.pack("<I", 1)); tick()
    ok("a UEL skip is logged", "Europa League entry (6) missing" in logs[-1] and "UEL missing 1" in logs[-1])
    write(cnt, struct.pack("<II", 2, 2)); tick()
    ok("both at once: an empty entry vector", "entry vector is empty" in logs[-1])
    n = len(logs); tick()
    ok("counters still: no repeat", len(logs) == n)
    # the stub's cave taken by something else: the old plain exit, nothing counted
    mem, logs, reg, prot, read, write, ctx = run_lua(True, taken=stub_va + 5)
    ok("stub area taken: the plain exit, no make_key", read(0x14252ee20, 29).hex() == const(s, "TRAMP_PLAIN") and not reg)
    ok("stub area taken: logged", any("is not free" in l for l in logs))


def main():
    s = open(SRC, encoding="utf-8").read()
    try:
        import capstone  # noqa: F401
    except ImportError:
        print("capstone not installed: the byte checks are skipped")
    else:
        check_bytes(s)
    check_lua(s)
    print("%d cases passed" % N)


if __name__ == "__main__":
    main()
