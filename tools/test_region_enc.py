"""python tools/test_region_enc.py [<folder with the game's tables>]

Regions 0..127 (sider/experimental/fl26reg128.lua).

Always, no game data needed:
  * mkleague.enc_region / dec_region round-trip every id 0..127, and the encoding is the one the
    module's parser reads: bits 3..7 = region bits 0..4, bit 0 = bit 5, bit 1 = bit 6;
  * every id below 64 encodes exactly as it did before (fl26reg64: bit 1 always clear), and
    every id below 32 is rid * 8, as the stock game wrote it;
  * every byte a world can hold decodes to what the module's parser computes from the dword
    (the 18 bytes at 0x1414f8390, emulated here);
  * 128 and -1 are refused.

With a base folder ($FL26_PESDB, or the argument): the league builder's region allocation for
a recipe with more new countries than fit below 64 -- every league gets a region of its own,
63 included, the ones past 63 go on from 64, and the Competition.bin +3 byte that
mkleague.add_league writes for one of them decodes back to its region. The whole world is
not built (that is regress018's job); the plan and the competition row are.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mkleague as M

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def parser128(dword):
    """the parser at 0x1414f8390 as fl26reg128 rewrites it, on the row's first dword:
    mov ecx,[rax]; mov eax,ecx; shr ecx,27; shr eax,19; and eax,0x60; or ecx,eax"""
    ecx = (dword >> 27) & 0x1f
    eax = (dword >> 19) & 0x60
    return ecx | eax


def parser64(dword):
    """fl26reg64's parser: the same with and eax,0x20"""
    return ((dword >> 27) & 0x1f) | ((dword >> 19) & 0x20)


def encoding():
    seen = set()
    for r in range(128):
        b = M.enc_region(r)
        ok_rt = M.dec_region(b) == r and 0 <= b <= 255 and not (b & 4)
        if not ok_rt:
            ok("region %d round-trips (byte 0x%02x -> %d)" % (r, b, M.dec_region(b)), False)
        seen.add(b)
    ok("enc/dec round-trip for every region 0..127, bit 2 never set", True)
    ok("128 regions, 128 different bytes", len(seen) == 128)
    ok("regions 0..31 are rid * 8 (the stock encoding)", all(M.enc_region(r) == r * 8 for r in range(32)))
    ok("regions 0..63 encode as fl26reg64 did (bit 1 clear)",
       all(M.enc_region(r) == (((r & 0x1f) << 3) | ((r >> 5) & 1)) for r in range(64)))
    for r in range(128):
        d0 = M.enc_region(r) << 24 | 0x00abcdef & 0x00ffffff    # the low three bytes are other fields
        if parser128(d0) != r:
            ok("the module's parser reads region %d from its byte" % r, False)
        if r < 64 and parser64(d0) != r:
            ok("fl26reg64's parser reads region %d as before" % r, False)
    ok("the module's parser reads every region 0..127 back from the dword", True)
    ok("a byte with bit 1 clear reads the same under fl26reg64 and fl26reg128",
       all(parser64(b << 24) == parser128(b << 24) for b in range(256) if not b & 2))
    ok("every byte decodes as the module's parser does",
       all(M.dec_region(b) == parser128(b << 24) for b in range(256)))
    for bad in (128, -1, 255):
        try:
            M.enc_region(bad)
            ok("region %d refused" % bad, False)
        except ValueError:
            pass
    ok("128, 255 and -1 refused", True)
    ok("127 is the top", M.REGION_MAX == 127)


def allocation(base):
    import leaguebuilder as B
    names = [n for n, _ in B.country_ids(base)]
    taken = {"England", "France", "Italy", "Spain", "Portugal", "Netherlands", "Belgium",
             "Russia", "Switzerland", "Denmark", "Scotland", "Turkey", "Greece", "Argentina",
             "Brazil", "Chile", "Colombia", "China", "Japan", "Saudi Arabia", "United States",
             "USA", "Mexico", "Thailand", "Poland"}
    countries = [n for n in names if n not in taken][:45]
    recipe = {"world": "_TestReg128",
              "leagues": [{"name": "Reg128 League %02d" % i, "country": c, "clubs": 10, "legs": 2}
                          for i, c in enumerate(countries)]}
    try:
        pl = B.plan(recipe, base)
    except B.BuildError as e:
        ok("plan of %d new countries: %s" % (len(countries), e), False)
        return
    regs = [p["region"] for p in pl["leagues"]]
    ok("%d leagues, %d regions, each its own" % (len(regs), len(set(regs))), len(set(regs)) == len(regs))
    ok("region 63 handed out like any other", 63 in regs)
    high = sorted(r for r in regs if r >= 64)
    ok("leagues past 63 go on from 64 (%s)" % high[:6], high and high[0] == 64)
    ok("every region within 29..127 (%d..%d)" % (min(regs), max(regs)),
       all(29 <= r <= 127 or r in (11, 13, 14, 20) for r in regs))
    # the competition row mkleague.add_league writes for the highest one
    comp = bytearray(M.COMP)
    r = max(regs)
    comp[M.REGION_OFF] = M.enc_region(r)
    ok("Competition.bin +3 for region %d is 0x%02x and decodes back" % (r, comp[M.REGION_OFF]),
       M.dec_region(comp[M.REGION_OFF]) == r and parser128(int.from_bytes(comp[0:4], "little")) == r)


def main():
    encoding()
    base = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("FL26_PESDB")
    if base and os.path.exists(os.path.join(base, "Competition.bin")):
        allocation(base)
    else:
        print("# no base tables given -- the builder's allocation is not checked")
    print("all %d passed" % N)


if __name__ == "__main__":
    main()
