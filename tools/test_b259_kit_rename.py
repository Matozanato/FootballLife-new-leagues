"""B259 (gianito9, 27.10.): a league of a world from a zip renamed, then Build. The plan's kit
folders are on the PC that built the pack; the zip's copies sit under the league's old name. The
Build must carry them to the new name instead of leaving the clubs in their lent kits.

python test_b259_kit_rename.py"""
import os
import shutil
import tempfile

import lbservers

WORLD = "_FL26M2400S"


def main():
    tmp = tempfile.mkdtemp(prefix="b259-")
    try:
        sider = os.path.join(tmp, "SiderAddons")
        kits = os.path.join(sider, "content", "kit-server")
        old = os.path.join(kits, WORLD, "Bulgarian First League", "Levski Sofia", "p1")
        os.makedirs(old)
        open(os.path.join(old, "u0001p1.ftex"), "wb").write(b"kit")
        with open(os.path.join(kits, "map.txt"), "w", encoding="utf-8") as f:
            f.write('71649, "%s\\Bulgarian First League\\Levski Sofia"   %s Bulgarian First League/7\n'
                    % (WORLD, lbservers.TAG))
            f.write('71650, "%s\\Bulgarian First League\\Slavia Sofia"   %s Bulgarian First League/8\n'
                    % (WORLD, lbservers.TAG))    # its folder is not there: nothing to carry
        gone = r"Q:\not-this-pc\SiderAddons\content\kit-server\Modpack\Bulgarian First League"
        pl = {"world": WORLD, "leagues": [{
            "name": "Efbet League", "teams": [71649, 71650], "club_names": ["Levski Sofia", "Slavia Sofia"],
            "kit_folders": [gone + "\\Levski Sofia", gone + "\\Slavia Sofia"]}]}
        logs = []
        lbservers.write(pl, sider, log=logs.append)
        new = os.path.join(kits, WORLD, "Efbet League", "Levski Sofia", "p1", "u0001p1.ftex")
        assert os.path.isfile(new), logs
        text = open(os.path.join(kits, "map.txt"), encoding="utf-8").read()
        assert '71649, "%s\\Efbet League\\Levski Sofia"' % WORLD in text, text
        assert "Bulgarian First League\\Levski Sofia" not in text, text
        assert any("Slavia Sofia" in l and "skipped" in l for l in logs), logs
        # a second Build: the copy is there, the line stays
        lbservers.write(pl, sider, log=logs.append)
        text = open(os.path.join(kits, "map.txt"), encoding="utf-8").read()
        assert text.count("71649,") == 1 and "Efbet League\\Levski Sofia" in text, text
        print("ok: test_b259_kit_rename")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
