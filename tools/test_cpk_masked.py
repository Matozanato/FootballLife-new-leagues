"""python test_cpk_masked.py [file.cpk]  -> a .cpk whose @UTF tables are masked unpacks like the plain one

GitHub/Discord 04.11.2026: "Tables Not Extracted" -- Settings > Game folder stopped on
`ValueError: not a CRI table: b'\\x1f\\x9e\\xf3\\xf5'`, which is "@UTF" under CRI's table mask.
This copies a .cpk of the game (FL26_DIR / FL26_EXE, or the path given), masks its CPK header
table and its TOC, and checks that cpkread reads the same files with the same bytes from both.
"""
import os
import shutil
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cpkread


def pick():
    if len(sys.argv) > 1:
        return sys.argv[1]
    import flpaths
    game = os.path.dirname(flpaths.need_exe())
    for name in sorted(os.listdir(os.path.join(game, "download"))):
        if name.startswith("data_s") and name.endswith(".cpk"):
            return os.path.join(game, "download", name)
    raise SystemExit("no download/data_s*.cpk in %s" % game)


def mask_table(buf, at):
    """mask the @UTF table whose 16-byte chunk header starts at `at`, in place"""
    size = struct.unpack("<Q", bytes(buf[at + 8:at + 16]))[0]
    start = at + 16
    buf[start:start + size + 8] = cpkread.utf_decrypt(bytes(buf[start:start + size + 8]))


def main():
    src = pick()
    tmp = tempfile.mkdtemp(prefix="cpkmask_")
    try:
        masked = os.path.join(tmp, "masked.cpk")
        buf = bytearray(open(src, "rb").read())
        hdr = cpkread.utf_parse(bytes(buf[16:16 + struct.unpack("<Q", bytes(buf[8:16]))[0] + 8]))[0]
        mask_table(buf, 0)
        mask_table(buf, hdr["TocOffset"])
        open(masked, "wb").write(buf)
        assert buf[16:20] != b"@UTF", "the header table was not masked"
        a, b = os.path.join(tmp, "a"), os.path.join(tmp, "b")
        na = cpkread.extract(src, a)
        nb = cpkread.extract(masked, b)
        assert na == nb and na > 0, (na, nb)
        assert cpkread.names(src) == cpkread.names(masked)
        for root, _, files in os.walk(a):
            for fn in files:
                p = os.path.join(root, fn)
                q = os.path.join(b, os.path.relpath(p, a))
                assert open(p, "rb").read() == open(q, "rb").read(), p
        print("ok: %s, %d files read the same from the masked copy" % (os.path.basename(src), na))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
