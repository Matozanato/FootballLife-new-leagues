r"""python tools/futve_cinematics.py [--make] [--game <folder>]
       python tools/futve_cinematics.py --check

The cinematics of the league play-offs' finals. The game's own modules
`SiderAddons\modules\common\cinematics.lua` (the entrance folder per tournament id) and
`cinematicsB.lua` (the Final stadium scenes) are copied to `out/futve/cinematics` with this mapping:

  - 261 (Final del Apertura) and 262 (Final del Clausura), when the match is the final
    (`ctx.match_info == 53`), take the UEFA Europa League final's entrance (`entry = 16`,
    "UEFA Europa League F") -- they join the Europa League branch of the module;
  - 263 (Final del FUTVE), when the match is the final, takes the UEFA Champions League final's
    entrance (`entry = 16`, "UEFA Champions League F") -- it joins the Champions League branch;
  - all three take the generic Final stadium scene (`Final\st001`) from cinematicsB.

The two files are otherwise untouched. The copies are what `futve_test.py` installs for an in-game
test; the sandbox backs up the game's originals and puts them back at the end. The sandbox runs this
tool by itself before a test; after changing the mapping, run it (or the test) again.

  python tools/futve_cinematics.py --make --game "G:\Games\SP Football Life 2026"
  python tools/futve_cinematics.py --check
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(REPO, "out", "futve", "cinematics")
MODULES = ("SiderAddons", "modules", "common")

OLD_UCL = (b"\tif tid == 2 or tid == 1026 or tid == 2050 or tid == 3074 or tid == 4098 or "
           b"tid == 5122 or tid == 6146 or tid == 7170 or tid == 8194 then")
OLD_UEL = (b"\telseif tid == 5 or tid == 1029 or tid == 2053 or tid == 3077 or tid == 4101 or "
           b"tid == 5125 or tid == 6149 or tid == 7173 or tid == 8197 or tid == 9221 or "
           b"tid == 10245 or tid == 11269 or tid == 12293 or tid == 6 then")
NEW_UCL = OLD_UCL[:-5] + b" or tid == 263 then"
NEW_UEL = OLD_UEL[:-5] + b" or tid == 261 or tid == 262 then"
OLD_B = b"if ctx.match_info == 53 then\r\n\t   if ctx.stadium == 1 then"
NEW_B = (b"if ctx.match_info == 53 then\r\n"
         b"\t   -- Liga FUTVE: the final competitions of fl26swiss (their one match is the final)\r\n"
         b"\t   if ctx.tournament_id == 261 or ctx.tournament_id == 262 or ctx.tournament_id == 263 then\r\n"
         b"\t      Entrance_fix = \"Final\\\\st001\"\r\n"
         b"\t   elseif ctx.stadium == 1 then")
PATCHES = {
    "cinematics.lua": ((OLD_UCL, NEW_UCL), (OLD_UEL, NEW_UEL)),
    "cinematicsB.lua": ((OLD_B, NEW_B),),
}


def make(game, out=OUT):
    os.makedirs(out, exist_ok=True)
    for name, pairs in PATCHES.items():
        p = os.path.join(game, *MODULES, name)
        if not os.path.isfile(p):
            raise SystemExit("no %s in %s" % (name, os.path.dirname(p)))
        data = open(p, "rb").read()
        for old, new in pairs:
            if data.count(new) == 1:
                continue
            if data.count(old) != 1:
                raise SystemExit("%s: the line to patch was not found once" % name)
            data = data.replace(old, new, 1)
        open(os.path.join(out, name), "wb").write(data)
        print("  %s -> %s" % (p, os.path.join(out, name)))


def check(out=OUT):
    bad = 0
    for name, pairs in PATCHES.items():
        p = os.path.join(out, name)
        if not os.path.isfile(p):
            print("  falta %s (run --make)" % p)
            bad += 1
            continue
        data = open(p, "rb").read()
        for old, new in pairs:
            if data.count(new) != 1 or data.count(old):
                print("  %s: the play-off finals' mapping is missing or half-applied" % p)
                bad += 1
                break
        else:
            print("  %s: ok" % p)
    return bad == 0


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
