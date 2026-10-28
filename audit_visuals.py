#!/usr/bin/env python3
"""Offline, experimental Poppler/OpenCV comparison; never opens reading memory."""

import argparse
import csv
import hashlib
import html
import json
from pathlib import Path
import platform
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

from visual_hints import PdfVisualIndex

VERSION = 'opencv-residual-v1'


def command(args):
    result = subprocess.run(args, capture_output=True, timeout=60)
    if result.returncode:
        raise ValueError(result.stderr.decode(errors='replace')[:300])
    return result.stdout


def word_pages(path):
    raw = command(['pdftotext', '-bbox', str(path), '-']).decode('utf-8')
    # Some math fonts become literal control codes in Poppler's XML output.
    # Remove only characters forbidden by XML 1.0; retain every word rectangle.
    cleaned, removed = re.subn('[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]', '', raw)
    root = ET.fromstring(cleaned)
    pages = []
    for element in root.iter():
        if element.tag.rsplit('}', 1)[-1] != 'page':
            continue
        boxes = []
        words = []
        for child in element.iter():
            if child.tag.rsplit('}', 1)[-1] == 'word':
                boxes.append([float(child.get(key)) for key in ('xMin', 'yMin', 'xMax', 'yMax')])
                words.append(child.text or '')
        pages.append(dict(width=float(element.get('width')), height=float(element.get('height')),
                          boxes=boxes, text=' '.join(words)))
    return pages, removed


def raster(path, number, folder):
    target = Path(folder) / f'page-{number}'
    command(['pdftoppm', '-f', str(number), '-l', str(number), '-singlefile',
             '-scale-to', '1600', '-png', str(path), str(target)])
    return Path(str(target) + '.png')


def cv_regions(image, page):
    """Suppress selectable text; inspect remaining ink, including rasterized lines.

    Regions are hypotheses, not object classes or semantic interpretation.
    """
    import cv2
    import numpy as np

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape
    _, ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    for x1, y1, x2, y2 in page['boxes']:
        left = max(0, int(x1 * width / page['width']) - 1)
        right = min(width, int(x2 * width / page['width']) + 2)
        top = max(0, int(y1 * height / page['height']) - 1)
        bottom = min(height, int(y2 * height / page['height']) + 2)
        ink[top:bottom, left:right] = 0
    rim = max(1, int(min(height, width) * .02))
    ink[:rim] = ink[-rim:] = 0
    ink[:, :rim] = ink[:, -rim:] = 0
    horizontal = cv2.morphologyEx(ink, cv2.MORPH_OPEN,
                                 cv2.getStructuringElement(cv2.MORPH_RECT, (max(20, width // 30), 1)))
    vertical = cv2.morphologyEx(ink, cv2.MORPH_OPEN,
                               cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(20, height // 35))))
    merged = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, np.ones((5, 5), dtype=np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(merged)
    regions = []
    for index in range(1, count):
        x, y, w, h, pixels = map(int, stats[index])
        if w < width * .07 or h < height * .025 or w * h < width * height * .002 or pixels < 60:
            continue
        regions.append(dict(box=[round(x / width, 4), round(y / height, 4),
                                 round(w / width, 4), round(h / height, 4)], pixels=pixels))
    regions.sort(key=lambda item: item['box'][2] * item['box'][3], reverse=True)
    return dict(regions=regions, horizontal_pixels=int(cv2.countNonZero(horizontal)),
                vertical_pixels=int(cv2.countNonZero(vertical)), text_words=len(page['boxes']),
                needs_ocr=not bool(page['boxes']))


def sample_pages(rows, limit):
    """Mix disagreements, positive agreement, and negative agreement reproducibly."""
    rng = random.Random(42)
    groups = [[row['page'] for row in rows if not row['error'] and row['group'] == group]
              for group in ('cv_only', 'poppler_only', 'both', 'neither')]
    for group in groups:
        rng.shuffle(group)
    selected = []
    while any(groups) and len(selected) < limit:
        for group in groups:
            if group and len(selected) < limit:
                selected.append(group.pop())
    return selected


def review_gallery(path, rows, selected, output):
    import cv2
    images = output / 'review'
    images.mkdir(exist_ok=True)
    cards = []
    with tempfile.TemporaryDirectory(prefix='reader-audit-review-') as folder:
        for number in selected:
            source = cv2.imread(str(raster(path, number, folder)))
            if source is None:
                raise ValueError(f'Image illisible pour la page {number}')
            # Save original page and a separate diagnostic overlay.
            cv2.imwrite(str(images / f'page-{number}.jpg'), source)
            height, width = source.shape[:2]
            row = rows[number - 1]
            for region in row['opencv']['regions']:
                x, y, w, h = region['box']
                cv2.rectangle(source, (int(x * width), int(y * height)),
                              (int((x + w) * width), int((y + h) * height)), (0, 0, 220), 3)
            cv2.imwrite(str(images / f'page-{number}-zones.jpg'), source)
            cards.append(f'<article><h2>Page physique {number} · {html.escape(row["group"])}</h2>'
                         f'<p>Poppler : {row["poppler"]["images"]} image(s), '
                         f'{row["poppler"]["paths"]} indices de tracés. '
                         f'OpenCV : {len(row["opencv"]["regions"])} zone(s).</p>'
                         f'<a href="review/page-{number}-zones.jpg">Voir les zones candidates</a>'
                         f'<img loading="lazy" src="review/page-{number}.jpg" alt="Page {number}">'
                         '<label>Contenu visuel présent ? '
                         f'<select data-page="{number}"><option value="unreviewed">À vérifier</option>'
                         '<option value="present">Oui</option><option value="absent">Non</option>'
                         '<option value="uncertain">Incertain</option></select></label></article>')
    payload = json.dumps(dict(pdf_sha256=output.name, labels=[]))
    report = ('<!doctype html><html lang="fr"><meta charset="utf-8"><title>Audit visuel Reader</title>'
              '<style>body{max-width:1100px;margin:2rem auto;padding:1rem;font:17px system-ui;'
              'background:#eee;color:#222}article{background:white;padding:1rem;margin:2rem 0}'
              'img{display:block;max-width:100%;max-height:850px;margin:1rem auto}'
              'button,select{font:inherit;padding:.5rem}</style><h1>Audit visuel Reader</h1>'
              '<p>Échantillon de contrôle, sans interprétation automatique. Les désaccords ne '
              'sont pas des erreurs confirmées. Choisir Oui/Non puis exporter les annotations. '
              'Aucune donnée n’est envoyée ; exporter avant de fermer cette page.</p>'
              '<button onclick="exportLabels()">Exporter les annotations JSON</button>' + ''.join(cards) +
              '<script>function exportLabels(){const result=' + payload + ';result.labels='
              '[...document.querySelectorAll("select")].map(s=>({page:Number(s.dataset.page),label:s.value}));'
              'const a=document.createElement("a");a.href=URL.createObjectURL(new Blob('
              '[JSON.stringify(result,null,2)],{type:"application/json"}));a.download="annotations.json";'
              'a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}</script></html>')
    (output / 'review.html').write_text(report, encoding='utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Comparer Poppler et OpenCV localement sur un PDF (expérimental).')
    parser.add_argument('pdf', type=Path)
    parser.add_argument('--output', type=Path, default=Path('output/pdf/visual-audit'))
    parser.add_argument('--sample', type=int, default=16, help='nombre de pages de contrôle à illustrer')
    args = parser.parse_args(argv)
    try:
        import cv2
        cv2.setNumThreads(1)
        path = args.pdf.expanduser().resolve(strict=True)
        for tool in ('pdftotext', 'pdftoppm', 'pdfimages', 'pdftocairo'):
            if not shutil.which(tool):
                raise ValueError('Outil manquant : ' + tool + ' (Poppler)')
        digest = hashlib.sha256()
        original = path.stat()
        signature = (original.st_size, original.st_mtime_ns)
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
        key = digest.hexdigest()
        current = path.stat()
        if (current.st_size, current.st_mtime_ns) != signature:
            raise ValueError('PDF modifié pendant la préparation ; relancez l’audit.')
        output = args.output.expanduser().resolve() / key
        output.mkdir(parents=True, exist_ok=True)
        pages, removed_controls = word_pages(path)
        if not pages:
            raise ValueError('Aucune page exploitable')
        metadata = dict(version=VERSION, pdf_sha256=key, pages=len(pages), scale=1600,
                        opencv=cv2.__version__, platform=platform.platform())
        if removed_controls:
            metadata['bbox_removed_xml_controls'] = removed_controls
            print(f'Extraction : {removed_controls} caractères de contrôle XML exclus ; rectangles conservés.', flush=True)
        old = output / 'manifest.json'
        if old.exists() and json.loads(old.read_text()) != metadata:
            raise ValueError('Configuration différente : choisissez un autre --output pour conserver les résultats.')
        old.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
        progress = output / 'pages'
        progress.mkdir(exist_ok=True)
        source = '\n\n'.join(page['text'] for page in pages)
        starts, cursor = [], 0
        for page in pages:
            starts.append(cursor)
            cursor += len(page['text']) + 2
        index = PdfVisualIndex(path, source, starts, output / 'structural-cache')
        rows = []
        start = time.monotonic()
        try:
            with tempfile.TemporaryDirectory(prefix='reader-audit-') as folder:
                for number, page in enumerate(pages, 1):
                    saved = progress / f'{number:04}.json'
                    if saved.exists():
                        row = json.loads(saved.read_text())
                    else:
                        row = dict(page=number, error='', poppler={}, opencv={})
                        try:
                            before = time.monotonic()
                            hint = index.analyze(number)
                            row['poppler'] = hint
                            row['poppler_seconds'] = round(time.monotonic() - before, 4)
                            before = time.monotonic()
                            image = cv2.imread(str(raster(path, number, folder)))
                            if image is None:
                                raise ValueError('Rendu illisible')
                            row['opencv'] = cv_regions(image, page)
                            row['opencv_with_render_seconds'] = round(time.monotonic() - before, 4)
                            if hint['error']:
                                raise ValueError(hint['error'])
                            pop, cv = bool(hint['images'] or hint['paths'] >= 4), bool(row['opencv']['regions'])
                            row['group'] = 'both' if pop and cv else 'poppler_only' if pop else 'cv_only' if cv else 'neither'
                        except (OSError, ValueError, subprocess.TimeoutExpired, ET.ParseError, cv2.error) as error:
                            row.update(error=str(error), group='error')
                        if not row['error']:
                            saved.write_text(json.dumps(row), encoding='utf-8')
                    rows.append(row)
                    if number % 20 == 0 or number == len(pages):
                        print(f'{number}/{len(pages)} pages analysées', flush=True)
        finally:
            index.close()
        elapsed = time.monotonic() - start
        current = path.stat()
        if (current.st_size, current.st_mtime_ns) != signature:
            raise ValueError('PDF modifié pendant l’analyse ; relancez l’audit.')
        selected = sample_pages(rows, max(0, args.sample))
        (output / 'results.json').write_text(json.dumps(dict(metadata=metadata, rows=rows, review_pages=selected),
                                                     ensure_ascii=False, indent=2), encoding='utf-8')
        with (output / 'results.csv').open('w', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(['page', 'groupe', 'images_poppler', 'traces_poppler', 'zones_opencv', 'sans_texte_selectionnable', 'erreur'])
            for row in rows:
                writer.writerow([row['page'], row['group'], row['poppler'].get('images', ''),
                                 row['poppler'].get('paths', ''), len(row['opencv'].get('regions', [])),
                                 row['opencv'].get('needs_ocr', ''), row['error']])
        review_gallery(path, rows, selected, output)
        counts = {group: sum(row['group'] == group for row in rows)
                  for group in ('both', 'poppler_only', 'cv_only', 'neither', 'error')}
        summary = ['# Comparaison locale Poppler / OpenCV', '',
                   f'{len(pages)} pages physiques. Durée de cette passe : {elapsed:.1f} s (hors galerie et extraction initiale).',
                   f'OpenCV {cv2.__version__} ; rendu maximal 1600 pixels ; CPU, un fil OpenCV.', '',
                   '| Résultat | Pages |', '|---|---:|']
        summary += [f'| {name} | {count} |' for name, count in counts.items()]
        summary += ['', 'Les résultats sont des candidats, pas des annotations de référence.',
                    '« cv_only » ne signifie pas oubli confirmé de Poppler ; « neither » ne prouve pas une absence.',
                    'Les formules, tableaux sans bordures et pages scannées nécessitent une attention particulière.',
                    'Les zones de texte sélectionnable sont masquées avant OpenCV ; une formule peut donc être masquée.',
                    'Les fichiers pages/*.json permettent une reprise ; leurs temps peuvent provenir d’une passe antérieure.',
                    '', 'Contrôle local : [galerie](review.html). Exporter les annotations pour construire une référence.',
                    'Aucune précision ni aucun rappel global ne peuvent être annoncés sans annotations indépendantes.', '',
                    'Méthodes : [morphologie OpenCV](https://docs.opencv.org/4.13.0/dd/dd7/tutorial_morph_lines_detection.html),',
                    '[contours](https://docs.opencv.org/4.13.0/d4/d73/tutorial_py_contours_begin.html).']
        if removed_controls:
            summary += ['', f'Extraction : {removed_controls} caractères interdits dans le XML exclus ; '
                        'les rectangles de mots sont conservés. Des symboles mathématiques peuvent donc manquer au texte extrait.']
        (output / 'summary.md').write_text('\n'.join(summary) + '\n', encoding='utf-8')
        print(json.dumps(dict(output=str(output), counts=counts, seconds=round(elapsed, 2)), ensure_ascii=False))
        return 1 if counts['error'] else 0
    except ImportError:
        print('OpenCV optionnel absent : utilisez .venv-audit et requirements-audit.txt.', file=sys.stderr)
        return 1
    except (OSError, ValueError, subprocess.TimeoutExpired, ET.ParseError) as error:
        print(f'audit : {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
