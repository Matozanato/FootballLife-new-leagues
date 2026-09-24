"""The date-spread stub: fixture dates for any regulation id, on a weekday of our choosing.

The date-template switch in 0x14157f810 (findings.md, "A new league gets no dates") sends
every free regulation id to case 62, which returns an empty vector, so a new league is
never scheduled.  Setting an id's case byte to 5 gives it the big-league calendar, but
then every new league lands on the same weekday as the ten shipped ones, and a calendar
day holds 280 match ids at most (0x141350290): fourteen leagues already put 271 on the
busiest day.  The other weekdays are nearly empty.

This stub takes case 62's place.  It looks the id up in a byte table:

    0xff          no calendar -- the old empty return, unchanged
    0x00 .. 0x06  the big-league calendar, shifted by that many days
    0x10 .. 0x16  the 16-team domestic cup calendar, shifted by the low three bits

It calls the shipped helper for whichever calendar the byte names, then adds the shift to
every entry's day, wrapping at 365.  The two helpers have the same signature -- id in cx,
&vector in rdx -- and each simply copies a static array of 12-byte date records into the
vector: 38 of them for the league (0x141582550, case 5), 10 for the cup (0x1415810d0,
case 38, the one the Belgian Croky Cup uses).  The shift loop therefore does not care
which of the two was called.

The switch's `ja` for ids above 175 is pointed at the same stub, so the table covers ids
1..255 whichever way the switch would have gone.  That is also the only way a cup can be
dated at all: a cup cannot live below regulation 175 (findings.md, "A cup cannot live
below regulation 175"), and above 175 the switch never consults the case table, so the
`ja` is the single point where a cup id can be caught.  Everything else about the season
is untouched: the same rounds, the same gaps, only on a different day of the week.

The stub lives in the padding at the end of the code section (0x14252e68c..0x14252e800,
372 bytes of zero); the code is 0x56 bytes and the table 256, hand-assembled below and
checked with capstone so that the bytes and the listing cannot disagree.

    python datecave.py                 print the listing for id 11 -> league +2 and
                                       id 186 -> cup
"""
import struct, sys

CAVE = 0x14252e690                   # 16-aligned, inside the section's tail padding
CAVE_END = 0x14252e800
CASE5 = 0x141582550                  # the big-league calendar, called as a function
CASE38 = 0x1415810d0                 # the 16-team domestic cup, same signature, 10 rounds
SWITCH_TABLE = 0x1415801ec           # dword per case, RVA of the case's entry
CASE_EMPTY = 62
JA_SITE = 0x14157f84b                # 0f 87 rel32: ids above 175 -> the empty return
EMPTY_RET = 0x14158013b
CASE_BYTES = 0x1415802e8             # byte per regulation id 1..175: which case it takes
TABLE_SIZE = 256
NO_CALENDAR = 0xff
CUP_BIT = 0x10                       # set in a table byte: take the cup calendar
SHIFT_MASK = 0x07                    # the rest of the byte is the day shift, 0..6
DAYS = 365


def rel8(target, next_ip):
    r = target - next_ip
    assert -128 <= r < 128, r
    return struct.pack("<b", r)


def rel32(target, next_ip):
    return struct.pack("<i", target - next_ip)


def build(offsets):
    """code + table bytes for {regulation id: calendar byte}; ids not listed get no calendar

    Assembled in two passes so a branch can be written before its target is known: pass
    one places every instruction with a zero displacement in order to fix the labels,
    pass two writes the real ones.  Nothing is hand-counted any more, so inserting an
    instruction cannot silently move a jump.
    """
    def emit(lab):
        at = lambda name: lab.get(name, 0)
        b = bytearray()
        b += bytes.fromhex("0fb7c7")                            # movzx eax, di      (id)
        b += b"=" + struct.pack("<I", TABLE_SIZE)               # cmp eax, 256
        b += b"s" + rel8(at("empty"), len(b) + 2)               # jae empty
        b += bytes.fromhex("488d0d") + rel32(at("table") + CAVE, CAVE + len(b) + 7)
        b += bytes.fromhex("0fb60401")                          # movzx eax, byte [rcx + rax]
        b += b"<" + bytes([NO_CALENDAR])                        # cmp al, 0xff
        b += b"t" + rel8(at("empty"), len(b) + 2)               # je empty
        b += bytes.fromhex("0fb7cf")                            # movzx ecx, di      (id)
        b += bytes.fromhex("8bf8")                              # mov edi, eax       (rdi is callee-saved)
        b += bytes.fromhex("83e7") + bytes([SHIFT_MASK])        # and edi, 7         (the day shift)
        b += bytes.fromhex("488bd3")                            # mov rdx, rbx       (&vector)
        b += bytes.fromhex("4c8d4520")                          # lea r8, [rbp + 0x20]
        b += bytes.fromhex("a8") + bytes([CUP_BIT])             # test al, 0x10
        b += b"u" + rel8(at("cup"), len(b) + 2)                 # jnz cup
        b += b"\xe8" + rel32(CASE5, CAVE + len(b) + 5)          # call the league calendar
        b += b"\xeb" + rel8(at("after"), len(b) + 2)            # jmp after
        lab["cup"] = len(b)
        b += b"\xe8" + rel32(CASE38, CAVE + len(b) + 5)         # cup: call the cup calendar
        lab["after"] = len(b)
        b += bytes.fromhex("488b0b")                            # after: mov rcx, [rbx]      (begin)
        b += bytes.fromhex("488b5308")                          # mov rdx, [rbx + 8]         (end)
        lab["loop"] = len(b)
        b += bytes.fromhex("483bca")                            # loop: cmp rcx, rdx
        b += b"s" + rel8(at("empty"), len(b) + 2)               # jae done
        b += bytes.fromhex("8b01")                              # mov eax, [rcx]     (day)
        b += bytes.fromhex("03c7")                              # add eax, edi
        b += b"=" + struct.pack("<I", DAYS)                     # cmp eax, 365
        b += b"r" + rel8(at("store"), len(b) + 2)               # jb store
        b += b"-" + struct.pack("<I", DAYS)                     # sub eax, 365
        lab["store"] = len(b)
        b += bytes.fromhex("8901")                              # store: mov [rcx], eax
        b += bytes.fromhex("4883c10c")                          # add rcx, 12
        b += b"\xeb" + rel8(at("loop"), len(b) + 2)             # jmp loop
        lab["empty"] = len(b)
        b += bytes.fromhex("4883c4205f5b5dc3")                  # done: add rsp,0x20; pop rdi,rbx,rbp; ret
        lab["table"] = len(b)
        return b

    lab = {}
    emit(lab)                                  # pass one: fix the labels
    b = bytearray(emit(dict(lab)))             # pass two: write the displacements
    code_len = lab["table"]
    table = bytearray([NO_CALENDAR] * TABLE_SIZE)
    for k, v in offsets.items():
        if not 1 <= k < TABLE_SIZE:
            raise SystemExit("regulation id %d is outside the stub's table (1..255)" % k)
        if v & ~(CUP_BIT | SHIFT_MASK) or (v & SHIFT_MASK) > 6:
            raise SystemExit("calendar byte 0x%02x for id %d is neither a day shift 0..6 "
                             "nor one with the cup bit 0x10 set" % (v, k))
        table[k] = v
    b += table
    if CAVE + len(b) > CAVE_END:
        raise SystemExit("the stub and its table want %d bytes, the cave holds %d"
                         % (len(b), CAVE_END - CAVE))
    return bytes(b), code_len


def league(shift=0):
    """table byte: the big-league calendar, shifted by `shift` days"""
    return shift


def cup(shift=0):
    """table byte: the 16-team domestic cup calendar, shifted by `shift` days"""
    return CUP_BIT | shift


def listing(code, code_len):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_64
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    out = []
    for i in md.disasm(code[:code_len], CAVE):
        out.append("%x  %-6s %s" % (i.address, i.mnemonic, i.op_str))
    return out


def patches(offsets, exe_bytes, off_of):
    """the three patches: the stub, the switch dword for case 62, the `ja` for ids > 175"""
    code, _ = build(offsets)
    old = exe_bytes[off_of(CAVE):off_of(CAVE) + len(code)]
    if any(old):
        raise SystemExit("the code cave at 0x%x is not empty in this exe" % CAVE)
    dw = SWITCH_TABLE + CASE_EMPTY * 4
    old_dw = exe_bytes[off_of(dw):off_of(dw) + 4]
    assert struct.unpack("<I", old_dw)[0] + 0x140000000 == EMPTY_RET, old_dw.hex()
    old_ja = exe_bytes[off_of(JA_SITE):off_of(JA_SITE) + 6]
    assert old_ja == b"\x0f\x87" + rel32(EMPTY_RET, JA_SITE + 6), old_ja.hex()
    shown = ", ".join("%d:%s+%d" % (k, "cup" if v & CUP_BIT else "league", v & SHIFT_MASK)
                      for k, v in sorted(offsets.items()))
    # An id the shipped game already used keeps its shipped case byte -- 76..78 are
    # Copa Libertadores and friends on case 3, 74 case 25, 138..140 cases 44..46 -- so
    # the switch never sends it to case 62 and the stub never sees it: the league gets a
    # cup calendar, no league fixtures, and the standings stay at -1 (the 0x1413236e4
    # crash on team confirm).  Point such ids at the empty case, which is now the stub.
    reused = []
    for k in sorted(offsets):
        if k > 175:
            continue                          # above the table: the `ja` covers it
        b = exe_bytes[off_of(CASE_BYTES + k - 1)]
        if b != CASE_EMPTY:
            reused.append({"va": "0x%x" % (CASE_BYTES + k - 1), "old": "%02x" % b,
                           "new": "%02x" % CASE_EMPTY,
                           "why": "fixture dates: regulation %d reuses a shipped id "
                                  "(case %d); send it to the stub" % (k, b),
                           "asm": "jump-table byte"})
    return reused + [
        {"va": "0x%x" % CAVE, "old": old.hex(), "new": code.hex(),
         "why": "fixture dates: the date-spread stub and its table (%s)" % shown,
         "asm": "code cave"},
        {"va": "0x%x" % dw, "old": old_dw.hex(),
         "new": struct.pack("<I", CAVE - 0x140000000).hex(),
         "why": "fixture dates: case 62 (free ids 1..175) goes to the stub",
         "asm": "jump-table dword"},
        {"va": "0x%x" % JA_SITE, "old": old_ja.hex(),
         "new": (b"\x0f\x87" + rel32(CAVE, JA_SITE + 6)).hex(),
         "why": "fixture dates: ids 176..1025 go to the stub instead of the empty return",
         "asm": "ja rel32"},
    ]


if __name__ == "__main__":
    code, code_len = build({11: league(2), 186: cup()})
    print("\n".join(listing(code, code_len)))
    print("%d bytes of code, %d of table, cave 0x%x..0x%x, %d spare"
          % (code_len, TABLE_SIZE, CAVE, CAVE + len(code), CAVE_END - CAVE - len(code)))
