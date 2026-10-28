import concurrent.futures
from pathlib import Path
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import visual_hints
from test_preview import sample_pdf
import test_terminal


AVAILABLE = shutil.which("pdfimages") and shutil.which("pdftocairo")


class VisualHintTests(unittest.TestCase):
    def test_glyph_definitions_do_not_count_as_drawings(self):
        root = ET.fromstring('<svg><defs><symbol><path d="M0 0 L1 1"/></symbol></defs>'
                             '<use href="#glyph"/><text>Figure</text></svg>')
        self.assertEqual(visual_hints.drawing_count(root), 0)
        root.append(ET.fromstring('<path stroke="black" d="M0 0 L1 1 L2 2 L3 3 L4 4"/>'))
        self.assertGreaterEqual(visual_hints.drawing_count(root), 4)

    def test_masks_and_small_images_are_filtered(self):
        listing = '\n'.join([
            '1 0 image 940 589 rgb 3 8 jpeg no 175 0 150 150 10K 1%',
            '1 1 smask 940 589 gray 1 8 image no 176 0 150 150 1K 1%',
            '1 2 image 40 40 rgb 3 8 jpeg no 177 0 150 150 1K 1%',
            'invalid header'])
        self.assertEqual(visual_hints.image_count(listing, 595 * 842), 1)

    def test_references_and_errors_do_not_claim_a_detected_image(self):
        hint = dict(images=0, paths=0, mention="Figure 3-2", error="")
        self.assertEqual(visual_hints.label(hint), "Référence Figure 3-2")
        hint.update(images=1, error="missing tool")
        self.assertEqual(visual_hints.label(hint), "Référence Figure 3-2")
        hint.update(mention="")
        self.assertEqual(visual_hints.label(hint), "")

    @unittest.skipUnless(AVAILABLE, "Poppler absent")
    def test_real_vectors_cache_and_source_invalidation(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / 'sample.pdf'
            sample_pdf(path)
            index = visual_hints.PdfVisualIndex(path, 'Figure 1\nPage two', [0, 9], folder / 'cache')
            try:
                first, second = index.analyze(1), index.analyze(2)
                self.assertFalse(first['error'], first)
                self.assertGreaterEqual(first['paths'], 4)
                self.assertGreaterEqual(second['paths'], 4)
                self.assertEqual(first['images'], 0)
                self.assertEqual(first['mention'], 'Figure 1')
                with patch.object(index, 'run', side_effect=AssertionError('cache missed')):
                    self.assertEqual(index.analyze(1), first)
                path.write_bytes(path.read_bytes() + b'\n% changed\n')
                self.assertIn('modifié', index.analyze(1)['error'])
            finally:
                index.close()
            changed = visual_hints.PdfVisualIndex(path, '', [0], folder / 'cache')
            self.assertNotEqual(index.folder, changed.folder)
            changed.close()

    def test_missing_tools_preserve_reference_and_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'sample.pdf'
            path.write_bytes(b'placeholder')
            index = visual_hints.PdfVisualIndex(path, 'See Figure 2', [0])
            try:
                with patch.object(visual_hints.shutil, 'which', return_value=None):
                    hint = index.analyze(1)
                self.assertIn('Poppler', hint['error'])
                self.assertEqual(visual_hints.label(hint), 'Référence Figure 2')
            finally:
                index.close()

    def test_multiple_pages_prefer_actual_visual_over_text_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'sample.pdf'
            path.write_bytes(b'placeholder')
            index = visual_hints.PdfVisualIndex(path, '', [0, 1])
            try:
                for number, images in ((1, 0), (2, 1)):
                    future = concurrent.futures.Future()
                    future.set_result(dict(page=number, images=images, paths=0, mention='Figure 2', error=''))
                    index.futures[number] = future
                hint, pending, pages = index.visible(1, 2)
                self.assertEqual(hint['page'], 2)
                self.assertFalse(pending)
                self.assertEqual(len(pages), 2)
            finally:
                index.close()

    def test_close_cancels_running_subprocess(self):
        import sys
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'sample.pdf'
            path.write_bytes(b'placeholder')
            index = visual_hints.PdfVisualIndex(path, '', [0])
            future = index.executor.submit(index.run, [sys.executable, '-c', 'import time; time.sleep(30)'])
            time.sleep(0.1)
            start = time.monotonic()
            index.close()
            self.assertLess(time.monotonic() - start, 2)
            with self.assertRaises(concurrent.futures.CancelledError):
                future.result()

    @unittest.skipUnless(AVAILABLE, "Poppler absent")
    def test_terminal_indicator_zen_and_disable(self):
        terminal = test_terminal.TerminalTests()
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / 'sample.pdf'
            sample_pdf(path)
            args = [str(path), '-S', str(folder / 'state.sqlite3'), '-m', 'w', '-s', '4']
            with patch.dict('os.environ', {'XDG_CACHE_HOME': str(folder / 'cache')}):
                output = terminal.session(args, [(1.5, b'q')])
                self.assertIn('Tracés visuels probables'.encode(), output)
                output = terminal.session([*args, '-z'], [(0.5, b'q')], expect_progress=False)
                self.assertIn('Tracés visuels probables'.encode(), output)
                self.assertNotIn(b'%', output)
                output = terminal.session([*args, '--no-visual-hints'], [(0.5, b'q')])
                self.assertNotIn('Tracés visuels probables'.encode(), output)
            self.assertEqual(terminal.status(args)['position'], 0)
