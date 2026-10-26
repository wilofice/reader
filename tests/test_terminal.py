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
    def session(self, args, actions, terminal_size=(24, 80)):
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


if __name__ == "__main__":
    unittest.main()
