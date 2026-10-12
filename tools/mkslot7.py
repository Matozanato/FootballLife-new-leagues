r"""python mkslot7.py [--out fl26slot7.lua]  -> a module that lets a club's league slot be 0..249

A team record keeps its Master League slot at +0x41c.  The game uses bits 0-6 for the slot
and bit 7 for a flag of its own (copied from bit 7 of the regulation's +0x304 when a Master
League is created; edited through field setter 0x141f11c80 / getter 0x141f11570; init sets it
to 1).  Bits 8-31 of the dword are full (+0x41d, +0x41e, two nibbles).  So the 7-bit slot
cannot grow in place: this module moves the flag to bit 0 of +0x41a (two bytes of padding
after the country word +0x418 that nothing in the exe reads or writes) and gives the slot the
whole byte +0x41c.  123 stays the "no slot" sentinel.

What changes (every byte read from the exe and verified before anything is written):
  * 32 readers   movzx r, byte [t+0x41c] ; and r, 0x7f      -> and r, 0xff   (1 byte each)
  * 11 writers   and [t+0x41c],0xffffff80 ; or [t+0x41c],r  -> mov byte [t+0x41c], r8
                 (and 0xffffff80 kept bit 7, so the flag byte is left alone)
  * 3 flag sets  btr/bts bit 7 of the dword                  -> mov byte [t+0x41a], flag
  * 2 staged-world writes in 0x141266490 (123 path and the normal path)
  * flag init 0x1414c5b41, field setter 0x141f12004, getters 0x141eddb4f / 0x141f116af
  * team copy 0x140b158d0: the country word copy becomes a dword copy, so +0x41a travels
  * the six callers of 0x141509c00 ("league slot of competition id", 7 for 123 and >= 128
    with fl26slots250) call our own version: id2slot, 7 only for 123 or >= 250
  * nothing in the Master League slot choice 0x141263b40: it already takes the first slot
    (lowest first) that carries a LEAGUE-format competition (find_if 0x14125fe50 ->
    comptab rows with that slot -> 0x1414cf750: regulation format in mask 0xf9c2), then
    69/70/73, then the lowest.  A league on 130 beats a cup on 40 as long as its comptab
    row says 130 and its regulation has a league format.

Requires fl26slots250 (it is what makes slots >= 124 exist at all).  Without it this module
changes nothing visible: no slot >= 128 is ever produced.
"""
import os
import re
import struct
import sys
import glob

import capstone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mkslots as S                                     # sections, offsets, Asm, checks

EXE = S.EXE
SIDER = S.SIDER
NATIVE = r"D:\dev\fl26\wt\limits\tools\native"
PAGE = 0x163c00000            # ours; fl26caps 0x163000000, fl26slots 0x163400000
CODE = PAGE
NMAX = 250
ID2SLOT = 0x1414cb2e0
TEAMSLOT_FN = 0x141509c00
TEAMSLOT_CALLERS = [0x140ae3de8, 0x140ae44d3, 0x14126275b, 0x141262e8b, 0x14135964b, 0x14135a50b]

READERS = [
    0x140b08f6b, 0x140c6c0b7, 0x140fa306f, 0x140fd2a77, 0x140fd8ea6, 0x141262379, 0x1412628ec,
    0x141262b7c, 0x141324ded, 0x14132a03d, 0x141333964, 0x141354dc9, 0x1413558cd, 0x141358f74,
    0x14135a8c5, 0x14135ae09, 0x14135b175, 0x14135d787, 0x141360372, 0x1413603eb, 0x141361119,
    0x141365906, 0x141365930, 0x14150956c, 0x14150d4e5, 0x14150d51f, 0x141511243, 0x1415191d3,
    0x141527eb7, 0x141541f62, 0x141546a09, 0x141547fe9,
]

NOP = "90"
FLAG_R15 = "418b8704030000" "c1e807" "2401" "4188851a040000"   # flag of regulation r15 -> [r13+0x41a]
FLAG_RSI = "8b8604030000" "c1e807" "2401" "4188851a040000"     # flag of regulation rsi -> [r13+0x41a]

# (va, old bytes, new bytes without padding, why) -- new is padded with nops to len(old)
REWRITES = [
    (0x141262760, "4183a51c040000800fb6c083e07f4109851c040000",
     "4188851c040000",
     "user's club: slot from 0x141509c00 -> byte +0x41c (flag in +0x41a untouched, as and 0xffffff80 kept bit 7)"),
    (0x1412627df, "4183a4241c040000800fb645ef83e07f410984241c040000",
     "0fb645ef" "418884241c040000",
     "user's club path: other club gets the saved slot [rbp-0x11] -> byte +0x41c"),
    (0x1412628f5, "4183a51c040000800fb6c04109851c040000",
     "4188851c040000",
     "user's club takes another club's slot (al) -> byte +0x41c"),
    (0x141262930, "418b8704030000c1e807a80175060fbaf207eb040fbaea074189951c040000",
     FLAG_R15,
     "flag of the regulation (+0x304 bit 7) -> +0x41a instead of bit 7 of +0x41c"),
    (0x14126294f, "83a11c040000800fb645ef83e07f09811c040000",
     "0fb645ef" "88811c040000",
     "other club gets the saved slot [rbp-0x11] -> byte +0x41c"),
    (0x141262b85, "4183a51c040000800fb6c04109851c040000",
     "4188851c040000",
     "user's club takes another club's slot (al) -> byte +0x41c"),
    (0x141262bc0, "8b8604030000c1e807a80175060fbaf207eb040fbaea074189951c040000",
     FLAG_RSI,
     "flag of the regulation (+0x304 bit 7) -> +0x41a instead of bit 7 of +0x41c"),
    (0x141262bde, "83a11c04000080410fb6c783e07f09811c040000",
     "410fb6c7" "88811c040000",
     "other club gets slot r15b -> byte +0x41c"),
    (0x141262e90, "0fb6c841338d1c04000083e17f41338d1c04000041898d1c040000"
                  "418b8704030000c1e807a80175060fbaf107eb040fbae90741898d1c040000",
     "4188851c040000" + FLAG_R15,
     "user's club: slot (al) -> byte +0x41c, regulation flag -> +0x41a"),
    (0x141262f77, "83a01c040000800fb645ef83e07f09811c040000",
     "0fb645ef" "88811c040000",
     "other club (rax == rcx) gets the saved slot [rbp-0x11] -> byte +0x41c"),
    (0x14136595f, "83a01c04000080400fb6cf09881c040000",
     "4088b81c040000",
     "season mover: club takes slot dil -> byte +0x41c"),
    (0x14136599f, "83a01c04000080410fb6cf09881c040000",
     "4488b81c040000",
     "season mover: club takes slot r15b -> byte +0x41c"),
    (0x14126655e, "8b856c03000083e0fb83c87b",
     "8b856c030000" "b07b",
     "staged world: no slot -> byte = 123 (was low 7 bits = 123, bit 7 kept)"),
    (0x1412665cb, "0fb6c88b856c03000033c883e17f33c1",
     "8b8d6c030000" "88c1" "89c8",
     "staged world: slot from 0x141263b40 -> whole byte +0x41c of the staged copy"),
    (0x1414c5b41, "818b1c04000080000000",
     "c6831a04000001",
     "team init: flag = 1 now in +0x41a (was or [+0x41c],0x80)"),
    (0x141f12004, "81a61c0400007fffffff098e1c040000",
     "c1e907" "888e1a040000",
     "edit field setter: flag (ecx = 0x80 or 0) -> +0x41a bit 0"),
    (0x141eddb4f, "8b801c040000c1e8072401",
     "0fb6801a040000" "2401",
     "flag reader: +0x41a bit 0"),
    (0x141f116af, "8b851c040000458bc6c1e8072401",
     "0fb6851a040000" "458bc6" "2401",
     "edit field getter: flag from +0x41a bit 0"),
    (0x140b15aa9, "0fb78718040000",
     "8b8718040000",
     "team copy: country word +0x418 copied as a dword, so +0x41a (flag) travels with it"),
    (0x140b15ab0, "66898318040000",
     "898318040000",
     "team copy: store the dword +0x418..+0x41b"),
]

def reader_patch(d, secs, va):
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    o = S.offset_of(secs, va)
    ins = list(md.disasm(d[o:o + 40], va))[:3]
    first = ins[0]
    if first.mnemonic != "movzx" or "byte ptr" not in first.op_str or "+ 0x41c]" not in first.op_str:
        raise SystemExit("0x%x: %s %s is not a movzx of byte +0x41c" % (va, first.mnemonic, first.op_str))
    dst = first.op_str.split(",")[0].strip()
    fam = {"eax": "al", "ecx": "cl", "edx": "dl", "ebx": "bl", "ebp": "bpl", "esi": "sil", "edi": "dil",
           "r15d": "r15b", "r14d": "r14b", "r8d": "r8b", "r9d": "r9b"}
    for i in ins[1:]:
        r = i.op_str.split(",")[0].strip()
        if i.mnemonic == "and" and i.op_str.endswith("0x7f") and r in (dst, fam.get(dst)) and i.bytes[-1] == 0x7f:
            immva = i.address + i.size - 1
            return (immva, "7f", "ff", "slot reader 0x%x: %s %s -> 0xff" % (va, i.mnemonic, i.op_str))
    raise SystemExit("0x%x: no `and %s, 0x7f` after the load" % (va, dst))


def main():
    out = (sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv
           else os.path.join(HERE, "..", "sider", "experimental", "fl26slot7.lua"))
    d = open(EXE, "rb").read()
    secs = S.sections(d)
    patches_code, stubs, ranges = [], [], []

    # 1. readers
    for va in READERS:
        p = reader_patch(d, secs, va)
        patches_code.append(p)
        ranges.append((p[0], 1))

    # 2. writers / flag
    for va, old, new, why in REWRITES:
        n = len(old) // 2
        if len(new) // 2 > n:
            raise SystemExit("0x%x: new code longer than old" % va)
        new = new + NOP * (n - len(new) // 2)
        patches_code.append((va, old, new, why))
        ranges.append((va, n))

    # 3. our "league slot of competition" function
    at = CODE
    a = S.Asm(at)
    a.b("4883ec28")                     # sub rsp,0x28
    a.b("0fb709")                       # movzx ecx, word [rcx]
    a.jabs("e8", ID2SLOT)               # call id2slot
    a.b("83f87b"); a.j8(0x74, "SEVEN")  # 123 -> 7
    a.b("3d" + struct.pack("<I", NMAX).hex()); a.j8(0x73, "SEVEN")   # >= 250 (unsigned) -> 7
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

    if at > PAGE + 0x1000:
        raise SystemExit("stubs overflow")

    # 5. checks
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
        for lv in vals:
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
    summary = ("team league slot 7 -> 8 bits (+0x41c byte, flag moved to +0x41a), "
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
    print("wrote %s: %d patches (%d readers, %d rewrites, %d calls, %d stub), code 0x%x bytes"
          % (out, len(patches), len(READERS), len(REWRITES), len(TEAMSLOT_CALLERS), len(stubs), at - CODE))
    return 0


DOC = """--[[
fl26slot7 -- a club's Master League league slot may be 0..249 (needs fl26slots250).

GENERATED FILE by mkslot7.py.  Every byte below was read from the exe at that address.

Summary: %(summary)s

A team record keeps its league slot in bits 0-6 of +0x41c; bit 7 is a flag of the game's own
and bits 8-31 are other fields.  With fl26slots250 a league can sit on slots 124..249, but a
club of a league on 130 got slot 130 & 0x7f = 2 when a Master League was created (the slot of
another competition), and every Master League lookup by club slot then went wrong.

This module moves the flag to +0x41a (padding next to the country word +0x418) and makes the
slot the whole byte +0x41c:
  * every reader masks with 0xff instead of 0x7f, every writer stores the byte,
  * the flag is set, read, edited and copied at +0x41a,
  * the six callers of 0x141509c00 get the real slot up to 249 (not 7 above 127),
  * the Master League slot choice (0x141263b40) is the game's own: the first slot holding a
    league-format competition wins, so a league on 130 gets 130 when fl26comptab gives its
    row slot 130.

Careers: a Master League created without this module stores the flag in bit 7; loading it
with this module reads every flagged club's slot as slot+128.  Start a NEW career after
installing (fl26slots250 already asks for that), and keep the module for that career.

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
