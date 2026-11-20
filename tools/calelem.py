r"""calelem.py [--survey elems.json] [--review]  -> the patches that make a day's match ids 32-bit

u32 match ids, step M2 (notes/plan-zahtjevi-limiti-0411.md, 05.11.). A calendar day lists its
matches as u16 ids from +0; with ids past 65535 every one of them has to become a dword. calwiden
already grows the day and moves its count and event slots; with `calwiden.ELEM = 4` the count
sits at 4 * ids instead of 2 * ids, and this rewrites every instruction that reads or writes an
element so it does so as a dword:

    movzx r32, word [d + i*2]     ->  mov r32, dword [d + i*4]      (one byte shorter)
    movzx r32, word [d]           ->  mov r32, dword [d]
    mov word [d + i*2], r16       ->  mov dword [d + i*4], r32      (the 0x66 goes)
    cmp word [p], r16 / add p, 2  ->  cmp dword [p], r32 / add p, 4 (the empty-slot walks)
    rep stosw                     ->  rep stosd                     (a day cleared to 0xffff)

None of them grows, so each is rewritten in place and padded with nops. An empty slot stays
the word 0xffff, now the dword 0x0000ffff: the walks compare against `mov edx, 0xffff` and the
clears store a zero-extended ax, and fl26match never hands out an id whose low word is 0xffff.

Where the sites come from: `calstride.py --elems` (the taint walk from the calendar base) gives
every operand inside the id list of a register it proved is a day, saved here as
patches/calendar-elem-sites.json. Three of its functions are not the id list (NOT_ELEMS); the
walks' pointer steps are not memory operands, so they are listed by hand (STEPS). Whatever the
taint cannot reach is found by fl26match's tracer in the game (fl26match.trace) and added here.

Every writer's source register was read by hand: r12w in 0x141350290 is `movzx r12d, r8w`, si is
`movzx esi, ax`, di in 0x141314350 is `mov edi, 0xffff` or `movzx edi, word [r13 + rax*4]` --
all zero-extended, so the dword they now store is the id.
"""
import json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOP = os.path.dirname(HERE)
SITES = os.path.join(TOP, "patches", "calendar-elem-sites.json")

# calstride's taint calls these days, but what they touch at +0..+0x10 is not the id list
NOT_ELEMS = {
    0x1413069c0: "the date at +0x3f17c (word year, byte month, byte day), reached off the base",
    0x1412e6e00: "an event slot's type word and its 0xffff parameter",
    0x1413fc0c0: "the per-day fixture table past the calendar (16 bytes a day), not a day",
    0x140aed760: "copies the whole day onto its stack in 0x80 blocks; calwiden sizes that copy",
    0x1413fbf60: "the unit copier, whole days in 0x80 blocks; calwiden sizes it",
    0x1412e72d0: "copies the whole day onto its stack; calwiden sizes that copy",
}

# the empty-slot walks step a pointer through the list: `add rcx, 2` -> 4 (hand-read, 05.11.)
STEPS = (0x141350337, 0x1413503d7, 0x141314648,
         # the clamp-idiom day walks (CLAMP's shape, pointer in a register): their reads were
         # rewritten, their steps were not, so they read every other id misaligned and saw half a
         # day (found by the fl26match detector as one constant cut moving site to site, 05.11.)
         0x14155004b, 0x14157ec6a, 0x14157f012, 0x14157f59f, 0x141585d98, 0x1415860a8)

# Reads the taint lost and the clamp idiom gives away: `cmp i, cap; jb; movzx x, word [d]; jmp;
# movzx x, word [d + i*2]` after a cap site (0x141321886 seen by the tracer in the game, 05.11.;
# the other three found by looking behind every cap site for the same shape).
CLAMP = (0x14132187f, 0x141321886, 0x14151153b, 0x141511543)

# 0x141314350 rebuilds a day from a vector of dword ids and reads them back as words
FLOW = (0x141314630,)

# The two functions that copy a day onto their stack (calwiden STACK / STACK2) read the ids out
# of the copy, where the taint does not go: the copy is at rsp/rbp + 0x40, which is the buffer's
# place, not an element offset, so it stays (hand-read, 05.11.).
HAND = {
    0x140aed88a: "mov r15d, dword ptr [rsp + 0x40]",          # the copy's first id
    0x140aed8b1: "mov edx, dword ptr [rsi]",                  # rsi walks the copy ...
    0x140aed90a: "add rsi, 4",                                # ... by one id
    0x1412e7449: "mov eax, dword ptr [rbp + 0x40]",
    0x1412e7452: "mov eax, dword ptr [rbp + r12*4 + 0x40]",
}


def load_sites():
    return json.load(open(SITES))


def survey(src):
    """calstride --elems output -> the word-sized element accesses this rewrites"""
    keep = []
    for e in json.load(open(src)):
        f = int(e["func"], 16)
        if f in NOT_ELEMS or e["lea"]:
            continue
        if e["size"] != 2:
            continue
        keep.append({"va": e["va"], "func": e["func"], "text": e["text"]})
    return keep


def widen_text(text):
    """the dword form of a word access to the id list"""
    m, _, ops = text.partition(" ")
    ops = ops.strip()
    r16 = {"ax": "eax", "bx": "ebx", "cx": "ecx", "dx": "edx", "si": "esi", "di": "edi",
           "bp": "ebp", "sp": "esp"}
    for i in range(8, 16):
        r16["r%dw" % i] = "r%dd" % i

    def mem(o):
        o = o.replace("word ptr", "dword ptr")
        if "*2" in o:
            o = o.replace("*2", "*4")
        # a disp inside the list counts elements: double it
        if "[" in o:
            inner = o[o.index("[") + 1:o.index("]")]
            parts = [p.strip() for p in inner.replace("-", "+-").split("+")]
            out = []
            for p in parts:
                if not p:
                    continue
                try:
                    v = int(p, 0)
                    out.append("0x%x" % (2 * v) if v >= 0 else "-0x%x" % (-2 * v))
                except ValueError:
                    out.append(p)
            o = o[:o.index("[") + 1] + " + ".join(out).replace("+ -", "- ") + o[o.index("]"):]
        return o

    if m == "rep" and ops.startswith("stosw"):
        return "rep stosd dword ptr [rdi], eax"
    if m == "movzx":
        dst, src = [x.strip() for x in ops.split(",", 1)]
        return "mov %s, %s" % (dst, mem(src))
    if m in ("mov", "cmp"):
        a, b = [x.strip() for x in ops.split(",", 1)]
        if "ptr" in a:
            if b in r16:
                return "%s %s, %s" % (m, mem(a), r16[b])
            raise SystemExit("an immediate store into the list needs a cave: %s" % text)
        if "ptr" in b:
            return "%s %s, %s" % (m, r16.get(a, a), mem(b))
    raise SystemExit("no dword form for %r" % text)


def patches(exe, ks=None):
    """-> calwiden-style patches: whole instructions, rewritten in place, nop-padded"""
    import keystone
    from capstone import Cs, CS_ARCH_X86, CS_MODE_64
    ks = ks or keystone.Ks(keystone.KS_ARCH_X86, keystone.KS_MODE_64)
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    out = []

    def one(va, why_kind):
        raw = exe.read(va, 16)
        ins = next(md.disasm(raw, va))
        old = bytes(ins.bytes)
        text = "%s %s" % (ins.mnemonic, ins.op_str)
        if why_kind == "hand":
            new_text = HAND[va]
        elif why_kind == "step":
            if not (ins.mnemonic == "add" and ins.op_str.endswith(", 2")):
                raise SystemExit("0x%x is not a +2 step: %s" % (va, text))
            new_text = text[:-1] + "4"
        else:
            new_text = widen_text(text)
        new = bytes(ks.asm(new_text, va)[0])
        if len(new) > len(old):
            raise SystemExit("0x%x: %s -> %s is %d bytes longer" % (va, text, new_text, len(new) - len(old)))
        new += b"\x90" * (len(old) - len(new))
        out.append({"va": "0x%x" % va, "old": old.hex(), "new": new.hex(),
                    "why": "day id list to u32 (%s): %s -> %s" % (why_kind, text, new_text),
                    "asm": "insn"})

    for s in load_sites():
        if int(s["func"], 16) in NOT_ELEMS:
            continue
        one(int(s["va"], 16), "element")
    for va in CLAMP:
        one(va, "element")
    for va in STEPS:
        one(va, "step")
    for va in FLOW:
        one(va, "flow")
    for va in sorted(HAND):
        one(va, "hand")
    return out


def main(argv):
    if "--survey" in argv:
        keep = survey(argv[argv.index("--survey") + 1])
        json.dump(keep, open(SITES, "w"), indent=0)
        print("%d element sites -> %s" % (len(keep), SITES))
    sys.path.insert(0, HERE)
    import calwiden
    ps = patches(calwiden.Exe())
    print("%d patches" % len(ps))
    if "--review" in argv:
        for p in ps:
            print("  %s  %s" % (p["va"], p["why"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
