"""Procesado de imagen: normalizar y recortar el fondo.

Recorte: usa `rembg` si está instalado (mejor calidad); si no, un recorte simple por
relleno desde las esquinas, que funciona con fondos lisos (pared, sábana, suelo).
"""
from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageOps

MAX_SIDE = 1280
MAGENTA = (255, 0, 255)


class BadImage(ValueError):
    pass


def load(data: bytes) -> Image.Image:
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as e:  # PIL lanza varios tipos
        raise BadImage("No es una imagen válida") from e
    img = ImageOps.exif_transpose(img)
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    return img


def has_alpha(img: Image.Image) -> bool:
    """True si la imagen trae transparencia real (ya viene recortada)."""
    if img.mode not in ("RGBA", "LA", "P"):
        return False
    a = img.convert("RGBA").getchannel("A")
    return a.getextrema()[0] < 250


def to_png(data: bytes) -> bytes:
    """PNG con alfa conservado, recortado al contenido (para fotos ya limpias)."""
    img = load(data).convert("RGBA")
    bbox = img.getchannel("A").getbbox()
    buf = io.BytesIO()
    (img.crop(bbox) if bbox else img).save(buf, "PNG")
    return buf.getvalue()


def normalize(data: bytes) -> bytes:
    """Devuelve JPEG RGB orientado y con tamaño acotado (la transparencia se aplana sobre blanco)."""
    img = load(data)
    if img.mode in ("RGBA", "LA", "P"):
        rgba = img.convert("RGBA")
        base = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        img = Image.alpha_composite(base, rgba)
    img = img.convert("RGB")
    out = io.BytesIO()
    img.save(out, "JPEG", quality=88)
    return out.getvalue()


def _floodfill_cutout(img: Image.Image, thresh: int = 38) -> Image.Image:
    rgb = img.convert("RGB")
    w, h = rgb.size
    work = rgb.copy()
    for xy in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
        if work.getpixel(xy) != MAGENTA:
            ImageDraw.floodfill(work, xy, MAGENTA, thresh=thresh)
    rgba = rgb.convert("RGBA")
    px, wpx = rgba.load(), work.load()
    for y in range(h):
        for x in range(w):
            if wpx[x, y] == MAGENTA:
                px[x, y] = (0, 0, 0, 0)
    bbox = rgba.getchannel("A").getbbox()
    return rgba.crop(bbox) if bbox else rgba


def remove_background(data: bytes) -> bytes:
    """PNG con transparencia, recortado al contenido."""
    try:
        from rembg import remove  # type: ignore

        out = remove(data)
        img = Image.open(io.BytesIO(out)).convert("RGBA")
        bbox = img.getchannel("A").getbbox()
        img = img.crop(bbox) if bbox else img
    except ImportError:
        img = _floodfill_cutout(load(data))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


PALETTE_RGB = {
    "negro": (25, 25, 25), "blanco": (240, 240, 240), "gris": (128, 128, 128), "beige": (215, 195, 160),
    "marrón": (110, 75, 45), "azul marino": (25, 35, 80), "azul": (40, 90, 190), "celeste": (140, 190, 235),
    "verde": (40, 130, 70), "caqui": (130, 125, 70), "rojo": (200, 35, 40), "burdeos": (110, 20, 40),
    "rosa": (240, 150, 175), "naranja": (240, 130, 30), "amarillo": (245, 210, 40), "morado": (120, 60, 150),
}


def dominant_color(data: bytes) -> str:
    """Color de la paleta más frecuente entre los píxeles opacos (sin IA)."""
    img = load(data).convert("RGBA")
    img.thumbnail((64, 64))
    counts: dict[str, int] = {}
    raw = img.tobytes()
    for i in range(0, len(raw), 4):
        r, g, b, a = raw[i : i + 4]
        if a < 200:
            continue
        name = min(PALETTE_RGB, key=lambda n: sum((x - y) ** 2 * w for x, y, w in zip((r, g, b), PALETTE_RGB[n], (3, 4, 2))))
        counts[name] = counts.get(name, 0) + 1
    return max(counts, key=counts.get) if counts else ""
