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
        drawn_check(tmp, pic, gone, base)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("%d cases passed" % N)


def drawn_check(tmp, pic, gone, base):
    """checks.drawn_pictures (release.py's checks step) on the record write_input leaves: the logo
    and crests with no picture, never the ones with a picture or one that is gone (keep_added).
    14.11.2026: 62 play-offs of GigaPack beta 2 had a drawn emblem and no check said so"""
    from modstudio import checks
    root = os.path.join(tmp, "drawn world")
    os.makedirs(root)
    ok("no leaguebuilder-input.json: nothing drawn to tell", checks.drawn_pictures(root) == [])
    plan = {"world": "Test", "leagues": [
        {"name": "Liga A", "cid": 3001, "country": "Croatia", "logo": pic,
         "teams": [911, 912, 913, 914], "abbrs": ["PIC", "KIT", "NON", "GON"],
         "club_names": ["Picture", "Kit shield", "Nothing", "Gone"],
         "club_crests": [pic, None, None, gone], "club_kits": ["", "red white", "", ""]},
        {"name": "Liga B", "cid": 3002, "country": "Croatia", "logo": None,
         "teams": [], "abbrs": [], "club_names": []},
        {"name": "Liga C", "cid": 3003, "country": "Croatia", "logo": gone,
         "teams": [], "abbrs": [], "club_names": []}]}
    B.write_input(root, "key", plan, base)
    got = checks.drawn_pictures(root)
    ok("the logo with no picture and the crests with none are drawn",
       sorted(got) == [("club_crest", 912, "KIT"), ("club_crest", 913, "NON"), ("league_logo", 3002, "Liga B")])
    ok("a logo or crest whose picture is gone is not (the world keeps its own)",
       not [j for j in got if j[1] in (3003, 914)])
    ok("shields_ok: the kit's shield counts as a picture",
       sorted(checks.drawn_pictures(root, shields_ok=True)) == [("club_crest", 913, "NON"), ("league_logo", 3002, "Liga B")])
    recipe_drawn_check(root, pic)


def recipe_drawn_check(root, pic):
    """17.11.2026 (GigaPack audit): a crest or logo the recipe takes from a folder of our drawn
    pictures (clubs/crests/drawn1111) is a picture to Build, so no job shows it; the check reads the
    plan the Build wrote. A real picture, a folder that only ends in "drawn" and a file named
    drawn are not ours"""
    import json
    from modstudio import checks
    base = os.path.join(os.path.dirname(pic), "megapack", "clubs", "crests")
    plan = {"world": "Test", "leagues": [
        {"name": "Liga A", "cid": 3001, "logo": os.path.join(os.path.dirname(pic), "logos", "drawn", "liga_a.png"),
         "teams": [921, 922, 923, 924, 925], "club_names": ["Drawn", "Drawn old", "Real", "Withdrawn", "Named drawn"],
         "club_crests": [base + "/drawn1111/out/nl_1.png", base + "\\drawn\\x.png", pic,
                         base + "/withdrawn/y.png", base + "/found/drawn.png"]},
        {"name": "Liga B", "cid": 3002, "teams": [931], "club_names": ["None"], "club_crests": [None]}],
        "others": [{"name": "Other clubs", "teams": [941], "club_names": ["Other drawn"],
                    "club_crests": ["D:/x/DRAWN2/z.png"]}]}
    with open(os.path.join(root, "leaguebuilder-plan.json"), "w", encoding="utf-8") as f:
        json.dump(plan, f)
    got = checks.recipe_drawn(root)
    ok("recipe crests in drawn folders are found (drawn1111, drawn, any case), and the drawn logo",
       sorted(got, key=str) == sorted([("recipe_crest", 921, "Drawn"), ("recipe_crest", 922, "Drawn old"),
                                       ("recipe_crest", 941, "Other drawn"), ("recipe_logo", 3001, "Liga A (logo)")], key=str))
    ok("a real picture, a 'withdrawn' folder and a file called drawn are not", not [g for g in got if g[1] in (923, 924, 925, 931)])
    all_ = checks.drawn_pictures(root)
    ok("drawn_pictures (the release check) reports them besides the ones Build drew",
       set(got) <= set(all_) and ("club_crest", 913, "NON") in all_ and len(all_) == len(got) + 3)
    os.remove(os.path.join(root, "leaguebuilder-input.json"))
    ok("without the Build's record the recipe's drawn pictures are still told", sorted(checks.drawn_pictures(root), key=str) == sorted(got, key=str))


if __name__ == "__main__":
    main()
