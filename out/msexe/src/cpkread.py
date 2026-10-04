"""python cpkread.py <file.cpk> <out dir> [name part ...]   -> unpack a CRI .cpk

The same reader as cpk.py / cpkx.py, as functions a program can call without running a
script: the league builder unpacks the game's tables with it, in its own process, so the
frozen .exe needs no Python. extract() writes every file whose path contains one of `parts`
(all of them when there are none) and returns how many it wrote.
"""
import os, struct, sys


def read_val(b, p, typ, gstr):
    fmt = {0: (">B", 1), 1: (">b", 1), 2: (">H", 2), 3: (">h", 2), 4: (">I", 4), 5: (">i", 4),
           6: (">Q", 8), 7: (">q", 8), 8: (">f", 4)}
    if typ in fmt:
        f, n = fmt[typ]
        return struct.unpack(f, b[p:p + n])[0], p + n
    if typ == 0xa:
        return gstr(struct.unpack(">I", b[p:p + 4])[0]), p + 4
    if typ == 0xb:
        o, s = struct.unpack(">QI", b[p:p + 12])
        return ("DATA", o, s), p + 12
    raise ValueError("@UTF column type %x" % typ)


def utf_parse(data):
    if data[:4] != b"@UTF":
        raise ValueError("not a CRI table: %r" % data[:4])
    size, = struct.unpack(">I", data[4:8])
    b = data[8:8 + size]
    rows_off, strings_off, data_off, table_name, n_cols, row_len, n_rows = struct.unpack(">IIIIHHI", b[:24])

    def gstr(o):
        e = b.index(b"\0", strings_off + o)
        return b[strings_off + o:e].decode("utf-8", "replace")
    cols, p = [], 24
    for _ in range(n_cols):
        flags = b[p]
        noff, = struct.unpack(">I", b[p + 1:p + 5])
        p += 5
        storage, typ, const = flags & 0xf0, flags & 0x0f, None
        if storage == 0x30:
            const, p = read_val(b, p, typ, gstr)
        cols.append((gstr(noff), storage, typ, const))
    rows = []
    for r in range(n_rows):
        p, row = rows_off + r * row_len, {}
        for name, storage, typ, const in cols:
            if storage == 0x30:
                row[name] = const
            elif storage == 0x10:
                row[name] = None
            else:
                row[name], p = read_val(b, p, typ, gstr)
        rows.append(row)
    return rows


def crilayla(src):
    usize, hsize = struct.unpack("<II", src[8:16])
    head = src[16 + hsize:16 + hsize + 0x100]      # the first 0x100 bytes are stored plain
    dest = bytearray(usize)
    data = src[16:16 + hsize]
    st = {"pos": len(data) - 1, "pool": 0, "count": 0}  # read bit by bit from the end

    def bits(n):
        v = 0
        while n > 0:
            if st["count"] == 0:
                st["pool"], st["count"] = data[st["pos"]], 8
                st["pos"] -= 1
            t = min(n, st["count"])
            v = (v << t) | ((st["pool"] >> (st["count"] - t)) & ((1 << t) - 1))
            st["count"] -= t
            n -= t
        return v
    out, vle = usize - 1, (2, 3, 5, 8)
    while out >= 0:
        if bits(1):
            ref, lvl, ln = bits(13) + 3, 0, 3
            while True:
                v = bits(vle[lvl] if lvl < 4 else 8)
                ln += v
                if lvl < 3:
                    if v != (1 << vle[lvl]) - 1:
                        break
                    lvl += 1
                elif v != 255:
                    break
            for _ in range(ln):
                dest[out] = dest[out + ref]
                out -= 1
        else:
            dest[out] = bits(8)
            out -= 1
    return bytes(head) + bytes(dest)


def toc(f):
    """(content base, [row]) of an open .cpk"""
    hdr = f.read(16)
    cpk = utf_parse(f.read(struct.unpack("<Q", hdr[8:16])[0] + 8))[0]
    t_off, ca = cpk["TocOffset"], cpk.get("ContentOffset", 0)
    f.seek(t_off)
    t = f.read(16)
    return (min(t_off, ca) if ca else t_off), utf_parse(f.read(struct.unpack("<Q", t[8:16])[0] + 8))


def path_of(r):
    return (r["DirName"] + "/" + r["FileName"]) if r["DirName"] else r["FileName"]


def names(path):
    """every file path in a .cpk -- the table of contents only, nothing is unpacked"""
    with open(path, "rb") as f:
        return [path_of(r) for r in toc(f)[1]]


def extract(path, outdir, parts=(), log=None):
    n = 0
    with open(path, "rb") as f:
        base, rows = toc(f)
        for r in rows:
            full = path_of(r)
            if parts and not any(p in full for p in parts):
                continue
            f.seek(base + r["FileOffset"])
            d = f.read(r["FileSize"])
            if r["ExtractSize"] > r["FileSize"] and d[:8] == b"CRILAYLA":
                d = crilayla(d)
            op = os.path.join(outdir, full.replace("/", os.sep))
            os.makedirs(os.path.dirname(op), exist_ok=True)
            with open(op, "wb") as o:
                o.write(d)
            n += 1
            if log:
                log("%d %s" % (len(d), full))
    return n


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    print("%d files" % extract(sys.argv[1], sys.argv[2], sys.argv[3:], log=print))
