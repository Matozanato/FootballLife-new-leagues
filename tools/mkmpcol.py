r"""mkmpcol.py -- a "matches played" column (MP) in the game's standings tables.

The standings screen (a league's table, the League Phase of the UEFA cups) is the layout
common/menu/general/rankingTeam.bin: Teams, Points, W, D, L, F, A, GD. The game keeps each club's
matches played in its table row (byte 0x0f) but no cell shows it. This writes a copy of the layout
into the world with an MP column between Points and W (A stays); fl26swiss.dll fills it (mp_fill:
the number in num_MatchesPlayed, "MP" in the top row's title_MatchesPlayed). Without this layout
the DLL finds no such cell and the table stays the game's.

    python mkmpcol.py --root <world livecpk root> --game <game folder> [--base <layout>]
    python mkmpcol.py --base <layout> --out <file>

  --root   the world's livecpk root: the layout is written there
  --game   where the game's layout comes from: the sider.ini roots other than the world, in their
           order, then the game's CPKs (mkcatflags.Source)
  --base   this layout instead
  --out    write here instead of the root

What changes, in the AP2 (Flash-like) movie inside the layout's TXP2 container:
  - the row sprite (choice_*, sprite 16) gets num_MatchesPlayed, a copy of num_Points, and the
    seven number columns move closer together to make room (in place, no size change);
  - the header (listHeader, sprite 15) gets nothing: a new cell there is never found by the game
    (its finder knows only the cells the layout's AS3 names), so each row also gets
    title_MatchesPlayed 44 px above its number -- just over the row, in the header line for the
    top one -- and the DLL writes "MP" into the top row's only, in title_Points' colour;
  - the names go to the end of the AP2's string table, the byte-swap list is made again, and the
    AP2 grows in place: the container's tables after it move along (appending the AP2 at the end
    of the container and repointing it left the screen empty in the game).
Each new cell goes after the last of its frame's tags, the header cell before num_MatchesPlayed:
placed after it, it was never found (2026-10-21). The layout is checked against the one this was
made for (sprites, cells, x positions) first; another one is left as it is.
"""
import os, struct, sys, zlib

PACKAGE = "common/menu/general/rankingTeam.bin"
NEW_NUM, NEW_HEAD = "num_MatchesPlayed", "title_MatchesPlayed"
COLS = ["Points", "Wins", "Draw", "Losses", "Goals", "GoalsConceded", "GoalsDifference"]
# the number columns' x (px) in frame 0 (a row on screen) and frame 3 (upDownDisp_off): the game's
# own seven, then ours -- eight in the room of seven, MP second
XS_GAME_ON = [650, 791, 932, 1073, 1214, 1355, 1496]
XS_ON = [650, 772, 894, 1016, 1138, 1260, 1382, 1504]
XS_OFF = [614, 738, 862, 986, 1110, 1234, 1358, 1482]
# the new cell has no __setProp of its own (alignment), so its text sits left in the cell where the
# others are centred: 44 px to the right puts the number halfway between Points and W (Pts 805,
# MP 882, W 1047 measured at 1920 wide, 2026-10-21)
MP_DX = 44
# the header cell: 44 px over the row's numbers (the header's titles sit 45 px over the first
# row's) and 13 px left of the number (measured: "MP" centred over it, as Points and W are)
HEAD_DX, HEAD_DY = -13, -44
ROW_SPRITE, HEAD_SPRITE = 16, 15

# TXP2 header: feature bit -> bytes of its entry
TXP2_ORDER = [(0x1, 8), (0x2, 4), (0x8, 8), (0x10, 4), (0x40, 8), (0x80, 4), (0x100, 8),
              (0x200, 4), (0x400, 4), (0x800, 8), (0x1000, 4), (0x2000, 8), (0x4000, 4),
              (0x8000, 4), (0x10000, 4), (0x20000, 4)]
SWL = {1: 2, 2: 4, 3: 8}


class Unknown(Exception):
    """not the layout this was made for"""


def decode_swaps(di):
    """the container's byte-swap list -> [(offset, bytes)]"""
    out, pos = [], 0
    for i in range(0, len(di), 2):
        w = struct.unpack_from('<H', di, i)[0]
        if w == 0:
            break
        pos += (w & 0x7f) * 2
        typ, loops = (w >> 13) & 7, (w >> 7) & 0x3f
        if typ == 0:
            pos += 256 * loops
            continue
        for _ in range(loops + 1):
            out.append((pos, SWL[typ]))
            pos += SWL[typ]
    return out


def encode_swaps(sw):
    words, pos, i = [], 0, 0
    rev = {2: 1, 4: 2, 8: 3}
    while i < len(sw):
        p, n = sw[i]
        j = i
        while j + 1 < len(sw) and j + 1 - i < 64 and sw[j + 1] == (sw[j][0] + n, n):
            j += 1
        gap = p - pos
        assert gap >= 0 and gap % 2 == 0, (p, pos)
        while gap > 254:
            loops = min(63, gap // 256)
            if loops == 0:
                words.append(127)
                gap -= 254
                continue
            words.append(loops << 7)
            gap -= 256 * loops
        words.append((rev[n] << 13) | ((j - i) << 7) | (gap // 2))
        pos = p + n * (j - i + 1)
        i = j + 1
    words.append(0)
    return b''.join(struct.pack('<H', w) for w in words)


def apply_swaps(data, sw):
    d = bytearray(data)
    for p, n in sw:
        d[p:p + n] = d[p:p + n][::-1]
    return d


class Movie:
    """the AP2 movie, unscrambled (D), with its swap list kept in step"""

    def __init__(self, swf, swaps):
        self.swaps = list(swaps)
        self.D = apply_swaps(swf, swaps)
        if struct.unpack_from('<I', self.D, 4)[0] != len(self.D):
            raise Unknown("AP2 length")
        self.str_off, self.str_size = struct.unpack_from('<II', self.D, 48)
        if self.str_off + self.str_size != len(self.D):
            raise Unknown("the string table does not end the AP2")

    # -- strings (scrambled: byte + 128 + its offset)
    def string_at(self, o):
        s, i = bytearray(), 0
        while True:
            c = (self.D[self.str_off + o + i] - 128 - (o + i)) & 0xff
            if c == 0:
                return s.decode('utf-8', 'replace')
            s.append(c)
            i += 1

    def find_string(self, name):
        i = 0
        while i < self.str_size:
            s = self.string_at(i)
            if s == name and i:
                return i
            i += len(s.encode()) + 1
        return None

    def add_string(self, name):
        o = self.str_size
        b = name.encode() + b'\0'
        self.D += bytes(((c + 128 + o + k) & 0xff) for k, c in enumerate(b))
        self.str_size += len(b)
        return o

    def name_offset(self, name):
        o = self.find_string(name)
        return self.add_string(name) if o is None else o

    # -- tags
    def tags_of(self, sub):
        """[(offset of tag word, tag id, size)] of the tag list whose header is at sub"""
        fl, nl, nf, nt, lo, fo, to = struct.unpack_from('<HHIIIII', self.D, sub)
        p, out = sub + to, []
        for _ in range(nt):
            w = struct.unpack_from('<I', self.D, p)[0]
            out.append((p, w >> 22, w & 0x3fffff))
            p += (((w & 0x3fffff) + 3) & ~3) + 4
        return out

    def sprite(self, sid):
        for p, tid, size in self.tags_of(struct.unpack_from('<I', self.D, 36)[0]):
            if tid == 0x79:
                fl, i = struct.unpack_from('<HH', self.D, p + 4)
                if i == sid:
                    return p, p + 4 + struct.unpack_from('<I', self.D, p + 8)[0]
        raise Unknown("no sprite %d" % sid)

    def frames(self, sub):
        nf, fo = struct.unpack_from('<I', self.D, sub + 4)[0], struct.unpack_from('<I', self.D, sub + 16)[0]
        return [(sub + fo + 4 * i, struct.unpack_from('<I', self.D, sub + fo + 4 * i)[0]) for i in range(nf)]

    def place_info(self, p):
        """PLACE_OBJECT at tag word p -> flags, depth, name, offsets of the a/d and tx/ty fields"""
        D = self.D
        flags, depth = struct.unpack_from('<IH', D, p + 4)
        q = p + 12
        info = {'flags': flags, 'depth': depth}
        if flags & 0x80000000:
            q += 4
        if flags & 2:
            q += 2
        if flags & 0x10:
            q += 2
        if flags & 0x20:
            info['name_field'] = q
            info['name'] = self.string_at(struct.unpack_from('<H', D, q)[0])
            q += 2
        if flags & 0x40:
            q += 2
        if flags & 0x20000:
            q += 1
        q = (((q - (p + 4)) + 3) & ~3) + p + 4
        if flags & 0x100:
            info['a'] = q
            q += 8
        if flags & 0x200:
            q += 8
        if flags & 0x400:
            info['tx'] = q
            q += 8
        info['end'] = q
        return info

    def insert(self, pos, blob, rel_swaps):
        assert len(blob) % 4 == 0
        self.D[pos:pos] = blob
        self.str_off += len(blob)
        moved = [(p + len(blob) if p >= pos else p, n) for p, n in self.swaps]
        self.swaps = sorted(moved + [(pos + p, n) for p, n in rel_swaps])

    def tag(self, p):
        w = struct.unpack_from('<I', self.D, p)[0]
        size = w & 0x3fffff
        return w, size, bytearray(self.D[p:p + 4 + ((size + 3) & ~3)])

    def swaps_in(self, p, n):
        return [(q - p, k) for q, k in self.swaps if p <= q < p + n]

    def cells(self, sid, names):
        """{name: (create tag, info)} in frame 0 and {name: (update tag, info)} in frame 3 of
        sprite sid (its 5 frames: on, ..., upDownDisp_off), the update found by the depth"""
        tw, sub = self.sprite(sid)
        tl, fr = self.tags_of(sub), self.frames(sub)
        if len(fr) != 5:
            raise Unknown("sprite %d has %d frames" % (sid, len(fr)))
        f0s, f0n = fr[0][1] & 0xfffff, fr[0][1] >> 20
        f3s, f3n = fr[3][1] & 0xfffff, fr[3][1] >> 20
        create, by_depth, update = {}, {}, {}
        for k in range(f0s, f0s + f0n):
            if tl[k][1] == 0x7f:
                inf = self.place_info(tl[k][0])
                if inf.get('name') in names:
                    create[inf['name']] = (tl[k][0], inf)
                    by_depth[inf['depth']] = inf['name']
        for k in range(f3s, f3s + f3n):
            if tl[k][1] == 0x7f:
                inf = self.place_info(tl[k][0])
                if inf['depth'] in by_depth:
                    update[by_depth[inf['depth']]] = (tl[k][0], inf)
        missing = [n for n in names if n not in create or n not in update]
        if missing:
            raise Unknown("sprite %d has no %s" % (sid, ", ".join(missing)))
        used = {self.place_info(p)['depth'] for p, tid, _ in tl if tid == 0x7f}
        return tw, sub, tl, fr, create, update, used

    def add_cell(self, sid, create_tag, update_tag, rel_c, rel_u):
        """one more cell in sprite sid: its create tag after frame 0's last, its update tag after
        frame 3's last; the frame table, the tag count and the sprite's size follow"""
        tw, sub = self.sprite(sid)
        tl, fr = self.tags_of(sub), self.frames(sub)
        f0s, f0n = fr[0][1] & 0xfffff, fr[0][1] >> 20
        f3s, f3n = fr[3][1] & 0xfffff, fr[3][1] >> 20
        e3, e0 = tl[f3s + f3n - 1], tl[f0s + f0n - 1]
        pos3 = e3[0] + ((e3[2] + 3) & ~3) + 4
        pos0 = e0[0] + ((e0[2] + 3) & ~3) + 4
        assert pos0 < pos3
        self.insert(pos3, bytes(update_tag), rel_u)            # the later one first
        self.insert(pos0, bytes(create_tag), rel_c)
        nt = struct.unpack_from('<I', self.D, sub + 8)[0]
        struct.pack_into('<I', self.D, sub + 8, nt + 2)
        for k, (fp, v) in enumerate(fr):
            s, n = v & 0xfffff, v >> 20
            if k == 0:
                n += 1
            elif k == 3:
                s, n = s + 1, n + 1
            else:
                s += 1 if k < 3 else 2
            struct.pack_into('<I', self.D, fp, s | (n << 20))
        w = struct.unpack_from('<I', self.D, tw)[0]
        struct.pack_into('<I', self.D, tw, (w & ~0x3fffff) | ((w & 0x3fffff) + len(create_tag) + len(update_tag)))

    def finish(self):
        """pad the string table to 4, fix the header; -> (scrambled AP2, swap list)"""
        while len(self.D) % 4:
            self.D += bytes([(128 + self.str_size) & 0xff])
            self.str_size += 1
        struct.pack_into('<I', self.D, 4, len(self.D))
        struct.pack_into('<II', self.D, 48, self.str_off, self.str_size)
        di = encode_swaps(self.swaps)
        assert decode_swaps(di) == self.swaps
        return bytes(apply_swaps(self.D, self.swaps)), di


def header_cell(m, x_on, x_off, depth):
    """title_MatchesPlayed: a copy of the row's num_Points, HEAD_DY over it, white through the
    colour fields the game's layouts use (0x2000 multiply ff000000 and 0x4000 add 00ffffff, one
    u32 each; the DLL gives it title_Points' FontColor as well, which is what draws it white)"""
    names = ['num_Points']
    tw, sub, tl, fr, create, update, used = m.cells(ROW_SPRITE, names)
    if depth in used:
        raise Unknown("depth %d is taken in the row" % depth)
    name = m.name_offset(NEW_HEAD)

    def make(p, inf, x, named):
        w, size, t = m.tag(p)
        flags = struct.unpack_from('<I', t, 4)[0]
        if flags & 0x80007800 or 'tx' not in inf or 'a' not in inf or inf['end'] != p + 4 + size:
            raise Unknown("num_Points' tag is not a plain one")
        sw = m.swaps_in(p, 4 + size)
        struct.pack_into('<I', t, 4, flags | 0x6000)
        struct.pack_into('<H', t, 8, depth)
        if named:
            struct.pack_into('<H', t, inf['name_field'] - p, name)
        struct.pack_into('<ii', t, inf['a'] - p, 1024, 1024)            # no 1.05 zoom: a header
        struct.pack_into('<i', t, inf['tx'] - p, int(round(x * 20)))
        ty = struct.unpack_from('<i', m.D, inf['tx'] + 4)[0]
        struct.pack_into('<i', t, inf['tx'] - p + 4, ty + HEAD_DY * 20)
        t += bytes([0xff, 0, 0, 0, 0, 0xff, 0xff, 0xff])
        struct.pack_into('<I', t, 0, (w & ~0x3fffff) | (size + 8))
        return t, sw + [(4 + size, 4), (8 + size, 4)]

    c, sc = make(*create['num_Points'], x_on, True)
    u, su = make(*update['num_Points'], x_off, False)
    m.add_cell(ROW_SPRITE, c, u, sc, su)


def columns(m, sid, prefix, add):
    """move sprite sid's seven number columns to XS_* and, with add, put num_MatchesPlayed after
    Points (a copy of its cell, at the next depth)"""
    names = [prefix + c for c in COLS]
    order = names[:]
    order.insert(1, prefix + "MatchesPlayed")
    tw, sub, tl, fr, create, update, used = m.cells(sid, names)
    for nm in names:
        i = order.index(nm)
        p, inf = create[nm]
        struct.pack_into('<i', m.D, inf['a'], 1024)
        struct.pack_into('<i', m.D, inf['tx'], int(round(XS_ON[i] * 20)))
        p, inf = update[nm]
        struct.pack_into('<i', m.D, inf['a'], int(round(1.05 * 1024)))
        struct.pack_into('<i', m.D, inf['tx'], int(round(XS_OFF[i] * 20)))
    if not add:
        return
    tp, tinf = create[prefix + "Points"]
    up, uinf = update[prefix + "Points"]
    depth = tinf['depth'] + 1
    if depth in used:
        raise Unknown("depth %d is taken in sprite %d" % (depth, sid))
    name = m.name_offset(NEW_NUM)
    _, size_c, c = m.tag(tp)
    _, size_u, u = m.tag(up)
    sc, su = m.swaps_in(tp, len(c)), m.swaps_in(up, len(u))
    struct.pack_into('<H', c, 8, depth)
    struct.pack_into('<H', c, tinf['name_field'] - tp, name)
    struct.pack_into('<i', c, tinf['tx'] - tp, int(round(XS_ON[1] * 20)))
    struct.pack_into('<H', u, 8, depth)
    struct.pack_into('<i', u, uinf['tx'] - up, int(round(XS_OFF[1] * 20)))
    m.add_cell(sid, c, u, sc, su)


def check(m):
    """the layout this was made for: the seven columns of the rows at the game's x, nothing of ours"""
    if m.find_string(NEW_NUM) is not None or m.find_string(NEW_HEAD) is not None:
        raise Unknown("it has an MP column already")
    _, _, _, _, create, _, _ = m.cells(ROW_SPRITE, ["num_" + c for c in COLS])
    xs = [int(round(struct.unpack_from('<i', m.D, create["num_" + c][1]['tx'])[0] / 20)) for c in COLS]
    if xs != XS_GAME_ON:
        raise Unknown("its columns stand at %s, not %s" % (xs, XS_GAME_ON))
    m.cells(HEAD_SPRITE, ["title_" + c for c in COLS])


def make(data):
    """the layout's bytes (WESYS or raw) -> the layout with the MP column (WESYS)"""
    raw = zlib.decompress(data[16:]) if data[3:8] == b'WESYS' else data
    pk_off, pk_len = struct.unpack_from('<II', raw, 8)
    T = bytearray(raw[pk_off:pk_off + pk_len])
    if T[:4] != b'TXP2' or struct.unpack_from('>I', T, 12)[0] != len(T):
        raise Unknown("no TXP2 container")
    feat = struct.unpack_from('>I', T, 20)[0]
    ho, sec = 24, {}
    for bit, n in TXP2_ORDER:
        if feat & bit:
            sec[bit] = ho
            ho += n
    if 0x800 not in sec or 0x20000 not in sec:
        raise Unknown("the container has no movie or no swap list")
    cnt, ent = struct.unpack_from('>II', T, sec[0x800])
    if cnt != 1:
        raise Unknown("%d movies" % cnt)
    _, swf_len, swf_off = struct.unpack_from('>III', T, ent)
    hdr_tab = struct.unpack_from('>I', T, sec[0x20000])[0]
    zero, di_len, di_off = struct.unpack_from('>III', T, hdr_tab)
    if zero or not swf_off + swf_len <= di_off <= len(T):
        raise Unknown("the swap list is not after the movie")
    swaps = decode_swaps(T[di_off:di_off + di_len])
    if decode_swaps(encode_swaps(swaps)) != swaps:
        raise Unknown("a swap list this cannot write back")
    m = Movie(bytes(T[swf_off:swf_off + swf_len]), swaps)
    check(m)
    # the header cell first (see the module's doc), then the column, then the header's titles
    header_cell(m, XS_ON[1] + MP_DX + HEAD_DX, XS_OFF[1] + MP_DX + HEAD_DX, 16)
    XS_ON[1] += MP_DX
    XS_OFF[1] += MP_DX
    try:
        columns(m, ROW_SPRITE, "num_", True)
        columns(m, HEAD_SPRITE, "title_", False)
    finally:
        XS_ON[1] -= MP_DX
        XS_OFF[1] -= MP_DX
    S2, DI2 = m.finish()

    # the container: the movie grows in place, everything after it moves by delta (a multiple of
    # 16, so their alignment holds), and every big-endian word of the header and of those tables
    # that points at or past the movie's old end moves with them
    old_end = swf_off + swf_len
    S2p = bytearray(S2)
    while len(S2p) % 16 != swf_len % 16:
        S2p += b'\0'
    delta = len(S2p) - swf_len

    def shift(buf, base):
        for p in range(0, len(buf) - 3, 4):
            if base + p == 12:
                continue
            v = struct.unpack_from('>I', buf, p)[0]
            if old_end <= v <= len(T):
                struct.pack_into('>I', buf, p, v + delta)

    H = bytearray(T[:swf_off])
    shift(H, 0)
    tail = bytearray(T[old_end:di_off])
    shift(tail, old_end)
    struct.pack_into('>III', H, ent, struct.unpack_from('>I', H, ent)[0], len(S2), swf_off)
    T2 = H + S2p + tail + DI2
    while len(T2) % 4:
        T2 += b'\0'
    struct.pack_into('>III', T2, hdr_tab + delta, 0, len(DI2), di_off + delta)
    struct.pack_into('>I', T2, 12, len(T2))

    out = bytearray(raw[:pk_off])
    struct.pack_into('<I', out, 12, len(T2))
    out += T2
    while len(out) % 16:
        out += b'\0'
    z = zlib.compress(bytes(out), 9)
    return b'\x00\x01\x01WESYS' + struct.pack('<II', len(z), len(out)) + z


def has_mp(path):
    """a layout this wrote (its strings are scrambled, so it is read, not searched)"""
    try:
        make(open(path, "rb").read())
    except Unknown as e:
        return "MP column already" in str(e)
    except (OSError, zlib.error, struct.error, IndexError):
        return False
    return False


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    get = lambda k, d=None: argv[argv.index(k) + 1] if k in argv else d
    root, game, base, out = get("--root"), get("--game"), get("--base"), get("--out")
    if not (root and game) and not (base and out):
        raise SystemExit(__doc__)
    src = None
    try:
        if not base:
            import mkcatflags
            src = mkcatflags.Source(game, root)
            # never a layout of ours (another world's, or this one installed elsewhere) as the base
            base = src.find(PACKAGE, lambda p: not has_mp(p))
            if not base:
                raise SystemExit("no %s in the sider roots or the game's CPKs" % PACKAGE)
        try:
            data = make(open(base, "rb").read())
        except Unknown as e:
            print("left as it is: %s is not the standings layout this knows (%s)" % (base, e))
            return 0
        out = out or os.path.join(root, *PACKAGE.split("/"))
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        open(out, "wb").write(data)
    finally:
        if src:
            src.close()
    print("wrote %s: the MP column, from %s" % (out, base))
    return 0


if __name__ == "__main__":
    sys.exit(main())
