r"""python mkslots.py [N] [--out fl26slots250.lua]  -> a module that widens the competition slots

The edit block keeps one club list per competition *slot* (region at edit+0xd0bd04, header
at +0xd0bcf8).  The game ships 123 slots of 750 dwords each, followed by 123 u16 counts at
+0x5a168; the whole region is 0x5a25e bytes and the constructor (0x1414d6270) memsets that
size.  Every access goes through five small functions:

    0x1414d6290  get(region, slot, i)        -> club id or -1
    0x1414d62c0  count(region, slot)         -> u16
    0x1414d62e0  clear(region)               fill every list, zero the counts
    0x1414d6330  set(region, slot, i, id)
    0x1414d6360  setcount(region, slot, n)   refused when n > capacity

The region cannot grow (it sits inside the edit block next to other members), so the
extra slots are paid for out of per-slot capacity.  Instead of one fixed stride, each slot
gets its own capacity from a table on our page, so that the two aggregate slots the game
builds from almost every club (79 and 80, see docs/limits.md) keep room for the whole team
pool (1600 with fl26caps); the slots the game fills from team region codes or merges
(0..5, 69..78) keep the 750 they always had, and the ordinary slots share what is left:

    N    lists (dwords)   79/80   0..5, 69..78   every other slot   counts at
   250       92125         1600       750              333           0x59f74
   128       92186         1600       750              706           0x5a068

Slot 123 stays the engine's "no slot" sentinel: id2slot (0x1414cb2e0) and cid2slot
(0x1414cb030) answer 123 when a competition has no row, three Select-Team builders push
123 as their "all teams" pseudo entry, and 0x1415191c8 compares against it.  Moving the
sentinel would mean finding every one of those; keeping it costs one slot.  The new
accessors refuse slot 123 exactly as the old ones refused 123..255, and slot 123 has
capacity 0.

Everything here is read from the exe and checked; nothing touches the game.
"""
import glob
import os
import re
import struct
import sys

import capstone

IMAGE_BASE = 0x140000000
EXE = os.path.join(os.environ.get("FL26_DIR", r"E:\instalacija"), "FL_2026.exe")
SIDER = r"D:\dev\fl26\wt\limits\sider"           # read only: overlap checks
HERE = os.path.dirname(os.path.abspath(__file__))

PAGE = 0x163400000            # our own page; fl26caps has 0x163000000
CODE = PAGE                   # stubs
OFF_TAB = PAGE + 0x800        # N dwords: first dword of each slot's list
CAP_TAB = PAGE + 0xc00        # N dwords: capacity of each slot

OLD_N = 123
SENTINEL = 0x7b
REGION = 0x5a25e              # constructor memset size -- untouched
OLD_CNT = 0x5a168             # the new layout ends at or below the old counts
# Slots the game fills from team region codes (0..5, 69..75) or merges out of other slots
# (76..80) keep at least the 750 they always had; 79 and 80 merge almost every club, so they
# get room for the whole team pool (1600 with fl26caps).  See docs/limits.md.
BIG = dict([(s, 750) for s in list(range(0, 6)) + list(range(69, 79))] + [(79, 1600), (80, 1600)])
TEAMSLOT_BITS = 7             # team record +0x41c holds the slot in 7 bits (bit 7 = flag)

# The five accessors as shipped (verified byte for byte before anything is generated).
ACC = {
    "get":      (0x1414d6290, "83fa7b73208bd20fb7845168a10500443bc07311418bc04869d2ee0200004803d08b0491c383c8ffc3"),
    "count":    (0x1414d62c0, "33c083fa7b730a8bc20fb7844168a10500c3"),
    "clear":    (0x1414d62e0, "488bc141b97b0000000f1f800000000041b8ee02000066660f1f8400000000008b153e4b0402c1ea0e89104883c0044983e80175eb4983e90175d54881c168a1050033d241b8f6000000e9f1b30c00"),
    "set":      (0x1414d6330, "83fa7b731c4181f8ee0200007313" "8bc24869d0ee020000418bc04803d044890c91c3"),
    "setcount": (0x1414d6360, "83fa7b7316b8ee02000066443bc0770b8bc2664489844168a10500c3"),
}

# compare + branch pairs on a slot number.
#   guard: 123 and anything >= N is rejected, the rest passes (signedness kept)
#   loop : the loop runs to N; slot 123 goes through the body and finds count 0
SITES = [
    (0x1414cb0f0, "guard", "cid2slot: only real slots of the rows a competition id has"),
    (0x1414f754e, "guard", "slot-list builder: slot of a competition entry (first test)"),
    (0x1414f756e, "guard", "slot-list builder: slot of a competition entry (second test)"),
    (0x1414f77da, "loop",  "slot-list builder: write every slot vector into the region"),
    (0x1412688e0, "guard", "regulation fill: slot of the competition"),
    (0x1412fac89, "guard", "Select Team list: a real slot, else the special list at +0xf0"),
    (0x1412fb24e, "guard", "Select Team list: a real slot, else the special list"),
    (0x1412fb6a5, "loop",  "Select Team list: walk every slot"),
    (0x1412640fc, "loop",  "user club categories: walk every slot looking for the club"),
]
BUILDER_N = 0x1414f6e48           # mov edx,0x7b -> number of slot vectors the builder makes
TEAMSLOT = 0x144acacec            # .impdata: team.slot = slot < 123 ? slot : 7
TEAMSLOT_OLD = "83f87bb9070000000f4cc889c8"
TEAMSLOT_BACK = 0x144acacf9
MEMSET = 0x1415a1720
FILL_SRC = 0x14351ae44            # [rip+0x2044b3e] in clear: the fill value << 0xe


def sections(d):
    pe = struct.unpack_from("<I", d, 0x3c)[0]
    n = struct.unpack_from("<H", d, pe + 6)[0]
    opt = struct.unpack_from("<H", d, pe + 20)[0]
    o = pe + 24 + opt
    out = []
    for i in range(n):
        h = d[o + i * 40:o + (i + 1) * 40]
        vs, va, rs, raw = struct.unpack_from("<IIII", h, 8)
        out.append((IMAGE_BASE + va, vs, raw, rs, h[:8].rstrip(b"\0").decode("latin1")))
    return out


def offset_of(secs, va):
    for base, vs, raw, rs, _ in secs:
        if base <= va < base + vs:
            off = va - base
            return raw + off if off < rs else None
    return None


def section_of(secs, va):
    for base, vs, raw, rs, name in secs:
        if base <= va < base + vs:
            return name, base, vs
    return None


def rel32(src_next, dst):
    d = dst - src_next
    if not -0x80000000 <= d < 0x80000000:
        raise SystemExit("rel32 out of range: 0x%x -> 0x%x" % (src_next, dst))
    return struct.pack("<i", d)


class Asm:
    """Just enough of an assembler: raw bytes, labels, short/near branches, rip operands."""

    def __init__(self, base):
        self.base, self.items = base, []

    def b(self, h):
        self.items.append(("raw", bytes.fromhex(h)))

    def label(self, name):
        self.items.append(("label", name))

    def j8(self, op, name):
        self.items.append(("j8", op, name))

    def jabs(self, opbytes, target):           # e9 / 0f 8x with an absolute target
        self.items.append(("jabs", bytes.fromhex(opbytes), target))

    def rip(self, pre, target, post=""):       # pre + disp32 + post, disp relative to end
        self.items.append(("rip", bytes.fromhex(pre), target, bytes.fromhex(post)))

    def build(self):
        def size(it):
            return {"raw": lambda: len(it[1]), "label": lambda: 0, "j8": lambda: 2,
                    "jabs": lambda: len(it[1]) + 4,
                    "rip": lambda: len(it[1]) + 4 + len(it[3])}[it[0]]()
        labels, pc = {}, self.base
        for it in self.items:
            if it[0] == "label":
                labels[it[1]] = pc
            pc += size(it)
        out, pc = b"", self.base
        for it in self.items:
            n = size(it)
            if it[0] == "raw":
                out += it[1]
            elif it[0] == "j8":
                d = labels[it[2]] - (pc + 2)
                if not -128 <= d < 128:
                    raise SystemExit("short branch out of range")
                out += bytes([it[1], d & 0xff])
            elif it[0] == "jabs":
                out += it[1] + rel32(pc + n, it[2])
            elif it[0] == "rip":
                out += it[1] + rel32(pc + len(it[1]) + 4 + len(it[3]), it[2]) + it[3]
            pc += n
        return out


def layout(n):
    if not OLD_N < n <= 250:
        raise SystemExit("N must be 124..250")
    listdw = (OLD_CNT - 2 * n) // 4
    cnt = listdw * 4
    big = {s: c for s, c in BIG.items() if s < n}
    normal = [s for s in range(n) if s != SENTINEL and s not in big]
    per = (listdw - sum(big.values())) // len(normal)
    caps = [0] * n
    for s in normal:
        caps[s] = per
    for s, c in big.items():
        caps[s] = c
    offs, at = [], 0
    for s in range(n):
        offs.append(at)
        at += caps[s]
    assert at <= listdw and cnt + 2 * n <= OLD_CNT <= REGION
    assert max(caps) < 0x10000
    return dict(listdw=listdw, cnt=cnt, caps=caps, offs=offs, per=per, used=at)


def accessor_stubs(n, L, base):
    """The four accessors that need the tables.  Registers clobbered: the originals' own.
    Each body starts on a 16-byte boundary, the same placement main() uses."""
    N32 = struct.pack("<I", n).hex()
    CNT = struct.pack("<I", L["cnt"]).hex()
    out = {}

    a = Asm(base)                     # get: rax, rdx (as the original)
    a.b("89d0"); a.b("3d" + N32); a.j8(0x73, "F"); a.b("3c7b"); a.j8(0x74, "F")
    a.b("0fb79441" + CNT)             # movzx edx, word [rcx+rax*2+CNT]
    a.b("443bc2"); a.j8(0x73, "F")    # cmp r8d, edx ; jae F
    a.rip("488d15", CAP_TAB); a.b("443b0482"); a.j8(0x73, "F")   # i >= capacity
    a.rip("488d15", OFF_TAB); a.b("8b1482"); a.b("4401c2")       # edx = off[slot] + i
    a.b("8b0491"); a.b("c3")
    a.label("F"); a.b("83c8ff"); a.b("c3")
    out["get"] = a.build()

    base = (base + len(out["get"]) + 15) & ~15
    a = Asm(base)                     # count: rax only (rdx saved)
    a.b("31c0"); a.b("81fa" + N32); a.j8(0x73, "R"); a.b("83fa7b"); a.j8(0x74, "R")
    a.b("52"); a.b("89d0"); a.rip("488d15", CAP_TAB); a.b("8b1482")
    a.b("0fb78441" + CNT)             # movzx eax, word [rcx+rax*2+CNT]
    a.b("39d0"); a.b("0f47c2")        # never more than the capacity
    a.b("5a")
    a.label("R"); a.b("c3")
    out["count"] = a.build()

    base = (base + len(out["count"]) + 15) & ~15
    a = Asm(base)                     # set: rax, rdx
    a.b("89d0"); a.b("3d" + N32); a.j8(0x73, "R"); a.b("3c7b"); a.j8(0x74, "R")
    a.rip("488d15", CAP_TAB); a.b("443b0482"); a.j8(0x73, "R")
    a.rip("488d15", OFF_TAB); a.b("8b1482"); a.b("4401c2")
    a.b("44890c91")
    a.label("R"); a.b("c3")
    out["set"] = a.build()

    base = (base + len(out["set"]) + 15) & ~15
    a = Asm(base)                     # setcount: rax only (rdx saved)
    a.b("81fa" + N32); a.j8(0x73, "R"); a.b("83fa7b"); a.j8(0x74, "R")
    a.b("52"); a.b("89d0"); a.rip("488d15", CAP_TAB); a.b("8b1482")
    a.b("664139d0"); a.j8(0x77, "P")  # n > capacity: refused, as the original did
    a.b("6644898441" + CNT)
    a.label("P"); a.b("5a")
    a.label("R"); a.b("c3")
    out["setcount"] = a.build()
    return out


JCC = {"jb": 0x2, "jae": 0x3, "je": 0x4, "jne": 0x5, "jbe": 0x6, "ja": 0x7,
       "jl": 0xc, "jge": 0xd, "jle": 0xe, "jg": 0xf}
GOOD_WHEN_TAKEN = ("jb", "jl")
BAD_WHEN_TAKEN = ("jae", "jge")


def site_patch(d, secs, va, kind, n, at, why):
    off = offset_of(secs, va)
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    cmp_i, jcc_i = list(md.disasm(d[off:off + 24], va))[:2]
    cb = bytes(cmp_i.bytes)
    i = cb.index(0x83) if 0x83 in cb else -1
    if cmp_i.mnemonic != "cmp" or i < 0 or cb[:i] not in (b"", b"\x41") \
            or len(cb) != i + 3 or cb[-1] != SENTINEL or (cb[i + 1] >> 3) & 7 != 7 \
            or cb[i + 1] >> 6 != 3:
        raise SystemExit("0x%x: %s %s (%s) is not `cmp r32, 0x7b`"
                         % (va, cmp_i.mnemonic, cmp_i.op_str, cb.hex()))
    if jcc_i.mnemonic not in GOOD_WHEN_TAKEN + BAD_WHEN_TAKEN:
        raise SystemExit("0x%x: followed by %s" % (va, jcc_i.mnemonic))
    wide = cb[:i] + b"\x81" + cb[i + 1:i + 2] + struct.pack("<I", n)
    target = int(jcc_i.op_str, 16)
    total = cmp_i.size + jcc_i.size
    back = va + total
    cc = "0f%02x" % (0x80 | JCC[jcc_i.mnemonic])
    a = Asm(at)
    if kind == "guard":
        a.b(cb.hex())                                   # cmp r, 0x7b
        a.jabs("0f84", target if jcc_i.mnemonic in BAD_WHEN_TAKEN else back)
    a.b(wide.hex())
    a.jabs(cc, target)
    a.jabs("e9", back)
    stub = a.build()
    site = b"\xe9" + rel32(va + 5, at) + b"\x90" * (total - 5)
    reg = cmp_i.op_str.split(",")[0]
    desc = ("%s: cmp %s,123 -> rejected; cmp %s,%d; %s 0x%x; jmp 0x%x"
            % (kind, reg, reg, n, jcc_i.mnemonic, target, back) if kind == "guard" else
            "%s: cmp %s,%d; %s 0x%x; jmp 0x%x" % (kind, reg, n, jcc_i.mnemonic, target, back))
    return ((at, "00" * len(stub), stub.hex(), "stub for 0x%x -- %s  [%s]" % (va, desc, why)),
            (va, (cb + bytes(jcc_i.bytes)).hex(), site.hex(),
             "%s %s / %s %s -> stub 0x%x  [%s]" % (cmp_i.mnemonic, cmp_i.op_str,
                                                     jcc_i.mnemonic, jcc_i.op_str, at, why)),
            len(stub), (va, total))


def branches_into(d, secs, va, total):
    """Direct branches whose target falls strictly inside [va, va+total)."""
    hits = []
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    md.skipdata = True
    name, base, vs = section_of(secs, va)
    lo = max(base, va - 0x2000)
    hi = min(base + vs, va + 0x2000)
    o = offset_of(secs, lo)
    for start in range(lo, lo + 16):            # several phases: resync is quick on x86
        oo = o + (start - lo)
        for ins in md.disasm(d[oo:oo + (hi - start)], start):
            if ins.mnemonic.startswith("j") or ins.mnemonic == "call":
                try:
                    t = int(ins.op_str, 16)
                except ValueError:
                    continue
                if va < t < va + total:
                    hits.append((ins.address, ins.mnemonic, t))
    # keep only branches that sit on the same instruction stream as the site itself
    real = []
    for a, m, t in sorted(set(hits)):
        oo = offset_of(secs, a)
        ins = list(md.disasm(d[oo:oo + (va - a) + 16], a)) if a < va else []
        if a < va and not any(x.address == va for x in ins):
            continue
        real.append((a, m, t))
    return real


def lua_ranges():
    """{file: [(va, len)]} for every {va=..., old=...} patch in the shipped modules."""
    out = {}
    pat = re.compile(r'va\s*=\s*0x([0-9a-fA-F]+)\s*,\s*old\s*=\s*"([0-9a-fA-F]*)"')
    for f in glob.glob(os.path.join(SIDER, "*.lua")) + glob.glob(os.path.join(SIDER, "experimental", "*.lua")):
        txt = open(f, encoding="utf-8", errors="replace").read()
        rs = [(int(v, 16), len(o) // 2) for v, o in pat.findall(txt)]
        lits = [int(x, 16) for x in re.findall(r"0x(14[0-9a-fA-F]{7})\b", txt)]
        out[f] = (rs, lits)
    return out


DOC = """--[[
fl26slots -- competition slots 123 -> %(n)d.

GENERATED FILE by mkslots.py.  Every byte below was read from the exe at that address.

Set:     slots%(n)d
Summary: %(summary)s

The edit block keeps one club list per competition slot.  The game ships 123 slots of 750
entries.  The region they live in cannot grow, so this module gives every slot a capacity
of its own, kept in a table on a page this module allocates at 0x%(page)x:

    slot 79 and 80 (aggregates the game merges from almost every club)   %(big)d entries
    slots 0..5 and 69..78 (region-code and merged lists)                750 entries (as before)
    slot 123 (the engine's "no slot" sentinel, kept as it is)            0
    every other slot                                                     %(per)d entries

and rewrites the five accessors (0x1414d6290..0x1414d637f, same entry addresses) to use it.
The bounds that used to say 123 now say %(n)d, and still refuse 123 itself.

Limits that stay (read docs/limits.md):
  * a team record stores its league slot in 7 bits (+0x41c & 0x7f), so a club whose
    LEAGUE is on a slot >= 128 gets team.slot = 7, exactly what the game already does for
    a league with no row.  Put leagues on 0..122 / 124..127; slots 128..%(last)d are fine for
    cups and other competitions.
  * slot 123 stays unusable.
  * a Master League career keeps its own copy of the region: start a NEW career after
    installing, and do not load a career made with this module without it.

Load order: this module touches no byte fl26caps touches, and its page is not fl26caps'
page, so the order does not matter.  Needs luajit.ext.enabled = 1 in sider.ini.

Install:
  1. copy this file to <game>\\SiderAddons\\modules\\fl26slots%(n)d.lua
  2. add to sider.ini:   lua.module = "fl26slots%(n)d.lua"
  3. start the game and read sider.log
--]]
"""


def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    n = int(a[0]) if a else 250
    if "--big" in sys.argv:
        # the two all-club slots sized for a bigger club table (2400 with the lim2400 layout):
        # every other slot pays for it out of the same fixed region
        big = int(sys.argv[sys.argv.index("--big") + 1])
        BIG[79] = BIG[80] = big
    out = (sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv
           else os.path.join(HERE, "fl26slots%d.lua" % n))
    d = open(EXE, "rb").read()
    secs = sections(d)
    L = layout(n)

    # 1. the accessors must be exactly what was read
    for k, (va, h) in ACC.items():
        got = d[offset_of(secs, va):offset_of(secs, va) + len(h) // 2].hex()
        if got != h:
            raise SystemExit("%s at 0x%x is %s, expected %s" % (k, va, got, h))
    if d[offset_of(secs, TEAMSLOT):offset_of(secs, TEAMSLOT) + 13].hex() != TEAMSLOT_OLD:
        raise SystemExit("team-slot stub moved")
    if d[offset_of(secs, BUILDER_N):offset_of(secs, BUILDER_N) + 5].hex() != "ba7b000000":
        raise SystemExit("builder count moved")
    disp = struct.unpack_from("<i", d, offset_of(secs, 0x1414d6302))[0]
    assert 0x1414d6306 + disp == FILL_SRC

    tables, stubs, jumps, imms, ranges = [], [], [], [], []
    tables.append((OFF_TAB, "00" * 4 * n, b"".join(struct.pack("<I", x) for x in L["offs"]).hex(),
                   "first entry of each slot's list (dword index into the region)"))
    tables.append((CAP_TAB, "00" * 4 * n, b"".join(struct.pack("<I", x) for x in L["caps"]).hex(),
                   "capacity of each slot (slot 123 = 0)"))

    at = CODE
    acc = accessor_stubs(n, L, at)
    for k in ("get", "count", "set", "setcount"):
        va = ACC[k][0]
        stubs.append((at, "00" * len(acc[k]), acc[k].hex(), "%s accessor body, table driven" % k))
        jumps.append((va, ACC[k][1][:10], ("e9" + rel32(va + 5, at).hex()),
                      "%s accessor 0x%x -> its new body at 0x%x (entry address kept)" % (k, va, at)))
        ranges.append((va, 5))
        at += len(acc[k])
        at = (at + 15) & ~15

    # clear: four immediates, the code stays where it is
    for va, oldv, newv, w in [
            (0x1414d62e5, 0x7b, 1, "clear: one pass over all lists instead of 123 x 750"),
            (0x1414d62f2, 0x2ee, L["listdw"], "clear: %d list dwords" % L["listdw"]),
            (0x1414d631e, OLD_CNT, L["cnt"], "clear: counts at +0x%x" % L["cnt"]),
            (0x1414d6326, 0xf6, 2 * n, "clear: %d counts" % n)]:
        o = offset_of(secs, va)
        if struct.unpack_from("<I", d, o)[0] != oldv:
            raise SystemExit("clear immediate at 0x%x" % va)
        imms.append((va, struct.pack("<I", oldv).hex(), struct.pack("<I", newv).hex(), w))
        ranges.append((va, 4))

    # builder: one heap vector per slot
    imms.append((BUILDER_N + 1, struct.pack("<I", 0x7b).hex(), struct.pack("<I", n).hex(),
                 "slot-list builder 0x1414f6e20: %d slot vectors (mov edx,0x7b)" % n))
    ranges.append((BUILDER_N + 1, 4))

    # compare/branch sites
    for va, kind, why in SITES:
        stub, jump, used, rng = site_patch(d, secs, va, kind, n, at, why)
        stubs.append(stub)
        jumps.append(jump)
        ranges.append(rng)
        at = (at + used + 15) & ~15

    # team slot (.impdata): keep 0..127 except 123, everything else 7
    tmax = min(n, 1 << TEAMSLOT_BITS)
    a = Asm(at)
    a.b("b907000000")                 # mov ecx,7
    a.b("83f87b"); a.j8(0x74, "K")    # 123 -> 7
    a.b("3d" + struct.pack("<I", tmax).hex()); a.j8(0x7d, "K")   # signed, like cmovl
    a.b("89c1")                       # mov ecx,eax
    a.label("K"); a.b("89c8")         # mov eax,ecx
    a.jabs("e9", TEAMSLOT_BACK)
    ts = a.build()
    stubs.append((at, "00" * len(ts), ts.hex(),
                  "team slot: slot < %d and != 123 kept, otherwise 7 (7-bit field +0x41c)" % tmax))
    site = b"\xe9" + rel32(TEAMSLOT + 5, at) + b"\x90" * 8
    jumps.append((TEAMSLOT, TEAMSLOT_OLD, site.hex(),
                  ".impdata 0x144acace0: cmp eax,0x7b / mov ecx,7 / cmovl / mov eax,ecx -> stub 0x%x" % at))
    ranges.append((TEAMSLOT, 13))
    at += len(ts)
    if at > OFF_TAB:
        raise SystemExit("stubs overflow into the tables")

    # 2. checks
    for va, oldh, newh, w in stubs + jumps + imms + tables:
        if va >= PAGE:
            continue
        o = offset_of(secs, va)
        if d[o:o + len(oldh) // 2].hex() != oldh:
            raise SystemExit("0x%x: file bytes are not %s" % (va, oldh))
    for va, oldh, newh, w in jumps:                      # rel32 reach to our page
        if newh.startswith("e9"):
            tgt = va + 5 + struct.unpack("<i", bytes.fromhex(newh[2:10]))[0]
            assert PAGE <= tgt < PAGE + 0x1000, hex(va)
    problems = []
    for va, total in ranges:
        if va < PAGE and total > 1:
            for hit in branches_into(d, secs, va, total):
                problems.append("branch into 0x%x+%d from 0x%x (%s 0x%x)" % ((va, total) + hit))
    overlap = []
    for f, (rs, lits) in lua_ranges().items():
        if os.path.basename(f).startswith("fl26slots"):
            continue
        for pva, plen in rs:
            for va, total in ranges:
                if pva < va + total and va < pva + max(plen, 1):
                    overlap.append("%s: 0x%x+%d overlaps ours 0x%x+%d"
                                   % (os.path.basename(f), pva, plen, va, total))
        for lv in lits:
            for va, total in ranges:
                if va <= lv < va + total:
                    overlap.append("%s mentions 0x%x inside ours 0x%x+%d"
                                   % (os.path.basename(f), lv, va, total))
    if problems or overlap:
        print("\n".join(problems + overlap))
        raise SystemExit("refusing to write: see above")

    patches = tables + stubs + jumps + imms          # tables and stubs before the jumps
    body = "\n".join('  {va=0x%x, old="%s", new="%s",\n   why="%s"},' % p for p in patches)
    tmpl = open(os.path.join(SIDER, "fl26caps.template.lua"), encoding="utf-8").read()
    tail = tmpl[tmpl.index("local PAGES"):]
    summary = ("competition slots 123 -> %d (slot 123 kept as sentinel), per-slot capacity "
               "%d, slots 79/80 %d, %d patches" % (n, L["per"], BIG[79], len(patches)))
    tail = (tail.replace("--[[PAGES]]", "0x%x" % PAGE)
                .replace("--[[SET]]", "slots%d" % n)
                .replace("--[[SUMMARY]]", summary)
                .replace("fl26caps_VirtualAlloc", "fl26slots_VirtualAlloc")
                .replace("fl26caps", "fl26slots"))
    doc = DOC % dict(n=n, summary=summary, page=PAGE, big=BIG[79], per=L["per"], last=n - 1)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(doc + "\nlocal m = {}\n\nlocal patches = {\n" + body + "\n}\n\n" + tail)
    print("wrote %s: %d patches; lists %d dwords (used %d), counts at +0x%x..+0x%x, "
          "per slot %d, 79/80 %d, page used 0x%x bytes of code"
          % (out, len(patches), L["listdw"], L["used"], L["cnt"], L["cnt"] + 2 * n,
             L["per"], BIG[79], at - CODE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
