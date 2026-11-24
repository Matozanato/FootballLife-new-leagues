"""Isolated planning tests: python -m unittest discover -s tools -p test_concacaf.py."""
import copy
import itertools
import os
import unittest
from unittest.mock import patch

import concacaf as C
import leaguebuilder as B
import mkccup


def sources():
    rows, start = [], 1
    for key, country, region, role, count in (
            ("mx", "Mexico", "north", "liga_mx", 12),
            ("us", "USA", "north", "mls", 12),
            ("ca", "Canada", "north", "canadian_premier", 8),
            ("central", "Costa Rica", "central", None, 12),
            ("caribbean", "Jamaica", "caribbean", None, 8)):
        rows.append(dict(id=key, country=country, region=region, roles=[role] if role else [],
                         conf=6, kind="league", capacity=count, teams=list(range(start, start + count))))
        start += count
    for key, country, role in (("ca", "Canada", "canadian_championship"), ("us", "USA", "us_open_cup")):
        rows.append(dict(id="cup:" + key, country=country, region="north", roles=[role],
                         conf=6, kind="cup", capacity=0))
    return rows


def results(pl):
    out = {k: dict(status="complete", clubs=list(s["teams"]))
           for k, s in pl["sources"].items() if s["kind"] == "league"}
    out.update({"cup:ca": dict(status="complete", clubs=[25]),
                "cup:us": dict(status="complete", clubs=[13]),
                "module:leagues_cup": dict(status="complete", clubs=[1, 13, 2, 14, 3, 15]),
                "module:central_american_cup": dict(status="complete", clubs=list(range(33, 45))),
                "module:caribbean_cup": dict(status="complete", clubs=list(range(45, 53)))})
    return out


class PlannerTests(unittest.TestCase):
    def assert_field(self, entries):
        self.assertEqual(27, len(entries))
        self.assertEqual(27, len({e["club"] for e in entries}))
        self.assertEqual(22, sum(e["stage"] == "round_one" for e in entries))
        self.assertEqual(5, sum(e["stage"] == "round_of_16" for e in entries))

    def test_all_eight_configurations(self):
        for flags in itertools.product((False, True), repeat=3):
            with self.subTest(flags=flags):
                modules = dict(zip(C.MODULES, flags))
                p = C.plan({"modules": modules}, sources())
                self.assertEqual(27, len(p["places"]))
                self.assertEqual(C.QUOTAS, {k: sum(s["path"] == k for s in p["places"]) for k in C.QUOTAS})
                self.assertEqual((11, 1, 2), (p["round_one_ties"], p["final_legs"], p["other_knockout_legs"]))
                self.assertFalse(p["defending_champion_berth"])
                self.assert_field(C.resolve(p, first_season=True))
                entries = C.resolve(p, results(p))
                self.assert_field(entries)
                if modules["leagues_cup"]:
                    path = [r for r in entries if r["path"] == "leagues_cup"]
                    self.assertEqual({1: "round_of_16", 13: "round_one", 2: "round_one"},
                                     {row["club"]: row["stage"] for row in path})

    def test_disabled_fallback_same_region(self):
        p = C.plan({}, sources())
        entries = C.resolve(p, first_season=True)
        for path, ids in (("central_american_cup", range(33, 45)), ("caribbean_cup", range(45, 53))):
            self.assertTrue(all(e["club"] in ids for e in entries if e["path"] == path))
        self.assertEqual(entries, C.resolve(C.plan({}, list(reversed(sources()))), first_season=True))

    def test_duplicates_get_replacements(self):
        p = C.plan({"modules": {k: True for k in C.MODULES}}, sources())
        entries = C.resolve(p, results(p))
        self.assert_field(entries)
        self.assertTrue(any(e["how"] == "duplicate_qualification" for e in entries))
        direct = [e for e in entries if e["stage"] == "round_of_16"]
        self.assertEqual(set(C.DIRECT), {e["path"] for e in direct})

    def test_unavailable_domestic_sources(self):
        rows = [s for s in sources() if s["id"] not in ("mx", "cup:ca", "ca")]
        p = C.plan({}, rows)
        self.assert_field(C.resolve(p, first_season=True))
        with self.assertRaisesRegex(C.QualificationError, "requires both"):
            C.plan({"modules": {"leagues_cup": True}}, rows)
        with self.assertRaisesRegex(C.QualificationError, "unavailable"):
            C.plan({"sources": {"liga_mx": ["missing"]}}, sources())

    def test_leagues_cup_dependencies_only(self):
        for missing in ("mx", "us"):
            rows = [s for s in sources() if s["id"] != missing]
            with self.assertRaises(C.QualificationError):
                C.plan({"modules": {"leagues_cup": True}}, rows)
            C.plan({"modules": {"central_american_cup": True, "caribbean_cup": True}}, rows)

    def test_result_states_are_distinct(self):
        p = C.plan({"modules": {"central_american_cup": True}}, sources())
        for status in ("incomplete", "missing", "invalid"):
            r = results(p)
            r["module:central_american_cup"] = {"status": status}
            error = C.QualificationPending if status == "incomplete" else C.QualificationError
            with self.assertRaises(error):
                C.resolve(p, r)
            if status == "invalid":
                with self.assertRaises(C.QualificationError):
                    C.resolve(p, r, first_season=True)
            else:
                self.assert_field(C.resolve(p, r, first_season=True))
        with self.assertRaises(C.QualificationError):
            C.resolve(p)

    def test_multi_season_sources_not_fixed_clubs(self):
        p = C.plan({}, sources())
        saved = copy.deepcopy(p)
        first = C.resolve(p, results(p))
        second_results = results(p)
        for s in second_results.values():
            s["clubs"].reverse()
        second = C.resolve(p, second_results)
        self.assertNotEqual(first, second)
        members = {k: [t + 1000 for t in s["teams"]] for k, s in p["sources"].items() if s["kind"] == "league"}
        third = C.resolve(p, first_season=True, memberships=members)
        self.assertTrue(all(e["club"] > 1000 for e in third))
        self.assertEqual(saved, p)

    def test_insufficient_unique_capacity(self):
        with self.assertRaisesRegex(C.QualificationError, "27 unique"):
            C.plan({}, sources()[:2])
        rows = sources()
        for s in rows:
            if s["kind"] == "league":
                s["teams"] = list(range(1, s["capacity"] + 1))
        with self.assertRaises(C.QualificationError):
            C.plan({}, rows)

    def test_legacy_assignments_and_pins(self):
        refs = [{"source": "mx", "rank": 1}, {"source": "mx", "rank": 3}, {"source": "us", "rank": 0}]
        pins = {"cid": 180, "reg": 300, "ko": 300}
        p = C.plan({}, sources(), refs, pins)
        self.assertEqual(refs, p["legacy_places"])
        self.assertEqual(pins, p["previous_ids"])
        self.assertTrue(p["requires_new_career"])
        self.assert_field(C.resolve(p, first_season=True))
        self.assertEqual(pins, {k: B.ccup_plan([], concacaf_plan=p)[0][0][k] for k in pins})
        with self.assertRaisesRegex(C.QualificationError, "repeated"):
            C.plan({}, sources(), refs[:1] * 2)
        with self.assertRaisesRegex(C.QualificationError, "quota"):
            C.plan({}, sources(), [{"source": "mx", "rank": n} for n in range(1, 8)])

    def test_validation(self):
        for raw in (False, {"modern": True}, {"modules": {"leagues_cup": 1}}, {"sources": {"leagues_cup": []}}):
            with self.subTest(raw=raw), self.assertRaises(C.QualificationError):
                C.configuration(raw)
        for row in ({}, dict(sources()[0], conf=5), dict(sources()[0], code=C.CODE)):
            with self.assertRaises(C.QualificationError):
                C.plan({}, [row] + sources()[1:])
        with self.assertRaisesRegex(C.QualificationError, "wrong domestic"):
            C.plan({"sources": {"liga_mx": ["us"]}}, sources())
        p = C.plan({}, sources())
        r = results(p)
        r["mx"]["clubs"] = [1, 1]
        with self.assertRaises(C.QualificationError):
            C.resolve(p, r)

    def test_other_regions_only_after_local_exhaustion(self):
        rows = sources()
        central = next(s for s in rows if s["id"] == "central")
        central.update(capacity=2, teams=[33, 34])
        entries = C.resolve(C.plan({}, rows), first_season=True)
        chosen = [e["club"] for e in entries if e["path"] == "central_american_cup"]
        self.assertEqual([33, 34], chosen[:2])
        self.assertEqual(6, len(chosen))

    def test_separate_champion_source_and_invalid_results(self):
        rows = sources() + [dict(id="mls_final", kind="cup", conf=6, region="north", country="USA",
                                capacity=0, roles=["mls_cup"])]
        p = C.plan({"modules": {"central_american_cup": True}}, rows)
        r = results(p)
        r["mls_final"] = dict(status="complete", clubs=[20])
        entries = C.resolve(p, r)
        self.assertEqual(20, next(e["club"] for e in entries if e["path"] == "mls" and e["stage"] == "round_of_16"))
        for key, clubs in (("mls_final", [1]), ("module:central_american_cup", [1, 2, 3, 4, 5, 6]),
                           ("module:central_american_cup", [33, 34])):
            bad = copy.deepcopy(r)
            bad[key] = dict(status="complete", clubs=clubs)
            with self.assertRaises(C.QualificationError):
                C.resolve(p, bad)


class IntegrationTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("CONCACAF_TEST_BASE"), "set CONCACAF_TEST_BASE for database integration")
    def test_real_recipe_plan_rebuild_round_trip(self):
        base = os.environ["CONCACAF_TEST_BASE"]
        from unittest.mock import patch
        for flags in itertools.product((False, True), repeat=3):
            recipe = {"world": "_FL26TestConcacaf", "concacaf": {"modules": dict(zip(C.MODULES, flags))},
                      "leagues": [{"name": "Test Mexico", "country": "Mexico", "clubs": 14,
                                   "europe": [[1, 13], [2, 13]]}]}
            with patch.multiple(B, FL27=True, TEAM_CAP=8000, PLAYER_CAP=180017):
                p = B.plan(recipe, base)
                self.assertFalse(p["concacaf_integration"]["access"]["champions_cup"]["ready"])
                restored = B.recipe_from_plan(p, base)
                expected = C.integration_draft(recipe)
                self.assertEqual(expected, C.integration_draft(restored))
                p["cup_ids"] = {"ccup:FL_CONCACAF": {"cid": 180, "reg": 300, "ko": 300}}
                again = B.plan(restored, base, p)
                self.assertEqual(p["leagues"][0]["rid"], again["leagues"][0]["rid"])
                self.assertEqual(p["cup_ids"], again["prev_cup_ids"])
                recovered = B.recipe_from_plan({k: v for k, v in again.items() if k != "settings"}, base)
                self.assertEqual(expected, C.integration_draft(recovered))

    def test_target_13_only_modern_pending(self):
        cup = B.ccup_plan([(123, 1, 13, 0)])[0][0]
        self.assertEqual((13, C.CODE, 27, C.FORMAT), (cup["number"], cup["code"], cup["participants"], cup["format"]))
        self.assertEqual([], cup["entry"])
        self.assertFalse(cup["runtime_ready"])

    def test_unrelated_cups_unchanged(self):
        own = [(123, n, 14, 0) for n in range(1, 5)]
        before = B.ccup_plan(own)
        after = B.ccup_plan(own + [(124, 1, 13, 0)])
        self.assertEqual(before[0], [c for c in after[0] if c["number"] != 13])
        self.assertEqual(before[1], after[1])
        B.require_competition_runtime({"ccups": before[0]})

    def test_build_guard_before_any_game_access(self):
        for pl in ({"concacaf": {"runtime_ready": False}}, {"ccups": [{"number": 13}]}):
            with patch.object(B.flpaths, "use_game") as game:
                with self.assertRaisesRegex(B.BuildError, "current 27-place plan"):
                    B.build(pl, "unused tables", "unused game")
                game.assert_not_called()
        with self.assertRaisesRegex(SystemExit, "dedicated 27-team generator"):
            mkccup.parse("CONCACAF|FL_CONCACAF|180|300|300|0|51:1,51:2,51:3,51:4")
        with self.assertRaises(B.BuildError):
            B.continental([{"number": 13}], "unused", "unused")

    def test_recipe_settings_round_trip(self):
        raw = {"modules": {"leagues_cup": True}, "sources": {"mls": [166]}}
        self.assertIn("concacaf", B.RECIPE_SETTINGS)
        self.assertTrue(B.has_edits({"concacaf": {}}))
        pl = {"world": "Test", "leagues": [], "settings": {"concacaf": raw}}
        with patch("mkflags.table", return_value="unused"), patch("mkflags.countries", return_value={}):
            recipe = B.recipe_from_plan(pl, "unused")
        self.assertEqual(raw, recipe["concacaf"])
        self.assertEqual(C.configuration(raw), C.configuration(recipe["concacaf"]))


if __name__ == "__main__":
    unittest.main()
