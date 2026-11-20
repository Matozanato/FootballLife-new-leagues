r"""python mkslot7.py [--out fl26slot7.lua]  -> a module that lets a club's league slot be 0..511

A team record keeps its Master League slot at +0x41c.  The game uses bits 0-6 for the slot
and bit 7 for a flag of its own (copied from bit 7 of the regulation's +0x304 when a Master
League is created; edited through field setter 0x141f11c80 / getter 0x141f11570; init sets it
to 1).  Bits 8-31 of the dword are full (+0x41d, +0x41e, two nibbles).  So the 7-bit slot
cannot grow in place: this module moves the flag to bit 0 of +0x41a and the slot's high bits
to +0x41b (the two bytes of padding after the country word +0x418 that nothing in the exe
reads or writes), so the slot is  byte +0x41c | byte +0x41b << 8  -- 9 bits used, 0..511.
123 stays the "no slot" sentinel.

B391 (10.11.2026): the first version gave the slot the byte +0x41c only (0..255).  FL 2027
has 465 slots and the GigaPack puts 149 leagues on 256..464; the Master League writer stored
slot & 0xff, so Taiwan Premier (344) clubs had 88 (Jupiler Pro League) and Team Info listed
them there, the league itself gone from the list.  Hence the high byte.

What changes (every byte read from the exe and verified before anything is written):
  * 32 readers   movzx r, byte [t+0x41c] ; and r, 0x7f  -> jmp to a stub of ours:
                 movzx r, word [t+0x41b] ; rol r16, 8 ; and r, 0x1ff  (r = the 9-bit slot),
                 and a byte compare right after it (cmp al, 0x7b ...) is made a dword compare
                 in the stub, so slot 379 is not taken for 123 nor 329 for 73
  * 10 writers   and [t+0x41c],0xffffff80 ; or [t+0x41c],r  -> store the low byte to +0x41c
                 and the high byte to +0x41b
  * 3 flag sets  btr/bts bit 7 of the dword                  -> mov byte [t+0x41a], flag
  * 2 staged-world writes in 0x141266490 (123 path and the normal path), both bytes
  * the season mover's "no slot" default (mov r15b, 0x7b) is a whole register now, as the
    writers store the whole register
  * flag init 0x1414c5b41, field setter 0x141f12004, getters 0x141eddb4f / 0x141f116af
  * team copy 0x140b158d0: the country word copy becomes a dword copy, so +0x41a/+0x41b travel
  * the six callers of 0x141509c00 ("league slot of competition id", 7 for 123 and >= 128
    with fl26slots250) call our own version: id2slot, 7 only for 123 (or past 511)
  * nothing in the Master League slot choice 0x141263b40: it already takes the first slot
    (lowest first) that carries a LEAGUE-format competition (find_if 0x14125fe50 ->
    comptab rows with that slot -> 0x1414cf750: regulation format in mask 0xf9c2), then
    69/70/73, then the lowest; it returns the slot as a dword.

Native code that reads the slot (fl26chain, fl26join, fl26swiss) tells the layout from the
first reader, 0x140b08f6b: e9 (our jump) = 9 bits in +0x41c/+0x41b, else the byte at
0x140b08f74 (0xff = 8 bits, 0x7f = the game's 7).

Requires fl26slots250 (it is what makes slots >= 124 exist at all).  Without it this module
changes nothing visible: no slot >= 128 is ever produced.
"""
import os
import re
import struct
import sys
import glob

import capstone
import keystone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mkslots as S                                     # sections, offsets, Asm, checks

EXE = S.EXE
SIDER = S.SIDER
NATIVE = os.path.join(HERE, "native")
PAGE = 0x163c00000            # ours; fl26caps 0x163000000, fl26slots 0x163400000
CODE = PAGE
NMAX = 512                    # 9 bits
ID2SLOT = 0x1414cb2e0
TEAMSLOT_FN = 0x141509c00
TEAMSLOT_CALLERS = [0x140ae3de8, 0x140ae44d3, 0x14126275b, 0x141262e8b, 0x14135964b, 0x14135a50b]
# native code reads these two to tell the slot layout (fl26chain/fl26join/fl26swiss)
PROBES = (0x140b08f6b, 0x140b08f74)

READERS = [
    0x140b08f6b, 0x140c6c0b7, 0x140fa306f, 0x140fd2a77, 0x140fd8ea6, 0x141262379, 0x1412628ec,
    0x141262b7c, 0x141324ded, 0x14132a03d, 0x141333964, 0x141354dc9, 0x1413558cd, 0x141358f74,
    0x14135a8c5, 0x14135ae09, 0x14135b175, 0x14135d787, 0x141360372, 0x1413603eb, 0x141361119,
    0x141365906, 0x141365930, 0x14150956c, 0x14150d4e5, 0x14150d51f, 0x141511243, 0x1415191d3,
    0x141527eb7, 0x141541f62, 0x141546a09, 0x141547fe9,
]

FLAG_R15 = ("mov eax, dword ptr [r15 + 0x304]; shr eax, 7; and al, 1; "
            "mov byte ptr [r13 + 0x41a], al")                      # flag of regulation r15
FLAG_RSI = ("mov eax, dword ptr [rsi + 0x304]; shr eax, 7; and al, 1; "
            "mov byte ptr [r13 + 0x41a], al")                      # flag of regulation rsi
# low byte -> +0x41c, high byte -> +0x41b; eax is free at every one of these sites
STORE_EAX_R13 = "mov byte ptr [r13 + 0x41c], al; shr eax, 8; mov byte ptr [r13 + 0x41b], al"

# (va, old bytes, new code (asm, assembled at va, padded with nops), why)
REWRITES = [
    (0x141262760, "4183a51c040000800fb6c083e07f4109851c040000",
     STORE_EAX_R13,
     "user's club: slot (eax) from 0x141509c00 -> +0x41c / +0x41b"),
    (0x1412627df, "4183a4241c040000800fb645ef83e07f410984241c040000",
     "movzx eax, word ptr [rbp - 0x11]; mov byte ptr [r12 + 0x41c], al; shr eax, 8; "
     "mov byte ptr [r12 + 0x41b], al",
     "user's club path: other club gets the saved slot [rbp-0x11] (a dword) -> +0x41c / +0x41b"),
    (0x1412628f5, "4183a51c040000800fb6c04109851c040000",
     STORE_EAX_R13,
     "user's club takes another club's slot (eax, our reader) -> +0x41c / +0x41b"),
    (0x141262930, "418b8704030000c1e807a80175060fbaf207eb040fbaea074189951c040000",
     FLAG_R15,
     "flag of the regulation (+0x304 bit 7) -> +0x41a instead of bit 7 of +0x41c"),
    (0x14126294f, "83a11c040000800fb645ef83e07f09811c040000",
     "movzx eax, word ptr [rbp - 0x11]; mov byte ptr [rcx + 0x41c], al; mov byte ptr [rcx + 0x41b], ah",
     "other club gets the saved slot [rbp-0x11] -> +0x41c / +0x41b"),
    (0x141262b85, "4183a51c040000800fb6c04109851c040000",
     STORE_EAX_R13,
     "user's club takes another club's slot (eax, our reader) -> +0x41c / +0x41b"),
    (0x141262bc0, "8b8604030000c1e807a80175060fbaf207eb040fbaea074189951c040000",
     FLAG_RSI,
     "flag of the regulation (+0x304 bit 7) -> +0x41a instead of bit 7 of +0x41c"),
    (0x141262bde, "83a11c04000080410fb6c783e07f09811c040000",
     "movzx eax, r15w; mov byte ptr [rcx + 0x41c], al; mov byte ptr [rcx + 0x41b], ah",
     "other club gets slot r15 (the user's club's, our reader 0x141262379) -> +0x41c / +0x41b"),
    (0x141262e90, "0fb6c841338d1c04000083e17f41338d1c04000041898d1c040000"
                  "418b8704030000c1e807a80175060fbaf107eb040fbae90741898d1c040000",
     STORE_EAX_R13 + "; " + FLAG_R15,
     "user's club: slot (eax) -> +0x41c / +0x41b, regulation flag -> +0x41a"),
    (0x141262f77, "83a01c040000800fb645ef83e07f09811c040000",
     "movzx eax, word ptr [rbp - 0x11]; mov byte ptr [rcx + 0x41c], al; mov byte ptr [rcx + 0x41b], ah",
     "other club (rax == rcx) gets the saved slot [rbp-0x11] -> +0x41c / +0x41b"),
    (0x1413658e1, "41b77b410fb6ff",
     "push 0x7b; pop r15; mov edi, r15d",
     "season mover: 'no slot' default 123 in the whole of r15 and edi (the writers store them whole)"),
    (0x14136595f, "83a01c04000080400fb6cf09881c040000",
     "mov ecx, edi; mov byte ptr [rax + 0x41c], cl; mov byte ptr [rax + 0x41b], ch",
     "season mover: club takes slot edi -> +0x41c / +0x41b"),
    (0x14136599f, "83a01c04000080410fb6cf09881c040000",
     "mov ecx, r15d; mov byte ptr [rax + 0x41c], cl; mov byte ptr [rax + 0x41b], ch",
     "season mover: club takes slot r15d -> +0x41c / +0x41b"),
    (0x14126655e, "8b856c03000083e0fb83c87b",
     "mov word ptr [rbp + 0x36b], 0x7b00; jmp 0x1412665e1",
     "staged world: no slot -> +0x41c = 123, +0x41b = 0 (skips the dword store at 0x1412665db; "
     "eax is dead past the call at 0x1412665f7)"),
    (0x1412665cb, "0fb6c88b856c03000033c883e17f33c1",
     "mov ecx, dword ptr [rbp + 0x36c]; mov cl, al; mov byte ptr [rbp + 0x36b], ah; mov eax, ecx",
     "staged world: slot (eax) from 0x141263b40 -> byte +0x41c, high byte +0x41b of the staged copy"),
    (0x1414c5b41, "818b1c04000080000000",
     "mov byte ptr [rbx + 0x41a], 1",
     "team init: flag = 1 now in +0x41a (was or [+0x41c],0x80)"),
    (0x141f12004, "81a61c0400007fffffff098e1c040000",
     "shr ecx, 7; mov byte ptr [rsi + 0x41a], cl",
     "edit field setter: flag (ecx = 0x80 or 0) -> +0x41a bit 0"),
    (0x141eddb4f, "8b801c040000c1e8072401",
     "movzx eax, byte ptr [rax + 0x41a]; and al, 1",
     "flag reader: +0x41a bit 0"),
    (0x141f116af, "8b851c040000458bc6c1e8072401",
     "movzx eax, byte ptr [rbp + 0x41a]; mov r8d, r14d; and al, 1",
     "edit field getter: flag from +0x41a bit 0"),
    (0x140b15aa9, "0fb78718040000",
     "mov eax, dword ptr [rdi + 0x418]",
     "team copy: country word +0x418 copied as a dword, so +0x41a (flag) and +0x41b (slot high) travel"),
    (0x140b15ab0, "66898318040000",
     "mov dword ptr [rbx + 0x418], eax",
     "team copy: store the dword +0x418..+0x41b"),
]

KS = keystone.Ks(keystone.KS_ARCH_X86, keystone.KS_MODE_64)
MD = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
B8 = {"eax": "al", "ecx": "cl", "edx": "dl", "ebx": "bl", "ebp": "bpl", "esi": "sil", "edi": "dil",
      "r15d": "r15b", "r14d": "r14b", "r8d": "r8b", "r9d": "r9b"}
W16 = {"eax": "ax", "ecx": "cx", "edx": "dx", "ebx": "bx", "ebp": "bp", "esi": "si", "edi": "di",
       "r15d": "r15w", "r14d": "r14w", "r8d": "r8w", "r9d": "r9w"}
D32 = {v: k for k, v in B8.items()}


def asm(text, at):
    enc, _ = KS.asm(text, at)
    return bytes(enc)


def reader_stub(d, secs, va, at):
    """([site patches], stub bytes, [ranges]) for the reader at va, the stub placed at `at`."""
    o = S.offset_of(secs, va)
    ins = list(MD.disasm(d[o:o + 48], va))[:3]
    first, mask = ins[0], ins[1]
    m = re.fullmatch(r"(\w+), byte ptr \[(\w+) \+ 0x41c\]", first.op_str)
    if first.mnemonic != "movzx" or not m:
        raise SystemExit("0x%x: %s %s is not a movzx of byte +0x41c" % (va, first.mnemonic, first.op_str))
    dst, base = m.groups()
    code = ["movzx %s, word ptr [%s + 0x41b]" % (dst, base), "rol %s, 8" % W16[dst],
            "and %s, 0x1ff" % dst]

    def is_mask(i):
        r = i.op_str.split(",")[0].strip()
        return i.mnemonic == "and" and i.op_str.endswith("0x7f") and r in (dst, B8.get(dst))
    if not is_mask(mask):
        # 0x141511243: movzx ecx ; lea rdx,[rip+..] ; and ecx,0x7f -- the stub takes the load
        # only, and the `and` further down becomes a nop (the stub has masked already)
        if is_mask(ins[2]) and dst not in ins[1].op_str and B8[dst] not in ins[1].op_str:
            code.append("jmp 0x%x" % (first.address + first.size))
            stub = asm("; ".join(code), at)
            n = first.size
            site = b"\xe9" + S.rel32(va + 5, at) + b"\x90" * (n - 5)
            nop = {3: "0f1f00", 4: "0f1f4000"}[ins[2].size]
            return ([(va, d[o:o + n].hex(), site.hex(),
                      "slot reader 0x%x: %s %s -> stub 0x%x (9 bits from +0x41c/+0x41b)"
                      % (va, first.mnemonic, first.op_str, at)),
                     (ins[2].address, ins[2].bytes.hex(), nop,
                      "slot reader 0x%x: its `%s %s` -> nop (the stub masks)" % (va, ins[2].mnemonic, ins[2].op_str))],
                    stub, [(va, n), (ins[2].address, ins[2].size)])
        raise SystemExit("0x%x: no `and %s, 0x7f` after the load" % (va, dst))
    used = [first, mask]
    # a byte use of the slot right after it: done on the whole register in the stub
    nxt = ins[2]
    ops = [x.strip() for x in nxt.op_str.split(",")]
    if nxt.mnemonic == "cmp" and ops[0] == B8[dst]:
        if ops[1].startswith("0x"):
            code.append("cmp %s, %s" % (dst, ops[1]))
        elif ops[1] in D32:
            code.append("cmp %s, %s" % (dst, D32[ops[1]]))    # the other one is ours too (9 bits)
        else:
            raise SystemExit("0x%x: cmp %s" % (nxt.address, nxt.op_str))
        used.append(nxt)
    elif nxt.mnemonic == "movzx" and ops[1] == B8[dst]:
        code.append("mov %s, %s" % (ops[0], dst))
        used.append(nxt)
    back = used[-1].address + used[-1].size
    code.append("jmp 0x%x" % back)
    stub = asm("; ".join(code), at)
    n = back - va
    site = b"\xe9" + S.rel32(va + 5, at) + b"\x90" * (n - 5)
    why = "slot reader 0x%x: %s -> stub 0x%x (9 bits from +0x41c/+0x41b)" % (
        va, " ; ".join("%s %s" % (i.mnemonic, i.op_str) for i in used), at)
    return [(va, d[o:o + n].hex(), site.hex(), why)], stub, [(va, n)]


def main():
    out = (sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv
           else os.path.join(HERE, "..", "sider", "experimental", "fl26slot7.lua"))
    d = open(EXE, "rb").read()
    secs = S.sections(d)
    patches_code, stubs, ranges = [], [], []

    # 1. our "league slot of competition" function
    at = CODE
    a = S.Asm(at)
    a.b("4883ec28")                     # sub rsp,0x28
    a.b("0fb709")                       # movzx ecx, word [rcx]
    a.jabs("e8", ID2SLOT)               # call id2slot
    a.b("83f87b"); a.j8(0x74, "SEVEN")  # 123 -> 7
    a.b("3d" + struct.pack("<I", NMAX).hex()); a.j8(0x73, "SEVEN")   # >= 512 (unsigned) -> 7
    a.b("4883c428c3")                   # add rsp,0x28 ; ret
    a.label("SEVEN")
    a.b("b807000000" "4883c428c3")      # mov eax,7 ; add rsp,0x28 ; ret
    fn = a.build()
    stubs.append((at, "00" * len(fn), fn.hex(),
                  "league slot of a competition id: id2slot, 7 only for 123 or >= %d (0x141509c00 caps at 128)" % NMAX))
    FN = at
    at = (at + len(fn) + 15) & ~15
    for va in TEAMSLOT_CALLERS:
        o = S.offset_of(secs, va)
        if d[o] != 0xe8 or va + 5 + struct.unpack_from("<i", d, o + 1)[0] != TEAMSLOT_FN:
            raise SystemExit("0x%x is not call 0x%x" % (va, TEAMSLOT_FN))
        patches_code.append((va, d[o:o + 5].hex(), "e8" + S.rel32(va + 5, FN).hex(),
                             "call 0x141509c00 -> our slot function 0x%x" % FN))
        ranges.append((va, 5))

    # 2. readers -> stubs
    for va in READERS:
        ps, stub, rg = reader_stub(d, secs, va, at)
        stubs.append((at, "00" * len(stub), stub.hex(), "stub of " + ps[0][3]))
        patches_code += ps
        ranges += rg
        at = (at + len(stub) + 7) & ~7

    # 3. writers / flag
    for va, old, new, why in REWRITES:
        n = len(old) // 2
        code = asm(new, va)
        if len(code) > n:
            raise SystemExit("0x%x: new code longer than old (%d > %d)" % (va, len(code), n))
        patches_code.append((va, old, (code + b"\x90" * (n - len(code))).hex(), why))
        ranges.append((va, n))

    if at > PAGE + 0x1000:
        raise SystemExit("stubs overflow")

    # 4. checks
    for va, oldh, newh, w in patches_code:
        o = S.offset_of(secs, va)
        if d[o:o + len(oldh) // 2].hex() != oldh:
            raise SystemExit("0x%x: file bytes are %s, not %s" % (va, d[o:o + len(oldh) // 2].hex(), oldh))
        if len(newh) != len(oldh):
            raise SystemExit("0x%x: length" % va)
    problems = []
    for va, total in ranges:
        if total > 1:
            for hit in S.branches_into(d, secs, va, total):
                # a branch that lands inside a rewrite is fine only when it comes from inside it
                if not (va <= hit[0] < va + total):
                    problems.append("branch into 0x%x+%d from 0x%x (%s 0x%x)" % ((va, total) + hit))
    rs = sorted(ranges)
    for (a1, l1), (a2, l2) in zip(rs, rs[1:]):
        if a2 < a1 + l1:
            problems.append("our own ranges overlap: 0x%x+%d / 0x%x+%d" % (a1, l1, a2, l2))
    overlap = []
    for f, (lr, lits) in S.lua_ranges().items():
        if os.path.basename(f).startswith("fl26slot7"):
            continue
        for pva, plen in lr:
            for va, total in ranges:
                if pva < va + total and va < pva + max(plen, 1):
                    overlap.append("%s: 0x%x+%d overlaps ours 0x%x+%d" % (os.path.basename(f), pva, plen, va, total))
        for lv in lits:
            for va, total in ranges:
                if va <= lv < va + total:
                    overlap.append("%s mentions 0x%x inside ours 0x%x+%d" % (os.path.basename(f), lv, va, total))
    # native DLLs: every *_RVA / *_SITE define and every absolute 0x14xxxxxxx literal
    for f in glob.glob(os.path.join(NATIVE, "*.c")):
        txt = open(f, encoding="utf-8", errors="replace").read()
        vals = set(int(x, 16) for x in re.findall(r"\b0x(14[0-9a-fA-F]{7})\b", txt))
        vals |= set(0x140000000 + int(x, 16) for x in
                    re.findall(r"#define\s+\w*(?:RVA|SITE)\w*\s+0x([0-9a-fA-F]{5,7})\b", txt))
        for lv in vals - set(PROBES):
            for va, total in ranges:
                if va <= lv < va + total:
                    overlap.append("%s: 0x%x inside ours 0x%x+%d" % (os.path.basename(f), lv, va, total))
    if problems or overlap:
        print("\n".join(problems + overlap))
        raise SystemExit("refusing to write: see above")

    patches = stubs + patches_code
    body = "\n".join('  {va=0x%x, old="%s", new="%s",\n   why="%s"},' % p for p in patches)
    tmpl = open(os.path.join(SIDER, "fl26caps.template.lua"), encoding="utf-8").read()
    tail = tmpl[tmpl.index("local PAGES"):]
    summary = ("team league slot 7 -> 9 bits (+0x41c low byte, +0x41b high byte, flag moved to +0x41a), "
               "%d patches" % len(patches))
    tail = (tail.replace("--[[PAGES]]", "0x%x" % PAGE)
                .replace("--[[SET]]", "slot7")
                .replace("--[[SUMMARY]]", summary)
                .replace("fl26caps_VirtualAlloc", "fl26slot7_VirtualAlloc")
                .replace("fl26caps", "fl26slot7"))
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(DOC % dict(summary=summary, page=PAGE)
                + "\nlocal m = {}\n\n"
                + "local patches = {\n" + body + "\n}\n\n" + tail)
    print("wrote %s: %d patches (%d readers + stubs, %d rewrites, %d calls, 1 function), code 0x%x bytes"
          % (out, len(patches), len(READERS), len(REWRITES), len(TEAMSLOT_CALLERS), at - CODE))
    return 0


DOC = """--[[
fl26slot7 -- a club's Master League league slot may be 0..511 (needs fl26slots250).

GENERATED FILE by mkslot7.py.  Every byte below was read from the exe at that address.

Summary: %(summary)s

A team record keeps its league slot in bits 0-6 of +0x41c; bit 7 is a flag of the game's own
and bits 8-31 are other fields.  With fl26slots250 a league can sit on slots 124..464, but a
club of a league on 130 got slot 130 & 0x7f = 2 when a Master League was created (the slot of
another competition), and every Master League lookup by club slot then went wrong.

This module moves the flag to +0x41a and the slot's high byte to +0x41b (padding next to the
country word +0x418), so the slot is +0x41c | +0x41b << 8:
  * every reader jumps to a stub that loads both bytes (9 bits); a byte compare right after
    the load is done on the whole register there,
  * every writer stores both bytes,
  * the flag is set, read, edited and copied at +0x41a,
  * the six callers of 0x141509c00 get the real slot (not 7 above 127),
  * the Master League slot choice (0x141263b40) is the game's own: the first slot holding a
    league-format competition wins, so a league on 344 gets 344 when fl26comptab gives its
    row slot 344.
B391 (10.11.2026): the 8-bit version stored 344 as 88, so Team Info put the clubs of a league
on 256..464 under the league on slot - 256.

Careers: a Master League created without this module stores the flag in bit 7; loading it
with this module reads every flagged club's slot as slot+128.  Start a NEW career after
installing (fl26slots250 already asks for that), and keep the module for that career.  A
career made with the 8-bit version of this module loads as it was (+0x41b is 0 there).

Load order: after fl26caps and fl26slots250 is fine; no byte overlaps any shipped module.
Page 0x%(page)x is its own.  Needs luajit.ext.enabled = 1 in sider.ini.

Install:
  1. copy this file to <game>\\SiderAddons\\modules\\fl26slot7.lua
  2. add to sider.ini:   lua.module = "fl26slot7.lua"   (after fl26slots250.lua)
  3. start the game and read sider.log ("fl26slot7: applied all ...")
--]]
"""

if __name__ == "__main__":
    sys.exit(main())
