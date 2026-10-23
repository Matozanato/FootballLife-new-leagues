"""python test_server_library.py -- a server's library (Game content > Servers, Build's checks) lists
the items a world put five folders down: the World Modpack's scoreboards are
scoreboard-server\\_FL26M2400S\\_packs\\England\\FA Cup\\BBC, and with the library three folders
deep every one of their map lines was "not found in the library" and turned yellow (SladeBR,
23.10.). An item at the top still counts, a folder with nothing of the game's in it does not."""
import os, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modstudio import servers as S

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def item(root, rel):
    """a scoreboard folder: the game's own layout under it (common\\...)"""
    d = os.path.join(root, *rel.split("\\"), "common", "render")
    os.makedirs(d)
    open(os.path.join(d, "x.dds"), "wb").close()


def main():
    t = tempfile.mkdtemp(prefix="fl26sblib-")
    try:
        item(t, "Premier League")
        item(t, "England\\Carabao Cup")
        item(t, "_FL26M2400S\\_packs\\England\\FA Cup\\BBC")
        item(t, "_FL26M2400S\\_packs\\Portugal\\Taca de Portugal")
        os.makedirs(os.path.join(t, "_FL26M2400S", "_packs", "Empty", "Nothing"))
        lib = {S.norm_item(p) for p in S.library(t, "folder")}
        ok("an item at the top", "premier league" in lib)
        ok("an item two folders down", "england\\carabao cup" in lib)
        ok("the Modpack's FA Cup scoreboard, five folders down", "_fl26m2400s\\_packs\\england\\fa cup\\bbc" in lib)
        ok("Taca de Portugal, four down", "_fl26m2400s\\_packs\\portugal\\taca de portugal" in lib)
        ok("a folder with nothing of the game's is no item", not any("empty" in p for p in lib))
        ok("a map line spelled with slashes matches", S.norm_item("_FL26M2400S/_packs/England/FA Cup/BBC") in lib)
    finally:
        shutil.rmtree(t, ignore_errors=True)
    print("%d ok" % N)


if __name__ == "__main__":
    main()
