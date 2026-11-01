import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from enrichment import Companion, validate
from test_reader import reader


def response():
    return dict(title='Comprendre', body='Quel rôle joue la mémoire ?', anchor='La mémoire',
                vocabulary=['mémoire', 'mot absent'], options=['A1', 'B2', 'C3', 'D4'],
                answer=1, explanation='Justification masquée avant la réponse.')


class CompanionTests(unittest.TestCase):
    def test_invented_anchor_is_rejected_and_vocabulary_is_grounded(self):
        with self.assertRaisesRegex(ValueError, 'extrait source'):
            validate(response(), 'Un autre texte', 'qcm')
        data = validate(response(), 'La mémoire permet de retenir.', 'qcm')
        self.assertEqual(data['vocabulary'], ['mémoire'])
        invalid = response()
        invalid['answer'] = True
        with self.assertRaisesRegex(ValueError, 'correction'):
            validate(invalid, 'La mémoire', 'qcm')
        for body in ('?', 'Voici un résumé sans question.'):
            invalid = response()
            invalid['body'] = body
            with self.assertRaisesRegex(ValueError, 'question explicite'):
                validate(invalid, 'La mémoire', 'qcm')

    def test_answer_is_hidden_until_attempt_and_cancel_clears_previous_passage(self):
        with tempfile.TemporaryDirectory() as directory:
            companion = Companion('modele-test', cache=Path(directory))
            try:
                companion.mode = 'qcm'
                companion.result = validate(response(), 'La mémoire permet de retenir.', 'qcm')
                self.assertNotIn(response()['explanation'], '\n'.join(companion.display()))
                self.assertNotIn('Correction : B', '\n'.join(companion.display()))
                companion.choice = 0
                self.assertIn('Correction : B', '\n'.join(companion.display()))
                self.assertIn(response()['explanation'], '\n'.join(companion.display()))
                companion.cancel()
                self.assertIsNone(companion.result)
                self.assertIsNone(companion.choice)
                self.assertNotIn(response()['explanation'], '\n'.join(companion.display()))
            finally:
                companion.close()

    def test_async_request_and_cache_do_not_require_an_installed_model(self):
        requests = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                requests.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({'message': {'content': json.dumps(response())}}).encode())
            def log_message(self, *args): pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                companion = Companion('modele-test', f'http://127.0.0.1:{server.server_port}', Path(directory))
                try:
                    companion.request('La mémoire permet de retenir.', 'qcm', 'Ligne source 1')
                    until = time.monotonic() + 5
                    while companion.process and time.monotonic() < until:
                        time.sleep(.02)
                        companion.poll()
                    self.assertIsNotNone(companion.result, companion.error)
                    self.assertEqual(len(requests), 1)
                    companion.request('La mémoire permet de retenir.', 'qcm', 'Ligne source 1')
                    self.assertIsNone(companion.process)
                    self.assertIsNotNone(companion.result)
                    self.assertEqual(len(requests), 1)
                    self.assertFalse(requests[0]['stream'])
                finally:
                    companion.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_missing_configuration_never_starts_a_model(self):
        companion = Companion()
        try:
            with patch('enrichment.subprocess.Popen') as process:
                companion.request('La mémoire', 'contexte', 'Ligne 1')
                process.assert_not_called()
                self.assertIn('--llm-model', companion.error)
        finally:
            companion.close()


if __name__ == '__main__':
    unittest.main()
