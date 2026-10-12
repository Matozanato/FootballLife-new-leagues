"""Offline checks only: these do not validate the competition in Master League."""
from collections import Counter
import json
import struct
import unittest

import prepare as P


class NordesteChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = json.loads((P.HERE / "nordeste2026.json").read_text(encoding="utf-8"))
        cls.clubs = cls.spec["participants"]

    def test_roster(self):
        self.assertEqual(len(self.clubs), 20)
        self.assertEqual(Counter(p["group"] for p in self.clubs), dict.fromkeys("ABCD", 5))
        self.assertEqual(Counter(p["squad"] for p in self.clubs),
                         {"existing": 6, "mod_placeholder": 14})
        ids = [p["team_id"] for p in self.clubs]
        self.assertNotIn(None, ids)
        self.assertEqual(len(set(ids)), 20)
        self.assertTrue(all(p["state"] in {"BA", "SE", "AL", "PE", "PB", "RN", "CE", "PI", "MA"}
                            for p in self.clubs))
        # Never confuse Botafogo-PB with Rio/SP, America-RN with MG, or the two Fortalezas.
        self.assertTrue({1246, 5139, 2450, 5371, 2453}.isdisjoint(ids))

    def test_group_schedule(self):
        matches = self.spec["fixtures"]
        self.assertEqual(len(matches), 50)
        groups = {p["name"]: p["group"] for p in self.clubs}
        seen = set()
        homes, appearances = Counter(), Counter()
        for m in matches:
            pair = frozenset((m["home"], m["away"]))
            self.assertNotIn(pair, seen)
            seen.add(pair)
            self.assertIn({groups[m["home"]], groups[m["away"]]}, [{"A", "B"}, {"C", "D"}])
            homes[m["home"]] += 1
            appearances.update((m["home"], m["away"]))
        for p in self.clubs:
            self.assertEqual(appearances[p["name"]], 5)
            self.assertEqual(homes[p["name"]], 3 if p["group"] in "AC" else 2)
        for rnd in range(1, 6):
            playing = [m[k] for m in matches if m["round"] == rnd for k in ("home", "away")]
            self.assertEqual(len(playing), 20)
            self.assertEqual(len(set(playing)), 20)

    def test_knockout(self):
        self.assertEqual(self.spec["quarterfinals"],
                         [["A1", "C2"], ["B1", "D2"], ["C1", "A2"], ["D1", "B2"]])
        self.assertEqual(self.spec["legs"],
                         {"groups": 1, "quarterfinals": 1, "semifinals": 2, "final": 2})

    def test_generated_squads(self):
        db = P.HERE / "staging/SiderAddons/livecpk/_FL26Nordeste2026Clubs/common/etc/pesdb"
        if not (db / "Team.bin").exists():
            self.skipTest("no staging: run prepare.py --build-clubs first")
        teams = P.pesdb.team_rows(P.pesdb.load("Team", str(db)))
        players = P.pesdb.load("Player", str(db))
        pids = {struct.unpack_from("<I", r, 8)[0] for r in P.pesdb.rows(players, 312)}
        squads = {}
        for r in P.pesdb.rows(P.pesdb.load("PlayerAssignment", str(db)), 16):
            _, pid, tid, _ = struct.unpack("<4I", r)
            squads.setdefault(tid, []).append(pid)
        generated = set()
        for p in self.clubs:
            tid = p["team_id"]
            self.assertIn(tid, teams)
            squad = squads.get(tid, [])
            self.assertGreaterEqual(len(squad), 11)
            self.assertLessEqual(len(squad), 40)
            self.assertEqual(len(squad), len(set(squad)))
            self.assertTrue(set(squad) <= pids)
            if p["squad"] == "mod_placeholder":
                self.assertEqual(len(squad), 30)
                self.assertTrue(generated.isdisjoint(squad))
                generated.update(squad)
        self.assertEqual(len(generated), 420)


if __name__ == "__main__":
    unittest.main(verbosity=2)
