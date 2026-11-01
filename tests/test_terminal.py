"""Integration checks using a real pseudo-terminal, without changing user state."""

import fcntl
import json
import os
from pathlib import Path
import pty
import select
import struct
import subprocess
import tempfile
import termios
import time
import unittest


EXECUTABLE = str(Path(__file__).resolve().parents[1] / "reader")


class TerminalTests(unittest.TestCase):
    def test_pasted_text_is_saved_and_reopened_by_name(self):
        with tempfile.TemporaryDirectory() as directory:
            state = str(Path(directory) / 'state.sqlite3')
            self.session(['--paste', '-n', 'Mon extrait', '-S', state, '-m', 'w', '-s', '2'],
                         [(.2, 'un deux trois quatre cinq six\n'.encode()), (.1, b'\x04'),
                          (.3, b'n'), (.2, b'q')])
            args = ['--open', 'Mon extrait', '-S', state, '-m', 'w', '-s', '2']
            saved = self.status(args)
            self.assertGreater(saved['position'], 0)
            self.session(args, [(.2, b'q')])
            self.assertEqual(self.status(args)['position'], saved['position'])

    def test_companion_panel_and_zen_do_not_change_progress(self):
        with tempfile.TemporaryDirectory() as directory:
            document = Path(directory) / 'notes.txt'
            document.write_text('La mémoire permet de retenir.\n' * 20)
            args = [str(document), '-S', str(Path(directory) / 'state.sqlite3')]
            output = self.session(args, [(.2, b'e'), (.1, b'1'), (.2, b'z'), (.1, b'z'), (.1, b'e'), (.1, b'q')],
                                  terminal_size=(35, 130))
            self.assertIn(b'Accompagnement IA', output)
            self.assertIn(b'--llm-model', output)
            self.assertEqual(self.status(args)['position'], 0)

    def test_space_pauses_manual_reading_without_advancing_and_p_remains_an_alias(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            document = folder / 'notes.txt'
            document.write_text('un deux trois quatre cinq six')
            args = [str(document), '-S', str(folder / 'state.sqlite3'), '-m', 'w', '-s', '2']
            self.session(args, [(.3, b' '), (1.1, b'q')])
            first = self.status(args)
            self.assertEqual(first['position'], 0)
            self.assertEqual(first['daily_words'], 0)
            self.assertLess(first['reading_seconds'], .9)
            self.session(args, [(.3, b'P'), (.4, b' '), (1.1, b'p'), (.5, b'q')])
            second = self.status(args)
            self.assertEqual(second['position'], 0)
            self.assertGreater(second['reading_seconds'] - first['reading_seconds'], 1)
            self.assertLess(second['reading_seconds'] - first['reading_seconds'], 2)
            self.session(args, [(.3, b'n'), (.2, b'q')])
            self.assertEqual(self.status(args)['daily_words'], 2)

    def test_space_pauses_and_resumes_automatic_progress(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            document = folder / 'notes.txt'
            document.write_text('un deux trois quatre cinq six sept huit')
            args = [str(document), '-S', str(folder / 'state.sqlite3'), '-m', 'w', '-s', '2', '-a', '-w', '120']
            self.session(args, [(.2, b' '), (1.2, b'q')])
            self.assertEqual(self.status(args)['position'], 0)
            self.session(args, [(.2, b'p'), (1.1, b' '), (1.2, b'q')])
            self.assertGreater(self.status(args)['position'], 0)

    def session(self, args, actions, terminal_size=(24, 80), expect_progress=True):
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", *terminal_size, 0, 0))
        original = termios.tcgetattr(slave)
        process = subprocess.Popen(
            [EXECUTABLE, *args], stdin=slave, stdout=slave, stderr=slave,
            env={**os.environ, "TERM": "xterm-256color"},
        )
        output = bytearray()

        def drain(seconds):
            until = time.monotonic() + seconds
            while time.monotonic() < until:
                timeout = min(0.03, max(0, until - time.monotonic()))
                if select.select([master], [], [], timeout)[0]:
                    output.extend(os.read(master, 65536))

        try:
            for delay, keys in actions:
                drain(delay)
                os.write(master, keys)
            until = time.monotonic() + 5
            while process.poll() is None and time.monotonic() < until:
                drain(0.05)
            self.assertEqual(process.poll(), 0, output.decode(errors="replace")[-1000:])
            restored = termios.tcgetattr(slave)
            # macOS sets this transient flag when tcsetattr requests reprocessing.
            pending = getattr(termios, "PENDIN", 0)
            restored[3] &= ~pending
            original[3] &= ~pending
            self.assertEqual(restored, original)
            if expect_progress:
                self.assertIn(b"%", output)
            return bytes(output)
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()
            os.close(master)
            os.close(slave)

    def status(self, args):
        return json.loads(subprocess.check_output([EXECUTABLE, *args, "--status"], text=True))

    def test_zen_hides_chrome_and_reference_returns_to_same_position(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            document = folder / "notes.txt"
            document.write_text("Un passage paisible à lire.\n" * 20)
            args = [str(document), "-S", str(folder / "state.sqlite3"), "-z"]
            output = self.session(args, [(0.4, b"q")], expect_progress=False)
            self.assertIn(b"Un passage paisible", output)
            self.assertNotIn(b"%", output)
            self.assertNotIn(b"notes.txt", output)
            self.assertNotIn(b"Temps cumul", output)
            output = self.session(args, [(0.4, b"i"), (0.2, b"\x1b"), (0.3, b"q")])
            self.assertIn(b"Ligne source : 1", output)
            self.assertEqual(self.status(args)["position"], 0)

    def test_new_cycle_starts_only_after_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            document = folder / "notes.txt"
            document.write_text("Un court texte.")
            args = [str(document), "-S", str(folder / "state.sqlite3")]
            self.session(args, [(0.4, b"N"), (0.2, b"q")])
            self.assertEqual(self.status(args)["reading_number"], 1)
            self.assertEqual(self.status(args)["completed_readings"], 0)
            self.session(args, [(0.4, b"n"), (0.2, b"q")])
            self.assertEqual(self.status(args)["completed_readings"], 1)
            self.session(args, [(0.4, b"N"), (0.2, b"q")])
            status = self.status(args)
            self.assertEqual(status["reading_number"], 2)
            self.assertEqual(status["position"], 0)
            self.assertEqual(status["completed_rereadings"], 0)
            self.session(args, [(0.4, b"n"), (0.2, b"q")])
            self.assertEqual(self.status(args)["completed_readings"], 2)
            self.assertEqual(self.status(args)["completed_rereadings"], 1)

    def test_resume_scroll_and_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            document = folder / "document avec espaces.txt"
            document.write_text("\n".join(f"Ligne {i} avec du texte pour lire." for i in range(100)))
            args = [str(document), "--state", str(folder / "state.sqlite3"), "--size", "3"]
            self.session(args, [(0.6, b"n"), (0.3, b"q")])
            first = self.status(args)["position"]
            self.assertGreater(first, 0)
            self.session(args, [(0.4, b"q")])
            self.assertEqual(self.status(args)["position"], first)
            self.session(args, [(0.4, b"b"), (0.3, b"q")])
            self.assertLess(self.status(args)["position"], first)
            self.session(args + ["--mode", "scroll", "--wpm", "2400"], [(1, b" "), (0.3, b"q")])
            self.assertGreater(self.status(args)["position"], 0)
            document.write_text("Fin.")
            self.session(args + ["--auto", "--wpm", "2400"], [(1, b"q")])
            self.assertEqual(self.status(args)["percent"], 100)

    def test_live_size_changes_and_markdown_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            document = folder / "notes.md"
            document.write_text("# Titre\n\n" + "\n".join(f"**Passage {i}** à lire." for i in range(50)))
            args = [str(document), "--state", str(folder / "state.sqlite3"), "--size", "1"]
            output = self.session(args, [(0.5, b"]"), (0.2, b"n"), (0.2, b"q")])
            self.assertIn(b"Passage : 2 lignes", output)
            self.assertNotIn(b"**Passage", output)
            first = self.status(args)["position"]
            self.assertGreater(first, 0)
            self.session(args, [(0.4, b"q")])
            self.assertEqual(self.status(args)["position"], first)
            self.session(args + ["--raw"], [(0.4, b"q")])
            self.assertEqual(self.status(args)["position"], first)
            output = self.session(args + ["-m", "w", "-s", "20"], [(0.4, b"["), (0.2, b"q")])
            self.assertIn(b"Passage : 10 mots", output)

    def test_help_pauses_auto_and_new_size_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            document = folder / "notes.txt"
            document.write_text(" ".join(f"mot{i}" for i in range(100)))
            args = [str(document), "-S", str(folder / "state.sqlite3"), "-m", "w", "-s", "20"]
            output = self.session(args + ["-a", "-w", "1200"], [(0.4, b"?"), (1.5, b"q")])
            self.assertIn("Raccourcis de lecture".encode(), output)
            self.assertIn("En pause".encode(), output)
            self.assertEqual(self.status(args)["position"], 0)
            self.assertLess(self.status(args)["reading_seconds"], 1.0)
            output = self.session(args, [(0.4, b"j"), (0.2, b"k"), (0.2, b"q")])
            self.assertIn(b"Passage : 10 mots", output)
            self.assertIn(b"Passage : 20 mots", output)
            self.assertEqual(self.status(args)["position"], 0)
            self.session(args, [(0.4, b"?"), (0.2, b"\x1b"), (0.3, b"n"), (0.2, b"q")])
            self.assertGreater(self.status(args)["position"], 0)

    def test_compact_terminal_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            document = folder / "notes.txt"
            document.write_text("Lecture dans un petit terminal.\n" * 20)
            args = [str(document), "-S", str(folder / "state.sqlite3")]
            output = self.session(args, [(0.4, b"n"), (0.2, b"q")], terminal_size=(8, 35))
            self.assertIn(b"notes.txt", output)
            self.assertGreater(self.status(args)["position"], 0)

    def test_reading_time_persists_and_manual_pause_stops_the_clock(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            document = folder / "notes.txt"
            document.write_text("Un passage à lire tranquillement.\n" * 30)
            args = [str(document), "-S", str(folder / "state.sqlite3")]
            output = self.session(args, [(0.6, b"p"), (1.2, b"q")])
            first = self.status(args)["reading_seconds"]
            self.assertGreater(first, 0.2)
            self.assertLess(first, 1.0)
            self.assertIn(b"Temps cumul", output)
            self.assertIn(b"calibrage", output)
            self.session(args, [(0.6, b"q")])
            second = self.status(args)["reading_seconds"]
            self.assertGreater(second, first + 0.3)
            self.assertEqual(second, self.status(args)["reading_seconds"])
            self.assertIsNone(self.status(args)["estimated_remaining_seconds"])

    def test_auto_pause_and_completion_stop_the_clock(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            document = folder / "notes.txt"
            document.write_text("mot " * 100)
            args = [str(document), "-S", str(folder / "state.sqlite3"), "-m", "w", "-s", "20", "-a", "-w", "1200"]
            self.session(args, [(0.4, b"p"), (1.2, b"q")])
            self.assertEqual(self.status(args)["position"], 0)
            self.assertLess(self.status(args)["reading_seconds"], 0.9)
            document.write_text("Fin.")
            before = self.status(args)["reading_seconds"]
            self.session(args, [(1.2, b"q")])
            after = self.status(args)
            self.assertEqual(after["percent"], 100)
            self.assertEqual(after["estimated_remaining_seconds"], 0)
            self.assertLess(after["reading_seconds"] - before, 0.7)


if __name__ == "__main__":
    unittest.main()
