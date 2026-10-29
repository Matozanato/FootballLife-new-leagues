r"""python tools/futve_join.py [--make] [--game <folder>]
       python tools/futve_join.py --check

The join module's season builder and the Liga FUTVE finals. The game's own
`SiderAddons\modules\fl26joindll.lua` hands the season builder the calendar-year cups it finds in
the world's `league` lines (their `cup=`/`scup=` ids above 175). The finals of this world are
competition ids **142** (Final del Apertura), **143** (Final del Clausura) and **144** (Final del
FUTVE): below 175 and not a league's cup, so the loop leaves them out. The season builder's compiled
case table over 2..175 has no case for them, their season tables stay empty, and the season/standings
walk at `0x141333485` reads a null on the fourth Apertura matchday (the FL_2026.exe c0000005 of
29.10, 07:19/07:24).

This copies the module with the three ids added to `BUILDER_EXTRA`/`BUILDER_CONF` (CONMEBOL runtime
code) just before `idbuf`, so the join adds them to the season builder at creation like the
calendar-year cups. The copies are what `futve_test.py` installs for a test; the sandbox backs up the
game's module and puts it back at the end.

  python tools/futve_join.py --make --game "G:\Games\SP Football Life 2026"
  python tools/futve_join.py --check
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(REPO, "out", "futve", "join")
MODULE = ("SiderAddons", "modules", "fl26joindll.lua")
ANCHOR = b'  idbuf = ffi.new("uint16_t[?]", #IDS)'
BLOCK = (
    b"  -- 0.2.5 (Liga FUTVE finals): 142, 143 and 144 are cups the world adds, but they are below 175\n"
    b"  -- and are not a league's cup=, so the calendar-year loop above leaves them out. The season\n"
    b"  -- builder's compiled case table over 2..175 has no case for them, their season tables stay\n"
    b"  -- empty, and the season/standings walk at 0x141333485 reads a null on the fourth Apertura\n"
    b"  -- matchday. Hand them to the builder like the calendar-year cups (CONMEBOL runtime code).\n"
    b"  for _, fid in ipairs({ 142, 143, 144 }) do\n"
    b"    local dup = false\n"
    b"    for _, v in ipairs(BUILDER_EXTRA) do if v == fid then dup = true end end\n"
    b"    if not dup then BUILDER_EXTRA[#BUILDER_EXTRA + 1] = fid end\n"
    b"    BUILDER_CONF[#BUILDER_CONF + 1] = { fid, RUNTIME_CONF[4] }\n"
    b"  end\n"
)


def make(game, out=OUT):
    os.makedirs(out, exist_ok=True)
    src = os.path.join(game, *MODULE)
    if not os.path.isfile(src):
        raise SystemExit("no %s" % src)
    data = open(src, "rb").read()
    if BLOCK in data:
        print("  %s already has the finals in the builder list" % src)
        body = data
    else:
        if data.count(ANCHOR) != 1:
            raise SystemExit("%s: the idbuf line was not found once" % src)
        body = data.replace(ANCHOR, BLOCK + ANCHOR, 1)
    dest = os.path.join(out, "fl26joindll.lua")
    open(dest, "wb").write(body)
    print("  %s -> %s" % (src, dest))


def check(out=OUT):
    p = os.path.join(out, "fl26joindll.lua")
    if not os.path.isfile(p):
        print("  falta %s (run --make)" % p)
        return False
    data = open(p, "rb").read()
    if BLOCK not in data:
        print("  %s: the finals are not in the builder list" % p)
        return False
    print("  %s: ok" % p)
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game", default=os.environ.get("FL26_DIR"))
    ap.add_argument("--make", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        return 0 if check() else 1
    if not a.game:
        raise SystemExit("pass --game (or set FL26_DIR)")
    make(a.game)
    return 0


if __name__ == "__main__":
    sys.exit(main())
