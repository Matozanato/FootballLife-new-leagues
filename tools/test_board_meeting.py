"""fl26swiss.dll: the board's objectives meeting names the cup of the club's own continent (B395).

The owner's judges (18 calls) have asked fl26swiss for a club's continent since 0.2.0; the meeting's
own text came from 0x140f446c0, which asks the game twice more, so a club of a new Asian league was
still told about "the UEFA Champions League". Checked here, without the game:

1. the source lists the judges' 18 calls and the meeting's 2, the two groups apart;
2. when a game exe is on this PC (FL27_EXE / FL26_EXE, else E:/FL/FL27/game/FL_2027.exe and
   E:/FL/FL26/game/FL_2026.exe): every one of the 20 sites is `call 0x1415111c0` in the file, and
   0x140f446c0 is the 62 bytes the fix was read from (0 -> 4, 2 -> 0x10, else 0xa), reached from
   0x140f44b30 only;
3. the DLL in tools/native is newer than the change (it holds the meeting's log line).

    python tools/test_board_meeting.py
"""
import os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "native", "fl26swiss.c")
DLL = os.path.join(HERE, "native", "fl26swiss.dll")
BASE, CONT = 0x140000000, 0x1415111c0
MEET_FN = bytes.fromhex("894c24084883ec28488d4c2430e8eeca5c0085c0750ab8040000004883c428c3"
                        "488d4c2430e8d6ca5c0083f802b8100000007405b80a0000004883c428c3")
N = 0


def ok(what, cond):
    global N
    N += 1
    if not cond:
        print("FAIL:", what)
        sys.exit(1)
    print("ok:", what)


def sections(path):
    raw = open(path, "rb").read()
    pe = struct.unpack_from("<I", raw, 0x3c)[0]
    nsec, optsz = struct.unpack_from("<H", raw, pe + 6)[0], struct.unpack_from("<H", raw, pe + 20)[0]
    base = struct.unpack_from("<Q", raw, pe + 24 + 24)[0]
    out = []
    for i in range(nsec):
        o = pe + 24 + optsz + 40 * i
        vsz, va, rsz, rp = struct.unpack_from("<IIII", raw, o + 8)
        out.append((base + va, vsz, rp, rsz))
    return raw, out


def read(raw, secs, va, n):
    for v, vsz, rp, rsz in secs:
        if v <= va < v + vsz and va - v + n <= rsz:
            return raw[rp + va - v:rp + va - v + n]
    return b""


src = open(SRC, encoding="utf8").read()


def table(name):
    m = re.search(r"static const uint32_t %s\[\] = \{(.*?)\};" % name, src, re.S)
    return [int(x, 16) for x in re.findall(r"0x[0-9a-fA-F]+", m.group(1))] if m else []


calls, meet = table("CONT_CALLS"), table("CONT_MEET")
ok("the judges' 18 calls, as before", len(calls) == 18 and calls[0] == 0xedc75a and calls[-1] == 0xede324)
ok("the meeting's 2 calls, inside 0x140f446c0", meet == [0xf446cd, 0xf446e5])
ok("no site in both groups", not set(calls) & set(meet))
ok("the meeting's calls are a group of their own (a miss leaves the judges patched)",
   "cont_group(exe_base, CONT_MEET" in src and src.index("cont_group(exe_base, CONT_CALLS") < src.index("cont_group(exe_base, CONT_MEET"))

for label, env, default in (("FL 2027", "FL27_EXE", "E:/FL/FL27/game/FL_2027.exe"),
                            ("FL 2026", "FL26_EXE", "E:/FL/FL26/game/FL_2026.exe")):
    exe = os.environ.get(env) or default
    if not os.path.exists(exe):
        print("skipped: %s's exe is not on this PC (%s)" % (label, exe))
        continue
    raw, secs = sections(exe)
    bad = []
    for rva in calls + meet:
        b = read(raw, secs, BASE + rva, 5)
        if len(b) != 5 or b[0] != 0xE8 or BASE + rva + 5 + struct.unpack_from("<i", b, 1)[0] != CONT:
            bad.append(hex(rva))
    ok("%s: all 20 sites call 0x1415111c0 in the file%s" % (label, bad and " -- not: " + " ".join(bad) or ""), not bad)
    ok("%s: 0x140f446c0 is the function the fix was read from" % label, read(raw, secs, 0x140f446c0, len(MEET_FN)) == MEET_FN)
    text = next(((v, raw[rp:rp + rsz]) for v, vsz, rp, rsz in secs if v <= 0x140f446c0 < v + vsz), None)
    callers = []
    at = text[1].find(b"\xe8")
    while at >= 0 and at + 5 <= len(text[1]):
        if text[0] + at + 5 + struct.unpack_from("<i", text[1], at + 1)[0] == 0x140f446c0:
            callers.append(text[0] + at)
        at = text[1].find(b"\xe8", at + 1)
    ok("%s: it is called from the objective-text function only (%s)" % (label, " ".join("%x" % c for c in callers)),
       callers == [0x140f44d85, 0x140f44f4c, 0x140f44fef])

ok("tools/native/fl26swiss.dll holds the change", b"the meeting names the same cup" in open(DLL, "rb").read())
print("all %d checks passed" % N)
