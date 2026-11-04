r"""python tools/test_install_empty_root.py

B317 (Jh / joseh.zk, 04.11.): Install mods of a big zip stopped with "[Errno 2] No such file or
directory: ...\livecpk\root (2)\.modstudio". The zip had a livecpk folder with no file in it, the
game already had a livecpk\root of its own, so the part went to "root (2)" -- a folder the copy
never made, there being nothing to copy -- and the mark written into it failed. Now a livecpk
folder with no file is no part: nothing to put in place and no cpk.root line for it.

A fake Sider folder in a temp folder. No game.
"""
import os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from modstudio import installer as I
from modstudio.siderini import SiderIni
from test_install_stop import Game, put, ok

import test_install_stop as T


def main():
    tmp = tempfile.mkdtemp(prefix="fl26_emptyroot_")
    try:
        sd = os.path.join(tmp, "SiderAddons")
        put(os.path.join(sd, "sider.ini"), '[sider]\ncpk.root = ".\\livecpk\\root"\nlua.module = "kserv.lua"\n')
        os.makedirs(os.path.join(sd, "modules"))
        put(os.path.join(sd, "livecpk", "root", "common", "x.bin"), "the game's own")
        src = os.path.join(tmp, "Pack", "SiderAddons")
        os.makedirs(os.path.join(src, "livecpk", "root", "common", "etc"))          # empty
        put(os.path.join(src, "livecpk", "Faces", "common", "face.bin"), "f")
        work = tempfile.mkdtemp(prefix="emptyroot_")
        parts = I.detect(I.unpack(os.path.join(tmp, "Pack"), work), "mod")
        ini = SiderIni.load(os.path.join(sd, "sider.ini"))
        inst = I.Installer(Game(sd), ini, "Pack.zip", replace_lines=True)
        inst.run(parts)
        ini.save()
        shutil.rmtree(work, ignore_errors=True)
        lines = [l.strip() for l in open(os.path.join(sd, "sider.ini"), encoding="utf-8")]
        ok("the install went through, the root with files is in place",
           os.path.exists(os.path.join(sd, "livecpk", "Faces", "common", "face.bin")))
        ok("no root (2) made and no line for it: %s" % lines,
           not os.path.exists(os.path.join(sd, "livecpk", "root (2)"))
           and not any("root (2)" in l for l in lines))
        ok("the game's own root untouched",
           open(os.path.join(sd, "livecpk", "root", "common", "x.bin"), encoding="utf-8").read() == "the game's own")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("test_install_empty_root: ok (%d)" % T.N)


if __name__ == "__main__":
    main()
