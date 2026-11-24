"""CONCACAF automatic qualification, covering the planner and the shared Qt draft flow."""
from copy import deepcopy
from itertools import product
import os
import tempfile
from unittest.mock import patch
import unittest

from modstudio import concacaf_allocation as A, qualification_data as Q, competition_catalog as Catalog
from modstudio.pages import qualification as UI
from modstudio.pages.qualification_presentation import allocation_rows
from test_concacaf_integration import league
import test_qualification as T

C = A.C


class AutomaticAccess(unittest.TestCase):
    def setUp(self):
        self.sources = [
            league(51, "USA", range(1, 31), ["mls"]),
            league(52, "Mexico", range(31, 49), ["liga_mx"]),
            league(61, "Guatemala", range(51, 71)),
            league(62, "Honduras", range(71, 91)),
            league(63, "Jamaica", range(91, 103)),
            league(64, "Haiti", range(103, 113)),
            league(65, "Trinidad and Tobago", range(113, 123)),
            league(66, "Dominican Republic", range(123, 133)),
        ]
        self.recipe = {"world": "_FL26AutoConcacaf", "leagues": [], "concacaf": {"version": 3}}
        planner = patch.object(A.B, "plan", side_effect=self.plan)
        planner.start()
        self.addCleanup(planner.stop)

    def plan(self, recipe, _base):
        config = C.integration_draft(recipe)
        return dict(leagues=[], concacaf_integration=dict(
            sources=self.sources, aliases={}, access=C.integration_access(config, self.sources)))

    def allocate(self, switches, regional=None):
        self.recipe["concacaf"].update(modules=dict(zip(C.MODULES, switches)), regional_access=regional or {})
        changes, report = A.generate(self.recipe, "fixture")
        config = C.integration_draft(Q.preview(self.recipe, changes))
        return config, report, changes

    def test_all_eight_combinations(self):
        expected = ((5, 22), (4, 20), (4, 17), (3, 15), (4, 20), (3, 18), (3, 15), (2, 13))
        for switches, totals in zip(product((False, True), repeat=3), expected):
            with self.subTest(switches=switches):
                config, report, changes = self.allocate(switches)
                cup = report["champions_cup"]
                self.assertTrue(cup["ready"])
                self.assertEqual(tuple(cup["configured"][key] for key in C.ACCESS_STAGES), totals)
                overview = {row.target: row.places for row in allocation_rows(
                    (), Q.preview(self.recipe, changes), 6, report)}
                self.assertEqual(tuple(overview[target] for target in (C.ROUND_OF_16, C.TARGET)),
                                 tuple(f"{count} / {count}" for count in totals))
                self.assertNotIn("leagues_cup", config["regional_access"])
                self.assertEqual(A.generate(Q.preview(self.recipe, changes), "fixture")[0], {})

    def test_region_exclusions_cover_leagues_with_zero_regional_places(self):
        regional = {"central_american_cup": [{"source": "61", "rank": rank} for rank in range(1, 21)],
                    "caribbean_cup": [{"source": league, "rank": rank}
                                      for league in ("63", "64") for rank in range(1, 6)]}
        config, report, _ = self.allocate((True, True, True), regional)
        self.assertTrue(report["champions_cup"]["ready"])
        self.assertEqual(config["regional_access"], regional)
        sources = {row["source"] for stage in config["champions_access"].values() for row in stage}
        self.assertEqual(sources, {"51", "52"})
        config, _, _ = self.allocate((False, False, False))
        sources = {row["source"] for stage in config["champions_access"].values() for row in stage}
        self.assertTrue({"62", "65", "66"} <= sources)

    def test_capacity_shortages_and_single_country(self):
        self.sources = [league(51, "USA", [1, 2], ["mls"]), league(61, "Guatemala", [3, 4]),
                        league(63, "Jamaica", range(5, 15))]
        config, report, _ = self.allocate((True, True, True))
        self.assertFalse(report["leagues_cup"]["ready"])
        self.assertFalse(report["central_american_cup"]["ready"])
        self.assertEqual(config["regional_access"]["caribbean_cup"], [{"source": "63", "rank": rank} for rank in range(1, 11)])
        self.assertEqual(report["champions_cup"]["required"], {"round_of_16": 4, "round_one": 20})
        self.assertFalse(report["champions_cup"]["ready"])
        self.assertEqual(len(config["champions_access"]["round_of_16"]), 2)
        self.assertIn("20 places still to assign", A.summary(report))

    def test_redistribution_and_duplicate_prevention(self):
        self.sources = [league(63, "Jamaica", range(1, 6)), league(65, "Trinidad and Tobago", range(6, 12))]
        config, report, _ = self.allocate((False, False, True))
        self.assertTrue(report["caribbean_cup"]["ready"])
        self.assertEqual({row["source"] for row in config["regional_access"]["caribbean_cup"]}, {"63", "65"})
        self.sources.append(league(66, "Dominican Republic", range(1, 6)))
        config, report, _ = self.allocate((False, False, False))
        known = {row["id"]: row["teams"] for row in self.sources}
        selected = [known[row["source"]][row["rank"] - 1]
                    for stage in config["champions_access"].values() for row in stage]
        self.assertEqual(len(selected), len(set(selected)))
        request = C.integration_draft(self.recipe)
        request["modules"]["caribbean_cup"] = True
        request["regional_access"]["caribbean_cup"] = [
            {"source": league, "rank": rank} for league in (63, 66) for rank in range(1, 6)]
        self.assertFalse(C.integration_access(request, self.sources)["caribbean_cup"]["ready"])

    def test_automatic_cup_winners_follow_their_region(self):
        for key, country in ((51, "USA"), (61, "Guatemala"), (63, "Jamaica")):
            self.sources.append(dict(id="cup:" + str(key), country=country, conf=6,
                                     region=C.region(country), kind="cup", capacity=0))
        config, report, _ = self.allocate((False, True, True))
        self.assertTrue(report["champions_cup"]["ready"])
        self.assertIn({"source": "cup:61", "rank": 1}, config["regional_access"]["central_american_cup"])
        self.assertIn({"source": "cup:63", "rank": 1}, config["regional_access"]["caribbean_cup"])
        champions = [row["source"] for rows in config["champions_access"].values() for row in rows]
        self.assertIn("cup:51", champions)
        self.assertNotIn("cup:61", champions)
        self.assertNotIn("cup:63", champions)
        config, report, _ = self.allocate((False, False, False))
        champions = [row["source"] for rows in config["champions_access"].values() for row in rows]
        self.assertTrue({"cup:61", "cup:63"} <= set(champions))

    def test_overview_refreshes_with_the_shared_plan(self):
        self.recipe["concacaf"]["modules"] = dict.fromkeys(C.MODULES, True)
        changes, _ = A.generate(self.recipe, "fixture")
        recipe = Q.preview(self.recipe, changes)
        # The source picker lists the MLS first round alongside its annual table.
        # The builder resolves both to one MLS source, as in the stock FL27 tables.
        picker = (*T.NATIVES, Q.Source("game", "166", "MLS First Round", "USA", 6, 30),
                  Q.Source("game", "51", "MLS annual", "USA", 6, 30))
        def summary(recipe, base):
            return {"concacaf_access": self.plan(recipe, base)["concacaf_integration"]["access"]}
        def check(editor, expected):
            q = editor.qualification
            q._overview_plan.stop()
            q.check_overview_plan()
            overview = {q.summary.topLevelItem(i).text(0): q.summary.topLevelItem(i).text(1)
                        for i in range(q.summary.topLevelItemCount())}
            self.assertEqual([overview[C.NAME + stage] for stage in (" (Round of 16)", " (Round One)")], expected)
        with patch.object(Q, "metadata", return_value=(picker, T.ASSOCIATIONS, T.CONF)), \
                patch.object(UI, "run_job", side_effect=T.inline), \
                patch.object(A.B, "game_tops", return_value=[]), patch.object(A.B, "game_competitions", return_value=[]), \
                patch.object(Catalog, "plan_summary", side_effect=summary), \
                patch("modstudio.pages.continental.run_job", side_effect=T.inline):
            _app, page, editor, _q = T.page_for(recipe, 6)
            check(editor, ["2 / 2", "13 / 13"])
            editor.settings["leagues_cup"].setChecked(False)
            check(editor, ["2 / 3", "13 / 15"])
            T.discard(page)
            editor = T.editor(page)
            check(editor, ["2 / 2", "13 / 13"])
            stage = ("qualification", "concacaf", "round_of_16")
            editor.set_qualification(stage, (True, editor.preview()["concacaf"]["champions_access"]["round_of_16"][:1]))
            check(editor, ["1 / 2", "13 / 13"])
            T.apply(page)
            check(T.editor(page), ["1 / 2", "13 / 13"])
            self.assertTrue(page.project.undo())
            check(T.editor(page), ["2 / 2", "13 / 13"])
            self.assertTrue(page.project.redo())
            check(T.editor(page), ["1 / 2", "13 / 13"])
            page.close()

    def test_standard_qt_draft_flow(self):
        recipe = T.data()
        recipe["concacaf"] = {"version": 3, "champions_access": {"round_one": [{"source": "North", "rank": 2}]}}
        draft = dict(C.integration_draft(recipe), champions_access={"round_of_16": [{"source": "North", "rank": 1}]})
        report = C.integration_access(draft, [league("North", "Canada", range(1, 17))])
        def propose(current, _base):
            changes = {}
            for key, values in draft["champions_access"].items():
                if C.integration_draft(current)["champions_access"].get(key) != values:
                    changes["qualification", "concacaf", key] = (True, values)
            if C.integration_draft(current)["champions_access"].get("round_one"):
                changes["qualification", "concacaf", "round_one"] = (False, [])
            return changes, report
        with patch.object(Q, "metadata", return_value=(T.NATIVES, T.ASSOCIATIONS, T.CONF)), \
                patch.object(UI, "run_job", side_effect=T.inline), patch.object(A, "generate", side_effect=propose), \
                patch.object(A.B, "game_tops", return_value=[]), patch.object(A.B, "game_competitions", return_value=[]), \
                patch.object(UI, "ask", return_value=False) as confirm:
            app, page, e, q = T.page_for(recipe, 6)
            before = deepcopy(app.project.recipe)
            self.assertEqual(q.generate_button.text(), "Auto-assign qualification places")
            q.generate_button.click()
            self.assertTrue(confirm.called)
            self.assertFalse(e.dirty_keys())
            confirm.return_value = True
            q.generate_button.click()
            self.assertEqual(e.preview()["concacaf"], draft)
            self.assertEqual(app.project.recipe, before)
            T.discard(page)
            e = T.editor(page)
            self.assertFalse(e.dirty_keys())
            e.qualification.generate_button.click()
            e.qualification.generate_button.click()
            T.apply(page)
            self.assertEqual(app.project.recipe["concacaf"], draft)
            self.assertTrue(app.project.undo())
            self.assertEqual(app.project.recipe, before)
            self.assertTrue(app.project.redo())
            with tempfile.TemporaryDirectory() as folder:
                path = os.path.join(folder, "auto-concacaf.json")
                app.project.save(path)
                app.project.open(path)
                self.assertEqual(app.project.recipe["concacaf"], draft)
            page.close()


if __name__ == "__main__":
    unittest.main()
