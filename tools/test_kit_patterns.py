"""python tools/test_kit_patterns.py

Every new club gets three kits (home, away, third) and a goalkeeper's, drawn in patterns of a
library of at least 100 (kitpatterns.py), in colours clearly apart, the same for the same club at
every Build and on every PC.  Needs Pillow.
"""
import json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kitmaker, kitpatterns as K
from PIL import Image, ImageChops

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


# a sample of clubs: NewLife-like shirts in words (some with an away kit), crest colours, and
# clubs with no colours at all (a numbered badge: colours picked by the name)
SAMPLE = [
    ("Dinamo Zagreb", "plain #1f4fbf #ffffff #ffffff", None),
    ("Hajduk Split", "plain #ffffff #103e7f #103e7f", "plain #103e7f #ffffff #ffffff"),
    ("Celtic", "hoops #ffffff #189163 #189163", None),
    ("Juventus", "stripes #ffffff #101010 #101010", "plain #ffc0cb #101010 #101010"),
    ("Liverpool", "plain #c8102e #c8102e #ffffff", "plain #ffffff #c8102e #c8102e"),
    ("Rijeka", "plain #ffffff #1f4fbf #1f4fbf", None),
    ("Osijek", "halves #1f4fbf #ffffff #ffffff", None),
    ("Arsenal", "sleeves #c8102e #ffffff #ffffff", None),
    ("Borussia", "plain #f5d000 #101010 #101010", None),
    ("Sampdoria", "band #1f4fbf #ffffff #c8102e", None),
    ("Grey FC", "plain #8a8f96 #8a8f96 #8a8f96", None),
    ("Green Town", "plain #1d8f3a #1d8f3a #1d8f3a", "plain #1d8f3a #ffffff #ffffff"),
] + [("Club %d" % i, None, None) for i in range(60)]


def kits_of(name, home, away):
    home = home or K.generated_home(name)
    return K.plan(home, away, name), home, away


def main():
    lib = K.LIBRARY
    ok("the library has at least 100 patterns (%d)" % len(lib), len(lib) >= 100)
    ok("every pattern has a name of its own", len({p.name for p in lib}) == len(lib))
    ok("every pattern has a description", all(p.desc for p in lib))
    ok("the seven names of before still read", all(kitmaker.words("%s #ffffff #101010" % n)
                                                     for n in ("plain", "stripes", "hoops", "halves",
                                                               "sleeves", "centre", "band")))
    ok("a pattern of the library reads as a shirt in words", kitmaker.words("sash-wide #ffffff #c8102e #101010")
       == "sash-wide #ffffff #c8102e #101010")
    ok("an unknown pattern does not", kitmaker.words("polkastripes #ffffff #101010") is None)

    # every pattern draws, and no two draw the same
    seen, blank = {}, []
    words = lambda p: "%s #1f4fbf #ffffff #c8102e" % p.name
    plain = K.render(words(K.get("plain")))
    for p in lib:
        im = K.render(words(p))
        assert im.size == (2048, 2048) and im.mode == "RGB", p.name
        if p.name != "plain" and not ImageChops.difference(im, plain).getbbox():
            blank.append(p.name)
        key = (K.panel_masks(p)[0].tobytes(), K.panel_masks(p)[1].tobytes(), p.sleeves, p.shorts, p.collar,
               p.cuffs)
        seen.setdefault(key, []).append(p.name)
    twins = [v for v in seen.values() if len(v) > 1]
    ok("every pattern draws a 2048 x 2048 kit", True)
    ok("no two patterns draw the same kit%s" % (": %s" % twins if twins else ""), not twins)
    ok("every pattern but plain shows something on the shirt%s" % (": %s" % blank if blank else ""), not blank)

    # the kits of the sample clubs
    plans = {}
    for name, home, away in SAMPLE:
        pl, h, a = kits_of(name, home, away)
        plans[name] = pl
        assert sorted(pl) == ["g1", "p1", "p2", "p3"], (name, pl)
        assert all(K.parse(w) for w in pl.values()), (name, pl)
    ok("every club gets home, away, third and goalkeeper kits (%d clubs)" % len(SAMPLE), True)

    bad = []
    for name, home, away in SAMPLE:
        pl = plans[name]
        given_away = away and K.parse(kitmaker.words(away) or "") and \
            K.parse(pl["p2"])[1:4] == K.parse(K.home_kit(kitmaker.words(away), name + "|away"))[1:4]
        pairs = [("p1", "p3"), ("p2", "p3"), ("p1", "g1"), ("p2", "g1"), ("p3", "g1")]
        if not given_away:
            pairs.append(("p1", "p2"))
        elif K.clash(pl["p1"], pl["p2"]):
            bad.append((name, "p1~p2 own away clashes"))
        for x, y in pairs:
            if not K.distinct(pl[x], pl[y]):
                bad.append((name, x, y, round(K.apart(pl[x], pl[y]), 1), round(K.shared(pl[x], pl[y]), 2)))
    ok("the three kits and the goalkeeper's are clearly apart in colour (CIEDE2000 >= %g)%s"
       % (K.DISTINCT, ": %s" % bad[:6] if bad else ""), not bad)
    ok("the goalkeeper is never in the pitch's green",
       all(K.de2000(K.parse(pl["g1"])[1], K.PITCH) >= K.DISTINCT for pl in plans.values()))

    # a club's own colours stay
    pl = plans["Celtic"]
    ok("a home shirt with a pattern of its own keeps it", pl["p1"] == "hoops-105 #ffffff #189163 #189163")
    p1 = K.parse(plans["Dinamo Zagreb"]["p1"])
    ok("a plain home shirt keeps its colours, in a quiet pattern of the library",
       p1[0].quiet and K.hexc(p1[1]) == "#1f4fbf" and K.hexc(p1[2]) == "#ffffff")
    a = K.parse(plans["Hajduk Split"]["p2"])
    ok("a club's own away colours are kept", K.hexc(a[1]) == "#103e7f")
    dark = K.parse(plans["Dinamo Zagreb"]["p2"])[1]
    light = K.parse(plans["Borussia"]["p2"])[1]
    ok("no away kit of its own: a light one for a dark home shirt, a dark one for a light one",
       K.lightness(dark) >= 62 and K.lightness(light) <= 45)

    # the same club, the same kits: in this run, and in another Python with other hash seeds
    again = {name: kits_of(name, h, a)[0] for name, h, a in SAMPLE}
    ok("the same kits for the same club every time", again == plans)
    code = ("import sys, json; sys.path.insert(0, %r); import kitpatterns as K, test_kit_patterns as T; "
            "print(json.dumps({n: T.kits_of(n, h, a)[0] for n, h, a in T.SAMPLE}))" % HERE)
    env = dict(os.environ, PYTHONHASHSEED="12345")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, cwd=HERE)
    ok("... and in another run of Python (another PC)", out.returncode == 0 and json.loads(out.stdout) == plans)

    # clubs of the same colours do not all look the same
    homes = {K.parse(pl["p1"])[0].name for n, pl in plans.items() if n.startswith("Club ")}
    thirds = {K.parse(pl["p3"])[0].name for pl in plans.values()}
    used = {K.parse(w)[0].name for pl in plans.values() for w in pl.values()}
    ok("clubs with no colours of their own get many patterns (%d home patterns of 60 clubs)" % len(homes),
       len(homes) >= 15)
    ok("the third kits are many patterns (%d of %d clubs)" % (len(thirds), len(plans)), len(thirds) >= 30)
    ok("%d patterns of the library worn by %d clubs" % (len(used), len(plans)), len(used) >= 60)
    same = [K.plan("plain #c8102e #ffffff #ffffff", None, "Red %d" % i)["p3"] for i in range(10)]
    ok("ten clubs in the same red and white get thirds of their own (%d)" % len(set(same)), len(set(same)) >= 8)

    # club_third_kits: a third kit of the recipe's own is worn as it is, the rest as before
    base = K.plan("plain #c8102e #ffffff #ffffff", None, "Third test")
    own3 = "hoops-105 #14285a #f5d000 #f5d000"
    mine = K.plan("plain #c8102e #ffffff #ffffff", None, "Third test", own3)
    ok("a recipe's own third kit is the third, home and away unchanged",
       mine["p3"] == own3 and mine["p1"] == base["p1"] and mine["p2"] == base["p2"])
    ok("the goalkeeper stays apart from the recipe's third", K.distinct(mine["g1"], own3))
    ok("no third given: the plan is the same as before", K.plan("plain #c8102e #ffffff #ffffff", None, "Third test", None) == base)

    # B360 (09.11.): the third kit in the home kit's colours, never an away kit's own colour
    pe = K.plan("plain #18397b #cd1018 #18397b", "plain #08f610 #08f610 #08f610", "Penya Encarnada d'Andorra")
    n3 = K._norm(pe["p3"])
    ok("B360: Penya Encarnada's third is red and blue, no lime (%s)" % pe["p3"],
       n3[1] == "#cd1018" and n3[2] == "#18397b" and "#08f610" not in pe["p3"])
    for home, away, seed in (("plain #1f4fbf #ffffff #1f4fbf", "plain #ffffff #1f4fbf #ffffff", "Blue White"),
                             ("plain #f5d000 #101010 #f5d000", "plain #101010 #f5d000 #101010", "Yellow Black"),
                             ("plain #0f5a32 #ffffff #0f5a32", "plain #f28cb1 #f28cb1 #f28cb1", "Green Pink")):
        p = K.plan(home, away, seed)
        n3, h = K._norm(p["p3"]), K._norm(home)
        ok("B360: %s's third: its second colour a home one, apart from both kits (%s)" % (seed, p["p3"]),
           n3[2] in h[1:4] and "#f28cb1" not in p["p3"] and K.distinct(p["p3"], p["p1"]) and K.distinct(p["p3"], p["p2"]))

    # the kit pictures
    tmp = tempfile.mkdtemp(prefix="fl26kitpat")
    try:
        got = kitmaker.pictures(os.path.join(tmp, "k"), "plain #1f4fbf #ffffff #ffffff", None, None, seed="Dinamo Zagreb")
        ok("kitmaker draws p1, p2, p3 and g1", sorted(got) == ["g1", "p1", "p2", "p3"]
           and all(Image.open(f).size == (2048, 2048) for f in got.values()))
        front = (1024, 1600)
        cols = [Image.open(got[v]).convert("RGB").getpixel(front) for v in ("p1", "p2", "p3", "g1")]
        ok("the four kits are four colours on the front of the shirt: %s" % [K.hexc(c) for c in cols],
           all(K.de2000(cols[i], cols[j]) >= 10 for i in range(4) for j in range(i + 1, 4)))
        got2 = kitmaker.pictures(os.path.join(tmp, "k2"), "plain #1f4fbf #ffffff #ffffff", None, None, seed="Dinamo Zagreb")
        ok("drawn again: the same pictures", all(open(got[v], "rb").read() == open(got2[v], "rb").read() for v in got))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("test_kit_patterns: %d ok" % N)


if __name__ == "__main__":
    main()
