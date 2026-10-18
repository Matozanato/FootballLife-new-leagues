"""python test_build_swap.py -- Build puts the new world in place of the old one without ever
leaving neither (B150, Tysonche35 18.10.: "livecpk/_FL26M2400E.building has no fl26world.txt"):
the old one is moved aside first and comes back when the new one cannot go in; a .building or .old
folder is no world for Switch on nor My world."""
import os, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B
from modstudio import worlds

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def put(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").write(data)


def main():
    root = tempfile.mkdtemp(prefix="fl26swap-")
    try:
        out = os.path.join(root, "livecpk", "_FL26Swap")
        put(os.path.join(out, B.MARK), "old")
        put(os.path.join(out + ".building", B.MARK), "new")
        B.swap_in(out + ".building", out)
        ok("the new world is in", open(os.path.join(out, B.MARK)).read() == "new")
        ok("no .building or .old left", not os.path.exists(out + ".building") and not os.path.exists(out + ".old"))

        # the rename of the new one fails: the old world comes back
        put(os.path.join(out + ".building", B.MARK), "newer")
        real = os.rename

        def rename(a, b):
            if a.endswith(".building"):
                raise PermissionError(13, "Access is denied")
            return real(a, b)
        os.rename = rename
        try:
            B.swap_in(out + ".building", out)
            said = None
        except B.BuildError as e:
            said = str(e)
        finally:
            os.rename = real
        ok("a failed swap says what to do: %s" % said, said and "close what has a file of it open" in said)
        ok("and the old world is still there", open(os.path.join(out, B.MARK)).read() == "new"
           and not os.path.exists(out + ".old"))

        # a world that was never built before
        fresh = os.path.join(root, "livecpk", "_FL26Fresh")
        put(os.path.join(fresh + ".building", B.MARK), "first")
        B.swap_in(fresh + ".building", fresh)
        ok("a first Build: the world is in", open(os.path.join(fresh, B.MARK)).read() == "first")

        ok("My world shows no .building or .old folder as a world",
           worlds.is_world("_FL26Swap") and not worlds.is_world("_FL26Swap.building")
           and not worlds.is_world("_FL26Swap.old"))
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("1..%d" % N)


if __name__ == "__main__":
    main()
