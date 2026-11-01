import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from saved_texts import SavedTexts, clipboard_text
from test_reader import reader


class SavedTextTests(unittest.TestCase):
    def test_named_text_survives_reopen_and_reimport_preserves_progress(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / 'state.sqlite3'
            memory = reader.Memory(state)
            library = SavedTexts(memory.db, state)
            path = library.save('Mon article', '# Titre\n\nUn texte à lire.')
            memory.save(path, path.read_text(), 9)
            memory.close()
            memory = reader.Memory(state)
            try:
                library = SavedTexts(memory.db, state)
                self.assertEqual(library.find('mon ARTICLE'), path)
                self.assertEqual(library.save('Mon article', path.read_text()), path)
                self.assertEqual(memory.resume(path, path.read_text()), (9, False))
                with self.assertRaisesRegex(ValueError, 'autre contenu'):
                    library.save('Mon article', 'Autre document')
                self.assertEqual(memory.resume(path, path.read_text()), (9, False))
                self.assertEqual(library.entries()[0][2], 9)
            finally:
                memory.close()

    def test_empty_text_and_invalid_names_are_rejected_and_paths_stay_inside_library(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / 'state.sqlite3'
            memory = reader.Memory(state)
            try:
                library = SavedTexts(memory.db, state)
                for name, text in [('', 'texte'), ('a\nb', 'texte'), ('Titre', ' \n\t')]:
                    with self.assertRaises(ValueError):
                        library.save(name, text)
                path = library.save('../../extérieur', 'Texte')
                self.assertTrue(path.is_relative_to(Path(directory).resolve() / 'texts'))
                self.assertEqual(path.read_text(), 'Texte')
            finally:
                memory.close()

    def test_cli_piped_import_list_and_named_status(self):
        with tempfile.TemporaryDirectory() as directory:
            common = ['-S', str(Path(directory) / 'state.sqlite3')]
            output = io.StringIO()
            with patch.object(reader.sys, 'stdin', io.StringIO('Un texte persistant.')), contextlib.redirect_stdout(output):
                self.assertEqual(reader.main([*common, '--paste', '-n', 'Article']), 0)
            with contextlib.redirect_stdout(output):
                self.assertEqual(reader.main([*common, '--library']), 0)
                self.assertEqual(reader.main([*common, '--open', 'Article', '-p']), 0)
            self.assertIn('Article', output.getvalue())
            self.assertIn('"position": 0', output.getvalue())

    def test_mac_clipboard_reads_unicode_and_reports_failure(self):
        import subprocess
        with patch('saved_texts.sys.platform', 'darwin'), patch('saved_texts.subprocess.run') as run:
            run.return_value = subprocess.CompletedProcess(['pbpaste'], 0, 'Énergie'.encode(), b'')
            self.assertEqual(clipboard_text(), 'Énergie')
            self.assertEqual(run.call_args.args[0], ['pbpaste'])
            run.return_value.returncode = 1
            with self.assertRaisesRegex(ValueError, 'Impossible'):
                clipboard_text()


if __name__ == '__main__':
    unittest.main()
