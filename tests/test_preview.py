import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import pdf_preview


def sample_pdf(path):
    """Original two-page fixture: selectable text, a vector diagram and a table."""
    streams = [
        b"BT /F1 20 Tf 50 750 Td (Page one: diagram and table) Tj ET "
        b"0 0 0 RG 50 480 180 100 re S 350 480 180 100 re S "
        b"230 530 m 350 530 l S 340 535 m 350 530 l 340 525 l S "
        b"BT /F1 16 Tf 65 530 Td (Client) Tj 300 0 Td (Server) Tj ET "
        b"50 260 480 120 re S 50 320 m 530 320 l S 280 260 m 280 380 l S "
        b"BT /F1 16 Tf 65 345 Td (Variable) Tj 240 0 Td (Value) Tj ET "
        b"BT /F1 16 Tf 65 285 Td (x) Tj 240 0 Td (2) Tj ET",
        b"BT /F1 20 Tf 50 750 Td (Page two: x = 2) Tj ET "
        b"0 0 1 RG 70 200 m 70 600 l 500 600 l S "
        b"70 250 m 150 300 l 250 350 l 400 500 l S",
    ]
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>",
               b"<< /Type /Pages /Kids [3 0 R 6 0 R] /Count 2 >>",
               b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
               f"<< /Length {len(streams[0])} >>\nstream\n".encode() + streams[0] + b"\nendstream",
               b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 7 0 R >>",
               f"<< /Length {len(streams[1])} >>\nstream\n".encode() + streams[1] + b"\nendstream"]
    pdf, offsets = bytearray(b"%PDF-1.4\n"), []
    for number, obj in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(b"xref\n0 8\n0000000000 65535 f \n")
    for offset in offsets:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(f"trailer\n<< /Size 8 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    path.write_bytes(pdf)


AVAILABLE = shutil.which("pdftoppm") and shutil.which("chafa")


class PreviewTests(unittest.TestCase):
    def test_graphics_fallback_is_conservative_and_override_is_possible(self):
        self.assertEqual(pdf_preview.graphics_format(environment={"TERM": "xterm-256color"}), "symbols")
        self.assertEqual(pdf_preview.graphics_format(environment={"TERM_PROGRAM": "iTerm.app"}), "iterm")
        self.assertEqual(pdf_preview.graphics_format(environment={"TERM": "xterm-kitty"}), "kitty")
        self.assertEqual(pdf_preview.graphics_format(environment={"TERM": "xterm-kitty", "TMUX": "yes"}), "symbols")
        self.assertEqual(pdf_preview.graphics_format("sixels", {}), "sixels")
        self.assertEqual(pdf_preview.graphics_format("iterm2", {}), "iterm")
        with patch.object(pdf_preview.sys, "platform", "darwin"):
            self.assertEqual(pdf_preview.graphics_format(environment={"TERM_PROGRAM": "Apple_Terminal"}), "quicklook")
            self.assertEqual(pdf_preview.graphics_format(environment={"TERM_PROGRAM": "Apple_Terminal", "SSH_CONNECTION": "remote"}), "symbols")
            self.assertEqual(pdf_preview.graphics_format(environment={"TERM_PROGRAM": "Apple_Terminal", "TMUX": "yes"}), "symbols")
        with patch.object(pdf_preview.sys, "platform", "linux"):
            self.assertEqual(pdf_preview.graphics_format(environment={"TERM_PROGRAM": "Apple_Terminal"}), "symbols")

    def test_missing_dependencies_have_an_actionable_error(self):
        with patch.object(pdf_preview.shutil, "which", return_value=None):
            with self.assertRaisesRegex(ValueError, "brew install poppler"):
                pdf_preview.PageRaster("missing.pdf")

    def test_quicklook_closes_only_its_process_and_counts_inspection(self):
        from unittest.mock import Mock
        screen = Mock()
        screen.getmaxyx.return_value = (24, 80)
        screen.getch.return_value = 27
        process = Mock()
        process.poll.return_value = None
        callback = Mock()
        with patch.object(pdf_preview.subprocess, "Popen", return_value=process) as start, \
                patch.object(pdf_preview.time, "monotonic", side_effect=[10, 10.5]):
            elapsed = pdf_preview.inspect_quicklook(screen, Path("page-3.png"), 3, 10, callback)
        self.assertEqual(elapsed, 0.5)
        callback.assert_called_once_with(0.5)
        self.assertEqual(start.call_args.args[0], ["qlmanage", "-p", "page-3.png"])
        process.terminate.assert_called_once()
        process.wait.assert_called_once_with(timeout=2)
        screen.touchwin.assert_called_once()

    def test_quicklook_dispatch_does_not_require_chafa(self):
        from unittest.mock import Mock
        screen = Mock()
        screen.getmaxyx.return_value = (24, 80)
        with patch.object(pdf_preview.sys, "platform", "darwin"), \
                patch.object(pdf_preview.shutil, "which", side_effect=lambda name: None if name == "chafa" else "/usr/bin/" + name), \
                patch.object(pdf_preview, "PageRaster") as raster, \
                patch.object(pdf_preview, "inspect_quicklook", return_value=2) as inspect:
            raster.return_value.page.return_value = Path("page.png")
            self.assertEqual(pdf_preview.inspect_pdf(screen, Path("document.pdf"), 2, 10, "quicklook"), 2)
            self.assertEqual(inspect.call_args.args[1:4], (Path("page.png"), 2, 10))
        with patch.object(pdf_preview.sys, "platform", "linux"):
            with self.assertRaisesRegex(ValueError, "nécessite macOS"):
                pdf_preview.inspect_pdf(screen, Path("document.pdf"), 1, 10, "quicklook")

    def test_timeout_is_reported(self):
        with patch.object(pdf_preview.subprocess, "run", side_effect=subprocess.TimeoutExpired("render", 30)):
            with self.assertRaisesRegex(ValueError, "30 secondes"):
                pdf_preview.checked_run(["render"])

    @unittest.skipUnless(AVAILABLE, "Poppler ou Chafa absent")
    def test_real_pages_zoom_cache_and_protocol_encoding(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            document = folder / "document avec espaces.pdf"
            sample_pdf(document)
            raster = pdf_preview.PageRaster(document, folder / "cache")
            first = raster.page(1)
            self.assertEqual(max(pdf_preview.png_size(first)), 1600)
            stamp = first.stat().st_mtime_ns
            self.assertEqual(raster.page(1).stat().st_mtime_ns, stamp)
            second = raster.page(2)
            self.assertNotEqual(first.read_bytes(), second.read_bytes())
            width, height = pdf_preview.png_size(first)
            cropped = raster.render(1, folder / "zoom", 2, 0, 0, (width, height))
            self.assertEqual(pdf_preview.png_size(cropped), (width, height))
            self.assertNotEqual(first.read_bytes(), cropped.read_bytes())
            for format in ("symbols", "kitty", "iterm"):
                payload = pdf_preview.checked_run(["chafa", "--probe=off", f"--format={format}", "--size=40x15", str(first)])
                self.assertTrue(payload)
                if format == "kitty":
                    self.assertIn(b"\x1b_G", payload)
                elif format == "iterm":
                    self.assertIn(b"1337;File=", payload)
            document.write_bytes(document.read_bytes() + b"\n% revision\n")
            with self.assertRaisesRegex(ValueError, "PDF a changé"):
                raster.page(1)
            self.assertNotEqual(pdf_preview.PageRaster(document, folder / "cache").folder, raster.folder)

    @unittest.skipUnless(AVAILABLE, "Poppler ou Chafa absent")
    def test_viewer_returns_to_text_without_moving_or_completing_cycle(self):
        import test_terminal

        terminal = test_terminal.TerminalTests()
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            document = folder / "preview.pdf"
            sample_pdf(document)
            args = [str(document), "-S", str(folder / "state.sqlite3"), "--graphics", "symbols",
                    "-m", "w", "-s", "5", "-a", "-w", "60"]
            with patch.dict(os.environ, {"XDG_CACHE_HOME": str(folder / "cache")}):
                output = terminal.session(args, [(0.5, b"v"), (1.5, b"+"), (0.6, b"\x1bOB"),
                                                 (0.6, b"n"), (0.6, b"v"), (0.3, b"q")])
            status = terminal.status(args)
            self.assertIn("Aperçu PDF".encode(), output)
            self.assertIn(b"Mode symboles", output)
            self.assertEqual(status["position"], 0)
            self.assertEqual(status["completed_readings"], 0)
            self.assertGreater(status["reading_seconds"], 1)


if __name__ == "__main__":
    unittest.main()
