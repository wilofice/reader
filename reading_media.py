"""Local Markdown image references and a small terminal media picker."""

import curses
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


def markdown_images(source, document):
    """Return source spans; never fetch a remote image or parse fenced code."""
    masked = list(source)
    fence = None
    cursor = 0
    for line in source.splitlines(keepends=True):
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line.rstrip('\n'))
        hidden = fence is not None or marker is not None or line.startswith('    ')
        if marker:
            if fence and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                fence = None
            elif not fence:
                fence = marker[1]
        if hidden:
            masked[cursor:cursor + len(line)] = ' ' * len(line)
        cursor += len(line)
    text = ''.join(masked)
    text = re.sub(r'(`+)(.+?)\1', lambda m: ' ' * len(m[0]), text)
    definitions = {}
    for match in re.finditer(r'^ {0,3}\[([^\]]+)\]:\s*(<[^>]+>|\S+)', text, re.M):
        definitions[' '.join(match[1].split()).casefold()] = match[2].strip('<>')
    found = []

    def add(start, end, alt, target):
        target = re.sub(r'\\([ ()\\])', r'\1', target)
        try:
            parsed = urlsplit(target)
        except ValueError:
            return
        if parsed.scheme or parsed.netloc or not parsed.path:
            return
        path = Path(unquote(parsed.path)).expanduser()
        if not path.is_absolute():
            path = Path(document).parent / path
        found.append(dict(start=start, end=end, path=path.resolve(), title=alt or path.name))

    pattern = r'(?<!\\)!\[([^\]]*)\](?:\(\s*(<[^>]+>|(?:[^()\n\\]|\\.|\([^()\n]*\))*)\s*\)|\[([^\]]*)\])?'
    for match in re.finditer(pattern, text):
        if match[2] is not None:
            target = match[2].strip()
            if target.startswith('<'):
                target = target[1:target.index('>')]
            else:
                target = re.sub(r'\s+["\'].*$', '', target)
        else:
            key = ' '.join((match[3] or match[1]).split()).casefold()
            target = definitions.get(key)
        if target:
            add(match.start(), match.end(), match[1], target)

    class Images(HTMLParser):
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == 'img' and attrs.get('src'):
                line, column = self.getpos()
                start = sum(len(s) for s in text.splitlines(keepends=True)[:line - 1]) + column
                add(start, start + len(self.get_starttag_text()), attrs.get('alt', ''), attrs['src'])
    Images().feed(text)
    return sorted(found, key=lambda item: item['start'])


def choose_media(screen, choices):
    """Return a choice, or None on cancellation; no reading position changes."""
    if len(choices) == 1:
        return choices[0]
    selected = 0
    while True:
        screen.erase()
        height, width = screen.getmaxyx()
        def put(row, text, style=0):
            try:
                screen.addstr(row, 0, text[:max(0, width - 1)], style)
            except curses.error:
                pass
        put(0, 'Contenus du passage · choisir', curses.A_BOLD)
        count = max(1, height - 4)
        top = max(0, selected - count + 1)
        for row, item in enumerate(choices[top:top + count], 2):
            index = top + row - 2
            put(row, ('› ' if index == selected else '  ') + item['title'],
                curses.A_REVERSE if index == selected else 0)
        put(height - 1, '↑/↓ choisir · Entrée ouvrir · v/Échap retour')
        screen.refresh()
        key = screen.getch()
        if key in (27, ord('q'), ord('v')):
            return None
        if key in (10, 13, curses.KEY_ENTER):
            return choices[selected]
        if key in (curses.KEY_DOWN, ord('j')):
            selected = min(len(choices) - 1, selected + 1)
        elif key in (curses.KEY_UP, ord('k')):
            selected = max(0, selected - 1)
