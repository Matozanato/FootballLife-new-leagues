r"""python checktwins.py <world> <the game's tables> [--all]

A hard check for the same man twice in a built world, for step 2 (checks) before any world zip
(GigaPack, NewLife) is exported, and after a Build of our own.

B421 (11.11.2026, Reddit r/SPFootballLife, "Duplicate Players for FL Studio": "many duplicate
players" -- the same name and nation, one with his real face and one with a wrong one -- and
"top players without clubs"). A world's data and the game spell some names apart ("Marc-Andre ter
Stegen" and the game's "M. ter Stegen"): Build made the data's player a new one (a new id, a
made face) and the game's lost his club. NewLife 1.6b4 on FL 2027 had some 230 such pairs, and
no check of ours looked: release.py asks for doubled ids only.

<world> is a world folder (livecpk\_FL26...), its common\etc\pesdb folder or a Player.bin;
<the game's tables> the same of the game the world was built for.

A pair is a player the world added (an id the game has not got) at a club, and a player of the
game, who are one man by more than the name (lbplayers.loose_name, as newlife.game_twin's second
pass): the same nationality, an age a year apart at most, on the same side of the goalkeeper line,
and
  - the game has its player at the very club the world has the added one at (a height 3 cm apart
    at most, one such player there), or
  - a height a centimetre apart at most and the same name, a name cut short or with a part left
    out (not a single word of it, not another first name);
one player of the game and one of the world so. The game's classics and default squads are
nobody's twin.

FAIL  the game's player of a pair has no club in the world, or is in the same squad as the added
      one: the same man twice, one of them a free agent or a team-mate of himself.
NOTE  the game's player of a pair is at another club: maybe one man at two clubs, maybe a
      namesake -- listed, not failed (the data has to say which).
NOTE  the game's players of 75 and more who had a club in the game and have none in the world,
      the best first: who the world let go.

Exit code 0: pass. 1: fail, with the pairs (the first 50; --all lists every one).
"""
import os
import re
import sys
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import checkratings as C
import lbplayers as P
import playeredit as E

SHOW = 50
TOP = 75                   # "top players without clubs": the overall from which a lost club is listed
FILLER = re.compile(r"^FL P\d+$")          # a prototype player nobody named


def special_team(name):
    """leaguebuilder.special_team: the Master League's default squads, the classic teams and the
    all-star selection"""
    n = (name or "").strip()
    return n.startswith("ML Default") or n.endswith(" Classics") or n == "World Selection"


def _num(v, f):
    bit, width, add = E.FIELDS[f][:3]
    return (v >> bit & ((1 << width) - 1)) + add


def _words(name):
    return {w for w in map(P._letters, P._words(name)) if len(w) >= 3}


def find(world, game):
    """(twice, maybe, lost) of two checkratings.Table: twice and maybe [(the game's id, the
    added id)], lost [the game's ids] who had a club in the game and have none in the world"""
    club = lambda t, pid: t.club.get(pid) if t.club.get(pid) not in t.national else None
    size = lambda v: (_num(v, "Age"), _num(v, "Height (cm)"))
    pool = collections.defaultdict(list)
    for pid, (v, name) in game.players.items():
        if pid not in world.players or special_team(game.teams.get(game.club.get(pid))):
            continue
        for w in _words(name):
            pool[(_num(v, "Nationality"), w)].append(pid)
    claims = collections.defaultdict(list)
    for pid, (v, name) in world.players.items():
        here = club(world, pid)
        if pid in game.players or here is None or FILLER.match(name):
            continue
        age, cm = size(v)
        fit = []
        for p in {p for w in _words(name) for p in pool.get((_num(v, "Nationality"), w), ())}:
            gv, gname = game.players[p]
            a, c = size(gv)
            if abs(a - age) > 1 or abs(c - cm) > 3 or P.keeper_side(C.position(v), C.position(gv)):
                continue
            kind = P.loose_name(name, gname)
            if kind:
                fit.append((p, kind, abs(c - cm)))
        at = [p for p, _k, _d in fit if club(game, p) == here]
        if len(at) == 1:
            claims[at[0]].append((pid, True))
        elif not at and len(fit) == 1 and fit[0][1] in ("same", "part", "initial") and fit[0][2] <= 1:
            claims[fit[0][0]].append((pid, False))
    twice, maybe = [], []
    for p, c in claims.items():
        c = [x for x in c if x[1]] if sum(1 for x in c if x[1]) == 1 else c
        if len(c) != 1:
            continue
        mine = club(world, p)
        (twice if mine is None or mine == club(world, c[0][0]) else maybe).append((p, c[0][0]))
    lost = [p for p in game.players if p in world.players and club(game, p) is not None and club(world, p) is None
            and not special_team(game.teams.get(game.club.get(p)))]
    return twice, maybe, lost


def check(world, game, show=SHOW, out=print):
    """(passed, the failing pairs) of a world against the game's tables"""
    w, g = C.Table(world), C.Table(game)
    twice, maybe, lost = find(w, g)
    over = lambda t, p: C.overall(t.players[p][0])
    line = lambda p, a: "   %2d  %-26s %-24s | %-26s %-24s  age %d/%d  cm %d/%d  (%d, %d)" % (
        over(w, p), w.players[p][1][:26], w.club_name(p)[:24], w.players[a][1][:26], w.club_name(a)[:24],
        _num(w.players[p][0], "Age"), _num(w.players[a][0], "Age"),
        _num(w.players[p][0], "Height (cm)"), _num(w.players[a][0], "Height (cm)"), p, a)
    added = sum(1 for p in w.players if p not in g.players)
    out("world %s: %d players, %d of them added to the game's %d" % (w.db, len(w.players), added, len(g.players)))
    for title, pairs in (("FAIL  the same man twice (the game's player without a club, or beside the added one)", twice),
                         ("NOTE  maybe the same man at two clubs", maybe)):
        pairs.sort(key=lambda x: -over(w, x[0]))
        out("%s: %d" % (title, len(pairs)))
        for p, a in pairs[:show]:
            out(line(p, a))
        if len(pairs) > show:
            out("   ... and %d more (--all lists them)" % (len(pairs) - show))
    top = sorted((p for p in lost if over(g, p) >= TOP), key=lambda p: -over(g, p))
    out("NOTE  the game's players who had a club and have none in the world: %d, %d of them %d and more" % (len(lost), len(top), TOP))
    for p in top[:min(show, 15)]:
        out("   %2d  %-26s was at %s  (%d)" % (over(g, p), g.players[p][1][:26], g.club_name(p), p))
    out("checktwins: %s" % ("PASS" if not twice else "FAIL, %d pair(s) of one man twice" % len(twice)))
    return not twice, twice


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    pos = [x for x in argv if not x.startswith("--")]
    if len(pos) != 2:
        raise SystemExit(__doc__)
    passed, _ = check(pos[0], pos[1], show=10 ** 9 if "--all" in argv else SHOW)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
