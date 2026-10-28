"""Shared, dependency-free layout cache contract and PDF/model fingerprints."""

import hashlib
import json
import os
from pathlib import Path
import tempfile

VERSION = 'formulas-v1'
MODEL_REVISION = '8c3299a30b8ff29a1503c4431b035b93220f7b11'
MODEL_SHA256 = '9a2ee0220fe3d9ad31b47e1d9f1282f46959a54e4618fce9cffcc9715b8286e2'
MODEL_NAME = 'doclayout_yolo_docstructbench_imgsz1024.pt'
MODEL_URL = f'https://huggingface.co/juliozhao/DocLayout-YOLO-DocStructBench/resolve/{MODEL_REVISION}/{MODEL_NAME}'


def cache_root():
    return Path(os.environ.get('XDG_CACHE_HOME', '~/.cache')).expanduser() / 'reader'


def fingerprint(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def model_path():
    return cache_root() / 'models' / MODEL_SHA256 / MODEL_NAME


def folder_for(digest, method):
    model_key = MODEL_SHA256[:12] if method in ('model', 'hybrid') else 'text'
    return cache_root() / VERSION / f'{method}-{model_key}' / digest


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, ensure_ascii=False)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def read_page(folder, number):
    try:
        item = json.loads((Path(folder) / f'page-{number}.json').read_text())
        if item['page'] != number or type(item['formulas']) is not int or item['formulas'] < 0:
            return None
        if (not isinstance(item['formula_regions'], list) or item['formulas'] != len(item['formula_regions'])
                or item.get('version') != VERSION or item['method'] not in ('text', 'model', 'hybrid')):
            return None
        return item
    except (OSError, ValueError, KeyError, TypeError):
        return None
