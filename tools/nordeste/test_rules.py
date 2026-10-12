import unittest

from rules import Match, Pending, Tournament


def tournament(seed="2026"):
    return Tournament({g: list(range(i * 5 + 1, i * 5 + 6)) for i, g in enumerate("ABCD")}, seed)


def groups_done(t, cards=True):
    for tie, (_, home, away) in enumerate(t.group_fixtures()):
        t.record(Match("groups", tie, 1, home, away, (home * 3 + away) % 4,
                       (away * 2 + home) % 3, **({"home_red": 0, "away_red": 0,
                       "home_yellow": home % 3, "away_yellow": away % 3} if cards else {})))


def finish(t, phase):
    for (tie, leg), (home, away) in sorted(t.knockout_fixtures(phase).items(), key=lambda x: (x[0][1], x[0][0])):
        t.record(Match(phase, tie, leg, home, away, 1, 0,
                       0, 0, 0, 0,
                       5 if leg == 2 else None, 4 if leg == 2 else None))


class RulesTests(unittest.TestCase):
    def test_schedule(self):
        t = tournament()
        fixtures = t.group_fixtures()
        self.assertEqual(len(fixtures), 50)
        self.assertEqual(len({frozenset((h, a)) for _, h, a in fixtures}), 50)
        for rnd in range(1, 6):
            self.assertEqual(len({c for r, h, a in fixtures if r == rnd for c in (h, a)}), 20)
        for i, g in enumerate("ABCD"):
            for club in t.groups[g]:
                self.assertEqual(sum(h == club for _, h, a in fixtures), 3 if g in "AC" else 2)

    def test_no_early_qualification(self):
        with self.assertRaises(Pending):
            tournament().knockout_fixtures("quarterfinals")

    def test_group_table_ignores_knockout(self):
        t = tournament()
        groups_done(t)
        tables = t.tables()
        finish(t, "quarterfinals")
        self.assertEqual(tables, t.tables())

    def test_crossings(self):
        t = tournament()
        groups_done(t)
        tables = t.tables()
        quarters = t.knockout_fixtures("quarterfinals")
        self.assertEqual(quarters[0, 1], (tables["A"][0], tables["C"][1]))
        self.assertEqual(quarters[3, 1], (tables["D"][0], tables["B"][1]))
        finish(t, "quarterfinals")
        semis = t.knockout_fixtures("semifinals")
        self.assertEqual(set(semis[0, 1]), {t.winner("quarterfinals", 0), t.winner("quarterfinals", 3)})
        self.assertEqual(set(semis[1, 1]), {t.winner("quarterfinals", 1), t.winner("quarterfinals", 2)})

    def test_return_home_is_cumulative(self):
        t = tournament()
        groups_done(t)
        finish(t, "quarterfinals")
        for (tie, leg), pair in t.knockout_fixtures("semifinals").items():
            if leg == 2:
                self.assertEqual(pair[0], t.rank(pair, {"groups", "quarterfinals"})[0])

    def test_full_competition_and_reload(self):
        t = tournament()
        groups_done(t)
        for phase in ("quarterfinals", "semifinals", "final"):
            finish(t, phase)
            t = Tournament.loads(t.dumps())
        self.assertEqual(len(t.results), 60)
        ranking = t.final_ranking()
        self.assertEqual(len(set(ranking)), 20)
        self.assertEqual(ranking[0], t.winner("final", 0))

    def test_new_season_is_empty(self):
        t = tournament()
        groups_done(t)
        following = Tournament(t.groups, "2027")
        self.assertEqual(following.results, {})
        self.assertTrue(all(s.played == 0 for s in following.stats({"groups"}).values()))

    def test_missing_cards_do_not_become_zero(self):
        t = tournament()
        for i, (_, h, a) in enumerate(t.group_fixtures()):
            t.record(Match("groups", i, 1, h, a, 0, 0))
        with self.assertRaisesRegex(Pending, "Red cards"):
            t.tables()

    def test_cards_and_lots(self):
        t = tournament()
        for i, (_, h, a) in enumerate(t.group_fixtures()):
            t.record(Match("groups", i, 1, h, a, 0, 0, int(h == 1), int(a == 1),
                           int(h == 2), int(a == 2)))
        self.assertEqual(t.tables()["A"][-2:], [2, 1])
        self.assertEqual(t.tables(), Tournament.loads(t.dumps()).tables())

    def test_wins_before_goal_difference(self):
        from rules import Stats
        t = tournament()
        stats = {1: Stats(points=6, wins=2, goals_for=2, goals_against=8),
                 2: Stats(points=6, wins=1, goals_for=9, goals_against=0)}
        t.stats = lambda _: stats
        self.assertEqual(t.rank([2, 1], {"groups"}), [1, 2])

    def test_penalties_no_away_goal(self):
        t = tournament()
        groups_done(t)
        finish(t, "quarterfinals")
        fixtures = t.knockout_fixtures("semifinals")
        h, a = fixtures[0, 1]
        t.record(Match("semifinals", 0, 1, h, a, 2, 1, 0, 0, 0, 0))
        t.record(Match("semifinals", 0, 2, a, h, 1, 0, 0, 0, 0, 0))
        with self.assertRaisesRegex(Pending, "Penalty"):
            t.winner("semifinals", 0)

    def test_one_game_draw_needs_penalties(self):
        t = tournament()
        groups_done(t)
        h, a = t.knockout_fixtures("quarterfinals")[0, 1]
        t.record(Match("quarterfinals", 0, 1, h, a, 1, 1, 0, 0, 0, 0))
        with self.assertRaises(Pending):
            t.winner("quarterfinals", 0)

    def test_wrong_opponents_rejected(self):
        t = tournament()
        with self.assertRaises(ValueError):
            t.record(Match("groups", 0, 1, 1, 2, 0, 0))

    def test_reload_is_idempotent(self):
        t = tournament()
        _, h, a = t.group_fixtures()[0]
        m = Match("groups", 0, 1, h, a, 2, 1, 0, 0, 0, 0)
        t.record(m)
        t.record(m)
        self.assertEqual(len(t.results), 1)
        self.assertEqual(Tournament.loads(t.dumps()).dumps(), t.dumps())
        with self.assertRaises(ValueError):
            t.record(Match("groups", 0, 1, h, a, 1, 2))

    def test_extra_penalties_rejected(self):
        t = tournament()
        groups_done(t)
        h, a = t.knockout_fixtures("quarterfinals")[0, 1]
        with self.assertRaises(ValueError):
            t.record(Match("quarterfinals", 0, 1, h, a, 1, 0, 0, 0, 0, 0, 4, 3))


if __name__ == "__main__":
    unittest.main(verbosity=2)
