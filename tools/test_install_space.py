"""python test_install_space.py -- B41 (vmican, 15.10.): Import your world unpacked every zip into
%TEMP% on C:, the Modpack is 7 GB unpacked, and on a full C: the unpack stopped half-way although
the game was on D:. installer.work_dir: %TEMP% while its disk has room, else a folder beside the
game, else a message naming the sizes before anything is unpacked."""
import os, shutil, sys, tempfile, zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modstudio import installer as I

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def main():
    root = tempfile.mkdtemp(prefix="fl26_b41_")
    real = I.free
    try:
        z = os.path.join(root, "world.zip")
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as f:
            f.writestr("livecpk/_W/a.bin", b"\0" * 3000000)
            f.writestr("livecpk/_W/b.txt", "x" * 1000)
        game = os.path.join(root, "game with space")
        os.makedirs(game)
        ok("the size unpacked is the zip's files", I.unpacked_size(z) == 3001000)
        ok("a folder counts 0", I.unpacked_size(game) == 0)

        tmp = os.path.normcase(os.path.abspath(tempfile.gettempdir()))
        w = I.work_dir(z, game)
        ok("room in %TEMP%: unpacked there as before", os.path.normcase(os.path.dirname(w)) == tmp)
        shutil.rmtree(w)

        I.free = lambda d: 10 if os.path.normcase(os.path.abspath(d)) == tmp else 50 * I.GB
        w = I.work_dir(z, game)
        ok("%TEMP%'s disk full: beside the game", os.path.normcase(w).startswith(
            os.path.normcase(os.path.join(game, "_fl26ms_unpack"))))
        top = I.unpack(z, w)
        ok("and the zip unpacks there", os.path.getsize(os.path.join(top, "livecpk", "_W", "a.bin")) == 3000000)

        I.free = lambda d: 10
        try:
            I.work_dir(z, game)
            said = ""
        except ValueError as e:
            said = str(e)
        ok("no room anywhere: a message with the sizes, before unpacking (%s)" % said,
           said.startswith("not enough free space") and "GB" in said)
        ok("no game folder known and %TEMP% full: the same message", _raises(lambda: I.work_dir(z, None)))
    finally:
        I.free = real
        shutil.rmtree(root, ignore_errors=True)
    print("test_install_space: ok (%d)" % N)


def _raises(f):
    try:
        f()
    except ValueError:
        return True
    return False


if __name__ == "__main__":
    main()
