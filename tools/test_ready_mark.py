r"""python test_ready_mark.py -> a world installed from a zip and built again on this PC is not a
ready world any more: Build does not carry the .modstudio mark over (0.2.4, the Build lock)"""
import os, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as LB

with tempfile.TemporaryDirectory() as t:
    old, new = os.path.join(t, "old"), os.path.join(t, "new")
    for d in (old, new):
        os.makedirs(os.path.join(d, "common", "render", "symbol", "flag"))
    open(os.path.join(old, ".modstudio"), "w").write("FL26 Modpack\n")
    open(os.path.join(old, "common", "render", "symbol", "flag", "e_900001_r.png"), "wb").write(b"png")
    open(os.path.join(new, "fl26world.txt"), "w").write("world x\n")
    kept = LB.keep_added(old, new, log=lambda s: None)
    assert ".modstudio" not in kept and not os.path.exists(os.path.join(new, ".modstudio")), kept
    assert "common/render/symbol/flag/e_900001_r.png" in kept, kept
print("ready mark: ok")
