import contextlib
import io
from pathlib import Path
import tempfile
import unittest

from tests.test_reader import reader


class InboxTests(unittest.TestCase):
    def test_external_document_gets_a_durable_copy_and_keeps_progress(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inbox = root / 'Lectures'
            inbox.mkdir()
            source = root / 'Downloads' / 'article.md'
            source.parent.mkdir()
            text = '# Article\n\nContenu durable.'
            source.write_text(text)
            memory = reader.Memory(root / 'state.sqlite3')
            try:
                memory.save(source.resolve(), text, 9)
                copied = reader.durable_reading_copy(source, inbox)
                memory.relocate(source.resolve(), copied, text)

                self.assertEqual(copied, (inbox / 'article.md').resolve())
                self.assertEqual(copied.read_text(), text)
                self.assertEqual(memory.resume(copied, text)[0], 9)
                self.assertIsNone(memory.db.execute(
                    'SELECT path FROM documents WHERE path=?', (str(source.resolve()),)).fetchone())
                self.assertEqual(reader.durable_reading_copy(source, inbox), copied)
            finally:
                memory.close()

    def test_recursive_discovery_is_idempotent_and_ignores_hidden_or_other_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inbox = root / 'a-lire'
            nested = inbox / 'technique'
            hidden = inbox / '.cache'
            nested.mkdir(parents=True)
            hidden.mkdir()
            markdown = inbox / 'article.md'
            pdf = nested / 'rapport.pdf'
            markdown.write_text('# Article\n\nÀ lire.')
            pdf.write_bytes(b'%PDF-placeholder')
            (inbox / 'notes.txt').write_text('ignoré')
            (hidden / 'secret.md').write_text('ignoré')
            memory = reader.Memory(root / 'state.sqlite3')
            try:
                self.assertEqual(memory.discover(inbox), (2, 2))
                self.assertEqual(memory.discover(inbox), (0, 2))
                entries = memory.history()
                self.assertEqual({Path(row[0]).name for row in entries}, {'article.md', 'rapport.pdf'})
                self.assertTrue(all(row[2] == 0 for row in entries))

                pdf.unlink()
                self.assertEqual(memory.discover(inbox), (0, 1))
                self.assertEqual([Path(row[0]).name for row in memory.history()], ['article.md'])

                text = markdown.read_text()
                memory.save(markdown.resolve(), text, 0)
                self.assertEqual(memory.db.execute(
                    'SELECT COUNT(*) FROM discovered_documents WHERE path=?',
                    (str(markdown.resolve()),)).fetchone()[0], 0)
            finally:
                memory.close()

    def test_folder_is_remembered_and_bare_reader_lists_new_documents(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inbox = root / 'lectures'
            inbox.mkdir()
            document = inbox / 'nouveau.md'
            document.write_text('# Nouveau document')
            state = root / 'state.sqlite3'
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                self.assertEqual(reader.main(['-S', str(state), '--folder', str(inbox)]), 0)
                self.assertEqual(reader.main(['-S', str(state)]), 0)

            rendered = output.getvalue()
            self.assertIn('Dossier de lecture mémorisé', rendered)
            self.assertIn('nouveau.md', rendered)
            self.assertIn('nouveau', rendered)


if __name__ == '__main__':
    unittest.main()
