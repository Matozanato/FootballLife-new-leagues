"""python tools/test_set_roles.py <pesdb>

Captain and set-piece takers for Build's new clubs (lbplayers.set_roles, mato 18.10.: the
goalkeeper captained every new club, which carried no role flags). On a copy of the game's
tables: clubs with their flags taken off get exactly one player for each of the six roles, an
outfield player of the first eleven, the captain the one with Captaincy when the eleven has
one; a club that keeps a flag is left as it is; shirt numbers and squad orders do not move.
"""
import os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lbplayers as L
import pesdb

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1


base = sys.argv[1]
# the bits as the game's Player Settings showed them (18.10., Al Kuwait test career)
ok("bit 5 is the captain, bit 4 penalties", L.ROLES[5] == "captain" and L.ROLES[4] == "penalties")
ok("bits 0-3: right corners, short FK, left corners, long FK",
   L.ROLES[:4] == ["right corners", "short free kicks", "left corners", "long free kicks"])
tmp = tempfile.mkdtemp(prefix="roles-")
try:
    for n in ("Player.bin", "PlayerAssignment.bin"):
        shutil.copy(os.path.join(base, n), tmp)
    sq = L.Squads(tmp)
    a = sq.assigns
    flagged = [t for t, v in sq.by_club.items() if any(L.u32(a, o + 12) >> L.ROLE_SHIFT for *_x, o in v)]
    plain = [t for t, v in sorted(sq.by_club.items()) if len(v) >= 18 and t not in flagged][:40]
    keep = flagged[0]
    strip = plain + flagged[1:2]                      # one club whose flags are taken off by hand
    for t in flagged[1:2]:
        for *_x, o in sq.by_club[t]:
            p = L.u32(a, o + 12) & (1 << L.ROLE_SHIFT) - 1
            a[o + 12:o + 16] = p.to_bytes(4, "little")
    open(os.path.join(tmp, "PlayerAssignment.bin"), "wb").write(pesdb.wesys_pack(bytes(a)))
    before = L.Squads(tmp)
    done = L.set_roles(tmp, strip + [keep], log=lambda *x: None)
    after = L.Squads(tmp)
    ok("every stripped club got roles", set(done) == set(strip))
    ok("a club with its own flags is left alone", keep not in done
       and [L.u32(before.assigns, o + 12) for *_x, o in before.by_club[keep]]
       == [L.u32(after.assigns, o + 12) for *_x, o in after.by_club[keep]])
    for t in strip:
        v = after.by_club[t]
        count = [0] * len(L.ROLES)
        for order, pid, shirt, o in v:
            f = L.u32(after.assigns, o + 12) >> L.ROLE_SHIFT
            for k in range(len(L.ROLES)):
                if f >> k & 1:
                    count[k] += 1
                    r = after.row(pid)
                    ok("club %d: %s in the first eleven" % (t, L.ROLES[k]), order < 11)
                    ok("club %d: %s is no goalkeeper" % (t, L.ROLES[k]), r["Registered Position"] != "GK")
        ok("club %d: one player for each role" % t, count == [1] * len(L.ROLES))
        ok("club %d: orders and shirts unchanged" % t,
           [(x[0], x[1], x[2]) for x in v] == [(x[0], x[1], x[2]) for x in before.by_club[t]])
        xi = [after.row(pid) for order, pid, _s, _o in v if order < 11]
        if any(r["Captaincy"] == "1" and r["Registered Position"] != "GK" for r in xi):
            ok("club %d: the captain has Captaincy" % t, after.row(done[t]["captain"])["Captaincy"] == "1")
    ok("a second run changes nothing", L.set_roles(tmp, strip, log=lambda *x: None) == {})
    # Build's call: every club and national team that has no flag, the flagged ones as they are
    flagged_now = {t for t, v in after.by_club.items() if any(L.u32(after.assigns, o + 12) >> L.ROLE_SHIFT
                                                             for *_x, o in v)}
    rest = L.set_roles(tmp, None, log=lambda *x: None)
    last = L.Squads(tmp)
    ok("every club gets roles", set(rest) == set(after.by_club) - flagged_now)
    ok("flagged clubs untouched", all([L.u32(after.assigns, o + 12) for *_x, o in after.by_club[t]]
                                      == [L.u32(last.assigns, o + 12) for *_x, o in last.by_club[t]]
                                      for t in flagged_now))
    ok("no club left without a captain", all(any(L.u32(last.assigns, o + 12) >> (L.ROLE_SHIFT + 5) & 1
                                                 for *_x, o in v) for t, v in last.by_club.items()
                                             if any(p in last.index for _o, p, _s, _x in v)))
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print("test_set_roles: %d ok" % N)
