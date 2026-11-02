import contextlib
import io
import json
from pathlib import Path
import curses
import tempfile
import unittest
from unittest.mock import Mock

from curated_library import read_catalog_key, select_item, speech_model_for_language
from tests.test_reader import reader


class CatalogSelectionTests(unittest.TestCase):
    def test_catalogue_language_selects_matching_phonon_model(self):
        self.assertEqual(speech_model_for_language('anglais'), 'phonon:31m-en')
        self.assertEqual(speech_model_for_language('anglais (aperçu français disponible)'), 'phonon:31m-en')
        self.assertEqual(speech_model_for_language('français'), 'phonon:40m-fr')
        self.assertEqual(speech_model_for_language(None), 'phonon:40m-fr')

    def test_open_book_uses_catalogue_language_and_keeps_explicit_override(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            document = folder / 'english.txt'
            document.write_text('A document written in English.', encoding='utf-8')
            state = str(folder / 'state.sqlite3')
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(reader.main(['-S', state, '--attach-book',
                                              'the-world-haass', str(document)]), 0)
            for extra, expected in (([], 'phonon:31m-en'),
                                    (['--speech-model', 'phonon:40m-fr'], 'phonon:40m-fr')):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(reader.main(['-S', state, '--open-book',
                                                  'the-world-haass', '--status', *extra]), 0)
                self.assertEqual(json.loads(output.getvalue())['speech_model'], expected)

    def fake_library(self):
        library = Mock()
        library.entries.return_value = [
            ({'id': 'first', 'title': 'Premier', 'note': '', 'download_url': None}, None, 0, 0),
            ({'id': 'second', 'title': 'Deuxième', 'note': '', 'download_url': None}, Path('/tmp/second.pdf'), 0, 10),
        ]
        return library

    def fake_screen(self, keys):
        screen = Mock()
        screen.getmaxyx.return_value = (20, 90)
        screen.getch.side_effect = keys
        return screen

    def test_down_arrow_selects_and_opens_second_item(self):
        screen = self.fake_screen([curses.KEY_DOWN, 10])

        self.assertEqual(select_item(screen, self.fake_library()), 'second')
        screen.keypad.assert_called_once_with(True)

    def test_selected_row_uses_visible_reverse_attribute(self):
        screen = self.fake_screen([ord('q')])

        self.assertIsNone(select_item(screen, self.fake_library()))
        selected_calls = [call for call in screen.addnstr.call_args_list
                          if call.args and '1. Premier' in call.args[2]]
        self.assertEqual(len(selected_calls), 1)
        self.assertTrue(selected_calls[0].args[4] & curses.A_REVERSE)

    def test_raw_csi_and_application_arrow_sequences_are_decoded(self):
        for sequence, expected in (([27, ord('['), ord('B')], curses.KEY_DOWN),
                                   ([27, ord('O'), ord('A')], curses.KEY_UP)):
            with self.subTest(sequence=sequence):
                screen = self.fake_screen(sequence)
                self.assertEqual(read_catalog_key(screen), expected)
                self.assertEqual(screen.timeout.call_args_list[0].args, (50,))
                self.assertEqual(screen.timeout.call_args_list[-1].args, (-1,))

    def test_raw_down_arrow_moves_catalog_selection(self):
        screen = self.fake_screen([27, ord('['), ord('B'), 10])

        self.assertEqual(select_item(screen, self.fake_library()), 'second')


if __name__ == '__main__':
    unittest.main()
