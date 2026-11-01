"""The crests of the Team List rows (tools/mkteamcrest.py): the layout it writes from the game's
teamSelectSingle.bin.

    python tools/test_mkteamcrest.py [<teamSelectSingle.bin> | <game folder>]

The layout is the game's (Konami's), so it is not in the repository: it comes from the argument,
FL26_DIR or the game folder this PC has (fl26world.base_dir), read the way Build reads it (the
sider roots, then the CPKs). Without one the test says so and passes. The cases:
  - the row sprite gets flTeamEmblem: a uirEmblemCompe instance (character 3) at depth 2, 38 px at
    (11, 2), the last tag of frame 0; the row's own three cells and the other frames as they were
    (each later frame starts one tag on);
  - every swap of the byte-swap list is still in the movie, the container's length is right;
  - our own layout is never taken as a base (has_crest) and is not changed again;
  - a layout this does not know (another mod's: a row cell at another depth; or another layout
    altogether) is left as it is: nothing written;
  - a world without a layout of its own gets one at switch on, and the next switch on leaves it.
Checked in FL27 1.00 on 2026-11-01 (the same bytes): the clubs of every league row with their
crests, the Squad List with the game's badges, after a restart too. FL26 2.2's layout is the
same file.
"""
import os, struct, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mkmpcol as M
import mkteamcrest as T

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
    return src.find(T.PACKAGE, lambda p: not T.has_crest(p)), src


def movie_of(data):
    """the AP2 movie of a layout (M.rebuild checks the container on the way)"""
    got = []
    M.rebuild(data, got.append)
    m = got[0]
    expect(all(p + n <= len(m.D) for p, n in m.swaps), "every swap inside the movie (%d swaps)" % len(m.swaps))
    return m


def row(m):
    _, sub = m.sprite(T.ROW)
    return m.tags_of(sub), [(v & 0xfffff, v >> 20) for _, v in m.frames(sub)]


def main():
    base, src = game_layout(sys.argv[1] if len(sys.argv) > 1 else None)
    try:
        if not base:
            print("no game layout (%s) on this PC: nothing to check" % T.PACKAGE)
            return 0
        print("base %s" % base)
        data = open(base, "rb").read()
        out = T.make(data)
        g, m = movie_of(data), movie_of(out)

        print("\nThe row")
        gtags, gframes = row(g)
        tags, frames = row(m)
        expect(len(tags) == len(gtags) + 1, "one tag more in the row sprite")
        expect(frames == [(0, gframes[0][1] + 1)] + [(s + 1, n) for s, n in gframes[1:]],
               "frame 0 has it, the later frames start one tag on (%r)" % frames)
        p = tags[gframes[0][1]][0]
        inf = m.place_info(p)
        expect(inf.get('name') == T.NEW and inf['depth'] == T.DEPTH,
               "%s at depth %d, the last tag of frame 0" % (T.NEW, T.DEPTH))
        expect(struct.unpack_from('<H', m.D, p + 12)[0] == 3 and T.class_table(m)[3] == "uirEmblemCompe",
               "an instance of character 3, uirEmblemCompe")
        expect(struct.unpack_from('<ii', m.D, inf['tx']) == (T.TX * 20, T.TY * 20),
               "at (%d, %d), the badge's place" % (T.TX, T.TY))
        expect(struct.unpack_from('<HH', m.D, p + 24) == (T.SCALE, T.SCALE), "38 px")
        same = all(m.D[a[0]:a[0] + 4 + a[2]] == g.D[b[0]:b[0] + 4 + b[2]]
                   for a, b in zip(tags[:gframes[0][1]], gtags[:gframes[0][1]]))
        later = all(m.D[a[0]:a[0] + 4 + a[2]] == g.D[b[0]:b[0] + 4 + b[2]]
                    for a, b in zip(tags[gframes[0][1] + 1:], gtags[gframes[0][1]:]))
        expect(same and later, "the row's other tags byte for byte the game's")
        depths = [m.place_info(q)['depth'] for q, tid, _ in tags[:gframes[0][1] + 1] if tid == 0x7f]
        expect(depths == [1, 3, 5, T.DEPTH] and max(depths) < 6, "depths 1, 3, 5 and 2: inside the row's 6")

        print("\nOurs and others'")
        tmp = tempfile.mkdtemp(prefix="fl26crest")
        ours = os.path.join(tmp, "ours.bin")
        open(ours, "wb").write(out)
        expect(T.has_crest(ours) and not T.has_crest(base), "has_crest tells ours from the game's")
        again = os.path.join(tmp, "again.bin")
        T.main(["--base", ours, "--out", again])
        expect(not os.path.exists(again), "ours is not changed again")

        def moved(mm):                     # the name a depth on: another mod's row
            q = row(mm)[0][1][0]
            struct.pack_into('<H', mm.D, q + 8, 4)
        other = os.path.join(tmp, "other.bin")
        open(other, "wb").write(M.rebuild(data, moved))
        out2 = os.path.join(tmp, "other-out.bin")
        T.main(["--base", other, "--out", out2])
        expect(not os.path.exists(out2), "another mod's layout (a row cell elsewhere) is left as it is")
        if src:
            rank = src.find(M.PACKAGE, lambda q: not M.has_mp(q))
            out3 = os.path.join(tmp, "rank-out.bin")
            if rank:
                T.main(["--base", rank, "--out", out3])
            expect(rank and not os.path.exists(out3), "another layout (rankingTeam.bin) is left as it is")

        game = src and src.game
        if game:
            print("\nA world built before the crests (no layout of its own), switched on")
            import leaguebuilder
            world = os.path.join(tmp, "oldworld")
            os.makedirs(world)
            lines = []
            leaguebuilder.crest_for_world(world, game, lines.append)
            made = os.path.join(world, *T.PACKAGE.split("/"))
            expect(os.path.isfile(made) and T.has_crest(made) and open(made, "rb").read() == out,
                   "the layout with crests made in the world (%s)" % "; ".join(lines))
            before = open(made, "rb").read()
            lines2 = []
            leaguebuilder.crest_for_world(world, game, lines2.append)
            expect(open(made, "rb").read() == before and not lines2, "the next switch on leaves it as it is")
    finally:
        if src:
            src.close()
    print(fails and "\n%d check(s) FAILED" % fails or "\nall checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
