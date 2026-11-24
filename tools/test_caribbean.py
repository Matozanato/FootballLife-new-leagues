import unittest
from pathlib import Path

import caribbean as C
import concacaf as Q
from modstudio import competition_catalog as UI
from test_concacaf import sources, results


class CaribbeanTests(unittest.TestCase):
    def test_lua_registers_caribbean_atomically_before_champions_cup(self):
        lua = (Path(__file__).resolve().parents[1] / "sider/experimental/fl26swiss.lua").read_text(encoding="utf-8")
        registry = lua.index('caribbean and "fl26_swiss_ccup_caribbean" or "fl26_swiss_ccup"')
        pack = lua.index("register(cbuf, len, #ccups, buf, #caribbean)", registry)
        preliminary = lua.index("load_lpres()", pack)
        champions = lua.index('ffi.cast("fl26_swiss_access_t", cqload)(buf, #cq)', preliminary)
        self.assertLess(registry, pack)
        self.assertLess(pack, preliminary)
        self.assertLess(preliminary, champions)
        self.assertNotIn('GetProcAddress(h, "fl26_swiss_caribbean")', lua)

    def test_capacity_and_redistribution(self):
        rows = sources()
        recipe = {"modules": {"caribbean_cup": True}}
        with self.assertRaisesRegex(Q.QualificationError, "10 unique Caribbean clubs"):
            C.sources(Q.plan(recipe, rows))
        rows.append(dict(id="dr", country="Dominican Republic", region="caribbean", roles=[],
                         conf=6, kind="league", capacity=9, teams=list(range(60, 69))))
        plan = Q.plan(recipe, rows)
        pools = [(s["teams"], quota) for _, s, quota in C.sources(plan)]
        field = C.select(pools)
        self.assertEqual([45, 46, 60, 61, 47, 62, 48, 63, 49, 64], field)
        self.assertEqual(field, C.select([(s["teams"], q) for _, s, q in C.sources(Q.plan(recipe, rows[::-1]))]))

    def test_podium_reserved_before_domestic_places(self):
        plan = Q.plan({"modules": {"caribbean_cup": True}}, sources())
        rows = Q.resolve(plan, results(plan))
        c = [r for r in rows if r["path"] == "caribbean_cup"]
        self.assertEqual([45, 46, 47], [r["club"] for r in c])
        self.assertEqual(["round_of_16", "round_one", "round_one"], [r["stage"] for r in c])
        self.assertEqual(27, len({r["club"] for r in rows}))

    def test_optional_recipe_setting_round_trip(self):
        start = {"concacaf": {"sources": {"mls": [51]}, "caribbean_titles": {"haiti": 810}}}
        setting = next(s for s in UI.SETTINGS if s.key == "caribbean_cup")
        self.assertFalse(UI.setting_value(start, setting))
        edited = UI.preview_recipe(start, {("setting", "caribbean_cup"): True}, {})
        self.assertTrue(UI.setting_value(edited, setting))
        self.assertNotIn("modules", start["concacaf"])
        self.assertEqual({"haiti": 810}, Q.configuration(edited["concacaf"])["legacy"]["caribbean_titles"])


if __name__ == "__main__":
    unittest.main()
