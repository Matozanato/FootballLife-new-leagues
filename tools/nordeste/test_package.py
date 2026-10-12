"""Verify the generated game's data and preservation of Sul/Libertadores."""
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import mkleague as M
import pesdb


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package = HERE / "package"
        cls.root = cls.package / "SiderAddons/livecpk/_FL26Nordeste2026"
        cls.db = cls.root / "common/etc/pesdb"
        cls.config = json.loads((cls.package / "nordeste-runtime.json").read_text(encoding="utf-8"))
        cls.raw = bytes(M.load(str(cls.db), "CompetitionRegulation.bin"))
        cls.regs = {int.from_bytes(cls.raw[i+2:i+4],"little"): cls.raw[i:i+M.REG]
                    for i in range(0,len(cls.raw),M.REG)}

    def test_three_masters_no_collision_and_correct_shapes(self):
        """the cup: groups shown (master + A-D of five) and a knockout of eight; the carrier: the
        matches' master and the rows A/B, C/D of ten"""
        self.assertEqual(len(self.raw)//M.REG, len(self.regs))
        shown, matches, ko = self.config["phases"]
        cup = self.config["competition"]
        own = sorted(i for i, r in self.regs.items() if r[M.R_CID] == cup)
        self.assertEqual(own, sorted([shown + 1024 * g for g in range(5)] + [ko]))
        carrier = self.regs[matches][M.R_CID]
        self.assertNotEqual(carrier, cup)
        self.assertEqual(sorted(i for i, r in self.regs.items() if r[M.R_CID] == carrier),
                         [matches, matches + 1024, matches + 2048])
        for master, groups, size in ((shown, 4, 5), (matches, 2, 10)):
            for g in range(groups + 1):
                r = self.regs[master + 1024 * g]
                self.assertEqual(r[9], 2)
                self.assertEqual(r[0x0a], 255 if g == 0 else g - 1)
                self.assertEqual(int.from_bytes(r[6:8], "little"), 0 if not g else master)
                self.assertEqual(r[0x10] & 31, groups)
                self.assertEqual(r[M.R_TEAMS] & 0x3f, 20 if g == 0 else size)
                self.assertEqual((int.from_bytes(r[16:20], "little") >> 12) & 7, 1)
                self.assertLessEqual(len(r[M.R_NAME:M.NAME_END].split(b"\0")[0]), 24)
        k = self.regs[ko]
        flags = int.from_bytes(k[0x10:0x14], "little")
        self.assertEqual((k[9], k[0x0a], k[M.R_TEAMS] & 0x3f), (3, 255, 8))
        self.assertEqual((flags >> 9) & 7, 2)
        self.assertFalse(flags & ((1 << 24) | (1 << 25) | (1 << 28)))
        self.assertTrue(flags & (1 << 27))
        emb = self.root / "common/render/symbol/emblemLc"
        for c in (cup, carrier):
            self.assertTrue((emb / ("emb_%04d_l.png" % c)).exists())

    def test_participants_and_distinct_placeholders(self):
        clubs=self.config["participants"]
        self.assertEqual(len({p["team_id"] for p in clubs}),20)
        teams=pesdb.team_rows(pesdb.load("Team",str(self.db)))
        for p in clubs:
            self.assertEqual(teams[p["team_id"]]["name"],p["database_name"])
            self.assertIn(p["state"],{"BA","SE","AL","PE","PB","RN","CE","PI","MA"})
            if p["squad"]=="mod_placeholder":
                self.assertGreaterEqual(p["team_id"],65536)   # the new-club block, not a club of the game
        self.assertEqual(sum(p["squad"]=="existing" for p in clubs),6)
        raw=M.load(str(self.db),"CompetitionEntry.bin")
        own=[int.from_bytes(raw[i:i+4],"little") for i in range(0,len(raw),M.ENT)
             if raw[i+M.E_CID]==self.config["competition"]]
        self.assertEqual(own,[p["team_id"] for p in clubs])

    def test_preserves_generated_sul_and_libertadores(self):
        original=HERE/"combined-assets/SiderAddons/livecpk/_FL26Nordeste2026/common/etc/pesdb"
        before=bytes(M.load(str(original),"CompetitionRegulation.bin"))
        self.assertEqual(self.raw[:len(before)],before)
        world=(self.root/"fl26world.txt").read_text(encoding="utf-8")
        for marker in ["ccup ", "lpre ", "feed=8", "single=1"]:
            self.assertIn(marker,world)

    def test_runtime_binary_and_config_match(self):
        self.assertEqual((self.package/"SiderAddons/modules/fl26swiss.dll").read_bytes(),
                         (HERE.parent/"native/fl26swiss.dll").read_bytes())
        loader=(self.package/"SiderAddons/modules/fl26swiss.lua").read_text(encoding="utf-8")
        self.assertIn(",".join(map(str,self.config["phases"])),loader)
        self.assertIn(",".join(str(p["team_id"]) for p in self.config["participants"]),loader)


if __name__ == "__main__":
    unittest.main(verbosity=2)
