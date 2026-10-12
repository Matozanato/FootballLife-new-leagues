"""python tools/test_pack_guard.py

The release guard (mszip.check_pack): the 0.2.0 package went out with an old fl26caps.lua,
so the zip now stops on a known crash site, on a fl26caps.lua that is not the generated set
or not the one in the game we test with, without FL26_DIR or without the regen face pack (51ab5df),
and lists modules not played in the game in that form.
"""
import os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mszip

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def write(p, text):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8", newline="").write(text)


def main():
    tmp = tempfile.mkdtemp()
    repo, keep = mszip.REPO, os.environ.get("FL26_DIR")
    try:
        mszip.REPO = os.path.join(tmp, "repo")
        pack, game = os.path.join(tmp, "pack"), os.path.join(tmp, "game")
        caps = "-- set, 3502 patches\n{0x1412f9100}\n"
        write(os.path.join(mszip.REPO, "sider", "fl26caps.lua"), caps)
        write(os.path.join(mszip.REPO, "sider", "fl26caps.some-set.lua"), caps)
        write(os.path.join(pack, "modules", "fl26caps.lua"), caps)
        write(os.path.join(pack, "modules", "fl26swiss.lua"), "-- swiss\n")
        write(os.path.join(game, "SiderAddons", "modules", "fl26caps.lua"), caps.replace("\n", "\r\n"))
        write(os.path.join(game, "SiderAddons", "modules", "fl26swiss.lua"), "-- swiss\n")
        write(os.path.join(pack, "modules", "fl26regen_faces.bin"), "faces")
        write(os.path.join(pack, "livecpk", "FL26 Regen Faces", "face.dds"), "face")
        os.environ.pop("FL26_DIR", None)
        ok("no FL26_DIR stops it", any("FL26_DIR is not set" in b for b in mszip.check_pack(pack)))
        os.environ["FL26_DIR"] = game
        ok("the tested set goes out (line endings aside)", mszip.check_pack(pack) == [])

        write(os.path.join(pack, "modules", "fl26caps.lua"), "-- old set, 3520 patches\n{0x1412F9046}\n")
        bad = mszip.check_pack(pack)
        ok("a known crash site stops it", any("creation crash" in b for b in bad))
        ok("so does a fl26caps.lua that is not the generated one", any("copy it over" in b for b in bad))
        ok("and one that is not the game's", any("not the one installed in the game" in b for b in bad))

        write(os.path.join(pack, "modules", "fl26caps.lua"), caps)
        write(os.path.join(pack, "modules", "fl26swiss.lua"), "-- swiss, newer\n")
        ok("a module the game has in another form is only listed", mszip.check_pack(pack) == [])

        os.remove(os.path.join(pack, "modules", "fl26regen_faces.bin"))
        ok("a package without the regen faces stops it", any("no regen face pack" in b for b in mszip.check_pack(pack)))
    finally:
        mszip.REPO = repo
        if keep is None:
            os.environ.pop("FL26_DIR", None)
        else:
            os.environ["FL26_DIR"] = keep
        shutil.rmtree(tmp, ignore_errors=True)
    print("%d cases passed" % N)


if __name__ == "__main__":
    main()
