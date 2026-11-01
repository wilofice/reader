from pathlib import Path
import curses
import unittest
from unittest.mock import Mock

from curated_library import read_catalog_key, select_item


class CatalogSelectionTests(unittest.TestCase):
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
