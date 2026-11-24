import itertools
import json
import os
from pathlib import Path
import tempfile
import unittest

import concacaf as Q
import leaguebuilder as B
import leagues_probe as LC
import mkconcacaf as G
import mkleague as M
import mkworld as W


def league(reg, country, clubs, roles=()):
    return dict(id=str(reg), kind="league", conf=6, region=Q.region(country),
                country=country, capacity=len(clubs), teams=list(clubs), roles=list(roles))


def draft(champions, switches):
    modules = dict(zip(Q.MODULES, switches))
    counts = Q.domestic_slots(modules)
    rank = itertools.count(1)
    return Q.configuration(dict(version=2, modules=modules,
                                regional_access={"central_american_cup": [dict(source=610, places=20)],
                                                 "caribbean_cup": [dict(source=611, places=6), dict(source=612, places=4)]},
                                champions_access={stage: [dict(source=51, rank=next(rank)) for _ in range(n)]
                                                  for stage, n in counts.items()} if champions else {}))


class AccessTests(unittest.TestCase):
    def setUp(self):
        self.sources = [league(51, "USA", [*LC.MLS, *range(1000, 1012)], ["mls"]),
                        league(609, "Mexico", LC.MX, ["liga_mx"]),
                        league(610, "Guatemala", range(2000, 2020)),
                        league(611, "Haiti", range(2040, 2050)),
                        league(612, "Jamaica", range(2060, 2070))]

    def test_sixteen_access_configurations(self):
        for switches in itertools.product((False, True), repeat=4):
            with self.subTest(switches=switches):
                config = draft(switches[0], switches[1:])
                access = Q.integration_access(config, self.sources)
                self.assertEqual(set(access), {"champions_cup", *(k for k, on in zip(Q.MODULES, switches[1:]) if on)})
                self.assertEqual(access["champions_cup"]["ready"], switches[0])
                self.assertTrue(all(c["ready"] for k, c in access.items() if k != "champions_cup"))
                if switches[0]:
                    plan = Q.explicit_champions_plan(dict(configuration=config, access=access, sources=self.sources))
                    regs = {"module:"+key: 708+i for i, key in enumerate(Q.MODULES)}
                    wire = G.vector(plan, 720, 721, regs)
                    self.assertEqual(wire[0], 3)
                    self.assertEqual(len(plan["places"]), 27)
                    self.assertEqual(sum(p["stage"] == "round_of_16" for p in plan["places"]), 5)
                    self.assertTrue(all(p["preferred"] and not p["fallback"] for p in plan["places"]))

    def test_incomplete_cup_does_not_affect_other_regional_cups(self):
        config = draft(True, (True, True, True))
        config["regional_access"]["caribbean_cup"].pop()
        access = Q.integration_access(config, self.sources)
        self.assertFalse(access["caribbean_cup"]["ready"])
        self.assertFalse(access["champions_cup"]["ready"])
        self.assertTrue(access["central_american_cup"]["ready"])
        self.assertTrue(access["leagues_cup"]["ready"])
        self.assertEqual(access["champions_cup"]["required"], Q.domestic_slots(
            {"leagues_cup": True, "central_american_cup": True}))

    def test_leagues_cup_rejects_manual_access(self):
        config = draft(False, (True, False, False))
        config["regional_access"]["leagues_cup"] = []
        with self.assertRaises(Q.QualificationError):
            Q.configuration(config)

    def test_recipe_round_trip_keeps_disabled_allocations_and_legacy(self):
        old = {"concacaf": {"modules": {"caribbean_cup": True}, "sources": {"mls": [51]}}}
        edit = Q.integration_draft(old)
        self.assertNotIn("champions_cup", edit)
        self.assertEqual(edit["legacy"]["sources"]["mls"], [51])
        self.assertFalse(edit["champions_access"])
        canonical = draft(True, (True, False, False))
        old_v2 = dict(canonical, version=2, champions_cup=False,
                      regional_access={"central_american_cup": [{"source": 610, "places": 20}],
                                       "caribbean_cup": [{"source": 611, "places": 6}, {"source": 612, "places": 4}]})
        self.assertEqual(Q.integration_draft({"concacaf": old_v2}), draft(True, (True, False, False)))
        old_explicit = {"leagues": [{"name": "Club League", "europe": [[3, 13], [0, 13]]}]}
        self.assertEqual(Q.integration_draft(old_explicit)["champions_access"],
                         {"round_one": [{"source": "Club League", "rank": 3},
                                        {"source": "cup:Club League", "rank": 1}]})
        cfg = draft(False, (False, False, False))
        self.assertEqual(Q.configuration(json.loads(json.dumps(cfg))), cfg)

    def test_individual_positions_cups_and_migration_conflicts(self):
        available = self.sources + [dict(id="cup:" + str(rid), kind="cup", conf=6,
                                        region=Q.region(country), country=country, capacity=0)
                                    for rid, country in ((610, "Guatemala"), (611, "Haiti"), (51, "USA"))]
        recipe = {"concacaf": {"version": 2, "modules": {"caribbean_cup": True},
                               "regional_access": {"caribbean_cup": [{"source": 611, "places": 3}]},
                               "champions_access": {"round_one": [{"source": 611, "rank": 1}]}}}
        config = Q.integration_draft(recipe)
        self.assertEqual(config, Q.integration_configuration(config))
        self.assertEqual([1, 2, 3], [row["rank"] for row in config["regional_access"]["caribbean_cup"]])
        self.assertTrue(Q.integration_access(config, available)["champions_cup"]["errors"])

        config = dict(version=3, modules={"central_american_cup": True, "caribbean_cup": True},
                      regional_access={cup: [{"source": source, "rank": rank}
                                            for rank in (3, 4, 6)] + [{"source": "cup:" + str(source), "rank": 1}]
                                       for cup, source in (("central_american_cup", 610), ("caribbean_cup", 611))},
                      champions_access={"round_of_16": [{"source": 610, "rank": 1}, {"source": 611, "rank": 1}],
                                        "round_one": [{"source": 610, "rank": 2}, {"source": 611, "rank": 2},
                                                      {"source": "cup:51", "rank": 1}]})
        access = Q.integration_access(config, available)
        self.assertFalse(any(row["errors"] for row in access.values()))
        for cup, source in (("central_american_cup", "610"), ("caribbean_cup", "611")):
            grouped = Q.group_regional_places(access[cup]["sources"])
            self.assertEqual(grouped, {source: [0, 3, 4, 6]})
            self.assertEqual(Q.initial_regional_field(grouped, {source: list(range(1, 11))}), [1, 3, 4, 6])
        config["champions_access"]["round_one"].append({"source": "cup:610", "rank": 1})
        self.assertTrue(Q.integration_access(config, available)["champions_cup"]["errors"])

    def test_aliases_do_not_allow_duplicate_ranks(self):
        config = draft(True, (False, False, False))
        config["champions_access"]["round_one"][0] = {"source": "MLS alias", "rank": 1}
        access = Q.integration_access(config, self.sources, {"MLS alias": "51"})
        self.assertFalse(access["champions_cup"]["ready"])
        self.assertIn("more than one stage", access["champions_cup"]["errors"][-1])

    @unittest.skipUnless(os.environ.get("CONCACAF_TEST_BASE"), "set CONCACAF_TEST_BASE to the FL27 native table fixture")
    def test_sixteen_staged_generation_configurations(self):
        base = os.environ["CONCACAF_TEST_BASE"]
        self.addCleanup(W.set_cid_wide, M.CID_WIDE)
        W.set_cid_wide(True)
        for switches in itertools.product((False, True), repeat=4):
            with self.subTest(switches=switches), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                db = root / "common/etc/pesdb"
                db.mkdir(parents=True)
                comp, reg, ent = (bytearray(M.load(base, n)) for n in
                                  ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin"))
                for c, s in enumerate(self.sources[1:], 920):
                    M.add_league(comp, reg, ent, c, int(s["id"]), M.enc_region(21), s["country"],
                                 f"FL_TEST_{c}", s["teams"], quiet=True, tier=1)
                data_sources = list(self.sources)
                if all(switches):
                    template = next(row for row in range(0, len(reg), M.REG)
                                    if int.from_bytes(reg[row+2:row+4], "little") == 6)
                    cup_template = reg[template:template+M.REG]
                    for source, rid, country in ((610, 620, "Guatemala"), (612, 621, "Jamaica")):
                        row = bytearray(cup_template)
                        row[2:4] = rid.to_bytes(2, "little")
                        reg.extend(row)
                        data_sources.append(dict(id="cup:" + str(source), runtime_reg=rid, kind="cup", conf=6,
                                                 region=Q.region(country), country=country, capacity=0))
                M.write_tables(temp, comp, reg, ent)
                config = draft(switches[0], switches[1:])
                if all(switches):
                    config["regional_access"]["central_american_cup"][0] = {"source": "cup:610", "rank": 1}
                    config["regional_access"]["caribbean_cup"][0]["rank"] = 9
                    config["regional_access"]["caribbean_cup"][6] = {"source": "cup:612", "rank": 1}
                access = Q.integration_access(config, data_sources)
                plan = dict(leagues=[], season_sums=[[51, 166, 167]], concacaf_integration=dict(
                    configuration=config, access=access, sources=data_sources))
                lines = B.build_concacaf(plan, temp, str(db), lambda *_: None)
                prefixes = ("concacaf 3", "leagues_probe 2", "central_probe 4", "caribbean 3")
                generated = plan["concacaf_emblems"]
                self.assertEqual(set(generated), {str(n) for n, on in zip(Q.CUP_NAMES, switches) if on})
                for prefix, enabled in zip(prefixes, switches):
                    self.assertEqual(sum(line.startswith(prefix) for line in lines), int(enabled), lines)
                if all(switches):
                    by_prefix = {line.split()[0]: list(map(int, line.split("data=")[1].split(",")))
                                 for line in lines if line.startswith(("central_probe ", "caribbean "))}
                    self.assertEqual(by_prefix["central_probe"][5], 620)
                    self.assertEqual(by_prefix["central_probe"][-20:][:3], [0, 2, 3])
                    self.assertEqual(by_prefix["caribbean"][11], 621)
                    self.assertIn(9, by_prefix["caribbean"][-10:])
                    self.assertIn(64, by_prefix["caribbean"][-10:])
                pinned = plan["cup_ids"]
                self.assertEqual(len({row["cid"] for row in pinned.values()}), len(pinned))
                regs = M.load(str(db), "CompetitionRegulation.bin")
                owners = [int.from_bytes(regs[i+2:i+4], "little") for i in range(0, len(regs), M.REG)]
                self.assertEqual(len(set(owners)), len(owners))
                for number, ids in generated.items():
                    row = next(regs[i:i+M.REG] for i in range(0, len(regs), M.REG)
                               if M.reg_cid(regs[i:i+M.REG]) == ids[0])
                    off = M.name_at(0)
                    self.assertEqual(Q.CUP_NAMES[int(number)].encode(), row[off:].split(b"\0", 1)[0])
                M.write_tables(temp, comp, reg, ent)
                disabled = draft(False, (False, False, False))
                turned_off = dict(leagues=[], prev_cup_ids=pinned, concacaf_integration=dict(
                    configuration=disabled, access={}, sources=self.sources))
                self.assertEqual(B.build_concacaf(turned_off, temp, str(db), lambda *_: None), [])
                self.assertEqual(turned_off["cup_ids"], pinned)
                rebuilt = dict(leagues=[], season_sums=[[51, 166, 167]], prev_cup_ids=turned_off["cup_ids"],
                               concacaf_integration=plan["concacaf_integration"])
                self.assertEqual(B.build_concacaf(rebuilt, temp, str(db), lambda *_: None), lines)
                self.assertEqual(rebuilt["cup_ids"], pinned)
