"""python test_code_stamp.py -- B244 (antonimus 26.10.): in Mod Studio's exe the Build's code stamp
(leaguebuilder.code_stamp, part of the key pictures_only compares) follows the exe, not the version
alone. Every beta of 0.2.5 is "0.2.5": with the version as the stamp a Build after an update with
the same recipe drew the pictures again and kept the world, so the update's fixes to the Build
(B241, no away goals in the modern CONMEBOL) never reached it. Two exes of one version are two
stamps; the same exe is one stamp; an exe that cannot be read never matches."""
import os, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def stamp_of(exe):
    old = getattr(sys, "frozen", None), sys.executable
    sys.frozen, sys.executable = True, exe
    try:
        return B.code_stamp()
    finally:
        if old[0] is None:
            del sys.frozen
        else:
            sys.frozen = old[0]
        sys.executable = old[1]


def main():
    d = tempfile.mkdtemp(prefix="fl26-stamp-")
    a, b, a2 = (os.path.join(d, n) for n in ("a.exe", "b.exe", "a2.exe"))
    body = os.urandom(3 << 20)
    for p, data in ((a, body), (b, body[:-1] + bytes([body[-1] ^ 1])), (a2, body)):
        with open(p, "wb") as f:
            f.write(data)
    from modstudio import VERSION
    sa, sb, sa2 = stamp_of(a), stamp_of(b), stamp_of(a2)
    ok("an exe's stamp is not its version alone (%s)" % VERSION, sa != VERSION)
    ok("two exes of one version, one byte apart, are two stamps", sa != sb)
    ok("the same exe twice is one stamp", sa == sa2 == stamp_of(a))
    gone = stamp_of(os.path.join(d, "missing.exe"))
    ok("an exe that cannot be read is no stamp of a readable one", gone not in (sa, sb, VERSION))
    ok("run from the sources the stamp is still the sources' hash", B.code_stamp() not in (sa, sb, VERSION))
    print("all %d checks passed" % N)


if __name__ == "__main__":
    main()
