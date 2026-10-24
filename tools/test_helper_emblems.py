"""python test_helper_emblems.py -- the modern CONMEBOL helper cups (the Sudamericana's first stage and
play-off, the Libertadores' qualifying) get an emblem: the one of the cup they are a round of. With none
the fixtures showed the Sudamericana's first stage with no emblem (B220, antonimus 23.10.)."""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def main():
    pl = {"leagues": [], "ccups": [{"number": B.SUDAM, "cid": 140, "name": "Sudamericana", "logo": "sud.png"}],
          "cup_ids": {"conmebol:" + B.SAM_FIRST_CODE: {"cid": 141, "reg": 900},
                      "conmebol:" + B.SPO_CODE: {"cid": 142, "reg": 901},
                      "conmebol:" + B.LIBQ_CODE: {"cid": 143, "reg": 902, "reg2": 903}}}
    got = {cid: (name, logo) for cid, name, logo in B.cup_emblems(pl)}
    ok("the Sudamericana itself", got.get(140) == ("Sudamericana", "sud.png"))
    ok("its first stage wears its emblem", got.get(141) == ("Sudamericana", "sud.png"))
    ok("its play-off too", got.get(142) == ("Sudamericana", "sud.png"))
    ok("the Libertadores qualifying gets one drawn", got.get(143) == ("Copa Libertadores", None))
    jobs, _flags, n = B.picture_jobs(pl, ".", log=lambda *a: None)
    ok("Build draws all four (%d cup logos)" % n, n == 4 and sum(1 for j in jobs if j[0] == "league_logo") == 4)
    pl2 = {"leagues": [], "ccups": [], "cup_ids": {"conmebol:" + B.SAM_FIRST_CODE: {"cid": 141, "reg": 900}}}
    ok("no Sudamericana cup in the plan: its name, drawn",
       B.cup_emblems(pl2) == [(141, B.SAM_FIRST_NAME, None)])
    ok("a world with no helper cups: nothing more", B.cup_emblems({"leagues": [], "ccups": []}) == [])
    print("1..%d" % N)


if __name__ == "__main__":
    main()
