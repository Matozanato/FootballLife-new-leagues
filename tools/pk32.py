r"""pk32.py [--review]  -> the patches that let a player index past 65535 keep its identity

The player key word (record+0x2c) is 16 bits; the allocator 0x1414bccd0 hands out a u32 index
and its 17 callers store the low word, clamped to 0xffff only from 0x10000 up. Three things
break once the player cap (patchset --player-cap / --fl27) is past 65535:

  1. 0x1414bb350 (id -> index, the only caller 0x1413e3f50) finds the record by id but returns
     its key WORD, which is 0xffff for every index >= 0xfffd: the caller reads "not found" and
     creates the player again.  It now returns the real 32-bit index, -1 when not found, and
     the caller tests eax == -1.
  2. the 17 allocator call sites: indices 0xfffd and 0xfffe kept their own word and divert to
     the second table (`lea eax,[rdx+3]; cmp ax,1; jbe`).  Every index >= 0xfffd now gets 0xffff
     (cmp eax,0xfffc; cmova eax,LIM), same span, nop-padded.
  3. the selected-player global 0x1436f9a60 (setter 0x140e40f90) is fed the key word at
     0x140c7b9fb and 0x140c7ba18; in a Master League a word of 0xffff is record 65535, another
     player.  Both call a 68-byte stub at 0x163a00000 (a VirtualAlloc page, like datecave): a
     word below 0xfffd passes unchanged, otherwise the id at key+4 is resolved through the
     patched 0x1414bb350 and the real index is passed (0xffff when not found).

Design and checks: scratchpad pk32_fixes.md (06.11.), items 1-3.  Every shipped instruction is
checked here against the exe; the new code is assembled with keystone, as in matchid32.py.
1 and 3 rely on the lookup's bound (0x1414bb35f, 0x1414bb396) and the consumer's (0x140b38612)
following the player cap; patchset.py's pk32 step refuses the set when they do not.
"""
import os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))

LOOKUP = 0x1414BB350      # id -> index (mode 2 scan of the career block's players)
LOOKUP_CALLER = 0x1413E4046
ALLOC = 0x1414BCCD0       # next player index, a raw u32
SETTER = 0x140E40F90      # mov [0x1436f9a60], edx; ret
OWNER = 0x143705E10       # the singleton 0x1414b6a60 returns; its +0x48 is the career block
CAVE = 0x163A00000        # its own page (datecave 0x163000000, fl26match 0x161000000)
STUB_LEN = 68
# sites that must already follow the player cap for 1 and 3 to be exact
CAP_SITES = (0x1414BB35F, 0x1414BB396, 0x140B38612)

# 1: (va, shipped instructions, new code, pad byte, why)
LOOKUP_ROWS = [
    (0x1414BB39F, ("mov eax, 0xffff",), "mov eax, 0xffffffff", 0x90,
     "pk32 1: id lookup 0x1414bb350, not found -> 0xffffffff (was 0xffff)"),
    (0x1414BB3A5, ("mov eax, r8d", "imul rcx, rax, 0x17c",
                   "movzx eax, word ptr [rcx + r10 + 0x2c]", "ret"),
     "mov eax, r8d; ret", 0xCC,
     "pk32 1: id lookup 0x1414bb350, found -> the real 32-bit index r8d (was the clamped key word)"),
    (0x1413E404B, ("cmp ax, r14w",), "cmp eax, -1", 0x90,
     "pk32 1: the lookup's only caller tests the 32-bit not-found value, not ax == 0xffff"),
]
# context that is read, never written: the lookup's caller and what it does with the result
LOOKUP_CONTEXT = [
    (LOOKUP_CALLER, "call 0x%x" % LOOKUP),
    (0x1413E404F, "je 0x1413e4073"),
    (0x1414BB35D, "jne 0x1414bb39f"),
]

# 2: call site of ALLOC -> (the span from call+5 to the jbe target as shipped, its new code)
CLAMP_SITES = {
    0x140AF2DC7: ("8b0b448bf0b8ffff00006644897550894d54443bf0760466894550",
                  "mov ecx, dword ptr [rbx]; mov r14d, eax; mov dword ptr [rbp + 0x54], ecx; "
                  "cmp eax, 0xfffc; mov eax, 0xffff; cmovbe eax, r14d; mov word ptr [rbp + 0x50], ax"),
    0x141264EC4: ("66894424288b4c2424894c242c413bc67606664489742428",
                  "mov ecx, dword ptr [rsp + 0x24]; mov dword ptr [rsp + 0x2c], ecx; "
                  "cmp eax, 0xfffc; cmova eax, r14d; mov word ptr [rsp + 0x28], ax"),
    0x141265537: ("6689442450895c2454b9ffff00003bc1760566894c2450",
                  "mov dword ptr [rsp + 0x54], ebx; mov ecx, 0xffff; "
                  "cmp eax, 0xfffc; cmova eax, ecx; mov word ptr [rsp + 0x50], ax"),
    0x141267982: ("66894424208b4c2434894c24243bc3760566895c2420",
                  "mov ecx, dword ptr [rsp + 0x34]; mov dword ptr [rsp + 0x24], ecx; "
                  "cmp eax, 0xfffc; cmova eax, ebx; mov word ptr [rsp + 0x20], ax"),
    0x141267BB2: ("66894424208b4c2434894c2424413bc67606664489742420",
                  "mov ecx, dword ptr [rsp + 0x34]; mov dword ptr [rsp + 0x24], ecx; "
                  "cmp eax, 0xfffc; cmova eax, r14d; mov word ptr [rsp + 0x20], ax"),
    0x141267DE2: ("66894424208b4c2434894c2424413bc67606664489742420",
                  "mov ecx, dword ptr [rsp + 0x34]; mov dword ptr [rsp + 0x24], ecx; "
                  "cmp eax, 0xfffc; cmova eax, r14d; mov word ptr [rsp + 0x20], ax"),
    0x141268012: ("66894424208b4c2434894c2424413bc67606664489742420",
                  "mov ecx, dword ptr [rsp + 0x34]; mov dword ptr [rsp + 0x24], ecx; "
                  "cmp eax, 0xfffc; cmova eax, r14d; mov word ptr [rsp + 0x20], ax"),
    0x14126830F: ("66894424308b4c244c894c2434b9ffff00003bc1760566894c2430",
                  "mov ecx, dword ptr [rsp + 0x4c]; mov dword ptr [rsp + 0x34], ecx; mov ecx, 0xffff; "
                  "cmp eax, 0xfffc; cmova eax, ecx; mov word ptr [rsp + 0x30], ax"),
    0x14126861F: ("66894424308b4c244c894c2434b9ffff00003bc1760566894c2430",
                  "mov ecx, dword ptr [rsp + 0x4c]; mov dword ptr [rsp + 0x34], ecx; mov ecx, 0xffff; "
                  "cmp eax, 0xfffc; cmova eax, ecx; mov word ptr [rsp + 0x30], ax"),
    0x14126C452: ("66894424408b4c2438894c2444b9ffff00003bc1760566894c2440",
                  "mov ecx, dword ptr [rsp + 0x38]; mov dword ptr [rsp + 0x44], ecx; mov ecx, 0xffff; "
                  "cmp eax, 0xfffc; cmova eax, ecx; mov word ptr [rsp + 0x40], ax"),
    0x14126C6EF: ("6689442438c744243cba0000803bc7760566897c2438",
                  "mov dword ptr [rsp + 0x3c], 0x800000ba; "
                  "cmp eax, 0xfffc; cmova eax, edi; mov word ptr [rsp + 0x38], ax"),
    0x14126D0F2: ("66894424588b4c244c894c245cb9ffff00003bc1760566894c2458",
                  "mov ecx, dword ptr [rsp + 0x4c]; mov dword ptr [rsp + 0x5c], ecx; mov ecx, 0xffff; "
                  "cmp eax, 0xfffc; cmova eax, ecx; mov word ptr [rsp + 0x58], ax"),
    0x14126D742: ("66894424588b4c243c894c245cb9ffff00003bc1760566894c2458",
                  "mov ecx, dword ptr [rsp + 0x3c]; mov dword ptr [rsp + 0x5c], ecx; mov ecx, 0xffff; "
                  "cmp eax, 0xfffc; cmova eax, ecx; mov word ptr [rsp + 0x58], ax"),
    0x14126DD73: ("66894424588b4c243c894c245cb9ffff00003bc1760566894c2458",
                  "mov ecx, dword ptr [rsp + 0x3c]; mov dword ptr [rsp + 0x5c], ecx; mov ecx, 0xffff; "
                  "cmp eax, 0xfffc; cmova eax, ecx; mov word ptr [rsp + 0x58], ax"),
    0x14126E452: ("66894424588b4c246c894c245cb9ffff00003bc1760566894c2458",
                  "mov ecx, dword ptr [rsp + 0x6c]; mov dword ptr [rsp + 0x5c], ecx; mov ecx, 0xffff; "
                  "cmp eax, 0xfffc; cmova eax, ecx; mov word ptr [rsp + 0x58], ax"),
    0x14126EDE2: ("66894424408b4c2438894c24443bc7760566897c2440",
                  "mov ecx, dword ptr [rsp + 0x38]; mov dword ptr [rsp + 0x44], ecx; "
                  "cmp eax, 0xfffc; cmova eax, edi; mov word ptr [rsp + 0x40], ax"),
    0x1413E40E2: ("66894424508b4f24894c2454413bc67606664489742450",
                  "mov ecx, dword ptr [rdi + 0x24]; mov dword ptr [rsp + 0x54], ecx; "
                  "cmp eax, 0xfffc; cmova eax, r14d; mov word ptr [rsp + 0x50], ax"),
}

# 3: the two feeds of the setter that pass the key word
FEEDS = (0x140C7B9FB, 0x140C7BA18)
FEED_OLD = "movzx edx, word ptr [rsp + 0x28]"


def _ks():
    import keystone
    return keystone.Ks(keystone.KS_ARCH_X86, keystone.KS_MODE_64)


def _md():
    from capstone import Cs, CS_ARCH_X86, CS_MODE_64
    return Cs(CS_ARCH_X86, CS_MODE_64)


def text(ins):
    return ("%s %s" % (ins.mnemonic, ins.op_str)).strip()


def stub():
    """the 68-byte stub at CAVE, laid out as in pk32_fixes.md (key at [rsp+0x30] on entry)"""
    ks = _ks()
    code = bytearray()

    def emit(s):
        code.extend(ks.asm(s, CAVE + len(code))[0])

    def jcc(op):
        at = len(code)
        code.extend(bytes([op, 0]))
        return at

    emit("movzx edx, word ptr [rsp + 0x30]")       # the key word, as the site did
    emit("cmp edx, 0xfffd")
    jb = jcc(0x72)                                 # below 0xfffd: bit-identical to today
    emit("push rcx")
    emit("push rdx")                               # entry = 8 mod 16 -> aligned after the sub
    emit("sub rsp, 0x28")
    code.extend(b"\x48\x8b\x05" + struct.pack("<i", OWNER - (CAVE + len(code) + 7)))
    emit("test rax, rax")
    je1 = jcc(0x74)
    emit("mov rcx, qword ptr [rax + 0x48]")        # the career block
    emit("test rcx, rcx")
    je2 = jcc(0x74)
    emit("mov edx, dword ptr [rsp + 0x6c]")        # the id, key+4
    emit("xor r8d, r8d")
    code.extend(b"\xe8" + struct.pack("<i", LOOKUP - (CAVE + len(code) + 5)))
    emit("cmp eax, -1")
    je3 = jcc(0x74)
    emit("mov dword ptr [rsp + 0x28], eax")        # into the pushed rdx
    restore = len(code)
    emit("add rsp, 0x28")
    emit("pop rdx")
    emit("pop rcx")
    done = len(code)
    code.append(0xC3)
    for j, t in ((jb, done), (je1, restore), (je2, restore), (je3, restore)):
        code[j + 1] = t - (j + 2)
    code = bytes(code)
    if len(code) != STUB_LEN:
        raise SystemExit("pk32 stub is %d bytes, not %d" % (len(code), STUB_LEN))
    # read it back: the two absolute targets the design depends on
    md = _md()
    md.detail = True
    seen = {}
    n = 0
    for ins in md.disasm(code, CAVE):
        n += ins.size
        if ins.mnemonic == "call":
            seen["call"] = ins.operands[0].imm
        if ins.mnemonic == "mov" and "rip" in ins.op_str:
            seen["owner"] = ins.address + ins.size + ins.operands[1].mem.disp
    if n != len(code) or seen != {"call": LOOKUP, "owner": OWNER}:
        raise SystemExit("pk32 stub does not decode back as built: %r" % seen)
    return code


def patches(read, in_code=None):
    """-> patchset-style patches.  read(va, n) gives the shipped bytes of the code section;
    in_code(va) says whether va is in it (the cave is not)."""
    ks, md = _ks(), _md()
    md.detail = True
    out = []

    def one(va):
        return next(md.disasm(read(va, 16), va))

    def shipped(va, wants):
        old, at = b"", va
        for want in wants:
            ins = one(at)
            if text(ins) != want:
                raise SystemExit("pk32 0x%x: %r, not %r -- another exe?" % (at, text(ins), want))
            old += bytes(ins.bytes)
            at += ins.size
        return old

    for va, want in LOOKUP_CONTEXT:
        shipped(va, (want,))
    # 1
    for va, wants, new_text, pad, why in LOOKUP_ROWS:
        old = shipped(va, wants)
        new = bytes(ks.asm(new_text, va)[0])
        if len(new) > len(old):
            raise SystemExit("pk32 0x%x: %s is %d bytes longer" % (va, new_text, len(new) - len(old)))
        new += bytes([pad]) * (len(old) - len(new))
        out.append({"va": "0x%x" % va, "old": old.hex(), "new": new.hex(), "why": why,
                    "asm": new_text})
    # 2
    for site, (old_hex, new_text) in sorted(CLAMP_SITES.items()):
        call = one(site)
        if text(call) != "call 0x%x" % ALLOC:
            raise SystemExit("pk32 0x%x: %r, not the allocator call" % (site, text(call)))
        start = site + call.size
        old = bytes.fromhex(old_hex)
        if read(start, len(old)) != old:
            raise SystemExit("pk32 0x%x: the clamp span is not as shipped: %s"
                             % (start, read(start, len(old)).hex()))
        end = start + len(old)
        # the span is exactly call+5 .. the jbe target, and decodes whole
        ins = list(md.disasm(old, start))
        if sum(i.size for i in ins) != len(old) or not any(
            i.mnemonic == "jbe" and i.operands[0].imm == end for i in ins
        ):
            raise SystemExit("pk32 0x%x: the span does not end at its jbe target" % start)
        new = bytes(ks.asm(new_text, start)[0])
        if len(new) > len(old):
            raise SystemExit("pk32 0x%x: the clamp is %d bytes longer" % (start, len(new) - len(old)))
        new += b"\x90" * (len(old) - len(new))
        out.append({"va": "0x%x" % start, "old": old.hex(), "new": new.hex(),
                    "why": "pk32 2: allocator call 0x%x, index >= 0xfffd -> key word 0xffff "
                           "(cmp eax,0xfffc; cmova)" % site,
                    "asm": new_text})
    # 3
    if in_code is not None and in_code(CAVE):
        raise SystemExit("pk32: the cave 0x%x is inside the image" % CAVE)
    out.append({"va": "0x%x" % CAVE, "old": bytes(STUB_LEN).hex(), "new": stub().hex(),
                "why": "pk32 3: selected-player stub: word < 0xfffd -> word; else the id at key+4 "
                       "through 0x1414bb350 (pk32 1) -> the real index; not found -> 0xffff",
                "asm": "code cave"})
    for va in FEEDS:
        old = shipped(va, (FEED_OLD,))
        nxt = va + len(old)
        # the setter follows (at 0x140c7ba18 after `mov rcx, rdi`), so rax and r8..r10 are dead
        for _ in range(2):
            ins = one(nxt)
            if text(ins) == "call 0x%x" % SETTER:
                break
            nxt += ins.size
        else:
            raise SystemExit("pk32 0x%x: the setter call does not follow" % va)
        new = b"\xe8" + struct.pack("<i", CAVE - (va + 5))
        out.append({"va": "0x%x" % va, "old": old.hex(), "new": new.hex(),
                    "why": "pk32 3: selected-player feed: movzx edx, word [rsp+0x28] -> call the stub",
                    "asm": "call 0x%x" % CAVE})
    return out


def main(argv):
    sys.path.insert(0, HERE)
    import calwiden
    exe = calwiden.Exe()
    ps = patches(exe.read)
    print("%d patches" % len(ps))
    if "--review" in argv:
        for p in ps:
            print("  %s  %s -> %s  %s" % (p["va"], p["old"], p["new"], p["why"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
