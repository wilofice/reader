from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import date
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import Mock

from focus_ui import choose_focus
from reading_habits import DailyReading, DailyWordIndex, FocusSession, big_clock
import test_reader
import test_terminal


class HabitTests(unittest.TestCase):
    def test_daily_intervals_deduplicate_overlap_and_persist(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'state.sqlite3'
            with closing(sqlite3.connect(path)) as db:
                daily = DailyReading(db)
                self.assertEqual(daily.record('doc', 'digest', 1, 0, 10), 10)
                self.assertEqual(daily.record('doc', 'digest', 1, 5, 15), 5)
                self.assertEqual(daily.record('doc', 'digest', 1, 2, 8), 0)
                self.assertEqual(daily.record('doc', 'digest', 1, 15, 20), 5)
                self.assertEqual(daily.words(), 20)
                self.assertEqual(db.execute('SELECT word_start,word_end FROM daily_coverage').fetchall(), [(0, 20)])
                daily.set_goal(20000)
            with closing(sqlite3.connect(path)) as db:
                daily = DailyReading(db)
                self.assertEqual(daily.words(), 20)
                self.assertEqual(daily.goal, 20000)
                self.assertEqual(daily.record('doc', 'digest', 2, 0, 10), 10)
                self.assertEqual(daily.record('another', 'digest', 1, 0, 10), 10)
                self.assertEqual(daily.words(), 40)

    def test_local_day_rollover_does_not_erase_yesterday(self):
        current = [date(2026, 10, 28)]
        with closing(sqlite3.connect(':memory:')) as db:
            daily = DailyReading(db, today=lambda: current[0])
            daily.record('doc', 'digest', 1, 0, 10)
            current[0] = date(2026, 10, 29)
            self.assertEqual(daily.words(), 0)
            self.assertEqual(daily.record('doc', 'digest', 1, 0, 10), 10)
            self.assertEqual(db.execute('SELECT SUM(words) FROM daily_words').fetchone()[0], 20)

    def test_concurrent_readers_do_not_count_the_same_range_twice(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'state.sqlite3'
            barrier = threading.Barrier(2)
            def record():
                with closing(sqlite3.connect(path)) as db:
                    daily = DailyReading(db)
                    barrier.wait(timeout=5)
                    return daily.record('doc', 'digest', 1, 0, 100)
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: record(), range(2)))
            self.assertEqual(sorted(results), [0, 100])
            with closing(sqlite3.connect(path)) as db:
                self.assertEqual(DailyReading(db).words(), 100)

    def test_daily_index_uses_preview_words_and_ignores_punctuation(self):
        source = '# Titre\n**alpha** beta ! ...\n'
        text, offsets = test_reader.reader.markdown_preview(source)
        index = DailyWordIndex(text, offsets)
        self.assertEqual(index.interval(0, len(source)), (0, 3))
        self.assertEqual(DailyWordIndex('un deux trois').interval(3, 8), (1, 2))

    def test_timer_minimum_finish_once_and_optional_start(self):
        focus = FocusSession()
        self.assertFalse(focus.visible)
        with self.assertRaisesRegex(ValueError, '5 minutes'):
            focus.start('timer', 4, 100)
        focus.start('timer', 5, 100)
        self.assertEqual(focus.display, '05:00')
        self.assertFalse(focus.update(399.5))
        self.assertEqual(focus.display, '00:01')
        self.assertTrue(focus.update(400))
        self.assertEqual(focus.display, '00:00')
        self.assertFalse(focus.update(500))
        focus.stop()
        self.assertFalse(focus.visible)

    def test_chrono_follows_active_reading_time_including_inspection(self):
        focus = FocusSession()
        focus.start('chrono', 25, 100)
        focus.update(110)
        focus.update(110)  # Reading paused / help / machine sleep: total unchanged.
        self.assertEqual(focus.display, '00:10')
        focus.update(115)  # Five seconds inspecting a figure.
        self.assertEqual(focus.display, '00:15')
        self.assertEqual(len(big_clock(focus.display)), 3)
        self.assertGreater(len(big_clock(focus.display)[0]), len(focus.display))

    def test_focus_picker_clamps_minimum_and_supports_both_modes(self):
        screen = Mock()
        screen.getmaxyx.return_value = (24, 80)
        screen.getch.side_effect = [ord('j')] * 10 + [10]
        self.assertEqual(choose_focus(screen, 'timer', 25), ('timer', 5))
        screen.getch.side_effect = [ord('c'), 10]
        self.assertEqual(choose_focus(screen), ('chrono', 25))
        screen.getch.side_effect = [27]
        self.assertIsNone(choose_focus(screen))

    def test_terminal_daily_count_survives_resume_and_counts_new_cycle(self):
        terminal = test_terminal.TerminalTests()
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            document = folder / 'notes.txt'
            document.write_text('un deux trois quatre cinq six')
            args = [str(document), '-S', str(folder / 'state.sqlite3'), '-m', 'w', '-s', '2', '--goal', '6']
            output = terminal.session(args, [(0.3, b'n'), (0.2, b'b'), (0.2, b'n'), (0.2, b'n'), (0.2, b'q')])
            self.assertIn(b'0/6 mots', output)
            self.assertEqual(terminal.status(args)['daily_words'], 4)
            terminal.session(args, [(0.3, b'n'), (0.2, b'q')])
            self.assertEqual(terminal.status(args)['daily_words'], 6)
            terminal.session(args, [(0.3, b'N'), (0.2, b'n'), (0.2, b'q')])
            self.assertEqual(terminal.status(args)['daily_words'], 8)
            result = subprocess.check_output([test_terminal.EXECUTABLE, '--daily', '-S', str(folder / 'state.sqlite3')], text=True)
            self.assertIn('8/6 mots', result)

    def test_raw_markdown_restart_does_not_inflate_daily_words(self):
        terminal = test_terminal.TerminalTests()
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            document = folder / 'notes.md'
            document.write_text('# Titre\n**alpha** beta gamma delta.\n')
            args = [str(document), '-S', str(folder / 'state.sqlite3')]
            terminal.session(args, [(0.3, b'n'), (0.2, b'q')])
            self.assertEqual(terminal.status(args)['daily_words'], 5)
            terminal.session([*args, '--raw', '--restart'], [(0.3, b'n'), (0.2, b'q')])
            self.assertEqual(terminal.status(args)['daily_words'], 5)

    def test_terminal_focus_is_explicit_large_and_not_restarted_on_reopen(self):
        terminal = test_terminal.TerminalTests()
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            document = folder / 'notes.txt'
            document.write_text('Lecture tranquille.\n' * 40)
            args = [str(document), '-S', str(folder / 'state.sqlite3'), '--focus-minutes', '5']
            output = terminal.session(args, [(0.3, b'q')])
            self.assertNotIn(b'FOCUS', output)
            output = terminal.session(args, [(0.3, b'f'), (0.2, b'c'), (0.2, b'\r'), (1.2, b'p'), (0.2, b'q')])
            self.assertIn('FOCUS · CHRONO'.encode(), output)
            self.assertIn('█▀█'.encode(), output)
            self.assertIn(b'pause', output)
            self.assertEqual(terminal.status(args)['position'], 0)
            output = terminal.session(args, [(0.3, b'q')])
            self.assertNotIn(b'FOCUS', output)

    def test_compact_and_zen_keep_controls_and_daily_counter(self):
        terminal = test_terminal.TerminalTests()
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            document = folder / 'notes.txt'
            document.write_text('Lecture tranquille.\n' * 40)
            args = [str(document), '-S', str(folder / 'state.sqlite3'), '-z', '--focus-minutes', '5']
            output = terminal.session(args, [(0.3, b'f'), (0.2, b'\r'), (0.4, b'q')],
                                      terminal_size=(12, 50), expect_progress=False)
            self.assertIn(b'Focus 05:00', output)
            self.assertIn(b'0/15000 mots', output)
            bad = subprocess.run([test_terminal.EXECUTABLE, *args, '--focus-minutes', '4'], capture_output=True)
            self.assertEqual(bad.returncode, 2)
