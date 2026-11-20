"""python lowertail.py  -> patches/lower-tail-sites.json

The lower tail is everything the block carries above the player array's shipped end and
below its old end: the players' dummy record at 0x184c3bc, the table at 0x184c538, the
group set at 0x184db1c, the object at 0x186b030 and the cluster that runs up to
0x186cec8.  The player array grows in place from +0, so once its cap passes the shipped
30001 records every one of those offsets is inside the array: the game writes player
records over them and then reads its own structures out of that memory (the crash of
2026-10-27 at 0x1414d688b is exactly this, `base[10]` read out of a player's name bytes).
So the whole span has to move to the grown block, and every real operand that names an
offset inside it has to move with it.

tailscan.py finds those by decoding every function and keeping only real operands, which
is the only filter that survives the arithmetic coincidence problem: a raw byte search of
[0x184c3bc, 0x1877068) returns hundreds of values against ~300 expected from chance.
This wraps that scan, drops the two false positives that decoding alone cannot tell from
a displacement, and writes the list the generator patches from.

    python lowertail.py           rescan and rewrite the list
    python lowertail.py --check   only report whether the list still matches the scan
"""

import json, os, sys

import tailscan

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LAYOUT = json.load(open(os.path.join(ROOT, "patches", "layout.json")))
H = lambda s: int(s, 16) if isinstance(s, str) else s

TAIL = LAYOUT["block"]["lower_tail"]
LO, HI = H(TAIL["start"]), H(TAIL["end"])
OUT = os.path.join(ROOT, TAIL["sites_file"])

# Two operands in the span are not block offsets.  Both sit in 0x141854f10, which reads a
# byte table and a jump table in .trace through the image base -- `[r9 + rcx + 0x1855004]`
# and `[r9 + rcx*4 + 0x1854ffc]` -- and the scan's scale-4 rule rejects the second but not
# the first, which has no index scale at all.  0x1870f98 is a bit mask: `and eax, 0x1870f98`
# clears the flags of an eax that happens to hold a number, and it is not an address.
FALSE_POSITIVES = {
    "0x141854fbb": "an .trace byte table reached through the image base, not the block",
    "0x1404106ef": "a bit mask (`and eax, 0x1870f98`), not a displacement",
    # 2026-11-06: immediates that only look like tail offsets. Moving 0x1800000 in the player
    # packer 0x1412e3b30 (field 7, `and eax, 0x1800000` after `shl eax, 0x17`) made it clear
    # bits 12-14 of the save entry's +0x14, so after save -> load every position was pos & 1
    "0x1412e40d7": "a bit mask (player field 7 in the save packer), not a displacement",
    "0x141402ce8": "a bit mask (player field 7 setter, `shl eax, 0x17`), not a displacement",
    "0x14145dd67": "a bit mask (`and eax, 0x1800000; cmp eax, 0x1800000`), not a displacement",
    "0x14145dd6c": "a bit mask compare (`and eax, 0x1800000; cmp eax, 0x1800000`), not a displacement",
    "0x1414cd1cf": "a bit field compare (after `and eax, 0x1f800000`), not a displacement",
    "0x1414cff05": "a bit field compare (after `and ecx, 0x1f800000`), not a displacement",
    "0x140f87b22": "a bit field compare (after `and eax, 0x1fc0000`), not a displacement",
    "0x1406b17ab": "a `bt` case mask (switch on edx - 0x834), not a displacement",
    "0x1406b18ce": "a `bt` case mask like 0x1406b17ab, not a displacement",
    "0x1406b193e": "a `bt` case mask like 0x1406b17ab, not a displacement",
    "0x1415d4b79": "an allocation size (24 MB), not a displacement",
    "0x1415d4bb5": "an allocation size (24 MB), not a displacement",
    "0x14235c9d7": "an allocation size (24 MB), not a displacement",
    "0x141621761": "a heap size in a constructor, not a displacement",
    "0x141621768": "a heap size in a constructor, not a displacement",
    "0x1418f9bd2": "a size argument to an API call, not a displacement",
    "0x1418fa3f4": "a size argument to an API call, not a displacement",
    "0x1418fac6a": "a size argument to an API call, not a displacement",
    "0x14167ad9f": "a constant (0x1800019), not a displacement",
    "0x14167ade4": "a constant (0x1800019) stored as data, not a displacement",
    # 2026-11-06 audit B: entries of two .trace switch tables (RVAs read as
    # `mov ecx, [image base + rcx*4 + 0x1814ba4]; jmp rcx`) that capstone decoded as `add [r], imm`
    "0x141814ba5": "a jump-table entry (table 0x141814ba4, RVA 0x1814b90), not code",
    "0x141814bad": "a jump-table entry (table 0x141814ba4, RVA 0x1814b90), not code",
    "0x141814bb5": "a jump-table entry (table 0x141814ba4, RVA 0x18149c4), not code",
    "0x141814bc2": "a jump-table entry (table 0x141814ba4, RVA 0x1814ab1), not code",
    "0x14181783a": "a jump-table entry (table 0x141817830, RVA 0x1817670), not code",
    "0x141817852": "a jump-table entry (table 0x141817830, RVA 0x181776b), not code",
    # 0x17d7840 = 25,000,000: `mov ecx, 25000000; sub rcx, [table]` and a config struct field
    "0x1418d4469": "the number 25,000,000, not a displacement",
    "0x1418d455a": "the number 25,000,000, not a displacement",
    "0x1418dc9ec": "the number 25,000,000, not a displacement",
    "0x1418e291a": "the number 25,000,000, not a displacement",
    "0x1418e36ce": "the number 25,000,000, not a displacement",
    "0x141481676": "the number 25,000,000 in a config struct (next to 27,000,000), not a displacement",
    # bytes after a protector stub's jmp or before a function's start: junk, never executed
    "0x140eef2c6": "junk bytes in a protector stub, not code",
    "0x1419ff527": "junk bytes in a protector stub, not code",
    "0x1414d756c": "junk bytes in a protector stub, not code",
    "0x141507ac4": "junk bytes in a protector stub, not code",
    "0x141140616": "junk bytes before the function at 0x141140621, not code",
}


# Arrays inside the span that a family of their own relocates: their operands are already
# patched there, and moving them here as well would move them twice.  Since 2026-11-04 the
# span starts at the calendar's end (0x16705a8) and so holds the match flags.
RELOCATED = [
    (H(LAYOUT["arrays"][n]["base_old"]),
     H(LAYOUT["arrays"][n]["base_old"]) + LAYOUT["arrays"][n]["cap_old"] * H(LAYOUT["arrays"][n]["stride"]))
    for n in ("matchflags",)
    if LO <= H(LAYOUT["arrays"][n]["base_old"]) < HI
]


def scan():
    tailscan.TAIL_LO, tailscan.TAIL_HI = LO, HI
    # off: with it every operand above the head counts as a constant, and the tail's offsets are
    # all above it. Its span is .trace's RVAs too; a table read as [image base + i + rva] is
    # rejected by scan itself (the base register is tracked)
    tailscan.TRACE_FILTER = False
    sites, _, _ = tailscan.scan()
    out = []
    for s in sites:
        if s["va"] in FALSE_POSITIVES:
            continue
        if any(lo <= H(s["value"]) < hi for lo, hi in RELOCATED):
            continue
        out.append(
            {
                "va": s["va"],
                "at": s["at"],
                "value": s["value"],
                "func": s["func"],
                "text": s["text"],
            }
        )
    out.sort(key=lambda s: (H(s["value"]), H(s["va"])))
    return out


def scaled():
    """the offsets in the span that the code carries divided by a scale

    An entry of the user's club table (block+0x1798ab0 + 0x83700, 40 entries of 0x18) is
    reached as `lea rcx, [rax + 0x1798ab]; lea rcx, [rax + rcx*2]; lea rcx, [rsi + rcx*8]`:
    24 * i + 16 * 0x1798ab, the club's offset folded into the index arithmetic.  No operand
    names 0x1798ab0, so scan() cannot see it, and an unmoved one reads the table where the
    team table sits now -- 2026-11-05, FL27 at 120k players died making a new ML at
    0x14132aba7 because the lookup 0x1413281d0 found the user's player in a table nobody had
    filled.  Three shapes, each a `lea` whose displacement times the scale lands in the span:

        lea rA, [rB + K]; lea rA, [rB + rA*2]; lea rX, [rY + rA*8]    16 * K
        lea rA, [rB + K]; lea rA, [rA + rA*2]; lea rX, [rY + rA*8]    24 * K
        lea rA, [rA + K]; lea rX, [rY + rA*8]                          8 * K

    The generator moves each by delta / scale, so the delta has to be a multiple of all three.
    """
    from capstone.x86 import (X86_INS_LEA, X86_INS_ADD, X86_OP_MEM, X86_OP_REG, X86_OP_IMM,
                              X86_REG_RIP, X86_REG_INVALID)

    def mem(ins):
        if ins.id != X86_INS_LEA or len(ins.operands) != 2 or ins.operands[1].type != X86_OP_MEM:
            return None
        return ins.operands[0].reg, ins.operands[1].mem

    def add_imm(a):
        # `add rA, K` with rA a 64-bit register
        if a.id != X86_INS_ADD or len(a.operands) != 2:
            return None
        o0, o1 = a.operands
        if o0.type != X86_OP_REG or o1.type != X86_OP_IMM or o0.size != 8:
            return None
        return o0.reg, o1.imm

    out = []
    for f in tailscan.FS:
        blob = tailscan.d[tailscan.off_of(f) : tailscan.off_of(tailscan.func_end(f))]
        ins = [i for i in tailscan.md.disasm(blob, f) if i.id != 0]
        for k, a in enumerate(ins):
            # 2026-11-06 (audit B): the same folding with an `add` instead of a lea --
            #   add rax, 0x3098a7; lea rdx, [rcx + rax*8]               8 * K  (0x1414f762d)
            #   add rdx, 0x5e1eb5; lea rdx, [rax + rdx*4]               4 * K  (0x140adfa38)
            #   add rcx, K; lea rcx, [rcx + rsi*4]; lea rcx, [r14 + rcx*4]   4 * K (0x14132e134)
            # 0x1414f762d is the end of a table whose begin (block+0x184c538) is moved, so an
            # unmoved end handed the sort after it a count off by the whole delta.
            ad = add_imm(a)
            if ad:
                ra, K = ad
                n1 = mem(ins[k + 1]) if k + 1 < len(ins) else None
                n2 = mem(ins[k + 2]) if k + 2 < len(ins) else None
                scale = None
                if n1 and n1[1].index == ra and n1[1].scale in (4, 8) and n1[1].base != ra:
                    scale = n1[1].scale
                elif (n1 and n1[0] == ra and n1[1].base == ra and n1[1].index not in (ra, X86_REG_INVALID)
                      and n2 and n2[1].index == ra and n2[1].scale in (4, 8) and n2[1].base != ra):
                    scale = n2[1].scale
                if scale and LO <= K * scale < HI:
                    out.append(
                        {
                            "va": "0x%x" % a.address,
                            "at": tailscan.const_offset(a, K),
                            "value": "0x%x" % K,
                            "scale": scale,
                            "names": "0x%x" % (K * scale),
                            "func": "0x%x" % f,
                            "text": "%s %s" % (a.mnemonic, a.op_str),
                        }
                    )
                continue
            m = mem(a)
            if not m or m[1].base == X86_REG_RIP or m[1].index != X86_REG_INVALID:
                continue
            ra, ma = m
            K = ma.disp
            n1 = mem(ins[k + 1]) if k + 1 < len(ins) else None
            n2 = mem(ins[k + 2]) if k + 2 < len(ins) else None
            last = lambda n: n and n[1].index == ra and n[1].scale == 8
            scale = None
            if n1 and n1[0] == ra and n1[1].index == ra and n1[1].scale == 2 and last(n2):
                scale = 24 if n1[1].base == ra else 16 if n1[1].base == ma.base else None
            elif ma.base == ra and last(n1) and n1[1].base != ra:
                scale = 8
            if not scale or not (LO <= K * scale < HI):
                continue
            out.append(
                {
                    "va": "0x%x" % a.address,
                    "at": tailscan.const_offset(a, K),
                    "value": "0x%x" % K,
                    "scale": scale,
                    "names": "0x%x" % (K * scale),
                    "func": "0x%x" % f,
                    "text": "%s %s" % (a.mnemonic, a.op_str),
                }
            )
    out.sort(key=lambda s: (H(s["names"]), H(s["va"])))
    return out


def main(argv):
    sites = scan()
    scaled_sites = scaled()
    doc = {
        "_comment": [
            "generated by tools/lowertail.py -- every real operand in block.lower_tail",
            "the generator shifts each one by one delta, so the whole span keeps its",
            "internal layout; nothing here is typed by hand",
        ],
        "range": ["0x%x" % LO, "0x%x" % HI],
        "sites": sites,
        "scaled": scaled_sites,
        "excluded": [{"va": k, "why": v} for k, v in sorted(FALSE_POSITIVES.items())],
    }
    text = json.dumps(doc, indent=1)
    if "--check" in argv:
        cur = open(OUT).read() if os.path.exists(OUT) else ""
        print(
            "%d sites, list %s"
            % (len(sites), "matches" if cur.strip() == text.strip() else "DIFFERS")
        )
        return 0 if cur.strip() == text.strip() else 1
    open(OUT, "w").write(text)
    print(
        "%d sites + %d scaled in 0x%x..0x%x, %d excluded; wrote %s"
        % (len(sites), len(scaled_sites), LO, HI, len(FALSE_POSITIVES), OUT)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
