"""Sporting rules for Copa do Nordeste 2026 (REC articles 12–22).

Independent of game memory. Missing discipline data and unplayed games never
silently produce a qualifier. The runtime must supply complete match results.
"""
from dataclasses import asdict, dataclass
from hashlib import sha256
import json

REC_SOURCE = "https://www.srgoool.com.br/downloads.php?id_anexo=1583"
PHASES = ("groups", "quarterfinals", "semifinals", "final")
QUARTERS = ((0, 2), (1, 3), (2, 0), (3, 1))
SEMIS = ((0, 3), (1, 2))  # E x H and F x G (REC art. 16)


class Pending(ValueError):
    """Required match, card count or penalty result has not been supplied."""


@dataclass(frozen=True)
class Match:
    phase: str
    tie: int
    leg: int
    home: int
    away: int
    home_goals: int
    away_goals: int
    home_red: int | None = None
    away_red: int | None = None
    home_yellow: int | None = None
    away_yellow: int | None = None
    home_penalties: int | None = None
    away_penalties: int | None = None

    def __post_init__(self):
        if self.phase not in PHASES or self.home == self.away:
            raise ValueError("Invalid phase or identical opponents")
        if self.tie < 0 or self.leg not in (1, 2):
            raise ValueError("Invalid tie/leg")
        for key, value in asdict(self).items():
            if key.endswith(("goals", "red", "yellow", "penalties")):
                if value is not None and (type(value) is not int or value < 0):
                    raise ValueError(f"Invalid {key}")
        if (self.home_penalties is None) != (self.away_penalties is None):
            raise ValueError("Penalty score needs both sides")


@dataclass
class Stats:
    played: int = 0
    points: int = 0
    wins: int = 0
    goals_for: int = 0
    goals_against: int = 0
    red: int | None = 0
    yellow: int | None = 0

    @property
    def sporting_key(self):
        return (self.points, self.wins, self.goals_for - self.goals_against, self.goals_for)

    def add(self, goals, against, red, yellow):
        self.played += 1
        self.points += 3 if goals > against else 1 if goals == against else 0
        self.wins += goals > against
        self.goals_for += goals
        self.goals_against += against
        self.red = self.red + red if self.red is not None and red is not None else None
        self.yellow = self.yellow + yellow if self.yellow is not None and yellow is not None else None


class Tournament:
    def __init__(self, groups, seed):
        if set(groups) != set("ABCD") or any(len(groups[g]) != 5 for g in groups):
            raise ValueError("Need four groups of five")
        self.groups = {g: tuple(groups[g]) for g in "ABCD"}
        self.clubs = tuple(t for g in self.groups.values() for t in g)
        if len(set(self.clubs)) != 20 or any(type(t) is not int or t <= 0 for t in self.clubs):
            raise ValueError("Need twenty distinct positive team IDs")
        if not isinstance(seed, str) or not seed:
            raise ValueError("Persistent season draw seed required")
        self.seed = seed
        self.results = {}

    def group_fixtures(self):
        fixtures = []
        for rnd in range(5):
            for left, right in (("A", "B"), ("C", "D")):
                for slot in range(5):
                    home = self.groups[left][slot]
                    away = self.groups[right][(slot + rnd) % 5]
                    if rnd % 2:
                        home, away = away, home
                    fixtures.append((rnd + 1, home, away))
        return fixtures

    def record(self, match):
        if match.home not in self.clubs or match.away not in self.clubs:
            raise ValueError("Non-participant")
        key = (match.phase, match.tie, match.leg)
        if key in self.results:
            if self.results[key] == match:
                return  # idempotent reconstruction after loading a save
            raise ValueError("Conflicting result for an already recorded match")
        if match.phase == "groups":
            expected = self.group_fixtures()
            if match.leg != 1 or match.tie >= len(expected):
                raise ValueError("Invalid group match")
            _, home, away = expected[match.tie]
        else:
            fixtures = self.knockout_fixtures(match.phase)
            try:
                home, away = fixtures[(match.tie, match.leg)]
            except KeyError:
                raise ValueError("Invalid knockout match") from None
        if (match.home, match.away) != (home, away):
            raise ValueError("Wrong opponents or home advantage")
        if match.home_penalties is not None:
            if match.phase == "groups" or (match.phase != "quarterfinals" and match.leg != 2):
                raise ValueError("Penalties cannot occur in this match")
            if match.home_penalties == match.away_penalties:
                raise ValueError("Unfinished penalty shootout")
            if match.phase == "quarterfinals":
                tied = match.home_goals == match.away_goals
            else:
                first = self.results.get((match.phase, match.tie, 1))
                if first is None:
                    raise Pending("First leg not played")
                tied = (first.home_goals + match.away_goals ==
                        first.away_goals + match.home_goals)
            if not tied:
                raise ValueError("Penalty shootout supplied for a decided tie")
        self.results[key] = match

    def stats(self, phases):
        out = {t: Stats() for t in self.clubs}
        for m in self.results.values():
            if m.phase not in phases:
                continue
            out[m.home].add(m.home_goals, m.away_goals, m.home_red, m.home_yellow)
            out[m.away].add(m.away_goals, m.home_goals, m.away_red, m.away_yellow)
        return out

    def rank(self, clubs, phases):
        """Points, wins, GD, GF, fewer RC, fewer YC, reproducible draw.

        Missing card data matters only where the preceding criteria are tied.
        No ID-order or head-to-head fallback is allowed by the REC.
        """
        stats = self.stats(phases)
        buckets = {}
        for club in clubs:
            buckets.setdefault(stats[club].sporting_key, []).append(club)
        result = []
        for key in sorted(buckets, reverse=True):
            tied = buckets[key]
            if len(tied) > 1:
                if any(stats[t].red is None for t in tied):
                    raise Pending("Red cards needed to break tie")
                by_red = {}
                for t in tied:
                    by_red.setdefault(stats[t].red, []).append(t)
                tied = []
                for red in sorted(by_red):
                    block = by_red[red]
                    if len(block) > 1:
                        if any(stats[t].yellow is None for t in block):
                            raise Pending("Yellow cards needed to break tie")
                        block.sort(key=lambda t: (stats[t].yellow,
                                   sha256(f"{self.seed}:{t}".encode()).digest()))
                    tied.extend(block)
            result.extend(tied)
        return result

    def tables(self):
        return {g: self.rank(self.groups[g], {"groups"}) for g in "ABCD"}

    def require_complete(self, phase):
        counts = {"groups": 50, "quarterfinals": 4, "semifinals": 4, "final": 2}
        if sum(m.phase == phase for m in self.results.values()) != counts[phase]:
            raise Pending(f"{phase} not complete")

    def winner(self, phase, tie):
        legs = 1 if phase == "quarterfinals" else 2
        played = [self.results.get((phase, tie, leg)) for leg in range(1, legs + 1)]
        if any(m is None for m in played):
            raise Pending("Tie not complete")
        first, last = played[0], played[-1]
        a, b = first.home, first.away
        points = {a: 0, b: 0}
        goals = {a: 0, b: 0}
        for m in played:
            goals[m.home] += m.home_goals
            goals[m.away] += m.away_goals
            points[m.home] += 3 if m.home_goals > m.away_goals else int(m.home_goals == m.away_goals)
            points[m.away] += 3 if m.away_goals > m.home_goals else int(m.home_goals == m.away_goals)
        for values in (points, goals):
            if values[a] != values[b]:
                return a if values[a] > values[b] else b
        if last.home_penalties is None:
            raise Pending("Penalty shootout required; no extra time or away-goal rule")
        return last.home if last.home_penalties > last.away_penalties else last.away

    def knockout_fixtures(self, phase):
        if phase == "quarterfinals":
            self.require_complete("groups")
            tables = self.tables()
            return {(i, 1): (tables["ABCD"[a]][0], tables["ABCD"[b]][1])
                    for i, (a, b) in enumerate(QUARTERS)}
        if phase == "semifinals":
            self.require_complete("quarterfinals")
            pairs = [(self.winner("quarterfinals", a), self.winner("quarterfinals", b))
                     for a, b in SEMIS]
            before = {"groups", "quarterfinals"}
        elif phase == "final":
            self.require_complete("semifinals")
            pairs = [(self.winner("semifinals", 0), self.winner("semifinals", 1))]
            before = {"groups", "quarterfinals", "semifinals"}
        else:
            raise ValueError("Unknown knockout phase")
        fixtures = {}
        for tie, pair in enumerate(pairs):
            better, worse = self.rank(pair, before)
            fixtures[tie, 1] = (worse, better)
            fixtures[tie, 2] = (better, worse)
        return fixtures

    def final_ranking(self):
        self.require_complete("final")
        champion = self.winner("final", 0)
        finalists = set(self.knockout_fixtures("final")[0, 1])
        second = (finalists - {champion}).pop()
        semi = {t for pair in self.knockout_fixtures("semifinals").values() for t in pair}
        quarter = {t for pair in self.knockout_fixtures("quarterfinals").values() for t in pair}
        all_phases = set(PHASES)
        return ([champion, second] + self.rank(semi - finalists, all_phases)
                + self.rank(quarter - semi, all_phases)
                + self.rank(set(self.clubs) - quarter, all_phases))

    def dumps(self):
        return json.dumps({"version": 1, "groups": self.groups, "seed": self.seed,
                           "results": [asdict(m) for m in self.results.values()]}, sort_keys=True)

    @classmethod
    def loads(cls, value):
        data = json.loads(value)
        if data["version"] != 1:
            raise ValueError("Unknown snapshot version")
        tournament = cls(data["groups"], data["seed"])
        for row in sorted(data["results"], key=lambda r: (PHASES.index(r["phase"]), r["leg"], r["tie"])):
            tournament.record(Match(**row))
        return tournament
