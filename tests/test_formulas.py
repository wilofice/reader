import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import formula_cache
import formula_detection
import formula_index
import layout_worker
import visual_hints
import test_terminal

HAS_PYMUPDF = importlib.util.find_spec('pymupdf') is not None


def fake_page(text, font='Times-Roman', bbox=(80, 200, 450, 230)):
    page = Mock()
    page.rotation = 0
    page.rect.width, page.rect.height = 600, 800
    page.get_text.return_value = {'blocks': [{'lines': [{'bbox': bbox, 'spans': [{'text': text, 'font': font}]}]}]}
    return page


class FormulaTests(unittest.TestCase):
    def test_worker_network_guard_blocks_internet_and_restores_socket(self):
        import socket
        original = socket.socket.connect
        with layout_worker.offline_network():
            with socket.socket() as stream:
                with self.assertRaisesRegex(OSError, 'réseau désactivé'):
                    stream.connect(('127.0.0.1', 9))
        self.assertIs(socket.socket.connect, original)

    def test_typography_detects_math_and_ignores_prose_or_greek_alone(self):
        self.assertTrue(formula_detection.text_regions(fake_page('∀x P(x) ⇒ Q(x)', 'CMMI10')))
        self.assertTrue(formula_detection.text_regions(fake_page('x = y + z = 3')))
        self.assertFalse(formula_detection.text_regions(fake_page('Une phrase en italique sans formule.', 'Times-Italic')))
        self.assertFalse(formula_detection.text_regions(fake_page('Καλημέρα κόσμε', 'Times-Roman')))
        self.assertFalse(formula_detection.text_regions(fake_page('x = 1', bbox=(10, 2, 60, 10))))

    def test_model_boxes_replace_overlapping_text_but_retain_other_evidence(self):
        text = [dict(box=[.1, .1, .3, .2], source='text'), dict(box=[.5, .5, .7, .6], source='text')]
        model = [dict(box=[.09, .09, .31, .21], source='model')]
        self.assertEqual(formula_detection.merge_regions(text, model), model + text[1:])

    def test_corrupt_and_old_cache_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            row = dict(page=1, formulas=1, formula_regions=[dict(box=[0, 0, 1, 1])], method='text', version=formula_cache.VERSION)
            formula_cache.atomic_json(folder / 'page-1.json', row)
            self.assertEqual(formula_cache.read_page(folder, 1), row)
            row['version'] = 'obsolete'
            formula_cache.atomic_json(folder / 'page-1.json', row)
            self.assertIsNone(formula_cache.read_page(folder, 1))
            (folder / 'page-1.json').write_text('{broken')
            self.assertIsNone(formula_cache.read_page(folder, 1))

    def test_unverified_model_is_rejected_before_loading(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'model.pt'
            target.write_bytes(b'untrusted')
            with patch.object(layout_worker, 'model_path', return_value=target):
                with self.assertRaisesRegex(ValueError, 'absent ou invalide'):
                    layout_worker.LayoutModel()

    def test_enrichment_preserves_images_and_reports_formula_failures(self):
        structural = Mock()
        structural.visible.return_value = (None, False, [dict(page=1, images=1, paths=0, mention='', error='')])
        formulas = Mock()
        formulas.visible.return_value = ({1: dict(formulas=2, formula_regions=[], method='hybrid')}, False, '')
        index = formula_index.EnrichedIndex(structural, formulas)
        hint, pending, pages = index.visible(1, 1)
        self.assertEqual(hint['images'], 1)
        self.assertIn('formules', visual_hints.label(hint))
        self.assertFalse(pending)
        formulas.visible.return_value = ({}, False, 'modèle absent')
        hint, _, pages = index.visible(1, 1)
        self.assertEqual(visual_hints.label(hint), 'Image repérée')
        self.assertEqual(pages[0]['formula_error'], 'modèle absent')
        index.close()
        structural.close.assert_called_once()
        formulas.close.assert_called_once()

    def test_worker_shutdown_and_changed_source_do_not_reuse_stale_hints(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'doc.pdf'
            path.write_bytes(b'pdf')
            process = Mock()
            process.poll.return_value = None
            with patch.object(formula_index.subprocess, 'Popen', return_value=process):
                index = formula_index.FormulaIndex(path, 'digest')
            path.write_bytes(b'changed')
            pages, pending, error = index.visible(1, 1)
            self.assertFalse(pages)
            self.assertFalse(pending)
            self.assertIn('modifié', error)
            index.close()
            process.terminate.assert_called_once()
            process.wait.assert_called_once_with(timeout=3)

    def test_source_changed_between_structural_and_formula_indexes_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'doc.pdf'
            path.write_bytes(b'pdf')
            original = path.stat()
            path.write_bytes(b'changed')
            with patch.object(formula_index.subprocess, 'Popen') as start:
                with self.assertRaisesRegex(ValueError, 'PDF modifié'):
                    formula_index.FormulaIndex(path, 'digest', signature=(original.st_size, original.st_mtime_ns))
            start.assert_not_called()

    @unittest.skipUnless(HAS_PYMUPDF, 'PyMuPDF facultatif absent')
    def test_rotated_page_regions_use_display_coordinates(self):
        import pymupdf
        with pymupdf.open() as document:
            page = document.new_page()
            page.insert_text((70, 200), 'x = y + z = 3', fontsize=18)
            page.set_rotation(90)
            regions = formula_detection.text_regions(page)
            self.assertTrue(regions)
            for region in regions:
                self.assertTrue(all(0 <= value <= 1 for value in region['box']))
                self.assertGreater(region['box'][2], region['box'][0])
                self.assertGreater(region['box'][3], region['box'][1])

    @unittest.skipUnless(HAS_PYMUPDF, 'PyMuPDF facultatif absent')
    def test_accelerator_failure_resets_predictor_before_cpu_fallback(self):
        import pymupdf
        model = layout_worker.LayoutModel.__new__(layout_worker.LayoutModel)
        model.device, model.names = 'mps', {}
        model.model = Mock()
        model.model.predict.side_effect = [RuntimeError('unsupported operation'), [Mock(boxes=[])]]
        with pymupdf.open() as document:
            page = document.new_page()
            self.assertEqual(model.regions(page), [])
        self.assertEqual(model.device, 'cpu')
        model.model.to.assert_called_once_with('cpu')
        self.assertIsNone(model.model.predictor)

    @unittest.skipUnless(HAS_PYMUPDF, 'PyMuPDF facultatif absent')
    def test_preparation_prioritizes_requested_page_and_reuses_results(self):
        import pymupdf
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / 'math.pdf'
            with pymupdf.open() as document:
                document.new_page().insert_text((70, 200), 'x = y + z = 3', fontsize=18)
                document.new_page().insert_text((70, 200), 'An ordinary sentence.', fontsize=18)
                document.save(path)
            priority = folder / 'priority.json'
            priority.write_text('[2]')
            seen = []
            detect = formula_detection.text_regions
            def recording(page):
                seen.append(page.number + 1)
                return detect(page)
            with patch.dict(os.environ, {'XDG_CACHE_HOME': str(folder / 'cache')}):
                with patch.object(layout_worker, 'text_regions', side_effect=recording):
                    self.assertEqual(layout_worker.main([str(path), '--method', 'text', '--priority-file', str(priority)]), 0)
                self.assertEqual(seen, [2, 1])
                cache = formula_cache.folder_for(formula_cache.fingerprint(path), 'text')
                self.assertGreater(formula_cache.read_page(cache, 1)['formulas'], 0)
                self.assertEqual(formula_cache.read_page(cache, 2)['formulas'], 0)
                with patch.object(layout_worker, 'text_regions', side_effect=AssertionError('cache missed')):
                    self.assertEqual(layout_worker.main([str(path), '--method', 'text']), 0)

    @unittest.skipUnless(HAS_PYMUPDF and (formula_index.ROOT / '.venv-layout/bin/python').exists(), 'Environnement enrichi absent')
    def test_terminal_formula_indicator_and_prepare_preserve_reading_memory(self):
        import pymupdf
        import subprocess
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / 'math.pdf'
            with pymupdf.open() as document:
                document.new_page().insert_text((70, 200), 'x = y + z = 3', fontsize=18)
                document.save(path)
            state = folder / 'reading.sqlite3'
            args = [str(path), '-S', str(state), '--formulas', 'text']
            with patch.dict(os.environ, {'XDG_CACHE_HOME': str(folder / 'cache')}):
                subprocess.run([test_terminal.EXECUTABLE, *args, '--prepare'], check=True, capture_output=True)
                self.assertFalse(state.exists(), '--prepare must not create or open reading memory')
                terminal = test_terminal.TerminalTests()
                output = terminal.session(args, [(1.2, b'q')])
                self.assertIn('Formule(s) probable(s)'.encode(), output)
                self.assertEqual(terminal.status(args)['position'], 0)
