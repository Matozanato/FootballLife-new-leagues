r"""caltab.py -- the fixture calendars the exe ships, read without starting the game

Every competition gets its fixture dates from a switch on the regulation id at 0x14157f810
(see tools/datecave.py). The switch has 63 cases; each one tail-calls a small builder, and
every builder does the same two things: it points at a static array of 12-byte date records
and copies a fixed number of them.

    record:  u32 day of the year (1 January = day 0), u32 round index, u32 kind

So the whole shipped calendar is readable from the file:

    python caltab.py                       # every case: its array, its length, its days
    python caltab.py --ids                 # regulation id -> case -> days
    python caltab.py --root <livecpk root> # per-day match demand of a whole world

The last one is the useful one. A calendar day holds 792 match ids (280 before 0.2.0) and the scheduler at
0x141350290 drops the rest without a word, so a world that asks for more than that on a day
loses matches silently. `daydemand.py` measures that from a running season; this predicts it
from the files, which means it can be answered before a world is ever built.

Our own leagues do not take a shipped case: the date stub gives them the big-league calendar
shifted by nought to six days. `--set <name>` reads those shifts straight out of the patch
set's own note, so the prediction matches whatever is actually installed; `--offsets
11:0,49:1,...` says them by hand instead.

How many matches a round is worth depends on the shape of the competition, which the
regulation row carries at +0x09: format 4 and 5 are leagues, so every round is half the club
count; formats 1 to 3 are knockouts, where the field halves each round. Both are models, and
the knockout one especially so -- a cup that seeds byes, or a group stage counted as a
knockout, will be out by some matches. So read the output as "which days are crowded and by
whom", not as a count to the match. A competition the tool cannot place is listed separately
rather than guessed at.

Nothing is written, and the game is not started.
"""
import os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import boundscan
import pesdb
import json
import re
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from capstone.x86 import X86_OP_IMM, X86_OP_REG

SWITCH_TABLE = 0x1415801ec     # dword per case: the case's entry, as an RVA
CASE_BYTES = 0x1415802e8       # one byte per regulation id 1..175: which case it takes
NCASES, LAST_ID, CASE_EMPTY = 63, 175, 62
DAY_CAP = 792                  # what a calendar day holds before the scheduler drops the rest:
                               # 792 with the -calendar set (0.2.0), 280 in the game as shipped

REC, R_ID, R_FORMAT, R_CLUBS, R_NAME = 2352, 0x02, 0x09, 0x0b, 0x14
LEAGUE_FORMATS = (4, 5)        # +0x09: 4 round robin, 5 split season; 1..3 are knockouts


class Image:
    def __init__(self):
        self.data, self.secs, self.base = boundscan.image()
        self.md = Cs(CS_ARCH_X86, CS_MODE_64)
        self.md.detail = True

    def off(self, va):
        r = va - self.base
        for _, vaS, vs, rp, rs in self.secs:
            if vaS <= r < vaS + vs:
                d = r - vaS
                return rp + d if d < rs else None
        return None

    def u32(self, va):
        return struct.unpack_from("<I", self.data, self.off(va))[0]

    def code(self, va, n=200):
        o = self.off(va)
        return self.data[o:o + n]


def follow(img, va, depth=0):
    """A case entry tail-jumps or calls its builder; return the builder's address."""
    for ins in img.md.disasm(img.code(va), va):
        if ins.mnemonic in ("jmp", "call") and ins.op_str.startswith("0x"):
            return int(ins.op_str, 16)
        if ins.mnemonic == "ret":
            return None
    return None


def builder(img, va):
    """-> (array address, record count), read off the builder's first lea and count."""
    arr = cnt = None
    for ins in img.md.disasm(img.code(va), va):
        if arr is None and ins.mnemonic == "lea" and "rip" in ins.op_str:
            arr = ins.address + ins.size + ins.operands[1].mem.disp
        elif arr is not None and cnt is None and ins.mnemonic == "mov" \
                and len(ins.operands) == 2 and ins.operands[0].type == X86_OP_REG \
                and ins.operands[1].type == X86_OP_IMM and 0 < ins.operands[1].imm < 0x100:
            cnt = ins.operands[1].imm
        if arr is not None and cnt is not None:
            return arr, cnt
        if ins.mnemonic == "ret":
            break
    return arr, cnt


def cases(img):
    """{case: (array, count, [day of year, ...])}"""
    out = {}
    for c in range(NCASES):
        entry = img.u32(SWITCH_TABLE + c * 4) + 0x140000000
        b = follow(img, entry)
        if b is None:
            continue
        arr, cnt = builder(img, b)
        if not arr or not cnt:
            continue
        o = img.off(arr)
        if o is None:
            continue
        days = [struct.unpack_from("<I", img.data, o + i * 12)[0] for i in range(cnt)]
        if any(d > 366 for d in days):          # not a date array: the lea pointed elsewhere
            continue
        out[c] = (arr, cnt, days)
    return out


def id_case(img):
    o = img.off(CASE_BYTES)
    return {i: img.data[o + i - 1] for i in range(1, LAST_ID + 1)}


def regulations(root):
    p = os.path.join(root, "common", "etc", "pesdb", "CompetitionRegulation.bin")
    raw = pesdb.wesys_unpack(open(p, "rb").read())
    out = {}
    for i in range(len(raw) // REC):
        r = raw[i * REC:(i + 1) * REC]
        rid = struct.unpack_from("<H", r, R_ID)[0]
        out.setdefault(rid, (r[R_CLUBS] & 0x3f, r[R_FORMAT],
                             r[R_NAME:R_NAME + 0x73].split(b"\0")[0].decode("latin1", "replace")))
    return out


def set_offsets(name):
    """{regulation id: day shift} out of the date-stub patch's own note in a set json."""
    p = os.path.join(os.path.dirname(HERE), "patches", name + ".json")
    note = ""
    for patch in json.load(open(p))["patches"]:
        m = re.search(r"date-spread stub and its table \(([^)]*)\)", patch.get("why", ""))
        if m:
            note = m.group(1)
    if not note:
        raise SystemExit("no date-stub patch in %s" % p)
    out = {}
    for part in note.split(", "):
        k, v = part.split(":")
        out[int(k)] = int(v.strip().lstrip("+"))
    return out


def main(argv):
    img = Image()
    cs = cases(img)
    idc = id_case(img)

    if "--root" not in argv and "--ids" not in argv:
        print("%d of %d cases carry a date array" % (len(cs), NCASES))
        for c, (arr, cnt, days) in sorted(cs.items()):
            print("  case %-3d array 0x%x  %2d rounds  days %s%s"
                  % (c, arr, cnt, ", ".join(str(d) for d in days[:8]),
                     " ..." if cnt > 8 else ""))
        return 0

    if "--ids" in argv:
        for rid in range(1, LAST_ID + 1):
            c = idc[rid]
            if c == CASE_EMPTY or c not in cs:
                continue
            print("  reg %-4d case %-3d %2d rounds, first day %d"
                  % (rid, c, cs[c][1], cs[c][2][0]))
        return 0

    root = argv[argv.index("--root") + 1]
    offsets = {}
    if "--set" in argv:
        offsets = set_offsets(argv[argv.index("--set") + 1])
        print("date shifts from the patch set: %d leagues" % len(offsets))
    if "--offsets" in argv:
        for part in argv[argv.index("--offsets") + 1].split(","):
            k, v = part.split(":")
            offsets[int(k)] = int(v)

    regs = regulations(root)
    load, who, unknown = {}, {}, []
    for rid, (clubs, fmt, nm) in sorted(regs.items()):
        if rid in offsets:
            days = [(d + offsets[rid]) % 365 for d in cs[5][2]]   # the big-league calendar
        elif rid <= LAST_ID and idc[rid] != CASE_EMPTY and idc[rid] in cs:
            days = cs[idc[rid]][2]
        else:
            unknown.append((rid, nm, clubs))
            continue
        for r, d in enumerate(days):
            per = clubs // 2 if fmt in LEAGUE_FORMATS else max(1, clubs // 2 >> r)
            load[d] = load.get(d, 0) + per
            who.setdefault(d, []).append(nm)

    over = [(d, n) for d, n in sorted(load.items()) if n > DAY_CAP]
    print("%d competitions dated, %d the tool cannot place" % (len(regs) - len(unknown), len(unknown)))
    print("busiest day: %d matches on day %d (the cap is %d)"
          % (max(load.values()), max(load, key=load.get), DAY_CAP))
    if not over:
        print("no day is over the cap")
    for d, n in over:
        print("  day %-4d %4d matches, %d over: %s" % (d, n, n - DAY_CAP, ", ".join(who[d])))
    print("")
    print("the ten busiest days:")
    for d, n in sorted(load.items(), key=lambda kv: -kv[1])[:10]:
        print("  day %-4d %4d matches  %s" % (d, n, ", ".join(sorted(set(who[d])))[:110]))
    if unknown and "--verbose" in argv:
        print("\nnot placed (no case, or a case with no array):")
        for rid, nm, clubs in unknown:
            print("  reg %-4d %-40s %d clubs" % (rid, nm, clubs))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
