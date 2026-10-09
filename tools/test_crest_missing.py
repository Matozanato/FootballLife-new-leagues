"""python tools/test_crest_missing.py

The pictures of a recipe made on another PC (leaguebuilder.have_picture): a club whose crest
path is not on this one gets the drawn badge, exactly the picture a club with no crest is given,
a club whose picture is here keeps it, a league logo that is gone is drawn too, a country whose
flag is gone keeps the game's flag -- and each of them is one line of the Build's log.
"""
import os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import leaguebuilder as B
import lbassets
import mkemblems

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def same(a, b):
    """two written pictures, byte for byte"""
    with open(a, "rb") as fa, open(b, "rb") as fb:
        return fa.read() == fb.read()


def main():
    """a recipe whose pictures were made on another PC, Build against a base with no kits"""
    from PIL import Image
    tmp = tempfile.mkdtemp()
    try:
        pic = os.path.join(tmp, "crest.png")
        Image.new("RGBA", (40, 60), (10, 20, 200, 255)).save(pic)
        gone = os.path.join(tmp, "not here", "crest.png")      # what another PC's recipe carries

        root = os.path.join(tmp, "world")
        base = os.path.join(tmp, "base")
        os.makedirs(base)                                      # no UniformParameter.bin: no kits
        plan = {"world": "Test", "leagues": [{
            "name": "Liga", "cid": 3001, "country": "Croatia", "flag": gone, "logo": gone,
            "teams": [901, 902], "abbrs": ["REA", "GON"],
            "club_names": ["Real crest", "Gone crest"],
            "club_crests": [pic, gone], "club_kits": ["", ""]}]}
        log = []
        B.pictures(plan, root, base, log=log.append)           # a picture that is gone, not a crash

        found = [l for l in log if "picture not found" in l]
        ok("one line per club with a gone crest", len([l for l in found if l.startswith("  crest picture")]) == 1)
        ok("the line names the club and the path it looked for",
           "  crest picture not found, drawn badge instead: Gone crest (%s)" % gone in found)
        ok("the league logo and the flag say it too",
           len([l for l in found if l.startswith("  logo picture")]) == 1 and len([l for l in found if l.startswith("  flag picture")]) == 1)

        # a club with no crest picture at all: what the gone one must come out as
        none = os.path.join(tmp, "no pictures")
        lbassets.club_crest(none, 902, "GON", None)
        drawn = os.path.join(tmp, "the picture")
        lbassets.club_crest(drawn, 901, "REA", pic)
        cr = os.path.join(root, *lbassets.CREST_DIR)
        ok("the club whose crest is gone gets the drawn badge",
           all(same(os.path.join(cr, "e_000902_r%s.png" % s), os.path.join(none, *lbassets.CREST_DIR, "e_000902_r%s.png" % s))
               for s in ("", "_l", "_ll")))
        ok("the club whose crest is here keeps its picture",
           all(same(os.path.join(cr, "e_000901_r%s.png" % s), os.path.join(drawn, *lbassets.CREST_DIR, "e_000901_r%s.png" % s))
               for s in ("", "_l", "_ll")))
        ok("and that is not the drawn badge",
           not same(os.path.join(cr, "e_000901_r_ll.png"), os.path.join(none, *lbassets.CREST_DIR, "e_000902_r_ll.png")))

        em = os.path.join(tmp, "no logo")
        lbassets.league_logo(em, 3001, "Liga", None)
        ed = os.path.join(root, *lbassets.EMBLEM_DIR)
        ok("a league logo that is gone is drawn",
           all(same(os.path.join(ed, "emb_3001%s.png" % suf), os.path.join(em, *lbassets.EMBLEM_DIR, "emb_3001%s.png" % suf))
               for suf, _ in mkemblems.VARIANTS))
        ok("a flag that is gone leaves the game's own flag",
           not [f for f in os.listdir(cr) if f.startswith("flag_")])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("%d cases passed" % N)


if __name__ == "__main__":
    main()
