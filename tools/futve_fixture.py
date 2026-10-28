r"""python futve_fixture.py --make  [--world <pesdb>] [--from <Player.bin>] [--out <folder>]
                                  [--team 71606] [--assignments <PlayerAssignment.bin>]
       python futve_fixture.py --check <Player.bin> [--assignments <PlayerAssignment.bin>]
                                  [--team 71606]

The test fixture of this branch: a Player.bin in which every one of the 25 stats of every player
of Deportivo Táchira (the world's team 71606) is 99. The in-game tests use it so a career with
Táchira is quick and predictable; the sandbox installs it for a test and puts the world's own
Player.bin back afterwards.

  --make   writes <out>/Player.bin (default out/futve/fixtures) with those stats set, and
           manifest.json: the sha256 of the source and the fixture, the team, the player ids and
           the 25 x players values checked. The source's own file is never modified.
  --check  reads a Player.bin and its PlayerAssignment.bin and fails (exit 1) unless every stat
           of every player of the team is 99. It is what the sandbox runs before and after
           installing the fixture.
  --from   a Player.bin to build from, instead of the world's (a copy of your own with the stats
           you want); --world where Player.bin and PlayerAssignment.bin are read from (default:
           FL26_DIR's _FL26MyWorld world).

"Stats" are the ability fields playeredit.ABILITIES knows -- Offensive Awareness, Ball Control,
Dribbling, ... GK Reach -- values 40..99; names, ids, positions, form, injury resistance and the
skills are left alone.

  python tools/futve_fixture.py --make --world "G:\...\_FL26MyWorld\common\etc\pesdb"
  python tools/futve_fixture.py --check out/futve/fixtures/Player.bin
"""
import argparse
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pesdb
import playeredit as E

TEAM = 71606
TEAM_NAME = "Deportivo Táchira"
STATS = [n for n, _b in E.ABILITIES]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load(db, name):
    p = os.path.join(db, name)
    if not os.path.isfile(p):
        raise SystemExit("no %s in %s" % (name, db))
    data = bytearray(pesdb.wesys_unpack(open(p, "rb").read()))
    if len(data) % (E.P_REC if name == "Player.bin" else E.A_REC):
        raise SystemExit("%s is not a whole number of records" % p)
    return p, data


def squad(assigns, team):
    """the player ids the team's assignments name, in squad order"""
    out = []
    for i in range(len(assigns) // E.A_REC):
        o = i * E.A_REC
        if E.u32(assigns, o + E.A_TID) == team:
            out.append((E.u32(assigns, o + E.A_PACK) >> 10, E.u32(assigns, o + E.A_PID)))
    return [p for _o, p in sorted(out)]


def index(players):
    return {E.u32(players, i * E.P_REC + E.P_ID): i * E.P_REC
            for i in range(len(players) // E.P_REC)}


def values(rec):
    v = int.from_bytes(rec, "little")
    return [(v >> b & 63) + 40 for _n, b in E.ABILITIES]


def set_99(rec):
    for name in STATS:
        E.setf(rec, name, 99)


def check_file(players_path, assigns_path, team):
    """(player ids, values checked, offenders): every stat of every player of the team 99"""
    players = bytearray(pesdb.wesys_unpack(open(players_path, "rb").read()))
    assigns = bytearray(pesdb.wesys_unpack(open(assigns_path, "rb").read()))
    ids = squad(assigns, team)
    if not ids:
        raise SystemExit("team %d has no player in %s" % (team, assigns_path))
    idx = index(players)
    bad = []
    n = 0
    for pid in ids:
        o = idx.get(pid)
        if o is None:
            bad.append((pid, "no record"))
            continue
        rec = players[o:o + E.P_REC]
        for name, val in zip(STATS, values(rec)):
            n += 1
            if val != 99:
                bad.append((pid, "%s %d" % (name, val)))
    return ids, n, bad


def make(a):
    world = a.world
    if not world:
        if not a.game:
            raise SystemExit("no world; pass --game / FL26_DIR or --world <pesdb>")
        world = os.path.join(a.game, "SiderAddons", "livecpk", "_FL26MyWorld", "common", "etc", "pesdb")
    src = a.source or os.path.join(world, "Player.bin")
    assigns_path = a.assignments or os.path.join(world, "PlayerAssignment.bin")
    if not os.path.isfile(src) or not os.path.isfile(assigns_path):
        raise SystemExit("no Player.bin / PlayerAssignment.bin in %s" % world)
    players = bytearray(pesdb.wesys_unpack(open(src, "rb").read()))
    if len(players) % E.P_REC:
        raise SystemExit("%s is not a whole number of records" % src)
    assigns = bytearray(pesdb.wesys_unpack(open(assigns_path, "rb").read()))
    ids = squad(assigns, a.team)
    if not ids:
        raise SystemExit("team %d has no player in %s (the world's Táchira is 71606)" % (a.team, assigns_path))
    idx = index(players)
    missing = [p for p in ids if p not in idx]
    if missing:
        raise SystemExit("players of team %d without a record: %s" % (a.team, ", ".join(map(str, missing[:8]))))
    touched = set()
    for pid in ids:
        o = idx[pid]
        rec = bytearray(players[o:o + E.P_REC])
        set_99(rec)
        if values(rec) != [99] * len(STATS):
            raise SystemExit("player %d does not take 99 in every stat" % pid)
        players[o:o + E.P_REC] = rec
        touched.add(o)
    # no other record changed
    src_players = bytearray(pesdb.wesys_unpack(open(src, "rb").read()))
    changed = [i for i in range(0, len(players), E.P_REC)
               if players[i:i + E.P_REC] != src_players[i:i + E.P_REC]]
    if any(i not in touched for i in changed):
        raise SystemExit("a player other than the team's changed; refusing to write")
    os.makedirs(a.out, exist_ok=True)
    out = os.path.join(a.out, "Player.bin")
    with open(out, "wb") as f:
        f.write(pesdb.wesys_pack(bytes(players)))
    man = {"team": a.team, "team_name": TEAM_NAME, "players": ids, "stats": STATS,
           "values": len(ids) * len(STATS), "source": os.path.abspath(src),
           "source_sha256": sha(src), "fixture": os.path.abspath(out), "fixture_sha256": sha(out),
           "assignments": os.path.abspath(assigns_path), "assignments_sha256": sha(assigns_path),
           "made": time.strftime("%Y-%m-%dT%H:%M:%S")}
    with open(os.path.join(a.out, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(man, f, indent=2)
    _ids, n, bad = check_file(out, assigns_path, a.team)
    print("fixture: %s" % out)
    print("  team %d (%s): %d players, %d stats values, %s"
          % (a.team, TEAM_NAME, len(ids), n, "all 99" if not bad else "%d NOT 99" % len(bad)))
    print("  source %s" % src)
    print("  source sha256 %s" % man["source_sha256"])
    print("  fixture sha256 %s" % man["fixture_sha256"])
    return 0 if not bad else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game", default=os.environ.get("FL26_DIR"))
    ap.add_argument("--world")
    ap.add_argument("--from", dest="source")
    ap.add_argument("--assignments")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(HERE), "out", "futve", "fixtures"))
    ap.add_argument("--team", type=int, default=TEAM)
    ap.add_argument("--make", action="store_true")
    ap.add_argument("--check", metavar="PLAYER_BIN")
    a = ap.parse_args()
    if a.check:
        assigns = a.assignments
        if not assigns:
            world = a.world or os.path.join(a.game or "", "SiderAddons", "livecpk", "_FL26MyWorld",
                                            "common", "etc", "pesdb")
            assigns = os.path.join(world, "PlayerAssignment.bin")
        if not os.path.isfile(assigns):
            raise SystemExit("no PlayerAssignment.bin at %s; pass --assignments" % assigns)
        ids, n, bad = check_file(a.check, assigns, a.team)
        print("team %d: %d players, %d stats values, %s" % (a.team, len(ids), n,
                                                            "all 99" if not bad else "%d NOT 99" % len(bad)))
        for pid, why in bad[:20]:
            print("  player %d: %s" % (pid, why))
        return 0 if not bad else 1
    if a.make:
        return make(a)
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
