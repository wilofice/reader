"""Nonblocking bridge between the stdlib reader and its optional layout worker."""

import json
import os
from pathlib import Path
import subprocess
import tempfile

from formula_cache import atomic_json, folder_for, model_path, read_page

ROOT = Path(__file__).resolve().parent


def layout_python():
    override = os.environ.get('READER_LAYOUT_PYTHON')
    return Path(override).expanduser() if override else ROOT / '.venv-layout/bin/python'


def available(method='auto'):
    python = layout_python()
    if method == 'off' or not python.is_file():
        return False
    if method == 'text':
        return True
    if method == 'auto' and not (python.parent.parent / 'reader-ready.json').exists():
        return False
    return model_path().is_file()


def prepare_document(path, method='auto'):
    if path.suffix.lower() != '.pdf':
        raise ValueError('--prepare concerne les PDF.')
    if method == 'off':
        raise ValueError('--prepare nécessite --formulas text, model ou hybrid.')
    if not available('hybrid' if method == 'auto' else method):
        raise ValueError('Repérage enrichi absent : lancez ./install.sh --layout.')
    process = subprocess.Popen([str(layout_python()), str(ROOT / 'layout_worker.py'), str(path),
                                '--method', 'hybrid' if method == 'auto' else method])
    try:
        return process.wait()
    except KeyboardInterrupt:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
        raise


class FormulaIndex:
    def __init__(self, path, digest, start_page=1, method='auto', signature=None):
        self.path = Path(path)
        info = self.path.stat()
        current = info.st_size, info.st_mtime_ns
        self.signature = signature or current
        if current != self.signature:
            raise ValueError('PDF modifié pendant la préparation ; rouvrez le document.')
        self.method = 'hybrid' if method == 'auto' else method
        self.folder = folder_for(digest, self.method)
        self.temporary = tempfile.TemporaryDirectory(prefix='reader-formulas-')
        self.priority = Path(self.temporary.name) / 'priority.json'
        self.state_file = Path(self.temporary.name) / 'state.json'
        self.last_priority = None
        self.log = tempfile.TemporaryFile()
        try:
            self.process = subprocess.Popen(
                [str(layout_python()), str(ROOT / 'layout_worker.py'), str(path), '--method', self.method,
                 '--start-page', str(start_page), '--priority-file', str(self.priority),
                 '--state-file', str(self.state_file)], stdin=subprocess.DEVNULL,
                stdout=self.log, stderr=self.log,
                env={**os.environ, 'ALBUMENTATIONS_OFFLINE': '1', 'NO_ALBUMENTATIONS_UPDATE': '1'})
        except OSError:
            self.log.close()
            self.temporary.cleanup()
            raise

    def visible(self, first, last):
        try:
            info = self.path.stat()
            if (info.st_size, info.st_mtime_ns) != self.signature:
                return {}, False, 'PDF modifié : rouvrez le document.'
        except OSError as error:
            return {}, False, str(error)
        priority = list(range(first, last + 1))
        if priority != self.last_priority:
            try:
                atomic_json(self.priority, priority)
            except OSError:
                pass  # Cache preparation remains usable with its initial order.
            self.last_priority = priority
        available_pages = {number: item for number in priority
                           if (item := read_page(self.folder, number)) is not None}
        try:
            state = json.loads(self.state_file.read_text())
        except (OSError, ValueError):
            state = {}
        pending = len(available_pages) < len(priority) and self.process.poll() is None
        error = state.get('error', '')
        if state.get('errors'):
            error = 'Certaines pages n’ont pas pu être préparées ; relancez --prepare.'
        if self.process.poll() not in (None, 0) and not error:
            error = 'Préparation enrichie interrompue ; lancez --prepare pour voir le diagnostic.'
        return available_pages, pending, error

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)
        self.log.close()
        self.temporary.cleanup()


class EnrichedIndex:
    def __init__(self, structural, formulas):
        self.structural, self.formulas = structural, formulas

    def visible(self, first, last):
        from visual_hints import label
        _, pending, pages = self.structural.visible(first, last)
        enriched, formula_pending, error = self.formulas.visible(first, last)
        by_page = {item['page']: dict(item) for item in pages}
        for number, data in enriched.items():
            item = by_page.setdefault(number, dict(page=number, images=0, paths=0, mention='', error=''))
            item.update(formulas=data['formulas'], formula_regions=data['formula_regions'],
                        formula_method=data['method'])
        if error:
            for number in range(first, last + 1):
                item = by_page.setdefault(number, dict(page=number, images=0, paths=0, mention='', error=''))
                item['formula_error'] = error
        pages = [by_page[number] for number in sorted(by_page)]
        candidates = [item for item in pages if label(item)]
        candidates.sort(key=lambda item: (not bool(item.get('formulas') or item['images'] or item['paths'] >= 4), item['page']))
        return (candidates[0] if candidates else None), pending or formula_pending, pages

    def close(self):
        try:
            self.formulas.close()
        finally:
            self.structural.close()
