"""Asset jobs and real Qt editors; fake native metadata, no game Build or install."""
import copy
import json
import os
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from PIL import Image
import continental_emblems as E
import lbassets
import leaguebuilder as B
from test_continental_competitions import (C, NATIVE, make_page, select, editor,
                                           apply, discard, qa)
from modstudio.pages.builder import CompetitionNamesDialog, QFileDialog
from modstudio.pages.cup_editors import CupConflict


class EmblemAssets(unittest.TestCase):
    def test_jobs_and_fallbacks(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = {}
            for mode, colour in (("default", "red"), ("dark", "blue"), ("light", "green")):
                paths[mode] = os.path.join(folder, mode + '.png')
                Image.new('RGBA', (40, 30), colour).save(paths[mode])
            pl = dict(leagues=[], edits={'competitions': {'2': {'logo': paths['default']}}},
                      ccups=[dict(number=9, cid=140, name='Sudamericana', logo=paths['default'])],
                      uecl=True, uecl_logo=paths['default'],
                      cup_ids={'conmebol:' + B.SAM_FIRST_CODE: {'cid': 141}},
                      continental_emblems={'game:2': {'dark': paths['dark'], 'light': paths['light']},
                                           'generated:9': {'dark': paths['dark']},
                                           'uecl': {'light': paths['light']},
                                           'game:1': {'dark': paths['dark']}})
            with patch.object(E, 'native_ids', return_value={2, 3, 5, 8}):
                jobs, _, _ = B.picture_jobs(pl, '.', log=lambda *a: None)
            self.assertEqual(len([j for j in jobs if j[0] == 'continental_variant']), 5)
            self.assertFalse(any('emb_0001' in f for j in jobs for f in j[2]))
            for fn, args, files in jobs:
                B.job_signature((fn, args, files))
                getattr(lbassets, fn)(folder, *args)
            root = os.path.join(folder, *lbassets.EMBLEM_DIR)
            for cid, suffix, colour in ((2, '_w', (0, 0, 255, 255)),
                                        (2, '_b', (0, 128, 0, 255)),
                                        (2, '', (255, 0, 0, 255)),
                                        (140, '_w', (0, 0, 255, 255)),
                                        (140, '_b', (255, 0, 0, 255)),
                                        (141, '_w', (0, 0, 255, 255))):
                for size, px in (('_l', 256), ('_ll', 512)):
                    with Image.open(os.path.join(root, 'emb_%04d%s%s.png' % (cid, suffix, size))) as im:
                        self.assertEqual(im.size, (px, px))
                        self.assertEqual(im.getpixel((px // 2, px // 2)), colour)
            # Variant-only native changes never emit blank/default replacement emblems.
            only = dict(leagues=[], continental_emblems={'game:2': {'dark': paths['dark']}})
            with patch.object(E, 'native_ids', return_value={2}):
                jobs, _, _ = B.picture_jobs(only, '.', log=lambda *a: None)
            self.assertEqual([j[0] for j in jobs], ['continental_variant'])
            self.assertEqual(jobs[0][2], E.files(2, 'dark'))
            only[E.ROOT]['game:2']['dark'] = os.path.join(folder, 'missing.png')
            gone = set()
            with patch.object(E, 'native_ids', return_value={2}):
                jobs, _, _ = B.picture_jobs(only, '.', log=lambda *a: None, gone=gone)
            self.assertEqual(jobs, [])
            self.assertEqual(gone, set(E.files(2, 'dark')))
            self.assertIn(E.ROOT, B.RECIPE_SETTINGS)
            self.assertTrue(B.has_edits(only))
            self.assertEqual(json.loads(json.dumps(only)), only)
            # Existing world export carries generated assets and the plan unchanged.
            from modstudio import installer
            world = '_FL26EmblemExport'
            sider = os.path.join(folder, 'sider')
            world_root = os.path.join(sider, 'livecpk', world)
            lbassets.continental_variant(world_root, 2, 'dark', paths['dark'])
            os.makedirs(world_root, exist_ok=True)
            with open(os.path.join(world_root, 'fl26world.txt'), 'w') as stream:
                stream.write('world ' + world + '\n')
            with open(os.path.join(world_root, 'leaguebuilder-plan.json'), 'w') as stream:
                json.dump(pl, stream)
            exported = os.path.join(folder, 'world.zip')
            installer.export_world(sider, world, exported)
            with zipfile.ZipFile(exported) as archive:
                prefix = 'SiderAddons/livecpk/' + world + '/'
                self.assertTrue(all(prefix + rel in archive.namelist() for rel in E.files(2, 'dark')))
                restored = json.loads(archive.read(prefix + 'leaguebuilder-plan.json'))
                self.assertEqual(restored[E.ROOT], pl[E.ROOT])


class EmblemEditors(unittest.TestCase):
    def setUp(self):
        self.patches = [patch.object(C.B, 'game_competitions', return_value=NATIVE),
                        patch.object(C.B, 'game_tops', return_value=[(1, 'Original', False)])]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)
        self.app, self.page = make_page()
        self.addCleanup(self.page.close)
        self.p = self.app.project

    def dialog(self):
        d = CompetitionNamesDialog(None, self.p)
        self.addCleanup(d.close)
        return d

    def test_draft_history_and_legacy_sync(self):
        original = copy.deepcopy(self.p.recipe)
        e = select(self.page, 'game:ucl')
        e.variant_logos['dark'].path = 'dark.png'
        e.variant_logos['dark'].changed()
        self.assertEqual(self.p.recipe, original)
        # A disjoint legacy edit must merge without overwriting the CUPS draft.
        d = self.dialog()
        d.variant_logos['light'].path = 'light.png'
        self.assertTrue(d.apply_to(self.p.recipe))
        self.p.touch()
        qa.processEvents()
        apply(self.page)
        self.assertEqual(self.p.recipe[E.ROOT]['game:2'], {'dark': 'dark.png', 'light': 'light.png'})
        self.p.undo(); qa.processEvents()
        self.assertEqual(self.p.recipe[E.ROOT]['game:2'], {'light': 'light.png'})
        self.p.redo(); qa.processEvents()
        self.assertEqual(self.p.recipe[E.ROOT]['game:2']['dark'], 'dark.png')
        d = self.dialog()
        self.assertEqual(d.variant_logos['dark'].path, 'dark.png')
        d.variant_logos['dark'].clear()
        d.reject()
        self.assertEqual(self.p.recipe[E.ROOT]['game:2']['dark'], 'dark.png')
        e = select(self.page, 'game:ucl')
        e.variant_logos['light'].clear()
        discard(self.page)
        self.assertEqual(editor(self.page).variant_logos['light'].path, 'light.png')

    def test_visibility_pick_clear_and_conflict(self):
        d = self.dialog()
        before = copy.deepcopy(self.p.recipe)
        self.assertFalse(d.apply_to(self.p.recipe))
        self.assertEqual(before, self.p.recipe)
        i = next(i for i, row in enumerate(d.rows) if row[1] == '98')
        d.list.setCurrentRow(i)
        self.assertTrue(all(w.isHidden() for w in d.variant_logos.values()))
        i = next(i for i, row in enumerate(d.rows) if row[:2] == ('game', '2'))
        d.list.setCurrentRow(i)
        with patch.object(QFileDialog, 'getOpenFileName', return_value=('dark.png', '')):
            d.variant_logos['dark'].pick()
        d.variant_logos['light'].path = 'light.png'
        d.variant_logos['dark'].clear()
        self.assertEqual(d.variant_logos['light'].path, 'light.png')
        d.variant_logos['dark'].path = 'draft.png'
        self.p.recipe[E.ROOT] = {'game:2': {'dark': 'newer.png'}}
        before = copy.deepcopy(self.p.recipe)
        with self.assertRaises(CupConflict):
            d.apply_to(self.p.recipe)
        self.assertEqual(before, self.p.recipe)

    def test_cups_detects_legacy_same_field_conflict(self):
        e = select(self.page, 'game:ucl')
        e.variant_logos['dark'].path = 'cups-draft.png'
        e.variant_logos['dark'].changed()
        d = self.dialog()
        d.variant_logos['dark'].path = 'dialog-applied.png'
        d.apply_to(self.p.recipe)
        self.p.touch()
        qa.processEvents()
        with self.assertRaises(CupConflict):
            editor(self.page).apply(self.p.recipe)
        self.assertEqual(self.p.recipe[E.ROOT]['game:2']['dark'], 'dialog-applied.png')
        self.assertEqual(editor(self.page).variant_logos['dark'].path, 'cups-draft.png')

    def test_generated_and_uecl(self):
        for key, stored in (('generated:8', 'generated:8'), ('uecl', 'uecl')):
            e = select(self.page, key)
            e.variant_logos['dark'].path = key + '.png'
            e.variant_logos['dark'].changed()
            apply(self.page)
            d = self.dialog()
            i = next(i for i, c in enumerate(d._entries) if c.key == key)
            d.list.setCurrentRow(i)
            self.assertEqual(d.variant_logos['dark'].path, key + '.png')
            self.assertEqual(self.p.recipe[E.ROOT][stored]['dark'], key + '.png')

    def test_world_switch_and_save_reload(self):
        e = select(self.page, 'game:ucl')
        e.variant_logos['dark'].path = 'world-a.png'
        e.variant_logos['dark'].changed()
        first_recipe = self.p.recipe
        d = self.dialog()
        other = dict(world='_FL26OtherEmblems', leagues=[],
                     continental_emblems={'game:2': {'dark': 'world-b.png'}})
        self.p.adopt(other, None)
        qa.processEvents()
        e = select(self.page, 'game:ucl')
        self.assertEqual(e.variant_logos['dark'].path, 'world-b.png')
        with self.assertRaises(CupConflict):
            d.apply_to(self.p.recipe)
        self.p.adopt(first_recipe, None)
        qa.processEvents()
        e = select(self.page, 'game:ucl')
        self.assertEqual(e.variant_logos['dark'].path, 'world-a.png')
        apply(self.page)
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'recipe.json')
            with open(path, 'w') as stream:
                json.dump(self.p.recipe, stream)
            with open(path) as stream:
                loaded = json.load(stream)
            self.assertEqual(loaded[E.ROOT], self.p.recipe[E.ROOT])

    def test_responsive_variant_controls(self):
        e = select(self.page, 'game:ucl')
        d = self.dialog()
        d.resize(900, 600)
        d.show()
        for width in (1080, 1400):
            self.page.resize(width, 640)
            qa.processEvents()
            for picture in e.variant_logos.values():
                self.assertLessEqual(picture.geometry().right(), picture.parentWidget().width())
                self.assertGreaterEqual(picture.width(), picture.minimumSizeHint().width())
        qa.processEvents()
        for picture in d.variant_logos.values():
            self.assertLessEqual(picture.geometry().right(), picture.parentWidget().width())
            self.assertGreaterEqual(picture.width(), picture.minimumSizeHint().width())


if __name__ == '__main__':
    unittest.main()
