r"""python tailscan.py [--review] [out.json]  -> who reaches the calendar's trailing neighbours

calstride.py surveyed the calendar itself: 365 days of 0x2c4 at edit block +0x16038a8, and
the sites that reach them.  Widening a day means growing that array, and 0x1413fbf60 -- the
one function that copies the calendar between the block and the mode copy -- keeps a single
`rsi = src - dst` for the days AND for what sits directly above them:

    +0x1642a1c   four small fields, the current day among them
    +0x1642a28   32 records of 0x16dc
    =+0x16705a8  the end of the unit the copier treats as one piece

So the trailing part has to move with the calendar, and whatever reaches it *by its own block
offset* -- rather than off the calendar base, which calstride.py already has -- has to be
found first.  attrib.json has nothing in that range, and a raw byte search there returns 1,617
distinct values over 2,785 occurrences against roughly 1,700 expected from chance, so it
cannot tell a displacement from a coincidence.

This decodes instead.  Every function is disassembled and only real 32-bit operands count: an
immediate, or a memory displacement, whose value lands inside the range.  A coincidence in the
middle of some other instruction is not an operand and does not survive that.  The stride
0x16dc and the record count 32 are reported alongside, because a walker of the 32 records
reaches the base once and then steps by the stride, and only the base has to be rewritten.

    --review   what was found, by value and by function
    out.json   the sites, in the shape calendar-sites.json uses
"""
import sys, json, bisect, struct, collections
from capstone import *
from capstone.x86 import *
import callindex

TAIL_LO, TAIL_HI = 0x1642a1c, 0x16705a8
CAL = 0x16038a8
REC_BASE, REC_STRIDE, REC_COUNT = 0x1642a28, 0x16dc, 32

d, nm, sva, ro, rsz = callindex.code_section()
off_of = lambda va: ro + (va - sva)
FS = sorted(f for f in callindex.starts() if sva <= f < sva + rsz)
md = Cs(CS_ARCH_X86, CS_MODE_64); md.detail = True; md.skipdata = True


def func_end(f):
    i = bisect.bisect_right(FS, f)
    return FS[i] if i < len(FS) else sva + rsz


def const_offset(ins, value):
    want = struct.pack("<I", value & 0xffffffff)
    hits = [i for i in range(max(0, len(ins.bytes) - 3)) if bytes(ins.bytes[i:i + 4]) == want]
    return hits[-1] if hits else None


HEAD_HI = 0x1642a34        # the four fields and the first record's first fields


def reject(ins, op, v):
    """why this operand is not a block offset, or None if it is one"""
    if v >= HEAD_HI:
        # The numeric range overlaps .trace, whose RVAs start 0x164... too. Everything found
        # above the head so far is one of two things, and neither is a block offset:
        if op.type == X86_OP_MEM and op.mem.index != 0 and op.mem.scale == 4:
            return "a jump table in .trace, reached as image base + rva + i*4"
        return "a constant, not a displacement (%s)" % ins.mnemonic
    return None


def scan():
    tail, strides, rejects = [], [], []
    for f in FS:
        blob = d[off_of(f):off_of(func_end(f))]
        for ins in md.disasm(blob, f):
            if ins.id == 0:
                continue
            for op in ins.operands:
                v = None
                # rip-relative is a *relative* displacement into the image, not a block
                # offset -- 557 calls and leas into the import area land in this range by
                # arithmetic and mean nothing here.
                if op.type == X86_OP_IMM and TAIL_LO <= op.imm < TAIL_HI:
                    v = op.imm
                elif op.type == X86_OP_MEM and op.mem.base != X86_REG_RIP                         and TAIL_LO <= op.mem.disp < TAIL_HI:
                    v = op.mem.disp
                if v is None:
                    continue
                at = const_offset(ins, v)
                if at is None:
                    continue
                rec = {"va": "0x%x" % ins.address, "at": at, "func": "0x%x" % f,
                       "value": "0x%x" % v, "kind": "tail",
                       "text": "%s %s" % (ins.mnemonic, ins.op_str)}
                why = reject(ins, op, v)
                if why:
                    rec["kind"], rec["why"] = "rejected", why
                    rejects.append(rec)
                else:
                    tail.append(rec)
            if ins.id == X86_INS_IMUL and len(ins.operands) == 3 \
                    and ins.operands[2].type == X86_OP_IMM \
                    and ins.operands[2].imm == REC_STRIDE:
                at = const_offset(ins, REC_STRIDE)
                strides.append({"va": "0x%x" % ins.address, "at": at, "func": "0x%x" % f,
                                "value": "0x%x" % REC_STRIDE, "kind": "rec_stride",
                                "text": "%s %s" % (ins.mnemonic, ins.op_str)})
    return tail, strides, rejects


def main(argv):
    tail, strides, rejects = scan()
    if "--review" in argv:
        print("  range  0x%x .. 0x%x   (the four fields, then %d records of 0x%x)"
              % (TAIL_LO, TAIL_HI, REC_COUNT, REC_STRIDE))
        print("  operand sites in range: %d, in %d function(s)"
              % (len(tail), len(set(s["func"] for s in tail))))
        by = collections.Counter(s["value"] for s in tail)
        for v, n in sorted(by.items(), key=lambda kv: int(kv[0], 16)):
            print("    %-12s %d" % (v, n))
        print("")
        for s in tail:
            print("  %-12s +%d  %-12s in %-12s %s"
                  % (s["va"], s["at"], s["value"], s["func"], s["text"][:60]))
        print("")
        print("  imul ..., 0x%x sites: %d  (the stride does not change; these are here so a"
              % (REC_STRIDE, len(strides)))
        print("     reader can see the 32 records are walked, not addressed one by one)")
        for s in strides:
            print("  %-12s in %-12s %s" % (s["va"], s["func"], s["text"][:60]))
        print("")
        print("  rejected: %d" % len(rejects))
        for s in rejects:
            print("  %-12s %-12s %-46s %s"
                  % (s["va"], s["value"], s["text"][:46], s["why"]))
        return 0
    out = {"_comment": "generated by tailscan.py -- the calendar's trailing neighbours",
           "range": ["0x%x" % TAIL_LO, "0x%x" % TAIL_HI],
           "sites": tail, "stride_walks": strides, "rejected": rejects}
    dst = [a for a in argv[1:] if not a.startswith("--")]
    js = json.dumps(out, indent=1)
    if dst:
        open(dst[0], "w").write(js)
    else:
        print(js)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
