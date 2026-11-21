r"""regions.py [--review]  -> the patches that let a world use regions (countries) 0..255

A competition's region is the Competition.bin +3 byte; fl26reg128 (sider/experimental) made the
game keep it whole in the byte at +0x2fe of the regulation record (stride 0x314) and taught all
32 readers to read that byte, but its parser takes only seven bits of the file byte:

    region = (b3 >> 3) | (b3 & 3) << 5          bits 3..7 -> 0..4, bit 0 -> 5, bit 1 -> 6

Bit 2 of the byte is the last one left. It belongs to the old nine-bit field d0 bits 18..26,
which the stock parser copied into +0x2fe (0x1414c9f30) and fl26reg128 replaced with the
record's mark; it is clear in every shipped row of both games (91 rows, FL26 and FL27 tables)
and in every row Mod Studio ever wrote (mkleague.enc_region kept it zero). With it the byte is
simply the region rotated left by three:

    region = ror8(b3, 3)                         bits 3..7 -> 0..4, bits 0..2 -> 5..7

so a byte with bit 2 clear reads exactly as under fl26reg128, and 128..255 become reachable.

Nothing else in the exe stops at 127 (checked on FL_2027.exe, 06.11.):
  * the setter fl26reg128 rewrote (0x1414c9c10) stores the whole dx at +0x2fe and clamps the
    6-bit field with an unsigned `cmp dl, 0x3f`, so 128..255 store as 0..127 do;
  * every reader is `movzx r32, byte [b+0x2fe]`, unsigned;
  * the 63 callers of the getter 0x1415415f0 and the inline readers pass the region on as a
    dword: equality, `cmp eax, 8/0xc/0x1d` (Belgium, Denmark, the old "no region"), the
    region -> competitions walk 0x1414ce270 (`cmp eax, r15d`), the region -> season type table
    0x141576140 (by pointer, dword), the region -> country table 0x1414cdbe0 (fl26catlist's
    stub), the European places 0x1413b7880; none indexes a table by it, none stores it in a
    byte or sign-extends one;
  * 0x1414cf160 (domestic region heading) is false from 29 up, 128..255 included.
The limits that did stop at 127 are in our own modules: fl26catlist (two `cmp r32, imm8` loop
counts -> `cmp r8, imm8`, and its 128-entry tables), fl26regnames (its row count likewise),
fl26augseason (`cmp eax, 0x63`), fl26join/fl26swiss (rec_region, g_stype[128], the split-carry
stub's signed imm8). Those are fixed in the modules; this step is the exe.

What this step writes. All 44 sites of fl26reg128 -- its 43 bytes as they are, the parser as the
rotate above -- so a caps set with this step owns the regions the way the standings step owns
fl26hdr255's sites: fl26reg128 (run after fl26caps) finds every site done and writes nothing.
fl26reg128.lua is the one source of the 43: they are read out of it, and every old= is checked
against the exe here.

The parser (0x1414f8390, 18 bytes up to the setter call's `mov edx, r14d` at 0x1414f83a2):

    movzx ecx, byte ptr [rax + 3]   ; the row's +3 byte (rax = the row, as before)
    ror   cl, 3
    movzx r14d, cl                  ; r14d = the region, as fl26reg128 leaves it
    nop dword ptr [rax + 0]         ; 7 bytes of padding

eax and ecx are dead after it: the setter call loads rcx, and the code after it reloads rax.
"""
import os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOP = os.path.dirname(HERE)
REG128 = os.path.join(TOP, "sider", "experimental", "fl26reg128.lua")

PARSER = 0x1414F8390
PARSER_END = 0x1414F83A2          # mov edx, r14d -- the setter call's argument
PARSER_OLD = "8b08c1e91b0fb6c1241f3c1d7304440fb6f1"
PARSER_ASM = "movzx ecx, byte ptr [rax + 3]; ror cl, 3; movzx r14d, cl"
NOP7 = bytes.fromhex("0f1f8000000000")
PARSER_NEW = "0fb64803c0c903440fb6f1" "0f1f8000000000"   # parser_code() checks it against keystone
GETTER_READ = 0x141541639         # fl26join/fl26swiss look here to know reg128's reads are live
TOP_REGION = 255
WHY = "regions: "                 # every why of this step starts with it (caps_wide looks for it)


def _ks():
    import keystone
    return keystone.Ks(keystone.KS_ARCH_X86, keystone.KS_MODE_64)


def _md():
    from capstone import Cs, CS_ARCH_X86, CS_MODE_64
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    md.detail = True
    return md


def reg128_sites(path=REG128):
    """[(va, old, new, why)] from fl26reg128.lua's PATCHES"""
    src = open(path, encoding="utf-8").read()
    rows = re.findall(r'\{va=(0x[0-9a-f]+), old="([0-9a-f]+)", new="([0-9a-f]+)"(?:, alt="[0-9a-f]+")?(?:, wide="[0-9a-f]+")?,\s*'
                      r'why="([^"]*)"\}', src)
    if len(rows) != 44:
        raise SystemExit("regions: %s has %d sites, not fl26reg128's 44" % (path, len(rows)))
    if 'wide="%s"' % PARSER_NEW not in src:
        raise SystemExit("regions: %s does not take this step's parser (wide=) as done" % path)
    return [(int(va, 16), old, new, why) for va, old, new, why in rows]


def parser_code():
    """the 18 bytes at PARSER, assembled and read back"""
    code = bytes(_ks().asm(PARSER_ASM, PARSER)[0])
    code += NOP7
    if len(code) != PARSER_END - PARSER:
        raise SystemExit("regions: the parser is %d bytes, not %d" % (len(code), PARSER_END - PARSER))
    got = ["%s %s" % (i.mnemonic, i.op_str) for i in _md().disasm(code, PARSER)]
    want = ["movzx ecx, byte ptr [rax + 3]", "ror cl, 3", "movzx r14d, cl", "nop dword ptr [rax]"]
    if got != want or code.hex() != PARSER_NEW:
        raise SystemExit("regions: the parser decodes as %r (%s)" % (got, code.hex()))
    return code


def decode(b3):
    """what the parser makes of a +3 byte (ror8 by 3)"""
    return ((b3 >> 3) | (b3 << 5)) & 0xFF


def whole(code, va):
    """code decodes into whole instructions that fill it exactly"""
    n = sum(i.size for i in _md().disasm(code, va))
    return n == len(code)


def branches_into(read, lo, hi, scan=(0x1414F7E80, 0x1414F8A00)):
    """direct branches of the parser's function (0x1414f7e80, in the scan window) that land
    strictly inside (lo, hi)"""
    md = _md()
    a, b = scan
    hits = []
    for ins in md.disasm(read(a, b - a), a):
        if ins.group(1) or ins.group(2) or ins.mnemonic.startswith("j"):     # jump / call
            op = ins.operands[0] if ins.operands else None
            if op is not None and op.type == 2 and lo < op.imm < hi:
                hits.append((ins.address, op.imm))
    return hits


def patches(read, in_code=None):
    """-> patchset-style patches. read(va, k) gives the shipped bytes of the code section."""
    out = []
    code = parser_code()
    for va, old, new, why in reg128_sites():
        got = read(va, len(old) // 2).hex()
        if got != old:
            raise SystemExit("regions 0x%x: the exe has %s, fl26reg128 expects %s -- another exe?"
                             % (va, got, old))
        if va == PARSER:
            if old != PARSER_OLD:
                raise SystemExit("regions: fl26reg128's parser site holds %s" % old)
            hits = branches_into(read, PARSER, PARSER_END)
            if hits:
                raise SystemExit("regions: branches into the parser: %s"
                                 % ", ".join("0x%x -> 0x%x" % h for h in hits))
            new = code.hex()
            why = ("parser: region = ror8(Competition.bin +3, 3) -- bits 3..7 -> 0..4, bit 0 -> 5, "
                   "bit 1 -> 6, bit 2 -> 7: 0..255; a byte with bit 2 clear reads as under fl26reg128")
        if len(new) != len(old) or not whole(bytes.fromhex(new), va):
            raise SystemExit("regions 0x%x: %s is not whole instructions of the old length" % (va, new))
        out.append({"va": "0x%x" % va, "old": old, "new": new, "why": WHY + why,
                    "asm": "regions"})
    if read(GETTER_READ, 12).hex() != "8b800c030000c1e80783e03f":
        raise SystemExit("regions: the getter's read at 0x%x is not the shipped one" % GETTER_READ)
    return out


def check_overlap(step, patches, name="-regions"):
    """no byte of the step may touch a patch already in the set"""
    spans = [(int(p["va"], 16), len(p["old"]) // 2, p["va"]) for p in patches]
    for q in step:
        a = int(q["va"], 16)
        b = a + len(q["old"]) // 2
        for s, k, v in spans:
            if s < b and a < s + k:
                raise SystemExit("%s: %s overlaps the set's patch at %s" % (name, q["va"], v))


def info():
    return {"top_region": TOP_REGION, "sites": 44, "parser": "0x%x" % PARSER,
            "encoding": "Competition.bin +3 = rol8(region, 3)"}


def caps_wide(path):
    """does the caps set at `path` (fl26caps*.lua) carry this step? The league builder hands out
    regions past 127 only when it does."""
    try:
        src = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return False
    want = '{va=0x%x, old="%s", new="%s"' % (PARSER, PARSER_OLD, PARSER_NEW)
    return want in src


def main(argv):
    import calwiden
    exe = calwiden.Exe()
    ps = patches(exe.read)
    print("%d patches; %r" % (len(ps), info()))
    if "--review" in argv:
        for p in ps:
            print("  %s  %s -> %s  %s" % (p["va"], p["old"], p["new"], p["why"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
