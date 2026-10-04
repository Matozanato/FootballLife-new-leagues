"""python mkswiss.py [outfile]  -> the draw table for a 36-club league phase

Builds and verifies the fixture set that `fl26swiss.dll` installs for a modern UEFA league
phase (Champions League and Europa League since 2024): one table of 36 clubs, each club
playing 8 of the other 35.

The engine cannot express this (docs/league-phase-swiss-decode.md): a league regulation always
plays a complete round robin, so the pairings have to be handed to it. This script produces
them, checks every property that matters, and writes a C header the DLL compiles in. It reads
nothing from the game.

Construction

  Clubs are addressed by their position in the regulation's club list, 0..35, and the pot of a
  club is its position divided by nine -- so the list is expected in seeding order, pot 1 first.
  Position p is mapped to a ring index c = (p mod 9) * 4 + (p div 9), which makes the pot equal
  to c mod 4. Opponents are the ring neighbours at distance 1, 2, 3 and 4, which gives every
  club eight opponents and, because the four distances cover the residues 0..3 twice over,
  exactly two opponents from each pot.

  Those 144 matches are then coloured into 8 rounds by backtracking, so that each round is a
  perfect matching of all 36 clubs. Home advantage comes from an Eulerian orientation of the
  same graph: every club has even degree, so orienting along Euler circuits gives each club
  exactly four home matches and four away.

  Finally each round is split into two matchdays of nine matches. A fixture record holds 16
  match slots and silently drops the rest, and a round of 36 clubs is 18 matches, so the split
  is what keeps the competition inside the shipped record. It costs one extra date per round.

Determinism: the edge order, the colouring search and the Euler walk are all fixed, so two runs
produce byte-identical output.
"""
import collections
import sys

N = 36
DISTANCES = (1, 2, 3, 4)
ROUNDS = 8
MATCHES_PER_MATCHDAY = 9


def ring_edges():
    """The opponent graph, as pairs of ring indices."""
    return sorted({(min(c, (c + d) % N), max(c, (c + d) % N))
                   for c in range(N) for d in DISTANCES})


def one_factorization(edges):
    """Colour the edges with ROUNDS colours so every club sees each colour once."""
    colour = [-1] * len(edges)
    used = [[False] * ROUNDS for _ in range(N)]

    def pick():
        best, best_n = None, ROUNDS + 1
        for i, (a, b) in enumerate(edges):
            if colour[i] != -1:
                continue
            n = sum(1 for c in range(ROUNDS) if not used[a][c] and not used[b][c])
            if n < best_n:
                best, best_n = i, n
                if n <= 1:
                    break
        return best

    def solve():
        i = pick()
        if i is None:
            return True
        a, b = edges[i]
        for c in range(ROUNDS):
            if used[a][c] or used[b][c]:
                continue
            colour[i] = c
            used[a][c] = used[b][c] = True
            if solve():
                return True
            colour[i] = -1
            used[a][c] = used[b][c] = False
        return False

    if not solve():
        raise SystemExit("no round assignment exists for this opponent graph")
    out = collections.defaultdict(list)
    for i, c in enumerate(colour):
        out[c].append(edges[i])
    return out


def euler_orientation(edges):
    """Orient every edge so each club is home exactly half the time."""
    inc = collections.defaultdict(list)
    for i, (a, b) in enumerate(edges):
        inc[a].append((b, i))
        inc[b].append((a, i))
    spent = [False] * len(edges)
    orient = {}
    for start in range(N):
        stack, walk = [start], []
        while stack:
            v = stack[-1]
            while inc[v] and spent[inc[v][-1][1]]:
                inc[v].pop()
            if not inc[v]:
                walk.append(stack.pop())
                continue
            u, ei = inc[v][-1]
            spent[ei] = True
            stack.append(u)
        for i in range(len(walk) - 1):
            home, away = walk[i + 1], walk[i]
            key = (min(home, away), max(home, away))
            orient.setdefault(key, (home, away))
    return orient


def build():
    to_position = lambda c: (c % 4) * 9 + (c // 4)
    rounds = one_factorization(ring_edges())
    by_round = [sorted((min(to_position(a), to_position(b)),
                        max(to_position(a), to_position(b)))
                       for a, b in rounds[r]) for r in range(ROUNDS)]
    orient = euler_orientation([e for rnd in by_round for e in rnd])

    table = []
    for r, rnd in enumerate(by_round):
        for k, edge in enumerate(rnd):
            home, away = orient[edge]
            table.append((2 * r + k // MATCHES_PER_MATCHDAY, home, away))
    table.sort()
    return table


def check(table):
    assert len(table) == N * ROUNDS // 2, len(table)
    opponents = collections.defaultdict(set)
    home_count = collections.Counter()
    pot_count = {v: [0, 0, 0, 0] for v in range(N)}
    per_matchday = collections.defaultdict(set)
    for md, home, away in table:
        assert home not in per_matchday[md] and away not in per_matchday[md], \
            "club plays twice on matchday %d" % md
        per_matchday[md].update((home, away))
        opponents[home].add(away)
        opponents[away].add(home)
        home_count[home] += 1
        pot_count[home][away // 9] += 1
        pot_count[away][home // 9] += 1
    assert set(len(v) for v in opponents.values()) == {ROUNDS}, "opponent count"
    assert set(home_count[v] for v in range(N)) == {ROUNDS // 2}, "home/away balance"
    assert all(pot_count[v] == [2, 2, 2, 2] for v in range(N)), "pot balance"
    assert set(len(v) for v in per_matchday.values()) == {MATCHES_PER_MATCHDAY * 2}, "matchday size"
    return len(per_matchday)


# ---- the Conference League: six pots of six, one opponent from each, six matches ----
#
# Pot = list position / 6. Five rounds pair the pots by the 1-factorisation of K6 (pot 5 fixed,
# the other five rotating), club k of one pot meeting club k+r+1 of the other; the sixth round
# is inside each pot. So every club meets exactly one club of every pot, its own included, and
# every round is a perfect matching of all 36. Home and away come from the same Euler walk,
# three each. Each round of 18 is split into two matchdays of 9, like the eight-round table.
POTS6 = 6


def build6():
    pos = lambda pot, k: pot * POTS6 + k
    rounds = []
    for r in range(5):
        pairs = [(5, r)] + [((r + d) % 5, (r - d) % 5) for d in (1, 2)]
        rnd = []
        for a, b in pairs:
            for k in range(POTS6):
                x, y = pos(a, k), pos(b, (k + r + 1) % POTS6)
                rnd.append((min(x, y), max(x, y)))
        rounds.append(sorted(rnd))
    rounds.append(sorted((pos(t, 2 * i), pos(t, 2 * i + 1)) for t in range(POTS6) for i in range(3)))
    orient = euler_orientation([e for rnd in rounds for e in rnd])
    table = []
    for r, rnd in enumerate(rounds):
        for k, edge in enumerate(rnd):
            home, away = orient[edge]
            table.append((2 * r + k // MATCHES_PER_MATCHDAY, home, away))
    table.sort()
    return table


def check6(table):
    assert len(table) == N * 6 // 2, len(table)
    opponents = collections.defaultdict(set)
    home_count = collections.Counter()
    pot_count = {v: [0] * POTS6 for v in range(N)}
    per_matchday = collections.defaultdict(set)
    for md, home, away in table:
        assert home not in per_matchday[md] and away not in per_matchday[md], md
        per_matchday[md].update((home, away))
        opponents[home].add(away)
        opponents[away].add(home)
        home_count[home] += 1
        pot_count[home][away // POTS6] += 1
        pot_count[away][home // POTS6] += 1
    assert set(len(v) for v in opponents.values()) == {6}, "opponent count"
    assert set(home_count[v] for v in range(N)) == {3}, "home/away balance"
    assert all(pot_count[v] == [1] * POTS6 for v in range(N)), "pot balance"
    assert set(len(v) for v in per_matchday.values()) == {MATCHES_PER_MATCHDAY * 2}, "matchday size"
    return len(per_matchday)


HEADER = """/* Generated by tools/mkswiss.py -- do not edit by hand.

   The draw for a 36-club league phase: %d matches over %d matchdays. Every club plays 8
   different opponents, exactly two from each pot of nine (pot = list position / 9), exactly
   four at home and four away. Each of the 8 rounds is a perfect matching of all 36 clubs and
   is split over two matchdays of %d matches, so no matchday exceeds the 16 match slots a
   fixture record holds. Club numbers are positions in the regulation's own club list. */

typedef struct { unsigned char md, home, away; } fl26_pair_t;

#define FL26_SWISS36_CLUBS      %d
#define FL26_SWISS36_PAIRS      %d
#define FL26_SWISS36_MATCHDAYS  %d

static const fl26_pair_t FL26_SWISS36[FL26_SWISS36_PAIRS] = {
"""


def main():
    table = build()
    matchdays = check(table)
    out = [HEADER % (len(table), matchdays, MATCHES_PER_MATCHDAY, N, len(table), matchdays)]
    for i in range(0, len(table), 6):
        out.append("  " + " ".join("{%2d,%2d,%2d}," % t for t in table[i:i + 6]) + "\n")
    out.append("};\n")
    six = build6()
    md6 = check6(six)
    out.append("\n/* The Conference League: 6 pots of six (pot = list position / 6), one opponent from\n"
               "   each pot, three at home and three away: %d matches over %d matchdays. */\n"
               "#define FL26_SWISS6_PAIRS      %d\n#define FL26_SWISS6_MATCHDAYS  %d\n\n"
               "static const fl26_pair_t FL26_SWISS6[FL26_SWISS6_PAIRS] = {\n"
               % (len(six), md6, len(six), md6))
    for i in range(0, len(six), 6):
        out.append("  " + " ".join("{%2d,%2d,%2d}," % t for t in six[i:i + 6]) + "\n")
    out.append("};\n")
    text = "".join(out)
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if path:
        with open(path, "w", newline="\n") as fh:
            fh.write(text)
        sys.stderr.write("%s: %d matches, %d matchdays; six-pot table %d matches, %d matchdays; "
                         "all checks passed\n" % (path, len(table), matchdays, len(six), md6))
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
