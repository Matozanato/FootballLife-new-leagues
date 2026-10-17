r"""python checkratings.py <world> [--old <previous world, pesdb folder or Player.bin>]
                       [--stars <file>] [--max 90] [--rise 8] [--all]

A hard check of the player ratings of a built world, for step 2 (checks) before any world zip
(Modpack, NewLife) is exported. Twice in one week a world went out with inflated ratings that
testers found and our checks (ids, kits, crests) did not: NewLife 1.5b5 (B64, Ryan Sessegnon
speed 99, ball control 91, ~100 in the game instead of ~75) and the Europe Modpack eu1, which
still had those ratings.

<world> is a world folder (livecpk\_FL26...), its common\etc\pesdb folder, or a Player.bin.

Rule A  no player the world wrote has an overall of --max (90) or more, unless his player id is
        in the stars list (--stars, default checkratings_stars.txt next to this file: one id per
        line, a # comment after it with the name). "The world wrote" is:
          - every player of a new club: a club id above the game's last (GAME_LAST_TID), or a
            club of the recipe's leagues (leaguebuilder-plan.json) that is not one of the game's
            clubs it keeps;
          - every player id above the game's last (GAME_LAST_PID): a player the world added,
            whatever club he is at (a NewLife player joined to a club of the game);
          - every game player whose record the recipe rewrites (leaguebuilder-plan.json
            "players" -> <game club id> -> "edits"): the NewLife refresh of the game's own
            leagues, where B64 was (Sessegnon, Fulham).
        Players the world leaves as the game ships them (the classics, the national teams' stars)
        are not held to it: the game rates them, not us.
Rule B  with --old: no player (the same player id and the same name in both; an id that now
        names someone else is skipped and counted) rose by more than --rise (8) overall points.
        A player whose position changed rose by the smaller of the rises at his position now
        and at his position then (rise()), so a move (an outfield player made a keeper) is not
        a rise, and abilities that went up everywhere are.

The summary: how many players, how many the world wrote, how many of each are 80+, 85+, 90+,
and the 15 best of each by overall, with name and club.

Exit code 0: pass. 1: fail, with the list of offenders (the first 50; --all lists every one).

The overall: the game's own formula is not known, and lbplayers.overall (the builder's rough one,
the plain mean of six abilities) puts Sessegnon at 70 in the good world and 83 in the bad one --
a 90 line never sees him. So this is an estimate of the number the game shows:

    m       = the mean of the abilities his registered position leans on (GROUPS below: GK, CB,
              full back, DMF, CMF, wide, AMF/SS, CF)
    overall = 80 + 1.5 * (m - TOP[group])

TOP[group] is the m of the shipped game's top 1% at that kind of position (its 99th percentile,
measured on C:\work\fl26base\ex_merged, the 19,420 players with a team), so the game's top 1%
at every position is 80 and up -- a keeper's or a centre back's abilities run higher than a full
back's, and the same m is a different player there. 1.5 overall points to an ability point is
the slope that matches what testers saw in the game: Ryan Sessegnon (LB) ~75 in Modpack r10
(m 76.8 -> 76) and ~100 in eu1, where every ability of his was 14 higher (m 90.1 -> 96). On the
shipped tables it gives Rodri 87, Van Dijk 86, Vinicius 86, Messi 84, Haaland 83, Alisson 81,
Mbappe 80. It may go past 99 (the game stops at 99) and is only meant for the top of the scale.
"""
import os
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pesdb
import playeredit as E

# the shipped tables' last ids (C:\work\fl26base\ex_merged, 27,927 players, 743 clubs, 2026-10-17):
# a world's own clubs and players are numbered after them
GAME_LAST_PID = 179672
GAME_LAST_TID = 71577
T_NATIONAL = 0x53          # Team.bin: top bit set on the national teams (lbplayers.T_NATIONAL)

MAX_OVR, MAX_RISE = 90, 8
STARS = os.path.join(HERE, "checkratings_stars.txt")
SHOW = 50

GROUPS = {
    "GK": ["GK Awareness", "GK Catching", "GK Clearing", "GK Reflexes", "GK Reach"],
    "CB": ["Defensive Awareness", "Ball Winning", "Aggression", "Physical Contact", "Heading",
           "Jump", "Speed"],
    "FB": ["Speed", "Acceleration", "Stamina", "Defensive Awareness", "Ball Winning", "Low Pass",
           "Lofted Pass", "Ball Control", "Dribbling", "Physical Contact"],
    "DMF": ["Defensive Awareness", "Ball Winning", "Low Pass", "Lofted Pass", "Stamina",
            "Physical Contact", "Ball Control", "Aggression"],
    "CMF": ["Low Pass", "Lofted Pass", "Ball Control", "Dribbling", "Tight Possession", "Stamina",
            "Offensive Awareness", "Ball Winning"],
    "WIDE": ["Speed", "Acceleration", "Dribbling", "Ball Control", "Tight Possession", "Low Pass",
             "Lofted Pass", "Curl", "Offensive Awareness", "Finishing"],
    "AMF": ["Offensive Awareness", "Ball Control", "Dribbling", "Tight Possession", "Low Pass",
            "Finishing", "Curl", "Acceleration"],
    "CF": ["Offensive Awareness", "Finishing", "Ball Control", "Dribbling", "Speed", "Acceleration",
           "Kicking Power", "Heading", "Physical Contact"],
}
GROUP_OF = {"GK": "GK", "CB": "CB", "LB": "FB", "RB": "FB", "DMF": "DMF", "CMF": "CMF",
            "LMF": "WIDE", "RMF": "WIDE", "LWF": "WIDE", "RWF": "WIDE", "AMF": "AMF", "SS": "AMF",
            "CF": "CF"}
# the m of the shipped game's top 1% (99th percentile) at each kind of position, and its overall
TOP = {"GK": 90.6, "CB": 85.7, "FB": 79.5, "DMF": 83.4, "CMF": 82.0, "WIDE": 82.9, "AMF": 86.5,
       "CF": 84.8}
TOP_OVR, SLOPE = 80, 1.5

_BIT = {n: b for n, b in E.ABILITIES}
_POS_BIT, _POS_W = E.FIELDS["Registered Position"][:2]


def position(v):
    """registered position of a record (as one int); an unknown one counts as CF, as lbplayers"""
    r = v >> _POS_BIT & ((1 << _POS_W) - 1)
    return E.POSITIONS[r] if r < len(E.POSITIONS) else "CF"


def ability(v, name):
    return (v >> _BIT[name] & 63) + 40


def overall(v, pos=None):
    """the estimated overall of a player record (int.from_bytes of the 312 bytes), at pos
    (default: his registered position)"""
    pos = pos or position(v)
    g = GROUP_OF.get(pos, "CF")
    m = sum(ability(v, n) for n in GROUPS[g]) / float(len(GROUPS[g]))
    return int(round(TOP_OVR + SLOPE * (m - TOP[g])))


def rise(v, ov):
    """(how much a player rose from record ov to record v, his overall then): the smaller of the
    rises at his position now and at his position then, so a move to another position (an
    outfield player made a keeper, whose keeping abilities were 40) is not a rise, and abilities
    that went up everywhere are; the overall then is at his position now"""
    now, then = position(v), position(ov)
    was = overall(ov, now)
    d = overall(v, now) - was
    if then != now:
        d = min(d, overall(v, then) - overall(ov, then))
    return d, was


def _unpack(raw):
    return pesdb.wesys_unpack(raw) if raw[3:8] == b"WESYS" else raw


def pesdb_dir(where):
    """the folder holding Player.bin for a world folder, a pesdb folder or a Player.bin"""
    if os.path.isfile(where):
        return os.path.dirname(os.path.abspath(where))
    for d in (os.path.join(where, "common", "etc", "pesdb"), where):
        if os.path.isfile(os.path.join(d, "Player.bin")):
            return d
    raise SystemExit("no Player.bin in %s (nor in its common\\etc\\pesdb)" % where)


def world_root(db):
    """the world folder above a pesdb folder, if it is one (it has leaguebuilder-plan.json)"""
    up = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(db))))
    return up if os.path.isfile(os.path.join(up, "leaguebuilder-plan.json")) else None


class Table:
    """the players of a set of tables: {pid: (record int, name)}, their clubs and club names"""

    def __init__(self, where, player_bin=None):
        self.db = pesdb_dir(where)
        pb = player_bin or (where if os.path.isfile(where) else os.path.join(self.db, "Player.bin"))
        raw = _unpack(open(pb, "rb").read())
        if len(raw) % E.P_REC:
            raise SystemExit("%s is not a whole number of player records" % pb)
        self.players = {}
        for o in range(0, len(raw), E.P_REC):
            rec = raw[o:o + E.P_REC]
            self.players[E.u32(rec, E.P_ID)] = (int.from_bytes(rec, "little"),
                                                E.cstr(rec[E.P_NAME:E.P_NAME + E.P_NAME_LEN]))
        self.teams, self.national = {}, set()
        tp = os.path.join(self.db, "Team.bin")
        if os.path.isfile(tp):
            t = _unpack(open(tp, "rb").read())
            for o in range(0, len(t) - E.T_REC + 1, E.T_REC):
                tid = E.u32(t, o + E.T_ID)
                self.teams[tid] = E.cstr(t[o + E.T_NAME:o + E.T_NAME + E.T_NAME_LEN])
                if t[o + T_NATIONAL] & 0x80:
                    self.national.add(tid)
        self.club = {}      # pid -> his club (a national team only when he has no club)
        ap = os.path.join(self.db, "PlayerAssignment.bin")
        if os.path.isfile(ap):
            a = _unpack(open(ap, "rb").read())
            for o in range(0, len(a) - E.A_REC + 1, E.A_REC):
                pid, tid = E.u32(a, o + E.A_PID), E.u32(a, o + E.A_TID)
                if pid not in self.club or (self.club[pid] in self.national and tid not in self.national):
                    self.club[pid] = tid

    def club_name(self, pid):
        tid = self.club.get(pid)
        if tid is None:
            return "(no club)"
        return self.teams.get(tid) or str(tid)


def world_scope(table):
    """(new club ids, {pid: why} of the players the world wrote)"""
    new_clubs = {t for t in table.teams if GAME_LAST_TID < t}
    edited = set()
    root = world_root(table.db)
    if root:
        plan = json.load(open(os.path.join(root, "leaguebuilder-plan.json"), encoding="utf-8"))
        for L in (plan.get("leagues") or []) + (plan.get("others") or []):
            gc = L.get("game_clubs") or {}
            kept = {int(e["id"]) for e in (gc.values() if isinstance(gc, dict) else gc)
                    if isinstance(e, dict) and str(e.get("id", "")).isdigit()}
            new_clubs |= {int(t) for t in (L.get("teams") or []) if int(t) not in kept}
        for key, c in (plan.get("players") or {}).items():
            if key.isdigit() and isinstance(c, dict):
                edited |= {int(p) for p in (c.get("edits") or {}) if str(p).isdigit()}
    why = {}
    for pid in table.players:
        if table.club.get(pid) in new_clubs:
            why[pid] = "new club"
        elif pid > GAME_LAST_PID:
            why[pid] = "added player"
        elif pid in edited:
            why[pid] = "rewritten game player"
    return new_clubs, why


def read_stars(path):
    """{pid} of the stars list: the first number of each line, # starts a comment"""
    out = set()
    if path and os.path.isfile(path):
        for line in open(path, encoding="utf-8"):
            s = line.split("#", 1)[0].strip()
            if s:
                tok = s.split()[0]
                if not tok.isdigit():
                    raise SystemExit("%s: %r is not a player id" % (path, line.strip()))
                out.add(int(tok))
    elif path and path != STARS:
        raise SystemExit("no stars list %s" % path)
    return out


def same_name(a, b):
    return " ".join(a.casefold().split()) == " ".join(b.casefold().split())


def check(world, old=None, stars=STARS, max_ovr=MAX_OVR, max_rise=MAX_RISE, show=SHOW, out=print):
    """run both rules; returns (passed, {"a": [...], "b": [...]}); prints the report via out"""
    T = Table(world)
    _new, why = world_scope(T)
    allow = read_stars(stars)
    ovr = {pid: overall(v) for pid, (v, _n) in T.players.items()}
    line = lambda pid: "%7d  %-28s %-4s %3d  %s" % (pid, T.players[pid][1][:28], position(T.players[pid][0]),
                                                   ovr[pid], T.club_name(pid))

    out("checkratings: %s" % T.db)
    out("players %d, written by the world %d (new clubs %d, added %d, rewritten game players %d)"
        % (len(T.players), len(why), sum(1 for w in why.values() if w == "new club"),
           sum(1 for w in why.values() if w == "added player"),
           sum(1 for w in why.values() if w == "rewritten game player")))
    for label, ids in (("all", list(T.players)), ("world's", list(why))):
        out("  %-8s 80+ %5d   85+ %5d   90+ %5d" % (label, sum(ovr[p] >= 80 for p in ids),
                                                    sum(ovr[p] >= 85 for p in ids), sum(ovr[p] >= 90 for p in ids)))
    for label, ids in (("all players", list(T.players)), ("the world's players", list(why))):
        out("top 15, %s:" % label)
        for pid in sorted(ids, key=lambda p: (-ovr[p], p))[:15]:
            out("  " + line(pid) + ("" if pid not in why else "   [%s]" % why[pid]))

    fails = {"a": [], "b": []}
    for pid in sorted(why, key=lambda p: (-ovr[p], p)):
        if ovr[pid] >= max_ovr and pid not in allow:
            fails["a"].append(pid)
    starred = sorted(p for p in why if ovr[p] >= max_ovr and p in allow)
    out("rule A (world's players under %d, %d on the stars list): %s"
        % (max_ovr, len(starred), "FAIL, %d players" % len(fails["a"]) if fails["a"] else "pass"))
    for pid in fails["a"][:show]:
        out("  " + line(pid) + "   [%s]" % why[pid])
    if len(fails["a"]) > show:
        out("  ... and %d more (--all lists every one)" % (len(fails["a"]) - show))

    if old:
        O = Table(old)
        same = renamed = 0
        rises = []
        for pid, (v, name) in T.players.items():
            if pid not in O.players:
                continue
            ov, oname = O.players[pid]
            if not same_name(name, oname):
                renamed += 1
                continue
            same += 1
            d, was = rise(v, ov)
            if d > max_rise:
                rises.append((d, pid, was))
        rises.sort(key=lambda r: (-r[0], r[1]))
        fails["b"] = [r[1] for r in rises]
        out("rule B (no rise over %d against %s; %d players compared, %d ids now name someone "
            "else): %s" % (max_rise, O.db, same, renamed,
                           "FAIL, %d players" % len(rises) if rises else "pass"))
        for d, pid, was in rises[:show]:
            out("  " + line(pid) + "   was %d, +%d" % (was, d))
        if len(rises) > show:
            out("  ... and %d more (--all lists every one)" % (len(rises) - show))

    passed = not fails["a"] and not fails["b"]
    out("checkratings: %s" % ("PASS" if passed else "FAIL"))
    return passed, fails


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = list(argv)
    get = lambda k, d=None: a[a.index(k) + 1] if k in a and a.index(k) + 1 < len(a) else d
    pos = [x for i, x in enumerate(a) if not x.startswith("--") and (i == 0 or a[i - 1] not in
                                                                      ("--old", "--stars", "--max", "--rise"))]
    if len(pos) != 1:
        raise SystemExit(__doc__)
    passed, _ = check(pos[0], old=get("--old"), stars=get("--stars", STARS),
                      max_ovr=int(get("--max", MAX_OVR)), max_rise=int(get("--rise", MAX_RISE)),
                      show=10 ** 9 if "--all" in a else SHOW)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
