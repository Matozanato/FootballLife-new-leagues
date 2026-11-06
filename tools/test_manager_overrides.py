"""Synthetic Team/Coach tables: python tools/test_manager_overrides.py (no game required)."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import leaguebuilder as B
import mkcoaches as C
import pesdb


def coach(cid, name):
    record = bytearray(C.C_REC)
    record[:4] = cid.to_bytes(4, "little")
    record[4:8] = b"\xab\xcd\xef\x12"  # packed attributes must survive
    for offset in (C.C_NAME1, C.C_NAME2):
        record[offset:offset + C.C_NAME_LEN] = name.encode().ljust(C.C_NAME_LEN, b"\0")
    return bytes(record)


def team(tid, cid):
    record = bytearray(C.T_REC)
    record[:4] = cid.to_bytes(4, "little")
    record[C.T_ID:C.T_ID + 4] = tid.to_bytes(4, "little")
    record[20:24] = b"keep"
    return bytes(record)


def names(raw):
    return {C.u32(raw, o): pesdb.cstr(raw[o + C.C_NAME1:o + C.C_NAME1 + C.C_NAME_LEN])
            for o in range(0, len(raw), C.C_REC)}


class ManagerOverridesTest(unittest.TestCase):
    def setUp(self):
        self.coaches = coach(50, "Shared") + coach(60, "Unique") + coach(70, "Unused")
        self.teams = team(101, 50) + team(102, 50) + team(103, 60)

    def test_unique_and_shared_preserve_records(self):
        coaches, teams, clones = C.rename_coaches(self.coaches, self.teams, {101: "New shared", 103: "New unique"})
        self.assertEqual(clones, {71: 50})
        self.assertEqual(coaches[:C.C_REC], self.coaches[:C.C_REC])
        self.assertEqual(teams[C.T_REC:], self.teams[C.T_REC:])
        self.assertEqual(C.u32(teams, 0), 71)
        self.assertEqual(teams[4:C.T_REC], self.teams[4:C.T_REC])
        self.assertEqual(coaches[-C.C_REC + 4:-C.C_REC + 8], self.coaches[4:8])
        self.assertEqual(coaches[C.C_REC:C.C_REC + 8], self.coaches[C.C_REC:C.C_REC + 8])
        self.assertEqual(names(coaches), {50: "Shared", 60: "New unique", 70: "Unused", 71: "New shared"})
        for o in range(0, len(coaches), C.C_REC):
            self.assertEqual(coaches[o + C.C_NAME1:o + C.C_NAME1 + C.C_NAME_LEN],
                             coaches[o + C.C_NAME2:o + C.C_NAME2 + C.C_NAME_LEN])

    def test_two_shared_edits_are_independent_and_deterministic(self):
        first = C.rename_coaches(self.coaches, self.teams, {102: "Second", 101: "First"})
        self.assertEqual(first, C.rename_coaches(self.coaches, self.teams, {101: "First", 102: "Second"}))
        self.assertEqual(first[2], {71: 50, 72: 50})
        self.assertEqual(names(first[0])[50], "Shared")
        self.assertEqual((C.u32(first[1], 0), C.u32(first[1], C.T_REC)), (71, 72))

    def test_blank_unchanged_and_invalid_are_safe(self):
        self.assertEqual(C.rename_coaches(self.coaches, self.teams, {101: "", 102: "Shared"}),
                         (self.coaches, self.teams, {}))
        for overrides in ({101: "Valid", 103: "é" * 23}, {999: "Missing"}, {101: "Bad\0name"}):
            with self.assertRaises(ValueError):
                C.rename_coaches(bytearray(self.coaches), bytearray(self.teams), overrides)
        with self.assertRaisesRegex(ValueError, "missing"):
            C.rename_coaches(self.coaches, team(101, 999), {101: "New"})

    def test_generated_tables_new_original_mixed_and_portrait(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder) / "source"
            world = Path(folder) / "generated"
            db = world / "common/etc/pesdb"
            base.mkdir()
            db.mkdir(parents=True)
            (base / "Coach.bin").write_bytes(pesdb.wesys_pack(self.coaches))
            (base / "Team.bin").write_bytes(pesdb.wesys_pack(self.teams))
            source_files = {p: p.read_bytes() for p in base.iterdir()}
            self.assertEqual(C.club_names(str(base)), {101: "Shared", 102: "Shared", 103: "Unique"})
            portrait = Path(folder) / "portrait.png"
            portrait.write_bytes(b"source portrait bytes")
            class Source:
                def __init__(self, game, skip):
                    self.game, self.skip = game, skip
                def find(self, rel):
                    assert rel == "common/render/symbol/coach/coach_50.png"
                    return str(portrait)
                def close(self):
                    pass
            plan = {"leagues": [{"name": "Mixed", "teams": [101, 1001], "game_clubs": {"0": {"id": 101}},
                                 "club_coaches": ["Ignored place value", "New club manager"]}],
                    "edits": {"clubs": {"101": {"coach": "Original club manager"}}}}
            with patch("mkcatflags.Source", Source):
                raw = B.write_managers(plan, str(base), str(db), bytearray(self.teams + team(1001, 5000)),
                                       1000, folder, str(world), log=lambda text: None)
            built_coaches = pesdb.wesys_unpack((db / "Coach.bin").read_bytes())
            self.assertEqual(pesdb.wesys_unpack((db / "Team.bin").read_bytes()), raw)
            self.assertEqual(names(built_coaches)[5000], "New club manager")
            self.assertEqual(names(built_coaches)[5001], "Original club manager")
            self.assertEqual(names(built_coaches)[50], "Shared")
            self.assertEqual(C.u32(raw, 0), 5001)
            self.assertEqual(raw[C.T_REC:3 * C.T_REC], self.teams[C.T_REC:])
            self.assertEqual((world / "common/render/symbol/coach/coach_5001.png").read_bytes(), portrait.read_bytes())
            self.assertEqual({p: p.read_bytes() for p in base.iterdir()}, source_files)
            # The existing portrait writer follows the new Team.bin reference, after source copying.
            from PIL import Image
            import lbplayers
            custom = Path(folder) / "custom.png"
            Image.new("RGB", (256, 256), "red").save(custom)
            plan["players"] = {"101": {"coach_portrait": str(custom)}}
            self.assertEqual(lbplayers.coach_portraits(plan, str(world), log=lambda text: None), 1)
            with Image.open(world / "common/render/symbol/coach/coach_5001.png") as im:
                self.assertEqual(im.getpixel((0, 0)), (255, 0, 0, 255))
            self.assertFalse((world / "common/render/symbol/coach/coach_50.png").exists())
            # Rebuild from the source: no accumulating clones or stale overrides.
            B.write_managers({"leagues": [], "edits": {}}, str(base), str(db), bytearray(self.teams),
                             1000, folder, str(world), log=lambda text: None)
            self.assertEqual(pesdb.wesys_unpack((db / "Coach.bin").read_bytes()), self.coaches)

    def test_missing_source_coach_table_is_explicit(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(B.BuildError, "require the source Coach.bin"):
                B.write_managers({"edits": {"clubs": {"101": {"coach": "New"}}}},
                                 folder, folder, self.teams, 1000, folder, folder)
            self.assertFalse((Path(folder) / "Team.bin").exists())


if __name__ == "__main__":
    unittest.main()
