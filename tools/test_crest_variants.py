"""python test_crest_variants.py -- a club of the game that ships its crest only as a light and a dark
version (1600 Spezia: e_001600_r_w / _r_b, no _r) gets a world's crest in those files too: the game
never reads _r for it, so Lanerossi Vicenza on 1600 in the Europack kept Spezia's crest everywhere
(B221, JoJofiaz 23.10.). A new club (71578 and up) keeps the three files it had."""
import os, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
import lbassets, mkcrests
import leaguebuilder as B
from modstudio import gamecrest

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def main():
    t = tempfile.mkdtemp(prefix="fl26crestvar-")
    try:
        game = [os.path.basename(r) for r in B.crest_files(1600)]
        ok("a club of the game: _r, _r_w and _r_b in three sizes (%d)" % len(game), len(game) == 9
           and {"e_001600_r.png", "e_001600_r_w.png", "e_001600_r_b_ll.png"} <= set(game))
        ours = [os.path.basename(r) for r in B.crest_files(71594)]
        ok("a new club: the three _r files only", ours == ["e_071594_r.png", "e_071594_r_l.png", "e_071594_r_ll.png"])
        pic = os.path.join(t, "vicenza.png")
        Image.new("RGBA", (300, 300), (200, 0, 0, 255)).save(pic)
        lbassets.club_crest(t, 1600, "LRV", pic)
        lbassets.club_crest(t, 71594, "SPE", pic)
        d = os.path.join(t, *lbassets.CREST_DIR)
        files = sorted(os.listdir(d))
        ok("Build writes every file crest_files names (%d)" % len(files),
           set(files) == {os.path.basename(r) for r in B.crest_files(1600) + B.crest_files(71594)})
        px = {f: Image.open(os.path.join(d, f)).size[0] for f in files}
        ok("each in its size", px["e_001600_r_w.png"] == 128 and px["e_001600_r_b_l.png"] == 256
           and px["e_001600_r_w_ll.png"] == 512)
        ok("the dark version is the same picture",
           Image.open(os.path.join(d, "e_001600_r_b.png")).getpixel((64, 64)) == (200, 0, 0, 255))
        # the Leagues page finds the game's crest of a club with only the light and dark ones
        g = os.path.join(t, "game")
        root = os.path.join(g, "SiderAddons", "livecpk", "pack")
        f = os.path.join(root, *gamecrest.FLAG.split("/"), "e_001600_r_w_l.png")
        os.makedirs(os.path.dirname(f))
        Image.new("RGBA", (256, 256)).save(f)
        os.makedirs(os.path.join(g, "SiderAddons"), exist_ok=True)
        open(os.path.join(g, "SiderAddons", "sider.ini"), "w").write('cpk.root = "livecpk/pack"\n')

        class G:
            folder, sider_dir = g, os.path.join(g, "SiderAddons")
        got = gamecrest.crest(G, 1600, cache=os.path.join(t, "cache"))
        ok("the Leagues page shows a light-only crest (%s)" % got, got and os.path.samefile(got, f))
    finally:
        shutil.rmtree(t, ignore_errors=True)
    print("%d ok" % N)


if __name__ == "__main__":
    main()
