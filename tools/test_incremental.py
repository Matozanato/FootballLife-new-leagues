"""python test_incremental.py <folder with the game's tables> -- a Build after an edit of pictures
alone (a league's logo, a club's crest) draws only those again (17.10., Vicentico: 20 minutes on
the Modpack to give one cup a new name and logo). The world it leaves must be the one a full Build
makes, file for file; anything else changed means a full Build. Worlds are built in temporary game
folders (nothing is switched on)."""
import hashlib, json, os, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B
from PIL import Image

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def png(path, colour):
    Image.new("RGBA", (200, 200), colour).save(path)
    return path


def game_folder():
    g = tempfile.mkdtemp(prefix="fl26-incr-")
    for d in ("livecpk", "modules", "content"):
        os.makedirs(os.path.join(g, "SiderAddons", d))
    with open(os.path.join(g, "SiderAddons", "sider.ini"), "w") as f:
        f.write("[sider]\n")
    return g


def recipe(pics, names=("", "", "", "", "", "", "", "", "", "")):
    return {"world": "_FL26IncrTest", "players": {}, "edits": {"leagues": {}, "clubs": {}},
            "leagues": [{"name": "Incr Albania", "country": "Albania", "clubs": 10, "legs": 2,
                         "logo": pics["logo"], "club_names": list(names),
                         "club_crests": [pics["c0"], pics["c1"]] + [None] * 8},
                        {"name": "Incr Andorra", "country": "Andorra", "clubs": 10, "legs": 2}]}


def world(game):
    return os.path.join(game, "SiderAddons", "livecpk", "_FL26IncrTest")


def build(base, game, r, full=False):
    """Build r into game (again, when the world is there); full: as if the last Build left no
    record of its input"""
    w = world(game)
    prev = None
    if os.path.exists(w):
        with open(os.path.join(w, "leaguebuilder-plan.json"), encoding="utf-8") as f:
            prev = json.load(f)
        if full and os.path.exists(os.path.join(w, B.INPUT)):
            os.remove(os.path.join(w, B.INPUT))
    said = []
    B.build(B.plan(r, base, prev), base, game, os.path.exists(w), log=said.append)
    return "\n".join(str(s) for s in said)


def files(game):
    w, out = world(game), {}
    for d, _ds, fs in os.walk(w):
        for f in fs:
            p = os.path.join(d, f)
            with open(p, "rb") as fh:
                out[os.path.relpath(p, w).replace(os.sep, "/")] = hashlib.sha1(fh.read()).hexdigest()
    return out


def differ(a, b):
    return sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))


def main(base):
    pics_dir = tempfile.mkdtemp(prefix="fl26-incr-pics-")
    fast, slow = game_folder(), game_folder()
    try:
        p = {"logo": png(os.path.join(pics_dir, "logo1.png"), (200, 0, 0, 255)),
             "c0": png(os.path.join(pics_dir, "c0.png"), (0, 120, 0, 255)),
             "c1": png(os.path.join(pics_dir, "c1.png"), (0, 0, 160, 255))}
        r1 = recipe(p)
        for g in (fast, slow):
            said = build(base, g, r1)
            ok("the first Build is a full one", "only pictures changed" not in said)
        ok("a Build leaves a record of what it was made from", os.path.exists(os.path.join(world(fast), B.INPUT)))
        ok("two full Builds of one recipe: the same world", not differ(files(fast), files(slow)))

        said = build(base, fast, r1)
        ok("built again unchanged: nothing drawn", "only pictures changed since the last Build: 0 drawn" in said)

        # a new logo for the league (another file) and a new picture in the place of a crest
        p2 = dict(p, logo=png(os.path.join(pics_dir, "logo2.png"), (240, 200, 0, 255)))
        png(p["c1"], (90, 0, 90, 255))
        r2 = recipe(p2)
        said = build(base, fast, r2)
        ok("a new logo and a crest changed in place: only those drawn",
           "only pictures changed since the last Build: 2 drawn again" in said)
        build(base, slow, r2, full=True)
        d = differ(files(fast), files(slow))
        ok("... and the world is the one a full Build makes, file for file %s" % d[:6], not d)

        # a crest put in by hand stays while the recipe draws the same one there as before
        tid = json.load(open(os.path.join(world(fast), "leaguebuilder-plan.json"), encoding="utf-8"))["leagues"][0]["teams"][5]
        hand = os.path.join(world(fast), "common", "render", "symbol", "flag", "e_%06d.png" % tid)
        png(hand, (1, 2, 3, 255))
        before = B.file_hash(hand)
        p3 = dict(p2, c0=png(os.path.join(pics_dir, "c0b.png"), (0, 200, 200, 255)))
        said = build(base, fast, recipe(p3))
        ok("another crest changed: only it drawn", "only pictures changed since the last Build: 1 drawn again" in said)
        ok("the crest put in by hand stays", B.file_hash(hand) == before)

        # anything but pictures: a full Build
        said = build(base, fast, recipe(p3, ("Renamed FC",) + ("",) * 9))
        ok("a club renamed: a full Build", "only pictures changed" not in said and "built " in said)

        # a picture whose source is not on this PC: a full Build (it keeps the world's own)
        p4 = dict(p3, logo=os.path.join(pics_dir, "nowhere.png"))
        said = build(base, fast, recipe(p4, ("Renamed FC",) + ("",) * 9))
        ok("a picture not on this PC: a full Build", "only pictures changed" not in said)

        # B239 (jibibi 25.10.): a recipe made on another PC (the Modpack's logo paths) -- once built
        # here, a crest changed draws just that crest and the world keeps its own logo
        logo_rels = B.logo_files(json.load(open(os.path.join(world(fast), "leaguebuilder-plan.json"),
                                                encoding="utf-8"))["leagues"][0]["cid"])
        logos = {r: B.file_hash(os.path.join(world(fast), r)) for r in logo_rels
                 if os.path.isfile(os.path.join(world(fast), r))}
        said = build(base, fast, recipe(p4, ("Renamed FC",) + ("",) * 9))
        ok("B239: built again with the picture still not on this PC: nothing drawn",
           "only pictures changed since the last Build: 0 drawn" in said)
        p4b = dict(p4, c0=png(os.path.join(pics_dir, "c0c.png"), (200, 0, 200, 255)))
        said = build(base, fast, recipe(p4b, ("Renamed FC",) + ("",) * 9))
        ok("B239: a crest changed beside a logo not on this PC: only the crest drawn",
           "only pictures changed since the last Build: 1 drawn again" in said)
        ok("B239: ... and the world's own logo stays (%d files)" % len(logos),
           logos and all(B.file_hash(os.path.join(world(fast), r)) == h for r, h in logos.items()))
        said = build(base, fast, recipe(p3, ("Renamed FC",) + ("",) * 9))
        ok("B239: the logo back on this PC: a full Build (keep_added decides)", "only pictures changed" not in said)

        # a picture added where there was none: what the plan holds changes -- a full Build
        p5 = dict(p3)
        r5 = recipe(p5, ("Renamed FC",) + ("",) * 9)
        r5["leagues"][0]["club_crests"][4] = png(os.path.join(pics_dir, "c4.png"), (10, 10, 10, 255))
        build(base, fast, recipe(p3, ("Renamed FC",) + ("",) * 9))
        said = build(base, fast, r5)
        ok("a crest where the club had none: a full Build", "only pictures changed" not in said)
    finally:
        for d in (fast, slow, pics_dir):
            shutil.rmtree(d, ignore_errors=True)
    print("1..%d" % N)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1])
