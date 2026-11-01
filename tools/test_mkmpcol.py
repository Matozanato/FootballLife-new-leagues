"""The MP column of the standings tables (tools/mkmpcol.py, 0.2.5): the layout it writes from the
game's rankingTeam.bin.

    python tools/test_mkmpcol.py [<rankingTeam.bin> | <game folder>]

The layout is the game's (Konami's), so it is not in the repository: it comes from the argument,
FL26_DIR or the game folder this PC has (fl26world.base_dir), read the way Build reads it (the
sider roots, then the CPKs). Without one the test says so and passes. The cases:
  - the layout comes out with num_MatchesPlayed between num_Points and num_Wins and the eight
    number columns at mkmpcol.XS_ON / XS_OFF, in frame 0 and frame 3 of the rows;
  - title_MatchesPlayed is a row cell too, before num_MatchesPlayed in frame 0 (placed after it,
    the game never found it), white through 0x2000/0x4000, HEAD_DY over the numbers;
  - the header's seven titles move with their columns, and the header gets no cell of its own;
  - every swap of the byte-swap list is still in the movie, the container's length is right;
  - our own layout is never taken as a base (has_mp) and is not changed again;
  - a layout whose columns stand elsewhere (another mod's) is left as it is: nothing written;
  - (0.3.0) the zone strip: flZone, a copy of num_Points at ZONE_DEPTH and (ZONE_X, ZONE_Y), the
    last tag of frame 0; every name we add starts on a multiple of 4 (has_zones tells it);
  - a world with the 0.2.5 layout (MP, no strip) gets the layout again at switch on, with both.
Checked in the game on 2026-10-21 (the same bytes): the League Phase of the Conference League
and the Belgian Challenger Pro League, MP = W + D + L, "MP" over its numbers.
The zone strip checked in FL26 2.2 on 2026-11-01: the HNL (1 blue, 2 teal, 10 red), the Druga NL
(1-2 green) and the Bosnian league, as tall as the row on its left edge.
"""
import os, struct, sys, tempfile, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mkmpcol as M

fails = 0


def expect(ok, what):
    global fails
    print("  %s  %s" % ("ok  " if ok else "FAIL", what))
    if not ok:
        fails += 1


def game_layout(arg):
    if arg and os.path.isfile(arg):
        return arg, None
    game = arg or os.environ.get("FL26_DIR")
    if not game:
        try:
            import fl26world
            game = fl26world.base_dir(None)
        except (SystemExit, Exception):
            game = None
    if not game or not os.path.isdir(game):
        return None, None
    import mkcatflags
    src = mkcatflags.Source(game, os.path.join(tempfile.gettempdir(), "no-world-root"))
    return src.find(M.PACKAGE, lambda p: not M.has_mp(p)), src


def unpacked(data):
    """a layout as the game reads it: FL26's CPKs pack it (WESYS + zlib), FL27's do not"""
    return zlib.decompress(data[16:]) if data[3:8] == b'WESYS' else data


def movie_of(data):
    """the AP2 movie of a layout, unscrambled"""
    raw = unpacked(data)
    pk_off, pk_len = struct.unpack_from('<II', raw, 8)
    T = raw[pk_off:pk_off + pk_len]
    assert struct.unpack_from('>I', T, 12)[0] == len(T), "container length"
    feat = struct.unpack_from('>I', T, 20)[0]
    ho, sec = 24, {}
    for bit, n in M.TXP2_ORDER:
        if feat & bit:
            sec[bit] = ho
            ho += n
    _, ent = struct.unpack_from('>II', T, sec[0x800])
    _, swf_len, swf_off = struct.unpack_from('>III', T, ent)
    hdr = struct.unpack_from('>I', T, sec[0x20000])[0]
    _, di_len, di_off = struct.unpack_from('>III', T, hdr)
    swaps = M.decode_swaps(T[di_off:di_off + di_len])
    expect(all(p + n <= swf_len for p, n in swaps), "every swap inside the movie (%d swaps)" % len(swaps))
    return M.Movie(T[swf_off:swf_off + swf_len], swaps)


def frame_cells(m, sid, k):
    """[(name or None, info)] of frame k of sprite sid, in tag order"""
    _, sub = m.sprite(sid)
    tl, fr = m.tags_of(sub), m.frames(sub)
    s, n = fr[k][1] & 0xfffff, fr[k][1] >> 20
    return [(m.place_info(tl[j][0]).get('name'), m.place_info(tl[j][0]), tl[j][0])
            for j in range(s, s + n) if tl[j][1] == 0x7f]


def x_of(m, inf):
    return int(round(struct.unpack_from('<i', m.D, inf['tx'])[0] / 20))


def depths_unique(cells):
    d = [inf['depth'] for _, inf, _ in cells]
    return len(d) == len(set(d))


def main():
    base, src = game_layout(sys.argv[1] if len(sys.argv) > 1 else None)
    try:
        if not base:
            print("no game layout (%s) on this PC: nothing to check" % M.PACKAGE)
            return 0
        print("base %s" % base)
        data = open(base, "rb").read()
        out = M.make(data)
        m = movie_of(out)

        print("\nThe rows")
        f0 = frame_cells(m, M.ROW_SPRITE, 0)
        names = [n for n, _, _ in f0]
        expect(M.NEW_NUM in names and M.NEW_HEAD in names, "num_MatchesPlayed and title_MatchesPlayed in the row")
        expect(names.index(M.NEW_HEAD) < names.index(M.NEW_NUM), "the header cell before the number in frame 0")
        order = ["num_Points", M.NEW_NUM] + ["num_" + c for c in M.COLS[1:]]
        by = dict((n, inf) for n, inf, _ in f0)
        expect([x_of(m, by[n]) for n in order] == [M.XS_ON[0], M.XS_ON[1] + M.MP_DX] + M.XS_ON[2:],
               "frame 0: the eight columns at XS_ON, MP %d px right" % M.MP_DX)
        depth = dict((inf['depth'], n) for n, inf, _ in f0)
        f3 = dict((depth.get(inf['depth']), inf) for _, inf, _ in frame_cells(m, M.ROW_SPRITE, 3))
        expect([x_of(m, f3[n]) for n in order] == [M.XS_OFF[0], M.XS_OFF[1] + M.MP_DX] + M.XS_OFF[2:],
               "frame 3: the eight columns at XS_OFF")
        h, num = by[M.NEW_HEAD], by[M.NEW_NUM]
        expect(h['flags'] & 0x6000 == 0x6000, "the header cell has the multiply and add colour")
        expect(x_of(m, h) == x_of(m, num) + M.HEAD_DX, "the header cell %d px from the number" % M.HEAD_DX)
        dy = (struct.unpack_from('<i', m.D, h['tx'] + 4)[0] - struct.unpack_from('<i', m.D, num['tx'] + 4)[0]) / 20
        expect(dy == M.HEAD_DY, "... and %d px over it" % M.HEAD_DY)
        col = struct.unpack_from('<II', m.D, h['end'])
        expect(m.D[h['end']:h['end'] + 8] == bytes([0xff, 0, 0, 0, 0, 0xff, 0xff, 0xff]),
               "... multiply ff000000, add 00ffffff (%08x %08x)" % col)

        print("\nThe zone strip")
        z = by.get(M.ZONE_CELL)
        expect(z is not None and names[-1] == M.ZONE_CELL, "flZone, the last cell of frame 0")
        if z:
            pts = by["num_Points"]
            expect(z['depth'] == M.ZONE_DEPTH and struct.unpack_from('<ii', m.D, z['tx']) == (M.ZONE_X * 20, M.ZONE_Y * 20),
                   "at depth %d, (%d, %d)" % (M.ZONE_DEPTH, M.ZONE_X, M.ZONE_Y))
            expect(z['flags'] == pts['flags'], "num_Points' kind of tag (a text cell the finder knows)")
        expect(all(m.find_string(n) % 4 == 0 for n in (M.NEW_NUM, M.NEW_HEAD, M.ZONE_CELL)),
               "our names start on 4 in the string table")
        expect(depths_unique(f0), "no two cells of frame 0 at one depth")

        print("\nThe header")
        hh = [(n, inf) for n, inf, _ in frame_cells(m, M.HEAD_SPRITE, 0)]
        hn = [n for n, _ in hh]
        expect(M.NEW_HEAD not in hn and M.NEW_NUM not in hn, "no cell of its own")
        hb = dict(hh)
        expect([x_of(m, hb["title_" + c]) for c in M.COLS] == [M.XS_ON[0]] + M.XS_ON[2:],
               "the seven titles over their columns")

        print("\nOurs and others'")
        tmp = tempfile.mkdtemp(prefix="fl26mp")
        ours = os.path.join(tmp, "ours.bin")
        open(ours, "wb").write(out)
        expect(M.has_mp(ours) and not M.has_mp(base), "has_mp tells ours from the game's")
        again = os.path.join(tmp, "again.bin")
        M.main(["--base", ours, "--out", again])
        expect(not os.path.exists(again), "ours is not changed again")
        # the game's layout with its Points column 2 px off: another mod's
        mm = movie_of(data)
        _, _, _, _, create, _, _ = mm.cells(M.ROW_SPRITE, ["num_Points"])
        p = create["num_Points"][1]['tx']
        struct.pack_into('<i', mm.D, p, struct.unpack_from('<i', mm.D, p)[0] + 40)
        raw = unpacked(data)
        pk_off, pk_len = struct.unpack_from('<II', raw, 8)
        T = bytearray(raw[pk_off:pk_off + pk_len])
        feat = struct.unpack_from('>I', T, 20)[0]
        ho, sec = 24, {}
        for bit, n in M.TXP2_ORDER:
            if feat & bit:
                sec[bit] = ho
                ho += n
        _, ent = struct.unpack_from('>II', T, sec[0x800])
        _, swf_len, swf_off = struct.unpack_from('>III', T, ent)
        T[swf_off:swf_off + swf_len] = M.apply_swaps(mm.D, mm.swaps)
        raw2 = bytearray(raw)
        raw2[pk_off:pk_off + pk_len] = T
        z = zlib.compress(bytes(raw2), 9)
        other = os.path.join(tmp, "other.bin")
        open(other, "wb").write(b'\x00\x01\x01WESYS' + struct.pack('<II', len(z), len(raw2)) + z)
        out2 = os.path.join(tmp, "other-out.bin")
        M.main(["--base", other, "--out", out2])
        expect(not os.path.exists(out2), "another mod's layout (columns elsewhere) is left as it is")

        game = src and src.game
        if game:
            print("\nA world built before 0.2.5 (no layout of its own), switched on")
            import leaguebuilder
            world = os.path.join(tmp, "oldworld")
            os.makedirs(world)
            lines = []
            leaguebuilder.mp_for_world(world, game, lines.append)
            made = os.path.join(world, *M.PACKAGE.split("/"))
            expect(os.path.isfile(made) and M.has_mp(made), "the layout with MP made in the world")
            before = open(made, "rb").read()
            lines2 = []
            leaguebuilder.mp_for_world(world, game, lines2.append)
            expect(open(made, "rb").read() == before and not lines2, "the next switch on leaves it as it is")

            print("\nA world built with 0.2.5 (MP, no zone strip), switched on")
            zc = M.zone_cells
            M.zone_cells = lambda mm: None
            try:
                old25 = M.make(data)
            finally:
                M.zone_cells = zc
            open(made, "wb").write(old25)
            expect(M.has_mp(made) and not M.has_zones(made), "the 0.2.5 layout: has_mp, not has_zones")
            lines3 = []
            leaguebuilder.mp_for_world(world, game, lines3.append)
            expect(M.has_zones(made) and open(made, "rb").read() == before,
                   "made again, with the strip (%s)" % "; ".join(lines3))
            om = os.path.join(tmp, "gameworld", *M.PACKAGE.split("/"))
            os.makedirs(os.path.dirname(om))
            open(om, "wb").write(data)
            leaguebuilder.mp_for_world(os.path.join(tmp, "gameworld"), game, lambda l: None)
            expect(open(om, "rb").read() == data, "a layout not ours (the game's own in the world) is left as it is")
    finally:
        if src:
            src.close()
    print(fails and "\n%d check(s) FAILED" % fails or "\nall checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
