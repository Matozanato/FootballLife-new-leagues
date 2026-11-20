r"""cidwide.py [--review]  -> the patches that let a competition id go past 255 (up to 1023)

The competition id (cid) is one byte in the three pesdb tables and in ~33 instructions that
read it before the game copies it into the live regulation record (+0x80, a dword from there
on).  This step gives the id a high byte in each table and makes those instructions read both:

    Competition.bin            low +5    high +7
    CompetitionRegulation.bin  low +8    high +0x910   (byte 0x53 of name slot 19: a name in
                                                         that slot must stay <= 82 bytes)
    CompetitionEntry.bin       low +8    high +0xb

All three high bytes are zero in the shipped pesdb and in every world Mod Studio has built, and
the exe never read them before this step, so a world whose ids are all below 256 runs exactly as
without it.  The census entry sort key is repacked from cid<<8 | (order-1) to cid<<6 | (order-1):
the order must stay below 64 (shipped max 44) and the id below 1024.

Sites (research: notes/cid-limit-istrazivanje.md, prototype 79d9234 on branch cid-wide,
re-checked against FL27 1.00 for this step):
  census 0x1414f1480      Competition id -> map key (dword), map walk/hint compares, the entry
                          sort key, the regulation sort key, regulation -> competition (2 loops)
  map helpers             std::map<uchar,row*> node ctors 0x1414e36f0 / 0x1414e3830, find
                          0x1414ede90, insert 0x1414e52f0: key byte -> dword (each has exactly
                          one caller, all inside the census -- checked when this was written)
  builder 0x1414f7e80     the full id into the live record +0x80 (setter 0x1419221f0), the
                          previous regulation of the same competition, which entries belong to
                          a regulation, the special ids 111/117/119/125 on the full id
  Select Team 0x1414f6e20 its own entry sort key and the entry id it groups by
  EDIT 0x141eee1c0 / 0x141eefe50  regulation, Competition row and entry by id

The caves sit on their own page CAVE (VirtualAlloc'd by fl26caps.lua through PAGES, like the
date stub and pk32's): one SLOT per cave, each the replaced instructions' new form, the original
conditional exit when it had one, and a jmp back.  Every shipped instruction is checked against
the exe here and again by fl26caps.lua at run time (all or nothing).
"""
import os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))

CAVE = 0x163E00000        # its own page (datecave 0x163000000, slots 0x163400000, regs1200
SLOT = 0x40               # 0x163800000, pk32 0x163a00000, slot7 0x163c00000)
CID_LIMIT = 1024          # the repacked entry key holds 10 bits of id
ORDER_LIMIT = 64          # ... and 6 bits of order - 1

# functions whose only callers must be inside the census for the map change to be exact
MAP_HELPERS = {0x1414E36F0: (0x1414F1554,), 0x1414E3830: (0x1414EDF17,),
               0x1414EDE90: (0x1414F1D8B, 0x1414F1EA1), 0x1414E52F0: (0x1414EDF30, 0x1414F156D)}

# in place: same length, nothing moves -- (va, shipped, new, why)
INPLACE = [
    (0x1414F1518, "384820", "394820", "census map walk: cmp [rax+0x20],ecx"),
    (0x1414F1534, "3a4b20", "3b4b20", "census map hint: cmp ecx,[rbx+0x20] (not 39: reversed)"),
    (0x1414E3722, "0fb611", "8b1190", "map node ctor A: mov edx,[rcx]"),
    (0x1414E3725, "418811", "418911", "map node ctor A: mov [r9],edx"),
    (0x1414E3862, "0fb611", "8b1190", "map node ctor B: mov edx,[rcx]"),
    (0x1414E3865, "418811", "418911", "map node ctor B: mov [r9],edx"),
    (0x1414EDEB6, "410fb610", "418b1090", "map find: mov edx,[r8]"),
    (0x1414EDEC0, "41385120", "41395120", "map find: cmp [r9+0x20],edx"),
    (0x1414EDEDE, "0fb64320", "8b432090", "map find: mov eax,[rbx+0x20]"),
    (0x1414EDEE2, "413800", "413900", "map find: cmp [r8],eax"),
    (0x1414E5341, "410fb64020", "418b402090", "map insert: mov eax,[r8+0x20]"),
    (0x1414E5346, "413801", "413901", "map insert: cmp [r9],eax"),
    (0x1414E5380, "410fb602", "418b0290", "map insert: mov eax,[r10]"),
    (0x1414E5384, "41384120", "41394120", "map insert: cmp [r9+0x20],eax"),
    (0x1414E53B3, "410fb631", "418b3190", "map insert: mov esi,[r9]"),
    (0x1414E53B7, "41387020", "41397020", "map insert: cmp [r8+0x20],esi"),
    (0x1414E542D, "41387120", "41397120", "map insert: cmp [r9+0x20],esi"),
    (0x1414E5478, "41387020", "41397020", "map insert: cmp [r8+0x20],esi"),
    (0x1414E54DB, "413a7120", "413b7120", "map insert: cmp esi,[r9+0x20]"),
    (0x1414F8335, "4080ed6f4080fd0e", "83ed6f83fd0e9090",
     "builder: special ids 111/117/119/125 on the full id (sub ebp,0x6f; cmp ebp,0xe)"),
]

# caves: (site, shipped bytes, body, keeps the site's jcc?, why).  The site's bytes are whole
# instructions; when the last one is a jcc, the cave ends with the same jcc to the same target.
CAVES = [
    (0x1414F1500, "0fb64f05884d68",
     "movzx ecx, byte ptr [rdi+7]; shl ecx, 8; mov cl, byte ptr [rdi+5]; mov dword ptr [rbp+0x68], ecx",
     "census: Competition id = +5 | +7<<8, map key stored as a dword"),
    (0x1414F1609, "0fb60f66ffc90fb647ff66c1e008660bc866894c2448",
     "movzx ecx, byte ptr [rdi]; dec cx; movzx eax, byte ptr [rdi+2]; shl eax, 8; "
     "mov al, byte ptr [rdi-1]; shl ax, 6; or cx, ax; mov word ptr [rsp+0x48], cx",
     "census: entry sort key cid<<6|(order-1), high byte +0xb; rdx is live and not touched"),
    (0x1414F1879, "410fb64424f8c1e014",
     "movzx eax, byte ptr [r12+0x900]; shl eax, 8; mov al, byte ptr [r12-8]; shl eax, 0x14",
     "census: regulation sort key cid<<20, high byte +0x910"),
    (0x1414F1D6A, "0fb64808884d68",
     "movzx ecx, byte ptr [rax+0x910]; shl ecx, 8; mov cl, byte ptr [rax+8]; mov dword ptr [rbp+0x68], ecx",
     "census: regulation -> competition map key (loop 1)"),
    (0x1414F1E5A, "0fb64808884d68",
     "movzx ecx, byte ptr [rax+0x910]; shl ecx, 8; mov cl, byte ptr [rax+8]; mov dword ptr [rbp+0x68], ecx",
     "census: regulation -> competition map key (loop 2)"),
    (0x1414F7EC2, "0fb668088bd5",
     "movzx ebp, byte ptr [rax+0x910]; shl ebp, 8; mov bpl, byte ptr [rax+8]; mov edx, ebp",
     "builder: the full id into the live record +0x80 (setter 0x1419221f0)"),
    (0x1414F7F0D, "403a68087537",
     "movzx ecx, byte ptr [rax+0x910]; shl ecx, 8; mov cl, byte ptr [rax+8]; cmp ebp, ecx",
     "builder: the previous regulation of the same competition"),
    (0x1414F7F63, "403a68087518",
     "movzx ecx, byte ptr [rax+0xb]; shl ecx, 8; mov cl, byte ptr [rax+8]; cmp ebp, ecx",
     "builder: which entries (clubs) belong to the regulation"),
    (0x1414F7348, "410fb60e66ffc9410fb646ff66c1e008660bc866894def",
     "movzx ecx, byte ptr [r14]; dec cx; movzx eax, byte ptr [r14+2]; shl eax, 8; "
     "mov al, byte ptr [r14-1]; shl ax, 6; or cx, ax; mov word ptr [rbp-0x11], cx",
     "Select Team: entry sort key cid<<6|(order-1)"),
    (0x1414F7533, "440fb67008",
     "movzx r14d, byte ptr [rax+0xb]; shl r14d, 8; mov r14b, byte ptr [rax+8]",
     "Select Team: the entry id it groups by (then cmp r14w,cx: 16 bits)"),
    (0x141EEE27C, "0fb650088b4d77",
     "movzx edx, byte ptr [rax+8]; movzx ecx, byte ptr [rax+0x910]; shl ecx, 8; or edx, ecx; "
     "mov ecx, dword ptr [rbp+0x77]",
     "EDIT: regulation by competition id"),
    (0x141EEE594, "0fb648053b4d77",
     "movzx ecx, byte ptr [rax+7]; shl ecx, 8; mov cl, byte ptr [rax+5]; cmp ecx, dword ptr [rbp+0x77]",
     "EDIT: Competition row by id"),
    (0x141EEFFE0, "410fb67e083b3b",
     "movzx edi, byte ptr [r14+0xb]; shl edi, 8; mov dil, byte ptr [r14+8]; cmp edi, dword ptr [rbx]",
     "EDIT: entry against the static id list"),
]


def _ks():
    import keystone
    return keystone.Ks(keystone.KS_ARCH_X86, keystone.KS_MODE_64)


def _md():
    from capstone import Cs, CS_ARCH_X86, CS_MODE_64
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    md.detail = True
    return md


def body_bytes(body):
    """a cave body assembled position independent (no jumps, calls or rip)"""
    md = _md()
    b = bytes(_ks().asm(body, 0)[0])
    n = 0
    for i in md.disasm(b, 0):
        n += i.size
        if i.mnemonic.startswith("j") or i.mnemonic == "call" or "rip" in i.op_str:
            raise SystemExit("cidwide: cave body %r is not position independent" % body)
    if n != len(b):
        raise SystemExit("cidwide: cave body %r does not decode back" % body)
    return b


def site_tail(va, orig):
    """the site's shipped instructions -> (next va, (jcc opcode byte, target) or None)"""
    md = _md()
    ins = list(md.disasm(orig, va))
    if sum(i.size for i in ins) != len(orig):
        raise SystemExit("cidwide 0x%x: the shipped bytes do not decode to whole instructions" % va)
    last = ins[-1]
    jcc = None
    if last.mnemonic.startswith("j"):
        if last.size != 2 or last.mnemonic not in ("je", "jne"):
            raise SystemExit("cidwide 0x%x: unexpected exit %s" % (va, last.mnemonic))
        jcc = (last.mnemonic, last.operands[0].imm)
    return va + len(orig), jcc


def cave_code(i):
    """the i-th cave, assembled at its address on the page"""
    va, orig, body, why = CAVES[i]
    at = CAVE + i * SLOT
    nxt, jcc = site_tail(va, bytes.fromhex(orig))
    code = bytearray(body_bytes(body))
    ks = _ks()
    if jcc:
        code += bytes(ks.asm("%s 0x%x" % jcc, at + len(code))[0])
    code += bytes(ks.asm("jmp 0x%x" % nxt, at + len(code))[0])
    if len(code) > SLOT:
        raise SystemExit("cidwide 0x%x: cave is %d bytes, the slot %d" % (va, len(code), SLOT))
    # read back: the exits go where the site went
    md = _md()
    exits = [(x.mnemonic, x.operands[0].imm) for x in md.disasm(bytes(code), at)
             if x.mnemonic.startswith("j")]
    want = ([jcc] if jcc else []) + [("jmp", nxt)]
    if exits != want:
        raise SystemExit("cidwide 0x%x: cave exits %r, expected %r" % (va, exits, want))
    return at, bytes(code)


def page_bytes():
    out = bytearray()
    for i in range(len(CAVES)):
        _, code = cave_code(i)
        out += code + b"\xcc" * (SLOT - len(code))
    return bytes(out)


def patches(read, in_code=None, calls_to=None):
    """-> patchset-style patches.  read(va, n): the shipped bytes; in_code(va): va is in the
    image (the cave must not be); calls_to(fn): the direct callers of fn, to check the map
    helpers are the census's alone (skipped when None)"""
    out = []
    md = _md()
    if calls_to is not None:
        for fn, want in MAP_HELPERS.items():
            got = tuple(sorted(calls_to(fn)))
            if got != tuple(sorted(want)):
                raise SystemExit("cidwide: 0x%x is called from %s, not only the census's %s"
                                 % (fn, ", ".join("0x%x" % a for a in got),
                                    ", ".join("0x%x" % a for a in want)))
    for va, orig, new, why in INPLACE:
        o, n = bytes.fromhex(orig), bytes.fromhex(new)
        got = read(va, len(o))
        if got != o:
            raise SystemExit("cidwide 0x%x: %s, not %s -- another exe?" % (va, got.hex(), orig))
        if len(o) != len(n):
            raise SystemExit("cidwide 0x%x: in-place bytes change length" % va)
        oi, ni = list(md.disasm(o, va)), list(md.disasm(n, va))
        if sum(i.size for i in oi) != len(o) or sum(i.size for i in ni) != len(n):
            raise SystemExit("cidwide 0x%x: not whole instructions" % va)
        out.append({"va": "0x%x" % va, "old": orig, "new": new, "why": "cidwide: " + why,
                    "asm": "; ".join("%s %s" % (i.mnemonic, i.op_str) for i in ni)})
    if in_code is not None and in_code(CAVE):
        raise SystemExit("cidwide: the cave 0x%x is inside the image" % CAVE)
    ks = _ks()
    for i, (va, orig, body, why) in enumerate(CAVES):
        o = bytes.fromhex(orig)
        got = read(va, len(o))
        if got != o:
            raise SystemExit("cidwide 0x%x: %s, not %s -- another exe?" % (va, got.hex(), orig))
        if len(o) < 5:
            raise SystemExit("cidwide 0x%x: the site is shorter than a jmp" % va)
        at, _ = cave_code(i)
        j = bytes(ks.asm("jmp 0x%x" % at, va)[0])
        if len(j) != 5:
            raise SystemExit("cidwide 0x%x: the cave 0x%x is out of rel32 reach" % (va, at))
        out.append({"va": "0x%x" % va, "old": orig, "new": (j + b"\x90" * (len(o) - 5)).hex(),
                    "why": "cidwide: %s -> cave 0x%x" % (why, at), "asm": "jmp 0x%x" % at})
    pg = page_bytes()
    out.append({"va": "0x%x" % CAVE, "old": bytes(len(pg)).hex(), "new": pg.hex(),
                "why": "cidwide: %d caves, 0x%x bytes each (competition ids up to %d)"
                       % (len(CAVES), SLOT, CID_LIMIT - 1),
                "asm": "code caves"})
    return out


def main(argv):
    sys.path.insert(0, HERE)
    import calwiden
    exe = calwiden.Exe()
    ps = patches(exe.read)
    print("%d patches (%d in place, %d caves at 0x%x)" % (len(ps), len(INPLACE), len(CAVES), CAVE))
    if "--review" in argv:
        for p in ps:
            print("  %s  %s -> %s  %s" % (p["va"], p["old"][:40], p["new"][:40], p["why"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
