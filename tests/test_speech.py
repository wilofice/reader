import json
import io
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
import wave
from urllib.error import HTTPError

from speech import Speech, synthesize_ollama, text_chunks
from test_reader import reader


class SpeechTests(unittest.TestCase):
    def test_native_mac_player_is_preferred_at_normal_tempo(self):
        from unittest.mock import Mock
        speech = Speech()
        try:
            speech.key = 'passage'
            speech.output = speech.folder / 'passage.wav'
            speech.error_file = (speech.folder / 'error.log').open('wb')
            speech.generator = Mock()
            speech.generator.poll.return_value = 0
            speech.generator.returncode = 0
            player = Mock()
            player.poll.return_value = None
            with patch('speech.sys.platform', 'darwin'), patch('speech.shutil.which', side_effect=lambda name: name), \
                    patch('speech.subprocess.Popen', return_value=player) as launch:
                speech.sync('passage', 'Bonjour.', True, 1.0)
                self.assertEqual(launch.call_args.args[0][0], 'afplay')
                self.assertEqual(speech.state, 'playing')
        finally:
            speech.player = speech.generator = None  # Aucun processus réel dans ce test.
            speech.close()

    def test_broken_ffplay_reports_a_repair_instead_of_a_dyld_dump(self):
        from unittest.mock import Mock
        speech = Speech()
        try:
            (speech.folder / 'error.log').write_text('dyld: Library not loaded: libjxl.0.11.dylib')
            speech.error_file = (speech.folder / 'error.log').open('ab')
            process = Mock(returncode=-6)
            with self.assertRaisesRegex(ValueError, 'tempo ×1.*brew reinstall ffmpeg'):
                speech.check_result(process, 'Lecture audio')
        finally:
            speech.close()

    def test_missing_model_is_downloaded_then_synthesis_retries(self):
        with tempfile.TemporaryDirectory() as directory:
            error = HTTPError('http://localhost/v1/audio/speech', 404, 'Not Found', {},
                              io.BytesIO(b'{"error":{"message":"model phonon:40m-fr not found"}}'))
            job = dict(output=str(Path(directory) / 'audio.wav'), url='http://localhost',
                       model='phonon:40m-fr', voice='default', text='Bonjour.')
            with patch('speech.urlopen', side_effect=[error, io.BytesIO(b'\x00\x00')]), \
                    patch('speech.pull_model') as pull:
                synthesize_ollama(job)
            pull.assert_called_once_with('http://localhost', 'phonon:40m-fr', None)

    def test_both_t_cases_activate_the_voice(self):
        from types import SimpleNamespace
        for key in ('t', 'T'):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as directory:
                keys = iter([ord(key), ord('q')])
                screen = unittest.mock.Mock()
                screen.getmaxyx.return_value = (30, 100)
                screen.getch.side_effect = lambda: next(keys)
                screen.focused.return_value = True
                memory = reader.Memory(Path(directory) / 'state.sqlite3')
                args = SimpleNamespace(auto=False, mode='words', wpm=200, size=2)
                try:
                    with patch.object(reader, 'Speech') as speech:
                        speech.return_value.state = 'preparing'
                        reader.run_ui(screen, 'un deux trois quatre', Path(directory) / 'notes.txt',
                                      memory, args, 0, False)
                        speech.assert_called_once()
                        speech.return_value.sync.assert_called_once()
                        self.assertEqual(memory.daily.words(), 0)
                finally:
                    memory.close()

    def test_chunking_preserves_words_and_limits_each_request(self):
        text = 'Première phrase. ' * 500 + 'x' * 8000
        chunks = list(text_chunks(text))
        self.assertTrue(all(0 < len(chunk) <= 3500 for chunk in chunks))
        self.assertEqual(''.join(text.split()), ''.join(''.join(chunks).split()))

    def test_pcm_api_and_playback_completion_are_separate(self):
        requests = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                job = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                requests.append((self.path, job))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'\x00\x00' * 2400)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                folder = Path(directory)
                player = folder / 'ffplay'
                player.write_text('#!/bin/sh\n/bin/sleep 0.4\n')
                player.chmod(0o700)
                with patch.dict(os.environ, {'PATH': str(folder)}):
                    speech = Speech(url=f'http://127.0.0.1:{server.server_port}')
                    try:
                        until = time.monotonic() + 5
                        while speech.state != 'playing' and time.monotonic() < until:
                            speech.sync((0, 10), 'Bonjour.', True)
                            time.sleep(.02)
                        self.assertEqual(speech.state, 'playing')
                        self.assertFalse(speech.finished)
                        speech.sync((0, 10), 'Bonjour.', False)
                        self.assertEqual(speech.state, 'paused')
                        time.sleep(.5)
                        self.assertIsNone(speech.player.poll())
                        speech.sync((0, 10), 'Bonjour.', True)
                        until = time.monotonic() + 3
                        while not speech.finished and time.monotonic() < until:
                            time.sleep(.02)
                            speech.sync((0, 10), 'Bonjour.', True)
                        self.assertTrue(speech.finished)
                        with wave.open(str(speech.output)) as audio:
                            self.assertEqual(audio.getnframes(), 2400)
                            self.assertEqual(audio.getframerate(), 24000)
                        self.assertEqual(len(requests), 1)
                        self.assertEqual(requests[0][0], '/v1/audio/speech')
                        self.assertNotIn('speed', requests[0][1])
                    finally:
                        speech.close()
                    self.assertFalse(speech.folder.exists())
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_generation_and_pause_do_not_advance_reading_but_audio_completion_does(self):
        from types import SimpleNamespace
        keys = iter([-1, ord(' '), -1, ord('p'), -1, ord('q')])

        class Screen:
            def timeout(self, value): pass
            def getmaxyx(self): return 30, 100
            def erase(self): pass
            def addstr(self, *args): pass
            def refresh(self): pass
            def getch(self): return next(keys)

        class FakeSpeech:
            def __init__(self, *args):
                self.state, self.calls = 'preparing', 0
            def sync(self, key, text, active, rate):
                self.calls += 1
                self.state = 'finished' if self.calls >= 5 else 'preparing'
            @property
            def finished(self): return self.state == 'finished'
            label = 'test'
            def stop(self): pass
            def close(self): pass

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'text.txt'
            text = 'un deux trois quatre cinq six'
            memory = reader.Memory(Path(directory) / 'state.sqlite3')
            args = SimpleNamespace(auto=True, mode='words', wpm=3000, size=2, speak=True)
            try:
                with patch.object(reader, 'Speech', FakeSpeech):
                    reader.run_ui(Screen(), text, path, memory, args, 0, False)
                self.assertEqual(memory.daily.words(), 2)
                self.assertEqual(memory.resume(path, text)[0], len('un deux '))
            finally:
                memory.close()


if __name__ == '__main__':
    unittest.main()
