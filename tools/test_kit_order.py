"""python test_kit_order.py -- our clubs' kit definitions go into UniformParameter.bin in the shipped
archive's order: the player kits first (1st, 2nd, 3rd), then the goalkeeper's. Written as 1st, 2nd,
GK1st, 3rd, FL27 offered only two kits of a new club (mato 07.11.)."""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mkkits as K

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def main():
    full = {k: b"x" for k in ("1st_realUni", "2nd_realUni", "3rd_realUni", "GK1st_realUni")}
    ok("the player kits before the goalkeeper's",
       K.kinds_of(full) == ("1st_realUni", "2nd_realUni", "3rd_realUni", "GK1st_realUni"))
    ok("the same order as the shipped archive (names sorted)", list(K.kinds_of(full)) == sorted(full))
    two = {k: b"x" for k in ("1st_realUni", "2nd_realUni", "GK1st_realUni")}
    ok("a club without a third kit", K.kinds_of(two) == ("1st_realUni", "2nd_realUni", "GK1st_realUni"))
    plain = {k: b"x" for k in K.PLAIN_KINDS}
    ok("plain kits as before", K.kinds_of(plain) == K.PLAIN_KINDS)
    out = K.repack([], [((72163, "Club"), (5, full))])
    names = [n.decode() for n in out.split(b"\0") if n.endswith(b".bin")]
    names = [n[n.index("6627"):] for n in names]
    ok("repacked in that order: %s" % names,
       names == ["6627_ACL_1st_realUni.bin", "6627_ACL_2nd_realUni.bin", "6627_ACL_3rd_realUni.bin",
                 "6627_ACL_GK1st_realUni.bin"])
    print("1..%d" % N)


if __name__ == "__main__":
    main()
