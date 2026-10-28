#!/usr/bin/env python3
"""Optional offline PDF preparation, isolated from the terminal and reading DB."""

import argparse
from contextlib import contextmanager
import errno
import fcntl
from functools import partial
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import urllib.request
from unittest.mock import patch

from formula_cache import (VERSION, MODEL_SHA256, MODEL_URL, atomic_json,
                           fingerprint, folder_for, model_path, read_page)
from formula_detection import text_regions, merge_regions


@contextmanager
def offline_network():
    """Keep the optional SDK's connectivity checks/telemetry offline as well."""
    import socket
    original = socket.socket.connect
    original_ex = socket.socket.connect_ex

    def connect(stream, address):
        if stream.family in (socket.AF_INET, socket.AF_INET6):
            raise OSError(errno.ENETUNREACH, 'Préparation locale : réseau désactivé')
        return original(stream, address)

    def connect_ex(stream, address):
        if stream.family in (socket.AF_INET, socket.AF_INET6):
            return errno.ENETUNREACH
        return original_ex(stream, address)

    with patch.object(socket.socket, 'connect', connect), patch.object(socket.socket, 'connect_ex', connect_ex), \
            patch.dict(os.environ, {'YOLO_AUTOINSTALL': 'False', 'NO_ALBUMENTATIONS_UPDATE': '1'}):
        yield


def download_model():
    target = model_path()
    if target.exists() and fingerprint(target) == MODEL_SHA256:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as stream:
            temporary = Path(stream.name)
            with urllib.request.urlopen(MODEL_URL, timeout=60) as response:
                while block := response.read(1024 * 1024):
                    stream.write(block)
        if fingerprint(temporary) != MODEL_SHA256:
            raise ValueError('Empreinte du modèle incorrecte ; téléchargement rejeté.')
        temporary.replace(target)
        return target
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


class LayoutModel:
    def __init__(self, device='auto'):
        target = model_path()
        if not target.exists() or fingerprint(target) != MODEL_SHA256:
            raise ValueError('Modèle absent ou invalide : lancez ./install.sh --layout.')
        import torch
        from doclayout_yolo import YOLOv10
        torch.set_num_threads(2)
        self.device = device
        if device == 'auto':
            self.device = 'cuda:0' if torch.cuda.is_available() else 'mps' if torch.backends.mps.is_available() else 'cpu'
        # This exact, hash-verified official checkpoint serializes its model class.
        # Scope legacy loading to it; never accept an arbitrary pickle/model path.
        original = torch.load
        try:
            torch.load = partial(original, weights_only=False)
            self.model = YOLOv10(str(target))
        finally:
            torch.load = original
        self.names = self.model.names
        if not any('formula' in str(name).lower() or 'equation' in str(name).lower()
                   for name in self.names.values()):
            raise ValueError('Le modèle ne fournit aucune classe de formule.')

    def regions(self, page):
        import numpy as np
        import pymupdf
        scale = 1536 / max(page.rect.width, page.rect.height)
        pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), colorspace=pymupdf.csRGB, alpha=False)
        image = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)[:, :, ::-1].copy()
        try:
            prediction = self.model.predict(image, imgsz=1024, conf=.25, device=self.device, verbose=False)[0]
        except RuntimeError:
            if self.device == 'cpu':
                raise
            self.device = 'cpu'
            self.model.to('cpu')
            self.model.predictor = None
            prediction = self.model.predict(image, imgsz=1024, conf=.25, device='cpu', verbose=False)[0]
        output = []
        for box in prediction.boxes:
            name = str(self.names[int(box.cls.item())]).lower()
            if 'formula' not in name and 'equation' not in name:
                continue
            if 'caption' in name:
                continue
            x0, y0, x1, y1 = box.xyxy[0].tolist()
            output.append(dict(box=[round(max(0, x0) / pix.width, 5), round(max(0, y0) / pix.height, 5),
                                    round(min(pix.width, x1) / pix.width, 5), round(min(pix.height, y1) / pix.height, 5)],
                               source='model', score=round(float(box.conf.item()), 4), category=name))
        return output


def run(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf', type=Path, nargs='?')
    parser.add_argument('--method', choices=('text', 'model', 'hybrid'), default='hybrid')
    parser.add_argument('--device', default='auto', choices=('auto', 'cpu', 'mps', 'cuda:0'))
    parser.add_argument('--pages', help='pages physiques séparées par des virgules, pour comparaison')
    parser.add_argument('--start-page', type=int, default=1)
    parser.add_argument('--priority-file', type=Path)
    parser.add_argument('--state-file', type=Path)
    parser.add_argument('--download-model', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)

    def state(**values):
        if args.state_file:
            atomic_json(args.state_file, values)

    try:
        if args.download_model:
            print('Modèle vérifié :', download_model(), flush=True)
            return 0
        import pymupdf
        if args.check:
            model = LayoutModel(args.device) if args.method != 'text' else None
            print(json.dumps(dict(ready=True, method=args.method, device=model.device if model else 'cpu')))
            return 0
        if not args.pdf:
            parser.error('indiquez un PDF')
        path = args.pdf.expanduser().resolve(strict=True)
        original = path.stat()
        signature = original.st_size, original.st_mtime_ns

        def unchanged():
            info = path.stat()
            if (info.st_size, info.st_mtime_ns) != signature:
                raise ValueError('PDF modifié pendant la préparation ; relancez-la.')

        digest = fingerprint(path)
        unchanged()
        folder = folder_for(digest, args.method)
        folder.mkdir(parents=True, exist_ok=True)
        with (folder / 'prepare.lock').open('a') as lock:
            while True:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    state(stage='shared', message='Préparation déjà en cours dans une autre session.')
                    time.sleep(.2)
            with pymupdf.open(path) as document:
                total = len(document)
                requested = sorted(set(int(value) for value in args.pages.split(','))) if args.pages else list(range(1, total + 1))
                if any(number < 1 or number > total for number in requested):
                    raise ValueError('Numéro de page hors du document.')
                order = [n for n in requested if n >= args.start_page] + [n for n in requested if n < args.start_page]
                missing = {n for n in requested if read_page(folder, n) is None}
                state(stage='loading', completed=len(requested) - len(missing), total=len(requested))
                model = LayoutModel(args.device) if missing and args.method != 'text' else None
                started = time.monotonic()
                errors = []
                while missing:
                    priority = []
                    if args.priority_file:
                        try:
                            priority = json.loads(args.priority_file.read_text())
                        except (OSError, ValueError):
                            pass
                    number = next((n for n in priority if type(n) is int and n in missing), None)
                    if number is None:
                        number = next(n for n in order if n in missing)
                    unchanged()
                    state(stage='processing', page=number, completed=len(requested) - len(missing),
                          total=len(requested), device=model.device if model else 'cpu')
                    before = time.monotonic()
                    try:
                        page = document[number - 1]
                        text = text_regions(page) if args.method != 'model' else []
                        visual = model.regions(page) if model else []
                        regions = merge_regions(text, visual)
                        unchanged()
                        atomic_json(folder / f'page-{number}.json', dict(
                            page=number, formulas=len(regions), formula_regions=regions, method=args.method,
                            text_regions=len(text), model_regions=len(visual),
                            seconds=round(time.monotonic() - before, 4), device=model.device if model else 'cpu',
                            version=VERSION))
                    except (RuntimeError, ValueError) as error:
                        errors.append(dict(page=number, error=str(error)[:300]))
                    missing.remove(number)
                    if len(missing) % 20 == 0 or not missing:
                        print(f'{len(requested) - len(missing)}/{len(requested)} pages préparées', flush=True)
                unchanged()
                report = dict(stage='complete' if not errors else 'incomplete', pages=total,
                              requested=len(requested), errors=errors, method=args.method,
                              seconds=round(time.monotonic() - started, 3),
                              model_sha256=MODEL_SHA256 if args.method != 'text' else None)
                atomic_json(folder / 'preparation.json', report)
                state(**report)
                print(json.dumps(dict(folder=str(folder), **report), ensure_ascii=False), flush=True)
                return 1 if errors else 0
    except KeyboardInterrupt:
        state(stage='interrupted')
        print('\nPréparation interrompue ; pages déjà préparées conservées.', file=sys.stderr)
        return 130
    except (OSError, ValueError, ImportError, RuntimeError) as error:
        state(stage='error', error=str(error)[:400])
        print(f'Préparation : {error}', file=sys.stderr)
        return 1


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    if '--download-model' in arguments:
        return run(arguments)
    with offline_network():
        return run(arguments)


if __name__ == '__main__':
    sys.exit(main())
