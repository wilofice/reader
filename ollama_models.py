"""Téléchargement à la demande des modèles absents du serveur Ollama."""

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def error_body(error):
    cached = getattr(error, '_reader_body', None)
    if cached is None:
        try:
            cached = error.read(2000)
        except OSError:
            cached = b''
        error._reader_body = cached
    return cached.decode('utf-8', errors='replace')


def model_missing(error):
    if not isinstance(error, HTTPError) or error.code not in (404, 400):
        return False
    body = error_body(error).lower()
    return 'model' in body and ('not found' in body or 'pull' in body)


def pull_model(url, model, status_path=None):
    """Télécharge le modèle sur le serveur réellement configuré (local ou distant)."""
    request = Request(url.rstrip('/') + '/api/pull',
                      data=json.dumps({'name': model, 'stream': True}).encode(),
                      headers={'Content-Type': 'application/json'})
    try:
        with urlopen(request, timeout=30) as response:
            for raw in response:
                if not raw.strip():
                    continue
                update = json.loads(raw)
                if update.get('error'):
                    raise ValueError(f"Téléchargement du modèle {model} impossible : {update['error']}")
                if status_path:
                    total, completed = update.get('total'), update.get('completed')
                    if total:
                        label = f"Installation {model} : {min(100, completed * 100 // total)} %"
                    else:
                        label = f"Installation du modèle {model}…"
                    _write_status(status_path, label)
    except HTTPError as error:
        detail = error.read(2000).decode('utf-8', errors='replace')
        raise ValueError(f"Ollama refuse le téléchargement de {model} (HTTP {error.code}) : {detail}") from error
    except URLError as error:
        raise ValueError(f"Ollama inaccessible pour télécharger {model} : {error.reason}") from error
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError(f"Réponse de téléchargement Ollama invalide pour {model}.") from error
    if status_path:
        _write_status(status_path, f"Modèle {model} installé · préparation…")


def _write_status(path, label):
    target = Path(path)
    temporary = target.with_suffix('.tmp-' + str(os.getpid()))
    try:
        temporary.write_text(json.dumps({'label': label}, ensure_ascii=False), encoding='utf-8')
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def read_status(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8')).get('label', '')
    except (OSError, ValueError, TypeError):
        return ''
