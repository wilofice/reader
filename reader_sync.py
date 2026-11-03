"""Portable, mergeable Reader state bundles and direct SSH synchronization."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import sqlite3
import subprocess
import sys
import tempfile

from curated_library import CuratedLibrary
from saved_texts import SavedTexts


BUNDLE_VERSION = 1
MAX_BUNDLE_BYTES = 64 * 1024 * 1024


def table_exists(db, name):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def backup_database(db, state_path):
    folder = Path(state_path).expanduser().resolve().parent / 'backups'
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    target = folder / f'reading-before-sync-{stamp}.sqlite3'
    destination = sqlite3.connect(target)
    try:
        db.backup(destination)
    finally:
        destination.close()
    target.chmod(0o600)
    return target


def _managed_documents(db):
    saved = dict(db.execute('SELECT path, name FROM saved_texts')) if table_exists(db, 'saved_texts') else {}
    catalog = dict(db.execute('SELECT path, item_id FROM curated_library_files')) if table_exists(db, 'curated_library_files') else {}
    return saved, catalog


def _document_record(db, row, saved, catalog):
    path, digest, position, length, updated, seconds, manual_words, manual_seconds, manual_digest = row
    cycles = [dict(zip(('number', 'completed', 'seconds', 'historical', 'started', 'finished', 'base_seconds'), cycle))
              for cycle in db.execute('''SELECT number, completed, seconds, historical, started, finished, base_seconds
                  FROM reading_cycles WHERE path=? AND digest=? ORDER BY number''', (path, digest))]
    coverage = [dict(zip(('day', 'cycle', 'start', 'end'), item))
                for item in db.execute('''SELECT day, cycle, word_start, word_end FROM daily_coverage
                    WHERE path=? AND digest=? ORDER BY day, cycle, word_start''', (path, digest))]
    return {
        'digest': digest, 'source_path': path, 'basename': Path(path).name,
        'position': position, 'length': length, 'updated': updated,
        'reading_seconds': seconds, 'manual_words': manual_words,
        'manual_seconds': manual_seconds, 'manual_digest': manual_digest,
        'saved_name': saved.get(path), 'catalog_id': catalog.get(path),
        'available': Path(path).is_file(),
        'cycles': cycles, 'coverage': coverage,
    }


def export_bundle(db, state_path):
    saved_paths, catalog_paths = _managed_documents(db)
    documents = [_document_record(db, row, saved_paths, catalog_paths) for row in db.execute('''
        SELECT path, digest, position, length, updated, reading_seconds,
               manual_words, manual_seconds, manual_digest
        FROM documents ORDER BY updated, path''')]
    if table_exists(db, 'sync_pending_documents'):
        known = {item['digest'] for item in documents}
        for digest, payload in db.execute('SELECT digest, payload FROM sync_pending_documents'):
            if digest not in known:
                item = json.loads(payload)
                item['available'] = False
                documents.append(item)
    texts = []
    if table_exists(db, 'saved_texts'):
        for name, raw_path, created in db.execute('SELECT name, path, created FROM saved_texts ORDER BY name'):
            path = Path(raw_path)
            if path.is_file() and path.stat().st_size <= 16 * 1024 * 1024:
                texts.append({'name': name, 'created': created, 'text': path.read_text(encoding='utf-8')})
    daily = dict(db.execute('SELECT day, words FROM daily_words')) if table_exists(db, 'daily_words') else {}
    folder = db.execute("SELECT value FROM preferences WHERE key='reading_folder'").fetchone()
    return {
        'format': 'reader-sync', 'version': BUNDLE_VERSION,
        'exported_at': datetime.now(timezone.utc).isoformat(),
        'source_home': str(Path.home()), 'documents': documents,
        'saved_texts': texts, 'daily_words': daily,
        'reading_folder': folder[0] if folder else str(Path.home() / 'Lectures'),
    }


def encode_bundle(bundle):
    data = json.dumps(bundle, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    if len(data) > MAX_BUNDLE_BYTES:
        raise ValueError('Le paquet de synchronisation dépasse 64 Mio.')
    return data


def decode_bundle(data):
    if len(data) > MAX_BUNDLE_BYTES:
        raise ValueError('Le paquet de synchronisation dépasse 64 Mio.')
    try:
        bundle = json.loads(data.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError('Paquet de synchronisation JSON invalide.') from error
    if bundle.get('format') != 'reader-sync' or bundle.get('version') != BUNDLE_VERSION:
        raise ValueError('Version de paquet de synchronisation incompatible.')
    if not isinstance(bundle.get('documents'), list) or not isinstance(bundle.get('saved_texts'), list):
        raise ValueError('Structure de paquet de synchronisation invalide.')
    return bundle


def _merge_intervals(db, day, path, digest, cycle, intervals):
    all_intervals = [(left, right) for left, right in db.execute('''SELECT word_start, word_end
        FROM daily_coverage WHERE day=? AND path=? AND digest=? AND cycle=?''', (day, path, digest, cycle))]
    all_intervals.extend((int(left), int(right)) for left, right in intervals if int(right) > int(left))
    all_intervals.sort()
    merged = []
    for left, right in all_intervals:
        if merged and left <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], right))
        else:
            merged.append((left, right))
    db.execute('DELETE FROM daily_coverage WHERE day=? AND path=? AND digest=? AND cycle=?',
               (day, path, digest, cycle))
    db.executemany('INSERT INTO daily_coverage VALUES (?, ?, ?, ?, ?, ?)',
                   ((day, path, digest, cycle, left, right) for left, right in merged))


def _merge_document(db, path, item):
    # Preserve the exact canonical path already known by Reader. Resolving here
    # would turn /var into /private/var on macOS and create a duplicate row.
    path = str(Path(path).expanduser())
    digest = item['digest']
    old = db.execute('''SELECT digest, position, length, updated, reading_seconds,
        manual_words, manual_seconds, manual_digest FROM documents WHERE path=?''', (path,)).fetchone()
    if old and old[0] != digest:
        return False
    values = {
        'position': max(old[1] if old else 0, int(item.get('position', 0))),
        'length': max(old[2] if old else 0, int(item.get('length', 0))),
        'updated': max(old[3] if old else '', item.get('updated') or ''),
        'reading_seconds': max(old[4] if old else 0, float(item.get('reading_seconds', 0))),
        'manual_words': max(old[5] if old else 0, int(item.get('manual_words', 0))),
        'manual_seconds': max(old[6] if old else 0, float(item.get('manual_seconds', 0))),
        'manual_digest': item.get('manual_digest') or (old[7] if old else ''),
    }
    db.execute('''INSERT INTO documents
        (path, digest, position, length, updated, reading_seconds, manual_words, manual_seconds, manual_digest)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(path) DO UPDATE SET
        digest=excluded.digest, position=excluded.position, length=excluded.length,
        updated=excluded.updated, reading_seconds=excluded.reading_seconds,
        manual_words=excluded.manual_words, manual_seconds=excluded.manual_seconds,
        manual_digest=excluded.manual_digest''',
        (path, digest, values['position'], values['length'], values['updated'], values['reading_seconds'],
         values['manual_words'], values['manual_seconds'], values['manual_digest']))
    for cycle in item.get('cycles', []):
        number = int(cycle['number'])
        existing = db.execute('''SELECT completed, seconds, historical, started, finished, base_seconds
            FROM reading_cycles WHERE path=? AND digest=? AND number=?''', (path, digest, number)).fetchone()
        completed = max(existing[0] if existing else 0, int(cycle.get('completed', 0)))
        seconds = max(existing[1] if existing else 0, float(cycle.get('seconds', 0)))
        historical = max(existing[2] if existing else 0, int(cycle.get('historical', 0)))
        starts = [value for value in ((existing[3] if existing else None), cycle.get('started')) if value]
        finishes = [value for value in ((existing[4] if existing else None), cycle.get('finished')) if value]
        base = max(existing[5] if existing else 0, float(cycle.get('base_seconds', 0)))
        db.execute('''INSERT INTO reading_cycles
            (path, digest, number, started, finished, completed, historical, seconds, base_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(path, digest, number) DO UPDATE SET
            started=excluded.started, finished=excluded.finished, completed=excluded.completed,
            historical=excluded.historical, seconds=excluded.seconds, base_seconds=excluded.base_seconds''',
            (path, digest, number, min(starts) if starts else None, max(finishes) if finishes else None,
             completed, historical, seconds, base))
    groups = {}
    for coverage in item.get('coverage', []):
        key = coverage['day'], int(coverage['cycle'])
        groups.setdefault(key, []).append((int(coverage['start']), int(coverage['end'])))
    for (day, cycle), intervals in groups.items():
        _merge_intervals(db, day, path, digest, cycle, intervals)
    return True


def _candidate_path(db, item, source_home, saved_map, catalog):
    if item.get('saved_name') in saved_map:
        return saved_map[item['saved_name']]
    if item.get('catalog_id'):
        candidate = catalog.path(item['catalog_id'])
        if candidate:
            return candidate
    matches = db.execute('SELECT path FROM documents WHERE digest=? ORDER BY updated DESC', (item['digest'],)).fetchall()
    for (raw_path,) in matches:
        if Path(raw_path).is_file():
            return Path(raw_path)
    raw = Path(item.get('source_path', ''))
    if raw.is_file():
        return raw
    try:
        relative = raw.relative_to(source_home)
        candidate = Path.home() / relative
        if candidate.is_file():
            return candidate
    except (TypeError, ValueError):
        pass
    return None


def _recalculate_daily(db, incoming):
    days = set(incoming)
    days.update(day for (day,) in db.execute('SELECT DISTINCT day FROM daily_coverage'))
    days.update(day for (day,) in db.execute('SELECT day FROM daily_words'))
    for day in days:
        computed = db.execute('SELECT COALESCE(SUM(word_end-word_start),0) FROM daily_coverage WHERE day=?', (day,)).fetchone()[0]
        current = db.execute('SELECT words FROM daily_words WHERE day=?', (day,)).fetchone()
        words = max(int(incoming.get(day, 0)), current[0] if current else 0, int(computed))
        db.execute('''INSERT INTO daily_words(day, words) VALUES (?, ?)
            ON CONFLICT(day) DO UPDATE SET words=excluded.words''', (day, words))


def import_bundle(db, state_path, bundle, make_backup=True):
    backup = backup_database(db, state_path) if make_backup else None
    saved = SavedTexts(db, state_path)
    catalog = CuratedLibrary(db)
    db.execute('''CREATE TABLE IF NOT EXISTS sync_pending_documents
        (digest TEXT PRIMARY KEY, payload TEXT NOT NULL, imported TEXT NOT NULL)''')
    saved_map = {}
    for item in bundle.get('saved_texts', []):
        name, text = str(item['name']), str(item['text'])
        try:
            path = saved.save(name, text)
        except ValueError:
            suffix = hashlib.sha256(text.encode('utf-8')).hexdigest()[:8]
            path = saved.save(f'{name} (sync {suffix})', text)
        saved_map[name] = path
    merged = pending = 0
    source_home = Path(bundle.get('source_home') or '/')
    with db:
        for item in bundle['documents']:
            if not isinstance(item, dict) or not item.get('digest'):
                raise ValueError('Document invalide dans le paquet de synchronisation.')
            path = _candidate_path(db, item, source_home, saved_map, catalog)
            if path and _merge_document(db, path, item):
                db.execute('DELETE FROM sync_pending_documents WHERE digest=?', (item['digest'],))
                merged += 1
            else:
                db.execute('''INSERT INTO sync_pending_documents(digest, payload, imported)
                    VALUES (?, ?, datetime('now')) ON CONFLICT(digest) DO UPDATE SET
                    payload=excluded.payload, imported=excluded.imported''',
                    (item['digest'], json.dumps(item, ensure_ascii=False, separators=(',', ':'))))
                pending += 1
        _recalculate_daily(db, bundle.get('daily_words', {}))
    integrity = db.execute('PRAGMA integrity_check').fetchone()[0]
    if integrity != 'ok':
        raise ValueError(f'Intégrité SQLite après import : {integrity}')
    return {'merged': merged, 'pending': pending, 'backup': str(backup) if backup else None}


def adopt_pending(db, path, digest):
    if not table_exists(db, 'sync_pending_documents'):
        return False
    row = db.execute('SELECT payload FROM sync_pending_documents WHERE digest=?', (digest,)).fetchone()
    if not row:
        return False
    item = json.loads(row[0])
    with db:
        if not _merge_document(db, path, item):
            return False
        db.execute('DELETE FROM sync_pending_documents WHERE digest=?', (digest,))
        _recalculate_daily(db, {})
    return True


def _read(path):
    if path == '-':
        return sys.stdin.buffer.read(MAX_BUNDLE_BYTES + 1)
    return Path(path).expanduser().read_bytes()


def _write(path, data):
    if path == '-':
        sys.stdout.buffer.write(data)
        return
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile(dir=target.parent, prefix=target.name + '.', delete=False) as output:
        temporary = Path(output.name)
        output.write(data)
    temporary.chmod(0o600)
    temporary.replace(target)


def _scan_configured(memory):
    configured = memory.daily.get('reading_folder', '')
    if configured and Path(configured).expanduser().is_dir():
        return memory.discover(configured)[0]
    return 0


def _copy_from_remote(host, bundle, local_bundle):
    folder = Path(local_bundle.get('reading_folder') or Path.home() / 'Lectures').expanduser()
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    local_digests = {item['digest'] for item in local_bundle['documents'] if item.get('available')}
    copied = 0
    for item in bundle['documents']:
        if not item.get('available') or item['digest'] in local_digests:
            continue
        source = item.get('source_path', '')
        name = Path(item.get('basename') or source).name
        if not source.startswith('/') or not name or any(ord(char) < 32 for char in name):
            continue
        target = folder / name
        if target.exists():
            continue
        # Modern macOS scp uses SFTP: argv already preserves spaces and quotes,
        # while adding shell quotes here would make them part of the filename.
        remote_source = f'{host}:{source}'
        result = subprocess.run(['scp', '-q', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8',
                                 remote_source, str(target)], capture_output=True, timeout=600)
        if result.returncode:
            raise ValueError('Copie SSH impossible : ' + result.stderr.decode('utf-8', errors='replace').strip())
        target.chmod(0o600)
        copied += 1
        local_digests.add(item['digest'])
    return copied


def _copy_to_remote(host, local_bundle, remote_bundle):
    folder = remote_bundle.get('reading_folder') or str(Path(remote_bundle['source_home']) / 'Lectures')
    setup = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', host,
                            f'mkdir -p {shlex.quote(folder)} && chmod 700 {shlex.quote(folder)}'],
                           capture_output=True, timeout=30)
    if setup.returncode:
        raise ValueError('Préparation du dossier distant impossible : ' + setup.stderr.decode('utf-8', errors='replace').strip())
    remote_digests = {item['digest'] for item in remote_bundle['documents'] if item.get('available')}
    copied = 0
    for item in local_bundle['documents']:
        source = Path(item.get('source_path', ''))
        if not item.get('available') or item['digest'] in remote_digests or not source.is_file():
            continue
        target = str(Path(folder) / source.name)
        exists = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', host,
                                 f'test -e {shlex.quote(target)}'], timeout=15).returncode == 0
        if exists:
            continue
        remote_target = f'{host}:{target}'
        result = subprocess.run(['scp', '-q', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8',
                                 str(source), remote_target], capture_output=True, timeout=600)
        if result.returncode:
            raise ValueError('Copie SSH impossible : ' + result.stderr.decode('utf-8', errors='replace').strip())
        subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', host,
                        f'chmod 600 {shlex.quote(target)}'], capture_output=True, timeout=15)
        copied += 1
        remote_digests.add(item['digest'])
    return copied


def sync_main(argv, default_state, memory_factory):
    parser = argparse.ArgumentParser(prog='reader sync', description='Synchroniser la mémoire Reader sans cloud.')
    parser.add_argument('-S', '--state', type=Path, default=default_state, help='base SQLite locale')
    commands = parser.add_subparsers(dest='command', required=True)
    export = commands.add_parser('export', help='créer un paquet JSON portable')
    export.add_argument('target', nargs='?', default='-', help='fichier cible, ou - pour stdout')
    restore = commands.add_parser('import', help='fusionner un paquet JSON')
    restore.add_argument('source', nargs='?', default='-', help='fichier source, ou - pour stdin')
    ssh = commands.add_parser('ssh', help='fusion bidirectionnelle directe par SSH')
    ssh.add_argument('host', help='hôte SSH, par exemple utilisateur@mac')
    ssh.add_argument('--remote-reader', default='~/dev/reader/reader', help='chemin de Reader sur l’autre Mac')
    ssh.add_argument('--remote-state', help='base distante facultative')
    args = parser.parse_args(argv)
    state = args.state.expanduser().resolve()
    memory = memory_factory(state)
    SavedTexts(memory.db, state)
    CuratedLibrary(memory.db)
    try:
        if args.command == 'export':
            _write(args.target, encode_bundle(export_bundle(memory.db, state)))
            if args.target != '-':
                print(f'Paquet Reader exporté : {Path(args.target).expanduser()}')
            return 0
        if args.command == 'import':
            result = import_bundle(memory.db, state, decode_bundle(_read(args.source)))
            discovered = _scan_configured(memory)
            print(f"Synchronisation importée : {result['merged']} document(s), {result['pending']} en attente, "
                  f"{discovered} nouveau(x) · sauvegarde {result['backup']}")
            return 0
        remote = args.remote_reader
        remote_state = ['-S', args.remote_state] if args.remote_state else []
        base = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', args.host, remote, 'sync', *remote_state]
        local_bundle = export_bundle(memory.db, state)
        fetched = subprocess.run([*base, 'export', '-'], capture_output=True, timeout=60)
        if fetched.returncode:
            raise ValueError('Export SSH impossible : ' + fetched.stderr.decode('utf-8', errors='replace').strip())
        remote_bundle = decode_bundle(fetched.stdout)
        received = _copy_from_remote(args.host, remote_bundle, local_bundle)
        local_result = import_bundle(memory.db, state, remote_bundle)
        _scan_configured(memory)
        sent_files = _copy_to_remote(args.host, local_bundle, remote_bundle)
        merged_data = encode_bundle(export_bundle(memory.db, state))
        sent = subprocess.run([*base, 'import', '-'], input=merged_data, capture_output=True, timeout=60)
        if sent.returncode:
            raise ValueError('Import SSH impossible : ' + sent.stderr.decode('utf-8', errors='replace').strip())
        print(f"Synchronisation SSH terminée avec {args.host} : {received} fichier(s) reçu(s), "
              f"{sent_files} envoyé(s), {local_result['merged']} document(s) fusionné(s), "
              f"{local_result['pending']} en attente localement. {sent.stdout.decode('utf-8', errors='replace').strip()}")
        return 0
    finally:
        memory.close()
