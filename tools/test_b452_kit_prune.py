"""B452 (13.11.2026): a club renamed in the recipe, then Build: the kit folder under the old name
must go (209 renamed clubs of the GigaPack left 342 MB in the zip), a folder changed by hand and a
folder Mod Studio did not put there must stay, and a Switch on (no redraw) takes nothing out.

python test_b452_kit_prune.py"""
import os
import shutil
import tempfile

import lbservers

WORLD = "_FL26B452"


def main():
    tmp = tempfile.mkdtemp(prefix="b452-")
    try:
        sider = os.path.join(tmp, "SiderAddons")
        kits = os.path.join(sider, "content", "kit-server")
        os.makedirs(kits)
        open(os.path.join(kits, "map.txt"), "w").close()
        src = os.path.join(tmp, "pack", "Always Ready")
        os.makedirs(os.path.join(src, "p1"))
        open(os.path.join(src, "p1", "u0001p1.ftex"), "wb").write(b"kit")

        def plan(name):
            return {"world": WORLD, "leagues": [{"name": "Division Profesional", "teams": [71649],
                                                 "club_names": [name], "kit_folders": [src]}]}
        logs = []
        lg = os.path.join(kits, WORLD, "Division Profesional")
        lbservers.write(plan("Always Ready"), sider, log=logs.append, redraw=True)
        assert os.path.isfile(os.path.join(lg, "Always Ready", "p1", "u0001p1.ftex")), logs
        # the player's own folders in the world's kit folder: one with no note of ours, one copy changed by hand
        own = os.path.join(lg, "My own kit", "p1")
        os.makedirs(own)
        open(os.path.join(own, "x.ftex"), "wb").write(b"mine")
        hand = os.path.join(lg, "Edited", "p1")
        shutil.copytree(os.path.join(lg, "Always Ready"), os.path.join(lg, "Edited"))
        open(os.path.join(hand, "extra.ftex"), "wb").write(b"by hand")
        # renamed; a Switch on (no redraw) leaves the old folder
        lbservers.write(plan("Club Always Ready"), sider, log=logs.append)
        assert os.path.isdir(os.path.join(lg, "Always Ready")), "a Switch on took a folder out"
        # a Build takes it out
        lbservers.write(plan("Club Always Ready"), sider, log=logs.append, redraw=True)
        assert os.path.isfile(os.path.join(lg, "Club Always Ready", "p1", "u0001p1.ftex")), logs
        assert not os.path.exists(os.path.join(lg, "Always Ready")), "the old name's folder stayed"
        assert os.path.isdir(own) and os.path.isdir(hand), "a folder of the player's was taken out"
        assert any("no map line names" in l for l in logs), logs
        text = open(os.path.join(kits, "map.txt"), encoding="utf-8").read()
        assert text.count("71649,") == 1 and "Club Always Ready" in text, text
        # a folder a world zip brought: the note carries the builder's times, the files the day of the Install
        zipped = os.path.join(lg, "From The Zip")
        shutil.copytree(os.path.join(lg, "Club Always Ready"), zipped)
        note = os.path.join(zipped, lbservers.COPIED)
        open(note, "w", encoding="utf-8").write("".join(
            "%s\t%d\t%d\n" % (r, sz, t - 400000) for r, (sz, t) in sorted(lbservers._files(zipped).items())))
        late = os.path.join(lg, "Zip Then Edited")
        shutil.copytree(zipped, late)
        f = os.path.join(late, "p1", "u0001p1.ftex")
        os.utime(f, (os.path.getmtime(f) + 3600, os.path.getmtime(f) + 3600))     # touched an hour after the Install
        lbservers.write(plan("Club Always Ready"), sider, log=logs.append, redraw=True)
        assert not os.path.exists(zipped), "an untouched folder from a zip stayed"
        assert os.path.isdir(late), "a folder edited after the Install was taken out"
        # once more: nothing else goes
        n = sum(len(f) for _d, _s, f in os.walk(os.path.join(kits, WORLD)))
        lbservers.write(plan("Club Always Ready"), sider, log=logs.append, redraw=True)
        assert n == sum(len(f) for _d, _s, f in os.walk(os.path.join(kits, WORLD)))
        # a map with no line of the world: nothing is judged
        open(os.path.join(kits, "map.txt"), "w").close()
        assert lbservers.prune(kits, WORLD, log=logs.append) == 0
        assert os.path.isdir(os.path.join(lg, "Club Always Ready"))
        print("ok: test_b452_kit_prune")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
