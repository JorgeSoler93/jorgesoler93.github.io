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


def normalize(data: bytes) -> bytes:
    """Devuelve JPEG RGB orientado y con tamaño acotado."""
    img = load(data).convert("RGB")
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
