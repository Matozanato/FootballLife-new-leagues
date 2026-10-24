"""python test_helper_emblems.py -- the modern CONMEBOL helper cups (the Sudamericana's first stage and
play-off, the Libertadores' qualifying) get an emblem: the one of the cup they are a round of. With none
the fixtures showed the Sudamericana's first stage with no emblem (B220, antonimus 23.10.)."""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def main():
    pl = {"leagues": [], "ccups": [{"number": B.SUDAM, "cid": 140, "name": "Sudamericana", "logo": "sud.png"}],
          "cup_ids": {"conmebol:" + B.SAM_FIRST_CODE: {"cid": 141, "reg": 900},
                      "conmebol:" + B.SPO_CODE: {"cid": 142, "reg": 901},
                      "conmebol:" + B.LIBQ_CODE: {"cid": 143, "reg": 902, "reg2": 903}}}
    got = {cid: (name, logo) for cid, name, logo in B.cup_emblems(pl)}
    ok("the Sudamericana itself", got.get(140) == ("Sudamericana", "sud.png"))
    ok("its first stage wears its emblem", got.get(141) == ("Sudamericana", "sud.png"))
    ok("its play-off too", got.get(142) == ("Sudamericana", "sud.png"))
    ok("the Libertadores qualifying: no picture of its own (Build takes the game's)", got.get(143) == ("Copa Libertadores", None))
    jobs, _flags, n = B.picture_jobs(pl, ".", log=lambda *a: None)
    ok("Build makes all four (%d cup logos): three drawn or given, the qualifying's the game's own" % n,
       n == 4 and sum(1 for j in jobs if j[0] == "league_logo") == 3 and
       [j[1] for j in jobs if j[0] == "game_emblem"] == [(143, "Copa Libertadores", B.GAME_LIBERTADORES)])
    ok("its job has a signature (pictures_only)",
       B.job_signature(next(j for j in jobs if j[0] == "game_emblem"))[1] == [143, "Copa Libertadores", 5])

    # the game's emblem from the install: a livecpk root of a mod first, else the game's cpks; none: drawn
    import tempfile, shutil
    from PIL import Image
    import flpaths, lbassets
    tmp = tempfile.mkdtemp()
    try:
        game = os.path.join(tmp, "game")
        sider = os.path.join(game, "SiderAddons")
        mod = os.path.join(sider, "livecpk", "Mod", *lbassets.EMBLEM_DIR)
        os.makedirs(mod)
        Image.new("RGBA", (256, 256), (200, 160, 40, 255)).save(os.path.join(mod, "emb_0005_b_l.png"))
        Image.new("RGBA", (512, 512), (200, 160, 40, 255)).save(os.path.join(mod, "emb_0005_b_ll.png"))
        Image.new("RGBA", (256, 256), (255, 255, 255, 255)).save(os.path.join(mod, "emb_0005_w_l.png"))
        open(os.path.join(sider, "sider.ini"), "w").write('cpk.root = ".\\livecpk\\Mod"\n')
        old = flpaths.GAME_DIR, flpaths.SIDER_DIR, flpaths.SIDER_INI
        flpaths.GAME_DIR, flpaths.SIDER_DIR, flpaths.SIDER_INI = game, sider, os.path.join(sider, "sider.ini")
        lbassets._GAME_EMBLEMS.clear()
        out = os.path.join(tmp, "world")
        lbassets.game_emblem(out, 143, "Copa Libertadores", 5)
        d = os.path.join(out, *lbassets.EMBLEM_DIR)
        px = lambda suf: Image.open(os.path.join(d, "emb_0143%s.png" % suf))
        ok("all six variants, each its size",
           all(px(s).size == (n, n) for s, n in lbassets.mkemblems.VARIANTS))
        ok("the game's light one where it has no plain one; its dark one where it has it, else the light",
           px("_l").getpixel((5, 5)) == (200, 160, 40, 255) and px("_w_l").getpixel((5, 5)) == (255, 255, 255, 255)
           and px("_w_ll").getpixel((5, 5)) == (200, 160, 40, 255))
        os.remove(os.path.join(sider, "sider.ini"))
        lbassets._GAME_EMBLEMS.clear()
        shutil.rmtree(out)
        lbassets.game_emblem(out, 143, "Copa Libertadores", 5)
        ok("no emblem anywhere in the install: drawn, as before", px("_l").getpixel((5, 5)) != (200, 160, 40, 255)
           and len(os.listdir(d)) == 6)
        flpaths.GAME_DIR, flpaths.SIDER_DIR, flpaths.SIDER_INI = old
    finally:
        lbassets._GAME_EMBLEMS.clear()
        shutil.rmtree(tmp, ignore_errors=True)
    pl2 = {"leagues": [], "ccups": [], "cup_ids": {"conmebol:" + B.SAM_FIRST_CODE: {"cid": 141, "reg": 900}}}
    ok("no Sudamericana cup in the plan: its name, drawn",
       B.cup_emblems(pl2) == [(141, B.SAM_FIRST_NAME, None)])
    ok("a world with no helper cups: nothing more", B.cup_emblems({"leagues": [], "ccups": []}) == [])
    print("1..%d" % N)


if __name__ == "__main__":
    main()
