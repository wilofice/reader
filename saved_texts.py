"""Textes importés, nommés et conservés à côté de la mémoire de lecture."""

from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid


def clipboard_text():
    if sys.platform == 'darwin':
        command = ['pbpaste']
    elif shutil.which('wl-paste'):
        command = ['wl-paste', '--no-newline']
    elif shutil.which('xclip'):
        command = ['xclip', '-selection', 'clipboard', '-o']
    elif shutil.which('xsel'):
        command = ['xsel', '--clipboard', '--output']
    else:
        raise ValueError('Presse-papiers indisponible : utilisez --paste pour coller le texte.')
    try:
        result = subprocess.run(command, capture_output=True, timeout=10)
    except subprocess.TimeoutExpired as error:
        raise ValueError('Le presse-papiers ne répond pas ; essayez --paste.') from error
    if result.returncode:
        raise ValueError('Impossible de lire le presse-papiers ; essayez --paste.')
    return result.stdout.decode('utf-8-sig')


class SavedTexts:
    def __init__(self, db, state_path):
        self.db = db
        self.folder = Path(state_path).expanduser().resolve().parent / 'texts'
        with db:
            db.execute('''CREATE TABLE IF NOT EXISTS saved_texts (
                name TEXT PRIMARY KEY COLLATE NOCASE, path TEXT NOT NULL UNIQUE,
                created TEXT NOT NULL DEFAULT (datetime('now')))''')

    def find(self, name):
        row = self.db.execute('SELECT path FROM saved_texts WHERE name = ?', (name.strip(),)).fetchone()
        if not row:
            raise ValueError(f'Texte introuvable : {name}. Consultez reader --library.')
        path = Path(row[0])
        if not path.is_file():
            raise ValueError(f'Le fichier du texte « {name} » est absent : {path}')
        return path

    def save(self, name, text):
        name = name.strip()
        if not name or len(name) > 120 or any(ord(char) < 32 or ord(char) == 127 for char in name):
            raise ValueError('Choisissez un nom de 1 à 120 caractères, sur une seule ligne.')
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        if not text.strip():
            raise ValueError('Aucun texte à importer ; le presse-papiers est peut-être vide.')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            existing = self.db.execute('SELECT path FROM saved_texts WHERE name = ?', (name,)).fetchone()
            if existing:
                path = self.find(name)
                if path.read_text(encoding='utf-8') != text:
                    raise ValueError(f'Le nom « {name} » existe avec un autre contenu. Choisissez un nouveau nom.')
                return path
            # Le nom ne sert jamais de chemin : chaque import a son propre dossier.
            folder = self.folder / uuid.uuid4().hex
            folder.mkdir(parents=True, mode=0o700)
            filename = re.sub(r'[^\w .-]', '_', name).strip(' .') or 'Texte'
            path = folder / (filename + '.md')
            try:
                with path.open('x', encoding='utf-8') as output:
                    path.chmod(0o600)
                    output.write(text)
                self.db.execute('INSERT INTO saved_texts (name, path) VALUES (?, ?)', (name, str(path)))
            except BaseException:
                path.unlink(missing_ok=True)
                folder.rmdir()
                raise
            return path

    def entries(self):
        return self.db.execute('''SELECT s.name, s.created, COALESCE(d.position, 0),
            COALESCE(d.length, 0) FROM saved_texts s LEFT JOIN documents d ON d.path = s.path
            ORDER BY s.created DESC, s.name''').fetchall()
