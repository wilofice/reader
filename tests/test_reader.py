import importlib.machinery
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import subprocess
import shutil
import sqlite3


loader = importlib.machinery.SourceFileLoader("reader", str(Path(__file__).resolve().parents[1] / "reader"))
spec = importlib.util.spec_from_loader(loader.name, loader)
reader = importlib.util.module_from_spec(spec)
loader.exec_module(reader)


class ReadingTests(unittest.TestCase):
    def test_cycles_require_completion_and_do_not_count_reopening(self):
        with tempfile.TemporaryDirectory() as folder:
            memory = reader.Memory(Path(folder) / "state.sqlite3")
            path, text = Path(folder) / "notes.txt", "un deux trois"
            try:
                memory.save(path, text, 3)
                with self.assertRaisesRegex(ValueError, "Terminez"):
                    memory.new_reading(path, text)
                memory.save(path, text, 3)
                self.assertEqual(len(memory.cycles(path, text)), 1)
                stats = memory.timing(path, text)
                stats.seconds = 12
                memory.save(path, text, len(text), stats)
                memory.save(path, text, len(text), stats)
                self.assertEqual(memory.cycles(path, text)[0][1:3], (1, 12))
                memory.new_reading(path, text)
                self.assertEqual(memory.resume(path, text), (0, False))
                with self.assertRaises(ValueError):
                    memory.new_reading(path, text)
                stats.seconds = 30
                memory.save(path, text, len(text), stats)
                rows = memory.cycles(path, text)
                self.assertEqual([row[2] for row in rows], [12, 18])
                self.assertEqual(sum(row[1] for row in rows), 2)
                self.assertEqual(memory.cycles(path, "autre version"), [])
                self.assertEqual(memory.timing(path, text).seconds, 30)
            finally:
                memory.close()

    def test_old_completed_position_imports_one_historical_cycle(self):
        with tempfile.TemporaryDirectory() as folder:
            memory = reader.Memory(Path(folder) / "state.sqlite3")
            path, text = Path(folder) / "notes.txt", "terminé"
            try:
                memory.db.execute("INSERT INTO documents (path,digest,position,length,updated,reading_seconds) VALUES (?,?,?,?,datetime('now'),99)",
                                  (str(path), reader.hashlib.sha256(text.encode()).hexdigest(), len(text), len(text)))
                memory.db.commit()
                memory.new_reading(path, text)
                rows = memory.cycles(path, text)
                self.assertEqual(rows[0][:4], (1, 1, 0, 1))
                self.assertIsNone(rows[0][4])
                self.assertIsNone(rows[0][5])
                self.assertEqual(rows[1][:3], (2, 0, 0))
            finally:
                memory.close()

    def test_pdf_pages_preserve_normalized_offsets_and_empty_pages(self):
        result = subprocess.CompletedProcess([], 0, b"First\n\f\fThird\n\f", b"")
        with patch.object(reader.shutil, "which", return_value="pdftotext"), patch.object(reader.subprocess, "run", return_value=result):
            text, starts = reader.load_document(Path("test.pdf"), "utf-8", with_pages=True)
        self.assertEqual(text, "First\n\n\n\n\nThird\n\n\n")
        self.assertEqual(starts, [0, 8, 10])
        self.assertEqual(text[starts[2]:].split()[0], "Third")

    def test_short_cli_options_match_long_options(self):
        import contextlib
        import io

        with tempfile.TemporaryDirectory() as folder:
            document = Path(folder) / "notes.txt"
            document.write_bytes(b"caf\xe9\n")
            database = str(Path(folder) / "state.sqlite3")

            def invoke(options):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(reader.main(options), 0)
                return output.getvalue()

            for mode in ("l", "w", "s"):
                expected = invoke([str(document), "--status", "--state", database, "--encoding", "latin-1",
                                   "--mode", {"l": "lines", "w": "words", "s": "scroll"}[mode],
                                   "--size", "5", "--auto", "--wpm", "180", "--restart", "--raw"])
                actual = invoke([str(document), "-p", "-S", database, "-e", "latin-1",
                                 "-m", mode, "-s", "5", "-a", "-w", "180", "-r", "-R"])
                self.assertEqual(actual, expected)
            self.assertEqual(invoke(["-H", "-S", database]), invoke(["--history", "--state", database]))

    def test_clock_excludes_pauses_help_auto_samples_and_suspension(self):
        now = [0.0]
        stats = reader.ReadingStats()
        clock = reader.ReadingClock(stats, now=lambda: now[0])

        def advance(seconds):
            for _ in range(seconds):
                now[0] += 1
                clock.tick()

        clock.configure(True, True)
        advance(10)
        clock.complete_passage(20)
        self.assertEqual(stats.seconds, 10)
        self.assertAlmostEqual(stats.manual_wpm, 120)
        clock.configure(False, True)
        advance(8)
        self.assertEqual(stats.seconds, 10)
        clock.configure(True, False)
        advance(5)
        clock.complete_passage(100)
        self.assertEqual(stats.seconds, 15)
        self.assertEqual(stats.manual_words, 20)
        self.assertEqual(stats.manual_seconds, 10)
        now[0] += 100
        clock.tick()
        self.assertEqual(stats.seconds, 15)

    def test_calibration_ignores_skips_and_changed_passages(self):
        now = [0.0]
        stats = reader.ReadingStats()
        clock = reader.ReadingClock(stats, now=lambda: now[0])
        clock.configure(True, True)
        now[0] += 0.1
        clock.complete_passage(100)
        self.assertIsNone(stats.manual_wpm)
        for _ in range(5):
            now[0] += 1
            clock.tick()
        clock.reset_passage()
        now[0] += 1
        clock.complete_passage(100)
        self.assertEqual(stats.manual_words, 0)
        for _ in range(10):
            now[0] += 1
            clock.tick()
        clock.complete_passage(20)
        self.assertAlmostEqual(stats.manual_wpm, 120)

    def test_manual_ui_calibrates_and_saves_an_observed_estimate(self):
        from types import SimpleNamespace

        now = [0.0]
        actions = iter([(1, -1)] * 10 + [(0, ord("n")), (0, ord("q"))])
        frames = []

        class Screen:
            def timeout(self, value):
                pass

            def getmaxyx(self):
                return 24, 80

            def erase(self):
                self.lines = {}

            def addstr(self, y, x, value, style=0):
                self.lines[y] = value

            def refresh(self):
                frames.append(dict(self.lines))

            def getch(self):
                seconds, key = next(actions)
                now[0] += seconds
                return key

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "notes.txt"
            text = " ".join(f"mot{i}" for i in range(100))
            memory = reader.Memory(Path(folder) / "state.sqlite3")
            try:
                args = SimpleNamespace(auto=False, mode="words", wpm=999, size=20)
                with patch.object(reader.time, "monotonic", side_effect=lambda: now[0]):
                    reader.run_ui(Screen(), text, path, memory, args, 0, False)
                stats = memory.timing(path, text)
                self.assertEqual(stats.seconds, 10)
                self.assertAlmostEqual(stats.manual_wpm, 120)
                self.assertIn("00h 01min observé", frames[-1][20])
                self.assertIn("120 mots/min observés", frames[-1][1])
            finally:
                memory.close()

    def test_calibration_also_works_for_single_word_passages(self):
        now = [0.0]
        stats = reader.ReadingStats()
        clock = reader.ReadingClock(stats, now=lambda: now[0])
        clock.configure(True, True)
        for _ in range(40):
            now[0] += 0.25
            clock.complete_passage(1)
        self.assertEqual(stats.manual_wpm, 240)

    def test_remaining_time_uses_configured_or_observed_speed(self):
        text = " ".join(f"mot{i}" for i in range(120))
        words = reader.WordIndex(text)
        stats = reader.ReadingStats()
        position = words.starts[20]
        self.assertEqual(reader.remaining_estimate(words, position, stats, False, 200), (None, "calibrating", None))
        self.assertEqual(reader.remaining_estimate(words, position, stats, True, 240), (25, "configured_speed", 240))
        self.assertEqual(reader.remaining_estimate(words, position, stats, True, 240, words.starts[80], 0.5), (10.5, "configured_speed", 240))
        stats.manual_words, stats.manual_seconds = 20, 10
        self.assertEqual(reader.remaining_estimate(words, position, stats, False, 999), (50, "observed_manual_speed", 120))
        self.assertEqual(reader.remaining_estimate(words, len(text), stats, False, 200), (0, "complete", None))
        self.assertEqual(reader.duration(59.9), "00h 00min")
        self.assertEqual(reader.duration(59.9, rounded_up=True), "00h 01min")
        self.assertEqual(reader.duration(3605), "01h 00min")

    def test_old_database_migration_preserves_positions_and_timing_persists(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "old.sqlite3"
            path = Path(folder) / "notes.txt"
            text = "un deux trois"
            old = sqlite3.connect(db)
            old.execute("CREATE TABLE documents (path TEXT PRIMARY KEY, digest TEXT NOT NULL, position INTEGER NOT NULL, length INTEGER NOT NULL, updated TEXT NOT NULL)")
            old.execute("INSERT INTO documents VALUES (?, ?, ?, ?, datetime('now'))",
                        (str(path), reader.hashlib.sha256(text.encode()).hexdigest(), 3, len(text)))
            old.commit()
            old.close()
            memory = reader.Memory(db)
            self.assertEqual(memory.resume(path, text), (3, False))
            stats = memory.timing(path, text)
            self.assertEqual(stats.seconds, 0)
            stats.seconds, stats.manual_words, stats.manual_seconds = 42, 20, 10
            memory.save(path, text, 3, stats)
            memory.close()
            memory = reader.Memory(db)
            try:
                restored = memory.timing(path, text)
                self.assertEqual(restored.seconds, 42)
                self.assertEqual(restored.manual_wpm, 120)
                changed = memory.timing(path, "nouveau contenu", changed=True)
                self.assertEqual(changed.seconds, 42)
                self.assertIsNone(changed.manual_wpm)
                self.assertIsNone(memory.timing(path, "autre rendu").manual_wpm)
                memory.save(path, text, 0)
                self.assertEqual(memory.timing(path, text).seconds, 42)
            finally:
                memory.close()

    def test_status_estimate_counts_markdown_preview_words(self):
        import contextlib
        import io
        import json

        with tempfile.TemporaryDirectory() as folder:
            document = Path(folder) / "notes.md"
            document.write_text("# Titre\n\n**un deux trois** [source](https://example.com)")
            args = [str(document), "-S", str(Path(folder) / "state.sqlite3"), "-p"]
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(reader.main(args + ["-a", "-w", "60"]), 0)
            result = json.loads(output.getvalue())
            self.assertEqual(result["remaining_words"], 5)
            self.assertEqual(result["estimated_remaining_seconds"], 5)
            self.assertEqual(result["estimate_basis"], "configured_speed")
            self.assertEqual(result["reading_seconds"], 0)

    def test_markdown_preview_and_source_positions(self):
        source = '''<img src="logo.png" />
# Un **titre**

Du *texte*, [un lien](https://example.com) et `nom_fichier *intact*`.[^1][^2]
- [x] Fait
- Suite

```sh
echo "# **code intact**"
```
<span style="display:none">ne pas afficher</span>
[^1]: https://example.com
[^2]: https://example.org
'''
        preview, offsets = reader.markdown_preview(source)
        self.assertIn("Un titre", preview)
        self.assertIn("Du texte, un lien et nom_fichier *intact*.", preview)
        self.assertIn("☑ Fait", preview)
        self.assertIn("• Suite", preview)
        self.assertIn('echo "# **code intact**"', preview)
        for hidden in ("<img", "```", "[^1]", "https://example.com", "ne pas afficher"):
            self.assertNotIn(hidden, preview)
        self.assertEqual(len(offsets), len(preview) + 1)
        self.assertEqual(offsets, sorted(offsets))
        self.assertEqual(offsets[-1], len(source))
        start = preview.index("echo")
        self.assertEqual(offsets[start], source.index("echo"))
        self.assertEqual(reader.bisect_left(offsets, offsets[start]), start)

    def test_markdown_escapes_and_parentheses_in_urls(self):
        preview, _ = reader.markdown_preview(r"Un \*astérisque\* et [article](https://example.com/a_(b)).")
        self.assertEqual(preview, "Un *astérisque* et article.")

    def test_markdown_reference_links_and_hidden_multiline_html(self):
        source = '''Titre
=====
Une [référence][ref], un [ref] et fichier_utile.txt.
<div hidden>
secret
</div>
visible
[ref]: https://example.com
'''
        preview, _ = reader.markdown_preview(source)
        self.assertIn("Une référence, un ref et fichier_utile.txt.", preview)
        self.assertIn("visible", preview)
        self.assertNotIn("secret", preview)
        self.assertNotIn("=====", preview)

    @unittest.skipUnless(shutil.which("pdftotext"), "Poppler absent")
    def test_real_pdf_extraction(self):
        # Minimal valid PDF, including its xref table, with selectable text.
        stream = b"BT /F1 18 Tf 50 750 Td (Reader PDF verification) Tj ET"
        second = b"BT /F1 18 Tf 50 750 Td (Second page with formula x = 2) Tj ET"
        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R 6 0 R] /Count 2 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 7 0 R >>",
            f"<< /Length {len(second)} >>\nstream\n".encode() + second + b"\nendstream",
        ]
        pdf = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for number, obj in enumerate(objects, 1):
            offsets.append(len(pdf))
            pdf.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
        xref = len(pdf)
        pdf.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
        for offset in offsets[1:]:
            pdf.extend(f"{offset:010d} 00000 n \n".encode())
        pdf.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "document test.pdf"
            path.write_bytes(pdf)
            self.assertIn("Reader PDF verification", reader.load_document(path, "utf-8"))
            text, starts = reader.load_document(path, "utf-8", with_pages=True)
            self.assertEqual(len(starts), 2)
            self.assertIn("Second page with formula", text[starts[1]:])
            memory = reader.Memory(Path(folder) / "state.sqlite3")
            memory.save(path.resolve(), text, starts[1])
            memory.close()
            import contextlib
            import io
            import json
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(reader.main([str(path), "-S", str(Path(folder) / "state.sqlite3"), "-p"]), 0)
            status = json.loads(output.getvalue())
            self.assertEqual(status["pdf_page"], 2)
            self.assertEqual(status["pdf_pages"], 2)

    def test_pagination_never_loses_characters(self):
        text = "Début café 漢字\n\n" + "longmot" * 20 + "\n fin du texte\n"
        for mode in ("lines", "words", "scroll"):
            with self.subTest(mode=mode):
                position = 0
                covered = []
                while position < len(text):
                    visible, end = reader.page(text, position, mode, 3, 12, 4)
                    self.assertGreater(end, position)
                    self.assertLessEqual(len(visible), 4)
                    for start, stop, line in visible:
                        self.assertLessEqual(sum(map(reader.cell_width, line)), 12)
                    step = visible[0][1] if mode == "scroll" else end
                    covered.append(text[position:step])
                    position = step
                self.assertEqual("".join(covered), text)

    def test_word_batches_and_screen_limit(self):
        text = "un deux trois quatre cinq six"
        visible, end = reader.page(text, 0, "words", 3, 80, 10)
        self.assertEqual(text[:end].split(), ["un", "deux", "trois"])
        visible, end = reader.page(text, 0, "words", 100, 5, 2)
        self.assertEqual(len(visible), 2)
        self.assertLess(end, len(text))

    def test_previous_and_finished_page(self):
        text = "un\ndeux\ntrois\nquatre\n"
        visible, end = reader.page(text, 0, "lines", 2, 50, 10)
        self.assertEqual(reader.previous(text, end, "lines", 2, 50, 10), 0)
        self.assertEqual(reader.previous(text, end, "scroll", 2, 50, 10), 3)
        self.assertEqual(reader.page(text, len(text), "lines", 2, 50, 10), ([], len(text)))

    def test_memory_survives_reopening_and_detects_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "memory.sqlite3"
            document = Path(folder) / "notes.txt"
            memory = reader.Memory(db)
            memory.save(document, "un deux trois", 3)
            memory.close()
            memory = reader.Memory(db)
            try:
                self.assertEqual(memory.resume(document, "un deux trois"), (3, False))
                self.assertEqual(memory.resume(document, "autre contenu"), (0, True))
                self.assertEqual(memory.resume(Path(folder) / "new.txt", "un deux trois"), (0, False))
                memory.save(document, "un deux trois", 13)
                self.assertEqual(memory.resume(document, "un deux trois"), (13, False))
                self.assertEqual(len(memory.history()), 1)
            finally:
                memory.close()

    def test_load_text_and_pdf_errors(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "notes.txt"
            path.write_bytes(b"\xef\xbb\xbfhello\r\nworld\x1b")
            self.assertEqual(reader.load_document(path, "utf-8-sig"), "hello\nworld")
            pdf = Path(folder) / "sample.pdf"
            with patch.object(reader.shutil, "which", return_value=None):
                with self.assertRaisesRegex(ValueError, "Poppler"):
                    reader.load_document(pdf, "utf-8")
            with patch.object(reader.shutil, "which", return_value="/bin/pdftotext"):
                result = subprocess.CompletedProcess([], 0, b"page one\fpage two", b"")
                with patch.object(reader.subprocess, "run", return_value=result):
                    self.assertEqual(reader.load_document(pdf, "utf-8"), "page one\n\npage two")
                result = subprocess.CompletedProcess([], 0, b"\f \n", b"")
                with patch.object(reader.subprocess, "run", return_value=result):
                    with self.assertRaisesRegex(ValueError, "OCR"):
                        reader.load_document(pdf, "utf-8")


if __name__ == "__main__":
    unittest.main()
