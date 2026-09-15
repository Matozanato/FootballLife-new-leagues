"""python mkplayers.py --base <pesdb dir> --out <livecpk root> [--per 23] [--clubs N]

Give the new placeholder clubs placeholder squads, so their matches can be played.

mkworld.py builds clubs and leagues, and the game invents a manager for every club that
lacks one -- but nothing invents players.  A season in a new league therefore runs its
calendar and forfeits every match:

    You have lost the match through default as you do not have the minimum number of
    players needed in order to field a side.

Two tables fix that, and this writes both:

  Player.bin            312 bytes.  Player id at +0x08, then four name slots of 0x3d bytes
                        from +0x44: full name, the name on the shirt, the name on screen,
                        and the printed name.  Everything else -- position, abilities,
                        playing style -- is what makes a player able to take the field, so
                        rather than invent numbers this clones a shipped squad and renames
                        it.  The clone keeps a legal spread of positions and a goalkeeper,
                        which a squad of copies of one player would not.

  PlayerAssignment.bin  16 bytes.  A unique entry id at +0x00, the player at +0x04, the club
                        at +0x08, and at +0x0c a packed field: the squad order in bits 10
                        and up, the shirt number in bits 0-9.  Shipped squads run 19 to 30
                        players, order 0 upward, and that is the shape copied here.

The ceiling is the player array.  It begins at offset 0 of the edit block, so every access
to it carries no displacement to rewrite and it cannot be relocated the way the team and
coach arrays were.  It does not have to be, though: once the teams have been relocated out
of the way, it can grow in place into the space they leave, as far as the regulation array
above it.  So the cap depends on the patch set that is installed, and `--cap` says which:

    unpatched, or teams-coaches:   30001, less 27927 shipped =  2074 =  90 squads of 23
    teams-coaches-players:         33314, less 27927 shipped =  5387 = 234 squads of 23

This fills clubs in order and stops when the budget runs out rather than writing a file the
game will refuse.
"""
import os, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pesdb

P_REC = 312
P_ID = 0x08
P_NAME, P_NAME_LEN, P_NAME_SLOTS = 0x44, 0x3d, 4

A_REC = 16
A_EID, A_PID, A_TID, A_PACK = 0x00, 0x04, 0x08, 0x0c

T_REC, T_ID = 1532, 0x08

PLAYER_CAP = 30001      # the shipped cap; --cap raises it to match the patch set


def load(d, n):
    return bytearray(pesdb.wesys_unpack(open(os.path.join(d, n), "rb").read()))


def put(b, off, s, n):
    v = s.encode("utf-8")[:n - 1]
    b[off:off + n] = v + b"\0" * (n - len(v))


def club_ids(raw):
    return [int.from_bytes(raw[i * T_REC + T_ID:i * T_REC + T_ID + 4], "little")
            for i in range(len(raw) // T_REC)]


def main():
    a = sys.argv[1:]
    get = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    base, out = get("--base"), get("--out")
    if not base or not out:
        print(__doc__)
        return 1
    per = int(get("--per", "23"))
    want = int(get("--clubs", "0"))
    pname = get("--player-name", "FL P%05d")
    cap = int(get("--cap", str(PLAYER_CAP)))

    outdb = os.path.join(out, "common", "etc", "pesdb")
    players = load(base, "Player.bin")
    assigns = load(base, "PlayerAssignment.bin")
    old = club_ids(load(base, "Team.bin"))
    new = club_ids(load(outdb, "Team.bin"))
    fresh = [c for c in new if c not in set(old)]
    nplayer = len(players) // P_REC
    print("base: %d players, %d assignments, %d clubs; %d new clubs in the root"
          % (nplayer, len(assigns) // A_REC, len(old), len(fresh)))

    # the prototype squad: a shipped club with at least `per` players, cloned whole so the
    # new squad keeps its positions, its goalkeeper and its shirt numbers
    by_club = collections.defaultdict(list)
    for i in range(len(assigns) // A_REC):
        r = assigns[i * A_REC:(i + 1) * A_REC]
        by_club[int.from_bytes(r[A_TID:A_TID + 4], "little")].append(
            (int.from_bytes(r[A_PID:A_PID + 4], "little"),
             int.from_bytes(r[A_PACK:A_PACK + 4], "little")))
    proto_club = next((c for c in sorted(by_club) if len(by_club[c]) >= per), None)
    if proto_club is None:
        raise SystemExit("no shipped club has %d players to copy" % per)
    proto = by_club[proto_club][:per]
    index = {int.from_bytes(players[i * P_REC + P_ID:i * P_REC + P_ID + 4], "little"): i
             for i in range(nplayer)}
    print("prototype squad: club %d, %d of its %d players"
          % (proto_club, per, len(by_club[proto_club])))

    room = cap - nplayer
    fit = room // per
    if want:
        fit = min(fit, want)
    if fit < len(fresh):
        print("player cap %d leaves room for %d more, so %d of the %d new clubs get squads"
              % (cap, room, fit, len(fresh)))
    fresh = fresh[:fit]
    if not fresh:
        raise SystemExit("no room for even one squad")

    pid = max(index) + 1
    eid = max(int.from_bytes(assigns[i * A_REC + A_EID:i * A_REC + A_EID + 4], "little")
              for i in range(len(assigns) // A_REC)) + 1
    made = 0
    for club in fresh:
        for src_pid, pack in proto:
            r = bytearray(players[index[src_pid] * P_REC:(index[src_pid] + 1) * P_REC])
            r[P_ID:P_ID + 4] = pid.to_bytes(4, "little")
            nm = pname % (made + 1)
            for k in range(P_NAME_SLOTS):
                put(r, P_NAME + k * P_NAME_LEN, nm, P_NAME_LEN)
            players += r
            e = bytearray(A_REC)
            e[A_EID:A_EID + 4] = eid.to_bytes(4, "little")
            e[A_PID:A_PID + 4] = pid.to_bytes(4, "little")
            e[A_TID:A_TID + 4] = club.to_bytes(4, "little")
            e[A_PACK:A_PACK + 4] = pack.to_bytes(4, "little")
            assigns += e
            pid += 1
            eid += 1
            made += 1
    os.makedirs(outdb, exist_ok=True)
    for n, b in (("Player.bin", players), ("PlayerAssignment.bin", assigns)):
        open(os.path.join(outdb, n), "wb").write(pesdb.wesys_pack(bytes(b)))
    print("  wrote Player.bin (%d records)" % (len(players) // P_REC))
    print("  wrote PlayerAssignment.bin (%d records)" % (len(assigns) // A_REC))
    print("\n%d clubs given %d players each; %d players in all (cap %d)"
          % (len(fresh), per, len(players) // P_REC, cap))
    return 0


if __name__ == "__main__":
    sys.exit(main())
