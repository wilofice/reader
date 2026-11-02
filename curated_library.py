"""Catalogue de lectures recommandées, téléchargements autorisés et liens locaux."""

import json
import os
from pathlib import Path
import re
import sqlite3
import curses
import urllib.request


CATALOG_FILE = Path(__file__).with_name('reading_catalog.json')


def speech_model_for_language(language):
    """Return the bundled Phonon model matching a catalogue language label."""
    normalized = (language or '').strip().lower()
    return 'phonon:31m-en' if normalized.startswith(('anglais', 'english', 'en')) else 'phonon:40m-fr'


def library_dir():
    data_root = os.environ.get('XDG_DATA_HOME')
    base = Path(data_root).expanduser() if data_root else Path.home() / '.local/share'
    return base / 'reader' / 'library'


class CuratedLibrary:
    def __init__(self, db):
        self.db = db
        with db:
            db.execute('''CREATE TABLE IF NOT EXISTS curated_library_files (
                item_id TEXT PRIMARY KEY, path TEXT NOT NULL, attached TEXT NOT NULL
            )''')
        raw = json.loads(CATALOG_FILE.read_text(encoding='utf-8'))
        self.items = raw['items']
        self.by_id = {item['id']: item for item in self.items}

    def item(self, item_id):
        try:
            return self.by_id[item_id]
        except KeyError as error:
            raise ValueError(f"Identifiant de lecture inconnu : {item_id}. Lancez reader --catalog.") from error

    def path(self, item_id):
        row = self.db.execute('SELECT path FROM curated_library_files WHERE item_id = ?', (item_id,)).fetchone()
        if row:
            path = Path(row[0]).expanduser()
            if path.is_file():
                return path.resolve()
        item = self.item(item_id)
        filename = item_id + '.pdf'
        candidate = library_dir() / filename
        return candidate.resolve() if candidate.is_file() else None

    def attach(self, item_id, path):
        self.item(item_id)
        path = Path(path).expanduser().resolve(strict=True)
        if not path.is_file():
            raise ValueError(f"Fichier illisible : {path}")
        if path.suffix.lower() not in ('.pdf', '.txt', '.md', '.markdown'):
            raise ValueError('Reader accepte ici les fichiers PDF, texte et Markdown.')
        with self.db:
            self.db.execute('''INSERT INTO curated_library_files (item_id, path, attached)
                VALUES (?, ?, datetime('now')) ON CONFLICT(item_id) DO UPDATE SET
                path=excluded.path, attached=excluded.attached''', (item_id, str(path)))
        return path

    def download(self, item_id, progress=None):
        item = self.item(item_id)
        url = item.get('download_url')
        if not url:
            raise ValueError(f"Pas de téléchargement automatique autorisé pour « {item['title']} ». Consultez : {item['url']}")
        if not url.startswith('https://'):
            raise ValueError('Le catalogue n’accepte que les URL HTTPS.')
        existing = self.path(item_id)
        if existing:
            return existing
        target_dir = library_dir()
        target_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        target = target_dir / (re.sub(r'[^a-z0-9-]', '-', item_id.lower()) + '.pdf')
        temporary = target.with_suffix('.pdf.part')
        request = urllib.request.Request(url, headers={'User-Agent': 'Reader/1.0 (personal reading library)'})
        try:
            with urllib.request.urlopen(request, timeout=45) as response, temporary.open('wb') as output:
                first = response.read(8)
                if not first.startswith(b'%PDF-'):
                    raise ValueError(f"La source n’a pas renvoyé un PDF. Ouvrez la source officielle : {item['url']}")
                output.write(first)
                total = int(response.headers.get('Content-Length') or 0)
                received = len(first)
                while chunk := response.read(128 * 1024):
                    received += len(chunk)
                    if received > 500 * 1024 * 1024:
                        raise ValueError('Téléchargement interrompu : le fichier dépasse 500 Mo.')
                    output.write(chunk)
                    if progress:
                        progress(received, total)
            temporary.chmod(0o600)
            temporary.replace(target)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
        with self.db:
            self.db.execute('''INSERT INTO curated_library_files (item_id, path, attached)
                VALUES (?, ?, datetime('now')) ON CONFLICT(item_id) DO UPDATE SET
                path=excluded.path, attached=excluded.attached''', (item_id, str(target.resolve())))
        return target.resolve()

    def entries(self):
        result = []
        for item in self.items:
            path = self.path(item['id'])
            position, length = (0, 0)
            if path:
                row = self.db.execute('SELECT position, length FROM documents WHERE path = ?', (str(path),)).fetchone()
                if row:
                    position, length = row
            result.append((item, path, position, length))
        return result

    def summary(self):
        lines = ['Bibliothèque de lecture · progression liée à chaque édition', '']
        for item, path, position, length in self.entries():
            state = f'{position / max(1, length):5.1%}' if path else ('à télécharger' if item.get('download_url') else 'accès externe')
            local = 'disponible' if path else item['access']
            lines.append(f"{item['id']:<31} {state:>12}  {item['title']} — {local}")
        lines.extend(['', 'Ouvrir : reader --open-book ID', 'Tout télécharger : reader --download-library',
                      'Rattacher un PDF personnel : reader --attach-book ID CHEMIN'])
        return '\n'.join(lines)

    def download_all(self, progress=None):
        outcomes = []
        for item in self.items:
            if not item.get('download_url') or item.get('auto_download') is False:
                continue
            try:
                path = self.download(item['id'], progress)
                outcomes.append((item['id'], path, None))
            except (OSError, ValueError) as error:
                outcomes.append((item['id'], None, str(error)))
        return outcomes


def select_item(screen, library):
    # Decode terminal escape sequences (arrows, Home/End) as curses keys.
    # Explicit setup matters for terminals and test harnesses that do not enter
    # keypad mode through curses.wrapper themselves.
    screen.keypad(True)
    index = 0
    notice = '↑/↓ naviguer · Entrée ouvrir · d télécharger · a rattacher · q quitter'
    while True:
        screen.erase()
        height, width = screen.getmaxyx()

        def put(y, value, attr=0):
            if 0 <= y < height:
                try:
                    screen.addnstr(y, 2, value, max(0, width - 4), attr)
                except Exception:
                    pass

        put(0, 'BIBLIOTHÈQUE DE LECTURE', 1)
        put(1, '↑/↓ choisir · Entrée ouvrir · d télécharger · a rattacher un PDF', 0)
        rows = library.entries()
        visible_count = max(1, height - 5)
        start = min(max(0, index - visible_count + 1), max(0, len(rows) - visible_count))
        for row_index, (item, path, position, length) in enumerate(rows[start:start + visible_count]):
            status = (f"{position / max(1, length):5.1%}" if path else
                      'PDF disponible' if item.get('download_url') else 'web / emprunt')
            screen_row = row_index + 3
            absolute_index = start + row_index
            title_width = max(10, width - 4 - 5 - len(status) - 2)
            title = item['title']
            if len(title) > title_width:
                title = title[:max(1, title_width - 1)] + '…'
            text = f"{absolute_index + 1:2}. {title:<{title_width}} {status}"
            selected = curses.A_REVERSE | curses.A_BOLD if absolute_index == index else 0
            put(screen_row, text, selected)
        put(height - 2, notice or '↑/↓ naviguer · Entrée ouvrir · d télécharger · a rattacher · q quitter')
        screen.refresh()
        key = read_catalog_key(screen)
        if key in (ord('q'), 27):
            return None
        if key in (curses.KEY_UP, ord('k')):
            index = max(0, index - 1)
        elif key in (curses.KEY_DOWN, ord('j')):
            index = min(len(rows) - 1, index + 1)
        elif key == curses.KEY_HOME:
            index = 0
        elif key == curses.KEY_END:
            index = len(rows) - 1
        elif key in (10, 13, curses.KEY_ENTER):
            item, path, _, _ = rows[index]
            if path:
                return item['id']
            notice = f"Fichier absent · {item['note']}"
        elif key == ord('d'):
            item = rows[index][0]
            notice = f"Téléchargement officiel : {item['title']}…"
            screen.erase()
            put(1, notice)
            screen.refresh()
            try:
                library.download(item['id'])
                notice = f"Téléchargé. Entrée ouvre {item['id']}."
            except (OSError, ValueError) as error:
                notice = str(error)
        elif key == ord('a'):
            item = rows[index][0]
            prompt = f"Chemin du PDF à associer à {item['id']} : "
            put(height - 2, prompt)
            try:
                screen.move(height - 2, min(width - 2, 2 + len(prompt)))
                curses.echo()
                raw_path = screen.getstr(height - 2, min(width - 2, 2 + len(prompt)), max(1, width - len(prompt) - 4))
            except curses.error:
                raw_path = b''
            finally:
                curses.noecho()
            filename = raw_path.decode('utf-8', errors='replace').strip()
            if filename:
                try:
                    library.attach(item['id'], filename)
                    notice = f"Document rattaché à {item['id']} ; Entrée pour lire."
                except (OSError, ValueError) as error:
                    notice = str(error)
            else:
                notice = f"Aucun fichier sélectionné. Sinon : ./reader --attach-book {item['id']} CHEMIN"


def read_catalog_key(screen):
    """Read arrows decoded by curses or sent as common raw escape sequences."""
    key = screen.getch()
    if key != 27:
        return key

    # Terminal.app and presentation devices may keep sending CSI arrows even
    # after curses enabled application keypad mode. Wait briefly to distinguish
    # a sequence from a deliberate Escape used to close the catalogue.
    screen.timeout(50)
    try:
        second = screen.getch()
        if second not in (ord('['), ord('O')):
            return 27
        sequence = []
        for _ in range(8):
            part = screen.getch()
            if part == -1:
                break
            sequence.append(part)
            if part in (ord('A'), ord('B'), ord('H'), ord('F')):
                break
        if not sequence:
            return 27
        return {
            ord('A'): curses.KEY_UP,
            ord('B'): curses.KEY_DOWN,
            ord('H'): curses.KEY_HOME,
            ord('F'): curses.KEY_END,
        }.get(sequence[-1], 27)
    finally:
        screen.timeout(-1)
