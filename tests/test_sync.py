import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from reader_sync import export_bundle, import_bundle
from saved_texts import SavedTexts
from tests.test_reader import reader


class SyncTests(unittest.TestCase):
    def memory(self, folder, name):
        return reader.Memory(Path(folder) / name / 'reading.sqlite3')

    def test_two_databases_merge_progress_time_and_daily_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'a').mkdir()
            (root / 'b').mkdir()
            first = root / 'a' / 'document.txt'
            second = root / 'b' / 'document.txt'
            text = 'un deux trois quatre cinq six sept huit neuf dix'
            first.write_text(text)
            second.write_text(text)
            left = self.memory(root, 'a')
            right = self.memory(root, 'b')
            try:
                left.save(first, text, 8, reader.ReadingStats(seconds=10))
                right.save(second, text, 25, reader.ReadingStats(seconds=18))
                digest = hashlib.sha256(text.encode()).hexdigest()
                left.daily.record(first, digest, 1, 0, 3)
                right.daily.record(second, digest, 1, 3, 7)

                result = import_bundle(left.db, root / 'a' / 'reading.sqlite3',
                                       export_bundle(right.db, root / 'b' / 'reading.sqlite3'))

                self.assertEqual(result['merged'], 1)
                self.assertEqual(result['pending'], 0)
                self.assertTrue(Path(result['backup']).is_file())
                row = left.db.execute('SELECT position, reading_seconds FROM documents WHERE path=?',
                                      (str(first),)).fetchone()
                self.assertEqual(row, (25, 18.0))
                self.assertEqual(left.daily.words(), 7)
            finally:
                left.close()
                right.close()

    def test_unavailable_document_waits_for_matching_file_then_resumes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'source').mkdir()
            (root / 'target').mkdir()
            original = root / 'source' / 'only-there.txt'
            text = 'document distant à reprendre plus tard'
            original.write_text(text)
            source = self.memory(root, 'source')
            target = self.memory(root, 'target')
            try:
                source.save(original, text, 17, reader.ReadingStats(seconds=12))
                bundle = export_bundle(source.db, root / 'source' / 'reading.sqlite3')
                original.unlink()

                result = import_bundle(target.db, root / 'target' / 'reading.sqlite3', bundle)
                self.assertEqual(result['pending'], 1)
                local = root / 'target' / 'renamed.txt'
                local.write_text(text)

                position, changed = target.resume(local, text)

                self.assertFalse(changed)
                self.assertEqual(position, 17)
                self.assertEqual(target.db.execute('SELECT COUNT(*) FROM sync_pending_documents').fetchone()[0], 0)
            finally:
                source.close()
                target.close()

    def test_saved_text_content_and_name_are_portable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'source').mkdir()
            (root / 'target').mkdir()
            source_state = root / 'source' / 'reading.sqlite3'
            target_state = root / 'target' / 'reading.sqlite3'
            source = reader.Memory(source_state)
            target = reader.Memory(target_state)
            try:
                path = SavedTexts(source.db, source_state).save('Extrait important', 'Un texte conservé.')
                source.save(path, path.read_text(), 5)

                result = import_bundle(target.db, target_state, export_bundle(source.db, source_state))

                imported = SavedTexts(target.db, target_state).find('Extrait important')
                self.assertEqual(imported.read_text(), 'Un texte conservé.')
                self.assertEqual(target.resume(imported, imported.read_text())[0], 5)
                self.assertEqual(result['merged'], 1)
            finally:
                source.close()
                target.close()

    def test_cli_exports_and_imports_a_versioned_json_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_state = root / 'source.sqlite3'
            target_state = root / 'target.sqlite3'
            document = root / 'document.txt'
            bundle = root / 'reader-sync.json'
            text = 'mémoire portable'
            document.write_text(text)
            memory = reader.Memory(source_state)
            try:
                memory.save(document, text, 7)
            finally:
                memory.close()

            self.assertEqual(reader.main(['sync', '-S', str(source_state), 'export', str(bundle)]), 0)
            payload = json.loads(bundle.read_text())
            self.assertEqual((payload['format'], payload['version']), ('reader-sync', 1))
            self.assertEqual(reader.main(['sync', '-S', str(target_state), 'import', str(bundle)]), 0)

            target = reader.Memory(target_state)
            try:
                self.assertEqual(target.resume(document, text)[0], 7)
            finally:
                target.close()


if __name__ == '__main__':
    unittest.main()
