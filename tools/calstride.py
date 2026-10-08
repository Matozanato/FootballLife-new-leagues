"""python calstride.py [out.json] [--review]  -> every site that must change to widen a day

The season calendar is 365 records of 0x2c4 bytes at edit block +0x16038a8: a day's match
ids from +0x00 (0x230 bytes, 280 of them), the count at +0x230, and 18 event slots of 8
bytes from +0x234.  The scheduler at 0x141350290 refuses to write a 281st id -- `cmp eax,
0x118` -- and with 39 new leagues the busiest day already holds 233, so the list is the
next wall.  There is no slack: the record ends exactly where the current-day field begins
(0x1642a1c), so widening the list means growing the stride and relocating the calendar.

That touches five kinds of site, and this walks the code to find them rather than trusting
the constants, because 0x230 and 0x118 are ordinary numbers that also appear in unrelated
structures inside the very same functions -- `call 0x1414bb000` then `cmp dword ptr [rax +
0x230], 1` turns up in eight of them and has nothing to do with the calendar.

For each function that mentions the calendar base, a register is tagged CAL when it is
loaded with `<any> + 0x16038a8`, and stays CAL through a move, through a spill and its
reload, or through `add cal, stride` where stride came from `imul r, i, 0x2c4`.  The tags
are carried to a fixpoint over the function's flow graph, merging at joins, because a
linear sweep gets this wrong: in 0x141315fd0 the early-return path holds `mov r13, [rsp +
0x28]`, which restores the caller's r13 and, read in order, makes every later day-record
field look like an unrelated pointer.  Blocks the graph never reaches -- a jump table's
targets above all -- are analysed from no assumptions rather than skipped, so a constant
inside them is still found.

A memory operand whose base or index is CAL is then a day-record field, and the
displacement says which:

    0x000..0x22f   an id in the list          (unchanged: the list still starts at +0)
    0x230          the count                  -> the new count offset
    0x234..0x2c3   an event slot              -> shifted by the same amount
    0x3f174 and up the fields after the calendar, reached off its base: the current day,
                   and two more at +0x3f178 and +0x3f17c

Where the taint does not arrive -- a pointer reloaded from a field, a block reached only
through a jump table -- a second pass falls back to the shape of the access, but only
inside a function the first pass already proved walks the calendar, and only for a *word*
at +0x230 or anything in the event range off a non-frame register.  Those sites are marked
`"by": "shape"` so a reviewer can tell them from the ones the taint established.  What is
left over is printed by --review; at the time of writing that is fourteen instances of the
0x1414bb000 idiom and nothing else.

`imul r, i, 0x2c4` is the stride and `cmp r, 0x118` the id cap.  Every site carries the
byte offset of its constant inside the instruction, so a patch can rewrite it in place, and
the text it was read from, so a reviewer can check it.
"""
import sys, json, bisect, collections, struct
from capstone import *
from capstone.x86 import *
import callindex

CAL = 0x16038a8
STRIDE = 0x2c4
DAYS = 365
COUNT, EVENTS, IDCAP = 0x230, 0x234, 0x118
TODAY = DAYS * STRIDE                      # 0x3f174, reached off the calendar base

d, nm, sva, ro, rsz = callindex.code_section()
off_of = lambda va: ro + (va - sva)
FS = sorted(f for f in callindex.starts() if sva <= f < sva + rsz)
md = Cs(CS_ARCH_X86, CS_MODE_64); md.detail = True; md.skipdata = True


def func_end(f):
    i = bisect.bisect_right(FS, f)
    return FS[i] if i < len(FS) else sva + rsz


def funcs_touching_base():
    """functions with an instruction whose disp32 or imm32 is the calendar base"""
    needle = struct.pack("<I", CAL)
    out = set()
    for f in FS:
        blob = d[off_of(f):off_of(func_end(f))]
        if needle not in blob:
            continue
        for ins in md.disasm(blob, f):
            if ins.id == 0:
                continue
            for op in ins.operands:
                if (op.type == X86_OP_IMM and op.imm == CAL) or \
                   (op.type == X86_OP_MEM and op.mem.disp == CAL):
                    out.add(f)
    return sorted(out)


def const_offset(ins, value):
    """byte offset of the 32-bit `value` inside the instruction's encoding, or None"""
    want = struct.pack("<I", value & 0xffffffff)
    hits = [i for i in range(max(0, len(ins.bytes) - 3)) if bytes(ins.bytes[i:i + 4]) == want]
    return hits[-1] if hits else None


SCRATCH = (X86_REG_RAX, X86_REG_RCX, X86_REG_RDX, X86_REG_R8, X86_REG_R9,
           X86_REG_R10, X86_REG_R11)


FRAME = (X86_REG_RBP, X86_REG_RSP)


def step(ins, tag, slot):
    """the transfer function: how one instruction changes the tags"""
    ops = ins.operands

    # a spill and its reload: the day pointer is routinely parked on the frame across a
    # call, and without this the reload looks like an unrelated pointer
    if ins.id == X86_INS_MOV and len(ops) == 2:
        if ops[0].type == X86_OP_MEM and ops[1].type == X86_OP_REG \
                and ops[0].mem.base in FRAME and ops[0].mem.index == 0:
            k = (ops[0].mem.base, ops[0].mem.disp)
            if tag.get(ops[1].reg):
                slot[k] = tag[ops[1].reg]
            else:
                slot.pop(k, None)
        elif ops[0].type == X86_OP_REG and ops[1].type == X86_OP_MEM \
                and ops[1].mem.base in FRAME and ops[1].mem.index == 0:
            k = (ops[1].mem.base, ops[1].mem.disp)
            if k in slot:
                tag[ops[0].reg] = slot[k]
            else:
                tag.pop(ops[0].reg, None)
            return

    if ins.id == X86_INS_LEA and ops[1].type == X86_OP_MEM:
        m, w = ops[1].mem, ops[0].reg
        if m.disp == CAL or tag.get(m.base) == "CAL" or tag.get(m.index) == "CAL":
            tag[w] = "CAL"
        else:
            tag.pop(w, None)
    elif ins.id == X86_INS_IMUL and len(ops) == 3 and ops[2].type == X86_OP_IMM \
            and ops[2].imm == STRIDE:
        tag[ops[0].reg] = "STRIDE"
    elif ins.id in (X86_INS_ADD, X86_INS_SUB) and len(ops) == 2 and ops[0].type == X86_OP_REG:
        w = ops[0].reg
        if ops[1].type == X86_OP_IMM and ops[1].imm == CAL:
            tag[w] = "CAL"
        elif ops[1].type == X86_OP_REG and {tag.get(w), tag.get(ops[1].reg)} == {"CAL", "STRIDE"}:
            tag[w] = "CAL"
        elif tag.get(w) == "CAL" and ops[1].type == X86_OP_IMM:
            pass                       # add cal, small -- still inside the record
        else:
            tag.pop(w, None)
    elif ins.id == X86_INS_MOV and len(ops) == 2 and ops[0].type == X86_OP_REG:
        w = ops[0].reg
        if ops[1].type == X86_OP_REG and tag.get(ops[1].reg):
            tag[w] = tag[ops[1].reg]
        else:
            tag.pop(w, None)       # a load clears it: `mov r14, [rbp - 0x28]` in 0x141314350
                                   # puts the block pointer back into a register that held a
                                   # day record, and every block field after it looked like
                                   # a calendar field
    if ins.id == X86_INS_CALL:
        for r in SCRATCH:
            tag.pop(r, None)


def successors(ins, lo, hi):
    """where control can go next, inside the function"""
    nxt = ins.address + ins.size
    g = ins.group
    if ins.id == X86_INS_RET or ins.id == X86_INS_INT3:
        return []
    if ins.id == X86_INS_JMP:
        op = ins.operands[0]
        t = op.imm if op.type == X86_OP_IMM else None
        return [t] if t is not None and lo <= t < hi else []
    if g(X86_GRP_JUMP):
        op = ins.operands[0]
        t = op.imm if op.type == X86_OP_IMM else None
        out = [nxt] if nxt < hi else []
        if t is not None and lo <= t < hi:
            out.append(t)
        return out
    return [nxt] if nxt < hi else []


def merge(a, b):
    """what both paths agree on; a tag survives a join only if it is the same on each"""
    return {k: v for k, v in a.items() if b.get(k) == v}


def states(f, lo, hi, code, seed=()):
    """the tag state on entry to every instruction, as a fixpoint over the flow graph

    `seed` is the registers that already hold the calendar base when the function is
    entered -- its arguments, when a caller passed it in.
    """
    entry = {a: (None, None) for a in code}
    run(entry, code, f, lo, hi, seed)
    # blocks the flow graph never reaches -- an indirect jump's targets, a handler, code the
    # linear decode found between functions -- are analysed from no assumptions at all rather
    # than skipped, so a constant inside them is still seen
    for a in sorted(code):
        if entry[a][0] is None:
            run(entry, code, a, lo, hi, seed if a == f else ())
    return entry


def run(entry, code, start, lo, hi, seed=()):
    entry[start] = ({r: "CAL" for r in seed}, {})
    work = [start]
    while work:
        a = work.pop()
        tag, slot = entry[a]
        if tag is None:
            continue
        tag, slot = dict(tag), dict(slot)
        ins = code[a]
        step(ins, tag, slot)
        for s in successors(ins, lo, hi):
            if s not in entry:
                continue
            old_t, old_s = entry[s]
            new_t = tag if old_t is None else merge(old_t, tag)
            new_s = slot if old_s is None else merge(old_s, slot)
            if old_t is None or new_t != old_t or new_s != old_s:
                entry[s] = (new_t, new_s)
                work.append(s)


ARGS = (X86_REG_RCX, X86_REG_RDX, X86_REG_R8, X86_REG_R9)


def walk(f, sites, odd, shape_ok=True, seed=(), passed=None):
    lo, hi = f, func_end(f)
    code = {}
    for ins in md.disasm(d[off_of(lo):off_of(hi)], lo):
        if ins.id != 0:
            code[ins.address] = ins
    entry = states(f, lo, hi, code, seed)
    for a in sorted(code):
        ins = code[a]
        tag = entry[a][0]
        if tag is None:
            continue               # unreachable by the linear decode; nothing to say about it
        ops = ins.operands

        for op in ops:                     # the calendar base itself
            v = op.imm if op.type == X86_OP_IMM else (op.mem.disp if op.type == X86_OP_MEM else None)
            if v == CAL:
                sites.append(dict(kind="base", va="0x%x" % ins.address, func="0x%x" % f,
                                  at=const_offset(ins, CAL),
                                  text="%s %s" % (ins.mnemonic, ins.op_str)))

        # `add cal, 0x2c4` steps to the next day, and `add cal, 0x3f180` reaches the unit's
        # trailing part -- both are immediates, not displacements, so the memory-operand
        # pass never sees them.  0x140af1fb0, the unit's constructor, does both.
        if ins.id == X86_INS_ADD and len(ops) == 2 and ops[0].type == X86_OP_REG                 and ops[1].type == X86_OP_IMM and tag.get(ops[0].reg) == "CAL":
            if ops[1].imm == STRIDE:
                sites.append(dict(kind="stride", va="0x%x" % ins.address, func="0x%x" % f,
                                  at=const_offset(ins, STRIDE),
                                  text="%s %s" % (ins.mnemonic, ins.op_str)))
            elif ops[1].imm >= TODAY:
                sites.append(dict(kind="after", by="taint", disp=ops[1].imm,
                                  va="0x%x" % ins.address, func="0x%x" % f,
                                  at=const_offset(ins, ops[1].imm),
                                  text="%s %s" % (ins.mnemonic, ins.op_str)))

        if ins.id == X86_INS_IMUL and len(ops) == 3 and ops[2].type == X86_OP_IMM \
                and ops[2].imm == STRIDE:
            sites.append(dict(kind="stride", va="0x%x" % ins.address, func="0x%x" % f,
                              at=const_offset(ins, STRIDE),
                              text="%s %s" % (ins.mnemonic, ins.op_str)))

        for op in ops:                     # a day-record field
            if op.type != X86_OP_MEM:
                continue
            m = op.mem
            if m.disp == CAL:
                continue
            by = "taint"
            if tag.get(m.base) != "CAL" and tag.get(m.index) != "CAL":
                # The taint does not reach every block: a jump table's targets are analysed
                # from no assumptions, and a pointer reloaded from a field rather than a frame
                # slot loses it.  Inside a function that demonstrably walks the calendar the
                # shape of the access is enough to tell, because the alternative -- another
                # structure with a word at +0x230 and an 18-slot array of qwords at +0x234 --
                # does not occur.  Frame-relative accesses are locals, and a *dword* at +0x230
                # belongs to the unrelated `cmp dword ptr [rax + 0x230], 1` object that shows
                # up in eight of these functions.
                if m.base in FRAME or m.index in FRAME or not shape_ok:
                    if m.disp in (COUNT, EVENTS, TODAY) and not (m.base in FRAME or m.index in FRAME):
                        odd.append(("untagged", ins.address, f,
                                    "%s %s" % (ins.mnemonic, ins.op_str)))
                    continue
                if m.disp == COUNT and op.size == 2:
                    by = "shape"
                elif EVENTS <= m.disp < STRIDE:
                    by = "shape"
                else:
                    if m.disp in (COUNT, EVENTS, TODAY):
                        odd.append(("untagged", ins.address, f,
                                    "%s %s" % (ins.mnemonic, ins.op_str)))
                    continue
            if m.disp == COUNT:
                k = "count"
            elif m.disp >= TODAY:
                k = "after"                # a block field past the calendar, reached off its
                                           # base: the current day at +0x3f174 and two more at
                                           # +0x3f178 and +0x3f17c
            elif EVENTS <= m.disp < STRIDE:
                k = "event"
            elif 0 <= m.disp < COUNT:
                continue                   # an id: the list still starts at +0
            else:
                odd.append(("disp", ins.address, f, "%s %s  (+0x%x)" % (ins.mnemonic, ins.op_str, m.disp)))
                continue
            sites.append(dict(kind=k, by=by, va="0x%x" % ins.address, func="0x%x" % f,
                              disp=m.disp, at=const_offset(ins, m.disp),
                              text="%s %s" % (ins.mnemonic, ins.op_str)))

        # a call that hands the calendar base to a callee: 0x1414c8fd0 is reached that way
        # from thirty callers and walks a day record with every constant this file rewrites,
        # and no instruction in it names the base.  Without following the argument the whole
        # function is invisible to the survey.
        if passed is not None and ins.id == X86_INS_CALL and ops and ops[0].type == X86_OP_IMM:
            for r in ARGS:
                if tag.get(r) == "CAL":
                    passed.add((ops[0].imm, r))

        for op in ops:                     # the id cap
            if op.type == X86_OP_IMM and op.imm == IDCAP and ins.id in (X86_INS_CMP, X86_INS_MOV):
                sites.append(dict(kind="cap", va="0x%x" % ins.address, func="0x%x" % f,
                                  at=const_offset(ins, IDCAP),
                                  text="%s %s" % (ins.mnemonic, ins.op_str)))


def main():
    rest = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = rest[0] if rest else None
    funcs = funcs_touching_base()
    sites, odd = [], []
    # Two kinds of function walk the calendar: the ones that name its base, and the ones
    # that are handed it.  seeds[f] is the argument registers f is entered with; the base
    # spreads along call edges to a fixpoint, because a callee can pass it on again.
    seeds = {f: frozenset() for f in funcs}
    work = list(funcs)
    while work:
        f = work.pop()
        if not (sva <= f < sva + rsz):
            continue
        passed = set()
        walk(f, [], [], shape_ok=False, seed=seeds[f], passed=passed)
        for callee, reg in passed:
            have = seeds.get(callee, frozenset())
            if reg not in have:
                seeds[callee] = have | {reg}
                work.append(callee)
    handed = [f for f in seeds if f not in funcs]
    for f in sorted(seeds):
        if not (sva <= f < sva + rsz):
            continue
        # the shape fallback is only safe where the function demonstrably walks the calendar
        # -- a field the taint did reach, or a multiply by the day stride -- so run once to
        # find out and then again with it enabled
        probe, throw = [], []
        walk(f, probe, throw, shape_ok=False, seed=seeds[f])
        proven = any(s["kind"] in ("count", "event", "after", "stride") for s in probe)
        if proven:
            walk(f, sites, odd, seed=seeds[f])
        else:
            sites.extend(probe)
            odd.extend(throw)
    seen, uniq = set(), []
    for s in sites:
        k = (s["va"], s["kind"])
        if k not in seen:
            seen.add(k)
            uniq.append(s)
    bad = [s for s in uniq if s["at"] is None]
    print("%d functions name the calendar base, %d more are handed it as an argument, "
          "%d sites" % (len(funcs), len(handed), len(uniq)))
    for k, n in sorted(collections.Counter(s["kind"] for s in uniq).items()):
        shape = sum(1 for s in uniq if s["kind"] == k and s.get("by") == "shape")
        print("  %-7s %d%s" % (k, n, "   (%d by shape, not taint)" % shape if shape else ""))
    print("  %d sites whose constant is not a plain dword in the encoding" % len(bad))
    for s in bad[:10]:
        print("    %s  %s" % (s["va"], s["text"]))
    print("  %d sites needing review" % len(odd))
    if "--review" in sys.argv:
        for w, va, f, t in odd:
            print("    %-8s %x  fn %x  %s" % (w, va, f, t))
    if out:
        json.dump({"_comment": __doc__,
                   "calendar": {"base": "0x%x" % CAL, "stride": "0x%x" % STRIDE, "days": DAYS,
                                "count_off": "0x%x" % COUNT, "events_off": "0x%x" % EVENTS,
                                "id_cap": IDCAP, "today_off": "0x%x" % TODAY},
                   "sites": uniq}, open(out, "w"), indent=1)
        print("wrote %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
