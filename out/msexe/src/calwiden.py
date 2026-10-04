r"""calwiden.py [--ids N] [--base 0x...] [--review]  -> the patches that widen a calendar day

A calendar day holds 280 match ids and the scheduler at 0x141350290 refuses the 281st
without a word. caltab.py puts our world at 277 on its busiest day, so the next league costs
matches. This produces the patch list that makes the day bigger.

The day record today is 0x2c4 bytes: the id list at +0x00 (0x230, so 280 u16 ids), the count
at +0x230, eighteen event slots of eight bytes from +0x234. calstride.py walked the code and
wrote every site that has to change into patches/calendar-sites.json -- 519 of them, in six
kinds -- so this does not search, it rewrites.

    base   135   the calendar base, a disp32 or imm32
    stride  81   imul r, i, 0x2c4
    cap     65   cmp r, 0x118
    count  101   the count at +0x230
    event   99   an event slot, +0x234 .. +0x2c3
    after   38   the four fields that live just past the calendar, read off its base

## The shape of the new day

The stride is not free. The mode copy's calendar is moved by 0x1413fbf60, whose per-day body
is an unrolled `mov ecx, 5` loop of 0x80-byte blocks plus a fixed 0x44-byte tail. Keeping
that tail means the new stride has to be k * 0x80 + 0x44, and then the only change to the
copier is the block count and one add:

    k =  5   stride 0x2c4    280 ids   (what ships)
    k =  9   stride 0x4c4    536 ids
    k = 13   stride 0x6c4    792 ids   (the default here)
    k = 21   stride 0xac4   1304 ids

## What actually has to move: the unit, not the calendar

The calendar is not a thing on its own. The block and the mode copy both hold the same unit:
365 days, then four small fields at +0x3f174, then 32 records of 0x16dc, 0x6cd00 bytes in all
(block 0x16038a8 .. 0x16705a8, copy +0xa8d4a0). 0x1413fbf60 copies it in both directions and
keeps ONE `rsi = src - dst` for the days and for everything above them, so the two sides have
to be laid out alike across the whole unit -- which is why the calendar cannot move alone, and
why mlcopy already relocates the unit on the copy side as one piece.

So the block's whole unit moves, the calendar part of it grows in the middle by
growth = 365 * (stride - 0x2c4), and what sits above it inside the unit shifts by that growth:

    the 38 `after` sites      +0x3f174 .. +0x3f180  ->  + growth
    the copier's own fields   the same

Not emitted here, because nobody has surveyed it: the references that reach the unit's
trailing part by its own block offset instead of off the calendar base. attrib.json has none
and a byte search cannot tell a displacement from a coincidence. patchset.py refuses to build
the set until that survey exists.

Nothing here is applied, and the base is a parameter: patchset.py decides where the calendar
actually lands, because only it knows what else the block is carrying.
"""
import json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import boundscan

SITES = os.path.join(TOP, "patches", "calendar-sites.json")
TAIL = os.path.join(TOP, "patches", "calendar-tail-sites.json")

OLD_STRIDE, OLD_CAP, OLD_COUNT, OLD_EVENTS = 0x2c4, 0x118, 0x230, 0x234
EVENTS_LEN, DAYS = 18 * 8, 365
OLD_BASE, COPY_BASE = 0x16038a8, 0xa8d4a0
OLD_UNIT = 0x6cd00                 # calendar + the four fields + 32 records of 0x16dc
BLOCK_TAIL = 0x44                  # the copier's fixed tail; the stride is k*0x80 + this

# The one site in calendar-sites.json that is not the calendar's: 0x1414bc5a8 bounds the
# 596-byte match table's binary search with the calendar base, because the table ends there.
# It belongs to that table and patchset.py already moves it with it. Moving it here as well
# would move it twice.
NOT_OURS = {0x1414bc5a8: "the match table's end pointer, moved with the match table"}

# 0x1413fbf60 -- the copier.  Its `mov ecx, 5` is the only thing in it the survey cannot
# see: the block count of an unrolled 0x80-byte copy is not a calendar constant to look at,
# it is arithmetic.  Everything else in that function (the stride it adds, the nine fields
# it copies past the calendar) the survey now finds on its own.
COPIER_BLOCKS = (0x1413fbf97, 1)   # mov ecx, 5     -> k


# Idioms the walk cannot express, each read and checked by hand.  A taint walk finds a
# pointer being *used*; these are places where the calendar's shape is a number in an
# argument, a frame, or a table -- nothing points anywhere.
#
#   the two constructors and the destructor call a vector-of-N-elements helper with the
#   element size in edx and the count in r8d: (0x2c4, 0x16d) for the days, (0x16dc, 0x20)
#   for the records above them.  Only the day size changes.
#
#   0x140af1fb0 builds the unit: memset(rcx, 0, 0x6cd00) -- the whole unit in one literal --
#   then steps 365 days and reaches the records at +0x3f180.  0x1414bab60 tears it down.
#   The fourth is an unwind funclet at 0x1424957c0 -- the cleanup the constructor runs if
#   it throws half way through the 365 days.  It is in the funclet region, which no function
#   start covers, so a linear decode walks past it and both the survey and the audit's own
#   disassembly miss it; only the byte-anchored pass sees it.
SIZE_SITES = (0x1414b9da3, 0x1414ba4d8, 0x1414bac08, 0x1424957d6)  # mov edx, 0x2c4 -> stride
UNIT_SITE = 0x140af1fc6                                # mov r8d, 0x6cd00 -> the new unit
AFTER_IMM = (0x140af201f, 0x1414babe2)                 # add rcx, 0x3f180 -> + growth

# 0x140aed760 copies a whole day record onto its own stack and reads it there, so its frame
# has to grow with the record.  The shipped numbers fall out of one formula, which is the
# check that the formula is right: buffer at +0x40, cookie at align16(0x40 + stride), frame
# 0x10 past it -- 0x40 + 0x2c4 -> 0x310 -> 0x320, exactly what it ships.  Every one of these
# constants is already a full dword in the encoding, so nothing changes length.
STACK = {"func": 0x140aed760, "buf": 0x40,
         "frame": (0x140aed778, 0x140aed96c),     # sub rsp, 0x320 / lea r11, [rsp + 0x320]
         "cookie": (0x140aed789, 0x140aed95c),    # the security cookie at [rsp + 0x310]
         "blocks": 0x140aed7f3,                   # mov ecx, 5, the same unrolled copy
         "count": 0x140aed878}                    # movzx r14d, word [rsp + 0x270] -- +0x230
                                                  # into the buffer, so it moves with it
# ... and the frame size is also in the unwind data, where a UWOP_ALLOC_LARGE holds it in
# eighths.  An exception that unwinds through this function restores rsp from that number,
# so it has to agree with the prologue.  UNWIND_INFO 0x142f2e7f4, node 7 (a u16, 0x320/8).
UNWIND_SLOT = 0x142f2e806


class Exe:
    def __init__(self):
        self.data, self.secs, self.base = boundscan.image()

    def off(self, va):
        r = va - self.base
        for _, vaS, vs, rp, rs in self.secs:
            if vaS <= r < vaS + vs:
                d = r - vaS
                return rp + d if d < rs else None
        return None

    def read(self, va, n):
        o = self.off(va)
        return self.data[o:o + n]

    def i32(self, va):
        return struct.unpack_from("<i", self.read(va, 4))[0]


def shape(ids):
    """-> (k, stride, id bytes, count offset, events offset) for a day of `ids` match ids"""
    want = ids * 2 + 4 + EVENTS_LEN
    k = (want - BLOCK_TAIL + 0x7f) // 0x80
    stride = k * 0x80 + BLOCK_TAIL
    id_bytes = stride - 4 - EVENTS_LEN
    return k, stride, id_bytes, id_bytes, id_bytes + 4


def find(exe, va, value):
    """the byte offset of `value` inside the instruction at `va` -- the last match wins"""
    want = struct.pack("<I", value & 0xffffffff)
    blob = exe.read(va, 16)
    hits = [i for i in range(len(blob) - 3) if blob[i:i + 4] == want]
    if not hits:
        raise SystemExit("0x%x does not carry 0x%x" % (va, value))
    return hits[-1]


def dword(exe, va, at, old, new, why):
    have = exe.i32(va + at)
    if have != old:
        raise SystemExit("0x%x + %d holds 0x%x, expected 0x%x (%s)"
                         % (va, at, have & 0xffffffff, old & 0xffffffff, why))
    return {"va": "0x%x" % (va + at), "old": struct.pack("<i", old).hex(),
            "new": struct.pack("<i", new).hex(), "why": why, "asm": "disp32/imm32"}


def build(ids, new_base):
    exe = Exe()
    k, stride, id_bytes, count_off, events_off = shape(ids)
    real_ids = id_bytes // 2
    D = new_base - OLD_BASE
    growth = DAYS * (stride - OLD_STRIDE)      # how much longer the calendar part of the unit is
    ev_shift = events_off - OLD_EVENTS
    sites = json.load(open(SITES))["sites"]

    out, skipped = [], []
    for s in sites:
        va, at, kind, text = int(s["va"], 16), s["at"], s["kind"], s["text"]
        if va in NOT_OURS:
            skipped.append((va, NOT_OURS[va]))
            continue
        if kind == "base":
            out.append(dword(exe, va, at, OLD_BASE, new_base,
                             "calendar base: 0x%x -> 0x%x (%s)" % (OLD_BASE, new_base, text)))
        elif kind == "stride":
            out.append(dword(exe, va, at, OLD_STRIDE, stride,
                             "day stride: 0x%x -> 0x%x (%s)" % (OLD_STRIDE, stride, text)))
        elif kind == "cap":
            out.append(dword(exe, va, at, OLD_CAP, real_ids,
                             "ids a day holds: %d -> %d (%s)" % (OLD_CAP, real_ids, text)))
        elif kind == "count":
            out.append(dword(exe, va, at, OLD_COUNT, count_off,
                             "the day's count moves: +0x%x -> +0x%x (%s)"
                             % (OLD_COUNT, count_off, text)))
        elif kind == "event":
            old = exe.i32(va + at)
            out.append(dword(exe, va, at, old, old + ev_shift,
                             "event slot moves: +0x%x -> +0x%x (%s)"
                             % (old, old + ev_shift, text)))
        elif kind == "after":
            old = exe.i32(va + at)
            out.append(dword(exe, va, at, old, old + growth,
                             "past the calendar, which is now longer: +0x%x -> +0x%x (%s)"
                             % (old, old + growth, text)))
        else:
            raise SystemExit("unknown kind %r at %s" % (kind, s["va"]))

    # the unit's trailing part, reached by its own block offset rather than off the calendar
    # base (tailscan.py). It moves with the unit AND sits above the calendar, so it takes both.
    for t in json.load(open(TAIL))["sites"]:
        va, at, v = int(t["va"], 16), t["at"], int(t["value"], 16)
        out.append(dword(exe, va, at, v, v + D + growth,
                         "past the calendar, by its own block offset: 0x%x -> 0x%x (%s)"
                         % (v, v + D + growth, t["text"])))

    va, at = COPIER_BLOCKS
    out.append(dword(exe, va, at, 5, k, "copy loop: 5 blocks of 0x80 a day -> %d" % k))

    for va in SIZE_SITES:
        out.append(dword(exe, va, find(exe, va, OLD_STRIDE), OLD_STRIDE, stride,
                         "a day's size, handed to the vector helper: 0x%x -> 0x%x"
                         % (OLD_STRIDE, stride)))
    out.append(dword(exe, UNIT_SITE, find(exe, UNIT_SITE, OLD_UNIT), OLD_UNIT,
                     OLD_UNIT + growth,
                     "the unit is cleared in one call: 0x%x -> 0x%x bytes"
                     % (OLD_UNIT, OLD_UNIT + growth)))
    for va in AFTER_IMM:
        v = exe.i32(va + find(exe, va, 0x3f180))
        out.append(dword(exe, va, find(exe, va, v), v, v + growth,
                         "past the calendar, added rather than addressed: +0x%x -> +0x%x"
                         % (v, v + growth)))

    # the stack copy
    buf = STACK["buf"]
    cookie_new = (buf + stride + 15) & ~15
    frame_new = cookie_new + 0x10
    cookie_old = (buf + OLD_STRIDE + 15) & ~15
    frame_old = cookie_old + 0x10
    for va in STACK["frame"]:
        out.append(dword(exe, va, find(exe, va, frame_old), frame_old, frame_new,
                         "0x%x copies a day onto its stack: the frame grows 0x%x -> 0x%x"
                         % (STACK["func"], frame_old, frame_new)))
    for va in STACK["cookie"]:
        out.append(dword(exe, va, find(exe, va, cookie_old), cookie_old, cookie_new,
                         "0x%x: the security cookie moves with the frame, +0x%x -> +0x%x"
                         % (STACK["func"], cookie_old, cookie_new)))
    out.append(dword(exe, STACK["blocks"], 1, 5, k,
                     "0x%x: the same unrolled copy, 5 blocks of 0x80 -> %d"
                     % (STACK["func"], k)))
    out.append(dword(exe, STACK["count"], find(exe, STACK["count"], buf + OLD_COUNT),
                     buf + OLD_COUNT, buf + count_off,
                     "0x%x reads the count out of its own copy: +0x%x -> +0x%x"
                     % (STACK["func"], buf + OLD_COUNT, buf + count_off)))
    have = struct.unpack_from("<H", exe.read(UNWIND_SLOT, 2))[0]
    if have != frame_old // 8:
        raise SystemExit("the unwind node at 0x%x holds %d, not %d"
                         % (UNWIND_SLOT, have, frame_old // 8))
    out.append({"va": "0x%x" % UNWIND_SLOT,
                "old": struct.pack("<H", frame_old // 8).hex(),
                "new": struct.pack("<H", frame_new // 8).hex(),
                "why": "0x%x's frame size in its unwind data, in eighths: %d -> %d"
                       % (STACK["func"], frame_old // 8, frame_new // 8),
                "asm": "UWOP_ALLOC_LARGE"})

    info = {
        "ids_per_day": real_ids, "blocks_of_0x80": k, "stride": "0x%x" % stride,
        "count_off": "0x%x" % count_off, "events_off": "0x%x" % events_off,
        "base_new": "0x%x" % new_base, "moved_by": "0x%x" % D,
        "calendar_bytes": DAYS * stride,
        "unit_growth": growth, "tail_sites": len(json.load(open(TAIL))["sites"]),
        "unit_bytes": OLD_UNIT + growth,
        "patches": len(out),
        "skipped": [{"va": "0x%x" % v, "why": w} for v, w in skipped],
    }
    return info, out


def main(argv):
    ids = int(argv[argv.index("--ids") + 1]) if "--ids" in argv else 792
    new_base = int(argv[argv.index("--base") + 1], 16) if "--base" in argv else 0x3100000
    info, out = build(ids, new_base)
    if "--review" in argv:
        for key, v in info.items():
            if key != "skipped":
                print("  %-24s %s" % (key, v))
        for s in info["skipped"]:
            print("  left alone: %s -- %s" % (s["va"], s["why"]))
        print("")
        for p in out[:10]:
            print("  %-12s %s -> %s  %s" % (p["va"], p["old"], p["new"], p["why"][:84]))
        print("  ... %d patches in all" % len(out))
        return 0
    json.dump({"_comment": "generated by calwiden.py", "calendar": info, "patches": out},
              sys.stdout, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
