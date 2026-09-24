"""python patchset.py <set> [-o patches/]  -> generate a verified patch set

A patch is {va, old, new, why}: the address, the bytes we expect to find there, the bytes
to write, and the reason. The applier refuses to write anything if a single `old` does not
match, so a patch set is all-or-nothing. Nothing here is typed by hand: every byte comes
from disassembling the instruction at the address and locating the 4-byte field inside it,
so a patch that claims to change a displacement really does change that displacement.

Sets:
    block       grow the edit block to the size the whole plan needs (Phase 1.1)
    teams-move  block + relocate the team array, cap unchanged (Phase 1.2)

Two invariants the generator enforces, both discovered from the code rather than assumed:

  * the block size must stay congruent to the memcpy tail (0x68) modulo the chunk size
    (0x80), because the backup copy is an unrolled loop of `chunk` bytes with a fixed tail;
    so the block may only grow by a multiple of 0x80;
  * an array base is aligned to 16.

Output: patches/<set>.json and sider/fl26caps.lua (self-contained, ready to install).
"""
import json, os, struct, sys
from capstone import *
from capstone.x86 import *
import bisect
import calwiden, callindex, datecave, flpaths, impscan

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LAYOUT = json.load(open(os.path.join(ROOT, "patches", "layout.json")))
H = lambda s: int(s, 16) if isinstance(s, str) else s

d, secname, sva, ro, rsz = callindex.code_section()
off_of = lambda va: ro + (va - sva)
md = Cs(CS_ARCH_X86, CS_MODE_64); md.detail = True

CHUNK = H(LAYOUT["block"]["memcpy_chunk_sites"][0]["chunk"])
TAIL = H(LAYOUT["block"]["memcpy_chunk_sites"][0]["tail"])
SIZE_OLD = H(LAYOUT["block"]["size_old"])


def insn_at(va):
    for ins in md.disasm(d[off_of(va):off_of(va) + 16], va):
        return ins
    raise SystemExit("could not decode an instruction at %x" % va)


def field_offset(ins, value):
    """byte offset of the unique little-endian dword `value` inside the instruction"""
    want = (value & 0xffffffff).to_bytes(4, "little")
    hits = [i for i in range(len(ins.bytes) - 3) if bytes(ins.bytes[i:i + 4]) == want]
    if len(hits) != 1:
        raise SystemExit("%x: expected exactly one copy of %08x in %s, found %d"
                         % (ins.address, value, ins.bytes.hex(), len(hits)))
    return hits[0]


def patch_dword(va, old_value, new_value, why):
    """rewrite one 32-bit field of the instruction at va, keeping every other byte"""
    ins = insn_at(va)
    k = field_offset(ins, old_value)
    if not (-0x80000000 <= new_value < 0x80000000):
        raise SystemExit("%x: %x does not fit in the 32-bit field" % (va, new_value))
    old = bytes(ins.bytes)
    new = old[:k] + (new_value & 0xffffffff).to_bytes(4, "little") + old[k + 4:]
    return {"va": "0x%x" % va, "old": old.hex(), "new": new.hex(), "why": why,
            "asm": "%s %s" % (ins.mnemonic, ins.op_str)}


def align(n, a):
    return (n + a - 1) // a * a


SLOTS32 = False           # --slots32 on the command line; see stride_of()


def stride_of(name):
    """the stride an array is being built with in this set

    G2b widens the fixture record from sixteen match slots to thirty-two, which doubles its
    stride.  Every place that sizes or walks the array reads the stride from here, so the
    new one flows into the arithmetic for free; the instructions that carry it as an
    immediate are a separate list (arrays.fixtures.g2b_sites, from tools/g2b.py).
    """
    a = LAYOUT["arrays"][name]
    if SLOTS32 and "stride_new" in a:
        return H(a["stride_new"])
    return H(a["stride"])


def field_growth(name, field):
    """how far a field inside a record moves when the record is widened

    A field at or past the end of the old slot array moves by the growth; anything before
    it stays.  For the fixture record exactly one field qualifies, the count at +0x204.
    """
    a = LAYOUT["arrays"].get(name)          # names like "teams:dummy" are not arrays
    if not a or not (SLOTS32 and "stride_new" in a):
        return 0
    return H(a["stride_new"]) - H(a["stride"]) if field and field >= H(a["count_off"]) else 0


def plan_layout(relocate, belt=False, calendar=None):
    """place the relocated arrays after the old block end; return (new_size, bases)

    With `belt`, the upper belt (layout.json block.upper_belt) goes after them as one
    piece, and bases["belt"] is where its first byte lands.

    With `calendar` (how many match ids a day is to hold), the calendar's whole unit goes
    FIRST, before the arrays, and bases["calendar"] is where it lands.  The unit, not the
    calendar: 0x1413fbf60 copies 365 days, then four fields, then 32 records of 0x16dc as
    one piece with a single src - dst difference, so the days cannot move without the rest.
    How far it moves is free -- the copy's own unit is grown in place by mlcopy -- but it
    goes first anyway, so the biggest single thing in the block is placed while the space
    above the old end is still unbroken.

    `block.tail_pad` is spare room after everything, holding no array.  It exists because
    not every reference to a relocated array is ours to move: the protector virtualises
    some of them into `.impdata`, where the attribution -- which reads `.trace` -- cannot
    see them, so they still compute from the array's old base.  One such read was measured
    on 2026-09-17 at `block + 0x3060284`, 0xc69c past an unpadded block, and killed the
    season twice.  The pad does not correct the address; it makes the stale read land in
    our own zeroed memory instead of off the end of the allocation.  A read only -- if a
    stale *write* is ever found, the pad hides it and must be reconsidered.
    """
    cursor = align(SIZE_OLD, 16)
    bases = {}
    if calendar:
        _, stride, _, _, _ = calwiden.shape(calendar)
        unit = calwiden.OLD_UNIT + calwiden.DAYS * (stride - calwiden.OLD_STRIDE)
        bases["calendar"] = cursor
        cursor = align(cursor + unit, 16)
    for name in relocate:
        a = LAYOUT["arrays"][name]
        bases[name] = cursor
        cursor = align(cursor + a["cap_new"] * stride_of(name), 16)
    if belt:
        b = LAYOUT["block"]["upper_belt"]
        bases["belt"] = cursor
        cursor = align(cursor + H(b["end"]) - H(b["start"]), 16)
    pad = H(LAYOUT["block"].get("tail_pad", "0x0"))
    growth = align(cursor - SIZE_OLD + pad, CHUNK)   # keep (size - tail) % chunk == 0
    new_size = SIZE_OLD + growth
    assert (new_size - TAIL) % CHUNK == 0, "block size broke the memcpy invariant"
    for name, b in bases.items():
        if name in ("belt", "calendar"):
            continue                      # sized from their own shape, not from an array
        a = LAYOUT["arrays"][name]
        end = b + a["cap_new"] * stride_of(name)
        assert end <= new_size, ("%s runs 0x%x bytes past the end of the grown block"
                                 % (name, end - new_size))
    return new_size, bases


def block_patches(new_size):
    out = []
    for s in LAYOUT["block"]["size_sites"]:
        out.append(patch_dword(H(s["va"]), SIZE_OLD, new_size,
                               "edit block size: %s" % s["role"]))
    for s in LAYOUT["block"]["memcpy_chunk_sites"]:
        old_chunks = (SIZE_OLD - TAIL) // CHUNK
        new_chunks = (new_size - TAIL) // CHUNK
        out.append(patch_dword(H(s["va"]), old_chunks, new_chunks,
                               "%d -> %d chunks of 0x%x: %s"
                               % (old_chunks, new_chunks, CHUNK, s["role"])))
    return out


def array_patches(name, base_new, attrib):
    """rewrite every attributed reference to one array's base by the same delta"""
    a = LAYOUT["arrays"][name]
    return shift_patches(name, base_new - H(a["base_old"]), attrib,
                         a.get("extra_sites", []), base_new=base_new)


# A `biased` site is a reference to a block array stored pre-biased by the *mode copy's*
# offset for the same array: `lea rcx, [r15 + X]; add rcx, rdi` with r15 = block - copy and
# rdi = copy + copy_base + i*stride, so the encoded constant is
#
#     X = block_base - copy_base
#
# and it is that difference, not the block delta, that the patch has to carry. While the
# copy keeps its shipped layout the two are the same thing (copy_base does not move, so
# adding the block delta is right). A set that grows copy A's own tables (mlcopy) moves
# copy_base as well, and then a site that only got the block delta points copy_base_new -
# copy_base_old bytes too high -- 0x15ca20 for coaches, 0x21b100 for regulations.
#
# So for sites inside copy A's code the new constant is computed from the two new bases
# directly. Copy A only: variant B (0x1413fea10) is not grown, its coach offset is still
# +0x133a30, and its biased site must keep taking the block delta.
def in_copy_a(va):
    return any(H(a) <= va < H(b) for a, b in LAYOUT["copy"]["mlcopy"]["code_a"])


def copy_base_new(name):
    """copy A's new offset for one array, or None if this set does not move the copy side"""
    if not MLCOPY_ON:
        return None
    regions = mlcopy_regions()
    shift = mlcopy_shift(regions)
    for r in regions:
        if r["array"] == name:
            return r["base"] + shift(r["base"])
    return None


def shift_patches(name, delta, attrib, extra=(), base_new=None):
    """move every attributed reference to `name` (an array, a dummy, a count, a region)"""
    out = []
    for s in attrib:
        if s["array"] != name or s["kind"] not in ("edit", "edit-pattern", "edit-manual", "biased", "imm", "imm-scaled"):
            continue
        va, old_value = H(s["va"]), H(s["operand"])
        if old_value >= 1 << 63:
            old_value -= 1 << 64          # attrib stores a negative disp sign-extended
        off, field = s.get("offset"), s.get("field") or 0
        if off is not None and old_value not in (off, off + field):
            # a derived pointer: `cmp word ptr [rcx], ax` after `lea rcx, [rsi + base]`,
            # or `[r8 - 0x314]` after `lea r8, [r13 + base + 0x314]`.  The lea is its
            # own attributed site and moves; this displacement is relative to it and
            # stays.  Every site of the proven sets (teams, coaches, rec596) has
            # operand == offset (+ field); regulations has 169 derived ones, each in a
            # function that also holds the base-carrying site.
            continue
        grow = field_growth(name, field) if old_value == (off or 0) + field else 0
        new_value, note = old_value + delta + grow, ""
        if grow:
            note = " [field +0x%x -> +0x%x]" % (field, field + grow)
        if s["kind"] == "biased" and base_new is not None and in_copy_a(va):
            cb = copy_base_new(name)
            if cb is not None:
                new_value = base_new - cb
                note = " [copy A: block 0x%x - copy 0x%x]" % (base_new, cb)
        out.append(patch_dword(va, old_value, new_value,
                               "%s %s: 0x%x -> 0x%x (%s %s)%s"
                               % (name, s["kind"], old_value, new_value,
                                  s["mnemonic"], s["text"], note)))
    # Sites the attribution files under a different array by value: the match table's
    # id lookup (0x1414bc560) bounds its binary search with the calendar base, because
    # the shipped table runs 0x80 bytes into the calendar.  Such an end pointer moves
    # with the array it bounds, by the same delta.
    for s in extra:
        va, old_value = H(s["va"]), H(s["operand"])
        out.append(patch_dword(va, old_value, old_value + delta,
                               "%s extra: 0x%x -> 0x%x (%s)"
                               % (name, old_value, old_value + delta, s["why"])))
    return out



def copy_delta():
    """how far the copy's fields move when its team array grows to the new cap"""
    c = LAYOUT["copy"]
    stride = H(LAYOUT["arrays"]["teams"]["stride"])
    cap_old = LAYOUT["arrays"]["teams"]["cap_old"]
    cap_new = LAYOUT["arrays"]["teams"]["cap_new"]
    end_old = H(c["teams"]) + cap_old * stride
    end_new = H(c["teams"]) + cap_new * stride
    assert end_old == H(c["coaches"]), (
        "the copy is not packed the way layout.json says: teams end at 0x%x, coaches "
        "begin at 0x%x" % (end_old, H(c["coaches"])))
    return align(end_new - end_old, 32)


def copy_patches(delta):
    """shift every copy field that sits after the team array

    The team array itself is not touched.  It is at +0x50, a disp8 that cannot be widened
    without lengthening the instruction, so it stays and the rest of the object moves.
    The buffer's *capacity* does not move either -- it is a length, not an offset.
    """
    sites = json.load(open(os.path.join(ROOT, "patches", "copylayout.json")))
    out, seen = [], set()
    for s in sites:
        if s["kind"] not in ("field-disp", "field-imm") or s["name"] == "buffer_cap":
            continue
        va, old = H(s["va"]), H(s["value"])
        if va in seen:
            raise SystemExit("%s: two copy fields change in one instruction" % s["va"])
        seen.add(va)
        out.append(patch_dword(va, old, old + delta,
                               "copy %s: 0x%x -> 0x%x (%s)"
                               % (s["name"], old, old + delta, s["text"])))
    return out


# The copy functions.  A bounds check inside one of these guards a write into the mode
# copy, whose team array is 750 records long and is not being moved, so raising it there
# would overrun the copy.  Raising it everywhere else lets the block hold more teams while
# the copy simply never sees one past the 750th.
COPY_CODE = [(0x140af30f0, 0x140af3f00), (0x140afd660, 0x140afd800),
             (0x1413fea10, 0x1413fef00), (0x1414007c0, 0x141402300)]


def in_copy_code(va):
    return any(a <= va < b for a, b in COPY_CODE)


# The copy functions, in address order, so a site can be attributed to the one it sits in.
COPY_FUNCS = [0x140af30f0, 0x140afd660, 0x1413fea10, 0x1413feda0, 0x1414007c0,
              0x141400940, 0x141400bb0, 0x141401060, 0x1414013a0, 0x1414016b0,
              0x141401c10, 0x141402100]


def enclosing(va):
    """which copy function a site belongs to, or None if it is outside them"""
    if not in_copy_code(va):
        return None
    fn = None
    for f in COPY_FUNCS:
        if f <= va and (fn is None or f > fn):
            fn = f
    return fn


def block_funcs(reloc):
    """copy functions that turned out to work on the block, not on a copy

    Four of the team-base relocations land inside the copy code.  A function that reads the
    block's team array at its real offset is reading the block, whatever region it was
    grouped into, so its bounds checks guard the block's array and have to be raised with
    it.  Leaving them at 750 is what made a reload wipe every club past the 743rd and put
    the count back: the loader filled exactly 750 relocated records and stopped.
    """
    return {enclosing(H(p["va"])) for p in reloc if in_copy_code(H(p["va"]))} - {None}


CAP_CHECKS = []


def check_cap_completeness(patches):
    """no function that has a cap raised may still carry an unexamined copy of the old cap

    The attribution walk finds a bounds check by walking out from an array access, so it
    reaches the test that sits next to the access and not always the one on the far side of
    the loop body.  A `for` loop written with both an entry test and a back edge therefore
    comes back half-attributed, and half a loop raised is worse than none: the entry test
    lets the index start past the old cap while the back edge still stops the walk there.

    That is exactly what held G2a up.  0x141579db0 searches the fixture array for a free
    record; its entry test at 0x141579e2e was raised to 6000 and its back edge at
    0x141579e64 was never seen, so the search still only ever examined records 0..1999.
    Every other bound in all thirteen fixture functions was verified live at 6000 and the
    season still stopped at exactly 2000 records.

    So after collecting the sites, sweep each function that has one and refuse to emit if it
    still holds an unrecorded immediate equal to the old cap.  Sites that are recorded --
    raised, held, or held with their own `from` count -- are fine; the check is only against
    sites nobody has ever looked at.
    """
    # a site the mlcopy region machinery owns is recorded too, just not by cap_patches:
    # the copy's own counts are raised with the region that grows them.  So is one a
    # different mechanism emitted (the mode-copy player walk at 0x140fc18f4), which is why
    # this runs over the finished patch list rather than inside cap_patches.
    emitted = {H(p["va"]) for p in patches}
    region_sites = set()
    for c in LAYOUT.get("copy", {}).values():
        for r in (c.get("regions", []) if isinstance(c, dict) else []):
            region_sites |= {H(x["va"]) for x in r.get("count_sites", [])}
    starts = sorted(callindex.starts())
    bad, loops = [], 0
    for name, vas, out in CAP_CHECKS:
        known = {H(v) for v in vas} | emitted | region_sites
        a = LAYOUT["arrays"][name]
        caps = {a["cap_old"], a["cap_old"] - 1}
        for pt in out:
            raised = H(pt["va"])
            k = bisect.bisect_right(starts, raised) - 1
            if k < 0:
                continue
            f = starts[k]
            end = starts[k + 1] if k + 1 < len(starts) else raised + 0x10
            prev = None
            for ins in md.disasm(d[off_of(f):off_of(end)], f):
                # the back edge is a conditional jump home; the test that feeds it is the
                # instruction before it, and the jump lands between the raised site and here
                if (prev is not None and ins.group(X86_GRP_JUMP)
                        and ins.operands and ins.operands[0].type == X86_OP_IMM
                        and raised <= ins.operands[0].imm <= prev.address
                        and prev.address not in known
                        and any(o.type == X86_OP_IMM and o.imm in caps
                                for o in prev.operands)):
                    bad.append((prev.address, f, name, a["cap_old"],
                                "%s %s" % (prev.mnemonic, prev.op_str)))
                prev = ins
            loops += 1
    bad = sorted(set(bad))
    if bad:
        raise SystemExit(
            "%d loop(s) were raised on the entry test only; the back edge still stops at the "
            "old cap:\n%s\n"
            "Half a raised loop is worse than none -- the index may start past the old cap "
            "while the walk still ends there.  Add each to patches/layout.json "
            "arrays.<array>.extra_cap_sites, or record it there with \"hold\": true and why "
            "it must keep the old count."
            % (len(bad), "\n".join("  0x%x  in 0x%x  %-12s %-6d %s" % (va, f, n, c, t)
                                    for va, f, n, c, t in bad)))
    print("   cap back edges: %d raised site(s) swept across %d array(s), none left behind"
          % (loops, len(CAP_CHECKS)))


def cap_patches(name, skip_copy=False, on_block=(), release=()):
    """raise every bounds check that guards one array

    Two sources, deliberately.  attrib.json finds the checks by what they guard, walking
    out from an array access; copylayout.json finds the ones inside the copy code, which
    the walk does not reach because the copy's team array carries no evidence of its own.
    Six sites are in both lists, which is a small check that the two agree.

    `release` names hold sites that may be raised after all, because the part that grows
    them has since been built.  It applies to both kinds of hold: the array-level
    `hold_sites` list and the per-site `hold` flag inside `extra_cap_sites`.  It did not
    apply to the second kind until 2026-09-16, which would have left copy A's fixture
    counts at 2000 while its array grew to 6000 -- the exact shape of an overrun.
    the copy's own array (mlcopy) is in the set.
    """
    a = LAYOUT["arrays"][name]
    cap_old, cap_new = a["cap_old"], a["cap_new"]
    att = json.load(open(os.path.join(ROOT, "patches", "attrib.json")))
    vas = {s["va"]: s for s in att if s["kind"] == "cap" and s["array"] == name}
    both = 0
    for s in json.load(open(os.path.join(ROOT, "patches", "copylayout.json"))):
        if s["kind"] == "team-cap" and name == "teams":
            if s["va"] in vas:
                both += 1
            else:
                vas[s["va"]] = s
    # An extra site may guard a *different* array of the same kind, and then its shipped
    # count is not this array's.  "from" gives that count (copy B holds 1750 fixture
    # records, not 2000); "hold" says the site is recorded but must never be raised, which
    # is how the third, hundred-record fixture array stays out of it.
    for s in a.get("extra_cap_sites", []):
        co = H(s["from"]) if "from" in s else cap_old
        if s["va"] not in vas:
            vas[s["va"]] = dict(s, text="%s 0x%x (extra)" % (s["mnemonic"], co), _from=co)
        else:
            # a site the walk already found, but layout.json knows something the walk does
            # not: that it counts a different array, or that it must never be raised
            vas[s["va"]].update({k: v for k, v in s.items()
                                 if k in ("hold", "hold_why")})
            if "from" in s:
                vas[s["va"]]["_from"] = co
    # Sites named in layout.json's hold_sites are never raised: loop bounds inside the copy
    # code that measure the copy's own arrays (750 teams, 750 coaches, 13000 matches), which
    # keep their shipped layout.  Raising 0x1413fea8f made the League-mode copy write coach
    # memory into block rows 750..1599 as teams.
    hold = {s["va"]: s["why"] for arr in LAYOUT["arrays"].values()
            for s in arr.get("hold_sites", []) if s["va"] not in release}
    out, held = [], 0
    for va in sorted(vas, key=lambda v: int(v, 16)):
        if va in hold:
            print("            %s left at %d: %s" % (va, cap_old, hold[va][:80]))
            continue
        if vas[va].get("hold") and va not in release:
            print("            %s left alone: %s"
                  % (va, (vas[va].get("hold_why") or vas[va].get("why", ""))[:100]))
            continue
        if skip_copy and in_copy_code(H(va)) and enclosing(H(va)) not in on_block:
            held += 1
            continue
        co = vas[va].get("_from", cap_old)
        # A bound may be written as `< cap` or as `<= cap - 1`; both are the same check and
        # both have to move.  Look for the count the site actually encodes rather than
        # assuming the first form, and carry the same off-by-one into the new value.
        bias = 0
        want = (co & 0xffffffff).to_bytes(4, "little")
        if bytes(insn_at(H(va)).bytes).count(want) != 1:
            alt = (co - 1) & 0xffffffff
            if bytes(insn_at(H(va)).bytes).count(alt.to_bytes(4, "little")) == 1:
                bias = -1
        out.append(patch_dword(H(va), co + bias, cap_new + bias,
                               "%s cap: %d -> %d (%s)%s"
                               % (name, co, cap_new, vas[va]["text"],
                                  ", written as <= cap - 1" if bias else "")))
    CAP_CHECKS.append((name, set(vas), list(out)))
    return out, both, held


SETS = {
    "block": [],
    "teams-move": ["teams"],
    "copy-move": [],
    "teams-1600": ["teams"],
    "teams-1600-block": ["teams"],
    "teams-1600-blockfull": ["teams"],
    # teams alone hits a wall at 526 new clubs, because the game gives every club a
    # manager and the coach array still stops at 1300.  This relocates and uncaps both.
    "teams-coaches": ["teams", "coaches"],
    # ... and clubs without players forfeit their matches.  The player array cannot be
    # relocated -- it starts at offset 0, so its accesses carry no displacement to rewrite
    # -- but it does not need to be: once the teams have moved out of the way, it can grow
    # in place into the space they leave, as far as the regulation array above it.
    "teams-coaches-players": ["teams", "coaches"],
    # ... and a new league never plays: the fixture dates of every competition come from a
    # switch on the regulation id inside the exe (0x14157f810), and every id the shipped
    # tables leave free falls into its empty default.  This is teams-coaches plus a one-byte
    # jump-table change per league so those ids take the big-league calendar instead.
    "teams-coaches-dates": ["teams", "coaches"],
    "teams-coaches-players-dates": ["teams", "coaches"],
    # ... and the match table is full: 13000 records, none free once 42 leagues of cup
    # ties have been drawn, and the allocator drops the rest without a word.  This moves
    # the table out to the grown block and doubles it.
    "teams-coaches-dates-matches": ["teams", "coaches", "rec596", "matchflags"],
    # everything the dates-matches set does, plus the player cap raised to 33314 so more
    # than 90 clubs get squads (234 of 23).  players is uncapped in place, not relocated;
    # the block cap ceiling stays 33314 (regulations sits just above the array), and the
    # separate season-mode ~30001 ceiling is untouched -- so this widens exhibition, not a
    # season.  See docs/plan.md.
    "teams-coaches-players-dates-matches": ["teams", "coaches", "rec596", "matchflags"],
    # ... and the regulation array moves out of the player array's way as well.  With
    # teams, regulations and coaches all relocated, the first thing left above the players
    # is the dummy-record triple at 0xd0b0ec (team, regulation, coach dummies, then the
    # count fields), so the player cap can go to 0xd0b0ec / 0x17c = 35991 (350 squads of
    # 23).  Pass --player-cap N to pick the cap; the generator refuses one that would
    # reach the dummies.  Attribution for regulations is complete (no review-* sites).
    "teams-coaches-regs-players-dates-matches": ["teams", "coaches", "regulations", "rec596", "matchflags"],
    # ... and the belt above the players -- the dummy triple, the count block, the fixture
    # table and the unnamed fields around it (layout.json block.upper_belt) -- moves as one
    # piece to the end of the grown block.  The dummies and the counts keep their role as
    # the walk's fingerprint (attribution runs on the shipped offsets); only the emitted
    # displacements change.  Above the belt lies the old 596-byte match table, dead once
    # rec596 is relocated, so the player array may now run up to the season calendar at
    # 0x16038a8: 0x16038a8 / 0x17c = 60745 players, far past the ~46k that 800 new clubs
    # need.  The cap still has to be 17 mod 32 (the mode copy's memcpy tails).
    "teams-coaches-regs-players-dates-matches-upper": ["teams", "coaches", "regulations", "rec596", "matchflags"],
    # ... and the Master League save carries the whole match table.  A season is saved
    # from mode copy A, whose own tables keep the caps its constructor hard-codes;
    # block -> A stops there, so every record past the 13000th is dropped from the save
    # and a season whose competitions used them loads back empty.  This grows the copy's
    # table to the block's cap: the fields above it move, the object grows, the three
    # counts follow.
    "teams-coaches-regs-players-dates-matches-upper-mlcopy": ["teams", "coaches", "regulations", "rec596", "matchflags"],
    # ... and the fixture table is full.  Measured 2026-09-16 on a running 39-league season:
    # all 2000 of its records are in use by 56 competitions and it has already overflowed --
    # our own regulation 143 starts at record 1997 and gets three rounds of a 38-round
    # season.  A record is one ROUND of one competition, so every competition costs as many
    # records as it has match days.  This takes the table out of the upper belt, relocates it
    # on its own and raises it to 6000.  See findings.md, "The fixture table is full".
    "teams-coaches-regs-players-dates-matches-upper-mlcopy-fixtures":
        ["teams", "coaches", "regulations", "rec596", "matchflags", "fixtures"],
    # ... and a calendar day is full.  A day holds 280 match ids and the scheduler at
    # 0x141350290 drops the rest without a word; caltab.py puts the 39-league world at 277
    # on its busiest day, so the next league costs matches nobody is told about.  This
    # widens the day to 792 ids and moves the calendar -- both the block's and the mode
    # copy's, by the same distance, which is what keeps their shared copier honest.
    # See docs/calendar-widening.md and tools/calwiden.py.
    "teams-coaches-regs-players-dates-matches-upper-mlcopy-fixtures-calendar":
        ["teams", "coaches", "regulations", "rec596", "matchflags", "fixtures"],
}
UPPER_SETS = {"teams-coaches-regs-players-dates-matches-upper",
              "teams-coaches-regs-players-dates-matches-upper-mlcopy",
              "teams-coaches-regs-players-dates-matches-upper-mlcopy-fixtures",
              "teams-coaches-regs-players-dates-matches-upper-mlcopy-fixtures-calendar"}
MLCOPY_SETS = {"teams-coaches-regs-players-dates-matches-upper-mlcopy",
               "teams-coaches-regs-players-dates-matches-upper-mlcopy-fixtures",
               "teams-coaches-regs-players-dates-matches-upper-mlcopy-fixtures-calendar"}
# Sets that widen the calendar day.  CALENDAR_IDS is how many match ids a day then holds;
# calwiden.shape() rounds it up to the next stride the mode copy's copier can step by.
CALENDAR_SETS = {"teams-coaches-regs-players-dates-matches-upper-mlcopy-fixtures-calendar"}
CALENDAR_IDS = 792
# set in main(): whether this set moves copy A's own table bases, which is what makes a
# pre-biased displacement need the two-base form rather than the block delta
MLCOPY_ON = False
MLCOPY_MOVED = {}

# The first block field above the player array once teams, regulations and coaches have
# moved out: the team dummy record at 0xd0b0ec (see docs/findings.md, dummy triple).
PLAYERS_HARD_END = 0xd0b0ec

# The mode copy's players (plan.md 3.3).  A season does not carry the block's 0x17c-byte
# player records: it carries a packed 0x9c-byte form of each, in a global table BH1
# (0x143700880, count pH1 at 0x143700888) that 0x1413fcc70 allocates for 30001 records
# and 0x1412e4b50 fills from the block (record i for i < min(count, 30001), the dummy
# 0x184c3bc past that).  The League-mode copy object A (0x141401060) keeps a copy of the
# table at +0x11403b8 -- 30001 x 0x9c = 0x4769dc bytes, so the object is 0x11403b8 +
# 0x4769dc = 0x15b6d94 -- and the copy-to-block side adopts that table as BH1 with count
# 30001 (0x140af2441) and unpacks it through a 30001-record vector (0x1412e5eb0).  Copy
# object B (0x140afd660) does the same with 30000 records at +0xee53d0 (0x135bd10 in
# all).  The compressor FL1 (0x141b39b40) takes the table by its byte length too.  None
# of these sites is reachable from the attribution walk (they measure the table, not the
# block), so a block with more players than 30001 gets a season in which every later
# player is the dummy and whoever reads past the table reads whatever follows it.
# These grow all of it with the block cap; the memcpy tails (0x5c / 0x3c / 0x40 bytes
# after the 0x80-byte chunks) are fixed code, so the cap has to keep them: c = 17 mod 32.
# Both constructors also keep a fallback that builds a 0x17c-record vector when BH1 is
# empty; it is grown the same way.  The last group is the block's own 30001 loops the
# walk never reached: its constructors, destructors and id lookups, two per-index side
# tables allocated on their own (30001 x 8 and 30001 x 4), and a 2400-player copy.
PACKED = 0x9c
COPY_PLAYER_SITES = [
    # va, old, new as a function of cap, what
    # the packed table BH1 and its owners
    (0x140afc129, 0x7531, lambda c: c, "BH1 allocation (0x140afc110)"),
    (0x140afc279, 0x7531, lambda c: c, "BH1 allocation (0x140afc270)"),
    (0x140b0ee16, 0x7531, lambda c: c, "BH1 allocation (0x140b0ee00)"),
    (0x140b0eee7, 0x7531, lambda c: c, "BH1 allocation (0x140b0eee0)"),
    (0x1412e4b7f, 0x7531, lambda c: c, "BH1 allocation inside the packer"),
    (0x1412e4bce, 0x7531, lambda c: c, "packer 0x1412e4b50: dummy switch"),
    (0x140af2441, 0x7531, lambda c: c, "A -> block: BH1 adopted with this count"),
    (0x1412e5f2f, 0xadf4c4, lambda c: 8 + c * 0x17c, "unpacker 0x1412e5eb0: vector allocation"),
    (0x1412e5f51, 0x7531, lambda c: c, "unpacker: vector count"),
    (0x1412e5f6d, 0x7531, lambda c: c, "unpacker: records constructed"),
    (0x1412e5fa0, 0x7531, lambda c: c, "unpacker: index bound"),
    (0x1412e62b3, 0x7531, lambda c: c, "unpacker: dummy switch in the block fill"),
    (0x1412e62d2, 0x7531, lambda c: c, "unpacker: block fill bound"),
    # copy object A: the packed table at +0x11403b8, the object size, the compressor
    (0x14140142e, 0x4769dc, lambda c: c * PACKED, "A: packed table length at +0x11403a8"),
    (0x1414015e4, 0x8ed3, lambda c: (c * PACKED) >> 7, "A: packed table memcpy chunks"),
    (0x14140085b, 0x4769dc, lambda c: c * PACKED, "A: bytes given to the compressor FL1"),
    (0x141400966, 0x4769dc, lambda c: c * PACKED, "A: uncompressed-length test on load"),
    (0x141400a3f, 0x8ed3, lambda c: (c * PACKED) >> 7, "A: decompressed table memcpy chunks"),
    (0x141400b6e, 0x15b6d94, lambda c: 0x11403b8 + c * PACKED, "A: object size ceiling for a compressed copy"),
    (0x141400b7c, 0x15b6d94, lambda c: 0x11403b8 + c * PACKED, "A: object size"),
    (0x141400ba0, 0x15b6d94, lambda c: 0x11403b8 + c * PACKED, "A: object size (constant getter)"),
    # copy object A: the fallback vector of full records
    (0x141401463, 0xadf4c4, lambda c: 8 + c * 0x17c, "A fallback: vector allocation"),
    (0x141401483, 0x7531, lambda c: c, "A fallback: vector count"),
    (0x14140149f, 0x7531, lambda c: c, "A fallback: records constructed"),
    (0x1414014cd, 0x7531, lambda c: c, "A fallback: dummy switch in the fill loop"),
    (0x1414014f3, 0x7531, lambda c: c, "A fallback: fill loop bound"),
    (0x1414014fb, 0xadf4bc, lambda c: c * 0x17c, "A fallback: table length at +0x11403a8"),
    (0x141401508, 0x15be9, lambda c: (c * 0x17c) >> 7, "A fallback: memcpy chunks"),
    # copy object B: 30000 records at +0xee53d0
    (0x140af23cf, 0x7530, lambda c: c - 1, "B -> block: BH1 adopted with this count"),
    (0x140afda04, 0x8ed2, lambda c: ((c - 1) * PACKED) >> 7, "B: packed table memcpy chunks"),
    (0x1413fea01, 0x135bd10, lambda c: 0xee53d0 + (c - 1) * PACKED, "B: object size"),
    (0x140afd87b, 0xadf348, lambda c: 8 + (c - 1) * 0x17c, "B fallback: vector allocation"),
    (0x140afd8a1, 0x7530, lambda c: c - 1, "B fallback: vector count"),
    (0x140afd8bd, 0x7530, lambda c: c - 1, "B fallback: records constructed"),
    (0x140afd8ed, 0x7531, lambda c: c, "B fallback: dummy switch in the fill loop"),
    (0x140afd913, 0x7530, lambda c: c - 1, "B fallback: fill loop bound"),
    (0x140afd91e, 0x15be6, lambda c: ((c - 1) * 0x17c) >> 7, "B fallback: memcpy chunks"),
    # the block's own 30001s the attribution walk never reached
    (0x140af3702, 0x7531, lambda c: c, "accessor 0x140af3680: dummy switch"),
    (0x1414bba00, 0x7531, lambda c: c, "block constructor 0x1414bb9f0: records constructed"),
    (0x1414bbe82, 0x7531, lambda c: c, "block constructor 0x1414bbe60: records constructed"),
    (0x1414ba61f, 0x7531, lambda c: c, "block destructor: records destroyed"),
    (0x142495060, 0x7531, lambda c: c, "block destructor 0x142495050: records destroyed"),
    (0x1414bb2ce, 0x7531, lambda c: c, "lookup 0x1414bb2a0: index bound"),
    (0x1414bca10, 0x7531, lambda c: c, "lookup 0x1414bca10: index bound"),
    (0x1414bc0d5, 0x7531, lambda c: c, "lookup 0x1414bc0a0: search bound"),
    (0x140fc18f4, 0x7531, lambda c: c, "walk 0x140fc16a0: index bound"),
    (0x1413fc4d1, 0x7531, lambda c: c, "2400-player copy 0x1413fc480: dummy switch"),
    (0x1413206cf, 0x3a988, lambda c: c * 8, "side table 0x1413206c0: allocation (8 per index)"),
    (0x1413206eb, 0x7531, lambda c: c, "side table 0x1413206c0: entries cleared"),
    (0x1413210cf, 0x1d4c4, lambda c: c * 4, "side table 0x1413210c0: allocation (4 per index)"),
    (0x1413210f0, 0x7531, lambda c: c, "side table 0x1413210c0: entries cleared"),
]
COPY_PLAYER_SETS = ["teams-coaches-regs-players-dates-matches",
                    "teams-coaches-regs-players-dates-matches-upper",
                    "teams-coaches-regs-players-dates-matches-upper-mlcopy",
                    "teams-coaches-regs-players-dates-matches-upper-mlcopy-fixtures",
                    "teams-coaches-regs-players-dates-matches-upper-mlcopy-fixtures-calendar"]
# what the fixed memcpy tails need of the cap (see above)
COPY_PLAYER_CAP_MOD = (32, 17)


def copy_player_patches(cap, taken):
    """taken: vas already patched by the cap walk, to be left alone"""
    m, r = COPY_PLAYER_CAP_MOD
    if cap % m != r:
        raise SystemExit("--player-cap %d: the mode copy's memcpy tails need cap = %d mod %d; "
                         "the nearest below is %d" % (cap, r, m, cap - (cap - r) % m))
    out = []
    for va, old, new, what in COPY_PLAYER_SITES:
        if "0x%x" % va in taken:
            continue
        out.append(patch_dword(va, old, new(cap),
                               "mode-copy players, %s: 0x%x -> 0x%x"
                               % (what, old, new(cap))))
    return out

# The mode copy's own tables (layout.json copy.mlcopy).  Copy A carries a copy of every
# array the block has, each at the cap its constructor hard-codes, and a season is saved
# from it: a record past the copy's cap never reaches the file, and the load fills the
# block back only as far as the copy goes.  That is one bug with four faces -- the match
# table lost the schedule, the team, coach and regulation tables lost the managed club,
# its manager and its league.
#
# The copy is one flat object, so a table grows only by moving everything above it.  Each
# region in copy.mlcopy.regions is [base, base + cap_old * stride) and is checked to end
# exactly where the next field begins; a field's shift is the sum of the growths of every
# region that starts below it, and each site gets ONE patch carrying the final value.  The
# team array is at +0x50 in a disp8 that cannot be widened, so it stays put and the rest of
# the object moves; teams drive a second region as well (the 0x10-byte per-team side array
# at +0xc016b4, counted by the same `mov ebp, 0x2ee`), so both grow together.
#
# Sites the players part already rewrote (the object size, the length stores whose
# displacement is +0x11403a8) are composed onto, not duplicated: the applier refuses two
# patches at one address, and the lua verifies the original bytes either way.
def grow_field(p, old_value, growth):
    """add `growth` to the 4-byte field that held `old_value` in an already-emitted patch"""
    ins = insn_at(H(p["va"]))
    k = field_offset(ins, old_value)
    new = bytearray.fromhex(p["new"])
    cur = int.from_bytes(new[k:k + 4], "little")
    new[k:k + 4] = ((cur + growth) & 0xffffffff).to_bytes(4, "little")
    p["new"] = new.hex()
    p["why"] += "; mlcopy: 0x%x -> 0x%x" % (cur, cur + growth)


# Set by main() when the set widens the calendar day: how many bytes longer the copy's
# calendar unit becomes.  The copy carries the same unit as the block at +0xa8d4a0, and
# mlcopy already relocates it; growing it there is what keeps the two sides alike.
CALENDAR_GROWTH = 0


def mlcopy_regions():
    """the grown regions, each checked against the copy's own layout, in offset order"""
    m = LAYOUT["copy"]["mlcopy"]
    fields = sorted(H(v) for v in m["fields"])
    out = []
    if CALENDAR_GROWTH:
        base, end = calwiden.COPY_BASE, calwiden.COPY_BASE + calwiden.OLD_UNIT
        if end not in fields:
            raise SystemExit("the copy's calendar unit ends at 0x%x, which is not a copy A "
                             "field -- the unit is not 0x%x bytes here"
                             % (end, calwiden.OLD_UNIT))
        out.append({"name": "calendar", "array": None, "base": base,
                    "stride": calwiden.OLD_STRIDE, "cap_old": calwiden.DAYS,
                    "cap_new": calwiden.DAYS, "ends_at": "0x%x" % end,
                    "growth": CALENDAR_GROWTH, "count_sites": []})
    for r in m["regions"]:
        a = LAYOUT["arrays"][r["array"]]
        cap_old, cap_new = a["cap_old"], a["cap_new"]
        base, stride, end = H(r["base"]), H(r["stride"]), H(r["ends_at"])
        if base + cap_old * stride != end:
            raise SystemExit("mlcopy region %s: 0x%x + %d * 0x%x is 0x%x, not the 0x%x the "
                             "next field begins at" % (r["name"], base, cap_old, stride,
                                                       base + cap_old * stride, end))
        if end not in fields:
            raise SystemExit("mlcopy region %s ends at 0x%x, which is not a copy A field"
                             % (r["name"], end))
        out.append(dict(r, cap_old=cap_old, cap_new=cap_new, base=base, stride=stride,
                        growth=(cap_new - cap_old) * stride))
    out.sort(key=lambda r: r["base"])
    return out


def mlcopy_shift(regions):
    """field offset -> how far it moves (the growths of every region below it)"""
    def shift(v):
        return sum(r["growth"] for r in regions if r["base"] < v)
    return shift


def mlcopy_check_fields(fields):
    """the field list must be everything following the copy pointer finds, or more

    copyfields.walk decodes linearly and runs past the end of its function, so each walk is
    bounded to its own function's extent here; a value found past that belongs to the next
    function and to a different object.
    """
    import bisect, copyfields
    m = LAYOUT["copy"]["mlcopy"]
    md2 = Cs(CS_ARCH_X86, CS_MODE_64); md2.detail = True; md2.skipdata = True
    starts = sorted(callindex.starts())
    walked = set()
    for fn in m["field_funcs"]:
        f = H(fn)
        end = starts[bisect.bisect_right(starts, f)]
        for s in copyfields.walk(d, md2, f):
            if f <= H(s["va"]) < end:
                walked.add(H(s["value"]))
    missing = walked - fields
    if missing:
        raise SystemExit("copy.mlcopy.fields lacks %s (found by copyfields.walk)"
                         % ", ".join("0x%x" % v for v in sorted(missing)))
    return md2


def mlcopy_patches(patches):
    """grow copy A's tables to the block's caps

    Returns the new patches; patches already in `patches` that touch one of the sites are
    composed onto in place.
    """
    c = LAYOUT["copy"]
    m = c["mlcopy"]
    regions = mlcopy_regions()
    shift = mlcopy_shift(regions)
    total = sum(r["growth"] for r in regions)
    fields = {H(v) for v in m["fields"]}
    md2 = mlcopy_check_fields(fields)
    moving = {v for v in fields if shift(v)}

    # no offset we are about to rewrite may double as a block offset someone attributed
    att = json.load(open(os.path.join(ROOT, "patches", "attrib.json")))
    clash = [s for s in att if H(s["operand"]) in moving
             and not s["kind"].startswith(("copy", "size-manual"))]
    if clash:
        raise SystemExit("mlcopy: %d attributed block sites carry a copy A field offset, "
                         "e.g. %s %s" % (len(clash), clash[0]["va"], clash[0]["text"]))

    by_va = {p["va"]: p for p in patches}
    out, composed, moved = [], 0, {}

    def move(va, value, what):
        nonlocal composed
        delta = shift(value)
        if not delta:
            return
        moved.setdefault(value, []).append(va)
        key = "0x%x" % va
        if key in by_va:
            grow_field(by_va[key], value, delta)
            composed += 1
        else:
            out.append(patch_dword(va, value, value + delta,
                                   "mlcopy %s: 0x%x -> 0x%x" % (what, value, value + delta)))

    # every displacement or immediate in the copy A code that is one of its moving fields
    starts = sorted(callindex.starts())
    for a, b in m["code_a"]:
        a, b = H(a), H(b)
        fns = [f for f in starts if a <= f < b]
        for i, f in enumerate(fns):
            end = fns[i + 1] if i + 1 < len(fns) else b
            for ins in md2.disasm(d[off_of(f):off_of(end)], f):
                if ins.id == 0:
                    continue
                try:
                    ops = ins.operands
                except CsError:
                    continue
                for op in ops:
                    if op.type == X86_OP_MEM and op.mem.base != X86_REG_RIP \
                            and op.mem.disp in moving:
                        move(ins.address, op.mem.disp, "A field (disp)")
                    elif op.type == X86_OP_IMM and op.imm in moving:
                        move(ins.address, op.imm, "A field (imm)")
    # the callers that reach a field of A from outside the copy code
    for s in m["outside_sites"]:
        if H(s["operand"]) not in fields:
            raise SystemExit("mlcopy outside site %s: 0x%x is not a listed field"
                             % (s["va"], H(s["operand"])))
        move(H(s["va"]), H(s["operand"]), "A field from %s (%s)" % (s["func"], s["why"]))

    # the object size: the players part raised it already, this raises it again
    size_old = H(c["size"])
    for va in c["size_sites"]:
        if va in by_va:
            grow_field(by_va[va], size_old, total)
            composed += 1
        else:
            out.append(patch_dword(H(va), size_old, size_old + total,
                                   "mlcopy A: object size 0x%x -> 0x%x"
                                   % (size_old, size_old + total)))

    # the record counts the copy code keeps for each of its own tables.
    #
    # A site does not always count records.  The standings copier 0x1413fb0b0 was compiled
    # with its entry loop unrolled two records to a pass, so it carries 50 with a stride of
    # 0x168 = 2 * 0xb4 -- and writing the cap there would copy twice the table.  `per` says
    # how many records one pass handles; the site then counts passes, and the cap has to
    # divide by it.
    for r in regions:
        for s in r["count_sites"]:
            per = s.get("per", 1)
            if r["cap_old"] % per or r["cap_new"] % per:
                raise SystemExit("mlcopy %s: count site %s handles %d records a pass, which "
                                 "divides neither %d nor %d"
                                 % (r["name"], s["va"], per, r["cap_old"], r["cap_new"]))
            co, cn = r["cap_old"] // per, r["cap_new"] // per
            if s["va"] in by_va:
                have = int.from_bytes(bytes.fromhex(by_va[s["va"]]["new"])[-4:], "little")
                if have != cn:
                    raise SystemExit("mlcopy count site %s is already patched, but to %d, "
                                     "not %d" % (s["va"], have, cn))
                continue
            out.append(patch_dword(H(s["va"]), co, cn,
                                   "mlcopy %s: %s: %d -> %d%s"
                                   % (r["name"], s["why"], co, cn,
                                      " (passes, %d records each)" % per if per != 1 else "")))
    return out, composed, moved, regions, total


def check_copy_fields(patches):
    """every occurrence of a remapped copy A field offset must be patched or explained

    mlcopy moves the copy's tables, so an offset such as the regulations' 0x1f2110 becomes
    0x40d210 everywhere it is used.  The field walk only covers copy A's own functions, and
    the few sites that reach a field from outside are listed by hand -- which is how
    0x140af3e73 was missed: the accessor 0x140af3680 had its regulation index bound raised
    to 600 while the `lea rdi, [rdx + 0x1f2110]` right above it kept the old layout, so a
    loaded season initialised 293 regulation records 0x21b100 bytes low, straight over the
    team array, and 69 clubs came back with broken squad handles.

    So scan the whole code section for each remapped value, and refuse to emit unless every
    occurrence is either patched or named in copy.mlcopy.field_scan_allow (variant B, which
    keeps its shipped layout and is not grown).
    """
    if not MLCOPY_MOVED:
        return
    allow = {H(a["va"]): a for a in LAYOUT["copy"]["mlcopy"].get("field_scan_allow", [])}
    patched = {H(p["va"]) for p in patches}
    starts = sorted(callindex.starts())
    bad = []
    for value in sorted(MLCOPY_MOVED):
        want = (value & 0xffffffff).to_bytes(4, "little")
        i = d.find(want)
        while i >= 0:
            va = sva + (i - ro)
            k = bisect.bisect_right(starts, va) - 1
            if k >= 0:
                f = starts[k]
                end = starts[k + 1] if k + 1 < len(starts) else va + 0x10
                for ins in md.disasm(d[off_of(f):off_of(end)], f):
                    if not (ins.address <= va < ins.address + ins.size):
                        continue
                    ops = [o for o in ins.operands
                           if (o.type == X86_OP_MEM and o.mem.base != X86_REG_RIP
                               and o.mem.disp == value)
                           or (o.type == X86_OP_IMM and o.imm == value)]
                    if ops and ins.address not in patched and ins.address not in allow:
                        bad.append((value, ins.address, "%s %s" % (ins.mnemonic, ins.op_str)))
                    break
            i = d.find(want, i + 1)
    if bad:
        raise SystemExit(
            "%d site(s) still carry a copy A field offset mlcopy moved:\n%s\n"
            "Patch them (patches/layout.json copy.mlcopy.outside_sites) or, if they belong "
            "to variant B, name them in copy.mlcopy.field_scan_allow with the reason."
            % (len(bad), "\n".join("  0x%x  %-34s (0x%x)" % (va, t, v)
                                     for v, va, t in bad)))
    print("   copy A field offsets: every occurrence of %d moved fields is patched or allowed"
          % len(MLCOPY_MOVED))


def check_biased(patches):
    """every pre-biased site in one copy function must end up with the same constant

    `lea rcx, [r15 + X]` there always resolves to block + copy_base + X + i*stride with
    rdi = copy + copy_base, so X = block_base - copy_base -- and because the block and the
    copy pack teams, coaches and regulations in the same order with the same caps and
    strides, that difference is one constant for the whole function. Three sites in
    0x1414016b0 disagreeing is precisely the bug this check exists to prevent: the coach
    and regulation sites once carried the block delta while the team site carried the
    difference, and a loaded season wrote its coaches 0x15ca20 bytes too high.

    Copy A only. Variant B (0x1413fea10) keeps its shipped layout while the block moves,
    so its biased constants legitimately differ from array to array.
    """
    seen = {}
    for p in patches:
        va = H(p["va"])
        if " biased: " not in p["why"] or not in_copy_a(va):
            continue
        seen.setdefault(enclosing(va), {}).setdefault(va, None)
    # recompute each new constant from the patched bytes: the changed dword is the only
    # difference between old and new
    for fn, sites in seen.items():
        for va in sites:
            p = next(q for q in patches if H(q["va"]) == va)
            o, n = bytes.fromhex(p["old"]), bytes.fromhex(p["new"])
            k = next(i for i in range(len(o)) if o[i] != n[i])
            k = min(k, len(o) - 4)
            sites[va] = int.from_bytes(n[k:k + 4], "little")
    for fn, sites in sorted(seen.items()):
        vals = set(sites.values())
        if len(vals) > 1:
            raise SystemExit(
                "biased sites in 0x%x disagree: %s. A pre-biased displacement encodes "
                "block_base_new - copy_base_new, which is one constant per copy function; "
                "a site carrying the block delta alone is the mlcopy load-path bug."
                % (fn, ", ".join("%s=0x%x" % ("0x%x" % v, c)
                                 for v, c in sorted(sites.items()))))
        if sites:
            print("   biased sites in 0x%x: %d, all 0x%x" % (fn, len(sites), vals.pop()))


def mlcopy_released():
    return [v for r in LAYOUT["copy"]["mlcopy"]["regions"]
            for v in r.get("released_hold_sites", [])]


# The date-template switch: a byte per regulation id 1..175 at DATE_CASES picks a case,
# and case 5 is the one the ten big leagues (ids 17-22, 50, 99, 116, 118) share -- a
# 38-round league calendar.  Free ids are in case 62, which returns nothing.
DATE_CASES, DATE_CASE_LEAGUE, DATE_CASE_EMPTY = 0x1415802e8, 5, 62
DATE_KEYS = [11]


def date_patches(keys):
    # The same 1..175 bound cup_patches enforces, and for the same reason: the table ends at
    # 0x141580396 and a table of 16-bit values begins at 0x141580397, so a case byte written
    # for id 176 or above lands in that one. It is also wrong to assume the byte found there
    # is DATE_CASE_EMPTY: ids that reuse a shipped calendar carry that calendar's case, so the
    # expected byte is read out of the exe rather than guessed. Both were live in the stored
    # ...-fixtures-calendar set (2026-09-21): seventeen of its thirty-eight date patches could
    # never verify, which aborted the whole set every run.
    out = []
    for k in keys:
        if not 1 <= k <= 175:
            raise SystemExit("--date-keys: regulation %d is outside the date table "
                             "(1..175), so no case byte exists to patch. Spread mode "
                             "(--date-offsets) is the only route to an id above 175." % k)
        va = DATE_CASES + k - 1
        cur = d[off_of(va)]
        out.append({"va": "0x%x" % va, "old": "%02x" % cur,
                    "new": "%02x" % DATE_CASE_LEAGUE,
                    "why": "fixture dates: regulation %d takes the big-league calendar" % k,
                    "asm": "jump-table byte"})
    return out


# A cup needs a cup's calendar, not a league's.  Case 38 is the Belgian Croky Cup
# (regulation 122): a sixteen-team domestic knockout, which is the shape mkcup.py copies.
# Sharing a case is ordinary -- nine ids share case 6 between the FA Cup, Coppa Italia,
# Copa del Rey and Coupe de France, and all of them run at once -- so this borrows a
# calendar rather than taking one away.  The id must be 175 or below: the table only
# covers 1..175, which is why a cup built on 186 came out with 37 ties and no dates.
DATE_CASE_CUP16 = 38


def cup_patches(keys):
    out = []
    for k in keys:
        if not 1 <= k <= 175:
            raise SystemExit("--cup-keys: regulation %d is outside the date table "
                             "(1..175), so no case byte exists to patch" % k)
        out.append({"va": "0x%x" % (DATE_CASES + k - 1),
                    "old": "%02x" % DATE_CASE_EMPTY,
                    "new": "%02x" % DATE_CASE_CUP16,
                    "why": "fixture dates: regulation %d takes the 16-team domestic cup "
                           "calendar (the one the Belgian Croky Cup uses)" % k,
                    "asm": "jump-table byte"})
    return out

# the sets that raise caps as well as relocating, and which arrays they raise
CAPPED = {
    "teams-1600": ["teams"],
    "teams-1600-block": ["teams"],
    "teams-1600-blockfull": ["teams"],
    "teams-coaches": ["teams", "coaches"],
    "teams-coaches-players": ["teams", "coaches", "players"],
    "teams-coaches-dates": ["teams", "coaches"],
    "teams-coaches-players-dates": ["teams", "coaches", "players"],
    "teams-coaches-dates-matches": ["teams", "coaches", "rec596", "matchflags"],
    "teams-coaches-players-dates-matches": ["teams", "coaches", "rec596", "matchflags", "players"],
    "teams-coaches-regs-players-dates-matches": ["teams", "coaches", "regulations", "rec596", "matchflags", "players"],
    "teams-coaches-regs-players-dates-matches-upper": ["teams", "coaches", "regulations", "rec596", "matchflags", "players"],
    "teams-coaches-regs-players-dates-matches-upper-mlcopy": ["teams", "coaches", "regulations", "rec596", "matchflags", "players"],
    "teams-coaches-regs-players-dates-matches-upper-mlcopy-fixtures":
        ["teams", "coaches", "regulations", "rec596", "matchflags", "players", "fixtures"],
    "teams-coaches-regs-players-dates-matches-upper-mlcopy-fixtures-calendar":
        ["teams", "coaches", "regulations", "rec596", "matchflags", "players", "fixtures"],
}


# The block constructor's unwind funclets (0x142495050 .. 0x1424953ad).  MSVC gives a
# class with this many array members one small funclet per member, to be run if a later
# member's constructor throws: `mov rcx, [rbp+0x80]` (the block under construction),
# `add rcx, <the member's offset>`, then __ehvec_dtor(rcx, stride, count, dtor).  They
# are invisible to the attribution walk, not because of the instruction shape -- the
# walk attributes 100 of the 109 `add r64, <block offset>` sites in .trace -- but because
# a funclet is unreachable: it holds no array access to walk out from, and nothing calls
# it, since only the unwind data names it.  `patches/attrib.json` has no site in the
# whole range.  One count, the player one, was found by hand and is patched through
# COPY_PLAYER_SITES; its eight siblings were left at the shipped offsets and counts.
# Relocated, that means the team funclet destroys 750 team objects at 0xadf4bc, which
# after the move is the middle of the player array, and the regulation and coach ones
# do the same elsewhere: destructors run over live records of another type, and the
# pointers they free are not pointers.
# Members above the belt (the calendar at 0x16038a8 and everything after it) do not
# move and are not listed.  The four inside the belt move with it in the -upper sets.
DTOR_FUNCLETS = [
    # member,                base site,    old offset, count site,   old count
    ("teams",                0x14249508d, 0xadf4bc,   0x14249509b, 0x2ee),
    ("regulations",          0x1424950c1, 0xc12e9c,   0x1424950cf, 0x12c),
    ("coaches",              0x1424950f5, 0xc4ca0c,   0x142495103, 0x514),
    ("rec596",               0x142495196, 0xe9ff08,   0x1424951a4, 0x32c8),
    ("teams:dummy",          0x142495120, 0xd0b0ec,   None,         None),
    ("regulations:dummy",    0x142495133, 0xd0b77c,   None,         None),
    ("fixtures",             0x14249514f, 0xd65f64,   0x14249515d, 0x7d0),
    ("upper2",               0x14249517a, 0xe9fee0,   None,         None),
]


def dtor_funclet_patches(bases, belt_shift, capped):
    """rewrite the block constructor's unwind funclets for the new layout

    bases: the relocated arrays' new offsets; belt_shift: how far the upper belt moved
    (0 when the set does not move it); capped: the arrays whose caps this set raises.
    """
    out = []
    for member, base_va, base_old, count_va, count_old in DTOR_FUNCLETS:
        array = member.split(":")[0]
        if member in bases:
            delta = bases[member] - base_old
        elif array in bases and ":" not in member:
            delta = bases[array] - base_old
        elif belt_shift and base_old >= H(LAYOUT["block"]["upper_belt"]["start"])                 and base_old < H(LAYOUT["block"]["upper_belt"]["end"]):
            delta = belt_shift
        else:
            delta = 0
        if delta:
            out.append(patch_dword(base_va, base_old, base_old + delta,
                                   "unwind funclet %s: 0x%x -> 0x%x (destroys the member "
                                   "where it now lives)" % (member, base_old, base_old + delta)))
        if count_va is not None and array in capped:
            cap_new = LAYOUT["arrays"][array]["cap_new"]
            if cap_new != count_old:
                out.append(patch_dword(count_va, count_old, cap_new,
                                       "unwind funclet %s: %d -> %d records destroyed"
                                       % (member, count_old, cap_new)))
    return out


def g2b_patches():
    """the immediates that carry the fixture record's shape, from arrays.fixtures.g2b_sites

    tools/g2b.py reads them out of docs/g2b-fixture-record.md and verifies every one
    against the exe, so there is nothing to work out here: each is an in-place immediate
    of the same width, and the list is emitted as it stands.
    """
    fx = LAYOUT["arrays"]["fixtures"]
    out = []
    for s in fx.get("g2b_sites", []):
        out.append({"va": s["va"], "old": s["old"], "new": s["new"], "why": s["why"]})
    return out


def copyb_patches():
    """shift variant B's offsets when the fixture record grows

    The mode copy is one allocation laid out two ways, and only variant A has ever had
    a shift table.  B's is small: thirty-one sites in four runs, recorded in
    `copy.variant_b.sites` by `copyscan.py --variant b`.  B is packed end to end --
    rec596 runs straight into the first singleton, `0x9a8c60 - 0x2a24c0 == 12360 *
    0x254` -- so a bigger fixture record moves rec596 and the ten singletons by the
    whole growth, and moves nothing before them.

    The allocation itself does not need separate sizing.  B sits below A at every
    corresponding field and grows less than A does (1750 records against 2000), so the
    size A's machinery already asks for covers B.
    """
    vb = LAYOUT["copy"]["variant_b"]
    fx = LAYOUT["arrays"]["fixtures"]
    grow = (H(fx["stride_new"]) - H(fx["stride"])) * vb["caps_from_ctor"]["fixtures"]
    after = H(vb["fixtures"])
    d = open(flpaths.need_exe(), "rb").read()
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    md.detail = True
    out = []
    for site in vb["sites"]:
        val = H(site["value"])
        if val <= after:
            continue                       # at or before the fixture array: it stays
        va = H(site["va"])
        off = va - 0x140001000 + 0x600
        ins = next(iter(md.disasm(d[off:off + 16], va)), None)
        if ins is None or bytes(ins.bytes).hex() != bytes(ins.bytes).hex():
            raise SystemExit("copy B: cannot decode %s" % site["va"])
        raw = bytes(ins.bytes)
        want = struct.pack("<I", val)
        k = raw.find(want)
        if k < 0 or raw.find(want, k + 1) >= 0:
            raise SystemExit("copy B: %s does not carry %s exactly once"
                             % (site["va"], site["value"]))
        out.append({"va": "0x%x" % (va + k),
                    "old": want.hex(),
                    "new": struct.pack("<I", val + grow).hex(),
                    "why": "copy B %s: 0x%x -> 0x%x, the fixture array grew by 0x%x (%s)"
                           % (site["field"], val, val + grow, grow, site["text"]),
                    "asm": site["text"]})
    return out


def main():
    global MLCOPY_ON, SLOTS32, CALENDAR_GROWTH
    which = sys.argv[1] if len(sys.argv) > 1 else "block"
    MLCOPY_ON = which in MLCOPY_SETS
    if which in CALENDAR_SETS:
        # mlcopy has to know before it plans the copy: the copy's calendar unit grows by
        # exactly what the block's does, and every copy field above it moves by that much.
        _, st, _, _, _ = calwiden.shape(CALENDAR_IDS)
        CALENDAR_GROWTH = calwiden.DAYS * (st - calwiden.OLD_STRIDE)
    SLOTS32 = "--slots32" in sys.argv
    if which not in SETS:
        raise SystemExit("unknown set %r; known: %s" % (which, ", ".join(SETS)))
    relocate = SETS[which]
    if "--player-cap" in sys.argv:
        # the player array grows in place, so its cap is bounded by whatever still sits
        # above it: the regulation array unless that is relocated too, else the dummies
        cap = int(sys.argv[sys.argv.index("--player-cap") + 1])
        pl = LAYOUT["arrays"]["players"]
        ceiling = PLAYERS_HARD_END if "regulations" in relocate else H(LAYOUT["arrays"]["regulations"]["base_old"])
        if which in UPPER_SETS:
            ceiling = H(LAYOUT["block"]["upper_belt"]["players_ceiling"])
        if which in CALENDAR_SETS:
            # That ceiling is the season calendar, sitting at 0x16038a8 -- and this set
            # moves the calendar unit out of the block's middle, so the player array may
            # run up to where the unit used to end instead.  Nothing is guessed about what
            # is above it: `blockrefs.py 16705a8 1877068` finds 3846 sites in that region
            # and the lowest offset any of them names is 0x16705a8 itself, which is exactly
            # where the unit ends.  So the whole 0x6cd00 the calendar vacates is free and
            # nothing beyond it is.
            ceiling = calwiden.OLD_BASE + calwiden.OLD_UNIT
        if cap * H(pl["stride"]) > ceiling:
            raise SystemExit("--player-cap %d: %d x 0x%x = 0x%x reaches 0x%x; the most "
                             "that fits is %d" % (cap, cap, H(pl["stride"]),
                                                  cap * H(pl["stride"]), ceiling,
                                                  ceiling // H(pl["stride"])))
        pl["cap_new"] = cap
        print("player cap for this set: %d (ceiling 0x%x)" % (cap, ceiling))
    # every set reserves room for everything the plan will relocate, so that the block
    # size is identical across phases and a crash can only come from the relocation itself
    plan = ["teams"] + [n for n in relocate if n != "teams"]
    new_size, bases = plan_layout(plan, belt=which in UPPER_SETS,
                                  calendar=CALENDAR_IDS if which in CALENDAR_SETS else None)
    patches = block_patches(new_size)
    delta = 0
    if which in ("copy-move", "teams-1600"):
        delta = copy_delta()
        patches += copy_patches(delta)
    for name in CAPPED.get(which, []):
        # An array that is only being uncapped, not moved, has no base to relocate, and so
        # no way to work out which copy functions are really working on the block -- so it
        # holds every copy-code site, the same as a relocated array does.  Raising them is
        # what a first attempt at the player cap did, on the reasoning that the mode copy
        # begins with the team array at +0x50 and therefore has no player region at all.
        # It loads and it lists, and then it dies the moment a season is created, so the
        # copy does keep players somewhere.  One player cap site sits in the copy code and
        # it stays where it is.
        skip = which not in ("teams-1600",)
        on_block = ()
        if skip and name in bases:
            att0 = json.load(open(os.path.join(ROOT, "patches", "attrib.json")))
            on_block = block_funcs(array_patches(name, bases[name], att0))
            if on_block:
                print("%s: copy functions that actually work on the block: %s"
                      % (name, ", ".join("0x%x" % f for f in sorted(on_block))))
        release = mlcopy_released() if which in MLCOPY_SETS else ()
        caps, both, held = cap_patches(name, skip_copy=skip, on_block=on_block, release=release)
        patches += caps
        a = LAYOUT["arrays"][name]
        print("%s caps: %d sites raised %d -> %d (%d found by both the attribution walk "
              "and the copy scan)" % (name, len(caps), a["cap_old"], a["cap_new"], both))
        if held:
            print("            %d left at %d because they are inside the copy code, whose "
                  "%s array is not moving" % (held, a["cap_old"], name))
    if which in COPY_PLAYER_SETS:
        cap = LAYOUT["arrays"]["players"]["cap_new"]
        extra = copy_player_patches(cap, {p["va"] for p in patches})
        patches += extra
        print("mode-copy players: %d sites grown to %d records (%d already raised by the walk)"
              % (len(extra), cap, len(COPY_PLAYER_SITES) - len(extra)))
    mlcopy = None
    if which in MLCOPY_SETS:
        extra, composed, moved, regions, total = mlcopy_patches(patches)
        global MLCOPY_MOVED
        MLCOPY_MOVED = moved
        patches += extra
        size_new = H(LAYOUT["copy"]["size"]) + total
        for p in patches:
            if p["va"] == LAYOUT["copy"]["size_sites"][1]:
                size_new = int.from_bytes(bytes.fromhex(p["new"])[-4:], "little")
        print("mode copy A: %d regions grown, object 0x%x -> 0x%x (+0x%x)"
              % (len(regions), H(LAYOUT["copy"]["size"]), size_new, total))
        for r in regions:
            print("   %-12s +0x%-8x %5d -> %-5d x 0x%-5x  grows 0x%-8x  ends 0x%x"
                  % (r["name"], r["base"], r["cap_old"], r["cap_new"], r["stride"],
                     r["growth"], H(r["ends_at"])))
        print("   %d new patches, %d composed onto earlier patches, %d fields at %d sites"
              % (len(extra), composed, len(moved), sum(len(v) for v in moved.values())))
        mlcopy = {"growth_total": "0x%x" % total,
                  "copy_size_new": "0x%x" % size_new,
                  "regions": [{"name": r["name"], "base": "0x%x" % r["base"],
                               "cap_old": r["cap_old"], "cap_new": r["cap_new"],
                               "stride": "0x%x" % r["stride"], "growth": "0x%x" % r["growth"],
                               "base_new": "0x%x" % (r["base"] + mlcopy_shift(regions)(r["base"]))}
                              for r in regions],
                  "fields_moved": {"0x%x" % k: ["0x%x" % v for v in vs]
                                   for k, vs in sorted(moved.items())}}
    calendar = None
    if which in CALENDAR_SETS:
        info, cal = calwiden.build(CALENDAR_IDS, bases["calendar"])
        patches += cal
        print("calendar: a day holds %d ids (stride %s), %d patches; the unit goes to "
              "+0x%x, 0x%x bytes of it, grown by %d"
              % (info["ids_per_day"], info["stride"], info["patches"], bases["calendar"],
                 info["unit_bytes"], info["unit_growth"]))
        print("   %d of those sites reach the unit's trailing part by its own block offset "
              "(tailscan.py); the copy's unit grew by the same %d through mlcopy"
              % (info["tail_sites"], info["unit_growth"]))
        calendar = info
    if relocate:
        att = json.load(open(os.path.join(ROOT, "patches", "attrib.json")))
        # An array that this set relocates on its own must NOT also be carried by the belt
        # shift, or every one of its references would be moved twice.  The match is on the
        # whole name: `teams:dummy` is its own array and stays in the belt even when
        # `teams` is relocated.
        members = ([m for m in LAYOUT["block"]["upper_belt"]["members"] if m not in relocate]
                   if which in UPPER_SETS else [])
        unresolved = [s for s in att
                      if (s["array"].split(":")[0] in relocate or s["array"] in members)
                      and s["kind"].startswith("review")]
        for name in relocate:
            patches += array_patches(name, bases[name], att)
        shift = 0
        if members:
            belt = LAYOUT["block"]["upper_belt"]
            shift = bases["belt"] - H(belt["start"])
            for name in members:
                n = len(patches)
                extra = LAYOUT["arrays"].get(name, {}).get("extra_sites", [])
                patches += shift_patches(name, shift, att, extra)
                print("   belt %-18s %4d sites moved by +0x%x" % (name, len(patches) - n, shift))
        funclets = dtor_funclet_patches(bases, shift if members else 0,
                                        CAPPED.get(which, []))
        patches += funclets
        print("block constructor unwind funclets: %d sites" % len(funclets))
        if unresolved:
            print("REFUSING to emit %s: %d sites for %s are still unattributed."
                  % (which, len(unresolved), ", ".join(relocate + members))
                  + "\nResolve them in patches/attrib-manual.json first; see docs/plan.md 0.1.")
            for s in unresolved[:10]:
                print("   %s  fn %s  %s %s" % (s["va"], s["func"], s["mnemonic"], s["text"]))
            return 1

    spread = None
    cupkeys = []
    if "-dates" in which:
        a = sys.argv[1:]
        # DATE_KEYS is one test league, and a set generated without --date-keys
        # therefore dates one league and leaves every other one's matches stamped
        # 0xffff, which no calendar day ever refers to.  That is how the
        # ...-fixtures set shipped on 17 September with 1 key where the set it
        # replaced had 39, and it cost five seasons of testing before anyone
        # looked at the calendar.  So the fallback is announced rather than taken
        # quietly, and a world of more than one league has to say so.
        if "--date-keys" in a:
            keys = [int(k) for k in a[a.index("--date-keys") + 1].split(",")]
        else:
            keys = DATE_KEYS
            print("WARNING: no --date-keys given, so only %s will be dated. Every "
                  "other league's matches will carry no date and never be "
                  "scheduled." % ", ".join(str(k) for k in keys))
        if "--cup-keys" in a:
            cupkeys[:] = [int(k) for k in a[a.index("--cup-keys") + 1].split(",")]
            clash = sorted(set(cupkeys) & set(keys))
            if clash:
                raise SystemExit("--cup-keys: %s are already league date keys; one id "
                                 "cannot take two calendars"
                                 % ", ".join(str(k) for k in clash))

        if "--date-offsets" in a:
            # spread mode: the stub in datecave.py.  Two forms.  A bare list of shifts
            # deals the keys round-robin over it, e.g. --date-offsets 2,6,5,1 for four
            # nearly empty weekdays.  A list of `key:shift` pairs assigns them one by one,
            # which is what tools/dayplan.py prints after measuring a real season: the
            # shipped competitions are not spread evenly, so an even deal is not the
            # flattest answer and can be worse than using fewer shifts.
            arg = a[a.index("--date-offsets") + 1]
            if ":" in arg:
                spread = {}
                for pair in arg.split(","):
                    k, _, o = pair.partition(":")
                    spread[int(k)] = int(o)
                missing = [k for k in keys if k not in spread]
                if missing:
                    raise SystemExit("--date-offsets: no shift given for %s"
                                     % ", ".join(str(k) for k in missing))
                extra = [k for k in spread if k not in keys]
                if extra:
                    raise SystemExit("--date-offsets: %s are not in --date-keys"
                                     % ", ".join(str(k) for k in extra))
            else:
                offs = [int(o) for o in arg.split(",")]
                spread = {k: offs[i % len(offs)] for i, k in enumerate(keys)}
            # A cup rides in the same table, with the cup bit set instead of a case byte
            # of its own.  This is the only route that reaches a cup at all: Stage C
            # established that a cup below regulation 175 will not let a season generate,
            # and above 175 the switch never looks at the case table, so the stub's `ja`
            # is the one place the id can be caught.  Cups take shift 0 -- the cup
            # calendar is ten rounds, not thirty-eight, so it is not what crowds a day.
            for k in cupkeys:
                spread[k] = datecave.cup()
            patches += datecave.patches(spread, d, off_of)
            if cupkeys:
                print("cups: %d regulation(s) given the 16-team knockout calendar "
                      "through the date stub: %s"
                      % (len(cupkeys), ", ".join(str(k) for k in cupkeys)))
        else:
            patches += date_patches(keys)
            if cupkeys:
                # Without the stub the only lever is the case byte, which exists for ids
                # 1..175 only -- and a cup down there will not generate.  Kept because it
                # is what proved that, but it is not a route to a working cup.
                patches += cup_patches(cupkeys)
                print("cups: %d regulation(s) given the 16-team knockout calendar by "
                      "case byte (ids 1..175 only, and no cup there has ever played): %s"
                      % (len(cupkeys), ", ".join(str(k) for k in cupkeys)))

    if SLOTS32:
        g2b = g2b_patches()
        patches += g2b
        print("slots32: %d fixture-record immediates (stride, count field, slot clamp)"
              % len(g2b))
        cb = copyb_patches()
        patches += cb
        print("slots32: %d mode-copy variant B offsets shifted" % len(cb))

    # The seventeen-megabyte `.impdata` section holds whole functions the protector
    # moved out of `.trace`, and nothing in this generator's attribution can see them,
    # so every block offset they carry stayed at its shipped value while the same
    # offset was moved everywhere else.  One of them is a linear search of the
    # regulation array that reads its count from the shipped place, gets whatever our
    # layout put there, and walks tens of thousands of records off the end -- the wall
    # the season kept hitting in the spring.  impscan finds them from the notes the
    # patches above already carry, so this needs no list of its own.
    imp = impscan.scan(patches)
    patches += imp
    print("impdata: %d offsets the .trace attribution cannot see" % len(imp))

    seen = {}
    for p in patches:
        if p["va"] in seen:
            raise SystemExit("two patches target %s" % p["va"])
        seen[p["va"]] = p
    check_biased(patches)
    check_cap_completeness(patches)
    check_copy_fields(patches)

    if SLOTS32:
        which = which + "-slots32"
    meta = {"set": which, "block_size_old": "0x%x" % SIZE_OLD,
            "date_keys": keys if "-dates" in which else None,
            "cup_keys": cupkeys or None,
            "date_offsets": spread,
            "block_size_new": "0x%x" % new_size,
            "bases_new": {k: "0x%x" % v for k, v in bases.items()},
            "relocated": relocate, "patches": patches}
    if delta:
        meta["copy_shift"] = "0x%x" % delta
        meta["copy_size_new"] = "0x%x" % (H(LAYOUT["copy"]["size"]) + delta)
    if mlcopy:
        meta["mlcopy"] = mlcopy
    if calendar:
        meta["calendar"] = calendar
    out = os.path.join(ROOT, "patches", which + ".json")
    json.dump(meta, open(out, "w"), indent=1)
    print("%s: %d patches, block 0x%x -> 0x%x (+%d bytes)"
          % (which, len(patches), SIZE_OLD, new_size, new_size - SIZE_OLD))
    for k, v in bases.items():
        if k in relocate:
            print("   %s array moves to +0x%x" % (k, v))
        elif k == "belt":
            print("   upper belt moves to +0x%x" % v)
    print("wrote", out)

    tpl = open(os.path.join(ROOT, "sider", "fl26caps.template.lua")).read()
    rows = "\n".join(
        '  {va=0x%s, old="%s", new="%s", why=%s},'
        % (p["va"][2:], p["old"], p["new"], json.dumps(p["why"]))
        for p in patches)
    lua = (tpl.replace("--[[SET]]", which)
              .replace("--[[PATCHES]]", rows)
              .replace("--[[SUMMARY]]", "block 0x%x -> 0x%x, %d patches"
                       % (SIZE_OLD, new_size, len(patches))))
    # Two files, deliberately. fl26caps.<set>.lua keeps every set that has been generated,
    # so one does not silently overwrite another; fl26caps.lua is the copy to install, and
    # is always the set generated last. The installed module in the game folder must match
    # it -- diff them before a run rather than trusting that it does.
    keep = os.path.join(ROOT, "sider", "fl26caps.%s.lua" % which)
    open(keep, "w").write(lua)
    print("wrote", keep)
    lp = os.path.join(ROOT, "sider", "fl26caps.lua")
    if SLOTS32 and "--install-copy" not in sys.argv:
        # An experimental set must not take the install copy's place.  It has done so
        # three times: generate a -slots32 set to look at it, and the file the game is
        # told to load now holds a block of a different size than the season running
        # against it.  Pass --install-copy to mean it.
        print("kept  ", lp, "(unchanged: %s is experimental, pass --install-copy to overwrite)"
              % which)
    else:
        open(lp, "w").write(lua)
        print("wrote", lp, "(this is the copy to install)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
