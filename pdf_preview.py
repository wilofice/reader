"""PDF page inspection with Poppler, inline Chafa graphics or macOS Quick Look."""

import curses
import hashlib
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import time


def graphics_format(requested="auto", environment=None):
    if requested == "iterm2":
        return "iterm"
    if requested != "auto":
        return requested
    env = os.environ if environment is None else environment
    # Conservative defaults: a multiplexer may need explicit passthrough setup.
    if env.get("TMUX") or env.get("STY"):
        return "symbols"
    if env.get("TERM_PROGRAM") == "iTerm.app":
        return "iterm"
    if (env.get("TERM_PROGRAM") == "Apple_Terminal" and sys.platform == "darwin"
            and not env.get("SSH_CONNECTION") and not env.get("SSH_TTY")):
        return "quicklook"
    if (env.get("KITTY_WINDOW_ID") or env.get("TERM") in ("xterm-kitty", "xterm-ghostty")
            or env.get("TERM_PROGRAM") in ("ghostty", "WezTerm")):
        return "kitty"
    return "symbols"


def checked_run(command):
    try:
        result = subprocess.run(command, capture_output=True, timeout=30, check=False)
    except subprocess.TimeoutExpired as error:
        raise ValueError("Le rendu a dépassé 30 secondes ; retour à la lecture.") from error
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"Aperçu PDF impossible : {detail[:300]}")
    return result.stdout


def png_size(path):
    with Path(path).open("rb") as stream:
        header = stream.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Le rendu de page n'est pas une image PNG valide.")
    return struct.unpack(">II", header[16:24])


class PageRaster:
    def __init__(self, path, cache_root=None):
        if not shutil.which("pdftoppm"):
            raise ValueError("Aperçu PDF : installez Poppler avec `brew install poppler`.")
        self.path = Path(path).resolve(strict=True)
        self.signature = self.file_signature()
        digest = hashlib.sha256()
        with self.path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        self.check_source()
        root = cache_root or (Path(os.environ.get("XDG_CACHE_HOME", "~/.cache")).expanduser() / "reader/pdf")
        self.folder = Path(root) / digest.hexdigest()
        self.folder.mkdir(parents=True, exist_ok=True)

    def file_signature(self):
        info = self.path.stat()
        return info.st_size, info.st_mtime_ns

    def check_source(self):
        if self.file_signature() != self.signature:
            raise ValueError("Le PDF a changé pendant l'aperçu ; fermez puis rouvrez le document.")

    def render(self, number, destination, zoom=1, x=0, y=0, crop=None):
        self.check_source()
        command = ["pdftoppm", "-f", str(number), "-l", str(number), "-singlefile",
                   "-scale-to", str(1600 * zoom), "-png"]
        if crop:
            command += ["-x", str(x), "-y", str(y), "-W", str(crop[0]), "-H", str(crop[1])]
        checked_run(command + [str(self.path), str(destination)])
        self.check_source()
        output = Path(str(destination) + ".png")
        png_size(output)
        return output

    def page(self, number):
        self.check_source()
        target = self.folder / f"page-{number}-1600-v1.png"
        if target.exists():
            try:
                png_size(target)
                return target
            except ValueError:
                target.unlink()
        with tempfile.TemporaryDirectory(dir=self.folder) as temporary:
            rendered = self.render(number, Path(temporary) / "page")
            rendered.replace(target)
        return target


def inspect_quicklook(screen, image, number, total, on_time=None, title=None):
    """Use macOS's native preview for this page image, keeping the reader alive."""
    screen.erase()
    height, width = screen.getmaxyx()
    messages = [title or f"Quick Look · page PDF {number}/{total}", "",
                "Fermez la fenêtre Quick Look pour revenir au même passage.",
                "Depuis ce terminal : v / Échap / q pour fermer l'aperçu."]
    for row, message in enumerate(messages[:height]):
        try:
            screen.addstr(row, 0, message[:max(0, width - 1)])
        except curses.error:
            pass
    screen.refresh()
    screen.timeout(100)
    seconds = 0.0
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(["qlmanage", "-p", str(image)], stdin=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL, stderr=errors)
        try:
            while process.poll() is None:
                before = time.monotonic()
                key = screen.getch()
                elapsed = time.monotonic() - before
                if 0 <= elapsed <= 3:
                    seconds += elapsed
                    if on_time is not None:
                        on_time(elapsed)
                if key in (ord("v"), ord("q"), 27):
                    break
            if process.poll() not in (None, 0):
                errors.seek(0)
                raise ValueError("Quick Look : " + errors.read().decode("utf-8", errors="replace")[:300])
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)
            screen.clear()
            screen.touchwin()
            screen.refresh()
    return seconds


def inspect_image(screen, path, requested="auto", on_time=None):
    """Display a local image, without converting or changing the Markdown source."""
    path = Path(path).resolve(strict=True)
    if not path.is_file():
        raise ValueError("L'image locale n'est pas un fichier.")
    if path.suffix.lower() not in ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tif', '.tiff'):
        raise ValueError("Format d'image non pris en charge : utilisez PNG, JPEG, GIF, WebP, BMP ou TIFF.")
    output_format = graphics_format(requested)
    if output_format == 'quicklook':
        if sys.platform != 'darwin' or not shutil.which('qlmanage'):
            raise ValueError('Le mode Quick Look nécessite macOS et qlmanage.')
        return inspect_quicklook(screen, path, 1, 1, on_time, title='Quick Look · ' + path.name)
    if not shutil.which('chafa'):
        raise ValueError('Aperçu intégré : installez Chafa avec `brew install chafa`.')
    dirty = True
    seconds = 0.0
    screen.timeout(100)

    def clear():
        if output_format == 'kitty':
            sys.stdout.buffer.write(b'\x1b_Ga=d,d=A\x1b\\')
            sys.stdout.buffer.flush()
        screen.clear()

    try:
        while True:
            height, width = screen.getmaxyx()
            if dirty:
                clear()
                try:
                    screen.addstr(0, 0, ('Image Markdown · ' + path.name)[:max(0, width - 1)], curses.A_BOLD)
                    screen.addstr(height - 1, 0, 'v/Échap/q : retour au passage'[:max(0, width - 1)])
                except curses.error:
                    pass
                screen.refresh()
                if height >= 8 and width >= 35:
                    payload = checked_run(['chafa', f'--format={output_format}', '--probe=off', '--animate=off',
                                           '--relative=on', '--scale=max', f'--size={width - 2}x{height - 4}',
                                           '--align=hcenter', f'--view-size={width - 2}x{height - 4}', str(path)])
                    screen.move(2, 1)
                    screen.refresh()
                    sys.stdout.buffer.write(payload)
                    sys.stdout.buffer.flush()
                dirty = False
            before = time.monotonic()
            key = screen.getch()
            elapsed = time.monotonic() - before
            if height >= 8 and width >= 35 and 0 <= elapsed <= 3:
                seconds += elapsed
                if on_time:
                    on_time(elapsed)
            if key in (27, ord('v'), ord('q')):
                return seconds
            if key == curses.KEY_RESIZE:
                dirty = True
    finally:
        clear()
        screen.touchwin()
        screen.refresh()


def inspect_pdf(screen, path, number, total, requested="auto", cache_root=None, on_time=None):
    """Return inspection time; never change the reader's text position or cycle."""
    output_format = graphics_format(requested)
    if output_format == "quicklook":
        if sys.platform != "darwin" or not shutil.which("qlmanage"):
            raise ValueError("Le mode Quick Look nécessite macOS et qlmanage.")
    elif not shutil.which("chafa"):
        raise ValueError("Aperçu intégré : installez Chafa avec `brew install chafa`.")
    raster = PageRaster(path, cache_root)
    if output_format == "quicklook":
        try:
            screen.erase()
            screen.addstr(0, 0, "Préparation de la page Quick Look…"[:screen.getmaxyx()[1] - 1])
            screen.refresh()
            image = raster.page(number)
            return inspect_quicklook(screen, image, number, total, on_time)
        finally:
            screen.clear()
            screen.touchwin()
            screen.refresh()
    zoom, x, y = 1, 0, 0
    dirty, paused = True, False
    inspection_seconds = 0.0
    screen.timeout(100)

    def clear_graphics():
        # Clear our alternate-screen view before replacing or leaving an image.
        if output_format == "kitty":
            sys.stdout.buffer.write(b"\x1b_Ga=d,d=A\x1b\\")
            sys.stdout.buffer.flush()
        screen.clear()

    try:
        with tempfile.TemporaryDirectory(prefix="reader-preview-") as temporary:
            while True:
                height, width = screen.getmaxyx()
                if dirty:
                    clear_graphics()

                    def put(row, value, style=0):
                        try:
                            screen.addstr(row, 0, value[:max(0, width - 1)], style)
                        except curses.error:
                            pass

                    put(0, f"Aperçu PDF · page {number}/{total} · zoom ×{zoom}", curses.A_BOLD)
                    if output_format == "symbols":
                        put(1, "Mode symboles : aperçu approximatif, petits détails peu lisibles.")
                    else:
                        put(1, f"Image de la page originale · protocole {output_format}")
                    put(height - 2, "+/- zoom · flèches déplacer · n/b pages · 0 ajuster")
                    put(height - 1, "p pause compteur · v/Échap retour · q quitter l'aperçu" + (" · PAUSE" if paused else ""))
                    if width >= 35 and height >= 8:
                        put(3, "Préparation de l'image…")
                        screen.refresh()
                        base = raster.page(number)
                        base_width, base_height = png_size(base)
                        x = min(max(0, x), base_width * (zoom - 1))
                        y = min(max(0, y), base_height * (zoom - 1))
                        image = base if zoom == 1 else raster.render(
                            number, Path(temporary) / "crop", zoom, x, y, (base_width, base_height))
                        payload = checked_run([
                            "chafa", f"--format={output_format}", "--probe=off", "--animate=off",
                            "--relative=on", "--scale=max", f"--size={width - 2}x{height - 5}",
                            "--align=hcenter", f"--view-size={width - 2}x{height - 5}", str(image),
                        ])
                        screen.move(3, 0)
                        screen.clrtoeol()
                        screen.move(2, 1)
                        screen.refresh()
                        sys.stdout.buffer.write(payload)
                        sys.stdout.buffer.flush()
                    else:
                        put(3, "Agrandissez le terminal (35 × 8 min).")
                        screen.refresh()
                    dirty = False
                before = time.monotonic()
                key = screen.getch()
                elapsed = time.monotonic() - before
                if not paused and width >= 35 and height >= 8 and elapsed <= 3:
                    inspection_seconds += max(0, elapsed)
                    if on_time is not None:
                        on_time(max(0, elapsed))
                if key in (ord("v"), ord("q"), 27):
                    break
                if key == -1:
                    continue
                if key == curses.KEY_RESIZE:
                    dirty = True
                    continue
                if width < 35 or height < 8:
                    continue
                if key in (ord("+"), ord("="), ord("-")):
                    new_zoom = min(4, max(1, zoom + (-1 if key == ord("-") else 1)))
                    x = int((x + base_width / 2) * new_zoom / zoom - base_width / 2)
                    y = int((y + base_height / 2) * new_zoom / zoom - base_height / 2)
                    zoom = new_zoom
                elif key in (ord("n"), ord("b")):
                    number = min(total, max(1, number + (1 if key == ord("n") else -1)))
                    zoom, x, y = 1, 0, 0
                elif key == ord("0"):
                    zoom, x, y = 1, 0, 0
                elif key == ord("p"):
                    paused = not paused
                elif key == curses.KEY_RIGHT:
                    x += max(1, base_width // 4)
                elif key == curses.KEY_LEFT:
                    x -= max(1, base_width // 4)
                elif key == curses.KEY_DOWN:
                    y += max(1, base_height // 4)
                elif key == curses.KEY_UP:
                    y -= max(1, base_height // 4)
                else:
                    continue
                dirty = True
    finally:
        clear_graphics()
        screen.touchwin()
        screen.refresh()
    return inspection_seconds
