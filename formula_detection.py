"""Formula evidence from PDF typography, without OCR or equation transcription."""

import re
import unicodedata

MATH_FONT = re.compile(r'(?:cmmi|cmsy|cmex|math|symbol|stix|xits|msam|msbm|esstix|mtmi|mtsy)', re.I)


def text_regions(page):
    # Exclude image bytes; analysis concerns selectable text only.
    content = page.get_text('dict', flags=0)
    regions = []
    width, height = page.rect.width, page.rect.height
    for block in content.get('blocks', []):
        for line in block.get('lines', []):
            spans = line.get('spans', [])
            text = ''.join(span.get('text', '') for span in spans).strip()
            chars = [char for char in text if not char.isspace()]
            if len(chars) < 4 or len(chars) > 160:
                continue
            operators = sum(unicodedata.category(char) == 'Sm' or char in '=<>±×÷' for char in chars)
            brackets = sum(char in '()[]{}' for char in chars)
            math_chars = sum(len(span.get('text', '').strip()) for span in spans
                             if MATH_FONT.search(span.get('font', '')))
            box = line.get('bbox', block.get('bbox'))
            if not box:
                continue
            if getattr(page, 'rotation', 0):
                import pymupdf
                box = pymupdf.Rect(box) * page.rotation_matrix
            fraction = math_chars / len(chars)
            dense = operators >= 2 and operators / len(chars) >= .08
            typed = math_chars >= 4 and fraction >= .25 and (operators or brackets >= 2)
            # Italic text or Greek characters alone do not constitute an equation.
            if not (dense or typed):
                continue
            words = re.findall(r'[^\W\d_]{4,}', text, re.UNICODE)
            if len(words) > 8 and fraction < .5:
                continue
            x0, y0, x1, y1 = box
            if min(width, x1) <= max(0, x0) or min(height, y1) <= max(0, y0):
                continue
            if y1 < height * .04 or y0 > height * .96:
                continue
            evidence = []
            if typed:
                evidence.append('math_font')
            if dense:
                evidence.append('operator_density')
            regions.append(dict(box=[round(max(0, x0) / width, 5), round(max(0, y0) / height, 5),
                                     round(min(width, x1) / width, 5), round(min(height, y1) / height, 5)],
                                source='text', evidence=evidence))
    return regions


def merge_regions(text, model):
    """Prefer the model's box where both methods describe the same expression."""
    result = list(model)
    for region in text:
        x0, y0, x1, y1 = region['box']
        area = max(0, x1 - x0) * max(0, y1 - y0)
        overlap = False
        for other in model:
            a0, b0, a1, b1 = other['box']
            intersection = max(0, min(x1, a1) - max(x0, a0)) * max(0, min(y1, b1) - max(y0, b0))
            if area > 0 and intersection / area > .5:
                overlap = True
                break
        if not overlap:
            result.append(region)
    return result
