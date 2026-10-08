r"""python calaudit.py <set.json>  -> does anything still read the calendar where it was?

The widening moves a 0x6cd00-byte unit -- 365 calendar days, four fields, 32 records of
0x16dc -- out of edit block +0x16038a8 and makes each day longer.  Two surveys found the
sites (calstride.py, tailscan.py) and calwiden.py rewrote them.  This asks the opposite
question, of the patched image rather than the shipped one: after every patch in the set is
applied, is there an instruction left that still names the old layout?

    the old base       0x16038a8 as an operand
    the old tail       0x1642a1c .. 0x1642a34, the four fields and the record table
    the old stride     imul r, i, 0x2c4, add r, 0x2c4, or 0x2c4 as an element size
    the old unit       0x6cd00, the size the unit is cleared in

Anything that survives is a site neither survey found.  One is expected and named: the
596-byte match table's end pointer at 0x1414bc5a8, which uses the calendar base because the
table runs up to it and which moves with that table instead.

This does not prove the set correct.  It proves the set complete in the only sense a
disassembler can: no instruction is left computing from where the calendar used to be.
"""
import sys, os, json, bisect, struct
from capstone import *
from capstone.x86 import *
import callindex, calwiden, calstride, json as _json

OLD_BASE = calwiden.OLD_BASE
TAIL_LO, TAIL_HI = 0x1642a1c, 0x1642a34
OLD_STRIDE = calwiden.OLD_STRIDE
EXPECTED = {
    0x1414bc5a8: "the match table's end pointer, moved with the match table",
    # 0x2c4 is an ordinary number and these three are not the calendar's: a value pushed
    # into a call's fifth argument slot beside 0x64 and 0x66, and twice a field offset in
    # an object that is memset 0xc0 bytes from +0x2c4 and has a flag at +0x2c0.
    0x1421c7a0e: "a number handed to a call, next to 0x64 and 0x66",
    0x1422a9d68: "a field at +0x2c4 of another object (memset 0xc0, flag at +0x2c0)",
    0x1422aabbe: "the same object, the other function that clears it",
}

d, nm, sva, ro, rsz = callindex.code_section()
off_of = lambda va: ro + (va - sva)
FS = sorted(f for f in callindex.starts() if sva <= f < sva + rsz)
md = Cs(CS_ARCH_X86, CS_MODE_64); md.detail = True; md.skipdata = True


def patched(path):
    """the code section with the set's patches applied, and how many landed in it"""
    buf = bytearray(d)
    hit = 0
    for p in json.load(open(path))["patches"]:
        va, old, new = int(p["va"], 16), bytes.fromhex(p["old"]), bytes.fromhex(p["new"])
        if not sva <= va < sva + rsz:          # .impdata and the like are not decoded here
            continue
        o = off_of(va)
        if bytes(buf[o:o + len(old)]) != old:
            raise SystemExit("%s: the image does not hold %s" % (p["va"], p["old"]))
        buf[o:o + len(new)] = new
        hit += 1
    return bytes(buf), hit


def leftovers(buf):
    out = []
    for i, f in enumerate(FS):
        end = FS[i + 1] if i + 1 < len(FS) else sva + rsz
        for ins in md.disasm(buf[off_of(f):off_of(end)], f):
            if ins.id == 0:
                continue
            why = None
            for op in ins.operands:
                v = op.imm if op.type == X86_OP_IMM else (
                    op.mem.disp if op.type == X86_OP_MEM and op.mem.base != X86_REG_RIP else None)
                if v is None:
                    continue
                if v == OLD_BASE:
                    why = "the old calendar base"
                elif TAIL_LO <= v < TAIL_HI:
                    why = "an old trailing field, 0x%x" % v
            if ins.id == X86_INS_IMUL and len(ins.operands) == 3 \
                    and ins.operands[2].type == X86_OP_IMM \
                    and ins.operands[2].imm == OLD_STRIDE:
                why = "the old day stride"
            if why:
                out.append((ins.address, why, "%s %s" % (ins.mnemonic, ins.op_str)))
    return out


def resurvey(buf, path):
    """run the same walk over the patched image, looking for the NEW layout

    The leftover scan says nothing still names the old calendar.  This says the new one is
    named in exactly as many places -- that every site was converted, not merely erased.
    """
    meta = _json.load(open(path)).get("calendar")
    if not meta:
        return None
    base = int(meta["base_new"], 16)
    stride = int(meta["stride"], 16)
    calstride.d = buf
    calstride.CAL = base
    calstride.STRIDE = stride
    calstride.COUNT = int(meta["count_off"], 16)
    calstride.EVENTS = int(meta["events_off"], 16)
    calstride.IDCAP = meta["ids_per_day"]
    calstride.TODAY = calstride.DAYS * stride
    sites, odd = [], []
    seeds = {f: frozenset() for f in calstride.funcs_touching_base()}
    work = list(seeds)
    while work:
        f = work.pop()
        passed = set()
        calstride.walk(f, [], [], shape_ok=False, seed=seeds[f], passed=passed)
        for callee, reg in passed:
            have = seeds.get(callee, frozenset())
            if reg not in have:
                seeds[callee] = have | {reg}
                work.append(callee)
    for f in sorted(seeds):
        probe = []
        calstride.walk(f, probe, [], shape_ok=False, seed=seeds[f])
        if any(x["kind"] in ("count", "event", "after", "stride") for x in probe):
            calstride.walk(f, sites, odd, seed=seeds[f])
        else:
            sites.extend(probe)
    seen = set()
    return [x for x in sites if not (x["va"], x["kind"]) in seen and not seen.add((x["va"], x["kind"]))]


def anchored(buf):
    """every occurrence of an old constant that a decode can reach, wherever it sits

    The function-by-function decode has a blind spot: the funclet region, where the cleanup
    code a constructor runs when it throws lives between function starts and a linear decode
    walks straight past it.  0x1424957c0 -- the funclet that destroys the 365 days -- carries
    a full day-size argument and was invisible to everything until this pass.

    So: find the bytes, then try to decode an instruction that ends up containing them,
    starting up to 15 bytes earlier.  A number inside a jump table decodes as nothing and
    drops out on its own.
    """
    out = []
    # 0x2c4 is a common field offset -- 124 instructions in this exe carry it as a
    # displacement and none of them is a calendar -- so the anchored pass only claims it in
    # the one form the function-by-function decode cannot reach: the element size of a
    # 365-element vector, `mov edx, 0x2c4` with `mov r8d, 0x16d` next to it.
    for value, why in ((OLD_BASE, "the old calendar base"),
                       (OLD_STRIDE, "the old day size, handed to the vector helper"),
                       (calwiden.OLD_UNIT, "the old unit size"),
                       (TAIL_LO, "the old current-day field")):
        want = struct.pack("<I", value)
        i = d.find(want, ro, ro + rsz)
        while i != -1:
            for back in range(1, 16):
                va = sva + (i - back - ro)
                for ins in md.disasm(buf[i - back:i - back + 16], va):
                    if ins.address != va or ins.address + ins.size <= sva + (i - ro):
                        break
                    # a decode that starts on the wrong byte can invent an instruction that
                    # happens to swallow the constant -- `imul esi, [rbx - 0x7c760001], 0x2c4`
                    # over what is really a plain mov.  Nothing real addresses memory two
                    # gigabytes from a register, so that is the tell.
                    if any(op.type == X86_OP_MEM and op.mem.base != X86_REG_RIP
                           and abs(op.mem.disp) > 0x10000000 for op in ins.operands):
                        break
                    hit = any((op.type == X86_OP_IMM and op.imm == value) or
                              (op.type == X86_OP_MEM and op.mem.base != X86_REG_RIP
                               and op.mem.disp == value) for op in ins.operands)
                    if hit and value == OLD_STRIDE:
                        after = next(md.disasm(buf[i - back + ins.size:i - back + ins.size + 16],
                                               ins.address + ins.size), None)
                        hit = (ins.id == X86_INS_IMUL or
                               (after is not None and
                                any(o.type == X86_OP_IMM and o.imm == calstride.DAYS
                                    for o in after.operands)))
                    if hit:
                        out.append((ins.address, why, "%s %s" % (ins.mnemonic, ins.op_str)))
                    break
                else:
                    continue
                if out and out[-1][0] == sva + (i - back - ro):
                    break
            i = d.find(want, i + 1, ro + rsz)
    return out


def main(argv):
    if len(argv) < 2:
        raise SystemExit(__doc__.strip().splitlines()[0])
    buf, hit = patched(argv[1])
    left = leftovers(buf)
    print("  %d patches applied to the code section" % hit)
    bad = [x for x in left if x[0] not in EXPECTED]
    for va, why, text in left:
        mark = "expected" if va in EXPECTED else "LEFT OVER"
        print("  %-9s 0x%-11x %-28s %s" % (mark, va, why, text[:52]))
    print("")
    print("  %d instruction(s) still name the old layout, %d of them expected"
          % (len(left), len(left) - len(bad)))
    anch = [x for x in anchored(buf) if x[0] not in {y[0] for y in left}]
    if anch:
        print("")
        print("  the byte-anchored pass found %d more:" % len(anch))
        for va, why, text in anch:
            print("  LEFT OVER 0x%-11x %-28s %s" % (va, why, text[:52]))
        bad += anch
    again = resurvey(buf, argv[1])
    if again is not None:
        import collections
        shipped = _json.load(open(os.path.join(os.path.dirname(__file__), "..", "patches",
                                               "calendar-sites.json")))["sites"]
        a = collections.Counter(s["kind"] for s in again)
        b = collections.Counter(s["kind"] for s in shipped)
        print("  the same walk over the patched image, against the new layout:")
        for k in sorted(set(a) | set(b)):
            mark = "" if a[k] == b[k] else "   <- was %d" % b[k]
            print("    %-7s %d%s" % (k, a[k], mark))
        av = {(x["va"], x["kind"]) for x in again}
        bv = {(x["va"], x["kind"]) for x in shipped}
        byva = {x["va"]: x for x in again}
        was = {x["va"]: x for x in shipped}
        # Two differences are the design, not a miss.  The skipped base site now belongs to
        # the match table.  And 0x141304943 carries 0x648, an offset in some other object:
        # under the old layout that was past the end of a day and the walk ignored it, under
        # the new one it lands in the event range and the shape fallback claims it.  It is
        # not patched either way.
        KNOWN = {("0x1414bc5a8", "base"): "skipped: the match table's end pointer",
                 ("0x141304943", "event"): "0x648 in another object, inside the new range"}
        for va, k in sorted(av - bv):
            if (va, k) in KNOWN:
                print("    allowed: %s %-7s %s" % (va, k, KNOWN[(va, k)]))
                continue
            print("    only after: %s %-7s %s" % (va, k, byva[va]["text"][:52]))
        for va, k in sorted(bv - av):
            if (va, k) in KNOWN:
                print("    allowed: %s %-7s %s" % (va, k, KNOWN[(va, k)]))
                continue
            print("    only before: %s %-7s %s" % (va, k, was[va]["text"][:52]))
        if (av - bv) - set(KNOWN) or (bv - av) - set(KNOWN):
            print("  the survey does not match: a site kept its old constant or took a "
                  "wrong new one -- unless every line above is understood")
            return 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
