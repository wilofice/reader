import base64
import curses
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import Mock, patch

import reading_media
import pdf_preview
import test_reader
import test_terminal
from test_preview import sample_pdf


class ReadingMediaTests(unittest.TestCase):
    def test_local_inline_reference_and_html_images_ignore_code_and_network(self):
        source = ('![schéma](<images/a b.png> "titre")\n'
                  '![tableau][T]\n[T]: images/table.png\n'
                  '<img src="images/html.jpg" alt="Photo">\n'
                  '![remote](https://example.com/a.png)\n'
                  '`![inline](ignored.png)`\n'
                  '```md\n![code](ignored.png)\n```\n'
                  '    ![indent](ignored.png)\n')
        images = reading_media.markdown_images(source, Path('/tmp/book/notes.md'))
        self.assertEqual([item['path'] for item in images],
                         [Path('/tmp/book/images/a b.png').resolve(), Path('/tmp/book/images/table.png').resolve(),
                          Path('/tmp/book/images/html.jpg').resolve()])
        self.assertEqual([item['title'] for item in images], ['schéma', 'tableau', 'Photo'])
        for item in images:
            self.assertIn(item['title'], source[item['start']:item['end']])

    def test_encoded_and_parenthesized_paths_and_no_alt_placeholder(self):
        images = reading_media.markdown_images('![](images/a%20b.png) ![x](images/a(b).png)', '/tmp/notes.md')
        self.assertEqual([item['path'].name for item in images], ['a b.png', 'a(b).png'])
        text, offsets = test_reader.reader.markdown_preview('![](a.png)\n')
        self.assertIn('Image', text)
        self.assertLess(offsets[0], images[0]['end'])

    def test_picker_selects_second_item_or_cancels(self):
        screen = Mock()
        screen.getmaxyx.return_value = (12, 60)
        choices = [dict(title='Page 1', page=1), dict(title='Page 2', page=2)]
        screen.getch.side_effect = [curses.KEY_DOWN, 10]
        self.assertEqual(reading_media.choose_media(screen, choices), choices[1])
        screen.getch.side_effect = [27]
        self.assertIsNone(reading_media.choose_media(screen, choices))
        self.assertEqual(reading_media.choose_media(screen, choices[:1]), choices[0])

    def test_quicklook_dispatch_and_missing_image_error(self):
        with tempfile.TemporaryDirectory() as folder:
            image = Path(folder) / 'image.png'
            image.write_bytes(b'placeholder')
            with patch.object(pdf_preview, 'graphics_format', return_value='quicklook'), \
                    patch.object(pdf_preview.sys, 'platform', 'darwin'), \
                    patch.object(pdf_preview.shutil, 'which', return_value='/usr/bin/qlmanage'), \
                    patch.object(pdf_preview, 'inspect_quicklook', return_value=1) as inspect:
                self.assertEqual(pdf_preview.inspect_image(Mock(), image), 1)
                self.assertEqual(inspect.call_args.args[1], image.resolve())
            with self.assertRaises(OSError):
                pdf_preview.inspect_image(Mock(), Path(folder) / 'missing.png')

    @unittest.skipUnless(shutil.which('chafa'), 'Chafa absent')
    def test_terminal_markdown_picker_preview_and_resume(self):
        terminal = test_terminal.TerminalTests()
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            image = folder / 'pixel.png'
            image.write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aVXcAAAAASUVORK5CYII='))
            document = folder / 'notes.md'
            document.write_text('# Lecture\n![Premier](pixel.png)\n![Second](pixel.png)\nSuite.\n')
            args = [str(document), '-S', str(folder / 'state.sqlite3'), '--graphics', 'symbols', '-s', '20']
            output = terminal.session(args, [(0.4, b'v'), (0.3, b'\x1bOB'), (0.2, b'\r'),
                                             (0.6, b'v'), (0.2, b'q')])
            self.assertIn(b'2 image(s) Markdown', output)
            self.assertIn(b'Contenus du passage', output)
            self.assertIn(b'Image Markdown', output)
            self.assertEqual(terminal.status(args)['position'], 0)

    @unittest.skipUnless(all(shutil.which(tool) for tool in ('chafa', 'pdfimages', 'pdftocairo')), 'Poppler/Chafa absent')
    def test_terminal_pdf_picker_opens_selected_page(self):
        terminal = test_terminal.TerminalTests()
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            document = folder / 'sample.pdf'
            sample_pdf(document)
            args = [str(document), '-S', str(folder / 'state.sqlite3'), '--graphics', 'symbols', '-s', '20']
            with patch.dict(os.environ, {'XDG_CACHE_HOME': str(folder / 'cache')}):
                output = terminal.session(args, [(1.2, b'v'), (0.3, b'\x1bOB'), (0.2, b'\r'),
                                                 (0.8, b'v'), (0.2, b'q')], terminal_size=(100, 100))
            self.assertIn(b'Contenus du passage', output)
            self.assertIn(b'page 2/2', output)
            self.assertEqual(terminal.status(args)['position'], 0)
