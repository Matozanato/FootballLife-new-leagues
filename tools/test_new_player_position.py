"""python tools/test_new_player_position.py -- B201/B202 (JoJofiaz 22.10.): a new player is a copy
of the club's player that was selected. Made a keeper, a copy of a midfielder kept the
midfielder's natural positions; made a CF, a copy of a keeper kept the keeper's abilities, and the
Rating box pushed them to 99.

Checked without the game: lbplayers.new_position (the Players page) and playeredit.natural
(Build, Player Editor) on made-up rows and a made-up Player.bin record.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lbplayers as P
import playeredit as E

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %2d - %s" % (N, name))


def player(pid, pos, base, **pos_ratings):
    r = {"player": pid, "name": "P" + pid, "Registered Position": pos}
    r.update({n: str(base) for n, _b in E.ABILITIES})
    if pos == "GK":                                   # a keeper: keeping high, the rest low
        r.update({n: "45" for n, _b in E.ABILITIES})
        r.update({n: str(base) for n, _b in E.ABILITIES if n.startswith(("GK", "Goalkeeping"))})
    r.update({p: "0" for p in E.POSITIONS})
    r.update({k: str(v) for k, v in pos_ratings.items()})
    r[pos] = "2"
    return r


def main():
    gk = player("1", "GK", 80)
    cf = player("2", "CF", 72, SS=1)
    cmf = player("3", "CMF", 74, DMF=1, AMF=2)
    rows = [gk, cf, cmf]

    # B202: a copy of the keeper made a CF, at the rating he had
    a = {"like": "1", "name": "New"}
    want = 73
    src = P.new_position(a, "CF", rows, want)
    m = dict(cf, **{k: v for k, v in a.items() if k != "like"})
    ok("a copy of the keeper made a CF becomes a copy of the club's CF", src is cf and a["like"] == "2")
    ok("at the rating asked for (%d)" % P.rating(dict(m, **{"Registered Position": "CF"})),
       abs(P.rating(dict(m, **{"Registered Position": "CF"})) - want) <= 1)
    ok("no ability at 99", all(int(m[n]) < 99 for n, _b in E.ABILITIES))
    ok("CF natural, GK 0", a["CF"] == "2" and a["GK"] == "0")

    # B201: a copy of a midfielder made a keeper
    a = {"like": "3", "name": "Keeper"}
    src = P.new_position(a, "GK", rows, 70)
    ok("a copy of the midfielder made a keeper becomes a copy of the keeper", src is gk and a["like"] == "1")
    ok("GK natural, every outfield position 0", a["GK"] == "2" and all(a[p] == "0" for p in E.POSITIONS if p != "GK"))

    # the same side: no new copy, the other positions he plays are kept
    a = {"like": "3", "name": "Ten"}
    ok("CMF -> AMF: still a copy of the CMF", P.new_position(a, "AMF", rows, 74) is None and a["like"] == "3")
    ok("AMF natural, GK 0, DMF not touched", a["AMF"] == "2" and a["GK"] == "0" and "DMF" not in a)

    # no keeper at the club: positions only
    a = {"like": "3"}
    ok("no keeper to copy: stays a copy of the CMF", P.new_position(a, "GK", [cf, cmf], 70) is None
       and a["like"] == "3" and a["GK"] == "2" and a["CMF"] == "0")

    # Build / Player Editor: natural() on a record
    rec = bytearray(E.P_REC)
    E.setf(rec, "Registered Position", E.POSITIONS.index("CMF"))
    for p, v in (("CMF", 2), ("AMF", 2), ("DMF", 1)):
        E.setf(rec, p, v)
    old = bytes(rec)
    E.setf(rec, "Registered Position", 0)
    E.natural(rec, old)
    ok("natural: a CMF made a keeper is GK 2 and plays no outfield position",
       E.getf(rec, "GK") == 2 and all(E.getf(rec, p) == 0 for p in E.POSITIONS[1:]))
    rec = bytearray(old)
    E.setf(rec, "Registered Position", 0)
    E.setf(rec, "DMF", 1)
    E.natural(rec, old, given={"Registered Position", "DMF"})
    ok("natural: a position the edit sets itself stays", E.getf(rec, "DMF") == 1 and E.getf(rec, "CMF") == 0)
    rec = bytearray(old)
    E.setf(rec, "Registered Position", E.POSITIONS.index("AMF"))
    E.natural(rec, old)
    ok("natural: CMF -> AMF keeps CMF and DMF", E.getf(rec, "AMF") == 2 and E.getf(rec, "CMF") == 2
       and E.getf(rec, "DMF") == 1)
    print("all passed")


if __name__ == "__main__":
    main()
