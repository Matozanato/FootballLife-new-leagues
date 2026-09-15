"""python mkteams.py [--count N] [--source IDX | --sources A,B,C] [--out <dir>]  -> a Team.bin with more clubs

Writing clubs into the running process proved the raised caps hold, and then a reload wiped
them: the edit save is a delta over base data, and a club with no base record has nothing to
be a delta of.  The base is common/etc/pesdb/Team.bin -- 743 records of 1532 bytes, packed
in Konami's WESYS zlib container, shipped in download/data_s2526*.cpk and overridable by
dropping a file of the same path under one of Sider's livecpk roots.

The club id is the dword at +0x08.  It is unique, ascending, and matches the ids in the
live block exactly, which is what identifies the field: the last three are 71574, 71576 and
71577, and 71577 is Selangor FC, the block's record 742.  The dword at +0x00 is a second id
of some other kind, also unique, so new records take fresh values there too.

The name is in the record after all, at +0x170, with the three-letter abbreviation at
+0x372 -- the same two strings the live block carries at +0x04 and +0x4a.  So a placeholder
club is complete here: clone, new ids, new name, new abbreviation.

One prototype for every club is what put twenty-two players in the same blue shirt on the
pitch in FL 741 v FL 747: the kit is not in this record, it is an asset keyed by the club
id the record was cloned from, so every club cloned from one source is visually that club.
`--sources` takes a list and rotates through it, which buys whatever colours those clubs
happen to wear -- not the plain blue and red the project wants, but enough to tell the two
halves of a fixture apart.  It clones more than the kit, so keep the list to ordinary
league clubs, away from anything with unusual links.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
import pesdb                                        # WESYS pack/unpack, record sizes

REC = 1532
ID_OFF, ALT_OFF = 0x08, 0x00
NAME_OFF, NAME_LEN = 0x170, 0x46
ABBR_OFF, ABBR_LEN = 0x372, 3


def main():
    a = sys.argv[1:]
    n = int(a[a.index("--count") + 1]) if "--count" in a else 10
    name = a[a.index("--name") + 1] if "--name" in a else "FL Test %02d"
    abbr = a[a.index("--abbr") + 1] if "--abbr" in a else "T%02d"
    src = int(a[a.index("--source") + 1]) if "--source" in a else None
    srcs = ([int(x) for x in a[a.index("--sources") + 1].split(",")]
            if "--sources" in a else None)
    inp = a[a.index("--in") + 1] if "--in" in a else None
    out = a[a.index("--out") + 1] if "--out" in a else None
    if not inp or not out:
        print(__doc__)
        print("give --in <extracted Team.bin> and --out <livecpk root>")
        return 1

    raw = pesdb.wesys_unpack(open(inp, "rb").read())
    if len(raw) % REC:
        print("%s is %d bytes, not a whole number of %d-byte records" % (inp, len(raw), REC))
        return 2
    count = len(raw) // REC
    rec = lambda i: raw[i * REC:(i + 1) * REC]
    ids = [int.from_bytes(rec(i)[ID_OFF:ID_OFF + 4], "little") for i in range(count)]
    alts = [int.from_bytes(rec(i)[ALT_OFF:ALT_OFF + 4], "little") for i in range(count)]
    if src is None:
        src = count - 1
    print("%s: %d clubs, highest id %d, highest alt id %d" % (os.path.basename(inp), count,
                                                              max(ids), max(alts)))

    if srcs is None:
        srcs = [src]
    named = lambda i: rec(i)[NAME_OFF:NAME_OFF + NAME_LEN].split(b"\0")[0].decode("utf-8", "replace")
    print("cloning from %s" % ", ".join("%d (%s)" % (i, named(i)) for i in srcs))
    add = bytearray()
    for j in range(n):
        r = bytearray(rec(srcs[j % len(srcs)]))
        r[ID_OFF:ID_OFF + 4] = (max(ids) + 1 + j).to_bytes(4, "little")
        r[ALT_OFF:ALT_OFF + 4] = (max(alts) + 1 + j).to_bytes(4, "little")
        nm = (name % (j + 1) if "%" in name else name).encode("utf-8")[:NAME_LEN - 1]
        ab = (abbr % (j + 1) if "%" in abbr else abbr).encode("utf-8")[:ABBR_LEN]
        r[NAME_OFF:NAME_OFF + NAME_LEN] = nm + b"\0" * (NAME_LEN - len(nm))
        r[ABBR_OFF:ABBR_OFF + ABBR_LEN] = ab + b"\0" * (ABBR_LEN - len(ab))
        add += r
        print("  club %d: id %d, alt id %d, %s (%s)"
              % (count + j, max(ids) + 1 + j, max(alts) + 1 + j, nm.decode(), ab.decode()))

    d = os.path.join(out, "common", "etc", "pesdb")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "Team.bin")
    open(p, "wb").write(pesdb.wesys_pack(bytes(raw) + bytes(add)))
    print("")
    print("wrote %s: %d clubs, %d bytes packed" % (p, count + n, os.path.getsize(p)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
