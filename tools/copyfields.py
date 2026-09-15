"""python copyfields.py [--json <file>]  -> every field reference in the mode copy

The first attempt at this listed only the fields whose offsets the copy's constructor
spells out as loop bases -- eight of them.  Patching just those shifted part of the object
and left the rest behind, and the game died the moment Master League finished loading.
The copy has far more fields than the constructor names.

So this does not look for known constants at all.  It follows the copy pointer instead.
The copy arrives in rcx at each of these functions, and every register it is copied into
holds it too; anything else written to a register takes it out of the set.  A memory
operand or an add on a register that holds the copy is a field of the copy, whatever its
offset happens to be, and that is the complete list by construction.

`lea rX, [copy + n]` deliberately does *not* leave rX holding the copy: it holds a pointer
into one array, and treating it as the copy again would drag in every record offset within
that array.
"""
import json, os, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_64, CsError
from capstone.x86 import X86_OP_MEM, X86_OP_IMM, X86_OP_REG, X86_REG_RIP
import flpaths

TEXT_VA, TEXT_OFF = 0x140001000, 0x600

# Functions that take the copy object in rcx.  The first six carry a manual verdict of
# "copy" in patches/attrib-manual.json; the rest are the copy's own code, reached from the
# two allocation sites at 0x140afbe06 and 0x140af1baa.
FUNCS = [0x140af30f0, 0x140afd660, 0x1413fea10, 0x1413feda0,
         0x1414007c0, 0x141400940, 0x141400bb0, 0x141401060, 0x1414013a0,
         0x1414016b0, 0x141401c10, 0x141402100]

TEAM_BASE = 0x50
MAX_FN = 0x4000


def ops_of(i):
    try:
        return i.operands
    except CsError:
        return []


def written(i):
    """registers this instruction writes, as capstone reports them"""
    try:
        _, regs_write = i.regs_access()
        return set(regs_write)
    except CsError:
        return set()


def walk(d, md, entry):
    o = lambda va: va - TEXT_VA + TEXT_OFF
    stream = md.disasm(d[o(entry):o(entry) + MAX_FN], entry)
    holds = {"rcx"}
    out = []
    rets = 0
    for i in stream:
        text = "%s %s" % (i.mnemonic, i.op_str)
        ops = ops_of(i)

        for op in ops:
            if op.type == X86_OP_MEM and op.mem.base != X86_REG_RIP and op.mem.disp >= TEAM_BASE:
                b = i.reg_name(op.mem.base) if op.mem.base else None
                if b in holds:
                    out.append(dict(va="0x%x" % i.address, fn="0x%x" % entry,
                                    value="0x%x" % op.mem.disp, how="disp",
                                    reg=b, text=text))
        if i.mnemonic in ("add", "sub") and len(ops) == 2 \
                and ops[0].type == X86_OP_REG and ops[1].type == X86_OP_IMM \
                and ops[1].imm >= TEAM_BASE and i.reg_name(ops[0].reg) in holds:
            out.append(dict(va="0x%x" % i.address, fn="0x%x" % entry,
                            value="0x%x" % ops[1].imm, how="add",
                            reg=i.reg_name(ops[0].reg), text=text))

        # propagate
        if i.mnemonic == "mov" and len(ops) == 2 and ops[0].type == X86_OP_REG \
                and ops[1].type == X86_OP_REG:
            src, dst = i.reg_name(ops[1].reg), i.reg_name(ops[0].reg)
            if src in holds:
                holds.add(dst)
                continue
        for r in written(i):
            holds.discard(i.reg_name(r))

        if i.mnemonic == "ret":
            rets += 1
            if rets > 24:
                break
    return out


def main():
    d = open(flpaths.need_exe(), "rb").read()
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    md.detail = True
    md.skipdata = True

    sites, seen = [], set()
    for fn in FUNCS:
        for s in walk(d, md, fn):
            k = (s["va"], s["value"])
            if k in seen:
                continue
            seen.add(k)
            sites.append(s)
    sites.sort(key=lambda s: int(s["va"], 16))

    vals = sorted({int(s["value"], 16) for s in sites})
    print("%d references to %d distinct offsets" % (len(sites), len(vals)))
    print("lowest 0x%x, highest 0x%x" % (vals[0], vals[-1]))
    print("\noffsets:")
    line = []
    for v in vals:
        line.append("0x%x" % v)
        if len(line) == 8:
            print("  " + " ".join("%-11s" % x for x in line))
            line = []
    if line:
        print("  " + " ".join("%-11s" % x for x in line))
    print("\nreferences:")
    for s in sites:
        print("  %s  fn %-12s %-11s %-5s %s"
              % (s["va"], s["fn"], s["value"], s["how"], s["text"]))

    if "--json" in sys.argv:
        p = sys.argv[sys.argv.index("--json") + 1]
        json.dump(sites, open(p, "w"), indent=1)
        print("\nwrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
