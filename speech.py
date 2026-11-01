"""Synthèse isolée et lecture audio pilotée par la session du terminal."""

import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import wave

from ollama_models import error_body, model_missing, pull_model, read_status


def text_chunks(text, limit=3500):
    text = text.strip()
    while text:
        end = min(len(text), limit)
        if end < len(text):
            boundary = max(text.rfind('\n', 0, end), text.rfind('. ', 0, end), text.rfind(' ', 0, end))
            if boundary > 0:
                end = boundary + 1
        yield text[:end]
        text = text[end:].lstrip()


def synthesize_ollama(job):
    """PCM brut : reconstruire un WAV de longueur exacte avant lecture."""
    destination = Path(job['output'])
    with wave.open(str(destination), 'wb') as output:
        output.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
        total = 0
        installed_missing_model = False
        for chunk in text_chunks(job['text']):
            request = Request(job['url'].rstrip('/') + '/v1/audio/speech',
                              data=json.dumps(dict(model=job['model'], voice=job['voice'],
                                                   input=chunk, response_format='pcm')).encode(),
                              headers={'Content-Type': 'application/json'})
            try:
                with urlopen(request, timeout=60) as response:
                    data = response.read(32 * 1024 * 1024 + 1)
            except HTTPError as error:
                if not installed_missing_model and model_missing(error):
                    pull_model(job['url'], job['model'], job.get('status'))
                    installed_missing_model = True
                    request = Request(job['url'].rstrip('/') + '/v1/audio/speech',
                                      data=json.dumps(dict(model=job['model'], voice=job['voice'],
                                                           input=chunk, response_format='pcm')).encode(),
                                      headers={'Content-Type': 'application/json'})
                    try:
                        with urlopen(request, timeout=60) as response:
                            data = response.read(32 * 1024 * 1024 + 1)
                    except HTTPError as retry_error:
                        detail = retry_error.read(2000).decode('utf-8', errors='replace')
                        raise ValueError(f'Ollama audio HTTP {retry_error.code} : {detail}') from retry_error
                else:
                    detail = error_body(error)
                    if error.code == 404:
                        raise ValueError('API vocale absente : mettez Ollama à jour (0.40.9+), puis redémarrez-le.') from error
                    raise ValueError(f'Ollama audio HTTP {error.code} : {detail}. '
                                     'Vérifiez Ollama 0.40.9+ et le modèle avec ollama list.') from error
            except URLError as error:
                raise ValueError(f'Ollama audio inaccessible : {error.reason}') from error
            total += len(data)
            if not data or len(data) % 2 or total > 32 * 1024 * 1024:
                raise ValueError('Audio PCM vide, invalide ou trop volumineux pour ce passage.')
            output.writeframes(data)


def stop_process(process, suspended=False):
    if process is not None and process.poll() is None:
        try:
            if suspended:
                os.killpg(process.pid, signal.SIGCONT)
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=2)
        except ProcessLookupError:
            pass


class Speech:
    """Un passage en préparation ou en lecture ; aucun minuteur ne le termine."""
    def __init__(self, engine='ollama', model='phonon:40m-fr', voice='default',
                 url='http://127.0.0.1:11434', wpm=200):
        self.engine, self.model, self.voice, self.url, self.wpm = engine, model, voice, url, wpm
        self.temporary = tempfile.TemporaryDirectory(prefix='reader-speech-')
        self.folder = Path(self.temporary.name)
        self.generator = self.player = None
        self.key = None
        self.state = 'off'
        self.suspended = False
        self.error_file = None

    @property
    def finished(self):
        return self.state == 'finished'

    @property
    def label(self):
        status = read_status(self.status_path) if getattr(self, 'status_path', None) else ''
        if status and self.state == 'preparing':
            return status
        return {'off': 'arrêtée', 'preparing': 'préparation', 'playing': 'lecture',
                'paused': 'pause', 'finished': 'fin du passage'}.get(self.state, self.state)

    def pause(self):
        if self.player is not None and self.player.poll() is None and not self.suspended:
            try:
                os.killpg(self.player.pid, signal.SIGSTOP)
                self.suspended = True
                self.state = 'paused'
            except ProcessLookupError:
                pass

    def stop(self):
        stop_process(self.player, self.suspended)
        stop_process(self.generator)
        self.player = self.generator = None
        self.suspended = False
        self.key, self.state = None, 'off'
        if self.error_file:
            self.error_file.close()
            self.error_file = None

    def check_result(self, process, action):
        if process.returncode:
            self.error_file.flush()
            with (self.folder / 'error.log').open('r', errors='replace') as errors:
                detail = errors.read(3000).strip()
            if action == 'Lecture audio' and 'Library not loaded' in detail:
                raise ValueError('FFplay est endommagé. Revenez au tempo ×1 (--audio-rate 1) '
                                 'ou lancez : brew reinstall ffmpeg')
            raise ValueError('Voix : ' + (detail or f'{action} impossible (code {process.returncode})'))

    def sync(self, key, text, active, rate=1.0):
        if key != self.key:
            self.stop()
            if not active:
                return
            self.key = key
            self.status_path = self.folder / 'status.json'
            self.status_path.unlink(missing_ok=True)
            self.error_file = (self.folder / 'error.log').open('wb')
            self.output = self.folder / ('passage.aiff' if self.engine == 'say' else 'passage.wav')
            if self.engine == 'say':
                if sys.platform != 'darwin' or not shutil.which('say'):
                    raise ValueError('La voix say nécessite macOS. Utilisez --tts ollama.')
                input_path = self.folder / 'passage.txt'
                input_path.write_text(text, encoding='utf-8')
                command = ['say', '-r', str(self.wpm), '-f', str(input_path), '-o', str(self.output)]
                if self.voice != 'default':
                    command += ['-v', self.voice]
                self.generator = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=self.error_file,
                                                  start_new_session=True)
            else:
                job = dict(text=text, model=self.model, voice=self.voice, url=self.url,
                           output=str(self.output), status=str(self.status_path))
                job_path = self.folder / 'job.json'
                job_path.write_text(json.dumps(job), encoding='utf-8')
                self.generator = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), str(job_path)],
                                                  stdout=subprocess.DEVNULL, stderr=self.error_file,
                                                  start_new_session=True)
            self.state = 'preparing'
        if not active:
            self.pause()
            return
        if self.generator is not None and self.generator.poll() is not None:
            self.check_result(self.generator, 'Synthèse vocale')
            self.generator = None
            if sys.platform == 'darwin' and abs(rate - 1) < 0.001 and shutil.which('afplay'):
                command = ['afplay', str(self.output)]
            elif shutil.which('ffplay'):
                command = ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'error', '-nostats',
                           '-af', f'atempo={rate:.2f}', str(self.output)]
            else:
                raise ValueError('Installez FFmpeg pour la lecture et sa vitesse : brew install ffmpeg '
                                 '(ou revenez à --audio-rate 1 sur macOS).')
            self.player = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                           stderr=self.error_file, start_new_session=True)
            self.state = 'playing'
        if self.player is not None:
            if self.player.poll() is not None:
                self.check_result(self.player, 'Lecture audio')
                self.state = 'finished'
            elif self.suspended:
                try:
                    os.killpg(self.player.pid, signal.SIGCONT)
                    self.suspended, self.state = False, 'playing'
                except ProcessLookupError:
                    pass

    def close(self):
        self.stop()
        self.temporary.cleanup()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('job', type=Path)
    args = parser.parse_args()
    try:
        synthesize_ollama(json.loads(args.job.read_text(encoding='utf-8')))
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
