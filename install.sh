#!/bin/bash
# Compatible avec le Bash 3.2 fourni par macOS ; aucun Python requis au démarrage.
set -euo pipefail

check_only=0
case "${1:-}" in
    --check) check_only=1 ;;
    -h|--help)
        printf '%s\n' 'Usage : ./install.sh [--check]' \
            'Installe les dépendances macOS manquantes : Python 3.10+, Poppler, Chafa.' \
            '--check : vérifier seulement, sans installation ni accès réseau.'
        exit 0 ;;
    '') ;;
    *) printf 'Option inconnue : %s\n' "$1" >&2; exit 2 ;;
esac
if [ "$#" -gt 1 ]; then
    printf '%s\n' 'Une seule option est acceptée. Voir ./install.sh --help.' >&2
    exit 2
fi
if [ "$(uname -s)" != Darwin ]; then
    printf '%s\n' 'Cet installateur concerne macOS. Sous Linux, installez Python 3.10+, poppler-utils et chafa.' >&2
    exit 1
fi

python_ready() {
    command -v python3 >/dev/null 2>&1 &&
        python3 -c 'import sys, curses, sqlite3; sys.exit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1
}
poppler_ready() {
    command -v pdftotext >/dev/null 2>&1 && command -v pdftoppm >/dev/null 2>&1 &&
        command -v pdfimages >/dev/null 2>&1 && command -v pdftocairo >/dev/null 2>&1 &&
        pdftotext -v >/dev/null 2>&1 && pdftoppm -v >/dev/null 2>&1 &&
        pdfimages -v >/dev/null 2>&1 && pdftocairo -v >/dev/null 2>&1
}
chafa_ready() {
    command -v chafa >/dev/null 2>&1 && chafa --version >/dev/null 2>&1
}
report() {
    local missing=0
    if python_ready; then
        printf 'OK  Python 3.10+ avec curses et SQLite : %s\n' "$(command -v python3)"
    else
        printf '%s\n' 'MANQUANT  Python 3.10+ fonctionnel avec curses et SQLite'
        missing=1
    fi
    if poppler_ready; then printf '%s\n' 'OK  Poppler : extraction et rendu PDF';
    else printf '%s\n' 'MANQUANT  Poppler (pdftotext, pdftoppm, pdfimages, pdftocairo)'; missing=1; fi
    if chafa_ready; then printf '%s\n' 'OK  Chafa : aperçu des images dans le terminal';
    else printf '%s\n' 'MANQUANT  Chafa'; missing=1; fi
    return "$missing"
}

if [ "$check_only" -eq 1 ]; then
    report
    exit 0
fi
if python_ready && poppler_ready && chafa_ready; then
    report
    printf '%s\n' 'Tout est prêt ; aucune installation nécessaire.' './reader README.md'
    exit 0
fi

brew_bin="$(command -v brew || true)"
if [ -z "$brew_bin" ]; then
    for candidate in /opt/homebrew/bin/brew /usr/local/bin/brew; do
        if [ -x "$candidate" ]; then brew_bin="$candidate"; break; fi
    done
fi
if [ -z "$brew_bin" ]; then
    printf '%s\n' 'Homebrew est absent : lancement de son installateur officiel.'
    installer_file="$(mktemp -t reader-homebrew)"
    trap 'rm -f "$installer_file"' EXIT
    curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh -o "$installer_file"
    /bin/bash "$installer_file"
    for candidate in /opt/homebrew/bin/brew /usr/local/bin/brew; do
        if [ -x "$candidate" ]; then brew_bin="$candidate"; break; fi
    done
    if [ -z "$brew_bin" ]; then
        printf '%s\n' 'Homebrew reste introuvable. Suivez les instructions de son installateur puis relancez ./install.sh.' >&2
        exit 1
    fi
fi

brew_prefix="$("$brew_bin" --prefix)"
export PATH="$brew_prefix/bin:$brew_prefix/sbin:$PATH"
packages=()
if ! python_ready; then packages+=(python); fi
if ! poppler_ready; then packages+=(poppler); fi
if ! chafa_ready; then packages+=(chafa); fi
if [ "${#packages[@]}" -gt 0 ]; then
    printf 'Installation avec Homebrew : %s\n' "${packages[*]}"
    "$brew_bin" install "${packages[@]}"
fi
if ! report; then
    printf '%s\n' "Des dépendances restent indisponibles. Vérifiez les erreurs Homebrew ci-dessus et l'ordre de votre PATH." >&2
    exit 1
fi
printf '\n%s\n' 'Installation terminée. Si Homebrew était absent du PATH de votre terminal, exécutez :'
printf 'export PATH="%s/bin:%s/sbin:$PATH"\n' "$brew_prefix" "$brew_prefix"
printf '\n%s\n' 'Puis lancez : ./reader README.md' \
    'iTerm2 est facultatif ; Terminal.app utilise Quick Look automatiquement.'
