import importlib.machinery
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import subprocess
import shutil


loader = importlib.machinery.SourceFileLoader("reader", str(Path(__file__).resolve().parents[1] / "reader"))
spec = importlib.util.spec_from_loader(loader.name, loader)
reader = importlib.util.module_from_spec(spec)
loader.exec_module(reader)


class ReadingTests(unittest.TestCase):
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
        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream",
        ]
        pdf = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for number, obj in enumerate(objects, 1):
            offsets.append(len(pdf))
            pdf.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
        xref = len(pdf)
        pdf.extend(b"xref\n0 6\n0000000000 65535 f \n")
        for offset in offsets[1:]:
            pdf.extend(f"{offset:010d} 00000 n \n".encode())
        pdf.extend(f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "document test.pdf"
            path.write_bytes(pdf)
            self.assertIn("Reader PDF verification", reader.load_document(path, "utf-8"))

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
