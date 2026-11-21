r"""python tools/test_cidwide.py -- competition ids past 255: the cidwide step and Mod Studio.

1. The caps set's cidwide step (cidwide.py): every cave body runs in unicorn on fake rows with
   ids 0, 44, 255, 256, 300, 556 and 1023 -- the id comes out whole, the entry sort keys stay
   ordered by (id, order), the registers the shipped code still needs are not touched, the
   compares give the right answer, the in-place bytes decode to the intended dword instructions
   and the special ids 111/117/119/125 are recognised on the full id only. With FL26_EXE set (or
   the game where flpaths finds it) the patches are also built against that exe.
2. Mod Studio: the accessors read the high bytes (Competition +7, Regulation +0x910, Entry +0xb),
   the setters refuse ids past 255 unless the game's set has the step and leave every byte of a
   narrow world as it was, slot 19's name keeps the high byte, mkworld's pool and CID_MAX follow
   set_cid_wide, leaguebuilder.cid_wide reads the Set: line of the caps module, and buildcheck's
   check 6 catches an id past 1023, an order past 63 and a slot-19 name over the high byte.
No game is started; nothing outside a temporary folder is written.
"""
import os, shutil, struct, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from capstone import CS_ARCH_X86, CS_MODE_64, Cs
from unicorn import UC_ARCH_X86, UC_MODE_64, Uc
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBP, UC_X86_REG_ECX, UC_X86_REG_EDX,
                               UC_X86_REG_EFLAGS, UC_X86_REG_R8, UC_X86_REG_R12, UC_X86_REG_R14,
                               UC_X86_REG_RAX, UC_X86_REG_RBP, UC_X86_REG_RBX, UC_X86_REG_RDI,
                               UC_X86_REG_RDX, UC_X86_REG_RSP)
import cidwide as CW

N = 0
FAIL = []


def ok(name, cond):
    global N
    if not cond:
        FAIL.append(name)
        print("not ok - %s" % name)
        return
    N += 1
    print("ok %d - %s" % (N, name))


CODE, ROW, STK = 0x100000, 0x200000, 0x300000
cs = Cs(CS_ARCH_X86, CS_MODE_64)
BODY = {c[0]: CW.body_bytes(c[2]) for c in CW.CAVES}


def run(va, regs, row=b"", stack=b""):
    uc = Uc(UC_ARCH_X86, UC_MODE_64)
    for base in (CODE, ROW, STK):
        uc.mem_map(base, 0x10000)
    body = BODY[va]
    uc.mem_write(CODE, body)
    uc.mem_write(ROW, row.ljust(0x1000, b"\0"))
    uc.mem_write(STK, stack.ljust(0x1000, b"\0"))
    for r, v in regs.items():
        uc.reg_write(r, v)
    uc.emu_start(CODE, CODE + len(body))
    return uc


def zf(uc):
    return bool(uc.reg_read(UC_X86_REG_EFLAGS) & 0x40)


def rd(uc, addr, n):
    return int.from_bytes(uc.mem_read(addr, n), "little")


def row_with(size, **f):
    b = bytearray(size)
    for off, v in f.items():
        b[int(off[1:], 16)] = v
    return bytes(b)


def caves():
    bad = []

    def check(name, got, want):
        if got != want:
            bad.append("%s: got %r, want %r" % (name, got, want))

    ids = [0, 44, 255, 256, 300, 556, 1023]
    for cid in ids:
        lo, hi = cid & 0xff, cid >> 8
        uc = run(0x1414F1500, {UC_X86_REG_RDI: ROW, UC_X86_REG_RBP: STK},
                 row_with(36, x5=lo, x7=hi, x6=0xa5, x4=0x27))
        check("census comp %d" % cid, rd(uc, STK + 0x68, 4), cid)
        reg = row_with(0x930, x8=lo, x910=hi, x9=0x5a)
        uc = run(0x1414F1879, {UC_X86_REG_R12: ROW + 0x10}, reg)
        check("reg sort %d" % cid, uc.reg_read(UC_X86_REG_EAX), cid << 20)
        for va in (0x1414F1D6A, 0x1414F1E5A):
            uc = run(va, {UC_X86_REG_RAX: ROW, UC_X86_REG_RBP: STK}, reg)
            check("reg->comp %x %d" % (va, cid), rd(uc, STK + 0x68, 4), cid)
        uc = run(0x1414F7EC2, {UC_X86_REG_RAX: ROW}, reg)
        check("builder ebp %d" % cid, uc.reg_read(UC_X86_REG_EBP), cid)
        check("builder edx %d" % cid, uc.reg_read(UC_X86_REG_EDX), cid)
        for other in ids:
            r2 = row_with(0x930, x8=other & 0xff, x910=other >> 8)
            uc = run(0x1414F7F0D, {UC_X86_REG_RAX: ROW, UC_X86_REG_EBP: cid}, r2)
            check("builder prev %d/%d" % (cid, other), zf(uc), cid == other)
            e2 = row_with(12, x8=other & 0xff, xb=other >> 8, xa=1)
            uc = run(0x1414F7F63, {UC_X86_REG_RAX: ROW, UC_X86_REG_EBP: cid}, e2)
            check("builder entry %d/%d" % (cid, other), zf(uc), cid == other)
            check("builder entry keeps rax", uc.reg_read(UC_X86_REG_RAX), ROW)
            uc = run(0x141EEE594, {UC_X86_REG_RAX: ROW, UC_X86_REG_RBP: STK},
                     row_with(36, x5=other & 0xff, x7=other >> 8), (b"\0" * 0x77) + cid.to_bytes(4, "little"))
            check("edit comp %d/%d" % (cid, other), zf(uc), cid == other)
            uc = run(0x141EEFFE0, {UC_X86_REG_R14: ROW, UC_X86_REG_RBX: STK},
                     row_with(12, x8=other & 0xff, xb=other >> 8), cid.to_bytes(4, "little"))
            check("edit entry %d/%d" % (cid, other), zf(uc), cid == other)
        uc = run(0x141EEE27C, {UC_X86_REG_RAX: ROW, UC_X86_REG_RBP: STK}, reg,
                 (b"\0" * 0x77) + (777).to_bytes(4, "little"))
        check("edit reg edx %d" % cid, uc.reg_read(UC_X86_REG_EDX), cid)
        check("edit reg ecx %d" % cid, uc.reg_read(UC_X86_REG_ECX), 777)
        uc = run(0x1414F7533, {UC_X86_REG_RAX: ROW}, row_with(12, x8=lo, xb=hi, xa=3))
        check("select team r14 %d" % cid, uc.reg_read(UC_X86_REG_R14), cid)
    keys = []
    for cid in ids:
        for order in (1, 2, 44, 63):
            e = row_with(12, x8=cid & 0xff, x9=order, xb=cid >> 8, xa=0x11)
            uc = run(0x1414F1609, {UC_X86_REG_RDI: ROW + 9, UC_X86_REG_RSP: STK,
                                   UC_X86_REG_RDX: 0xdeadbeefcafe, UC_X86_REG_R8: 0x1234}, e)
            k = rd(uc, STK + 0x48, 2)
            check("census pack %d/%d" % (cid, order), k, (cid << 6) | (order - 1))
            check("census pack keeps rdx", uc.reg_read(UC_X86_REG_RDX), 0xdeadbeefcafe)
            check("census pack keeps rdi", uc.reg_read(UC_X86_REG_RDI), ROW + 9)
            uc2 = run(0x1414F7348, {UC_X86_REG_R14: ROW + 9, UC_X86_REG_RBP: STK + 0x100,
                                    UC_X86_REG_RDX: 0x55, UC_X86_REG_RDI: 0x66}, e)
            check("select pack %d/%d" % (cid, order), rd(uc2, STK + 0x100 - 0x11, 2), k)
            check("select pack keeps rdx", uc2.reg_read(UC_X86_REG_RDX), 0x55)
            check("select pack keeps rdi", uc2.reg_read(UC_X86_REG_RDI), 0x66)
            keys.append(k)
    if keys != sorted(keys) or len(set(keys)) != len(keys):
        bad.append("entry sort keys are not strictly ordered by (id, order)")
    return bad


WANT = {
    0x1414F1518: "cmp dword ptr [rax + 0x20], ecx", 0x1414F1534: "cmp ecx, dword ptr [rbx + 0x20]",
    0x1414E3722: "mov edx, dword ptr [rcx]", 0x1414E3725: "mov dword ptr [r9], edx",
    0x1414E3862: "mov edx, dword ptr [rcx]", 0x1414E3865: "mov dword ptr [r9], edx",
    0x1414EDEB6: "mov edx, dword ptr [r8]", 0x1414EDEC0: "cmp dword ptr [r9 + 0x20], edx",
    0x1414EDEDE: "mov eax, dword ptr [rbx + 0x20]", 0x1414EDEE2: "cmp dword ptr [r8], eax",
    0x1414E5341: "mov eax, dword ptr [r8 + 0x20]", 0x1414E5346: "cmp dword ptr [r9], eax",
    0x1414E5380: "mov eax, dword ptr [r10]", 0x1414E5384: "cmp dword ptr [r9 + 0x20], eax",
    0x1414E53B3: "mov esi, dword ptr [r9]", 0x1414E53B7: "cmp dword ptr [r8 + 0x20], esi",
    0x1414E542D: "cmp dword ptr [r9 + 0x20], esi", 0x1414E5478: "cmp dword ptr [r8 + 0x20], esi",
    0x1414E54DB: "cmp esi, dword ptr [r9 + 0x20]", 0x1414F8335: "sub ebp, 0x6f",
}


def in_place():
    bad = []
    for va, orig, new, _ in CW.INPLACE:
        o = next(cs.disasm(bytes.fromhex(orig), va))
        n = next(cs.disasm(bytes.fromhex(new), va))
        if "%s %s" % (n.mnemonic, n.op_str) != WANT[va]:
            bad.append("0x%x decodes to %s %s" % (va, n.mnemonic, n.op_str))
        if o.mnemonic.replace("movzx", "mov") != n.mnemonic:
            bad.append("0x%x changes %s into %s" % (va, o.mnemonic, n.mnemonic))
    return bad


def special():
    # 0x1414f8335..0x1414f8353 as patched: 111/117/119/125 -> edx 2, anything else -> edx 1
    code = bytes.fromhex("83ed6f83fd0e9090" "770f" "b941410000" "ba02000000" "0fa3e9" "7205" "ba01000000")
    bad = []
    for cid in (0, 44, 110, 111, 117, 119, 125, 126, 255, 256, 367, 373, 381, 637, 1023):
        uc = Uc(UC_ARCH_X86, UC_MODE_64)
        uc.mem_map(CODE, 0x10000)
        uc.mem_write(CODE, code)
        uc.reg_write(UC_X86_REG_EBP, cid)
        uc.emu_start(CODE, CODE + len(code))
        if uc.reg_read(UC_X86_REG_EDX) != (2 if cid in (111, 117, 119, 125) else 1):
            bad.append("special %d" % cid)
    return bad


def against_exe():
    """the patches built against the exe, when there is one (FL26_EXE or flpaths' default)"""
    import flpaths
    if not os.path.isfile(flpaths.EXE):
        print("# no exe at %s: the patches are not built against one (set FL26_EXE)" % flpaths.EXE)
        return
    import callindex, datecave
    d, secname, sva, ro, rsz = callindex.code_section()
    read = lambda va, n: d[ro + va - sva:ro + va - sva + n]
    ps = CW.patches(read, in_code=lambda va: va < datecave.IMAGE_END)
    ok("cidwide builds against %s: %d patches" % (flpaths.EXE, len(ps)),
       len(ps) == len(CW.INPLACE) + len(CW.CAVES) + 1)
    page = [p for p in ps if int(p["va"], 16) == CW.CAVE]
    ok("one patch on the cave page, %d caves of 0x%x" % (len(CW.CAVES), CW.SLOT),
       len(page) == 1 and len(page[0]["new"]) // 2 == len(CW.CAVES) * CW.SLOT)
    # every site jumps to its own slot, and the slot jumps back right after the site
    for i, (va, orig, *_r) in enumerate(CW.CAVES):
        at = CW.CAVE + i * CW.SLOT
        j = next(cs.disasm(bytes.fromhex(next(p["new"] for p in ps if int(p["va"], 16) == va)), va))
        code = bytes.fromhex(page[0]["new"])[i * CW.SLOT:(i + 1) * CW.SLOT]
        exits = [x.op_str for x in cs.disasm(code, at) if x.mnemonic == "jmp"]
        if j.op_str != "0x%x" % at or "0x%x" % (va + len(orig) // 2) not in exits[:1]:
            FAIL.append("cave 0x%x: site jumps to %s, cave exits %s" % (va, j.op_str, exits))
    ok("every site jumps to its slot and every slot back past its site", not [f for f in FAIL if f.startswith("cave ")])
    try:
        CW.patches(lambda va, n: b"\0" * n)
        ok("another exe is refused", False)
    except SystemExit as e:
        ok("another exe is refused (%s)" % str(e)[:50], "another exe" in str(e))


def modstudio():
    import mkleague as M
    import mkworld as W
    import leaguebuilder as B
    import buildcheck
    # readers: the high byte counts, a narrow row reads as before
    c = bytearray(M.COMP); g = bytearray(M.REG); e = bytearray(M.ENT)
    c[M.CID_OFF], g[M.R_CID], e[M.E_CID] = 44, 44, 44
    ok("narrow rows read their byte", (M.comp_cid(c), M.reg_cid(g), M.ent_cid(e)) == (44, 44, 44))
    c[M.CID_HI], g[M.R_CID_HI], e[M.E_CID_HI] = 1, 2, 3
    ok("the high bytes count", (M.comp_cid(c), M.reg_cid(g), M.ent_cid(e)) == (300, 556, 812))
    ok("+0x910 is byte 0x53 of name slot 19", M.R_CID_HI - M.name_at(M.NAME_SLOTS - 1) == 0x53)
    # setters: narrow refuses past 255 and leaves the high byte alone
    W.set_cid_wide(False)
    ok("narrow: CID_MAX 255, pool ends at 255", W.CID_MAX == 255 and max(W.cid_pool()) == 255)
    g2 = bytearray(M.REG); g2[M.R_CID_HI] = 0x5a           # a byte that is not ours to touch
    M.set_reg_cid(g2, 200)
    ok("narrow: a set id below 256 writes the low byte only", g2[M.R_CID] == 200 and g2[M.R_CID_HI] == 0x5a)
    try:
        M.set_comp_cid(bytearray(M.COMP), 300)
        ok("narrow: id 300 is refused", False)
    except ValueError as x:
        ok("narrow: id 300 is refused (%s)" % str(x)[:40], "cidwide" in str(x))
    # wide: up to 1023, high byte written (and cleared on a row copied from a wide one)
    W.set_cid_wide(True)
    try:
        ok("wide: CID_MAX 1023, the pool starts as before", W.CID_MAX == 1023 and M.CID_WIDE
           and W.cid_pool()[:126] == list(range(130, 256)) and max(W.cid_pool()) == 1023)
        for setter, getter, n in ((M.set_comp_cid, M.comp_cid, M.COMP), (M.set_reg_cid, M.reg_cid, M.REG),
                                  (M.set_ent_cid, M.ent_cid, M.ENT)):
            b = bytearray(n)
            setter(b, 1023)
            v1 = getter(b)
            setter(b, 130)
            ok("wide: %s 1023 then 130" % setter.__name__, v1 == 1023 and getter(b) == 130)
        try:
            M.set_ent_cid(bytearray(M.ENT), 1024)
            ok("wide: 1024 is refused", False)
        except ValueError:
            ok("wide: 1024 is refused", True)
        # a rename keeps the high byte; slot 19 stops at 82 bytes
        g3 = bytearray(M.REG)
        M.set_reg_cid(g3, 700)
        M.put_names(g3, 0, "X" * 200)
        ok("wide: put_names keeps the id (700)", M.reg_cid(g3) == 700)
        s19 = g3[M.name_at(19):M.R_CID_HI]
        ok("wide: slot 19 holds 82 bytes and a NUL", s19 == b"X" * 82 + b"\0")
    finally:
        W.set_cid_wide(False)
    g4 = bytearray(M.REG)
    M.put_names(g4, 0, "X" * 200)
    ok("narrow: put_names as before (slot 19 is the whole 0x73 bytes)",
       g4[M.name_at(19):M.name_at(19) + M.NAME_SLOT] == b"X" * (M.NAME_SLOT - 1) + b"\0")

    tmp = tempfile.mkdtemp(prefix="cidwide-")
    try:
        # leaguebuilder.cid_wide: the Set: line of the game's fl26caps.lua (and the pack's copy)
        game = os.path.join(tmp, "Game Folder")
        mods = os.path.join(game, "SiderAddons", "modules")
        os.makedirs(mods)
        open(os.path.join(game, "FL_2027.exe"), "wb").close()
        open(os.path.join(game, "SiderAddons", "sider.ini"), "w").close()
        open(os.path.join(game, "SiderAddons", "sider.dll"), "wb").close()
        lua = os.path.join(mods, "fl26caps.lua")
        old_pack = B.pack_dir
        B.pack_dir = lambda: (_ for _ in ()).throw(B.BuildError("no pack"))
        try:
            ok("no caps module: narrow", not B.cid_wide(game))
            open(lua, "w").write("--[[\nSet:     teams-coaches-regs-players-dates-matches-upper-mlcopy-"
                                 "fixtures-calendar-pk32.fl27.elem4.teams8000\n--]]\n")
            ok("a set without the step: narrow", not B.cid_wide(game))
            open(lua, "w").write("--[[\nSet:     teams-coaches-regs-players-dates-matches-upper-mlcopy-"
                                 "fixtures-calendar-pk32-cidwide.fl27.elem4.teams8000\n--]]\n")
            ok("a set with the step: wide", B.cid_wide(game))
            open(lua, "w").write("--[[\nSet:     teams-coaches-regs-players-dates-matches-upper-mlcopy-"
                                 "fixtures-calendar-pk32-standings-cidwide-regions.fl27.elem4.teams8000\n--]]\n")
            ok("a set with the step and one after it (-regions): wide", B.cid_wide(game))
            open(lua, "w").write("--[[\nSet:     teams-coaches-regs-players-dates-matches-upper-mlcopy-"
                                 "fixtures-calendar-pk32-cidwidex.fl27.elem4.teams8000\n--]]\n")
            ok("a step only named like it: narrow", not B.cid_wide(game))
            open(lua, "w").write("--[[\nSet:     teams-coaches-regs-players-dates-matches-upper-mlcopy-"
                                 "fixtures-calendar-pk32-cidwide.fl27.elem4.teams8000\n--]]\n")
            B.use_game(game)
            ok("use_game makes the process wide", W.CID_MAX == 1023 and M.CID_WIDE)
            pack = os.path.join(tmp, "pack")
            os.makedirs(os.path.join(pack, "modules"))        # the pack's files sit in its modules (install_modules)
            packed = os.path.join(pack, "modules", "fl26caps.fl27.lua")
            B.pack_dir = lambda: pack
            open(packed, "w").write("--[[\nSet:     teams-pk32-cidwide.fl27.elem4\n--]]\n")
            ok("the pack's copy with the step too: wide", B.cid_wide(game))
            open(packed, "w").write("--[[\nSet:     teams-pk32.fl27\n--]]\n")
            ok("the pack's copy without the step (a Build would put it in): narrow", not B.cid_wide(game))
            B.use_game(game)
            ok("use_game makes the process narrow again", W.CID_MAX == 255 and not M.CID_WIDE)
        finally:
            B.pack_dir = old_pack
            W.set_cid_wide(False)

        # buildcheck check 6
        world = os.path.join(tmp, "w")
        os.makedirs(world)
        W.set_cid_wide(True)
        comp, regs, ents = bytearray(), bytearray(), bytearray()
        for cid, rid in ((44, 500), (300, 501)):
            c = bytearray(M.COMP); M.set_comp_cid(c, cid); comp += c
            g = bytearray(M.REG); M.set_reg_cid(g, cid); g[M.R_ID:M.R_ID + 2] = rid.to_bytes(2, "little")
            g[M.R_TYPE] = 4; M.put_names(g, 0, "League %d" % cid); regs += g
            for k in range(2):
                e = bytearray(M.ENT); M.set_ent_cid(e, cid); e[M.E_ORDER] = k + 1
                e[M.E_TEAM:M.E_TEAM + 4] = (1000 + cid * 10 + k).to_bytes(4, "little"); ents += e
        W.set_cid_wide(False)

        def check6(comp, regs, ents):
            import io, contextlib
            import pesdb
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                M.write_tables(world, comp, regs, ents)
            db = os.path.join(world, "common", "etc", "pesdb")
            open(os.path.join(db, "Team.bin"), "wb").write(pesdb.wesys_pack(b""))
            buf = io.StringIO()
            old = sys.argv
            sys.argv = ["buildcheck.py", db]
            try:
                with contextlib.redirect_stdout(buf):
                    try:
                        buildcheck.main()
                    except SystemExit:
                        pass
            finally:
                sys.argv = old
            return next((l for l in buf.getvalue().splitlines() if "check 6" in l), buf.getvalue()[-300:])

        line = check6(comp, regs, ents)
        ok("buildcheck check 6 passes a world with 44 and 300 (%s)" % line, line.startswith("PASS check 6")
           and "1 past 255" in line)
        bad = bytearray(ents); bad[M.E_ORDER] = 64
        ok("check 6: an order of 64 fails", check6(comp, regs, bad).startswith("FAIL check 6"))
        bad = bytearray(regs); bad[M.REG + M.name_at(19):M.REG + M.R_CID_HI] = b"Y" * 0x53
        ok("check 6: a slot-19 name over the high byte fails", check6(comp, bad, ents).startswith("FAIL check 6"))
        bad = bytearray(comp); bad[M.COMP + M.CID_HI] = 4
        ok("check 6: id 1068 fails", check6(bad, regs, ents).startswith("FAIL check 6"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def generators():
    """pesdb's rows (spreadregions, mkflags, mkregioncats read them) and modscan take the high byte"""
    import mkleague as M
    import pesdb, modscan
    c = bytearray(M.COMP); g = bytearray(M.REG)
    wide, M.CID_WIDE = M.CID_WIDE, True
    try:
        M.set_comp_cid(c, 812); M.set_reg_cid(g, 812)
    finally:
        M.CID_WIDE = wide
    ok("pesdb: Competition and Regulation rows read 812",
       pesdb.comp_rows(bytes(c))[0]["id"] == 812 and pesdb.reg_rows(bytes(g))[0]["comp"] == 812)
    e = pesdb.entry_pack(1, 2, 812, 5)
    r = pesdb.entry_rows(e)[0]
    ok("pesdb: an Entry row of 812 keeps its order (5) and reads back", (r["comp"], r["slot"]) == (812, 5)
       and M.ent_cid(e) == 812 and e[M.E_ORDER] == 5)
    ok("pesdb: a narrow Entry row packs as before", pesdb.entry_pack(1, 2, 44, 3) == struct.pack("<III", 1, 2, 44 | 3 << 8))
    ok("modscan: lineups keys on the full id", set(modscan.lineups(e)) == {812})


def main():
    ok("cave bodies on fake rows (ids 0..1023)", not caves() or print("\n".join(caves()[:20])))
    ok("in-place bytes decode to the dword forms", not in_place() or print("\n".join(in_place())))
    ok("special ids 111/117/119/125 on the full id only", not special() or print(special()))
    for i in range(len(CW.CAVES)):
        CW.cave_code(i)
    ok("all %d caves assemble at their slots with the shipped exits" % len(CW.CAVES), True)
    against_exe()
    modstudio()
    generators()
    print("FAIL: %d\n  " % len(FAIL) + "\n  ".join(FAIL) if FAIL else "OK: %d checks" % N)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
