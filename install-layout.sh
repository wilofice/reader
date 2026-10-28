#!/bin/bash
# Préparation locale des formules, séparée des dépendances du lecteur.
set -euo pipefail
repo_dir="$(cd "$(dirname "$0")" && pwd)"
layout_python=""
for candidate in python3.12 python3.13 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; sys.exit(0 if (3,10) <= sys.version_info[:2] <= (3,13) else 1)' >/dev/null 2>&1; then
        layout_python="$(command -v "$candidate")"
        break
    fi
done
if [ -z "$layout_python" ] && [ "$(uname -s)" = Darwin ]; then
    brew_bin="$(command -v brew || true)"
    if [ -z "$brew_bin" ]; then
        for candidate in /opt/homebrew/bin/brew /usr/local/bin/brew; do
            if [ -x "$candidate" ]; then brew_bin="$candidate"; break; fi
        done
    fi
    if [ -n "$brew_bin" ]; then
        "$brew_bin" install python@3.12
        layout_python="$("$brew_bin" --prefix python@3.12)/bin/python3.12"
    fi
fi
if [ -z "$layout_python" ]; then
    printf '%s\n' 'Installez Python 3.12 (ou 3.10 à 3.13), puis relancez ./install-layout.sh.' >&2
    exit 1
fi
if [ ! -x "$repo_dir/.venv-layout/bin/python" ]; then
    "$layout_python" -m venv "$repo_dir/.venv-layout"
fi
worker_python="$repo_dir/.venv-layout/bin/python"
rm -f "$repo_dir/.venv-layout/reader-ready.json"
"$worker_python" -m pip install -r "$repo_dir/requirements-layout.txt"
"$worker_python" "$repo_dir/layout_worker.py" --download-model
"$worker_python" "$repo_dir/layout_worker.py" --check
"$worker_python" -c 'import json,sys; from pathlib import Path; (Path(sys.prefix)/"reader-ready.json").write_text(json.dumps({"ready": True}))'
printf '%s\n' 'Repérage enrichi prêt. Les prochains PDF seront préparés en arrière-plan.' \
    './reader "document.pdf" --prepare   # préparer tout le document avant lecture'
