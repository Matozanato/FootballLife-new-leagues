"""python tools/test_replaced_shield.py

A place of the game's leagues that NewLife gives another club (refresh_game_leagues marks it with
"kit" in edits.clubs, B57): with no crest picture it gets that club's shield, the picture a new
club with the same shirt gets, or the drawn badge when the club has no shirt either -- never the
crest of the game's club that went down. A club with a crest picture keeps it; a club of the game
only renamed keeps the game's crest. Its team id is the same.
"""
import os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import leaguebuilder as B
import lbassets

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def same(a, b):
    with open(a, "rb") as fa, open(b, "rb") as fb:
        return fa.read() == fb.read()


def main():
    from PIL import Image
    tmp = tempfile.mkdtemp()
    try:
        pic = os.path.join(tmp, "crest.png")
        Image.new("RGBA", (40, 60), (10, 20, 200, 255)).save(pic)
        kit = "stripes #ffffff #0052d5 #ffffff"
        root, base = os.path.join(tmp, "world"), os.path.join(tmp, "base")
        os.makedirs(base)
        plan = {"world": "Test", "leagues": [], "edits": {"clubs": {
            "2452": {"name": "Avaí", "abbr": "AVA", "kit": kit},                 # NewLife, no crest picture
            "2468": {"name": "Vila Nova", "abbr": "VIL", "kit": ""},             # no shirt either
            "5139": {"name": "Botafogo SP", "abbr": "BOT", "crest": pic, "kit": kit},
            "1936": {"name": "Sport Recife"}}}}                                  # renamed by hand only
        B.pictures(plan, root, base, log=lambda s: None)
        cr = os.path.join(root, *lbassets.CREST_DIR)
        new = os.path.join(tmp, "new club")
        lbassets.club_crest(new, 2452, "AVA", None, kit)        # a new club with that shirt
        lbassets.club_crest(new, 2468, "VIL", None, None)       # a new club with none
        lbassets.club_crest(new, 5139, "BOT", pic, kit)
        nc = os.path.join(new, *lbassets.CREST_DIR)
        sizes = ("", "_l", "_ll")
        ok("no crest picture: the shield of its shirt, as a new club",
           all(same(os.path.join(cr, "e_002452_r%s.png" % s), os.path.join(nc, "e_002452_r%s.png" % s)) for s in sizes))
        ok("no shirt either: the drawn badge, as a new club",
           all(same(os.path.join(cr, "e_002468_r%s.png" % s), os.path.join(nc, "e_002468_r%s.png" % s)) for s in sizes))
        ok("a crest picture wins over the shirt",
           all(same(os.path.join(cr, "e_005139_r%s.png" % s), os.path.join(nc, "e_005139_r%s.png" % s)) for s in sizes))
        ok("a club only renamed keeps the game's crest", not os.path.exists(os.path.join(cr, "e_001936_r.png")))
        ok("each under its own team id", sorted(os.listdir(cr)) == sorted(
            "e_%06d_r%s.png" % (t, s) for t in (2452, 2468, 5139) for s in sizes))
        print("replaced shield: ok")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
