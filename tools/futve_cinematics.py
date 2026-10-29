r"""python tools/futve_cinematics.py [--make] [--game <folder>]
       python tools/futve_cinematics.py --check

The cinematics of the league play-offs' finals. The game's own modules
`SiderAddons\modules\common\cinematics.lua` (entrance folder per tournament id) and
`cinematicsB.lua` (the Final stadium scenes) are copied to `out/futve/cinematics` with one mapping
added: the final competitions' regulations -- 261 (the Apertura final), 262 (the Clausura final) and
263 (the Final del FUTVE) -- get the Copa América final's entrance (`entry = 42`, `"CopaAmerica F"`)
when the match is the final (`ctx.match_info == 53`), and the generic Final stadium scene
(`Final\st001`) from cinematicsB. The two files are otherwise untouched.

The copies are what `futve_test.py` installs for an in-game test; the sandbox backs up the game's
originals and puts them back at the end. The sandbox runs this tool by itself when the copies are
missing; after changing the mapping, run it (or the test) again.

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

OLD_A = (b"\telseif tid == 43 or tid == 104 or tid == 1128 or tid == 2152 or tid == 3176 then")
NEW_A = (b"\t-- Liga FUTVE: the finals are competitions of their own (fl26swiss); their one match is\r\n"
         b"\t-- the final, and it takes the Copa America final's entrance and trophy entry (42).\r\n"
         b"\telseif (tid == 261 or tid == 262 or tid == 263) and ctx.match_info == 53 then\r\n"
         b"\t\tentry = 42\r\n"
         b"\t\tEntrance = \"CopaAmerica F\"\r\n"
         + OLD_A)
OLD_B = b"if ctx.match_info == 53 then\r\n\t   if ctx.stadium == 1 then"
NEW_B = (b"if ctx.match_info == 53 then\r\n"
         b"\t   -- Liga FUTVE: the final competitions of fl26swiss (their one match is the final)\r\n"
         b"\t   if ctx.tournament_id == 261 or ctx.tournament_id == 262 or ctx.tournament_id == 263 then\r\n"
         b"\t      Entrance_fix = \"Final\\\\st001\"\r\n"
         b"\t   elseif ctx.stadium == 1 then")
FILES = {"cinematics.lua": (OLD_A, NEW_A), "cinematicsB.lua": (OLD_B, NEW_B)}


def make(game, out=OUT):
    os.makedirs(out, exist_ok=True)
    for name, (old, new) in FILES.items():
        p = os.path.join(game, *MODULES, name)
        if not os.path.isfile(p):
            raise SystemExit("no %s in %s" % (name, os.path.dirname(p)))
        data = open(p, "rb").read()
        if data.count(new) == 1:
            print("  %s: already has the play-off finals' mapping" % name)
            body = data
        else:
            if data.count(old) != 1:
                raise SystemExit("%s: the branch to patch was not found once" % name)
            body = data.replace(old, new, 1)
        open(os.path.join(out, name), "wb").write(body)
        print("  %s -> %s" % (p, os.path.join(out, name)))


def check(out=OUT):
    bad = 0
    for name, (_old, new) in FILES.items():
        p = os.path.join(out, name)
        if not os.path.isfile(p):
            print("  falta %s (run --make)" % p)
            bad += 1
            continue
        data = open(p, "rb").read()
        if data.count(new) != 1:
            print("  %s: the play-off finals' mapping is missing" % p)
            bad += 1
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
