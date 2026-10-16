"""python tools/test_pool_nibble_edits.py

B65: a club of the game that the recipe's edits rename into another (edits.clubs, NewLife's
replaced places) or swap into a league (edits.swaps) keeps its Team.bin record, and so its "Other
..." nibble (T_POOL). From a place the tables file in Otros latinoamericanos (6) the club showed
up in its league and in the Others list too. Synthetic tables, no game:

  - leaguebuilder.clear_league_pools clears the nibble of every club with a league place -- the
    renamed one, the swapped one, one the tables ship so -- and leaves a club in a pre-season
    tournament only, or in no competition, as it is;
  - buildcheck check 4 FAILs on the renamed club with a nibble (its id and league are the
    base's), stays INFO on the base's own club there as shipped, and PASSes once cleared.
"""
import contextlib, io, os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import leaguebuilder as B
import buildcheck
import mkleague as M
import mkworld as W
import pesdb

N = 0
LEAGUE_A, LEAGUE_B, FRIENDLY = 20, 21, 50          # competition ids
CLUBS = {   # id: (name, nibble, [competition ids])
    1001: ("Atletico Tucuman", 0, [LEAGUE_A, FRIENDLY]),
    1002: ("Godoy Cruz", 6, [LEAGUE_A]),           # filed in Otros latinoamericanos, renamed
    1003: ("Libertad", 6, [LEAGUE_A]),             # the tables ship it so: in the league and Otros
    1004: ("Banfield", 0, [LEAGUE_B, FRIENDLY]),
    1005: ("Cerro Porteno", 6, [FRIENDLY]),        # a pre-season tournament only: stays in Otros
    1006: ("Olimpia", 6, []),                      # in no competition: stays in Otros
    1007: ("Huracan", 7, [LEAGUE_A]),              # swapped with Banfield into League B
}


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def nibble(raw, tid):
    for o in range(0, len(raw), W.T_REC):
        if int.from_bytes(raw[o + W.T_ID:o + W.T_ID + 4], "little") == tid:
            return raw[o + B.T_POOL] >> 4
    raise KeyError(tid)


def tables():
    raw = bytearray()
    for tid, (name, nib, _c) in sorted(CLUBS.items()):
        r = bytearray(W.T_REC)
        r[W.T_ID:W.T_ID + 4] = tid.to_bytes(4, "little")
        M.put(r, W.T_NAME, name, W.T_NAME_LEN)
        r[B.T_POOL] = (nib << 4) | 0x05             # the low half is something else: kept
        raw += r
    ents = bytearray()
    for tid, (_n, _nib, cids) in sorted(CLUBS.items()):
        for c in cids:
            e = bytearray(M.ENT)
            e[M.E_TEAM:M.E_TEAM + 4] = tid.to_bytes(4, "little")
            e[M.E_CID] = c
            ents += e
    regs = bytearray()
    for rid, c in ((101, LEAGUE_A), (102, LEAGUE_B), (106, FRIENDLY)):
        g = bytearray(M.REG)
        g[M.R_ID:M.R_ID + 2] = rid.to_bytes(2, "little")
        g[M.R_CID] = c
        g[M.R_TYPE] = 4
        regs += g
    return raw, regs, ents


def write(d, raw, regs, ents):
    os.makedirs(d)
    for n, b in (("Team.bin", raw), ("CompetitionRegulation.bin", regs),
                 ("CompetitionEntry.bin", ents), ("Competition.bin", b"")):
        open(os.path.join(d, n), "wb").write(pesdb.wesys_pack(bytes(b)))


def check(world, base):
    out = io.StringIO()
    argv = sys.argv
    sys.argv = ["buildcheck.py", world, "--base", base]
    try:
        with contextlib.redirect_stdout(out):
            rc = buildcheck.main()
    finally:
        sys.argv = argv
    return rc, [ln for ln in out.getvalue().splitlines() if "check 4" in ln or ln.startswith("     club")]


def main():
    tmp = tempfile.mkdtemp()
    try:
        raw, regs, ents = tables()
        base = os.path.join(tmp, "base")
        write(base, raw, regs, ents)

        # the build's steps on the game's tables: the edits rename 1002, the swap trades 1004/1007
        raw, ents = bytearray(raw), bytearray(ents)
        B.apply_edits({"clubs": {"1002": {"name": "Estudiantes de Rio Cuarto", "abbr": "ERC"}}},
                      raw, regs, log=lambda *a: None)
        B.exchange_entries(ents, 1004, 1007)
        ok("the renamed club keeps its nibble before the fix's step", nibble(raw, 1002) == 6)

        before = os.path.join(tmp, "before")
        write(before, raw, regs, ents)
        rc, lines = check(before, base)
        print("\n".join("   # " + ln for ln in lines))
        ok("buildcheck fails on the uncleared world", rc == 1)
        ok("check 4 names the renamed club", any("club 1002:" in ln and "renamed" in ln for ln in lines))
        ok("check 4 names the club swapped in", any("club 1007:" in ln for ln in lines))
        ok("check 4 leaves the base's own club as shipped to INFO",
           not any("club 1003:" in ln for ln in lines if not ln.startswith("INFO"))
           and any(ln.startswith("INFO check 4") and "1003" in ln for ln in lines))
        ok("check 4 leaves the pre-season tournament and the club in no competition",
           not any("club 1005" in ln or "club 1006" in ln for ln in lines))

        # the build's step: the world's leagues as build() counts them, the friendlies left out
        gl = B.game_leagues(base)
        cids = {c for _r, c, _n, _t in gl} - B.friendly_cids(gl)
        ok("the pre-season tournament is no league", cids == {LEAGUE_A, LEAGUE_B})
        cleared = B.clear_league_pools(raw, ents, cids)
        ok("cleared the renamed, the swapped and the shipped club, each once",
           sorted(cleared) == [1002, 1003, 1007])
        ok("every club with a league place has nibble 0",
           all(nibble(raw, t) == 0 for t in (1001, 1002, 1003, 1004, 1007)))
        ok("the friendly-only and the no-competition club stay in Otros",
           nibble(raw, 1005) == 6 and nibble(raw, 1006) == 6)
        ok("the low half of the byte is kept",
           all(raw[o + B.T_POOL] & 0x0f == 0x05 for o in range(0, len(raw), W.T_REC)))
        ok("a second pass clears nothing", B.clear_league_pools(raw, ents, cids) == [])

        after = os.path.join(tmp, "after")
        write(after, raw, regs, ents)
        rc, lines = check(after, base)
        ok("buildcheck passes once cleared", rc == 0 and any(ln.startswith("PASS check 4") for ln in lines))

        # the base itself checked against itself: what it ships is no failure
        rc, lines = check(base, base)
        ok("the shipped base passes check 4", rc == 0)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("all %d ok" % N)


if __name__ == "__main__":
    main()
