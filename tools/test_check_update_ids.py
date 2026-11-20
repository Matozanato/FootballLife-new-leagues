"""check_update_ids: an Update that only appends passes; one that inserts a competition in the middle,
renumbers entry ids, enters a new club or makes a kept player older fails (18.11.2026, beta 3 -> 4)."""
import os, struct, sys, tempfile, zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_update_ids as C          # noqa: E402
import playeredit as pe               # noqa: E402

P = "SiderAddons/livecpk/_W/common/etc/pesdb/"


def player(pid, age):
    r = bytearray(pe.P_REC)
    struct.pack_into("<I", r, pe.P_ID, pid)
    pe.setf(r, "Age", age)
    return bytes(r)


def team(tid):
    r = bytearray(pe.T_REC)
    struct.pack_into("<I", r, pe.T_ID, tid)
    return bytes(r)


def coach(cid):
    return struct.pack("<I", cid) + bytes(96)


def comp(cid):
    return bytes(5) + bytes([cid & 0xff]) + bytes(1) + bytes([cid >> 8]) + bytes(28)


def reg(key):
    return bytes(2) + struct.pack("<H", key) + bytes(2348)


def entry(t, eid, cid, slot):
    return struct.pack("<III", t, eid, (cid & 0xff) | slot << 8 | (cid >> 8) << 24)


def world(path, players, teams, comps, regs, ents):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(P + "Player.bin", b"".join(player(*p) for p in players))
        z.writestr(P + "Team.bin", b"".join(team(t) for t in teams))
        z.writestr(P + "Coach.bin", b"".join(coach(t) for t in teams))
        z.writestr(P + "Competition.bin", b"".join(comp(c) for c in comps))
        z.writestr(P + "CompetitionRegulation.bin", b"".join(reg(k) for k in regs))
        z.writestr(P + "CompetitionEntry.bin", b"".join(entry(*e) for e in ents))


def main():
    d = tempfile.mkdtemp()
    base = dict(players=[(10, 20), (12, 30)], teams=[100, 101], comps=[5, 7], regs=[5, 7],
                ents=[(100, 1, 5, 1), (101, 2, 7, 1)])
    prev = os.path.join(d, "prev.zip")
    world(prev, **base)

    ok = os.path.join(d, "append.zip")              # new league, club and player appended
    world(ok, players=base["players"] + [(11, 18)], teams=base["teams"] + [102], comps=[5, 7, 9],
          regs=[5, 7, 9], ents=base["ents"] + [(101, 3, 9, 1)])
    r = C.check(prev, ok)
    assert r["result"] == "PASS", r["fail"]
    assert any("1 of them below" in s for s in r["info"]), r["info"]    # a hole: reported, not failed

    bad = os.path.join(d, "insert.zip")             # beta 4: the new league in the middle, its club new
    world(bad, players=[(10, 22), (12, 30)], teams=base["teams"] + [102], comps=[5, 9, 7], regs=[5, 9, 7],
          ents=[(100, 1, 5, 1), (102, 2, 9, 1), (101, 3, 7, 1)])
    r = C.check(prev, bad)
    f = "\n".join(r["fail"])
    assert r["result"] == "FAIL"
    for want in ("Competition.bin: 1 of 2 rows", "CompetitionRegulation.bin: 1 of 2 rows",
                 "1 of 2 entry ids", "1 new clubs play", "1 kept players are older"):
        assert want in f, (want, f)
    assert "only in competitions prev does not have (9)" in f, f

    old = os.path.join(d, "oldleague.zip")         # a new club appended to a league prev has
    world(old, players=base["players"], teams=base["teams"] + [102, 103], comps=[5, 7], regs=[5, 7],
          ents=base["ents"] + [(102, 3, 7, 2)])
    r = C.check(prev, old)
    f = "\n".join(r["fail"])
    assert r["result"] == "FAIL"
    for want in ("1 new places in 1 competitions prev has", "1 new clubs play in competitions prev has"):
        assert want in f, (want, f)
    assert any("1 new clubs are in no competition" in s and "103" in s for s in r["info"]), r["info"]
    print("test_check_update_ids: OK")


if __name__ == "__main__":
    main()
