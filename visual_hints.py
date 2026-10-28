"""Local, conservative PDF visual hints using existing Poppler tools."""

from concurrent.futures import ThreadPoolExecutor, CancelledError
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import threading
import time
import xml.etree.ElementTree as ET


def drawing_count(root):
    count = 0

    def visit(element):
        nonlocal count
        tag = element.tag.rsplit("}", 1)[-1]
        if tag in ("defs", "symbol", "clipPath", "mask", "text"):
            return  # Glyph outlines and clipping paths are not figures.
        if tag == "path":
            style = element.get("style", "")
            stroke = element.get("stroke") or next(iter(re.findall(r"(?:^|;)\s*stroke:\s*([^;]+)", style)), "none")
            commands = re.findall(r"[LlCcQqSsTtHhVv]", element.get("d", "")) if stroke != "none" else []
            count += max(1, len(re.findall(r"[Mm]", element.get("d", ""))), len(commands))
        elif tag in ("line", "rect", "polygon", "polyline", "circle", "ellipse"):
            count += 1
        for child in element:
            visit(child)

    visit(root)
    return count


def image_count(listing, page_area):
    count = 0
    for line in listing.splitlines():
        fields = line.split()
        if len(fields) < 14 or fields[2] != "image":
            continue
        try:
            width, height = int(fields[3]), int(fields[4])
            xppi, yppi = float(fields[12]), float(fields[13])
            if width < 32 or height < 32:
                continue
            if xppi > 0 and yppi > 0:
                area = width * height * 72 * 72 / (xppi * yppi)
                if area < page_area * 0.015:
                    continue
            elif width * height < 16384:
                continue
            count += 1
        except ValueError:
            continue
    return count


def label(hint):
    if hint.get('formulas'):
        return 'Image et formules probables' if hint['images'] else 'Formule(s) probable(s)'
    if hint.get("error"):
        return "Référence " + hint["mention"] if hint.get("mention") else ""
    if hint["images"]:
        return "Image repérée"
    if hint["paths"] >= 4:
        return "Tracés visuels probables"
    if hint.get("mention"):
        return "Référence " + hint["mention"]
    return ""


class PdfVisualIndex:
    def __init__(self, path, source, starts, cache_root=None):
        self.path, self.source, self.starts = Path(path), source, starts
        self.closed = threading.Event()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="reader-visual")
        self.futures = {}
        before = self.path.stat()
        self.signature = (before.st_size, before.st_mtime_ns)
        digest = hashlib.sha256()
        with self.path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        info = self.path.stat()
        if (info.st_size, info.st_mtime_ns) != self.signature:
            raise ValueError("PDF modifié pendant la préparation ; rouvrez le document")
        root = cache_root or Path(os.environ.get("XDG_CACHE_HOME", "~/.cache")).expanduser() / "reader/visuals-v1"
        self.folder = Path(root) / digest.hexdigest()

    def run(self, command):
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        deadline = time.monotonic() + 8
        try:
            while not self.closed.is_set():
                try:
                    output, errors = process.communicate(timeout=0.1)
                    if process.returncode:
                        raise ValueError(errors.decode(errors="replace")[:200])
                    return output
                except subprocess.TimeoutExpired:
                    if time.monotonic() >= deadline:
                        raise ValueError("Analyse visuelle trop longue")
            raise CancelledError()
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()

    def analyze(self, number):
        result = dict(page=number, images=0, paths=0, mention="", error="")
        try:
            info = self.path.stat()
            if (info.st_size, info.st_mtime_ns) != self.signature:
                raise ValueError("PDF modifié : rouvrez le document")
            cache = self.folder / f"page-{number}.json"
            try:
                cached = json.loads(cache.read_text())
                if (cached.get("page") == number and not cached.get("error")
                        and all(type(cached.get(key)) is int and cached[key] >= 0 for key in ("images", "paths"))
                        and isinstance(cached.get("mention"), str)):
                    return cached
            except (OSError, ValueError, AttributeError):
                pass
            start = self.starts[number - 1]
            end = self.starts[number] if number < len(self.starts) else len(self.source)
            match = re.search(r"\b((?:Figure|Fig\.|Tableau|Table|Schéma)\s+\d+(?:[.\-–]\d+)*)\b",
                              self.source[start:end], re.I)
            if match:
                result["mention"] = match[1][:45]
            if not shutil.which("pdfimages") or not shutil.which("pdftocairo"):
                raise ValueError("Repérage incomplet : installez Poppler (pdfimages, pdftocairo)")
            listing = self.run(["pdfimages", "-f", str(number), "-l", str(number), "-list", str(self.path)])
            with tempfile.TemporaryDirectory(prefix="reader-visual-") as temporary:
                svg = Path(temporary) / "page.svg"
                self.run(["pdftocairo", "-svg", "-f", str(number), "-l", str(number), str(self.path), str(svg)])
                root = ET.parse(svg).getroot()
                view = [float(item) for item in root.get("viewBox", "0 0 595 842").split()]
                result["images"] = image_count(listing.decode(errors="replace"), max(1, view[2] * view[3]))
                result["paths"] = drawing_count(root)
            info = self.path.stat()
            if (info.st_size, info.st_mtime_ns) != self.signature:
                raise ValueError("PDF modifié : rouvrez le document")
            try:
                self.folder.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(mode="w", dir=self.folder, delete=False) as stream:
                    json.dump(result, stream, ensure_ascii=False)
                    temporary_name = Path(stream.name)
                temporary_name.replace(cache)
            except OSError:
                pass  # A read-only cache must not prevent reading.
        except (OSError, ValueError, ET.ParseError, IndexError) as error:
            result["error"] = str(error)
        return result

    def visible(self, first, last):
        # Limit outstanding work when a reader navigates faster than extraction.
        for number in range(first, min(last + 1, len(self.starts)) + 1):
            if number not in self.futures:
                if sum(not f.done() for f in self.futures.values()) >= 3:
                    break
                self.futures[number] = self.executor.submit(self.analyze, number)
        available, pending = [], False
        for number in range(first, last + 1):
            future = self.futures.get(number)
            if future is None or not future.done():
                pending = True
            elif not future.cancelled():
                available.append(future.result())
        candidates = [hint for hint in available if label(hint)]
        candidates.sort(key=lambda hint: (not bool(hint["images"] or hint["paths"] >= 4), hint["page"]))
        return (candidates[0] if candidates else None), pending, available

    def close(self):
        self.closed.set()
        self.executor.shutdown(wait=True, cancel_futures=True)
