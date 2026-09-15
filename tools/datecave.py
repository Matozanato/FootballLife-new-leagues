"""The date-spread stub: fixture dates for any regulation id, on a weekday of our choosing.

The date-template switch in 0x14157f810 (findings.md, "A new league gets no dates") sends
every free regulation id to case 62, which returns an empty vector, so a new league is
never scheduled.  Setting an id's case byte to 5 gives it the big-league calendar, but
then every new league lands on the same weekday as the ten shipped ones, and a calendar
day holds 280 match ids at most (0x141350290): fourteen leagues already put 271 on the
busiest day.  The other weekdays are nearly empty.

This stub takes case 62's place.  It looks the id up in a byte table -- 0xff means "no
calendar", as before; 0..6 means "the big-league calendar, shifted by that many days" --
calls case 5 for the vector and then adds the shift to every entry's day, wrapping at 365.
The switch's `ja` for ids above 175 is pointed at the same stub, so the table covers ids
1..255 whichever way the switch would have gone.  Everything else about the season is
untouched: the same rounds, the same gaps, only on a different day of the week.

The stub lives in the padding at the end of the code section (0x14252e68c..0x14252e800,
372 bytes of zero); the code is 0x56 bytes and the table 256, hand-assembled below and
checked with capstone so that the bytes and the listing cannot disagree.

    python datecave.py                 print the listing for a table with id 11 -> +2
"""
import struct, sys

CAVE = 0x14252e690                   # 16-aligned, inside the section's tail padding
CAVE_END = 0x14252e800
CASE5 = 0x141582550                  # the big-league calendar, called as a function
SWITCH_TABLE = 0x1415801ec           # dword per case, RVA of the case's entry
CASE_EMPTY = 62
JA_SITE = 0x14157f84b                # 0f 87 rel32: ids above 175 -> the empty return
EMPTY_RET = 0x14158013b
CASE_BYTES = 0x1415802e8             # byte per regulation id 1..175: which case it takes
TABLE_SIZE = 256
NO_CALENDAR = 0xff
DAYS = 365


def rel8(target, next_ip):
    r = target - next_ip
    assert -128 <= r < 128, r
    return struct.pack("<b", r)


def rel32(target, next_ip):
    return struct.pack("<i", target - next_ip)


def build(offsets):
    """code + table bytes for {regulation id: day shift}; ids not listed get no calendar"""
    L = {"empty": 0x4e, "loop": 0x31, "store": 0x46, "table": 0x56}   # fixed layout
    b = bytearray()
    b += b"\x0f\xb7\xc7"                                   # movzx eax, di
    b += b"\x3d" + struct.pack("<I", TABLE_SIZE)          # cmp eax, 256
    b += b"\x73" + rel8(L["empty"], len(b) + 2)           # jae empty
    b += b"\x48\x8d\x0d" + rel32(L["table"], len(b) + 7)  # lea rcx, [rip + table]
    b += b"\x0f\xb6\x04\x01"                              # movzx eax, byte [rcx + rax]
    b += b"\x3c\xff"                                      # cmp al, 0xff
    b += b"\x74" + rel8(L["empty"], len(b) + 2)           # je empty
    b += b"\x0f\xb7\xcf"                                  # movzx ecx, di      (id)
    b += b"\x8b\xf8"                                      # mov edi, eax       (shift, rdi is callee-saved)
    b += b"\x48\x8b\xd3"                                  # mov rdx, rbx       (&vector)
    b += b"\x4c\x8d\x45\x20"                              # lea r8, [rbp + 0x20]
    b += b"\xe8" + rel32(CASE5, CAVE + len(b) + 5)        # call case 5
    b += b"\x48\x8b\x0b"                                  # mov rcx, [rbx]     (begin)
    b += b"\x48\x8b\x53\x08"                              # mov rdx, [rbx + 8] (end)
    assert len(b) == L["loop"]
    b += b"\x48\x3b\xca"                                  # loop: cmp rcx, rdx
    b += b"\x73" + rel8(L["empty"], len(b) + 2)           # jae done
    b += b"\x8b\x01"                                      # mov eax, [rcx]     (day)
    b += b"\x03\xc7"                                      # add eax, edi
    b += b"\x3d" + struct.pack("<I", DAYS)                # cmp eax, 365
    b += b"\x72" + rel8(L["store"], len(b) + 2)           # jb store
    b += b"\x2d" + struct.pack("<I", DAYS)                # sub eax, 365
    assert len(b) == L["store"]
    b += b"\x89\x01"                                      # store: mov [rcx], eax
    b += b"\x48\x83\xc1\x0c"                              # add rcx, 12
    b += b"\xeb" + rel8(L["loop"], len(b) + 2)            # jmp loop
    assert len(b) == L["empty"]
    b += b"\x48\x83\xc4\x20\x5f\x5b\x5d\xc3"              # done/empty: add rsp,0x20; pop rdi; pop rbx; pop rbp; ret
    assert len(b) == L["table"]
    table = bytearray([NO_CALENDAR] * TABLE_SIZE)
    for k, off in offsets.items():
        if not 1 <= k < TABLE_SIZE:
            raise SystemExit("regulation id %d is outside the stub's table (1..255)" % k)
        if not 0 <= off < 7:
            raise SystemExit("day shift %d for id %d is not 0..6" % (off, k))
        table[k] = off
    b += table
    assert CAVE + len(b) <= CAVE_END
    return bytes(b)


def listing(code):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_64
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    out = []
    for i in md.disasm(code[:0x56], CAVE):
        out.append("%x  %-6s %s" % (i.address, i.mnemonic, i.op_str))
    return out


def patches(offsets, exe_bytes, off_of):
    """the three patches: the stub, the switch dword for case 62, the `ja` for ids > 175"""
    code = build(offsets)
    old = exe_bytes[off_of(CAVE):off_of(CAVE) + len(code)]
    if any(old):
        raise SystemExit("the code cave at 0x%x is not empty in this exe" % CAVE)
    dw = SWITCH_TABLE + CASE_EMPTY * 4
    old_dw = exe_bytes[off_of(dw):off_of(dw) + 4]
    assert struct.unpack("<I", old_dw)[0] + 0x140000000 == EMPTY_RET, old_dw.hex()
    old_ja = exe_bytes[off_of(JA_SITE):off_of(JA_SITE) + 6]
    assert old_ja == b"\x0f\x87" + rel32(EMPTY_RET, JA_SITE + 6), old_ja.hex()
    shown = ", ".join("%d:+%d" % (k, v) for k, v in sorted(offsets.items()))
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
    code = build({11: 2})
    print("\n".join(listing(code)))
    print("%d bytes of code, %d of table, cave 0x%x..0x%x, %d spare"
          % (0x56, TABLE_SIZE, CAVE, CAVE + len(code), CAVE_END - CAVE - len(code)))
