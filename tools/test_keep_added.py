"""Build replaces the whole world folder: pictures put there by hand must survive it (Xxspedd 04.10.)

    python tools/test_keep_added.py
"""
import os, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as LB

FLAG = "common/render/symbol/flag/"


def put(root, rel, data):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(data)


def read(root, rel):
    with open(os.path.join(root, rel), "rb") as f:
        return f.read()


def build(root, files):
    """a fresh build in root/new with these files, then the old->new swap Build does"""
    old, new = os.path.join(root, "w"), os.path.join(root, "new")
    for rel, data in files.items():
        put(new, rel, data)
    LB.write_manifest(new)
    if os.path.exists(old):
        LB.keep_added(old, new, log=lambda *a: None)
        shutil.rmtree(old)
    os.rename(new, old)
    return old


def main():
    root = tempfile.mkdtemp()
    try:
        w = build(root, {FLAG + "e_65536_r.png": b"shield", "common/etc/pesdb/Team.bin": b"t1",
                         FLAG + "e_65537_r.png": b"shield2"})
        put(w, FLAG + "e_70000_r.png", b"mine")             # added by hand
        put(w, FLAG + "e_65536_r.png", b"real crest")       # ours, replaced by hand
        put(w, "common/etc/pesdb/Team.bin", b"hand")         # not a picture: the build's wins
        w = build(root, {FLAG + "e_65536_r.png": b"shield", "common/etc/pesdb/Team.bin": b"t2",
                         FLAG + "e_65537_r.png": b"recipe crest"})
        assert read(w, FLAG + "e_70000_r.png") == b"mine"
        assert read(w, FLAG + "e_65536_r.png") == b"real crest"
        assert read(w, "common/etc/pesdb/Team.bin") == b"t2"
        assert read(w, FLAG + "e_65537_r.png") == b"recipe crest"
        # the recipe unchanged: the hand-made crest is kept build after build
        w = build(root, {FLAG + "e_65536_r.png": b"shield", "common/etc/pesdb/Team.bin": b"t2",
                         FLAG + "e_65537_r.png": b"recipe crest"})
        assert read(w, FLAG + "e_65536_r.png") == b"real crest"
        assert read(w, FLAG + "e_70000_r.png") == b"mine"
        # a crest set in the recipe later beats the hand-made one
        w = build(root, {FLAG + "e_65536_r.png": b"recipe", "common/etc/pesdb/Team.bin": b"t3"})
        assert read(w, FLAG + "e_65536_r.png") == b"recipe"
        assert read(w, FLAG + "e_70000_r.png") == b"mine"
        assert not os.path.exists(os.path.join(w, FLAG + "e_65537_r.png"))   # ours, gone from the recipe
        # a world built before the manifest: only pictures the new build does not write are kept
        os.remove(os.path.join(w, LB.MANIFEST))
        put(w, "common/etc/old.bin", b"x")
        w = build(root, {"common/etc/pesdb/Team.bin": b"t4"})
        assert read(w, FLAG + "e_65536_r.png") == b"recipe"
        assert not os.path.exists(os.path.join(w, "common/etc/old.bin"))
        print("ok")
    finally:
        shutil.rmtree(root)


if __name__ == "__main__":
    main()
