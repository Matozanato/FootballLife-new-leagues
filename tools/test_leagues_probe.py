import json
import os
from pathlib import Path
import struct
import tempfile
import unittest

import leagues_probe as P


class LeaguesProbeTests(unittest.TestCase):
    def test_competition_info_snapshot_includes_control_competition(self):
        block, offset, base, count_offset = 0x1000, 0x400, 0x800, 0x200
        code = {
            0x140AED39C: b"\xf2\x0f\x10\x81" + struct.pack("<i", offset),
            0x1414BB070: b"\x8b\x81" + struct.pack("<i", count_offset),
            0x1414BB076: b"\x48\x8d\x93" + struct.pack("<i", base),
            0x1414BB07D: b"\x48\x69\xc8" + struct.pack("<i", 0x314),
            block + offset: struct.pack("<IHH", 9, 0xffff, 0),
        }
        fixture_base = 0x2000
        code.update({
            0x141579F83: b"\x48\x8d\x96" + struct.pack("<i", fixture_base),
            0x141579F8A: b"\x48\x69\xc8" + struct.pack("<i", 0x208),
            0x141579F7A: b"\x3d" + struct.pack("<i", 1),
        })
        fixture = bytearray(0x208)
        struct.pack_into("<H", fixture, 0, 706)
        struct.pack_into("<HH", fixture, 12, 125, 0xffff)
        struct.pack_into("<III", fixture, 16, 0x340002c2, 0x350002c2, 0x07f7ffff)
        struct.pack_into("<II", fixture, 28, 0x330002c2, 0x730002c2)
        struct.pack_into("<I", fixture, 0x204, (0x34 << 26) | 1)
        code[block + fixture_base] = bytes(fixture)
        rows = bytearray(3 * 0x314)
        for slot, (reg, comp) in enumerate(((706, 768), (10, 9), (11, 12))):
            struct.pack_into("<H", rows, slot*0x314, reg)
            struct.pack_into("<I", rows, slot*0x314+0x80, comp)
        code[block + base] = bytes(rows)

        class Memory:
            def read(self, address, size):
                result = code.get(address, b"\xe8\x10\x00\x00\x00")
                return result if len(result) == size else None

            def u32(self, address):
                return 3 if address == block + count_offset else None

        report = P.inspect_competition_info(Memory(), block, {706})
        self.assertEqual((9, 0xffff), (report["competition"], report["regulation"]))
        self.assertEqual({"10", "706"}, set(report["records"]))
        self.assertEqual(0x34, report["rounds"][0]["kind"])
        self.assertEqual((125, 0xffff), report["rounds"][0]["slots"][0]["match_ids"])
        self.assertEqual(0x340002c2, report["rounds"][0]["slots"][0]["key"])
        self.assertEqual((0x350002c2, 0x07f7ffff), report["rounds"][0]["slots"][0]["destinations"])
        self.assertEqual((0x330002c2, 0x730002c2), report["rounds"][0]["slots"][0]["sources"])
        self.assertEqual("0x140aedd4c", report["call_targets"]["0x140aedd37"])
        self.assertEqual("0x140b34c37", report["call_targets"]["0x140b34c22"])

    def test_second_edition_audit_rejects_previous_year(self):
        rows = [(r, s, (2027, *d[1:]), f, h, a, score)
                for r, s, d, f, h, a, score in self.fixture_rows()]
        self.assertEqual(54, P.audit_report(rows, self.masters, self.clubs, year=2027)["played"])
        with self.assertRaises(ValueError):
            P.audit_report(rows, self.masters, self.clubs, year=2026)

    clubs = P.MLS + P.MX
    masters = list(range(710, 716))

    def fixture_rows(self, score=(1, 0, 4, 1, 0, 3)):
        return [(self.masters[b]+1024*t, 2, (2026, 8, P.DAYS[b]), 0x40, h, a, score)
                for b, pairs in enumerate(P.schedule(self.clubs)) for t, (h, a) in enumerate(pairs, 1)]

    def test_schedule(self):
        self.assertEqual(36, len(set(self.clubs)))
        pairs = P.schedule(self.clubs)
        self.assertEqual([9]*6, list(map(len, pairs)))
        self.assertEqual((6, 6, 13, 13, 20, 20), P.DAYS)
        played = {c: [] for c in self.clubs}
        encounters = set()
        for day, fixtures in zip(P.DAYS, pairs):
            for h, a in fixtures:
                self.assertNotEqual(h in P.MLS, a in P.MLS)
                encounters.add(frozenset((h, a)))
                played[h].append(day)
                played[a].append(day)
        self.assertEqual(54, len(encounters))
        self.assertTrue(all(len(ds) == 3 and min(y-x for x, y in zip(ds, ds[1:])) >= 3
                            for ds in played.values()))
        with self.assertRaises(ValueError):
            P.schedule(self.clubs[:-1] + self.clubs[:1])

    def test_tables_and_reload(self):
        rows = self.fixture_rows()
        tables = P.tables(rows, self.masters, self.clubs)
        self.assertEqual([18, 18], list(map(len, tables.values())))
        all_rows = [s for table in tables.values() for s in table.values()]
        self.assertEqual(162, sum(s["Pts"] for s in all_rows))
        self.assertTrue(all(s["GD"] == 0 and s["P"] == s["GF"] == s["GA"] == 3 for s in all_rows))
        replay = [(r, st, tuple(d), f, h, a, s) for r, st, d, f, h, a, s in json.loads(json.dumps(rows))]
        self.assertEqual(tables, P.tables(replay, self.masters, self.clubs))
        report = P.audit_report(rows, self.masters, self.clubs, require_complete=True)
        self.assertEqual(report, json.loads(json.dumps(report)))
        self.assertEqual(report, P.audit_report(replay[::-1], self.masters, self.clubs))
        first = report["fixtures"][0]
        self.assertEqual([1, 1], first["regulation"])
        self.assertEqual([4, 3], first["penalties"])
        self.assertEqual(first["home"], first["shootout_winner"])
        incomplete = [(*rows[0][:3], 0, *rows[0][4:]), *rows[1:]]
        self.assertEqual(53, P.audit_report(incomplete, self.masters, self.clubs)["played"])
        with self.assertRaises(ValueError):
            P.audit_report(incomplete, self.masters, self.clubs, require_complete=True)
        regulation = P.tables(self.fixture_rows((2, 0, 0, 0, 0, 0)), self.masters, self.clubs)
        h, a = rows[0][4:6]
        self.assertGreater(regulation["MLS"][h]["RW"], 0)
        self.assertGreater(regulation["LigaMX"][a]["RL"], 0)

    def test_rejects_missing_duplicate_misdated_and_invalid(self):
        rows = self.fixture_rows()
        for bad in (rows[:-1], rows + rows[:1],
                    [(*rows[0][:2], (2026, 8, 31), *rows[0][3:]), *rows[1:]],
                    self.fixture_rows((1, 0, 0, 1, 0, 0)),
                    self.fixture_rows((1, 0, 255, 1, 0, 4)),
                    self.fixture_rows((1, 1, 4, 1, 0, 3))):
            with self.assertRaises(ValueError):
                P.tables(bad, self.masters, self.clubs)

    def test_calendar_spacing_and_batch_ownership(self):
        club = self.clubs[9]
        score = (0,)*6
        rows = [(167, 0, (2026, 8, 9), 0, club, 4156, score),
                (167, 0, (2026, 8, 17), 0, club, 4156, score)]
        self.assertEqual([], P.calendar_conflicts(rows + self.fixture_rows(), self.masters, self.clubs))
        rows.append((167, 0, (2026, 8, 13), 0, club, 4156, score))
        self.assertEqual([dict(master=713, date="2026-08-13", regulation=167,
                               native_date="2026-08-13", home=club, away=4156, clubs=[club])],
                         P.calendar_conflicts(rows, self.masters, self.clubs))

    def test_dynamic_master_dates_and_day_lists(self):
        selected = (5, 7, 12, 16, 19, 21)
        rows = [(reg, st, (2026, 8, selected[self.masters.index(reg & 1023)]), flag, h, a, score)
                for reg, st, _, flag, h, a, score in self.fixture_rows()]
        report = P.audit_report(rows, self.masters, self.clubs, require_complete=True)
        self.assertEqual(set(selected), {row["date"][2] for row in report["fixtures"]})
        self.assertEqual(report, P.audit_report(rows[::-1], self.masters, self.clubs))
        lists = [[] for _ in range(365)]
        for slot, row in enumerate(rows):
            lists[211+row[2][2]].append(slot)
        P.check_day_lists(rows, list(range(54)), lists)
        lists[0].append(0)
        with self.assertRaises(ValueError):
            P.check_day_lists(rows, list(range(54)), lists)
        club = self.clubs[0]
        later = [(54, 0, (2026, 8, 14), 0, club, 4156, (0,)*6)]
        self.assertEqual(712, P.calendar_conflicts(later, self.masters, self.clubs, selected)[0]["master"])
        close = [(reg, st, (2026, 8, 7) if reg & 1023 == 712 else day, flag, h, a, score)
                 for reg, st, day, flag, h, a, score in rows]
        with self.assertRaises(ValueError):
            P.audit_report(close, self.masters, self.clubs)

    def test_62_fixture_bracket_and_podium(self):
        phase = P.audit_report(self.fixture_rows(), self.masters, self.clubs, require_complete=True)
        mls, mx = (list(map(int, P.rank_table(phase["standings"][k])[:4])) for k in ("MLS", "LigaMX"))
        qf = list(zip(mls, reversed(mx)))
        sf = [(mls[0], mls[3]), (mls[1], mls[2])]
        finals = [(mls[3], mls[2]), (mls[0], mls[1])]
        rows = [(r+1024*t, 0, (2026, 8, day), 0x40, home, away, (0, 0, 4, 0, 0, 3))
                for r, day, stage in zip((706, 707, 708), (23, 26, 29), (qf, sf, finals))
                for t, (home, away) in enumerate(stage, 1)]
        complete = P.knockout_report(phase, rows, [706, 707, 708])
        view = P.knockout_view(phase, complete, [706, 707, 708], 2026)
        self.assertEqual(["quarterfinal"]*4 + ["semifinal"]*2 + ["third_place", "final"],
                         [node["stage"] for node in view["nodes"]])
        self.assertEqual([mls[3], mls[2]], view["nodes"][-2]["clubs"])
        self.assertEqual([mls[0], mls[1]], view["nodes"][-1]["clubs"])
        self.assertEqual([4, 3], view["nodes"][-1]["result"]["penalties"])
        self.assertEqual(((706, 1, "winner"), (706, 4, "winner")), view["nodes"][4]["sources"])
        partial = P.knockout_report(phase, rows[:4], [706, 707, 708])
        pending = P.knockout_view(phase, partial, [706, 707, 708], 2026)["nodes"]
        self.assertEqual([mls[0], mls[3]], pending[4]["clubs"])
        self.assertIsNone(pending[4]["result"])
        self.assertEqual([None, None], pending[-2]["clubs"])
        self.assertEqual(62, phase["scheduled"] + len(complete["fixtures"]))
        self.assertEqual(dict(champion=mls[0], runner_up=mls[1], third=mls[3]), complete["podium"])
        self.assertEqual(complete, P.knockout_report(phase, rows[::-1], [706, 707, 708]))
        with self.assertRaises(ValueError):
            P.knockout_report(phase, rows[1:], [706, 707, 708])

    @unittest.skipUnless(os.environ.get("LEAGUES_TEST_WORLD") and os.environ.get("CONCACAF_TEST_BASE"),
                         "requires archived team data and stock FL27 competition tables")
    def test_generated_native_rows(self):
        root = Path(os.environ["LEAGUES_TEST_WORLD"])
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / "test-world"
            inventory = P.build(root / P.DB, Path(os.environ["CONCACAF_TEST_BASE"]),
                                root / "fl26world.txt", dest)
            self.assertEqual(54, sum(map(len, inventory["fixtures"].values())))
            self.assertEqual({"2026-08-06": 18, "2026-08-13": 18, "2026-08-20": 18},
                             {day: len(pairs) for day, pairs in inventory["fixtures"].items()})
            masters = inventory["masters"]
            stock = Path(os.environ["CONCACAF_TEST_BASE"])
            base_comp, base_rules, base_entries = P.rows(stock)
            comp, rules, entries = P.rows(dest / P.DB)
            self.assertEqual(base_comp, comp[:len(base_comp)])
            self.assertEqual(base_rules, rules[:len(base_rules)])
            self.assertEqual(base_entries, entries)
            own = [r for r in rules if P.K.rid(r) % 1024 in masters]
            self.assertEqual(60, len(own))
            self.assertEqual({m+1024*t for m in masters for t in range(10)},
                             {P.K.rid(r) for r in own})
            for r in own:
                flags = int.from_bytes(r[16:20], "little")
                self.assertTrue(flags & P.PENALTIES)
                self.assertFalse(flags & P.OTHER_RULES)


if __name__ == "__main__":
    unittest.main()
