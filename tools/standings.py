r"""standings.py [--review] [T] [N]  -> the patches that grow the standings pool and its header

The standings object ([[0x143705e10] + 0x78], allocated at 0x1414b62cb, 0x3a2ef0 bytes) starts
with a header of 100 competition entries of 0xb4 and then 600 phase tables of 0x187c; a member
at +0x39a8f0 and 154 sites that reach the tail after it make in-place growth a bad trade.  So
the pool moves to the top of a grown object instead -- the old end, 0x3a2ef0 -- and the tail
stays where it is:

    +0x000000   header, N entries of 0xb4               (N = 1024: 0x2d000 bytes)
    +0x02d000   unused: the old pool area
    +0x39a5f0   0x300 bytes, the members from +0x39a8f0 on, the tail to 0x3a2ef0 (unchanged)
    +0x3a2ef0   T phase tables of 0x187c                (T = 2400: up to 0x11fb970)

Design: scratchpad standings600.md section 3 (06.11.).  What this writes:

  * the 13 header bounds `cmp r32, 0x64; jb rel8` -> trampolines with `cmp r32, N` (the same
    redirect fl26hdr255 makes, hdr127.bound_trampoline), the header initialiser's count
    (0x1414fd4e3) and the copier's header pair count (0x1413fb0d4, two entries a pass);
  * the 6 table-base sites (disp32/imm32) and the folded `+0x314` state byte at 0x14159edca;
  * the 8 table-count sites (`0x258`, imm32) outside the copier;
  * the object's allocation and memset size (0x1414b62cb, 0x1414b62e5);
  * the copier 0x1413fb0b0, shared by copy A (Master League), copy B (Cup/League Mode) and copy
    S (Cup save).  It copies from the same offsets on both sides, so its table walk
    (`lea rbx, [rcx + 0x5ec6]; mov ebp, 0x258` at 0x1413fb1fa) goes to a cave that maps: the
    live object's tables at TOP, a copy's at the compact base right behind the header (CB =
    N * 0xb4), and the count is T for copy A and what fits in the 0x39a8f0 slot for B and S.
    Copy A is told apart by a flag byte that a two-instruction stub sets on its way to the
    copier -- the copy A calls at 0x141401aff (load, A -> live) and 0x1414020ae (save, live
    -> A) call the stub instead.  The flag is read and cleared on every pass through the cave,
    so it never outlives the call that set it;
  * copy A's slot (+0xcaf24c) grows to CB + T * 0x187c: that is a region of patchset's mlcopy
    (slot_growth() here), which moves every copy A field above it.

These are exactly the sites fl26hdr255.lua patches (plus the size, the copier cave and the
copy A stubs), so a set with this step replaces fl26hdr255; its FL 2027 copy
(sider/experimental/fl26hdr255.fl27.lua) sees the widened header and stands down.

The new code is assembled with keystone and read back with capstone; every shipped instruction
is checked against the exe before a byte is planned.  Nothing here touches the game.
"""
import os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hdr127

OWNER = 0x143705E10          # the singleton 0x1414b6a60 returns; +0x78 is the standings object
OBJ_SIZE_OLD = 0x3A2EF0      # its allocation (and memset) size
TOP = OBJ_SIZE_OLD           # the new table base: the old end, 16-aligned
STRIDE = 0x187C
COUNT_OLD = 0x258
BASE_OLD = 0x4650            # 100 * 0xb4
HDR = 0xB4
HDR_OLD = 100
SLOT = 0x39A8F0              # every copy slot's length (A, B, S)
SLOT_TABLES_END = 0x39A5F0   # what the copier may fill in a slot: the 0x300 after it is not copied
COPY_A = 0xCAF24C            # copy A's slot field (layout.json copy.mlcopy.fields)
COPY_A_NEXT = 0x1049B3C      # the copy A field after it
COPIER = 0x1413FB0B0
CAVE = 0x163B00000           # its own page (pk32 0x163a00000, datecave 0x163000000)
CAVE_STUB_A = CAVE + 0x100
CAVE_FLAG = CAVE + 0x1F0
CAVE_HDR = CAVE + 0x200      # the 13 header trampolines
DEFAULT_T, DEFAULT_N = 2400, 1024

# (instruction va, shipped text, the immediate/displacement it carries)
COUNT_SITES = [
    (0x1414FD476, "mov edi, 0x258"),       # table constructor loop 0x1414fd460
    (0x14158DF83, "cmp eax, 0x258"),
    (0x14158F381, "cmp ebx, 0x258"),       # allocator 0x14158f350: first free table
    (0x14158F3B0, "cmp ebx, 0x258"),
    (0x14158F8D2, "cmp eax, 0x258"),       # release 0x14158f870 (July rotation)
    (0x14158FE38, "cmp r14d, 0x258"),      # slot builder 0x14158fd90
    (0x141590254, "cmp edi, 0x258"),
    (0x14159EDB3, "cmp ecx, 0x258"),
]
BASE_SITES = [
    (0x1414FD46F, "lea rbx, [rcx + 0x4650]", 0),
    (0x14158DF91, "lea rax, [r10 + 0x4650]", 0),
    (0x14158F39A, "lea rdi, [rax + 0x4650]", 0),
    (0x14158F8E0, "lea rbx, [r14 + 0x4650]", 0),
    (0x14158FE4C, "lea rbx, [r9 + 0x4650]", 0),
    (0x14159026B, "add r15, 0x4650", 0),
    (0x14159EDCA, "cmp byte ptr [rcx + 0x4964], sil", 0x314),   # base + a table's state byte
]
SIZE_SITES = [
    (0x1414B62CB, "mov edx, 0x3a2ef0"),    # the allocation
    (0x1414B62E5, "mov r8d, 0x3a2ef0"),    # its memset
]
HDR_INIT = (0x1414FD4E3, "mov r9d, 0x64")  # the header initialiser stamps N entries free
HDR_PAIRS = (0x1413FB0D4, "mov r9d, 0x32") # the copier moves the header two entries a pass
COPIER_WALK = 0x1413FB1FA
COPIER_WALK_OLD = ("lea rbx, [rcx + 0x5ec6]", "mov ebp, 0x258")
COPIER_LOOP = 0x1413FB210                  # the table loop's head, right after a 10-byte nop
COPY_A_CALLS = (0x141401AFF, 0x1414020AE)  # load (A -> live), save (live -> A)
OTHER_CALLS = (0x1413FECCA, 0x1413FF116, 0x1413FC7B3, 0x1413FCB73)   # B and S, unchanged
# context read, never written: the table loop the cave returns to
LOOP_CONTEXT = [
    (0x1413FB206, "nop word ptr [rax + rax]"),
    (COPIER_LOOP, "movzx eax, word ptr [rdi + rbx - 0x1876]"),
    (0x1413FB2BE, "add rbx, 0x187c"),
    (0x1413FB2C5, "sub rbp, 1"),
]


def _ks():
    import keystone
    return keystone.Ks(keystone.KS_ARCH_X86, keystone.KS_MODE_64)


def _md():
    from capstone import Cs, CS_ARCH_X86, CS_MODE_64
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    md.detail = True
    return md


def text(ins):
    return ("%s %s" % (ins.mnemonic, ins.op_str)).strip()


def compact_base(n):
    return (n * HDR + 15) & ~15


def slot_tables(n):
    """how many tables a 0x39a8f0 slot (copies B and S) holds behind an n-entry header"""
    return (SLOT_TABLES_END - compact_base(n)) // STRIDE


def slot_growth(t, n):
    """how far copy A's slot grows: CB + T tables, rounded to 0x40 (every copy A field above it
    keeps its alignment)"""
    need = compact_base(n) + t * STRIDE
    return max(0, (need - SLOT + 0x3F) & ~0x3F)


def check(t, n):
    if n % 2 or not HDR_OLD < n <= 4096:
        raise SystemExit("standings: header %d -- an even number above 100 (the copier moves two a pass)" % n)
    if not COUNT_OLD <= t <= 0x7FFF:
        raise SystemExit("standings: %d tables -- 600 .. 32767" % t)
    if slot_tables(n) < 64:
        raise SystemExit("standings: a %d-entry header leaves copies B and S %d tables" % (n, slot_tables(n)))
    if TOP + t * STRIDE >= 0x7FFFFFFF:
        raise SystemExit("standings: %d tables do not fit a 32-bit size" % t)


def cave(t, n):
    """the copier's table walk: rcx = dst, rdi = src - dst; returns to COPIER_LOOP with rbx =
    dst + base_dst + 0x1876, rdi = (src + base_src) - (dst + base_dst), ebp = the count"""
    cb, nb = compact_base(n), slot_tables(n)
    src = """
        mov rdx, %(flag)#x
        movzx eax, byte ptr [rdx]
        mov byte ptr [rdx], 0
        mov ebp, %(nb)d
        mov edx, %(t)d
        test eax, eax
        cmovne ebp, edx
        mov rax, %(owner)#x
        mov rax, qword ptr [rax]
        test rax, rax
        je compact
        mov rax, qword ptr [rax + 0x78]
        test rax, rax
        je compact
        cmp rax, rcx
        je dst_live
        lea rdx, [rcx + rdi]
        cmp rax, rdx
        je src_live
    compact:
        lea rbx, [rcx + %(cbf)#x]
        jmp %(back)#x
    dst_live:
        lea rbx, [rcx + %(topf)#x]
        add rdi, %(down)d
        jmp %(back)#x
    src_live:
        lea rbx, [rcx + %(cbf)#x]
        add rdi, %(up)d
        jmp %(back)#x
    """ % dict(flag=CAVE_FLAG, nb=nb, t=t, owner=OWNER, cbf=cb + 0x1876, topf=TOP + 0x1876,
               down=cb - TOP, up=TOP - cb, back=COPIER_LOOP)
    code = bytes(_ks().asm(src, CAVE)[0])
    if CAVE + len(code) > CAVE_STUB_A:
        raise SystemExit("standings: the copier cave is %d bytes" % len(code))
    # read back: the three exits land on the loop, the constants are the ones planned
    md = _md()
    seen, n_bytes = {"back": 0, "flag": 0, "owner": 0, "lea": set(), "add": set()}, 0
    for ins in md.disasm(code, CAVE):
        n_bytes += ins.size
        if ins.mnemonic == "jmp" and ins.operands[0].imm == COPIER_LOOP:
            seen["back"] += 1
        if ins.mnemonic in ("mov", "movabs") and ins.operands[1].type == 2:
            v = ins.operands[1].imm
            seen["flag"] += v == CAVE_FLAG
            seen["owner"] += v == OWNER
        if ins.mnemonic == "lea" and ins.operands[0].reg and "rbx" in ins.op_str:
            seen["lea"].add(ins.operands[1].mem.disp)
        if ins.mnemonic == "add" and ins.op_str.startswith("rdi"):
            seen["add"].add(ins.operands[1].imm)
    want = {"back": 3, "flag": 1, "owner": 1, "lea": {cb + 0x1876, TOP + 0x1876},
            "add": {cb - TOP, TOP - cb}}
    if n_bytes != len(code) or seen != want:
        raise SystemExit("standings: the copier cave does not decode as built: %r" % seen)
    return code


def stub_a():
    """copy A's way into the copier: set the flag, then the copier itself (its ret goes back to
    the caller).  r10 is volatile and no argument."""
    code = bytes(_ks().asm("mov r10, %#x; mov byte ptr [r10], 1; jmp %#x" % (CAVE_FLAG, COPIER),
                           CAVE_STUB_A)[0])
    ins = list(_md().disasm(code, CAVE_STUB_A))
    if sum(i.size for i in ins) != len(code) or ins[-1].mnemonic != "jmp" \
            or ins[-1].operands[0].imm != COPIER or ins[0].operands[1].imm != CAVE_FLAG:
        raise SystemExit("standings: the copy A stub does not decode as built")
    return code


def patches(read, t=DEFAULT_T, n=DEFAULT_N, in_code=None):
    """-> patchset-style patches.  read(va, k) gives the shipped bytes of the code section."""
    check(t, n)
    md = _md()
    out = []
    cb = compact_base(n)

    def one(va):
        return next(md.disasm(read(va, 16), va))

    def shipped(va, want):
        ins = one(va)
        if text(ins) != want:
            raise SystemExit("standings 0x%x: %r, not %r -- another exe?" % (va, text(ins), want))
        return ins

    def field(va, want, old, new, why):
        ins = shipped(va, want)
        b = bytes(ins.bytes)
        raw = struct.pack("<I", old)
        k = b.rfind(raw)
        if k < 0 or b.find(raw) != k or k + 4 != len(b):
            raise SystemExit("standings 0x%x: %#x is not the tail field of %s" % (va, old, b.hex()))
        nb = b[:k] + struct.pack("<I", new) + b[k + 4:]
        out.append({"va": "0x%x" % va, "old": b.hex(), "new": nb.hex(), "why": why,
                    "asm": text(ins)})

    for va, want in LOOP_CONTEXT:
        shipped(va, want)
    for va in COPY_A_CALLS + OTHER_CALLS:
        shipped(va, "call 0x%x" % COPIER)
    if in_code is not None and in_code(CAVE):
        raise SystemExit("standings: the cave 0x%x is inside the image" % CAVE)

    # the caves first: the applier writes in order, and a jump must not exist before its code
    code = cave(t, n)
    out.append({"va": "0x%x" % CAVE, "old": bytes(len(code)).hex(), "new": code.hex(),
                "why": "standings: copier table walk -- live tables at +0x%x, a copy's at +0x%x; "
                       "%d for copy A, %d for copies B and S" % (TOP, cb, t, slot_tables(n)),
                "asm": "code cave"})
    sa = stub_a()
    out.append({"va": "0x%x" % CAVE_STUB_A, "old": bytes(len(sa)).hex(), "new": sa.hex(),
                "why": "standings: copy A stub -- flag byte at 0x%x, then the copier 0x%x"
                       % (CAVE_FLAG, COPIER), "asm": "code cave"})
    # the header bounds: the same trampolines fl26hdr255 builds, on our page.  hdr127 decodes
    # the pair from a whole-file image, so it gets one
    img, secs = _image(read)
    at = CAVE_HDR
    jumps = []
    for va in hdr127.BOUNDS:
        stub, jump, used = hdr127.bound_trampoline(img, secs, va, n, at)
        out.append({"va": "0x%x" % stub[0], "old": stub[1], "new": stub[2],
                    "why": "standings: " + stub[3], "asm": "code cave"})
        jumps.append({"va": "0x%x" % jump[0], "old": jump[1], "new": jump[2],
                      "why": "standings: " + jump[3], "asm": "jmp 0x%x" % at})
        at += (used + 3) & ~3
    if at > CAVE + 0x1000:
        raise SystemExit("standings: the header trampolines run past the page")
    out += jumps
    field(HDR_INIT[0], HDR_INIT[1], HDR_OLD, n,
          "standings: header initialiser count %d -> %d entries stamped free" % (HDR_OLD, n))
    field(HDR_PAIRS[0], HDR_PAIRS[1], HDR_OLD // 2, n // 2,
          "standings: copier header pairs %d -> %d (two entries a pass)" % (HDR_OLD // 2, n // 2))
    for va, want, add in BASE_SITES:
        field(va, want, BASE_OLD + add, TOP + add,
              "standings: table base%s 0x%x -> 0x%x" % (" + 0x%x" % add if add else "",
                                                         BASE_OLD + add, TOP + add))
    for va, want in COUNT_SITES:
        field(va, want, COUNT_OLD, t, "standings: table count %d -> %d" % (COUNT_OLD, t))
    size_new = TOP + t * STRIDE
    for va, want in SIZE_SITES:
        field(va, want, OBJ_SIZE_OLD, size_new,
              "standings: object size 0x%x -> 0x%x (%d tables at +0x%x)" % (OBJ_SIZE_OLD, size_new, t, TOP))
    # the copier's walk -> the cave
    old, va = b"", COPIER_WALK
    for want in COPIER_WALK_OLD:
        ins = shipped(va, want)
        old += bytes(ins.bytes)
        va += ins.size
    if va != 0x1413FB206:
        raise SystemExit("standings: the copier walk ends at 0x%x" % va)
    new = b"\xe9" + struct.pack("<i", CAVE - (COPIER_WALK + 5)) + b"\xcc" * (len(old) - 5)
    out.append({"va": "0x%x" % COPIER_WALK, "old": old.hex(), "new": new.hex(),
                "why": "standings: copier 0x%x table walk -> the cave at 0x%x" % (COPIER, CAVE),
                "asm": "jmp 0x%x" % CAVE})
    for va in COPY_A_CALLS:
        ins = one(va)
        new = b"\xe8" + struct.pack("<i", CAVE_STUB_A - (va + 5))
        out.append({"va": "0x%x" % va, "old": bytes(ins.bytes).hex(), "new": new.hex(),
                    "why": "standings: copy A %s -> the copy A stub at 0x%x"
                           % ("load (A -> live)" if va == COPY_A_CALLS[0] else "save (live -> A)",
                              CAVE_STUB_A),
                    "asm": "call 0x%x" % CAVE_STUB_A})
    return out


def _image(read):
    """a minimal file image of .trace for hdr127's decoders: (bytes, sections)"""
    base, size = 0x140001000, 0x252D800
    data = read(base, size)
    return data, [(base, size, 0, len(data), ".trace")]


def info(t, n):
    return {"tables": t, "header": n, "table_base": "0x%x" % TOP,
            "copy_base": "0x%x" % compact_base(n), "copy_bs_tables": slot_tables(n),
            "object_size": "0x%x" % (TOP + t * STRIDE),
            "copy_a_slot_growth": "0x%x" % slot_growth(t, n), "cave": "0x%x" % CAVE}


def main(argv):
    import calwiden
    a = [x for x in argv[1:] if not x.startswith("--")]
    t = int(a[0]) if a else DEFAULT_T
    n = int(a[1]) if len(a) > 1 else DEFAULT_N
    exe = calwiden.Exe()
    ps = patches(exe.read, t, n)
    print("%d patches; %r" % (len(ps), info(t, n)))
    if "--review" in argv:
        for p in ps:
            print("  %s  %s -> %s  %s" % (p["va"], p["old"], p["new"], p["why"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
