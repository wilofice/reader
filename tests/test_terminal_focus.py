import curses
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import pdf_preview
import terminal_focus
from terminal_focus import FOCUS_EVENT, FocusScreen, TerminalFocus
import test_reader
import test_terminal


class FocusTests(unittest.TestCase):
    def test_focus_protocol_does_not_quit_or_consume_other_keys(self):
        state = TerminalFocus(environment={})
        screen = Mock()
        screen.getch.side_effect = [27, ord('['), ord('O'), ord('x'),
                                   27, ord('['), ord('I'), curses.KEY_DOWN, 27, -1]
        wrapped = FocusScreen(screen, state)
        self.assertEqual(wrapped.getch(), FOCUS_EVENT)
        self.assertFalse(wrapped.focused())
        self.assertEqual(wrapped.getch(), ord('x'))
        self.assertEqual(wrapped.getch(), FOCUS_EVENT)
        self.assertTrue(wrapped.focused())
        self.assertEqual(wrapped.getch(), curses.KEY_DOWN)
        self.assertEqual(wrapped.getch(), 27)
        self.assertEqual(screen.timeout.call_args.args, (1000,))

    def test_native_fallback_is_throttled_and_remote_sessions_skip_it(self):
        now = [0.0]
        native = Mock()
        native.bundle.return_value = 'com.apple.Terminal'
        with patch.object(terminal_focus.sys, 'platform', 'darwin'), \
                patch.object(terminal_focus, 'MacForeground', return_value=native) as factory:
            state = TerminalFocus(environment={'TERM_PROGRAM': 'Apple_Terminal'}, now=lambda: now[0])
            self.assertTrue(state.focused())
            now[0] = .5
            self.assertTrue(state.focused())
            native.bundle.assert_called_once()
            native.bundle.return_value = 'com.apple.Safari'
            now[0] = 1.1
            self.assertFalse(state.focused())
            calls = native.bundle.call_count
            state.event(False)
            now[0] = 5
            self.assertFalse(state.focused())
            self.assertEqual(native.bundle.call_count, calls)
            native.bundle.return_value = 'com.apple.Terminal'
            state.event(True)
            self.assertTrue(state.focused())
            factory.reset_mock()
            TerminalFocus(environment={'TERM_PROGRAM': 'Apple_Terminal', 'SSH_CONNECTION': 'remote'})
            factory.assert_not_called()

    def test_reading_clock_excludes_background_and_return_transition(self):
        reader = test_reader.reader
        now, focused = [0.0], [True]
        stats = reader.ReadingStats()
        clock = reader.ReadingClock(stats, now=lambda: now[0], focused=lambda: focused[0])
        clock.configure(True, True)
        now[0] = 1
        clock.tick()
        focused[0] = False
        for second in (2, 3, 4):
            now[0] = second
            clock.tick()
        focused[0] = True
        now[0] = 5
        clock.tick()
        self.assertEqual(stats.seconds, 1)
        now[0] = 6
        clock.tick()
        self.assertEqual(stats.seconds, 2)

    def test_quicklook_background_time_is_not_recorded(self):
        screen, process, callback = Mock(), Mock(), Mock()
        screen.getmaxyx.return_value = (24, 80)
        screen.getch.return_value = 27
        screen.focused.return_value = False
        process.poll.return_value = None
        with patch.object(pdf_preview.subprocess, 'Popen', return_value=process), \
                patch.object(pdf_preview.time, 'monotonic', side_effect=[10, 10.5]):
            self.assertEqual(pdf_preview.inspect_quicklook(screen, Path('page.png'), 1, 1, callback), 0)
        callback.assert_not_called()

    def test_terminal_focus_events_freeze_time_and_automatic_progress(self):
        terminal = test_terminal.TerminalTests()
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            document = folder / 'notes.txt'
            document.write_text('un deux trois quatre cinq six sept huit')
            args = [str(document), '-S', str(folder / 'state.sqlite3'), '-m', 'w', '-s', '2', '-a', '-w', '60']
            output = terminal.session(args, [(0.35, b'\x1b[O'), (2.2, b'\x1b[I'), (0.3, b'q')])
            status = terminal.status(args)
            self.assertEqual(status['position'], 0)
            self.assertEqual(status['daily_words'], 0)
            self.assertLess(status['reading_seconds'], 1.4)
            self.assertIn(b'\x1b[?1004h', output)
            self.assertIn(b'\x1b[?1004l', output)
            self.assertIn('fenêtre inactive'.encode(), output)
            terminal.session(args, [(0.35, b'\x1b[O'), (1.2, b'\x1b[I'), (1.85, b'q')])
            self.assertGreater(terminal.status(args)['position'], 0)

    def test_manual_reading_without_keystrokes_counts_while_focused(self):
        terminal = test_terminal.TerminalTests()
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            document = folder / 'notes.txt'
            document.write_text('Un passage à lire tranquillement.')
            args = [str(document), '-S', str(folder / 'state.sqlite3')]
            terminal.session(args, [(1.3, b'q')])
            self.assertGreater(terminal.status(args)['reading_seconds'], .8)
