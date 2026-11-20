"""python test_b489_playoff_names.py [<folder with the game's tables>] -- a play-off's name fits
the game's lists (B489).

Dolokhov's Hungarian world (FL 2027, 16.11.2026): Competition Info -> Select Competition drew his
play-offs as a crest with no name. Build named a play-off the recipe names not "<league> Relegation
Play-off" / "<league> Promotion Play-off" -- 42 to 60 characters for "Megyei I. Osztály ..." --
and the game's lists draw a name past leaguebuilder.LONGEST_NAME (38) blank (#101, B477). Now
promo_default_name keeps it to 38: the same name when it fits, else "Rel./Prom. Play-off", else
"Play-off", else the league's leading words go; never two the same. A recipe's own playoff_name
is kept, and Check the plan says when it is longer.

Without the tables only the naming runs; with them a plan of the Hungarian shape as well."""
import contextlib
import copy
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import leaguebuilder as B

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="backslashreplace")     # Hungarian letters on a cp1252 console
N = 0


def ok(name, cond):
    global N
    if not cond:
        raise SystemExit("FAIL " + name)
    N += 1
    print("ok  " + name)


def naming():
    f = B.promo_default_name
    ok("a name that fits stays as it was", f("EFL League One", "Promotion Play-off") == "EFL League One Promotion Play-off")
    ok("GigaPack's 37-character name stays (accented letters count once)",
       f("NB III Északnyugat", "Promotion Play-off") == "NB III Északnyugat Promotion Play-off")
    n = "x" * (B.LONGEST_NAME - len(" Relegation Play-off"))
    ok("exactly %d characters: unchanged" % B.LONGEST_NAME, f(n, "Relegation Play-off") == n + " Relegation Play-off")
    ok("39: the short word (%r)" % f(n + "y", "Relegation Play-off"), f(n + "y", "Relegation Play-off") == n + "y Rel. Play-off")
    ok("Ukrainian First League: Rel. (%r)" % f("Ukrainian First League", "Relegation Play-off"),
       f("Ukrainian First League", "Relegation Play-off") == "Ukrainian First League Rel. Play-off")
    ok("Megyei I. Osztály Pest: Rel. (%r)" % f("Megyei I. Osztály Pest", "Relegation Play-off"),
       f("Megyei I. Osztály Pest", "Relegation Play-off") == "Megyei I. Osztály Pest Rel. Play-off")
    ok("NB III Közép written out: plain Play-off (%r)" % f("Nemzeti Bajnokság III Közép", "Promotion Play-off"),
       f("Nemzeti Bajnokság III Közép", "Promotion Play-off") == "Nemzeti Bajnokság III Közép Play-off")
    g = f("Megyei I. Osztály Szabolcs-Szatmár-Bereg", "Relegation Play-off")
    ok("a 40-character league: its leading words go, the county stays (%r)" % g,
       g == "Szabolcs-Szatmár-Bereg Rel. Play-off")
    g = f("A" * 60, "Promotion Play-off")
    ok("one word longer than all: cut (%d characters)" % len(g), len(g) == B.LONGEST_NAME and g.endswith(" Play-off"))
    a = f("Megyei I. Osztály Győr-Moson-Sopron Észak", "Relegation Play-off")
    b = f("Megyei II. Osztály Győr-Moson-Sopron Észak", "Relegation Play-off", [a])
    ok("two that come out the same: the second gets 2 (%r, %r)" % (a, b), a != b and b.endswith(" 2") and len(b) <= 38)
    for lg in ("Megyei I. Osztály Jász-Nagykun-Szolnok", "Primera Federación Grupo 1", "Ab", "Liga 3 Serie A Norte e Nordeste"):
        for w in ("Relegation Play-off", "Promotion Play-off"):
            ok("%s %s: %d characters at most" % (lg, w, B.LONGEST_NAME), len(f(lg, w)) <= B.LONGEST_NAME)


def split_naming():
    """19.11.2026: the Apertura and Clausura playoffs (playoff_cups) are kept to 38 as well"""
    f = B.split_playoff_name
    ok("a split playoff that fits stays as it was", f("Liga MX", "Apertura") == "Liga MX Apertura Playoffs")
    for lg, want in (("Primera División de El Salvador", "El Salvador %s Playoffs"),
                     ("Liga Nacional de Guatemala", "Guatemala %s Playoffs"),
                     ("Liga Nacional de Honduras", "Honduras %s Playoffs"),
                     ("Liga Primera de Nicaragua", "Nicaragua %s Playoffs")):
        for tag in ("Apertura", "Clausura"):
            g = f(lg, tag)
            ok("%s %s -> %r (%d)" % (lg, tag, g, len(g)), g == want % tag and len(g) <= B.LONGEST_NAME)
    g = f("A" * 60, "Clausura")
    ok("one word longer than all: cut (%d characters)" % len(g), len(g) <= B.LONGEST_NAME and g.endswith(" Clausura Playoffs"))
    ok("Apertura and Clausura never the same", f("Liga Nacional de Guatemala", "Apertura") != f("Liga Nacional de Guatemala", "Clausura"))


def lg(name, clubs=16, **k):
    return dict({"name": name, "country": "Hungary", "clubs": clubs, "legs": 2}, **k)


def plan(base):
    r = {"world": "_FL26B489", "leagues": [
        lg("Nemzeti Bajnokság II", 20),
        lg("Nemzeti Bajnokság III Közép", above="Nemzeti Bajnokság II", exchange=1, playoff={"places": [1, 2]}),
        lg("Nemzeti Bajnokság III Kelet", above="Nemzeti Bajnokság II", exchange=1),
        lg("Megyei I. Osztály Szabolcs-Szatmár-Bereg", above="Nemzeti Bajnokság III Kelet", exchange=1, playoff={"tie": True}),
        lg("Megyei I. Osztály Pest", above="Nemzeti Bajnokság III Közép", exchange=1, playoff={"tie": True})]}
    with contextlib.redirect_stdout(io.StringIO()):
        pl = B.plan(copy.deepcopy(r), base)
    names = sorted(c["name"] for c in pl["home_cups"] if c["kind"] == "promo")
    ok("plan: three play-offs, every name %d characters at most (%s)" % (B.LONGEST_NAME, names),
       len(names) == 3 and all(len(n) <= B.LONGEST_NAME for n in names) and len(set(names)) == 3)
    ok("plan: the 22-character league keeps its name (%s)" % names, "Megyei I. Osztály Pest Rel. Play-off" in names)
    ok("Check the plan has no play-off NOTE when Build names them",
       "the play-off name" not in B.describe(pl))
    r["leagues"][4]["playoff_name"] = "Megyei I. Osztály Pest osztályozó mérkőzés"
    with contextlib.redirect_stdout(io.StringIO()):
        pl = B.plan(copy.deepcopy(r), base)
    names = [c["name"] for c in pl["home_cups"] if c["kind"] == "promo"]
    ok("plan: the recipe's own playoff_name is kept as it is", "Megyei I. Osztály Pest osztályozó mérkőzés" in names)
    ok("Check the plan says it is longer than %d" % B.LONGEST_NAME,
       "NOTE: the play-off name Megyei I. Osztály Pest osztályozó mérkőzés is 42 characters" in B.describe(pl))


def main():
    naming()
    split_naming()
    if len(sys.argv) < 2:
        print("skip - the plan (give the folder with the game's tables)")
        print("all passed (%d)" % N)
        return
    t = sys.argv[1]
    deep = os.path.join(t, "common", "etc", "pesdb")
    plan(B.base_dir(deep if os.path.isdir(deep) else t))
    print("all passed (%d)" % N)


if __name__ == "__main__":
    main()
