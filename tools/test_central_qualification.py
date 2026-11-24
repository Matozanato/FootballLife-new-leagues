"""Offline checks of the Central American world-to-native contract."""

import unittest
from collections import Counter
from itertools import combinations

from central_qualification import contract, database_phase_shapes


class QualificationContract(unittest.TestCase):
    def setUp(self):
        self.lines = [
            "league 18 country=112 region=83 tier=1 clubs=10 legs=2 name=Costa Rica",
            "league 19 country=112 region=83 tier=2 above=18 clubs=12 legs=2 name=Second",
            "league 31 country=119 region=86 tier=1 clubs=12 legs=2 name=Guatemala",
            "league 42 country=121 region=87 tier=1 clubs=10 legs=3 name=Honduras",
            "season 87 1",
        ]

    def test_top_divisions_missing_country_and_calendar_region(self):
        sources = contract(self.lines)
        self.assertEqual(sources[0][:7], [18, 0, 0, 18, 10, 2, 0])
        self.assertEqual(sources[2][:7], [42, 1, 0, 42, 10, 3, 0])
        self.assertEqual(sources[6], [0] * 19)

    def test_combined_halves(self):
        sources = contract(self.lines + ["seasonsum 80 parts=42,81"], {81: (10, 2)})
        self.assertEqual(sources[2][:11], [42, 1, 0, 42, 10, 3, 0, 81, 10, 2, 0])
        sources = contract(self.lines + ["split 31 regular=910 groups=911 carry=0"],
                           {910: (12, 1), 911: (12, 1)})
        self.assertEqual(sources[1][:11], [31, 0, 0, 910, 12, 1, 0, 911, 12, 1, 0])

    def test_three_tier_split(self):
        sources = contract(self.lines + ["split 31 regular=910 groups=911,912,913"],
                           {910: (12, 2), 911: (4, 1), 912: (4, 1), 913: (4, 1)})
        self.assertEqual(sources[1], [31, 0, 0, 910, 12, 2, 0, 911, 4, 1, 1,
                                      912, 4, 1, 2, 913, 4, 1, 3])

    def test_only_explicit_cup_berth(self):
        lines = [line.replace("legs=3", "legs=3 cup=99") for line in self.lines]
        self.assertEqual(contract(lines)[2][2], 0)
        self.assertEqual(contract(lines, cup_berths={121: 99})[2][2], 99)
        with self.assertRaisesRegex(ValueError, "without top division"):
            contract(lines, cup_berths={108: 99})

    def test_reject_infeasible_or_ambiguous(self):
        with self.assertRaisesRegex(ValueError, "too few"):
            contract(self.lines[:-2])
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            contract(self.lines + ["league 39 country=119 tier=1 clubs=8 legs=2"])
        with self.assertRaisesRegex(ValueError, "unknown or invalid schedule"):
            contract(self.lines + ["seasonsum 80 parts=42,81"])

    def test_read_native_phase_shape(self):
        row = bytearray(20)
        row[9], row[11] = 4, 0xC0 | 12
        row[16:20] = (3 << 12).to_bytes(4, "little")
        self.assertEqual(database_phase_shapes({123: row}), {123: (12, 3)})

    def test_dynamic_fixture_audit(self):
        from central_probe_audit import check

        rows = []
        dates = [(7, 29), (8, 5), (8, 12), (8, 19), (8, 26)]
        for group in range(4):
            field = range(1 + 5 * group, 6 + 5 * group)
            for i, (a, b) in enumerate(combinations(field, 2)):
                if b - a > 2:
                    a, b = b, a
                rows.append((700 + 1024 * (group + 1), 1, (2027, *dates[i // 2]), 0,
                             a, b, (0,) * 6))
        config = {"group": 700, "knockout": 701, "helper": 702, "groups": [],
                  "annual_sources": [], "club_countries": {i: i % 4 for i in range(1, 21)}}
        self.assertEqual(Counter(row[0] for row in rows), {r: 10 for r in range(1724, 4797, 1024)})
        check(rows, config, "groups")
        check([], config, "pre-draw", 2027)
        check(rows, config, "pre-draw", 2028)
        with self.assertRaises(AssertionError):
            check(rows, config, "pre-draw", 2027)
        with self.assertRaises(AssertionError):
            check(rows[:-1], config, "groups")
        config["club_countries"] = dict.fromkeys(range(1, 21), 1)
        with self.assertRaises(AssertionError):
            check(rows, config, "groups")

    def test_qualification_trace_matches_native_groups(self):
        from central_probe_audit import qualification

        fields = [list(range(1 + 5 * g, 6 + 5 * g)) for g in range(4)]
        log = ["CA qualification begin edition=2027 creation=2026:000 cutoff=2027:201"]
        for g, field in enumerate(fields):
            for pot, club in enumerate(field, 1):
                log += [f"CA ranking association={g} period=2026 completed=2027:143 rank={pot} "
                        f"club={club} basis=annual",
                        f"CA entrant club={club} association={g} rank={pot} pot={pot} basis=annual place=quota"]
            log.append(f"Central American Cup: group {chr(65+g)} " + " ".join(map(str, field)))
        log.append("CA qualification end edition=2027")
        self.assertEqual(len(qualification(log, 2027, fields, "annual")["entrants"]), 20)
        for lines, reason in ((log[:-1], "annual"), (log, "bootstrap")):
            with self.assertRaises(AssertionError):
                qualification(lines, 2027, fields, reason)


if __name__ == "__main__":
    unittest.main()
