"""AFP menu packages (common/menu/**/*.bin): read their pictures and add pictures of our own.

A menu .bin is a WESYS (zlib) file holding one package:

  package header  little-endian {1, 8, offset of TXP2, length of TXP2, name length} + the name
                  ('afp_<menu>.apk'), padded to the offset
  TXP2            big-endian throughout.  From its start:
                    +0x0c  length of the TXP2
                    +0x18  number of textures      +0x1c  texture list: {name, block size, block offset}
                    +0x24  number of pictures      +0x28  picture table: 10 bytes each,
                           {texture, x0, y0, x1, y1} in half pixels of the texture
                    +0x2c  the NAMP that names the pictures
  NAMP            'NAMP', 0, 0x00010100, 0x00010100, count, u16 a, u16 b, offset of the entries;
                  entries {hash, index, name offset} sorted by hash.  a is half the largest power
                  of two not above the count (at least 1), b = 2a - 1.
  texture block   {raw size, packed size, data}: packed 0 means stored as it is, otherwise 'nlz'
                  (below).  The raw data is a TXDT: a 0x40-byte header (width and height u16 at
                  +0x10, the format in the last byte of the dword at +0x14; 0x15 = 32-bit ARGB)
                  and the pixels.

A picture is found by name: the game hashes the name it is asked for and looks it up in the
NAMP (namehash below; it matches all 1441 names in FL26's own menus).  All of this was read out
of FL_2026.exe: the texture block reader 0x141f9d9d0, 'nlz' 0x141f9d7f0, the TXDT byte swap
0x141f9d600, the NAMP swap 0x141f9d570 (measured 2026-09-28).
"""
import struct, zlib

WESYS = b"WESYS"


def nlz(src, rawsize):
    """the game's 'nlz': LZSS with a 4096-byte window starting at 0xfee, a flag byte per eight
    items (bit set = one literal byte; clear = two bytes: offset b1 | (b2 & 0xf0) << 4,
    length (b2 & 0xf) + 3)"""
    ring = bytearray(4096)
    r, i, flags, out = 0xfee, 0, 0, bytearray()
    while len(out) < rawsize and i < len(src):
        flags >>= 1
        if not flags & 0x100:
            flags = src[i] | 0xff00
            i += 1
            if i >= len(src):
                break
        if flags & 1:
            c = src[i]
            i += 1
            out.append(c)
            ring[r] = c
            r = (r + 1) & 0xfff
        else:
            if i + 1 >= len(src):
                break
            b1, b2 = src[i], src[i + 1]
            i += 2
            off, n = b1 | ((b2 & 0xf0) << 4), (b2 & 0xf) + 3
            for k in range(n):
                c = ring[(off + k) & 0xfff]
                out.append(c)
                ring[r] = c
                r = (r + 1) & 0xfff
    return bytes(out[:rawsize])


def namehash(name):
    """the NAMP key of a name: the low six bits of each character, lowest bit first, shifted into
    a CRC-32 remainder (polynomial 0x04C11DB7, starting at 0, no final xor)"""
    h = 0
    for c in name.encode("latin1"):
        for k in range(6):
            top = h >> 31
            h = ((h << 1) & 0xffffffff) | ((c >> k) & 1)
            if top:
                h ^= 0x04C11DB7
    return h


def namp_params(n):
    if n == 0:
        return 0, 0xffff
    p = 1
    while p * 2 <= n:
        p *= 2
    a = max(1, p // 2)
    return a, 2 * a - 1


def cstr(b, o):
    return b[o:b.index(b"\0", o)].decode("latin1")


def align(b, n):
    return b + bytes(-len(b) % n)


class Package:
    def __init__(self, data):
        self.wesys = data[3:8] == WESYS
        if self.wesys:
            self.prefix = data[:3]
            csz, usz = struct.unpack_from("<II", data, 8)
            data = zlib.decompress(data[16:16 + csz])
        self.outer = data
        self.at, self.size = struct.unpack_from("<II", data, 8)
        self.txp = bytearray(data[self.at:self.at + self.size])
        if self.txp[:4] != b"TXP2":
            raise ValueError("no TXP2 in this package")

    def u32(self, o):
        return struct.unpack_from(">I", self.txp, o)[0]

    def textures(self):
        return [struct.unpack_from(">III", self.txp, self.u32(0x1c) + 12 * i) for i in range(self.u32(0x18))]

    def txdt(self, i):
        _, _, off = self.textures()[i]
        raw, packed = struct.unpack_from(">II", self.txp, off)
        body = self.txp[off + 8:off + 8 + (packed or raw)]
        return bytes(body[:raw]) if packed == 0 else nlz(bytes(body), raw)

    def image(self, i):
        from PIL import Image
        t = self.txdt(i)
        w, h = struct.unpack_from(">HH", t, 0x10)
        if t[0x17] != 0x15:
            raise ValueError("texture %d is format 0x%x, only 32-bit ARGB (0x15) is read" % (i, t[0x17]))
        return Image.frombytes("RGBA", (w, h), t[0x40:0x40 + w * h * 4], "raw", "ARGB")

    def pictures(self):
        """[(name, index, (texture, x0, y0, x1, y1))] in NAMP order"""
        table, namp = self.u32(0x28), self.u32(0x2c)
        n, off = self.u32(namp + 0x10), self.u32(namp + 0x18)
        out = []
        for k in range(n):
            h, idx, so = struct.unpack_from(">III", self.txp, off + 12 * k)
            out.append((cstr(self.txp, so), idx, struct.unpack_from(">5H", self.txp, table + 10 * idx)))
        return out

    def add_pictures(self, items, tex=0, cell=None):
        """add [(name, RGBA image)] to texture `tex`, each in a cell of its own below the pictures
        already there (the atlas grows downwards; nothing already in the package moves).  `cell`
        is the side of a cell in pixels -- by default the size of the first picture."""
        from PIL import Image
        have = {nm for nm, _, _ in self.pictures()}
        clash = [nm for nm, _ in items if nm in have]
        if clash:
            raise ValueError("already in the package: %s" % ", ".join(clash))
        atlas = self.image(tex)
        pics = self.pictures()
        if cell is None:
            r = min(pics, key=lambda p: p[1])[2]
            cell = (r[3] + 1) // 2 - r[1] // 2
        cols = max(1, atlas.width // cell)
        rows = -(-len(items) // cols)
        top = atlas.height
        big = Image.new("RGBA", (atlas.width, top + rows * cell), (255, 255, 255, 0))
        big.paste(atlas, (0, 0))
        count, table = self.u32(0x24), self.u32(0x28)
        rects = bytes(self.txp[table:table + 10 * count])
        entries = [(h, idx, so) for (h, idx, so) in
                   (struct.unpack_from(">III", self.txp, self.u32(self.u32(0x2c) + 0x18) + 12 * k)
                    for k in range(self.u32(self.u32(0x2c) + 0x10)))]
        names = b""
        for k, (nm, im) in enumerate(items):
            x, y = (k % cols) * cell, top + (k // cols) * cell
            big.paste(im.convert("RGBA").resize((cell, cell)) if im.size != (cell, cell) else im.convert("RGBA"), (x, y))
            rects += struct.pack(">5H", tex, 2 * x + 1, 2 * y + 1, 2 * (x + cell) - 1, 2 * (y + cell) - 1)
            entries.append((namehash(nm), count + k, len(names)))   # name offset fixed up below
            names += nm.encode("latin1") + b"\0"
        # The game copies only the first meta_size() bytes of the TXP2 into the buffer where it
        # turns offsets into addresses (0x141f93a40); a table or NAMP past that end is read
        # from outside it (measured 2026-09-28: blank list, then a crash at 0x141f932d0).  So
        # the new names, picture table and NAMP go in at the end of that part, and everything
        # after it moves down.
        at_meta, meta = self.meta_field(), self.meta_size()
        ins = bytearray()
        names_at = meta
        ins += names
        ins = align(ins, 4)
        table_at = meta + len(ins)
        ins += rects
        ins = align(ins, 4)
        namp_at = meta + len(ins)
        fixed = []
        for h, idx, so in entries:
            fixed.append((h, idx, so + names_at if idx >= count else so))
        fixed.sort()
        n = len(fixed)
        a, b = namp_params(n)
        old_namp = self.u32(0x2c)
        ins += bytes(self.txp[old_namp:old_namp + 0x10]) + struct.pack(">IHHI", n, a, b, namp_at + 0x1c)
        for e in fixed:
            ins += struct.pack(">III", *e)
        ins = align(ins, 16)
        shift = len(ins)
        # header offsets at or past the end of that part (the texture blocks, the data after
        # the metadata) move with it; the part's own size grows by what went in
        for o in range(0x18, 0x6c, 4):
            if o != at_meta and self.u32(o) >= meta and o not in (0x18, 0x24):
                struct.pack_into(">I", self.txp, o, self.u32(o) + shift)
        struct.pack_into(">I", self.txp, at_meta, meta + shift)
        tl = self.u32(0x1c)
        for i in range(self.u32(0x18)):
            if self.u32(tl + 12 * i + 8) >= meta:
                struct.pack_into(">I", self.txp, tl + 12 * i + 8, self.u32(tl + 12 * i + 8) + shift)
        self.txp[meta:meta] = ins
        # the blocks named by flags 15-17 carry an offset of their own at +8 (the loader adds
        # the base to it, 0x141f93d00 and 0x141f93140): the one after the metadata moved
        for o in self.fields(15, 16, 17):
            ptr = self.u32(o)
            if ptr and self.u32(ptr + 8) >= meta:
                struct.pack_into(">I", self.txp, ptr + 8, self.u32(ptr + 8) + shift)
        struct.pack_into(">III", self.txp, 0x24, count + len(items), table_at, namp_at)
        # the grown atlas, stored as it is, at the end; the old block goes if it was the last
        t = bytearray(self.txdt(tex)[:0x40])
        _, oldsize, oldat = self.textures()[tex]
        if oldat + oldsize >= len(self.txp) - 16:
            del self.txp[oldat:]
        struct.pack_into(">HH", t, 0x10, big.width, big.height)
        r, g, b_, a_ = big.split()
        px = Image.merge("RGBA", (a_, r, g, b_)).tobytes()          # ARGB byte order
        struct.pack_into(">I", t, 0x0c, 0x40 + len(px))
        block = struct.pack(">II", 0x40 + len(px), 0) + bytes(t) + px
        self.txp = align(self.txp, 16)
        block_at = len(self.txp)
        self.txp += block
        struct.pack_into(">II", self.txp, tl + 12 * tex + 4, len(block), block_at)
        return cell

    # the header's fields after +0x18: each is there only when its bit of the flags word at
    # +0x14 is set, in this order and of this size (0x141f9cf70 swaps them, 0x141f93e60 finds
    # the metadata size among them)
    FIELDS = ((0, 8), (1, 4), (3, 8), (4, 4), (6, 8), (7, 4), (8, 8), (9, 4), (10, 4),
              (11, 8), (12, 4), (13, 8), (14, 4), (15, 4), (16, 4), (17, 4))

    def fields(self, *bits):
        """header offsets of the fields for these flag bits that the package has"""
        f, o, out = self.u32(0x14), 0x18, []
        for bit, n in self.FIELDS:
            if f >> bit & 1:
                if bit in bits:
                    out.append(o)
                o += n
        return out

    def meta_field(self):
        """where the header keeps the size of the part the game copies and fixes up"""
        o = self.fields(10)
        if not o:
            raise ValueError("this package has no metadata size field (flags 0x%x)" % self.u32(0x14))
        return o[0]

    def meta_size(self):
        return self.u32(self.meta_field())

    def pack(self):
        out = bytearray(self.outer[:self.at]) + self.txp
        struct.pack_into("<I", out, 12, len(self.txp))
        out = bytes(out)
        if self.wesys:
            c = zlib.compress(out, 9)
            out = self.prefix + WESYS + struct.pack("<II", len(c), len(out)) + c
        return out
