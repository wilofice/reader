import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import audit_visuals
from test_preview import sample_pdf


HAS_CV = importlib.util.find_spec('cv2') is not None


class AuditTests(unittest.TestCase):
    def test_math_font_xml_controls_are_removed_without_losing_word_boxes(self):
        raw = (b'<doc><page width="100" height="200"><word xMin="1" yMin="2" '
               b'xMax="3" yMax="4">\x0f,x</word></page></doc>')
        with patch.object(audit_visuals, 'command', return_value=raw):
            pages, removed = audit_visuals.word_pages(Path('math.pdf'))
        self.assertEqual(removed, 1)
        self.assertEqual(pages[0]['text'], ',x')
        self.assertEqual(pages[0]['boxes'], [[1, 2, 3, 4]])

    def test_sample_contains_agreements_and_disagreements_without_errors(self):
        rows = [dict(page=n, group=group, error='failed' if group == 'error' else '')
                for n, group in enumerate(('both', 'neither', 'cv_only', 'poppler_only', 'error'), 1)]
        sample = audit_visuals.sample_pages(rows, 4)
        self.assertEqual(set(sample), {1, 2, 3, 4})
        self.assertEqual(sample, audit_visuals.sample_pages(rows, 4))

    @unittest.skipUnless(HAS_CV, 'OpenCV facultatif absent')
    def test_text_mask_is_negative_and_outline_is_positive(self):
        import cv2
        import numpy as np
        image = np.full((1000, 700, 3), 255, dtype=np.uint8)
        cv2.rectangle(image, (100, 100), (500, 150), (0, 0, 0), -1)
        page = dict(width=700, height=1000, boxes=[[95, 95, 505, 155]])
        self.assertFalse(audit_visuals.cv_regions(image, page)['regions'])
        cv2.rectangle(image, (100, 300), (500, 600), (0, 0, 0), 3)
        hint = audit_visuals.cv_regions(image, page)
        self.assertTrue(hint['regions'])
        self.assertGreater(hint['horizontal_pixels'], 0)
        self.assertGreater(hint['vertical_pixels'], 0)
        self.assertFalse(hint['needs_ocr'])

    @unittest.skipUnless(HAS_CV, 'OpenCV facultatif absent')
    def test_no_selectable_text_is_marked_for_review(self):
        import numpy as np
        hint = audit_visuals.cv_regions(np.full((100, 100, 3), 255, dtype=np.uint8),
                                       dict(width=100, height=100, boxes=[]))
        self.assertTrue(hint['needs_ocr'])
        self.assertFalse(hint['regions'])

    @unittest.skipUnless(HAS_CV and all(shutil.which(tool) for tool in
                          ('pdftotext', 'pdftoppm', 'pdfimages', 'pdftocairo')), 'OpenCV/Poppler absents')
    def test_full_audit_generates_inventory_gallery_and_reuses_page_results(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            document = folder / 'document.pdf'
            sample_pdf(document)
            arguments = [str(document), '--output', str(folder / 'audit'), '--sample', '2']
            self.assertEqual(audit_visuals.main(arguments), 0)
            output = next((folder / 'audit').iterdir())
            data = json.loads((output / 'results.json').read_text())
            self.assertEqual(len(data['rows']), 2)
            self.assertTrue(all(row['group'] == 'both' for row in data['rows']))
            self.assertIn('Exporter les annotations', (output / 'review.html').read_text())
            stamp = (output / 'pages/0001.json').stat().st_mtime_ns
            with patch.object(audit_visuals, 'cv_regions', side_effect=AssertionError('recomputation')):
                self.assertEqual(audit_visuals.main(arguments), 0)
            self.assertEqual((output / 'pages/0001.json').stat().st_mtime_ns, stamp)
