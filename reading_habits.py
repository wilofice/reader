"""Opt-in reading focus and persistent daily word coverage."""

from bisect import bisect_left
from datetime import date
import math
import re


class DailyReading:
    def __init__(self, db, today=None):
        self.db = db
        self.today = today or date.today
        with db:
            db.execute('CREATE TABLE IF NOT EXISTS preferences (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS daily_words (day TEXT PRIMARY KEY, words INTEGER NOT NULL DEFAULT 0)')
            db.execute('''CREATE TABLE IF NOT EXISTS daily_coverage (
                day TEXT NOT NULL, path TEXT NOT NULL, digest TEXT NOT NULL, cycle INTEGER NOT NULL,
                word_start INTEGER NOT NULL, word_end INTEGER NOT NULL,
                PRIMARY KEY (day, path, digest, cycle, word_start))''')

    def get(self, key, default):
        row = self.db.execute('SELECT value FROM preferences WHERE key = ?', (key,)).fetchone()
        return row[0] if row else default

    def set(self, key, value):
        with self.db:
            self.db.execute('INSERT INTO preferences VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                            (key, str(value)))

    @property
    def goal(self):
        return int(self.get('daily_goal', '15000'))

    def set_goal(self, words):
        if words <= 0:
            raise ValueError('L’objectif quotidien doit être positif.')
        self.set('daily_goal', words)

    @property
    def day(self):
        return self.today().isoformat()

    def words(self):
        row = self.db.execute('SELECT words FROM daily_words WHERE day = ?', (self.day,)).fetchone()
        return row[0] if row else 0

    def record(self, path, digest, cycle, start, end):
        if end <= start:
            return 0
        key = self.day, str(path), digest, cycle
        # Acquire the writer lock before inspecting coverage, including across sessions.
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            intervals = self.db.execute('''SELECT word_start, word_end FROM daily_coverage
                WHERE day=? AND path=? AND digest=? AND cycle=? AND word_end>=? AND word_start<=?''',
                (*key, start, end)).fetchall()
            added = end - start - sum(max(0, min(end, right) - max(start, left)) for left, right in intervals)
            left = min([start] + [a for a, _ in intervals])
            right = max([end] + [b for _, b in intervals])
            self.db.execute('''DELETE FROM daily_coverage WHERE day=? AND path=? AND digest=?
                AND cycle=? AND word_end>=? AND word_start<=?''', (*key, start, end))
            self.db.execute('INSERT INTO daily_coverage VALUES (?, ?, ?, ?, ?, ?)', (*key, left, right))
            self.db.execute('''INSERT INTO daily_words VALUES (?, ?)
                ON CONFLICT(day) DO UPDATE SET words=words+excluded.words''', (key[0], added))
        return added


class DailyWordIndex:
    def __init__(self, text, offsets=None):
        self.anchors = [offsets[match.start()] if offsets is not None else match.start()
                        for match in re.finditer(r'\S+', text) if any(char.isalnum() for char in match[0])]

    def interval(self, source_start, source_end):
        return bisect_left(self.anchors, source_start), bisect_left(self.anchors, source_end)


class FocusSession:
    """Follow accumulated reading time; pause/help/sleep handling stays consistent."""
    def __init__(self):
        self.state = 'off'
        self.mode = 'timer'
        self.elapsed = 0.0
        self.limit = 0
        self.last = 0.0

    @property
    def visible(self):
        return self.state != 'off'

    def start(self, mode, minutes, reading_seconds):
        if mode not in ('timer', 'chrono'):
            raise ValueError('Mode focus inconnu.')
        if mode == 'timer' and minutes < 5:
            raise ValueError('Le minuteur doit durer au moins 5 minutes.')
        self.mode, self.limit = mode, minutes * 60
        self.elapsed, self.last, self.state = 0.0, reading_seconds, 'running'

    def stop(self):
        self.state = 'off'

    def update(self, reading_seconds):
        delta = max(0, reading_seconds - self.last)
        self.last = reading_seconds
        if self.state != 'running':
            return False
        self.elapsed += delta
        if self.mode == 'timer' and self.elapsed >= self.limit:
            self.elapsed, self.state = float(self.limit), 'finished'
            return True
        return False

    @property
    def display(self):
        minutes = math.ceil(max(0, self.limit - self.elapsed) / 60) if self.mode == 'timer' else int(self.elapsed // 60)
        hours, minutes = divmod(minutes, 60)
        return f'{hours:02d}:{minutes:02d}'


DIGITS = {
    '0': ('█▀█', '█ █', '█▄█'), '1': (' ▄█', '  █', '  █'),
    '2': ('▀▀█', '█▀▀', '█▄▄'), '3': ('▀▀█', ' ▀█', '▄▄█'),
    '4': ('█ █', '▀▀█', '  █'), '5': ('█▀▀', '▀▀█', '▄▄█'),
    '6': ('█▀▀', '█▀█', '█▄█'), '7': ('▀▀█', '  █', '  █'),
    '8': ('█▀█', '█▀█', '█▄█'), '9': ('█▀█', '▀▀█', '▄▄█'),
    ':': (' ', '▀', '▄'),
}


def big_clock(value):
    return [' '.join(DIGITS[char][row] for char in value) for row in range(3)]
