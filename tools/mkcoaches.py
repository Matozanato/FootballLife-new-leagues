"""python mkcoaches.py <world pesdb dir> --coach <shipped Coach.bin> [--min-id N] [--name FMT] [--out Coach.bin]

Give every added club a manager of its own.

A club names its manager in the first dword of its Team.bin record (+0x00): Arsenal carries
102109, which is Mikel Arteta in Coach.bin, Juventus 1195 (Igor Tudor). All 743 shipped clubs
point at a coach Coach.bin has. Worlds built by mkworld.py before 2026-09-26 (and clubs added
with mkteams.py) give each new club a fresh value there but no Coach record, so the game makes
one up -- and every made-up manager is a copy of the first record, Jorge Jesus. In Edit >
Managers every club of every added league then lists "Jorge Jesus". mkworld.py now writes the
Coach.bin itself; this fixes a world that was built without it.

This writes a Coach.bin that is the shipped one plus one record per added club whose manager
id is missing: that id, a placeholder name (--name, default "FL M%04d", numbered by the club's
position among the added clubs, so FL 0031 gets FL M0031), and the rest cloned from a shipped
coach no club employs. The Coach record is 100 bytes: id at +0, a packed dword at +4 whose low
nine bits are the nationality (the same country codes as the club's), and the name twice, at
+0x08 and +0x36, 46 bytes each. The nationality is set to the club's own country (9 bits at bit
562 of its Team.bin record); the other bits of +4 are the template's.

Shipped coaches and clubs are not touched; records are only appended. Without --out it prints
what it would do. It never writes over its input. The output goes into the same
common/etc/pesdb folder as the world's Team.bin; deleting it undoes it.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pesdb

T_REC, T_ID, T_COACH = 1532, 0x08, 0x00
T_NAT_BIT, NAT_BITS = 562, 9
C_REC, C_ID, C_BITS = 100, 0x00, 0x04
C_NAME1, C_NAME2, C_NAME_LEN = 0x08, 0x36, 46
FIRST_NEW_ID = 71578          # the shipped club ids end at 71577 (Selangor FC)


def u32(b, o):
    return int.from_bytes(b[o:o + 4], "little")


def club_country(rec):
    lo, hi = T_NAT_BIT // 8, (T_NAT_BIT + NAT_BITS + 7) // 8
    return (int.from_bytes(rec[lo:hi], "little") >> (T_NAT_BIT % 8)) & ((1 << NAT_BITS) - 1)


def add_coaches(coaches, teams, min_id=FIRST_NEW_ID, fmt="FL M%04d"):
    """coaches, teams: unpacked Coach.bin and Team.bin. Returns (records to append, stats)."""
    assert len(coaches) % C_REC == 0 and len(teams) % T_REC == 0
    have = {u32(coaches, i) for i in range(0, len(coaches), C_REC)}
    # template: the last shipped coach no club employs, so a clone copies nobody's record
    employed = {u32(teams, o + T_COACH) for o in range(0, len(teams), T_REC)}
    free = [i for i in range(0, len(coaches), C_REC) if u32(coaches, i) not in employed]
    tpl = coaches[free[-1]:free[-1] + C_REC] if free else coaches[-C_REC:]

    add, new_ids = bytearray(), set()
    clubs = kept = shared = 0
    for o in range(0, len(teams), T_REC):
        rec = teams[o:o + T_REC]
        if u32(rec, T_ID) < min_id:
            continue
        clubs += 1
        cid = u32(rec, T_COACH)
        if cid in have:
            kept += 1
            continue
        if cid in new_ids:                 # two clubs naming one missing manager: one record
            shared += 1
            continue
        new_ids.add(cid)
        r = bytearray(tpl)
        r[C_ID:C_ID + 4] = cid.to_bytes(4, "little")
        nm = (fmt % clubs if "%" in fmt else fmt).encode("utf-8")[:C_NAME_LEN - 1]
        nm += bytes(C_NAME_LEN - len(nm))
        r[C_NAME1:C_NAME1 + C_NAME_LEN] = nm
        r[C_NAME2:C_NAME2 + C_NAME_LEN] = nm
        bits = (u32(r, C_BITS) & ~0x1ff) | club_country(rec)
        r[C_BITS:C_BITS + 4] = bits.to_bytes(4, "little")
        add += r
    return bytes(add), {"clubs": clubs, "kept": kept, "shared": shared,
                        "added": len(add) // C_REC, "template": u32(tpl, 0),
                        "template_name": pesdb.cstr(tpl[C_NAME1:C_NAME1 + C_NAME_LEN])}


def main():
    a = sys.argv[1:]
    if not a or a[0].startswith("-") or "--coach" not in a:
        print(__doc__)
        return 1
    db = a[0]
    coach_in = a[a.index("--coach") + 1]
    min_id = int(a[a.index("--min-id") + 1]) if "--min-id" in a else FIRST_NEW_ID
    fmt = a[a.index("--name") + 1] if "--name" in a else "FL M%04d"
    out = a[a.index("--out") + 1] if "--out" in a else None

    teams = pesdb.wesys_unpack(open(os.path.join(db, "Team.bin"), "rb").read())
    craw = open(coach_in, "rb").read()
    coaches = pesdb.wesys_unpack(craw)
    add, s = add_coaches(coaches, teams, min_id, fmt)
    print("clubs from id %d: %d; manager already in Coach.bin: %d; shared missing id: %d"
          % (min_id, s["clubs"], s["kept"], s["shared"]))
    print("template coach %d (%s)" % (s["template"], s["template_name"]))
    print("%s %d coaches (%d shipped -> %d)"
          % ("added" if out else "would add", s["added"], len(coaches) // C_REC,
             len(coaches) // C_REC + s["added"]))
    if out:
        if os.path.abspath(out) == os.path.abspath(coach_in):
            raise SystemExit("--out is the input file; write somewhere else and move it in yourself")
        open(out, "wb").write(pesdb.wesys_pack(coaches + add, craw[:3]))
        print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
